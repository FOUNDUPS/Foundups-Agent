#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared Module-Path Resolution -- Validated FoundUpJob module_path Resolver.

Single-source-of-truth for the module-path trust rule. Lives independently of
both ``hermes_foundup_job_executor.py`` and ``build_plan_generator.py``; both
files import from here so the trust rule has exactly ONE implementation.

History (load-bearing precedent):

  - #774 audit identified payload.module_path trust at
    hermes_foundup_job_executor.py:217-237 as the consumer-wiring blocker.
  - #778 (HERMES_MODULE_PATH_TRUST_REMOVAL_PHASE1) closed the executor
    seam with this resolver, originally living in the executor file.
  - This module (BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1)
    is the Addendum-C behavior-preserving extraction. The executor now
    re-exports every name as a back-compat shim so its tests pass with
    ZERO edits; build_plan_generator imports from here directly.
  - WSP_97 verifies "exactly one implementation" via
    NO_SECOND_MODULE_PATH_RESOLVER (an AST scan in the shared-resolver
    test file).

WSP 97 TRUTH BOUNDARIES:

  - This module EXECUTES NOTHING. It reads JSON via ``Path.read_text``
    and calls the #773 validator (which is itself execution-free).
  - No subprocess, no Popen, no os.system, no eval, no exec, no
    importlib dynamic loading, no network, no file write.
  - No runtime executor / consumer imports. No CABR / payout / DAO.
  - The #771/#773 ``foundup_manifest_validator`` is the source of truth
    for canonical module_path exact-match. We import its public API
    plus one underscore-helper (``_canonicalize_module_path``) and do
    NOT mutate its public surface.

Public API:

  - ``ResolvedModulePath`` (frozen dataclass)
  - ``DEFAULT_REPO_ROOT`` (Path)
  - ``_MANIFEST_SEARCH_GLOBS`` (Tuple[str, ...])
  - ``FAIL_TOKEN_SYNTACTIC_REJECT`` / ``..._MANIFEST_MISMATCH`` /
    ``..._MANIFEST_MISSING`` / ``..._CROSS_FOUNDUP_MISMATCH`` (str)
  - ``ALL_FAIL_TOKENS`` (frozenset)
  - ``_resolve_validated_module_path(job, repo_root)`` -> ``ResolvedModulePath``
  - ``_find_manifest_for_foundup_id(repo_root, foundup_id)`` -> ``Optional[Path]``
  - ``_stringify_ignored(declared)`` -> ``Optional[str]``

NAVIGATION:

  -> Consumed by: hermes_foundup_job_executor.py (shim; re-exports here)
  -> Consumed by: build_plan_generator.py (direct import)
  -> Validates via: foundup_manifest_validator.validate_manifest_file (#773)
  -> Tested by: tests/test_module_path_resolution.py (#778 test file still
                exercises the same surface via the executor shim)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Tuple

from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    FoundUpJob,
)
from modules.foundups.agent.src.foundup_manifest_validator import (
    validate_manifest_file,
)
from modules.foundups.agent.src.foundup_manifest_validator import (
    _canonicalize_module_path as _validator_canonicalize_module_path,
)

__all__ = [
    "ResolvedModulePath",
    "DEFAULT_REPO_ROOT",
    "FAIL_TOKEN_SYNTACTIC_REJECT",
    "FAIL_TOKEN_MANIFEST_MISMATCH",
    "FAIL_TOKEN_MANIFEST_MISSING",
    "FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH",
    "ALL_FAIL_TOKENS",
]


# Default repository root for manifest lookup. Derived from this source file's
# location so the resolver does not depend on a CWD or env var.
# modules/foundups/agent/src/module_path_resolution.py -> parents[4] = repo root
# (identical depth to hermes_foundup_job_executor.py so the constant remains
# byte-equal to the #778 origin per Addendum-C extraction equivalence.)
DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[4]

# Bounded glob set for foundup_id -> manifest lookup when the job payload
# omits module_path / source_module entirely. Mirrors the canonical
# manifest directory set surveyed in Phase 0 (8 manifests on disk today;
# this resolver's lookup walks at most these globs and never recurses).
_MANIFEST_SEARCH_GLOBS: Tuple[str, ...] = (
    "modules/foundups/*/foundup_manifest.json",
    "modules/gamification/*/foundup_manifest.json",
    "modules/platform_integration/*/foundup_manifest.json",
    "modules/communication/*/foundup_manifest.json",
    "modules/ai_intelligence/*/foundup_manifest.json",
    "modules/infrastructure/*/foundup_manifest.json",
)

