def generate_response(state):
    if not state.promotion:
        state.final_response="I need a promotion ID before I can classify the planned promotion."
        return state
    c=state.classification; v=state.validation_result
    citations="; ".join(f"[{d['document_id']}: {d['title']} / {d['section']}]" for d in state.retrieved_documents)
    status = "Pending human merchant approval." if v and v.decision.value=="HUMAN_REVIEW" and not state.human_approval else "Classification recorded successfully."
    state.final_response=(f"**Risk classification: {c.risk_band.value}**\n\n"
      f"Promotion **{state.promotion.promotion_id}** ({state.promotion.category}, {state.promotion.discount_pct}% discount) has a high-risk probability of **{c.probability_high_risk:.0%}**.\n\n"
      f"**Why:** {' '.join(c.reasons)}\n\n"
      f"**Recommendation:** {c.recommended_action}. {status}\n\n"
      f"**Sources:** {citations}")
    return state
