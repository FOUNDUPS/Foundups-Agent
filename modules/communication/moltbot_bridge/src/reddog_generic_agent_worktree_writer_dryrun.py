"""Generic agent worktree writer dry-run.

Slice: REDDOG_GENERIC_AGENT_WORKTREE_WRITER_DRYRUN_PHASE1
Contract: docs/audits/architecture/REDDOG_GENERIC_AGENT_WORKTREE_WRITE_SPINE_CONTRACT_PHASE1.md

This module proves the generic worktree-write spine without writing files, creating a
worktree, running shell/git/gh, opening PRs, merging, or settling rewards. It validates
that a signed authority, receipt chain, full execution-valve decision, domain profile,
re-derived root, pin-independent denylist, and WRE cwd guard would authorize a future
writer. It emits a dry-run receipt only.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union

from modules.communication.moltbot_bridge.src.reddog_operator_loop_wardrobe_selection import (
    EXECUTION_GOVERNED_CANDIDATE,
    WARDROBE_SELECTION_ACCEPT,
    WARDROBE_SOVEREIGN_EXECUTION,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_work_order_policy_gate import (
    SIGNATURE_GATE_ACCEPTED,
)
from modules.communication.moltbot_bridge.src.reddog_signed_receipt_chain import (
    SIGNED_RECEIPT_CHAIN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_cwd_guard import (
    WreCwdGuardResult,
    validate_wre_worker_operation_cwd,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_WORKTREE_CREATE,
)

GENERIC_WRITER_DRYRUN_ACCEPT = "GENERIC_WRITER_DRYRUN_ACCEPT"
GENERIC_WRITER_DRYRUN_REJECT = "GENERIC_WRITER_DRYRUN_REJECT"

FAIL_PROFILE_INVALID = "FAIL_PROFILE_INVALID"
FAIL_OPERATION_MISMATCH = "FAIL_OPERATION_MISMATCH"
FAIL_DOMAIN_ID_INVALID = "FAIL_DOMAIN_ID_INVALID"
FAIL_CANONICAL_ROOT_INVALID = "FAIL_CANONICAL_ROOT_INVALID"
FAIL_CALLER_PATHS_WIDEN_PROFILE = "FAIL_CALLER_PATHS_WIDEN_PROFILE"
FAIL_ARTIFACTS_INVALID = "FAIL_ARTIFACTS_INVALID"
FAIL_DENIED_PATH = "FAIL_DENIED_PATH"
FAIL_SELECTION_RECEIPT = "FAIL_SELECTION_RECEIPT"
FAIL_SIGNED_AUTHORITY = "FAIL_SIGNED_AUTHORITY"
FAIL_RECEIPT_CHAIN = "FAIL_RECEIPT_CHAIN"
FAIL_VALVE_DECISION = "FAIL_VALVE_DECISION"
FAIL_CONSENSUS_REQUIRED = "FAIL_CONSENSUS_REQUIRED"
FAIL_CWD_GUARD = "FAIL_CWD_GUARD"
FAIL_PROTECTED_BRANCH = "FAIL_PROTECTED_BRANCH"
FAIL_HOLOINDEX_INDEX_GAP = "FAIL_HOLOINDEX_INDEX_GAP"

PIN_INDEPENDENT_DENYLIST = (
    ".env",
    ".env.*",
    ".github/workflows/**",
    "WSP_framework/**",
    "holo_index/**",
    "modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py",
    "modules/communication/moltbot_bridge/src/reddog_openclaw_work_order_policy_gate.py",
    "modules/communication/moltbot_bridge/src/reddog_work_order_signature_verifier.py",
    "modules/communication/moltbot_bridge/src/reddog_signed_receipt_chain.py",
    "modules/communication/moltbot_bridge/src/reddog_operator_loop_wardrobe_selection.py",
    "modules/**/secrets/**",
    "modules/**/wallet/**",
    "modules/**/nonce/**",
    "modules/**/permission/**",
)

_DEVICE_PREFIXES = ("\\\\?\\", "\\\\.\\", "//?/", "//./")
_PROTECTED_BRANCHES = frozenset({"main", "master"})


@dataclass(frozen=True)
class GenericAgentWorktreeDomainProfile:
    profile_id: str
    operation: str
    artifact_contract_type: str
    domain_id_pattern: str
    canonical_root_template: str
    allowed_path_patterns: List[str]
    denied_path_patterns: List[str]
    required_tests: List[str]
    branch_prefix: str
    draft_pr_only: bool = True
    consensus_required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GenericAgentWorktreeWriterDryRunRequest:
    work_order_id: str
    operation: str
    domain_id: str
    domain_profile: Union[GenericAgentWorktreeDomainProfile, Mapping[str, Any]]
    planned_artifacts: List[str]
    requested_allowed_paths: List[str]
    target_branch: str
    repo_root: str
    worktree_path: str
    selection_receipt: Mapping[str, Any]
    signed_authority: Mapping[str, Any]
    signed_receipt_chain: Mapping[str, Any]
    execution_valve_decision: Mapping[str, Any]
    permission_snapshot_digest: str = ""
    consensus_receipt_digest: Optional[str] = None
    operation_cwd: Optional[str] = None
    holoindex_evidence: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if isinstance(self.domain_profile, GenericAgentWorktreeDomainProfile):
            payload["domain_profile"] = self.domain_profile.to_dict()
        return payload


@dataclass(frozen=True)
class GenericAgentWorktreeWriterDryRunReceipt:
    receipt_id: str
    work_order_id: str
    domain_profile_id: str
    canonical_root: str
    canonical_root_digest: str
    artifact_manifest_digest: str
    selection_receipt_digest: str
    signed_authority_digest: str
    receipt_chain_terminal_hash: str
    execution_valve_decision_digest: str
    consensus_receipt_digest: Optional[str]
    cwd_guard_receipt_digest: str
    planned_artifacts: List[str]
    allowed_paths: List[str]
    denied_paths: List[str]
    target_branch: str
    no_write_performed: bool = True
    no_worktree_created: bool = True
    no_shell_performed: bool = True
    no_merge_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GenericAgentWorktreeWriterDryRunResult:
    decision: str
    accepted: bool
    rejection_reasons: List[str]
    receipt: Optional[GenericAgentWorktreeWriterDryRunReceipt]
    cwd_guard: Optional[WreCwdGuardResult]
    no_execution_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["receipt"] = self.receipt.to_dict() if self.receipt else None
        payload["cwd_guard"] = self.cwd_guard.to_dict() if self.cwd_guard else None
        return payload


def _as_profile(
    profile: Union[GenericAgentWorktreeDomainProfile, Mapping[str, Any]],
) -> Optional[GenericAgentWorktreeDomainProfile]:
    if isinstance(profile, GenericAgentWorktreeDomainProfile):
        return profile
    if not isinstance(profile, Mapping):
        return None
    try:
        return GenericAgentWorktreeDomainProfile(
            profile_id=str(profile["profile_id"]),
            operation=str(profile["operation"]),
            artifact_contract_type=str(profile["artifact_contract_type"]),
            domain_id_pattern=str(profile["domain_id_pattern"]),
            canonical_root_template=str(profile["canonical_root_template"]),
            allowed_path_patterns=[str(v) for v in profile.get("allowed_path_patterns", [])],
            denied_path_patterns=[str(v) for v in profile.get("denied_path_patterns", [])],
            required_tests=[str(v) for v in profile.get("required_tests", [])],
            branch_prefix=str(profile["branch_prefix"]),
            draft_pr_only=bool(profile.get("draft_pr_only", True)),
            consensus_required=bool(profile.get("consensus_required", False)),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _mapping(
    request: Union[GenericAgentWorktreeWriterDryRunRequest, Mapping[str, Any]],
) -> Mapping[str, Any]:
    if isinstance(request, GenericAgentWorktreeWriterDryRunRequest):
        return request.to_dict()
    return request


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _dedupe(values: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def _has_device_prefix(value: str) -> bool:
    return any(str(value).startswith(prefix) for prefix in _DEVICE_PREFIXES)


def _normalize_repo_path(value: str) -> Optional[str]:
    text = str(value or "").replace("\\", "/").strip()
    if not text or text.startswith("/") or _has_device_prefix(text):
        return None
    parts: List[str] = []
    for raw in text.split("/"):
        part = raw.strip(" \t").rstrip(" .")
        if not part or part in {".", ".."} or ":" in part:
            return None
        parts.append(part)
    return "/".join(parts)


def _derive_canonical_root(profile: GenericAgentWorktreeDomainProfile, domain_id: str) -> Optional[str]:
    try:
        if re.fullmatch(profile.domain_id_pattern, domain_id) is None:
            return None
    except re.error:
        return None
    try:
        rendered = profile.canonical_root_template.format(domain_id=domain_id)
    except Exception:
        return None
    return _normalize_repo_path(rendered)


def _is_under(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


def _pattern_matches(path: str, pattern: str) -> bool:
    pat = str(pattern or "").replace("\\", "/").strip()
    return bool(pat) and fnmatch.fnmatch(path.lower(), pat.lower())


def _path_denied(path: str, denied_patterns: Sequence[str]) -> bool:
    base = path.rsplit("/", 1)[-1].rstrip(" .").lower()
    if base in {".env", "foundup_registry.json"}:
        return True
    for pattern in list(PIN_INDEPENDENT_DENYLIST) + [str(v) for v in denied_patterns]:
        pat = pattern.replace("\\", "/").strip()
        if _pattern_matches(path, pat):
            return True
        if pat.endswith("/**") and _is_under(path.lower(), pat[:-3].lower().rstrip("/")):
            return True
    return False


def _allowed_paths_subset(requested: Sequence[str], canonical_root: str) -> bool:
    if not requested:
        return True
    for raw in requested:
        text = str(raw or "").replace("\\", "/").strip()
        if text.endswith("/**"):
            normalized = _normalize_repo_path(text[:-3])
            if normalized is None or not _is_under(normalized, canonical_root):
                return False
            continue
        normalized = _normalize_repo_path(text)
        if normalized is None or not _is_under(normalized, canonical_root):
            return False
    return True


def _selection_ok(selection: Mapping[str, Any]) -> bool:
    return (
        selection.get("decision") in (None, WARDROBE_SELECTION_ACCEPT)
        and selection.get("selected_wardrobe") == WARDROBE_SOVEREIGN_EXECUTION
        and selection.get("execution_plane") == EXECUTION_GOVERNED_CANDIDATE
        and selection.get("no_execution_performed") is True
    )


def _signed_authority_ok(authority: Mapping[str, Any], work_order_id: str, permission_digest: str) -> bool:
    accepted = authority.get("accepted") is True or authority.get("signature_gate_status") == SIGNATURE_GATE_ACCEPTED
    if not accepted:
        return False
    if authority.get("work_order_id") not in (None, work_order_id):
        return False
    supplied_digest = authority.get("permission_snapshot_digest")
    if permission_digest and supplied_digest not in (None, permission_digest):
        return False
    return True


def _receipt_chain_ok(chain: Mapping[str, Any]) -> bool:
    return (
        chain.get("accepted") is True
        and chain.get("decision") == SIGNED_RECEIPT_CHAIN_ACCEPT
        and chain.get("no_execution_performed") is not False
        and chain.get("no_reward_settlement_performed") is not False
    )


def _valve_ok(valve: Mapping[str, Any]) -> bool:
    return (
        valve.get("valve_state") == VALVE_OPEN_WORKTREE_CREATE
        and valve.get("no_execution_performed") is True
        and not list(valve.get("rejection_reasons") or [])
        and bool(valve.get("decision_digest"))
    )


def _holoindex_gap_blocks_write(holoindex_evidence: Mapping[str, Any]) -> bool:
    return (
        holoindex_evidence.get("index_gap_detected") is True
        or str(holoindex_evidence.get("retrieval_quality") or "").upper() == "INDEX_GAP"
    )


def plan_generic_agent_worktree_writer_dry_run(
    request: Union[GenericAgentWorktreeWriterDryRunRequest, Mapping[str, Any]],
) -> GenericAgentWorktreeWriterDryRunResult:
    """Validate a future generic worktree write and emit a dry-run receipt only."""
    req = _mapping(request)
    reasons: List[str] = []
    cwd_guard: Optional[WreCwdGuardResult] = None

    work_order_id = str(req.get("work_order_id") or "")
    operation = str(req.get("operation") or "")
    domain_id = str(req.get("domain_id") or "")
    profile = _as_profile(req.get("domain_profile") or {})

    if profile is None or not profile.draft_pr_only or not profile.branch_prefix.startswith("feat/"):
        reasons.append(FAIL_PROFILE_INVALID)
        canonical_root = ""
    else:
        if operation != profile.operation:
            reasons.append(FAIL_OPERATION_MISMATCH)
        canonical_root = _derive_canonical_root(profile, domain_id) or ""
        if not canonical_root:
            reasons.append(FAIL_DOMAIN_ID_INVALID)

    planned: List[str] = []
    if canonical_root:
        for raw in req.get("planned_artifacts") or []:
            normalized = _normalize_repo_path(str(raw))
            if normalized is None:
                reasons.append(FAIL_ARTIFACTS_INVALID)
                continue
            if not _is_under(normalized, canonical_root):
                reasons.append(FAIL_ARTIFACTS_INVALID)
            if profile is not None and _path_denied(normalized, profile.denied_path_patterns):
                reasons.append(FAIL_DENIED_PATH)
            planned.append(normalized)
        if not planned:
            reasons.append(FAIL_ARTIFACTS_INVALID)
        if not _allowed_paths_subset(req.get("requested_allowed_paths") or [], canonical_root):
            reasons.append(FAIL_CALLER_PATHS_WIDEN_PROFILE)
    else:
        reasons.append(FAIL_CANONICAL_ROOT_INVALID)

    if not _selection_ok(dict(req.get("selection_receipt") or {})):
        reasons.append(FAIL_SELECTION_RECEIPT)
    if not _signed_authority_ok(
        dict(req.get("signed_authority") or {}),
        work_order_id,
        str(req.get("permission_snapshot_digest") or ""),
    ):
        reasons.append(FAIL_SIGNED_AUTHORITY)
    chain = dict(req.get("signed_receipt_chain") or {})
    if not _receipt_chain_ok(chain):
        reasons.append(FAIL_RECEIPT_CHAIN)
    valve = dict(req.get("execution_valve_decision") or {})
    if not _valve_ok(valve):
        reasons.append(FAIL_VALVE_DECISION)
    if profile is not None and profile.consensus_required and not req.get("consensus_receipt_digest"):
        reasons.append(FAIL_CONSENSUS_REQUIRED)
    if _holoindex_gap_blocks_write(dict(req.get("holoindex_evidence") or {})):
        reasons.append(FAIL_HOLOINDEX_INDEX_GAP)

    branch = str(req.get("target_branch") or "")
    if profile is not None:
        if branch in _PROTECTED_BRANCHES or not branch.startswith(profile.branch_prefix):
            reasons.append(FAIL_PROTECTED_BRANCH)

    repo_root = str(req.get("repo_root") or "")
    worktree_path = str(req.get("worktree_path") or "")
    operation_cwd = str(req.get("operation_cwd") or worktree_path)
    try:
        cwd_guard = validate_wre_worker_operation_cwd(
            repo_root=Path(repo_root),
            worktree_path=Path(worktree_path),
            operation_cwd=Path(operation_cwd),
        )
        if not cwd_guard.ok:
            reasons.append(FAIL_CWD_GUARD)
    except Exception:
        reasons.append(FAIL_CWD_GUARD)

    deduped = _dedupe(reasons)
    if deduped:
        return GenericAgentWorktreeWriterDryRunResult(
            decision=GENERIC_WRITER_DRYRUN_REJECT,
            accepted=False,
            rejection_reasons=deduped,
            receipt=None,
            cwd_guard=cwd_guard,
        )

    assert profile is not None
    root_payload = {
        "domain_profile_id": profile.profile_id,
        "canonical_root": canonical_root,
        "allowed_paths": req.get("requested_allowed_paths") or [canonical_root + "/**"],
        "denied_paths": list(PIN_INDEPENDENT_DENYLIST) + list(profile.denied_path_patterns),
    }
    artifact_payload = {"canonical_root": canonical_root, "planned_artifacts": sorted(planned)}
    receipt = GenericAgentWorktreeWriterDryRunReceipt(
        receipt_id="generic_wt_dryrun_" + hashlib.sha256(
            _digest({"work_order_id": work_order_id, "root": canonical_root, "artifacts": planned}).encode("utf-8")
        ).hexdigest()[:16],
        work_order_id=work_order_id,
        domain_profile_id=profile.profile_id,
        canonical_root=canonical_root,
        canonical_root_digest=_digest(root_payload),
        artifact_manifest_digest=_digest(artifact_payload),
        selection_receipt_digest=_digest(req.get("selection_receipt") or {}),
        signed_authority_digest=(
            str((req.get("signed_authority") or {}).get("signature_gate_digest") or "")
            or str((req.get("signed_authority") or {}).get("verification_digest") or "")
            or _digest(req.get("signed_authority") or {})
        ),
        receipt_chain_terminal_hash=str(chain.get("terminal_receipt_hash") or ""),
        execution_valve_decision_digest=str(valve.get("decision_digest")),
        consensus_receipt_digest=(
            None if req.get("consensus_receipt_digest") is None else str(req.get("consensus_receipt_digest"))
        ),
        cwd_guard_receipt_digest=_digest(cwd_guard.to_dict() if cwd_guard else {}),
        planned_artifacts=sorted(planned),
        allowed_paths=list(req.get("requested_allowed_paths") or [canonical_root + "/**"]),
        denied_paths=list(PIN_INDEPENDENT_DENYLIST) + list(profile.denied_path_patterns),
        target_branch=branch,
    )
    return GenericAgentWorktreeWriterDryRunResult(
        decision=GENERIC_WRITER_DRYRUN_ACCEPT,
        accepted=True,
        rejection_reasons=[],
        receipt=receipt,
        cwd_guard=cwd_guard,
    )


__all__ = [
    "FAIL_ARTIFACTS_INVALID",
    "FAIL_CALLER_PATHS_WIDEN_PROFILE",
    "FAIL_CANONICAL_ROOT_INVALID",
    "FAIL_CONSENSUS_REQUIRED",
    "FAIL_CWD_GUARD",
    "FAIL_DENIED_PATH",
    "FAIL_DOMAIN_ID_INVALID",
    "FAIL_HOLOINDEX_INDEX_GAP",
    "FAIL_OPERATION_MISMATCH",
    "FAIL_PROFILE_INVALID",
    "FAIL_PROTECTED_BRANCH",
    "FAIL_RECEIPT_CHAIN",
    "FAIL_SELECTION_RECEIPT",
    "FAIL_SIGNED_AUTHORITY",
    "FAIL_VALVE_DECISION",
    "GENERIC_WRITER_DRYRUN_ACCEPT",
    "GENERIC_WRITER_DRYRUN_REJECT",
    "GenericAgentWorktreeDomainProfile",
    "GenericAgentWorktreeWriterDryRunReceipt",
    "GenericAgentWorktreeWriterDryRunRequest",
    "GenericAgentWorktreeWriterDryRunResult",
    "PIN_INDEPENDENT_DENYLIST",
    "plan_generic_agent_worktree_writer_dry_run",
]
