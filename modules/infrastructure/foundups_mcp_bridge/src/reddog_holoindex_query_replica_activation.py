"""Governed exact-HEAD activation of one immutable HoloIndex query replica."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from holo_index.authority_worktree import select_holoindex_workspace_authority
from holo_index.repository_state import read_repository_state
from holo_index.storage_contract import HOLOINDEX_SSD_PATH_ENV

from scripts.reddog_holoindex_owner_query_once import query_once

from .reddog_holoindex_acceptance_guards import create_isolated_store
from .reddog_holoindex_candidate_query_validation import (
    CandidateAcceptanceError,
    validate_activation_query,
)
from .reddog_holoindex_maintenance_handshake import (
    ensure_reddog_holoindex_current,
)
from .reddog_holoindex_owner_bootstrap import cleanup_reddog_holoindex_owner
from .reddog_holoindex_owner_replica_route import (
    QUERY_REPLICA_ROUTE_FILE_ENV,
    build_query_replica_owner_route,
    resolve_query_replica_owner_route,
)
from .reddog_holoindex_query_replica import materialize_query_replica
from .reddog_holoindex_query_replica_activation_contract import (
    ACTIVATION_QUERY,
    ACTIVATION_RECEIPT_MAX_BYTES,
    ACTIVATION_SCHEMA_VERSION,
    QueryReplicaActivationConfig,
    QueryReplicaActivationResult,
    build_candidate_route_record,
    fail_activation,
    stable_activation_error,
    validate_activation_config,
)
from .reddog_holoindex_query_replica_plan import (
    build_query_replica_activation_plan,
)
from .reddog_holoindex_query_route_store import QueryRouteStore
from .reddog_private_json_publication import (
    atomic_publish_private_json_proven,
    verify_proven_private_json,
)


_POSTCOMMIT_QUERY_ATTEMPTS = 2


@dataclass
class QueryReplicaActivationDependencies:
    read_state: Callable[..., Any] = read_repository_state
    cleanup_owner: Callable[..., Any] = cleanup_reddog_holoindex_owner
    ensure_current: Callable[..., Any] = ensure_reddog_holoindex_current
    build_plan: Callable[..., Any] = build_query_replica_activation_plan
    create_store: Callable[..., Any] = create_isolated_store
    materialize: Callable[..., Any] = materialize_query_replica
    build_owner_route: Callable[..., Any] = build_query_replica_owner_route
    query: Callable[..., Mapping[str, Any]] = query_once
    select_authority: Callable[..., Any] = select_holoindex_workspace_authority
    publish: Callable[..., Any] = atomic_publish_private_json_proven
    verify_publication: Callable[..., bool] = verify_proven_private_json
    now: Callable[[], datetime] = field(
        default_factory=lambda: lambda: datetime.now(timezone.utc)
    )


@dataclass
class _ActivationEvidence:
    previous_revision: int = 0
    previous_route_digest: str = ""
    activation_id: str = ""
    committed_revision: int = 0
    committed_route_digest: str = ""
    repo_root_digest: str = ""
    generation_id: str = ""
    freshness_receipt_digest: str = ""
    descriptor_digest: str = ""
    replica_id: str = ""
    path_identity_digest: str = ""
    artifact_count: int = 0
    artifact_bytes: int = 0
    candidate_query_receipt_id: str = ""
    normal_query_receipt_id: str = ""
    route_committed: bool = False
    post_query_replica_unchanged: bool = False
    recovered_committed_route: bool = False


def _store(config: QueryReplicaActivationConfig) -> QueryRouteStore:
    return QueryRouteStore(
        config.route_path,
        runtime_root=config.route_runtime_root,
        canonical_store=config.canonical_store,
        repo_roots=(config.repo_root,),
        lock_timeout_seconds=min(config.timeout_seconds, 300.0),
    )


def _prove_exact_repository(
    config: QueryReplicaActivationConfig,
    dependencies: QueryReplicaActivationDependencies,
) -> None:
    state = dependencies.read_state(config.repo_root)
    if (
        getattr(state, "proven_clean", False) is not True
        or getattr(state, "head_sha", "") != config.expected_repo_head_sha
    ):
        fail_activation("ACTIVATION_REPOSITORY_STATE_INVALID")


def _require_new_receipt(config: QueryReplicaActivationConfig) -> None:
    try:
        os.lstat(config.receipt_path)
    except FileNotFoundError:
        return
    except OSError:
        fail_activation("ACTIVATION_RECEIPT_TARGET_UNAVAILABLE")
    fail_activation("ACTIVATION_RECEIPT_EXISTS")


def _maintenance_environment(config: QueryReplicaActivationConfig) -> dict[str, str]:
    environment = dict(os.environ)
    environment[HOLOINDEX_SSD_PATH_ENV] = str(config.canonical_store)
    environment.pop("HOLOINDEX_QUERY_SERVICE_URL", None)
    environment.pop("HOLOINDEX_QUERY_SERVICE_TOKEN", None)
    return environment


def _ensure_current_generation(
    config: QueryReplicaActivationConfig,
    dependencies: QueryReplicaActivationDependencies,
) -> Any:
    dependencies.cleanup_owner()
    current = dependencies.ensure_current(
        repo_root=config.repo_root,
        owner_runtime_root=config.owner_runtime_root,
        requested=True,
        auto_maintenance=True,
        timeout_seconds=config.timeout_seconds,
        environ=_maintenance_environment(config),
    )
    if (
        getattr(current, "ready", False) is not True
        or getattr(current, "repo_head_sha", "") != config.expected_repo_head_sha
    ):
        fail_activation(
            str(getattr(current, "error", "") or "ACTIVATION_MAINTENANCE_FAILED")
        )
    return current


def _materialize_candidate(
    config: QueryReplicaActivationConfig,
    dependencies: QueryReplicaActivationDependencies,
) -> tuple[Any, Any]:
    plan = dependencies.build_plan(
        canonical_repo_root=config.repo_root,
        canonical_store=config.canonical_store,
        expected_repo_head_sha=config.expected_repo_head_sha,
    )
    proof = dependencies.create_store(
        config.replica_root,
        canonical_store=config.canonical_store,
        repo_roots=(config.repo_root,),
    )
    result = dependencies.materialize(
        canonical_store=config.canonical_store,
        replica_root_proof=proof,
        binding=plan.binding,
        manifests=plan.manifests,
    )
    route = dependencies.build_owner_route(
        canonical_repo_root=config.repo_root,
        canonical_ssd_path=config.canonical_store,
        replica_root_proof=proof,
    )
    binding = route.binding
    if (
        result.active_descriptor != binding.descriptor_path
        or result.descriptor_digest != binding.descriptor_digest
        or result.generation_directory != binding.generation_directory
        or result.file_count != len(binding.artifacts)
        or result.total_bytes != sum(item.size for item in binding.artifacts)
    ):
        fail_activation("ACTIVATION_MATERIALIZATION_BINDING_MISMATCH")
    return route, result


def _run_query(
    config: QueryReplicaActivationConfig,
    dependencies: QueryReplicaActivationDependencies,
    route: Any,
    *,
    stable_route: bool,
) -> str:
    if stable_route:
        resolver = lambda **kwargs: _resolve_stable_route(
            config,
            **kwargs,
        )
    else:
        resolver = lambda **_kwargs: route
    result = dependencies.query(
        {"query": ACTIVATION_QUERY, "limit": 5},
        repo_root=config.repo_root,
        select_authority=dependencies.select_authority,
        select_runtime_root=lambda _root: config.owner_runtime_root,
        resolve_ssd_path=lambda: config.canonical_store,
        resolve_replica_route=resolver,
        operation_timeout_seconds=min(config.timeout_seconds, 60.0),
    )
    binding = route.binding
    return validate_activation_query(
        result,
        expected_query=ACTIVATION_QUERY,
        expected_sha=binding.canonical_repo_head_sha,
        expected_root_digest=binding.canonical_repo_root_digest,
        generation_id=binding.generation_id,
        receipt_digest=binding.canonical_receipt_digest,
        expected_replica_binding=binding.public_binding,
    )


def _resolve_stable_route(
    config: QueryReplicaActivationConfig,
    *,
    canonical_repo_root: Any,
    canonical_ssd_path: Any,
    environment: Mapping[str, str] | None = None,
) -> Any:
    """Resolve only the committed route, superseding caller route inputs."""

    del environment
    return resolve_query_replica_owner_route(
        canonical_repo_root=canonical_repo_root,
        canonical_ssd_path=canonical_ssd_path,
        environment={QUERY_REPLICA_ROUTE_FILE_ENV: str(config.route_path)},
    )


def _run_postcommit_query(
    config: QueryReplicaActivationConfig,
    dependencies: QueryReplicaActivationDependencies,
    route: Any,
) -> str:
    """Retry one failed proof after commit; every attempt remains read-only."""

    last_error: CandidateAcceptanceError | None = None
    for _attempt in range(_POSTCOMMIT_QUERY_ATTEMPTS):
        try:
            return _run_query(config, dependencies, route, stable_route=True)
        except CandidateAcceptanceError as exc:
            last_error = exc
    if last_error is None:  # Defensive: the attempt constant is module-owned.
        fail_activation("ACTIVATION_QUERY_PROOF_INVALID")
    raise last_error


def _revalidate(route: Any) -> None:
    observed = route.revalidate()
    if observed != route.binding:
        fail_activation("ACTIVATION_REPLICA_CHANGED")


def _receipt_payload(
    config: QueryReplicaActivationConfig,
    evidence: _ActivationEvidence,
    *,
    verdict: str,
    error: str,
) -> dict[str, object]:
    return {
        "schema_version": ACTIVATION_SCHEMA_VERSION,
        "verdict": verdict,
        "error": error,
        "repo_head_sha": config.expected_repo_head_sha,
        "repo_root_digest": evidence.repo_root_digest,
        "generation_id": evidence.generation_id,
        "freshness_receipt_digest": evidence.freshness_receipt_digest,
        "activation_id": evidence.activation_id,
        "previous_route_revision": evidence.previous_revision,
        "previous_route_digest": evidence.previous_route_digest,
        "committed_route_revision": evidence.committed_revision,
        "committed_route_digest": evidence.committed_route_digest,
        "query_replica_descriptor_digest": evidence.descriptor_digest,
        "query_replica_id": evidence.replica_id,
        "query_replica_path_identity_digest": evidence.path_identity_digest,
        "artifact_count": evidence.artifact_count,
        "artifact_bytes": evidence.artifact_bytes,
        "candidate_query_receipt_id": evidence.candidate_query_receipt_id,
        "normal_query_receipt_id": evidence.normal_query_receipt_id,
        "route_committed": evidence.route_committed,
        "post_query_replica_unchanged": evidence.post_query_replica_unchanged,
        "recovered_committed_route": evidence.recovered_committed_route,
    }


def _publish_receipt(
    config: QueryReplicaActivationConfig,
    dependencies: QueryReplicaActivationDependencies,
    evidence: _ActivationEvidence,
    *,
    verdict: str,
    error: str,
) -> str:
    payload = _receipt_payload(config, evidence, verdict=verdict, error=error)
    proof = dependencies.publish(
        config.receipt_path,
        payload,
        allowed_root=config.route_runtime_root,
        canonical_store=config.canonical_store,
        repo_roots=(config.repo_root,),
        max_bytes=ACTIVATION_RECEIPT_MAX_BYTES,
        expected_schema=ACTIVATION_SCHEMA_VERSION,
        reject_absolute_paths=True,
    )
    if not dependencies.verify_publication(
        proof,
        expected_payload=payload,
        max_bytes=ACTIVATION_RECEIPT_MAX_BYTES,
        expected_schema=ACTIVATION_SCHEMA_VERSION,
    ):
        fail_activation("ACTIVATION_RECEIPT_PROOF_INVALID")
    return str(proof.digest)


def _record_binding(
    evidence: _ActivationEvidence,
    route: Any,
    *,
    artifact_count: int,
    artifact_bytes: int,
) -> None:
    binding = route.binding
    evidence.repo_root_digest = binding.canonical_repo_root_digest
    evidence.generation_id = binding.generation_id
    evidence.freshness_receipt_digest = binding.canonical_receipt_digest
    evidence.descriptor_digest = binding.descriptor_digest
    evidence.replica_id = binding.replica_id
    evidence.path_identity_digest = binding.path_identity_digest
    evidence.artifact_count = artifact_count
    evidence.artifact_bytes = artifact_bytes


def _recover_committed_route(
    config: QueryReplicaActivationConfig,
    dependencies: QueryReplicaActivationDependencies,
    selected: Any,
    evidence: _ActivationEvidence,
) -> bool:
    record = selected.record
    if record.status != "CURRENT" or record.replica_root != str(config.replica_root):
        return False
    if (
        record.authority_repo_root != str(config.repo_root)
        or record.canonical.get("repo_head_sha") != config.expected_repo_head_sha
    ):
        fail_activation("ACTIVATION_EXISTING_TARGET_CONFLICT")
    route = resolve_query_replica_owner_route(
        canonical_repo_root=config.repo_root,
        canonical_ssd_path=config.canonical_store,
        environment={QUERY_REPLICA_ROUTE_FILE_ENV: str(config.route_path)},
    )
    binding = route.binding
    _record_binding(
        evidence,
        route,
        artifact_count=len(binding.artifacts),
        artifact_bytes=sum(item.size for item in binding.artifacts),
    )
    evidence.previous_revision = record.revision - 1
    evidence.previous_route_digest = record.previous_route_digest
    evidence.activation_id = record.activation_id
    evidence.committed_revision = record.revision
    evidence.committed_route_digest = selected.digest
    evidence.route_committed = True
    evidence.recovered_committed_route = True
    evidence.normal_query_receipt_id = _run_postcommit_query(
        config, dependencies, route
    )
    _revalidate(route)
    evidence.post_query_replica_unchanged = True
    return True


def _activate_route(
    config: QueryReplicaActivationConfig,
    dependencies: QueryReplicaActivationDependencies,
    store: QueryRouteStore,
    previous: Any,
    route: Any,
    evidence: _ActivationEvidence,
) -> Any:
    _prove_exact_repository(config, dependencies)
    candidate = build_candidate_route_record(
        previous, route, now=dependencies.now()
    )
    evidence.activation_id = candidate.activation_id
    with store.transition(
        candidate,
        expected_revision=previous.record.revision,
        expected_route_digest=previous.digest,
    ) as transition:
        evidence.candidate_query_receipt_id = _run_query(
            config, dependencies, route, stable_route=False
        )
        _revalidate(route)
        _prove_exact_repository(config, dependencies)
        transition.commit()
    evidence.route_committed = transition.committed
    if not evidence.route_committed:
        fail_activation("ACTIVATION_COMMIT_UNPROVEN")
    committed = store.load_readonly()
    if committed.record != candidate:
        fail_activation("ACTIVATION_COMMITTED_ROUTE_MISMATCH")
    evidence.committed_revision = committed.record.revision
    evidence.committed_route_digest = committed.digest
    return committed


def _execute_activation(
    config: QueryReplicaActivationConfig,
    dependencies: QueryReplicaActivationDependencies,
    evidence: _ActivationEvidence,
) -> None:
    _prove_exact_repository(config, dependencies)
    store = _store(config)
    previous = store.initialize_empty()
    evidence.previous_revision = previous.record.revision
    evidence.previous_route_digest = previous.digest
    if _recover_committed_route(config, dependencies, previous, evidence):
        return
    _ensure_current_generation(config, dependencies)
    _prove_exact_repository(config, dependencies)
    route, result = _materialize_candidate(config, dependencies)
    _record_binding(
        evidence,
        route,
        artifact_count=result.file_count,
        artifact_bytes=result.total_bytes,
    )
    _activate_route(config, dependencies, store, previous, route, evidence)
    evidence.normal_query_receipt_id = _run_postcommit_query(
        config, dependencies, route
    )
    _revalidate(route)
    evidence.post_query_replica_unchanged = True


def _activation_outcome(
    config: QueryReplicaActivationConfig,
    dependencies: QueryReplicaActivationDependencies,
    evidence: _ActivationEvidence,
) -> tuple[str, str, BaseException | None]:
    try:
        _execute_activation(config, dependencies, evidence)
        return "PASS", "", None
    except Exception as exc:
        verdict = "COMMITTED_UNVERIFIED" if evidence.route_committed else "FAILED"
        return verdict, stable_activation_error(exc), None
    except BaseException as exc:
        verdict = "COMMITTED_UNVERIFIED" if evidence.route_committed else "FAILED"
        return verdict, "ACTIVATION_INTERRUPTED", exc


def _publish_outcome(
    config: QueryReplicaActivationConfig,
    dependencies: QueryReplicaActivationDependencies,
    evidence: _ActivationEvidence,
    outcome: tuple[str, str, BaseException | None],
) -> QueryReplicaActivationResult:
    verdict, error, pending = outcome
    try:
        receipt_digest = _publish_receipt(
            config, dependencies, evidence, verdict=verdict, error=error
        )
    except Exception:
        if pending is not None:
            raise pending
        return QueryReplicaActivationResult(
            False,
            "COMMITTED_UNVERIFIED" if evidence.route_committed else "FAILED",
            "ACTIVATION_RECEIPT_PUBLICATION_FAILED",
            route_committed=evidence.route_committed,
            post_query_replica_unchanged=evidence.post_query_replica_unchanged,
        )
    except BaseException as exc:
        if pending is not None:
            pending.add_note("ACTIVATION_RECEIPT_PUBLICATION_INTERRUPTED")
            raise pending from exc
        raise
    if pending is not None:
        raise pending
    return QueryReplicaActivationResult(
        verdict == "PASS",
        verdict,
        error,
        receipt_digest,
        evidence.route_committed,
        evidence.post_query_replica_unchanged,
    )


def activate_query_replica(
    config: QueryReplicaActivationConfig,
    *,
    dependencies: QueryReplicaActivationDependencies | None = None,
) -> QueryReplicaActivationResult:
    """Execute one real activation or return an inert bounded result."""

    try:
        validated = validate_activation_config(config)
    except Exception as exc:
        return QueryReplicaActivationResult(
            False, "FAILED", stable_activation_error(exc)
        )
    if validated.real is not True:
        return QueryReplicaActivationResult(False, "NOT_REQUESTED")
    deps = dependencies or QueryReplicaActivationDependencies()
    try:
        _prove_exact_repository(validated, deps)
        _require_new_receipt(validated)
    except Exception as exc:
        return QueryReplicaActivationResult(
            False, "FAILED", stable_activation_error(exc)
        )
    evidence = _ActivationEvidence()
    return _publish_outcome(
        validated,
        deps,
        evidence,
        _activation_outcome(validated, deps, evidence),
    )


__all__ = [
    "QueryReplicaActivationDependencies",
    "activate_query_replica",
]
