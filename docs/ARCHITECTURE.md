# ARCHITECTURE DOCUMENTATION — QuakeScope

## 1. System Overview

QuakeScope is an interactive geospatial monitoring and intelligence platform that combines automated batch data generation with client-side real-time capabilities.

```
                           +--------------------------------------+
                           |             DATA SOURCES             |
                           |  USGS Earthquake Hazards GeoJSON    |
                           |  GitHub REST Search API (Python)     |
                           +------------------+-------------------+
                                              |
                     +------------------------+------------------------+
                     | (Build-time batch ingestion)                   | (Client-side live query)
                     v                                                 v
       +----------------------------+                     +----------------------------+
       |   PYTHON PIPELINE SERVICE  |                     |  BROWSER CLIENT FETCH      |
       |  - quake_service.py        |                     |  - Native CORS fetch       |
       |  - data_pipeline.py        |                     |  - Feed selector (24h/7d)  |
       |  - Atomic write to _site/  |                     |  - Offline fallback logic  |
       +-------------+--------------+                     +-------------+--------------+
                     |                                                  |
                     +------------------------+-------------------------+
                                              |
                                              v
                           +--------------------------------------+
                           |         QUAKESCOPE INTERFACE         |
                           |  - Leaflet.js Vector Map             |
                           |  - Plotly Intelligence Analytics     |
                           |  - Accessible Sortable Explorer      |
                           |  - GitHub Repository Intelligence    |
                           |  - Client-Side CSV/GeoJSON Export    |
                           +--------------------------------------+
```

---

## 2. Core Modules

### A. Geospatial Service (`quake_service.py`)
* **Purpose**: Reusable data abstraction layer for telemetry ingestion, field validation, security sanitization, statistical metrics, and format serialization.
* **Key Functions**:
  * `fetch_earthquakes_raw(feed_key)`: Connects to official USGS GeoJSON endpoints with bounded retries and exponential backoff.
  * `parse_earthquake_features(data)`: Validates coordinate boundaries (`lat [-90, 90]`, `lon [-180, 180]`), parses ISO timestamps, extracts depths, and sanitizes strings.
  * `fetch_top_repositories_raw(token)`: Ingests popular Python repositories from GitHub Search API, inspecting rate-limit headers.
  * `calculate_analytics(earthquakes)`: Generates KPI aggregates, magnitude histograms, depth bins, and hourly frequency tables.
  * `export_records_to_csv()`, `export_records_to_geojson()`: Formats records for export.

### B. Pipeline Orchestrator (`data_pipeline.py`)
* **Purpose**: CLI executable and CI build service.
* **Workflow**:
  1. Attempts live network ingestion of USGS and GitHub data.
  2. If upstream APIs are unreachable or rate-limited, safely recovers the verified snapshot from `data/cache_data.json`.
  3. If both live and cache data are missing, halts the build with an error code to protect the existing deployment from being overwritten with blank data (DEF-01).
  4. Generates HTML using `dashboard_template.py`.
  5. Performs atomic write: writes to `.html.tmp`, verifies file size (> 20KB) and closing tags, and executes an atomic file replacement.

### C. Dashboard Generator (`dashboard_template.py`)
* **Purpose**: Merges the pre-rendered JSON payload with `templates/dashboard.html` for instantaneous first-contentful paint.

### D. Single-Page Intelligence Application (`templates/dashboard.html`)
* **Styling**: Self-contained CSS tokens for dark navy / charcoal scientific analytics.
* **Map Engine**: Leaflet.js with CartoDB Dark Matter base tiles, OSM, and Esri Satellite.
* **Analytics**: Plotly histograms and bar charts with responsive resize listeners.
* **Data Explorer**: In-memory searchable, sortable, paginated table with detail modal and CSV/GeoJSON export.
* **Live Ingestion**: Client-side async fetch connecting directly to USGS GeoJSON (which natively supports browser CORS), updating the dashboard on demand.

---

## 3. Reliability & Security Principles

1. **Zero Data Destruction**: An API failure never overwrites a good dashboard.
2. **Atomic Writes**: Output files are written to `.tmp` files and validated before replacing target files.
3. **No Credential Leakage**: Unauthenticated requests are used by default; optional tokens are read from environment variables and never written to client-side bundles.
4. **URL & String Sanitization**: External links are validated against `https://` schemes, and text fields are HTML-escaped to prevent XSS.
5. **Static Hosting Compatibility**: Fully deployable to GitHub Pages with zero server-side runtime dependencies.

