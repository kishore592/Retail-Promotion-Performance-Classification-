from app.models.schemas import Finding

def investigate(state):
    p=state.promotion
    h=state.retrieved_data.get("historical_performance",{})
    evidence=[]
    risk=0.0
    if p:
        if p.discount_pct >= 50: risk += .45; evidence.append(f"Discount is {p.discount_pct}%, an aggressive promotion level.")
        elif p.discount_pct >= 40: risk += .25; evidence.append(f"Discount is {p.discount_pct}%, above the standard approval threshold.")
        if p.expected_margin_pct < 15: risk += .25; evidence.append(f"Expected margin is only {p.expected_margin_pct}%.")
        if h.get("return_rate_pct",0) >= 12: risk += .15; evidence.append(f"Historical return rate is {h['return_rate_pct']}%.")
        if h.get("margin_change_pct",0) <= -10: risk += .20; evidence.append(f"Historical margin change is {h['margin_change_pct']}%.")
        if h.get("avg_lift_pct",0) <= 0: risk += .15; evidence.append(f"Historical average sales lift is {h['avg_lift_pct']}%.")
    risk=min(risk,1)
    refs=[f"{d['document_id']} — {d['title']} — {d['section']}" for d in state.retrieved_documents]
    state.investigation_result=Finding(issue_type="promotion_performance_risk", evidence=evidence or ["No material risk trigger identified from available data."], policy_reference=refs, recommended_action="Review before approval" if risk>=.45 else "Eligible for merchant approval", confidence=.88 if p else .35, requires_human_review=risk>=.65)
    state.confidence=state.investigation_result.confidence
    return state