# Greppable failure-mode tokens emitted on resolution failure. The
# StatusReasonCode (executor side) stays frozen at FAIL_VALIDATION_ERROR;
# the build_plan_generator side maps these into GenerationValidationResult
# error_code. Granularity comes from this token prefix on reason_human +
# a parallel evidence_refs entry. This lets W10 and future audits
# distinguish failure classes by greppable string match instead of prose
# parsing.
FAIL_TOKEN_SYNTACTIC_REJECT: str = "syntactic_reject"
FAIL_TOKEN_MANIFEST_MISMATCH: str = "manifest_mismatch"
FAIL_TOKEN_MANIFEST_MISSING: str = "manifest_missing"
FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH: str = "cross_foundup_mismatch"

ALL_FAIL_TOKENS: frozenset = frozenset({
    FAIL_TOKEN_SYNTACTIC_REJECT,
    FAIL_TOKEN_MANIFEST_MISMATCH,
    FAIL_TOKEN_MANIFEST_MISSING,
    FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH,
})


@dataclass(frozen=True)
class ResolvedModulePath:
    """Outcome of validated module-path resolution.

    Observable-ignore shape mirroring
    ``modules/foundups/agent/src/source_authority.py:resolve_source_authority``:
    the consumer can inspect ``ignored`` to see exactly what the caller
    tried to declare, even on success. Silent swallow is refused per the
    #777 convention.

    Attributes:
        effective: canonical module_path from the validated manifest (the
            source of truth). ``None`` iff ``failed`` is True.
        ignored: the payload-declared candidate, stringified, or ``None``
            if and only if the caller supplied no candidate (neither
            ``payload.module_path`` nor ``payload.source_module``).
            Visible even on success; this is the observable-ignore
            channel.
        failed: True iff resolution failed.
        fail_token: one of ``ALL_FAIL_TOKENS`` on failure, else ``None``.
        fail_human: human-readable explanation prefixed with the
            ``fail_token`` for grep-ability; empty on success.
    """

    effective: Optional[str]
    ignored: Optional[str]
    failed: bool
    fail_token: Optional[str]
    fail_human: str


def _stringify_ignored(declared: Any) -> Optional[str]:
    """Mirror of ``source_authority.py``'s ignored-value stringification.

    Returns ``None`` if and only if ``declared`` is ``None``; otherwise
    ``str(declared)``. The observable-ignore channel uses this so callers
    can detect a (potentially malicious) declaration attempt regardless
    of input type.
    """
    if declared is None:
        return None
    return str(declared)


def _find_manifest_for_foundup_id(
    repo_root: Path, foundup_id: str
) -> Optional[Path]:
    """Locate a manifest file whose top-level ``foundup_id`` matches.

    Bounded scan over the 6 canonical manifest directories (Phase 0 found
    8 manifests today). Returns the first matching path, or ``None``.
    Used ONLY when the job payload omits both ``module_path`` and
    ``source_module``; this is the explicit alternative to the removed
    ``foundup_id``-as-path heuristic.

    The scan reads each candidate JSON only to check its top-level
    ``foundup_id`` field. No execution. No write.
    """
    if not foundup_id:
        return None
    for glob in _MANIFEST_SEARCH_GLOBS:
        for candidate in sorted(repo_root.glob(glob)):
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("foundup_id") == foundup_id:
                return candidate
    return None


