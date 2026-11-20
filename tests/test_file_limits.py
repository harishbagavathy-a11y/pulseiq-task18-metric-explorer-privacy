"""Test Suite: Platform File Limits & Data Minimization Verification
Verifies that all exported data files (Parquet & SQLite) strictly adhere to platform
limits (< 200 MB, < 100 MB GitHub limit) and that PII tables are excluded.
"""

import sqlite3
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PARQUET_DIR = DATA_DIR / "parquet"
LIVE_DB_PATH = DATA_DIR / "pulseiq_live_dw.db"

MAX_PLATFORM_FILE_SIZE_BYTES = 200 * 1024 * 1024  # 200 MB
MAX_GITHUB_FILE_SIZE_BYTES = 100 * 1024 * 1024    # 100 MB


class TestPlatformFileLimits(unittest.TestCase):
    def test_live_database_size_well_within_limits(self):
        """Verifies that pulseiq_live_dw.db is under 200 MB and under 100 MB."""
        self.assertTrue(LIVE_DB_PATH.exists(), "pulseiq_live_dw.db must exist")
        db_size = LIVE_DB_PATH.stat().st_size
        db_size_mb = db_size / (1024 * 1024)
        
        self.assertLess(db_size, MAX_PLATFORM_FILE_SIZE_BYTES, f"DB size {db_size_mb:.2f} MB exceeds 200 MB platform limit")
        self.assertLess(db_size, MAX_GITHUB_FILE_SIZE_BYTES, f"DB size {db_size_mb:.2f} MB exceeds 100 MB GitHub limit")
        # In fact, our aggregate DB should be ultra-lean (< 5 MB)
        self.assertLess(db_size_mb, 5.0, f"DB size {db_size_mb:.2f} MB should be under 5 MB for an aggregate warehouse")

    def test_parquet_files_exist_and_within_limits(self):
        """Verifies Parquet files are present, valid, and well within limits."""
        self.assertTrue(PARQUET_DIR.exists(), "parquet directory must exist")
        parquet_files = list(PARQUET_DIR.glob("*.parquet"))
        self.assertGreaterEqual(len(parquet_files), 6, "Must export at least 6 Parquet aggregate files")

        total_parquet_size = 0
        for pf in parquet_files:
            size = pf.stat().st_size
            total_parquet_size += size
            self.assertLess(size, MAX_PLATFORM_FILE_SIZE_BYTES, f"Parquet file {pf.name} exceeds 200 MB")
        
        total_mb = total_parquet_size / (1024 * 1024)
        self.assertLess(total_mb, 5.0, f"Total parquet footprint {total_mb:.2f} MB should be under 5 MB")

    def test_pii_tables_excluded_from_live_database(self):
        """Verifies that no raw employee PII or granular tables exist in the live DB."""
        conn = sqlite3.connect(LIVE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")
        names = [r[0] for r in cursor.fetchall()]
        conn.close()

        # Prohibited raw PII & transaction tables
        prohibited_tables = ["dim_employee", "fact_payroll", "fact_leave", "fact_task", "dim_account"]
        for p in prohibited_tables:
            self.assertNotIn(p, names, f"Prohibited PII table '{p}' found in public live database!")


if __name__ == "__main__":
    unittest.main()
