"""Automated Privacy Engine & Role-Based Access Control Unit Tests (Task 18)
Verifies:
  1. Small groups (< minimum group size) NEVER appear in outputs.
  2. Role-based views: Different roles see strictly different metrics and dimensions.
  3. Secondary / Complementary suppression defeats subtraction / differencing attacks.
  4. Break-it test cases: D00 Executive Office (N=1) and Team of 3 Attrition suppression.
"""

import unittest
from pathlib import Path
import sys

# Add src to path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from privacy_engine import (
    ROLE_PERMISSIONS,
    parse_min_group_size,
    filter_metrics_for_role,
    evaluate_privacy_suppression,
    apply_secondary_suppression_table
)


class TestPrivacyEngine(unittest.TestCase):
    def setUp(self):
        self.mock_metrics = [
            {"metric_id": "M01", "metric_name": "Headcount", "owner_team": "HR Analytics", "minimum_group_size": "5"},
            {"metric_id": "M04", "metric_name": "Attrition rate (monthly)", "owner_team": "HR Analytics", "minimum_group_size": "10"},
            {"metric_id": "M07", "metric_name": "Gross pay", "owner_team": "Payroll", "minimum_group_size": "5"},
            {"metric_id": "M09", "metric_name": "Payroll cost", "owner_team": "Finance", "minimum_group_size": "5"},
            {"metric_id": "M13", "metric_name": "Attendance rate", "owner_team": "HR Analytics", "minimum_group_size": "5"},
            {"metric_id": "M16", "metric_name": "Revenue", "owner_team": "Finance", "minimum_group_size": None},
            {"metric_id": "M18", "metric_name": "Operating margin", "owner_team": "Finance", "minimum_group_size": None},
            {"metric_id": "M22", "metric_name": "Task completion rate", "owner_team": "Engineering Ops", "minimum_group_size": "5 tasks"},
            {"metric_id": "M24", "metric_name": "Velocity", "owner_team": "Engineering Ops", "minimum_group_size": "5 tasks"},
            {"metric_id": "M27", "metric_name": "High-risk share", "owner_team": "AI/ML", "minimum_group_size": "10"}
        ]

    def test_parse_min_group_size(self):
        """Verifies parsing of group size strings, integers, and NaNs."""
        self.assertEqual(parse_min_group_size(5), 5)
        self.assertEqual(parse_min_group_size("10"), 10)
        self.assertEqual(parse_min_group_size("5 tasks"), 5)
        self.assertEqual(parse_min_group_size("nan", default=5), 5)
        self.assertEqual(parse_min_group_size(None, default=5), 5)

    def test_role_based_metric_filtering(self):
        """Verifies that each role receives strictly governed metric subsets."""
        # Admin gets everything
        admin_metrics = filter_metrics_for_role("ADMIN", self.mock_metrics)
        self.assertEqual(len(admin_metrics), len(self.mock_metrics))

        # Executive sees strategic financials and headcount, but NOT micro-team sprint tasks
        exec_metrics = filter_metrics_for_role("EXECUTIVE", self.mock_metrics)
        exec_ids = [m["metric_id"] for m in exec_metrics]
        self.assertIn("M16", exec_ids)  # Revenue
        self.assertIn("M18", exec_ids)  # Operating Margin
        self.assertIn("M01", exec_ids)  # Headcount
        self.assertNotIn("M22", exec_ids)  # Micro task completion excluded

        # HR sees people & workforce metrics, but NOT ledger profit/margin metrics
        hr_metrics = filter_metrics_for_role("HR", self.mock_metrics)
        hr_ids = [m["metric_id"] for m in hr_metrics]
        self.assertIn("M01", hr_ids)  # Headcount
        self.assertIn("M04", hr_ids)  # Attrition
        self.assertIn("M13", hr_ids)  # Attendance
        self.assertNotIn("M16", hr_ids)  # Revenue excluded
        self.assertNotIn("M18", hr_ids)  # Operating margin excluded

        # Manager sees team delivery and team attendance, NOT corporate financials
        mgr_metrics = filter_metrics_for_role("MANAGER", self.mock_metrics)
        mgr_ids = [m["metric_id"] for m in mgr_metrics]
        self.assertIn("M22", mgr_ids)  # Task completion rate
        self.assertIn("M24", mgr_ids)  # Velocity
        self.assertIn("M13", mgr_ids)  # Team attendance
        self.assertNotIn("M16", mgr_ids)  # Corporate revenue excluded
        self.assertNotIn("M07", mgr_ids)  # Individual gross pay check excluded

    def test_primary_suppression_small_groups(self):
        """Verifies that groups with N < k are masked and groups N >= k pass."""
        # N=1 < k=5 (e.g. Executive Office)
        res_d00 = evaluate_privacy_suppression(group_size=1, min_size=5)
        self.assertTrue(res_d00["is_suppressed"])
        self.assertIn("REDACTED", res_d00["display_val"])
        self.assertEqual(res_d00["status_badge"], "Privacy Masked")

        # N=4 < k=5
        res_4 = evaluate_privacy_suppression(group_size=4, min_size=5)
        self.assertTrue(res_4["is_suppressed"])

        # N=5 == k=5 (Boundary)
        res_5 = evaluate_privacy_suppression(group_size=5, min_size=5)
        self.assertFalse(res_5["is_suppressed"])
        self.assertEqual(res_5["status_badge"], "Certified Safe")

        # N=25 > k=5
        res_25 = evaluate_privacy_suppression(group_size=25, min_size=5)
        self.assertFalse(res_25["is_suppressed"])

    def test_think_for_yourself_team_of_3_attrition(self):
        """Verifies that a team of 3 CANNOT see attrition (k=10)."""
        # For attrition, min_group_size is 10
        team_size = 3
        k_attrition = 10
        res = evaluate_privacy_suppression(group_size=team_size, min_size=k_attrition)
        self.assertTrue(res["is_suppressed"], "Attrition rate must be suppressed for a team of 3!")
        self.assertIn("N=3 < k=10", res["display_val"])

    def test_secondary_complementary_suppression(self):
        """Verifies that mathematical differencing attacks are blocked by suppressing the total or second group."""
        # Scenario: Total = 20, Unit A = 18, Unit B = 2
        # Without secondary suppression, Unit B = Total - Unit A = 20 - 18 = 2!
        rows = [
            {"dimension_value": "Unit A", "val": 1800000, "headcount": 18, "is_total": False},
            {"dimension_value": "Unit B", "val": 200000, "headcount": 2, "is_total": False},
            {"dimension_value": "Total", "val": 2000000, "headcount": 20, "is_total": True}
        ]

        result = apply_secondary_suppression_table(
            rows=rows,
            val_key="val",
            group_size_key="headcount",
            min_size=5,
            has_total_row=True
        )

        unit_b_res = next(r for r in result if r["dimension_value"] == "Unit B")
        total_res = next(r for r in result if r["dimension_value"] == "Total")

        # Unit B must be primarily suppressed
        self.assertTrue(unit_b_res["is_suppressed"])
        self.assertIn("REDACTED", str(unit_b_res["val"]))

        # Total must be SECONDARILY suppressed to prevent differencing
        self.assertTrue(total_res["is_suppressed"], "Total row must be secondarily suppressed to prevent differencing!")
        self.assertIn("Secondary Suppression", total_res["privacy_status"])


if __name__ == "__main__":
    unittest.main()
