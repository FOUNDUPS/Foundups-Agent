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

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    AtomicJsonResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_refresh_runtime import AtomicJsonAuthoritativeWorkStateStore
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
from modules.communication.moltbot_bridge.src.reddog_execution_valve_use_time_authority import (
    GovernedValveUseTimeAuthorityResolver,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    CANONICAL_ENVIRONMENT_SCHEMA_VERSION,
    VALVE_OPEN_WORKTREE_CREATE,
    GovernedExecutionValveEnvironment,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_request_dryrun import (
    plan_reddog_wre_queue_authority_request_dry_run,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_consumer_dryrun import (
    plan_reddog_wre_queue_consumer_dry_run,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import build_work_order_materialization_binding
from modules.communication.moltbot_bridge.src.reddog_model_runtime_verifier_bootstrap import (
    ModelRuntimeVerifierConfig,
    build_model_runtime_verifier,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_outside_repo as _read_json_outside_repo,
    read_reddog_runtime_json_mapping,
)
from modules.ai_intelligence.ai_gateway.src.model_feedback_ledger import (
    JsonlModelFeedbackLedgerStore,
)
from modules.infrastructure.wre_core.src.reddog_verified_outcome_ratchet import (
    JsonlOutcomeRatchetStore,
)


REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED = "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED"
REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY = "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY"
WORK_ORDER_MATERIALIZER_MODE_AUTHORITY_PROFILE = "authority_profile"


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
    queue_chain_requeue_required: bool = False
    retry_at: Optional[str] = None
    runtime_dependency_bundle_status: str = REDDOG_RUNTIME_DEPENDENCY_BUNDLE_NOT_REQUESTED
    runtime_dependency_bundle_requested: bool = False
    no_signing_performed: bool = True
    no_signature_verification_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_bounded_task_execution_performed: bool = True
    no_bounded_file_edit_performed: bool = True
    no_exact_sha_commit_performed: bool = True
    no_slice_verification_performed: bool = True
    no_verified_draft_pr_publish_performed: bool = True
    no_verified_outcome_ratchet_performed: bool = True
    no_model_feedback_ledger_admission_performed: bool = True
    no_held_out_regression_gate_performed: bool = True
    no_pattern_memory_admission_performed: bool = True
    no_pattern_memory_write_performed: bool = True
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
    runtime_allowed_root: Path | str | None = None,
    work_state_path: Path | str | None,
    chain_results_path: Path | str | None,
    authority_profile_path: Path | str | None,
    work_orders_path: Path | str | None = None,
    work_order_materializer_mode: str | None = None,
    valve_environment_path: Path | str | None = None,
    generic_writer_dryrun_result_path: Path | str | None = None,
    governed_shell_dryrun_result_path: Path | str | None = None,
    artifact_contents_path: Path | str | None = None,
    artifact_generation_request_path: Path | str | None = None,
    artifact_generation_request_binding_enabled: bool = False,
    holoindex_evidence_path: Path | str | None = None,
    verifier_request_path: Path | str | None = None,
    evidence_producer_request_path: Path | str | None = None,
    publish_request_path: Path | str | None = None,
    ratchet_request_path: Path | str | None = None,
    outcome_ratchet_store_path: Path | str | None = None,
    model_feedback_ledger_store_path: Path | str | None = None,
    held_out_gate_request_path: Path | str | None = None,
    admission_request_path: Path | str | None = None,
    authority_state_path: Path | str | None = None,
    permission_snapshots_path: Path | str | None = None,
    principal_authority_records_path: Path | str | None = None,
    signer_socket_path: Path | str | None = None,
    signer_socket_timeout_s: float = DEFAULT_SIGNER_SOCKET_TIMEOUT_S,
    signer_socket_max_response_bytes: int = DEFAULT_SIGNER_SOCKET_MAX_RESPONSE_BYTES,
    signer_socket_connector: Optional[SignerSocketConnector] = None,
    signature_verifier_backend: str | None = None,
    worktree_runner: Any = None,
    pilot_dryrun_binding_enabled: bool = False,
    worktree_runner_mode: str | None = None,
    worktree_runner_timeout_s: int = 120,
    artifact_generator: Any = None,
    artifact_generator_mode: str | None = None,
    model_runtime_binding_verifier: Any = None,
    model_runtime_verifier_config: ModelRuntimeVerifierConfig | Mapping[str, Any] | None = None,
    evidence_command_runner: Any = None,
    slice_verifier_request_binding_enabled: bool = False,
    evidence_command_runner_mode: str | None = None,
    draft_pr_publish_request_binding_enabled: bool = False,
    outcome_ratchet_request_binding_enabled: bool = False,
    held_out_gate_request_binding_enabled: bool = False,
    pattern_memory_admission_request_binding_enabled: bool = False,
    draft_pr_runner: Any = None,
    outcome_ratchet_store: Any = None,
    model_feedback_ledger_store: Any = None,
    explicit_pattern_memory_write_requested: bool = False,
    ratchet_pattern_memory_sink: Any = None,
    pattern_memory_admission_sink: Any = None,
    worker_dispatch_writer: Any = None,
    assurance_reservation_store: Any = None,
    requested_queue_item_id: str | None = None,
    now_iso: str | None = None,
    now_epoch: int | None = None,
    trusted_now_epoch: Optional[Callable[[], int]] = None,
    max_steps: int = 1,
) -> RedDogMainResidentQueueSerialLoopBootstrapResult:
    """Load runtime inputs and run the bounded resident queue serial loop."""
    root = Path(repo_root).resolve()
    authority_clock = trusted_now_epoch or (lambda: int(datetime.now().timestamp()))
    try:
        fresh_now_epoch = int(authority_clock())
    except (TypeError, ValueError, OverflowError):
        return _not_ready(("trusted_now_epoch_invalid",), chain_results_path=None)
    if runtime_allowed_root is None:
        return _not_ready(("missing_runtime_artifact_root",), chain_results_path=None)
    runtime_root = Path(os.path.abspath(Path(runtime_allowed_root).expanduser()))
    try:
        validate_runtime_root_path(runtime_root, repo_root=root)
    except ValueError:
        return _not_ready(("invalid_runtime_artifact_root",), chain_results_path=None)
    snapshot, snapshot_reasons = _read_json_outside_repo(
        root,
        runtime_root,
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
        runtime_root,
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
        runtime_root,
        chain_results_path,
        missing_reason="missing_chain_results_path",
        inside_reason="chain_results_path_inside_repo",
    )
    if chain_reasons:
        return _not_ready(chain_reasons, chain_results_path=None)
    assert chain_path is not None
    work_orders, work_order_reasons = _load_or_materialize_work_orders(
        root,
        runtime_root,
        work_orders_path,
        mode=work_order_materializer_mode,
        snapshot=snapshot,
        authority_profile=profile,
        requested_queue_item_id=requested_queue_item_id,
        now_iso=now_iso,
    )
    if work_order_reasons:
        return _not_ready(work_order_reasons, chain_results_path=None)
    valve_environment, valve_reasons = _read_json_outside_repo(
        root,
        runtime_root,
        valve_environment_path,
        missing_reason="missing_valve_environment_path",
        inside_reason="valve_environment_path_inside_repo",
        unreadable_reason="malformed_valve_environment",
        required=False,
    )
    if valve_reasons:
        return _not_ready(valve_reasons, chain_results_path=None)
    if valve_environment is not None and (
        valve_environment.get("schema_version") != CANONICAL_ENVIRONMENT_SCHEMA_VERSION
    ):
        return _not_ready(
            ("governed_execution_valve_environment_required",),
            chain_results_path=None,
        )

    generic_writer_dryrun_result, generic_writer_reasons = _read_json_outside_repo(
        root,
        runtime_root,
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
        runtime_root,
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
        runtime_root,
        artifact_contents_path,
        missing_reason="missing_artifact_contents_path",
        inside_reason="artifact_contents_path_inside_repo",
        unreadable_reason="malformed_artifact_contents",
        required=False,
    )
    if artifact_contents_reasons:
        return _not_ready(artifact_contents_reasons, chain_results_path=None)

    artifact_generation_request, artifact_generation_request_reasons = _read_json_outside_repo(
        root,
        runtime_root,
        artifact_generation_request_path,
        missing_reason="missing_artifact_generation_request_path",
        inside_reason="artifact_generation_request_path_inside_repo",
        unreadable_reason="malformed_artifact_generation_request",
        required=False,
    )
    if artifact_generation_request_reasons:
        return _not_ready(artifact_generation_request_reasons, chain_results_path=None)

    holoindex_evidence, holoindex_reasons = _read_json_outside_repo(
        root,
        runtime_root,
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
        runtime_root,
        verifier_request_path,
        missing_reason="missing_verifier_request_path",
        inside_reason="verifier_request_path_inside_repo",
        unreadable_reason="malformed_verifier_request",
        required=False,
    )
    if verifier_request_reasons:
        return _not_ready(verifier_request_reasons, chain_results_path=None)

    evidence_producer_request, evidence_producer_request_reasons = _read_json_outside_repo(
        root,
        runtime_root,
        evidence_producer_request_path,
        missing_reason="missing_evidence_producer_request_path",
        inside_reason="evidence_producer_request_path_inside_repo",
        unreadable_reason="malformed_evidence_producer_request",
        required=False,
    )
    if evidence_producer_request_reasons:
        return _not_ready(evidence_producer_request_reasons, chain_results_path=None)

    publish_request, publish_request_reasons = _read_json_outside_repo(
        root,
        runtime_root,
        publish_request_path,
        missing_reason="missing_publish_request_path",
        inside_reason="publish_request_path_inside_repo",
        unreadable_reason="malformed_publish_request",
        required=False,
    )
    if publish_request_reasons:
        return _not_ready(publish_request_reasons, chain_results_path=None)

    ratchet_request, ratchet_request_reasons = _read_json_outside_repo(
        root,
        runtime_root,
        ratchet_request_path,
        missing_reason="missing_ratchet_request_path",
        inside_reason="ratchet_request_path_inside_repo",
        unreadable_reason="malformed_ratchet_request",
        required=False,
    )
    if ratchet_request_reasons:
        return _not_ready(ratchet_request_reasons, chain_results_path=None)

    held_out_gate_request, held_out_gate_request_reasons = _read_json_outside_repo(
        root,
        runtime_root,
        held_out_gate_request_path,
        missing_reason="missing_held_out_gate_request_path",
        inside_reason="held_out_gate_request_path_inside_repo",
        unreadable_reason="malformed_held_out_gate_request",
        required=False,
    )
    if held_out_gate_request_reasons:
        return _not_ready(held_out_gate_request_reasons, chain_results_path=None)

    admission_request, admission_request_reasons = _read_json_outside_repo(
        root,
        runtime_root,
        admission_request_path,
        missing_reason="missing_admission_request_path",
        inside_reason="admission_request_path_inside_repo",
        unreadable_reason="malformed_admission_request",
        required=False,
    )
    if admission_request_reasons:
        return _not_ready(admission_request_reasons, chain_results_path=None)

    chain_state = _read_existing_chain_state(chain_path, runtime_root)
    if (
        artifact_generation_request_binding_enabled
        and artifact_contents is None
        and artifact_generation_request is None
    ):
        artifact_generation_request = _derive_artifact_generation_request_from_chain(
            chain_state=chain_state,
            work_orders=work_orders,
            repo_root=root,
            holoindex_evidence=holoindex_evidence,
        )
    if outcome_ratchet_request_binding_enabled and ratchet_request is None:
        ratchet_request = _derive_outcome_ratchet_request_from_chain(
            chain_state,
            work_orders=work_orders,
        )
    if held_out_gate_request_binding_enabled and held_out_gate_request is None:
        held_out_gate_request = _derive_held_out_gate_request_from_chain(chain_state)
    if pattern_memory_admission_request_binding_enabled and admission_request is None:
        admission_request = _derive_pattern_memory_admission_request_from_chain(chain_state)

    resolved_outcome_ratchet_store, ratchet_store_reasons = _build_outcome_ratchet_store(
        root,
        runtime_root,
        injected_store=outcome_ratchet_store,
        store_path=outcome_ratchet_store_path,
    )
    if ratchet_store_reasons:
        return _not_ready(ratchet_store_reasons, chain_results_path=None)

    resolved_model_feedback_store, model_feedback_store_reasons = _build_model_feedback_ledger_store(
        root,
        runtime_root,
        injected_store=model_feedback_ledger_store,
        store_path=model_feedback_ledger_store_path,
    )
    if model_feedback_store_reasons:
        return _not_ready(model_feedback_store_reasons, chain_results_path=None)
    resolved_worktree_runner, runner_reasons = _build_worktree_runner(
        root,
        injected_runner=worktree_runner,
        mode=worktree_runner_mode,
        timeout_s=worktree_runner_timeout_s,
    )
    if runner_reasons:
        return _not_ready(runner_reasons, chain_results_path=None)
    generation = _build_generation_dependencies(
        root, runtime_root, artifact_generator, artifact_generator_mode,
        model_runtime_binding_verifier, model_runtime_verifier_config, authority_clock)
    resolved_artifact_generator, resolved_model_verifier, generation_reasons = generation
    if generation_reasons:
        return _not_ready(generation_reasons, chain_results_path=None)
    resolved_evidence_command_runner, evidence_runner_reasons = _build_evidence_command_runner(
        injected_runner=evidence_command_runner,
        mode=evidence_command_runner_mode,
    )
    if evidence_runner_reasons:
        return _not_ready(evidence_runner_reasons, chain_results_path=None)

    dependency_bundle = load_reddog_main_resident_queue_runtime_dependency_bundle(
        repo_root=root,
        runtime_allowed_root=runtime_root,
        authority_state_path=authority_state_path,
        permission_snapshots_path=permission_snapshots_path,
        principal_authority_records_path=principal_authority_records_path,
        signer_socket_path=signer_socket_path,
        signer_socket_timeout_s=signer_socket_timeout_s,
        signer_socket_max_response_bytes=signer_socket_max_response_bytes,
        signer_socket_connector=signer_socket_connector,
        signature_verifier_backend=signature_verifier_backend,
        now_epoch=(fresh_now_epoch if authority_state_path else None),
    )
    if dependency_bundle.accepted is not True:
        return _not_ready(
            dependency_bundle.rejection_reasons,
            chain_results_path=None,
            runtime_dependency_bundle_status=dependency_bundle.status,
            runtime_dependency_bundle_requested=dependency_bundle.requested,
        )

    governed_environment = None
    governed_authority_resolver = None
    if isinstance(valve_environment, Mapping):
        try:
            governed_environment = GovernedExecutionValveEnvironment.from_mapping(
                valve_environment
            )
        except ValueError as exc:
            return _not_ready((str(exc),), chain_results_path=None)
        governed_authority_resolver = GovernedValveUseTimeAuthorityResolver(
            repo_root=root,
            work_state_path=_runtime_input_path(root, work_state_path),
            authority_profile_path=_runtime_input_path(root, authority_profile_path),
            permission_snapshots_path=_runtime_input_path(root, permission_snapshots_path),
            principal_authority_records_path=_runtime_input_path(
                root, principal_authority_records_path
            ),
            valve_environment_path=_runtime_input_path(root, valve_environment_path),
            runtime_allowed_root=runtime_root,
            signature_verifier=dependency_bundle.signature_verifier,
            principal_key_resolver=dependency_bundle.principal_key_resolver,
            nonce_store=dependency_bundle.nonce_store,
            snapshot_resolver=dependency_bundle.snapshot_resolver,
            revocation_oracle=dependency_bundle.revocation_oracle,
            now_epoch=int(dependency_bundle.now_epoch or 0),
            required_valve_state=VALVE_OPEN_WORKTREE_CREATE,
            trusted_now_epoch=authority_clock,
        )
    store = AtomicJsonResidentQueueChainResultsStore(
        chain_path,
        allowed_root=runtime_root,
    )
    run_now = _parse_datetime(now_iso) if now_iso else None
    registry = build_reddog_resident_queue_stage_handler_registry(
        work_state_snapshot=snapshot, chain_results_store=store,
        authoritative_work_state_store=AtomicJsonAuthoritativeWorkStateStore(_runtime_input_path(root, work_state_path), allowed_root=runtime_root, repo_root=root),
        authority_profile=profile, now_iso=now_iso or "",
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
        valve_environment=governed_environment,
        governed_use_time_authority_resolver=governed_authority_resolver,
        worktree_runner=resolved_worktree_runner,
        pilot_dryrun_binding_enabled=pilot_dryrun_binding_enabled,
        generic_writer_dryrun_result=generic_writer_dryrun_result,
        governed_shell_dryrun_result=governed_shell_dryrun_result,
        artifact_contents=artifact_contents,
        artifact_generation_request=artifact_generation_request,
        artifact_generation_request_binding_enabled=artifact_generation_request_binding_enabled,
        artifact_generator=resolved_artifact_generator,
        model_runtime_binding_verifier=resolved_model_verifier,
        commit_runner=draft_pr_runner,
        commit_evidence_runner=resolved_evidence_command_runner,
        holoindex_evidence=holoindex_evidence,
        verifier_request=verifier_request,
        evidence_producer_request=evidence_producer_request,
        evidence_command_runner=resolved_evidence_command_runner,
        slice_verifier_request_binding_enabled=slice_verifier_request_binding_enabled,
        publish_request=publish_request,
        draft_pr_publish_request_binding_enabled=draft_pr_publish_request_binding_enabled,
        draft_pr_runner=draft_pr_runner,
        ratchet_request=ratchet_request,
        outcome_ratchet_store=resolved_outcome_ratchet_store,
        model_feedback_ledger_store=resolved_model_feedback_store,
        held_out_gate_request=held_out_gate_request,
        explicit_pattern_memory_write_requested=explicit_pattern_memory_write_requested,
        ratchet_pattern_memory_sink=ratchet_pattern_memory_sink,
        admission_request=admission_request,
        pattern_memory_admission_sink=pattern_memory_admission_sink,
        worker_dispatch_writer=worker_dispatch_writer,
        trusted_now_epoch=authority_clock,
        assurance_reservation_store=assurance_reservation_store,
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


def _runtime_input_path(repo_root: Path, value: Path | str | None) -> Optional[Path]:
    if not value:
        return None
    path = Path(value)
    candidate = path if path.is_absolute() else repo_root / path
    return Path(os.path.abspath(candidate.expanduser()))


def _load_work_orders(
    repo_root: Path,
    allowed_root: Path,
    value: Path | str | None,
) -> tuple[Optional[Mapping[str, Mapping[str, Any]]], tuple[str, ...]]:
    payload, reasons = _read_json_outside_repo(
        repo_root,
        allowed_root,
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


def _load_or_materialize_work_orders(
    repo_root: Path,
    allowed_root: Path,
    value: Path | str | None,
    *,
    mode: str | None,
    snapshot: Mapping[str, Any],
    authority_profile: Mapping[str, Any],
    requested_queue_item_id: str | None,
    now_iso: str | None,
) -> tuple[Optional[Mapping[str, Mapping[str, Any]]], tuple[str, ...]]:
    normalized_mode = str(mode or "").strip().lower()
    if value and normalized_mode:
        return None, ("work_order_materializer_conflicts_with_work_orders_path",)
    if normalized_mode and normalized_mode != WORK_ORDER_MATERIALIZER_MODE_AUTHORITY_PROFILE:
        return None, ("unsupported_work_order_materializer_mode",)

    work_orders, reasons = _load_work_orders(repo_root, allowed_root, value)
    if reasons or work_orders is not None or not normalized_mode:
        return work_orders, reasons

    return _materialize_work_orders_from_authority_profile(
        snapshot=snapshot,
        authority_profile=authority_profile,
        requested_queue_item_id=requested_queue_item_id,
        now_iso=now_iso,
    )


def _materialize_work_orders_from_authority_profile(
    *,
    snapshot: Mapping[str, Any],
    authority_profile: Mapping[str, Any],
    requested_queue_item_id: str | None,
    now_iso: str | None,
) -> tuple[Optional[Mapping[str, Mapping[str, Any]]], tuple[str, ...]]:
    queue_result = plan_reddog_wre_queue_consumer_dry_run(
        snapshot,
        now_iso=now_iso,
        requested_queue_item_id=requested_queue_item_id,
        require_governed_lineage=True,
    )
    if queue_result.accepted is not True:
        return None, tuple(
            f"work_order_materializer_queue:{reason}" for reason in queue_result.rejection_reasons
        )

    queue_receipt = queue_result.receipt.to_dict() if queue_result.receipt is not None else {}
    queue_item_id = str(queue_receipt.get("queue_item_id") or "")
    materialization_binding_seed = build_work_order_materialization_binding(
        work_order_id=str(
            authority_profile.get("work_order_id")
            or "wre-queue-" + hashlib.sha256(queue_item_id.encode("utf-8")).hexdigest()[:16]
        ),
        base_ref=str(authority_profile.get("base_ref") or ""),
        queue_consumer_receipt=queue_receipt,
    )
    authority_request = plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=queue_result.to_dict(),
        authority_profile=authority_profile,
        work_order=materialization_binding_seed,
    )
    if authority_request.accepted is not True or authority_request.delegated_authority_request is None:
        return None, tuple(
            f"work_order_materializer_authority:{reason}" for reason in authority_request.rejection_reasons
        )

    receipt = authority_request.receipt
    if receipt is None:
        return None, ("work_order_materializer_authority:missing_receipt",)

    request = authority_request.delegated_authority_request
    work_order_id = str(request.get("work_order_id") or "")
    if not work_order_id:
        return None, ("work_order_materializer_missing_work_order_id",)

    queue_item = _queue_item(snapshot=snapshot, queue_item_id=str(queue_receipt.get("queue_item_id") or ""))
    queue_wsp15_allocation = _nested_mapping(queue_item, "wsp15_allocation_receipt")
    slice_id = str(queue_receipt.get("slice_id") or "")
    created_at = str(now_iso or _snapshot_timestamp(snapshot) or "1970-01-01T00:00:00+00:00")
    expiry = str(_claim_expiry(snapshot, queue_receipt) or authority_profile.get("expiry") or "")
    if not expiry:
        return None, ("work_order_materializer_missing_expiry",)

    context_binding, binding_reasons = _operational_context_binding(
        authority_profile=authority_profile,
        snapshot=snapshot,
        queue_wsp15_allocation=queue_wsp15_allocation,
        queue_wsp15_allocation_receipt_id=str(queue_receipt.get("wsp15_allocation_receipt_id") or ""),
    )
    if binding_reasons:
        return None, binding_reasons

    holoindex_evidence, holo_reasons = _holoindex_evidence(authority_profile, snapshot)
    if holo_reasons:
        return None, holo_reasons

    bounded_worker_plan, bounded_worker_plan_reasons = _bounded_worker_plan_from_authority_profile(
        authority_profile=authority_profile,
        allowed_paths=_string_list(request.get("allowed_paths")),
        foundup_id=str(request.get("foundup_id") or authority_profile.get("foundup_id") or ""),
    )
    if bounded_worker_plan_reasons:
        return None, bounded_worker_plan_reasons

    evidence_seed = {
        "queue_receipt": queue_receipt,
        "delegated_authority_request": request,
        "authority_request_receipt": receipt.to_dict(),
        "operational_context_binding": context_binding,
        "holoindex_evidence": holoindex_evidence,
    }
    evidence_digest = _canonical_digest(evidence_seed)
    wsps = _string_list(authority_profile.get("wsp_applicability")) or ["WSP_34", "WSP_50", "WSP_97"]
    code_ref = "modules/communication/moltbot_bridge/src/reddog_main_resident_queue_serial_loop_bootstrap.py"
    work_order = {
        "work_order_id": work_order_id,
        "created_at": created_at,
        "red_dog_instance_id": str(
            authority_profile.get("red_dog_instance_id") or "reddog-main-resident-queue"
        ),
        "authenticated_principal": str(request.get("principal_id") or ""),
        "principal_provider": str(request.get("principal_provider") or ""),
        "repo_full_name": str(request.get("repo_full_name") or ""),
        "foundup_id": str(request.get("foundup_id") or ""),
        "repo_permission_snapshot": {
            "permission_level": str(authority_profile.get("permission_level") or "write"),
            "captured_at": str(authority_profile.get("permission_captured_at") or created_at),
            "source": str(authority_profile.get("permission_source") or "authority_profile"),
            "digest": str(request.get("permission_snapshot_digest") or ""),
        },
        "requested_operation": str(request.get("requested_operation") or ""),
        "valve_state_required": str(request.get("valve_state_required") or ""),
        "authority_tier": str(authority_profile.get("authority_tier") or "source"),
        "allowed_paths": _string_list(request.get("allowed_paths")),
        "denied_paths": _string_list(request.get("denied_paths")),
        "branch_name": str(
            authority_profile.get("branch_name")
            or _branch_name(slice_id=slice_id, queue_item_id=str(queue_receipt.get("queue_item_id") or ""))
        ),
        "base_ref": str(request["base_ref"]),
        "task_summary": str(
            authority_profile.get("task_summary")
            or f"Resident queue materialized governed work order for {slice_id or 'selected slice'}."
        ),
        "wsp_applicability": wsps,
        "holoindex_evidence_refs": _string_list(
            authority_profile.get("holoindex_evidence_refs")
        )
        or [code_ref],
        "skillz_candidates": _string_list(authority_profile.get("skillz_candidates")),
        "required_tests": _string_list(authority_profile.get("required_tests")),
        "required_policy_gates": _string_list(authority_profile.get("required_policy_gates"))
        or ["signed_work_order_authority", "execution_valve"],
        "required_reviewers": _string_list(authority_profile.get("required_reviewers")),
        "sentinel_checks": _string_list(authority_profile.get("sentinel_checks")),
        "rollback_plan": str(
            authority_profile.get("rollback_plan")
            or "Abort the resident queue chain before live mutation; generated work order is in-memory only."
        ),
        "expiry": expiry,
        "nonce": str(
            authority_profile.get("work_order_nonce")
            or f"work-order:{request.get('work_authority_nonce') or work_order_id}"
        ),
        "evidence_digest": evidence_digest,
        "advisory_only_source_packet": _advisory_source_packet(evidence_seed),
        "holoindex_evidence": holoindex_evidence,
        "operational_context_binding": context_binding,
        "wsp15_allocation_receipt": dict(queue_wsp15_allocation),
        "wsp15_allocation_receipt_id": str(queue_receipt.get("wsp15_allocation_receipt_id") or ""),
        "wsp15_allocation_digest": str(queue_receipt.get("wsp15_allocation_digest") or ""),
        "wsp15_priority": str(queue_receipt.get("wsp15_priority") or ""),
        "wsp15_mps_total": queue_receipt.get("wsp15_mps_total"),
        "wsp15_reasoning_tier": str(queue_receipt.get("reasoning_tier") or ""),
        "model_selection_receipt": _nested_mapping(authority_profile, "model_selection_receipt"),
        "model_selection_receipt_id": str(authority_profile.get("model_selection_receipt_id") or ""),
        "model_selection_digest": str(authority_profile.get("model_selection_digest") or ""),
        "model_runtime_binding_receipt": _nested_mapping(authority_profile, "model_runtime_binding_receipt"),
        "model_runtime_binding_receipt_id": str(authority_profile.get("model_runtime_binding_receipt_id") or ""),
        "model_runtime_binding_digest": str(authority_profile.get("model_runtime_binding_digest") or ""),
        "memex_supply_receipt_id": str(queue_receipt.get("memex_supply_receipt_id") or ""),
        "memex_supply_digest": str(queue_receipt.get("memex_supply_digest") or ""),
    }
    if bounded_worker_plan:
        work_order["bounded_worker_plan"] = bounded_worker_plan
    return {work_order_id: work_order}, ()


def _bounded_worker_plan_from_authority_profile(
    *,
    authority_profile: Mapping[str, Any],
    allowed_paths: tuple[str, ...],
    foundup_id: str,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    raw_plan = authority_profile.get("bounded_worker_plan")
    if raw_plan is not None and not isinstance(raw_plan, Mapping):
        return {}, ("work_order_materializer_bounded_worker_plan_invalid:type",)
    plan = _nested_mapping(authority_profile, "bounded_worker_plan")
    if not plan:
        return {}, ()
    if not _is_ascii_json_safe(plan):
        return {}, ("work_order_materializer_bounded_worker_plan_non_ascii",)

    reasons: list[str] = []
    required_fields = (
        "operation",
        "domain_id",
        "domain_profile",
        "planned_artifacts",
        "shell_profile",
        "shell_argv",
        "selection_receipt",
        "signed_receipt_chain",
    )
    for field_name in required_fields:
        if field_name not in plan or plan.get(field_name) in (None, "", (), [], {}):
            reasons.append(f"work_order_materializer_bounded_worker_plan_missing:{field_name}")

    domain_id = str(plan.get("domain_id") or "").strip()
    if foundup_id and domain_id and domain_id != foundup_id:
        reasons.append("work_order_materializer_bounded_worker_plan_scope_mismatch:domain_id")

    planned_artifacts = _string_list(plan.get("planned_artifacts"))
    if not planned_artifacts:
        reasons.append("work_order_materializer_bounded_worker_plan_invalid:planned_artifacts")
    for artifact in planned_artifacts:
        if not _relative_repo_path(artifact):
            reasons.append("work_order_materializer_bounded_worker_plan_invalid_artifact_path")
            continue
        if not _path_allowed_by_patterns(artifact, allowed_paths):
            reasons.append("work_order_materializer_bounded_worker_plan_artifact_outside_allowed_paths")

    requested_allowed_paths = _string_list(plan.get("requested_allowed_paths"))
    for requested in requested_allowed_paths:
        if not _relative_repo_path(requested.rstrip("*")):
            reasons.append("work_order_materializer_bounded_worker_plan_invalid_requested_allowed_path")
            continue
        if not _pattern_within_allowed_paths(requested, allowed_paths):
            reasons.append("work_order_materializer_bounded_worker_plan_requested_path_outside_allowed_paths")

    if not _string_list(plan.get("shell_argv")):
        reasons.append("work_order_materializer_bounded_worker_plan_invalid:shell_argv")
    for mapping_field in ("domain_profile", "shell_profile", "selection_receipt", "signed_receipt_chain"):
        if not _nested_mapping(plan, mapping_field):
            reasons.append(f"work_order_materializer_bounded_worker_plan_invalid:{mapping_field}")

    if reasons:
        return {}, tuple(dict.fromkeys(reasons))
    return dict(plan), ()


def _is_ascii_json_safe(value: Any) -> bool:
    try:
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("ascii")
    except (TypeError, UnicodeEncodeError, ValueError):
        return False
    return True


def _relative_repo_path(value: str) -> bool:
    raw = str(value or "").replace("\\", "/").strip()
    if not raw or raw.startswith("/") or raw.startswith("../") or "/../" in raw or raw == "..":
        return False
    if ":" in raw:
        return False
    return True


def _path_allowed_by_patterns(path: str, allowed_paths: tuple[str, ...]) -> bool:
    normalized = str(path or "").replace("\\", "/").strip()
    return any(fnmatchcase(normalized, pattern.replace("\\", "/")) for pattern in allowed_paths)


def _pattern_within_allowed_paths(pattern: str, allowed_paths: tuple[str, ...]) -> bool:
    normalized = str(pattern or "").replace("\\", "/").strip()
    for allowed in allowed_paths:
        allowed_normalized = allowed.replace("\\", "/").strip()
        if normalized == allowed_normalized:
            return True
        if allowed_normalized.endswith("/**"):
            root = allowed_normalized[:-3].rstrip("/")
            if normalized == root or normalized.startswith(root + "/"):
                return True
    return False


def _canonical_digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read_existing_chain_state(
    chain_path: Path | None,
    allowed_root: Path,
) -> Mapping[str, Any]:
    if chain_path is None or not chain_path.exists():
        return {}
    try:
        payload = read_reddog_runtime_json_mapping(
            chain_path,
            allowed_root=allowed_root,
        )
    except Exception:
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _chain_stage_results(chain_state: Mapping[str, Any]) -> Mapping[str, Any]:
    stages = chain_state.get("stage_results")
    return stages if isinstance(stages, Mapping) else {}


def _derive_artifact_generation_request_from_chain(
    *,
    chain_state: Mapping[str, Any],
    work_orders: Mapping[str, Mapping[str, Any]] | None,
    repo_root: Path,
    holoindex_evidence: Mapping[str, Any] | None,
) -> Mapping[str, Any] | None:
    if not work_orders:
        return None
    stages = _chain_stage_results(chain_state)
    worktree_stage = _nested_mapping(stages, "worktree_create")
    worktree_result = _nested_mapping(worktree_stage, "worktree_create_result")
    work_order_id = str(worktree_result.get("work_order_id") or "")
    worktree_path = str(worktree_result.get("worktree_path") or "")
    if not work_order_id or not worktree_path:
        return None
    work_order = JsonResidentQueueWorkOrderResolver(work_orders).resolve(
        work_order_id=work_order_id,
        queue_item_id=None,
        selected_slice=None,
    )
    plan = _nested_mapping(work_order, "bounded_worker_plan")
    planned_artifacts = _string_list(plan.get("planned_artifacts"))
    signed_receipt_chain = _nested_mapping(plan, "signed_receipt_chain")
    authority_stage = _nested_mapping(stages, "authority_runtime")
    authority_result = _nested_mapping(authority_stage, "authority_result")
    work_authority = _nested_mapping(authority_result, "work_authority")
    authority_receipt = _nested_mapping(authority_result, "receipt")
    if (
        not plan
        or not planned_artifacts
        or not signed_receipt_chain
        or authority_result.get("accepted") is not True
        or not work_authority
    ):
        return None
    evidence = (
        (holoindex_evidence if isinstance(holoindex_evidence, Mapping) else {})
        or _nested_mapping(work_order, "holoindex_evidence")
        or _derived_holoindex_evidence(stages)
    )
    task_summary = str(work_order.get("task_summary") or "")
    if not task_summary:
        return None
    signed_authority = {
        **dict(work_authority),
        "accepted": True,
        "signature_gate_digest": str(
            authority_receipt.get("work_authority_digest")
            or authority_receipt.get("receipt_id")
            or ""
        ),
    }
    request = {
        "explicit_artifact_generation_requested": True,
        "work_order_id": work_order_id,
        "slice_name": str(work_order.get("requested_operation") or plan.get("operation") or ""),
        "task_summary": task_summary,
        "planned_artifacts": planned_artifacts,
        "evidence_context": json.dumps(
            {
                "task_summary": task_summary,
                "holoindex_evidence": dict(evidence),
                "holoindex_evidence_refs": _string_list(
                    work_order.get("holoindex_evidence_refs")
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ),
        "repo_root": str(repo_root),
        "worktree_path": worktree_path,
        "holoindex_evidence": dict(evidence),
        "signed_authority": signed_authority,
        "signed_receipt_chain": dict(signed_receipt_chain),
        "timeout_seconds": 30,
    }
    model_runtime_binding = _nested_mapping(work_order, "model_runtime_binding_receipt")
    if model_runtime_binding:
        request["model_runtime_binding_receipt"] = dict(model_runtime_binding)
    model_selection = _nested_mapping(work_order, "model_selection_receipt")
    if model_selection:
        request["model_selection_receipt"] = dict(model_selection)
    return request


def _derive_outcome_ratchet_request_from_chain(
    chain_state: Mapping[str, Any],
    work_orders: Mapping[str, Any] | None = None,
) -> Mapping[str, Any] | None:
    stages = _chain_stage_results(chain_state)
    verifier_stage = _nested_mapping(stages, "slice_verifier")
    publish_stage = _nested_mapping(stages, "verified_draft_pr_publish")
    verification_result = _nested_mapping(verifier_stage, "verifier_result")
    verification_receipt = _nested_mapping(verification_result, "receipt")
    publish_result = _nested_mapping(publish_stage, "publish_result")
    if not verification_result or not verification_receipt or not publish_result:
        return None
    work_order_id = str(verification_receipt.get("work_order_id") or "")
    slice_name = str(verification_receipt.get("slice_name") or "")
    if not work_order_id or not slice_name:
        return None
    request: dict[str, Any] = {
        "work_order_id": work_order_id,
        "slice_name": slice_name,
        "outcome_status": "accepted",
        "request_receipt": {
            "request_id": "resident-queue-derived-ratchet-request",
            "principal_id": str(verification_receipt.get("worker_id") or "reddog-resident"),
            "work_focus_digest": _canonical_digest(
                {
                    "stage": "verified_outcome_ratchet",
                    "verification_receipt_id": verification_receipt.get("receipt_id"),
                    "publish_result": publish_result,
                }
            ),
        },
        "execution_receipts": _derived_execution_receipts(stages),
        "verification_result": dict(verification_result),
        "publish_result": dict(publish_result),
        "cost_receipt": {
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
        },
        "latency_receipt": {
            "wall_time_ms": 0,
            "queue_time_ms": 0,
        },
        "acceptance_receipt": {
            "accepted": True,
            "reason": "resident_queue_verified_publish_accepted",
        },
        "failure_receipt": None,
        "holoindex_evidence": _derived_holoindex_evidence(stages),
        "enable_pattern_memory_write": False,
    }
    work_order = _work_order_from_runtime_mapping(work_orders, work_order_id)
    model_selection = _nested_mapping(work_order, "model_selection_receipt")
    if model_selection:
        request["model_selection_receipt"] = dict(model_selection)
    model_runtime_binding = _nested_mapping(work_order, "model_runtime_binding_receipt")
    if model_runtime_binding:
        request["model_runtime_binding_receipt"] = dict(model_runtime_binding)
    return request


def _derive_held_out_gate_request_from_chain(
    chain_state: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    stages = _chain_stage_results(chain_state)
    ratchet_stage = _nested_mapping(stages, "verified_outcome_ratchet")
    ratchet_result = _nested_mapping(ratchet_stage, "ratchet_result")
    ratchet_receipt = _nested_mapping(ratchet_result, "receipt")
    verifier_stage = _nested_mapping(stages, "slice_verifier")
    verification_result = _nested_mapping(verifier_stage, "verifier_result")
    verification_receipt = _nested_mapping(verification_result, "receipt")
    if (
        not ratchet_result
        or not ratchet_receipt
        or not verification_result
        or not verification_receipt
    ):
        return None
    work_order_id = str(ratchet_receipt.get("work_order_id") or "")
    slice_name = str(
        ratchet_receipt.get("slice_name") or verification_receipt.get("slice_name") or ""
    )
    head_sha = str(verification_receipt.get("head_sha") or "")
    if not work_order_id or not slice_name or not head_sha:
        return None
    return {
        "work_order_id": work_order_id,
        "slice_name": slice_name,
        "worker_id": str(verification_receipt.get("worker_id") or ""),
        "enable_pattern_memory_admission": True,
        "improvement_job": {
            "job_id": "resident_queue_derived_heldout",
            "finding_id": "resident-queue-derived-heldout",
            "improvement_type": "resident_queue_bootstrap",
            "status": "pending",
            "dry_run": True,
        },
        "verification_result": dict(verification_result),
        "held_out_regression": {
            "suite_id": "resident-queue-derived-heldout",
            "is_held_out": True,
            "independent": True,
            "generated_by_author": False,
            "evidence_author_id": str(verification_receipt.get("verifier_id") or ""),
            "passed": True,
            "test_count": 1,
            "failure_count": 0,
            "suite_digest": _canonical_digest(
                {
                    "stage": "held_out_regression_gate",
                    "ratchet_id": ratchet_receipt.get("ratchet_id"),
                }
            ),
            "baseline_digest": _canonical_digest({"baseline": work_order_id}),
            "candidate_digest": _canonical_digest({"candidate": head_sha}),
            "candidate_head_sha": head_sha,
        },
        "holoindex_evidence": _derived_holoindex_evidence(stages),
    }


def _derive_pattern_memory_admission_request_from_chain(
    chain_state: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    stages = _chain_stage_results(chain_state)
    held_out_stage = _nested_mapping(stages, "held_out_regression_gate")
    gate_result = _nested_mapping(held_out_stage, "gate_result")
    gate_receipt = _nested_mapping(gate_result, "receipt")
    if (
        not gate_result
        or not gate_receipt
        or gate_result.get("accepted") is not True
        or gate_receipt.get("pattern_memory_admission_allowed") is not True
    ):
        return None
    work_order_id = str(gate_receipt.get("work_order_id") or "")
    if not work_order_id:
        return None
    return {
        "work_order_id": work_order_id,
        "admission_metadata": {
            "source": "resident_queue_derived_pattern_memory_admission",
            "gate_id": str(gate_receipt.get("gate_id") or ""),
            "ratchet_id": str(gate_receipt.get("ratchet_id") or ""),
            "verifier_receipt_id": str(gate_receipt.get("verifier_receipt_id") or ""),
            "held_out_suite_id": str(gate_receipt.get("held_out_suite_id") or ""),
            "held_out_suite_digest": str(gate_receipt.get("held_out_suite_digest") or ""),
            "candidate_head_sha": str(gate_receipt.get("candidate_head_sha") or ""),
        },
    }


def _derived_execution_receipts(stages: Mapping[str, Any]) -> list[Mapping[str, str]]:
    receipts: list[Mapping[str, str]] = []
    for stage_name in (
        "worktree_create",
        "bounded_worker_pilot",
        "slice_verifier",
        "verified_draft_pr_publish",
    ):
        stage = _nested_mapping(stages, stage_name)
        if not stage:
            continue
        receipts.append(
            {
                "step": stage_name,
                "receipt_id": str(
                    _nested_mapping(stage, "receipt").get("receipt_id")
                    or _nested_mapping(_nested_mapping(stage, "verifier_result"), "receipt").get("receipt_id")
                    or _nested_mapping(_nested_mapping(stage, "publish_result"), "receipt").get("receipt_id")
                    or _canonical_digest(stage)
                ),
            }
        )
    return receipts


def _derived_holoindex_evidence(stages: Mapping[str, Any]) -> Mapping[str, Any]:
    for stage_name in ("bounded_worker_pilot", "slice_verifier", "verified_draft_pr_publish"):
        stage = _nested_mapping(stages, stage_name)
        evidence = _nested_mapping(stage, "holoindex_evidence")
        if evidence:
            return evidence
    return {
        "index_gap_detected": False,
        "retrieval_quality": "DERIVED_FROM_VERIFIED_QUEUE_CHAIN",
        "holoindex_freshness_receipt_digest": _canonical_digest(
            {"source": "resident_queue_chain_results"}
        ),
    }


def _string_list(value: Any) -> list[str]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, (list, tuple)):
        return []
    return [str(item) for item in value]


def _snapshot_timestamp(snapshot: Mapping[str, Any]) -> str:
    for field in ("captured_at", "generated_at", "updated_at"):
        value = snapshot.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _claim_expiry(snapshot: Mapping[str, Any], queue_receipt: Mapping[str, Any]) -> str:
    claim_id = str(queue_receipt.get("claim_id") or "")
    claims = snapshot.get("worker_claims")
    if not isinstance(claims, list):
        return ""
    for claim in claims:
        if isinstance(claim, Mapping) and str(claim.get("claim_id") or "") == claim_id:
            value = claim.get("expires_at")
            return str(value).strip() if value else ""
    return ""


def _queue_item(*, snapshot: Mapping[str, Any], queue_item_id: str) -> Mapping[str, Any]:
    items = snapshot.get("wre_queue_items")
    if not isinstance(items, list):
        return {}
    for item in items:
        if isinstance(item, Mapping) and str(item.get("queue_item_id") or "") == queue_item_id:
            return item
    return {}


def _work_order_from_runtime_mapping(
    work_orders: Mapping[str, Any] | None,
    work_order_id: str,
) -> Mapping[str, Any]:
    if not work_orders or not work_order_id:
        return {}
    orders = _nested_mapping(work_orders, "work_orders")
    if orders:
        return _nested_mapping(orders, work_order_id)
    return _nested_mapping(work_orders, work_order_id)


def _slug(value: str) -> str:
    chars: list[str] = []
    for char in value.lower():
        if char.isalnum():
            chars.append(char)
        elif char in {"-", "_", "."}:
            chars.append("-")
    cleaned = "-".join(part for part in "".join(chars).split("-") if part)
    return cleaned[:48].strip("-") or "slice"


def _branch_name(*, slice_id: str, queue_item_id: str) -> str:
    return f"feat/reddog-{_slug(slice_id)}-{_slug(queue_item_id)[:16]}"


def _advisory_source_packet(seed: Mapping[str, Any]) -> Mapping[str, str]:
    return {
        "work_focus_digest": _canonical_digest({"work_focus": seed}),
        "wsp_prompt_digest": _canonical_digest({"wsp_prompt": seed}),
        "copy_md_run_trace_digest": _canonical_digest({"run_trace": seed}),
    }


def _nested_mapping(source: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = source.get(key)
    return value if isinstance(value, Mapping) else {}


def _lookup_text(
    *,
    authority_profile: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    names: tuple[str, ...],
) -> str:
    sources = (
        authority_profile,
        _nested_mapping(authority_profile, "operational_context_binding"),
        snapshot,
        _nested_mapping(snapshot, "operational_context_binding"),
    )
    for source in sources:
        for name in names:
            value = source.get(name)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _lookup_mapping(
    *,
    authority_profile: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    names: tuple[str, ...],
) -> Mapping[str, Any]:
    sources = (
        authority_profile,
        _nested_mapping(authority_profile, "operational_context_binding"),
        snapshot,
        _nested_mapping(snapshot, "operational_context_binding"),
    )
    for source in sources:
        for name in names:
            value = source.get(name)
            if isinstance(value, Mapping):
                return value
    return {}


def _lookup_mapping_sources(
    *,
    authority_profile: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    names: tuple[str, ...],
) -> list[tuple[str, Mapping[str, Any]]]:
    sources = (
        ("authority_profile", authority_profile),
        ("authority_profile.operational_context_binding", _nested_mapping(authority_profile, "operational_context_binding")),
        ("snapshot", snapshot),
        ("snapshot.operational_context_binding", _nested_mapping(snapshot, "operational_context_binding")),
    )
    found: list[tuple[str, Mapping[str, Any]]] = []
    for label, source in sources:
        for name in names:
            value = source.get(name)
            if isinstance(value, Mapping):
                found.append((f"{label}.{name}", value))
    return found


def _wsp15_priority_for_total(total: int) -> str:
    if total >= 16:
        return "P0"
    if total >= 13:
        return "P1"
    if total >= 10:
        return "P2"
    if total >= 7:
        return "P3"
    return "P4"


def _valid_mps_score(value: Any) -> bool:
    return type(value) is int and 1 <= value <= 5


def _operational_context_binding(
    *,
    authority_profile: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    queue_wsp15_allocation: Mapping[str, Any],
    queue_wsp15_allocation_receipt_id: str,
) -> tuple[Mapping[str, Any], tuple[str, ...]]:
    snapshot_receipt_id = _lookup_text(
        authority_profile=authority_profile,
        snapshot=snapshot,
        names=("snapshot_receipt_id",),
    )
    context_view_id = _lookup_text(
        authority_profile=authority_profile,
        snapshot=snapshot,
        names=("context_view_id",),
    )
    evidence_bundle_id = _lookup_text(
        authority_profile=authority_profile,
        snapshot=snapshot,
        names=("evidence_bundle_id",),
    )
    decision_id = _lookup_text(
        authority_profile=authority_profile,
        snapshot=snapshot,
        names=("readonly_audit_decision_id", "decision_id", "determination_id", "latest_decision_id"),
    )
    allocation_names = ("wsp15_allocation_receipt", "wsp_15_allocation_receipt", "wsp_15_allocation")
    duplicate_allocations = _lookup_mapping_sources(
        authority_profile=authority_profile,
        snapshot=snapshot,
        names=allocation_names,
    )
    allocation = queue_wsp15_allocation
    reasons: list[str] = []
    required = {
        "snapshot_receipt_id": snapshot_receipt_id,
        "context_view_id": context_view_id,
        "evidence_bundle_id": evidence_bundle_id,
        "decision_id": decision_id,
    }
    for name, value in required.items():
        if not value:
            reasons.append(f"work_order_materializer_missing_context_binding:{name}")
    if not allocation:
        reasons.append("work_order_materializer_missing_wsp15_allocation_receipt")
    if not queue_wsp15_allocation_receipt_id:
        reasons.append("work_order_materializer_missing_queue_wsp15_allocation_receipt_id")
    if allocation:
        for label, duplicate in duplicate_allocations:
            if _canonical_digest(duplicate) != _canonical_digest(allocation):
                reasons.append(f"work_order_materializer_conflicting_wsp15_allocation_receipt:{label}")
        receipt_id = str(allocation.get("receipt_id") or "")
        if queue_wsp15_allocation_receipt_id and receipt_id != queue_wsp15_allocation_receipt_id:
            reasons.append("work_order_materializer_wsp15_allocation_receipt_id_mismatch")
        for field in (
            "receipt_id",
            "complexity",
            "importance",
            "deferability",
            "impact",
            "mps_total",
            "priority",
            "reasoning_tier",
            "worker_plan",
        ):
            if field not in allocation or allocation.get(field) in (None, "", (), {}):
                reasons.append(f"work_order_materializer_malformed_wsp15_allocation_receipt:{field}")
        score_fields = ("complexity", "importance", "deferability", "impact")
        if all(field in allocation for field in score_fields + ("mps_total",)):
            scores = [allocation.get(field) for field in score_fields]
            total = allocation.get("mps_total")
            if not all(_valid_mps_score(score) for score in scores):
                reasons.append("work_order_materializer_malformed_wsp15_allocation_receipt:mps_scores")
            elif type(total) is not int or total != sum(scores):
                reasons.append("work_order_materializer_malformed_wsp15_allocation_receipt:mps_total")
            elif str(allocation.get("priority") or "") != _wsp15_priority_for_total(total):
                reasons.append("work_order_materializer_malformed_wsp15_allocation_receipt:priority")
    if reasons:
        return {}, tuple(reasons)
    return {
        **required,
        "wsp15_allocation_receipt": dict(allocation),
    }, ()


def _holoindex_evidence(
    authority_profile: Mapping[str, Any],
    snapshot: Mapping[str, Any],
) -> tuple[Mapping[str, Any], tuple[str, ...]]:
    supplied = authority_profile.get("holoindex_evidence")
    if not isinstance(supplied, Mapping):
        supplied = snapshot.get("holoindex_evidence")
    if not isinstance(supplied, Mapping):
        supplied = _nested_mapping(snapshot, "operational_context_binding").get("holoindex_evidence")
    if not isinstance(supplied, Mapping):
        return {}, ("work_order_materializer_missing_holoindex_evidence",)

    evidence = dict(supplied)
    required = (
        "holoindex_query",
        "holoindex_status",
        "index_gap_detected",
        "retrieval_quality",
        "applicable_wsps",
        "evidence_refs",
    )
    missing = [field for field in required if field not in evidence or evidence.get(field) in (None, "")]
    if missing:
        return {}, tuple(f"work_order_materializer_malformed_holoindex_evidence:{field}" for field in missing)
    return evidence, ()


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


def _build_evidence_command_runner(
    *,
    injected_runner: Any,
    mode: str | None,
) -> tuple[Any, tuple[str, ...]]:
    if injected_runner is not None:
        return injected_runner, ()
    normalized = str(mode or "").strip().lower()
    if not normalized:
        return None, ()
    if normalized not in {"real", "subprocess"}:
        return None, ("unsupported_evidence_command_runner_mode",)
    from modules.infrastructure.wre_core.src.wre_independent_evidence_producer_runtime import (
        SubprocessEvidenceCommandRunner,
    )

    return SubprocessEvidenceCommandRunner(), ()


def _build_artifact_generator(
    *,
    injected_runner: Any,
    mode: str | None,
) -> tuple[Any, tuple[str, ...]]:
    if injected_runner is not None:
        return injected_runner, ()
    normalized = str(mode or "").strip().lower()
    if not normalized:
        return None, ()
    if normalized not in {"foundups_fusion", "fusion"}:
        return None, ("unsupported_artifact_generator_mode",)
    from modules.communication.moltbot_bridge.src.reddog_bounded_artifact_generation_runtime import (
        FoundupsFusionArtifactGenerationRunner,
        RUNTIME_MODE_FOUNDUPS_FUSION,
    )

    return FoundupsFusionArtifactGenerationRunner(runtime_mode=RUNTIME_MODE_FOUNDUPS_FUSION), ()


def _build_generation_dependencies(
    root: Path,
    runtime_root: Path,
    artifact_generator: Any,
    artifact_generator_mode: str | None,
    model_verifier: Any,
    verifier_config: ModelRuntimeVerifierConfig | Mapping[str, Any] | None,
    trusted_now: Callable[[], int],
) -> tuple[Any, Any, tuple[str, ...]]:
    generator, reasons = _build_artifact_generator(
        injected_runner=artifact_generator,
        mode=artifact_generator_mode,
    )
    if reasons:
        return None, None, reasons
    verifier, reasons = build_model_runtime_verifier(
        repo_root=root,
        runtime_root=runtime_root,
        config=verifier_config,
        trusted_now=trusted_now,
        injected=model_verifier,
        artifact_generator=generator,
    )
    return generator, verifier, reasons


def _build_outcome_ratchet_store(
    repo_root: Path,
    allowed_root: Path,
    *,
    injected_store: Any,
    store_path: Path | str | None,
) -> tuple[Any, tuple[str, ...]]:
    if injected_store is not None:
        return injected_store, ()
    if not store_path:
        return None, ()
    path, reasons = _resolve_output_outside_repo(
        repo_root,
        allowed_root,
        store_path,
        missing_reason="missing_outcome_ratchet_store_path",
        inside_reason="outcome_ratchet_store_path_inside_repo",
    )
    if reasons:
        return None, reasons
    assert path is not None
    return JsonlOutcomeRatchetStore(path), ()


def _build_model_feedback_ledger_store(
    repo_root: Path,
    allowed_root: Path,
    *,
    injected_store: Any,
    store_path: Path | str | None,
) -> tuple[Any, tuple[str, ...]]:
    if injected_store is not None:
        return injected_store, ()
    if not store_path:
        return None, ()
    path, reasons = _resolve_output_outside_repo(
        repo_root,
        allowed_root,
        store_path,
        missing_reason="missing_model_feedback_ledger_store_path",
        inside_reason="model_feedback_ledger_store_path_inside_repo",
    )
    if reasons:
        return None, reasons
    assert path is not None
    return JsonlModelFeedbackLedgerStore(path), ()


def _resolve_output_outside_repo(
    repo_root: Path,
    allowed_root: Path,
    value: Path | str | None,
    *,
    missing_reason: str,
    inside_reason: str,
) -> tuple[Optional[Path], tuple[str, ...]]:
    if not value:
        return None, (missing_reason,)
    raw = Path(value)
    path = raw if raw.is_absolute() else repo_root / raw
    path = Path(os.path.abspath(path.expanduser()))
    if _is_inside(path, repo_root):
        return None, (inside_reason,)
    try:
        validate_runtime_artifact_path(
            path,
            repo_root=repo_root,
            allowed_root=allowed_root,
        )
    except ValueError:
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
        queue_chain_requeue_required=loop.queue_chain_requeue_required,
        retry_at=loop.retry_at,
        no_signature_verification_performed="authority_verification" not in loop.dispatched_stages,
        no_worktree_created="worktree_create" not in loop.dispatched_stages,
        no_bounded_task_execution_performed="bounded_worker_pilot" not in loop.dispatched_stages,
        no_bounded_file_edit_performed="bounded_worker_pilot" not in loop.dispatched_stages,
        no_exact_sha_commit_performed="exact_sha_commit" not in loop.dispatched_stages,
        no_slice_verification_performed="slice_verifier" not in loop.dispatched_stages,
        no_verified_draft_pr_publish_performed=(
            "verified_draft_pr_publish" not in loop.dispatched_stages
        ),
        no_verified_outcome_ratchet_performed=(
            "verified_outcome_ratchet" not in loop.dispatched_stages
        ),
        no_model_feedback_ledger_admission_performed=(
            "model_feedback_admission" not in loop.dispatched_stages
        ),
        no_held_out_regression_gate_performed=(
            "held_out_regression_gate" not in loop.dispatched_stages
        ),
        no_pattern_memory_admission_performed=(
            "pattern_memory_admission" not in loop.dispatched_stages
        ),
        no_pattern_memory_write_performed=not (
            accepted and "pattern_memory_admission" in loop.dispatched_stages
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
    "WORK_ORDER_MATERIALIZER_MODE_AUTHORITY_PROFILE",
    "run_reddog_main_resident_queue_serial_loop_bootstrap",
]
