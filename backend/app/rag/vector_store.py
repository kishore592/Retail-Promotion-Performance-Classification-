from pathlib import Path
from app.config.settings import settings

class KnowledgeStore:
    def __init__(self):
        self.docs = [
            {"document_id":"POL-001","title":"Promotion Approval Policy","source":"internal/promotion-policy.md","section":"Discount thresholds","version":"2026.1","effective_date":"2026-01-01","text":"Discounts above 40% require merchant approval. Discounts above 50% require senior commercial approval and a documented margin rationale."},
            {"document_id":"POL-002","title":"Promotion Risk SOP","source":"internal/risk-sop.md","section":"High-risk triggers","version":"2026.2","effective_date":"2026-04-01","text":"High-risk classification should consider historical lift, returns, margin erosion, category risk and confidence. Low-confidence high-impact recommendations must be reviewed by a human."},
            {"document_id":"POL-003","title":"Review Capacity Policy","source":"internal/review-capacity.md","section":"Operational review","version":"2026.1","effective_date":"2026-01-01","text":"The review queue should prioritize the highest-risk promotions and operate within the merchant review capacity."},
        ]
        self.chroma = None
        try:
            import chromadb
            self.chroma = chromadb.PersistentClient(path=settings.chroma_persist_dir)
            self.collection = self.chroma.get_or_create_collection("project_policies")
        except Exception:
            self.collection = None

    def search(self, query: str, category: str | None = None, k: int = 4):
        if self.collection:
            try:
                if self.collection.count() == 0:
                    self.ingest()
                result = self.collection.query(query_texts=[query], n_results=k)
                out=[]
                for i, doc in enumerate(result.get("documents", [[]])[0]):
                    meta = result.get("metadatas", [[]])[0][i]
                    out.append({**meta, "text": doc})
                return out
            except Exception:
                pass
        q=set(query.lower().split())
        scored=[]
        for d in self.docs:
            score=sum(w in d["text"].lower() or w in d["title"].lower() for w in q)
            scored.append((score,d))
        return [d for score,d in sorted(scored,key=lambda x:x[0],reverse=True)[:k] if score>0] or self.docs[:k]

    def ingest(self):
        if not self.collection: return
        self.collection.upsert(ids=[d["document_id"] for d in self.docs], documents=[d["text"] for d in self.docs], metadatas=[{k:v for k,v in d.items() if k not in {"text"}} for d in self.docs])

knowledge_store = KnowledgeStore()
