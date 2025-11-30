import json
import os
import re
from collections import defaultdict


class InvertedIndex:
    def __init__(self):
        self.index = defaultdict(dict)
        self.doc_lengths = {}

    def tokenize(self, text):
        text = text.lower()
        tokens = re.findall(r"[a-zA-Z0-9\u0600-\u06FF]+", text)
        return tokens

    def add_document(self, doc_id, text):
        tokens = self.tokenize(text)
        self.doc_lengths[doc_id] = len(tokens)

        freqs = defaultdict(int)
        for t in tokens:
            freqs[t] += 1

        for term, count in freqs.items():
            self.index[term][doc_id] = count

    def build(self, documents):
        for i, doc in enumerate(documents):
            text = (doc.get("title", "") + " " + doc.get("content", "")).strip()
            self.add_document(str(i), text)

    def save(self, path):
        data = {
            "index": self.index,
            "doc_lengths": self.doc_lengths
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        print(f"✓ Inverted index saved → {path}")

    def load(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.index = data["index"]
        self.doc_lengths = data["doc_lengths"]
        print(f"✓ Inverted index loaded → {path}")

    def search(self, query):
        tokens = self.tokenize(query)
        results = defaultdict(int)
        for t in tokens:
            if t in self.index:
                for doc_id, freq in self.index[t].items():
                    results[doc_id] += freq
        return sorted(results.items(), key=lambda x: x[1], reverse=True)


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(__file__))
    cleaned_path = os.path.join(base_dir, "data", "cleaned", "isna_cleaned.json")
    index_path = os.path.join(base_dir, "data", "isna_index.json")

    with open(cleaned_path, "r", encoding="utf-8") as f:
        docs = json.load(f)

    idx = InvertedIndex()
    idx.build(docs)
    idx.save(index_path)

    print("✓ Build complete.")
