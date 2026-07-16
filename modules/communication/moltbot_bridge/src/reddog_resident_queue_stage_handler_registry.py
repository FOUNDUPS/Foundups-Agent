"""Resident RedDog queue stage-handler registry.

Slice: REDDOG_RESIDENT_QUEUE_STAGE_HANDLER_REGISTRY_PHASE1

This module centralizes construction of the already-built resident queue stage
handlers. It performs dependency presence checks and returns only handlers whose
dependencies were explicitly injected by the caller. It does not create default
signers, runners, stores, shells, worktrees, PR clients, PatternMemory clients,
OpenClaw clients, Hermes clients, or HoloIndex indexers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping, MutableSet, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_resident_queue_authority_request_handler import (
    AUTHORITY_REQUEST_STAGE_KEY,
    build_reddog_resident_queue_authority_request_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_authority_runtime_handler import (
    AUTHORITY_RUNTIME_STAGE_KEY,
    build_reddog_resident_queue_authority_runtime_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_authority_verification_handler import (
    AUTHORITY_VERIFICATION_STAGE_KEY,
    build_reddog_resident_queue_authority_verification_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_bounded_worker_pilot_handler import (
    BOUNDED_WORKER_PILOT_STAGE_KEY,
    build_reddog_resident_queue_bounded_worker_pilot_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_execution_valve_handler import (
    EXECUTION_VALVE_STAGE_KEY,
    build_reddog_resident_queue_execution_valve_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_executor_plan_handler import (
    EXECUTOR_PLAN_STAGE_KEY,
    build_reddog_resident_queue_executor_plan_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_held_out_regression_gate_handler import (
    HELD_OUT_REGRESSION_GATE_STAGE_KEY,
    build_reddog_resident_queue_held_out_regression_gate_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageHandler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_pattern_memory_admission_handler import (
    PATTERN_MEMORY_ADMISSION_STAGE_KEY,
    build_reddog_resident_queue_pattern_memory_admission_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_slice_verifier_handler import (
    SLICE_VERIFIER_STAGE_KEY,
    build_reddog_resident_queue_slice_verifier_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_verified_draft_pr_publish_handler import (
    VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY,
    build_reddog_resident_queue_verified_draft_pr_publish_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_verified_outcome_ratchet_handler import (
    VERIFIED_OUTCOME_RATCHET_STAGE_KEY,
    build_reddog_resident_queue_verified_outcome_ratchet_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_work_order_invocation_handler import (
    WORK_ORDER_INVOCATION_STAGE_KEY,
    build_reddog_resident_queue_work_order_invocation_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_worker_dispatch_dryrun_handler import (
    WORKER_DISPATCH_DRYRUN_STAGE_KEY,
    build_reddog_resident_queue_worker_dispatch_dryrun_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_worktree_create_handler import (
    WORKTREE_CREATE_STAGE_KEY,
    build_reddog_resident_queue_worktree_create_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_WORKTREE_CREATE,
    ExecutionValveEnvironment,
)


RESIDENT_QUEUE_STAGE_HANDLER_REGISTRY_READY = "RESIDENT_QUEUE_STAGE_HANDLER_REGISTRY_READY"


@dataclass(frozen=True)
class ResidentQueueStageHandlerRegistry:
    """Registry result returned to startup/runtime callers."""

    handlers: Mapping[str, ResidentQueueStageHandler]
    missing_stage_reasons: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    no_default_signer_created: bool = True
    no_default_runner_created: bool = True
    no_shell_command_executed: bool = True
    no_worktree_created: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_client_created: bool = True
    no_reward_settlement_performed: bool = True

    @property
    def status(self) -> str:
        return RESIDENT_QUEUE_STAGE_HANDLER_REGISTRY_READY

    @property
    def registered_stage_keys(self) -> tuple[str, ...]:
        return tuple(self.handlers.keys())

    @property
    def registered_stage_count(self) -> int:
        return len(self.handlers)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "registered_stage_keys": self.registered_stage_keys,
            "registered_stage_count": self.registered_stage_count,
            "missing_stage_reasons": dict(self.missing_stage_reasons),
            "no_default_signer_created": self.no_default_signer_created,
            "no_default_runner_created": self.no_default_runner_created,
            "no_shell_command_executed": self.no_shell_command_executed,
            "no_worktree_created": self.no_worktree_created,
            "no_openclaw_enqueue_performed": self.no_openclaw_enqueue_performed,
            "no_hermes_dispatch_performed": self.no_hermes_dispatch_performed,
            "no_repo_mutation_performed": self.no_repo_mutation_performed,
            "no_holoindex_reindex_performed": self.no_holoindex_reindex_performed,
            "no_pr_created": self.no_pr_created,
            "no_pattern_memory_client_created": self.no_pattern_memory_client_created,
            "no_reward_settlement_performed": self.no_reward_settlement_performed,
        }


def _missing(*pairs: tuple[str, Any]) -> tuple[str, ...]:
    reasons: list[str] = []
    for name, value in pairs:
        if value is None:
            reasons.append(f"missing_dependency:{name}")
        elif isinstance(value, Mapping) and not value:
            reasons.append(f"missing_dependency:{name}")
    return tuple(reasons)


def _add_if_ready(
    handlers: Dict[str, ResidentQueueStageHandler],
    missing: Dict[str, tuple[str, ...]],
    stage_key: str,
    reasons: tuple[str, ...],
    builder: Any,
) -> None:
    if reasons:
        missing[stage_key] = reasons
        return
    handlers[stage_key] = builder()


def build_reddog_resident_queue_stage_handler_registry(
    *,
    work_state_snapshot: Mapping[str, Any],
    chain_results_store: ResidentQueueChainResultsStore,
    now_iso: str,
    authority_profile: Optional[Mapping[str, Any]] = None,
    authority_store: Any = None,
    signer: Any = None,
    principal_resolver: Any = None,
    snapshot_resolver: Any = None,
    now_epoch: Optional[int] = None,
    signature_verifier: Any = None,
    principal_key_resolver: Any = None,
    nonce_store: Any = None,
    revocation_oracle: Any = None,
    required_valve_state: str = VALVE_OPEN_WORKTREE_CREATE,
    forbidden_operations: Sequence[str] = (),
    revoked_key_epochs: Sequence[str] = (),
    leeway_s: int = 60,
    work_order_resolver: Any = None,
    permission_snapshot: Optional[Mapping[str, Any]] = None,
    now_datetime: Optional[datetime] = None,
    seen_nonces: Optional[MutableSet[str]] = None,
    receipt_store: Any = None,
    permission_ttl_seconds: int = 300,
    permission_expires_at: Optional[str] = None,
    locks: Optional[MutableSet[str]] = None,
    repo_root: Optional[Path | str] = None,
    valve_environment: Optional[ExecutionValveEnvironment | Mapping[str, Any]] = None,
    intake_target: str = "foundup_job",
    expected_valve_state: str = VALVE_OPEN_WORKTREE_CREATE,
    worktree_runner: Any = None,
    generic_writer_dryrun_result: Optional[Mapping[str, Any]] = None,
    governed_shell_dryrun_result: Optional[Mapping[str, Any]] = None,
    artifact_contents: Optional[Mapping[str, Any]] = None,
    operation_cwd: Optional[Path] = None,
    holoindex_evidence: Optional[Mapping[str, Any]] = None,
    verifier_request: Optional[Mapping[str, Any]] = None,
    evidence_producer_request: Optional[Mapping[str, Any]] = None,
    evidence_command_runner: Any = None,
    publish_request: Optional[Mapping[str, Any]] = None,
    draft_pr_runner: Any = None,
    ratchet_request: Optional[Mapping[str, Any]] = None,
    outcome_ratchet_store: Any = None,
    explicit_pattern_memory_write_requested: bool = False,
    ratchet_pattern_memory_sink: Any = None,
    held_out_gate_request: Optional[Mapping[str, Any]] = None,
    admission_request: Optional[Mapping[str, Any]] = None,
    pattern_memory_admission_sink: Any = None,
) -> ResidentQueueStageHandlerRegistry:
    """Build a handler map from explicitly injected dependencies."""

    handlers: Dict[str, ResidentQueueStageHandler] = {}
    missing: Dict[str, tuple[str, ...]] = {}
    root = Path(repo_root) if repo_root is not None else None

    _add_if_ready(
        handlers,
        missing,
        AUTHORITY_REQUEST_STAGE_KEY,
        _missing(("authority_profile", authority_profile)),
        lambda: build_reddog_resident_queue_authority_request_stage_handler(
            work_state_snapshot=work_state_snapshot,
            authority_profile=authority_profile or {},
            now_iso=now_iso,
        ),
    )
    _add_if_ready(
        handlers,
        missing,
        AUTHORITY_RUNTIME_STAGE_KEY,
        _missing(
            ("authority_store", authority_store),
            ("signer", signer),
            ("principal_resolver", principal_resolver),
            ("snapshot_resolver", snapshot_resolver),
            ("now_epoch", now_epoch),
        ),
        lambda: build_reddog_resident_queue_authority_runtime_stage_handler(
            chain_results_store=chain_results_store,
            authority_store=authority_store,
            signer=signer,
            principal_resolver=principal_resolver,
            snapshot_resolver=snapshot_resolver,
            now=int(now_epoch or 0),
            leeway_s=leeway_s,
        ),
    )
    _add_if_ready(
        handlers,
        missing,
        AUTHORITY_VERIFICATION_STAGE_KEY,
        _missing(
            ("signature_verifier", signature_verifier),
            ("principal_key_resolver", principal_key_resolver),
            ("nonce_store", nonce_store),
            ("snapshot_resolver", snapshot_resolver),
            ("revocation_oracle", revocation_oracle),
            ("now_epoch", now_epoch),
        ),
        lambda: build_reddog_resident_queue_authority_verification_stage_handler(
            chain_results_store=chain_results_store,
            signature_verifier=signature_verifier,
            principal_key_resolver=principal_key_resolver,
            nonce_store=nonce_store,
            snapshot_resolver=snapshot_resolver,
            revocation_oracle=revocation_oracle,
            now=int(now_epoch or 0),
            required_valve_state=required_valve_state,
            forbidden_operations=forbidden_operations,
            revoked_key_epochs=revoked_key_epochs,
            leeway_s=leeway_s,
        ),
    )
    _add_if_ready(
        handlers,
        missing,
        WORKER_DISPATCH_DRYRUN_STAGE_KEY,
        (),
        lambda: build_reddog_resident_queue_worker_dispatch_dryrun_stage_handler(
            work_state_snapshot=work_state_snapshot,
            chain_results_store=chain_results_store,
        ),
    )
    _add_if_ready(
        handlers,
        missing,
        WORK_ORDER_INVOCATION_STAGE_KEY,
        _missing(("work_order_resolver", work_order_resolver)),
        lambda: build_reddog_resident_queue_work_order_invocation_stage_handler(
            chain_results_store=chain_results_store,
            work_order_resolver=work_order_resolver,
            permission_snapshot=permission_snapshot,
            now=now_datetime,
            seen_nonces=seen_nonces,
            receipt_store=receipt_store,
            permission_ttl_seconds=permission_ttl_seconds,
            permission_expires_at=permission_expires_at,
        ),
    )
    _add_if_ready(
        handlers,
        missing,
        EXECUTOR_PLAN_STAGE_KEY,
        _missing(("work_order_resolver", work_order_resolver), ("repo_root", root)),
        lambda: build_reddog_resident_queue_executor_plan_stage_handler(
            chain_results_store=chain_results_store,
            work_order_resolver=work_order_resolver,
            now=now_datetime,
            locks=locks,
            repo_root=root or ".",
        ),
    )
    _add_if_ready(
        handlers,
        missing,
        EXECUTION_VALVE_STAGE_KEY,
        _missing(("work_order_resolver", work_order_resolver), ("valve_environment", valve_environment)),
        lambda: build_reddog_resident_queue_execution_valve_stage_handler(
            chain_results_store=chain_results_store,
            work_order_resolver=work_order_resolver,
            valve_environment=valve_environment or {},
            now=now_datetime,
            intake_target=intake_target,
            expected_valve_state=expected_valve_state,
        ),
    )
    _add_if_ready(
        handlers,
        missing,
        WORKTREE_CREATE_STAGE_KEY,
        _missing(("work_order_resolver", work_order_resolver), ("worktree_runner", worktree_runner), ("repo_root", root)),
        lambda: build_reddog_resident_queue_worktree_create_stage_handler(
            chain_results_store=chain_results_store,
            work_order_resolver=work_order_resolver,
            runner=worktree_runner,
            repo_root=root or Path("."),
            now=now_datetime,
            locks=locks,
        ),
    )
    _add_if_ready(
        handlers,
        missing,
        BOUNDED_WORKER_PILOT_STAGE_KEY,
        _missing(
            ("work_order_resolver", work_order_resolver),
            ("generic_writer_dryrun_result", generic_writer_dryrun_result),
            ("governed_shell_dryrun_result", governed_shell_dryrun_result),
            ("artifact_contents", artifact_contents),
            ("repo_root", root),
        ),
        lambda: build_reddog_resident_queue_bounded_worker_pilot_stage_handler(
            chain_results_store=chain_results_store,
            work_order_resolver=work_order_resolver,
            generic_writer_dryrun_result=generic_writer_dryrun_result or {},
            governed_shell_dryrun_result=governed_shell_dryrun_result or {},
            artifact_contents=artifact_contents or {},
            repo_root=root or Path("."),
            operation_cwd=operation_cwd,
            holoindex_evidence=holoindex_evidence,
        ),
    )
    _add_if_ready(
        handlers,
        missing,
        SLICE_VERIFIER_STAGE_KEY,
        _slice_verifier_missing(
            verifier_request=verifier_request,
            evidence_producer_request=evidence_producer_request,
            evidence_command_runner=evidence_command_runner,
        ),
        lambda: build_reddog_resident_queue_slice_verifier_stage_handler(
            chain_results_store=chain_results_store,
            verifier_request=verifier_request,
            evidence_producer_request=evidence_producer_request,
            evidence_command_runner=evidence_command_runner,
        ),
    )
    _add_if_ready(
        handlers,
        missing,
        VERIFIED_DRAFT_PR_PUBLISH_STAGE_KEY,
        _missing(("publish_request", publish_request), ("draft_pr_runner", draft_pr_runner)),
        lambda: build_reddog_resident_queue_verified_draft_pr_publish_stage_handler(
            chain_results_store=chain_results_store,
            publish_request=publish_request or {},
            runner=draft_pr_runner,
        ),
    )
    _add_if_ready(
        handlers,
        missing,
        VERIFIED_OUTCOME_RATCHET_STAGE_KEY,
        _missing(("ratchet_request", ratchet_request), ("outcome_ratchet_store", outcome_ratchet_store)),
        lambda: build_reddog_resident_queue_verified_outcome_ratchet_stage_handler(
            chain_results_store=chain_results_store,
            ratchet_request=ratchet_request or {},
            store=outcome_ratchet_store,
            explicit_pattern_memory_write_requested=explicit_pattern_memory_write_requested,
            pattern_memory_sink=ratchet_pattern_memory_sink,
        ),
    )
    _add_if_ready(
        handlers,
        missing,
        HELD_OUT_REGRESSION_GATE_STAGE_KEY,
        _missing(("held_out_gate_request", held_out_gate_request)),
        lambda: build_reddog_resident_queue_held_out_regression_gate_stage_handler(
            chain_results_store=chain_results_store,
            held_out_gate_request=held_out_gate_request or {},
        ),
    )
    _add_if_ready(
        handlers,
        missing,
        PATTERN_MEMORY_ADMISSION_STAGE_KEY,
        _missing(("admission_request", admission_request), ("pattern_memory_admission_sink", pattern_memory_admission_sink)),
        lambda: build_reddog_resident_queue_pattern_memory_admission_stage_handler(
            chain_results_store=chain_results_store,
            admission_request=admission_request or {},
            sink=pattern_memory_admission_sink,
        ),
    )

    return ResidentQueueStageHandlerRegistry(
        handlers=handlers,
        missing_stage_reasons=missing,
    )


def _slice_verifier_missing(
    *,
    verifier_request: Optional[Mapping[str, Any]],
    evidence_producer_request: Optional[Mapping[str, Any]],
    evidence_command_runner: Any,
) -> tuple[str, ...]:
    if verifier_request:
        return ()
    if evidence_producer_request and evidence_command_runner is not None:
        return ()
    reasons: list[str] = []
    if not verifier_request:
        reasons.append("missing_dependency:verifier_request")
    if not evidence_producer_request:
        reasons.append("missing_dependency:evidence_producer_request")
    if evidence_command_runner is None:
        reasons.append("missing_dependency:evidence_command_runner")
    return tuple(reasons)


__all__ = [
    "RESIDENT_QUEUE_STAGE_HANDLER_REGISTRY_READY",
    "ResidentQueueStageHandlerRegistry",
    "build_reddog_resident_queue_stage_handler_registry",
]
