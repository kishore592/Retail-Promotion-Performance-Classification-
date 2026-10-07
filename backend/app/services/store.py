from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from app.models.database import (
    AsyncSessionLocal,
    Message,
    Workflow,
)


def _json_safe(value: Any):
    """
    Convert Pydantic models, enums and nested objects into
    JSON-serializable Python values.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]

    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump())

    if hasattr(value, "dict"):
        return _json_safe(value.dict())

    if hasattr(value, "value"):
        return _json_safe(value.value)

    return str(value)


class PersistentStore:
    """
    Persistent application store.

    Business/workflow state is stored in the database.
    Metrics remain lightweight application-level counters for now.
    """

    def __init__(self):
        self.metrics = {
            "requests": 0,
            "errors": 0,
            "latency_ms": [],
        }

    async def save_message(self, session_id, role, content, user_id=None):
        async with AsyncSessionLocal() as db:
            message = Message(
                session_id=session_id,
                role=role,
                content=str(content),
            )

            db.add(message)

            # Create the session record if it does not exist.
            existing = await db.get(
                __import__(
                    "app.models.database",
                    fromlist=["Session"],
                ).Session,
                session_id,
            )

            if existing is None:
                Session = __import__(
                    "app.models.database",
                    fromlist=["Session"],
                ).Session

                db.add(
                    Session(
                        session_id=session_id,
                        user_id=user_id,
                    )
                )

            await db.commit()

    async def get_session(self, session_id):
        result = await self._get_messages(session_id)
        return result

    async def _get_messages(self, session_id):
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Message)
                .where(Message.session_id == session_id)
                .order_by(Message.created_at.asc(), Message.id.asc())
            )

            messages = result.scalars().all()

            return [
                {
                    "role": message.role,
                    "content": message.content,
                    "ts": message.created_at.isoformat()
                    if message.created_at
                    else None,
                }
                for message in messages
            ]

    async def save_workflow(self, workflow_id, session_id, state):
        safe_state = _json_safe(state)

        classification = safe_state.get("classification") or {}

        risk_band = classification.get("risk_band")
        confidence = classification.get("confidence")

        if isinstance(risk_band, dict):
            risk_band = risk_band.get("value")

        if isinstance(confidence, dict):
            confidence = confidence.get("value")

        async with AsyncSessionLocal() as db:
            workflow = await db.get(Workflow, workflow_id)

            if workflow is None:
                workflow = Workflow(
                    workflow_id=workflow_id,
                    session_id=session_id,
                    status="COMPLETED",
                    risk_band=risk_band,
                    confidence=confidence,
                    state_json=safe_state,
                )
                db.add(workflow)
            else:
                workflow.status = "COMPLETED"
                workflow.risk_band = risk_band
                workflow.confidence = confidence
                workflow.state_json = safe_state
                workflow.updated_at = datetime.utcnow()

            await db.commit()

    async def get_workflow(self, workflow_id):
        async with AsyncSessionLocal() as db:
            workflow = await db.get(Workflow, workflow_id)

            if workflow is None:
                return None

            return workflow.state_json

    async def record_request(self):
        self.metrics["requests"] += 1

    async def record_error(self):
        self.metrics["errors"] += 1

    def record_latency(self, latency_ms):
        self.metrics["latency_ms"].append(float(latency_ms))

        # Prevent unbounded memory growth.
        if len(self.metrics["latency_ms"]) > 1000:
            self.metrics["latency_ms"] = self.metrics["latency_ms"][-1000:]

    async def health_check(self):
        async with AsyncSessionLocal() as db:
            await db.execute(select(func.count()).select_from(Workflow))
        return True


store = PersistentStore()
