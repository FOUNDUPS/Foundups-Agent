"""Atomic private JSON publication with no-delete quarantine rollback."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import platform
import stat
import tempfile
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    redact_runtime_value,
)

from .reddog_holoindex_acceptance_windows import publish_windows_temp_no_replace


ACCEPTANCE_SCHEMA_VERSION = "reddog_holoindex_candidate_acceptance.v1"


@dataclass(frozen=True)
class _OwnedFileProof:
    device: int
    inode: int
    size: int


@dataclass(frozen=True)
class PublishedPrivateJsonProof:
    """Exact identity and canonical-content proof for one published JSON file."""

    path: Path
    device: int
    inode: int
    size: int
    digest: str
    allowed_root: Path
    orphan_root: Path


@dataclass(frozen=True)
class QuarantinedPathProof:
    """Relative, non-secret evidence for one preserved failed object."""

    relative_path: str
    device: int
    inode: int
    size: int
    digest: str


def _guards() -> Any:
    from . import reddog_holoindex_acceptance_guards as guards

    return guards


def _fail(code: str) -> None:
    _guards()._fail(code)


def _contains_absolute_path(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _contains_absolute_path(key) or _contains_absolute_path(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_absolute_path(item) for item in value)
    return isinstance(value, str) and Path(value).is_absolute()


def _fsync_directory(parent: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _owned_file_proof(metadata: os.stat_result) -> _OwnedFileProof:
    if (
        not stat.S_ISREG(metadata.st_mode)
        or int(getattr(metadata, "st_nlink", 1)) != 1
        or int(metadata.st_ino) <= 0
    ):
        _fail("RECEIPT_TEMP_IDENTITY_INVALID")
    return _OwnedFileProof(
        int(metadata.st_dev), int(metadata.st_ino), int(metadata.st_size)
    )


def _same_owned_identity(path: Path, proof: _OwnedFileProof) -> bool:
    try:
        metadata = os.lstat(path)
    except OSError:
        return False
    return bool(
        stat.S_ISREG(metadata.st_mode)
        and not _guards()._is_link_or_reparse(path, metadata)
        and int(metadata.st_dev) == proof.device
        and int(metadata.st_ino) == proof.inode
        and int(getattr(metadata, "st_nlink", 1)) == 1
    )


def _matches_owned_file(path: Path, proof: _OwnedFileProof) -> bool:
    if not _same_owned_identity(path, proof):
        return False
    try:
        return int(os.lstat(path).st_size) == proof.size
    except OSError:
        return False


def _rename_path_no_replace(source: Path, target: Path) -> None:
    if os.name == "nt":
        os.rename(source, target)
        return
    if platform.system() != "Linux":
        _fail("RECEIPT_ATOMIC_RENAME_UNAVAILABLE")
    renameat2 = getattr(ctypes.CDLL(None, use_errno=True), "renameat2", None)
    if renameat2 is None:
        _fail("RECEIPT_ATOMIC_RENAME_UNAVAILABLE")
    result = renameat2(-100, os.fsencode(source), -100, os.fsencode(target), 1)
    if result == 0:
        return
    error = ctypes.get_errno()
    if error == 17:
        _fail("RECEIPT_TARGET_NOT_NEW")
    raise OSError(error, os.strerror(error))


def _publish_temp_no_replace(
    temporary: Path, target: Path, proof: _OwnedFileProof,
) -> None:
    if os.name == "nt":
        publish_windows_temp_no_replace(
            temporary, target,
            expected_identity=(proof.device, proof.inode, proof.size),
        )
    else:
        _rename_path_no_replace(temporary, target)
    if not _matches_owned_file(target, proof):
        _fail("RECEIPT_PUBLISHED_IDENTITY_INVALID")


def _write_receipt_temp(descriptor: int, encoded: bytes) -> _OwnedFileProof:
    remaining = memoryview(encoded)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError("receipt_temp_write_incomplete")
        remaining = remaining[written:]
    os.fsync(descriptor)
    proof = _owned_file_proof(os.fstat(descriptor))
    if proof.size != len(encoded):
        _fail("RECEIPT_TEMP_SIZE_MISMATCH")
    return proof


def _encode_payload(
    payload: Mapping[str, Any], max_bytes: int, *, expected_schema: str,
    reject_absolute_paths: bool,
) -> bytes:
    if payload.get("schema_version") != expected_schema:
        _fail("RECEIPT_SCHEMA_INVALID")
    if type(max_bytes) is not int or max_bytes <= 0:
        _fail("RECEIPT_SIZE_BOUND")
    redaction_items = min(max(max_bytes, 128), 1_000_000)
    if redact_runtime_value(payload, max_items=redaction_items) != dict(payload) or (
        reject_absolute_paths and _contains_absolute_path(payload)
    ):
        _fail("RECEIPT_NOT_SECRET_FREE")
    encoded = (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")
    if len(encoded) > max_bytes:
        _fail("RECEIPT_SIZE_BOUND")
    return encoded


def _validate_target(
    path: Path | str, allowed_root: Path | str, canonical_store: Path | str,
    repo_roots: Iterable[Path | str],
) -> tuple[Path, Path]:
    guards = _guards()
    target = guards._normalized(path)
    root = guards._normalized(allowed_root)
    if not guards._relative_to(target, root) or target == root:
        _fail("RECEIPT_OUTSIDE_ALLOWED_ROOT")
    guards._reject_link_components(target)
    guards._reject_overlap(target, (canonical_store, *tuple(repo_roots)))
    if not target.parent.is_dir() or target.exists():
        _fail("RECEIPT_TARGET_NOT_NEW")
    return target, root


def _verify_published(
    target: Path, proof: _OwnedFileProof,
) -> None:
    if not _matches_owned_file(target, proof):
        _fail("RECEIPT_PUBLISHED_IDENTITY_INVALID")
    _fsync_directory(target.parent)
    if not _matches_owned_file(target, proof):
        _fail("RECEIPT_PUBLISHED_IDENTITY_CHANGED")


def _prepare_orphan_root(path: Path, allowed_root: Path) -> Path:
    guards = _guards()
    orphan_root = guards._normalized(path)
    if orphan_root == allowed_root or not guards._relative_to(orphan_root, allowed_root):
        _fail("RECEIPT_ORPHAN_ROOT_INVALID")
    guards._reject_link_components(orphan_root)
    if not orphan_root.exists():
        orphan_root.mkdir(mode=0o700)
    metadata = os.lstat(orphan_root)
    if not stat.S_ISDIR(metadata.st_mode) or guards._is_link_or_reparse(
        orphan_root, metadata
    ):
        _fail("RECEIPT_ORPHAN_ROOT_INVALID")
    return orphan_root


def _quarantine_name(
    source: Path, *, allowed_root: Path, orphan_root: Path, label: str,
    token: str, max_bytes: int,
) -> QuarantinedPathProof:
    if not label.replace("-", "").isalnum() or not token.isalnum():
        _fail("RECEIPT_ORPHAN_NAME_INVALID")
    target = orphan_root / f"{label}-{token}-{source.name}"
    _rename_path_no_replace(source, target)
    metadata = os.lstat(target)
    digest = ""
    if stat.S_ISREG(metadata.st_mode) and int(metadata.st_size) <= max_bytes:
        try:
            digest = "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest()
        except OSError:
            digest = ""
    proof = QuarantinedPathProof(
        relative_path=target.relative_to(allowed_root).as_posix(),
        device=int(metadata.st_dev), inode=int(metadata.st_ino),
        size=int(metadata.st_size), digest=digest,
    )
    try:
        _fsync_directory(source.parent)
        if target.parent != source.parent:
            _fsync_directory(target.parent)
    except BaseException as exc:
        exc.orphan_proof = proof
        raise
    return proof


def quarantine_proven_private_json(
    proof: PublishedPrivateJsonProof, *, label: str = "active",
    token: str | None = None, max_bytes: int = 2_097_152,
) -> QuarantinedPathProof:
    """Atomically preserve whatever occupies the published owned name."""

    if type(proof) is not PublishedPrivateJsonProof:
        _fail("RECEIPT_PUBLICATION_PROOF_INVALID")
    return quarantine_owned_path_no_replace(
        proof.path, allowed_root=proof.allowed_root, orphan_root=proof.orphan_root,
        label=label, token=token or secrets.token_hex(16), max_bytes=max_bytes,
    )


def quarantine_owned_path_no_replace(
    source: Path | str, *, allowed_root: Path | str, orphan_root: Path | str,
    label: str, token: str, max_bytes: int,
) -> QuarantinedPathProof:
    """No-replace move of one owned-root name; never inspect then delete."""

    guards = _guards()
    root = guards._normalized(allowed_root)
    candidate = guards._normalized(source)
    orphans = _prepare_orphan_root(guards._normalized(orphan_root), root)
    if candidate == root or not guards._relative_to(candidate, root):
        _fail("RECEIPT_ORPHAN_SOURCE_INVALID")
    return _quarantine_name(
        candidate, allowed_root=root, orphan_root=orphans, label=label,
        token=token, max_bytes=max_bytes,
    )


def _publication_error(
    cause: BaseException, preserved: list[QuarantinedPathProof], unsafe: list[str],
) -> BaseException:
    error = _guards().AcceptanceGuardError("RECEIPT_PUBLICATION_FAILED")
    error.orphan_relative_paths = tuple(item.relative_path for item in preserved)
    error.unsafe_relative_paths = tuple(unsafe)
    error.__cause__ = cause
    return error


def _preserve_publication_failure(
    *, descriptor: int, temporary: Path, target: Path, publish_attempted: bool,
    root: Path, orphans: Path, max_bytes: int, cause: BaseException,
) -> BaseException:
    if descriptor >= 0:
        try:
            os.close(descriptor)
        except OSError:
            pass
    preserved: list[QuarantinedPathProof] = []
    unsafe: list[str] = []
    candidate = temporary if temporary.exists() else target if (
        publish_attempted and target.exists()
    ) else None
    if candidate is None:
        return _publication_error(cause, preserved, unsafe)
    try:
        preserved.append(_quarantine_name(
            candidate, allowed_root=root, orphan_root=orphans,
            label="publication", token=secrets.token_hex(16),
            max_bytes=max_bytes,
        ))
    except BaseException as quarantine_exc:
        partial = getattr(quarantine_exc, "orphan_proof", None)
        if type(partial) is QuarantinedPathProof:
            preserved.append(partial)
            unsafe.append(partial.relative_path)
        else:
            unsafe.append(candidate.relative_to(root).as_posix())
    return _publication_error(cause, preserved, unsafe)


def atomic_publish_private_json_proven(
    path: Path | str, payload: Mapping[str, Any], *, allowed_root: Path | str,
    canonical_store: Path | str, repo_roots: Iterable[Path | str], max_bytes: int,
    expected_schema: str, reject_absolute_paths: bool = True,
    orphan_root: Path | str | None = None,
) -> PublishedPrivateJsonProof:
    """Publish immutable JSON and return its exact identity/content capability."""

    target, root = _validate_target(path, allowed_root, canonical_store, repo_roots)
    orphans = _prepare_orphan_root(
        _guards()._normalized(orphan_root) if orphan_root is not None
        else root / ".private-json-orphans",
        root,
    )
    encoded = _encode_payload(
        payload, max_bytes, expected_schema=expected_schema,
        reject_absolute_paths=reject_absolute_paths,
    )
    descriptor, temporary_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    publish_attempted = False
    try:
        _owned_file_proof(os.fstat(descriptor))
        content = _write_receipt_temp(descriptor, encoded)
        os.close(descriptor)
        descriptor = -1
        publish_attempted = True
        _publish_temp_no_replace(temporary, target, content)
        _verify_published(target, content)
        return PublishedPrivateJsonProof(
            target, content.device, content.inode, content.size,
            "sha256:" + hashlib.sha256(encoded).hexdigest(), root, orphans,
        )
    except BaseException as exc:
        raise _preserve_publication_failure(
            descriptor=descriptor, temporary=temporary, target=target,
            publish_attempted=publish_attempted, root=root, orphans=orphans,
            max_bytes=max_bytes, cause=exc,
        )


def atomic_publish_private_json(*args: Any, **kwargs: Any) -> Path:
    """Compatibility wrapper returning the published path."""

    return atomic_publish_private_json_proven(*args, **kwargs).path


def _proof_identity(proof: PublishedPrivateJsonProof) -> _OwnedFileProof:
    return _OwnedFileProof(proof.device, proof.inode, proof.size)


def verify_proven_private_json(
    proof: PublishedPrivateJsonProof, *, expected_payload: Mapping[str, Any],
    max_bytes: int, expected_schema: str,
) -> bool:
    """Verify exact identity, size, digest, and canonical payload."""

    if type(proof) is not PublishedPrivateJsonProof:
        return False
    encoded = _encode_payload(
        expected_payload, max_bytes, expected_schema=expected_schema,
        reject_absolute_paths=False,
    )
    expected_digest = "sha256:" + hashlib.sha256(encoded).hexdigest()
    identity = _proof_identity(proof)
    if proof.digest != expected_digest or not _matches_owned_file(proof.path, identity):
        return False
    try:
        content = proof.path.read_bytes()
    except OSError:
        return False
    return content == encoded and _matches_owned_file(proof.path, identity)


def atomic_publish_acceptance_receipt(
    path: Path | str, payload: Mapping[str, Any], *, allowed_root: Path | str,
    canonical_store: Path | str, repo_roots: Iterable[Path | str], max_bytes: int,
) -> Path:
    return atomic_publish_private_json(
        path, payload, allowed_root=allowed_root, canonical_store=canonical_store,
        repo_roots=repo_roots, max_bytes=max_bytes,
        expected_schema=ACCEPTANCE_SCHEMA_VERSION,
    )


__all__ = [
    "PublishedPrivateJsonProof",
    "QuarantinedPathProof",
    "atomic_publish_acceptance_receipt",
    "atomic_publish_private_json",
    "atomic_publish_private_json_proven",
    "quarantine_proven_private_json",
    "quarantine_owned_path_no_replace",
    "verify_proven_private_json",
]
