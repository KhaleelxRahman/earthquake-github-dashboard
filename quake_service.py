"""Core data service for QuakeScope.

Handles API ingestion, validation, sanitization, statistical aggregation,
and serialization for USGS earthquake data and GitHub repository intelligence.
"""

from __future__ import annotations

import html
import logging
import math
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("quake_service")

USGS_FEEDS: Dict[str, str] = {
    "4.5_week": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson",
    "2.5_week": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson",
    "all_week": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson",
    "4.5_day": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson",
    "4.5_month": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_month.geojson",
}

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
DEFAULT_TIMEOUT_SECONDS = 15
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0


def sanitize_url(raw_url: Optional[str]) -> str:
    """Sanitize and validate an external URL, allowing only HTTPS/HTTP schemes."""
    if not raw_url or not isinstance(raw_url, str):
        return ""
    stripped = raw_url.strip()
    try:
        parsed = urlparse(stripped)
        if parsed.scheme in ("https", "http") and parsed.netloc:
            return stripped
    except Exception:
        pass
    return ""


def sanitize_text(raw_text: Optional[str], default: str = "") -> str:
    """Sanitize and escape external text strings to prevent HTML injection."""
    if raw_text is None:
        return default
    cleaned = str(raw_text).strip()
    return html.escape(cleaned, quote=True) if cleaned else default


def validate_coordinates(lat: Any, lon: Any, depth: Any) -> Tuple[bool, Optional[float], Optional[float], Optional[float], str]:
    """Validate latitude, longitude, and depth coordinates.

    Latitude must be between -90 and 90.
    Longitude must be between -180 and 180.
    Depth must be a finite float.
    """
    try:
        f_lat = float(lat)
        f_lon = float(lon)
        f_depth = float(depth)
    except (TypeError, ValueError):
        return False, None, None, None, "Coordinates must be numeric"

    if any(math.isnan(x) or math.isinf(x) for x in (f_lat, f_lon, f_depth)):
        return False, None, None, None, "Coordinates must be finite numbers"

    if not (-90.0 <= f_lat <= 90.0):
        return False, None, None, None, f"Latitude {f_lat} outside [-90, 90]"

    if not (-180.0 <= f_lon <= 180.0):
        return False, None, None, None, f"Longitude {f_lon} outside [-180, 180]"

    return True, round(f_lat, 4), round(f_lon, 4), round(f_depth, 2), "OK"


def validate_magnitude(mag: Any) -> Tuple[bool, Optional[float], str]:
    """Validate earthquake magnitude (must be a finite float between -2.0 and 10.0)."""
    try:
        f_mag = float(mag)
    except (TypeError, ValueError):
        return False, None, "Magnitude must be numeric"

    if math.isnan(f_mag) or math.isinf(f_mag):
        return False, None, "Magnitude must be a finite number"

    if not (-2.0 <= f_mag <= 10.5):
        return False, None, f"Magnitude {f_mag} outside reasonable range [-2.0, 10.5]"

    return True, round(f_mag, 2), "OK"


def request_with_retry(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = MAX_RETRIES,
    backoff_factor: float = INITIAL_BACKOFF_SECONDS,
) -> Optional[requests.Response]:
    """Execute an HTTP GET request with bounded retries and exponential backoff."""
    req_headers = {"User-Agent": "QuakeScope-Intelligence/2.0 (Geospatial Research)"}
    if headers:
        req_headers.update(headers)

    attempt = 0
    while attempt < max_retries:
        attempt += 1
        try:
            response = requests.get(
                url,
                params=params,
                headers=req_headers,
                timeout=timeout,
            )
            # Handle rate limiting explicitly
            if response.status_code == 403 and "X-RateLimit-Remaining" in response.headers:
                remaining = response.headers.get("X-RateLimit-Remaining")
                reset_time = response.headers.get("X-RateLimit-Reset")
                logger.warning(
                    "GitHub API rate limit hit (remaining: %s, reset: %s).",
                    remaining,
                    reset_time,
                )
                return response

            if response.status_code in (429, 500, 502, 503, 504):
                logger.warning(
                    "Server error %d on attempt %d/%d for %s.",
                    response.status_code,
                    attempt,
                    max_retries,
                    url,
                )
                if attempt < max_retries:
                    sleep_time = backoff_factor * (2 ** (attempt - 1))
                    time.sleep(sleep_time)
                    continue

            response.raise_for_status()
            return response

        except (requests.ConnectionError, requests.Timeout) as exc:
            logger.warning(
                "Network transient failure on attempt %d/%d for %s: %s",
                attempt,
                max_retries,
                url,
                exc,
            )
            if attempt < max_retries:
                sleep_time = backoff_factor * (2 ** (attempt - 1))
                time.sleep(sleep_time)
                continue
        except requests.RequestException as exc:
            logger.error("Non-retryable request error for %s: %s", url, exc)
            return None

    logger.error("Exceeded max retries (%d) for %s.", max_retries, url)
    return None


