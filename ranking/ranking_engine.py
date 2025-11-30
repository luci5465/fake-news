import json
import os
from collections import defaultdict
import math
import re

class RankingEngine:
    def __init__(self, index_path, graph_path):
        # --- load index ---
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # normalize: ensure all doc_ids are strings
        self.index = {}
        for term, postings in data["index"].items():
            fixed = {}
            for doc_id, freq in postings.items():
                try:
                    fixed[str(doc_id)] = int(freq)
                except:
                    # ignore invalid entries
                    continue
            self.index[term] = fixed

        # normalize doc lengths
        self.doc_lengths = {str(k): int(v) for k, v in data["doc_lengths"].items()}

        # --- load graph ---
        with open(graph_path, "r", encoding="utf-8") as f:
            g = json.load(f)

        # ensure keys are strings
        self.degree = {str(k): v for k, v in g["degree"].items()}
        self.authority = {str(k): float(v) for k, v in g["authority"].items()}
        self.hub = {str(k): float(v) for k, v in g["hub"].items()}

    def tokenize(self, text):
        text = text.lower()
        return re.findall(r"[a-zA-Z0-9\u0600-\u06FF]+", text)

    def tf_score(self, query_terms):
        scores = defaultdict(float)
        for term in query_terms:
            if term in self.index:
                for doc_id, freq in self.index[term].items():
                    if isinstance(freq, (int, float)):
                        scores[doc_id] += freq
        return scores

    def normalize_tf(self, scores):
        if not scores:
            return {}
        max_tf = max(scores.values())
        return {doc_id: v / max_tf for doc_id, v in scores.items()}

    def graph_score(self, doc_id):
        d = self.degree.get(doc_id, {"in": 0, "out": 0})
        a = self.authority.get(doc_id, 0.0)
        h = self.hub.get(doc_id, 0.0)

        deg = math.log(1 + d.get("in", 0) + d.get("out", 0))
        return a, h, deg

    def rank(self, query, top_k=5, alpha=0.5, beta=0.2, gamma=0.2, delta=0.1):
        q_terms = self.tokenize(query)

        tf_s = self.tf_score(q_terms)
        tf_norm = self.normalize_tf(tf_s)

        final = {}
        for doc_id in tf_norm:
            a, h, deg = self.graph_score(doc_id)
            final[doc_id] = (
                alpha * tf_norm[doc_id] +
                beta * a +
                gamma * h +
                delta * deg
            )

        ranked = sorted(final.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(__file__))
    index_path = os.path.join(base, "data", "isna_index.json")
    graph_path = os.path.join(base, "data", "isna_graph.json")

    engine = RankingEngine(index_path, graph_path)
    r = engine.rank("ایسنا")
    print(r)
