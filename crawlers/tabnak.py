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
import concurrent.futures
from threading import Lock

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("PROJECT_DATA_DIR", os.path.join(BASE_DIR, "data"))

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR)
        except OSError:
            pass

def safe_request(url, retries=3, timeout=10):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Connection": "keep-alive"
    }
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=timeout, verify=False)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
    return None

def normalize_date(raw_date):
    if not raw_date: return "unknown"
    months = {"فروردین":"01","اردیبهشت":"02","خرداد":"03","تیر":"04","مرداد":"05","شهریور":"06","مهر":"07","آبان":"08","آذر":"09","دی":"10","بهمن":"11","اسفند":"12"}
    clean_date = re.sub(r'[^\w\s:\-]', '', raw_date).strip()
    parts = clean_date.split()
    day, month, year, time_str = "", "", "", ""
    for part in parts:
        if part in months: month = months[part]
        elif re.match(r"^\d{4}$", part): year = part
        elif re.match(r"^\d{1,2}$", part): day = part.zfill(2)
        elif re.match(r"^\d{1,2}:\d{2}$", part): time_str = part
    if year and month and day:
        final = f"{year}-{month}-{day}"
        if time_str: final += f" {time_str}"
        return final
    return raw_date

def extract_links(soup, base_url):
    links = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        if "tabnak.ir" in href and "/fa/" in href:
            links.add(href)
    return list(links)

def extract_content(soup, url):
    title = ""
    selectors_title = ["h1.title", "h1.news_title", "div.news_title h1", "h1", "meta[property='og:title']"]
    for sel in selectors_title:
        if sel.startswith("meta"):
            tag = soup.select_one(sel)
            if tag: title = tag.get("content", "")
        else:
            tag = soup.select_one(sel)
            if tag: title = tag.get_text(strip=True)
        if title: break
    
    if title:
        title = title.split("|")[0].strip().replace("\u200c", " ")
    else:
        return None 

    content = ""
    selectors_content = ["div.body", "div.news_body", "div.item-text", "div.news-text", "article"]
    content_soup = None
    for sel in selectors_content:
        content_soup = soup.select_one(sel)
        if content_soup:
            paragraphs = content_soup.find_all("p")
            clean_paras = []
            for p in paragraphs:
                txt = p.get_text(" ", strip=True)
                if txt and len(txt) > 20 and not txt.startswith("http"):
                    clean_paras.append(txt)
            content = " ".join(clean_paras)
            if len(content) > 50: break
    
    if not content:
        return None

    date = ""
    selectors_date = ["div.news_path_print span.date_item", "div.news_nav", "span.date_time", "meta[property='article:published_time']"]
    for sel in selectors_date:
        if sel.startswith("meta"):
            tag = soup.select_one(sel)
            if tag: date = tag.get("content", "")
        else:
            tag = soup.select_one(sel)
            if tag: 
                date = tag.get_text(strip=True)
                date = re.sub(r'بازدید\s*\d+', '', date, flags=re.IGNORECASE).strip()
                date = re.sub(r'تعداد\s*بازدید\s*\d+', '', date, flags=re.IGNORECASE).strip()
        if date: break

    return {
        "url": url,
        "title": title,
        "content": content,
        "publish_date": normalize_date(date),
        "source": "tabnak"
    }

def save_data(data, depth):
    if not data: return
    ensure_data_dir()
    filename = f"tabnak_depth{depth}_data.json"
    filepath = os.path.join(DATA_DIR, filename)
    
    current_data = []
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                current_data = json.load(f)
        except:
            current_data = []
    
    existing_urls = {d['url'] for d in current_data}
    new_items = [d for d in data if d['url'] not in existing_urls]

    if not new_items: return

    final_data = current_data + new_items
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        print(f"\nSuccessfully saved {len(new_items)} new articles. Total: {len(final_data)}")
    except Exception as e:
        print(f"Error saving: {e}")

def process_url(url, depth, visited, lock):
    with lock:
        if url in visited: return None, []
        visited.add(url)
    
    html = safe_request(url)
    if not html: return None, []
    
    soup = BeautifulSoup(html, "html.parser")
    found_links = extract_links(soup, url)
    
    is_article = "/news/" in url
    item = None
    if is_article:
        item = extract_content(soup, url)
        if item:
            item["depth"] = depth
            item["outgoing_links"] = found_links
            
    return item, found_links

def run_interactive():
    print("\n--- Tabnak Crawler (Fast) ---")
    try: max_depth = int(input("Enter Crawl Depth [2]: ") or 2)
    except: max_depth = 2
    try: max_pages = int(input("Max Pages [100]: ") or 100)
    except: max_pages = 100
    try: workers = int(input("Threads [10]: ") or 10)
    except: workers = 10

    start_url = "https://www.tabnak.ir/fa/archive"
    visited = set()
    visited_lock = Lock()
    queue = deque([(start_url, 0)])
    results = []
    
    pbar = tqdm(total=max_pages, desc="Crawling", unit="page")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        while queue and len(results) < max_pages:
            batch = []
            while queue and len(batch) < workers * 2:
                batch.append(queue.popleft())
            
            if not batch: break
            
            future_to_url = {
                executor.submit(process_url, url, depth, visited, visited_lock): (url, depth)
                for url, depth in batch
            }
            
            for future in concurrent.futures.as_completed(future_to_url):
                if len(results) >= max_pages: break
                url, depth = future_to_url[future]
                
                try:
                    item, links = future.result()
                    if item:
                        results.append(item)
                        pbar.update(1)
                    
                    if depth < max_depth:
                        with visited_lock:
                            for link in links:
                                if link not in visited:
                                    queue.append((link, depth + 1))
                except:
                    pass

    pbar.close()
    save_data(results, max_depth)

if __name__ == "__main__":
    run_interactive()
