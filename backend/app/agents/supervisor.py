"""Supervisor policy layer.

The LangGraph graph is the executable orchestrator; this module centralizes
routing policy so the supervisor decision is explicit and testable.
"""
def supervisor_route(state):
    if state.intent and state.intent.missing_information:
        return "request_information"
    if state.errors and not state.retrieved_data:
        return "recover_data"
    return "classify_promotion"
