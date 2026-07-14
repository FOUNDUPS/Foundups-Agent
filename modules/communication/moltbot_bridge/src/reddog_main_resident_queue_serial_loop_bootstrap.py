"""Main-startup adapter for the resident RedDog serial queue loop.

Slice: REDDOG_MAIN_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_PHASE1

This adapter lets ``main.py`` run the bounded serial queue loop behind an
explicit environment flag. It reads existing runtime JSON artifacts from
outside the repository checkout, builds the injected handler registry with the
dependencies this bootstrap owns today, and advances through the serial loop up
to a bounded max step count.

This slice does not introduce production signer, verifier, runner, PR,
PatternMemory, OpenClaw, Hermes, or HoloIndex dependencies. Missing later-stage
dependencies fail closed through the registry and dispatcher.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    AtomicJsonResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_runtime_dependency_bundle import (
    REDDOG_RUNTIME_DEPENDENCY_BUNDLE_NOT_REQUESTED,
    load_reddog_main_resident_queue_runtime_dependency_bundle,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import (
    DEFAULT_SIGNER_SOCKET_MAX_RESPONSE_BYTES,
    DEFAULT_SIGNER_SOCKET_TIMEOUT_S,
    SignerSocketConnector,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_serial_loop import (
    ResidentQueueSerialLoopResult,
    run_reddog_resident_queue_serial_loop,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_stage_handler_registry import (
    build_reddog_resident_queue_stage_handler_registry,
)


REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED = "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED"
REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY = "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY"


@dataclass(frozen=True)
class RedDogMainResidentQueueSerialLoopBootstrapResult:
    """Result emitted by the startup serial-loop adapter."""

    accepted: bool
    status: str
    queue_item_id: Optional[str]
    selected_slice: Optional[str]
    steps_run: int
    dispatched_stages: tuple[str, ...]
    next_action: Optional[str]
    chain_results_path: Optional[str]
    store_revision: Optional[str]
    rejection_reasons: tuple[str, ...]
    runtime_dependency_bundle_status: str = REDDOG_RUNTIME_DEPENDENCY_BUNDLE_NOT_REQUESTED
    runtime_dependency_bundle_requested: bool = False
    no_signing_performed: bool = True
    no_signature_verification_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_client_created: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_main_resident_queue_serial_loop_bootstrap(
    *,
    repo_root: Path | str,
    work_state_path: Path | str | None,
    chain_results_path: Path | str | None,
    authority_profile_path: Path | str | None,
    authority_state_path: Path | str | None = None,
    permission_snapshots_path: Path | str | None = None,
    principal_authority_records_path: Path | str | None = None,
    signer_socket_path: Path | str | None = None,
    signer_socket_timeout_s: float = DEFAULT_SIGNER_SOCKET_TIMEOUT_S,
    signer_socket_max_response_bytes: int = DEFAULT_SIGNER_SOCKET_MAX_RESPONSE_BYTES,
    signer_socket_connector: Optional[SignerSocketConnector] = None,
    requested_queue_item_id: str | None = None,
    now_iso: str | None = None,
    now_epoch: int | None = None,
    max_steps: int = 1,
) -> RedDogMainResidentQueueSerialLoopBootstrapResult:
    """Load runtime inputs and run the bounded resident queue serial loop."""

    root = Path(repo_root).resolve()
    snapshot, snapshot_reasons = _read_json_outside_repo(
        root,
        work_state_path,
        missing_reason="missing_authoritative_work_state_path",
        inside_reason="work_state_path_inside_repo",
        unreadable_reason="malformed_authoritative_work_state",
    )
    if snapshot_reasons:
        return _not_ready(snapshot_reasons, chain_results_path=None)
    assert snapshot is not None

    profile, profile_reasons = _read_json_outside_repo(
        root,
        authority_profile_path,
        missing_reason="missing_authority_profile_path",
        inside_reason="authority_profile_path_inside_repo",
        unreadable_reason="malformed_authority_profile",
    )
    if profile_reasons:
        return _not_ready(profile_reasons, chain_results_path=None)
    assert profile is not None

    chain_path, chain_reasons = _resolve_output_outside_repo(
        root,
        chain_results_path,
        missing_reason="missing_chain_results_path",
        inside_reason="chain_results_path_inside_repo",
    )
    if chain_reasons:
        return _not_ready(chain_reasons, chain_results_path=None)
    assert chain_path is not None

    dependency_bundle = load_reddog_main_resident_queue_runtime_dependency_bundle(
        repo_root=root,
        authority_state_path=authority_state_path,
        permission_snapshots_path=permission_snapshots_path,
        principal_authority_records_path=principal_authority_records_path,
        signer_socket_path=signer_socket_path,
        signer_socket_timeout_s=signer_socket_timeout_s,
        signer_socket_max_response_bytes=signer_socket_max_response_bytes,
        signer_socket_connector=signer_socket_connector,
        now_epoch=now_epoch,
    )
    if dependency_bundle.accepted is not True:
        return _not_ready(
            dependency_bundle.rejection_reasons,
            chain_results_path=None,
            runtime_dependency_bundle_status=dependency_bundle.status,
            runtime_dependency_bundle_requested=dependency_bundle.requested,
        )

    store = AtomicJsonResidentQueueChainResultsStore(chain_path)
    registry = build_reddog_resident_queue_stage_handler_registry(
        work_state_snapshot=snapshot,
        chain_results_store=store,
        authority_profile=profile,
        now_iso=now_iso or "",
        authority_store=dependency_bundle.authority_store,
        signer=dependency_bundle.signer,
        principal_resolver=dependency_bundle.principal_resolver,
        snapshot_resolver=dependency_bundle.snapshot_resolver,
        now_epoch=dependency_bundle.now_epoch,
    )
    loop = run_reddog_resident_queue_serial_loop(
        explicit_resident_queue_serial_loop_requested=True,
        work_state_snapshot=snapshot,
        store=store,
        handlers=registry.handlers,
        now_iso=now_iso or "",
        requested_queue_item_id=requested_queue_item_id,
        max_steps=max_steps,
    )
    if loop.accepted is not True:
        return _from_loop(
            loop,
            accepted=False,
            status=REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY,
            chain_results_path=chain_path,
            runtime_dependency_bundle_status=dependency_bundle.status,
            runtime_dependency_bundle_requested=dependency_bundle.requested,
        )

    return _from_loop(
        loop,
        accepted=True,
        status=REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED,
        chain_results_path=chain_path,
        runtime_dependency_bundle_status=dependency_bundle.status,
        runtime_dependency_bundle_requested=dependency_bundle.requested,
    )


def _read_json_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
    unreadable_reason: str,
) -> tuple[Optional[Mapping[str, Any]], tuple[str, ...]]:
    if not value:
        return None, (missing_reason,)
    path = Path(value)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    else:
        path = path.resolve()
    if _is_inside(path, repo_root):
        return None, (inside_reason,)
    if not path.exists() or not path.is_file():
        return None, (missing_reason,)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, (unreadable_reason,)
    if not isinstance(payload, Mapping):
        return None, (unreadable_reason,)
    return payload, ()


def _resolve_output_outside_repo(
    repo_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
) -> tuple[Optional[Path], tuple[str, ...]]:
    if not value:
        return None, (missing_reason,)
    path = Path(value)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    else:
        path = path.resolve()
    if _is_inside(path, repo_root):
        return None, (inside_reason,)
    return path, ()


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _not_ready(
    reasons: tuple[str, ...],
    *,
    chain_results_path: Path | None,
    runtime_dependency_bundle_status: str = REDDOG_RUNTIME_DEPENDENCY_BUNDLE_NOT_REQUESTED,
    runtime_dependency_bundle_requested: bool = False,
) -> RedDogMainResidentQueueSerialLoopBootstrapResult:
    return RedDogMainResidentQueueSerialLoopBootstrapResult(
        accepted=False,
        status=REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY,
        queue_item_id=None,
        selected_slice=None,
        steps_run=0,
        dispatched_stages=(),
        next_action=None,
        chain_results_path=str(chain_results_path) if chain_results_path else None,
        store_revision=None,
        runtime_dependency_bundle_status=runtime_dependency_bundle_status,
        runtime_dependency_bundle_requested=runtime_dependency_bundle_requested,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason).strip())),
    )


def _from_loop(
    loop: ResidentQueueSerialLoopResult,
    *,
    accepted: bool,
    status: str,
    chain_results_path: Path,
    runtime_dependency_bundle_status: str = REDDOG_RUNTIME_DEPENDENCY_BUNDLE_NOT_REQUESTED,
    runtime_dependency_bundle_requested: bool = False,
) -> RedDogMainResidentQueueSerialLoopBootstrapResult:
    final_plan = loop.final_plan
    last_dispatch = loop.dispatch_results[-1] if loop.dispatch_results else None
    record = last_dispatch.record_result if last_dispatch else None
    receipt = record.receipt if record else None
    return RedDogMainResidentQueueSerialLoopBootstrapResult(
        accepted=accepted,
        status=status,
        queue_item_id=final_plan.selected_queue_item_id if final_plan else None,
        selected_slice=final_plan.selected_slice if final_plan else None,
        steps_run=loop.steps_run,
        dispatched_stages=loop.dispatched_stages,
        next_action=loop.next_action,
        chain_results_path=str(chain_results_path),
        store_revision=receipt.store_revision if receipt else None,
        runtime_dependency_bundle_status=runtime_dependency_bundle_status,
        runtime_dependency_bundle_requested=runtime_dependency_bundle_requested,
        rejection_reasons=tuple(loop.rejection_reasons),
    )


__all__ = [
    "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED",
    "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY",
    "RedDogMainResidentQueueSerialLoopBootstrapResult",
    "run_reddog_main_resident_queue_serial_loop_bootstrap",
]
