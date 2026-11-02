"""Unit and regression tests for QuakeScope core service.

Executable with standard `unittest` without external dependencies,
and compatible with `pytest`.
"""

import unittest
from unittest.mock import MagicMock, patch

from quake_service import (
    calculate_analytics,
    export_records_to_csv,
    export_records_to_geojson,
    parse_earthquake_features,
    parse_repository_items,
    request_with_retry,
    sanitize_text,
    sanitize_url,
    validate_coordinates,
    validate_magnitude,
)


class TestValidationAndSanitization(unittest.TestCase):
    """Test data sanitization and boundary checking."""

    def test_sanitize_url(self):
        self.assertEqual(
            sanitize_url("https://earthquake.usgs.gov/event/123"),
            "https://earthquake.usgs.gov/event/123",
        )
        self.assertEqual(sanitize_url("http://example.com/item"), "http://example.com/item")
        self.assertEqual(sanitize_url("javascript:alert(1)"), "")
        self.assertEqual(sanitize_url("data:text/html,<html>"), "")
        self.assertEqual(sanitize_url(""), "")
        self.assertEqual(sanitize_url(None), "")
        self.assertEqual(sanitize_url("not a url"), "")

    def test_sanitize_text(self):
        self.assertEqual(sanitize_text("Hello World"), "Hello World")
        self.assertEqual(
            sanitize_text("<script>alert('xss')</script>"),
            "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;",
        )
        self.assertEqual(sanitize_text(None, default="fallback"), "fallback")
        self.assertEqual(sanitize_text("", default="default_val"), "default_val")

    def test_validate_coordinates(self):
        # Valid
        valid, lat, lon, depth, msg = validate_coordinates(35.6895, 139.6917, 10.5)
        self.assertTrue(valid)
        self.assertEqual(lat, 35.6895)
        self.assertEqual(lon, 139.6917)
        self.assertEqual(depth, 10.5)

        # Latitude out of bounds
        valid, _, _, _, msg = validate_coordinates(95.0, 10.0, 5.0)
        self.assertFalse(valid)
        self.assertIn("Latitude", msg)

        # Longitude out of bounds
        valid, _, _, _, msg = validate_coordinates(0.0, -195.0, 5.0)
        self.assertFalse(valid)
        self.assertIn("Longitude", msg)

        # Non-numeric
        valid, _, _, _, msg = validate_coordinates("invalid", 10.0, 5.0)
        self.assertFalse(valid)

        # NaN / Infinity
        valid, _, _, _, _ = validate_coordinates(float("nan"), 10.0, 5.0)
        self.assertFalse(valid)
        valid, _, _, _, _ = validate_coordinates(0.0, float("inf"), 5.0)
        self.assertFalse(valid)

    def test_validate_magnitude(self):
        # Valid
        valid, mag, _ = validate_magnitude("5.4")
        self.assertTrue(valid)
        self.assertEqual(mag, 5.4)

        # Out of bounds
        valid, _, msg = validate_magnitude(15.0)
        self.assertFalse(valid)

        # Non-numeric
        valid, _, _ = validate_magnitude("bad_mag")
        self.assertFalse(valid)

        # NaN
        valid, _, _ = validate_magnitude(float("nan"))
        self.assertFalse(valid)


