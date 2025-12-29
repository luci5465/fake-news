import json
import os
import math
import numpy as np
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("PROJECT_DATA_DIR", os.path.join(BASE_DIR, "data"))
GRAPH_FILE = os.path.join(DATA_DIR, "news_graph.json")

PERSIAN_STOPWORDS = [
    "از", "به", "در", "که", "و", "را", "این", "آن", "برای", "با", "است", "شد", "می", "ها", "های", "بر",
    "تا", "یک", "بود", "نیز", "کند", "شود", "کرده", "شده", "باید", "گفت", "دارد", "وی", "اما", "اگر"
]

class WebGraph:
    def __init__(self):
        self.nodes = set()
        self.edges = defaultdict(list)
        self.incoming = defaultdict(list)
        self.doc_map = {}

    def build_from_docs(self, docs, sim_threshold=0.3, max_sim_edges=5):
        print("Checking explicit links...")
        
        url_to_id = {d['url']: d['id'] for d in docs if 'url' in d}
        
        for doc in docs:
            src_id = doc['id']
            self.nodes.add(src_id)
            self.doc_map[src_id] = doc.get('url', '')
            
            for link in doc.get('outgoing_links', []):
                link = link.rstrip('/')
                if link in url_to_id:
                    dst_id = url_to_id[link]
                    if src_id != dst_id:
                        self.edges[src_id].append(dst_id)
                        self.incoming[dst_id].append(src_id)

        print("Computing content similarity edges...")
        self._add_similarity_edges(docs, sim_threshold, max_sim_edges)

    def _add_similarity_edges(self, docs, threshold, k):
        valid_docs = [d for d in docs if len(d.get('content', '')) > 50]
        ids = [d['id'] for d in valid_docs]
        texts = [d['title'] + " " + d['content'] for d in valid_docs]

        if not texts: return

        vectorizer = TfidfVectorizer(max_features=1000, stop_words=PERSIAN_STOPWORDS)
        tfidf_matrix = vectorizer.fit_transform(texts)
        
        sim_matrix = cosine_similarity(tfidf_matrix)

        count = 0
        for i in range(len(ids)):
            scores = sim_matrix[i]
            scores[i] = 0 
            top_indices = np.argsort(scores)[::-1][:k]
            
            for idx in top_indices:
                if scores[idx] > threshold:
                    src = ids[i]
                    dst = ids[idx]
                    
                    if dst not in self.edges[src]:
                        self.edges[src].append(dst)
                        self.incoming[dst].append(src)
                        count += 1
        print(f"Added {count} similarity edges.")

    def pagerank(self, damping=0.85, max_iter=100, tol=1e-6):
        N = len(self.nodes)
        if N == 0: return {}
        
        pr = {node: 1.0/N for node in self.nodes}
        
        for _ in range(max_iter):
            new_pr = {}
            diff = 0
            
            for node in self.nodes:
                incoming_score = 0
                for inc_node in self.incoming[node]:
                    out_count = len(self.edges[inc_node])
                    if out_count > 0:
                        incoming_score += pr[inc_node] / out_count
                
                new_val = (1 - damping) / N + damping * incoming_score
                new_pr[node] = new_val
                diff += abs(new_val - pr[node])
            
            pr = new_pr
            if diff < tol:
                break
                
        return pr

    def hits(self, max_iter=50, tol=1e-6):
        hub = {n: 1.0 for n in self.nodes}
        auth = {n: 1.0 for n in self.nodes}
        
        for _ in range(max_iter):
            old_auth = auth.copy()
            
            for n in self.nodes:
                score = 0
                for inc in self.incoming[n]:
                    score += hub[inc]
                auth[n] = score
            
            norm = math.sqrt(sum(v*v for v in auth.values()))
            for n in auth: auth[n] /= (norm + 1e-9)

            for n in self.nodes:
                score = 0
                for out in self.edges[n]:
                    score += auth[out]
                hub[n] = score
                
            norm = math.sqrt(sum(v*v for v in hub.values()))
            for n in hub: hub[n] /= (norm + 1e-9)

            diff = sum(abs(auth[n] - old_auth[n]) for n in self.nodes)
            if diff < tol:
                break
                
        return auth, hub

def run_graph_builder():
    print("\n--- Web Graph Builder ---")
    
    if not os.path.exists(DATA_DIR):
        print("Data directory not found.")
        return

    clean_files = [f for f in os.listdir(DATA_DIR) if f.endswith("_clean.json")]
    if not clean_files:
        print("No cleaned data files found.")
        return

    docs = []
    for f in clean_files:
        with open(os.path.join(DATA_DIR, f), "r", encoding="utf-8") as file:
            docs.extend(json.load(file))

    print(f"Building graph from {len(docs)} documents...")
    
    graph = WebGraph()
    graph.build_from_docs(docs)

    print("Calculating PageRank...")
    pr_scores = graph.pagerank()

    print("Calculating HITS (Hubs & Authorities)...")
    auth_scores, hub_scores = graph.hits()

    output = {
        "nodes": list(graph.nodes),
        "edges_count": sum(len(v) for v in graph.edges.values()),
        "pagerank": pr_scores,
        "authority": auth_scores,
        "hub": hub_scores,
        "url_map": graph.doc_map
    }

    try:
        with open(GRAPH_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"Graph built and saved to: {GRAPH_FILE}")
    except Exception as e:
        print(f"Failed to save graph: {e}")

if __name__ == "__main__":
    run_graph_builder()
