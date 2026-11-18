"""Derive and independently verify inert runtime ABI attestation evidence."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_text,
    validate_runtime_artifact_path,
)
from modules.infrastructure.shared_utilities.runtime_artifact_windows_streams import (
    require_unnamed_data_stream_only,
)

from .reddog_holoindex_base_runtime_contract import (
    INVENTORY_NAME as BASE_INVENTORY_NAME,
    parse_canonical_json as parse_base_json,
    validate_inventory as validate_base_inventory,
)
from .reddog_holoindex_acceptance_guards import (
    AcceptanceGuardError,
    StoreProof,
    prove_existing_isolated_store,
    verify_store_proof,
)
from .reddog_holoindex_dependency_runtime_contract import (
    INVENTORY_NAME as DEPENDENCY_INVENTORY_NAME,
    canonical_json_bytes,
    digest_bytes,
    is_digest,
    validate_inventory as validate_dependency_inventory,
)
from .reddog_holoindex_query_replica_orphans import OwnedDirectoryProof
from .reddog_holoindex_runtime_abi_contract import (
    BASE_ROLE,
    DEPENDENCY_ROLE,
    DESCRIPTOR_NAME,
    INVENTORY_NAME,
    RuntimeAbiBinding,
    RuntimeAbiContractError,
    RuntimeAbiLimits,
    runtime_abi_descriptor,
    runtime_abi_inventory,
    stable_error_code,
    validate_runtime_abi_descriptor,
    validate_runtime_abi_inventory,
)
from .reddog_holoindex_runtime_abi_metadata import (
    DistributionEvidence,
    RuntimeAbiMetadataError,
    bound_payload,
    distribution_evidence,
)
from .reddog_holoindex_runtime_abi_graph import (
    NativeNode,
    derive_declared_abi_rows,
)
from .reddog_holoindex_runtime_composition_contract import (
    RuntimeCompositionBinding,
)
from .reddog_holoindex_runtime_composition_descriptor import (
    RuntimeCompositionDescriptorError,
    verify_runtime_composition_generation,
)
from .reddog_holoindex_windows_pe import (
    AMD64_MACHINE,
    PE32_PLUS_MAGIC,
    PEFormatError,
    PEImage,
    PELimits,
    parse_pe_image,
)


class RuntimeAbiDescriptorError(RuntimeError):
    """Stable ABI derivation or generation-verification error."""


def _fail(code: str) -> None:
    raise RuntimeAbiDescriptorError(code)


@dataclass(frozen=True)
class RuntimeAbiEvidence:
    composition: RuntimeCompositionBinding
    inventory: Mapping[str, Any]
    descriptor: Mapping[str, Any]


@dataclass
class _AggregateUsage:
    import_libraries: int = 0
    import_thunk_entries: int = 0
    exports: int = 0
    name_bytes: int = 0


def build_runtime_abi_evidence(
    *, composition_kwargs: Mapping[str, Any],
    abi_limits: RuntimeAbiLimits = RuntimeAbiLimits(),
    pe_limits: PELimits = PELimits(),
) -> RuntimeAbiEvidence:
    """Reprove composition, derive ABI facts, then reprove composition again."""

    try:
        before = verify_runtime_composition_generation(**dict(composition_kwargs))
        inventory = _derive_inventory(before, abi_limits, pe_limits)
        after = verify_runtime_composition_generation(**dict(composition_kwargs))
        if after != before:
            _fail("RUNTIME_ABI_COMPOSITION_MUTATED_DURING_SCAN")
        descriptor = runtime_abi_descriptor(
            composition_generation_id=before.generation_id,
            composition_descriptor_digest=before.descriptor_digest,
            inventory=inventory,
        )
        return RuntimeAbiEvidence(after, inventory, descriptor)
    except RuntimeAbiDescriptorError:
        raise
    except (
        OSError, TypeError, ValueError, UnicodeError, PEFormatError,
        RuntimeAbiMetadataError,
        RuntimeAbiContractError, RuntimeCompositionDescriptorError,
    ) as exc:
        raise RuntimeAbiDescriptorError(
            stable_error_code(exc, "RUNTIME_ABI_EVIDENCE_FAILED")
        ) from exc


def verify_runtime_abi_generation(
    *, abi_store_root: Path | str, generation_root: Path | str,
    composition_kwargs: Mapping[str, Any],
    abi_limits: RuntimeAbiLimits = RuntimeAbiLimits(),
    pe_limits: PELimits = PELimits(), expected_generation_id: str | None = None,
) -> RuntimeAbiBinding:
    """Verify stored canonical evidence against a fresh exact component scan."""

    evidence = build_runtime_abi_evidence(
        composition_kwargs=composition_kwargs, abi_limits=abi_limits,
        pe_limits=pe_limits,
    )
    expected = expected_generation_id or f"sha256:{Path(str(generation_root)).name}"
    return _verify_generation(
        abi_store_root=abi_store_root, generation_root=generation_root,
        expected_generation_id=expected, evidence=evidence,
        abi_limits=abi_limits, owned_root=None, bind_canonical_name=True,
        canonical_store=composition_kwargs["canonical_store"],
        repo_roots=tuple(composition_kwargs["repo_roots"]),
    )


def verify_runtime_abi_staging(
    *, abi_store_root: Path | str, staging_root: Path | str,
    expected_generation_id: str, owned_root: OwnedDirectoryProof,
    evidence: RuntimeAbiEvidence, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
    abi_limits: RuntimeAbiLimits = RuntimeAbiLimits(),
) -> RuntimeAbiBinding:
    """Verify unpublished process-owned evidence without rescanning components."""

    return _verify_generation(
        abi_store_root=abi_store_root, generation_root=staging_root,
        expected_generation_id=expected_generation_id, evidence=evidence,
        abi_limits=abi_limits, owned_root=owned_root, bind_canonical_name=False,
        canonical_store=canonical_store, repo_roots=repo_roots,
    )


def _derive_inventory(
    composition: RuntimeCompositionBinding, limits: RuntimeAbiLimits,
    pe_limits: PELimits,
) -> Mapping[str, Any]:
    limits.validate()
    base_rows = _component_inventory(
        composition.base_runtime.generation_root / BASE_INVENTORY_NAME,
        composition.base_runtime.generation_root,
        limits.max_inventory_bytes, validate_base_inventory, parse_base_json,
    )["files"]
    dependency_rows = _component_inventory(
        composition.dependency_runtime.generation_root / DEPENDENCY_INVENTORY_NAME,
        composition.dependency_runtime.generation_root,
        limits.max_inventory_bytes, validate_dependency_inventory, _parse_json,
    )["files"]
    native_dependency = [row for row in dependency_rows if _native_path(row["path"])]
    distributions = distribution_evidence(
        composition.dependency_runtime.site_packages_root,
        dependency_rows, native_dependency, limits,
    )
    nodes = _native_nodes(
        composition, base_rows, native_dependency, distributions,
        limits, pe_limits,
    )
    rows = derive_declared_abi_rows(nodes, limits)
    return runtime_abi_inventory(
        composition_generation_id=composition.generation_id,
        distributions=list(distributions.rows), native_files=rows,
    )


def _component_inventory(
    path: Path, root: Path, maximum: int, validator, parser,
) -> Mapping[str, Any]:
    raw = secure_read_confined_text(path, allowed_root=root, max_bytes=maximum)
    return validator(parser(raw))


def _native_nodes(
    composition: RuntimeCompositionBinding, base_rows: list[Mapping[str, Any]],
    dependency_rows: list[Mapping[str, Any]], distributions: DistributionEvidence,
    limits: RuntimeAbiLimits, pe_limits: PELimits,
) -> list[NativeNode]:
    selected = [
        (BASE_ROLE, composition.base_runtime.base_prefix_root, row, "", "")
        for row in base_rows if _native_path(row["path"])
    ] + [
        (
            DEPENDENCY_ROLE, composition.dependency_runtime.site_packages_root, row,
            *distributions.owner_by_path[str(row["path"]).casefold()],
        )
        for row in dependency_rows
    ]
    if (
        not selected or len(selected) > limits.max_native_files
        or sum(int(row["size"]) for _role, _root, row, _dist, _tag in selected)
        > limits.max_total_native_bytes
    ):
        _fail("RUNTIME_ABI_NATIVE_FILE_LIMIT_EXCEEDED")
    nodes: list[NativeNode] = []
    usage = _AggregateUsage()
    for role, root, row, distribution, wheel_tag in selected:
        payload = bound_payload(root, row, limits.max_native_file_bytes)
        try:
            image = parse_pe_image(
                payload, _remaining_pe_limits(pe_limits, limits, usage)
            )
        except PEFormatError as exc:
            raise RuntimeAbiDescriptorError(f"RUNTIME_ABI_PE_INVALID:{exc}") from exc
        _accumulate_usage(usage, image, limits)
        if image.machine != AMD64_MACHINE or image.optional_magic != PE32_PLUS_MAGIC:
            _fail("RUNTIME_ABI_PE_MACHINE_INCOMPATIBLE")
        suffix = PurePosixPath(str(row["path"])).suffix.casefold()
        if image.is_dll is not (suffix in {".dll", ".pyd"}):
            _fail("RUNTIME_ABI_PE_IMAGE_KIND_INVALID")
        nodes.append(NativeNode(
            role, str(row["path"]), row, image, distribution, wheel_tag
        ))
    nodes.sort(key=lambda node: (node.role.casefold(), node.path.casefold(), node.path))
    return nodes


def _remaining_pe_limits(
    pe_limits: PELimits, limits: RuntimeAbiLimits, usage: _AggregateUsage,
) -> PELimits:
    return replace(
        pe_limits,
        max_import_libraries=max(1, min(
            pe_limits.max_import_libraries,
            limits.max_total_import_libraries - usage.import_libraries,
        )),
        max_import_thunk_entries=max(1, min(
            pe_limits.max_import_thunk_entries,
            limits.max_total_import_thunk_entries - usage.import_thunk_entries,
        )),
        max_exports=max(1, min(
            pe_limits.max_exports, limits.max_total_exports - usage.exports,
        )),
        max_decoded_name_bytes=max(1, min(
            pe_limits.max_decoded_name_bytes,
            limits.max_total_name_bytes - usage.name_bytes,
        )),
    )


def _accumulate_usage(
    usage: _AggregateUsage, image: PEImage, limits: RuntimeAbiLimits,
) -> None:
    usage.import_libraries += image.import_descriptor_count
    usage.import_thunk_entries += image.import_thunk_entry_count
    usage.exports += image.export_table_entry_count
    usage.name_bytes += image.decoded_name_byte_count
    if (
        usage.import_libraries > limits.max_total_import_libraries
        or usage.import_thunk_entries > limits.max_total_import_thunk_entries
        or usage.exports > limits.max_total_exports
        or usage.name_bytes > limits.max_total_name_bytes
    ):
        _fail("RUNTIME_ABI_AGGREGATE_PE_LIMIT_EXCEEDED")


def _verify_generation(
    *, abi_store_root: Path | str, generation_root: Path | str,
    expected_generation_id: str, evidence: RuntimeAbiEvidence,
    abi_limits: RuntimeAbiLimits, owned_root: OwnedDirectoryProof | None,
    bind_canonical_name: bool, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
) -> RuntimeAbiBinding:
    try:
        abi_limits.validate()
        if not is_digest(expected_generation_id):
            _fail("RUNTIME_ABI_GENERATION_ID_INVALID")
        store = _verified_store(
            abi_store_root, canonical_store=canonical_store, repo_roots=repo_roots
        )
        generation = _literal_generation(generation_root, store, repo_roots)
        metadata = os.lstat(generation)
        if owned_root is not None and (
            generation != owned_root.path or metadata.st_dev != owned_root.device
            or metadata.st_ino != owned_root.inode
        ):
            _fail("RUNTIME_ABI_STAGING_IDENTITY_CHANGED")
        if bind_canonical_name and generation.name != expected_generation_id[7:]:
            _fail("RUNTIME_ABI_GENERATION_NAME_INVALID")
        _generation_topology(generation)
        inventory_raw = secure_read_confined_text(
            generation / INVENTORY_NAME, allowed_root=generation,
            max_bytes=abi_limits.max_inventory_bytes,
        )
        descriptor_raw = secure_read_confined_text(
            generation / DESCRIPTOR_NAME, allowed_root=generation,
            max_bytes=abi_limits.max_descriptor_bytes,
        )
        inventory = validate_runtime_abi_inventory(_parse_json(inventory_raw), abi_limits)
        descriptor = validate_runtime_abi_descriptor(_parse_json(descriptor_raw))
        if inventory != evidence.inventory or descriptor != evidence.descriptor:
            _fail("RUNTIME_ABI_EVIDENCE_BINDING_MISMATCH")
        if descriptor["generation_id"] != expected_generation_id:
            _fail("RUNTIME_ABI_GENERATION_ID_INVALID")
        verify_store_proof(
            store, canonical_store=canonical_store, repo_roots=repo_roots
        )
        return _binding(generation, inventory_raw, descriptor_raw, descriptor)
    except RuntimeAbiDescriptorError:
        raise
    except (
        AcceptanceGuardError, OSError, TypeError, ValueError, RuntimeAbiContractError,
    ) as exc:
        raise RuntimeAbiDescriptorError(
            stable_error_code(exc, "RUNTIME_ABI_GENERATION_VERIFICATION_FAILED")
        ) from exc


def _verified_store(
    root: Path | str, *, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...],
) -> StoreProof:
    store = prove_existing_isolated_store(
        root, canonical_store=canonical_store, repo_roots=repo_roots
    )
    verify_store_proof(store, canonical_store=canonical_store, repo_roots=repo_roots)
    return store


def _literal_generation(
    value: Path | str, store: StoreProof, repo_roots: tuple[Path | str, ...],
) -> Path:
    raw = str(value or "")
    if not raw or "\x00" in raw or not Path(raw).is_absolute():
        _fail("RUNTIME_ABI_GENERATION_PATH_INVALID")
    for repo_root in repo_roots:
        validate_runtime_artifact_path(raw, repo_root=repo_root, allowed_root=store.path)
    path = Path(os.path.abspath(raw))
    if os.path.normcase(str(path.parent)) != os.path.normcase(str(store.path)):
        _fail("RUNTIME_ABI_GENERATION_PATH_INVALID")
    metadata = os.lstat(path)
    if not stat.S_ISDIR(metadata.st_mode) or _is_link(path, metadata):
        _fail("RUNTIME_ABI_GENERATION_PATH_INVALID")
    return path


def _generation_topology(root: Path) -> None:
    expected = {INVENTORY_NAME, DESCRIPTOR_NAME, ".runtime-abi-publication-orphans"}
    entries = tuple(os.scandir(root))
    if {entry.name for entry in entries} != expected:
        _fail("RUNTIME_ABI_GENERATION_TOPOLOGY_INVALID")
    for entry in entries:
        path = Path(entry.path)
        metadata = os.lstat(path)
        directory = entry.name.startswith(".")
        if _is_link(path, metadata) or stat.S_ISDIR(metadata.st_mode) is not directory:
            _fail("RUNTIME_ABI_GENERATION_TOPOLOGY_INVALID")
        require_unnamed_data_stream_only(path)
    if tuple(os.scandir(root / ".runtime-abi-publication-orphans")):
        _fail("RUNTIME_ABI_GENERATION_TOPOLOGY_INVALID")


def _binding(
    root: Path, inventory_raw: str, descriptor_raw: str,
    descriptor: Mapping[str, Any],
) -> RuntimeAbiBinding:
    truth = {
        name: bool(descriptor[name]) for name in (
            "artifact_bytes_independently_reverified", "declared_pe_metadata_verified",
            "declared_pe_machine_compatible", "wheel_tag_compatibility_verified",
            "record_ownership_verified", "declared_python_link_abi_verified",
            "native_loader_closure_verified", "deterministic_effects_verified",
            "preimport_bootstrap_verified", "signature_verified", "write_denial_verified",
            "activation_eligible", "exact_runtime_closure_verified",
        )
    }
    composition = descriptor["runtime_composition"]
    return RuntimeAbiBinding(
        generation_root=root, descriptor_path=root / DESCRIPTOR_NAME,
        descriptor_digest=digest_bytes(descriptor_raw.encode("ascii")),
        inventory_path=root / INVENTORY_NAME,
        inventory_digest=digest_bytes(inventory_raw.encode("ascii")),
        generation_id=str(descriptor["generation_id"]),
        runtime_composition_generation_id=str(composition["generation_id"]),
        runtime_composition_descriptor_digest=str(composition["descriptor_digest"]),
        native_file_count=int(descriptor["native_file_count"]),
        native_total_bytes=int(descriptor["native_total_bytes"]),
        distribution_count=int(descriptor["distribution_count"]), **truth,
    )


def _parse_json(raw: str) -> dict[str, Any]:
    def strict(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if type(key) is not str or key in result:
                _fail("RUNTIME_ABI_JSON_DUPLICATE_KEY")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=strict, parse_constant=lambda _v: _fail(
            "RUNTIME_ABI_JSON_INVALID"
        ))
    except RuntimeAbiDescriptorError:
        raise
    except Exception:
        _fail("RUNTIME_ABI_JSON_INVALID")
    if type(value) is not dict or canonical_json_bytes(value).decode("ascii") != raw:
        _fail("RUNTIME_ABI_JSON_INVALID")
    return value


def _native_path(value: object) -> bool:
    return PurePosixPath(str(value)).suffix.casefold() in {".exe", ".dll", ".pyd"}


def _is_link(path: Path, metadata: os.stat_result) -> bool:
    return bool(
        stat.S_ISLNK(metadata.st_mode)
        or int(getattr(metadata, "st_file_attributes", 0))
        & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        or getattr(path, "is_junction", lambda: False)()
    )


__all__ = [
    "RuntimeAbiDescriptorError", "RuntimeAbiEvidence", "build_runtime_abi_evidence",
    "verify_runtime_abi_generation", "verify_runtime_abi_staging",
]
