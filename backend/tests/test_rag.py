from app.rag.vector_store import knowledge_store

def test_policy_retrieval_has_metadata():
    docs=knowledge_store.search("discount above 50 percent approval margin")
    assert docs
    assert all("document_id" in d and "section" in d for d in docs)
