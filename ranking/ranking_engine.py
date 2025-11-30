import json
import os
import math
import re
from collections import defaultdict


class RankingEngine:
    def __init__(self, index_path, graph_path):
        # Load index
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.index = data["index"]              # {term: {doc_id: freq}}
        self.doc_lengths = data["doc_lengths"]  # {doc_id: length}

        # Load graph
        with open(graph_path, "r", encoding="utf-8") as f:
            g = json.load(f)

        self.degree = g.get("degree", {})
        self.authority = g.get("authority", {})
        self.hub = g.get("hub", {})

    # ------------------------------------------------------
    # Tokenizer
    # ------------------------------------------------------
    def tokenize(self, text):
        text = text.lower()
        return re.findall(r"[a-zA-Z0-9\u0600-\u06FF]+", text)

    # ------------------------------------------------------
    # Term Frequency (simple sum)
    # ------------------------------------------------------
    def tf_score(self, query_terms):
        scores = defaultdict(float)

        for term in query_terms:
            if term in self.index:
                for doc_id, freq in self.index[term].items():
                    scores[doc_id] += float(freq)

        return scores

    # ------------------------------------------------------
    # Normalize by max TF
    # ------------------------------------------------------
    def normalize_tf(self, tf_scores):
        if not tf_scores:
            return {}

        max_tf = max(tf_scores.values())
        if max_tf == 0:
            max_tf = 1.0

        return {doc_id: score / max_tf for doc_id, score in tf_scores.items()}

    # ------------------------------------------------------
    # Graph score: authority, hub, degree
    # ------------------------------------------------------
    def graph_score(self, doc_id):
        deg_info = self.degree.get(doc_id, {"in": 0, "out": 0})
        a = float(self.authority.get(doc_id, 0))
        h = float(self.hub.get(doc_id, 0))

        deg = math.log(1 + deg_info["in"] + deg_info["out"])

        return a, h, deg

    # ------------------------------------------------------
    # Final ranking
    # ------------------------------------------------------
    def rank(self, query, top_k=5, alpha=0.6, beta=0.2, gamma=0.1, delta=0.1):
        q_terms = self.tokenize(query)

        # Step 1: TF scores
        tf_raw = self.tf_score(q_terms)
        tf_norm = self.normalize_tf(tf_raw)

        final = {}

        for doc_id in tf_norm:
            a, h, deg = self.graph_score(doc_id)

            # Weighted sum
            score = (
                alpha * tf_norm[doc_id] +
                beta * a +
                gamma * h +
                delta * deg
            )

            final[doc_id] = score

        ranked = sorted(final.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(__file__))
    index_path = os.path.join(base, "data", "isna_index.json")
    graph_path = os.path.join(base, "data", "isna_graph.json")

    engine = RankingEngine(index_path, graph_path)
    print("✓ RankingEngine loaded successfully.")

    result = engine.rank("تهران")
    print("Top results:", result)
