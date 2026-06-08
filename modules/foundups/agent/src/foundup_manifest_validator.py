#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FoundUp Manifest Validator -- Read-Only Build/Execution Contract Validator

Validates the declarative ``build_contract`` and ``execution_routing`` blocks
added to FoundUp manifests by FOUNDUP_MANIFEST_BASELINE_IMPL_PHASE1 (PR #770
predecessor). This validator protects the *shape and safety* of those contracts.

WSP 97 TRUTH BOUNDARIES:
  - This validator EXECUTES NOTHING. It reads JSON and returns result objects.
  - It performs no shell-out, no process spawning, no sockets / network access,
    no dynamic module loading, and no file writes.
  - It imports NO runtime executor or consumer (no Hermes executor, no OpenClaw
    runtime, no WRE FoundUpJob consumer, no AI Overseer).
  - Contract presence is NOT build readiness. A manifest may validate while
    build_ready / autonomous_execution_ready remain false. This slice does not
    promote readiness.

Architecture:
  build_contract / execution_routing are DECLARATIVE. They describe routing and
  the gates that real execution would have to pass; they do not grant execution
  permission and cannot self-authorize a gate bypass. Enforcement remains
  OpenClaw -> FoundUpJob -> WRE -> Hermes.

WSP Compliance:
  WSP 11  : Interface contract (typed result objects)
  WSP 50  : Pre-Action Verification (validate before any downstream use)
  WSP 84  : Code reuse (extends manifest convention; no new build system)
  WSP 97  : Truth boundaries (read-only, no overclaim, no execution)

NAVIGATION:
  -> Validates: modules/foundups/<...>/foundup_manifest.json (build_contract,
     execution_routing)
  -> Related (NOT imported): build_plan_generator.py, foundup_job_contract.py
  -> Tested by: modules/foundups/agent/tests/test_foundup_manifest_validator.py
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Union

__all__ = [
    "ManifestValidationResult",
    "validate_manifest",
    "validate_manifest_file",
    "REQUIRED_GATES",
    "REQUIRED_FORBIDDEN_MARKERS",
    "ALLOWED_ORCHESTRATORS",
    "ALLOWED_EXECUTORS",
    "ALLOWED_AUDITORS",
    "ALLOWED_BUILD_STATUS",
]

# ---------------------------------------------------------------------------
# Canonical required values (single source of truth for the validator)
# ---------------------------------------------------------------------------

# Gates a baseline build/test contract MUST reference. These mirror the secured
# boundaries: genesis gate (#747), typed exec boundary (#768), no-live-launch
# (#762), and the D0-D6 destructive-action guard.
REQUIRED_GATES: tuple = (
    "genesis_gate",
    "manifest_gate",
    "dry_run_gate",
    "test_gate",
    "destructive_action_guard_d0_d6",
    "typed_exec_boundary",
    "no_live_launch",
    "policy_required_sovereign_valve_for_non_dry_run",
)

# forbidden_paths MUST cover these markers. ".env" and "main.py" are exact;
# "_dae.py" and "vendor" are substring markers (e.g. "**/*_dae.py").
_REQUIRED_FORBIDDEN_EXACT: tuple = (".env", "main.py")
_REQUIRED_FORBIDDEN_SUBSTRING: tuple = ("_dae.py", "vendor")
REQUIRED_FORBIDDEN_MARKERS: tuple = _REQUIRED_FORBIDDEN_EXACT + _REQUIRED_FORBIDDEN_SUBSTRING

ALLOWED_ORCHESTRATORS: frozenset = frozenset({"openclaw"})
ALLOWED_EXECUTORS: frozenset = frozenset({"hermes"})
ALLOWED_AUDITORS: frozenset = frozenset({"ai_overseer"})
ALLOWED_BUILD_STATUS: frozenset = frozenset(
    {"BASELINE_DECLARATIVE_ONLY", "NEEDS_LABEL_RECONCILIATION"}
)

# Command argv elements may not contain these shell control characters. Path
# separators ("/") are deliberately NOT included -- a test path is not an
# injection vector. forbidden_paths globs ("**", "*") are NOT command argv and
# are not subject to this check.
_SHELL_METACHARACTERS: frozenset = frozenset(
    ";|&$`><(){}\n\r\t*?[]~!#\\\"'"
)
_SHELL_METAStringS: tuple = ("&&", "||", "$(", "${", ">>", "<<")

_COMMAND_FIELDS: tuple = ("build", "test", "dry_run")

# ---------------------------------------------------------------------------
# Canonical repo-relative path matching (predecessor PR #772 hardening)
# ---------------------------------------------------------------------------
# PR #772 audited the WRE context-bundle boundary and identified the prior
# suffix-match fallback in _expected_module_path_matches as latent today but
# mandatory to remove before any consumer derives allowed_source_roots from
# build_contract.module_path. This block implements exact-only repo-relative
# path equality with explicit rejection of absolute / UNC / traversal forms.
# No execution. No IO. No dynamic import.

