"""Pure execution-result evidence helpers for WRE Skillz."""

from __future__ import annotations

import json
from typing import Any, Mapping


def structural_step_output(result: Mapping[str, Any]) -> dict[str, Any]:
    """Return only meaningful output fields used for structural fidelity."""
    evidence: dict[str, Any] = {}
    output = result.get("output")
    if _meaningful_output(output):
        evidence["output"] = output
    steps_completed = result.get("steps_completed")
    if type(steps_completed) is int and steps_completed > 0:
        evidence["steps_completed"] = steps_completed
    return evidence


def _meaningful_output(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (dict, list, tuple)):
        return bool(value)
    return False


def stable_json_record(value: Any) -> str:
    """Serialize evidence strictly or return an explicit unavailable marker."""
    try:
        return json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, OverflowError):
        return '{"record_unavailable":"non_json_value"}'
