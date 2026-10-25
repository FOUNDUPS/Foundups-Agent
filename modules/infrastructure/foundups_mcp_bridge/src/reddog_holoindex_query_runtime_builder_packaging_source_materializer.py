"""Publish one inert content-addressed source from a retained packaging wheel."""

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
    digest_bytes,
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
from .reddog_holoindex_query_runtime_builder_packaging_source_contract import (
    BUILDER_PACKAGING_SOURCE_DESCRIPTOR_NAME,
    BUILDER_PACKAGING_SOURCE_DESCRIPTOR_SCHEMA_VERSION,
    BUILDER_PACKAGING_SOURCE_INVENTORY_NAME,
    BUILDER_PACKAGING_SOURCE_INVENTORY_SCHEMA_VERSION,
    BUILDER_PACKAGING_SOURCE_PUBLICATION_ORPHANS,
    BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY,
    BUILDER_PACKAGING_SOURCE_WHEEL_DIRECTORY,
    BuilderPackagingSourceContractError,
    BuilderPackagingSourceLimits,
    BuilderPackagingSourceMaterializationResult,
    BuilderPackagingSourcePlan,
    absolute_builder_packaging_source_store_path,
    build_builder_packaging_source_plan,
    builder_packaging_source_entry_exists,
    stable_builder_packaging_source_error,
    validated_builder_packaging_source_token,
)
from . import reddog_holoindex_query_runtime_builder_packaging_source_verifier as source_verifier
from .reddog_holoindex_query_runtime_builder_packaging_source_writer_windows import (
    BuilderPackagingSourceWriterError,
    write_builder_packaging_source_windows,
)
from . import reddog_holoindex_query_runtime_builder_packaging_wheel as wheel_module


class BuilderPackagingSourceMaterializationError(RuntimeError):
    """Stable path-free packaging-source materialization error."""


def _fail(code: str) -> None:
    raise BuilderPackagingSourceMaterializationError(code)


def _wrapped(error: BaseException) -> BuilderPackagingSourceMaterializationError:
    code = stable_builder_packaging_source_error(error, "BUILDER_PACKAGING_SOURCE_MATERIALIZATION_FAILED")
    return BuilderPackagingSourceMaterializationError(code)


def _noop(*_args: Any) -> None: return None

@dataclass(frozen=True)
class _BuilderPackagingSourceDependencies:
    write_source: Callable[..., Any] = write_builder_packaging_source_windows
    publish_json: Callable[..., Any] = atomic_publish_private_json_proven
    publish_directory: Callable[[Path, Path], None] = publish_directory_no_replace
    after_contracts: Callable[[Path], None] = _noop
    after_publish: Callable[[Path], None] = _noop
    token: Callable[[], str] = lambda: secrets.token_hex(16)


@dataclass(frozen=True)
class _Request:
    source_store: Path
    store_proof: StoreProof
    orphan_root: Path
    plan: BuilderPackagingSourcePlan
    reviewed_pin_match: bool
    source_lease_held: bool


@dataclass(frozen=True)
class _Staging:
    path: Path
    proof: StoreProof
    identity: OwnedDirectoryProof
    token: str


def _source_store(
    path: Path, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
) -> StoreProof:
    try:
        return prove_existing_isolated_store(
            path, canonical_store=canonical_store, repo_roots=repo_roots,
        )
    except (AcceptanceGuardError, OSError):
        try:
            return create_isolated_store(
                path, canonical_store=canonical_store, repo_roots=repo_roots,
            )
        except AcceptanceGuardError:
            return prove_existing_isolated_store(
                path, canonical_store=canonical_store, repo_roots=repo_roots,
            )


