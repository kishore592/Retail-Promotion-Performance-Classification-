import re
from app.models.schemas import TriageResult, Promotion

def triage(state):
    ids = re.findall(r"P-\d+", state.user_query.upper())
    discount = re.search(r"(\d+(?:\.\d+)?)\s*%", state.user_query)
    duration = re.search(r"(\d+)\s*(?:day|days)", state.user_query.lower())
    entities={}
    if ids: entities["promotion_id"]=ids[0]
    if discount: entities["discount_pct"]=float(discount.group(1))
    if duration: entities["duration_days"]=int(duration.group(1))
    missing=[] if ids else ["promotion_id"]
    result=TriageResult(intent="promotion_risk_classification", category="retail_promotion", priority="high" if ids else "medium", entities=entities, missing_information=missing, confidence=0.96 if ids else 0.45, recommended_route="classify_promotion" if ids else "request_information")
    state.intent=result
    return state
