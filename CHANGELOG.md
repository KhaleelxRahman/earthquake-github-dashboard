# CHANGELOG — QuakeScope

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] — 2026-11-01

### Major Upgrade: QuakeScope Global Earthquake Intelligence Platform

#### Added
* **Interactive Leaflet.js Geospatial Map**:
  * CartoDB Dark Matter tiles, OpenStreetMap, and Esri Satellite layer toggles.
  * Magnitude-scaled vector circle markers with dynamic color coding (Minor, Moderate, Strong, Major).
  * Animated pulse rings on major seismic events.
  * Interactive click popups displaying place, magnitude, depth, coordinates, timestamp, and USGS links.
  * Map controls: Zoom in/out, Reset View, Fullscreen toggle, and Live Cursor Coordinate HUD.
  * Real-time map filters for minimum magnitude and depth categories.
* **Modern Intelligence Design System**:
  * Dark navy / charcoal scientific analytics theme (`#070b14`, `#0d1527`, `#131f38`).
  * High-contrast typography with system font stack and monospace metric displays.
  * Multi-view tabbed navigation: *Overview*, *Live Map*, *Analytics*, *Explorer*, *GitHub Intelligence*, *About & Sources*.
  * Responsive layout tested from 1920px down to 360px mobile viewports.
  * Reduced-motion media query support (`prefers-reduced-motion: reduce`).
* **Dual Ingestion & Live Client-Side Refresh**:
  * Direct browser queries to USGS GeoJSON endpoints (CORS-enabled) allowing real-time switching between Past 24h, Past 7d, and Past 30d feeds without redeployment.
  * Pre-rendered static snapshot fallback for zero-latency initial load and offline resilience.
  * Honest data freshness ribbon displaying generation timestamp, active feed, and source status.
  * UTC and Local browser time toggle with dynamic updates across all views.
* **Seismic Analytics & Visualizations**:
  * Executive KPI metric cards: Total Earthquakes, Peak Magnitude, Average Magnitude, M5.0+ count, Shallow (<70km) count, and Most Active Region.
  * Plotly visualizations: Magnitude Distribution Histogram, Depth Distribution, Seismic Activity by UTC Hour, and Top 10 Active Regions.
* **Earthquake Event Explorer**:
  * Real-time search across location, country, and event ID.
  * Multi-column sortable table by Magnitude, Place, Date & Time, and Depth.
  * Pagination with configurable page size.
  * Event Detail Inspector Modal with felt reports and tsunami alert indicators.
  * Client-side export to RFC 4180 CSV and standard GeoJSON FeatureCollections.
* **GitHub Repository Intelligence**:
  * Upgraded popular Python repositories tracker with star metrics, fork counts, and descriptions.
  * Interactive horizontal bar chart ranking top repositories by star count.
* **Robust Python Backend & Data Pipeline (`quake_service.py` & `data_pipeline.py`)**:
  * Bounded HTTP retries with exponential backoff.
  * Rate-limit inspection for GitHub API.
  * Strict coordinate validation (`-90 <= lat <= 90`, `-180 <= lon <= 180`, `depth >= 0`).
  * Atomic file replacement (`.tmp` write, size and schema verification, atomic rename).
  * Last-known-good dataset preservation on upstream failure (prevents blank dashboard overwrites).
* **Automated Test Suite**:
  * 21 automated unit and integration tests covering parsing, validation, sanitization, analytics, exports, and atomic writer reliability.
* **CI/CD Deployment to GitHub Pages**:
  * Modernized GitHub Actions workflow with testing gate, automated builds into `_site/`, scheduled 6-hour refresh cron, and least-privilege permissions.

#### Fixed
* **DEF-01**: Resolved silent dashboard destruction where API outages wiped `index.html` with empty charts and returned code 0.
* **DEF-02**: Resolved GitHub Actions failure where `.github/workflows/deploy-pages.yml` deployed raw repository root without installing dependencies or running the pipeline.
* **DEF-04**: Fixed unclickable tooltip links in Plotly charts by moving event links to persistent Leaflet click popups and modal inspectors.
* **DEF-05**: Handled GitHub 403 rate limits with fallback to cached repository metadata.
* **DEF-07**: Added strict geospatial validation preventing `NaN` and out-of-bounds coordinates from breaking map rendering.
* **DEF-09**: Fixed inaccurate upstream repository links in README and dashboard.

---

## [1.0.0] — Initial Legacy Version
* Basic academic demonstration script generating two Plotly figures in a static HTML file.

