"""Materialize one inert content-addressed HoloIndex Python base runtime."""

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
from .reddog_holoindex_base_runtime_contract import (
    ADMITTED_PATH_ROOTS,
    DESCRIPTOR_NAME,
    DESCRIPTOR_SCHEMA_VERSION,
    EXCLUDED_PATH_ROOTS,
    INVENTORY_NAME,
    INVENTORY_ROLES,
    INVENTORY_SCHEMA_VERSION,
    PAYLOAD_DIRECTORY,
    PLATFORM_TAG,
    REQUIRED_INVENTORY_ROLES,
    BaseRuntimeContractError,
    BaseRuntimeLimits,
    BaseRuntimeMaterializationResult,
    base_runtime_file_role,
    base_runtime_tree_digest,
)
from .reddog_holoindex_base_runtime_descriptor import (
    BaseRuntimeDescriptorError,
    verify_base_runtime_generation,
    verify_base_runtime_staging,
)
from .reddog_holoindex_dependency_runtime_contract import DependencyRuntimeLimits
from .reddog_holoindex_dependency_runtime_copy import (
    DependencyRuntimeSourcePlan,
    copy_dependency_runtime_snapshot,
    plan_dependency_runtime_snapshot,
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


_REQUIRED_DIRECTORY_ROOTS = ("DLLs", "Lib", "tcl")
_NESTED_EXCLUSIONS = ("Lib/site-packages",)


class BaseRuntimeMaterializationError(RuntimeError):
    """Stable inert base-runtime materialization error."""


def _fail(code: str) -> None:
    raise BaseRuntimeMaterializationError(code)


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
class _BaseRuntimePlan:
    source_plan: DependencyRuntimeSourcePlan
    generation_id: str
    inventory_rows: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class _MaterializationRequest:
    source: Path
    runtime_store: Path
    store_proof: StoreProof
    orphan_root: Path
    plan: _BaseRuntimePlan


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


def _dependency_limits(limits: BaseRuntimeLimits) -> DependencyRuntimeLimits:
    limits.validate()
    return DependencyRuntimeLimits(
        max_files=limits.max_files,
        max_directories=limits.max_directories,
        max_directory_depth=limits.max_directory_depth,
        max_path_bytes=limits.max_path_bytes,
        max_total_path_bytes=limits.max_total_path_bytes,
        max_file_bytes=limits.max_file_bytes,
        max_total_bytes=limits.max_total_bytes,
        max_inventory_bytes=limits.max_inventory_bytes,
        max_descriptor_bytes=limits.max_descriptor_bytes,
    )


def _runtime_store(
    path: Path, canonical_store: Path | str,
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


def _root_file_is_admitted(name: str) -> bool:
    lowered = name.casefold()
    return bool(
        (lowered.startswith("python") and lowered.endswith((".exe", ".dll")))
        or (lowered.startswith("vcruntime140") and lowered.endswith(".dll"))
        or lowered.endswith((".cfg", "._pth"))
    )


def _included_roots(source: Path) -> tuple[str, ...]:
    try:
        entries = tuple(os.scandir(source))
    except OSError as exc:
        raise BaseRuntimeMaterializationError(
            "BASE_RUNTIME_SOURCE_UNAVAILABLE"
        ) from exc
    names = {entry.name.casefold(): entry.name for entry in entries}
    required = tuple(root for root in _REQUIRED_DIRECTORY_ROOTS)
    if any(root.casefold() not in names for root in required):
        _fail("BASE_RUNTIME_REQUIRED_ROOT_MISSING")
    roots = [names[root.casefold()] for root in required]
    roots.extend(
        entry.name for entry in entries
        if entry.is_file(follow_symlinks=False) and _root_file_is_admitted(entry.name)
    )
    return tuple(sorted(roots, key=str.casefold))


def _inventory_rows_from_plan(
    plan: DependencyRuntimeSourcePlan,
) -> tuple[dict[str, Any], ...]:
    rows = tuple(
        {
            "path": item.relative_path,
            "size": item.size,
            "sha256": item.sha256,
            "role": base_runtime_file_role(item.relative_path),
        }
        for item in plan.files
    )
    return rows


def _plan_source(
    source: Path, limits: BaseRuntimeLimits,
    dependencies: _MaterializerDependencies,
) -> _BaseRuntimePlan:
    plan = dependencies.plan_tree(
        source, limits=_dependency_limits(limits),
        included_roots=_included_roots(source),
        excluded_roots=_NESTED_EXCLUSIONS,
    )
    rows = _inventory_rows_from_plan(plan)
    generation_id = base_runtime_tree_digest(plan.directories, list(rows))
    return _BaseRuntimePlan(plan, generation_id, rows)


def _prepare_request(
    *, source_base_prefix: Path | str, runtime_store_root: Path | str,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: BaseRuntimeLimits, dependencies: _MaterializerDependencies,
    expected_store: StoreProof | None = None,
) -> _MaterializationRequest:
    source = _absolute(source_base_prefix, "BASE_RUNTIME_SOURCE_PATH_INVALID")
    runtime = _absolute(runtime_store_root, "BASE_RUNTIME_STORE_PATH_INVALID")
    store = expected_store or _runtime_store(runtime, canonical_store, repo_roots)
    if os.path.normcase(str(store.path)) != os.path.normcase(str(runtime)):
        _fail("BASE_RUNTIME_STORE_IDENTITY_CHANGED")
    verify_store_proof(store, canonical_store=canonical_store, repo_roots=repo_roots)
    plan = _plan_source(source, limits, dependencies)
    if plan.source_plan.source_root != source:
        _fail("BASE_RUNTIME_SOURCE_PLAN_MISMATCH")
    return _MaterializationRequest(
        source, runtime, store, runtime / ".base-runtime-orphans", plan
    )


def _entry_exists(path: Path) -> bool:
    try:
        os.lstat(path)
        return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise BaseRuntimeMaterializationError(
            "BASE_RUNTIME_GENERATION_LOOKUP_FAILED"
        ) from exc


def _generation_target(request: _MaterializationRequest) -> Path:
    return request.runtime_store / request.plan.generation_id.removeprefix("sha256:")


def _verify_source_unchanged(
    request: _MaterializationRequest, limits: BaseRuntimeLimits,
    dependencies: _MaterializerDependencies,
) -> None:
    observed = _plan_source(request.source, limits, dependencies)
    if observed != request.plan:
        _fail("BASE_RUNTIME_SOURCE_CHANGED")


def _verify_existing(
    request: _MaterializationRequest, target: Path,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: BaseRuntimeLimits, dependencies: _MaterializerDependencies,
) -> BaseRuntimeMaterializationResult:
    binding = verify_base_runtime_generation(
        runtime_store_root=request.runtime_store, generation_root=target,
        expected_generation_id=request.plan.generation_id,
        canonical_store=canonical_store, repo_roots=repo_roots, limits=limits,
    )
    _verify_source_unchanged(request, limits, dependencies)
    return BaseRuntimeMaterializationResult(binding, True)


def _create_staging(
    request: _MaterializationRequest, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...], dependencies: _MaterializerDependencies,
) -> _StagingState:
    token = dependencies.token()
    staging = request.runtime_store / f".base-runtime-stage-{token}"
    proof = create_isolated_store(
        staging, canonical_store=canonical_store, repo_roots=repo_roots
    )
    return _StagingState(staging, proof, owned_directory(staging), token)


def _inventory(copy_proof: Any, plan: _BaseRuntimePlan) -> dict[str, Any]:
    rows = [
        {
            "path": item.relative_path,
            "size": item.size,
            "sha256": item.destination_sha256,
            "role": base_runtime_file_role(item.relative_path),
        }
        for item in copy_proof.files
    ]
    if tuple(rows) != plan.inventory_rows:
        _fail("BASE_RUNTIME_COPY_PROOF_INVALID")
    return {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "platform_tag": PLATFORM_TAG,
        "admitted_path_roots": list(ADMITTED_PATH_ROOTS),
        "excluded_path_roots": list(EXCLUDED_PATH_ROOTS),
        "directories": list(plan.source_plan.directories),
        "files": rows,
    }


def _descriptor(
    inventory: dict[str, Any], inventory_proof: Any, generation_id: str,
) -> dict[str, Any]:
    rows = inventory["files"]
    directories = inventory["directories"]
    return {
        "schema_version": DESCRIPTOR_SCHEMA_VERSION,
        "status": "INERT",
        "generation_id": generation_id,
        "inventory_file": INVENTORY_NAME,
        "inventory_digest": inventory_proof.digest,
        "inventory_bytes": inventory_proof.size,
        "base_runtime_tree_digest": generation_id,
        "file_count": len(rows),
        "directory_count": len(directories),
        "total_bytes": sum(row["size"] for row in rows),
        "platform_tag": PLATFORM_TAG,
        "admitted_path_roots": list(ADMITTED_PATH_ROOTS),
        "excluded_path_roots": list(EXCLUDED_PATH_ROOTS),
        "inventory_roles": list(INVENTORY_ROLES),
        "required_inventory_roles": list(REQUIRED_INVENTORY_ROLES),
        "artifact_bytes_verified_at_publication": True,
        "native_loader_closure_verified": False,
        "deterministic_effects_verified": False,
        "signature_verified": False,
        "write_denial_verified": False,
        "activation_eligible": False,
        "exact_runtime_closure_verified": False,
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
        _fail("BASE_RUNTIME_CONTRACT_PUBLICATION_INVALID")
    return proof


def _publish_contracts(
    *, staging: Path, request: _MaterializationRequest,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    copy_proof: Any, limits: BaseRuntimeLimits,
    dependencies: _MaterializerDependencies,
) -> None:
    orphan_root = staging / ".base-runtime-publication-orphans"
    inventory = _inventory(copy_proof, request.plan)
    inventory_proof = _publish_one_json(
        path=staging / INVENTORY_NAME, payload=inventory,
        schema=INVENTORY_SCHEMA_VERSION, max_bytes=limits.max_inventory_bytes,
        staging=staging, orphan_root=orphan_root,
        canonical_store=canonical_store, repo_roots=repo_roots,
        dependencies=dependencies,
    )
    descriptor = _descriptor(
        inventory, inventory_proof, request.plan.generation_id
    )
    _publish_one_json(
        path=staging / DESCRIPTOR_NAME, payload=descriptor,
        schema=DESCRIPTOR_SCHEMA_VERSION, max_bytes=limits.max_descriptor_bytes,
        staging=staging, orphan_root=orphan_root,
        canonical_store=canonical_store, repo_roots=repo_roots,
        dependencies=dependencies,
    )


def _copy_candidate(
    request: _MaterializationRequest, staging: _StagingState,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: BaseRuntimeLimits, dependencies: _MaterializerDependencies,
) -> Any:
    source_plan = request.plan.source_plan
    copied = dependencies.copy_tree(
        request.source, staging.path / PAYLOAD_DIRECTORY,
        store_proof=staging.proof, canonical_store=canonical_store,
        repo_roots=repo_roots, limits=_dependency_limits(limits),
        expected_plan=source_plan, included_roots=source_plan.included_roots,
        excluded_roots=source_plan.excluded_roots,
    )
    if copied.destination_digest != source_plan.generation_id:
        _fail("BASE_RUNTIME_COPY_PROOF_INVALID")
    return copied


def _verify_staging(
    request: _MaterializationRequest, staging: _StagingState,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: BaseRuntimeLimits,
) -> None:
    binding = verify_base_runtime_staging(
        runtime_store_root=request.runtime_store, staging_root=staging.path,
        expected_generation_id=request.plan.generation_id,
        owned_root=staging.identity, canonical_store=canonical_store,
        repo_roots=repo_roots, limits=limits,
    )
    if binding.generation_id != request.plan.generation_id:
        _fail("BASE_RUNTIME_STAGING_BINDING_INVALID")


def _publish_candidate(
    request: _MaterializationRequest, staging: _StagingState,
    dependencies: _MaterializerDependencies,
) -> tuple[Path, bool]:
    target = _generation_target(request)
    try:
        dependencies.publish_directory(staging.path, target)
        published = owned_directory(target)
        if published.device != staging.identity.device or published.inode != staging.identity.inode:
            _fail("BASE_RUNTIME_PUBLICATION_IDENTITY_CHANGED")
        return target, False
    except QueryReplicaGenerationError as exc:
        if str(exc) != "QUERY_REPLICA_GENERATION_EXISTS":
            raise
        return target, True


def _quarantine(
    proof: OwnedDirectoryProof, request: _MaterializationRequest, token: str,
) -> None:
    quarantine_owned_staging(
        proof, allowed_root=request.runtime_store,
        orphan_root=request.orphan_root, token=token,
    )


def _materialize_new(
    *, request: _MaterializationRequest, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...], limits: BaseRuntimeLimits,
    dependencies: _MaterializerDependencies,
) -> BaseRuntimeMaterializationResult:
    staging = _create_staging(request, canonical_store, repo_roots, dependencies)
    published_proof: OwnedDirectoryProof | None = None
    try:
        copied = _copy_candidate(
            request, staging, canonical_store, repo_roots, limits, dependencies
        )
        _publish_contracts(
            staging=staging.path, request=request, canonical_store=canonical_store,
            repo_roots=repo_roots, copy_proof=copied, limits=limits,
            dependencies=dependencies,
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
        return BaseRuntimeMaterializationResult(result.binding, False)
    except BaseException:
        if published_proof is not None:
            _quarantine(published_proof, request, staging.token)
        raise
    finally:
        _quarantine(staging.identity, request, staging.token)


def _materialize_base_runtime_for_test(
    *, source_base_prefix: Path | str, runtime_store_root: Path | str,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: BaseRuntimeLimits = BaseRuntimeLimits(),
    dependencies: _MaterializerDependencies = _MaterializerDependencies(),
    expected_store: StoreProof | None = None,
) -> BaseRuntimeMaterializationResult:
    try:
        request = _prepare_request(
            source_base_prefix=source_base_prefix,
            runtime_store_root=runtime_store_root,
            canonical_store=canonical_store, repo_roots=repo_roots,
            limits=limits, dependencies=dependencies, expected_store=expected_store,
        )
        target = _generation_target(request)
        if _entry_exists(target):
            return _verify_existing(
                request, target, canonical_store, repo_roots, limits, dependencies
            )
        return _materialize_new(
            request=request, canonical_store=canonical_store,
            repo_roots=repo_roots, limits=limits, dependencies=dependencies,
        )
    except BaseRuntimeMaterializationError:
        raise
    except (
        AcceptanceGuardError, BaseRuntimeContractError,
        BaseRuntimeDescriptorError, QueryReplicaGenerationError,
        OSError, TypeError, ValueError,
    ) as exc:
        raise BaseRuntimeMaterializationError(str(exc)) from exc


def materialize_base_runtime(
    *, source_base_prefix: Path | str, runtime_store_root: Path | str,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: BaseRuntimeLimits = BaseRuntimeLimits(),
) -> BaseRuntimeMaterializationResult:
    """Create or reprove one inert generation without activating it."""

    try:
        runtime = _absolute(runtime_store_root, "BASE_RUNTIME_STORE_PATH_INVALID")
        store = _runtime_store(runtime, canonical_store, repo_roots)
        lock_identity = f"reddog-base-runtime:{store.device}:{store.inode}"
        with runtime_operation_lock(lock_identity):
            return _materialize_base_runtime_for_test(
                source_base_prefix=source_base_prefix,
                runtime_store_root=runtime, canonical_store=canonical_store,
                repo_roots=repo_roots, limits=limits, expected_store=store,
            )
    except BaseRuntimeMaterializationError:
        raise
    except (
        AcceptanceGuardError, BaseRuntimeContractError,
        BaseRuntimeDescriptorError, QueryReplicaGenerationError,
        OSError, TypeError, ValueError,
    ) as exc:
        raise BaseRuntimeMaterializationError(str(exc)) from exc


__all__ = ["BaseRuntimeMaterializationError", "materialize_base_runtime"]
