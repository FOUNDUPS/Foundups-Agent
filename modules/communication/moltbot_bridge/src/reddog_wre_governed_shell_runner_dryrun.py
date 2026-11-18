"""Governed shell runner dry-run.

Slice: REDDOG_WRE_GOVERNED_SHELL_RUNNER_DRYRUN_PHASE1
Contract: docs/audits/architecture/REDDOG_WRE_GOVERNED_SHELL_RUNNER_CONTRACT_PHASE1.md

This module validates whether a future WRE shell command would be authorized by
the RedDog execution spine. It never executes commands, opens files, creates
worktrees, mutates HoloIndex, or invokes subprocesses. It emits a dry-run
receipt only.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union

from modules.communication.moltbot_bridge.src.reddog_generic_agent_worktree_writer_dryrun import (
    GENERIC_WRITER_DRYRUN_ACCEPT,
)
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

GOVERNED_SHELL_DRYRUN_ACCEPT = "GOVERNED_SHELL_DRYRUN_ACCEPT"
GOVERNED_SHELL_DRYRUN_REJECT = "GOVERNED_SHELL_DRYRUN_REJECT"

FAIL_PROFILE_INVALID = "FAIL_PROFILE_INVALID"
FAIL_ARGV_INVALID = "FAIL_ARGV_INVALID"
FAIL_ARGV_PREFIX = "FAIL_ARGV_PREFIX"
FAIL_DENIED_ARG = "FAIL_DENIED_ARG"
FAIL_ARG_NOT_ALLOWED = "FAIL_ARG_NOT_ALLOWED"
FAIL_SHELL_METACHARACTER = "FAIL_SHELL_METACHARACTER"
FAIL_SELECTION_RECEIPT = "FAIL_SELECTION_RECEIPT"
FAIL_SIGNED_AUTHORITY = "FAIL_SIGNED_AUTHORITY"
FAIL_RECEIPT_CHAIN = "FAIL_RECEIPT_CHAIN"
FAIL_VALVE_DECISION = "FAIL_VALVE_DECISION"
FAIL_CWD_GUARD = "FAIL_CWD_GUARD"
FAIL_GENERIC_WRITER_RECEIPT = "FAIL_GENERIC_WRITER_RECEIPT"
FAIL_CONSENSUS_REQUIRED = "FAIL_CONSENSUS_REQUIRED"
FAIL_SECRET_IN_REQUEST = "FAIL_SECRET_IN_REQUEST"
FAIL_HOLOINDEX_INDEX_GAP = "FAIL_HOLOINDEX_INDEX_GAP"
FAIL_HOLOINDEX_FRESHNESS_RECEIPT = "FAIL_HOLOINDEX_FRESHNESS_RECEIPT"
FAIL_TIMEOUT_INVALID = "FAIL_TIMEOUT_INVALID"
FAIL_OUTPUT_CAP_INVALID = "FAIL_OUTPUT_CAP_INVALID"

COMMAND_KINDS = frozenset(
    {
        "test",
        "lint",
        "format_check",
        "static_analysis",
        "build_check",
        "readonly_probe",
    }
)
OUTPUT_REDACTION_POLICIES = frozenset({"strict", "secret_safe", "none_forbidden"})
MAX_TIMEOUT_SECONDS = 3600
MAX_OUTPUT_BYTES = 2_000_000

SHELL_METACHARACTERS = (";", "&&", "||", "|", ">", "<", "`", "$(", "\n", "\r")
FORBIDDEN_COMMAND_PATTERNS = (
    "git push",
    "git merge",
    "git reset",
    "git checkout",
    "gh pr ready",
    "gh pr merge",
    "npm publish",
    "twine upload",
    "python -m build",
    "holo_index.py --index",
    "holo_index.py --reindex",
)
SECRET_MARKERS = (
    "bearer ",
    "authorization:",
    "api_key",
    "apikey",
    "private_key",
    "begin private key",
    "token=",
    "secret=",
    "password=",
)


@dataclass(frozen=True)
class GovernedShellCommandProfile:
    profile_id: str
    command_kind: str
    argv_prefix: List[str]
    allowed_arg_patterns: List[str]
    denied_arg_patterns: List[str]
    requires_cwd_guard: bool
    requires_worktree: bool
    timeout_seconds: int
    max_stdout_bytes: int
    max_stderr_bytes: int
    secret_env_refs: List[str]
    output_redaction_policy: str
    draft_pr_only: bool = True
    consensus_required: bool = False
    repo_sensitive: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GovernedShellRunDryRunRequest:
    work_order_id: str
    profile: Union[GovernedShellCommandProfile, Mapping[str, Any]]
    argv: List[str]
    operation_cwd: str
    worktree_path: str
    repo_root: str
    selection_receipt: Mapping[str, Any]
    signed_authority: Mapping[str, Any]
    signed_receipt_chain: Mapping[str, Any]
    execution_valve_decision: Mapping[str, Any]
    generic_writer_dryrun_receipt: Mapping[str, Any] = field(default_factory=dict)
    permission_snapshot_digest: str = ""
    consensus_receipt_digest: Optional[str] = None
    stdin_policy: Union[str, Mapping[str, Any]] = "none"
    env_policy: Mapping[str, Any] = field(default_factory=dict)
    holoindex_evidence: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if isinstance(self.profile, GovernedShellCommandProfile):
            payload["profile"] = self.profile.to_dict()
        return payload


@dataclass(frozen=True)
class GovernedShellRunDryRunReceipt:
    run_receipt_id: str
    work_order_id: str
    profile_id: str
    argv_digest: str
    cwd_guard_receipt_digest: str
    signed_authority_digest: str
    receipt_chain_terminal_hash: str
    execution_valve_decision_digest: str
    generic_writer_dryrun_receipt_digest: Optional[str]
    holoindex_freshness_receipt_digest: str
    exit_code: Optional[int] = None
    timed_out: bool = False
    stdout_digest: str = ""
    stderr_digest: str = ""
    output_truncated: bool = False
    no_merge_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_command_executed: bool = True
    no_subprocess_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GovernedShellRunDryRunResult:
    decision: str
    accepted: bool
    rejection_reasons: List[str]
    receipt: Optional[GovernedShellRunDryRunReceipt]
    cwd_guard: Optional[WreCwdGuardResult]
    no_execution_performed: bool = True
    no_command_executed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["receipt"] = self.receipt.to_dict() if self.receipt else None
        payload["cwd_guard"] = self.cwd_guard.to_dict() if self.cwd_guard else None
        return payload


def _mapping(
    request: Union[GovernedShellRunDryRunRequest, Mapping[str, Any]],
) -> Mapping[str, Any]:
    if isinstance(request, GovernedShellRunDryRunRequest):
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


def _as_profile(
    profile: Union[GovernedShellCommandProfile, Mapping[str, Any]],
) -> Optional[GovernedShellCommandProfile]:
    if isinstance(profile, GovernedShellCommandProfile):
        return profile
    if not isinstance(profile, Mapping):
        return None
    try:
        return GovernedShellCommandProfile(
            profile_id=str(profile["profile_id"]),
            command_kind=str(profile["command_kind"]),
            argv_prefix=[str(v) for v in profile.get("argv_prefix", [])],
            allowed_arg_patterns=[str(v) for v in profile.get("allowed_arg_patterns", [])],
            denied_arg_patterns=[str(v) for v in profile.get("denied_arg_patterns", [])],
            requires_cwd_guard=bool(profile.get("requires_cwd_guard", True)),
            requires_worktree=bool(profile.get("requires_worktree", True)),
            timeout_seconds=int(profile["timeout_seconds"]),
            max_stdout_bytes=int(profile["max_stdout_bytes"]),
            max_stderr_bytes=int(profile["max_stderr_bytes"]),
            secret_env_refs=[str(v) for v in profile.get("secret_env_refs", [])],
            output_redaction_policy=str(profile["output_redaction_policy"]),
            draft_pr_only=bool(profile.get("draft_pr_only", True)),
            consensus_required=bool(profile.get("consensus_required", False)),
            repo_sensitive=bool(profile.get("repo_sensitive", True)),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _profile_invalid(profile: GovernedShellCommandProfile) -> bool:
    if not profile.profile_id or profile.command_kind not in COMMAND_KINDS:
        return True
    if not profile.argv_prefix or not all(isinstance(arg, str) and arg for arg in profile.argv_prefix):
        return True
    if not profile.draft_pr_only:
        return True
    if profile.output_redaction_policy not in OUTPUT_REDACTION_POLICIES:
        return True
    return False


def _timeout_invalid(profile: GovernedShellCommandProfile) -> bool:
    return profile.timeout_seconds <= 0 or profile.timeout_seconds > MAX_TIMEOUT_SECONDS


def _output_caps_invalid(profile: GovernedShellCommandProfile) -> bool:
    return (
        profile.max_stdout_bytes <= 0
        or profile.max_stderr_bytes <= 0
        or profile.max_stdout_bytes > MAX_OUTPUT_BYTES
        or profile.max_stderr_bytes > MAX_OUTPUT_BYTES
    )


def _argv_list(value: Any) -> Optional[List[str]]:
    if not isinstance(value, list) or not value:
        return None
    argv: List[str] = []
    for item in value:
        if not isinstance(item, str) or item == "":
            return None
        argv.append(item)
    return argv


def _has_shell_metacharacter(argv: Sequence[str]) -> bool:
    return any(any(marker in arg for marker in SHELL_METACHARACTERS) for arg in argv)


def _joined_argv(argv: Sequence[str]) -> str:
    return " ".join(argv).lower()


def _matches(pattern: str, value: str) -> bool:
    text = str(pattern or "")
    if not text:
        return False
    try:
        return re.fullmatch(text, value) is not None
    except re.error:
        return False


def _searches(pattern: str, value: str) -> bool:
    text = str(pattern or "")
    if not text:
        return False
    try:
        return re.search(text, value) is not None
    except re.error:
        return False


def _argv_policy_reasons(profile: GovernedShellCommandProfile, argv: Sequence[str]) -> List[str]:
    reasons: List[str] = []
    if list(argv[: len(profile.argv_prefix)]) != list(profile.argv_prefix):
        reasons.append(FAIL_ARGV_PREFIX)
        return reasons
    if _has_shell_metacharacter(argv):
        reasons.append(FAIL_SHELL_METACHARACTER)
    joined = _joined_argv(argv)
    if any(pattern in joined for pattern in FORBIDDEN_COMMAND_PATTERNS):
        reasons.append(FAIL_DENIED_ARG)
    trailing = list(argv[len(profile.argv_prefix) :])
    for arg in trailing:
        if any(_searches(pattern, arg) for pattern in profile.denied_arg_patterns):
            reasons.append(FAIL_DENIED_ARG)
            continue
        if profile.allowed_arg_patterns and not any(_matches(pattern, arg) for pattern in profile.allowed_arg_patterns):
            reasons.append(FAIL_ARG_NOT_ALLOWED)
    return reasons


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


def _generic_writer_receipt_ok(receipt: Mapping[str, Any]) -> bool:
    decision = receipt.get("decision")
    return (
        decision in (None, GENERIC_WRITER_DRYRUN_ACCEPT)
        and receipt.get("no_write_performed") is True
        and receipt.get("no_worktree_created") is True
        and receipt.get("no_shell_performed") is True
        and bool(receipt.get("canonical_root_digest"))
        and bool(receipt.get("artifact_manifest_digest"))
    )


def _holoindex_gap_blocks_command(holoindex_evidence: Mapping[str, Any]) -> bool:
    return (
        holoindex_evidence.get("index_gap_detected") is True
        or str(holoindex_evidence.get("retrieval_quality") or "").upper() == "INDEX_GAP"
    )


def _holoindex_freshness_digest(holoindex_evidence: Mapping[str, Any]) -> str:
    return str(
        holoindex_evidence.get("holoindex_freshness_receipt_digest")
        or holoindex_evidence.get("freshness_receipt_digest")
        or ""
    )


def _contains_raw_secret(payload: Any, parent_key: str = "") -> bool:
    if parent_key == "secret_env_refs":
        return False
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            key_text = str(key).lower()
            if key_text != "secret_env_refs" and any(marker.rstrip(" =:") in key_text for marker in SECRET_MARKERS):
                return True
            if _contains_raw_secret(value, key_text):
                return True
        return False
    if isinstance(payload, (list, tuple)):
        return any(_contains_raw_secret(value, parent_key) for value in payload)
    text = str(payload or "").lower()
    if not text:
        return False
    if parent_key == "secret_env_refs":
        return False
    return any(marker in text for marker in SECRET_MARKERS)


def _secret_in_request(req: Mapping[str, Any], profile: Optional[GovernedShellCommandProfile]) -> bool:
    inspected = {
        "argv": req.get("argv"),
        "stdin_policy": req.get("stdin_policy"),
        "env_policy": req.get("env_policy"),
    }
    if _contains_raw_secret(inspected):
        return True
    if profile is None:
        return False
    for ref in profile.secret_env_refs:
        text = str(ref or "")
        if not text or _has_shell_metacharacter([text]):
            return True
        if text.lower().startswith(("bearer ", "token=", "secret=", "password=")):
            return True
    return False


def _authority_digest(authority: Mapping[str, Any]) -> str:
    return str(authority.get("signature_gate_digest") or authority.get("verification_digest") or "") or _digest(authority)


def plan_governed_shell_runner_dry_run(
    request: Union[GovernedShellRunDryRunRequest, Mapping[str, Any]],
) -> GovernedShellRunDryRunResult:
    """Validate a future governed shell run and emit a dry-run receipt only."""
    req = _mapping(request)
    reasons: List[str] = []
    cwd_guard: Optional[WreCwdGuardResult] = None

    work_order_id = str(req.get("work_order_id") or "")
    profile = _as_profile(req.get("profile") or {})
    argv = _argv_list(req.get("argv"))

    if profile is None or _profile_invalid(profile):
        reasons.append(FAIL_PROFILE_INVALID)
    else:
        if _timeout_invalid(profile):
            reasons.append(FAIL_TIMEOUT_INVALID)
        if _output_caps_invalid(profile):
            reasons.append(FAIL_OUTPUT_CAP_INVALID)

    if argv is None:
        reasons.append(FAIL_ARGV_INVALID)
    elif profile is not None:
        reasons.extend(_argv_policy_reasons(profile, argv))

    if _secret_in_request(req, profile):
        reasons.append(FAIL_SECRET_IN_REQUEST)

    selection = dict(req.get("selection_receipt") or {})
    if not _selection_ok(selection):
        reasons.append(FAIL_SELECTION_RECEIPT)

    authority = dict(req.get("signed_authority") or {})
    if not _signed_authority_ok(authority, work_order_id, str(req.get("permission_snapshot_digest") or "")):
        reasons.append(FAIL_SIGNED_AUTHORITY)

    chain = dict(req.get("signed_receipt_chain") or {})
    if not _receipt_chain_ok(chain):
        reasons.append(FAIL_RECEIPT_CHAIN)

    valve = dict(req.get("execution_valve_decision") or {})
    if not _valve_ok(valve):
        reasons.append(FAIL_VALVE_DECISION)

    if profile is not None and profile.consensus_required and not req.get("consensus_receipt_digest"):
        reasons.append(FAIL_CONSENSUS_REQUIRED)

    writer_receipt = dict(req.get("generic_writer_dryrun_receipt") or {})
    if profile is not None and profile.requires_worktree and not _generic_writer_receipt_ok(writer_receipt):
        reasons.append(FAIL_GENERIC_WRITER_RECEIPT)

    holoindex_evidence = dict(req.get("holoindex_evidence") or {})
    if profile is not None and profile.repo_sensitive:
        if _holoindex_gap_blocks_command(holoindex_evidence):
            reasons.append(FAIL_HOLOINDEX_INDEX_GAP)
        if not _holoindex_freshness_digest(holoindex_evidence):
            reasons.append(FAIL_HOLOINDEX_FRESHNESS_RECEIPT)

    if profile is not None and (profile.requires_cwd_guard or profile.requires_worktree):
        try:
            cwd_guard = validate_wre_worker_operation_cwd(
                repo_root=Path(str(req.get("repo_root") or "")),
                worktree_path=Path(str(req.get("worktree_path") or "")),
                operation_cwd=Path(str(req.get("operation_cwd") or req.get("worktree_path") or "")),
            )
            if not cwd_guard.ok:
                reasons.append(FAIL_CWD_GUARD)
        except Exception:
            reasons.append(FAIL_CWD_GUARD)

    deduped = _dedupe(reasons)
    if deduped:
        return GovernedShellRunDryRunResult(
            decision=GOVERNED_SHELL_DRYRUN_REJECT,
            accepted=False,
            rejection_reasons=deduped,
            receipt=None,
            cwd_guard=cwd_guard,
        )

    assert profile is not None
    assert argv is not None
    argv_digest = _digest({"argv": argv})
    empty_output_digest = _digest("")
    receipt = GovernedShellRunDryRunReceipt(
        run_receipt_id="governed_shell_dryrun_" + hashlib.sha256(
            _digest({"work_order_id": work_order_id, "profile_id": profile.profile_id, "argv": argv}).encode("utf-8")
        ).hexdigest()[:16],
        work_order_id=work_order_id,
        profile_id=profile.profile_id,
        argv_digest=argv_digest,
        cwd_guard_receipt_digest=_digest(cwd_guard.to_dict() if cwd_guard else {}),
        signed_authority_digest=_authority_digest(authority),
        receipt_chain_terminal_hash=str(chain.get("terminal_receipt_hash") or ""),
        execution_valve_decision_digest=str(valve.get("decision_digest") or ""),
        generic_writer_dryrun_receipt_digest=(
            None if not writer_receipt else str(writer_receipt.get("receipt_id") or _digest(writer_receipt))
        ),
        holoindex_freshness_receipt_digest=_holoindex_freshness_digest(holoindex_evidence),
        stdout_digest=empty_output_digest,
        stderr_digest=empty_output_digest,
    )
    return GovernedShellRunDryRunResult(
        decision=GOVERNED_SHELL_DRYRUN_ACCEPT,
        accepted=True,
        rejection_reasons=[],
        receipt=receipt,
        cwd_guard=cwd_guard,
    )


__all__ = [
    "FAIL_ARGV_INVALID",
    "FAIL_ARGV_PREFIX",
    "FAIL_ARG_NOT_ALLOWED",
    "FAIL_CONSENSUS_REQUIRED",
    "FAIL_CWD_GUARD",
    "FAIL_DENIED_ARG",
    "FAIL_GENERIC_WRITER_RECEIPT",
    "FAIL_HOLOINDEX_FRESHNESS_RECEIPT",
    "FAIL_HOLOINDEX_INDEX_GAP",
    "FAIL_OUTPUT_CAP_INVALID",
    "FAIL_PROFILE_INVALID",
    "FAIL_RECEIPT_CHAIN",
    "FAIL_SECRET_IN_REQUEST",
    "FAIL_SELECTION_RECEIPT",
    "FAIL_SHELL_METACHARACTER",
    "FAIL_SIGNED_AUTHORITY",
    "FAIL_TIMEOUT_INVALID",
    "FAIL_VALVE_DECISION",
    "GOVERNED_SHELL_DRYRUN_ACCEPT",
    "GOVERNED_SHELL_DRYRUN_REJECT",
    "GovernedShellCommandProfile",
    "GovernedShellRunDryRunReceipt",
    "GovernedShellRunDryRunRequest",
    "GovernedShellRunDryRunResult",
    "plan_governed_shell_runner_dry_run",
]
