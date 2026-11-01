# AUDIT REPORT — QuakeScope (formerly Earthquake GitHub Dashboard)
**Date:** 2026-11-01  
**Auditor:** Principal Full-Stack & Geospatial Systems Engineer  
**Repository:** `https://github.com/KhaleelxRahman/earthquake-github-dashboard`  
**Current Branch:** `main`  
**Commit Baseline:** `origin/main`

---

## 1. Executive Summary

A comprehensive architectural, code, UX, security, and deployment audit was conducted on the repository. The project originated as a rudimentary academic demonstration script combining the USGS past-week M4.5+ GeoJSON feed and the GitHub repository search API, outputting two static Plotly figures into a bare `index.html`.

While the foundational concept is sound, critical architectural, security, accessibility, and reliability flaws prevent it from operating as a dependable, production-grade intelligence platform.

---

## 2. Inventory of Existing Files

| File Path | Size | Purpose | Audit Status |
| :--- | :--- | :--- | :--- |
| `data_pipeline.py` | 9,988 B | Monolithic script for API fetch, data frame conversion, Plotly figure creation, and HTML output | **High Defects**: Silent data wipeout on API failure, zero retries, no rate-limit handling, lacks atomic file writing. |
| `index.html` | 60,061 B | Generated static page containing Plotly CDN script and embedded JSON chart divs | **Critical UX & A11y Defects**: No navigation, no summary metrics, no filters, unclickable tooltip links, no fallback if CDN blocked. |
| `requirements.txt` | 43 B | Dependencies: `pandas>=2.0`, `plotly>=5.18`, `requests>=2.31` | **Medium Defect**: Missing test runners (`pytest`), linters, and type annotations. |
| `.gitignore` | 33 B | Ignores `.venv/`, `__pycache__/`, `*.py[cod]` | **Low Defect**: Needs coverage for `.env`, IDE artifacts (`.vscode`, `.idea`), coverage reports, and build output directories (`_site/`, `dist/`). |
| `README.md` | 1,473 B | High-level summary of the beginner demo | **High Defect**: Points to upstream fork owner (`mohduzairali1710-bit`), claims "Live Data Pipeline", missing architecture, testing, and configuration. |
| `.github/workflows/deploy-pages.yml` | 805 B | GitHub Actions deployment to GitHub Pages | **Critical Defect**: Deploys raw workspace root without installing dependencies or running the Python pipeline. Leaks tests and configs to public web. |
| `earthquake-github-dashboard` | 0 B | Empty untracked file active in user editor | Preserved as-is per instruction not to touch unrelated files. |

---

## 3. Defect Classification & Detailed Findings

### Critical Defects

#### DEF-01: Silent Dashboard Destruction & Non-Failing Pipeline (Data Loss / Integrity)
* **Location**: `data_pipeline.py:48-58`, `data_pipeline.py:65-70`, `data_pipeline.py:122-124`, `data_pipeline.py:271-274`
* **Finding**: When an upstream API is unreachable, times out, returns HTTP 429/500, or invalid JSON, `get_json()` catches the exception, logs an error, and returns `None`. `fetch_earthquakes()` and `fetch_top_repositories()` turn `None` into empty DataFrames. `save_dashboard()` then writes an empty dashboard with "No earthquake data is available" directly into `index.html`, and `main()` exits with status `0`.
* **Impact**: A momentary network glitch or GitHub API rate limit permanently destroys the live dashboard with an empty placeholder while reporting success to CI.
* **Remediation**: Implement atomic file writing (`.tmp` file), schema and record validation, last-known-good data preservation, and non-zero exit codes on fatal data ingestion failures.

#### DEF-02: GitHub Actions Workflow Does Not Execute Data Pipeline
* **Location**: `.github/workflows/deploy-pages.yml:32-35`
* **Finding**: The deployment workflow simply checks out the repository and uploads `path: .` to GitHub Pages. It never installs Python, never installs requirements, never runs tests, and never runs `data_pipeline.py`.
* **Impact**: Pushing changes or running scheduled updates does not update data. Furthermore, deploying `.` publishes repository internal files (`.github`, `.gitignore`, `data_pipeline.py`, tests) to the public web.
* **Remediation**: Reconfigure GitHub Actions to setup Python 3.11+, install requirements, run unit tests, execute the pipeline to generate into an isolated `_site/` directory, and deploy exclusively `_site/`.

