def execute_action(state):
    if state.validation_result and state.validation_result.decision.value=="HUMAN_REVIEW" and not state.human_approval:
        return state
    state.tool_results.append({"tool":"record_classification","status":"success","risk_band":state.classification.risk_band.value if state.classification else None})
    return state