def _prepare_request(
    *, plan: BuilderPackagingSourcePlan, source_store_root: Path | str,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    reviewed_pin_match: bool,
    source_lease_held: bool, expected_store: StoreProof | None = None,
) -> _Request:
    source_store = absolute_builder_packaging_source_store_path(source_store_root)
    store = expected_store or _source_store(source_store, canonical_store, repo_roots)
    verify_store_proof(store, canonical_store=canonical_store, repo_roots=repo_roots)
    if os.path.normcase(str(store.path)) != os.path.normcase(str(source_store)):
        _fail("BUILDER_PACKAGING_SOURCE_STORE_IDENTITY_CHANGED")
    if type(reviewed_pin_match) is not bool or type(source_lease_held) is not bool:
        _fail("BUILDER_PACKAGING_SOURCE_AUTHORITY_INVALID")
    return _Request(
        source_store, store, source_store / ".builder-packaging-source-orphans",
        plan,
        reviewed_pin_match, source_lease_held,
    )


def _target(request: _Request) -> Path:
    return request.source_store / request.plan.generation_id.removeprefix("sha256:")


def _create_staging(
    request: _Request, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...], token: str,
) -> _Staging:
    staging = request.source_store / f".builder-packaging-source-stage-{token}"
    proof = create_isolated_store(
        staging, canonical_store=canonical_store, repo_roots=repo_roots,
    )
    return _Staging(staging, proof, owned_directory(staging), token)


def _descriptor(request: _Request) -> dict[str, Any]:
    plan, proof = request.plan, request.plan.payload.proof
    return {
        "schema_version": BUILDER_PACKAGING_SOURCE_DESCRIPTOR_SCHEMA_VERSION,
        "status": "INERT_SOURCE", "generation_id": plan.generation_id,
        "inventory_file": BUILDER_PACKAGING_SOURCE_INVENTORY_NAME,
        "inventory_digest": digest_bytes(plan.inventory_raw),
        "inventory_bytes": len(plan.inventory_raw),
        "wheel_directory": BUILDER_PACKAGING_SOURCE_WHEEL_DIRECTORY,
        "wheel_file": wheel_module.PACKAGING_26_WHEEL_FILENAME,
        "wheel_size": len(plan.payload.wheel_bytes),
        "wheel_sha256": digest_bytes(plan.payload.wheel_bytes),
        "site_packages_directory": BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY,
        "central_directory_digest": proof.central_directory_digest,
        "member_set_digest": proof.member_set_digest,
        "metadata_digest": proof.metadata_digest,
        "wheel_metadata_digest": proof.wheel_metadata_digest,
        "record_digest": proof.record_digest,
        "owned_files_digest": proof.owned_files_digest,
        "dependency_tree_digest": plan.dependency_tree_digest,
        "member_count": len(plan.payload.members),
        "directory_count": len(plan.directories),
        "expanded_bytes": sum(len(member.payload) for member in plan.payload.members),
        "reviewed_pin_match": request.reviewed_pin_match,
        "source_lease_held_through_publication": False,
        "strict_archive_verified": True, "record_ownership_verified": True,
        "source_only_topology_verified": True,
        "source_materialization_performed": True, "extraction_performed": True,
        "publication_performed": True, "wheel_to_tree_verified": True,
        "artifact_bytes_verified_at_publication": True,
        "official_provenance_authenticated": False, "signature_verified": False,
        "network_performed": False, "download_performed": False,
        "installation_performed": False, "import_authority_verified": False,
        "child_execution_authorized": False, "builder_runtime_authenticated": False,
        "preimport_loader_authority_verified": False,
        "native_loader_closure_verified": False, "subprocess_closure_verified": False,
        "exact_runtime_closure_verified": False,
        "deterministic_effects_verified": False, "write_denial_verified": False,
        "activation_eligible": False, "a_grade_verified": False,
        "retrieval_rsi_verified": False,
    }


