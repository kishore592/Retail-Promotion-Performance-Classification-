from contextvars import ContextVar
from uuid import uuid4


# Request-scoped context identifiers.
# ContextVar keeps concurrent asynchronous requests isolated.

request_id_var: ContextVar[str | None] = ContextVar(
    "request_id", default=None
)

trace_id_var: ContextVar[str | None] = ContextVar(
    "trace_id", default=None
)

session_id_var: ContextVar[str | None] = ContextVar(
    "session_id", default=None
)

user_id_var: ContextVar[str | None] = ContextVar(
    "user_id", default=None
)

conversation_id_var: ContextVar[str | None] = ContextVar(
    "conversation_id", default=None
)

agent_run_id_var: ContextVar[str | None] = ContextVar(
    "agent_run_id", default=None
)


def generate_id() -> str:
    """Generate a unique identifier."""
    return str(uuid4())


def initialize_request_context() -> dict[str, str]:
    """Generate IDs for a new request and initialize its context."""

    identifiers = {
        "request_id": generate_id(),
        "trace_id": generate_id(),
        "session_id": generate_id(),
        "user_id": "anonymous",
        "conversation_id": generate_id(),
        "agent_run_id": generate_id(),
    }

    request_id_var.set(identifiers["request_id"])
    trace_id_var.set(identifiers["trace_id"])
    session_id_var.set(identifiers["session_id"])
    user_id_var.set(identifiers["user_id"])
    conversation_id_var.set(identifiers["conversation_id"])
    agent_run_id_var.set(identifiers["agent_run_id"])

    return identifiers


def get_request_context() -> dict[str, str | None]:
    """Return the current request's identifiers."""

    return {
        "request_id": request_id_var.get(),
        "trace_id": trace_id_var.get(),
        "session_id": session_id_var.get(),
        "user_id": user_id_var.get(),
        "conversation_id": conversation_id_var.get(),
        "agent_run_id": agent_run_id_var.get(),
    }


def clear_request_context() -> None:
    """Clear identifiers after the request completes."""

    request_id_var.set(None)
    trace_id_var.set(None)
    session_id_var.set(None)
    user_id_var.set(None)
    conversation_id_var.set(None)
    agent_run_id_var.set(None)
