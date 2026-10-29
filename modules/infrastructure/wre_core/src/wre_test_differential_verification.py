"""Independent recomputation of WRE pytest differential evidence."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_exact_sha_commit_receipt import (
    validate_exact_sha_commit_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
)
from modules.infrastructure.wre_core.src.wre_test_differential_capability import (
    bounded_canonical_digest,
    consume_test_differential_capability,
)
from modules.infrastructure.wre_core.src.wre_test_impact_differential_gate import (
    evaluate_test_differential,
    make_test_impact_plan,
)
from modules.infrastructure.wre_core.src.wre_test_scope_coverage import (
    resolve_test_scope_coverage,
)

RUNTIME_SCHEMA = "wre_test_differential_runtime_receipt.v1"
FAIL_TEST_DIFFERENTIAL = "FAIL_TEST_DIFFERENTIAL_EVIDENCE"

_EVIDENCE_KEYS = {
    "schema_version", "receipt_id", "plan", "base_snapshot",
    "candidate_snapshot", "differential", "collector_digest",
    "base_report_digest", "candidate_report_digest",
    "execution_authority_verified",
}


def verify_test_differential_evidence(
    evidence: Mapping[str, Any], *, request: Mapping[str, Any]
) -> tuple[bool, str, str]:
    """Recompute analysis and every security-relevant runtime binding."""
    try:
        bounded_canonical_digest(evidence)
        return _verify(evidence, request)
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError):
        return False, "", ""


def _verify(
    evidence: Mapping[str, Any], request: Mapping[str, Any]
) -> tuple[bool, str, str]:
    item = evidence if isinstance(evidence, Mapping) else {}
    req = request if isinstance(request, Mapping) else {}
    if set(item) != _EVIDENCE_KEYS or item.get("schema_version") != RUNTIME_SCHEMA:
        return False, "", ""
    if item.get("execution_authority_verified") is not False:
        return False, "", ""
    expected_id = "wre_test_runtime_" + _digest(_without(item, "receipt_id"))[7:]
    if item.get("receipt_id") != expected_id:
        return False, "", ""
    plan = _mapping(item.get("plan"))
    base = _mapping(item.get("base_snapshot"))
    candidate = _mapping(item.get("candidate_snapshot"))
    authority = _mapping(req.get("signed_authority"))
    if not _bindings_match(item, plan, base, candidate, req, authority):
        return False, "", ""
    recomputed = evaluate_test_differential(plan, base, candidate).to_dict()
    if recomputed != item.get("differential") or recomputed.get("differential_clean") is not True:
        return False, "", ""
    capability = req.get("test_differential_capability")
    if not consume_test_differential_capability(capability, item, request=req):
        return False, "", ""
    digest = bounded_canonical_digest(item)
    return True, str(item["receipt_id"]), digest


def _bindings_match(
    item: Mapping[str, Any], plan: Mapping[str, Any], base: Mapping[str, Any],
    candidate: Mapping[str, Any], req: Mapping[str, Any], authority: Mapping[str, Any],
) -> bool:
    author = str(req.get("verifier_id") or "")
    return bool(
        _authority_context_matches(req, plan, authority)
        and plan.get("base_sha") == req.get("base_sha") == base.get("head_sha")
        and plan.get("candidate_sha") == req.get("head_sha") == candidate.get("head_sha")
        and plan.get("wsp15_allocation_receipt_id")
        == authority.get("wsp15_allocation_receipt_id")
        and plan.get("wsp15_allocation_receipt_digest")
        == authority.get("wsp15_allocation_digest")
        and base.get("runner_digest") == candidate.get("runner_digest")
        == plan.get("runner_digest") == item.get("collector_digest")
        and base.get("evidence_receipt_digest") == item.get("base_report_digest")
        and candidate.get("evidence_receipt_digest") == item.get("candidate_report_digest")
        and base.get("evidence_author_id") == candidate.get("evidence_author_id") == author
        and base.get("independent") is True and candidate.get("independent") is True
        and author and author != str(req.get("worker_id") or "")
    )


def _authority_context_matches(
    req: Mapping[str, Any], plan: Mapping[str, Any], authority: Mapping[str, Any]
) -> bool:
    work_order = _mapping(req.get("bound_work_order"))
    commit = _mapping(req.get("exact_sha_commit_receipt"))
    policy = _mapping(req.get("test_impact_policy"))
    verifier_plan = _mapping(work_order.get("slice_verifier_plan"))
    changed = sorted(str(item) for item in req.get("expected_changed_paths", ()))
    if not work_order or not commit or not policy or not changed:
        return False
    scope = resolve_test_scope_coverage(
        changed, str(policy.get("impact_class") or ""),
        policy.get("selection_args", ()),
    )
    if not scope.accepted:
        return False
    expected = make_test_impact_plan(
        base_sha=req.get("base_sha"), candidate_sha=req.get("head_sha"),
        changed_paths_digest=_digest(changed), impact_class=policy.get("impact_class"),
        suite_scope_digest=_digest(policy.get("selection_args")),
        runner_digest=plan.get("runner_digest"), environment_digest=plan.get("environment_digest"),
        dependency_lock_digest=plan.get("dependency_lock_digest"),
        selection_policy_digest=_digest("trusted-pytest-exact-id-collector.v1"),
        selection_args_digest=_digest(policy.get("selection_args")),
        base_lineage_receipt_digest=_digest({
            "base_sha": req.get("base_sha"), "head_sha": req.get("head_sha"),
            "ancestor": True,
        }),
        wsp15_allocation_receipt_id=authority.get("wsp15_allocation_receipt_id"),
        wsp15_allocation_receipt_digest=authority.get("wsp15_allocation_digest"),
        **{name: policy.get(name) for name in (
            "dependency_evidence_stale", "protected_authority_surface",
            "release_candidate", "periodic_health_audit",
            "security_closure_required", "held_out_closure_required",
            "omitted_scope_rationale",
        )},
    )
    return bool(
        validate_exact_sha_commit_receipt(commit)
        and canonical_full_work_order_digest(work_order) == commit.get("work_order_digest")
        and commit.get("work_order_id") == req.get("work_order_id") == work_order.get("work_order_id")
        and commit.get("base_sha") == req.get("base_sha")
        and commit.get("head_sha") == req.get("head_sha")
        and sorted(commit.get("changed_paths", ())) == changed
        and verifier_plan.get("test_impact_policy") == policy
        and plan.get("impact_class") == scope.effective_impact
        and plan.get("required_suite_kind") == scope.required_suite_kind
        and expected == plan
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _without(value: Mapping[str, Any], key: str) -> dict[str, Any]:
    return {name: item for name, item in value.items() if name != key}


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = ["FAIL_TEST_DIFFERENTIAL", "verify_test_differential_evidence"]
