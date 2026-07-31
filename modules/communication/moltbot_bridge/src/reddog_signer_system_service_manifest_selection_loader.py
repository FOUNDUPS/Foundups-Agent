"""Root-owned current-generation selection loader for the signer system service."""

from __future__ import annotations

import json
import os
import stat
import sys
import time
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water_reader import (
    AtomicSignerRuntimeGenerationHighWaterReader,
)
from modules.communication.moltbot_bridge.src.reddog_current_generation_manifest_launch_selection import (
    _issue_current_generation_launch_owner_authority,
    create_current_generation_manifest_launch_selection_boundary,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
    ascii_deep,
    digest,
    is_sha256,
    raw_digest,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_launch_selection import (
    CONFIG_FILENAME,
    RUN_PACKET_FILENAME,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_reader import (
    DurableSignerRuntimeGenerationReader,
    create_signer_runtime_generation_high_water_reader_authority,
    create_signer_runtime_generation_reader_authority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_verifier_authority import (
    create_signer_runtime_generation_verifier_authority,
    require_signer_runtime_generation_verifier_authority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_witness_binding import (
    SignerRuntimeGenerationWitnessBinding,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityReader,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


SCHEMA_VERSION = "reddog_signer_system_service_owner_config.v1"
MAX_OWNER_CONFIG_BYTES = 64 * 1024
ROOT_UID = 0
FIELDS = frozenset(
    {
        "schema_version",
        "config_id",
        "repo_root_digest",
        "runtime_root",
        "anchor_path",
        "anchor_id",
        "generation_public_key",
        "generation_authenticator_id",
        "generation_key_epoch",
        "generation_signer_public_key_fingerprint",
        "high_water_root",
        "high_water_path",
        "high_water_store_id",
        "high_water_durability_receipt_id",
        "witness_root",
        "witness_path",
        "witness_store_id",
        "witness_durability_receipt_id",
    }
)


def load_system_service_manifest_selection(
    *,
    owner_config_path: Path | str,
    repo_root: Path,
    config_path: Path | None = None,
    run_packet_path: Path | None = None,
) -> tuple[object, Any]:
    """Load root-owned trust, reconstruct read-only readers, and select current."""

    repo = Path(repo_root).resolve()
    owner = _load_owner_config(owner_config_path, repo=repo)
    runtime = validate_runtime_root_path(owner["runtime_root"], repo_root=repo)
    _require_cli_paths(runtime, config_path, run_packet_path)
    verifier_authority, verifier_boundary = (
        create_signer_runtime_generation_verifier_authority(
            str(owner["generation_public_key"])
        )
    )
    verifier = require_signer_runtime_generation_verifier_authority(
        verifier_authority, verifier_boundary
    )
    if verifier.authenticator_id != owner["generation_authenticator_id"]:
        raise RuntimeArtifactManifestError(
            "signer_owner_generation_authenticator_mismatch"
        )
    reader_authority, reader_boundary = _build_generation_reader(
        owner,
        repo=repo,
        runtime=runtime,
        verifier_authority=verifier_authority,
        verifier_boundary=verifier_boundary,
    )
    owner_authority, owner_boundary = (
        _issue_current_generation_launch_owner_authority(
            repo_root=repo,
            runtime_root=runtime,
            anchor_id=str(owner["anchor_id"]),
            authenticator_id=verifier.authenticator_id,
            high_water_store_id=str(owner["high_water_store_id"]),
            high_water_durability_receipt_id=str(
                owner["high_water_durability_receipt_id"]
            ),
            owner_config_id=str(owner["config_id"]),
        )
    )
    boundary = create_current_generation_manifest_launch_selection_boundary(
        owner_authority=owner_authority,
        owner_authority_boundary=owner_boundary,
        generation_reader_authority=reader_authority,
        generation_reader_authority_boundary=reader_boundary,
    )
    return boundary.select({}, now_epoch=int(time.time())), boundary


def _build_generation_reader(
    owner: Mapping[str, Any],
    *,
    repo: Path,
    runtime: Path,
    verifier_authority: object,
    verifier_boundary: Any,
) -> tuple[object, Any]:
    witness = SqliteMonotonicAuthorityReader(
        owner["witness_path"],
        allowed_root=owner["witness_root"],
        repo_root=repo,
        store_id=str(owner["witness_store_id"]),
        durability_receipt_id=str(
            owner["witness_durability_receipt_id"]
        ),
    )
    binding = _witness_binding(owner, runtime=runtime)
    high_water = AtomicSignerRuntimeGenerationHighWaterReader(
        owner["high_water_path"],
        allowed_root=owner["high_water_root"],
        repo_root=repo,
        store_id=str(owner["high_water_store_id"]),
        durability_receipt_id=str(
            owner["high_water_durability_receipt_id"]
        ),
        verifier_authority=verifier_authority,
        verifier_authority_boundary=verifier_boundary,
        generation_witness_reader=witness,
        generation_witness_binding=binding,
    )
    high_authority, high_boundary = (
        create_signer_runtime_generation_high_water_reader_authority(
            high_water
        )
    )
    reader = DurableSignerRuntimeGenerationReader(
        owner["anchor_path"],
        allowed_root=runtime,
        repo_root=repo,
        anchor_id=str(owner["anchor_id"]),
        verifier_authority=verifier_authority,
        verifier_authority_boundary=verifier_boundary,
        high_water_authority=high_authority,
        high_water_authority_boundary=high_boundary,
    )
    return create_signer_runtime_generation_reader_authority(reader)


def _witness_binding(
    owner: Mapping[str, Any], *, runtime: Path
) -> SignerRuntimeGenerationWitnessBinding:
    return SignerRuntimeGenerationWitnessBinding(
        authenticator_id=str(owner["generation_authenticator_id"]),
        signer_public_key_fingerprint=str(
            owner["generation_signer_public_key_fingerprint"]
        ),
        key_epoch=str(owner["generation_key_epoch"]),
        runtime_root_digest=raw_digest(str(runtime).encode("utf-8")),
        high_water_store_id=str(owner["high_water_store_id"]),
        high_water_durability_receipt_id=str(
            owner["high_water_durability_receipt_id"]
        ),
        witness_store_id=str(owner["witness_store_id"]),
        witness_durability_receipt_id=str(
            owner["witness_durability_receipt_id"]
        ),
    )


def _load_owner_config(
    path: Path | str, *, repo: Path
) -> dict[str, Any]:
    target = Path(path)
    if not target.is_absolute():
        raise RuntimeArtifactManifestError("signer_owner_config_not_absolute")
    root = validate_runtime_root_path(target.parent, repo_root=repo)
    target = validate_runtime_artifact_path(
        target, allowed_root=root, repo_root=repo
    )
    raw = _read_root_owned_bytes(target, root)
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeArtifactManifestError(
            "signer_owner_config_malformed"
        ) from exc
    return _validate_owner_config(value, repo=repo, owner_root=root)


def _read_root_owned_bytes(target: Path, root: Path) -> bytes:
    if not sys.platform.startswith("linux"):
        raise RuntimeArtifactManifestError(
            "signer_owner_linux_service_required"
        )
    try:
        return _read_root_owned_linux_bytes(target, root)
    except OSError as exc:
        raise RuntimeArtifactManifestError(
            "signer_owner_config_descriptor_invalid"
        ) from exc


def _read_root_owned_linux_bytes(target: Path, root: Path) -> bytes:
    _require_secure_ancestry(root)
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    file_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    directory_fd = os.open(root, directory_flags)
    try:
        _require_root_directory_fd(directory_fd)
        file_fd = os.open(target.name, file_flags, dir_fd=directory_fd)
        try:
            _require_root_file_fd(file_fd)
            return _read_bounded_fd(file_fd)
        finally:
            os.close(file_fd)
    finally:
        os.close(directory_fd)


def _require_secure_ancestry(root: Path) -> None:
    for directory in (root, *root.parents):
        metadata = directory.stat(follow_symlinks=False)
        if (
            directory.is_symlink()
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != ROOT_UID
            or stat.S_IMODE(metadata.st_mode) & 0o022
        ):
            raise RuntimeArtifactManifestError(
                "signer_owner_config_permissions_invalid"
            )


def _require_root_directory_fd(file_descriptor: int) -> None:
    metadata = os.fstat(file_descriptor)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != ROOT_UID
        or stat.S_IMODE(metadata.st_mode) & 0o022
    ):
        raise RuntimeArtifactManifestError(
            "signer_owner_config_permissions_invalid"
        )


def _require_root_file_fd(file_descriptor: int) -> None:
    metadata = os.fstat(file_descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != ROOT_UID
        or stat.S_IMODE(metadata.st_mode) & 0o022
    ):
        raise RuntimeArtifactManifestError(
            "signer_owner_config_permissions_invalid"
        )


def _read_bounded_fd(file_descriptor: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while total <= MAX_OWNER_CONFIG_BYTES:
        chunk = os.read(
            file_descriptor,
            min(8192, MAX_OWNER_CONFIG_BYTES + 1 - total),
        )
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    if total == 0 or total > MAX_OWNER_CONFIG_BYTES:
        raise RuntimeArtifactManifestError("signer_owner_config_size_invalid")
    return b"".join(chunks)


def _validate_owner_config(
    value: object, *, repo: Path, owner_root: Path
) -> dict[str, Any]:
    if (
        not isinstance(value, Mapping)
        or set(value) != FIELDS
        or not ascii_deep(value)
        or value.get("schema_version") != SCHEMA_VERSION
    ):
        raise RuntimeArtifactManifestError("signer_owner_config_shape_invalid")
    checked = dict(value)
    expected_id = digest(
        {key: item for key, item in checked.items() if key != "config_id"}
    )
    if checked["config_id"] != expected_id:
        raise RuntimeArtifactManifestError("signer_owner_config_id_invalid")
    if checked["repo_root_digest"] != raw_digest(
        str(repo).encode("utf-8")
    ):
        raise RuntimeArtifactManifestError(
            "signer_owner_repo_binding_mismatch"
        )
    _validate_owner_text_and_digests(checked)
    _validate_owner_paths(checked, repo=repo, owner_root=owner_root)
    return checked


def _validate_owner_text_and_digests(value: Mapping[str, Any]) -> None:
    text_fields = (
        "anchor_id",
        "generation_public_key",
        "generation_authenticator_id",
        "generation_key_epoch",
        "high_water_store_id",
        "witness_store_id",
    )
    digest_fields = (
        "config_id",
        "repo_root_digest",
        "generation_signer_public_key_fingerprint",
        "high_water_durability_receipt_id",
        "witness_durability_receipt_id",
    )
    if any(not _ascii(value.get(name)) for name in text_fields) or any(
        not is_sha256(value.get(name)) for name in digest_fields
    ):
        raise RuntimeArtifactManifestError("signer_owner_config_value_invalid")


def _validate_owner_paths(
    value: Mapping[str, Any], *, repo: Path, owner_root: Path
) -> None:
    runtime = validate_runtime_root_path(value["runtime_root"], repo_root=repo)
    high_root = validate_runtime_root_path(
        value["high_water_root"], repo_root=repo
    )
    witness_root = validate_runtime_root_path(
        value["witness_root"], repo_root=repo
    )
    roots = (runtime, high_root, witness_root)
    if any(
        first == second
        or first in second.parents
        or second in first.parents
        for first, second in (
            (runtime, high_root),
            (runtime, witness_root),
            (high_root, witness_root),
            *((owner_root, item) for item in roots),
        )
    ):
        raise RuntimeArtifactManifestError("signer_owner_root_overlap")
    expected = (
        (value["anchor_path"], runtime, "generation-anchor.json"),
        (value["high_water_path"], high_root, "high-water.json"),
        (value["witness_path"], witness_root, "generation.sqlite3"),
    )
    for raw_path, root, filename in expected:
        path = validate_runtime_artifact_path(
            raw_path, allowed_root=root, repo_root=repo
        )
        if path != root / filename:
            raise RuntimeArtifactManifestError("signer_owner_path_invalid")


def _require_cli_paths(
    runtime: Path,
    config_path: Path | None,
    run_packet_path: Path | None,
) -> None:
    if config_path is None and run_packet_path is None:
        return
    if config_path is None or run_packet_path is None:
        raise RuntimeArtifactManifestError(
            "signer_owner_cli_path_mismatch"
        )
    expected = (
        (Path(config_path).resolve(), runtime / CONFIG_FILENAME),
        (Path(run_packet_path).resolve(), runtime / RUN_PACKET_FILENAME),
    )
    if any(actual != wanted for actual, wanted in expected):
        raise RuntimeArtifactManifestError(
            "signer_owner_cli_path_mismatch"
        )


def _ascii(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and value.strip()
        and value.isascii()
        and len(value) <= 1024
    )


__all__ = [
    "SCHEMA_VERSION",
    "load_system_service_manifest_selection",
]