def _resolve_validated_module_path(
    job: FoundUpJob,
    repo_root: Path,
) -> ResolvedModulePath:
    """Resolve a job's ``module_path`` through the #773 validator. Fail-closed.

    Pinned design (HERMES_MODULE_PATH_TRUST_REMOVAL_PHASE1):

    - **candidate** = ``payload.module_path`` or, if absent, the alias
      ``payload.source_module``. Empty string is treated as ABSENT
      (Addendum D #4).
    - **foundup_id heuristic REMOVED**: a ``/`` in ``foundup_id`` is
      no longer a path source. If the candidate is absent, fall through
      to a bounded foundup_id scan, NEVER to the raw ``foundup_id``
      string.
    - **syntactic hardening BEFORE any manifest contact**: the candidate
      is canonicalized via the validator's ``_canonicalize_module_path``
      helper. Empty / absolute / UNC / ``..`` traversal / backslash
      forms (and anything not under ``modules/``) are REJECTED with
      ``FAIL_TOKEN_SYNTACTIC_REJECT``.
    - **manifest location**: when the candidate resolves syntactically,
      the manifest is ``<repo_root>/<canonical>/foundup_manifest.json``.
      When the candidate is absent, the manifest is the first hit of the
      bounded foundup_id scan.
    - **validator gate**: ``validate_manifest_file`` (#773) is consumed
      as-is. It never raises; ``ok=False`` on missing / unreadable /
      shape-invalid manifest. Tokenized as ``manifest_missing`` for
      I/O-class errors, ``manifest_mismatch`` otherwise.
    - **cross-FoundUp substitution defense** (Addendum D #1, load-bearing):
      after validator passes, the manifest's ``foundup_id`` MUST equal
      ``job.foundup_id``. A job carrying ``foundup_id=A`` with a payload
      pointing at FoundUp B's real manifest is REJECTED with
      ``FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH``. The "some valid manifest
      exists for this path" check is NOT sufficient.
    - **case-variant defense** (Addendum D #3, Windows host reality):
      when the candidate was provided, the candidate's canonical form
      is exact-string-compared (case-sensitive) against the manifest's
      ``build_contract.module_path`` canonical form. Mismatch =>
      ``FAIL_TOKEN_MANIFEST_MISMATCH``.
    - **derivation when candidate absent**: ``effective`` becomes the
      manifest's canonical ``module_path`` (manifest is the source of
      truth). The ``foundup_id`` heuristic is never the source.
    - **observable ignored**: the payload-declared candidate is visible
      in ``ResolvedModulePath.ignored`` even on success (mirrors #777).
    """
    payload = job.payload or {}

    # Step 1: extract candidate; treat empty string as ABSENT.
    raw_candidate: Any = payload.get("module_path")
    if isinstance(raw_candidate, str) and not raw_candidate:
        raw_candidate = None
    if raw_candidate is None:
        raw_candidate = payload.get("source_module")
        if isinstance(raw_candidate, str) and not raw_candidate:
            raw_candidate = None
    ignored = _stringify_ignored(raw_candidate)

    canonical: Optional[str] = None
    manifest_path: Path

    if raw_candidate is not None:
        # Step 2: syntactic harden BEFORE any manifest contact.
        #
        # The validator's ``_canonicalize_module_path`` would itself convert
        # backslashes to forward slashes ("harmless equivalents"). For the
        # CONSUMER boundary (Addendum C #5) backslashes must be REJECTED
        # before any manifest contact -- on a Windows host, accepting them
        # invites path-name confusion. We do the backslash check here
        # explicitly so the rejection token is ``syntactic_reject`` and not
        # the more ambiguous ``manifest_mismatch``.
        if isinstance(raw_candidate, str) and "\\" in raw_candidate:
            return ResolvedModulePath(
                effective=None,
                ignored=ignored,
                failed=True,
                fail_token=FAIL_TOKEN_SYNTACTIC_REJECT,
                fail_human=(
                    f"{FAIL_TOKEN_SYNTACTIC_REJECT}: payload module_path "
                    f"{raw_candidate!r} contains backslashes; only "
                    f"POSIX-style forward slashes are accepted"
                ),
            )
        canonical = _validator_canonicalize_module_path(raw_candidate)
        if canonical is None or not canonical.startswith("modules/"):
            return ResolvedModulePath(
                effective=None,
                ignored=ignored,
                failed=True,
                fail_token=FAIL_TOKEN_SYNTACTIC_REJECT,
                fail_human=(
                    f"{FAIL_TOKEN_SYNTACTIC_REJECT}: payload module_path "
                    f"{raw_candidate!r} is empty, absolute, UNC, contains "
                    f"'..' traversal, or is not under modules/"
                ),
            )
        manifest_path = repo_root / canonical / "foundup_manifest.json"
    else:
        # Step 3: derive from validated manifest via bounded foundup_id scan.
        manifest_path_opt = _find_manifest_for_foundup_id(
            repo_root, job.foundup_id or ""
        )
        if manifest_path_opt is None:
            return ResolvedModulePath(
                effective=None,
                ignored=ignored,
                failed=True,
                fail_token=FAIL_TOKEN_MANIFEST_MISSING,
                fail_human=(
                    f"{FAIL_TOKEN_MANIFEST_MISSING}: no payload module_path; "
                    f"bounded scan for foundup_id={job.foundup_id!r} returned "
                    f"no manifest"
                ),
            )
        manifest_path = manifest_path_opt

    # Step 4: validate via #773 (never raises). Pass the manifest path as a
    # string -- the validator's public signature accepts ``str | PurePosixPath``
    # and normalizes internally; passing the OS ``Path`` directly satisfies
    # the runtime contract but tickles the static-type checker, which is why
    # we stringify here.
    result = validate_manifest_file(str(manifest_path))
    if not result.ok:
        err = result.errors[0] if result.errors else "validation failed"
        # I/O-class errors -> manifest_missing; shape errors -> manifest_mismatch.
        if (
            "not found" in err
            or "unreadable" in err
            or "not valid JSON" in err
        ):
            token = FAIL_TOKEN_MANIFEST_MISSING
        else:
            token = FAIL_TOKEN_MANIFEST_MISMATCH
        return ResolvedModulePath(
            effective=None,
            ignored=ignored,
            failed=True,
            fail_token=token,
            fail_human=f"{token}: {err}",
        )

    # Step 5: re-read the validated manifest to extract foundup_id and
    # module_path for the two final cross-checks. The validator confirmed
    # the manifest is well-formed and that its declared module_path matches
    # the manifest file's parent directory; we now confirm the foundup_id
    # binding and (when applicable) the candidate's case-sensitive match.
    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return ResolvedModulePath(
            effective=None,
            ignored=ignored,
            failed=True,
            fail_token=FAIL_TOKEN_MANIFEST_MISSING,
            fail_human=(
                f"{FAIL_TOKEN_MANIFEST_MISSING}: re-read failed: "
                f"{type(exc).__name__}"
            ),
        )
    manifest_foundup_id = manifest_data.get("foundup_id")
    manifest_module_path = manifest_data.get("build_contract", {}).get(
        "module_path", ""
    )
    canonical_manifest_module = _validator_canonicalize_module_path(
        manifest_module_path
    )

    if canonical_manifest_module is None:
        return ResolvedModulePath(
            effective=None,
            ignored=ignored,
            failed=True,
            fail_token=FAIL_TOKEN_MANIFEST_MISMATCH,
            fail_human=(
                f"{FAIL_TOKEN_MANIFEST_MISMATCH}: manifest at {manifest_path} "
                f"has un-canonicalizable build_contract.module_path="
                f"{manifest_module_path!r}"
            ),
        )

    # Step 6: cross-FoundUp substitution defense (Addendum D #1).
    if manifest_foundup_id != job.foundup_id:
        return ResolvedModulePath(
            effective=None,
            ignored=ignored,
            failed=True,
            fail_token=FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH,
            fail_human=(
                f"{FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH}: job.foundup_id="
                f"{job.foundup_id!r} but the manifest at {manifest_path} "
                f"declares foundup_id={manifest_foundup_id!r}"
            ),
        )

    # Step 7: when candidate provided, exact-string compare candidate canonical
    # vs manifest canonical (#773 exact-match at consumer boundary; Addendum
    # D #3 case-variant defense). When candidate was absent, derivation is
    # already from the validated manifest and this check is a no-op.
    if raw_candidate is not None and canonical != canonical_manifest_module:
        return ResolvedModulePath(
            effective=None,
            ignored=ignored,
            failed=True,
            fail_token=FAIL_TOKEN_MANIFEST_MISMATCH,
            fail_human=(
                f"{FAIL_TOKEN_MANIFEST_MISMATCH}: payload candidate canonical "
                f"{canonical!r} != manifest module_path "
                f"{canonical_manifest_module!r}"
            ),
        )

    # Success: effective is the manifest's canonical module_path (the source
    # of truth). The payload-declared value is preserved in ``ignored`` for
    # observability even when it matches.
    return ResolvedModulePath(
        effective=canonical_manifest_module,
        ignored=ignored,
        failed=False,
        fail_token=None,
        fail_human="",
    )
