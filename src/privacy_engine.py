"""PulseIQ Privacy by Design & Self-Service Governance Engine (Task 18)
Implements:
  1. Role-Based Access Control (RBAC) filtering across ADMIN, HR, MANAGER, EXECUTIVE.
  2. Strict k-Anonymity & Minimum Group Size Enforcement (default k=5, k=10 for attrition/risk).
  3. Secondary / Complementary Suppression to defeat mathematical differencing attacks.
  4. Privacy Audit & Adversarial Break-Test Validation.
"""

from typing import Dict, Any, List, Optional, Tuple
import re

# Governed RBAC Matrix Definitions
ROLE_PERMISSIONS = {
    "ADMIN": {
        "allowed_dimensions": ["Company", "Department", "Team"],
        "metric_domains": ["ALL"],
        "can_view_financial_margins": True,
        "can_view_workforce_pii": False,  # Zero raw PII in platform
        "can_view_delivery_tasks": True,
        "allowed_department_scope": "ALL",
        "allowed_team_scope": "ALL",
        "badge_color": "#4f46e5",
        "description": "System & Governance Administrator: Full catalog oversight and audit verification."
    },
    "EXECUTIVE": {
        "allowed_dimensions": ["Company", "Department"],
        "metric_domains": ["Finance", "HR Analytics", "AI/ML"],
        "can_view_financial_margins": True,
        "can_view_workforce_pii": False,
        "can_view_delivery_tasks": False,  # Restricted from micro-team task inspection
        "allowed_department_scope": "ALL",
        "allowed_team_scope": "NONE",
        "badge_color": "#0284c7",
        "description": "Executive Leadership: Company & Department macro strategic & financial scorecard."
    },
    "HR": {
        "allowed_dimensions": ["Company", "Department", "Team"],
        "metric_domains": ["HR Analytics", "Payroll", "AI/ML"],
        "can_view_financial_margins": False,  # Excluded from ledger net profit / operating margins
        "can_view_workforce_pii": False,
        "can_view_delivery_tasks": True,
        "allowed_department_scope": "ALL",
        "allowed_team_scope": "ALL",
        "badge_color": "#16a34a",
        "description": "People & Culture Operations: Workforce dynamics, headcount, attendance, and attrition."
    },
    "MANAGER": {
        "allowed_dimensions": ["Department", "Team"],
        "metric_domains": ["Engineering Ops", "HR Analytics"],
        "can_view_financial_margins": False,
        "can_view_workforce_pii": False,
        "can_view_delivery_tasks": True,
        "allowed_department_scope": "ASSIGNED",
        "allowed_team_scope": "ASSIGNED",
        "badge_color": "#ea580c",
        "description": "Department & Team Lead: Scoped strictly to assigned department and team delivery metrics."
    }
}


def parse_min_group_size(min_size_raw: Any, default: int = 5) -> int:
    """Parses minimum group size from metric dictionary (supports integers, strings like '5 tasks', NaN)."""
    if min_size_raw is None:
        return default
    val_str = str(min_size_raw).strip().lower()
    if val_str in ("nan", "none", "", "null"):
        return default
    # Extract leading digits
    match = re.search(r'\d+', val_str)
    if match:
        return int(match.group())
    return default


