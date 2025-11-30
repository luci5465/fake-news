import requests
from bs4 import BeautifulSoup
import json
import time
import random
from urllib.parse import urljoin, urlparse
import os


class IsnaCrawler:
    def __init__(
        self,
        base_url="https://www.isna.ir/",
        max_articles=150,
        request_timeout=10,
        min_content_chars=500,
        delay_min=0.5,
        delay_max=1.5,
    ):
        self.base_url = base_url.rstrip("/")
        self.domain = urlparse(self.base_url).netloc
        self.max_articles = max_articles
        self.request_timeout = request_timeout
        self.min_content_chars = min_content_chars
        self.delay_min = delay_min
        self.delay_max = delay_max

        self.visited = set()
        self.articles = []
        self.article_ids = {}  # url -> int id

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            }
        )

    def _sleep(self):
        time.sleep(random.uniform(self.delay_min, self.delay_max))

    def fetch(self, url):
        try:
            resp = self.session.get(url, timeout=self.request_timeout)
            if resp.status_code == 200 and "text/html" in resp.headers.get("Content-Type", ""):
                return resp.text
            return None
        except Exception as e:
            print(f"   ! Fetch error for {url}: {e}")
            return None

    def _is_same_domain(self, url):
        return urlparse(url).netloc == self.domain

    def _normalize_url(self, url):
        parsed = urlparse(url)
        clean = parsed._replace(fragment="").geturl()
        if clean.endswith("/"):
            clean = clean[:-1]
        return clean

    def _is_article_page(self, url, soup):
        """
        ساده ولی مؤثر:
        - آدرس شامل /news/ باشد
        - عنوان و متن خبر وجود داشته باشد
        """
        if "/news/" not in url:
            return False

        title_tag = soup.find("h1", class_="first-title")
        text_tag = soup.find("div", class_="item-text")
        if not title_tag or not text_tag:
            return False

        content = text_tag.get_text(strip=True)
        if len(content) < self.min_content_chars:
            return False

        return True

    def parse_article(self, url, soup):
        title_tag = soup.find("h1", class_="first-title")
        text_tag = soup.find("div", class_="item-text")
        date_tag = soup.find("span", class_="date-publish")

        title = title_tag.get_text(strip=True) if title_tag else ""
        content = text_tag.get_text(separator="\n", strip=True) if text_tag else ""
        publish_date = date_tag.get_text(strip=True) if date_tag else None

        outgoing = []
        for a in soup.find_all("a", href=True):
            full = urljoin(url, a["href"])
            full = self._normalize_url(full)
            if self._is_same_domain(full):
                outgoing.append(full)

        if url not in self.article_ids:
            self.article_ids[url] = len(self.article_ids) + 1

        return {
            "id": self.article_ids[url],
            "url": url,
            "title": title,
            "content": content,
            "publish_date": publish_date,
            "outgoing_links": outgoing,
            "incoming_links": [],  # بعداً در graph_builder پر می‌کنیم
            "language": "fa",
            "source": "isna",
            "label": "real",
        }

    def crawl(self, start_url=None):
        if start_url is None:
            start_url = self.base_url

        start_url = self._normalize_url(start_url)
        queue = [start_url]
        pages_seen = 0

        while queue and len(self.articles) < self.max_articles:
            url = queue.pop(0)
            url = self._normalize_url(url)

            if url in self.visited:
                continue
            self.visited.add(url)

            print(f"[{len(self.articles)}/{self.max_articles}] Fetching → {url}")
            html = self.fetch(url)
            if not html:
                continue

            pages_seen += 1
            soup = BeautifulSoup(html, "html.parser")

            if self._is_article_page(url, soup):
                article = self.parse_article(url, soup)
                self.articles.append(article)
                print(f"   ✓ Saved article: {article['title'][:60]}")
            else:
                print("   ⚠ Not an article (or too short)")

            # اضافه‌کردن لینک‌های جدید به صف
            for a in soup.find_all("a", href=True):
                full = urljoin(url, a["href"])
                full = self._normalize_url(full)
                if not self._is_same_domain(full):
                    continue
                if full not in self.visited:
                    queue.append(full)

            self._sleep()

        print(f"\n✓ Finished. Saved {len(self.articles)} articles. "
              f"(visited {pages_seen} HTML pages total)")
        return self.articles

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.articles, f, ensure_ascii=False, indent=2)
        print(f"✓ Saved {len(self.articles)} articles to {path}")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(__file__))
    save_path = os.path.join(base_dir, "data", "isna_sample.json")

    crawler = IsnaCrawler(
        base_url="https://www.isna.ir/",
        max_articles=150,
        min_content_chars=500,
    )
    articles = crawler.crawl()
    crawler.save(save_path)
