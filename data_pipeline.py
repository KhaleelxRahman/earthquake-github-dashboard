"""QuakeScope — Global Earthquake Intelligence Data Pipeline.

Fetches global seismic data from the USGS and repository metrics from GitHub,
validates incoming telemetry, computes analytics distributions, and atomically
generates the QuakeScope production dashboard.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import dashboard_template
import quake_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("data_pipeline")

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CACHE_FILE = DATA_DIR / "cache_data.json"
DEFAULT_OUTPUT_FILE = BASE_DIR / "index.html"
SITE_DIR = BASE_DIR / "_site"


def load_cached_data() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Load the verified fallback baseline snapshot from cache."""
    if not CACHE_FILE.exists():
        logger.warning("Cache file %s does not exist.", CACHE_FILE)
        return [], [], {}

    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        earthquakes = data.get("earthquakes", [])
        repositories = data.get("repositories", [])
        freshness = {
            "cached_at": data.get("cached_at"),
            "source": data.get("source", "Offline Cache Snapshot"),
            "is_fallback": True,
        }
        logger.info(
            "Loaded cached baseline with %d earthquakes and %d repositories.",
            len(earthquakes),
            len(repositories),
        )
        return earthquakes, repositories, freshness
    except Exception as exc:
        logger.error("Failed to read cache file %s: %s", CACHE_FILE, exc)
        return [], [], {}


def save_cached_data(earthquakes: List[Dict[str, Any]], repositories: List[Dict[str, Any]]) -> None:
    """Save the latest verified dataset to the cache file."""
    if not earthquakes and not repositories:
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "source": "USGS GeoJSON & GitHub REST API Live Ingestion",
        "earthquakes": earthquakes,
        "repositories": repositories,
    }
    try:
        CACHE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info("Persisted updated snapshot to cache (%s).", CACHE_FILE)
    except Exception as exc:
        logger.warning("Could not persist snapshot to cache: %s", exc)


def validate_output_html(file_path: Path) -> bool:
    """Validate that the generated HTML file is non-empty, well-formed, and contains required data."""
    if not file_path.exists():
        logger.error("Validation failed: file %s does not exist.", file_path)
        return False

    size = file_path.stat().st_size
    if size < 20000:
        logger.error("Validation failed: file size %d bytes is below 20KB threshold.", size)
        return False
    if size > 1500000:
        logger.error("Validation failed: file size %d bytes exceeds 1.5MB safety threshold.", size)
        return False

    try:
        content = file_path.read_text(encoding="utf-8")
        if "</html>" not in content or "QuakeScope" not in content:
            logger.error("Validation failed: missing closing HTML tags or product marker.")
            return False
        if "quakescope-data" not in content:
            logger.error("Validation failed: missing embedded quakescope-data payload.")
            return False
        return True
    except Exception as exc:
        logger.error("Validation failed due to read error: %s", exc)
        return False


def atomic_write_dashboard(html_content: str, destination_path: Path) -> None:
    """Write dashboard HTML atomically to prevent corrupting an existing working dashboard."""
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = destination_path.with_suffix(".html.tmp")

    try:
        tmp_path.write_text(html_content, encoding="utf-8")
        if not validate_output_html(tmp_path):
            raise ValueError(f"Temporary output failed integrity validation: {tmp_path}")

        # Atomic replacement
        if destination_path.exists() and destination_path.resolve() == DEFAULT_OUTPUT_FILE.resolve():
            # Create a backup of the previous good root file
            bak_path = destination_path.with_suffix(".html.bak")
            try:
                shutil.copy2(destination_path, bak_path)
            except Exception:
                pass

        # Atomic rename
        os.replace(tmp_path, destination_path)
        logger.info("Atomically updated dashboard at %s (%d bytes).", destination_path, destination_path.stat().st_size)

    except Exception as exc:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise RuntimeError(f"Atomic write to {destination_path} failed: {exc}") from exc


