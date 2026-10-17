# Polite Scraper Pipeline (Books to Scrape)

A production-grade, fault-tolerant web scraping and ETL ingestion pipeline built with **Python 3.10+**, **Requests**, **BeautifulSoup4**, and **Pydantic v2**[cite: 5]. 

This project collects product metadata across 60 books on a practice sandbox, normalizes messy raw text into typed models, enforces strict schema validation, survives broken pages without crashing, and generates structured execution metrics[cite: 4, 8].

---

## 🎯 Stage 0: Target Classification & Ethics

* **Target Site:** `https://books.toscrape.com/`[cite: 6]
* **Target Purpose:** Public practice sandbox built specifically for web scraping experimentation[cite: 6].
* **Collection Scope:** First 3 catalogue pages (60 unique book items)[cite: 4, 6].
* **Data Extracted:** `title`, `product_url`, `price_text`, `price_gbp` (numeric), `availability_text`, `rating_text`, `description`, `source_page`, and `fetched_at`[cite: 7, 8].
* **Robots.txt Result:** `no robots file found` (HTTP 404 response upon requesting `https://books.toscrape.com/robots.txt`)[cite: 6].
* **Ethics Statement:** Always check target site rules and terms before scraping[cite: 6]. Use official APIs whenever available, never bypass logins, paywalls, or access controls, and collect only the data necessary for the workload.

> **Compliance Statement:** I will not reuse this code on another site without checking its rules and terms first[cite: 6].

---

## 🛠️ Politeness Rules & Pipeline Architecture

1. **User-Agent Identification:** Sends custom header `FlyRankInternship-A9/1.0 (+https://github.com/shahbaazcodes/polite-scraper-pipeline)` on every request[cite: 6].
2. **Rate Limiting:** Enforces a mandatory `500 ms` delay (`time.sleep(0.5)`) prior to outbound HTTP network calls[cite: 7, 8].
3. **Request Timeout:** Enforces a strict `10.0s` timeout to prevent hanging connections[cite: 6].
4. **Local Caching:** Writes HTML pages to `cache/` upon initial fetch[cite: 6]. Subsequent pipeline executions read from disk (`CACHE HIT`), eliminating unnecessary server load[cite: 6].
5. **No-Browser Rationale:** The core catalogue and detail pages are fully server-side rendered HTML[cite: 9]. Raw HTTP requests via `requests` extract all target payload elements directly, making a headless browser (e.g., Playwright or Selenium) unnecessary and computationally wasteful[cite: 9].

---

## 📋 Data Schema (`BookRecord`)

Implemented using **Pydantic v2** in `src/main.py`[cite: 5, 8]:

| Field | Type | Description |
| :--- | :--- | :--- |
| `title` | `str` | Full title of the book (`min_length=1`)[cite: 7, 8] |
| `product_url` | `HttpUrl` | Canonical absolute URL of the product detail page[cite: 7, 8] |
| `price_text` | `str` | Raw string price from HTML (e.g., `"£51.77"`)[cite: 7, 8] |
| `price_gbp` | `float` | Cleaned floating point numeric price in GBP (`ge=0.0`)[cite: 8] |
| `availability_text` | `str` | Raw stock availability string[cite: 7, 8] |
| `rating_text` | `str` | Text representation of book rating (e.g., `"Three"`)[cite: 7, 8] |
| `description` | `Optional[str]` | Detailed description string or `None` if absent[cite: 7, 8] |
| `source_page` | `HttpUrl` | Provenance URL of catalogue page where link was discovered[cite: 7, 8] |
| `fetched_at` | `str` | ISO 8601 UTC timestamp of fetch[cite: 7, 8] |

---

## 🚀 Quick Start & Single-Command Execution

```bash
# 1. Clone repository
git clone [https://github.com/shahbaazcodes/polite-scraper-pipeline.git](https://github.com/shahbaazcodes/polite-scraper-pipeline.git)
cd polite-scraper-pipeline

# 2. Setup virtual environment & dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Execute Scraper Pipeline
python3 src/main.py
```

---

## 📊 Sample Execution Metrics (`output/run-report.json`)

```json
{
  "start_time": "2026-10-17T03:12:00Z",
  "duration_seconds": 0.15,
  "pages_fetched": 1,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1
}
```

---

## ⚠️ Known Limitation

* **Static Pagination Reliance:** The pipeline currently relies on standard CSS selectors (`li.next > a`) for HTML pagination[cite: 7]. If the target site transitions to dynamic client-side rendering or API-backed pagination, selector strategy updates or API endpoint reverse-engineering would be required.