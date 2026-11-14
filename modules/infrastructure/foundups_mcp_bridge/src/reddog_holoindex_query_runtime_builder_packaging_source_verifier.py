"""Full wheel-to-tree verification for inert builder packaging sources."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from modules.infrastructure.shared_utilities.runtime_artifact_confined_byte_reader import (
    secure_read_confined_bytes_impl,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_text,
)
from modules.infrastructure.shared_utilities.runtime_artifact_windows_streams import (
    require_unnamed_data_stream_only,
)

from .reddog_holoindex_acceptance_guards import (
    AcceptanceGuardError,
)
from .reddog_holoindex_dependency_runtime_contract import (
    DependencyRuntimeLimits,
    canonical_json_bytes,
    digest_bytes,
)
from .reddog_holoindex_dependency_runtime_copy import (
    DependencyRuntimeSourcePlan,
    plan_dependency_runtime_snapshot,
)
from .reddog_holoindex_query_replica_orphans import OwnedDirectoryProof
from .reddog_holoindex_query_runtime_builder_packaging_source_contract import (
    BUILDER_PACKAGING_SOURCE_DESCRIPTOR_NAME,
    BUILDER_PACKAGING_SOURCE_INVENTORY_NAME,
    BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY,
    BUILDER_PACKAGING_SOURCE_WHEEL_DIRECTORY,
    BuilderPackagingSourceBinding,
    BuilderPackagingSourceContractError,
    BuilderPackagingSourceLimits,
    derive_builder_packaging_source_generation_id,
    require_builder_packaging_source_authority,
    stable_builder_packaging_source_error,
    validate_builder_packaging_source_descriptor,
    validate_builder_packaging_source_inventory,
)
from .reddog_holoindex_query_runtime_builder_packaging_source_topology_windows import (
    BuilderPackagingSourceTopologyError,
    pinned_builder_packaging_source_generation,
    retained_builder_packaging_source_topology,
    verify_builder_packaging_source_direct_topology,
    verify_builder_packaging_source_regular_file,
)
from . import reddog_holoindex_query_runtime_builder_packaging_wheel as wheel_module


class BuilderPackagingSourceVerificationError(RuntimeError):
    """Stable full-byte source-generation verification error."""


def _fail(code: str) -> None:
    raise BuilderPackagingSourceVerificationError(code)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if type(key) is not str or key in result:
            _fail("BUILDER_PACKAGING_SOURCE_JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _parse_canonical(raw: str, code: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw, object_pairs_hook=_strict_object,
            parse_constant=lambda _value: _fail(code),
        )
        if type(value) is not dict or canonical_json_bytes(value).decode("ascii") != raw:
            _fail(code)
        return value
    except BuilderPackagingSourceVerificationError:
        raise
    except Exception as exc:
        raise BuilderPackagingSourceVerificationError(code) from exc


def _read_contracts(
    generation: Path, limits: BuilderPackagingSourceLimits,
) -> tuple[dict[str, Any], dict[str, Any], bytes, bytes]:
    descriptor_text = secure_read_confined_text(
        generation / BUILDER_PACKAGING_SOURCE_DESCRIPTOR_NAME,
        allowed_root=generation, max_bytes=limits.max_descriptor_bytes,
    )
    inventory_text = secure_read_confined_text(
        generation / BUILDER_PACKAGING_SOURCE_INVENTORY_NAME,
        allowed_root=generation, max_bytes=limits.max_inventory_bytes,
    )
    try:
        descriptor = validate_builder_packaging_source_descriptor(
            _parse_canonical(descriptor_text, "BUILDER_PACKAGING_SOURCE_DESCRIPTOR_INVALID")
        )
        inventory = validate_builder_packaging_source_inventory(
            _parse_canonical(inventory_text, "BUILDER_PACKAGING_SOURCE_INVENTORY_INVALID")
        )
        return descriptor, inventory, descriptor_text.encode("ascii"), inventory_text.encode("ascii")
    except BuilderPackagingSourceContractError as exc:
        _fail(str(exc))


def _dependency_limits(limits: BuilderPackagingSourceLimits) -> DependencyRuntimeLimits:
    return DependencyRuntimeLimits(
        max_files=limits.max_files, max_directories=limits.max_directories + 1,
        max_directory_depth=limits.max_directory_depth,
        max_path_bytes=limits.max_path_bytes,
        max_total_path_bytes=limits.max_total_path_bytes,
        max_file_bytes=limits.max_file_bytes, max_total_bytes=limits.max_total_bytes,
        max_inventory_bytes=limits.max_inventory_bytes,
        max_descriptor_bytes=limits.max_descriptor_bytes,
    )


def _read_stored_wheel(
    generation: Path, descriptor: dict[str, Any], limits: BuilderPackagingSourceLimits,
):
    wheel_directory = generation / BUILDER_PACKAGING_SOURCE_WHEEL_DIRECTORY
    require_unnamed_data_stream_only(wheel_directory)
    entries = tuple(os.scandir(wheel_directory))
    if len(entries) != 1 or entries[0].name != wheel_module.PACKAGING_26_WHEEL_FILENAME:
        _fail("BUILDER_PACKAGING_SOURCE_WHEEL_TOPOLOGY_INVALID")
    wheel_path = Path(entries[0].path)
    verify_builder_packaging_source_regular_file(wheel_path)
    reviewed = descriptor["reviewed_pin_match"] is True
    expected_size = (
        wheel_module.PACKAGING_26_WHEEL_SIZE if reviewed else descriptor["wheel_size"]
    )
    expected_sha256 = (
        wheel_module.PACKAGING_26_WHEEL_SHA256
        if reviewed else descriptor["wheel_sha256"].removeprefix("sha256:")
    )
    payload, cursor = secure_read_confined_bytes_impl(
        wheel_path, allowed_root=generation,
        max_bytes=expected_size + 1,
    )
    if cursor != len(payload) or len(payload) != expected_size:
        _fail("BUILDER_PACKAGING_SOURCE_WHEEL_BYTES_INVALID")
    parsed = wheel_module._prove_packaging_wheel_payload_for_test(
        wheel_bytes=payload,
        expected_filename=wheel_module.PACKAGING_26_WHEEL_FILENAME,
        expected_size=expected_size, expected_sha256=expected_sha256,
    )
    _require_wheel_descriptor_binding(
        descriptor, parsed.proof, expected_size, expected_sha256,
    )
    return wheel_path, parsed


def _require_wheel_descriptor_binding(
    descriptor: dict[str, Any], proof: Any, expected_size: int,
    expected_sha256: str,
) -> None:
    expected = {
        "wheel_file": wheel_module.PACKAGING_26_WHEEL_FILENAME,
        "wheel_size": expected_size,
        "wheel_sha256": "sha256:" + expected_sha256,
        "central_directory_digest": proof.central_directory_digest,
        "member_set_digest": proof.member_set_digest,
        "metadata_digest": proof.metadata_digest,
        "wheel_metadata_digest": proof.wheel_metadata_digest,
        "record_digest": proof.record_digest,
        "owned_files_digest": proof.owned_files_digest,
        "member_count": proof.member_count,
        "expanded_bytes": proof.expanded_bytes,
    }
    if any(descriptor.get(key) != value for key, value in expected.items()):
        _fail("BUILDER_PACKAGING_SOURCE_WHEEL_BINDING_INVALID")


def _plan_site_packages(
    generation: Path, limits: BuilderPackagingSourceLimits,
) -> DependencyRuntimeSourcePlan:
    try:
        return plan_dependency_runtime_snapshot(
            generation / BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY,
            limits=_dependency_limits(limits),
        )
    except Exception as exc:
        raise BuilderPackagingSourceVerificationError(
            "BUILDER_PACKAGING_SOURCE_MEMBER_TREE_INVALID"
        ) from exc


def _require_inventory_matches_plan(
    inventory: dict[str, Any], plan: DependencyRuntimeSourcePlan,
) -> None:
    observed = tuple(
        {"path": item.relative_path, "size": item.size,
         "sha256": item.sha256, "role": "packaging_wheel_member"}
        for item in plan.files
    )
    if (
        tuple(inventory["directories"]) != plan.directories
        or tuple(inventory["files"]) != observed
    ):
        _fail("BUILDER_PACKAGING_SOURCE_INVENTORY_MISMATCH")


def _require_exact_member_bytes(generation: Path, parsed: Any) -> None:
    site = generation / BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY
    for member in parsed.members:
        payload, cursor = secure_read_confined_bytes_impl(
            site / Path(member.path), allowed_root=site,
            max_bytes=len(member.payload) + 1,
        )
        if cursor != len(payload) or payload != member.payload:
            _fail("BUILDER_PACKAGING_SOURCE_MEMBER_BYTES_MISMATCH")


def _binding(
    *, generation: Path, descriptor: dict[str, Any], descriptor_raw: bytes,
    inventory_raw: bytes, plan: DependencyRuntimeSourcePlan,
    reviewed_pin_match: bool,
) -> BuilderPackagingSourceBinding:
    generation_id = _derived_generation_id(descriptor, plan)
    if (
        descriptor["generation_id"] != generation_id
        or descriptor["inventory_digest"] != digest_bytes(inventory_raw)
        or descriptor["inventory_bytes"] != len(inventory_raw)
        or descriptor["dependency_tree_digest"] != plan.generation_id
        or descriptor["member_count"] != plan.file_count
        or descriptor["directory_count"] != len(plan.directories)
        or descriptor["expanded_bytes"] != plan.total_bytes
    ):
        _fail("BUILDER_PACKAGING_SOURCE_DESCRIPTOR_BINDING_INVALID")
    return BuilderPackagingSourceBinding(
        generation_root=generation,
        site_packages_root=generation / BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY,
        wheel_path=generation / BUILDER_PACKAGING_SOURCE_WHEEL_DIRECTORY / descriptor["wheel_file"],
        descriptor_path=generation / BUILDER_PACKAGING_SOURCE_DESCRIPTOR_NAME,
        descriptor_digest=digest_bytes(descriptor_raw), generation_id=generation_id,
        inventory_digest=descriptor["inventory_digest"],
        wheel_sha256=descriptor["wheel_sha256"],
        member_set_digest=descriptor["member_set_digest"],
        dependency_tree_digest=plan.generation_id, member_count=plan.file_count,
        directory_count=len(plan.directories), expanded_bytes=plan.total_bytes,
        reviewed_pin_match=reviewed_pin_match,
        source_lease_held_through_publication=False,
        source_lease_held_through_current_verification=False,
    )


def _derived_generation_id(
    descriptor: dict[str, Any], plan: DependencyRuntimeSourcePlan,
) -> str:
    return derive_builder_packaging_source_generation_id(
        wheel_filename=descriptor["wheel_file"], wheel_size=descriptor["wheel_size"],
        wheel_sha256=descriptor["wheel_sha256"],
        central_directory_digest=descriptor["central_directory_digest"],
        member_set_digest=descriptor["member_set_digest"],
        metadata_digest=descriptor["metadata_digest"],
        wheel_metadata_digest=descriptor["wheel_metadata_digest"],
        record_digest=descriptor["record_digest"],
        owned_files_digest=descriptor["owned_files_digest"],
        dependency_tree_digest_value=plan.generation_id,
        member_count=plan.file_count, directory_count=len(plan.directories),
        expanded_bytes=plan.total_bytes,
    )


def _verify_contents(
    generation: Path, expected_generation_id: str, bind_name: bool,
    limits: BuilderPackagingSourceLimits, require_reviewed_authority: bool,
) -> BuilderPackagingSourceBinding:
    verify_builder_packaging_source_direct_topology(generation)
    descriptor, inventory, descriptor_raw, inventory_raw = _read_contracts(generation, limits)
    require_builder_packaging_source_authority(
        descriptor, require_reviewed_authority,
        wheel_module.PACKAGING_26_WHEEL_SIZE,
        wheel_module.PACKAGING_26_WHEEL_SHA256,
    )
    reviewed_pin_match = (
        descriptor["wheel_size"] == wheel_module.PACKAGING_26_WHEEL_SIZE
        and descriptor["wheel_sha256"]
        == "sha256:" + wheel_module.PACKAGING_26_WHEEL_SHA256
    )
    if bind_name and generation.name != expected_generation_id.removeprefix("sha256:"):
        _fail("BUILDER_PACKAGING_SOURCE_DESCRIPTOR_BINDING_INVALID")
    _wheel_path, parsed = _read_stored_wheel(generation, descriptor, limits)
    plan = _plan_site_packages(generation, limits)
    _require_inventory_matches_plan(inventory, plan)
    _require_exact_member_bytes(generation, parsed)
    binding = _binding(
        generation=generation, descriptor=descriptor, descriptor_raw=descriptor_raw,
        inventory_raw=inventory_raw, plan=plan,
        reviewed_pin_match=reviewed_pin_match,
    )
    if binding.generation_id != expected_generation_id:
        _fail("BUILDER_PACKAGING_SOURCE_DESCRIPTOR_BINDING_INVALID")
    return binding


def _verify_generation(
    *, source_store_root: Path | str, generation_root: Path | str,
    expected_generation_id: str, bind_name: bool,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: BuilderPackagingSourceLimits, owned_root: OwnedDirectoryProof | None,
    require_reviewed_authority: bool,
) -> BuilderPackagingSourceBinding:
    limits.validate()
    with pinned_builder_packaging_source_generation(
        source_store_root=source_store_root, generation_root=generation_root,
        canonical_store=canonical_store, repo_roots=repo_roots,
        owned_root=owned_root,
    ) as pinned:
        first = _verify_contents(pinned.path, expected_generation_id, bind_name, limits, require_reviewed_authority)
        with retained_builder_packaging_source_topology(pinned, limits):
            second = _verify_contents(pinned.path, expected_generation_id, bind_name, limits, require_reviewed_authority)
            if first != second: _fail("BUILDER_PACKAGING_SOURCE_VERIFICATION_CHANGED")
            return second


def verify_builder_packaging_source_staging(
    *, source_store_root: Path | str, staging_root: Path | str,
    expected_generation_id: str, owned_root: OwnedDirectoryProof,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: BuilderPackagingSourceLimits = BuilderPackagingSourceLimits(),
) -> BuilderPackagingSourceBinding:
    return _stable_verify(
        source_store_root=source_store_root, generation_root=staging_root,
        expected_generation_id=expected_generation_id, bind_name=False,
        canonical_store=canonical_store, repo_roots=repo_roots, limits=limits,
        owned_root=owned_root, require_reviewed_authority=True,
    )


def verify_builder_packaging_source_generation(
    *, source_store_root: Path | str, generation_root: Path | str,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: BuilderPackagingSourceLimits = BuilderPackagingSourceLimits(),
    expected_generation_id: str | None = None,
) -> BuilderPackagingSourceBinding:
    expected = expected_generation_id or f"sha256:{Path(str(generation_root)).name}"
    return _stable_verify(
        source_store_root=source_store_root, generation_root=generation_root,
        expected_generation_id=expected, bind_name=True,
        canonical_store=canonical_store, repo_roots=repo_roots, limits=limits,
        owned_root=None, require_reviewed_authority=True,
    )


def _verify_builder_packaging_source_staging_for_test(
    *, source_store_root: Path | str, staging_root: Path | str,
    expected_generation_id: str, owned_root: OwnedDirectoryProof,
    canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
    limits: BuilderPackagingSourceLimits,
) -> BuilderPackagingSourceBinding:
    return _stable_verify(
        source_store_root=source_store_root, generation_root=staging_root,
        expected_generation_id=expected_generation_id, bind_name=False,
        canonical_store=canonical_store, repo_roots=repo_roots, limits=limits,
        owned_root=owned_root, require_reviewed_authority=False,
    )


def _verify_builder_packaging_source_generation_for_test(
    *, source_store_root: Path | str, generation_root: Path | str,
    expected_generation_id: str, canonical_store: Path | str,
    repo_roots: tuple[Path | str, ...], limits: BuilderPackagingSourceLimits,
) -> BuilderPackagingSourceBinding:
    return _stable_verify(
        source_store_root=source_store_root, generation_root=generation_root,
        expected_generation_id=expected_generation_id, bind_name=True,
        canonical_store=canonical_store, repo_roots=repo_roots, limits=limits,
        owned_root=None, require_reviewed_authority=False,
    )


def _stable_verify(**kwargs: Any) -> BuilderPackagingSourceBinding:
    try:
        return _verify_generation(**kwargs)
    except BuilderPackagingSourceVerificationError:
        raise
    except (
        AcceptanceGuardError, BuilderPackagingSourceContractError,
        BuilderPackagingSourceTopologyError,
        OSError, TypeError, ValueError,
    ) as exc:
        raise BuilderPackagingSourceVerificationError(stable_builder_packaging_source_error(exc, "BUILDER_PACKAGING_SOURCE_VERIFICATION_FAILED")) from exc


__all__ = [
    "BuilderPackagingSourceVerificationError",
    "verify_builder_packaging_source_generation",
    "verify_builder_packaging_source_staging",
]
