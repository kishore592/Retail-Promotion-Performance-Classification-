from app.rag.vector_store import knowledge_store

def retrieve_policy(state):
    q=state.user_query
    if state.promotion:
        q += f" {state.promotion.discount_pct}% {state.promotion.category} margin review high risk"
    state.retrieved_documents=knowledge_store.search(q, state.promotion.category if state.promotion else None)
    return state
