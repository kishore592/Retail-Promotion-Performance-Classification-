from app.models.schemas import ValidationDecision, ValidationResult

def validate(state):
    issues=[]; checks=[]
    if not state.promotion: issues.append("Promotion data is missing")
    else: checks.append("Promotion record available")
    if not state.retrieved_documents: issues.append("No policy evidence retrieved")
    else: checks.append("Policy citations available")
    if not state.classification: issues.append("Risk classification missing")
    else: checks.append("Structured classification available")
    if state.errors: issues.extend(state.errors)
    if issues:
        decision=ValidationDecision.RETRY if state.retry_count < 2 else ValidationDecision.BLOCK
    elif state.classification and state.classification.risk_band.value=="HIGH":
        decision=ValidationDecision.HUMAN_REVIEW
    else:
        decision=ValidationDecision.PASS
    state.validation_result=ValidationResult(decision=decision, checks=checks, issues=issues)
    return state
