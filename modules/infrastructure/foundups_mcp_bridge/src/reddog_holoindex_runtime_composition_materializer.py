"""Publish one inert descriptor generation for exact Holo runtime components."""

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
from .reddog_holoindex_base_runtime_contract import BaseRuntimeLimits
from .reddog_holoindex_dependency_runtime_contract import DependencyRuntimeLimits
from .reddog_holoindex_query_replica_generation import (
    QueryReplicaGenerationError,
    publish_directory_no_replace,
)
from .reddog_holoindex_query_replica_orphans import (
    OwnedDirectoryProof,
    owned_directory,
    quarantine_owned_staging,
)
from .reddog_holoindex_runtime_composition_contract import (
    DESCRIPTOR_NAME,
    DESCRIPTOR_SCHEMA_VERSION,
    RuntimeCompositionContractError,
    RuntimeCompositionLimits,
    RuntimeCompositionMaterializationResult,
    runtime_composition_descriptor,
)
from .reddog_holoindex_runtime_composition_descriptor import (
    RuntimeCompositionDescriptorError,
    VerifiedRuntimeCompositionComponents,
    verify_runtime_composition_components,
    verify_runtime_composition_generation,
    verify_runtime_composition_staging,
)


class RuntimeCompositionMaterializationError(RuntimeError):
    """Stable inert-composition publication error."""


def _fail(code: str) -> None:
    raise RuntimeCompositionMaterializationError(code)


def _after_descriptor_noop(_staging: Path) -> None:
    """Trusted seam for unpublished-descriptor falsification tests."""


@dataclass(frozen=True)
class _MaterializerDependencies:
    publish_json: Callable[..., Any] = atomic_publish_private_json_proven
    publish_directory: Callable[[Path, Path], None] = publish_directory_no_replace
    after_descriptor: Callable[[Path], None] = _after_descriptor_noop
    token: Callable[[], str] = lambda: secrets.token_hex(16)


@dataclass(frozen=True)
class _MaterializationRequest:
    store: StoreProof
    components: VerifiedRuntimeCompositionComponents
    descriptor: dict[str, Any]
    target: Path
    orphan_root: Path
    base_store: Path
    dependency_store: Path


@dataclass(frozen=True)
class _StagingState:
    path: Path
    proof: StoreProof
    identity: OwnedDirectoryProof
    token: str


def materialize_runtime_composition(
    *,
    composition_store_root: Path | str,
    base_runtime_store_root: Path | str,
    base_generation_root: Path | str,
    dependency_runtime_store_root: Path | str,
    dependency_generation_root: Path | str,
    canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    composition_limits: RuntimeCompositionLimits = RuntimeCompositionLimits(),
    base_limits: BaseRuntimeLimits = BaseRuntimeLimits(),
    dependency_limits: DependencyRuntimeLimits = DependencyRuntimeLimits(),
) -> RuntimeCompositionMaterializationResult:
    """Create or fully reprove one inert composition without copying payloads."""

    try:
        composition_root = _absolute(
            composition_store_root, "RUNTIME_COMPOSITION_STORE_PATH_INVALID"
        )
        _require_disjoint_runtime_stores(
            composition_root,
            Path(base_runtime_store_root),
            Path(dependency_runtime_store_root),
        )
        store = _composition_store(
            composition_root,
            canonical_store=canonical_store,
            repo_roots=repo_roots,
        )
        lock_identity = f"reddog-runtime-composition:{store.device}:{store.inode}"
        with runtime_operation_lock(lock_identity):
            return _materialize_runtime_composition_for_test(
                composition_store_root=store.path,
                base_runtime_store_root=base_runtime_store_root,
                base_generation_root=base_generation_root,
                dependency_runtime_store_root=dependency_runtime_store_root,
                dependency_generation_root=dependency_generation_root,
                canonical_store=canonical_store,
                repo_roots=repo_roots,
                composition_limits=composition_limits,
                base_limits=base_limits,
                dependency_limits=dependency_limits,
                expected_store=store,
            )
    except RuntimeCompositionMaterializationError:
        raise
    except _EXPECTED_ERRORS as exc:
        raise RuntimeCompositionMaterializationError(str(exc)) from exc


def _materialize_runtime_composition_for_test(
    *,
    composition_store_root: Path | str,
    base_runtime_store_root: Path | str,
    base_generation_root: Path | str,
    dependency_runtime_store_root: Path | str,
    dependency_generation_root: Path | str,
    canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    composition_limits: RuntimeCompositionLimits = RuntimeCompositionLimits(),
    base_limits: BaseRuntimeLimits = BaseRuntimeLimits(),
    dependency_limits: DependencyRuntimeLimits = DependencyRuntimeLimits(),
    dependencies: _MaterializerDependencies = _MaterializerDependencies(),
    expected_store: StoreProof | None = None,
) -> RuntimeCompositionMaterializationResult:
    try:
        request = _prepare_request(
            composition_store_root=composition_store_root,
            base_runtime_store_root=base_runtime_store_root,
            base_generation_root=base_generation_root,
            dependency_runtime_store_root=dependency_runtime_store_root,
            dependency_generation_root=dependency_generation_root,
            canonical_store=canonical_store,
            repo_roots=repo_roots,
            composition_limits=composition_limits,
            base_limits=base_limits,
            dependency_limits=dependency_limits,
            expected_store=expected_store,
        )
        return _materialize_prepared(
            request, base_generation_root, dependency_generation_root,
            canonical_store, repo_roots, composition_limits,
            base_limits, dependency_limits, dependencies,
        )
    except RuntimeCompositionMaterializationError:
        raise
    except _EXPECTED_ERRORS as exc:
        raise RuntimeCompositionMaterializationError(str(exc)) from exc


