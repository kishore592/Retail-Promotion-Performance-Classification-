from app.graph.workflow import run_workflow

def test_low_or_medium_promotion():
    r=run_workflow("s1","u1","Classify promotion P-1002 for 10% discount")
    assert r["classification"]["risk_band"] in {"LOW","MEDIUM"}
    assert r["retrieved_documents"]

def test_high_risk_promotion_requires_review():
    r=run_workflow("s2","u1","Classify promotion P-1003 for 55% discount for 30 days")
    assert r["classification"]["risk_band"]=="HIGH"
    assert r["validation_result"]["decision"]=="HUMAN_REVIEW"

def test_missing_promotion_id():
    r=run_workflow("s3","u1","Please classify this promotion")
    assert "promotion ID" in r["final_response"]
