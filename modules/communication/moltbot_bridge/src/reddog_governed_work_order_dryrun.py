"""RedDog governed repo work-order dry-run validator (no mutation).

Slice: REDDOG_GOVERNED_REPO_WORK_ORDER_DRYRUN_PHASE1
Contract: docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md

RedDog receives bounded delegated capability per work order after fresh verification.
This module validates envelope + policy semantics only — no GitHub, branch, PR, write,
shell, or merge.

WAE-L1 alignment (Addendum B — mapping only, no WAE refactor this slice):
| WAE-L1 direction field      | RedDogGovernedWorkOrder field   |
|-----------------------------|---------------------------------|
| direction_id                | work_order_id                   |
| created_at                  | created_at                      |
| principal_id                | authenticated_principal         |
| target_repo                 | repo_full_name                  |
| proposed_action             | requested_operation             |
| authority_hint              | authority_tier                  |
| path_scope                  | allowed_paths / denied_paths    |
| branch_hint                 | branch_name / base_ref          |
| holo_evidence_packet        | holoindex_evidence              |
| wsp_tags                    | wsp_applicability               |
| skillz_hints                | skillz_candidates               |
| advisory_digest             | evidence_digest                 |
| source_packet               | advisory_only_source_packet     |
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, MutableSet, Optional, Sequence, Union

DECISION_ACCEPT = "WOULD_ACCEPT"
DECISION_REJECT = "WOULD_REJECT"
DECISION_ACCEPT_WITH_GAP = "WOULD_ACCEPT_WITH_RETRIEVAL_GAP"

RETRIEVAL_QUALITIES = frozenset({"HIGH", "MEDIUM", "LOW", "INDEX_GAP"})

WRITE_SENSITIVE_OPERATIONS = frozenset(
    {
        "repo",
        "write",
        "branch",
        "pr",
        "source",
        "feature_slice",
        "test_fix",
        "docs_patch",
        "merge_request",
        "security",
        "auth",
        "runtime",
    }
)

DOCS_ONLY_OPERATIONS = frozenset({"audit_only", "docs_audit", "docs_only"})

FORBIDDEN_OPERATION_TOKENS = frozenset(
    {
        "admin",
        "permission_management",
        "grant_permission",
        "merge_autonomous",
        "autonomous_merge",
        "credential",
        "secret",
        "oauth_token",
        "deploy_production",
    }
)

FORBIDDEN_PATH_GLOBS = (
    ".env",
    ".env.*",
    "**/.env",
    "**/credentials*",
    "**/secrets/**",
    "**/.git/**",
)

PROTECTED_BASE_REFS = frozenset({"main", "master"})


@dataclass
class RepoPermissionSnapshot:
    permission_level: str
    captured_at: str
    source: str
    digest: str


@dataclass
class AdvisoryOnlySourcePacket:
    work_focus_digest: str
    wsp_prompt_digest: str
    copy_md_run_trace_digest: str


@dataclass
class HoloIndexEvidencePacket:
    holoindex_query: str
    holoindex_status: str
    code_hits: List[str] = field(default_factory=list)
    wsp_hits: List[str] = field(default_factory=list)
    skillz_hits: List[str] = field(default_factory=list)
    direct_read_fallback_used: bool = False
    index_gap_detected: bool = False
    applicable_wsps: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    retrieval_quality: str = "LOW"
    skillz_gap_detected: bool = False


@dataclass
class RedDogGovernedWorkOrder:
    work_order_id: str
    created_at: str
    red_dog_instance_id: str
    authenticated_principal: str
    principal_provider: str
    repo_full_name: str
    repo_permission_snapshot: RepoPermissionSnapshot
    requested_operation: str
    authority_tier: str
    allowed_paths: List[str]
    denied_paths: List[str]
    branch_name: str
    base_ref: str
    task_summary: str
    wsp_applicability: List[str]
    holoindex_evidence_refs: List[str]
    skillz_candidates: List[str]
    required_tests: List[str]
    required_policy_gates: List[str]
    required_reviewers: List[str]
    sentinel_checks: List[str]
    rollback_plan: str
    expiry: str
    nonce: str
    evidence_digest: str
    advisory_only_source_packet: AdvisoryOnlySourcePacket
    holoindex_evidence: Optional[HoloIndexEvidencePacket] = None


@dataclass
class DryRunReceipt:
    decision: str
    rejection_reasons: List[str]
    gates_checked: List[str]
    no_mutation_performed: bool
    receipt_digest: str
    work_order_id: str


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


def _non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return len(value) > 0
    return True


def _normalize_operation(op: str) -> str:
    return op.strip().lower().replace("-", "_").replace(" ", "_")


def _is_write_sensitive_operation(operation: str) -> bool:
    norm = _normalize_operation(operation)
    if norm in DOCS_ONLY_OPERATIONS:
        return False
    if norm in WRITE_SENSITIVE_OPERATIONS:
        return True
    return any(token in norm for token in ("write", "branch", "pr", "repo", "source", "auth", "runtime", "security"))


def _path_matches_any(path: str, patterns: Sequence[str]) -> bool:
    normalized = path.replace("\\", "/")
    for pattern in patterns:
        pat = pattern.replace("\\", "/")
        if fnmatch.fnmatch(normalized, pat) or fnmatch.fnmatch(normalized, f"**/{pat}"):
            return True
    return False


def _forbidden_path_overlap(paths: Iterable[str]) -> List[str]:
    hits: List[str] = []
    for path in paths:
        if _path_matches_any(path, FORBIDDEN_PATH_GLOBS):
            hits.append(path)
    return hits


def _skillz_handoff_claimed(order: RedDogGovernedWorkOrder) -> bool:
    summary = order.task_summary.lower()
    if order.skillz_candidates:
        return False
    if "skillz" in summary or "wardrobe" in summary or "rolodex" in summary:
        return True
    gates = " ".join(order.required_policy_gates).lower()
    return "skillz" in gates or "wardrobe" in gates


def _work_order_from_mapping(data: Mapping[str, Any]) -> RedDogGovernedWorkOrder:
    snap = data["repo_permission_snapshot"]
    packet = data["advisory_only_source_packet"]
    holo_raw = data.get("holoindex_evidence")
    holo = None
    if holo_raw is not None:
        holo = HoloIndexEvidencePacket(
            holoindex_query=str(holo_raw["holoindex_query"]),
            holoindex_status=str(holo_raw["holoindex_status"]),
            code_hits=list(holo_raw.get("code_hits") or []),
            wsp_hits=list(holo_raw.get("wsp_hits") or []),
            skillz_hits=list(holo_raw.get("skillz_hits") or []),
            direct_read_fallback_used=bool(holo_raw.get("direct_read_fallback_used")),
            index_gap_detected=bool(holo_raw.get("index_gap_detected")),
            applicable_wsps=list(holo_raw.get("applicable_wsps") or []),
            evidence_refs=list(holo_raw.get("evidence_refs") or []),
            retrieval_quality=str(holo_raw.get("retrieval_quality") or "LOW"),
            skillz_gap_detected=bool(holo_raw.get("skillz_gap_detected")),
        )
    return RedDogGovernedWorkOrder(
        work_order_id=str(data["work_order_id"]),
        created_at=str(data["created_at"]),
        red_dog_instance_id=str(data["red_dog_instance_id"]),
        authenticated_principal=str(data["authenticated_principal"]),
        principal_provider=str(data["principal_provider"]),
        repo_full_name=str(data["repo_full_name"]),
        repo_permission_snapshot=RepoPermissionSnapshot(
            permission_level=str(snap["permission_level"]),
            captured_at=str(snap["captured_at"]),
            source=str(snap["source"]),
            digest=str(snap["digest"]),
        ),
        requested_operation=str(data["requested_operation"]),
        authority_tier=str(data["authority_tier"]),
        allowed_paths=list(data.get("allowed_paths") or []),
        denied_paths=list(data.get("denied_paths") or []),
        branch_name=str(data["branch_name"]),
        base_ref=str(data["base_ref"]),
        task_summary=str(data["task_summary"]),
        wsp_applicability=list(data.get("wsp_applicability") or []),
        holoindex_evidence_refs=list(data.get("holoindex_evidence_refs") or []),
        skillz_candidates=list(data.get("skillz_candidates") or []),
        required_tests=list(data.get("required_tests") or []),
        required_policy_gates=list(data.get("required_policy_gates") or []),
        required_reviewers=list(data.get("required_reviewers") or []),
        sentinel_checks=list(data.get("sentinel_checks") or []),
        rollback_plan=str(data.get("rollback_plan") or ""),
        expiry=str(data["expiry"]),
        nonce=str(data["nonce"]),
        evidence_digest=str(data["evidence_digest"]),
        advisory_only_source_packet=AdvisoryOnlySourcePacket(
            work_focus_digest=str(packet["work_focus_digest"]),
            wsp_prompt_digest=str(packet["wsp_prompt_digest"]),
            copy_md_run_trace_digest=str(packet["copy_md_run_trace_digest"]),
        ),
        holoindex_evidence=holo,
    )


def validate_work_order_dryrun(
    order: Union[RedDogGovernedWorkOrder, Mapping[str, Any]],
    *,
    now: Optional[datetime] = None,
    seen_nonces: Optional[MutableSet[str]] = None,
) -> DryRunReceipt:
    """Validate a governed work order without performing any mutation."""
    if isinstance(order, Mapping):
        work_order = _work_order_from_mapping(order)
    else:
        work_order = order

    gates_checked: List[str] = []
    rejection_reasons: List[str] = []
    now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    nonce_store = seen_nonces if seen_nonces is not None else set()

    required_scalar_fields = {
        "work_order_id": work_order.work_order_id,
        "created_at": work_order.created_at,
        "red_dog_instance_id": work_order.red_dog_instance_id,
        "authenticated_principal": work_order.authenticated_principal,
        "principal_provider": work_order.principal_provider,
        "repo_full_name": work_order.repo_full_name,
        "requested_operation": work_order.requested_operation,
        "authority_tier": work_order.authority_tier,
        "branch_name": work_order.branch_name,
        "base_ref": work_order.base_ref,
        "task_summary": work_order.task_summary,
        "rollback_plan": work_order.rollback_plan,
        "expiry": work_order.expiry,
        "nonce": work_order.nonce,
        "evidence_digest": work_order.evidence_digest,
    }
    gates_checked.append("required_fields")
    for name, value in required_scalar_fields.items():
        if not _non_empty(value):
            rejection_reasons.append(f"missing_required_field:{name}")

    snap = work_order.repo_permission_snapshot
    gates_checked.append("repo_permission_snapshot")
    for name, value in (
        ("permission_level", snap.permission_level),
        ("captured_at", snap.captured_at),
        ("source", snap.source),
        ("digest", snap.digest),
    ):
        if not _non_empty(value):
            rejection_reasons.append(f"missing_required_field:repo_permission_snapshot.{name}")

    packet = work_order.advisory_only_source_packet
    gates_checked.append("advisory_only_source_packet")
    for name, value in (
        ("work_focus_digest", packet.work_focus_digest),
        ("wsp_prompt_digest", packet.wsp_prompt_digest),
        ("copy_md_run_trace_digest", packet.copy_md_run_trace_digest),
    ):
        if not _non_empty(value):
            rejection_reasons.append(f"missing_required_field:advisory_only_source_packet.{name}")

    list_fields = {
        "allowed_paths": work_order.allowed_paths,
        "denied_paths": work_order.denied_paths,
        "wsp_applicability": work_order.wsp_applicability,
        "holoindex_evidence_refs": work_order.holoindex_evidence_refs,
        "skillz_candidates": work_order.skillz_candidates,
        "required_tests": work_order.required_tests,
        "required_policy_gates": work_order.required_policy_gates,
        "required_reviewers": work_order.required_reviewers,
        "sentinel_checks": work_order.sentinel_checks,
    }
    gates_checked.append("required_list_fields")
    for name, value in list_fields.items():
        if value is None:
            rejection_reasons.append(f"missing_required_field:{name}")

    gates_checked.append("expiry")
    try:
        expiry_dt = _parse_iso8601(work_order.expiry)
        if now_utc > expiry_dt:
            rejection_reasons.append("expired_work_order")
    except ValueError:
        rejection_reasons.append("invalid_expiry_timestamp")

    gates_checked.append("nonce_replay")
    if work_order.nonce in nonce_store:
        rejection_reasons.append("replayed_nonce")
    else:
        nonce_store.add(work_order.nonce)

    gates_checked.append("forbidden_operations")
    op_norm = _normalize_operation(work_order.requested_operation)
    tier_norm = work_order.authority_tier.strip().lower()
    if tier_norm in {"admin", "autonomous_f0_merge", "merge_autonomous"}:
        rejection_reasons.append("forbidden_authority_tier")
    if any(token in op_norm for token in FORBIDDEN_OPERATION_TOKENS):
        rejection_reasons.append("forbidden_requested_operation")
    if snap.permission_level.strip().lower() == "admin" and _is_write_sensitive_operation(op_norm):
        rejection_reasons.append("admin_permission_snapshot_write_blocked")

    gates_checked.append("main_mutation")
    branch = work_order.branch_name.strip().lower()
    if branch in PROTECTED_BASE_REFS and _is_write_sensitive_operation(op_norm):
        rejection_reasons.append("direct_main_branch_mutation")
    if branch == work_order.base_ref.strip().lower() and _is_write_sensitive_operation(op_norm):
        rejection_reasons.append("branch_equals_base_ref_for_write")

    gates_checked.append("path_scope")
    forbidden_allowed = _forbidden_path_overlap(work_order.allowed_paths)
    if forbidden_allowed:
        rejection_reasons.append("forbidden_paths_in_allowed_scope")
    forbidden_denied = _forbidden_path_overlap(work_order.denied_paths)
    if forbidden_denied and not work_order.denied_paths:
        rejection_reasons.append("invalid_denied_paths")
    overlap = [p for p in work_order.denied_paths if p in work_order.allowed_paths]
    if overlap:
        rejection_reasons.append("denied_path_also_allowed")
    if _is_write_sensitive_operation(op_norm) and not work_order.allowed_paths:
        rejection_reasons.append("empty_allowed_paths_for_write_operation")

    gates_checked.append("holoindex_evidence")
    index_gap_docs_only = False
    holo = work_order.holoindex_evidence
    if holo is None:
        rejection_reasons.append("missing_holoindex_evidence")
    else:
        if holo.retrieval_quality not in RETRIEVAL_QUALITIES:
            rejection_reasons.append("invalid_retrieval_quality")
        if not _non_empty(holo.holoindex_query) or not _non_empty(holo.holoindex_status):
            rejection_reasons.append("missing_holoindex_evidence")
        write_sensitive = _is_write_sensitive_operation(op_norm)
        if write_sensitive:
            if not holo.applicable_wsps and not holo.wsp_hits:
                rejection_reasons.append("missing_applicable_wsp_evidence")
            if holo.retrieval_quality == "INDEX_GAP" or holo.index_gap_detected:
                rejection_reasons.append("index_gap_blocks_write_operation")
            elif holo.retrieval_quality in {"LOW", "MEDIUM"} and not holo.direct_read_fallback_used:
                rejection_reasons.append("weak_wsp_recall_requires_direct_read_fallback")
        elif holo.retrieval_quality == "INDEX_GAP" or holo.index_gap_detected:
            index_gap_docs_only = True
            gates_checked.append("index_gap_docs_only_exception")

    gates_checked.append("skillz_handoff")
    if _skillz_handoff_claimed(work_order):
        holo_skillz_ok = bool(work_order.skillz_candidates)
        if holo is not None:
            holo_skillz_ok = holo_skillz_ok or bool(holo.skillz_hits) or holo.skillz_gap_detected
        if not holo_skillz_ok:
            rejection_reasons.append("skillz_handoff_missing_evidence")

    if rejection_reasons:
        decision = DECISION_REJECT
    elif index_gap_docs_only:
        decision = DECISION_ACCEPT_WITH_GAP
    else:
        decision = DECISION_ACCEPT

    receipt_core = {
        "decision": decision,
        "rejection_reasons": rejection_reasons,
        "gates_checked": gates_checked,
        "no_mutation_performed": True,
        "work_order_id": work_order.work_order_id,
    }
    return DryRunReceipt(
        decision=decision,
        rejection_reasons=rejection_reasons,
        gates_checked=gates_checked,
        no_mutation_performed=True,
        receipt_digest=_canonical_digest(receipt_core),
        work_order_id=work_order.work_order_id,
    )


def work_order_to_dict(order: RedDogGovernedWorkOrder) -> Dict[str, Any]:
    """Serialize a work order for receipts and tests."""
    data = asdict(order)
    return data
