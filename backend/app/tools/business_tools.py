from pydantic import BaseModel

PROMOTIONS = {
    "P-1001": {"promotion_id":"P-1001","category":"Footwear","product_id":"SKU-1001","discount_pct":30,"duration_days":14,"expected_units":1200,"expected_margin_pct":24,"channel":"ONLINE"},
    "P-1002": {"promotion_id":"P-1002","category":"Home","product_id":"SKU-1002","discount_pct":10,"duration_days":7,"expected_units":800,"expected_margin_pct":38,"channel":"STORE"},
    "P-1003": {"promotion_id":"P-1003","category":"Electronics","product_id":"SKU-1003","discount_pct":55,"duration_days":30,"expected_units":2200,"expected_margin_pct":8,"channel":"ONLINE"},
}

HISTORY = {
    "SKU-1001": {"avg_lift_pct": 8, "return_rate_pct": 9, "margin_change_pct": -5, "category_high_risk_rate": 0.18},
    "SKU-1002": {"avg_lift_pct": 22, "return_rate_pct": 4, "margin_change_pct": -2, "category_high_risk_rate": 0.10},
    "SKU-1003": {"avg_lift_pct": -3, "return_rate_pct": 16, "margin_change_pct": -18, "category_high_risk_rate": 0.34},
}

def get_promotion(promotion_id: str):
    if promotion_id not in PROMOTIONS:
        raise ValueError(f"Promotion {promotion_id} not found")
    return PROMOTIONS[promotion_id]

def get_historical_performance(product_id: str):
    return HISTORY.get(product_id, {"avg_lift_pct":0,"return_rate_pct":0,"margin_change_pct":0,"category_high_risk_rate":0.20})
