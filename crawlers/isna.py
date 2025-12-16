import requests
from bs4 import BeautifulSoup
from collections import deque
import time
import random
import re
from urllib.parse import urljoin, urlparse
from tqdm import tqdm
import json
import os
import sys
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("PROJECT_DATA_DIR", os.path.join(BASE_DIR, "data"))

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR)
        except OSError:
            pass

def safe_request(url, retries=4, timeout=10):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive"
    }

    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=timeout, verify=False)
            if r.status_code == 200:
                if "text/html" in r.headers.get("Content-Type", "").lower():
                    return r.text
            elif r.status_code == 404:
                return None
        except Exception:
            pass
        
        time.sleep((1.5 ** attempt) + random.uniform(0.5, 1.5))

    return None

def clean_soup(soup):
    for tag in soup(["script", "style", "iframe", "video", "figure", "nav", "footer", "header", "aside", "form", "svg", "button"]):
        tag.decompose()
    return soup

def normalize_url(base_url, href):
    return urljoin(base_url, href)

def same_domain(url):
    parsed = urlparse(url)
    return parsed.netloc.endswith("isna.ir")

def is_news_url(url):
    pattern = r"https?://(www\.)?isna\.ir/(fa/)?(news|service|photo)/\d{6,16}(/[^ \s<>]+)?"
    return re.match(pattern, url) is not None

def extract_headline(soup):
    cands = [
        soup.find("h1"),
        soup.find("meta", attrs={"property": "og:title"}),
        soup.find("meta", attrs={"name": "title"}),
        soup.title
    ]
    for c in cands:
        if not c: 
            continue
        if hasattr(c, "get_text"):
            txt = c.get_text(strip=True)
        else:
            txt = c.get("content", "")
        if txt:
            txt = txt.split("|")[0].split("-")[0].replace("\u200c", " ")
            return txt.strip()
    return ""

def extract_content(soup):
    blocks = soup.find_all("p")
    text = " ".join(p.get_text(" ", strip=True) for p in blocks)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text.split()) > 50 else ""

def normalize_date(raw):
    if not raw: 
        return "unknown"
    
    raw = raw.replace("،", " ").replace("/", " ").strip()
    
    months = {
        "فروردین": "01", "اردیبهشت": "02", "خرداد": "03",
        "تیر": "04", "مرداد": "05", "شهریور": "06",
        "مهر": "07", "آبان": "08", "آذر": "09",
        "دی": "10", "بهمن": "11", "اسفند": "12"
    }
    
    day = month = year = hour = minute = ""
    
    for part in raw.split():
        if part in months:
            month = months[part]
        elif re.fullmatch(r"\d{4}", part):
            year = part
        elif re.fullmatch(r"\d{1,2}", part):
            day = part.zfill(2)
        elif re.fullmatch(r"\d{1,2}:\d{2}", part):
            hour, minute = part.split(":")
            
    if year and month and day:
        result = f"{year}-{month}-{day}"
        if hour and minute:
            result += f" {hour}:{minute}"
        return result
        
    return raw

def extract_publish_date(soup):
    cands = [
        soup.find("time"),
        soup.find("span", class_=re.compile("date")),
        soup.find("meta", attrs={"property": "article:published_time"}),
        soup.find("meta", attrs={"name": "pubdate"}),
        soup.find("meta", attrs={"name": "lastmod"})
    ]
    
    for c in cands:
        if not c:
            continue
        txt = c.get("content") if c.has_attr("content") else c.get_text(strip=True)
        txt = txt.strip()
        if len(txt) > 5:
            return normalize_date(txt)
            
    return "unknown"

def extract_links(soup, base_url):
    links = set()
    for a in soup.find_all("a", href=True):
        full = normalize_url(base_url, a["href"])
        if same_domain(full) and is_news_url(full):
            links.add(full)
    return list(links)

def save_data(data, depth):
    if not data:
        return

    ensure_data_dir()
    path = os.path.join(DATA_DIR, f"isna_depth{depth}_data.json")

    current = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                current = json.load(f)
        except Exception:
            current = []

    existing = {d["url"] for d in current}
    merged = current + [d for d in data if d["url"] not in existing]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    
    print(f"\n[Saved] {len(merged)} articles saved to {path}")

def run_interactive():
    try:
        max_depth = int(input("Enter Crawl Depth [Default 2]: ") or 2)
    except ValueError:
        max_depth = 2

    try:
        max_pages = int(input("Max Pages [Default 100]: ") or 100)
    except ValueError:
        max_pages = 100

    start_url = "https://www.isna.ir/"
    visited = set()
    queue = deque([(start_url, 0)])
    in_queue = {start_url}
    results = []

    pbar = tqdm(total=max_pages, desc="Crawling News")

    while queue and len(results) < max_pages:
        url, depth = queue.popleft()
        
        if url in visited or depth > max_depth:
            continue

        visited.add(url)
        html = safe_request(url)
        if not html:
            continue

        soup = clean_soup(BeautifulSoup(html, "html.parser"))
        found_links = extract_links(soup, url)

        if url == start_url or not is_news_url(url):
            if depth < max_depth:
                for link in found_links:
                    if link not in visited and link not in in_queue:
                        queue.append((link, depth + 1))
                        in_queue.add(link)
            continue

        title = extract_headline(soup)
        content = extract_content(soup)

        if not title or not content:
            continue

        item = {
            "url": url,
            "title": title,
            "content": content,
            "publish_date": extract_publish_date(soup),
            "depth": depth,
            "source": "isna"
        }

        results.append(item)
        pbar.update(1)

        if depth < max_depth:
            for link in found_links:
                if link not in visited and link not in in_queue:
                    queue.append((link, depth + 1))
                    in_queue.add(link)

        time.sleep(0.3)

    pbar.close()
    save_data(results, max_depth)

if __name__ == "__main__":
    run_interactive()