def fetch_earthquakes_raw(feed_key: str = "4.5_week") -> Tuple[Optional[dict], str]:
    """Fetch raw GeoJSON payload from USGS for the given feed key."""
    feed_url = USGS_FEEDS.get(feed_key, USGS_FEEDS["4.5_week"])
    logger.info("Fetching USGS earthquake GeoJSON feed: %s", feed_url)

    response = request_with_retry(feed_url)
    if response is None:
        return None, "Network failure or timeout contacting USGS API"

    if response.status_code != 200:
        return None, f"USGS API returned HTTP status {response.status_code}"

    try:
        data = response.json()
    except ValueError as exc:
        return None, f"Invalid JSON received from USGS: {exc}"

    if not isinstance(data, dict):
        return None, "USGS response payload is not a JSON object"

    return data, "OK"


def parse_earthquake_features(data: dict) -> List[Dict[str, Any]]:
    """Parse and validate USGS GeoJSON features into structured records."""
    if not isinstance(data, dict):
        return []

    features = data.get("features")
    if not isinstance(features, list):
        logger.error("USGS payload missing 'features' list.")
        return []

    valid_records: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()

    for feature in features:
        if not isinstance(feature, dict):
            continue

        feat_id = feature.get("id") or ""
        if feat_id and feat_id in seen_ids:
            continue  # Prevent duplicate events

        properties = feature.get("properties")
        geometry = feature.get("geometry")
        if not isinstance(properties, dict) or not isinstance(geometry, dict):
            continue

        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) < 3:
            continue

        # Coordinate validation
        lon, lat, depth = coordinates[0], coordinates[1], coordinates[2]
        coord_valid, f_lat, f_lon, f_depth, coord_err = validate_coordinates(lat, lon, depth)
        if not coord_valid:
            logger.debug("Skipping feature %s due to coord error: %s", feat_id, coord_err)
            continue

        # Magnitude validation
        mag = properties.get("mag")
        mag_valid, f_mag, mag_err = validate_magnitude(mag)
        if not mag_valid:
            logger.debug("Skipping feature %s due to mag error: %s", feat_id, mag_err)
            continue

        # Timestamp validation
        raw_time = properties.get("time")
        if raw_time is None:
            continue
        try:
            timestamp_ms = int(raw_time)
            dt = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
            iso_time = dt.isoformat()
        except (ValueError, TypeError, OverflowError):
            continue

        place = sanitize_text(properties.get("place"), default="Unknown location")
        url = sanitize_url(properties.get("url"))
        felt = properties.get("felt")
        tsunami = properties.get("tsunami")
        sig = properties.get("sig")
        status = properties.get("status")
        mag_type = properties.get("magType")

        record = {
            "id": feat_id or f"quake-{f_lat}-{f_lon}-{timestamp_ms}",
            "place": place,
            "magnitude": f_mag,
            "time_ms": timestamp_ms,
            "time_iso": iso_time,
            "latitude": f_lat,
            "longitude": f_lon,
            "depth_km": f_depth,
            "url": url,
            "felt": int(felt) if felt is not None and isinstance(felt, (int, float)) else None,
            "tsunami": int(tsunami) if tsunami in (0, 1) else 0,
            "significance": int(sig) if sig is not None and isinstance(sig, (int, float)) else None,
            "status": sanitize_text(status, default="reviewed"),
            "mag_type": sanitize_text(mag_type, default=""),
        }

        if feat_id:
            seen_ids.add(feat_id)
        valid_records.append(record)

    # Sort descending by event time
    valid_records.sort(key=lambda r: r["time_ms"], reverse=True)
    logger.info("Parsed %d valid earthquake records from USGS feed.", len(valid_records))
    return valid_records