def run_pipeline(
    feed_key: str = "4.5_week",
    output_dir: Optional[Path] = None,
    github_token: Optional[str] = None,
    google_maps_api_key: Optional[str] = None,
    offline_mode: bool = False,
) -> int:
    """Execute the full data pipeline and generate the dashboard."""
    logger.info("Initializing QuakeScope pipeline execution.")
    token = github_token or os.environ.get("GITHUB_TOKEN")
    gmaps_key = (google_maps_api_key or os.environ.get("GOOGLE_MAPS_API_KEY", "")).strip()

    earthquakes: List[Dict[str, Any]] = []
    repositories: List[Dict[str, Any]] = []
    usgs_status = "live"
    github_status = "live"

    if offline_mode:
        logger.info("Offline mode requested; skipping network ingestion.")
        cached_eq, cached_repo, _ = load_cached_data()
        earthquakes = cached_eq
        repositories = cached_repo
        usgs_status = "offline_cache"
        github_status = "offline_cache"
    else:
        # Ingest USGS with EMSC secondary fallback
        raw_usgs, usgs_err = quake_service.fetch_earthquakes_raw(feed_key)
        if raw_usgs and usgs_err == "OK":
            earthquakes = quake_service.parse_earthquake_features(raw_usgs)
        else:
            logger.warning("USGS live fetch failed (%s); attempting EMSC secondary fallback.", usgs_err)
            raw_emsc, emsc_err = quake_service.fetch_emsc_earthquakes_raw()
            if raw_emsc and emsc_err == "OK":
                earthquakes = quake_service.parse_emsc_features(raw_emsc)
                usgs_status = "live_emsc_fallback"
            else:
                logger.warning("EMSC fallback also failed (%s); falling back to cached baseline.", emsc_err)
                cached_eq, _, _ = load_cached_data()
                earthquakes = cached_eq
                usgs_status = f"fallback ({usgs_err})"

        # Ingest GitHub
        raw_github, github_err = quake_service.fetch_top_repositories_raw(token)
        if raw_github and github_err == "OK":
            repositories = quake_service.parse_repository_items(raw_github)
        else:
            logger.warning("GitHub live fetch failed (%s); falling back to cached baseline.", github_err)
            _, cached_repo, _ = load_cached_data()
            repositories = cached_repo
            github_status = f"fallback ({github_err})"

        # If live ingestion succeeded, update cache
        if usgs_status == "live" and github_status == "live" and earthquakes and repositories:
            save_cached_data(earthquakes, repositories)

    # Protection against empty pipeline output (DEF-01)
    if not earthquakes and not repositories:
        cached_eq, cached_repo, _ = load_cached_data()
        if cached_eq or cached_repo:
            logger.warning("Using cached baseline to safeguard against empty dashboard.")
            earthquakes = cached_eq
            repositories = cached_repo
            usgs_status = "cache_emergency"
            github_status = "cache_emergency"
        else:
            logger.critical("No earthquake or repository data available. Aborting build to protect dashboard.")
            return 1

    # Analytics calculation
    analytics = quake_service.calculate_analytics(earthquakes)

    # Freshness metadata
    freshness = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "usgs_feed": feed_key,
        "usgs_status": usgs_status,
        "github_status": github_status,
        "earthquake_count": len(earthquakes),
        "repository_count": len(repositories),
    }

    # Render HTML template
    logger.info("Generating production HTML with %d events and %d repositories.", len(earthquakes), len(repositories))
    html_output = dashboard_template.generate_dashboard_html(
        earthquakes=earthquakes,
        repositories=repositories,
        analytics=analytics,
        freshness=freshness,
        config={"googleMapsApiKey": gmaps_key},
    )

    # Determine targets
    target_files = [DEFAULT_OUTPUT_FILE]
    if output_dir:
        target_files.append(output_dir / "index.html")
    else:
        # Also mirror into _site/ if _site exists or is used for CI
        target_files.append(SITE_DIR / "index.html")

    for target in target_files:
        atomic_write_dashboard(html_output, target)
        target_dir = target.parent
        # Copy static assets if target is not the project root
        if target_dir.resolve() != BASE_DIR.resolve():
            for asset in ("favicon.ico", "favicon.svg"):
                asset_src = BASE_DIR / asset
                if asset_src.exists():
                    try:
                        shutil.copy2(asset_src, target_dir / asset)
                    except Exception as exc:
                        logger.warning("Could not copy asset %s to %s: %s", asset, target_dir, exc)

    logger.info("Pipeline completed successfully.")
    return 0


def main() -> None:
    """CLI entry point for QuakeScope data pipeline."""
    parser = argparse.ArgumentParser(description="QuakeScope Global Earthquake Intelligence Pipeline.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional destination directory for index.html (e.g. _site)",
    )
    parser.add_argument(
        "--feed",
        type=str,
        default="4.5_week",
        choices=["4.5_week", "2.5_week", "all_week", "4.5_day", "4.5_month"],
        help="USGS GeoJSON feed identifier",
    )
    parser.add_argument(
        "--google-maps-key",
        type=str,
        default=None,
        help="Optional Google Maps JavaScript API key for interactive map features",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run in offline mode using cached baseline",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the existing index.html without modifying it",
    )

    args = parser.parse_args()

    if args.validate_only:
        valid = validate_output_html(DEFAULT_OUTPUT_FILE)
        if valid:
            logger.info("Validation passed for %s.", DEFAULT_OUTPUT_FILE)
            sys.exit(0)
        else:
            logger.error("Validation failed for %s.", DEFAULT_OUTPUT_FILE)
            sys.exit(1)

    exit_code = run_pipeline(
        feed_key=args.feed,
        output_dir=args.output_dir,
        google_maps_api_key=args.google_maps_key,
        offline_mode=args.offline,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
