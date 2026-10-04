"""Pure execution-result evidence helpers for WRE Skillz."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

from .wre_test_impact_differential_gate import validate_test_impact_plan

_PROJECTION_FALSE_FLAGS = {
    "repository_authority_verified", "test_execution_performed", "pytest_invoked",
    "candidate_code_executed", "signed_authority_verified", "execution_authority_verified",
    "collector_integrity_verified", "os_isolation_verified", "verification_capability_issued",
}
_PROJECTION_KEYS = _PROJECTION_FALSE_FLAGS | {
    "schema_version", "base_sha", "head_sha", "changed_paths", "changed_paths_digest",
    "lineage_digest", "worktree_path_digest", "repository_common_dir_digest",
    "recognized_dependency_digest", "recognized_dependency_parity_verified",
    "impact_class", "required_suite_kind", "logical_scope_digest", "test_impact_plan",
    "base", "candidate", "systemic_batched", "planning_only", "execution_status", "projection_id",
}
_SIDE_KEYS = {"registry_digest", "shard_ids", "paths", "batches", "plan_digest"}


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


def _bounded_builtin_json(value: Any) -> bool:
    """Bound traversal before copying; never invoke caller-defined methods."""
    nodes, characters, active = 0, 0, set()

    def visit(item, depth):
        nonlocal nodes, characters
        nodes += 1
        if depth > 16 or nodes > 50000:
            return False
        kind = type(item)
        if kind is str:
            characters += len(item)
            return len(item) <= 65536 and characters <= 1048576
        if item is None or kind is bool or kind is int:
            return True
        if kind is float:
            return math.isfinite(item)
        if not (kind is dict or kind is list or kind is tuple) or id(item) in active:
            return False
        active.add(id(item))
        try:
            if kind is dict:
                return all(type(key) is str and visit(key, depth + 1)
                           and visit(child, depth + 1) for key, child in item.items())
            return all(visit(child, depth + 1) for child in item)
        finally:
            active.remove(id(item))

    return visit(value, 0)


def _projection_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def normalize_registry_scope_projection(value: Any, *, request: Any) -> dict | None:
    """Validate/detach a planning report, without authenticating its assertions."""
    if type(value) is not dict or not _bounded_builtin_json(value):
        return None
    if set(value) != {"projected", "rejection_reasons", "evidence"}:
        return None
    if type(value["projected"]) is not bool or type(value["evidence"]) is not dict:
        return None
    reasons = value["rejection_reasons"]
    if type(reasons) not in (list, tuple) or len(reasons) > 32:
        return None
    if any(type(reason) is not str or not reason or len(reason) > 256 for reason in reasons):
        return None
    try:
        serialized = _projection_json(value)
        if len(serialized) > 8388608:
            return None
        report = json.loads(serialized)
        if report["projected"]:
            if reasons or not _valid_projection_evidence(report["evidence"], request):
                return None
        elif not reasons or report["evidence"]:
            return None
    except (TypeError, ValueError, OverflowError, RecursionError):
        return None
    return {
        "success": False, "_effect_evidence": False,
        "telemetry_completed": report["projected"],
        "telemetry_status": "projected" if report["projected"] else "rejected",
        "projection": report,
    }


def _valid_projection_evidence(evidence: dict, request: Any) -> bool:
    if set(evidence) != _PROJECTION_KEYS or type(request) is not dict:
        return False
    if not _bounded_builtin_json(request):
        return False
    encoded_request = _projection_json(request)
    if len(encoded_request) > 8388608:
        return False
    request = json.loads(encoded_request)
    if set(request) != {"base_sha", "head_sha", "expected_changed_paths", "projection_input"}:
        return False
    if evidence["schema_version"] != "wre_test_registry_scope_projection.v1":
        return False
    if any(evidence[name] is not False for name in _PROJECTION_FALSE_FLAGS):
        return False
    if any(evidence[name] is not True for name in ("planning_only", "recognized_dependency_parity_verified")):
        return False
    if evidence["execution_status"] != "BLOCKED_BY_OS_ISOLATED_RUNNER":
        return False
    if evidence["systemic_batched"] is not (evidence["impact_class"] == "SYSTEMIC"):
        return False
    if any(evidence[name] != request[name] for name in ("base_sha", "head_sha")):
        return False
    if evidence["changed_paths"] != request["expected_changed_paths"]:
        return False
    if not _projection_field_shapes(evidence):
        return False
    plan = evidence["test_impact_plan"]
    if type(plan) is not dict or validate_test_impact_plan(plan):
        return False
    pairs = {"base_sha": "base_sha", "candidate_sha": "head_sha", "impact_class": "impact_class",
             "required_suite_kind": "required_suite_kind", "changed_paths_digest": "changed_paths_digest",
             "suite_scope_digest": "logical_scope_digest", "dependency_lock_digest": "recognized_dependency_digest"}
    if any(plan[left] != evidence[right] for left, right in pairs.items()):
        return False
    body = {key: item for key, item in evidence.items() if key != "projection_id"}
    expected = "wre_registry_scope_" + hashlib.sha256(_projection_json(body).encode("ascii")).hexdigest()
    return evidence["projection_id"] == expected


def _projection_field_shapes(evidence: dict) -> bool:
    """Check report field types, not shard correctness or source authority."""
    def digest(value):
        return (type(value) is str and len(value) == 71 and value.startswith("sha256:")
                and all(c in "0123456789abcdef" for c in value[7:]))

    def strings(value):
        return type(value) is list and all(type(item) is str and bool(item) for item in value)

    if not strings(evidence["changed_paths"]) or not evidence["changed_paths"]:
        return False
    if not all(digest(evidence[name]) for name in (
        "changed_paths_digest", "lineage_digest", "worktree_path_digest",
        "repository_common_dir_digest", "recognized_dependency_digest", "logical_scope_digest",
    )):
        return False
    for name in ("base", "candidate"):
        side = evidence[name]
        if type(side) is not dict or set(side) != _SIDE_KEYS:
            return False
        if not digest(side["registry_digest"]) or not digest(side["plan_digest"]):
            return False
        if not strings(side["shard_ids"]) or not strings(side["paths"]):
            return False
        if type(side["batches"]) is not list or not all(strings(batch) for batch in side["batches"]):
            return False
    return True
