from app.rag.vector_store import knowledge_store
knowledge_store.ingest()
print(f"Indexed {len(knowledge_store.docs)} policy documents")