def _publish_json(
    *, path: Path, payload: dict[str, Any], schema: str, max_bytes: int,
    staging: Path, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...], dependencies: _BuilderPackagingSourceDependencies,
) -> None:
    proof = dependencies.publish_json(
        path, payload, allowed_root=staging, canonical_store=canonical_store,
        repo_roots=repo_roots, max_bytes=max_bytes, expected_schema=schema,
        reject_absolute_paths=True,
        orphan_root=staging / BUILDER_PACKAGING_SOURCE_PUBLICATION_ORPHANS,
    )
    if not verify_proven_private_json(
        proof, expected_payload=payload, max_bytes=max_bytes, expected_schema=schema,
    ):
        _fail("BUILDER_PACKAGING_SOURCE_CONTRACT_PUBLICATION_INVALID")


def _publish_contracts(
    request: _Request, staging: _Staging, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...], limits: BuilderPackagingSourceLimits,
    dependencies: _BuilderPackagingSourceDependencies,
) -> None:
    _publish_json(
        path=staging.path / BUILDER_PACKAGING_SOURCE_INVENTORY_NAME,
        payload=request.plan.inventory,
        schema=BUILDER_PACKAGING_SOURCE_INVENTORY_SCHEMA_VERSION,
        max_bytes=limits.max_inventory_bytes, staging=staging.path,
        canonical_store=canonical_store, repo_roots=repo_roots,
        dependencies=dependencies,
    )
    _publish_json(
        path=staging.path / BUILDER_PACKAGING_SOURCE_DESCRIPTOR_NAME,
        payload=_descriptor(request),
        schema=BUILDER_PACKAGING_SOURCE_DESCRIPTOR_SCHEMA_VERSION,
        max_bytes=limits.max_descriptor_bytes, staging=staging.path,
        canonical_store=canonical_store, repo_roots=repo_roots,
        dependencies=dependencies,
    )


def _write_candidate(
    request: _Request, staging: _Staging, limits: BuilderPackagingSourceLimits,
    dependencies: _BuilderPackagingSourceDependencies,
) -> None:
    result = dependencies.write_source(
        staging_root=staging.path, owned_root=staging.identity,
        wheel_filename=wheel_module.PACKAGING_26_WHEEL_FILENAME,
        wheel_bytes=request.plan.payload.wheel_bytes,
        members=request.plan.payload.members, directories=request.plan.directories,
        limits=limits,
    )
    if (
        result.written_member_count != len(request.plan.payload.members)
        or result.written_member_bytes
        != sum(len(member.payload) for member in request.plan.payload.members)
    ):
        _fail("BUILDER_PACKAGING_SOURCE_WRITE_PROOF_INVALID")


def _verify_staging(
    request: _Request, staging: _Staging, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...], limits: BuilderPackagingSourceLimits,
) -> None:
    verify = (
        source_verifier.verify_builder_packaging_source_staging
        if request.reviewed_pin_match and request.source_lease_held
        else source_verifier._verify_builder_packaging_source_staging_for_test
    )
    binding = verify(
        source_store_root=request.source_store, staging_root=staging.path,
        expected_generation_id=request.plan.generation_id,
        owned_root=staging.identity, canonical_store=canonical_store,
        repo_roots=repo_roots, limits=limits,
    )
    if binding.generation_id != request.plan.generation_id:
        _fail("BUILDER_PACKAGING_SOURCE_STAGING_BINDING_INVALID")


def _verify_existing(
    request: _Request, target: Path, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...], limits: BuilderPackagingSourceLimits,
) -> BuilderPackagingSourceMaterializationResult:
    verify = (
        source_verifier.verify_builder_packaging_source_generation
        if request.reviewed_pin_match and request.source_lease_held
        else source_verifier._verify_builder_packaging_source_generation_for_test
    )
    binding = verify(
        source_store_root=request.source_store, generation_root=target,
        expected_generation_id=request.plan.generation_id,
        canonical_store=canonical_store, repo_roots=repo_roots, limits=limits,
    )
    return BuilderPackagingSourceMaterializationResult(binding, True)


