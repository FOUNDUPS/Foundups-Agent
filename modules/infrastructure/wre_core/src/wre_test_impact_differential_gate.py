"""Pure WRE test-impact and parent/candidate differential analysis.

This module never authenticates evidence or authorizes promotion. It provides
deterministic integrity checks and exact test-ID deltas for an independently
authenticated evidence plane to consume.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "wre_test_run_snapshot.v1"
PLAN_SCHEMA = "wre_test_impact_plan.v1"
RECEIPT_SCHEMA = "wre_test_differential_receipt.v1"

FAIL_PLAN = "FAIL_TEST_IMPACT_PLAN"
FAIL_SNAPSHOT = "FAIL_TEST_RUN_SNAPSHOT"
FAIL_BINDING = "FAIL_TEST_EXECUTION_BINDING"
FAIL_REMOVED_TEST = "FAIL_TEST_REMOVED"
FAIL_NEW_FAILURE = "FAIL_NEW_TEST_FAILURE"
FAIL_NEW_ERROR = "FAIL_NEW_TEST_ERROR"
FAIL_NEW_SKIP = "FAIL_NEW_TEST_SKIP"
FAIL_NEW_XFAIL = "FAIL_NEW_TEST_XFAIL"
FAIL_NEW_XPASS = "FAIL_NEW_TEST_XPASS"
FAIL_NEW_DESELECTION = "FAIL_NEW_TEST_DESELECTION"
FAIL_SUITE_SCOPE = "FAIL_REQUIRED_TEST_SUITE_SCOPE"
FAIL_SECURITY_CLOSURE = "FAIL_SECURITY_CLOSURE_REQUIRED"
FAIL_HELD_OUT_CLOSURE = "FAIL_HELD_OUT_CLOSURE_REQUIRED"

_SHA_LENGTH = 40
_DIGEST_PREFIX = "sha256:"
_SUITE_RANK = {
    "FOCUSED": 1,
    "MODULE_CLOSURE": 2,
    "DEPENDENCY_CLOSURE": 3,
    "FULL_REPOSITORY": 4,
}
_IMPACT_CLASSES = {"ISOLATED", "MODULAR", "SYSTEMIC"}
_OUTCOME_FIELDS = (
    "passed_ids",
    "failed_ids",
    "skipped_ids",
    "error_ids",
    "xfailed_ids",
    "xpassed_ids",
    "deselected_ids",
)
_PLAN_KEYS = {
    "schema_version", "plan_id", "base_sha", "candidate_sha",
    "changed_paths_digest", "impact_class", "required_suite_kind",
    "suite_scope_digest", "runner_digest", "environment_digest",
    "dependency_lock_digest", "selection_policy_digest", "selection_args_digest",
    "base_lineage_receipt_digest", "wsp15_allocation_receipt_id",
    "wsp15_allocation_receipt_digest", "dependency_evidence_stale",
    "protected_authority_surface", "release_candidate", "periodic_health_audit",
    "security_closure_required", "held_out_closure_required",
    "omitted_scope_rationale",
}
_SNAPSHOT_KEYS = {
    "schema_version", "snapshot_id", "head_sha", "suite_kind",
    "suite_scope_digest", "collection_manifest_digest", "runner_digest",
    "environment_digest", "dependency_lock_digest", "selection_policy_digest",
    "selection_args_digest", "base_lineage_receipt_digest", "evidence_receipt_id",
    "evidence_receipt_digest", "evidence_author_id", "independent",
    "security_closure_passed", "held_out_closure_passed", "collected_ids",
    *_OUTCOME_FIELDS,
}


@dataclass(frozen=True)
class TestDifferentialReceipt:
    schema_version: str
    receipt_id: str
    base_sha: str
    candidate_sha: str
    impact_class: str
    required_suite_kind: str
    base_snapshot_id: str
    candidate_snapshot_id: str
    unchanged_failures: tuple[str, ...]
    resolved_failures: tuple[str, ...]
    added_passing_tests: tuple[str, ...]
    removed_tests: tuple[str, ...]
    new_failures: tuple[str, ...]
    new_errors: tuple[str, ...]
    new_skips: tuple[str, ...]
    new_xfails: tuple[str, ...]
    new_xpasses: tuple[str, ...]
    new_deselections: tuple[str, ...]
    rejection_reasons: tuple[str, ...]
    differential_clean: bool
    authority_verified: bool = False
    promotion_authorized: bool = False
    no_test_execution_performed: bool = True
    no_repository_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_test_differential(
    plan: Mapping[str, Any],
    base: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> TestDifferentialReceipt:
    """Analyze normalized snapshots without treating them as authority."""
    safe_plan = _mapping(plan)
    safe_base = _mapping(base)
    safe_candidate = _mapping(candidate)
    reasons = _validate_plan(safe_plan)
    reasons.extend(_validate_snapshot(safe_base))
    reasons.extend(_validate_snapshot(safe_candidate))
    reasons.extend(_binding_reasons(safe_plan, safe_base, safe_candidate))
    reasons.extend(_scope_reasons(safe_plan, safe_base, safe_candidate))
    deltas = _differential_sets(safe_base, safe_candidate)
    reasons.extend(_delta_reasons(deltas))
    return _build_receipt(safe_plan, safe_base, safe_candidate, reasons, deltas)


def make_test_impact_plan(**fields: Any) -> dict[str, Any]:
    """Create an integrity-bound plan with policy-derived escalation."""
    impact_class = str(fields.get("impact_class") or "")
    signals = {
        name: fields.get(name, False)
        for name in (
            "dependency_evidence_stale",
            "protected_authority_surface",
            "release_candidate",
            "periodic_health_audit",
        )
    }
    required_suite_kind = _required_suite_kind(
        impact_class,
        **signals,
    )
    payload = {
        "schema_version": PLAN_SCHEMA,
        "base_sha": fields.get("base_sha"),
        "candidate_sha": fields.get("candidate_sha"),
        "changed_paths_digest": fields.get("changed_paths_digest"),
        "impact_class": impact_class,
        "required_suite_kind": required_suite_kind,
        **{name: fields.get(name) for name in (
            "suite_scope_digest", "runner_digest", "environment_digest",
            "dependency_lock_digest", "selection_policy_digest",
            "selection_args_digest", "base_lineage_receipt_digest",
            "wsp15_allocation_receipt_id", "wsp15_allocation_receipt_digest",
        )},
        **signals,
        "security_closure_required": fields.get("security_closure_required", False),
        "held_out_closure_required": fields.get("held_out_closure_required", False),
        "omitted_scope_rationale": fields.get("omitted_scope_rationale", ""),
    }
    payload["plan_id"] = "wre_test_plan_" + _digest_hex(payload)
    return payload


def make_test_run_snapshot(**fields: Any) -> dict[str, Any]:
    """Normalize runner output and bind its exact collection manifest."""
    outcomes = {
        name: _normalized_ids(fields.get(name, ())) for name in _OUTCOME_FIELDS
    }
    collected = sorted(set().union(*(set(values) for values in outcomes.values())))
    payload = {
        "schema_version": SCHEMA,
        "head_sha": fields.get("head_sha"),
        "suite_kind": fields.get("suite_kind"),
        "suite_scope_digest": fields.get("suite_scope_digest"),
        "collection_manifest_digest": _digest({"collected_ids": collected}),
        **{name: fields.get(name) for name in (
            "runner_digest", "environment_digest", "dependency_lock_digest",
            "selection_policy_digest", "selection_args_digest",
            "base_lineage_receipt_digest", "evidence_receipt_id",
            "evidence_receipt_digest", "evidence_author_id", "independent",
        )},
        "security_closure_passed": fields.get("security_closure_passed", False),
        "held_out_closure_passed": fields.get("held_out_closure_passed", False),
        "collected_ids": collected,
        **outcomes,
    }
    payload["snapshot_id"] = "wre_test_run_" + _digest_hex(payload)
    return payload


def _required_suite_kind(impact_class: str, **signals: bool) -> str:
    if impact_class == "SYSTEMIC" or any(signals.values()):
        return "FULL_REPOSITORY"
    if impact_class == "MODULAR":
        return "MODULE_CLOSURE"
    return "FOCUSED"


def _validate_plan(plan: Mapping[str, Any]) -> list[str]:
    expected = "wre_test_plan_" + _safe_digest_hex(_without(plan, "plan_id"))
    digest_fields = (
        "changed_paths_digest", "suite_scope_digest", "runner_digest",
        "environment_digest", "dependency_lock_digest", "selection_policy_digest",
        "selection_args_digest", "base_lineage_receipt_digest",
        "wsp15_allocation_receipt_digest",
    )
    bool_fields = (
        "dependency_evidence_stale", "protected_authority_surface",
        "release_candidate", "periodic_health_audit", "security_closure_required",
        "held_out_closure_required",
    )
    derived = _required_suite_kind(
        str(plan.get("impact_class") or ""),
        **{name: plan.get(name) is True for name in bool_fields[:4]},
    )
    valid = (
        set(plan) == _PLAN_KEYS
        and plan.get("schema_version") == PLAN_SCHEMA
        and plan.get("impact_class") in _IMPACT_CLASSES
        and plan.get("required_suite_kind") == derived
        and _is_sha(plan.get("base_sha")) and _is_sha(plan.get("candidate_sha"))
        and plan.get("base_sha") != plan.get("candidate_sha")
        and all(_is_digest(plan.get(name)) for name in digest_fields)
        and all(isinstance(plan.get(name), bool) for name in bool_fields)
        and bool(str(plan.get("wsp15_allocation_receipt_id") or "").strip())
        and isinstance(plan.get("omitted_scope_rationale"), str)
        and plan.get("plan_id") == expected
    )
    return [] if valid else [FAIL_PLAN]


def _validate_snapshot(snapshot: Mapping[str, Any]) -> list[str]:
    expected = "wre_test_run_" + _safe_digest_hex(_without(snapshot, "snapshot_id"))
    groups = [_ids(snapshot, name) for name in _OUTCOME_FIELDS]
    collected = _ids(snapshot, "collected_ids")
    manifest = _safe_digest({"collected_ids": sorted(collected)})
    digest_fields = (
        "suite_scope_digest", "runner_digest", "environment_digest",
        "dependency_lock_digest", "selection_policy_digest", "selection_args_digest",
        "base_lineage_receipt_digest", "evidence_receipt_digest",
    )
    valid = (
        set(snapshot) == _SNAPSHOT_KEYS
        and snapshot.get("schema_version") == SCHEMA
        and _is_sha(snapshot.get("head_sha"))
        and snapshot.get("suite_kind") in _SUITE_RANK
        and all(_is_digest(snapshot.get(name)) for name in digest_fields)
        and snapshot.get("collection_manifest_digest") == manifest
        and bool(str(snapshot.get("evidence_receipt_id") or "").strip())
        and bool(str(snapshot.get("evidence_author_id") or "").strip())
        and snapshot.get("independent") is True
        and all(isinstance(snapshot.get(name), bool) for name in (
            "security_closure_passed", "held_out_closure_passed"
        ))
        and all(_ids_are_canonical(snapshot.get(name)) for name in (*_OUTCOME_FIELDS, "collected_ids"))
        and bool(collected)
        and sum(len(group) for group in groups) == len(set().union(*groups))
        and set().union(*groups) == collected
        and snapshot.get("snapshot_id") == expected
    )
    return [] if valid else [FAIL_SNAPSHOT]


def _binding_reasons(plan: Mapping[str, Any], base: Mapping[str, Any], candidate: Mapping[str, Any]) -> list[str]:
    bindings = (
        "suite_scope_digest", "runner_digest", "environment_digest",
        "dependency_lock_digest", "selection_policy_digest", "selection_args_digest",
        "base_lineage_receipt_digest",
    )
    valid = (
        base.get("head_sha") == plan.get("base_sha")
        and candidate.get("head_sha") == plan.get("candidate_sha")
        and base.get("suite_kind") == candidate.get("suite_kind")
        and all(base.get(name) == candidate.get(name) == plan.get(name) for name in bindings)
    )
    return [] if valid else [FAIL_BINDING]


def _scope_reasons(plan: Mapping[str, Any], base: Mapping[str, Any], candidate: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    required = _SUITE_RANK.get(str(plan.get("required_suite_kind") or ""), 99)
    if min(_SUITE_RANK.get(str(base.get("suite_kind") or ""), 0), _SUITE_RANK.get(str(candidate.get("suite_kind") or ""), 0)) < required:
        reasons.append(FAIL_SUITE_SCOPE)
    if plan.get("security_closure_required") is True and candidate.get("security_closure_passed") is not True:
        reasons.append(FAIL_SECURITY_CLOSURE)
    if plan.get("held_out_closure_required") is True and candidate.get("held_out_closure_passed") is not True:
        reasons.append(FAIL_HELD_OUT_CLOSURE)
    return reasons


def _differential_sets(base: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, set[str]]:
    base_collected = _ids(base, "collected_ids")
    candidate_collected = _ids(candidate, "collected_ids")
    return {
        "unchanged_failures": _ids(base, "failed_ids") & _ids(candidate, "failed_ids"),
        "resolved_failures": _ids(base, "failed_ids") & _ids(candidate, "passed_ids"),
        "added_passing": (candidate_collected - base_collected) & _ids(candidate, "passed_ids"),
        "removed": base_collected - candidate_collected,
        "new_failures": _ids(candidate, "failed_ids") - _ids(base, "failed_ids"),
        "new_errors": _ids(candidate, "error_ids") - _ids(base, "error_ids"),
        "new_skips": _ids(candidate, "skipped_ids") - _ids(base, "skipped_ids"),
        "new_xfails": _ids(candidate, "xfailed_ids") - _ids(base, "xfailed_ids"),
        "new_xpasses": _ids(candidate, "xpassed_ids") - _ids(base, "xpassed_ids"),
        "new_deselections": _ids(candidate, "deselected_ids") - _ids(base, "deselected_ids"),
    }


def _delta_reasons(deltas: Mapping[str, set[str]]) -> list[str]:
    checks = (
        ("removed", FAIL_REMOVED_TEST), ("new_failures", FAIL_NEW_FAILURE),
        ("new_errors", FAIL_NEW_ERROR), ("new_skips", FAIL_NEW_SKIP),
        ("new_xfails", FAIL_NEW_XFAIL), ("new_xpasses", FAIL_NEW_XPASS),
        ("new_deselections", FAIL_NEW_DESELECTION),
    )
    return [reason for name, reason in checks if deltas[name]]


def _build_receipt(plan: Mapping[str, Any], base: Mapping[str, Any], candidate: Mapping[str, Any], reasons: Sequence[str], deltas: Mapping[str, set[str]]) -> TestDifferentialReceipt:
    deduped = tuple(dict.fromkeys(reasons))
    seed = {
        "plan_id": str(plan.get("plan_id") or ""),
        "base_snapshot_id": str(base.get("snapshot_id") or ""),
        "candidate_snapshot_id": str(candidate.get("snapshot_id") or ""),
        "rejection_reasons": deduped,
        "deltas": {name: sorted(values) for name, values in deltas.items()},
    }
    return TestDifferentialReceipt(
        schema_version=RECEIPT_SCHEMA,
        receipt_id="wre_test_diff_" + _digest_hex(seed),
        base_sha=str(base.get("head_sha") or ""), candidate_sha=str(candidate.get("head_sha") or ""),
        impact_class=str(plan.get("impact_class") or ""), required_suite_kind=str(plan.get("required_suite_kind") or ""),
        base_snapshot_id=str(base.get("snapshot_id") or ""), candidate_snapshot_id=str(candidate.get("snapshot_id") or ""),
        unchanged_failures=tuple(sorted(deltas["unchanged_failures"])), resolved_failures=tuple(sorted(deltas["resolved_failures"])),
        added_passing_tests=tuple(sorted(deltas["added_passing"])), removed_tests=tuple(sorted(deltas["removed"])),
        new_failures=tuple(sorted(deltas["new_failures"])), new_errors=tuple(sorted(deltas["new_errors"])),
        new_skips=tuple(sorted(deltas["new_skips"])), new_xfails=tuple(sorted(deltas["new_xfails"])),
        new_xpasses=tuple(sorted(deltas["new_xpasses"])), new_deselections=tuple(sorted(deltas["new_deselections"])),
        rejection_reasons=deduped, differential_clean=not deduped,
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _without(value: Mapping[str, Any], key: str) -> dict[str, Any]:
    return {name: item for name, item in value.items() if name != key}


def _ids(snapshot: Mapping[str, Any], name: str) -> set[str]:
    value = snapshot.get(name)
    return {item for item in value if isinstance(item, str) and item.strip()} if isinstance(value, list) else set()


def _normalized_ids(values: Iterable[str]) -> list[str]:
    if isinstance(values, (str, bytes)):
        return []
    try:
        return sorted({value.strip() for value in values if isinstance(value, str) and value.strip()})
    except TypeError:
        return []


def _ids_are_canonical(value: Any) -> bool:
    return isinstance(value, list) and value == _normalized_ids(value)


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == _SHA_LENGTH and all(char in "0123456789abcdef" for char in value)


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 71 and value.startswith(_DIGEST_PREFIX) and all(char in "0123456789abcdef" for char in value[7:])


def _digest(value: Any) -> str:
    return _DIGEST_PREFIX + _digest_hex(value)


def _digest_hex(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_digest(value: Any) -> str:
    return _DIGEST_PREFIX + _safe_digest_hex(value)


def _safe_digest_hex(value: Any) -> str:
    try:
        return _digest_hex(value)
    except (TypeError, ValueError, OverflowError):
        return "0" * 64


__all__ = [
    "PLAN_SCHEMA", "RECEIPT_SCHEMA", "SCHEMA", "TestDifferentialReceipt",
    "evaluate_test_differential", "make_test_impact_plan", "make_test_run_snapshot",
]
