"""Governed isolated acceptance for a RedDog HoloIndex candidate commit.

The default mode is inert.  Real mode must be explicitly selected by the
trusted host and executes one isolated refresh followed by exactly two direct,
generation-bound owner queries.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from holo_index.embedding_space import resolve_sentence_transformer_snapshot
from holo_index.authority_worktree import resolve_holoindex_authority_root
from holo_index.freshness_receipt import freshness_receipt_path
from holo_index.isolated_collection_snapshot_probe import (
    IsolatedSnapshotProbeError,
    STABLE_RUNTIME_ERRORS,
    verify_collection_snapshots_isolated,
)
from holo_index.maintenance_lock import (
    MaintenanceLeaseBusy,
    MaintenanceLockError,
    acquire_maintenance_lease,
)
from holo_index.query_admission import rehydrate_canonical_freshness_proof
from modules.communication.moltbot_bridge.src.reddog_holoindex_owner_query_client import (
    query_holoindex_owner,
)

from .holo_query_service_supervisor import PORT_IN_USE_ERROR, _owner_port_available
from .reddog_holoindex_acceptance_guards import (
    AcceptanceGuardError,
    atomic_publish_acceptance_receipt,
    copy_model_snapshot,
    create_isolated_store,
    read_bounded_digest,
    validate_acceptance_worktrees,
    validate_acceptance_runtime_root,
    verify_store_proof,
)
from .reddog_holoindex_acceptance_receipt_proof import (
    open_freshness_receipt_proof, verify_freshness_receipt_snapshot,
)
from .reddog_holoindex_candidate_acceptance_types import (
    CandidateAcceptanceConfig, CandidateAcceptanceResult,
    CandidateAcceptanceState as _RunState,
)
from .reddog_holoindex_candidate_query_validation import (
    CandidateAcceptanceError,
    K1_ACCEPTANCE_QUERY,
    K12_INCIDENT_QUERY,
    _activation_binding_valid,
    _raise,
    _stable_operational_error,
    _validate_activation_query,
    _validate_operational,
    _validate_query,
    _validate_rehydration,
)
from .reddog_holoindex_candidate_receipt_finalization import (
    SSD_PATH_ENV,
    _check_canonical_receipt,
    _cleanup_owned,
    _cleanup_private_owner,
    _finalize,
    _handoff_digest,
    _receipt_payload,
    _require_no_activation_handoff,
    _restore_environment,
)
from . import reddog_holoindex_maintenance_handshake as maintenance_handshake
from .reddog_holoindex_owner_bootstrap import (
    cleanup_reddog_holoindex_owner,
    resolve_reddog_holoindex_owner_handoff,
)
from scripts.reddog_holoindex_owner_query_once import (
    query_once as supported_owner_query_once,
)


_ACCEPTANCE_SESSION_LOCK = threading.Lock()


def _candidate_self_selection(repo_root: Path) -> Any:
    """Ignore ambient explicit authority during candidate activation."""

    return resolve_holoindex_authority_root(repo_root, environment={})


def _activate_supported_wrapper(
    *, repo_root: Path, query: str, limit: int
) -> Mapping[str, Any]:
    """Exercise the supported extension adapter through candidate selection."""

    return supported_owner_query_once(
        {"query": query, "limit": limit},
        repo_root=repo_root,
        select_authority=_candidate_self_selection,
    )


def _acceptance_session_lock_path(config: "CandidateAcceptanceConfig") -> Path:
    """Return a host-local lock path shared by one canonical-store/port pair."""

    identity = (
        os.path.normcase(os.path.abspath(os.fspath(config.canonical_store)))
        + "\0127.0.0.1\0"
        + str(int(config.port))
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return (
        Path(tempfile.gettempdir())
        / "foundups-reddog-candidate-acceptance-locks"
        / f"{digest}.lock"
    )


def _acquire_acceptance_session_lease(config: "CandidateAcceptanceConfig") -> Any:
    """Acquire the existing non-blocking cross-process lease primitive."""

    return acquire_maintenance_lease(_acceptance_session_lock_path(config))


@dataclass
class CandidateAcceptanceDependencies:
    validate_worktrees: Callable[..., Any] = validate_acceptance_worktrees
    validate_runtime: Callable[..., Any] = validate_acceptance_runtime_root
    create_store: Callable[..., Any] = create_isolated_store
    verify_store: Callable[..., Any] = verify_store_proof
    resolve_model: Callable[..., Any] = resolve_sentence_transformer_snapshot
    copy_model: Callable[..., Any] = copy_model_snapshot
    read_digest: Callable[..., Any] = read_bounded_digest
    port_available: Callable[..., bool] = _owner_port_available
    resolve_handoff: Callable[..., Any] = resolve_reddog_holoindex_owner_handoff
    ensure_operational: Callable[..., Any] = maintenance_handshake.ensure_reddog_holoindex_operational
    query_owner: Callable[..., Mapping[str, Any]] = query_holoindex_owner
    rehydrate: Callable[..., Any] = rehydrate_canonical_freshness_proof
    cleanup_owner: Callable[..., Any] = cleanup_reddog_holoindex_owner
    activate_supported_wrapper: Callable[..., Mapping[str, Any]] = (
        _activate_supported_wrapper
    )
    open_receipt_proof: Callable[..., Any] = open_freshness_receipt_proof
    verify_collection_snapshots: Callable[..., Any] = (
        verify_collection_snapshots_isolated
    )
    publish_receipt: Callable[..., Any] = atomic_publish_acceptance_receipt
    acquire_session_lease: Callable[..., Any] = _acquire_acceptance_session_lease


def _copy_isolated_model(
    config: CandidateAcceptanceConfig,
    dependencies: CandidateAcceptanceDependencies,
    state: _RunState,
    store_proof: Any,
) -> None:
    models_root = config.canonical_store / "models"
    source = dependencies.resolve_model(models_root, config.model_name)
    if source is None:
        _raise("CANONICAL_MODEL_UNAVAILABLE")
    short_name = config.model_name.split("/")[-1]
    copied = dependencies.copy_model(
        source,
        config.isolated_store / "models" / short_name,
        store_proof=store_proof,
        canonical_store=config.canonical_store,
        repo_roots=(config.candidate_root, config.authority_root, config.owner_runtime_root),
        limits=config.model_limits,
    )
    if not copied.source_digest or copied.source_digest != copied.destination_digest:
        _raise("MODEL_DIGEST_MISMATCH")
    state.model_digest = copied.destination_digest
    state.model_files = int(copied.file_count)
    state.model_bytes = int(copied.total_bytes)


def _prepare_isolation(
    config: CandidateAcceptanceConfig,
    dependencies: CandidateAcceptanceDependencies,
    state: _RunState,
) -> Any:
    worktrees = dependencies.validate_worktrees(
        config.candidate_root,
        config.authority_root,
        expected_sha=config.expected_sha,
    )
    state.candidate_digest = worktrees.candidate_root_digest
    state.authority_digest = worktrees.authority_root_digest
    runtime = dependencies.validate_runtime(
        config.candidate_root,
        config.authority_root,
        config.owner_runtime_root,
    )
    state.runtime_digest = runtime.runtime_root_digest
    state.runtime_site_packages = tuple(runtime.site_packages)
    state.runtime_executable_proof = runtime.base_executable_proof
    state.canonical_before = dependencies.read_digest(
        freshness_receipt_path(config.canonical_store),
        allowed_root=config.canonical_store,
        max_bytes=config.max_receipt_bytes,
    )
    store_proof = dependencies.create_store(
        config.isolated_store,
        canonical_store=config.canonical_store,
        repo_roots=(config.candidate_root, config.authority_root, config.owner_runtime_root),
    )
    _copy_isolated_model(config, dependencies, state, store_proof)
    dependencies.verify_store(
        store_proof,
        canonical_store=config.canonical_store,
        repo_roots=(config.candidate_root, config.authority_root, config.owner_runtime_root),
    )
    return store_proof


def _set_isolated_environment(config: CandidateAcceptanceConfig, state: _RunState) -> None:
    state.environment_present = SSD_PATH_ENV in os.environ
    state.environment_value = os.environ.get(SSD_PATH_ENV, "")
    os.environ[SSD_PATH_ENV] = str(config.isolated_store)
    state.environment_changed = True


def _run_queries(
    config: CandidateAcceptanceConfig,
    dependencies: CandidateAcceptanceDependencies,
    state: _RunState,
    store_proof: Any,
) -> None:
    assert state.owned_handoff is not None
    for query, limit in ((K1_ACCEPTANCE_QUERY, 1), (K12_INCIDENT_QUERY, 12)):
        dependencies.verify_store(
            store_proof,
            canonical_store=config.canonical_store,
            repo_roots=(config.candidate_root, config.authority_root, config.owner_runtime_root),
        )
        result = dependencies.query_owner(
            repo_root=config.candidate_root,
            query=query,
            limit=limit,
            service_url=state.owned_handoff[0],
            service_token=state.owned_handoff[1],
            timeout_seconds=config.timeout_seconds,
        )
        _validate_query(
            result,
            expected_sha=config.expected_sha,
            generation_id=state.generation_id,
            receipt_digest=state.receipt_digest,
        )
        state.query_count += 1


def _start_isolated_owner(
    config: CandidateAcceptanceConfig,
    dependencies: CandidateAcceptanceDependencies,
    state: _RunState,
) -> Any:
    operational: Any = None
    startup_failure: BaseException | None = None
    capture_failure: BaseException | None = None
    try:
        operational = dependencies.ensure_operational(
            repo_root=config.candidate_root,
            owner_runtime_root=config.owner_runtime_root,
            requested=True,
            auto_maintenance=True,
            timeout_seconds=config.timeout_seconds,
            environ=dict(os.environ),
        )
    except BaseException as exc:
        startup_failure = exc
    finally:
        try:
            _capture_present_owner_handoff(dependencies, state)
        except BaseException as exc:
            capture_failure = exc
    if startup_failure is not None:
        raise startup_failure
    operational_error = getattr(operational, "error", "")
    if operational_error == PORT_IN_USE_ERROR:
        _raise("OWNER_PORT_NOT_AVAILABLE")
    if _stable_operational_error(operational_error):
        _raise(operational_error)
    if capture_failure is not None:
        raise capture_failure
    _validate_operational(operational, config.expected_sha)
    if state.owned_handoff is None:
        _raise("NEW_PRIVATE_OWNER_HANDOFF_MISSING")
    return operational


def _run_isolated_owner(
    config: CandidateAcceptanceConfig,
    dependencies: CandidateAcceptanceDependencies,
    state: _RunState,
    store_proof: Any,
) -> None:
    if dependencies.resolve_handoff() is not None:
        _raise("OWNER_HANDOFF_ALREADY_PRESENT")
    if dependencies.port_available("127.0.0.1", config.port) is not True:
        _raise("OWNER_PORT_NOT_AVAILABLE")
    dependencies.verify_store(
        store_proof,
        canonical_store=config.canonical_store,
        repo_roots=(config.candidate_root, config.authority_root, config.owner_runtime_root),
    )
    _set_isolated_environment(config, state)
    operational = _start_isolated_owner(config, dependencies, state)
    state.generation_id = operational.generation_id
    state.receipt_digest = operational.freshness_receipt_digest
    _run_queries(config, dependencies, state, store_proof)
    dependencies.verify_store(
        store_proof,
        canonical_store=config.canonical_store,
        repo_roots=(config.candidate_root, config.authority_root, config.owner_runtime_root),
    )


def _capture_present_owner_handoff(
    dependencies: CandidateAcceptanceDependencies,
    state: _RunState,
) -> None:
    """Capture a newly created private handoff when one is present."""

    handoff = dependencies.resolve_handoff()
    if handoff is None:
        return
    if (
        not isinstance(handoff, (tuple, list))
        or len(handoff) != 2
        or not isinstance(handoff[0], str)
        or not isinstance(handoff[1], str)
        or not handoff[0]
        or not handoff[1]
    ):
        _raise("NEW_PRIVATE_OWNER_HANDOFF_INVALID")
    state.owned_handoff = (handoff[0], handoff[1])
    state.owner_session_digest = _handoff_digest(state.owned_handoff)


def _verify_post_activation_semantics(
    config: CandidateAcceptanceConfig,
    dependencies: CandidateAcceptanceDependencies,
    state: _RunState,
) -> None:
    admission = dependencies.rehydrate(
        repo_root=config.candidate_root,
        ssd_path=config.isolated_store,
        expected_repo_head_sha=config.expected_sha,
    )
    _validate_rehydration(
        admission,
        expected_sha=config.expected_sha,
        generation_id=state.generation_id,
        receipt_digest=state.receipt_digest,
    )
    try:
        unchanged = verify_freshness_receipt_snapshot(
            opener=dependencies.open_receipt_proof,
            verifier=dependencies.verify_collection_snapshots,
            path=freshness_receipt_path(config.isolated_store),
            allowed_root=config.isolated_store,
            expected_ssd_path=config.isolated_store,
            expected_repo_root=config.candidate_root,
            expected_repo_head_sha=config.expected_sha,
            expected_generation_id=state.generation_id,
            expected_receipt_digest=state.receipt_digest,
            max_bytes=config.max_receipt_bytes,
            timeout_seconds=config.timeout_seconds,
            runtime_site_packages=state.runtime_site_packages,
            base_executable_proof=state.runtime_executable_proof,
        )
    except IsolatedSnapshotProbeError as exc:
        _raise(exc.code if exc.code in STABLE_RUNTIME_ERRORS else "SEMANTIC_STORE_RECEIPT_INVALID")
    except Exception:
        _raise("SEMANTIC_STORE_RECEIPT_INVALID")
    if not unchanged:
        _raise("SEMANTIC_STORE_PROOF_CHANGED")
    state.semantic_store_proof_unchanged = True


def _run_activation_and_semantic_proof(
    config: CandidateAcceptanceConfig,
    dependencies: CandidateAcceptanceDependencies,
    state: _RunState,
    store_proof: Any,
) -> None:
    dependencies.verify_store(
        store_proof,
        canonical_store=config.canonical_store,
        repo_roots=(config.candidate_root, config.authority_root, config.owner_runtime_root),
    )
    try:
        activation = dependencies.activate_supported_wrapper(
            repo_root=config.candidate_root,
            query=K1_ACCEPTANCE_QUERY,
            limit=1,
        )
    except Exception:
        _raise("ACTIVATION_QUERY_FAILED")
    if not isinstance(activation, Mapping):
        _raise("ACTIVATION_QUERY_PROOF_INVALID")
    state.activation_query_receipt_digest = _validate_activation_query(
        activation,
        expected_sha=config.expected_sha,
        expected_root_digest=state.candidate_digest,
        generation_id=state.generation_id,
        receipt_digest=state.receipt_digest,
    )
    state.activation_query_count = 1
    _require_no_activation_handoff(dependencies)
    dependencies.verify_store(
        store_proof,
        canonical_store=config.canonical_store,
        repo_roots=(config.candidate_root, config.authority_root, config.owner_runtime_root),
    )
    _verify_post_activation_semantics(config, dependencies, state)


def _execute_locked_acceptance(
    config: CandidateAcceptanceConfig,
    dependencies: CandidateAcceptanceDependencies,
) -> CandidateAcceptanceResult:
    state = _RunState()
    pending: BaseException | None = None
    result: CandidateAcceptanceResult
    try:
        store_proof = _prepare_isolation(config, dependencies, state)
        _run_isolated_owner(config, dependencies, state, store_proof)
        _cleanup_private_owner(dependencies, state)
        _run_activation_and_semantic_proof(
            config, dependencies, state, store_proof
        )
    except (AcceptanceGuardError, CandidateAcceptanceError) as exc:
        state.error = str(exc)
    except Exception:
        state.error = "CANDIDATE_ACCEPTANCE_FAILED"
    except BaseException as exc:
        state.error = "CANDIDATE_ACCEPTANCE_INTERRUPTED"
        pending = exc
    finally:
        result, finalization_failure = _finalize(config, dependencies, state)
        if pending is None:
            pending = finalization_failure
    if pending is not None:
        raise pending
    return result


def run_candidate_acceptance(
    config: CandidateAcceptanceConfig,
    *,
    dependencies: CandidateAcceptanceDependencies | None = None,
) -> CandidateAcceptanceResult:
    """Run one explicit isolated acceptance or return an inert default result."""

    if config.real_mode is not True:
        return CandidateAcceptanceResult("NOT_RUN", "REAL_MODE_REQUIRED")
    deps = dependencies or CandidateAcceptanceDependencies()
    if not _ACCEPTANCE_SESSION_LOCK.acquire(blocking=False):
        return CandidateAcceptanceResult(
            "FAIL", "COMPLETED", "ACCEPTANCE_SESSION_BUSY", False
        )
    lease: Any = None
    try:
        try:
            lease = deps.acquire_session_lease(config)
        except MaintenanceLeaseBusy:
            return CandidateAcceptanceResult(
                "FAIL", "COMPLETED", "ACCEPTANCE_SESSION_BUSY", False
            )
        except (MaintenanceLockError, OSError, ValueError, RuntimeError, TypeError):
            return CandidateAcceptanceResult(
                "FAIL", "COMPLETED", "ACCEPTANCE_SESSION_LOCK_FAILED", False
            )
        return _execute_locked_acceptance(config, deps)
    finally:
        try:
            if lease is not None:
                lease.release()
        finally:
            _ACCEPTANCE_SESSION_LOCK.release()


__all__ = [
    "CandidateAcceptanceConfig",
    "CandidateAcceptanceDependencies",
    "CandidateAcceptanceResult",
    "K1_ACCEPTANCE_QUERY",
    "K12_INCIDENT_QUERY",
    "run_candidate_acceptance",
]
