"""
Polite Scraper Pipeline - Stage 5: Fault Tolerance, Single-Retry Logic, and Run Reporting
Target: https://books.toscrape.com
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
import time

from pydantic import BaseModel, HttpUrl, Field, ValidationError
import requests
from bs4 import BeautifulSoup

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
POLITE_DELAY_SECONDS = 0.5  # 500ms rate-limit delay
MAX_CATALOGUE_PAGES = 3


class BookRecord(BaseModel):
    """Normalized and strictly validated schema for a book entity."""
    title: str = Field(..., min_length=1, description="Full title of the book")
    product_url: HttpUrl = Field(..., description="Canonical absolute URL of the product page")
    price_text: str = Field(..., description="Raw price string extracted from HTML")
    price_gbp: float = Field(..., ge=0.0, description="Parsed numerical price in GBP")
    availability_text: str = Field(..., description="Raw stock availability text")
    rating_text: str = Field(..., description="Textual rating representation")
    description: str | None = Field(None, description="Book description if present")
    source_page: HttpUrl = Field(..., description="Catalogue URL where link was discovered")
    fetched_at: str = Field(..., description="ISO 8601 UTC timestamp of fetch")


def fetch_and_cache_page(url: str, cache_filename: str, metrics: dict) -> str | None:
    """
    Politely fetches an HTML page with single-retry logic for transient errors (5xx/timeouts),
    skipping non-retriable client errors (404/403).
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        logger.info(f"CACHE HIT | Reading {cache_path.name}")
        metrics["cache_hits"] += 1
        return cache_path.read_text(encoding="utf-8")

    headers = {"User-Agent": USER_AGENT}
    max_attempts = 2

    for attempt in range(1, max_attempts + 1):
        time.sleep(POLITE_DELAY_SECONDS)
        logger.info(f"FETCH (Attempt {attempt}/{max_attempts}) | Requesting: {url}")

        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            
            # 404/403 are client errors; do not retry
            if response.status_code in (404, 403):
                logger.error(f"Client error {response.status_code} for {url}. Skipping.")
                metrics["failed_pages"] += 1
                return None

            if response.status_code != 200:
                logger.warning(f"Server error {response.status_code} for {url}.")
                if attempt < max_attempts:
                    time.sleep(1.0)
                    continue
                metrics["failed_pages"] += 1
                return None

            html_content = response.text
            cache_path.write_text(html_content, encoding="utf-8")
            metrics["pages_fetched"] += 1
            return html_content

        except requests.RequestException as exc:
            logger.warning(f"Network error on attempt {attempt} for {url}: {exc}")
            if attempt < max_attempts:
                time.sleep(1.0)
                continue
            metrics["failed_pages"] += 1
            return None

    return None


def extract_book_urls(html_content: str, current_page_url: str) -> list[str]:
    """Extracts product page links from a catalogue page and resolves absolute URLs."""
    soup = BeautifulSoup(html_content, "html.parser")
    book_urls: list[str] = []

    articles = soup.select("article.product_pod")
    for article in articles:
        link_tag = article.select_one("h3 > a")
        if link_tag and "href" in link_tag.attrs:
            from urllib.parse import urljoin
            relative_href = str(link_tag["href"])
            absolute_url = urljoin(current_page_url, relative_href)
            book_urls.append(absolute_url)

    return book_urls


def extract_next_page_url(html_content: str, current_page_url: str) -> str | None:
    """Finds the pagination 'next' link from the catalogue page if present."""
    soup = BeautifulSoup(html_content, "html.parser")
    next_tag = soup.select_one("li.next > a")
    if next_tag and "href" in next_tag.attrs:
        from urllib.parse import urljoin
        return urljoin(current_page_url, str(next_tag["href"]))
    return None


