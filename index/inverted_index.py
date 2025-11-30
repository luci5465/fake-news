import json
import re
from collections import defaultdict
import math


class InvertedIndex:
    def __init__(self):
        # term -> {doc_id -> {"tf":count, "positions":[..]}}
        self.index = defaultdict(lambda: defaultdict(lambda: {"tf": 0, "positions": []}))

        # doc stats
        self.doc_lengths = {}      # doc_id → length of tokens
        self.num_docs = 0          # number of documents
        self.idf_cache = {}        # cached IDF values

        # simple Persian + English stopwords
        self.stopwords = set([
            "و", "در", "که", "به", "از", "می", "برای",
            "the", "is", "and", "of", "to", "a", "in"
        ])

    # ----------------------------------------------------
    # TOKENIZER (supports Persian-English digits-letters)
    # ----------------------------------------------------
    def tokenize(self, text):
        text = text.lower()
        tokens = re.findall(r"[a-zA-Z0-9\u0600-\u06FF]+", text)
        return [t for t in tokens if t not in self.stopwords]

    # ----------------------------------------------------
    # Add document with TF + POSITIONS
    # ----------------------------------------------------
    def add_document(self, doc_id, text):
        tokens = self.tokenize(text)
        self.doc_lengths[doc_id] = len(tokens)
        self.num_docs += 1

        for pos, term in enumerate(tokens):
            entry = self.index[term][doc_id]
            entry["tf"] += 1
            entry["positions"].append(pos)

    # ----------------------------------------------------
    # Build index from documents
    # ----------------------------------------------------
    def build(self, documents):
        for i, doc in enumerate(documents):
            text = (doc.get("title", "") + " " + doc.get("content", "")).strip()
            self.add_document(i, text)

    # ----------------------------------------------------
    # IDF calculation with smoothing
    # ----------------------------------------------------
    def idf(self, term):
        if term in self.idf_cache:
            return self.idf_cache[term]

        df = len(self.index.get(term, {}))
        if df == 0:
            return 0

        value = math.log((self.num_docs + 1) / (df + 1)) + 1
        self.idf_cache[term] = value
        return value

    # ----------------------------------------------------
    # TF-IDF search
    # ----------------------------------------------------
    def search(self, query, top_k=10):
        tokens = self.tokenize(query)
        scores = defaultdict(float)

        for term in tokens:
            if term not in self.index:
                continue

            idf_val = self.idf(term)

            for doc_id, stats in self.index[term].items():
                tf = stats["tf"]
                scores[doc_id] += (tf * idf_val)

        # normalize by doc length
        for doc_id in scores:
            if self.doc_lengths[doc_id] > 0:
                scores[doc_id] /= self.doc_lengths[doc_id]

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    # ----------------------------------------------------
    # SAVE & LOAD
    # ----------------------------------------------------
    def save(self, path):
        data = {
            "index": self.index,
            "doc_lengths": self.doc_lengths,
            "num_docs": self.num_docs
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.index = data["index"]
        self.doc_lengths = data["doc_lengths"]
        self.num_docs = data["num_docs"]

