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

### European-Mediterranean Seismological Centre (EMSC) (Secondary Fallback)
* **Provider**: European-Mediterranean Seismological Centre (EMSC)
* **Official Website**: [seismicportal.eu](https://www.seismicportal.eu)
* **API Documentation**: [FDSNWS Event Web Service](https://www.seismicportal.eu/fdsnws/event/1/)
* **Endpoint**: `https://www.seismicportal.eu/fdsnws/event/1/query?format=json&limit=100&minmag=4.5`
* **License / Terms**: Open research data service. Public scientific use under standard CC-BY 4.0 citation.
* **Role in QuakeScope**: Automatically queried if USGS GeoJSON endpoint times out or fails.

### GitHub REST API (Search Repositories)
* **Provider**: GitHub, Inc.
* **Official Website**: [api.github.com](https://api.github.com)
* **Endpoint**: `https://api.github.com/search/repositories?q=language:python&sort=stars&order=desc&per_page=10`
* **Rate Limits**:
  * Unauthenticated: 60 requests/hour per IP (10 requests/minute for Search).
  * Authenticated: 5,000 requests/hour with personal access token (`GITHUB_TOKEN`).
* **Fallback Strategy**: In the event of a rate limit (HTTP 403), QuakeScope falls back to cached repository telemetry.

---

## 2. Geological Data & Plate Boundaries

### Global Tectonic Plate Boundaries (Peter Bird 2003 / PB2002)
* **Author & Citation**: Peter Bird (2003), *"An updated digital model of plate boundaries"*, Geochemistry, Geophysics, Geosystems (G3), 4(3), 1027, doi:10.1029/2001GC000252.
* **Dataset Model**: PB2002 digital boundary lines (subduction zones, continental transforms, ocean spreading ridges).
* **Date Compiled**: 2002–2003.
* **License**: Public scientific domain / Open academic citation.
* **Location in Project**: `data/tectonic_plates.geojson`.

---

## 3. Geospatial Map Tiles, Terms & Usage Limits

1. **CARTO Dark Matter Tiles (Default Basemap)**:
   * Provider: [CARTO](https://carto.com/basemaps/)
   * URL: `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`
   * Key Required: None for standard web applications under CARTO direct raster guidelines.
   * Required Attribution: `&copy; <a href="https://carto.com/">CARTO</a> &bull; &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>`
2. **OpenStreetMap Standard**:
   * Provider: [OpenStreetMap Foundation](https://www.openstreetmap.org/)
   * URL: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`
   * Key Required: None. Standard fair-use tile policy applies.
   * Required Attribution: `&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>`
3. **Esri World Imagery (Satellite)**:
   * Provider: [Esri, Inc.](https://www.esri.com/)
   * URL: `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`
   * Key Required: None (public imagery tile service).
   * Required Attribution: `Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community`
4. **Google Maps JavaScript API (Opt-In Alternative)**:
   * Provider: Google Cloud Platform
   * Key Required: Yes (`GOOGLE_MAPS_API_KEY`).
   * Quota / Terms: $200 monthly free credit (~28,000 loads/month). If key is absent or quota exceeded, QuakeScope gracefully falls back to Leaflet.

---

## 4. Scientific Disclaimers

* **No Earthquake Prediction**: Seismological consensus (IASPEI, USGS) affirms that earthquakes cannot be predicted with deterministic time, location, and magnitude. All statistics (Aki $b$-value, radiated energy, spatial aftershock clustering) are strictly descriptive and exploratory of observed catalog data.
* **Magnitude Completeness & Uncertainty**: $b$-value calculation requires $N \ge 15$ events above completeness threshold $M_c$. If sample size is below 15, the dashboard explicitly reports "Insufficient data" to maintain scientific rigor.

---

## 3. Data Freshness & Timestamps

* **Build Snapshot**: Generated during GitHub Actions CI or local `python data_pipeline.py` execution. Displayed in the status ribbon.
* **Live Refresh**: Updated directly from the user's browser upon clicking **Refresh** or selecting a different feed.
* **Time Zones**: Users can toggle between **UTC** (scientific standard) and **Local Browser Time** across all tables, feeds, and popups.