def _prepare_request(
    *,
    composition_store_root: Path | str,
    base_runtime_store_root: Path | str,
    base_generation_root: Path | str,
    dependency_runtime_store_root: Path | str,
    dependency_generation_root: Path | str,
    canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    composition_limits: RuntimeCompositionLimits,
    base_limits: BaseRuntimeLimits,
    dependency_limits: DependencyRuntimeLimits,
    expected_store: StoreProof | None,
) -> _MaterializationRequest:
    composition_limits.validate()
    root = _absolute(composition_store_root, "RUNTIME_COMPOSITION_STORE_PATH_INVALID")
    _require_disjoint_runtime_stores(
        root, Path(base_runtime_store_root), Path(dependency_runtime_store_root)
    )
    store = expected_store or _composition_store(
        root, canonical_store=canonical_store, repo_roots=repo_roots
    )
    if os.path.normcase(str(store.path)) != os.path.normcase(str(root)):
        _fail("RUNTIME_COMPOSITION_STORE_IDENTITY_CHANGED")
    verify_store_proof(store, canonical_store=canonical_store, repo_roots=repo_roots)
    components = verify_runtime_composition_components(
        base_runtime_store_root=base_runtime_store_root,
        base_generation_root=base_generation_root,
        dependency_runtime_store_root=dependency_runtime_store_root,
        dependency_generation_root=dependency_generation_root,
        canonical_store=canonical_store,
        repo_roots=repo_roots,
        base_limits=base_limits,
        dependency_limits=dependency_limits,
    )
    descriptor = _descriptor_for(components)
    target = store.path / str(descriptor["generation_id"])[7:]
    return _MaterializationRequest(
        store=store,
        components=components,
        descriptor=descriptor,
        target=target,
        orphan_root=store.path / ".runtime-composition-orphans",
        base_store=Path(base_runtime_store_root),
        dependency_store=Path(dependency_runtime_store_root),
    )


def _descriptor_for(
    components: VerifiedRuntimeCompositionComponents,
) -> dict[str, Any]:
    return runtime_composition_descriptor(
        base_runtime=components.base_runtime,
        dependency_runtime=components.dependency_runtime,
        interpreter_content_digest=components.interpreter_content_digest,
        interpreter_size=components.interpreter_size,
    )


def _materialize_prepared(
    request: _MaterializationRequest,
    base_generation_root: Path | str,
    dependency_generation_root: Path | str,
    canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    composition_limits: RuntimeCompositionLimits,
    base_limits: BaseRuntimeLimits,
    dependency_limits: DependencyRuntimeLimits,
    dependencies: _MaterializerDependencies,
) -> RuntimeCompositionMaterializationResult:
    verify_kwargs = _verification_kwargs(
        request=request,
        base_generation_root=base_generation_root,
        dependency_generation_root=dependency_generation_root,
        canonical_store=canonical_store,
        repo_roots=repo_roots,
        composition_limits=composition_limits,
        base_limits=base_limits,
        dependency_limits=dependency_limits,
    )
    if _entry_exists(request.target):
        binding = verify_runtime_composition_generation(**verify_kwargs)
        return RuntimeCompositionMaterializationResult(binding, True)
    return _materialize_new(
        request=request,
        verify_kwargs=verify_kwargs,
        canonical_store=canonical_store,
        repo_roots=repo_roots,
        composition_limits=composition_limits,
        dependencies=dependencies,
    )


def _materialize_new(
    *,
    request: _MaterializationRequest,
    verify_kwargs: dict[str, Any],
    canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    composition_limits: RuntimeCompositionLimits,
    dependencies: _MaterializerDependencies,
) -> RuntimeCompositionMaterializationResult:
    staging = _create_staging(
        request, canonical_store=canonical_store,
        repo_roots=repo_roots, dependencies=dependencies,
    )
    published: OwnedDirectoryProof | None = None
    try:
        _publish_descriptor(
            request, staging, canonical_store, repo_roots,
            composition_limits, dependencies,
        )
        dependencies.after_descriptor(staging.path)
        verify_runtime_composition_staging(
            composition_store_root=request.store.path,
            staging_root=staging.path,
            expected_generation_id=str(request.descriptor["generation_id"]),
            owned_root=staging.identity,
            components=request.components,
            component_store_roots=(request.base_store, request.dependency_store),
            canonical_store=canonical_store,
            repo_roots=repo_roots,
            limits=composition_limits,
        )
        target, reused = _publish_candidate(request, staging, dependencies)
        if not reused:
            published = OwnedDirectoryProof(
                target, staging.identity.device, staging.identity.inode
            )
        binding = verify_runtime_composition_generation(**verify_kwargs)
        return RuntimeCompositionMaterializationResult(binding, reused)
    except BaseException:
        if published is not None:
            _quarantine(published, request=request, token=staging.token)
        raise
    finally:
        _quarantine(staging.identity, request=request, token=staging.token)


