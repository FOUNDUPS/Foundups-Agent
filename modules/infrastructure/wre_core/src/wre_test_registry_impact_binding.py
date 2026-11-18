"""Bind registry scope to the canonical WRE test-impact plan contract."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from .wre_test_impact_differential_gate import (
    make_test_impact_plan,
    validate_test_impact_plan,
)

FAIL_POLICY = "FAIL_TEST_REGISTRY_PROJECTION_INPUT"
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_FIELDS = {
    "impact_class", "max_shards_per_batch", "max_total_shards", "max_files",
    "runner_digest", "environment_digest", "base_lineage_receipt_digest",
    "wsp15_allocation_receipt_id", "wsp15_allocation_receipt_digest",
    "dependency_evidence_fresh", "holoindex_evidence_fresh",
    "protected_authority_surface", "release_candidate",
    "periodic_health_audit", "security_closure_required",
    "held_out_closure_required", "omitted_scope_rationale",
}


def validated_projection_input(value: Any) -> Mapping[str, Any] | None:
    """Return exact registry bounds plus canonical impact-plan inputs."""
    if type(value) is not dict or set(value) != _FIELDS:
        return None
    digests = (
        "runner_digest", "environment_digest", "base_lineage_receipt_digest",
        "wsp15_allocation_receipt_digest",
    )
    booleans = (
        "dependency_evidence_fresh", "holoindex_evidence_fresh",
        "protected_authority_surface", "release_candidate",
        "periodic_health_audit", "security_closure_required",
        "held_out_closure_required",
    )
    valid = (
        value.get("impact_class") in {"ISOLATED", "MODULAR", "SYSTEMIC"}
        and _bounded(value.get("max_shards_per_batch"), 1, 32)
        and _bounded(value.get("max_total_shards"), 1, 512)
        and _bounded(value.get("max_files"), 1, 4096)
        and all(_DIGEST.fullmatch(str(value.get(name) or "")) for name in digests)
        and all(type(value.get(name)) is bool for name in booleans)
        and bool(str(value.get("wsp15_allocation_receipt_id") or "").strip())
        and isinstance(value.get("omitted_scope_rationale"), str)
    )
    return value if valid else None


def effective_projection_impact(value: Mapping[str, Any]) -> str:
    """Escalate stale, protected, release, and health work to SYSTEMIC."""
    systemic = (
        value["dependency_evidence_fresh"] is not True
        or value["holoindex_evidence_fresh"] is not True
        or value["protected_authority_surface"] is True
        or value["release_candidate"] is True
        or value["periodic_health_audit"] is True
    )
    return "SYSTEMIC" if systemic else str(value["impact_class"])


def projected_selection_args_digest(plan: Any) -> str:
    """Bind the exact per-side shard IDs, paths, and batches."""
    return _digest({
        side: {
            "shard_ids": getattr(plan, side).shard_ids,
            "paths": getattr(plan, side).paths,
            "batches": getattr(plan, side).batches,
        }
        for side in ("base", "candidate")
    })


def bound_test_impact_plan(
    value: Mapping[str, Any], *, base_sha: str, head_sha: str,
    changed_paths: Sequence[str], suite_scope_digest: str,
    dependency_lock_digest: str, selection_args_digest: str,
) -> Mapping[str, Any] | None:
    """Build and validate the existing wre_test_impact_plan.v1 contract."""
    selection_policy = {
        name: value[name] for name in (
            "dependency_evidence_fresh", "holoindex_evidence_fresh",
            "protected_authority_surface", "release_candidate",
            "periodic_health_audit", "security_closure_required",
            "held_out_closure_required", "omitted_scope_rationale",
        )
    }
    plan = make_test_impact_plan(
        base_sha=base_sha, candidate_sha=head_sha,
        changed_paths_digest=_digest(tuple(changed_paths)),
        impact_class=effective_projection_impact(value),
        suite_scope_digest=suite_scope_digest,
        selection_policy_digest=_digest(selection_policy),
        dependency_lock_digest=dependency_lock_digest,
        selection_args_digest=selection_args_digest,
        dependency_evidence_stale=value["dependency_evidence_fresh"] is not True,
        **{name: value[name] for name in (
            "runner_digest", "environment_digest", "base_lineage_receipt_digest",
            "wsp15_allocation_receipt_id", "wsp15_allocation_receipt_digest",
            "protected_authority_surface", "release_candidate",
            "periodic_health_audit", "security_closure_required",
            "held_out_closure_required", "omitted_scope_rationale",
        )},
    )
    return plan if not validate_test_impact_plan(plan) else None


def _bounded(value: Any, minimum: int, maximum: int) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("ascii")).hexdigest()


__all__ = [
    "FAIL_POLICY", "bound_test_impact_plan", "effective_projection_impact",
    "projected_selection_args_digest", "validated_projection_input",
]
