from app.models.schemas import RiskBand, RiskClassification

def classify(state):
    p=state.promotion; h=state.retrieved_data.get("historical_performance",{})
    high=0
    if p:
        high += .45 if p.discount_pct >= 50 else .25 if p.discount_pct >= 40 else 0
        high += .25 if p.expected_margin_pct < 15 else .10 if p.expected_margin_pct < 25 else 0
        high += .15 if h.get("return_rate_pct",0)>=12 else 0
        high += .20 if h.get("margin_change_pct",0)<=-10 else 0
        high += .15 if h.get("avg_lift_pct",0)<=0 else 0
    high=min(high,1)
    band=RiskBand.HIGH if high>=.65 else RiskBand.MEDIUM if high>=.30 else RiskBand.LOW
    reasons=state.investigation_result.evidence if state.investigation_result else []
    state.classification=RiskClassification(risk_band=band, probability_high_risk=high, confidence=state.confidence or .7, reasons=reasons, recommended_action="Human merchant review required" if band==RiskBand.HIGH else "Proceed to merchant approval" if band==RiskBand.MEDIUM else "Eligible for approval")
    state.proposed_actions=[{"action":"record_classification","risk_band":band.value,"requires_approval":band==RiskBand.HIGH}]
    return state
