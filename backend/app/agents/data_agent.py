from app.tools.business_tools import get_promotion, get_historical_performance
from app.models.schemas import Promotion

def retrieve_data(state):
    if not state.intent or not state.intent.entities.get("promotion_id"):
        return state
    try:
        p=get_promotion(state.intent.entities["promotion_id"])
        state.promotion=Promotion(**p)
        history=get_historical_performance(p["product_id"])
        state.retrieved_data={"promotion":p,"historical_performance":history}
        state.tool_results.append({"tool":"get_promotion","status":"success","promotion_id":p["promotion_id"]})
        state.tool_results.append({"tool":"get_historical_performance","status":"success","product_id":p["product_id"]})
    except Exception as exc:
        state.errors.append(str(exc))
    return state
