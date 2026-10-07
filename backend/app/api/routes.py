import time

from fastapi import APIRouter, File, UploadFile, HTTPException

from app.models.schemas import ChatRequest, ApprovalRequest
from app.models.database import AsyncSessionLocal, Approval, AuditLog
from app.services.store import store
from app.graph.workflow import run_workflow
from app.rag.vector_store import knowledge_store
from app.config.settings import settings


router = APIRouter(prefix="/api")


@router.post("/chat")
async def chat(req: ChatRequest):
    start = time.perf_counter()

    await store.record_request()

    try:
        # Persist user message
        await store.save_message(
            req.session_id,
            "user",
            req.query,
            req.user_id,
        )

        # Get previous conversation
        history = await store.get_session(req.session_id)

        # Run existing LangGraph workflow
        result = run_workflow(
            req.session_id,
            req.user_id,
            req.query,
            history,
        )

        workflow_id = result["workflow_id"]

        # Persist complete workflow state
        await store.save_workflow(
            workflow_id,
            req.session_id,
            result,
        )

        # Persist assistant response
        await store.save_message(
            req.session_id,
            "assistant",
            result.get("final_response", ""),
            req.user_id,
        )

        return {
            "workflow_id": workflow_id,
            "response": result.get("final_response"),
            "risk_classification": result.get("classification"),
            "validation": result.get("validation_result"),
            "sources": result.get("retrieved_documents", []),
            "tool_results": result.get("tool_results", []),
        }

    except Exception:
        await store.record_error()
        raise

    finally:
        store.record_latency(
            (time.perf_counter() - start) * 1000
        )


@router.post("/agent/run")
async def agent_run(req: ChatRequest):
    return await chat(req)


@router.post("/documents/upload")
async def upload(file: UploadFile = File(...)):
    # Basic filename validation
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )

    allowed_extensions = {
        ".txt",
        ".md",
        ".pdf",
        ".docx",
    }

    filename = file.filename.lower()

    if not any(filename.endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type",
        )

    content = await file.read()

    # 5 MB upload limit
    if len(content) > 5_000_000:
        raise HTTPException(
            status_code=413,
            detail="File too large",
        )

    return {
        "filename": file.filename,
        "bytes": len(content),
        "status": "accepted",
        "note": "Use /documents/ingest to index curated knowledge.",
    }


@router.post("/documents/ingest")
async def ingest():
    knowledge_store.ingest()

    return {
        "status": "success",
        "documents": len(knowledge_store.docs),
    }


@router.get("/sessions/{session_id}")
async def session(session_id: str):
    return {
        "session_id": session_id,
        "messages": await store.get_session(session_id),
    }


@router.get("/workflows/{workflow_id}")
async def workflow(workflow_id: str):
    result = await store.get_workflow(workflow_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow not found",
        )

    return result


@router.post("/approval/{workflow_id}")
async def approval(
    workflow_id: str,
    req: ApprovalRequest,
):
    state = await store.get_workflow(workflow_id)

    if state is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow not found",
        )

    decision = req.decision.upper()

    if decision not in {"APPROVE", "REJECT", "MODIFY"}:
        raise HTTPException(
            status_code=400,
            detail="Decision must be APPROVE, REJECT, or MODIFY",
        )

    state["human_approval"] = {
        "decision": decision,
        "comment": req.comment,
    }

    # Execute approved action using the existing agent
    if decision == "APPROVE":
        from app.agents.action import execute_action

        classification = state.get("classification", {})

        risk_band = classification.get("risk_band", "UNKNOWN")

        if isinstance(risk_band, dict):
            risk_band = risk_band.get("value", "UNKNOWN")

        action_state = type(
            "ActionState",
            (),
            {
                "validation_result": type(
                    "ValidationResult",
                    (),
                    {
                        "decision": type(
                            "Decision",
                            (),
                            {"value": "PASS"},
                        )()
                    },
                )(),
                "human_approval": state["human_approval"],
                "tool_results": state.get("tool_results", []),
                "classification": type(
                    "Classification",
                    (),
                    {
                        "risk_band": type(
                            "RiskBand",
                            (),
                            {"value": risk_band},
                        )()
                    },
                )(),
            },
        )()

        action_result = execute_action(action_state)

        state["tool_results"] = action_result.tool_results

        promotion = state.get("promotion", {})
        promotion_id = promotion.get("promotion_id", workflow_id)

        state["final_response"] = (
            f"**Merchant approval received.**\\n\\n"
            f"Promotion **{promotion_id}** has been approved after human merchant review."
        )

    # Persist updated workflow
    await store.save_workflow(
        workflow_id,
        state.get("session_id", ""),
        state,
    )

    # Persist approval and audit record
    async with AsyncSessionLocal() as db:
        db.add(
            Approval(
                workflow_id=workflow_id,
                decision=decision,
                comment=req.comment,
            )
        )

        db.add(
            AuditLog(
                workflow_id=workflow_id,
                event="HUMAN_APPROVAL",
                details={
                    "decision": decision,
                    "comment": req.comment,
                },
            )
        )

        await db.commit()

    return state


@router.get("/health")
async def health():
    database_status = "ok"

    try:
        await store.health_check()
    except Exception:
        database_status = "error"

    overall_status = (
        "ok"
        if database_status == "ok"
        else "degraded"
    )

    return {
        "status": overall_status,
        "database": database_status,
        "openai_configured": bool(settings.openai_api_key),
    }


@router.get("/metrics")
async def metrics():
    vals = store.metrics["latency_ms"]

    return {
        **store.metrics,
        "avg_latency_ms": (
            sum(vals) / len(vals)
            if vals
            else 0
        ),
    }
