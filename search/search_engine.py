import os
import json
import math
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
        self.is_loaded = False
        self.index_data = {}
        self.graph_data = {}
        self.doc_details_map = {}
        self.load_data()

    def normalize_text(self, text):
        if not text: return ""
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r'[^\w\s]', ' ', text)
        return re.sub(r'\s+', ' ', text).strip()

    def tokenize(self, text):
        text = self.normalize_text(text)
        tokens = text.split()
        return [t for t in tokens if t not in PERSIAN_STOPWORDS and len(t) > 1]

    def load_raw_content(self):
        try:
            if not os.path.exists(DATA_DIR): return
            for f in os.listdir(DATA_DIR):
                if f.endswith("_clean.json"):
                    file_source = "نامشخص"
                    if "isna" in f.lower(): file_source = "خبرگزاری ایسنا"
                    elif "tabnak" in f.lower(): file_source = "تابناک"
                    elif "tasnim" in f.lower(): file_source = "خبرگزاری تسنیم"
                    
                    path = os.path.join(DATA_DIR, f)
                    with open(path, "r", encoding="utf-8") as file:
                        docs = json.load(file)
                        for doc in docs:
                            self.doc_details_map[doc['id']] = {
                                'content': doc.get('content', ''),
                                'source': doc.get('source', file_source)
                            }
        except Exception as e:
            print(f"Warning: Could not load raw content: {e}")

    def load_data(self):
        print("Loading Engine Data...")
        try:
            if not os.path.exists(INDEX_FILE):
                print(f"CRITICAL: Index file missing at {INDEX_FILE}")
                return
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                self.index_data = json.load(f)

            if os.path.exists(GRAPH_FILE):
                with open(GRAPH_FILE, "r", encoding="utf-8") as f:
                    self.graph_data = json.load(f)
                print(f"Graph Metrics Loaded. Nodes: {len(self.graph_data.get('nodes', []))}")
            else:
                print("WARNING: Graph file not found. Ranking will be text-only.")

            self.load_raw_content()
            self.is_loaded = True
            print("Engine Ready.")
            
        except Exception as e:
            print(f"Error loading search engine: {e}")

    def search(self, query, top_k=3):
        if not self.is_loaded or not query: return []

        query_tokens = self.tokenize(query)
        if not query_tokens: return []

        query_vec = {}
        for token in query_tokens:
            query_vec[token] = query_vec.get(token, 0) + 1
        
        query_norm = 0
        query_tfidf = {}
        vocab = self.index_data.get('vocab', {})
        idf = self.index_data.get('idf', {})

        for term, count in query_vec.items():
            if term in idf:
                w = (1 + math.log(count)) * idf[term]
                query_tfidf[term] = w
                query_norm += w ** 2
        
        query_norm = math.sqrt(query_norm)
        text_scores = {}
        
        for term, w_q in query_tfidf.items():
            if term in vocab:
                for p in vocab[term]:
                    doc_id = p['doc_id']
                    w_d = p['tfidf']
                    text_scores[doc_id] = text_scores.get(doc_id, 0) + (w_q * w_d)

        doc_norms = self.index_data.get('doc_norms', {})
        final_results = []
        
        ALPHA = 0.7
        BETA = 0.3

        pagerank_scores = self.graph_data.get('pagerank', {})
        
        for doc_id, dot_product in text_scores.items():
            d_norm = doc_norms.get(doc_id, 1)
            
            cosine_sim = 0
            if d_norm > 0 and query_norm > 0:
                cosine_sim = dot_product / (d_norm * query_norm)
            
            pr_score = pagerank_scores.get(doc_id, 0.0) * 50
            
            final_score = (ALPHA * cosine_sim) + (BETA * pr_score)
            
            if final_score > 0.05:
                doc_info = self.index_data['doc_map'].get(doc_id, {}).copy()
                details = self.doc_details_map.get(doc_id, {})
                
                doc_info['id'] = doc_id
                doc_info['score'] = final_score
                doc_info['text_score'] = cosine_sim
                doc_info['graph_score'] = pr_score
                doc_info['content'] = details.get('content', "")
                doc_info['source'] = details.get('source', "نامشخص")
                
                final_results.append(doc_info)

        final_results = sorted(final_results, key=lambda x: x['score'], reverse=True)
        return final_results[:top_k]