def _verification_kwargs(
    *, request: _MaterializationRequest,
    base_generation_root: Path | str,
    dependency_generation_root: Path | str,
    canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    composition_limits: RuntimeCompositionLimits,
    base_limits: BaseRuntimeLimits,
    dependency_limits: DependencyRuntimeLimits,
) -> dict[str, Any]:
    return {
        "composition_store_root": request.store.path,
        "generation_root": request.target,
        "base_runtime_store_root": request.base_store,
        "base_generation_root": base_generation_root,
        "dependency_runtime_store_root": request.dependency_store,
        "dependency_generation_root": dependency_generation_root,
        "canonical_store": canonical_store,
        "repo_roots": repo_roots,
        "composition_limits": composition_limits,
        "base_limits": base_limits,
        "dependency_limits": dependency_limits,
        "expected_generation_id": str(request.descriptor["generation_id"]),
    }


def _composition_store(
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


def _create_staging(
    request: _MaterializationRequest,
    *, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    dependencies: _MaterializerDependencies,
) -> _StagingState:
    token = dependencies.token()
    path = request.store.path / f".runtime-composition-stage-{token}"
    proof = create_isolated_store(
        path, canonical_store=canonical_store, repo_roots=repo_roots
    )
    return _StagingState(path, proof, owned_directory(path), token)


def _publish_descriptor(
    request: _MaterializationRequest,
    staging: _StagingState,
    canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    limits: RuntimeCompositionLimits,
    dependencies: _MaterializerDependencies,
) -> None:
    orphan_root = staging.path / ".runtime-composition-publication-orphans"
    proof = dependencies.publish_json(
        staging.path / DESCRIPTOR_NAME,
        request.descriptor,
        allowed_root=staging.path,
        canonical_store=canonical_store,
        repo_roots=repo_roots,
        max_bytes=limits.max_descriptor_bytes,
        expected_schema=DESCRIPTOR_SCHEMA_VERSION,
        reject_absolute_paths=True,
        orphan_root=orphan_root,
    )
    if not verify_proven_private_json(
        proof,
        expected_payload=request.descriptor,
        max_bytes=limits.max_descriptor_bytes,
        expected_schema=DESCRIPTOR_SCHEMA_VERSION,
    ):
        _fail("RUNTIME_COMPOSITION_DESCRIPTOR_PUBLICATION_INVALID")


def _publish_candidate(
    request: _MaterializationRequest,
    staging: _StagingState,
    dependencies: _MaterializerDependencies,
) -> tuple[Path, bool]:
    try:
        dependencies.publish_directory(staging.path, request.target)
        observed = owned_directory(request.target)
        if (
            observed.device != staging.identity.device
            or observed.inode != staging.identity.inode
        ):
            _fail("RUNTIME_COMPOSITION_PUBLICATION_IDENTITY_CHANGED")
        return request.target, False
    except QueryReplicaGenerationError as exc:
        if str(exc) != "QUERY_REPLICA_GENERATION_EXISTS":
            raise
        return request.target, True


def _quarantine(
    proof: OwnedDirectoryProof,
    *, request: _MaterializationRequest,
    token: str,
) -> None:
    quarantine_owned_staging(
        proof,
        allowed_root=request.store.path,
        orphan_root=request.orphan_root,
        token=token,
    )


def _entry_exists(path: Path) -> bool:
    try:
        os.lstat(path)
        return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise RuntimeCompositionMaterializationError(
            "RUNTIME_COMPOSITION_GENERATION_LOOKUP_FAILED"
        ) from exc


def _absolute(value: Path | str, code: str) -> Path:
    raw = str(value or "")
    if not raw or "\x00" in raw or not Path(raw).is_absolute():
        _fail(code)
    return Path(os.path.abspath(raw))


def _require_disjoint_runtime_stores(*roots: Path) -> None:
    normalized = [Path(root).resolve(strict=False) for root in roots]
    for index, first in enumerate(normalized):
        for second in normalized[index + 1:]:
            try:
                common = Path(os.path.commonpath((str(first), str(second))))
            except ValueError:
                continue
            if common == first or common == second:
                _fail("RUNTIME_COMPOSITION_STORE_OVERLAP")


_EXPECTED_ERRORS = (
    AcceptanceGuardError,
    QueryReplicaGenerationError,
    RuntimeCompositionContractError,
    RuntimeCompositionDescriptorError,
    OSError,
    TypeError,
    ValueError,
)


__all__ = [
    "RuntimeCompositionMaterializationError",
    "materialize_runtime_composition",
]
