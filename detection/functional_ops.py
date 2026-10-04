"""
Functional Programming Utilities (Module 3 & 4)
Provides data filtering, mapping, lambda pipelines, and aggregations.
"""
from functools import reduce
from typing import List, Dict, Any, Callable, Optional


# 1. Lambda Functions for Fine Adjustments & Speed Violations
calculate_speed_overshoot = lambda detected, limit: max(0.0, round(detected - limit, 1))

is_extreme_speed = lambda detected, limit: (detected - limit) > 30.0

calculate_fine_multiplier = lambda excess_speed: 1.5 if excess_speed > 30.0 else (1.2 if excess_speed > 15.0 else 1.0)


# 2. Functional Data Filtering
def filter_by_violation_type(violations: List[Dict[str, Any]], violation_type: str) -> List[Dict[str, Any]]:
    """Filter violation records using functional filter() and lambda."""
    return list(filter(lambda v: v.get("violation_type") == violation_type, violations))


def filter_by_min_fine(violations: List[Dict[str, Any]], min_amount: float) -> List[Dict[str, Any]]:
    """Filter violations with fine >= threshold."""
    return list(filter(lambda v: float(v.get("fine_amount", 0)) >= min_amount, violations))


def filter_unissued_violations(violations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter violations awaiting E-Challan generation."""
    return list(filter(lambda v: v.get("status") == "RECORDED", violations))


# 3. Functional Data Mapping
def map_to_alert_summary(violations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Transform raw violation records into clean notification cards using map()."""
    transform = lambda v: {
        "id": v.get("violation_id"),
        "vehicle": v.get("vehicle_number"),
        "offense": v.get("violation_type"),
        "fine": f"INR {v.get('fine_amount', 0):,.0f}",
        "location": v.get("location"),
        "time": v.get("timestamp", "").split("T")[-1][:8] if "T" in v.get("timestamp", "") else v.get("timestamp", ""),
        "status": v.get("status"),
    }
    return list(map(transform, violations))


def extract_field(records: List[Dict[str, Any]], key: str) -> List[Any]:
    """Extract a single field across records using map and itemgetter lambda."""
    return list(map(lambda r: r.get(key), records))


# 4. Functional Aggregation (Reduce)
def calculate_total_fine(violations: List[Dict[str, Any]]) -> float:
    """Calculate total accumulated fines using functional reduce()."""
    if not violations:
        return 0.0
    return reduce(lambda total, v: total + float(v.get("fine_amount", 0)), violations, 0.0)
