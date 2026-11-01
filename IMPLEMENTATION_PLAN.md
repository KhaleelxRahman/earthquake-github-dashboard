# IMPLEMENTATION PLAN — QuakeScope: Global Earthquake Intelligence
**Project:** QuakeScope — Global Earthquake Intelligence  
**Author:** Principal Full-Stack & Geospatial Architect  
**Date:** 2026-11-01  

---

## 1. Architectural Strategy

QuakeScope is structured around a **Dual-Layer Ingestion & Intelligence Architecture**:

```
+-------------------------------------------------------------+
|                      DATA SOURCES                           |
|   USGS GeoJSON API (Past 7 Days M4.5+ / M2.5+ / All)       |
|   GitHub Search API (Popular Python Repositories)           |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|              PYTHON DATA PIPELINE & BUILD SERVICE           |
|  - Exponential Backoff Retries & Timeout Guards             |
|  - Strict Geospatial Schema & Coordinate Validation          |
|  - Safe Atomic File Operations & Fallback Cache             |
|  - Static Asset Generation into isolated `_site/`           |
|  - Automated Test Suite Gate (pytest/unittest)              |
+------------------------------+------------------------------+
                               | (Build Artifacts)
                               v
+-------------------------------------------------------------+
|             CLIENT-SIDE QUAKESCOPE WEB PLATFORM             |
|  - Modern Dark-Navy / Charcoal Intelligence Design System   |
|  - Interactive Leaflet.js Map + CartoDB Dark Matter Tiles    |
|  - Magnitude-colored & Scaled Vector Pulse Markers          |
|  - Persistent Click Popups with USGS Deep Links             |
|  - Plotly & Chart Analytics (Frequency, Depth, Trends)      |
|  - Live Client-Side Feed Refresher (CORS USGS Direct Fetch)  |
|  - Earthquake Event Explorer with Instant Search & Sorting   |
|  - Event Details Inspector Modal                            |
|  - Accessible Data Tables with Screen-Reader Support        |
|  - Client-Side CSV & GeoJSON Export                         |
|  - GitHub Repository Intelligence Module                    |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                 AUTOMATED CI/CD (GitHub Pages)              |
|  - Test Runner Gate (Fails on broken parsing/schema)        |
|  - Scheduled Cron Refresh (Every 6 hours)                   |
|  - Least-Privilege GitHub Actions deploying `_site/`        |
+-------------------------------------------------------------+
```

---

## 2. Implementation Phases & Milestones

### Phase A: Core Pipeline & Geospatial Service Refactoring
* Create `quake_service.py` to decouple data fetching, sanitization, validation, statistics calculation, and caching.
* Support configurable time windows (1h, 1d, 7d, 30d) and magnitude thresholds (M2.5+, M4.5+, M6.0+).
* Implement exponential backoff retry for network errors.
* Validate coordinates (-90 <= lat <= 90, -180 <= lon <= 180, depth >= 0).
* Sanitize all external strings and URLs (`https://` scheme whitelist only).
* Implement atomic file replacement: write to `.tmp`, validate schema, then replace target file. If upstream APIs fail, preserve last-known-good dataset and exit with error.

### Phase B: Design System & Modern Web Interface
* Implement dark navy / charcoal scientific palette:
  * Primary Background: `#0a0f1d`, Surface: `#131d31`, Border: `#1f2d47`, Highlight: `#0ea5e9`, Accent: `#14b8a6`.
  * Magnitude color scale:
    * M < 5.0: Green / Teal (`#10b981`)
    * M 5.0 - 5.9: Amber (`#f59e0b`)
    * M 6.0 - 6.9: Coral / Orange (`#f97316`)
    * M 7.0+: Crimson / Alert Red (`#ef4444`)
* Multi-view tabbed architecture:
  1. **Overview**: Key metrics, global map preview, recent feed, strongest quakes list, time trend.
  2. **Live Map**: Full-screen interactive Leaflet map with zoom, pan, reset view, layer toggles, and filters.
  3. **Analytics**: Plotly visualizations for magnitude distribution, depth analysis, and regional charts.
  4. **Earthquake Explorer**: Sortable table with search, magnitude/depth filter, pagination, and CSV/GeoJSON export.
  5. **GitHub Intelligence**: Popular Python repos, star chart, search, and direct links.
  6. **About & Sources**: Data attribution, architecture, and technology specs.

### Phase C: Dual-Mode Live Refresh & Offline Fallback
* Bake the build-time dataset into the HTML payload as safe JSON.
* Add client-side live fetcher that directly polls USGS GeoJSON API (which natively supports browser CORS) so visitors can switch feeds (Past 24h, Past 7d, Past 30d) or click "Refresh Now".
* If offline or API fails, smoothly fallback to the pre-rendered snapshot with a clear "Stale / Offline" badge.

### Phase D: Testing & Quality Assurance
* Create `tests/test_pipeline.py` with mock responses:
  * Normal USGS feed parsing.
  * Empty GeoJSON features.
  * Malformed coordinates (out of range, NaN, non-numeric).
  * Missing properties.
  * GitHub API valid responses, rate limit (HTTP 403) handling, and network failures.
  * Atomic writer and last-known-good protection.
  * CSV/GeoJSON export data fidelity.
* Verify test execution with standard `unittest` and `pytest`.

### Phase E: GitHub Actions Workflow Upgrade
* Update `.github/workflows/deploy-pages.yml`:
  * Install dependencies.
  * Run test suite.
  * Run pipeline generating into `_site/`.
  * Upload only `_site/` artifact.
  * Add scheduled cron trigger (`cron: '0 */6 * * *'`).

### Phase F: Documentation & Project Standards
* Update `requirements.txt` with test & production dependencies.
* Rewrite `README.md` with features, screenshots, local run steps, test instructions, and attribution.
* Create `docs/ARCHITECTURE.md`, `docs/DATA_SOURCES.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `TESTING_REPORT.md`, `.env.example`, and `LICENSE` (MIT).

