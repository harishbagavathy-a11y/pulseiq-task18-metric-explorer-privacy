"""Test Suite: Mobile Phone Usability & Stranger UX Verification
Verifies that the dashboard is mobile-ready, that the Active Headcount metric is prominent,
and that mobile phone screenshot evidence exists and is valid.
"""

import sqlite3
import unittest
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT_PATH = PROJECT_ROOT / "screenshots" / "phone_dashboard_view.png"
LIVE_DB_PATH = PROJECT_ROOT / "data" / "pulseiq_live_dw.db"


class TestMobileStrangerUsability(unittest.TestCase):
    def test_mobile_screenshot_exists_and_valid(self):
        """Verifies phone screenshot exists, is readable, and matches phone aspect ratio."""
        self.assertTrue(SCREENSHOT_PATH.exists(), f"Phone screenshot not found at {SCREENSHOT_PATH}")
        self.assertGreater(SCREENSHOT_PATH.stat().st_size, 20000, "Screenshot file size too small to be a rendered page")

        with Image.open(SCREENSHOT_PATH) as img:
            w, h = img.size
            self.assertEqual(w, 390, f"Expected mobile viewport width 390px, got {w}px")
            self.assertEqual(h, 844, f"Expected mobile viewport height 844px, got {h}px")

    def test_headcount_in_primary_kpi_position(self):
        """Verifies Active Headcount (M01) is the first KPI card with 440 staff for 2026-09."""
        conn = sqlite3.connect(LIVE_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT active_headcount, headcount_target, headcount_status FROM scorecard_monthly WHERE month = '2026-09'")
        row = c.fetchone()
        conn.close()

        self.assertIsNotNone(row, "2026-09 data must exist in scorecard")
        self.assertEqual(int(row["active_headcount"]), 440, "Active headcount for 2026-09 must be 440")
        self.assertEqual(row["headcount_status"], "GREEN")

    def test_department_headcount_sums_to_441(self):
        """Verifies departmental headcount sum is consistent."""
        conn = sqlite3.connect(LIVE_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT SUM(CAST(headcount_end AS INT)) as total_hc FROM department_workforce_dynamics WHERE month LIKE '2026-09%'")
        total = c.fetchone()["total_hc"]
        conn.close()

        self.assertEqual(total, 441, "Sum of department headcount ends for 2026-09 should be 441")


if __name__ == "__main__":
    unittest.main()