class TestEarthquakeParsing(unittest.TestCase):
    """Test USGS GeoJSON feature parsing and error handling."""

    def setUp(self):
        self.sample_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": "us6000test1",
                    "properties": {
                        "mag": 6.2,
                        "place": "120 km W of Tokyo, Japan",
                        "time": 1700000000000,
                        "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us6000test1",
                        "felt": 45,
                        "tsunami": 0,
                        "sig": 580,
                        "status": "reviewed",
                        "magType": "mww",
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [139.5, 35.5, 25.0],
                    },
                },
                {
                    "type": "Feature",
                    "id": "us6000test2",
                    "properties": {
                        "mag": 4.8,
                        "place": "Central Chile",
                        "time": 1700000050000,
                        "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us6000test2",
                        "felt": None,
                        "tsunami": 1,
                        "sig": 350,
                        "status": "reviewed",
                        "magType": "mb",
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-71.2, -33.1, 45.0],
                    },
                },
            ],
        }

    def test_parse_valid_features(self):
        records = parse_earthquake_features(self.sample_geojson)
        self.assertEqual(len(records), 2)
        # Should be ordered descending by time
        self.assertEqual(records[0]["id"], "us6000test2")
        self.assertEqual(records[0]["magnitude"], 4.8)
        self.assertEqual(records[0]["tsunami"], 1)

        self.assertEqual(records[1]["id"], "us6000test1")
        self.assertEqual(records[1]["magnitude"], 6.2)
        self.assertEqual(records[1]["depth_km"], 25.0)

    def test_parse_empty_features(self):
        records = parse_earthquake_features({"type": "FeatureCollection", "features": []})
        self.assertEqual(records, [])

    def test_parse_malformed_features(self):
        malformed = {
            "type": "FeatureCollection",
            "features": [
                None,  # Not a dict
                {"properties": None, "geometry": None},  # Missing objects
                {  # Invalid coords
                    "id": "bad_coords",
                    "properties": {"mag": 5.0, "time": 1700000000000},
                    "geometry": {"coordinates": [999.0, 999.0, 0.0]},
                },
                {  # Missing magnitude
                    "id": "no_mag",
                    "properties": {"mag": None, "time": 1700000000000},
                    "geometry": {"coordinates": [10.0, 10.0, 10.0]},
                },
            ],
        }
        records = parse_earthquake_features(malformed)
        self.assertEqual(len(records), 0)

    def test_duplicate_prevention(self):
        duped = {
            "features": [
                {
                    "id": "same_id",
                    "properties": {"mag": 5.0, "time": 1000, "place": "Place 1"},
                    "geometry": {"coordinates": [0.0, 0.0, 10.0]},
                },
                {
                    "id": "same_id",
                    "properties": {"mag": 5.5, "time": 2000, "place": "Place 2"},
                    "geometry": {"coordinates": [1.0, 1.0, 10.0]},
                },
            ]
        }
        records = parse_earthquake_features(duped)
        self.assertEqual(len(records), 1)

    def test_parse_scientific_provenance_fields(self):
        """Verify ingestion of official USGS scientific fields (MMI, CDI, PAGER alert, network)."""
        data = {
            "features": [
                {
                    "id": "us7000test_sci",
                    "properties": {
                        "mag": 7.1,
                        "place": "Offshore Honshu, Japan",
                        "time": 1700000100000,
                        "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us7000test_sci",
                        "felt": 1250,
                        "cdi": 6.8,
                        "mmi": 7.4,
                        "alert": "yellow",
                        "status": "reviewed",
                        "net": "us",
                        "magType": "mww",
                        "tsunami": 1,
                        "sig": 890,
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [142.3, 38.2, 32.0],
                    },
                }
            ]
        }
        records = parse_earthquake_features(data)
        self.assertEqual(len(records), 1)
        r = records[0]
        self.assertEqual(r["mmi"], 7.4)
        self.assertEqual(r["cdi"], 6.8)
        self.assertEqual(r["alert"], "yellow")
        self.assertEqual(r["status"], "reviewed")
        self.assertEqual(r["net"], "us")
        self.assertEqual(r["mag_type"], "mww")
        self.assertEqual(r["felt"], 1250)
        self.assertEqual(r["tsunami"], 1)

    def test_parse_scientific_fields_edge_cases(self):
        """Verify handling of missing, null, or out-of-range scientific values."""
        data = {
            "features": [
                {
                    "id": "us_missing_fields",
                    "properties": {
                        "mag": 5.0,
                        "place": "Aleutian Islands",
                        "time": 1700000200000,
                        "felt": None,
                        "cdi": None,
                        "mmi": None,
                        "alert": None,
                        "magType": None,
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-175.0, 52.0, 15.0],
                    },
                },
                {
                    "id": "us_invalid_ranges",
                    "properties": {
                        "mag": 5.2,
                        "place": "Mid-Atlantic Ridge",
                        "time": 1700000300000,
                        "mmi": 99.0,  # Out of range (>12.0)
                        "cdi": -5.0,  # Negative
                        "alert": "invalid_color_alert",  # Unknown PAGER alert
                        "felt": -10,  # Negative felt reports
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [-25.0, 10.0, 10.0],
                    },
                },
            ]
        }
        records = parse_earthquake_features(data)
        self.assertEqual(len(records), 2)
        # Check missing fields record
        r_missing = next(x for x in records if x["id"] == "us_missing_fields")
        self.assertIsNone(r_missing["mmi"])
        self.assertIsNone(r_missing["cdi"])
        self.assertIsNone(r_missing["alert"])
        self.assertIsNone(r_missing["felt"])
        self.assertEqual(r_missing["mag_type"], "")

        # Check invalid ranges record
        r_invalid = next(x for x in records if x["id"] == "us_invalid_ranges")
        self.assertIsNone(r_invalid["mmi"])
        self.assertIsNone(r_invalid["cdi"])
        self.assertIsNone(r_invalid["alert"])
        self.assertIsNone(r_invalid["felt"])


