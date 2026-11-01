"""Integration and reliability tests for QuakeScope data pipeline."""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data_pipeline import (
    atomic_write_dashboard,
    run_pipeline,
    validate_output_html,
)


class TestPipelineReliability(unittest.TestCase):
    """Test pipeline reliability, atomic writing, and validation gates."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="quakescope_test_"))
        self.dest_file = self.test_dir / "index.html"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_validate_output_html_valid(self):
        valid_html = """<!doctype html>
<html>
<head><title>QuakeScope — Global Earthquake Intelligence</title></head>
<body>
  <h1>QuakeScope</h1>
  <script id="quakescope-data">{"earthquakes": []}</script>
</body>
</html>
""" + ("<!-- padding to meet 20KB threshold -->\n" * 600)

        self.dest_file.write_text(valid_html, encoding="utf-8")
        self.assertTrue(validate_output_html(self.dest_file))

    def test_validate_output_html_too_small(self):
        small_html = "<html><body>QuakeScope</body></html>"
        self.dest_file.write_text(small_html, encoding="utf-8")
        self.assertFalse(validate_output_html(self.dest_file))

    def test_validate_output_html_missing_marker(self):
        no_marker = ("<div>Large content without closing tags</div>\n" * 800)
        self.dest_file.write_text(no_marker, encoding="utf-8")
        self.assertFalse(validate_output_html(self.dest_file))

    def test_atomic_write_preserves_target_on_failure(self):
        # Create an existing good file
        original_content = "ORIGINAL_GOOD_CONTENT_PLACEHOLDER"
        self.dest_file.write_text(original_content, encoding="utf-8")

        # Attempt to write invalid short HTML content (fails validation)
        invalid_short_content = "invalid"
        with self.assertRaises(RuntimeError):
            atomic_write_dashboard(invalid_short_content, self.dest_file)

        # Original content must remain intact!
        self.assertEqual(self.dest_file.read_text(encoding="utf-8"), original_content)
        # Temporary file must be cleaned up
        tmp_file = self.dest_file.with_suffix(".html.tmp")
        self.assertFalse(tmp_file.exists())

    def test_run_pipeline_offline_mode(self):
        output_dir = self.test_dir / "out"
        code = run_pipeline(output_dir=output_dir, offline_mode=True)
        self.assertEqual(code, 0)
        out_html = output_dir / "index.html"
        self.assertTrue(out_html.exists())
        self.assertGreater(out_html.stat().st_size, 30000)

    @patch("data_pipeline.load_cached_data")
    @patch("quake_service.fetch_earthquakes_raw")
    @patch("quake_service.fetch_top_repositories_raw")
    def test_empty_pipeline_fails_safely(self, mock_repos, mock_quakes, mock_cache):
        # Everything returns empty / failure
        mock_quakes.return_value = (None, "Network failure")
        mock_repos.return_value = (None, "Rate limit")
        mock_cache.return_value = ([], [], {})

        code = run_pipeline(output_dir=self.test_dir, offline_mode=False)
        # Must return exit code 1 to abort and protect existing deployment!
        self.assertEqual(code, 1)

    def test_template_javascript_syntax_valid(self):
        """Regression test: verify all inline JavaScript in template is syntactically valid."""
        import re
        import subprocess

        template_path = Path(__file__).parent.parent / "templates" / "dashboard.html"
        self.assertTrue(template_path.exists())
        content = template_path.read_text(encoding="utf-8")

        pattern = re.compile(
            r'<script(?![^>]*type=["\']application/json["\'])[^>]*>(.*?)</script>',
            re.DOTALL | re.IGNORECASE,
        )
        scripts = pattern.findall(content)
        self.assertGreater(len(scripts), 0, "No executable script blocks found in template")

        for idx, script_body in enumerate(scripts, 1):
            code = script_body.strip()
            if not code:
                continue
            proc = subprocess.run(
                ["node", "--check"],
                input=code,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(
                proc.returncode,
                0,
                f"Syntax error in script block #{idx}:\n{proc.stderr.strip()}",
            )

    def test_production_build_copies_assets(self):
        """Verify production build creates index.html and copies static assets."""
        out_dir = self.test_dir / "site_out"
        code = run_pipeline(output_dir=out_dir, offline_mode=True)
        self.assertEqual(code, 0)
        self.assertTrue((out_dir / "index.html").exists())
        self.assertTrue((out_dir / "favicon.ico").exists())
        self.assertTrue((out_dir / "favicon.svg").exists())


if __name__ == "__main__":
    unittest.main()

