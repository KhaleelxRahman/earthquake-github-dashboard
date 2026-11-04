# QuakeScope Pro — Scientific Platform Specification & Architecture

## 1. System Mission & Core Tenets

QuakeScope Pro is a real-time, scientifically rigorous earthquake intelligence and geospatial visualization platform. It bridges empirical seismology with modern high-performance web graphics.

### Anti-Slop & Scientific Integrity Directives
1. **No Deterministic Prediction**: In accordance with the consensus of the international seismological community (IASPEI, USGS), earthquakes cannot be predicted with exact time, location, and magnitude. The platform strictly presents **probabilistic, empirical, and observed historical seismicity**.
2. **Standard Seismological Formulations**:
   - **Gutenberg-Richter Magnitude-Frequency Relation**:
     $$\log_{10} N = a - bM$$
     The $b$-value is estimated via Aki's (1965) Maximum Likelihood Estimator:
     $$b = \frac{\log_{10}(e)}{\bar{M} - (M_{min} - \frac{\Delta M}{2})}$$
     where $\bar{M}$ is the sample mean magnitude, $M_{min}$ is the magnitude of completeness, and $\Delta M$ is the magnitude binning interval (typically $0.1$).
   - **Seismic Radiated Energy Formulation (Gutenberg-Richter 1956)**:
     $$\log_{10} E = 4.8 + 1.5 M \implies E = 10^{4.8 + 1.5 M} \text{ Joules}$$
     Equivalent TNT yield calculated using standard metric: $1 \text{ ton of TNT} \approx 4.184 \times 10^9 \text{ Joules}$.
   - **Hypocentral Depth Classification**:
     - *Shallow*: $0 \le d < 70\text{ km}$ (associated with highest surface peak ground acceleration).
     - *Intermediate*: $70 \le d < 300\text{ km}$.
     - *Deep*: $d \ge 300\text{ km}$ (subduction zone Wadati-Benioff zones).
   - **Aftershock Identification Heuristic (Modified Gardner-Knopoff Window)**:
     Identifies secondary clusters occurring within a spatial radius $R(M) = 10^{0.1238 M + 0.983}$ km and temporal window $T(M) = 10^{0.032 M + 1.68}$ days following a major mainshock.
   - **Tectonic Boundary Proximity**:
     Calculates geodesic haversine distance from each hypocenter epicenter to the nearest plate boundary based on Peter Bird's (2003) Global Tectonic Plates Model (*PB2002*).

---

## 2. Architecture & Data Flow

```text
[ USGS GeoJSON Feed ] ----> [ Exponential Backoff HTTP ]
[ EMSC Fallback Feed ] ---> [ Validation & Normalizer  ] ---> [ Seismology Engine ]
[ Bird 2003 Plates ] ----> [ Python Pipeline Runner   ]            |
                                    |                              v
                                    +--------------------> [ data/cache_data.json ]
                                                                   |
                                                                   v
                                                      [ Atomic Template Renderer ]
                                                                   |
                                                                   v
                                                        [ static index.html ]
                                                                   |
            +------------------------------------------------------+---------------------+
            | (Zero-Key Default)                                                         | (Opt-In Key)
            v                                                                            v
  [ Leaflet + Canvas Marker Layer ]                                            [ Google Maps Engine ]
  - Hardware-accelerated Canvas layer                                          - Vector / Satellite Hybrid
  - Tectonic plate polylines                                                   - Dynamic tile overlays
  - Depth-stratified color ramps                                               - Smooth zoom & tilt
  - Timeline chronological scrubber
```

---

## 3. Data Schema Definitions

### Earthquake Record Schema
```typescript
interface EarthquakeRecord {
  id: string;               // Unique provider identifier (e.g., "us7000pq1a")
  place: string;            // Geographic location description (HTML-sanitized)
  magnitude: number;        // Moment magnitude (-2.0 to 10.0)
  time: number;             // Epoch millisecond timestamp (UTC)
  coordinates: [number, number, number]; // [Longitude, Latitude, Depth in km]
  depth: number;            // Depth in km
  status: string;           // Review status ("reviewed" | "automatic")
  tsunami: number;          // Tsunami flag (0: none, 1: potential hazard)
  sig: number;              // USGS event significance index (0 to 1000)
  url: string;              // Official USGS event detail URL
  energy_joules: number;    // Calculated radiated energy (Joules)
  energy_tnt_tons: number;  // Calculated TNT equivalent (metric tons)
  nearest_plate?: string;   // Nearest tectonic plate boundary code
  plate_distance_km?: number; // Geodesic distance to plate boundary
}
```

### Plate Boundary Schema (Bird 2003 PB2002)
```typescript
interface PlateBoundaryFeature {
  type: "Feature";
  properties: {
    name: string;           // E.g., "Pacific - North American"
    code: string;           // E.g., "PA-NA"
    boundary_type: string;  // "subduction" | "transform" | "ridge"
  };
  geometry: {
    type: "LineString" | "MultiLineString";
    coordinates: number[][][]; // Lon, Lat pairs
  };
}
```

---

## 4. Security, Resilience & Fallback Guarantees

1. **Zero-Key First Default**:
   - The application functions with 100% feature parity out-of-the-box without requiring user accounts, paid subscriptions, or API keys.
   - Map tiles are served via public OpenStreetMap / CartoDB Positron raster layers with Leaflet Canvas marker clustering.
2. **Opt-In Key Elevation**:
   - If `GOOGLE_MAPS_API_KEY` is supplied via environment or configuration, the client activates the Google Maps dual-engine toggle while retaining instant fallback if offline or over quota.
3. **Defense-in-Depth Sanitization**:
   - Every external string (`place`, `id`, `url`) from USGS/EMSC APIs is explicitly escaped via HTML entity sanitization prior to template interpolation to eliminate XSS vectors.
4. **Pipeline Atomic Write**:
   - File generation writes first to `index.html.tmp.<uuid>` and commits via atomic file replacement (`os.replace`) to guarantee zero downtime or partially rendered states.

