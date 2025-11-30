import json
import re
import os
from collections import defaultdict
from math import sqrt


def tokenize(text):
    """توکن‌سازی فارسی + انگلیسی"""
    text = text.lower()
    return re.findall(r"[a-zA-Z0-9\u0600-\u06FF]+", text)


def build_index(docs):
    index = defaultdict(lambda: defaultdict(int))
    doc_lengths = {}

    for item in docs:
        doc_id = str(item["id"])
        content = item["content"]

        tokens = tokenize(content)
        if not tokens:
            continue

        # مرحله ۱: ساخت inverted index
        freqs = defaultdict(int)
        for token in tokens:
            freqs[token] += 1

        for token, count in freqs.items():
            index[token][doc_id] = count

        # مرحله ۲: طول سند (L2 norm)
        length = sqrt(sum(count * count for count in freqs.values()))
        doc_lengths[doc_id] = max(length, 1e-6)

    return index, doc_lengths


def save_index(index, doc_lengths, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    out = {
        "index": index,
        "doc_lengths": doc_lengths,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)

    print(f"✓ Index saved → {path}")


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(__file__))
    clean_path = os.path.join(base, "data", "cleaned", "isna_cleaned.json")
    out_path = os.path.join(base, "data", "isna_index.json")

    with open(clean_path, "r", encoding="utf-8") as f:
        docs = json.load(f)

    index, doc_len = build_index(docs)
    save_index(index, doc_len, out_path)
