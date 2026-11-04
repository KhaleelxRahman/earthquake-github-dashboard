"""Unit tests for QuakeScope seismology calculation engine."""

import math
import unittest

from seismology import (
    calculate_b_value,
    calculate_cumulative_energy,
    calculate_energy_joules,
    calculate_energy_tnt_tons,
    classify_depth,
    detect_aftershock_clusters,
    find_nearest_plate_boundary,
    haversine_distance_km,
)


class TestSeismologyEngine(unittest.TestCase):
    """Test mathematical and physical accuracy of seismological formulas."""

    def test_energy_scaling_ratio(self):
        """Verify that a 2.0 unit magnitude increase corresponds to 1000x radiated energy."""
        e_m5 = calculate_energy_joules(5.0)
        e_m7 = calculate_energy_joules(7.0)
        ratio = e_m7 / e_m5
        self.assertAlmostEqual(ratio, 1000.0, places=1)

    def test_energy_joules_formula(self):
        """Verify exact calculation against Gutenberg-Richter formula for M=4.0."""
        # log10(E) = 4.8 + 1.5 * 4.0 = 10.8 => E = 10^10.8
        expected = 10.0 ** 10.8
        actual = calculate_energy_joules(4.0)
        self.assertAlmostEqual(actual, expected, places=2)

    def test_energy_tnt_conversion(self):
        """Verify TNT tonnage calculation."""
        # 1 ton of TNT = 4.184e9 Joules
        joules = calculate_energy_joules(5.0)
        expected_tnt = joules / 4.184e9
        actual_tnt = calculate_energy_tnt_tons(5.0)
        self.assertAlmostEqual(actual_tnt, expected_tnt, places=4)

    def test_cumulative_energy(self):
        """Verify cumulative energy summation across multiple events."""
        mags = [5.0, 5.0, 6.0]
        total_joules, total_tnt = calculate_cumulative_energy(mags)
        expected_joules = 2 * calculate_energy_joules(5.0) + calculate_energy_joules(6.0)
        self.assertAlmostEqual(total_joules, expected_joules, places=2)
        self.assertAlmostEqual(total_tnt, expected_joules / 4.184e9, places=4)

    def test_b_value_aki_estimator(self):
        """Verify Aki's maximum likelihood b-value estimation."""
        # Create a synthetic distribution with mean magnitude ~ 4.93 for Mmin=4.5
        # Expected b ~ 1.0
        # If b = 1.0, denominator = 0.43429 => mean_M - (4.5 - 0.05) = 0.43429 => mean_M = 4.88429
        # Let's provide a set of magnitudes with exact mean:
        mags = [4.5, 4.6, 4.7, 4.8, 4.9, 5.0, 5.2, 5.5, 6.0] * 10
        b_val, std_err, count = calculate_b_value(mags, min_magnitude=4.5, delta_m=0.1)
        self.assertIsNotNone(b_val)
        self.assertIsNotNone(std_err)
        self.assertEqual(count, 90)
        self.assertTrue(0.7 <= b_val <= 1.4)
        self.assertTrue(std_err > 0)

    def test_b_value_insufficient_sample(self):
        """Verify b-value returns None when fewer than 5 events are present."""
        mags = [5.0, 5.1, 5.2]
        b_val, std_err, count = calculate_b_value(mags, min_magnitude=4.5)
        self.assertIsNone(b_val)
        self.assertIsNone(std_err)
        self.assertEqual(count, 3)

    def test_depth_classification(self):
        """Verify standard IASPEI depth stratification."""
        self.assertEqual(classify_depth(10.5), "Shallow")
        self.assertEqual(classify_depth(69.9), "Shallow")
        self.assertEqual(classify_depth(70.0), "Intermediate")
        self.assertEqual(classify_depth(299.9), "Intermediate")
        self.assertEqual(classify_depth(300.0), "Deep")
        self.assertEqual(classify_depth(650.0), "Deep")
        self.assertEqual(classify_depth(float("nan")), "Unknown")

    def test_haversine_distance(self):
        """Verify geodesic haversine calculation."""
        # London to Paris is ~343-344 km
        dist = haversine_distance_km(51.5074, -0.1278, 48.8566, 2.3522)
        self.assertTrue(340.0 <= dist <= 346.0)

        # Distance between same coordinates is 0
        self.assertAlmostEqual(haversine_distance_km(35.0, 139.0, 35.0, 139.0), 0.0, places=4)

    def test_detect_aftershock_clusters(self):
        """Verify temporal-spatial aftershock clustering."""
        base_time = 1700000000000  # ms
        records = [
            # Mainshock M6.5 in Southern California
            {
                "id": "mainshock-1",
                "magnitude": 6.5,
                "latitude": 34.0,
                "longitude": -118.0,
                "time_ms": base_time,
            },
            # Aftershock 1: 15 km away, 3 hours later
            {
                "id": "aftershock-1a",
                "magnitude": 4.5,
                "latitude": 34.1,
                "longitude": -118.1,
                "time_ms": base_time + 3 * 3600 * 1000,
            },
            # Aftershock 2: 25 km away, 12 hours later
            {
                "id": "aftershock-1b",
                "magnitude": 4.2,
                "latitude": 33.9,
                "longitude": -118.2,
                "time_ms": base_time + 12 * 3600 * 1000,
            },
            # Unrelated event: in Japan, 1 hour later
            {
                "id": "japan-event",
                "magnitude": 5.0,
                "latitude": 35.5,
                "longitude": 139.5,
                "time_ms": base_time + 1 * 3600 * 1000,
            },
        ]
        clusters = detect_aftershock_clusters(records, mainshock_min_mag=6.0, max_radius_km=75.0)
        self.assertIn("mainshock-1", clusters)
        self.assertIn("aftershock-1a", clusters["mainshock-1"])
        self.assertIn("aftershock-1b", clusters["mainshock-1"])
        self.assertNotIn("japan-event", clusters["mainshock-1"])

    def test_nearest_plate_boundary(self):
        """Verify plate boundary lookup against sample feature."""
        plate_features = [
            {
                "type": "Feature",
                "properties": {"name": "San Andreas Fault", "code": "SAF"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-120.0, 36.0], [-119.0, 35.0], [-118.0, 34.0]],
                },
            }
        ]
        name, dist = find_nearest_plate_boundary(35.0, -119.0, plate_features)
        self.assertEqual(name, "San Andreas Fault")
        self.assertAlmostEqual(dist, 0.0, places=1)


if __name__ == "__main__":
    unittest.main()

