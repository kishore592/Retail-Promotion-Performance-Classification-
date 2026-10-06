from uuid import uuid4
try:
    from langgraph.graph import StateGraph, END
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False
from app.models.schemas import AgentState
from app.agents.triage import triage
from app.agents.data_agent import retrieve_data
from app.agents.rag_agent import retrieve_policy
from app.agents.investigation import investigate
from app.agents.classifier import classify
from app.agents.validator import validate
from app.agents.action import execute_action
from app.agents.response import generate_response

def _fallback_run(state):
    for fn in (triage, retrieve_data, retrieve_policy, investigate, classify, validate):
        state = fn(state)
    if state.validation_result.decision.value == "HUMAN_REVIEW":
        return state.model_dump()
    if state.validation_result.decision.value == "PASS":
        state = execute_action(state)
    elif state.validation_result.decision.value == "RETRY":
        state.retry_count += 1
    state = generate_response(state)
    return state.model_dump()

def make_graph():
    if not HAS_LANGGRAPH:
        return None
    g=StateGraph(AgentState)
    for name,fn in [("triage",triage),("data",retrieve_data),("rag",retrieve_policy),("investigation",investigate),("classifier",classify),("validator",validate),("action",execute_action),("response",generate_response),("retry",bump_retry)]:
        g.add_node(name,fn)
    g.set_entry_point("triage")
    g.add_edge("triage","data"); g.add_edge("data","rag"); g.add_edge("rag","investigation"); g.add_edge("investigation","classifier"); g.add_edge("classifier","validator")
    g.add_conditional_edges("validator",route_after_validation,{"action":"action","response":"response","retry":"retry"})
    g.add_edge("retry","rag")
    g.add_edge("action","response"); g.add_edge("response",END)
    return g.compile()

graph=make_graph()

def run_workflow(session_id,user_id,query,history=None):
    state=AgentState(session_id=session_id,user_id=user_id,user_query=query,conversation_history=history or [],workflow_id=str(uuid4()))
    return graph.invoke(state) if graph else _fallback_run(state)