---

### High Defects

#### DEF-03: Zero Automated Test Suite
* **Location**: Entire repository (no `tests/` directory)
* **Finding**: No automated unit, integration, or regression tests exist.
* **Impact**: Any refactoring or API payload changes cannot be validated automatically.
* **Remediation**: Create a comprehensive test suite covering valid GeoJSON parsing, malformed coordinates, rate limits, empty results, timestamp conversions, and atomic writes.

#### DEF-04: Tooltip Link Trap & Inaccessible Map Visualizations
* **Location**: `data_pipeline.py:194`, `data_pipeline.py:223`
* **Finding**: External links are placed inside Plotly hover templates (`<a href='%{customdata[0]}' target='_blank'>`). In Plotly scatter_geo, tooltips disappear as soon as the mouse leaves the point, making the link virtually impossible to click on desktop and completely inoperable on touch/mobile devices. Furthermore, WebGL/SVG scatter plots are inaccessible to keyboard navigation and screen readers.
* **Remediation**: Provide an interactive Leaflet map with persistent click popups and a synchronized, accessible, sortable data table for complete screen reader and keyboard accessibility.

#### DEF-05: Unhandled GitHub Public Rate Limits (403/429)
* **Location**: `data_pipeline.py:46-50`
* **Finding**: Unauthenticated requests to GitHub Search API are limited to 60 requests/hr per IP (or 10 requests/min for search). When exceeded, GitHub returns HTTP 403 with `X-RateLimit-Remaining: 0` and `X-RateLimit-Reset`. The script crashes into the empty-data failure path.
* **Remediation**: Inspect rate-limit response headers, log reset times, support optional GitHub token if provided via environment variable, and fall back to cached repository data.

---

### Medium Defects

#### DEF-06: Misleading "Live" Claims & Missing Freshness Indicators
* **Location**: `index.html:13`, `README.md:1`
* **Finding**: The application claims to be a "Live Data Pipeline", yet it is a static snapshot with zero timestamps indicating when it was fetched, what time zone was used, or the status of the data feeds.
* **Remediation**: Rebrand as **QuakeScope — Global Earthquake Intelligence**. Provide explicit freshness badges with generation timestamps in both UTC and local browser time, feed window indicators, and client-side live refresh capability.

#### DEF-07: Incomplete GeoJSON and Coordinate Validation
* **Location**: `data_pipeline.py:86-104`
* **Finding**: Coordinates are blindly extracted as `coordinates[:3]`. Latitude is not checked for [-90, 90], Longitude is not checked for [-180, 180], and depth is not validated against non-negative physical values. Non-finite values (`NaN`, `Infinity`) can corrupt visualizations.
* **Remediation**: Implement a strict geospatial validation layer with coordinate boundary enforcement and NaN filtering.

#### DEF-08: Fragile CDN-Only Script Loading
* **Location**: `index.html:15`
* **Finding**: If `cdn.plot.ly` is blocked by ad-blockers, enterprise firewalls, or offline operation, the page fails silently to blank containers with zero feedback.
* **Remediation**: Provide fallback containers, error states, and noscript fallbacks.

---

### Low Defects

#### DEF-09: README Attribution & Upstream Link Discrepancies
* **Location**: `README.md:9-10`
* **Finding**: Hardcoded URL points to `mohduzairali1710-bit.github.io` rather than the active repository.
* **Remediation**: Rewrite `README.md` with accurate URLs, architecture diagrams, installation guides for Windows PowerShell and Unix, and clear licensing.

#### DEF-10: Incomplete `.gitignore`
* **Location**: `.gitignore`
* **Finding**: Missing common development artifacts like `.env`, `.pytest_cache/`, `_site/`, `.coverage`.
* **Remediation**: Upgrade `.gitignore` to standard Python and web deployment templates.

---

## 4. Verification of Baseline Run
* Running `.\.venv\Scripts\python.exe data_pipeline.py` in sandbox without network cleanly reproduced **DEF-01**: it wiped `index.html` with empty charts and returned code 0.
* Restored `index.html` to commit HEAD to ensure non-destructive testing baseline.

