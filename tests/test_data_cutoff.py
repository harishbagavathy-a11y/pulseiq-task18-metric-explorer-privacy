"""Test Suite: Data Cut-off Date & Metadata Verification
Verifies that the audited warehouse data cut-off date is present, properly formatted,
and matches the latest operating period.
"""

import json
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
METADATA_PATH = PROJECT_ROOT / "data" / "metadata.json"
APP_PATH = PROJECT_ROOT / "app.py"


class TestDataCutOffVerification(unittest.TestCase):
    def test_metadata_file_exists_and_valid(self):
        """Verifies metadata.json exists and is valid JSON."""
        self.assertTrue(METADATA_PATH.exists(), "metadata.json must exist in data directory")
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.assertIn("data_cut_off_date", data)
        self.assertIn("data_checksum_sha256", data)
        self.assertIn("latest_operating_month", data)
        self.assertIn("privacy_governance", data)

    def test_cutoff_date_format(self):
        """Verifies cutoff date adheres to 'YYYY-MM-DD HH:MM:SS UTC' standard."""
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        cutoff = data["data_cut_off_date"]
        
        pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC$"
        self.assertRegex(cutoff, pattern, f"Cut-off date '{cutoff}' does not match required UTC format")
        self.assertTrue(cutoff.startswith("2026-09-30"), f"Expected 2026-09-30 cutoff, got {cutoff}")

    def test_app_displays_data_cutoff(self):
        """Verifies that app.py contains the logic and UI elements to render the data cut-off date."""
        with open(APP_PATH, "r", encoding="utf-8") as f:
            app_code = f.read()

        self.assertIn("DATA_CUT_OFF", app_code)
        self.assertIn("Data Cut-off:", app_code)
        self.assertIn("cutoff-pill", app_code)


if __name__ == "__main__":
    unittest.main()
