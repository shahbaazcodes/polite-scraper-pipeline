"""
AI-Generated Scraper Version (Quarantine Mode for Stage 7 Audit)
Target: https://books.toscrape.com
"""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import requests

BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"


def ai_scrape():
    # Flaw 1: Hardcoded catalog page loop instead of reading pagination links dynamically
    urls = [
        "https://books.toscrape.com/catalogue/page-1.html",
        "https://books.toscrape.com/catalogue/page-2.html",
        "https://books.toscrape.com/catalogue/page-3.html",
    ]

    book_links = []
    # Flaw 2: Missing custom User-Agent, timeout configuration, and caching logic
    for page in urls:
        res = requests.get(page)
        soup = BeautifulSoup(res.text, "html.parser")
        for a in soup.find_all("a"):
            if "title" in a.attrs:
                # Relative link handling using naive string manipulation
                href = a["href"]
                full_url = "https://books.toscrape.com/catalogue/" + href.replace("../", "")
                book_links.append(full_url)

    # Inject one broken page
    book_links.append("https://books.toscrape.com/catalogue/non_existent_broken_book_9999/index.html")

    results = []
    for link in book_links:
        try:
            # Flaw 3: Direct HTTP requests without rate limiting (sleep) or error retries
            r = requests.get(link)
            if r.status_code != 200:
                # Flaw 4: Unhandled status codes crash or skip quietly without logging provenance
                continue

            b_soup = BeautifulSoup(r.text, "html.parser")
            title = b_soup.find("h1").text
            price_str = b_soup.find("p", class_="price_color").text

            # Flaw 5: Naive slicing assumption for price instead of regex normalization
            price_gbp = float(price_str.replace("£", "").replace("Â", ""))

            # Flaw 6: Missing Pydantic schema validation or type guarantees
            results.append({
                "title": title,
                "product_url": link,
                "price_gbp": price_gbp
            })
        except Exception as e:
            print(f"Error scraping {link}: {e}")

    with open("ai_books.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    ai_scrape()