#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ContextBundle Builder -- Read-Only Provenance Envelope for Validated Manifests

Converts a validated FoundUp manifest (build_contract / execution_routing)
into a bounded provenance envelope (ContextBundle) for future WRE / Hermes
use. This module produces the bundle object ONLY. It does NOT:

  - wire the bundle into any WRE consumer
  - call Hermes, OpenClaw, AI Overseer, or any runtime executor
  - dispatch / enqueue / drain FoundUpJob
  - run builds or execute commands
  - promote manifest / build / autonomous-execution readiness
  - serialize gate pass-or-fail booleans as authority

Predecessors:
  #768 typed shell=False exec boundary + redaction
  #769 durable design / build on existing primitives
  #770 manifest readiness audit
  #771 baseline build_contract / execution_routing + read-only validator
  #772 WRE context bundle boundary audit
  #773 canonical exact module_path validator hardening
  #774 OpenClaw / WRE / Hermes execution-chain audit

Trust seam (carry-forward from #774):
  Hermes legacy executor still trusts payload.module_path. That trust is
  BLOCKED before consumer wiring. This bundle's ``module_path`` is sourced
  from the validated manifest's ``build_contract.module_path`` ONLY,
  never from an external job payload. The public ``build_context_bundle``
  API exposes no ``job_payload`` / ``payload`` / ``job`` / ``task`` /
  ``request`` parameter; a test enforces this.

Validator pinning (#773):
  ``foundup_manifest_validator.validate_manifest_file`` is imported and
  called BEFORE trusting ``module_path``. The validator is the single
  source of truth for canonical exact-match. We do NOT reimplement its
  logic; we import its public API and the one helper we need for
  module_path canonicalization.

WSP 97 TRUTH BOUNDARIES:
  - Read-only. No subprocess, no Popen, no os.system, no eval, no exec,
    no importlib dynamic loading, no network, no runtime command exec.
  - File bodies are NEVER included in the bundle. Only path + sha256 +
    size + role. Hashes are stream-computed in chunks (no full-body
    in-memory load).
  - max_context_bytes is enforced fail-closed: an oversized total causes
    exclusion-with-record, never silent truncation.
  - Symlink escapes module_path -> rejected.
  - Forbidden paths (.env, main.py, *_dae.py, vendor/, wallet/, token/,
    reward/, payout/, cabr/, blockchain/, credentials*, secrets*) are
    excluded with a counter recorded under ``excluded_paths_summary``.
  - Readiness fields are echoed VERBATIM from the manifest; this module
    NEVER flips a readiness flag to True. If the manifest carries any
    readiness=True, the builder REJECTS.
  - ``bundle_id`` is sha256-derived from
    ``source_manifest_sha256 + "|" + module_path + "|" + bundle_version``
    -- deterministic, never wall-clock, never random.
  - ``created_at`` is a REQUIRED parameter; the builder does NOT call
    time.time() / now() to populate identity fields.

WSP Compliance:
  WSP 11  : Interface contract (typed result objects).
  WSP 50  : Pre-action validation -- call validator BEFORE building.
  WSP 77  : Agent coordination -- consumed by future WRE / Hermes use only.
  WSP 84  : Code reuse -- imports validator; does not reimplement.
  WSP 97  : Truth boundaries (read-only, no overclaim, no execution).

NAVIGATION:
  -> Validates via: foundup_manifest_validator.validate_manifest_file
  -> Builds: ContextBundle (frozen dataclass)
  -> Tested by: modules/foundups/agent/tests/test_context_bundle_builder.py
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from modules.foundups.agent.src.foundup_manifest_validator import (
    ManifestValidationResult,
    validate_manifest_file,
    _canonicalize_module_path,
)

__all__ = [
    "ContextBundle",
    "ContextBundleRejected",
    "FileRef",
    "ProvenanceRecord",
    "build_context_bundle",
    "BUNDLE_VERSION",
    "BUILDER_VERSION",
    "DEFAULT_MAX_CONTEXT_BYTES",
    "PER_FILE_READ_CAP_BYTES",
]

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

BUNDLE_VERSION = "0.1.0"
BUILDER_VERSION = "0.1.0"

# Default total cap for the sum of all included-file sizes in a bundle.
DEFAULT_MAX_CONTEXT_BYTES = 65536  # 64 KiB

# Per-file read cap. A file larger than this is recorded as excluded
# (oversized) using Path.stat() and is NEVER stream-read in full. This
# prevents any single file from causing memory pressure during hashing.
PER_FILE_READ_CAP_BYTES = 4 * 1024 * 1024  # 4 MiB

# Stream-hash chunk size. Files are hashed in successive reads of this size;
# the full body is never held in memory.
_HASH_CHUNK_BYTES = 65536

# Bounded test-file collection. If build_contract.test.command points at a
# tests directory, we walk for ``test_*.py`` files capped here to prevent
# walking pathological trees.
_MAX_TEST_FILES_PER_DIR = 50

# WSPs explicitly applied by this builder. Recorded in provenance.
_WSPS_APPLIED: Tuple[str, ...] = ("WSP_11", "WSP_50", "WSP_77", "WSP_84", "WSP_97")

# Optional module-doc roles. (relative filename, role).
_OPTIONAL_DOC_REFS: Tuple[Tuple[str, str], ...] = (
    ("README.md", "readme"),
    ("INTERFACE.md", "interface"),
    ("ModLog.md", "modlog"),
    ("ROADMAP.md", "roadmap"),
    ("tests/TestModLog.md", "testmodlog"),
    ("requirements.txt", "requirements"),
)

# Exclusion reasons recorded under ``excluded_paths_summary``.
_REASON_OUTSIDE_REPO = "outside_repo"
_REASON_OUTSIDE_MODULE = "outside_module"
_REASON_FORBIDDEN = "forbidden_path"
_REASON_OVERSIZED = "oversized"
_REASON_UNREADABLE = "unreadable"
_REASON_OVER_TOTAL_CAP = "over_total_cap"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ContextBundleRejected(Exception):
    """Raised when validation or any safety check refuses to build a bundle.

    On rejection the builder NEVER produces a bundle. The exception
    message is suitable for logging at the call site; no secrets are
    embedded in the message.
    """


# ---------------------------------------------------------------------------
# Typed result objects (frozen; no setters; no execution)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FileRef:
    """Minimal file reference: path + sha256 + size + role.

    NEVER contains: file body, source text, prompt text copied from
    files, secrets, environment content, or command output.
    """

    path: str            # repo-relative POSIX
    sha256: str          # 64-hex-char lower-case
    size_bytes: int      # >= 0
    role: str            # "manifest" | "readme" | "interface" | "modlog" | "test" | ...


@dataclass(frozen=True)
class ProvenanceRecord:
    """Builder + validator + repo provenance. No file bodies."""

    builder_version: str
    validator_module_path: str  # repo-relative POSIX
    validator_sha256: str
    repo_root: str              # absolute POSIX
    source_manifest_sha256: str
    wsps_applied: Tuple[str, ...]


@dataclass(frozen=True)
class ContextBundle:
    """Read-only provenance envelope for a validated manifest.

    NEVER carries gate pass-or-fail authority. The bundle may LIST the
    names of required gates to re-check; it does NOT serialize
    gate_passed / security_passed / permission_passed / dry_run_passed /
    build_ready / autonomous_execution_ready / cabr_ready / payout_ready /
    dao_ready = true as truth fields.
    """

    bundle_version: str
    bundle_id: str
    created_at: str
    source_manifest_path: str
    source_manifest_sha256: str
    foundup_id: str
    module_path: str  # canonical, repo-relative POSIX
    contract_version: str
    build_contract_status: str
    execution_routing_summary: Dict[str, Any]
    dry_run_required: bool
    readiness_flags: Dict[str, bool]  # echoed from manifest; never promoted here
    required_gates_to_recheck: Tuple[str, ...]
    forbidden_paths: Tuple[str, ...]
    safe_mutation_surface: Tuple[str, ...]
    included_file_refs: Tuple[FileRef, ...]
    excluded_paths_summary: Dict[str, int]
    max_context_bytes: int
    total_referenced_bytes: int
    validator_result_summary: Dict[str, Any]
    provenance: ProvenanceRecord

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_version": self.bundle_version,
            "bundle_id": self.bundle_id,
            "created_at": self.created_at,
            "source_manifest_path": self.source_manifest_path,
            "source_manifest_sha256": self.source_manifest_sha256,
            "foundup_id": self.foundup_id,
            "module_path": self.module_path,
            "contract_version": self.contract_version,
            "build_contract_status": self.build_contract_status,
            "execution_routing_summary": dict(self.execution_routing_summary),
            "dry_run_required": self.dry_run_required,
            "readiness_flags": dict(self.readiness_flags),
            "required_gates_to_recheck": list(self.required_gates_to_recheck),
            "forbidden_paths": list(self.forbidden_paths),
            "safe_mutation_surface": list(self.safe_mutation_surface),
            "included_file_refs": [
                {"path": r.path, "sha256": r.sha256, "size_bytes": r.size_bytes, "role": r.role}
                for r in self.included_file_refs
            ],
            "excluded_paths_summary": dict(self.excluded_paths_summary),
            "max_context_bytes": self.max_context_bytes,
            "total_referenced_bytes": self.total_referenced_bytes,
            "validator_result_summary": dict(self.validator_result_summary),
            "provenance": {
                "builder_version": self.provenance.builder_version,
                "validator_module_path": self.provenance.validator_module_path,
                "validator_sha256": self.provenance.validator_sha256,
                "repo_root": self.provenance.repo_root,
                "source_manifest_sha256": self.provenance.source_manifest_sha256,
                "wsps_applied": list(self.provenance.wsps_applied),
            },
        }


# ---------------------------------------------------------------------------
# Internal helpers (pure; no IO except documented reads; no execution)
# ---------------------------------------------------------------------------


def _normalize_posix(p: str) -> str:
    return str(p).replace("\\", "/")


def _is_path_within(child_realpath: Path, base_realpath: Path) -> bool:
    """True if ``child_realpath`` is at or under ``base_realpath`` after
    symlink resolution. Uses ``Path.relative_to`` semantics; never
    executes anything.
    """
    try:
        child_realpath.relative_to(base_realpath)
        return True
    except ValueError:
        return False


def _is_path_forbidden(repo_relative_posix: str) -> bool:
    """Forbidden-path screen for inclusion. Returns True if the path
    matches one of the never-include patterns. Case-insensitive on the
    full path; segment-aware for directory markers.
    """
    p = repo_relative_posix.lower()
    parts = p.split("/")
    base = parts[-1] if parts else ""
    # .env  /  .env.foo  /  any leaf starting with ".env"
    if base == ".env" or base.startswith(".env."):
        return True
    # main.py at any directory level
    if base == "main.py":
        return True
    # *_dae.py at any directory level
    if base.endswith("_dae.py"):
        return True
    # credentials* / secrets*
    if base.startswith("credentials") or base.startswith("secrets"):
        return True
    # Forbidden directory segments anywhere in the path.
    forbidden_segments = {
        "vendor", "wallet", "token", "reward", "payout",
        "cabr", "blockchain",
    }
    for seg in parts[:-1]:  # exclude the basename
        if seg in forbidden_segments:
            return True
    return False


def _stream_sha256(path: Path) -> Tuple[str, int]:
    """Stream-hash a file in chunks. Returns ``(hex_digest, size_bytes)``.

    NEVER loads the full body into memory. If the file size (from
    Path.stat) exceeds ``PER_FILE_READ_CAP_BYTES``, returns
    ``("", size)`` so the caller can record the file as excluded
    (oversized) without ever opening the body.

    Raises ``OSError`` if the file cannot be stat'd or opened. The caller
    is expected to record an "unreadable" exclusion in that case.
    """
    size = path.stat().st_size
    if size > PER_FILE_READ_CAP_BYTES:
        return ("", size)
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(_HASH_CHUNK_BYTES)
            if not chunk:
                break
            h.update(chunk)
    return (h.hexdigest(), size)


def _collect_candidate_refs(
    manifest_realpath: Path,
    repo_root: Path,
    module_root: Path,
    canonical_module: str,
    build_contract: Dict[str, Any],
) -> List[Tuple[Path, str, str]]:
    """Return the candidate list as a sequence of
    ``(realpath, repo_relative_posix, role)`` tuples.

    Inclusion is conservative: only the manifest itself plus
    well-known module-doc files plus test paths declared by
    ``build_contract.test.command`` IF they resolve inside
    ``module_root``. No filesystem walk outside ``module_root``.
    """
    candidates: List[Tuple[Path, str, str]] = []

    # Manifest is always a candidate (it is the provenance anchor).
    try:
        manifest_rel = manifest_realpath.relative_to(repo_root).as_posix()
    except ValueError:
        manifest_rel = canonical_module + "/foundup_manifest.json"
    candidates.append((manifest_realpath, manifest_rel, "manifest"))

    # Module-local doc refs.
    for fname, role in _OPTIONAL_DOC_REFS:
        try:
            p = (module_root / fname).resolve()
        except OSError:
            continue
        if not p.exists() or not p.is_file():
            continue
        if not _is_path_within(p, module_root):
            continue  # symlink escape
        try:
            rel = p.relative_to(repo_root).as_posix()
        except ValueError:
            continue
        candidates.append((p, rel, role))

    # Declared test files via build_contract.test.command argv.
    test_block = build_contract.get("test", {})
    if isinstance(test_block, dict):
        cmd = test_block.get("command")
        if isinstance(cmd, list):
            for token in cmd:
                if not isinstance(token, str):
                    continue
                tok = token.replace("\\", "/").strip()
                if not tok or tok.startswith("-") or tok in ("python", "pytest", "-m"):
                    continue
                try:
                    candidate = (repo_root / tok).resolve()
                except OSError:
                    continue
                if not _is_path_within(candidate, module_root):
                    continue
                if not candidate.exists():
                    continue
                if candidate.is_dir():
                    try:
                        test_files = sorted(candidate.rglob("test_*.py"))
                    except OSError:
                        test_files = []
                    for tf in test_files[:_MAX_TEST_FILES_PER_DIR]:
                        try:
                            tf_real = tf.resolve()
                        except OSError:
                            continue
                        if not _is_path_within(tf_real, module_root):
                            continue
                        try:
                            rel = tf_real.relative_to(repo_root).as_posix()
                        except ValueError:
                            continue
                        candidates.append((tf_real, rel, "test"))
                elif candidate.is_file():
                    try:
                        rel = candidate.relative_to(repo_root).as_posix()
                    except ValueError:
                        continue
                    candidates.append((candidate, rel, "test"))

    return candidates


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_context_bundle(
    manifest_path: Path,
    repo_root: Path,
    *,
    created_at: str,
    max_context_bytes: int = DEFAULT_MAX_CONTEXT_BYTES,
) -> ContextBundle:
    """Build a read-only ``ContextBundle`` from a validated manifest.

    Args:
        manifest_path: path to a FoundUp manifest JSON. Must be readable
            and inside ``repo_root`` after symlink resolution.
        repo_root: repository root used for path-safety checks. Both
            inputs are resolved (symlinks followed) before comparison.
        created_at: REQUIRED non-empty string. The builder does NOT call
            wall-clock APIs. The caller injects a deterministic value
            (for example an ISO-8601 timestamp captured at the call
            site). ``bundle_id`` is sha256-derived and remains identical
            across runs that pass the same inputs and the same
            ``created_at``.
        max_context_bytes: total cap on the sum of included file sizes.
            Default 64 KiB. Fail-closed: if the cap would be exceeded the
            offending file is recorded as excluded
            (``over_total_cap``), never silently truncated.

    Returns:
        ContextBundle (frozen dataclass).

    Raises:
        ContextBundleRejected: on any validation failure, readiness
            promotion, non-declarative routing, external-agent-allowed,
            self-authorization, module_path escape, or other safety
            refusal. The builder NEVER produces a bundle on rejection.
    """
    # --- 0. Argument guards ---
    if not isinstance(created_at, str) or not created_at.strip():
        raise ContextBundleRejected("created_at must be a non-empty string")
    if not isinstance(max_context_bytes, int) or max_context_bytes <= 0:
        raise ContextBundleRejected("max_context_bytes must be a positive int")

    manifest_path = Path(manifest_path)
    repo_root = Path(repo_root).resolve()

    # --- 1. Validate via #773 validator (imported, not reimplemented) ---
    validation: ManifestValidationResult = validate_manifest_file(manifest_path)
    if not validation.ok:
        raise ContextBundleRejected(
            "manifest validation failed: "
            + str(len(validation.errors))
            + " errors: "
            + " | ".join(validation.errors[:3])
        )

    # --- 2. Read manifest JSON (validator already verified shape) ---
    try:
        manifest_realpath = manifest_path.resolve()
    except OSError as exc:
        raise ContextBundleRejected(
            "manifest path could not be resolved: " + type(exc).__name__
        )
    if not _is_path_within(manifest_realpath, repo_root):
        raise ContextBundleRejected("manifest path escapes repo root after resolve()")
    try:
        raw_manifest = manifest_realpath.read_text(encoding="utf-8")
        data = json.loads(raw_manifest)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContextBundleRejected("manifest unreadable: " + type(exc).__name__)

    build_contract = data.get("build_contract", {})
    routing = data.get("execution_routing", {})
    readiness = build_contract.get("readiness", {}) if isinstance(build_contract, dict) else {}

    # --- 3. Defence-in-depth safety re-checks (validator already enforces) ---
    if readiness.get("build_ready") is True:
        raise ContextBundleRejected("readiness.build_ready=true; bundle refuses promotion")
    if readiness.get("autonomous_execution_ready") is True:
        raise ContextBundleRejected(
            "readiness.autonomous_execution_ready=true; bundle refuses promotion"
        )
    if readiness.get("manifest_ready") is True:
        raise ContextBundleRejected("readiness.manifest_ready=true; bundle refuses promotion")
    if routing.get("external_agent_allowed") is True:
        raise ContextBundleRejected("execution_routing.external_agent_allowed=true; refused")
    if routing.get("can_self_authorize") is True:
        raise ContextBundleRejected("execution_routing.can_self_authorize=true; refused")
    if routing.get("declarative_only") is not True:
        raise ContextBundleRejected(
            "execution_routing.declarative_only must be true; routing is declaration only"
        )

    # --- 4. Module path canonicalization (uses validator helper) ---
    raw_module_path = build_contract.get("module_path", "")
    canonical_module = _canonicalize_module_path(raw_module_path)
    if canonical_module is None:
        raise ContextBundleRejected(
            "build_contract.module_path canonicalization failed"
        )
    try:
        module_root = (repo_root / canonical_module).resolve()
    except OSError:
        raise ContextBundleRejected("module_path could not be resolved")
    if not _is_path_within(module_root, repo_root):
        raise ContextBundleRejected("module_path escapes repo root after resolve()")

    # --- 5. Source manifest hash (stream) ---
    try:
        source_manifest_sha256, _ = _stream_sha256(manifest_realpath)
    except OSError as exc:
        raise ContextBundleRejected("manifest unhashable: " + type(exc).__name__)
    if not source_manifest_sha256:
        raise ContextBundleRejected("manifest exceeds per-file read cap; cannot hash")

    # --- 6. Candidate file collection ---
    candidates = _collect_candidate_refs(
        manifest_realpath=manifest_realpath,
        repo_root=repo_root,
        module_root=module_root,
        canonical_module=canonical_module,
        build_contract=build_contract,
    )

    # --- 7. Filter, hash, cap (fail-closed at total-cap boundary) ---
    included: List[FileRef] = []
    excluded: Dict[str, int] = {}
    total_bytes = 0
    seen_paths: set = set()

    for realpath, rel_posix, role in candidates:
        if rel_posix in seen_paths:
            continue
        seen_paths.add(rel_posix)

        # Symlink-escape rejection (manifest is allowed even outside module).
        if not _is_path_within(realpath, repo_root):
            excluded[_REASON_OUTSIDE_REPO] = excluded.get(_REASON_OUTSIDE_REPO, 0) + 1
            continue
        is_manifest_ref = (role == "manifest")
        if not is_manifest_ref and not _is_path_within(realpath, module_root):
            excluded[_REASON_OUTSIDE_MODULE] = excluded.get(_REASON_OUTSIDE_MODULE, 0) + 1
            continue

        if _is_path_forbidden(rel_posix):
            excluded[_REASON_FORBIDDEN] = excluded.get(_REASON_FORBIDDEN, 0) + 1
            continue

        try:
            sha, size = _stream_sha256(realpath)
        except OSError:
            excluded[_REASON_UNREADABLE] = excluded.get(_REASON_UNREADABLE, 0) + 1
            continue
        if not sha:
            excluded[_REASON_OVERSIZED] = excluded.get(_REASON_OVERSIZED, 0) + 1
            continue

        if total_bytes + size > max_context_bytes:
            excluded[_REASON_OVER_TOTAL_CAP] = (
                excluded.get(_REASON_OVER_TOTAL_CAP, 0) + 1
            )
            continue

        included.append(FileRef(path=rel_posix, sha256=sha, size_bytes=size, role=role))
        total_bytes += size

    # --- 8. Provenance (validator file path + hash) ---
    validator_path = Path(__file__).resolve().parent / "foundup_manifest_validator.py"
    try:
        validator_sha256, _ = _stream_sha256(validator_path)
    except OSError as exc:
        raise ContextBundleRejected("validator unhashable: " + type(exc).__name__)
    if not validator_sha256:
        raise ContextBundleRejected("validator exceeds per-file read cap; cannot hash")

    try:
        validator_rel = validator_path.relative_to(repo_root).as_posix()
    except ValueError:
        validator_rel = validator_path.as_posix()

    provenance = ProvenanceRecord(
        builder_version=BUILDER_VERSION,
        validator_module_path=validator_rel,
        validator_sha256=validator_sha256,
        repo_root=repo_root.as_posix(),
        source_manifest_sha256=source_manifest_sha256,
        wsps_applied=_WSPS_APPLIED,
    )

    # --- 9. Deterministic bundle_id ---
    bundle_id = hashlib.sha256(
        (
            source_manifest_sha256 + "|" + canonical_module + "|" + BUNDLE_VERSION
        ).encode("utf-8")
    ).hexdigest()

    # --- 10. Echo readiness verbatim (NEVER promote; validator already
    #         rejected truthy readiness; defensive echo only).
    readiness_flags = {
        "manifest_ready": bool(readiness.get("manifest_ready", False)),
        "build_ready": bool(readiness.get("build_ready", False)),
        "autonomous_execution_ready": bool(
            readiness.get("autonomous_execution_ready", False)
        ),
    }

    execution_routing_summary = {
        "orchestrator": routing.get("orchestrator"),
        "executor": routing.get("executor"),
        "auditor": routing.get("auditor"),
        "declarative_only": routing.get("declarative_only"),
        "external_agent_allowed": routing.get("external_agent_allowed"),
        "can_self_authorize": routing.get("can_self_authorize"),
    }

    return ContextBundle(
        bundle_version=BUNDLE_VERSION,
        bundle_id=bundle_id,
        created_at=created_at,
        source_manifest_path=_normalize_posix(str(manifest_path)),
        source_manifest_sha256=source_manifest_sha256,
        foundup_id=str(build_contract.get("foundup_id", "")),
        module_path=canonical_module,
        contract_version=str(build_contract.get("contract_version", "")),
        build_contract_status=str(build_contract.get("status", "")),
        execution_routing_summary=execution_routing_summary,
        dry_run_required=bool(
            isinstance(build_contract.get("dry_run"), dict)
            and build_contract["dry_run"].get("required", False)
        ),
        readiness_flags=readiness_flags,
        required_gates_to_recheck=tuple(build_contract.get("required_gates", []) or []),
        forbidden_paths=tuple(build_contract.get("forbidden_paths", []) or []),
        safe_mutation_surface=tuple(build_contract.get("safe_mutation_surface", []) or []),
        included_file_refs=tuple(included),
        excluded_paths_summary=dict(excluded),
        max_context_bytes=max_context_bytes,
        total_referenced_bytes=total_bytes,
        validator_result_summary={
            "ok": True,
            "error_count": 0,
            "warning_count": len(validation.warnings),
        },
        provenance=provenance,
    )
