"""OpenClaw RedDog governed work-order policy gate (no execution).

Slice: REDDOG_OPENCLAW_WORK_ORDER_POLICY_GATE_PHASE1
Contract: docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md

Convergence point before any future WRE execution. Validates dry-run envelope,
permission snapshot freshness/capability, and HoloIndex evidence policy — without
branch, PR, commit, merge, file write, WRE executor, or Hermes queue dispatch.

WAE-L1 / external RedDog alignment (Addendum B — mapping only, no WAE refactor):
| WAE-L1 direction field      | RedDogGovernedWorkOrder field   | PolicyGateReceipt field        |
|-----------------------------|---------------------------------|--------------------------------|
| direction_id                | work_order_id                   | work_order_id                  |
| created_at                  | created_at                      | checked_at (gate evaluation)   |
| principal_id                | authenticated_principal         | (via permission_truth_label)   |
| target_repo                 | repo_full_name                  | permission_snapshot_digest     |
| proposed_action             | requested_operation             | gates_checked (capability)     |
| authority_hint              | authority_tier                  | rejection_reasons              |
| path_scope                  | allowed_paths / denied_paths    | dry_run_receipt_digest         |
| branch_hint                 | branch_name / base_ref          | dry_run_receipt_digest         |
| holo_evidence_packet        | holoindex_evidence              | holoindex_evidence_digest      |
| wsp_tags                    | wsp_applicability               | holoindex_evidence_digest      |
| skillz_hints                | skillz_candidates               | rejection_reasons (skillz)     |
| advisory_digest             | evidence_digest                 | receipt_digest                 |
| source_packet               | advisory_only_source_packet     | SPECIFIED_NOT_IMPLEMENTED      |
| (no WAE runtime dispatch)   | (no extension execution)        | no_execution_performed: true   |

Field gaps marked SPECIFIED_NOT_IMPLEMENTED — do not refactor WAE in this slice.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, MutableSet, Optional, Union

from modules.communication.moltbot_bridge.src.reddog_governed_work_order_dryrun import (
    DECISION_ACCEPT,
    DECISION_ACCEPT_WITH_GAP,
    DECISION_REJECT,
    DOCS_ONLY_OPERATIONS,
    RedDogGovernedWorkOrder,
    validate_work_order_dryrun,
    _is_write_sensitive_operation,
    _normalize_operation,
    _work_order_from_mapping,
)
from modules.platform_integration.github_integration.src.reddog_github_permission_probe import (
    permission_to_capabilities,
)

POLICY_ACCEPT = "POLICY_ACCEPT"
POLICY_REJECT = "POLICY_REJECT"
POLICY_ACCEPT_WITH_RETRIEVAL_GAP = "POLICY_ACCEPT_WITH_RETRIEVAL_GAP"

TRUTH_OBSERVED = "OBSERVED"
TRUTH_NEEDS_VERIFICATION = "NEEDS_VERIFICATION"

DEFAULT_PERMISSION_TTL_SECONDS = 300
TRUSTED_PERMISSION_SOURCES = frozenset({"gh_cli", "github_api", "mock"})


@dataclass
class PolicyGateReceipt:
    receipt_id: str
    work_order_id: str
    decision: str
    rejection_reasons: List[str]
    gates_checked: List[str]
    dry_run_receipt_digest: str
    permission_snapshot_digest: str
    permission_truth_label: str
    holoindex_evidence_digest: str
    no_execution_performed: bool
    checked_at: str
    expires_at: Optional[str]
    next_required_check_at: Optional[str]
    receipt_digest: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _utc_now(now: Optional[datetime] = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc)


def _iso8601(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def _parse_iso8601(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def permission_truth_label(permission_level: str, source: str) -> str:
    """OBSERVED when permission is proven; NEEDS_VERIFICATION when not."""
    level = (permission_level or "").strip().lower()
    src = (source or "").strip().lower()
    if level in {"unknown", "none", ""}:
        return TRUTH_NEEDS_VERIFICATION
    if src in TRUSTED_PERMISSION_SOURCES and level in {
        "admin",
        "maintain",
        "write",
        "triage",
        "read",
    }:
        return TRUTH_OBSERVED
    if level in {"admin", "maintain", "write", "triage", "read"}:
        return TRUTH_OBSERVED
    return TRUTH_NEEDS_VERIFICATION


def _permission_snapshot_fresh(
    captured_at: str,
    *,
    now: datetime,
    ttl_seconds: int = DEFAULT_PERMISSION_TTL_SECONDS,
    expires_at: Optional[str] = None,
) -> bool:
    if expires_at:
        try:
            return now <= _parse_iso8601(expires_at)
        except ValueError:
            return False
    try:
        captured = _parse_iso8601(captured_at)
        return now <= captured + timedelta(seconds=max(1, ttl_seconds))
    except ValueError:
        return False


def _holoindex_evidence_digest(work_order: RedDogGovernedWorkOrder) -> str:
    holo = work_order.holoindex_evidence
    if holo is None:
        return _canonical_digest({"missing": True})
    payload = {
        "holoindex_status": holo.holoindex_status,
        "retrieval_quality": holo.retrieval_quality,
        "applicable_wsps": sorted(holo.applicable_wsps),
        "evidence_refs": sorted(holo.evidence_refs),
        "direct_read_fallback_used": holo.direct_read_fallback_used,
        "index_gap_detected": holo.index_gap_detected,
        "skillz_gap_detected": holo.skillz_gap_detected,
    }
    return _canonical_digest(payload)


def _evaluate_holoindex_policy(work_order: RedDogGovernedWorkOrder) -> List[str]:
    """Addendum A — HoloIndex evidence enforcement at policy layer."""
    reasons: List[str] = []
    holo = work_order.holoindex_evidence
    op_norm = _normalize_operation(work_order.requested_operation)
    write_sensitive = _is_write_sensitive_operation(op_norm)

    if holo is None:
        return ["missing_holoindex_evidence"]

    required_fields = {
        "holoindex_status": holo.holoindex_status,
        "retrieval_quality": holo.retrieval_quality,
        "applicable_wsps": holo.applicable_wsps,
        "evidence_refs": holo.evidence_refs,
    }
    if write_sensitive:
        for name, value in required_fields.items():
            if not value:
                reasons.append("missing_holoindex_evidence")

    if holo.retrieval_quality == "INDEX_GAP" or holo.index_gap_detected:
        if write_sensitive:
            reasons.append("index_gap_blocks_write_operation")
        elif op_norm not in DOCS_ONLY_OPERATIONS:
            reasons.append("index_gap_blocks_non_docs_operation")

    if write_sensitive and holo.retrieval_quality in {"LOW", "MEDIUM"}:
        if not holo.direct_read_fallback_used:
            reasons.append("weak_wsp_recall_requires_direct_read_fallback")
        elif not holo.evidence_refs:
            reasons.append("weak_wsp_recall_missing_direct_read_ref")

    return reasons


def _permission_supports_operation(permission_level: str, operation: str) -> bool:
    op_norm = _normalize_operation(operation)
    can_read, can_write, _ = permission_to_capabilities(permission_level)
    if op_norm in DOCS_ONLY_OPERATIONS:
        return can_read
    if _is_write_sensitive_operation(op_norm):
        return can_write
    return can_read


def evaluate_work_order_policy_gate(
    order: Union[RedDogGovernedWorkOrder, Mapping[str, Any]],
    *,
    now: Optional[datetime] = None,
    seen_nonces: Optional[MutableSet[str]] = None,
    permission_ttl_seconds: int = DEFAULT_PERMISSION_TTL_SECONDS,
    permission_expires_at: Optional[str] = None,
) -> PolicyGateReceipt:
    """Evaluate OpenClaw policy gate for a governed work order. No execution performed."""
    if isinstance(order, Mapping):
        work_order = _work_order_from_mapping(order)
    else:
        work_order = order

    checked = _utc_now(now)
    gates_checked: List[str] = ["dry_run_validator"]
    rejection_reasons: List[str] = []

    dry_run = validate_work_order_dryrun(work_order, now=checked, seen_nonces=seen_nonces)
    gates_checked.extend(dry_run.gates_checked)
    if dry_run.decision == DECISION_REJECT:
        rejection_reasons.extend(dry_run.rejection_reasons)

    gates_checked.append("holoindex_evidence_policy")
    holo_reasons = _evaluate_holoindex_policy(work_order)
    rejection_reasons.extend(holo_reasons)

    snap = work_order.repo_permission_snapshot
    truth = permission_truth_label(snap.permission_level, snap.source)
    gates_checked.append("permission_snapshot_freshness")
    fresh = _permission_snapshot_fresh(
        snap.captured_at,
        now=checked,
        ttl_seconds=permission_ttl_seconds,
        expires_at=permission_expires_at,
    )
    if not fresh:
        rejection_reasons.append("stale_permission_snapshot")

    gates_checked.append("permission_capability")
    op_norm = _normalize_operation(work_order.requested_operation)
    if not _permission_supports_operation(snap.permission_level, work_order.requested_operation):
        rejection_reasons.append("insufficient_permission_for_operation")

    if truth == TRUTH_NEEDS_VERIFICATION and _is_write_sensitive_operation(op_norm):
        rejection_reasons.append("permission_needs_verification")

    permission_expiry_dt: Optional[datetime] = None
    if permission_expires_at:
        try:
            permission_expiry_dt = _parse_iso8601(permission_expires_at)
        except ValueError:
            pass
    elif snap.captured_at:
        try:
            permission_expiry_dt = _parse_iso8601(snap.captured_at) + timedelta(
                seconds=max(1, permission_ttl_seconds)
            )
        except ValueError:
            pass

    work_order_expiry_dt: Optional[datetime] = None
    try:
        work_order_expiry_dt = _parse_iso8601(work_order.expiry)
    except ValueError:
        pass

    next_check_candidates = [dt for dt in (work_order_expiry_dt, permission_expiry_dt) if dt is not None]
    next_required_check_at = _iso8601(min(next_check_candidates)) if next_check_candidates else None

    deduped_reasons = list(dict.fromkeys(rejection_reasons))

    if deduped_reasons:
        decision = POLICY_REJECT
    elif dry_run.decision == DECISION_ACCEPT_WITH_GAP or (
        holo := work_order.holoindex_evidence
    ) and (holo.retrieval_quality == "INDEX_GAP" or holo.index_gap_detected) and op_norm in DOCS_ONLY_OPERATIONS:
        decision = POLICY_ACCEPT_WITH_RETRIEVAL_GAP
    elif dry_run.decision == DECISION_ACCEPT:
        decision = POLICY_ACCEPT
    else:
        decision = POLICY_REJECT
        if "policy_gate_unexpected_dry_run_state" not in deduped_reasons:
            deduped_reasons.append("policy_gate_unexpected_dry_run_state")

    holo_digest = _holoindex_evidence_digest(work_order)
    id_seed = _canonical_digest(
        {
            "work_order_id": work_order.work_order_id,
            "checked_at": _iso8601(checked),
            "nonce": work_order.nonce,
        }
    )
    receipt_id = f"policy-gate-{work_order.work_order_id}-{id_seed[:12]}"

    receipt_core = {
        "receipt_id": receipt_id,
        "work_order_id": work_order.work_order_id,
        "decision": decision,
        "rejection_reasons": deduped_reasons,
        "gates_checked": gates_checked,
        "dry_run_receipt_digest": dry_run.receipt_digest,
        "permission_snapshot_digest": snap.digest,
        "permission_truth_label": truth,
        "holoindex_evidence_digest": holo_digest,
        "no_execution_performed": True,
        "checked_at": _iso8601(checked),
        "expires_at": work_order.expiry,
        "next_required_check_at": next_required_check_at,
    }
    receipt_digest = _canonical_digest(receipt_core)

    return PolicyGateReceipt(
        receipt_digest=receipt_digest,
        **receipt_core,
    )
