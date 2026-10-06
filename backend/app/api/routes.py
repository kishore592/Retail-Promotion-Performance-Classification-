import time
from fastapi import APIRouter, File, UploadFile, HTTPException
from app.models.schemas import ChatRequest, ApprovalRequest
from app.services.store import store
from app.graph.workflow import run_workflow
from app.rag.vector_store import knowledge_store

router=APIRouter(prefix="/api")

@router.post("/chat")
def chat(req: ChatRequest):
    start=time.perf_counter(); store.metrics["requests"]+=1
    store.save_message(req.session_id,"user",req.query)
    result=run_workflow(req.session_id,req.user_id,req.query,store.get_session(req.session_id))
    store.workflows[result["workflow_id"]]=result
    store.save_message(req.session_id,"assistant",result["final_response"])
    store.metrics["latency_ms"].append((time.perf_counter()-start)*1000)
    return {"workflow_id":result["workflow_id"],"response":result["final_response"],"risk_classification":result.get("classification"),"validation":result.get("validation_result"),"sources":result.get("retrieved_documents",[]),"tool_results":result.get("tool_results",[])}

@router.post("/agent/run")
def agent_run(req: ChatRequest): return chat(req)

@router.post("/documents/upload")
async def upload(file: UploadFile=File(...)):
    if file.size and file.size>5_000_000: raise HTTPException(413,"File too large")
    content=(await file.read()).decode("utf-8",errors="ignore")
    return {"filename":file.filename,"characters":len(content),"status":"accepted","note":"Use /documents/ingest to index curated knowledge."}

@router.post("/documents/ingest")
def ingest(): knowledge_store.ingest(); return {"status":"success","documents":len(knowledge_store.docs)}

@router.get("/sessions/{session_id}")
def session(session_id:str): return {"session_id":session_id,"messages":store.get_session(session_id)}

@router.get("/workflows/{workflow_id}")
def workflow(workflow_id:str):
    if workflow_id not in store.workflows: raise HTTPException(404,"Workflow not found")
    return store.workflows[workflow_id]

@router.post("/approval/{workflow_id}")
def approval(workflow_id:str, req: ApprovalRequest):
    state=store.workflows.get(workflow_id)
    if not state: raise HTTPException(404,"Workflow not found")
    state["human_approval"]={"decision":req.decision,"comment":req.comment}
    if req.decision.upper()=="APPROVE":
        from app.agents.action import execute_action
        from app.agents.response import generate_response
        state=execute_action(type("S",(),{"validation_result":type("V",(),{"decision":type("D",(),{"value":"PASS"})()})(),"human_approval":state["human_approval"],"tool_results":state.get("tool_results",[]),"classification":type("C",(),{"risk_band":type("R",(),{"value":state["classification"]["risk_band"]})()})()})())
        state = {**store.workflows[workflow_id],"human_approval":state.human_approval,"tool_results":state.tool_results}
        store.workflows[workflow_id]=state
    return store.workflows[workflow_id]

@router.get("/health")
def health(): return {"status":"ok"}

@router.get("/metrics")
def metrics():
    vals=store.metrics["latency_ms"]
    return {**store.metrics,"avg_latency_ms":sum(vals)/len(vals) if vals else 0}
