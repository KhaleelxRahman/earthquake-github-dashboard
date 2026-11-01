"""Dashboard HTML generator for QuakeScope.

Loads the production template from `templates/dashboard.html` and securely injects
the validated pre-rendered JSON payload for instant initial render.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

TEMPLATE_PATH = Path(__file__).parent / "templates" / "dashboard.html"


def generate_dashboard_html(
    earthquakes: List[Dict[str, Any]],
    repositories: List[Dict[str, Any]],
    analytics: Dict[str, Any],
    freshness: Dict[str, Any],
) -> str:
    """Render the complete QuakeScope dashboard HTML with embedded initial state."""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Dashboard template not found at {TEMPLATE_PATH.resolve()}")

    template_content = TEMPLATE_PATH.read_text(encoding="utf-8")

    initial_payload = {
        "earthquakes": earthquakes,
        "repositories": repositories,
        "analytics": analytics,
        "freshness": freshness,
    }
    payload_json = json.dumps(initial_payload, ensure_ascii=False)

    # Clean injection into template placeholder
    rendered = template_content.replace("/* QUAKESCOPE_INITIAL_PAYLOAD */", payload_json)
    return rendered
