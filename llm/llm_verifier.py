import requests
import math
from typing import List, Dict, Any
from ranking_engine import RankingEngine
from inverted_index import InvertedIndex


class FakeNewsDetector:
    def __init__(self, host: str, model: str, ranker: RankingEngine, embeddings: List[Dict[str, Any]]):
        self.host = host
        self.model = model
        self.ranker = ranker
        self.embeddings = embeddings

    # -----------------------------
    # 1) Embed text using Ollama
    # -----------------------------
    def embed(self, text: str) -> List[float]:
        url = f"{self.host}/api/embeddings"
        payload = {"model": "nomic-embed-text", "prompt": text}

        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["embedding"]  # nomic returns { "embedding": [...] }

    # ---------------------------------
    # 2) Semantic Vector Search
    # ---------------------------------
    def semantic_search(self, query: str, top_k=5):
        q_emb = self.embed(query)

        def cosine(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(x * x for x in b))
            if na == 0 or nb == 0:
                return 0
            return dot / (na * nb)

        scored = []
        for doc in self.embeddings:
            sim = cosine(q_emb, doc["embedding"])
            scored.append((doc["id"], sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    # ---------------------------------
    # 3) Hybrid Retrieval
    # ---------------------------------
    def hybrid_retrieve(self, query: str, k=5):
        lex = self.ranker.rank(query, top_k=k)
        sem = self.semantic_search(query, top_k=k)

        combined = {}

        for doc_id, score in lex:
            combined[doc_id] = combined.get(doc_id, 0) + score

        for doc_id, score in sem:
            combined[doc_id] = combined.get(doc_id, 0) + score

        final = sorted(combined.items(), key=lambda x: x[1], reverse=True)
        return [doc_id for doc_id, _ in final[:k]]

    # ---------------------------------
    # 4) Ask LLM (Ollama) with Debug Output
    # ---------------------------------
    def ask_llm(self, claim, evidence):
        url = f"{self.host}/api/generate"

        prompt = (
            "آیا این ادعا واقعی است یا جعلی؟\n"
            f"ادعا: {claim}\n\n"
            "شواهد:\n"
            f"{evidence}\n\n"
            "پاسخ را فقط با یکی از این سه کلمه بده: واقعی / جعلی / نامشخص"
        )

        payload = {"model": self.model, "prompt": prompt}

        resp = requests.post(url, json=payload)

        # DEBUG:
        print("\n=== RAW RESPONSE FROM OLLAMA ===")
        print(resp.text)
        print("================================\n")

        data = resp.json()

        # حالت‌های مختلف پاسخ Ollama
        if "response" in data:
            return data["response"]

        if "message" in data:
            return data["message"]

        if "output" in data:
            return data["output"]

        return str(data)

    # ---------------------------------
    # 5) Full Detection Pipeline
    # ---------------------------------
    def detect(self, claim: str, documents: Dict[str, Any]):
        # Retrieve evidence
        top_docs = self.hybrid_retrieve(claim, k=5)

        evidence_text = ""
        for doc_id in top_docs:
            for d in documents:
                if str(d.get("id")) == str(doc_id):
                    evidence_text += f"\n---\n{d.get('title','')}\n{d.get('content','')}\n"

        # Ask LLM to decide
        verdict = self.ask_llm(claim, evidence_text)

        return verdict, evidence_text
