"""Materialize one inert content-addressed Holo dependency-runtime tree."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)

from .reddog_holoindex_acceptance_guards import (
    AcceptanceGuardError,
    StoreProof,
    atomic_publish_private_json_proven,
    create_isolated_store,
    prove_existing_isolated_store,
    verify_proven_private_json,
    verify_store_proof,
)
from .reddog_holoindex_dependency_runtime_contract import (
    DESCRIPTOR_NAME,
    DESCRIPTOR_SCHEMA_VERSION,
    INVENTORY_NAME,
    INVENTORY_SCHEMA_VERSION,
    SITE_PACKAGES_DIRECTORY,
    DependencyRuntimeContractError,
    DependencyRuntimeLimits,
    DependencyRuntimeMaterializationResult,
)
from .reddog_holoindex_dependency_runtime_copy import (
    DependencyRuntimeSourcePlan,
    copy_dependency_runtime_snapshot,
    plan_dependency_runtime_snapshot,
)
from .reddog_holoindex_dependency_runtime_descriptor import (
    DependencyRuntimeDescriptorError,
    verify_dependency_runtime_generation,
    verify_dependency_runtime_staging,
)
from .reddog_holoindex_query_replica_generation import (
    QueryReplicaGenerationError,
    publish_directory_no_replace,
)
from .reddog_holoindex_query_replica_orphans import (
    OwnedDirectoryProof,
    owned_directory,
    quarantine_owned_staging,
)


class DependencyRuntimeMaterializationError(RuntimeError):
    """Stable inert-generation materialization error."""


def _fail(code: str) -> None:
    raise DependencyRuntimeMaterializationError(code)


def _after_contracts_noop(_staging: Path) -> None:
    """Trusted no-op seam for unpublished-staging falsification."""


@dataclass(frozen=True)
class _MaterializerDependencies:
    plan_tree: Callable[..., DependencyRuntimeSourcePlan] = plan_dependency_runtime_snapshot
    copy_tree: Callable[..., Any] = copy_dependency_runtime_snapshot
    publish_json: Callable[..., Any] = atomic_publish_private_json_proven
    publish_directory: Callable[[Path, Path], None] = publish_directory_no_replace
    after_contracts: Callable[[Path], None] = _after_contracts_noop
    token: Callable[[], str] = lambda: secrets.token_hex(16)


@dataclass(frozen=True)
class _MaterializationRequest:
    source: Path
    runtime_store: Path
    store_proof: StoreProof
    orphan_root: Path
    plan: DependencyRuntimeSourcePlan


@dataclass(frozen=True)
class _StagingState:
    path: Path
    proof: StoreProof
    identity: OwnedDirectoryProof
    token: str


def _absolute(value: Path | str, code: str) -> Path:
    raw = str(value or "")
    if not raw or "\x00" in raw or not Path(raw).is_absolute():
        _fail(code)
    return Path(os.path.abspath(raw))


def _runtime_store(
    path: Path, *, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
) -> StoreProof:
    try:
        return prove_existing_isolated_store(
            path, canonical_store=canonical_store, repo_roots=repo_roots
        )
    except (AcceptanceGuardError, OSError):
        try:
            return create_isolated_store(
                path, canonical_store=canonical_store, repo_roots=repo_roots
            )
        except AcceptanceGuardError:
            return prove_existing_isolated_store(
                path, canonical_store=canonical_store, repo_roots=repo_roots
            )


def _prepare_request(
    *, source_site_packages: Path | str, runtime_store_root: Path | str,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: DependencyRuntimeLimits, dependencies: _MaterializerDependencies,
    expected_store: StoreProof | None = None,
) -> _MaterializationRequest:
    limits.validate()
    source = _absolute(source_site_packages, "DEPENDENCY_RUNTIME_SOURCE_PATH_INVALID")
    runtime = _absolute(runtime_store_root, "DEPENDENCY_RUNTIME_STORE_PATH_INVALID")
    store = expected_store or _runtime_store(
        runtime, canonical_store=canonical_store, repo_roots=repo_roots
    )
    if os.path.normcase(str(store.path)) != os.path.normcase(str(runtime)):
        _fail("DEPENDENCY_RUNTIME_STORE_IDENTITY_CHANGED")
    verify_store_proof(store, canonical_store=canonical_store, repo_roots=repo_roots)
    plan = dependencies.plan_tree(source, limits=limits)
    if plan.source_root != source:
        _fail("DEPENDENCY_RUNTIME_SOURCE_PLAN_MISMATCH")
    return _MaterializationRequest(
        source, runtime, store, runtime / ".dependency-runtime-orphans", plan
    )


def _entry_exists(path: Path) -> bool:
    try:
        os.lstat(path)
        return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise DependencyRuntimeMaterializationError(
            "DEPENDENCY_RUNTIME_GENERATION_LOOKUP_FAILED"
        ) from exc


def _generation_target(request: _MaterializationRequest) -> Path:
    return request.runtime_store / request.plan.generation_id.removeprefix("sha256:")


def _verify_source_unchanged(
    request: _MaterializationRequest, limits: DependencyRuntimeLimits,
    dependencies: _MaterializerDependencies,
) -> None:
    observed = dependencies.plan_tree(request.source, limits=limits)
    if observed != request.plan:
        _fail("DEPENDENCY_RUNTIME_SOURCE_CHANGED")


def _verify_existing(
    request: _MaterializationRequest, target: Path,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: DependencyRuntimeLimits, dependencies: _MaterializerDependencies,
) -> DependencyRuntimeMaterializationResult:
    binding = verify_dependency_runtime_generation(
        runtime_store_root=request.runtime_store, generation_root=target,
        expected_generation_id=request.plan.generation_id,
        canonical_store=canonical_store, repo_roots=repo_roots, limits=limits,
    )
    if binding.generation_id != request.plan.generation_id:
        _fail("DEPENDENCY_RUNTIME_GENERATION_REUSE_MISMATCH")
    _verify_source_unchanged(request, limits, dependencies)
    return DependencyRuntimeMaterializationResult(binding, True)


def _create_staging(
    request: _MaterializationRequest, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...], dependencies: _MaterializerDependencies,
) -> _StagingState:
    token = dependencies.token()
    staging = request.runtime_store / f".dependency-runtime-stage-{token}"
    proof = create_isolated_store(
        staging, canonical_store=canonical_store, repo_roots=repo_roots
    )
    return _StagingState(staging, proof, owned_directory(staging), token)


def _inventory(
    copy_proof: Any, plan: DependencyRuntimeSourcePlan,
) -> dict[str, Any]:
    rows = [
        {"path": item.relative_path, "size": item.size,
         "sha256": item.destination_sha256, "role": "dependency_payload"}
        for item in copy_proof.files
    ]
    if (
        len(rows) != copy_proof.file_count
        or sum(row["size"] for row in rows) != copy_proof.total_bytes
    ):
        _fail("DEPENDENCY_RUNTIME_COPY_PROOF_INVALID")
    return {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "directories": list(plan.directories), "files": rows,
    }


def _descriptor(
    copy_proof: Any, inventory_proof: Any, plan: DependencyRuntimeSourcePlan,
) -> dict[str, Any]:
    return {
        "schema_version": DESCRIPTOR_SCHEMA_VERSION, "status": "INERT",
        "generation_id": copy_proof.destination_digest,
        "inventory_file": INVENTORY_NAME,
        "inventory_digest": inventory_proof.digest,
        "inventory_bytes": inventory_proof.size,
        "dependency_tree_digest": copy_proof.destination_digest,
        "file_count": copy_proof.file_count, "total_bytes": copy_proof.total_bytes,
        "directory_count": len(plan.directories),
        "site_packages_directory": SITE_PACKAGES_DIRECTORY,
        "artifact_bytes_verified_at_publication": True,
        "write_denial_verified": False, "activation_eligible": False,
    }


def _publish_one_json(
    *, path: Path, payload: dict[str, Any], schema: str, max_bytes: int,
    staging: Path, orphan_root: Path, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...], dependencies: _MaterializerDependencies,
) -> Any:
    proof = dependencies.publish_json(
        path, payload, allowed_root=staging, canonical_store=canonical_store,
        repo_roots=repo_roots, max_bytes=max_bytes, expected_schema=schema,
        reject_absolute_paths=True, orphan_root=orphan_root,
    )
    if not verify_proven_private_json(
        proof, expected_payload=payload, max_bytes=max_bytes,
        expected_schema=schema,
    ):
        _fail("DEPENDENCY_RUNTIME_CONTRACT_PUBLICATION_INVALID")
    return proof


def _publish_contracts(
    *, staging: Path, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...], copy_proof: Any,
    limits: DependencyRuntimeLimits, dependencies: _MaterializerDependencies,
    plan: DependencyRuntimeSourcePlan,
) -> None:
    orphan_root = staging / ".dependency-runtime-publication-orphans"
    inventory = _inventory(copy_proof, plan)
    inventory_proof = _publish_one_json(
        path=staging / INVENTORY_NAME, payload=inventory,
        schema=INVENTORY_SCHEMA_VERSION, max_bytes=limits.max_inventory_bytes,
        staging=staging, orphan_root=orphan_root,
        canonical_store=canonical_store, repo_roots=repo_roots,
        dependencies=dependencies,
    )
    descriptor = _descriptor(copy_proof, inventory_proof, plan)
    _publish_one_json(
        path=staging / DESCRIPTOR_NAME, payload=descriptor,
        schema=DESCRIPTOR_SCHEMA_VERSION, max_bytes=limits.max_descriptor_bytes,
        staging=staging, orphan_root=orphan_root,
        canonical_store=canonical_store, repo_roots=repo_roots,
        dependencies=dependencies,
    )


def _copy_candidate(
    *, request: _MaterializationRequest, staging: _StagingState,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: DependencyRuntimeLimits, dependencies: _MaterializerDependencies,
) -> Any:
    copied = dependencies.copy_tree(
        request.source, staging.path / SITE_PACKAGES_DIRECTORY,
        store_proof=staging.proof, canonical_store=canonical_store,
        repo_roots=repo_roots, limits=limits, expected_plan=request.plan,
    )
    if copied.destination_digest != request.plan.generation_id:
        _fail("DEPENDENCY_RUNTIME_COPY_PROOF_INVALID")
    return copied


def _verify_staging(
    request: _MaterializationRequest, staging: _StagingState,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: DependencyRuntimeLimits,
) -> None:
    binding = verify_dependency_runtime_staging(
        runtime_store_root=request.runtime_store, staging_root=staging.path,
        expected_generation_id=request.plan.generation_id,
        owned_root=staging.identity, canonical_store=canonical_store,
        repo_roots=repo_roots, limits=limits,
    )
    if binding.generation_id != request.plan.generation_id:
        _fail("DEPENDENCY_RUNTIME_STAGING_BINDING_INVALID")


def _publish_candidate(
    request: _MaterializationRequest, staging: _StagingState,
    dependencies: _MaterializerDependencies,
) -> tuple[Path, bool]:
    target = _generation_target(request)
    try:
        dependencies.publish_directory(staging.path, target)
        published = owned_directory(target)
        if (
            published.device != staging.identity.device
            or published.inode != staging.identity.inode
        ):
            _fail("DEPENDENCY_RUNTIME_PUBLICATION_IDENTITY_CHANGED")
        return target, False
    except QueryReplicaGenerationError as exc:
        if str(exc) != "QUERY_REPLICA_GENERATION_EXISTS":
            raise
        return target, True


def _quarantine(
    proof: OwnedDirectoryProof, *, request: _MaterializationRequest, token: str,
) -> None:
    quarantine_owned_staging(
        proof, allowed_root=request.runtime_store,
        orphan_root=request.orphan_root, token=token,
    )


def _materialize_new(
    *, request: _MaterializationRequest, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...], limits: DependencyRuntimeLimits,
    dependencies: _MaterializerDependencies,
) -> DependencyRuntimeMaterializationResult:
    staging = _create_staging(request, canonical_store, repo_roots, dependencies)
    published_proof: OwnedDirectoryProof | None = None
    try:
        copied = _copy_candidate(
            request=request, staging=staging, canonical_store=canonical_store,
            repo_roots=repo_roots, limits=limits, dependencies=dependencies,
        )
        _publish_contracts(
            staging=staging.path, canonical_store=canonical_store,
            repo_roots=repo_roots, copy_proof=copied, limits=limits,
            dependencies=dependencies, plan=request.plan,
        )
        dependencies.after_contracts(staging.path)
        _verify_staging(request, staging, canonical_store, repo_roots, limits)
        target, reused = _publish_candidate(request, staging, dependencies)
        if reused:
            return _verify_existing(
                request, target, canonical_store, repo_roots, limits, dependencies
            )
        published_proof = OwnedDirectoryProof(
            target, staging.identity.device, staging.identity.inode
        )
        result = _verify_existing(
            request, target, canonical_store, repo_roots, limits, dependencies
        )
        return DependencyRuntimeMaterializationResult(result.binding, False)
    except BaseException:
        if published_proof is not None:
            _quarantine(published_proof, request=request, token=staging.token)
        raise
    finally:
        _quarantine(staging.identity, request=request, token=staging.token)


def _materialize_dependency_runtime_for_test(
    *, source_site_packages: Path | str, runtime_store_root: Path | str,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: DependencyRuntimeLimits = DependencyRuntimeLimits(),
    dependencies: _MaterializerDependencies = _MaterializerDependencies(),
    expected_store: StoreProof | None = None,
) -> DependencyRuntimeMaterializationResult:
    try:
        request = _prepare_request(
            source_site_packages=source_site_packages,
            runtime_store_root=runtime_store_root, canonical_store=canonical_store,
            repo_roots=repo_roots, limits=limits, dependencies=dependencies,
            expected_store=expected_store,
        )
        target = _generation_target(request)
        if _entry_exists(target):
            return _verify_existing(
                request, target, canonical_store, repo_roots, limits, dependencies
            )
        return _materialize_new(
            request=request, canonical_store=canonical_store, repo_roots=repo_roots,
            limits=limits, dependencies=dependencies,
        )
    except DependencyRuntimeMaterializationError:
        raise
    except (
        AcceptanceGuardError, DependencyRuntimeContractError,
        DependencyRuntimeDescriptorError, QueryReplicaGenerationError,
        OSError, TypeError, ValueError,
    ) as exc:
        raise DependencyRuntimeMaterializationError(str(exc)) from exc


def materialize_dependency_runtime(
    *, source_site_packages: Path | str, runtime_store_root: Path | str,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: DependencyRuntimeLimits = DependencyRuntimeLimits(),
) -> DependencyRuntimeMaterializationResult:
    """Create or reprove one inert generation without activating it."""

    try:
        limits.validate()
        runtime = _absolute(
            runtime_store_root, "DEPENDENCY_RUNTIME_STORE_PATH_INVALID"
        )
        store = _runtime_store(
            runtime, canonical_store=canonical_store, repo_roots=repo_roots
        )
        lock_identity = (
            f"reddog-dependency-runtime:{store.device}:{store.inode}"
        )
        with runtime_operation_lock(lock_identity):
            return _materialize_dependency_runtime_for_test(
                source_site_packages=source_site_packages,
                runtime_store_root=runtime,
                canonical_store=canonical_store,
                repo_roots=repo_roots,
                limits=limits,
                expected_store=store,
            )
    except DependencyRuntimeMaterializationError:
        raise
    except (
        AcceptanceGuardError, DependencyRuntimeContractError,
        DependencyRuntimeDescriptorError, QueryReplicaGenerationError,
        OSError, TypeError, ValueError,
    ) as exc:
        raise DependencyRuntimeMaterializationError(str(exc)) from exc


__all__ = ["DependencyRuntimeMaterializationError", "materialize_dependency_runtime"]