def fetch_top_repositories_raw(token: Optional[str] = None) -> Tuple[Optional[dict], str]:
    """Fetch top Python repositories from GitHub Search API."""
    headers: Dict[str, str] = {
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    params = {
        "q": "language:python",
        "sort": "stars",
        "order": "desc",
        "per_page": 10,
    }
    logger.info("Fetching popular Python repositories from GitHub Search API.")
    response = request_with_retry(GITHUB_SEARCH_URL, params=params, headers=headers)

    if response is None:
        return None, "Network failure or timeout contacting GitHub API"

    if response.status_code == 403:
        return None, "GitHub API rate limit exceeded (HTTP 403)"

    if response.status_code != 200:
        return None, f"GitHub API returned HTTP {response.status_code}"

    try:
        data = response.json()
    except ValueError as exc:
        return None, f"Invalid JSON received from GitHub: {exc}"

    if not isinstance(data, dict):
        return None, "GitHub response is not a JSON object"

    return data, "OK"


def parse_repository_items(data: dict) -> List[Dict[str, Any]]:
    """Parse and validate GitHub repository items into clean records."""
    if not isinstance(data, dict):
        return []

    items = data.get("items")
    if not isinstance(items, list):
        return []

    valid_repos: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        name = item.get("name")
        full_name = item.get("full_name")
        stars = item.get("stargazers_count")
        if not name or stars is None:
            continue

        try:
            stars_int = int(stars)
            forks_int = int(item.get("forks_count", 0))
        except (ValueError, TypeError):
            continue

        repo_url = sanitize_url(item.get("html_url"))
        description = sanitize_text(item.get("description"), default="No description provided.")
        language = sanitize_text(item.get("language"), default="Python")
        updated_at = item.get("updated_at") or ""

        valid_repos.append(
            {
                "name": sanitize_text(name),
                "full_name": sanitize_text(full_name or name),
                "stars": stars_int,
                "forks": forks_int,
                "description": description,
                "url": repo_url,
                "language": language,
                "updated_at": updated_at,
            }
        )

    # Sort descending by stars
    valid_repos.sort(key=lambda r: r["stars"], reverse=True)
    logger.info("Parsed %d repository records from GitHub.", len(valid_repos))
    return valid_repos


def calculate_analytics(earthquakes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate key performance indicators and distributions from earthquake records."""
    if not earthquakes:
        return {
            "total_count": 0,
            "max_magnitude": 0.0,
            "max_event_place": "N/A",
            "avg_magnitude": 0.0,
            "strong_count": 0,  # Mag >= 5.0
            "major_count": 0,   # Mag >= 6.0
            "shallow_count": 0, # Depth < 70 km
            "deep_count": 0,    # Depth >= 300 km
            "intermediate_count": 0, # 70 <= Depth < 300 km
            "most_active_region": "None",
            "tsunami_alerts": 0,
            "magnitude_bins": {"< 5.0": 0, "5.0 - 5.9": 0, "6.0 - 6.9": 0, "7.0+": 0},
            "depth_bins": {"0-35km": 0, "35-70km": 0, "70-150km": 0, "150-300km": 0, "300km+": 0},
            "hourly_distribution": {str(h): 0 for h in range(24)},
            "latest_event_iso": None,
            "oldest_event_iso": None,
        }

    total = len(earthquakes)
    magnitudes = [e["magnitude"] for e in earthquakes]
    depths = [e["depth_km"] for e in earthquakes]

    max_mag = max(magnitudes)
    max_event = next((e for e in earthquakes if e["magnitude"] == max_mag), earthquakes[0])
    avg_mag = round(sum(magnitudes) / total, 2)

    strong_count = sum(1 for m in magnitudes if m >= 5.0)
    major_count = sum(1 for m in magnitudes if m >= 6.0)

    shallow_count = sum(1 for d in depths if d < 70.0)
    intermediate_count = sum(1 for d in depths if 70.0 <= d < 300.0)
    deep_count = sum(1 for d in depths if d >= 300.0)

    tsunami_alerts = sum(1 for e in earthquakes if e.get("tsunami") == 1)

    # Magnitude bins
    mag_bins = {"< 5.0": 0, "5.0 - 5.9": 0, "6.0 - 6.9": 0, "7.0+": 0}
    for m in magnitudes:
        if m < 5.0:
            mag_bins["< 5.0"] += 1
        elif m < 6.0:
            mag_bins["5.0 - 5.9"] += 1
        elif m < 7.0:
            mag_bins["6.0 - 6.9"] += 1
        else:
            mag_bins["7.0+"] += 1

    # Depth bins
    depth_bins = {"0-35km": 0, "35-70km": 0, "70-150km": 0, "150-300km": 0, "300km+": 0}
    for d in depths:
        if d < 35.0:
            depth_bins["0-35km"] += 1
        elif d < 70.0:
            depth_bins["35-70km"] += 1
        elif d < 150.0:
            depth_bins["70-150km"] += 1
        elif d < 300.0:
            depth_bins["150-300km"] += 1
        else:
            depth_bins["300km+"] += 1

    # Extract regions (approximate from place)
    region_counts: Dict[str, int] = {}
    hourly_dist: Dict[str, int] = {str(h): 0 for h in range(24)}

    for e in earthquakes:
        place = e.get("place", "")
        region = place.split(",")[-1].strip() if "," in place else place
        region_counts[region] = region_counts.get(region, 0) + 1

        # Hourly UTC distribution
        try:
            dt = datetime.fromtimestamp(e["time_ms"] / 1000.0, tz=timezone.utc)
            hourly_dist[str(dt.hour)] += 1
        except Exception:
            pass

    most_active_region = "Unknown"
    if region_counts:
        most_active_region = max(region_counts.items(), key=lambda item: item[1])[0]

    return {
        "total_count": total,
        "max_magnitude": max_mag,
        "max_event_place": max_event.get("place", "Unknown"),
        "avg_magnitude": avg_mag,
        "strong_count": strong_count,
        "major_count": major_count,
        "shallow_count": shallow_count,
        "intermediate_count": intermediate_count,
        "deep_count": deep_count,
        "most_active_region": most_active_region,
        "tsunami_alerts": tsunami_alerts,
        "magnitude_bins": mag_bins,
        "depth_bins": depth_bins,
        "hourly_distribution": hourly_dist,
        "latest_event_iso": earthquakes[0]["time_iso"] if earthquakes else None,
        "oldest_event_iso": earthquakes[-1]["time_iso"] if earthquakes else None,
    }


def export_records_to_csv(earthquakes: List[Dict[str, Any]]) -> str:
    """Generate RFC 4180 compliant CSV string from earthquake records."""
    headers = [
        "id",
        "magnitude",
        "place",
        "time_utc",
        "latitude",
        "longitude",
        "depth_km",
        "tsunami",
        "felt_reports",
        "significance",
        "usgs_url",
    ]
    lines = [",".join(headers)]

    for e in earthquakes:
        place_escaped = '"' + e.get("place", "").replace('"', '""') + '"'
        row = [
            str(e.get("id", "")),
            str(e.get("magnitude", "")),
            place_escaped,
            str(e.get("time_iso", "")),
            str(e.get("latitude", "")),
            str(e.get("longitude", "")),
            str(e.get("depth_km", "")),
            str(e.get("tsunami", 0)),
            str(e.get("felt") if e.get("felt") is not None else ""),
            str(e.get("significance") if e.get("significance") is not None else ""),
            str(e.get("url", "")),
        ]
        lines.append(",".join(row))

    return "\n".join(lines)


def export_records_to_geojson(earthquakes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Serialize earthquake records back to standard GeoJSON FeatureCollection."""
    features = []
    for e in earthquakes:
        feature = {
            "type": "Feature",
            "id": e.get("id"),
            "geometry": {
                "type": "Point",
                "coordinates": [e.get("longitude"), e.get("latitude"), e.get("depth_km")],
            },
            "properties": {
                "mag": e.get("magnitude"),
                "place": e.get("place"),
                "time": e.get("time_ms"),
                "url": e.get("url"),
                "tsunami": e.get("tsunami"),
                "felt": e.get("felt"),
                "sig": e.get("significance"),
                "status": e.get("status"),
            },
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "metadata": {
            "generated": int(time.time() * 1000),
            "title": "QuakeScope GeoJSON Export",
            "count": len(features),
        },
        "features": features,
    }

