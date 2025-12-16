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
        time.sleep(0.3 + random.random())
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

def extract_links(soup, base_url):
    links = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        if "tabnak.ir" in href and "/fa/" in href:
            links.add(href)
    return list(links)

def save_data(data, depth):
    if not data:
        return
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

    if not new_items:
        print("No new unique items to save.")
        return

    final_data = current_data + new_items
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        print(f"\nSuccessfully saved {len(new_items)} new articles. Total: {len(final_data)}")
        print(f"Path: {filepath}")
    except Exception as e:
        print(f"Error saving: {e}")

def run_interactive():
    print("\n--- Tabnak Crawler ---")
    
    try: max_depth = int(input("Enter Crawl Depth (1-10) [Default: 2]: ") or 2)
    except: max_depth = 2

    try: max_pages = int(input("Max Pages to Fetch [Default: 100]: ") or 100)
    except: max_pages = 100

    start_url = "https://www.tabnak.ir/fa/archive"
    
    print(f"\nStarting Crawl...")
    print(f"Target: {start_url}")
    print(f"Depth: {max_depth}")
    print(f"Max Pages: {max_pages}")
    print("-" * 30)

    visited = set()
    queue = deque([(start_url, 0)])
    results = []
    in_queue = set([start_url])
    
    pbar = tqdm(total=max_pages, desc="Crawling News", unit="page")

    while queue and len(results) < max_pages:
        url, depth = queue.popleft()
        
        if depth > max_depth or url in visited:
            continue
            
        visited.add(url)
        
        html = safe_request(url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        found_links = extract_links(soup, url)
        
        is_article = "/news/" in url
        if is_article:
            item = extract_content(soup, url)
            if item:
                item["depth"] = depth
                results.append(item)
                pbar.update(1)

        if depth < max_depth:
            for link in found_links:
                if link not in visited and link not in in_queue:
                    queue.append((link, depth + 1))
                    in_queue.add(link)
        
        time.sleep(0.1)

    pbar.close()
    print(f"\nCrawl Finished. Collected {len(results)} pages.")
    save_data(results, max_depth)

if __name__ == "__main__":
    run_interactive()