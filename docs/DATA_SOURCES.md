# DATA SOURCES & ATTRIBUTION — QuakeScope

## 1. Primary Data Sources

### United States Geological Survey (USGS) Earthquake Hazards Program
* **Provider**: U.S. Geological Survey (USGS)
* **Official Website**: [earthquake.usgs.gov](https://earthquake.usgs.gov)
* **API Documentation**: [USGS GeoJSON Feed Documentation](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php)
* **License / Terms**: USGS data is in the public domain. Attribution is provided per USGS guidelines.
* **Endpoints Supported in QuakeScope**:
  * `4.5_week.geojson`: Earthquakes of magnitude 4.5+ over the past 7 days (Default build target).
  * `2.5_week.geojson`: Earthquakes of magnitude 2.5+ over the past 7 days.
  * `4.5_day.geojson`: Earthquakes of magnitude 4.5+ over the past 24 hours.
  * `4.5_month.geojson`: Earthquakes of magnitude 4.5+ over the past 30 days.
* **CORS Support**: USGS GeoJSON feeds natively support Cross-Origin Resource Sharing (CORS), enabling direct client-side browser updates.

### GitHub REST API (Search Repositories)
* **Provider**: GitHub, Inc.
* **Official Website**: [api.github.com](https://api.github.com)
* **Endpoint**: `https://api.github.com/search/repositories?q=language:python&sort=stars&order=desc&per_page=10`
* **Rate Limits**:
  * Unauthenticated: 60 requests/hour per IP (10 requests/minute for Search).
  * Authenticated: 5,000 requests/hour with personal access token (`GITHUB_TOKEN`).
* **Fallback Strategy**: In the event of a rate limit (HTTP 403), QuakeScope falls back to cached repository telemetry.

---

## 2. Geospatial Map Tiles & Attribution

1. **CARTO Dark Matter Tiles**:
   * Provider: [CARTO](https://carto.com/)
   * URL: `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`
   * Attribution: &copy; CARTO &bull; &copy; OpenStreetMap contributors
2. **OpenStreetMap**:
   * Provider: [OpenStreetMap Foundation](https://www.openstreetmap.org/)
   * Attribution: &copy; OpenStreetMap contributors
3. **Esri World Imagery**:
   * Provider: [Esri, Inc.](https://www.esri.com/)
   * Attribution: Tiles &copy; Esri &bull; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community

---

## 3. Data Freshness & Timestamps

* **Build Snapshot**: Generated during GitHub Actions CI or local `python data_pipeline.py` execution. Displayed in the status ribbon.
* **Live Refresh**: Updated directly from the user's browser upon clicking **Refresh** or selecting a different feed.
* **Time Zones**: Users can toggle between **UTC** (scientific standard) and **Local Browser Time** across all tables, feeds, and popups.

