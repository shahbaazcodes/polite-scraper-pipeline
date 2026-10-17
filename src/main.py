"""
Polite Scraper Pipeline - Stage 2: Discover 3 Catalogue Pages
Target: https://books.toscrape.com
"""

import logging
from pathlib import Path
import time
from typing import List, Optional
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
    Politely fetches an HTML page with a 500ms delay for uncached network requests,
    a custom User-Agent, and strict timeout checking[cite: 6, 7].
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / cache_filename

    # Check local cache first
    if cache_path.exists():
        logger.info(f"CACHE HIT | Reading {cache_path.name}")
        return cache_path.read_text(encoding="utf-8")

    # Enforce politeness delay for live network requests
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
    """
    Extracts all product page links from a catalogue HTML page and resolves
    relative hrefs into absolute URLs using urljoin.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    book_urls: List[str] = []

    # Target the product containers explicitly
    articles = soup.select("article.product_pod")
    for article in articles:
        link_tag = article.select_one("h3 > a")
        if link_tag and "href" in link_tag.attrs:
            relative_href = str(link_tag["href"])
            # Resolve relative link using urljoin (never string concatenation)
            absolute_url = urljoin(current_page_url, relative_href)
            book_urls.append(absolute_url)

    return book_urls


def extract_next_page_url(html_content: str, current_page_url: str) -> Optional[str]:
    """
    Finds the pagination 'next' link from the catalogue page if present.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    next_tag = soup.select_one("li.next > a")
    if next_tag and "href" in next_tag.attrs:
        return urljoin(current_page_url, str(next_tag["href"]))
    return None


def discover_book_urls(start_url: str, max_pages: int = MAX_CATALOGUE_PAGES) -> List[str]:
    """
    Crawls catalogue pages sequentially up to max_pages, discovering all book links[cite: 7].
    """
    discovered_urls: List[str] = []
    current_url: Optional[str] = start_url
    page_count = 0

    while current_url and page_count < max_pages:
        page_count += 1
        cache_filename = f"catalogue-page-{page_count}.html"
        
        logger.info(f"Processing Catalogue Page {page_count}/{max_pages}: {current_url}")
        html_content = fetch_and_cache_page(current_url, cache_filename)
        
        page_book_urls = extract_book_urls(html_content, current_url)
        discovered_urls.extend(page_book_urls)
        logger.info(f"Extracted {len(page_book_urls)} book links from page {page_count}")

        # Follow pagination link dynamically[cite: 7]
        current_url = extract_next_page_url(html_content, current_url)

    # Deduplicate while preserving order[cite: 7]
    unique_urls = list(dict.fromkeys(discovered_urls))

    print("\n--- STAGE 2 CHECKPOINT SUMMARY ---")
    print(f"catalogue_pages = {page_count}")
    print(f"discovered = {len(discovered_urls)}")
    print(f"unique_urls = {len(unique_urls)}")
    print("-----------------------------------\n")

    return unique_urls


def main():
    logger.info("Initializing Stage 2 Execution...")
    discover_book_urls(START_URL, max_pages=MAX_CATALOGUE_PAGES)


if __name__ == "__main__":
    main()