def _publish_candidate(
    request: _Request, staging: _Staging,
    dependencies: _BuilderPackagingSourceDependencies,
) -> tuple[Path, bool]:
    target = _target(request)
    try:
        dependencies.publish_directory(staging.path, target)
        published = owned_directory(target)
        if (
            published.device != staging.identity.device
            or published.inode != staging.identity.inode
        ):
            _fail("BUILDER_PACKAGING_SOURCE_PUBLICATION_IDENTITY_CHANGED")
        return target, False
    except QueryReplicaGenerationError as exc:
        if str(exc) != "QUERY_REPLICA_GENERATION_EXISTS":
            raise
        return target, True


def _quarantine(proof: OwnedDirectoryProof, request: _Request, token: str) -> None:
    quarantine_owned_staging(
        proof, allowed_root=request.source_store,
        orphan_root=request.orphan_root, token=token,
    )


def _preserve_failure_after_quarantine(
    primary: BaseException, proofs: tuple[OwnedDirectoryProof, ...],
    request: _Request, token: str,
) -> None:
    quarantine_failed = False
    for proof in proofs:
        try:
            _quarantine(proof, request, token)
        except BaseException:
            quarantine_failed = True
    if quarantine_failed:
        raise BuilderPackagingSourceMaterializationError(
            "BUILDER_PACKAGING_SOURCE_QUARANTINE_FAILED"
        ) from primary
    raise primary


def _materialize_new(
    *, request: _Request, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...], limits: BuilderPackagingSourceLimits,
    dependencies: _BuilderPackagingSourceDependencies,
    source_reproof: Callable[[], Any],
    token: str,
) -> BuilderPackagingSourceMaterializationResult:
    staging = _create_staging(request, canonical_store, repo_roots, token)
    published_proof: OwnedDirectoryProof | None = None
    try:
        _write_candidate(request, staging, limits, dependencies)
        _publish_contracts(request, staging, canonical_store, repo_roots, limits, dependencies)
        dependencies.after_contracts(staging.path)
        _verify_staging(request, staging, canonical_store, repo_roots, limits)
        source_reproof()
        target, reused = _publish_candidate(request, staging, dependencies)
        if reused:
            result = _verify_existing(request, target, canonical_store, repo_roots, limits)
        else:
            published_proof = OwnedDirectoryProof(
                target, staging.identity.device, staging.identity.inode,
            )
            dependencies.after_publish(target)
            existing = _verify_existing(request, target, canonical_store, repo_roots, limits)
            result = BuilderPackagingSourceMaterializationResult(existing.binding, False)
        source_reproof()
    except BaseException as primary:
        proofs = (
            (published_proof, staging.identity)
            if published_proof is not None else (staging.identity,)
        )
        _preserve_failure_after_quarantine(
            primary, proofs, request, staging.token,
        )
        raise AssertionError("unreachable")
    _quarantine(staging.identity, request, staging.token)
    return result


def _materialize_request(
    *, request: _Request, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...], limits: BuilderPackagingSourceLimits,
    dependencies: _BuilderPackagingSourceDependencies,
    source_reproof: Callable[[], Any],
    token: str,
) -> BuilderPackagingSourceMaterializationResult:
    target = _target(request)
    if builder_packaging_source_entry_exists(target):
        result = _verify_existing(request, target, canonical_store, repo_roots, limits)
        source_reproof()
        return result
    return _materialize_new(
        request=request, canonical_store=canonical_store, repo_roots=repo_roots,
        limits=limits, dependencies=dependencies, source_reproof=source_reproof, token=token,
    )


def _materialize_payload(
    *, payload: Any, source_store_root: Path | str,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: BuilderPackagingSourceLimits,
    dependencies: _BuilderPackagingSourceDependencies,
    reviewed_pin_match: bool, source_lease_held: bool,
    source_reproof: Callable[[], Any],
) -> BuilderPackagingSourceMaterializationResult:
    limits.validate()
    plan = build_builder_packaging_source_plan(
        payload=payload, wheel_filename=wheel_module.PACKAGING_26_WHEEL_FILENAME, limits=limits,
    )
    token = validated_builder_packaging_source_token(dependencies.token())
    store_path = absolute_builder_packaging_source_store_path(source_store_root)
    store = _source_store(store_path, canonical_store, repo_roots)
    lock_identity = f"reddog-builder-packaging-source:{store.device}:{store.inode}"
    with runtime_operation_lock(lock_identity):
        request = _prepare_request(
            plan=plan, source_store_root=store_path,
            canonical_store=canonical_store, repo_roots=repo_roots,
            reviewed_pin_match=reviewed_pin_match,
            source_lease_held=source_lease_held, expected_store=store,
        )
        result = _materialize_request(
            request=request, canonical_store=canonical_store,
            repo_roots=repo_roots, limits=limits, dependencies=dependencies,
            source_reproof=source_reproof, token=token,
        )
        live = request.reviewed_pin_match and request.source_lease_held
        binding = result.binding.with_live_source_authority(
            verified=live, published=not result.reused_existing_generation,
        )
        return BuilderPackagingSourceMaterializationResult(
            binding, result.reused_existing_generation,
        )


def _materialize_builder_packaging_source_bytes_for_test(
    *, wheel_bytes: bytes, source_store_root: Path | str,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: BuilderPackagingSourceLimits = BuilderPackagingSourceLimits(),
    dependencies: _BuilderPackagingSourceDependencies = _BuilderPackagingSourceDependencies(),
) -> BuilderPackagingSourceMaterializationResult:
    """Materialize synthetic proved bytes while claiming no pin/lease authority."""

    payload = wheel_module._prove_packaging_wheel_payload_for_test(
        wheel_bytes=wheel_bytes,
        expected_filename=wheel_module.PACKAGING_26_WHEEL_FILENAME,
        expected_size=len(wheel_bytes),
        expected_sha256=digest_bytes(wheel_bytes).removeprefix("sha256:"),
    )
    return _stable_materialize(
        payload=payload, source_store_root=source_store_root,
        canonical_store=canonical_store, repo_roots=repo_roots, limits=limits,
        dependencies=dependencies, reviewed_pin_match=False,
        source_lease_held=False, source_reproof=_noop,
    )


def materialize_pinned_builder_packaging_source(
    *, wheel_path: Path | str, wheel_store_root: Path | str,
    source_store_root: Path | str, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    limits: BuilderPackagingSourceLimits = BuilderPackagingSourceLimits(),
) -> BuilderPackagingSourceMaterializationResult:
    """Persist the exact reviewed wheel and extracted tree without activation."""

    try:
        with wheel_module._retain_pinned_builder_packaging_wheel(
            wheel_path=wheel_path, wheel_store_root=wheel_store_root,
        ) as retained:
            result = _stable_materialize(
                payload=retained.payload, source_store_root=source_store_root,
                canonical_store=canonical_store, repo_roots=repo_roots,
                limits=limits, dependencies=_BuilderPackagingSourceDependencies(),
                reviewed_pin_match=True, source_lease_held=True,
                source_reproof=retained.reprove_and_admit,
            )
            return result
    except BuilderPackagingSourceMaterializationError:
        raise
    except Exception as exc:
        raise _wrapped(exc) from exc


def _stable_materialize(**kwargs: Any) -> BuilderPackagingSourceMaterializationResult:
    try:
        return _materialize_payload(**kwargs)
    except BuilderPackagingSourceMaterializationError:
        raise
    except (
        AcceptanceGuardError, BuilderPackagingSourceContractError,
        source_verifier.BuilderPackagingSourceVerificationError,
        BuilderPackagingSourceWriterError,
        QueryReplicaGenerationError, OSError, TypeError, ValueError,
    ) as exc:
        raise _wrapped(exc) from exc


__all__ = [
    "BuilderPackagingSourceMaterializationError",
    "materialize_pinned_builder_packaging_source",
]
