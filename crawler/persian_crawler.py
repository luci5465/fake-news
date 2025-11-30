import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin
import os


class IsnaCrawler:
    def __init__(self, base_url="https://www.isna.ir/", delay=0.8):
        self.base_url = base_url.rstrip("/")
        self.delay = delay
        self.visited = set()
        self.results = []

    def fetch(self, url):
        try:
            r = requests.get(
                url,
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
            )
            if r.status_code == 200:
                return r.text
            return None
        except Exception as e:
            print("   ⚠ Fetch error:", e)
            return None

    def extract_title(self, soup):
        candidates = [
            ("h1", {"class": "first-title"}),
            ("h1", {}),
            ("h2", {}),
        ]
        for tag, attr in candidates:
            t = soup.find(tag, attr)
            if t:
                return t.get_text(strip=True)
        return ""

    def extract_content(self, soup):
        candidates = [
            "item-text",
            "read__content",
            "body",
            "news-body",
            "report-content",
            "article-body",
            "content",
            "text",
        ]
        for c in candidates:
            div = soup.find("div", class_=c)
            if div:
                return div.get_text(" ", strip=True)

        paras = soup.find_all("p")
        text = " ".join(p.get_text(" ", strip=True) for p in paras)
        return text

    def extract_links(self, soup, current_url):
        links = []
        for a in soup.find_all("a", href=True):
            full = urljoin(current_url, a["href"])
            if full.startswith(self.base_url):
                links.append(full)
        return links

    def parse_page(self, url, html):
        soup = BeautifulSoup(html, "html.parser")

        title = self.extract_title(soup)
        content = self.extract_content(soup)
        outgoing = self.extract_links(soup, url)

        date_tag = soup.find("span", class_="date-publish")
        publish_date = date_tag.get_text(strip=True) if date_tag else ""

        return {
            "url": url,
            "title": title,
            "content": content,
            "publish_date": publish_date,
            "outgoing_links": outgoing,
            "incoming_links": [],
            "language": "fa",
            "label": "real",
        }

    def crawl(self, start_url, max_pages=150):
        queue = [start_url]

        while queue and len(self.results) < max_pages:
            url = queue.pop(0)

            if url in self.visited:
                continue
            self.visited.add(url)

            print(f"[{len(self.results)}/{max_pages}] Fetching → {url}")

            html = self.fetch(url)
            if not html:
                print("   ⚠ No HTML")
                continue

            data = self.parse_page(url, html)

            # اینجا فقط برای صفحات خبری واقعی ذخیره می‌کنیم
            if data["content"] and len(data["content"]) > 200 and "/news/" in url:
                print("   ✓ Saved article:", data["title"][:60])
                self.results.append(data)
            else:
                print("   ⚠ Not an article (or too short)")

            for o in data["outgoing_links"]:
                if o not in self.visited:
                    queue.append(o)

            time.sleep(self.delay)

        return self.results


if __name__ == "__main__":
    crawler = IsnaCrawler()
    data = crawler.crawl("https://www.isna.ir/", max_pages=150)

    base_dir = os.path.dirname(os.path.dirname(__file__))
    save_path = os.path.join(base_dir, "data", "isna_sample.json")

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Saved {len(data)} articles to {save_path}")
