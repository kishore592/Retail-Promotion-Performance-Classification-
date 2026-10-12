import json
import logging
import os
import re
import sqlite3
from typing import Any

from app.observability.context import get_request_context
from app.observability.database import get_connection


VALID_LEVELS = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
}

logger = logging.getLogger(__name__)


def _redact_text(value: str) -> str:
    """Remove common credential patterns from log text."""

    value = re.sub(
        r"sk-[A-Za-z0-9_-]{10,}",
        "[REDACTED_API_KEY]",
        value,
    )

    value = re.sub(
        r"(?i)\bBearer\s+\S+",
        "Bearer [REDACTED]",
        value,
    )

    value = re.sub(
        r"(?i)(api[_-]?key|password|secret|authorization)"
        r"\s*[:=]\s*['\"]?[^'\"\s,;]+",
        r"\1=[REDACTED]",
        value,
    )

    return value


def _sanitize(value: Any) -> Any:
    """Sanitize metadata before storing it as JSON."""

    sensitive_keys = {
        "api_key",
        "apikey",
        "openai_api_key",
        "authorization",
        "password",
        "secret",
        "access_token",
        "refresh_token",
        "credentials",
    }

    if isinstance(value, dict):
        result = {}

        for key, item in value.items():
            if str(key).lower() in sensitive_keys:
                result[str(key)] = "[REDACTED]"
            else:
                result[str(key)] = _sanitize(item)

        return result

    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]

    if isinstance(value, str):
        return _redact_text(value)

    if value is None or isinstance(value, (int, float, bool)):
        return value

    return _redact_text(str(value))


def log_event(
    message: str,
    level: str = "INFO",
    service: str = "retail-promotion-backend",
    endpoint: str | None = None,
    agent_name: str | None = None,
    tool_name: str | None = None,
    model_name: str | None = None,
    latency_ms: float | None = None,
    status: str | None = None,
    error_type: str | None = None,
    details: dict[str, Any] | None = None,
) -> bool:
    """
    Persist a structured application event in observability.db.

    Returns True when saved successfully and False if persistence fails.
    Logging failures do not interrupt the main application.
    """

    normalized_level = level.upper()

    if normalized_level not in VALID_LEVELS:
        normalized_level = "INFO"

    context = get_request_context()

    details_json = json.dumps(
        _sanitize(details or {}),
        default=str,
        ensure_ascii=False,
    )

    conn: sqlite3.Connection | None = None

    try:
        conn = get_connection()

        conn.execute(
            """
            INSERT INTO application_logs (
                level,
                service,
                environment,
                request_id,
                trace_id,
                session_id,
                user_id,
                conversation_id,
                agent_run_id,
                agent_name,
                tool_name,
                model_name,
                endpoint,
                message,
                latency_ms,
                status,
                error_type,
                details_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_level,
                service,
                os.getenv("APP_ENV", "development"),
                context.get("request_id"),
                context.get("trace_id"),
                context.get("session_id"),
                context.get("user_id"),
                context.get("conversation_id"),
                context.get("agent_run_id"),
                agent_name,
                tool_name,
                model_name,
                endpoint,
                _redact_text(message),
                latency_ms,
                status,
                error_type,
                details_json,
            ),
        )

        conn.commit()
        return True

    except Exception:
        logger.exception(
            "Failed to persist observability event"
        )
        return False

    finally:
        if conn is not None:
            conn.close()
