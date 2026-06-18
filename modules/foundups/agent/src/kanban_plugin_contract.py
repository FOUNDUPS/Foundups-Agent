#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kanban Plugin Contract -- WRE-side typed seam (pure, execution-free).

Implements the three plugin-contract shapes from the Hermes Kanban plugin contract
(#804) and the launch-flow audit (#806): the published card (WRE -> Kanban), the
bounded worker task (Kanban worker receives), and the returned evidence packet
(Kanban -> WRE). It is the clean WRE-side seam that lets Kanban workers exist
WITHOUT giving Kanban authority.

WSP 97 TRUTH BOUNDARIES:
  - This module EXECUTES NOTHING. Pure dataclasses + validators.
  - It imports nothing from Hermes/Kanban/OpenClaw/WRE-consumer/AI-Overseer runtime.
  - No subprocess, no Popen, no os.system, no sockets/network, no file writes, no
    Kanban DB write, no worker spawn. Stdlib + dataclasses + typing + re + unicodedata.
  - Forbidden AUTHORITY cannot ride through any shape: gate-pass, source_authority
    promotion, merge/land tokens, repo creation, public code, real-execution. The
    authority scan normalizes keys AND scans string values (anti-evasion).
  - WreEvidencePacket is ADVISORY: ``verified`` is always False at construction; a
    payload asserting verified=true is rejected. The WRE-side verifier transition is
    a separate, deferred slice (WRE_EVIDENCE_PACKET_VERIFICATION_TRANSITION_PHASE1).
  - Secret VALUES are redacted from free-text before storage (the #768 policy,
    reimplemented locally so this module imports no ai_overseer runtime).

Architecture (authority split, from #806):
  PFmall = surface | Kanban = worker board | Evidence = advisory |
  Registry/manifest/PR/WSP = truth | WRE = state authority | LAND/W10 = merge authority.

NAVIGATION:
  -> Implements: #804 plugin contract + #806 CardSpec/WorkerTaskSpec/EvidencePacket
  -> Beside: context_bundle_builder.py, foundup_manifest_validator.py, module_path_resolution.py
  -> Tested by: modules/foundups/agent/tests/test_kanban_plugin_contract.py
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Union

__all__ = [
    "ArtifactRef",
    "KanbanCardSpec",
    "WorkerTaskSpec",
    "WreEvidencePacket",
    "ContractValidationResult",
    "KanbanContractError",
    "validate_card_spec",
    "validate_worker_task_spec",
    "validate_evidence_packet",
    "redact_sensitive",
    "ALLOWED_SOURCE_AUTHORITY",
    "ALLOWED_RISK_CLASSES",
]

# Phase-1 source authority. A card/task/packet may never carry a different stage.
ALLOWED_SOURCE_AUTHORITY = "monorepo_poc"
ALLOWED_RISK_CLASSES = frozenset({"DOCS_DECISION_ONLY", "SPINE_CODE"})

# Future slice that owns the WRE-side verifier transition (NOT implemented here).
VERIFIER_TRANSITION_SLICE = "WRE_EVIDENCE_PACKET_VERIFICATION_TRANSITION_PHASE1"


class KanbanContractError(ValueError):
    """Raised when a shape is constructed with a hard-forbidden value (e.g. verified=true)."""


# ---------------------------------------------------------------------------
# Secret redaction (the #768 policy, reimplemented locally; no ai_overseer import)
# ---------------------------------------------------------------------------

_REDACTION = "[REDACTED]"
_REDACT_SUBS: Tuple[Tuple["re.Pattern[str]", str], ...] = (
    (
        re.compile(
            r"(\b(?:access_token|refresh_token|id_token|client_secret|client_id|"
            r"user_code|authorization_code|password|passwd|api_key|apikey|token)\b"
            r"\s*[\"']?\s*[:=]\s*[\"']?)([^\s&\"'}]+)",
            re.IGNORECASE,
        ),
        r"\1" + _REDACTION,
    ),
    (
        re.compile(
            r"([?&](?:code|access_token|refresh_token|id_token|token)=)[^\s&\"'}]+",
            re.IGNORECASE,
        ),
        r"\1" + _REDACTION,
    ),
    (
        re.compile(r"(\b[A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|APIKEY)\s*[:=]\s*)(\S+)"),
        r"\1" + _REDACTION,
    ),
    (re.compile(r"(\b[Bb]earer\s+)[A-Za-z0-9._\-]+"), r"\1" + _REDACTION),
    (re.compile(r"\bya29\.[0-9A-Za-z._\-]+"), _REDACTION),
    (re.compile(r"\b1//[0-9A-Za-z._\-]{10,}"), _REDACTION),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{10,}"), _REDACTION),
    (re.compile(r"\bsk-[A-Za-z0-9]{16,}"), _REDACTION),
    (re.compile(r"\bgh[posru]_[A-Za-z0-9]{16,}"), _REDACTION),
)


def redact_sensitive(text: Optional[str]) -> str:
    """Redact credential-adjacent material from text BEFORE it is stored. Pure."""
    if not text:
        return ""
    out = str(text)
    for pattern, repl in _REDACT_SUBS:
        out = pattern.sub(repl, out)
    return out


def _redact_deep(node: Any) -> Any:
    """Deep-redact EVERY string in a value, recursing into list/tuple/dict.

    Reuses ``redact_sensitive`` per string so a raw secret can NEVER appear in
    serialized output, even when nested inside a list/dict free-text field. Pure;
    returns a NEW structure (does not mutate the input). Non-string leaves pass
    through unchanged (only string-shaped credential material is touched)."""
    if isinstance(node, str):
        return redact_sensitive(node)
    if isinstance(node, dict):
        return {k: _redact_deep(v) for k, v in node.items()}
    if isinstance(node, (list, tuple)):
        return [_redact_deep(item) for item in node]
    return node


# ---------------------------------------------------------------------------
# Authority-evasion normalization (Addendum D) + markers (Addenda D/E)
# ---------------------------------------------------------------------------

_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_MULTI_US = re.compile(r"_+")


def _normalize(token: Any) -> str:
    """NFKC -> camel-split -> casefold -> {space,hyphen,dot}->_ -> collapse/strip.

    Defeats gatePassed / gate-passed / gate passed / gate.passed / GATE_PASSED /
    fullwidth, etc. Returns "" for non-string inputs.
    """
    if not isinstance(token, str):
        return ""
    s = unicodedata.normalize("NFKC", token)
    s = _CAMEL.sub("_", s)
    s = s.casefold()
    s = s.replace(" ", "_").replace("-", "_").replace(".", "_")
    s = _MULTI_US.sub("_", s)
    return s.strip("_ \t")


def _is_printable_ascii(s: str) -> bool:
    return all(32 <= ord(c) < 127 for c in s)


def _has_control_chars(s: str) -> bool:
    return any(ord(c) < 32 or ord(c) == 127 for c in s)


# Authority markers (normalized). A KEY containing one of these with a TRUTHY value,
# or any string VALUE containing one of these, is forbidden.
_AUTHORITY_MARKERS: frozenset = frozenset({
    "gate_passed", "gates_passed", "all_gates_passed", "security_passed",
    "permission_passed", "dry_run_passed", "build_passed", "verification_complete",
    "merge_token", "merge_approved", "merge_authorized", "can_merge", "land_approved",
    "cabr_ready", "cabr_passed", "payout_ready", "payout_approved",
    "dao_ready", "dao_approved", "dao_passed",
    "create_repo", "repo_create", "external_repo_requested", "provision_repo",
    "real_execution", "execute_real", "live_launch_approved", "gate_bypass",
})
# Stage tokens that, if asserted as a source_authority, are a promotion.
_NON_MONOREPO_STAGES: frozenset = frozenset({
    "external_proto", "proto", "soft_proto", "mvp", "opo", "growth", "infra",
    "mega", "systemic", "dao", "smartdao",
})
# Keys that name a command/exec field; a shell-string value there is a smuggle.
_COMMAND_KEY_MARKERS: tuple = ("command", "cmd", "argv", "shell", "exec", "run_cmd", "script")
_SHELL_METACHARS: frozenset = frozenset(";|&$`><(){}\n\r\t!#\\\"'")
_SHELL_METASTRINGS: tuple = ("&&", "||", "$(", "${", ">>", "<<")


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return _normalize(value) in ("true", "1", "yes", "on", "approved", "ready", "passed")
    if isinstance(value, (int, float)):
        return value != 0
    return bool(value)


def _value_carries_authority(value: str) -> Optional[str]:
    nv = _normalize(value)
    for m in _AUTHORITY_MARKERS:
        if m in nv:
            return m
    if "source_authority" in nv and "monorepo_poc" not in nv:
        return "source_authority_promotion"
    for stage in _NON_MONOREPO_STAGES:
        if ("source_authority_" + stage) in nv or ("lifecycle_" + stage) in nv:
            return "source_authority_promotion"
    return None


def _scan_authority(node: Any, trail: str, errors: List[str]) -> None:
    """Recursively reject forbidden authority on keys (truthy) AND string values."""
    if isinstance(node, dict):
        for key, value in node.items():
            if not isinstance(key, str):
                # No-raw-echo (#807): never echo the raw key/value/repr/trail. Name the
                # rule only; the offending key/value are user-controlled.
                errors.append("non-string key rejected")
                continue
            if not _is_printable_ascii(unicodedata.normalize("NFKC", key)):
                errors.append("non-ASCII / non-printable key rejected")
            nkey = _normalize(key)
            # verified=true anywhere is rejected (advisory-until-verified).
            if nkey == "verified" and _truthy(value):
                errors.append("verified=true is forbidden (advisory-until-verified)")
            # source_authority promotion.
            if nkey in ("source_authority", "lifecycle_stage", "source_authority_stage"):
                if isinstance(value, str) and _normalize(value) not in ("monorepo_poc", "incubating", "idea", ""):
                    errors.append("source_authority promotion is forbidden (only monorepo_poc)")
            if "promote" in nkey or "promotion" in nkey:
                if _truthy(value):
                    errors.append("promotion flag is forbidden")
            # authority-marker key: PRESENCE is forbidden (no legitimate field
            # normalizes to an authority marker), regardless of value. KEEP the fixed
            # marker class {m} (from _AUTHORITY_MARKERS taxonomy -- NOT user input);
            # DROP the user-controlled key/trail.
            for m in _AUTHORITY_MARKERS:
                if m in nkey:
                    errors.append(f"forbidden authority field present (class: {m})")
                    break
            # command-key: argv-or-null ONLY. A command-key value is accepted only
            # when it is null/None OR an argv LIST of safe strings. A bare STRING
            # (even metachar-free, e.g. "rm -rf /"), a dict, or a list with any unsafe
            # element (shell metachar / authority marker / path bypass) is rejected.
            # No-raw-echo (#838): name the rule class only; NEVER echo the command value.
            if any(c in nkey for c in _COMMAND_KEY_MARKERS):
                if not _command_value_is_argv_or_null(value):
                    errors.append("command must be argv-list-or-null (bare string / unsafe argv forbidden)")
            _scan_authority(value, f"{trail}{key}.", errors)
    elif isinstance(node, (list, tuple, set)):
        for idx, item in enumerate(node):
            _scan_authority(item, f"{trail}{idx}.", errors)
    elif isinstance(node, str):
        carried = _value_carries_authority(node)
        if carried:
            # KEEP the fixed carried-marker class {carried} (taxonomy, NOT user input);
            # DROP the user-controlled value repr and the trail.
            errors.append(f"value carries a forbidden authority marker (class: {carried})")


def _has_shell(value: str) -> bool:
    if any(ch in _SHELL_METACHARS for ch in value):
        return True
    return any(tok in value for tok in _SHELL_METASTRINGS)


def _argv_element_unsafe(item: Any) -> bool:
    """An argv element is SAFE only if it is a string with no shell metachar, no
    authority marker, and no path/traversal bypass. Any other element type (or an
    unsafe string) is UNSAFE. Reuses the existing _has_shell + authority/path checks
    per element -- nothing here weakens those checks."""
    if not isinstance(item, str):
        return True
    if _has_shell(item):
        return True
    if _value_carries_authority(item) is not None:
        return True
    path_errs: List[str] = []
    _check_path("argv", item, path_errs)
    return bool(path_errs)


def _command_value_is_argv_or_null(value: Any) -> bool:
    """The contract guarantee: a command-key value is ACCEPTED only if it is None
    (null) OR a non-empty argv LIST whose every element is a safe string. A bare
    STRING (even metachar-free, e.g. ``rm -rf /``), a dict, or a list with any unsafe
    element is REJECTED -- 'argv-or-null only', NOT 'metachar-free string allowed'."""
    if value is None:
        return True
    if isinstance(value, (list, tuple)):
        # A NON-EMPTY argv list of all-safe elements. An empty argv list ([]) is
        # degenerate/malformed and is REJECTED (all([]) would otherwise pass it).
        return len(value) >= 1 and all(not _argv_element_unsafe(item) for item in value)
    return False


# ---------------------------------------------------------------------------
# Path / ref hygiene (Addendum F)
# ---------------------------------------------------------------------------

_DRIVE = re.compile(r"^[A-Za-z]:")


def _check_path(field_name: str, value: Any, errors: List[str]) -> None:
    # No-raw-echo (#807): field_name is a FIXED contract field label + positional index
    # (not user content) and the type name is a fixed Python type -- both safe to keep.
    # The user-controlled path/ref VALUE (and any raw bytes it carries) is NEVER echoed:
    # name the field + the rule only, never repr(value) or the offending characters.
    if not isinstance(value, str):
        errors.append(f"{field_name}: path/ref must be a string, got {type(value).__name__}")
        return
    if value == "":
        errors.append(f"{field_name}: empty path/ref")
        return
    if not _is_printable_ascii(value):
        errors.append(f"{field_name}: path/ref must be printable ASCII")
        return
    if _has_control_chars(value):
        errors.append(f"{field_name}: control character in path/ref")
        return
    if value.startswith("/") or value.startswith("\\") or value.startswith("//") or value.startswith("\\\\"):
        errors.append(f"{field_name}: absolute/UNC path forbidden")
    if _DRIVE.match(value):
        errors.append(f"{field_name}: drive path forbidden")
    norm_sep = value.replace("\\", "/")
    if ".." in norm_sep.split("/"):
        errors.append(f"{field_name}: path traversal '..' forbidden")
    # shell-control metacharacters (glob '*'/'?'/'[]' and '/' are allowed in path fields).
    bad = set(";|&$`><(){}\n\r\t!#") & set(value)
    if bad:
        errors.append(f"{field_name}: shell metacharacters in path/ref forbidden")


# ---------------------------------------------------------------------------
# Shapes
# ---------------------------------------------------------------------------

@dataclass
class ArtifactRef:
    """A reference to a produced artifact -- ref + digest only, never a body."""

    path: str
    sha256: str
    size_bytes: int = 0
    role: str = "artifact"

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "sha256": self.sha256, "size_bytes": int(self.size_bytes), "role": self.role}


@dataclass
class KanbanCardSpec:
    """WRE -> Kanban: a projection of WRE-authored work. Carries no authority."""

    slice_id: str
    lane: str
    contextbundle_id: str
    risk_class: str
    required_gates: List[str] = field(default_factory=list)
    allowed_paths: List[str] = field(default_factory=list)
    forbidden_paths: List[str] = field(default_factory=list)
    branch: str = ""
    worktree: str = ""
    expected_evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """REDACTED canonical body (WRE -> Kanban). Defense-in-depth: every string
        field -- and every string nested in a list/dict field -- is passed through
        ``redact_sensitive`` so a raw secret in any free-text field NEVER serializes
        verbatim (parity with WreEvidencePacket's value redaction). Redaction is done
        at SERIALIZATION (the dataclass instance is NOT mutated); the redacted dict is
        the canonical body, so any digest a consumer computes over ``to_dict()`` is a
        digest over redacted text (CARD_ID_FROM_REDACTED_CANONICAL_BODY)."""
        return _redact_deep(asdict(self))


@dataclass
class WorkerTaskSpec:
    """The bounded task a worker receives. ContextBundle is the only work-package authority."""

    slice_id: str
    contextbundle_id: str
    required_gates: List[str] = field(default_factory=list)
    allowed_paths: List[str] = field(default_factory=list)
    dry_run: bool = True
    prompt_pack_ref: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WreEvidencePacket:
    """Kanban -> WRE: ADVISORY evidence. verified is always False at construction.

    Free-text fields are redacted before storage (before any truncation a caller
    might apply). A payload asserting verified=true is rejected.
    """

    slice_id: str
    contextbundle_id: str
    pr_url: str = ""
    head_sha: str = ""
    tests_run: List[str] = field(default_factory=list)
    wsp97_rows: List[str] = field(default_factory=list)
    artifact_refs: List[ArtifactRef] = field(default_factory=list)
    changed_files: List[str] = field(default_factory=list)
    residual_risk: str = ""
    blocked_reason: str = ""
    stdout_tail: str = ""
    stderr_tail: str = ""
    notes: str = ""
    verified: bool = False

    def __post_init__(self) -> None:
        # Advisory-until-verified: verified can never be set True at construction.
        if self.verified is not False:
            raise KanbanContractError(
                "WreEvidencePacket.verified must be False at construction; the WRE-side "
                f"verifier transition is deferred to {VERIFIER_TRANSITION_SLICE}"
            )
        # Redact secret VALUES before storage (runs before any external truncation).
        # Defense-in-depth: redact EVERY string-bearing field, not only free-text
        # narrative -- a token can hide in pr_url / head_sha / tests_run too.
        # redact_sensitive is a no-op on clean values (only token shapes match).
        self.residual_risk = redact_sensitive(self.residual_risk)
        self.blocked_reason = redact_sensitive(self.blocked_reason)
        self.stdout_tail = redact_sensitive(self.stdout_tail)
        self.stderr_tail = redact_sensitive(self.stderr_tail)
        self.notes = redact_sensitive(self.notes)
        self.pr_url = redact_sensitive(self.pr_url)
        self.head_sha = redact_sensitive(self.head_sha)
        self.tests_run = [redact_sensitive(t) for t in self.tests_run]
        self.wsp97_rows = [redact_sensitive(r) for r in self.wsp97_rows]
        self.changed_files = [redact_sensitive(c) for c in self.changed_files]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["artifact_refs"] = [a.to_dict() if isinstance(a, ArtifactRef) else a for a in self.artifact_refs]
        d["verified"] = False
        return d


# ---------------------------------------------------------------------------
# Validators (accept a typed shape OR a hostile inbound dict)
# ---------------------------------------------------------------------------

@dataclass
class ContractValidationResult:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.ok = self.ok and not self.errors


def _as_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return obj
    raise KanbanContractError(f"cannot validate {type(obj).__name__}; expected shape or dict")


def _validate_common(obj: Any, path_fields: Tuple[str, ...]) -> ContractValidationResult:
    errors: List[str] = []
    try:
        data = _as_dict(obj)
    except KanbanContractError as exc:
        return ContractValidationResult(ok=False, errors=[str(exc)])
    # 1. recursive authority scan over keys + values (Addenda D/E).
    _scan_authority(data, "", errors)
    # 2. path / ref hygiene (Addendum F).
    for pf in path_fields:
        val = data.get(pf)
        if isinstance(val, list):
            for i, item in enumerate(val):
                if isinstance(item, dict) and "path" in item:
                    _check_path(f"{pf}[{i}].path", item.get("path"), errors)
                else:
                    _check_path(f"{pf}[{i}]", item, errors)
        elif val not in (None, ""):
            _check_path(pf, val, errors)
    return ContractValidationResult(ok=not errors, errors=errors)


def validate_card_spec(obj: Union[KanbanCardSpec, Dict[str, Any]]) -> ContractValidationResult:
    res = _validate_common(obj, ("allowed_paths", "forbidden_paths", "worktree", "expected_evidence"))
    data = _as_dict(obj)
    if data.get("risk_class") not in ALLOWED_RISK_CLASSES:
        # No-raw-echo (#807): the supplied risk_class is user-controlled -- name the rule and
        # the fixed allowed set (taxonomy, NOT user input), never the rejected value.
        res.errors.append(f"risk_class not in allowed set {sorted(ALLOWED_RISK_CLASSES)}")
    for req in ("slice_id", "contextbundle_id", "lane"):
        if not data.get(req):
            res.errors.append(f"{req} missing or empty")
    return ContractValidationResult(ok=not res.errors, errors=res.errors, warnings=res.warnings)


def validate_worker_task_spec(obj: Union[WorkerTaskSpec, Dict[str, Any]]) -> ContractValidationResult:
    res = _validate_common(obj, ("allowed_paths", "prompt_pack_ref"))
    data = _as_dict(obj)
    if not data.get("contextbundle_id"):
        res.errors.append("contextbundle_id missing; a worker needs a ContextBundle, not raw repo authority")
    if data.get("dry_run") is False and not res.errors:
        res.warnings.append("dry_run=False requires a WRE gate; the card cannot grant it")
    return ContractValidationResult(ok=not res.errors, errors=res.errors, warnings=res.warnings)


def validate_evidence_packet(obj: Union[WreEvidencePacket, Dict[str, Any]]) -> ContractValidationResult:
    # Inbound dict asserting verified=true is rejected up front (advisory-until-verified).
    if isinstance(obj, dict) and _truthy(obj.get("verified")):
        return ContractValidationResult(
            ok=False,
            errors=["verified=true is forbidden on inbound evidence (advisory-until-verified)"],
        )
    res = _validate_common(obj, ("changed_files", "artifact_refs"))
    data = _as_dict(obj)
    for ref in data.get("artifact_refs", []) or []:
        if isinstance(ref, dict):
            for body_key in ("body", "content", "source_text", "file_body"):
                if body_key in ref:
                    res.errors.append(f"artifact_ref carries a body key '{body_key}' (refs only)")
    if data.get("verified") not in (False, None):
        res.errors.append("verified must be False on inbound evidence")
    return ContractValidationResult(ok=not res.errors, errors=res.errors, warnings=res.warnings)
