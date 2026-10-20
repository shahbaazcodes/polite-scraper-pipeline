# Polite Scraper & Data Ingestion Pipeline (Books to Scrape)

A production-grade, fault-tolerant web scraping and ETL ingestion pipeline built with **Python 3.10+**, **Requests**, **BeautifulSoup4**, and **Pydantic v2**[cite: 5].

This project collects product metadata across 60 books on a practice sandbox, normalizes messy raw text into typed models, enforces strict schema validation, exports both JSON and CSV payloads, survives broken pages without crashing, and generates structured execution metrics[cite: 4, 8, 9]..

---

## 🎯 Target Classification & Compliance

* **Target Site:** `https://books.toscrape.com/`[cite: 6]
* **Target Purpose:** Public practice sandbox built specifically for web scraping experimentation[cite: 6].
* **Collection Scope:** First 3 catalogue pages (60 unique book items)[cite: 4, 6].
* **Data Extracted:** `title`, `product_url`, `price_text`, `price_gbp` (numeric), `availability_text`, `rating_text`, `description`, `source_page`, and `fetched_at`[cite: 7, 8].
* **Robots.txt Result:** `no robots file found` (HTTP 404 response upon requesting `https://books.toscrape.com/robots.txt`)[cite: 6].
* **Ethics Statement:** Always check target site rules and terms before scraping[cite: 6]. Use official APIs whenever available, never bypass logins, paywalls, or access controls, and collect only the data necessary for the workload[cite: 9].

> **Compliance Statement:** I will not reuse this code on another site without checking its rules and terms first[cite: 6].

---

## 🛠️ Politeness Rules & Pipeline Architecture

1. **User-Agent Identification:** Sends custom header `FlyRankInternship-A9/1.0 (+https://github.com/shahbaazcodes/polite-scraper-pipeline)` on every request[cite: 6].
2. **Rate Limiting:** Enforces a mandatory `500 ms` delay (`time.sleep(0.5)`) prior to outbound HTTP network calls[cite: 7, 8].
3. **Request Timeout:** Enforces a strict `10.0s` timeout to prevent hanging connections[cite: 6].
4. **Local Caching:** Writes HTML pages to `cache/` upon initial fetch[cite: 6]. Subsequent pipeline executions read from disk (`CACHE HIT`), eliminating unnecessary server load[cite: 6].
5. **No-Browser Rationale:** The core catalogue and detail pages are fully server-side rendered HTML[cite: 9]. Raw HTTP requests via `requests` extract all target payload elements directly, making a headless browser (e.g., Playwright or Selenium) unnecessary and computationally wasteful[cite: 9].

---

## 📋 Data Schema & Optional Extras

### Pydantic v2 Model (`BookRecord`)
* **Strict Validation:** Validates required fields, URL schemes (`HttpUrl`), numeric price bounds (`ge=0.0`), and optional descriptions[cite: 8].
* **CSV Export:** Converts validated Pydantic objects into `output/books.csv` alongside `output/books.json`[cite: 8, 9].
* **Change Detection (Delta Hashing):** Computes an `SHA256` content hash for each record to track `new` vs `unchanged` items across pipeline executions[cite: 9].

---

## 🚀 Quick Start & Single-Command Execution

```bash
# 1. Setup virtual environment & dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Execute Production Scraper Pipeline
python3 src/main.py
```

---

## ⚔️ Bonus Stage: AI vs Me Code Audit

An AI-generated scraper was prompted and generated in quarantine at `ai-version/main.py`[cite: 10]. Comparing the two versions revealed critical architectural differences[cite: 10]:

### 1. Pagination & URL Resolution
* **AI Implementation:** Hardcoded the catalogue page loop (`page-1`, `page-2`, `page-3`) and used naive string replacement (`replace("../", "")`) to resolve relative links[cite: 7, 10].
* **Custom Implementation:** Follows pagination links dynamically (`li.next > a`) and uses standard `urllib.parse.urljoin()` to resolve absolute URLs safely[cite: 7, 10].

### 2. Caching & Politeness Controls
* **AI Implementation:** Issued direct HTTP requests without custom `User-Agent` headers, timeout definitions, or local HTML disk caching, hammering the target server repeatedly on every run[cite: 6, 10].
* **Custom Implementation:** Implements local `cache/` storage, custom header identification, and a mandatory `500ms` rate-limit delay[cite: 6, 7, 10].

### 3. Data Validation & Error Recovery
* **AI Implementation:** Relied on raw string slicing for currency formatting (`replace("£", "")`), which fails on non-standard encoding like `Â£51.77`[cite: 8, 10]. Unhandled page errors or missing fields crash the script[cite: 8, 10].
* **Custom Implementation:** Uses regex-based currency parsing, Pydantic v2 schema validation, single-retry transient error handling, and isolates broken pages without taking down the pipeline[cite: 8, 10].

---

## 📊 Sample Execution Metrics (`output/run-report.json`)

```json
{
  "start_time": "2026-10-17T03:15:00Z",
  "duration_seconds": 0.15,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1,
  "delta_summary": {
    "new": 0,
    "unchanged": 60
  }
}
```
