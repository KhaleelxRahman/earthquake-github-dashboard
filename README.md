# QuakeScope — Global Earthquake Intelligence

[![Deploy QuakeScope to GitHub Pages](https://github.com/KhaleelxRahman/earthquake-github-dashboard/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/KhaleelxRahman/earthquake-github-dashboard/actions/workflows/deploy-pages.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-teal.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

**QuakeScope** is an interactive, professional-grade global earthquake intelligence and geospatial analytics platform. It ingests verified seismic telemetry from the **United States Geological Survey (USGS)** and open-source software trends from the **GitHub REST API**, transforming raw data into an accessible, responsive dashboard with real-time browser refresh capabilities.

---

## Live Dashboard

Explore the hosted application on GitHub Pages:  
👉 **[https://KhaleelxRahman.github.io/earthquake-github-dashboard/](https://KhaleelxRahman.github.io/earthquake-github-dashboard/)**

---

## What It Does & Does Not Do

### What It Does
* **Dual-Provider Interactive Geospatial Visualization**: Global vector map with an instant in-app provider switcher:
  * **🌐 Leaflet.js (Default)**: Hardware-accelerated HTML5 Canvas marker renderer (`L.canvas()`) with CartoDB Dark Matter, OpenStreetMap, and Esri Satellite basemaps. Zero keys needed.
  * **🗺️ Google Maps**: Official Google Maps JavaScript API with customized dark theme, magnitude circle scaling, interactive InfoWindows, and smooth controls.
* **Tectonic Plate Boundary Overlays**: Bundled Peter Bird (2003) global plate boundary and fault line vector layer (*PB2002*), with toggleable visibility and boundary classifications.
* **Empirical Seismology & Physics Engine (Exploratory / Non-Predictive)**:
  * **Gutenberg-Richter Law & Aki's (1965) MLE**: Computes dynamic $b$-value slope and standard error ($\sigma_b$) directly from observed magnitude distributions. Documents completeness threshold ($M_c$), binning ($\Delta M = 0.1$), and sample size ($N \ge 15$). Descriptive/exploratory only; strictly not an earthquake prediction or rupture forecast.
  * **Seismic Radiated Energy Formulation**: Real-time energy computation via Gutenberg-Richter (1956) formulation ($E = 10^{4.8 + 1.5M}$ Joules) with metric ton TNT equivalencies.
  * **IASPEI Depth Stratification**: Color and filter classification into Shallow (<70 km), Intermediate (70–300 km), and Deep (≥300 km) events.
* **Chronological Time Scrubber & Playback**: Interactive timeline scrubber and automated play/pause animation allowing sequential review of seismic event propagation.
* **Scientific Dark / Paper Light Mode**: Toggleable accessible theme switcher supporting high-contrast daylight field research and dark laboratory environments.
* **Multi-Source Ingestion with EMSC Fallback**: Automated primary ingestion from USGS GeoJSON with live secondary fallback to EMSC (European-Mediterranean Seismological Centre) and verified cached baselines.
* **Magnitude-Scaled & Colored Telemetry**: Visualizes earthquakes with magnitude-scaled markers and color indicators (Minor, Moderate, Strong, Major) with pulse animations for significant events.
* **Dual-Layer Ingestion**: Combines pre-rendered build snapshots for zero-latency initial page loads with direct client-side browser polling to the USGS CORS endpoints.
* **Advanced Analytics**: Interactive Plotly distributions for earthquake magnitude, focal depth, UTC hourly frequency, and regional activity rankings.
* **Accessible Earthquake Explorer**: Searchable, multi-column sortable table with pagination, event detail inspector modal, and client-side **RFC 4180 CSV** and **GeoJSON** export.
* **GitHub Repository Intelligence**: Tracks popular Python repositories with stars, forks, and interactive bar chart rankings.
* **Zero-Data-Loss Architecture**: Atomic file writing, retry mechanisms with exponential backoff, and automatic fallback to verified snapshots prevent pipeline failures from wiping out working dashboards.
* **Graceful Map Degradation**: If Google Maps is selected without a key, or if authentication fails (`gm_authFailure`), QuakeScope displays a clear, polite notice banner and retains a fully operational Leaflet fallback—**never blanking the dashboard**.

### What It Does Not Do
* **No AI Earthquake Predictions**: Earthquakes cannot be predicted. QuakeScope reports historical and real-time observed telemetry provided by scientific seismic monitoring networks.
* **No Closed APIs or Paid Dependencies**: Operates entirely with open-source mapping and public science endpoints.

---

## Platform Architecture

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
|  - Bounded Retries with Exponential Backoff                 |
|  - Strict Geospatial Schema & Coordinate Validation          |
|  - Safe Atomic File Operations & Fallback Cache             |
|  - Output Generation into `_site/` and `index.html`         |
|  - Automated Test Suite Gate (21 Unit & Integration Tests)  |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|             CLIENT-SIDE QUAKESCOPE WEB PLATFORM             |
|  - Dark Navy / Charcoal Scientific Analytics Theme          |
|  - Interactive Leaflet.js Map + Layer Toggles               |
|  - Interactive Plotly Visualizations & Hourly Activity      |
|  - Real-Time Search, Filtering, and Pagination               |
|  - Client-Side Live Refresh (USGS CORS Direct Fetch)        |
|  - Client-Side CSV & GeoJSON Export                         |
|  - GitHub Repository Intelligence Module                    |
+-------------------------------------------------------------+
```

---

## Technology Stack

* **Language**: Python 3.10+ (tested on Python 3.11, 3.12, 3.13)
* **Data Processing**: Pandas, Requests, Python Standard Library (`unittest`, `json`, `pathlib`)
* **Mapping**: Leaflet.js 1.9.4 with CartoDB Dark Matter, OpenStreetMap, and Esri World Imagery
* **Data Visualization**: Plotly.js 2.29.1
* **Frontend**: Semantic HTML5, CSS3 Custom Properties (Dark Navy Theme), Vanilla ES6+ JavaScript
* **CI/CD**: GitHub Actions deploying to GitHub Pages

---

## Local Setup & Run

### 1. Clone the Repository
```bash
git clone https://github.com/KhaleelxRahman/earthquake-github-dashboard.git
cd earthquake-github-dashboard
```

### 2. Set Up Virtual Environment

#### Windows PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run the Data Pipeline
```bash
# Standard run (fetches live data, falls back to cache if offline)
python data_pipeline.py

# Build with Google Maps JavaScript API enabled
python data_pipeline.py --google-maps-key "YOUR_API_KEY"

# Force offline build using verified baseline
python data_pipeline.py --offline

# Validate output integrity without modifying files
python data_pipeline.py --validate-only
```

See [docs/GOOGLE_MAPS_SETUP.md](docs/GOOGLE_MAPS_SETUP.md) for full instructions on Google Cloud configuration, domain restrictions, and secret setup.

Open `index.html` in your web browser to explore the dashboard locally.

---

## Running the Automated Test Suite

QuakeScope includes 39 comprehensive unit and integration tests that run completely offline:

```bash
# Run tests with Python's built-in test runner
python -m unittest discover -s tests -v

# Or using pytest if installed
pytest -v
```

All tests validate coordinate ranges, data sanitization, empty responses, malformed records, rate-limit recovery, Google Maps fallback and injection, inline JavaScript syntax validation, and atomic writing.

---

## GitHub Pages Deployment

The repository includes an automated workflow in `.github/workflows/deploy-pages.yml` that:
1. Runs the automated test suite.
2. Ingests fresh data from the USGS and GitHub APIs.
3. Builds the production site into an isolated `_site/` directory.
4. Validates the build output.
5. Deploys the artifact to GitHub Pages.
6. Automatically refreshes every 6 hours via scheduled cron (`cron: '0 */6 * * *'`).

### One-Time Manual Setup in GitHub:
1. Go to your repository on GitHub: `https://github.com/KhaleelxRahman/earthquake-github-dashboard`.
2. Click **Settings** &rarr; **Pages**.
3. Under **Build and deployment** &rarr; **Source**, select **GitHub Actions**.
4. Push to `main` or trigger **Deploy QuakeScope to GitHub Pages** under the **Actions** tab.

---

## Data Sources & Attribution

* **Earthquake Telemetry**: [USGS Earthquake Hazards Program](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php). Data is in the public domain.
* **Repository Telemetry**: [GitHub REST API](https://docs.github.com/en/rest).
* **Map Tiles**: [CARTO Dark Matter](https://carto.com/basemaps/), [OpenStreetMap](https://www.openstreetmap.org/), and [Esri](https://www.esri.com/).

See [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) for endpoint details and rate-limit specifications.

---

## License

This project is licensed under the [MIT License](LICENSE) &copy; 2026 Khaleel Rahman.