class TestRepositoryParsing(unittest.TestCase):
    """Test GitHub repository response parsing."""

    def test_parse_valid_repositories(self):
        data = {
            "items": [
                {
                    "name": "cpython",
                    "full_name": "python/cpython",
                    "stargazers_count": 60000,
                    "forks_count": 30000,
                    "description": "The Python programming language",
                    "html_url": "https://github.com/python/cpython",
                    "language": "Python",
                    "updated_at": "2026-10-30T12:00:00Z",
                },
                {
                    "name": "flask",
                    "full_name": "pallets/flask",
                    "stargazers_count": 68000,
                    "forks_count": 16000,
                    "description": "The Python micro framework for building web applications",
                    "html_url": "https://github.com/pallets/flask",
                    "language": "Python",
                    "updated_at": "2026-10-29T10:00:00Z",
                },
            ]
        }
        repos = parse_repository_items(data)
        self.assertEqual(len(repos), 2)
        # Should be sorted descending by stars
        self.assertEqual(repos[0]["name"], "flask")
        self.assertEqual(repos[0]["stars"], 68000)
        self.assertEqual(repos[1]["name"], "cpython")

    def test_parse_malformed_repositories(self):
        data = {
            "items": [
                {"name": None, "stargazers_count": 100},
                {"name": "missing_stars", "stargazers_count": None},
                "not_a_dict",
            ]
        }
        repos = parse_repository_items(data)
        self.assertEqual(len(repos), 0)


class TestAnalyticsAndExport(unittest.TestCase):
    """Test statistics calculation and export formatting."""

    def setUp(self):
        self.records = [
            {
                "id": "eq1",
                "place": "Near Coast of Peru",
                "magnitude": 6.5,
                "time_ms": 1700000000000,
                "time_iso": "2023-11-14T22:13:20+00:00",
                "latitude": -12.5,
                "longitude": -77.2,
                "depth_km": 20.0,
                "url": "https://earthquake.usgs.gov/eq1",
                "felt": 120,
                "tsunami": 1,
                "significance": 620,
                "status": "reviewed",
                "mag_type": "mww",
            },
            {
                "id": "eq2",
                "place": "Southern Alaska",
                "magnitude": 4.6,
                "time_ms": 1700003600000,
                "time_iso": "2023-11-14T23:13:20+00:00",
                "latitude": 61.2,
                "longitude": -149.8,
                "depth_km": 110.0,
                "url": "https://earthquake.usgs.gov/eq2",
                "felt": 10,
                "tsunami": 0,
                "significance": 320,
                "status": "reviewed",
                "mag_type": "ml",
            },
        ]

    def test_calculate_analytics(self):
        stats = calculate_analytics(self.records)
        self.assertEqual(stats["total_count"], 2)
        self.assertEqual(stats["max_magnitude"], 6.5)
        self.assertEqual(stats["avg_magnitude"], 5.55)
        self.assertEqual(stats["strong_count"], 1)  # mag >= 5.0
        self.assertEqual(stats["major_count"], 1)   # mag >= 6.0
        self.assertEqual(stats["shallow_count"], 1) # depth < 70km
        self.assertEqual(stats["intermediate_count"], 1) # 70-300km
        self.assertEqual(stats["tsunami_alerts"], 1)

    def test_analytics_empty_records(self):
        stats = calculate_analytics([])
        self.assertEqual(stats["total_count"], 0)
        self.assertEqual(stats["max_magnitude"], 0.0)
        self.assertEqual(stats["avg_magnitude"], 0.0)

    def test_export_to_csv(self):
        csv_str = export_records_to_csv(self.records)
        lines = csv_str.strip().split("\n")
        self.assertEqual(len(lines), 3)
        self.assertIn("Near Coast of Peru", lines[1])
        self.assertIn("6.5", lines[1])
        self.assertIn("Southern Alaska", lines[2])

    def test_export_to_geojson(self):
        geojson_dict = export_records_to_geojson(self.records)
        self.assertEqual(geojson_dict["type"], "FeatureCollection")
        self.assertEqual(len(geojson_dict["features"]), 2)
        feat0 = geojson_dict["features"][0]
        self.assertEqual(feat0["geometry"]["coordinates"], [-77.2, -12.5, 20.0])
        self.assertEqual(feat0["properties"]["mag"], 6.5)


class TestRetryAndNetwork(unittest.TestCase):
    """Test retry mechanism with mocks."""

    @patch("requests.get")
    def test_retry_on_500_error(self, mock_get):
        # First two fail with 500, third succeeds with 200
        mock_fail = MagicMock()
        mock_fail.status_code = 500
        mock_fail.raise_for_status.side_effect = Exception("Internal Server Error")

        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {"status": "ok"}

        mock_get.side_effect = [mock_fail, mock_fail, mock_success]

        resp = request_with_retry("https://api.example.com", backoff_factor=0.01)
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_get.call_count, 3)


if __name__ == "__main__":
    unittest.main()

