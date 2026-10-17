# Polite Scraper Pipeline (Books to Scrape)

A production-grade, polite web scraping and data normalization pipeline built with **Python 3.10+**, **Requests**, **BeautifulSoup4**, and **Pydantic v2**[cite: 5].

---

## 🎯 Stage 0: Target Classification

* **Target Site:** `https://books.toscrape.com/`
* **Target Purpose:** Public practice sandbox built specifically for web scraping experimentation.
* **Collection Scope:** First 3 catalogue pages (60 book items total)[cite: 4, 6].
* **Data Extracted:** Book title, product URL, price text, price GBP (numeric), availability, rating, description, source page URL, and fetch timestamp[cite: 7, 8].
* **Robots.txt Status:** `no robots file found` (HTTP 404 response upon requesting `https://books.toscrape.com/robots.txt`)[cite: 6].
* **Appropriateness:** Scraping is conducted against an explicit public testing sandbox with rate limiting (500ms delay), custom User-Agent identification, and client-side HTML caching[cite: 6, 10].

> **Compliance Statement:** I will not reuse this code on another site without checking its rules and terms first[cite: 6].

---

## 🛠️ Setup & Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt