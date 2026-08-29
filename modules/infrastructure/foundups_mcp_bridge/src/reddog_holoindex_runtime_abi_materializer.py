"""Publish one inert composition-bound runtime ABI attestation generation."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

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
from .reddog_holoindex_query_replica_generation import (
    QueryReplicaGenerationError,
    publish_directory_no_replace,
)
from .reddog_holoindex_query_replica_orphans import (
    OwnedDirectoryProof,
    owned_directory,
    quarantine_owned_staging,
)
from .reddog_holoindex_runtime_abi_contract import (
    DESCRIPTOR_NAME,
    DESCRIPTOR_SCHEMA_VERSION,
    INVENTORY_NAME,
    INVENTORY_SCHEMA_VERSION,
    RuntimeAbiContractError,
    RuntimeAbiLimits,
    RuntimeAbiMaterializationResult,
    stable_error_code,
)
from .reddog_holoindex_runtime_abi_descriptor import (
    RuntimeAbiDescriptorError,
    RuntimeAbiEvidence,
    build_runtime_abi_evidence,
    verify_runtime_abi_generation,
    verify_runtime_abi_staging,
)
from .reddog_holoindex_runtime_abi_metadata import RuntimeAbiMetadataError
from .reddog_holoindex_windows_pe import PELimits


class RuntimeAbiMaterializationError(RuntimeError):
    """Stable inert ABI-attestation publication error."""


def _fail(code: str) -> None:
    raise RuntimeAbiMaterializationError(code)


def _after_evidence_noop(_staging: Path) -> None:
    """Trusted seam for unpublished-evidence falsification tests."""


@dataclass(frozen=True)
class _MaterializerDependencies:
    publish_json: Callable[..., Any] = atomic_publish_private_json_proven
    publish_directory: Callable[[Path, Path], None] = publish_directory_no_replace
    after_evidence: Callable[[Path], None] = _after_evidence_noop
    token: Callable[[], str] = lambda: secrets.token_hex(16)


@dataclass(frozen=True)
class _Request:
    store: StoreProof
    evidence: RuntimeAbiEvidence
    target: Path
    orphan_root: Path
    canonical_store: Path | str
    repo_roots: tuple[Path | str, ...]


@dataclass(frozen=True)
class _Staging:
    path: Path
    identity: OwnedDirectoryProof
    token: str


def materialize_runtime_abi_attestation(
    *, abi_store_root: Path | str, composition_kwargs: Mapping[str, Any],
    abi_limits: RuntimeAbiLimits = RuntimeAbiLimits(),
    pe_limits: PELimits = PELimits(),
) -> RuntimeAbiMaterializationResult:
    """Create or fully reprove one inert ABI attestation generation."""

    try:
        root = _absolute(abi_store_root, "RUNTIME_ABI_STORE_PATH_INVALID")
        canonical, repo_roots = _context(composition_kwargs)
        _require_disjoint(root, composition_kwargs)
        store = _attestation_store(
            root, canonical_store=canonical, repo_roots=repo_roots
        )
        lock_identity = f"reddog-runtime-abi:{store.device}:{store.inode}"
        with runtime_operation_lock(lock_identity):
            return _materialize_runtime_abi_for_test(
                abi_store_root=store.path,
                composition_kwargs=composition_kwargs,
                abi_limits=abi_limits, pe_limits=pe_limits,
                expected_store=store,
            )
    except RuntimeAbiMaterializationError:
        raise
    except _EXPECTED_ERRORS as exc:
        raise RuntimeAbiMaterializationError(
            stable_error_code(exc, "RUNTIME_ABI_MATERIALIZATION_FAILED")
        ) from exc


def _materialize_runtime_abi_for_test(
    *, abi_store_root: Path | str, composition_kwargs: Mapping[str, Any],
    abi_limits: RuntimeAbiLimits = RuntimeAbiLimits(),
    pe_limits: PELimits = PELimits(),
    dependencies: _MaterializerDependencies = _MaterializerDependencies(),
    expected_store: StoreProof | None = None,
) -> RuntimeAbiMaterializationResult:
    try:
        request = _prepare_request(
            abi_store_root, composition_kwargs, abi_limits, pe_limits,
            expected_store,
        )
        if _entry_exists(request.target):
            binding = verify_runtime_abi_generation(
                abi_store_root=request.store.path,
                generation_root=request.target,
                composition_kwargs=composition_kwargs,
                abi_limits=abi_limits, pe_limits=pe_limits,
                expected_generation_id=str(request.evidence.descriptor["generation_id"]),
            )
            return RuntimeAbiMaterializationResult(binding, True)
        return _materialize_new(
            request, composition_kwargs, abi_limits, pe_limits, dependencies
        )
    except RuntimeAbiMaterializationError:
        raise
    except _EXPECTED_ERRORS as exc:
        raise RuntimeAbiMaterializationError(
            stable_error_code(exc, "RUNTIME_ABI_MATERIALIZATION_FAILED")
        ) from exc


def _prepare_request(
    abi_store_root: Path | str, composition_kwargs: Mapping[str, Any],
    abi_limits: RuntimeAbiLimits, pe_limits: PELimits,
    expected_store: StoreProof | None,
) -> _Request:
    abi_limits.validate()
    pe_limits.validate()
    root = _absolute(abi_store_root, "RUNTIME_ABI_STORE_PATH_INVALID")
    canonical, repo_roots = _context(composition_kwargs)
    _require_disjoint(root, composition_kwargs)
    store = expected_store or _attestation_store(
        root, canonical_store=canonical, repo_roots=repo_roots
    )
    if os.path.normcase(str(store.path)) != os.path.normcase(str(root)):
        _fail("RUNTIME_ABI_STORE_IDENTITY_CHANGED")
    verify_store_proof(store, canonical_store=canonical, repo_roots=repo_roots)
    evidence = build_runtime_abi_evidence(
        composition_kwargs=composition_kwargs,
        abi_limits=abi_limits, pe_limits=pe_limits,
    )
    target = store.path / str(evidence.descriptor["generation_id"])[7:]
    return _Request(
        store, evidence, target, store.path / ".runtime-abi-orphans",
        canonical, repo_roots,
    )


def _materialize_new(
    request: _Request, composition_kwargs: Mapping[str, Any],
    abi_limits: RuntimeAbiLimits, pe_limits: PELimits,
    dependencies: _MaterializerDependencies,
) -> RuntimeAbiMaterializationResult:
    staging = _create_staging(request, dependencies)
    published: OwnedDirectoryProof | None = None
    try:
        _publish_evidence(request, staging, abi_limits, dependencies)
        dependencies.after_evidence(staging.path)
        verify_runtime_abi_staging(
            abi_store_root=request.store.path, staging_root=staging.path,
            expected_generation_id=str(request.evidence.descriptor["generation_id"]),
            owned_root=staging.identity, evidence=request.evidence,
            canonical_store=request.canonical_store, repo_roots=request.repo_roots,
            abi_limits=abi_limits,
        )
        target, reused = _publish_candidate(request, staging, dependencies)
        if not reused:
            published = OwnedDirectoryProof(
                target, staging.identity.device, staging.identity.inode
            )
        binding = verify_runtime_abi_generation(
            abi_store_root=request.store.path, generation_root=request.target,
            composition_kwargs=composition_kwargs,
            abi_limits=abi_limits, pe_limits=pe_limits,
            expected_generation_id=str(request.evidence.descriptor["generation_id"]),
        )
        return RuntimeAbiMaterializationResult(binding, reused)
    except BaseException:
        if published is not None:
            _quarantine(published, request, staging.token)
        raise
    finally:
        _quarantine(staging.identity, request, staging.token)


def _create_staging(
    request: _Request, dependencies: _MaterializerDependencies,
) -> _Staging:
    token = dependencies.token()
    path = request.store.path / f".runtime-abi-stage-{token}"
    create_isolated_store(
        path, canonical_store=request.canonical_store,
        repo_roots=request.repo_roots,
    )
    return _Staging(path, owned_directory(path), token)


def _publish_evidence(
    request: _Request, staging: _Staging, limits: RuntimeAbiLimits,
    dependencies: _MaterializerDependencies,
) -> None:
    orphan_root = staging.path / ".runtime-abi-publication-orphans"
    pairs = (
        (
            INVENTORY_NAME, request.evidence.inventory,
            limits.max_inventory_bytes, INVENTORY_SCHEMA_VERSION,
        ),
        (
            DESCRIPTOR_NAME, request.evidence.descriptor,
            limits.max_descriptor_bytes, DESCRIPTOR_SCHEMA_VERSION,
        ),
    )
    for name, payload, maximum, schema in pairs:
        proof = dependencies.publish_json(
            staging.path / name, payload, allowed_root=staging.path,
            canonical_store=request.canonical_store, repo_roots=request.repo_roots,
            max_bytes=maximum, expected_schema=schema,
            reject_absolute_paths=True, orphan_root=orphan_root,
        )
        if not verify_proven_private_json(
            proof, expected_payload=payload, max_bytes=maximum,
            expected_schema=schema,
        ):
            _fail("RUNTIME_ABI_EVIDENCE_PUBLICATION_INVALID")


def _publish_candidate(
    request: _Request, staging: _Staging,
    dependencies: _MaterializerDependencies,
) -> tuple[Path, bool]:
    try:
        dependencies.publish_directory(staging.path, request.target)
        observed = owned_directory(request.target)
        if (
            observed.device != staging.identity.device
            or observed.inode != staging.identity.inode
        ):
            _fail("RUNTIME_ABI_PUBLICATION_IDENTITY_CHANGED")
        return request.target, False
    except QueryReplicaGenerationError as exc:
        if str(exc) != "QUERY_REPLICA_GENERATION_EXISTS":
            raise
        return request.target, True


def _quarantine(proof: OwnedDirectoryProof, request: _Request, token: str) -> None:
    quarantine_owned_staging(
        proof, allowed_root=request.store.path,
        orphan_root=request.orphan_root, token=token,
    )


def _context(
    composition_kwargs: Mapping[str, Any],
) -> tuple[Path | str, tuple[Path | str, ...]]:
    if type(composition_kwargs) is not dict:
        _fail("RUNTIME_ABI_COMPOSITION_ARGUMENTS_INVALID")
    canonical = composition_kwargs.get("canonical_store")
    repo_roots = composition_kwargs.get("repo_roots")
    if not isinstance(repo_roots, tuple) or not repo_roots or canonical is None:
        _fail("RUNTIME_ABI_COMPOSITION_ARGUMENTS_INVALID")
    return canonical, repo_roots


def _attestation_store(
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


def _require_disjoint(root: Path, composition_kwargs: Mapping[str, Any]) -> None:
    others = [
        Path(composition_kwargs[name]) for name in (
            "composition_store_root", "base_runtime_store_root",
            "dependency_runtime_store_root",
        ) if name in composition_kwargs
    ]
    normalized = [root.resolve(strict=False), *(path.resolve(strict=False) for path in others)]
    for other in normalized[1:]:
        try:
            common = Path(os.path.commonpath((str(normalized[0]), str(other))))
        except ValueError:
            continue
        if common in {normalized[0], other}:
            _fail("RUNTIME_ABI_STORE_OVERLAP")


def _entry_exists(path: Path) -> bool:
    try:
        os.lstat(path)
        return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise RuntimeAbiMaterializationError(
            "RUNTIME_ABI_GENERATION_LOOKUP_FAILED"
        ) from exc


def _absolute(value: Path | str, code: str) -> Path:
    raw = str(value or "")
    if not raw or "\x00" in raw or not Path(raw).is_absolute():
        _fail(code)
    return Path(os.path.abspath(raw))


_EXPECTED_ERRORS = (
    AcceptanceGuardError, OSError, QueryReplicaGenerationError,
    RuntimeAbiContractError, RuntimeAbiDescriptorError, RuntimeAbiMetadataError,
    TypeError, ValueError,
)


__all__ = [
    "RuntimeAbiMaterializationError", "materialize_runtime_abi_attestation",
]
