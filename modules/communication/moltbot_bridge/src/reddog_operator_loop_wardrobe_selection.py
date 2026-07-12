"""RedDog operator-loop wardrobe selection dry-run.

Slice: REDDOG_OPERATOR_LOOP_WARDROBE_SELECTION_DRYRUN_PHASE1
Contract: docs/audits/architecture/REDDOG_OPERATOR_LOOP_WARDROBE_SELECTION_CONTRACT_PHASE1.md

This module turns a normalized 012 work focus plus observed retrieval evidence into a
deterministic WSP_97/WSP_95 wardrobe-selection receipt. It is a pure planner: no extension
runtime wiring, no live enqueue, no shell, no worktree, and no HoloIndex mutation.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

WARDROBE_SOLO_RETRIEVAL = "wsp97_solo_retrieval"
WARDROBE_ARCHITECT_AUDIT = "wsp97_architect_audit"
WARDROBE_IMPLEMENTATION_SLICE = "wsp97_implementation_slice"
WARDROBE_SOVEREIGN_EXECUTION = "wsp97_sovereign_execution"

EXECUTION_ADVISORY_ONLY = "advisory_only"
EXECUTION_AUDIT_ONLY = "audit_only"
EXECUTION_WORKER_DRAFT_PR = "worker_draft_pr"
EXECUTION_GOVERNED_CANDIDATE = "governed_execution_candidate"

AUTHORITY_NONE = "no_authority"
AUTHORITY_DRAFT_PR_ONLY = "draft_pr_only"
AUTHORITY_SIGNED_VALVE_REQUIRED = "signed_valve_required"
AUTHORITY_SOVEREIGN_TOKEN_REQUIRED = "sovereign_token_required"

IMPLEMENTATION_STATUS_SPECIFIED_NOT_IMPLEMENTED = "SPECIFIED_NOT_IMPLEMENTED"

WARDROBE_SELECTION_ACCEPT = "WARDROBE_SELECTION_ACCEPT"
WARDROBE_SELECTION_REJECT = "WARDROBE_SELECTION_REJECT"

FRESHNESS_FRESH = "fresh"
FRESHNESS_STALE = "stale"
FRESHNESS_UNKNOWN = "unknown"
FRESHNESS_INDEX_GAP = "index_gap"

_WHITESPACE_RE = re.compile(r"\s+")
_WSP_RE = re.compile(r"\bWSP[_\s-]?(\d{1,3})\b", re.IGNORECASE)

_SOVEREIGN_TERMS = (
    "live enqueue",
    "live writer",
    "worktree",
    "shell",
    "merge authority",
    "merge pr",
    "merge pull request",
    "push",
    "reward",
    "wallet",
    "sovereign token",
    "valve_open",
    "spawn workers",
    "recursive worker",
    "worker orchestration",
)

_IMPLEMENTATION_TERMS = (
    "implement",
    "fix",
    "add",
    "edit",
    "build",
    "test",
    "draft pr",
    "pull request",
    "branch",
    "slice",
)

_AUDIT_TERMS = (
    "audit",
    "architecture",
    "contract",
    "security",
    "governance",
    "authority",
    "holoindex",
    "wsp",
    "openclaw",
    "hermes",
    "wre",
    "wardrobe",
    "skillz",
    "operator loop",
)

_REPO_TERMS = (
    "repo",
    "codebase",
    "module",
    "file",
    ".py",
    ".js",
    ".md",
    "wsp",
    "holoindex",
    "reddog",
    "openclaw",
    "hermes",
    "wre",
)

_SOVEREIGN_AUTHORITY_REQUESTS = frozenset(
    {
        "live_enqueue",
        "worktree_write",
        "shell",
        "merge",
        "reward",
        "worker_orchestration",
    }
)

_SOVEREIGN_TOKEN_REQUESTS = frozenset({"worktree_write", "shell", "merge", "reward"})


@dataclass(frozen=True)
class RedDogOperatorLoopWardrobeSelectionReceipt:
    selection_id: str
    work_focus_digest: str
    selected_wardrobe: str
    wsp97_depth: str
    selected_context_mode: str
    selected_model_mode: str
    selected_effort: str
    execution_plane: str
    wre_required: bool
    authority_boundary: str
    holoindex_query_digest: str
    holoindex_freshness_label: str
    index_gap_detected: bool
    direct_read_required: bool
    skillz_candidates: List[str]
    lane_refs: List[str]
    rejection_reasons: List[str]
    no_execution_performed: bool
    no_enqueue_performed: bool
    implementation_status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RedDogOperatorLoopWardrobeSelectionResult:
    decision: str
    receipt: RedDogOperatorLoopWardrobeSelectionReceipt
    governing_wsps: List[str]
    authority_request: str

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["receipt"] = self.receipt.to_dict()
        return payload


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", str(value or "").strip())


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _dedupe(values: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def _normalize_authority_request(value: str) -> str:
    text = _normalize_text(value).lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "none": "none",
        "advisory": "none",
        "audit": "none",
        "draft": "draft_pr",
        "draft_pr": "draft_pr",
        "pr": "draft_pr",
        "pull_request": "draft_pr",
        "live_enqueue": "live_enqueue",
        "enqueue": "live_enqueue",
        "worktree": "worktree_write",
        "worktree_write": "worktree_write",
        "shell": "shell",
        "merge": "merge",
        "reward": "reward",
        "worker": "worker_orchestration",
        "workers": "worker_orchestration",
        "worker_orchestration": "worker_orchestration",
    }
    return aliases.get(text, text or "none")


def _derive_wsps(work_focus: str, supplied_wsps: Optional[Sequence[str]]) -> List[str]:
    wsps = ["WSP_00", "WSP_97", "WSP_95", "WSP_15"]
    for item in supplied_wsps or []:
        text = str(item or "").strip()
        if text:
            wsps.append(text.replace(" ", "_").replace("-", "_"))
    for match in _WSP_RE.finditer(work_focus):
        wsps.append(f"WSP_{match.group(1)}")
    return _dedupe(wsps)


def _holoindex_query_digest(holoindex_evidence: Optional[Mapping[str, Any]]) -> str:
    evidence = dict(holoindex_evidence or {})
    explicit = evidence.get("holoindex_query_digest") or evidence.get("query_digest")
    if explicit:
        return str(explicit)
    digest_payload = {
        "query": evidence.get("holoindex_query") or evidence.get("query") or "",
        "status": evidence.get("holoindex_status") or evidence.get("status") or "",
        "code_hits": _hit_paths(evidence.get("code_hits") or evidence.get("code") or []),
        "wsp_hits": _hit_paths(evidence.get("wsp_hits") or evidence.get("wsps") or []),
        "skill_hits": _hit_paths(evidence.get("skill_hits") or evidence.get("skills") or []),
    }
    return _canonical_digest(digest_payload)


def _hit_paths(values: Any) -> List[str]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return []
    paths: List[str] = []
    for value in values:
        if isinstance(value, Mapping):
            candidate = (
                value.get("path")
                or value.get("location")
                or value.get("wsp")
                or value.get("skill_name")
                or value.get("title")
            )
            if candidate:
                paths.append(str(candidate))
        else:
            paths.append(str(value))
    return _dedupe(paths)


def _index_gap_detected(holoindex_evidence: Optional[Mapping[str, Any]]) -> bool:
    evidence = dict(holoindex_evidence or {})
    return (
        evidence.get("index_gap_detected") is True
        or str(evidence.get("retrieval_quality") or "").upper() == "INDEX_GAP"
        or str(evidence.get("holoindex_status") or "").upper() == "INDEX_GAP"
    )


def _holoindex_freshness_label(holoindex_evidence: Optional[Mapping[str, Any]]) -> str:
    evidence = dict(holoindex_evidence or {})
    if _index_gap_detected(evidence):
        return FRESHNESS_INDEX_GAP
    explicit = str(evidence.get("holoindex_freshness_label") or evidence.get("freshness") or "")
    if explicit in {FRESHNESS_FRESH, FRESHNESS_STALE, FRESHNESS_UNKNOWN}:
        return explicit
    status = str(evidence.get("holoindex_status") or evidence.get("status") or "").lower()
    if status in {"bundle_json_ok", "ok", "ready"}:
        return FRESHNESS_FRESH
    if status in {"stale", "offline"}:
        return FRESHNESS_STALE
    return FRESHNESS_UNKNOWN


def _skillz_candidates(
    work_focus: str,
    holoindex_evidence: Optional[Mapping[str, Any]],
) -> List[str]:
    evidence = dict(holoindex_evidence or {})
    candidates: List[str] = []
    for key in ("skill_hits", "skills", "skillz_hits"):
        hits = evidence.get(key)
        if isinstance(hits, Sequence) and not isinstance(hits, (str, bytes)):
            for hit in hits:
                if isinstance(hit, Mapping):
                    value = hit.get("skill_name") or hit.get("path") or hit.get("description")
                else:
                    value = hit
                if value:
                    candidates.append(str(value))
    if _contains_any(work_focus, ("skillz", "wardrobe", "operator loop")):
        candidates.append("wsp95_wardrobe_selection")
    return _dedupe(candidates)[:8]


def _select_profile(
    normalized_focus: str,
    authority_request: str,
) -> Tuple[str, str, str, bool]:
    if authority_request in _SOVEREIGN_AUTHORITY_REQUESTS or _contains_any(
        normalized_focus, _SOVEREIGN_TERMS
    ):
        return (
            WARDROBE_SOVEREIGN_EXECUTION,
            "sovereign",
            EXECUTION_GOVERNED_CANDIDATE,
            True,
        )
    if authority_request == "draft_pr" or _contains_any(normalized_focus, _IMPLEMENTATION_TERMS):
        return (
            WARDROBE_IMPLEMENTATION_SLICE,
            "implementation",
            EXECUTION_WORKER_DRAFT_PR,
            True,
        )
    if _contains_any(normalized_focus, _AUDIT_TERMS):
        return (WARDROBE_ARCHITECT_AUDIT, "audit", EXECUTION_AUDIT_ONLY, False)
    return (WARDROBE_SOLO_RETRIEVAL, "solo", EXECUTION_ADVISORY_ONLY, False)


def _select_modes(
    selected_wardrobe: str,
    selected_context_mode: str,
    selected_model_mode: str,
    selected_effort: str,
) -> Tuple[str, str, str]:
    context = _normalize_text(selected_context_mode).lower() or "auto"
    model = _normalize_text(selected_model_mode).lower() or "auto"
    effort = _normalize_text(selected_effort).lower() or "auto"

    if context == "auto":
        if selected_wardrobe == WARDROBE_SOLO_RETRIEVAL:
            context = "wsp_holo"
        elif selected_wardrobe == WARDROBE_ARCHITECT_AUDIT:
            context = "wsp_holo_skillz"
        else:
            context = "wsp_holo_git_skillz"
    if model == "auto":
        model = "openrouter_single" if selected_wardrobe == WARDROBE_SOLO_RETRIEVAL else "foundups_fusion"
    if effort == "auto":
        if selected_wardrobe == WARDROBE_SOLO_RETRIEVAL:
            effort = "regular"
        elif selected_wardrobe == WARDROBE_ARCHITECT_AUDIT:
            effort = "high"
        else:
            effort = "ultra"
    return context, model, effort


def _authority_boundary(selected_wardrobe: str, authority_request: str) -> str:
    if selected_wardrobe == WARDROBE_SOVEREIGN_EXECUTION:
        if authority_request in _SOVEREIGN_TOKEN_REQUESTS:
            return AUTHORITY_SOVEREIGN_TOKEN_REQUIRED
        return AUTHORITY_SIGNED_VALVE_REQUIRED
    if selected_wardrobe == WARDROBE_IMPLEMENTATION_SLICE:
        return AUTHORITY_DRAFT_PR_ONLY
    return AUTHORITY_NONE


def _repo_sensitive_work(work_focus: str, authority_request: str, required_targets: Sequence[str]) -> bool:
    return bool(required_targets) or authority_request != "none" or _contains_any(work_focus, _REPO_TERMS)


def select_reddog_operator_loop_wardrobe_dryrun(
    work_focus: str,
    *,
    principal_ref: str = "unknown",
    authority_request: str = "none",
    selected_context_mode: str = "auto",
    selected_model_mode: str = "auto",
    selected_effort: str = "auto",
    holoindex_evidence: Optional[Mapping[str, Any]] = None,
    required_targets: Optional[Sequence[str]] = None,
    target_recall_ok: Optional[bool] = None,
    wsp_refs: Optional[Sequence[str]] = None,
    lane_refs: Optional[Sequence[str]] = None,
    continuation_packet_digest: Optional[str] = None,
) -> RedDogOperatorLoopWardrobeSelectionResult:
    """Select the RedDog WSP_97/WSP_95 wardrobe profile without executing work."""

    normalized_focus = _normalize_text(work_focus)
    normalized_authority = _normalize_authority_request(authority_request)
    targets = _dedupe(required_targets or [])
    lanes = _dedupe(lane_refs or [])
    governing_wsps = _derive_wsps(normalized_focus, wsp_refs)
    holo = dict(holoindex_evidence or {})

    selected_wardrobe, wsp97_depth, execution_plane, wre_required = _select_profile(
        normalized_focus, normalized_authority
    )
    context_mode, model_mode, effort = _select_modes(
        selected_wardrobe, selected_context_mode, selected_model_mode, selected_effort
    )
    boundary = _authority_boundary(selected_wardrobe, normalized_authority)
    index_gap = _index_gap_detected(holo)
    freshness = _holoindex_freshness_label(holo)
    repo_sensitive = _repo_sensitive_work(normalized_focus, normalized_authority, targets)

    rejection_reasons: List[str] = []
    if repo_sensitive and not holo:
        rejection_reasons.append("holoindex_evidence_missing_for_repo_work")
    if targets and target_recall_ok is False:
        rejection_reasons.append("required_target_recall_not_ok")
    if index_gap and selected_wardrobe in {
        WARDROBE_IMPLEMENTATION_SLICE,
        WARDROBE_SOVEREIGN_EXECUTION,
    }:
        rejection_reasons.append("write_sensitive_index_gap")
    if selected_wardrobe == WARDROBE_SOVEREIGN_EXECUTION:
        rejection_reasons.append("sovereign_authority_requires_downstream_signed_valve")
    if not governing_wsps and normalized_authority != "none":
        rejection_reasons.append("missing_governing_wsp_for_authority_request")

    direct_read_required = bool(targets) or (repo_sensitive and (index_gap or target_recall_ok is False))
    work_focus_digest = _canonical_digest({"work_focus": normalized_focus})
    query_digest = _holoindex_query_digest(holo)
    candidates = _skillz_candidates(normalized_focus, holo)

    receipt_payload: Dict[str, Any] = {
        "work_focus_digest": work_focus_digest,
        "principal_ref": str(principal_ref or "unknown"),
        "authority_request": normalized_authority,
        "selected_wardrobe": selected_wardrobe,
        "wsp97_depth": wsp97_depth,
        "selected_context_mode": context_mode,
        "selected_model_mode": model_mode,
        "selected_effort": effort,
        "execution_plane": execution_plane,
        "wre_required": wre_required,
        "authority_boundary": boundary,
        "holoindex_query_digest": query_digest,
        "holoindex_freshness_label": freshness,
        "index_gap_detected": index_gap,
        "direct_read_required": direct_read_required,
        "skillz_candidates": candidates,
        "lane_refs": lanes,
        "wsp_refs": governing_wsps,
        "continuation_packet_digest": str(continuation_packet_digest or ""),
        "rejection_reasons": _dedupe(rejection_reasons),
        "no_execution_performed": True,
        "no_enqueue_performed": True,
        "implementation_status": IMPLEMENTATION_STATUS_SPECIFIED_NOT_IMPLEMENTED,
    }
    selection_id = _canonical_digest(receipt_payload)

    receipt = RedDogOperatorLoopWardrobeSelectionReceipt(
        selection_id=selection_id,
        work_focus_digest=work_focus_digest,
        selected_wardrobe=selected_wardrobe,
        wsp97_depth=wsp97_depth,
        selected_context_mode=context_mode,
        selected_model_mode=model_mode,
        selected_effort=effort,
        execution_plane=execution_plane,
        wre_required=wre_required,
        authority_boundary=boundary,
        holoindex_query_digest=query_digest,
        holoindex_freshness_label=freshness,
        index_gap_detected=index_gap,
        direct_read_required=direct_read_required,
        skillz_candidates=candidates,
        lane_refs=lanes,
        rejection_reasons=_dedupe(rejection_reasons),
        no_execution_performed=True,
        no_enqueue_performed=True,
        implementation_status=IMPLEMENTATION_STATUS_SPECIFIED_NOT_IMPLEMENTED,
    )
    decision = WARDROBE_SELECTION_REJECT if receipt.rejection_reasons else WARDROBE_SELECTION_ACCEPT
    return RedDogOperatorLoopWardrobeSelectionResult(
        decision=decision,
        receipt=receipt,
        governing_wsps=governing_wsps,
        authority_request=normalized_authority,
    )
