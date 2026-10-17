"""
Polite Scraper Pipeline - Stage 4: Clean, Validate, and Store Records
Target: https://books.toscrape.com
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from pydantic import BaseModel, HttpUrl, Field, ValidationError
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
OUTPUT_DIR = Path("output")
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/shahbaazcodes/polite-scraper-pipeline)"
REQUEST_TIMEOUT = 10.0  # seconds
POLITE_DELAY_SECONDS = 0.5  # 500ms delay between live network requests
MAX_CATALOGUE_PAGES = 3


# --- Pydantic v2 Validation Schema ---
class BookRecord(BaseModel):
    """Normalized and strictly validated schema for a book entity."""
    title: str = Field(..., min_length=1, description="Full title of the book")
    product_url: HttpUrl = Field(..., description="Canonical absolute URL of the product page")
    price_text: str = Field(..., description="Raw price string extracted from HTML")
    price_gbp: float = Field(..., ge=0.0, description="Parsed numerical price in GBP")
    availability_text: str = Field(..., description="Raw stock availability text")
    rating_text: str = Field(..., description="Textual rating representation")
    description: Optional[str] = Field(None, description="Book description if present")
    source_page: HttpUrl = Field(..., description="Catalogue URL where link was discovered")
    fetched_at: str = Field(..., description="ISO 8601 UTC timestamp of fetch")


def fetch_and_cache_page(url: str, cache_filename: str) -> str:
    """Politely fetches an HTML page with a 500ms delay for uncached requests."""
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


def normalize_price(price_text: str) -> float:
    """Extracts floating point number from messy price string like 'Â£51.77'."""
    match = re.search(r"(\d+\.\d+)", price_text)
    if match:
        return float(match.group(1))
    raise ValueError(f"Could not parse numeric price from: '{price_text}'")


def extract_raw_book_detail(html_content: str, product_url: str, source_page: str) -> Dict[str, Any]:
    """Parses product details from raw HTML."""
    soup = BeautifulSoup(html_content, "html.parser")
    main_pod = soup.select_one("div.product_main")

    title = main_pod.select_one("h1").text.strip() if main_pod and main_pod.select_one("h1") else ""

    price_tag = main_pod.select_one("p.price_color") if main_pod else None
    price_text = price_tag.text.strip() if price_tag else ""

    availability_tag = main_pod.select_one("p.instock.availability") if main_pod else None
    availability_text = " ".join(availability_tag.text.split()) if availability_tag else ""

    rating_text = ""
    rating_tag = main_pod.select_one("p.star-rating") if main_pod else None
    if rating_tag:
        classes = rating_tag.get("class", [])
        rating_classes = [c for c in classes if c != "star-rating"]
        if rating_classes:
            rating_text = rating_classes[0]

    description: Optional[str] = None
    desc_header = soup.find("div", id="product_description")
    if desc_header:
        desc_paragraph = desc_header.find_next_sibling("p")
        if desc_paragraph:
            description = desc_paragraph.text.strip()

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


def process_and_store_records():
    """Fetches, normalizes, validates against schema, and writes clean records to output/books.json."""
    entries = discover_book_entries(START_URL, max_pages=MAX_CATALOGUE_PAGES)
    validated_records: List[Dict[str, Any]] = []
    error_records: List[Dict[str, Any]] = []

    logger.info(f"Normalizing and validating {len(entries)} records...")

    for idx, entry in enumerate(entries, start=1):
        product_url = entry["product_url"]
        source_page = entry["source_page"]
        
        url_slug = re.sub(r"[^a-zA-Z0-9-]", "_", product_url.split("/")[-2])
        cache_filename = f"detail-{idx:02d}-{url_slug}.html"

        html_content = fetch_and_cache_page(product_url, cache_filename)
        raw_record = extract_raw_book_detail(html_content, product_url, source_page)

        try:
            # 1. Normalize price text to float numeric GBP
            price_gbp = normalize_price(raw_record["price_text"])
            
            # Combine raw record with normalized field
            full_record = {**raw_record, "price_gbp": price_gbp}

            # 2. Validate against Pydantic schema
            validated_model = BookRecord(**full_record)
            
            # Dump back to dictionary with serializable types (HttpUrl -> str)
            validated_records.append(validated_model.model_dump(mode="json"))

        except (ValueError, ValidationError) as err:
            logger.warning(f"Schema validation failed for {product_url}: {err}")
            error_records.append({
                "product_url": product_url,
                "error": str(err),
                "raw_record": raw_record
            })

    # Save outputs idempotently
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    books_file = OUTPUT_DIR / "books.json"
    errors_file = OUTPUT_DIR / "errors.json"

    books_file.write_text(json.dumps(validated_records, indent=2), encoding="utf-8")
    errors_file.write_text(json.dumps(error_records, indent=2), encoding="utf-8")

    print("\n--- STAGE 4 CHECKPOINT SUMMARY ---")
    print(f"validated_records = {len(validated_records)}")
    print(f"error_records = {len(error_records)}")
    print(f"Output written to: {books_file}")
    if validated_records:
        sample = validated_records[0]
        print(f"Sample price_gbp: {sample['price_gbp']} (type: {type(sample['price_gbp']).__name__})")
        print(f"Sample URL: {sample['product_url']}")
    print("-----------------------------------\n")


def main():
    logger.info("Initializing Stage 4 Execution...")
    process_and_store_records()


if __name__ == "__main__":
    main()