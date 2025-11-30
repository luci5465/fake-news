import json
import os
from collections import defaultdict

class WebGraph:
    def __init__(self):
        self.outgoing = defaultdict(set)
        self.incoming = defaultdict(set)
        self.nodes = set()

    # -------------------------------------------------------
    # Pass 1 — Collect outgoing links
    # -------------------------------------------------------
    def build_outgoing(self, documents):
        for doc in documents:
            url = doc["url"]
            self.nodes.add(url)

            for link in doc["outgoing_links"]:
                self.outgoing[url].add(link)
                self.nodes.add(link)

    # -------------------------------------------------------
    # Pass 2 — Compute incoming links
    # -------------------------------------------------------
    def build_incoming(self):
        for src, links in self.outgoing.items():
            for dst in links:
                self.incoming[dst].add(src)

    # -------------------------------------------------------
    # Compute node degree (in-degree, out-degree)
    # -------------------------------------------------------
    def compute_degree(self):
        degree = {}

        for n in self.nodes:
            in_d = len(self.incoming.get(n, []))
            out_d = len(self.outgoing.get(n, []))
            degree[n] = {"in": in_d, "out": out_d}

        return degree

    # -------------------------------------------------------
    # HITS Algorithm
    # -------------------------------------------------------
    def hits(self, max_iter=30, eps=1e-8):
        auth = {n: 1.0 for n in self.nodes}
        hub =  {n: 1.0 for n in self.nodes}

        for _ in range(max_iter):
            new_auth = {}
            new_hub = {}

            # Authority(n) = sum of hub(i) for i linking to n
            for n in self.nodes:
                new_auth[n] = sum(hub.get(src, 0) for src in self.incoming.get(n, []))

            # Hub(n) = sum of authority(i) for i linked from n
            for n in self.nodes:
                new_hub[n] = sum(new_auth.get(dst, 0) for dst in self.outgoing.get(n, []))

            # Normalization
            norm_a = sum(new_auth.values()) or 1
            norm_h = sum(new_hub.values()) or 1

            for n in self.nodes:
                new_auth[n] /= norm_a
                new_hub[n] /= norm_h

            # Check convergence
            if max(abs(new_auth[n] - auth.get(n, 0)) for n in self.nodes) < eps:
                break

            auth = new_auth
            hub = new_hub

        return auth, hub

    # -------------------------------------------------------
    # Save Graph
    # -------------------------------------------------------
    def save(self, path, degrees, authority, hub):
        data = {
            "nodes": list(self.nodes),
            "outgoing": {k: list(v) for k, v in self.outgoing.items()},
            "incoming": {k: list(v) for k, v in self.incoming.items()},
            "degree": degrees,
            "authority": authority,
            "hub": hub
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(__file__))
    cleaned_path = os.path.join(base, "data", "cleaned", "isna_cleaned.json")
    save_path = os.path.join(base, "data", "isna_graph.json")

    with open(cleaned_path, "r", encoding="utf-8") as f:
        docs = json.load(f)

    g = WebGraph()
    g.build_outgoing(docs)
    g.build_incoming()
    degree = g.compute_degree()
    auth, hub = g.hits()

    g.save(save_path, degree, auth, hub)

    print("✓ WebGraph built & saved at:", save_path)

