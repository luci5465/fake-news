import json
import os
from inverted_index import InvertedIndex

base_dir = os.path.dirname(os.path.dirname(__file__))
cleaned_path = os.path.join(base_dir, "data", "cleaned", "isna_cleaned.json")
index_path = os.path.join(base_dir, "data", "isna_index.json")

with open(cleaned_path, "r", encoding="utf-8") as f:
    docs = json.load(f)

idx = InvertedIndex()
idx.build(docs)
idx.save(index_path)

print("Index saved to:", index_path)