def discover_book_entries(start_url: str, metrics: dict, max_pages: int = MAX_CATALOGUE_PAGES) -> list[dict[str, str]]:
    """Crawls catalogue pages sequentially, storing product URLs with source page provenance."""
    discovered_entries: list[dict[str, str]] = []
    current_url: str | None = start_url
    page_count = 0

    while current_url and page_count < max_pages:
        page_count += 1
        cache_filename = f"catalogue-page-{page_count}.html"
        
        html_content = fetch_and_cache_page(current_url, cache_filename, metrics)
        if not html_content:
            logger.error(f"Failed to fetch catalogue page {page_count}. Aborting crawl loop.")
            break

        page_book_urls = extract_book_urls(html_content, current_url)
        for book_url in page_book_urls:
            discovered_entries.append({
                "product_url": book_url,
                "source_page": current_url
            })

        current_url = extract_next_page_url(html_content, current_url)

    # Deduplicate while preserving order
    unique_entries = []
    seen_urls = set()
    for entry in discovered_entries:
        if entry["product_url"] not in seen_urls:
            seen_urls.add(entry["product_url"])
            unique_entries.append(entry)

    # Inject one synthetic broken URL to prove fault tolerance without hammering the target site
    test_broken_entry = {
        "product_url": "https://books.toscrape.com/catalogue/non_existent_broken_book_9999/index.html",
        "source_page": start_url
    }
    unique_entries.append(test_broken_entry)
    logger.info("Injected 1 intentional broken URL into discovery queue for Stage 5 resilience verification.")

    return unique_entries


def normalize_price(price_text: str) -> float:
    """Extracts floating point number from messy price string."""
    match = re.search(r"(\d+\.\d+)", price_text)
    if match:
        return float(match.group(1))
    raise ValueError(f"Could not parse numeric price from: '{price_text}'")


def extract_raw_book_detail(html_content: str, product_url: str, source_page: str) -> dict[str, str | None]:
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

    description: str | None = None
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


def run_pipeline():
    """Runs the full pipeline, isolating bad pages and writing output/run-report.json[cite: 8]."""
    start_time_utc = datetime.now(timezone.utc)
    start_timestamp = start_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    metrics = {
        "start_time": start_timestamp,
        "duration_seconds": 0.0,
        "pages_fetched": 0,
        "cache_hits": 0,
        "valid_records": 0,
        "invalid_records": 0,
        "failed_pages": 0,
    }

    entries = discover_book_entries(START_URL, metrics, max_pages=MAX_CATALOGUE_PAGES)
    validated_records = []
    error_records = []

    logger.info(f"Processing detail extraction for {len(entries)} queued entries...")

    for idx, entry in enumerate(entries, start=1):
        product_url = entry["product_url"]
        source_page = entry["source_page"]

        url_slug = re.sub(r"[^a-zA-Z0-9-]", "_", product_url.split("/")[-2])
        cache_filename = f"detail-{idx:02d}-{url_slug}.html"

        html_content = fetch_and_cache_page(product_url, cache_filename, metrics)
        
        # If fetch failed (e.g. 404 broken page), log and skip without taking down the run[cite: 8]
        if not html_content:
            logger.warning(f"Skipping record extraction for unresolvable URL: {product_url}")
            continue

        try:
            raw_record = extract_raw_book_detail(html_content, product_url, source_page)
            price_gbp = normalize_price(raw_record["price_text"])
            full_record = {**raw_record, "price_gbp": price_gbp}

            validated_model = BookRecord(**full_record)
            validated_records.append(validated_model.model_dump(mode="json"))
            metrics["valid_records"] += 1

        except (ValueError, ValidationError) as err:
            logger.warning(f"Validation failed for {product_url}: {err}")
            error_records.append({
                "product_url": product_url,
                "error": str(err)
            })
            metrics["invalid_records"] += 1

    # End execution timer
    end_time_utc = datetime.now(timezone.utc)
    metrics["duration_seconds"] = round((end_time_utc - start_time_utc).total_seconds(), 2)

    # Save outputs idempotently[cite: 8]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    books_file = OUTPUT_DIR / "books.json"
    errors_file = OUTPUT_DIR / "errors.json"
    report_file = OUTPUT_DIR / "run-report.json"

    books_file.write_text(json.dumps(validated_records, indent=2), encoding="utf-8")
    errors_file.write_text(json.dumps(error_records, indent=2), encoding="utf-8")
    report_file.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("\n--- STAGE 5 CHECKPOINT RUN REPORT ---")
    print(json.dumps(metrics, indent=2))
    print("-------------------------------------\n")


def main():
    logger.info("Initializing Stage 5 Execution...")
    run_pipeline()


if __name__ == "__main__":
    main()