# Validator file lives at modules/foundups/agent/src/foundup_manifest_validator.py.
# Four directory levels above is the repo root. The repo root is used ONLY to
# strip a known prefix from on-disk manifest paths during the compare; it is
# not used to read or execute anything.
_VALIDATOR_FILE = Path(__file__).resolve()
_REPO_ROOT_POSIX = _VALIDATOR_FILE.parents[4].as_posix()

# Matches a Windows drive prefix (e.g. "C:") or a leading "/". After
# backslash conversion, UNC paths such as "\\\\server\\share\\..." become
# "//server/share/..." which the leading-slash branch catches.
_ABSOLUTE_OR_UNC_PATTERN = re.compile(r"^([A-Za-z]:|/)")


@dataclass
class ManifestValidationResult:
    """Structured, read-only validation result. Contains no side effects."""

    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    manifest_path: str = ""

    def __post_init__(self) -> None:
        # ok is authoritative on errors; keep it consistent if constructed raw.
        self.ok = self.ok and not self.errors


# ---------------------------------------------------------------------------
# Internal helpers (pure)
# ---------------------------------------------------------------------------

def _normalize(path: str) -> str:
    return str(path).replace("\\", "/")


def _is_argv_list_or_null(value: Any) -> bool:
    """A command must be null or a list of strings (never a shell string)."""
    if value is None:
        return True
    if not isinstance(value, list):
        return False
    return all(isinstance(item, str) for item in value)


def _argv_metachar_offenders(argv: List[str]) -> List[str]:
    offenders: List[str] = []
    for item in argv:
        if any(ch in _SHELL_METACHARACTERS for ch in item):
            offenders.append(item)
            continue
        if any(token in item for token in _SHELL_METAStringS):
            offenders.append(item)
    return offenders


def _scan_bypass_flags(node: Any, trail: str, errors: List[str]) -> None:
    """Reject any truthy key that marks a gate bypass as allowed."""
    if isinstance(node, dict):
        for key, value in node.items():
            key_l = str(key).lower()
            if "bypass" in key_l and bool(value) is True:
                errors.append(
                    f"gate-bypass flag '{trail}{key}' is set truthy; "
                    f"contracts cannot mark gate bypass as allowed"
                )
            _scan_bypass_flags(value, f"{trail}{key}.", errors)
    elif isinstance(node, list):
        for idx, item in enumerate(node):
            _scan_bypass_flags(item, f"{trail}{idx}.", errors)


def _canonicalize_module_path(raw: Any) -> Optional[str]:
    """Canonicalize a manifest-declared module_path to repo-relative POSIX form.

    Accepts harmless equivalents only: leading "./", repeated "/", "."
    segments, backslashes. Returns the canonical form with no leading or
    trailing "/", no "." segments, and no "//"-runs.

    Rejects (returns None):
      - non-string or empty input
      - absolute paths (drive letter prefix such as "C:" or leading "/")
      - UNC paths (after backslash conversion they appear as leading "//")
      - any ".." segment (traversal not permitted in a declarative
        repo-relative subpath)
    """
    if not isinstance(raw, str):
        return None
    text = raw.strip().replace("\\", "/")
    if not text:
        return None
    if _ABSOLUTE_OR_UNC_PATTERN.match(text):
        return None
    parts: List[str] = []
    for seg in text.split("/"):
        seg = seg.strip()
        if seg in ("", "."):
            continue
        if seg == "..":
            return None
        parts.append(seg)
    if not parts:
        return None
    return "/".join(parts)


def _canonicalize_manifest_path_for_compare(raw: Any) -> Optional[str]:
    """Canonicalize an on-disk manifest path to repo-relative POSIX form.

    Identical to ``_canonicalize_module_path`` with one additional step: if
    the path begins with the validator's known repo root, that prefix is
    stripped (case-insensitive, to tolerate Windows drive-letter casing).
    Any leftover absolute / UNC / traversal form is rejected.
    """
    if not isinstance(raw, str):
        return None
    text = raw.strip().replace("\\", "/")
    if not text:
        return None
    repo_lower = _REPO_ROOT_POSIX.lower()
    text_lower = text.lower()
    if text_lower.startswith(repo_lower + "/"):
        text = text[len(_REPO_ROOT_POSIX) + 1:]
    elif text_lower == repo_lower:
        # The path IS the repo root; there is no manifest there. Reject.
        return None
    if _ABSOLUTE_OR_UNC_PATTERN.match(text):
        return None
    parts: List[str] = []
    for seg in text.split("/"):
        seg = seg.strip()
        if seg in ("", "."):
            continue
        if seg == "..":
            return None
        parts.append(seg)
    if not parts:
        return None
    return "/".join(parts)


