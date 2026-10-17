"""
Polite Scraper Pipeline - Stage 1: Fetch and Cache HTML
Target: https://books.toscrape.com
"""

import logging
from pathlib import Path
import requests

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("PoliteScraper")

# Pipeline Configuration
BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_DIR = Path("cache")
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/shahbaazcodes/polite-scraper-pipeline)"
REQUEST_TIMEOUT = 10.0  # seconds


def fetch_and_cache_page(url: str, cache_filename: str) -> str:
    """
    Politely fetches an HTML page with timeout and custom User-Agent,
    caching the result locally to prevent redundant server traffic.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / cache_filename

    # Check local cache first
    if cache_path.exists():
        logger.info(f"CACHE HIT | Reading from {cache_path}")
        html_content = cache_path.read_text(encoding="utf-8")
        size_kb = len(html_content.encode("utf-8")) / 1024
        logger.info(f"Page size: {size_kb:.2f} KB (Cached)")
        return html_content

    # Cache miss - issue polite network request
    logger.info(f"FETCH | Requesting: {url}")
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        # Verify HTTP status code before processing
        if response.status_code != 200:
            logger.error(f"Fetch failed with status code: {response.status_code}")
            response.raise_for_status()

        html_content = response.text
        
        # Save raw HTML to cache
        cache_path.write_text(html_content, encoding="utf-8")
        size_kb = len(response.content) / 1024
        logger.info(f"Successfully fetched and cached {cache_path.name} | Size: {size_kb:.2f} KB")
        return html_content

    except requests.RequestException as exc:
        logger.error(f"HTTP request error: {exc}")
        raise


def main():
    logger.info("Initializing Stage 1 Execution...")
    fetch_and_cache_page(BASE_URL, "catalogue-page-1.html")


if __name__ == "__main__":
    main()
