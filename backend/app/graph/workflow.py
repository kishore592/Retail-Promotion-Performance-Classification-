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
from app.config.settings import settings


def route_after_validation(state: AgentState):
    """
    Route the workflow based on validation decision.

    PASS         -> execute action
    HUMAN_REVIEW -> response / human approval
    RETRY        -> retry retrieval/investigation path
    """

    decision = state.validation_result.decision.value

    if decision == "PASS":
        return "action"

    if decision == "HUMAN_REVIEW":
        return "response"

    if decision == "RETRY":
        if state.retry_count < settings.max_retries:
            return "retry"
        return "response"

    return "response"


def bump_retry(state: AgentState):
    """
    Increment the bounded retry counter.

    The maximum number of retries is controlled by MAX_RETRIES.
    """

    state.retry_count += 1

    return state


def _fallback_run(state):
    """
    Fallback execution path used when LangGraph is unavailable.
    """

    for fn in (
        triage,
        retrieve_data,
        retrieve_policy,
        investigate,
        classify,
        validate,
    ):
        state = fn(state)

    decision = state.validation_result.decision.value

    if decision == "HUMAN_REVIEW":
        return state.model_dump()

    if decision == "PASS":
        state = execute_action(state)

    elif decision == "RETRY":
        if state.retry_count < settings.max_retries:
            state.retry_count += 1

            # Retry the retrieval/investigation path once bounded.
            state = retrieve_policy(state)
            state = investigate(state)
            state = classify(state)
            state = validate(state)

            if state.validation_result.decision.value == "PASS":
                state = execute_action(state)

    state = generate_response(state)

    return state.model_dump()


def _node_adapter(fn):
    """
    Adapt existing AgentState-returning agents to LangGraph's
    dict-based node update contract.
    """
    def wrapped(state):
        if isinstance(state, dict):
            state = AgentState.model_validate(state)

        result = fn(state)

        if isinstance(result, AgentState):
            return result.model_dump()

        return result

    return wrapped


def make_graph():
    if not HAS_LANGGRAPH:
        return None

    g = StateGraph(AgentState)

    nodes = [
        ("triage", triage),
        ("data", retrieve_data),
        ("rag", retrieve_policy),
        ("investigation", investigate),
        ("classifier", classify),
        ("validator", validate),
        ("action", execute_action),
        ("response", generate_response),
        ("retry", bump_retry),
    ]

    for name, fn in nodes:
        g.add_node(name, _node_adapter(fn))

    g.set_entry_point("triage")

    g.add_edge("triage", "data")
    g.add_edge("data", "rag")
    g.add_edge("rag", "investigation")
    g.add_edge("investigation", "classifier")
    g.add_edge("classifier", "validator")

    g.add_conditional_edges(
        "validator",
        lambda state: route_after_validation(
            AgentState.model_validate(state)
        ),
        {
            "action": "action",
            "response": "response",
            "retry": "retry",
        },
    )

    # Retry starts again from policy retrieval.
    g.add_edge("retry", "rag")

    g.add_edge("action", "response")
    g.add_edge("response", END)

    return g.compile()


graph = make_graph()


def run_workflow(session_id, user_id, query, history=None):
    state = AgentState(
        session_id=session_id,
        user_id=user_id,
        user_query=query,
        conversation_history=history or [],
        workflow_id=str(uuid4()),
    )

    if graph:
        result = graph.invoke(state.model_dump())

        # LangGraph may return a Pydantic state or dictionary depending
        # on the installed LangGraph version/configuration.
        if hasattr(result, "model_dump"):
            return result.model_dump()

        return result

    return _fallback_run(state)