def _expected_module_path_matches(manifest_path: str, module_path: str) -> bool:
    """Require EXACT normalized repo-relative path equality between
    ``build_contract.module_path`` and the manifest file's parent directory.

    Both inputs are canonicalized to repo-relative POSIX form (backslashes
    converted to "/", leading "./" stripped, "." segments collapsed,
    "//"-runs collapsed, repo-root prefix stripped from the manifest path
    only). Absolute paths, UNC paths, and ".." traversal are REJECTED in
    both inputs.

    Suffix-only matches (parent that merely ends with "/" + module_path)
    are REJECTED. Predecessor PR #772 identified the prior suffix-match
    fallback as latent today but mandatory to remove before any consumer
    derives ``allowed_source_roots`` from ``module_path``.
    """
    canonical_module = _canonicalize_module_path(module_path)
    if canonical_module is None:
        return False
    canonical_manifest = _canonicalize_manifest_path_for_compare(manifest_path)
    if canonical_manifest is None:
        return False
    parent = PurePosixPath(canonical_manifest).parent.as_posix()
    if parent == ".":
        return False
    return parent == canonical_module


def _validate_command_block(
    block_name: str, block: Any, errors: List[str]
) -> None:
    if not isinstance(block, dict):
        errors.append(f"build_contract.{block_name} must be an object")
        return
    if "command" not in block:
        errors.append(f"build_contract.{block_name}.command missing")
        return
    command = block["command"]
    if isinstance(command, str):
        errors.append(
            f"build_contract.{block_name}.command is a shell string; "
            f"must be an argv list or null"
        )
        return
    if not _is_argv_list_or_null(command):
        errors.append(
            f"build_contract.{block_name}.command must be an argv list "
            f"(list of strings) or null"
        )
        return
    if isinstance(command, list):
        offenders = _argv_metachar_offenders(command)
        if offenders:
            errors.append(
                f"build_contract.{block_name}.command argv contains shell "
                f"metacharacters: {offenders}"
            )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_manifest(
    data: Dict[str, Any],
    manifest_path: str = "",
    *,
    allow_readiness_promotion: bool = False,
) -> ManifestValidationResult:
    """Validate a manifest dict's build_contract + execution_routing blocks.

    Pure function: no IO, no execution. Returns a ManifestValidationResult.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(data, dict):
        return ManifestValidationResult(
            ok=False,
            errors=["manifest must be a JSON object"],
            manifest_path=manifest_path,
        )

    top_foundup_id = data.get("foundup_id")
    if not top_foundup_id:
        errors.append("top-level foundup_id missing or empty")

    # --- build_contract --------------------------------------------------
    build_contract = data.get("build_contract")
    if not isinstance(build_contract, dict):
        errors.append("build_contract block missing or not an object")
    else:
        bc_fid = build_contract.get("foundup_id")
        if bc_fid != top_foundup_id:
            errors.append(
                f"build_contract.foundup_id '{bc_fid}' does not match "
                f"top-level foundup_id '{top_foundup_id}'"
            )

        module_path = build_contract.get("module_path")
        if not isinstance(module_path, str) or not module_path:
            errors.append("build_contract.module_path missing or empty")
        elif manifest_path and not _expected_module_path_matches(
            manifest_path, module_path
        ):
            errors.append(
                f"build_contract.module_path '{module_path}' does not match "
                f"manifest location '{_normalize(manifest_path)}'"
            )

        status = build_contract.get("status")
        if status not in ALLOWED_BUILD_STATUS:
            errors.append(
                f"build_contract.status '{status}' not in "
                f"{sorted(ALLOWED_BUILD_STATUS)}"
            )

        for block_name in _COMMAND_FIELDS:
            if block_name not in build_contract:
                errors.append(f"build_contract.{block_name} missing")
            else:
                _validate_command_block(
                    block_name, build_contract[block_name], errors
                )

        dry_run = build_contract.get("dry_run")
        if isinstance(dry_run, dict):
            if dry_run.get("default") is False:
                errors.append(
                    "build_contract.dry_run.default is false; dry-run must "
                    "default to true"
                )
            if dry_run.get("required") is not True:
                errors.append("build_contract.dry_run.required must be true")

        forbidden = build_contract.get("forbidden_paths")
        if not isinstance(forbidden, list) or not forbidden:
            errors.append("build_contract.forbidden_paths missing or empty")
        else:
            for marker in _REQUIRED_FORBIDDEN_EXACT:
                if marker not in forbidden:
                    errors.append(
                        f"build_contract.forbidden_paths missing required "
                        f"entry '{marker}'"
                    )
            for marker in _REQUIRED_FORBIDDEN_SUBSTRING:
                if not any(marker in str(p) for p in forbidden):
                    errors.append(
                        f"build_contract.forbidden_paths missing required "
                        f"coverage for '{marker}'"
                    )

        gates = build_contract.get("required_gates")
        if not isinstance(gates, list) or not gates:
            errors.append("build_contract.required_gates missing or empty")
        else:
            for gate in REQUIRED_GATES:
                if gate not in gates:
                    errors.append(
                        f"build_contract.required_gates missing gate '{gate}'"
                    )

        readiness = build_contract.get("readiness")
        if not isinstance(readiness, dict):
            errors.append("build_contract.readiness missing or not an object")
        else:
            if readiness.get("build_ready") is True:
                errors.append(
                    "build_contract.readiness.build_ready is true; this slice "
                    "does not promote build readiness"
                )
            if readiness.get("autonomous_execution_ready") is True:
                errors.append(
                    "build_contract.readiness.autonomous_execution_ready is "
                    "true; autonomous execution readiness is not permitted"
                )
            if readiness.get("manifest_ready") is True and not allow_readiness_promotion:
                errors.append(
                    "build_contract.readiness.manifest_ready is true; this "
                    "slice does not promote manifest readiness"
                )

        if "safe_mutation_surface" not in build_contract:
            errors.append("build_contract.safe_mutation_surface missing")
        if "evidence_output" not in build_contract:
            errors.append("build_contract.evidence_output missing")

    # --- execution_routing ----------------------------------------------
    routing = data.get("execution_routing")
    if not isinstance(routing, dict):
        errors.append("execution_routing block missing or not an object")
    else:
        orchestrator = routing.get("orchestrator")
        if orchestrator not in ALLOWED_ORCHESTRATORS:
            errors.append(
                f"execution_routing.orchestrator '{orchestrator}' is unknown "
                f"or privileged; allowed: {sorted(ALLOWED_ORCHESTRATORS)}"
            )

        executor = routing.get("executor")
        if executor not in ALLOWED_EXECUTORS:
            errors.append(
                f"execution_routing.executor '{executor}' is unknown or "
                f"privileged; allowed: {sorted(ALLOWED_EXECUTORS)}"
            )

        auditor = routing.get("auditor")
        if auditor not in ALLOWED_AUDITORS:
            errors.append(
                f"execution_routing.auditor '{auditor}' is unknown; "
                f"allowed: {sorted(ALLOWED_AUDITORS)}"
            )

        if routing.get("external_agent_allowed") is True:
            errors.append(
                "execution_routing.external_agent_allowed is true; external "
                "agents are untrusted-by-default and must remain disabled"
            )

        if routing.get("declarative_only") is not True:
            errors.append(
                "execution_routing.declarative_only must be true; routing is "
                "declaration only"
            )

        if routing.get("can_self_authorize") is True:
            errors.append(
                "execution_routing.can_self_authorize is true; routing cannot "
                "self-authorize execution or gate bypass"
            )

        for required_key in (
            "wre_coordinator",
            "external_agent_contract_required",
            "build_plan_source",
            "job_contract_source",
        ):
            if required_key not in routing:
                errors.append(f"execution_routing.{required_key} missing")

    # --- global: reject any gate-bypass marker ---------------------------
    if isinstance(build_contract, dict):
        _scan_bypass_flags(build_contract, "build_contract.", errors)
    if isinstance(routing, dict):
        _scan_bypass_flags(routing, "execution_routing.", errors)

    return ManifestValidationResult(
        ok=not errors,
        errors=errors,
        warnings=warnings,
        manifest_path=_normalize(manifest_path),
    )


def validate_manifest_file(
    manifest_path: Union[str, PurePosixPath],
    *,
    allow_readiness_promotion: bool = False,
) -> ManifestValidationResult:
    """Read a manifest file (read-only) and validate it.

    Reads via Path.read_text; performs no writes and no execution.
    """
    path_str = _normalize(str(manifest_path))
    try:
        raw = Path(manifest_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return ManifestValidationResult(
            ok=False,
            errors=[f"manifest file not found: {path_str}"],
            manifest_path=path_str,
        )
    except OSError as exc:  # pragma: no cover - environment dependent
        return ManifestValidationResult(
            ok=False,
            errors=[f"manifest file unreadable: {exc}"],
            manifest_path=path_str,
        )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return ManifestValidationResult(
            ok=False,
            errors=[f"manifest is not valid JSON: {exc}"],
            manifest_path=path_str,
        )

    return validate_manifest(
        data,
        manifest_path=path_str,
        allow_readiness_promotion=allow_readiness_promotion,
    )
