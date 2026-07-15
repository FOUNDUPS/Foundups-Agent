"""Main-startup adapter for the resident RedDog serial queue loop.

Slice: REDDOG_MAIN_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_PHASE1

This adapter lets ``main.py`` run the bounded serial queue loop behind an
explicit environment flag. It reads existing runtime JSON artifacts from
outside the repository checkout, builds the injected handler registry with the
dependencies this bootstrap owns today, and advances through the serial loop up
to a bounded max step count.

This slice does not introduce a production signer, runner, PR, PatternMemory,
OpenClaw, Hermes, or HoloIndex dependency. Work-order and valve artifacts are
loaded only from outside-repo JSON snapshots. Public signature verification can
be enabled only through the explicit runtime dependency bundle. Missing
later-stage dependencies fail closed through the registry and dispatcher.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
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
    no_bounded_task_execution_performed: bool = True
    no_bounded_file_edit_performed: bool = True
    no_slice_verification_performed: bool = True
    no_verified_draft_pr_publish_performed: bool = True
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


class JsonResidentQueueWorkOrderResolver:
    """Resolve queue-bound work orders from an outside-repo JSON snapshot."""

    def __init__(self, work_orders: Mapping[str, Mapping[str, Any]]) -> None:
        self._work_orders = {str(key): dict(value) for key, value in work_orders.items()}

    def resolve(
        self,
        *,
        work_order_id: str,
        queue_item_id: Optional[str],
        selected_slice: Optional[str],
    ) -> Mapping[str, Any]:
        _ = (queue_item_id, selected_slice)
        return self._work_orders.get(str(work_order_id), {})


def run_reddog_main_resident_queue_serial_loop_bootstrap(
    *,
    repo_root: Path | str,
    work_state_path: Path | str | None,
    chain_results_path: Path | str | None,
    authority_profile_path: Path | str | None,
    work_orders_path: Path | str | None = None,
    valve_environment_path: Path | str | None = None,
    generic_writer_dryrun_result_path: Path | str | None = None,
    governed_shell_dryrun_result_path: Path | str | None = None,
    artifact_contents_path: Path | str | None = None,
    holoindex_evidence_path: Path | str | None = None,
    verifier_request_path: Path | str | None = None,
    publish_request_path: Path | str | None = None,
    authority_state_path: Path | str | None = None,
    permission_snapshots_path: Path | str | None = None,
    principal_authority_records_path: Path | str | None = None,
    signer_socket_path: Path | str | None = None,
    signer_socket_timeout_s: float = DEFAULT_SIGNER_SOCKET_TIMEOUT_S,
    signer_socket_max_response_bytes: int = DEFAULT_SIGNER_SOCKET_MAX_RESPONSE_BYTES,
    signer_socket_connector: Optional[SignerSocketConnector] = None,
    signature_verifier_backend: str | None = None,
    worktree_runner: Any = None,
    worktree_runner_mode: str | None = None,
    worktree_runner_timeout_s: int = 120,
    draft_pr_runner: Any = None,
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

    work_orders, work_order_reasons = _load_work_orders(root, work_orders_path)
    if work_order_reasons:
        return _not_ready(work_order_reasons, chain_results_path=None)

    valve_environment, valve_reasons = _read_json_outside_repo(
        root,
        valve_environment_path,
        missing_reason="missing_valve_environment_path",
        inside_reason="valve_environment_path_inside_repo",
        unreadable_reason="malformed_valve_environment",
        required=False,
    )
    if valve_reasons:
        return _not_ready(valve_reasons, chain_results_path=None)

    generic_writer_dryrun_result, generic_writer_reasons = _read_json_outside_repo(
        root,
        generic_writer_dryrun_result_path,
        missing_reason="missing_generic_writer_dryrun_result_path",
        inside_reason="generic_writer_dryrun_result_path_inside_repo",
        unreadable_reason="malformed_generic_writer_dryrun_result",
        required=False,
    )
    if generic_writer_reasons:
        return _not_ready(generic_writer_reasons, chain_results_path=None)

    governed_shell_dryrun_result, governed_shell_reasons = _read_json_outside_repo(
        root,
        governed_shell_dryrun_result_path,
        missing_reason="missing_governed_shell_dryrun_result_path",
        inside_reason="governed_shell_dryrun_result_path_inside_repo",
        unreadable_reason="malformed_governed_shell_dryrun_result",
        required=False,
    )
    if governed_shell_reasons:
        return _not_ready(governed_shell_reasons, chain_results_path=None)

    artifact_contents, artifact_contents_reasons = _read_json_outside_repo(
        root,
        artifact_contents_path,
        missing_reason="missing_artifact_contents_path",
        inside_reason="artifact_contents_path_inside_repo",
        unreadable_reason="malformed_artifact_contents",
        required=False,
    )
    if artifact_contents_reasons:
        return _not_ready(artifact_contents_reasons, chain_results_path=None)

    holoindex_evidence, holoindex_reasons = _read_json_outside_repo(
        root,
        holoindex_evidence_path,
        missing_reason="missing_holoindex_evidence_path",
        inside_reason="holoindex_evidence_path_inside_repo",
        unreadable_reason="malformed_holoindex_evidence",
        required=False,
    )
    if holoindex_reasons:
        return _not_ready(holoindex_reasons, chain_results_path=None)

    verifier_request, verifier_request_reasons = _read_json_outside_repo(
        root,
        verifier_request_path,
        missing_reason="missing_verifier_request_path",
        inside_reason="verifier_request_path_inside_repo",
        unreadable_reason="malformed_verifier_request",
        required=False,
    )
    if verifier_request_reasons:
        return _not_ready(verifier_request_reasons, chain_results_path=None)

    publish_request, publish_request_reasons = _read_json_outside_repo(
        root,
        publish_request_path,
        missing_reason="missing_publish_request_path",
        inside_reason="publish_request_path_inside_repo",
        unreadable_reason="malformed_publish_request",
        required=False,
    )
    if publish_request_reasons:
        return _not_ready(publish_request_reasons, chain_results_path=None)

    resolved_worktree_runner, runner_reasons = _build_worktree_runner(
        root,
        injected_runner=worktree_runner,
        mode=worktree_runner_mode,
        timeout_s=worktree_runner_timeout_s,
    )
    if runner_reasons:
        return _not_ready(runner_reasons, chain_results_path=None)

    dependency_bundle = load_reddog_main_resident_queue_runtime_dependency_bundle(
        repo_root=root,
        authority_state_path=authority_state_path,
        permission_snapshots_path=permission_snapshots_path,
        principal_authority_records_path=principal_authority_records_path,
        signer_socket_path=signer_socket_path,
        signer_socket_timeout_s=signer_socket_timeout_s,
        signer_socket_max_response_bytes=signer_socket_max_response_bytes,
        signer_socket_connector=signer_socket_connector,
        signature_verifier_backend=signature_verifier_backend,
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
    run_now = _parse_datetime(now_iso) if now_iso else None
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
        signature_verifier=dependency_bundle.signature_verifier,
        principal_key_resolver=dependency_bundle.principal_key_resolver,
        nonce_store=dependency_bundle.nonce_store,
        revocation_oracle=dependency_bundle.revocation_oracle,
        work_order_resolver=(
            JsonResidentQueueWorkOrderResolver(work_orders) if work_orders is not None else None
        ),
        repo_root=root,
        valve_environment=valve_environment,
        worktree_runner=resolved_worktree_runner,
        generic_writer_dryrun_result=generic_writer_dryrun_result,
        governed_shell_dryrun_result=governed_shell_dryrun_result,
        artifact_contents=artifact_contents,
        holoindex_evidence=holoindex_evidence,
        verifier_request=verifier_request,
        publish_request=publish_request,
        draft_pr_runner=draft_pr_runner,
        now_datetime=run_now,
        permission_expires_at=(
            str(valve_environment.get("permission_expires_at"))
            if isinstance(valve_environment, Mapping) and valve_environment.get("permission_expires_at")
            else None
        ),
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
    required: bool = True,
) -> tuple[Optional[Mapping[str, Any]], tuple[str, ...]]:
    if not value:
        return None, (missing_reason,) if required else ()
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


def _load_work_orders(
    repo_root: Path,
    value: Path | str | None,
) -> tuple[Optional[Mapping[str, Mapping[str, Any]]], tuple[str, ...]]:
    payload, reasons = _read_json_outside_repo(
        repo_root,
        value,
        missing_reason="missing_work_orders_path",
        inside_reason="work_orders_path_inside_repo",
        unreadable_reason="malformed_work_orders",
        required=False,
    )
    if reasons:
        return None, reasons
    if payload is None:
        return None, ()
    raw = payload.get("work_orders")
    if not isinstance(raw, Mapping):
        return None, ("malformed_work_orders",)
    work_orders: dict[str, Mapping[str, Any]] = {}
    for key, item in raw.items():
        if not isinstance(item, Mapping):
            return None, ("malformed_work_orders",)
        work_order_id = str(item.get("work_order_id") or "").strip()
        if not work_order_id or str(key) != work_order_id:
            return None, ("malformed_work_orders",)
        work_orders[work_order_id] = dict(item)
    return work_orders, ()


def _build_worktree_runner(
    repo_root: Path,
    *,
    injected_runner: Any,
    mode: str | None,
    timeout_s: int,
) -> tuple[Any, tuple[str, ...]]:
    if injected_runner is not None:
        return injected_runner, ()
    normalized = str(mode or "").strip().lower()
    if not normalized:
        return None, ()
    if normalized not in {"real", "git_worktree"}:
        return None, ("unsupported_worktree_runner_mode",)
    if int(timeout_s) <= 0:
        return None, ("invalid_worktree_runner_timeout",)
    from modules.communication.moltbot_bridge.src.reddog_wre_worktree_runner import (
        RealRedDogWorktreeRunner,
    )

    return RealRedDogWorktreeRunner(repo_root, timeout_s=int(timeout_s)), ()


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


def _parse_datetime(value: str) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


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
        no_signature_verification_performed="authority_verification" not in loop.dispatched_stages,
        no_worktree_created="worktree_create" not in loop.dispatched_stages,
        no_bounded_task_execution_performed="bounded_worker_pilot" not in loop.dispatched_stages,
        no_bounded_file_edit_performed="bounded_worker_pilot" not in loop.dispatched_stages,
        no_slice_verification_performed="slice_verifier" not in loop.dispatched_stages,
        no_verified_draft_pr_publish_performed=(
            "verified_draft_pr_publish" not in loop.dispatched_stages
        ),
        no_repo_mutation_performed=not any(
            stage in loop.dispatched_stages for stage in ("worktree_create", "bounded_worker_pilot")
        ),
        no_pr_created="verified_draft_pr_publish" not in loop.dispatched_stages,
    )


__all__ = [
    "JsonResidentQueueWorkOrderResolver",
    "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED",
    "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY",
    "RedDogMainResidentQueueSerialLoopBootstrapResult",
    "run_reddog_main_resident_queue_serial_loop_bootstrap",
]
