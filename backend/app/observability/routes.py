import math
import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.observability.database import get_connection


router = APIRouter()


def fetch_all(
    conn: sqlite3.Connection,
    query: str,
    params: tuple = (),
) -> list[dict[str, Any]]:
    """Execute a SELECT query and return dictionaries."""
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def percentile(values: list[float], p: float) -> float | None:
    """Calculate a percentile using the nearest-rank method."""
    if not values:
        return None

    values = sorted(values)
    index = max(0, math.ceil(p * len(values)) - 1)

    return round(values[index], 2)


@router.get("/api/observability/overview")
def observability_overview():
    """Return summary KPIs from persisted observability data."""

    conn = get_connection()

    try:
        requests = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END)
                    AS successful,
                SUM(CASE WHEN status != 'SUCCESS' THEN 1 ELSE 0 END)
                    AS failed,
                AVG(latency_ms) AS avg_latency,
                MAX(latency_ms) AS max_latency
            FROM request_metrics
            """
        ).fetchone()

        total = requests["total"] or 0
        successful = requests["successful"] or 0
        failed = requests["failed"] or 0

        latencies = [
            float(row["latency_ms"])
            for row in conn.execute(
                """
                SELECT latency_ms
                FROM request_metrics
                WHERE latency_ms IS NOT NULL
                """
            ).fetchall()
        ]

        llm = conn.execute(
            """
            SELECT
                COUNT(*) AS calls,
                COALESCE(SUM(total_tokens), 0) AS tokens,
                COALESCE(SUM(estimated_cost), 0) AS cost
            FROM llm_metrics
            """
        ).fetchone()

        agents = conn.execute(
            "SELECT COUNT(*) AS total FROM agent_metrics"
        ).fetchone()

        tools = conn.execute(
            "SELECT COUNT(*) AS total FROM tool_metrics"
        ).fetchone()

        rag = conn.execute(
            "SELECT COUNT(*) AS total FROM rag_metrics"
        ).fetchone()

        logs = conn.execute(
            "SELECT COUNT(*) AS total FROM application_logs"
        ).fetchone()

        alerts = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM alerts
            WHERE status IN ('WARNING', 'CRITICAL')
            """
        ).fetchone()

        guardrails = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM guardrail_events
            WHERE UPPER(decision) IN ('BLOCK', 'BLOCKED', 'DENY', 'DENIED')
            """
        ).fetchone()

        drift = conn.execute(
            "SELECT status FROM drift_observations ORDER BY id DESC LIMIT 1"
        ).fetchone()

        drift_status = drift["status"] if drift else "NO_DATA"

        return {
            "requests": {
                "total": total,
                "successful": successful,
                "failed": failed,
                "success_rate_percent": round(
                    successful / total * 100, 2
                ) if total else 0,
                "failure_rate_percent": round(
                    failed / total * 100, 2
                ) if total else 0,
                "average_latency_ms": round(
                    requests["avg_latency"], 2
                ) if requests["avg_latency"] is not None else None,
                "p50_latency_ms": percentile(latencies, 0.50),
                "p95_latency_ms": percentile(latencies, 0.95),
                "p99_latency_ms": percentile(latencies, 0.99),
                "max_latency_ms": requests["max_latency"],
            },
            "llm": {
                "total_calls": llm["calls"],
                "total_tokens": llm["tokens"],
                "estimated_cost": round(llm["cost"], 6),
            },
            "agents": {
                "total_runs": agents["total"],
            },
            "tools": {
                "total_calls": tools["total"],
            },
            "rag": {
                "total_retrievals": rag["total"],
            },
            "application_logs": logs["total"],
            "active_alerts": alerts["total"],
            "guardrail_blocks": guardrails["total"],
            "drift_status": drift_status,
        }

    finally:
        conn.close()


@router.get("/api/logs")
def get_logs(
    level: str | None = None,
    status: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    session_id: str | None = None,
    endpoint: str | None = None,
    search: str | None = None,
    sort_by: str = Query(
        default="timestamp",
        pattern="^(timestamp|level|latency_ms|status)$",
    ),
    sort_order: str = Query(
        default="desc",
        pattern="^(asc|desc)$",
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Search and paginate persisted application logs."""

    conditions = []
    params: list[Any] = []

    filters = [
        ("level", level),
        ("status", status),
        ("request_id", request_id),
        ("trace_id", trace_id),
        ("session_id", session_id),
        ("endpoint", endpoint),
    ]

    for column, value in filters:
        if value:
            conditions.append(f"{column} = ?")
            params.append(value)

    if search:
        conditions.append(
            """
            (
                message LIKE ?
                OR endpoint LIKE ?
                OR error_type LIKE ?
                OR request_id LIKE ?
                OR trace_id LIKE ?
            )
            """
        )
        term = f"%{search}%"
        params.extend([term, term, term, term, term])

    where = " WHERE " + " AND ".join(conditions) if conditions else ""

    conn = get_connection()

    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM application_logs{where}",
            tuple(params),
        ).fetchone()[0]

        rows = fetch_all(
            conn,
            f"""
            SELECT *
            FROM application_logs
            {where}
            ORDER BY {sort_by} {sort_order.upper()}, id DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params) + (limit, offset),
        )

        return {
            "items": rows,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    finally:
        conn.close()


@router.get("/api/logs/{log_id}")
def get_log(log_id: int):
    """Return one complete structured log record."""

    conn = get_connection()

    try:
        row = conn.execute(
            "SELECT * FROM application_logs WHERE id = ?",
            (log_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Log record not found",
            )

        return dict(row)

    finally:
        conn.close()


@router.get("/api/metrics/requests")
def get_request_metrics(
    endpoint: str | None = None,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Return request KPIs and paginated request records."""

    conditions = []
    params: list[Any] = []

    if endpoint:
        conditions.append("endpoint = ?")
        params.append(endpoint)

    if status:
        conditions.append("status = ?")
        params.append(status)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""

    conn = get_connection()

    try:
        summary = conn.execute(
            f"""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END)
                    AS successful,
                SUM(CASE WHEN status != 'SUCCESS' THEN 1 ELSE 0 END)
                    AS failed,
                AVG(latency_ms) AS average_latency_ms,
                MAX(latency_ms) AS maximum_latency_ms
            FROM request_metrics
            {where}
            """,
            tuple(params),
        ).fetchone()

        total = summary["total"] or 0
        successful = summary["successful"] or 0
        failed = summary["failed"] or 0

        latencies = [
            float(row["latency_ms"])
            for row in conn.execute(
                f"""
                SELECT latency_ms
                FROM request_metrics
                {where}
                AND latency_ms IS NOT NULL
                """ if where else """
                SELECT latency_ms
                FROM request_metrics
                WHERE latency_ms IS NOT NULL
                """,
                tuple(params),
            ).fetchall()
        ]

        records = fetch_all(
            conn,
            f"""
            SELECT *
            FROM request_metrics
            {where}
            ORDER BY timestamp DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params) + (limit, offset),
        )

        return {
            "summary": {
                "total_requests": total,
                "successful_requests": successful,
                "failed_requests": failed,
                "success_rate_percent": round(
                    successful / total * 100, 2
                ) if total else 0,
                "failure_rate_percent": round(
                    failed / total * 100, 2
                ) if total else 0,
                "average_latency_ms": round(
                    summary["average_latency_ms"], 2
                ) if summary["average_latency_ms"] is not None else None,
                "p50_latency_ms": percentile(latencies, 0.50),
                "p95_latency_ms": percentile(latencies, 0.95),
                "p99_latency_ms": percentile(latencies, 0.99),
                "maximum_latency_ms": summary["maximum_latency_ms"],
            },
            "items": records,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    finally:
        conn.close()


@router.get("/api/traces")
def get_traces(
    status: str | None = None,
    request_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List traces with pagination."""

    conditions = []
    params: list[Any] = []

    if status:
        conditions.append("status = ?")
        params.append(status)

    if request_id:
        conditions.append("request_id = ?")
        params.append(request_id)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""

    conn = get_connection()

    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM traces{where}",
            tuple(params),
        ).fetchone()[0]

        items = fetch_all(
            conn,
            f"""
            SELECT *
            FROM traces
            {where}
            ORDER BY start_time DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params) + (limit, offset),
        )

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    finally:
        conn.close()


@router.get("/api/traces/{trace_id}")
def get_trace(trace_id: str):
    """Return a trace and related observability records."""

    conn = get_connection()

    try:
        trace = conn.execute(
            "SELECT * FROM traces WHERE trace_id = ?",
            (trace_id,),
        ).fetchone()

        if trace is None:
            raise HTTPException(
                status_code=404,
                detail="Trace not found",
            )

        related_tables = {
            "spans": "spans",
            "logs": "application_logs",
            "requests": "request_metrics",
            "llm_calls": "llm_metrics",
            "agent_runs": "agent_metrics",
            "tool_calls": "tool_metrics",
            "rag_retrievals": "rag_metrics",
            "errors": "error_events",
            "guardrails": "guardrail_events",
            "approvals": "human_approval_events",
        }

        related = {}

        for key, table in related_tables.items():
            related[key] = fetch_all(
                conn,
                f"SELECT * FROM {table} WHERE trace_id = ?",
                (trace_id,),
            )

        return {
            "trace": dict(trace),
            **related,
        }

    finally:
        conn.close()


@router.get("/api/drift")
def get_drift(
    drift_type: str | None = None,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List persisted drift observations."""

    conditions = []
    params: list[Any] = []

    if drift_type:
        conditions.append("drift_type = ?")
        params.append(drift_type)

    if status:
        conditions.append("status = ?")
        params.append(status)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""

    conn = get_connection()

    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM drift_observations{where}",
            tuple(params),
        ).fetchone()[0]

        items = fetch_all(
            conn,
            f"""
            SELECT *
            FROM drift_observations
            {where}
            ORDER BY timestamp DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params) + (limit, offset),
        )

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    finally:
        conn.close()
