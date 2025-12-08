import json
import math
import os
import sys
import re
import unicodedata

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("PROJECT_DATA_DIR", os.path.join(BASE_DIR, "data"))
INDEX_DIR = os.path.join(BASE_DIR, "index")
INDEX_FILE = os.path.join(INDEX_DIR, "inverted_index.json")
GRAPH_FILE = os.path.join(DATA_DIR, "news_graph.json")

PERSIAN_STOPWORDS = {
    "از", "به", "در", "که", "و", "را", "این", "آن", "برای", "با", "است", "شد", "می", "ها", "های", "بر",
    "تا", "یک", "بود", "نیز", "کند", "شود", "کرده", "شده", "باید", "گفت", "دارد", "وی", "اما", "اگر",
    "نیست", "هستند", "بی", "تر", "ترین", "خود", "دیگر", "هم", "چون", "چه", "پس", "پیش", "بین", "سپس"
}

class SearchEngine:
    def __init__(self):
        self.index = {}
        self.graph = {}
        self.is_loaded = False
        self.load_data()

    def normalize(self, text):
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r'[^\w\s]', ' ', text)
        return re.sub(r'\s+', ' ', text).strip()

    def tokenize(self, text):
        tokens = self.normalize(text).split()
        return [t for t in tokens if t not in PERSIAN_STOPWORDS and len(t) > 1]

    def load_data(self):
        if not os.path.exists(INDEX_FILE):
            print(f"Index file not found at: {INDEX_FILE}")
            print("Please run index_builder.py first.")
            return

        print("Loading Index & Graph...")
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                self.index = json.load(f)
            
            if os.path.exists(GRAPH_FILE):
                with open(GRAPH_FILE, "r", encoding="utf-8") as f:
                    self.graph = json.load(f)
            else:
                self.graph = {"pagerank": {}}
                print("Warning: Graph file not found. Ranking will rely only on content.")
            
            self.is_loaded = True
            doc_count = self.index.get('stats', {}).get('total_docs', 0)
            print(f"Engine Ready. Loaded {doc_count} documents.")
            
        except Exception as e:
            print(f"Error loading data: {e}")

    def search(self, query, top_k=10, alpha=0.85):
        if not self.is_loaded: return []

        query_tokens = self.tokenize(query)
        if not query_tokens: return []

        scores = {}
        
        vocab = self.index.get("vocab", {})
        idf = self.index.get("idf", {})
        doc_norms = self.index.get("doc_norms", {})

        q_vec = {}
        for t in query_tokens:
            q_vec[t] = q_vec.get(t, 0) + 1
        
        q_norm = 0
        for t in q_vec:
            if t in idf:
                w = (1 + math.log(q_vec[t])) * idf[t]
                q_vec[t] = w
                q_norm += w**2
            else:
                q_vec[t] = 0
        q_norm = math.sqrt(q_norm)

        if q_norm == 0: return []

        for t, q_weight in q_vec.items():
            if q_weight == 0 or t not in vocab: continue
            
            postings = vocab[t]
            for p in postings:
                doc_id = p['doc_id']
                doc_tfidf = p['tfidf']
                
                scores[doc_id] = scores.get(doc_id, 0) + (q_weight * doc_tfidf)

        for did in scores:
            if did in doc_norms and doc_norms[did] > 0:
                scores[did] /= (doc_norms[did] * q_norm)

        pagerank = self.graph.get("pagerank", {})
        final_scores = []
        
        doc_map = self.index.get("doc_map", {})

        for did, content_score in scores.items():
            pr_score = pagerank.get(did, 0)
            
            hybrid_score = (alpha * content_score) + ((1 - alpha) * pr_score * 20)
            
            doc_info = doc_map.get(did, {})
            if isinstance(doc_info, str):
                url = doc_info
                title = "No Title"
                date = "Unknown"
            else:
                url = doc_info.get('url', 'N/A')
                title = doc_info.get('title', 'N/A')
                date = doc_info.get('date', 'N/A')

            final_scores.append({
                "id": did,
                "title": title,
                "url": url,
                "date": date,
                "score": hybrid_score,
                "content_score": content_score,
                "pr_score": pr_score
            })

        final_scores.sort(key=lambda x: x["score"], reverse=True)
        return final_scores[:top_k]

def run_interactive():
    engine = SearchEngine()
    if not engine.is_loaded: return

    print("\n--- Search Engine (Interactive) ---")
    print("Type 'exit' to quit.\n")

    while True:
        query = input("Search > ").strip()
        if query.lower() in ('exit', 'quit'): break
        if not query: continue

        results = engine.search(query)
        
        print(f"\nResults for: {query}")
        if not results:
            print("No matches found.")
        else:
            for i, res in enumerate(results, 1):
                print(f"{i}. {res['title']}")
                print(f"   Date: {res['date']} | URL: {res['url']}")
                print(f"   Score: {res['score']:.4f} (Content: {res['content_score']:.4f} | PR: {res['pr_score']:.6f})")
                print("-" * 40)

if __name__ == "__main__":
    run_interactive()
