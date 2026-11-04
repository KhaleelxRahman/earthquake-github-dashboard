"""Scientific Seismology Calculation Engine for QuakeScope.

Implements standard empirical seismological formulations:
1. Aki's (1965) Maximum Likelihood Estimator for Gutenberg-Richter b-value.
2. Gutenberg-Richter (1956) Seismic Radiated Energy (Joules & TNT metric tons).
3. Hypocentral depth classification (IASPEI standard).
4. Spatial-temporal clustering heuristics for aftershock identification.
5. Geodesic distance calculation to Peter Bird (2003) tectonic plate boundaries.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

# Physical & Seismological Constants
LOG10_E = math.log10(math.e)  # ~0.4342944819032518
JOULES_PER_TON_TNT = 4.184e9  # 1 ton of TNT = 4.184 GJ
EARTH_RADIUS_KM = 6371.0088   # IUGG Mean Earth Radius


def calculate_energy_joules(magnitude: float) -> float:
    """Calculate seismic radiated energy in Joules using Gutenberg-Richter (1956).

    Formula: log10(E) = 4.8 + 1.5 * M  =>  E = 10 ** (4.8 + 1.5 * M)
    """
    if magnitude is None or math.isnan(magnitude) or math.isinf(magnitude):
        return 0.0
    # Bound magnitude to avoid float overflow on corrupted data
    clamped_mag = max(-2.0, min(float(magnitude), 10.5))
    return 10.0 ** (4.8 + 1.5 * clamped_mag)


def calculate_energy_tnt_tons(magnitude: float) -> float:
    """Convert seismic radiated energy to equivalent metric tons of TNT."""
    joules = calculate_energy_joules(magnitude)
    return joules / JOULES_PER_TON_TNT


def calculate_cumulative_energy(magnitudes: List[float]) -> Tuple[float, float]:
    """Calculate cumulative radiated energy in Joules and equivalent TNT tons."""
    total_joules = 0.0
    for m in magnitudes:
        if m is not None and not math.isnan(m) and not math.isinf(m):
            total_joules += calculate_energy_joules(m)
    total_tnt = total_joules / JOULES_PER_TON_TNT
    return total_joules, total_tnt


def calculate_b_value(
    magnitudes: List[float],
    min_magnitude: Optional[float] = None,
    delta_m: float = 0.1,
) -> Tuple[Optional[float], Optional[float], int]:
    """Estimate the Gutenberg-Richter b-value using Aki's (1965) Maximum Likelihood method.

    DISCLAIMER:
        This metric is strictly exploratory and descriptive of observed historical magnitude
        frequency distributions. It does NOT predict earthquake occurrence, calculate fault
        rupture probability, or constitute an official seismological forecast.

    Parameters:
        magnitudes: List of observed earthquake magnitudes.
        min_magnitude: Completeness threshold (M_c). If omitted, defaults to min(magnitudes).
        delta_m: Magnitude binning interval (default 0.1 for USGS catalog precision).

    Formula (Aki 1965):
        b = log10(e) / (mean_M - (M_min - delta_m / 2))

    Standard error (Shi & Bolt 1982):
        sigma_b = b / sqrt(N)

    Returns:
        (b_value, standard_error, count_used)
        Returns (None, None, count) if sample size N < 15, documenting data insufficiency.
    """
    valid_mags = [
        float(m) for m in magnitudes
        if m is not None and not math.isnan(m) and not math.isinf(m)
    ]
    if not valid_mags:
        return None, None, 0

    if min_magnitude is None:
        # Default completeness threshold to min magnitude present
        min_magnitude = min(valid_mags)

    m_filtered = [m for m in valid_mags if m >= min_magnitude]
    n = len(m_filtered)
    if n < 15:
        # Insufficient sample size for statistically robust Aki b-value estimation (requires N >= 15)
        return None, None, n

    mean_m = sum(m_filtered) / n
    denominator = mean_m - (min_magnitude - (delta_m / 2.0))
    if denominator <= 1e-6:
        return None, None, n

    b_val = LOG10_E / denominator
    std_err = b_val / math.sqrt(n)

    return round(b_val, 3), round(std_err, 3), n


def classify_depth(depth_km: float) -> str:
    """Classify hypocenter depth into standard IASPEI tiers."""
    if depth_km is None or math.isnan(depth_km) or math.isinf(depth_km):
        return "Unknown"
    d = float(depth_km)
    if d < 70.0:
        return "Shallow"
    elif d < 300.0:
        return "Intermediate"
    else:
        return "Deep"


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda / 2.0) ** 2))
    a = min(1.0, max(0.0, a))  # Numerical clamp
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c


def find_nearest_plate_boundary(
    lat: float,
    lon: float,
    plate_features: List[Dict[str, Any]],
) -> Tuple[Optional[str], Optional[float]]:
    """Find the nearest tectonic plate boundary and the geodesic distance in kilometers."""
    if not plate_features:
        return None, None

    nearest_name: Optional[str] = None
    min_dist: float = float("inf")

    for feature in plate_features:
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        name = properties.get("name") or properties.get("code") or "Tectonic Boundary"
        geom_type = geometry.get("type")
        coords = geometry.get("coordinates", [])

        # Process LineString or MultiLineString
        line_segments: List[List[List[float]]] = []
        if geom_type == "LineString":
            line_segments.append(coords)
        elif geom_type == "MultiLineString":
            line_segments.extend(coords)

        for line in line_segments:
            for pt in line:
                if len(pt) >= 2:
                    p_lon, p_lat = pt[0], pt[1]
                    dist = haversine_distance_km(lat, lon, p_lat, p_lon)
                    if dist < min_dist:
                        min_dist = dist
                        nearest_name = name

    if nearest_name is not None:
        return nearest_name, round(min_dist, 1)
    return None, None


def detect_aftershock_clusters(
    records: List[Dict[str, Any]],
    mainshock_min_mag: float = 5.5,
    max_radius_km: float = 75.0,
    max_time_window_hours: float = 72.0,
) -> Dict[str, List[str]]:
    """Identify secondary aftershocks associated with significant mainshocks.

    DISCLAIMER:
        This function uses a simple descriptive spatial-temporal proximity window heuristic
        (modified Gardner-Knopoff window). It is intended strictly for exploratory event grouping.
        It does NOT compute physical Coulomb stress transfer, model Omori-Utsu decay parameters,
        or generate an official aftershock probability forecast.

    Returns a mapping of {mainshock_id: [aftershock_id_1, aftershock_id_2, ...]}.
    """
    clusters: Dict[str, List[str]] = {}
    time_window_ms = max_time_window_hours * 3600.0 * 1000.0

    # Sort ascending by time to preserve causality
    sorted_recs = sorted(records, key=lambda r: r.get("time_ms", 0))

    mainshocks = [
        r for r in sorted_recs
        if r.get("magnitude") is not None and r["magnitude"] >= mainshock_min_mag
    ]

    for ms in mainshocks:
        ms_id = ms.get("id")
        if not ms_id:
            continue
        ms_time = ms.get("time_ms", 0)
        ms_lat = ms.get("latitude")
        ms_lon = ms.get("longitude")
        ms_mag = ms.get("magnitude", 0.0)

        if ms_lat is None or ms_lon is None:
            continue

        aftershocks: List[str] = []
        for other in sorted_recs:
            other_id = other.get("id")
            if other_id == ms_id:
                continue
            other_time = other.get("time_ms", 0)
            other_lat = other.get("latitude")
            other_lon = other.get("longitude")
            other_mag = other.get("magnitude", 0.0)

            # Causality check: must occur after mainshock, within time window
            dt = other_time - ms_time
            if 0 < dt <= time_window_ms:
                # Aftershocks must be smaller than mainshock
                if other_mag < ms_mag and other_lat is not None and other_lon is not None:
                    dist = haversine_distance_km(ms_lat, ms_lon, other_lat, other_lon)
                    if dist <= max_radius_km:
                        aftershocks.append(other_id)

        if aftershocks:
            clusters[ms_id] = aftershocks

    return clusters

