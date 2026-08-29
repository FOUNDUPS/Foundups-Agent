"""Held-descriptor admission for the reviewed RedDog builder packaging wheel."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import os
from pathlib import Path
import stat
from typing import Mapping

from modules.infrastructure.shared_utilities.runtime_artifact_windows_streams import (
    require_unnamed_data_stream_only,
)

from .reddog_holoindex_acceptance_windows import (
    open_windows_directory_lease,
    open_windows_file_lease_descriptor,
    open_windows_source_file_lease,
    validate_windows_directory_lease,
    validate_windows_directory_lease_exact_path,
    validate_windows_file_descriptor_exact_path,
    validate_windows_file_lease,
)
from .reddog_holoindex_packaging_distribution_contract import (
    PackagingDistributionContractError,
    prove_packaging_distribution_members,
)
from .reddog_holoindex_strict_wheel_archive import (
    StrictWheelArchiveError,
    StrictWheelLimits,
    parse_strict_wheel_archive,
)


PACKAGING_26_WHEEL_FILENAME = "packaging-26.0-py3-none-any.whl"
PACKAGING_26_WHEEL_SIZE = 74_366
PACKAGING_26_WHEEL_SHA256 = (
    "b36f1fef9334a5588b4166f8bcd26a14e521f2b55e6b9de3aaa80d3ff7a37529"
)
BuilderPackagingWheelLimits = StrictWheelLimits


class BuilderPackagingWheelError(RuntimeError):
    """Stable path-free reviewed-wheel admission error."""


def _fail(code: str) -> None:
    raise BuilderPackagingWheelError(code)


@dataclass(frozen=True)
class _BuilderPackagingWheelByteProof:
    """Internal parser result with no reviewed-pin or held-lease authority."""

    central_directory_digest: str
    member_set_digest: str
    metadata_digest: str
    wheel_metadata_digest: str
    record_digest: str
    owned_files_digest: str
    distribution_name: str
    distribution_version: str
    wheel_tag: str
    member_count: int
    expanded_bytes: int
    compressed_bytes: int


@dataclass(frozen=True)
class BuilderPackagingWheelAdmission:
    schema_version: str
    wheel_filename: str
    wheel_size: int
    wheel_sha256: str
    central_directory_digest: str
    member_set_digest: str
    metadata_digest: str
    wheel_metadata_digest: str
    record_digest: str
    owned_files_digest: str
    distribution_name: str
    distribution_version: str
    wheel_tag: str
    member_count: int
    expanded_bytes: int
    compressed_bytes: int
    reviewed_pin_match: bool = True
    source_lease_held_during_admission: bool = True
    strict_archive_verified: bool = True
    record_ownership_verified: bool = True
    source_only_topology_verified: bool = True
    official_provenance_authenticated: bool = False
    signature_verified: bool = False
    extraction_performed: bool = False
    publication_performed: bool = False
    import_authority_verified: bool = False
    child_execution_authorized: bool = False
    deterministic_effects_verified: bool = False
    write_denial_verified: bool = False
    activation_eligible: bool = False
    a_grade_verified: bool = False
    retrieval_rsi_verified: bool = False
    builder_runtime_authenticated: bool = False
    preimport_loader_authority_verified: bool = False
    native_loader_closure_verified: bool = False
    subprocess_closure_verified: bool = False
    exact_runtime_closure_verified: bool = False
    network_performed: bool = False
    download_performed: bool = False
    installation_performed: bool = False

    @property
    def public_binding(self) -> Mapping[str, object]:
        return asdict(self)


def admit_pinned_builder_packaging_wheel(
    *,
    wheel_path: Path | str,
    wheel_store_root: Path | str,
    limits: BuilderPackagingWheelLimits = BuilderPackagingWheelLimits(),
) -> BuilderPackagingWheelAdmission:
    """Admit the exact repository-reviewed wheel without reopening its path."""

    if os.name != "nt":
        _fail("BUILDER_PACKAGING_WHEEL_WINDOWS_REQUIRED")
    _require_limits(limits)
    path, root = _approved_paths(wheel_path, wheel_store_root)
    directory_lease = file_lease = None
    try:
        expected_identity = _initial_file_identity(path)
        directory_lease = open_windows_directory_lease(
            root, require_delete_authority=False,
        )
        validate_windows_directory_lease_exact_path(directory_lease)
        require_unnamed_data_stream_only(root)
        file_lease = open_windows_source_file_lease(
            path, directory_lease, expected_identity=expected_identity,
        )
        require_unnamed_data_stream_only(path)
        payload = _read_leased_bytes(file_lease, path, limits)
        proof = _prove_packaging_wheel_bytes_for_test(
            wheel_bytes=payload,
            expected_filename=PACKAGING_26_WHEEL_FILENAME,
            expected_size=PACKAGING_26_WHEEL_SIZE,
            expected_sha256=PACKAGING_26_WHEEL_SHA256,
            limits=limits,
        )
        _final_reproof(directory_lease, file_lease, path, expected_identity)
        return _public_admission(proof)
    except BuilderPackagingWheelError:
        raise
    except (StrictWheelArchiveError, PackagingDistributionContractError) as exc:
        _fail(str(exc))
    except Exception:
        _fail("BUILDER_PACKAGING_WHEEL_ADMISSION_UNAVAILABLE")
    finally:
        if file_lease is not None:
            file_lease.close()
        if directory_lease is not None:
            directory_lease.close()


def _prove_packaging_wheel_bytes_for_test(
    *,
    wheel_bytes: bytes,
    expected_filename: str,
    expected_size: int,
    expected_sha256: str,
    limits: BuilderPackagingWheelLimits = BuilderPackagingWheelLimits(),
) -> _BuilderPackagingWheelByteProof:
    """Private byte parser seam with no reviewed-pin or held-lease claim."""

    _require_limits(limits)
    if (
        expected_filename != PACKAGING_26_WHEEL_FILENAME
        or type(expected_size) is not int
        or expected_size <= 0
        or type(expected_sha256) is not str
        or len(expected_sha256) != 64
        or any(character not in "0123456789abcdef" for character in expected_sha256)
        or type(wheel_bytes) is not bytes
        or len(wheel_bytes) != expected_size
        or hashlib.sha256(wheel_bytes).hexdigest() != expected_sha256
    ):
        _fail("BUILDER_PACKAGING_WHEEL_PIN_MISMATCH")
    try:
        archive = parse_strict_wheel_archive(wheel_bytes, limits=limits)
        members = {member.path: member.payload for member in archive.members}
        distribution = prove_packaging_distribution_members(members)
    except (StrictWheelArchiveError, PackagingDistributionContractError) as exc:
        _fail(str(exc))
    return _BuilderPackagingWheelByteProof(
        central_directory_digest=archive.central_directory_digest,
        member_set_digest=archive.member_set_digest,
        metadata_digest=distribution.metadata_digest,
        wheel_metadata_digest=distribution.wheel_metadata_digest,
        record_digest=distribution.record_digest,
        owned_files_digest=distribution.owned_files_digest,
        distribution_name=distribution.distribution_name,
        distribution_version=distribution.distribution_version,
        wheel_tag=distribution.wheel_tag,
        member_count=len(archive.members),
        expanded_bytes=archive.expanded_bytes,
        compressed_bytes=archive.compressed_bytes,
    )


def _public_admission(
    proof: _BuilderPackagingWheelByteProof,
) -> BuilderPackagingWheelAdmission:
    if type(proof) is not _BuilderPackagingWheelByteProof:
        _fail("BUILDER_PACKAGING_WHEEL_BYTE_PROOF_INVALID")
    return BuilderPackagingWheelAdmission(
        schema_version="reddog_builder_packaging_wheel_admission.v1",
        wheel_filename=PACKAGING_26_WHEEL_FILENAME,
        wheel_size=PACKAGING_26_WHEEL_SIZE,
        wheel_sha256="sha256:" + PACKAGING_26_WHEEL_SHA256,
        **asdict(proof),
    )


def _require_limits(limits: object) -> None:
    if type(limits) is not StrictWheelLimits:
        _fail("STRICT_WHEEL_LIMIT_INVALID")
    try:
        limits.validate()
    except StrictWheelArchiveError as exc:
        _fail(str(exc))


def _approved_paths(
    wheel_path: Path | str, wheel_store_root: Path | str,
) -> tuple[Path, Path]:
    if not isinstance(wheel_path, (Path, str)) or not isinstance(wheel_store_root, (Path, str)):
        _fail("BUILDER_PACKAGING_WHEEL_PATH_INVALID")
    path, root = Path(wheel_path), Path(wheel_store_root)
    if (
        not path.is_absolute() or not root.is_absolute()
        or path.drive.rstrip(":").upper() not in {"O", "E"}
        or root.drive.rstrip(":").upper() not in {"O", "E"}
        or path.parent != root
        or path.name != PACKAGING_26_WHEEL_FILENAME
    ):
        _fail("BUILDER_PACKAGING_WHEEL_PATH_INVALID")
    try:
        resolved_root = root.resolve(strict=True)
        resolved_path = path.resolve(strict=True)
    except OSError:
        _fail("BUILDER_PACKAGING_WHEEL_PATH_INVALID")
    if resolved_root != root.absolute() or resolved_path != path.absolute():
        _fail("BUILDER_PACKAGING_WHEEL_PATH_INVALID")
    return path, root


def _initial_file_identity(path: Path) -> tuple[int, int, int, int, int]:
    metadata = os.lstat(path)
    identity = (
        int(metadata.st_dev), int(metadata.st_ino), int(metadata.st_size),
        int(metadata.st_mtime_ns), int(getattr(metadata, "st_nlink", 1)),
    )
    if not stat.S_ISREG(metadata.st_mode) or identity[4] != 1:
        _fail("BUILDER_PACKAGING_WHEEL_SOURCE_INVALID")
    return identity


def _read_leased_bytes(file_lease, path: Path, limits: StrictWheelLimits) -> bytes:
    descriptor = open_windows_file_lease_descriptor(file_lease)
    try:
        validate_windows_file_descriptor_exact_path(descriptor, path)
        chunks, total = [], 0
        while True:
            chunk = os.read(descriptor, min(64 * 1024, limits.max_archive_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > limits.max_archive_bytes:
                _fail("STRICT_WHEEL_ARCHIVE_SIZE_INVALID")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _final_reproof(directory_lease, file_lease, path: Path, expected_identity) -> None:
    validate_windows_directory_lease(directory_lease)
    if validate_windows_file_lease(file_lease) != expected_identity:
        _fail("BUILDER_PACKAGING_WHEEL_SOURCE_MUTATED")
    descriptor = open_windows_file_lease_descriptor(file_lease)
    try:
        validate_windows_file_descriptor_exact_path(descriptor, path)
    finally:
        os.close(descriptor)


__all__ = [
    "BuilderPackagingWheelAdmission",
    "BuilderPackagingWheelError",
    "BuilderPackagingWheelLimits",
    "PACKAGING_26_WHEEL_FILENAME",
    "PACKAGING_26_WHEEL_SHA256",
    "PACKAGING_26_WHEEL_SIZE",
    "admit_pinned_builder_packaging_wheel",
]
