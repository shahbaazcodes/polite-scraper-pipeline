"""
Polite Scraper Pipeline - Stage 3: Extract Raw Book Details
Target: https://books.toscrape.com
"""

from datetime import datetime, timezone
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("PoliteScraper")

# Pipeline Configuration
START_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_DIR = Path("cache")
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/shahbaazcodes/polite-scraper-pipeline)"
REQUEST_TIMEOUT = 10.0  # seconds
POLITE_DELAY_SECONDS = 0.5  # 500ms delay between live network requests
MAX_CATALOGUE_PAGES = 3


def fetch_and_cache_page(url: str, cache_filename: str) -> str:
    """
    Politely fetches an HTML page with a 500ms delay for uncached requests,
    a custom User-Agent, and strict timeout checking.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        logger.info(f"CACHE HIT | Reading {cache_path.name}")
        return cache_path.read_text(encoding="utf-8")

    time.sleep(POLITE_DELAY_SECONDS)
    logger.info(f"FETCH | Requesting: {url}")
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            logger.error(f"Fetch failed with status code: {response.status_code}")
            response.raise_for_status()

        html_content = response.text
        cache_path.write_text(html_content, encoding="utf-8")
        return html_content

    except requests.RequestException as exc:
        logger.error(f"HTTP request failed for {url}: {exc}")
        raise


def extract_book_urls(html_content: str, current_page_url: str) -> List[str]:
    """Extracts product page links from a catalogue page and resolves absolute URLs."""
    soup = BeautifulSoup(html_content, "html.parser")
    book_urls: List[str] = []

    articles = soup.select("article.product_pod")
    for article in articles:
        link_tag = article.select_one("h3 > a")
        if link_tag and "href" in link_tag.attrs:
            relative_href = str(link_tag["href"])
            absolute_url = urljoin(current_page_url, relative_href)
            book_urls.append(absolute_url)

    return book_urls


def extract_next_page_url(html_content: str, current_page_url: str) -> Optional[str]:
    """Finds the pagination 'next' link from the catalogue page if present."""
    soup = BeautifulSoup(html_content, "html.parser")
    next_tag = soup.select_one("li.next > a")
    if next_tag and "href" in next_tag.attrs:
        return urljoin(current_page_url, str(next_tag["href"]))
    return None


def discover_book_entries(start_url: str, max_pages: int = MAX_CATALOGUE_PAGES) -> List[Dict[str, str]]:
    """Crawls catalogue pages sequentially, storing product URLs with source page provenance."""
    discovered_entries: List[Dict[str, str]] = []
    current_url: Optional[str] = start_url
    page_count = 0

    while current_url and page_count < max_pages:
        page_count += 1
        cache_filename = f"catalogue-page-{page_count}.html"
        
        logger.info(f"Processing Catalogue Page {page_count}/{max_pages}: {current_url}")
        html_content = fetch_and_cache_page(current_url, cache_filename)
        
        page_book_urls = extract_book_urls(html_content, current_url)
        for book_url in page_book_urls:
            discovered_entries.append({
                "product_url": book_url,
                "source_page": current_url
            })

        current_url = extract_next_page_url(html_content, current_url)

    # Deduplicate by product_url while preserving order
    unique_entries = []
    seen_urls = set()
    for entry in discovered_entries:
        if entry["product_url"] not in seen_urls:
            seen_urls.add(entry["product_url"])
            unique_entries.append(entry)

    return unique_entries


def extract_raw_book_detail(html_content: str, product_url: str, source_page: str) -> Dict[str, Any]:
    """
    Parses product details from raw HTML, targeting specific product containers.
    Returns 8 raw fields including provenance metadata[cite: 7].
    """
    soup = BeautifulSoup(html_content, "html.parser")
    main_pod = soup.select_one("div.product_main")

    # 1. Title
    title = main_pod.select_one("h1").text.strip() if main_pod and main_pod.select_one("h1") else ""

    # 2. Price Text
    price_tag = main_pod.select_one("p.price_color") if main_pod else None
    price_text = price_tag.text.strip() if price_tag else ""

    # 3. Availability Text
    availability_tag = main_pod.select_one("p.instock.availability") if main_pod else None
    availability_text = " ".join(availability_tag.text.split()) if availability_tag else ""

    # 4. Rating Text (e.g. class="star-rating Three")
    rating_text = ""
    rating_tag = main_pod.select_one("p.star-rating") if main_pod else None
    if rating_tag:
        classes = rating_tag.get("class", [])
        rating_classes = [c for c in classes if c != "star-rating"]
        if rating_classes:
            rating_text = rating_classes[0]

    # 5. Description (Optional field - store None if missing, never invent text)[cite: 7]
    description: Optional[str] = None
    desc_header = soup.find("div", id="product_description")
    if desc_header:
        desc_paragraph = desc_header.find_next_sibling("p")
        if desc_paragraph:
            description = desc_paragraph.text.strip()

    # Provenance timestamp[cite: 7]
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }


def extract_all_raw_records() -> List[Dict[str, Any]]:
    """Fetches and extracts raw records for all 60 discovered books[cite: 7]."""
    entries = discover_book_entries(START_URL, max_pages=MAX_CATALOGUE_PAGES)
    raw_records: List[Dict[str, Any]] = []

    logger.info(f"Starting detail page extraction for {len(entries)} books...")

    for idx, entry in enumerate(entries, start=1):
        product_url = entry["product_url"]
        source_page = entry["source_page"]
        
        # Derive a safe cache filename from book URL
        url_slug = re.sub(r"[^a-zA-Z0-9-]", "_", product_url.split("/")[-2])
        cache_filename = f"detail-{idx:02d}-{url_slug}.html"

        html_content = fetch_and_cache_page(product_url, cache_filename)
        raw_record = extract_raw_book_detail(html_content, product_url, source_page)
        raw_records.append(raw_record)

    print("\n--- STAGE 3 CHECKPOINT SUMMARY ---")
    print(f"detail_pages = {len(raw_records)}")
    print("Sample Raw Record (Book #1):")
    import json
    print(json.dumps(raw_records[0], indent=2))
    print("-----------------------------------\n")

    return raw_records


def main():
    logger.info("Initializing Stage 3 Execution...")
    extract_all_raw_records()


if __name__ == "__main__":
    main()