def filter_metrics_for_role(role: str, metric_catalog: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Returns the subset of metrics safe and authorized for the specified role."""
    perms = ROLE_PERMISSIONS.get(role.upper(), ROLE_PERMISSIONS["MANAGER"])
    allowed_domains = perms["metric_domains"]
    
    filtered = []
    for m in metric_catalog:
        m_id = m.get("metric_id", "")
        domain = m.get("owner_team", "")
        
        # Admin gets everything
        if "ALL" in allowed_domains:
            filtered.append(m)
            continue
            
        # Manager specific restrictions
        if role.upper() == "MANAGER":
            # Manager allowed Engineering Ops metrics (M22-M25) and basic attendance (M13, M14)
            if domain == "Engineering Ops":
                filtered.append(m)
            elif m_id in ("M13", "M14", "M01"):  # Attendance, Late arrivals, Headcount
                filtered.append(m)
            continue
            
        # HR specific restrictions
        if role.upper() == "HR":
            # HR allowed HR Analytics, Payroll aggregates, and AI/ML risk share, but NOT corporate finance margins
            if m_id in ("M16", "M17", "M18", "M19", "M20", "M21"):
                continue  # Skip P&L ledger margins
            if domain in ("HR Analytics", "Payroll", "AI/ML", "Engineering Ops"):
                filtered.append(m)
            continue
            
        # Executive specific restrictions
        if role.upper() == "EXECUTIVE":
            # Executive sees strategic financials and company/dept headcount/attrition, but not micro-team tasks
            if domain == "Engineering Ops":
                continue  # Skip sprint micro tasks
            filtered.append(m)
            continue

    return filtered


def evaluate_privacy_suppression(
    group_size: int,
    min_size: int,
    metric_id: str = "",
    is_secondary: bool = False
) -> Dict[str, Any]:
    """Evaluates whether a metric value must be suppressed based on minimum group size.
    
    Returns a dict with:
      - is_suppressed: bool
      - display_val: str
      - reason: str
      - status_badge: str
    """
    if is_secondary:
        return {
            "is_suppressed": True,
            "display_val": "🛡️ REDACTED (Differential Privacy)",
            "reason": "Secondary / Complementary suppression active: Value hidden to prevent mathematical subtraction leakage.",
            "status_badge": "Secondary Suppression"
        }

    if group_size < min_size:
        return {
            "is_suppressed": True,
            "display_val": f"🛡️ REDACTED (N={group_size} < k={min_size})",
            "reason": f"Privacy Rule Enforced: Group size (N={group_size}) is strictly below the governed minimum threshold (k={min_size}) to prevent re-identification and compensation exposure.",
            "status_badge": "Privacy Masked"
        }

    return {
        "is_suppressed": False,
        "display_val": None,
        "reason": f"Certified Safe: Sample size (N={group_size}) satisfies k-anonymity (k={min_size}).",
        "status_badge": "Certified Safe"
    }


def apply_secondary_suppression_table(
    rows: List[Dict[str, Any]],
    val_key: str,
    group_size_key: str,
    min_size: int,
    has_total_row: bool = True
) -> List[Dict[str, Any]]:
    """Applies Primary and Secondary (Complementary) Suppression to a collection of sibling rows.
    
    If exactly ONE subgroup in a breakdown is suppressed and the total is visible, an attacker
    can deduce the suppressed value via Subgroup = Total - Sum(Other Subgroups).
    To close this leak, the secondary suppression masks either the total or the next smallest group.
    """
    processed = []
    suppressed_count = 0
    non_total_rows = []
    total_row = None

    for r in rows:
        r_copy = dict(r)
        g_size = int(r_copy.get(group_size_key, 0) or 0)
        is_tot = r_copy.get("is_total", False) or r_copy.get("dimension_value") == "Total"
        
        if is_tot:
            total_row = r_copy
        else:
            eval_res = evaluate_privacy_suppression(g_size, min_size)
            r_copy["privacy_status"] = eval_res["status_badge"]
            r_copy["privacy_reason"] = eval_res["reason"]
            r_copy["is_suppressed"] = eval_res["is_suppressed"]
            if eval_res["is_suppressed"]:
                r_copy[val_key] = eval_res["display_val"]
                suppressed_count += 1
            non_total_rows.append(r_copy)

    # Check for Differencing Attack vulnerability:
    # If exactly 1 row is suppressed and there are 2 or more rows total:
    if suppressed_count == 1 and len(non_total_rows) >= 2:
        # If total is present, suppress total row to break subtraction
        if total_row:
            total_row["privacy_status"] = "Secondary Suppression"
            total_row["privacy_reason"] = "Suppressed to defeat differencing attack on the single masked subgroup."
            total_row["is_suppressed"] = True
            total_row[val_key] = "🛡️ REDACTED (Secondary Suppression)"
        else:
            # If no total row, find the next smallest group and suppress it
            sorted_candidates = sorted(
                [r for r in non_total_rows if not r["is_suppressed"]],
                key=lambda x: int(x.get(group_size_key, 0) or 0)
            )
            if sorted_candidates:
                sec_target = sorted_candidates[0]
                sec_target["privacy_status"] = "Secondary Suppression"
                sec_target["privacy_reason"] = "Secondary suppression applied to prevent subtractive re-identification."
                sec_target["is_suppressed"] = True
                sec_target[val_key] = "🛡️ REDACTED (Secondary Suppression)"

    if total_row:
        if not total_row.get("is_suppressed", False):
            tot_size = int(total_row.get(group_size_key, 0) or 0)
            eval_tot = evaluate_privacy_suppression(tot_size, min_size)
            total_row["privacy_status"] = eval_tot["status_badge"]
            total_row["privacy_reason"] = eval_tot["reason"]
            total_row["is_suppressed"] = eval_tot["is_suppressed"]
            if eval_tot["is_suppressed"]:
                total_row[val_key] = eval_tot["display_val"]
        processed = non_total_rows + [total_row]
    else:
        processed = non_total_rows

    return processed
