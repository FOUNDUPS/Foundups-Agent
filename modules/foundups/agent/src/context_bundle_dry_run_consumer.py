#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ContextBundle Dry-Run Consumer -- Standalone, Return-Value-Only Preview.

First consumer wiring of the read-only #775 ContextBundle into the EXISTING
dry-run evidence path. This module CONSUMES a ContextBundle as its TRUSTED
input and returns a typed ``DryRunResult`` describing what a FoundUp dry-run
WOULD do. It performs NO live build, NO real execution, NO subprocess, NO
Hermes real delegation, NO executor sink, NO FAM event, and NO file write.

Phase-1 boundary (WRE_CONTEXT_BUNDLE_DRYRUN_CONSUMER_PHASE1, ruling A/B):

  - STANDALONE: this module + its tests consume a ContextBundle + the shared
    validated module-path resolver and RETURN a dry-run preview. It is NOT
    plumbed into the live OpenClaw / WRE consumer dispatch seam (#774). The
    runtime wiring is a separate Phase-2 slice.
  - RETURN-VALUE-ONLY: ``consume_context_bundle_dry_run`` returns a frozen
    ``DryRunResult``. It has NO side effects: no FAM event, no file write, no
    subprocess, no network. ``dry_run`` is always True; ``real_execution_
    performed`` is always False.

Adopted EXISTING dry-run primitives (NOT invented):

  - ``build_plan_executor.py`` (#779 W10 finding): ``BuildPlanExecutor.
    execute_step`` returns BLOCKED for ``dry_run=False`` and SIMULATED for
    dry-run; ``ExecutionReceipt`` truth fields are always False. The
    declared (never executed) action shape and the
    ``REAL_EXECUTION_NOT_IMPLEMENTED`` block reason are reused here for
    ``planned_actions`` and the dry-run assertion.
  - ``hermes_foundup_job_executor.execute_foundup_job`` (#778): the
    FoundUpJob -> WRE router -> Hermes dry-run path that resolves
    module_path via the shared validated resolver before any sink. This
    consumer reuses the SAME resolver object.
  - ``HERMES_DELEGATE_ENABLED`` (default 0) /
    ``BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED`` (wre_core
    ``hermes_job_executor.py``): live Hermes delegation stays BLOCKED. This
    consumer NEVER enables the flag and NEVER calls a real delegation sink.

Trust rules (PINNED -- not local decisions):

  1. The ContextBundle is the TRUSTED input. The consumer does NOT re-derive
     trust from the raw manifest / payload; it reads validated fields from
     the bundle (``module_path``, ``source_authority``,
     ``required_gates_to_recheck``, ``readiness_flags``,
     ``included_file_refs``).
  2. ``module_path`` comes ONLY from the bundle's validated value, optionally
     cross-checked against the shared single-source resolver
     ``module_path_resolution._resolve_validated_module_path`` (#778/#779).
     It is NEVER read from ``payload.module_path`` / ``payload.source_module``
     / ``foundup_id``-as-path. No second resolver is defined here.
  3. ``source_authority`` from the bundle MUST equal ``"monorepo_poc"``
     (``SourceAuthority.MONOREPO_POC`` in ``ACTIVE_STAGES``). The consumer
     CANNOT promote the stage; any non-monorepo_poc bundle is REFUSED.
  4. ``required_gates_to_recheck`` are gate NAMES to re-check, NEVER trusted
     as pass-state. The consumer records them as ``gates_to_recheck`` and
     asserts NO gate-pass boolean is serialized.
  5. DRY-RUN ONLY: the result describes what WOULD run. No real build /
     subprocess / Hermes real delegation / executor sink is ever invoked.
  6. Observable-ignore: any rejected / ignored payload value is visible in
     ``DryRunResult.rejected_input`` and is NEVER used as authority.

STRICT NON-GOALS (enforced by tests):
  - NO new orchestrator (OpenClaw owns the worker loop).
  - NO live build / real execution / subprocess build.
  - NO external agent (``external_agent_allowed`` stays untrusted/False).
  - NO readiness promotion (readiness flags echoed, all False).
  - NO repo concatenation (bundle refs + sha256 only; never file bodies).
  - NO mutation of the producer / validator / source_authority modules.
  - NO live-loop runtime wiring; NO FAM event; NO file write.

WSP Compliance:
  WSP 11 : Interface contract (typed ``DryRunResult``).
  WSP 50 : Pre-action validation (consumes validated bundle; refuses bad input).
  WSP 77 : Agent coordination (consumed by future WRE dispatch in Phase-2).
  WSP 84 : Code reuse (imports shared resolver + source_authority + bundle;
           defines no duplicate).
  WSP 97 : Truth boundaries (read-only, no overclaim, no execution).

NAVIGATION:
  -> Consumes: context_bundle_builder.ContextBundle (#775, read-only)
  -> Reuses resolver: module_path_resolution._resolve_validated_module_path (#778/#779)
  -> Reuses authority: source_authority.resolve_source_authority / ACTIVE_STAGES (#777)
  -> Adopts dry-run shape: build_plan_executor (BLOCKED/SIMULATED, #779)
  -> Tested by: modules/foundups/agent/tests/test_context_bundle_dry_run_consumer.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    FoundUpJob,
)
from modules.foundups.agent.src.context_bundle_builder import ContextBundle
from modules.foundups.agent.src.source_authority import (
    ACTIVE_STAGES,
    SourceAuthority,
    resolve_source_authority,
)

# Single-source-of-truth validated module-path resolver (#778/#779). Imported,
# NOT reimplemented: there is exactly ONE ``_resolve_validated_module_path``
# repo-wide and this consumer binds that object. An AST test asserts this
# module defines no second resolver.
from modules.foundups.agent.src.module_path_resolution import (
    DEFAULT_REPO_ROOT,
    ResolvedModulePath,
    _resolve_validated_module_path,
)

__all__ = [
    "DryRunResult",
    "DryRunConsumerRejected",
    "PlannedAction",
    "consume_context_bundle_dry_run",
    "CONSUMER_VERSION",
    "REQUIRED_SOURCE_AUTHORITY",
]

# Consumer version. Recorded in the result for provenance.
CONSUMER_VERSION = "0.1.0"

# The only source-authority stage this Phase-1 consumer will proceed for.
# Value-pinned to ``SourceAuthority.MONOREPO_POC`` so a drift in the enum
# breaks tests rather than silently widening the boundary.
REQUIRED_SOURCE_AUTHORITY = SourceAuthority.MONOREPO_POC.value  # "monorepo_poc"


class DryRunConsumerRejected(Exception):
    """Raised when the consumer refuses to produce a dry-run preview.

    The consumer NEVER returns a ``DryRunResult`` on rejection. Rejection
    reasons: non-monorepo_poc source_authority, module_path that does not
    match the shared validated resolver, a promoted readiness flag, or an
    external-agent-allowed bundle. The message is log-safe; no secrets.
    """


@dataclass(frozen=True)
class PlannedAction:
    """A build/test action the dry-run WOULD run -- declared, never executed.

    ``argv`` is the declared command tokens (or ``None`` when the bundle
    declares no command). It is recorded for the operator to inspect; this
    module NEVER passes it to a shell, subprocess, or any executor.
    """

    name: str            # e.g. "test" | "build" | "validate_manifest"
    argv: Optional[Tuple[str, ...]]  # declared tokens; never executed
    would_mutate: bool   # True if the declared action would mutate files
    executed: bool       # ALWAYS False -- nothing ran


@dataclass(frozen=True)
class DryRunResult:
    """Return-value-only dry-run preview of a ContextBundle consumption.

    No side effects produced this object: no FAM event, no file write, no
    subprocess, no network. ``dry_run`` is always True;
    ``real_execution_performed`` is always False. The bundle was the
    TRUSTED input; no field here is sourced from a raw payload value.

    Fields (pinned for the W10 contract gate):
      - ``planned_actions``: declared build/test actions that WOULD run
        (argv or None); never executed.
      - ``resolved_module_path``: validated canonical path from the bundle /
        shared resolver; never a payload value.
      - ``source_authority``: equals ``"monorepo_poc"``.
      - ``gates_to_recheck``: gate NAMES from the bundle; NOT pass-state.
      - ``readiness_flags``: echoed from the bundle, all False.
      - ``evidence_refs``: the bundle's file_refs (path + sha256 + size);
        NO file bodies.
      - ``rejected_input``: observable-ignore of any payload value ignored /
        rejected by the shared resolver.
      - ``dry_run`` / ``real_execution_performed``: explicit booleans
        asserting nothing ran.
    """

    consumer_version: str
    bundle_id: str
    foundup_id: str
    resolved_module_path: str
    source_authority: str
    planned_actions: Tuple[PlannedAction, ...]
    gates_to_recheck: Tuple[str, ...]
    readiness_flags: Dict[str, bool]
    evidence_refs: Tuple[Dict[str, Any], ...]
    rejected_input: Dict[str, Any]
    dry_run: bool = True
    real_execution_performed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consumer_version": self.consumer_version,
            "bundle_id": self.bundle_id,
            "foundup_id": self.foundup_id,
            "resolved_module_path": self.resolved_module_path,
            "source_authority": self.source_authority,
            "planned_actions": [
                {
                    "name": a.name,
                    "argv": list(a.argv) if a.argv is not None else None,
                    "would_mutate": a.would_mutate,
                    "executed": a.executed,
                }
                for a in self.planned_actions
            ],
            "gates_to_recheck": list(self.gates_to_recheck),
            "readiness_flags": dict(self.readiness_flags),
            "evidence_refs": [dict(r) for r in self.evidence_refs],
            "rejected_input": dict(self.rejected_input),
            "dry_run": self.dry_run,
            "real_execution_performed": self.real_execution_performed,
        }


# ---------------------------------------------------------------------------
# Internal helpers (pure; no IO; no execution)
# ---------------------------------------------------------------------------


def _planned_actions_from_bundle(bundle: ContextBundle) -> Tuple[PlannedAction, ...]:
    """Derive the declared (never executed) actions from the bundle.

    Reuses the EXISTING dry-run primitive's shape: a dry-run describes the
    test/build it WOULD run. The bundle's ``execution_routing_summary``
    declares an executor (e.g. "hermes") and ``dry_run_required`` declares
    a mandatory dry-run. We surface a single declared "build" action plus a
    declared "test" action when test refs are present. ``argv`` is ``None``
    here because the bundle carries refs + sha256 only (never command
    bodies); the operator re-checks the manifest's test.command via the
    gates. Every action's ``executed`` is False.
    """
    actions: List[PlannedAction] = []

    # Declared build action: would route to the bundle's declared executor.
    executor = bundle.execution_routing_summary.get("executor")
    build_name = "build:" + str(executor) if executor else "build"
    actions.append(
        PlannedAction(
            name=build_name,
            argv=None,            # bundle carries no command bodies
            would_mutate=True,    # a real build would mutate; never run here
            executed=False,
        )
    )

    # Declared test action only when the bundle referenced test files.
    has_test_refs = any(r.role == "test" for r in bundle.included_file_refs)
    if has_test_refs:
        actions.append(
            PlannedAction(
                name="test",
                argv=None,
                would_mutate=False,
                executed=False,
            )
        )

    return tuple(actions)


def _evidence_refs_from_bundle(bundle: ContextBundle) -> Tuple[Dict[str, Any], ...]:
    """Map the bundle's FileRefs to evidence entries: path + sha256 + size.

    NO file bodies. NO repo-wide read. This is a pure projection of the
    bundle's already-bounded ``included_file_refs`` (refs + sha256 only).
    """
    return tuple(
        {
            "path": r.path,
            "sha256": r.sha256,
            "size_bytes": r.size_bytes,
            "role": r.role,
        }
        for r in bundle.included_file_refs
    )


def _resolved_rejected_input(resolved: Optional[ResolvedModulePath]) -> Dict[str, Any]:
    """Observable-ignore projection of the shared resolver outcome.

    Mirrors the #777 / #778 observable-ignore convention: the payload-
    declared candidate the resolver IGNORED (even on success) is surfaced
    so the operator can see exactly what was rejected. The value is NEVER
    used as authority. When no resolver was run (no job provided), returns
    an empty observable dict.
    """
    if resolved is None:
        return {"payload_module_path_ignored": None, "resolver_run": False}
    return {
        "payload_module_path_ignored": resolved.ignored,
        "resolver_run": True,
        "resolver_failed": resolved.failed,
        "resolver_fail_token": resolved.fail_token,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def consume_context_bundle_dry_run(
    bundle: ContextBundle,
    *,
    job: Optional[FoundUpJob] = None,
    repo_root: Optional[Path] = None,
) -> DryRunResult:
    """Consume a trusted ContextBundle and RETURN a dry-run preview.

    Standalone (ruling A) and return-value-only (ruling B): no side effects,
    no FAM event, no file write, no subprocess, no network, no real
    execution. The bundle is the TRUSTED input.

    Args:
        bundle: a read-only ``ContextBundle`` produced by
            ``context_bundle_builder.build_context_bundle`` (#775). It is
            treated as already-validated trusted input; this consumer does
            NOT re-derive trust from a raw payload.
        job: OPTIONAL ``FoundUpJob`` whose payload may carry a (forged)
            ``module_path`` / ``source_module``. When provided, the SHARED
            validated resolver (#778/#779) is run as defense-in-depth and
            its effective canonical path MUST match the bundle's validated
            ``module_path``; any payload-declared candidate is surfaced as
            observable-ignore in ``rejected_input`` and is NEVER used. When
            omitted, no payload is trusted at all.
        repo_root: repository root for the shared resolver. Defaults to the
            resolver's ``DEFAULT_REPO_ROOT``.

    Returns:
        ``DryRunResult`` (frozen) -- a return-value-only preview.

    Raises:
        DryRunConsumerRejected: on non-monorepo_poc source_authority, a
            module_path that does not match the shared validated resolver, a
            promoted readiness flag, an external-agent-allowed bundle, or a
            cross-FoundUp payload substitution. The consumer NEVER returns a
            ``DryRunResult`` on rejection.
    """
    # --- 0. Argument guard ---
    if not isinstance(bundle, ContextBundle):
        raise DryRunConsumerRejected(
            "bundle must be a ContextBundle; got " + type(bundle).__name__
        )

    # --- 1. Source-authority gate (NO promotion; monorepo_poc only) ---
    #
    # Read the stage FROM THE BUNDLE (trusted input). Run it through the
    # #777 resolver, which ALWAYS returns MONOREPO_POC and surfaces the
    # declared value as ignored -- so even if a bundle somehow carried a
    # higher stage string, the consumer cannot promote it. We then assert
    # the BUNDLE's declared stage is exactly monorepo_poc (a tampered bundle
    # claiming dao_managed is refused outright). ACTIVE_STAGES is the
    # single-source set of reachable stages.
    effective_authority, declared_ignored = resolve_source_authority(
        bundle.source_authority
    )
    if effective_authority not in ACTIVE_STAGES:
        # Unreachable in Phase-1 (resolver always returns MONOREPO_POC) but
        # pinned defensively: the consumer cannot proceed off an active stage.
        raise DryRunConsumerRejected(
            "effective source_authority "
            + repr(effective_authority.value)
            + " is not an active Phase-1 stage"
        )
    if bundle.source_authority != REQUIRED_SOURCE_AUTHORITY:
        raise DryRunConsumerRejected(
            "bundle.source_authority " + repr(bundle.source_authority)
            + " is not " + repr(REQUIRED_SOURCE_AUTHORITY)
            + "; the consumer cannot promote a lifecycle stage and refuses "
            "non-monorepo_poc input (declared-ignored="
            + repr(declared_ignored) + ")"
        )

    # --- 2. Readiness must not be promoted (echo only; all False) ---
    #
    # The #775 builder already rejects truthy readiness, so a real bundle's
    # flags are all False. Defense-in-depth: refuse any True flag rather than
    # echo a promoted readiness into the preview.
    readiness_flags = dict(bundle.readiness_flags)
    promoted = [k for k, v in readiness_flags.items() if v is True]
    if promoted:
        raise DryRunConsumerRejected(
            "bundle carries promoted readiness flags " + repr(promoted)
            + "; the consumer refuses readiness promotion"
        )

    # --- 3. External agent must stay untrusted ---
    if bundle.execution_routing_summary.get("external_agent_allowed") is True:
        raise DryRunConsumerRejected(
            "bundle.execution_routing_summary.external_agent_allowed=True; "
            "external agents are not trusted in Phase-1"
        )
    if bundle.execution_routing_summary.get("can_self_authorize") is True:
        raise DryRunConsumerRejected(
            "bundle.execution_routing_summary.can_self_authorize=True; refused"
        )

    # --- 4. module_path via the SHARED validated resolver ONLY ---
    #
    # The bundle's ``module_path`` is the validated canonical path (#775
    # sourced it from the validator, never from a payload). When a job is
    # supplied (it may carry a forged payload.module_path / source_module),
    # we run the SINGLE shared resolver (#778/#779) as defense-in-depth and
    # require its effective path to equal the bundle's module_path. The
    # payload-declared candidate is surfaced as observable-ignore and is
    # NEVER used as the resolved path. We define NO second resolver.
    resolved: Optional[ResolvedModulePath] = None
    if job is not None:
        effective_repo_root = repo_root or DEFAULT_REPO_ROOT
        resolved = _resolve_validated_module_path(job, effective_repo_root)
        if resolved.failed:
            raise DryRunConsumerRejected(
                "shared resolver rejected the job payload: "
                + resolved.fail_human
                + " (payload-ignored=" + repr(resolved.ignored) + ")"
            )
        if resolved.effective != bundle.module_path:
            raise DryRunConsumerRejected(
                "shared resolver effective module_path "
                + repr(resolved.effective)
                + " does not match bundle.module_path "
                + repr(bundle.module_path)
                + " (payload-ignored=" + repr(resolved.ignored)
                + "); the payload value is NEVER trusted"
            )

    # The resolved module_path is ALWAYS the bundle's validated value -- never
    # a payload value, even when a job was supplied.
    resolved_module_path = bundle.module_path

    # --- 5. Gate names to RE-CHECK (never pass-state) ---
    #
    # ``required_gates_to_recheck`` are gate NAMES. We carry them verbatim as
    # names. No gate-pass boolean is ever computed or serialized here.
    gates_to_recheck = tuple(bundle.required_gates_to_recheck)

    # --- 6. Declared (never executed) actions + evidence refs ---
    planned_actions = _planned_actions_from_bundle(bundle)
    evidence_refs = _evidence_refs_from_bundle(bundle)
    rejected_input = _resolved_rejected_input(resolved)

    # --- 7. Return-value-only preview. dry_run True / real_execution False. ---
    return DryRunResult(
        consumer_version=CONSUMER_VERSION,
        bundle_id=bundle.bundle_id,
        foundup_id=bundle.foundup_id,
        resolved_module_path=resolved_module_path,
        source_authority=bundle.source_authority,
        planned_actions=planned_actions,
        gates_to_recheck=gates_to_recheck,
        readiness_flags=readiness_flags,
        evidence_refs=evidence_refs,
        rejected_input=rejected_input,
        dry_run=True,
        real_execution_performed=False,
    )
