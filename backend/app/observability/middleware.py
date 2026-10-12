import json
import os
import sqlite3
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.responses import Response

from app.observability.context import (
    request_id_var,
    trace_id_var,
    session_id_var,
    user_id_var,
    conversation_id_var,
    agent_run_id_var,
    clear_request_context,
)
from app.observability.database import get_connection
from app.observability.logger import log_event


def utc_now() -> str:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def persist_request_metrics(
    request_id: str,
    trace_id: str,
    session_id: str,
    endpoint: str,
    method: str,
    status_code: int,
    status: str,
    latency_ms: float,
    start_time: str,
    end_time: str,
    error_type: str | None = None,
) -> None:
    """Persist request metrics and complete its root trace."""

    conn = get_connection()

    try:
        conn.execute(
            """
            INSERT INTO request_metrics (
                request_id,
                trace_id,
                session_id,
                endpoint,
                method,
                status_code,
                status,
                latency_ms,
                environment,
                error_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                trace_id,
                session_id,
                endpoint,
                method,
                status_code,
                status,
                latency_ms,
                os.getenv("APP_ENV", "development"),
                error_type,
            ),
        )

        conn.execute(
            """
            UPDATE traces
            SET end_time = ?,
                duration_ms = ?,
                status = ?
            WHERE trace_id = ?
            """,
            (
                end_time,
                latency_ms,
                status,
                trace_id,
            ),
        )

        # Record the root HTTP span for this request.
        conn.execute(
            """
            INSERT INTO spans (
                span_id,
                trace_id,
                parent_span_id,
                span_name,
                span_type,
                service_name,
                start_time,
                end_time,
                duration_ms,
                status,
                input_json,
                output_json,
                error,
                metadata_json
            )
            VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                trace_id,
                f"{method} {endpoint}",
                "HTTP",
                "retail-promotion-backend",
                start_time,
                end_time,
                latency_ms,
                status,
                json.dumps({
                    "method": method,
                    "endpoint": endpoint,
                }),
                json.dumps({
                    "status_code": status_code,
                }),
                error_type,
                json.dumps({
                    "request_id": request_id,
                    "session_id": session_id,
                    "environment": os.getenv(
                        "APP_ENV", "development"
                    ),
                }),
            ),
        )

        conn.commit()

    finally:
        conn.close()


async def observability_middleware(
    request: Request,
    call_next,
) -> Response:
    """Record request logs, metrics and root trace information."""

    request_id = str(uuid4())
    trace_id = str(uuid4())

    # These can be replaced with application-specific identifiers
    # when the request payload is connected to the context.
    session_id = request.headers.get(
        "X-Session-ID"
    ) or str(uuid4())

    user_id = request.headers.get(
        "X-User-ID"
    ) or "anonymous"

    conversation_id = request.headers.get(
        "X-Conversation-ID"
    ) or str(uuid4())

    agent_run_id = str(uuid4())

    identifiers = {
        request_id_var: request_id,
        trace_id_var: trace_id,
        session_id_var: session_id,
        user_id_var: user_id,
        conversation_id_var: conversation_id,
        agent_run_id_var: agent_run_id,
    }

    # Set context identifiers for this asynchronous request.
    context_tokens = {
        variable: variable.set(value)
        for variable, value in identifiers.items()
    }

    request.state.request_id = request_id
    request.state.trace_id = trace_id

    started_at = utc_now()
    started_counter = perf_counter()

    endpoint = request.url.path
    method = request.method
    environment = os.getenv("APP_ENV", "development")

    conn = None

    try:
        # Create a root trace before executing the API endpoint.
        conn = get_connection()

        conn.execute(
            """
            INSERT INTO traces (
                trace_id,
                request_id,
                session_id,
                user_id,
                conversation_id,
                start_time,
                status,
                environment,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trace_id,
                request_id,
                session_id,
                user_id,
                conversation_id,
                started_at,
                "IN_PROGRESS",
                environment,
                json.dumps({
                    "method": method,
                    "endpoint": endpoint,
                }),
            ),
        )

        conn.commit()

    except Exception:
        # An observability failure must not prevent the actual
        # application request from running.
        import logging
        logging.getLogger(__name__).exception(
            "Could not create observability trace"
        )

    finally:
        if conn is not None:
            conn.close()

    log_event(
        message="request_received",
        level="INFO",
        endpoint=endpoint,
        status="STARTED",
        details={"method": method},
    )

    try:
        response = await call_next(request)

        latency_ms = (
            perf_counter() - started_counter
        ) * 1000

        end_time = utc_now()
        status_code = response.status_code

        status = (
            "SUCCESS" if status_code < 400 else "ERROR"
        )

        error_type = (
            "HTTPError" if status_code >= 400 else None
        )

        log_event(
            message=(
                "request_completed"
                if status_code < 400
                else "request_failed"
            ),
            level=(
                "INFO"
                if status_code < 400
                else "WARNING"
                if status_code < 500
                else "ERROR"
            ),
            endpoint=endpoint,
            latency_ms=round(latency_ms, 2),
            status=status,
            error_type=error_type,
            details={
                "method": method,
                "status_code": status_code,
            },
        )

        try:
            persist_request_metrics(
                request_id=request_id,
                trace_id=trace_id,
                session_id=session_id,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                status=status,
                latency_ms=round(latency_ms, 2),
                start_time=started_at,
                end_time=end_time,
                error_type=error_type,
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Could not persist request metrics"
            )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id

        return response

    except Exception as exc:
        latency_ms = (
            perf_counter() - started_counter
        ) * 1000

        end_time = utc_now()
        error_type = type(exc).__name__

        log_event(
            message="request_failed",
            level="ERROR",
            endpoint=endpoint,
            latency_ms=round(latency_ms, 2),
            status="ERROR",
            error_type=error_type,
            details={
                "method": method,
                "exception_type": error_type,
            },
        )

        try:
            persist_request_metrics(
                request_id=request_id,
                trace_id=trace_id,
                session_id=session_id,
                endpoint=endpoint,
                method=method,
                status_code=500,
                status="ERROR",
                latency_ms=round(latency_ms, 2),
                start_time=started_at,
                end_time=end_time,
                error_type=error_type,
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Could not persist failed request metrics"
            )

        raise

    finally:
        # Restore previous context values after the request finishes.
        for variable, token in context_tokens.items():
            variable.reset(token)
