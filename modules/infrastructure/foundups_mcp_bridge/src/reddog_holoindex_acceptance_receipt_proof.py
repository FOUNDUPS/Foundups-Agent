"""Descriptor-held proof for one isolated HoloIndex freshness receipt."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Callable, Mapping

from holo_index.freshness_receipt import (
    CollectionFreshness,
    HoloIndexFreshnessReceipt,
    freshness_receipt_from_mapping,
    freshness_receipt_integrity_ok,
    freshness_receipt_path,
)

from .reddog_holoindex_acceptance_guards import _reject_link_components
from .reddog_holoindex_acceptance_windows import (
    WindowsDirectoryLease,
    open_windows_directory_lease,
    open_windows_source_file,
    validate_windows_directory_lease,
    validate_windows_file_descriptor,
)


_RECEIPT_FIELDS = {field.name for field in fields(HoloIndexFreshnessReceipt)}
_COLLECTION_FIELDS = {field.name for field in fields(CollectionFreshness)}
_RECEIPT_STRING_FIELDS = _RECEIPT_FIELDS - {"collections"}
_COLLECTION_REQUIRED = {
    "name", "count", "status", "source", "repo_head_sha", "last_indexed_at"
}


def _fail(code: str) -> None:
    raise ValueError(code)


def _normal(path: Path | str) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _same_path(left: Path | str, right: Path | str) -> bool:
    return os.path.normcase(os.fspath(_normal(left))) == os.path.normcase(
        os.fspath(_normal(right))
    )


def _identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    if not stat.S_ISREG(metadata.st_mode) or int(getattr(metadata, "st_nlink", 1)) != 1:
        _fail("RECEIPT_NOT_PRIVATE_REGULAR")
    return (
        int(metadata.st_dev), int(metadata.st_ino), int(metadata.st_size),
        int(metadata.st_mtime_ns), int(getattr(metadata, "st_nlink", 1)),
    )


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("RECEIPT_JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _strict_mapping(payload: bytes) -> Mapping[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=_reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("RECEIPT_JSON_INVALID") from exc
    if not isinstance(value, dict) or set(value) != _RECEIPT_FIELDS:
        _fail("RECEIPT_SCHEMA_INVALID")
    if any(not isinstance(value[name], str) for name in _RECEIPT_STRING_FIELDS):
        _fail("RECEIPT_SCHEMA_INVALID")
    collections = value.get("collections")
    if not isinstance(collections, list):
        _fail("RECEIPT_SCHEMA_INVALID")
    for entry in collections:
        _validate_collection(entry)
    return value


def _validate_collection(entry: Any) -> None:
    if not isinstance(entry, dict):
        _fail("RECEIPT_COLLECTION_INVALID")
    keys = set(entry)
    if not _COLLECTION_REQUIRED <= keys or not keys <= _COLLECTION_FIELDS:
        _fail("RECEIPT_COLLECTION_INVALID")
    if type(entry.get("count")) is not int:
        _fail("RECEIPT_COLLECTION_INVALID")
    for key, value in entry.items():
        if key != "count" and not isinstance(value, str):
            _fail("RECEIPT_COLLECTION_INVALID")


def _read_descriptor(descriptor: int, max_bytes: int) -> tuple[bytes, tuple[int, int, int, int, int]]:
    if max_bytes <= 0:
        _fail("RECEIPT_BOUND_INVALID")
    identity = _identity(os.fstat(descriptor))
    if identity[2] > max_bytes:
        _fail("RECEIPT_BOUND_EXCEEDED")
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    remaining = identity[2] + 1
    while remaining:
        chunk = os.read(descriptor, min(remaining, 1024 * 1024))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    payload = b"".join(chunks)
    if len(payload) != identity[2]:
        _fail("RECEIPT_SIZE_CHANGED")
    return payload, identity


def _open_descriptor(path: Path, identity: tuple[int, int, int, int, int]):
    if os.name == "nt":
        parent = open_windows_directory_lease(path.parent)
        try:
            descriptor = open_windows_source_file(path, parent, expected_identity=identity)
        except BaseException:
            parent.close()
            raise
        return descriptor, parent
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    if _identity(os.fstat(descriptor)) != identity:
        os.close(descriptor)
        _fail("RECEIPT_IDENTITY_CHANGED")
    return descriptor, None


@dataclass
class FreshnessReceiptProof:
    """Live descriptor and immutable content binding spanning one probe."""

    path: Path
    descriptor: int
    identity: tuple[int, int, int, int, int]
    digest: str
    receipt: HoloIndexFreshnessReceipt
    max_bytes: int
    parent: WindowsDirectoryLease | None = None

    def revalidate(self) -> None:
        if self.descriptor < 0:
            _fail("RECEIPT_PROOF_CLOSED")
        if self.parent is not None:
            validate_windows_directory_lease(self.parent)
            validate_windows_file_descriptor(
                self.descriptor, self.path, expected_identity=self.identity
            )
        current = _identity(os.lstat(self.path))
        if current != self.identity:
            _fail("RECEIPT_PATH_IDENTITY_CHANGED")
        payload, identity = _read_descriptor(self.descriptor, self.max_bytes)
        if identity != self.identity or _digest(payload) != self.digest:
            _fail("RECEIPT_CONTENT_CHANGED")

    def close(self) -> None:
        if self.descriptor >= 0:
            os.close(self.descriptor)
            self.descriptor = -1
        if self.parent is not None:
            self.parent.close()
            self.parent = None

    def __enter__(self) -> "FreshnessReceiptProof":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _validate_binding(
    receipt: HoloIndexFreshnessReceipt,
    *, expected_ssd_path: Path, expected_repo_root: Path,
    expected_repo_head_sha: str, expected_generation_id: str,
) -> None:
    if not freshness_receipt_integrity_ok(receipt):
        _fail("RECEIPT_INTEGRITY_INVALID")
    if not _same_path(receipt.ssd_path, expected_ssd_path):
        _fail("RECEIPT_SSD_PATH_MISMATCH")
    if not _same_path(receipt.repo_root, expected_repo_root):
        _fail("RECEIPT_REPO_ROOT_MISMATCH")
    if receipt.repo_head_sha.lower() != expected_repo_head_sha.lower():
        _fail("RECEIPT_REPO_HEAD_MISMATCH")
    if receipt.generation_id != expected_generation_id:
        _fail("RECEIPT_GENERATION_MISMATCH")


def open_freshness_receipt_proof(
    *, path: Path | str, allowed_root: Path | str, expected_ssd_path: Path | str,
    expected_repo_root: Path | str, expected_repo_head_sha: str,
    expected_generation_id: str, expected_receipt_digest: str,
    max_bytes: int,
) -> FreshnessReceiptProof:
    """Open and bind the exact canonical receipt under one isolated store."""

    target, root = _normal(path), _normal(allowed_root)
    if not _same_path(root, expected_ssd_path):
        _fail("RECEIPT_ALLOWED_ROOT_MISMATCH")
    if not _same_path(target, freshness_receipt_path(root)):
        _fail("RECEIPT_PATH_NONCANONICAL")
    _reject_link_components(target)
    expected_identity = _identity(os.lstat(target))
    descriptor, parent = _open_descriptor(target, expected_identity)
    try:
        payload, live_identity = _read_descriptor(descriptor, max_bytes)
        digest = _digest(payload)
        if live_identity != expected_identity or digest != expected_receipt_digest:
            _fail("RECEIPT_DIGEST_OR_IDENTITY_MISMATCH")
        receipt = freshness_receipt_from_mapping(_strict_mapping(payload))
        _validate_binding(
            receipt,
            expected_ssd_path=_normal(expected_ssd_path),
            expected_repo_root=_normal(expected_repo_root),
            expected_repo_head_sha=expected_repo_head_sha,
            expected_generation_id=expected_generation_id,
        )
        proof = FreshnessReceiptProof(
            target, descriptor, live_identity, digest, receipt, max_bytes, parent
        )
        proof.revalidate()
        return proof
    except BaseException:
        os.close(descriptor)
        if parent is not None:
            parent.close()
        raise


def verify_freshness_receipt_snapshot(
    *, opener: Callable[..., FreshnessReceiptProof], verifier: Callable[..., Any],
    path: Path | str, allowed_root: Path | str, expected_ssd_path: Path | str,
    expected_repo_root: Path | str, expected_repo_head_sha: str,
    expected_generation_id: str, expected_receipt_digest: str, max_bytes: int,
    timeout_seconds: float,
    runtime_site_packages: tuple[str, ...] = (),
    base_executable_proof: Any = None,
) -> bool:
    """Hold and re-prove one receipt around the isolated snapshot probe."""

    proof = opener(
        path=path, allowed_root=allowed_root, expected_ssd_path=expected_ssd_path,
        expected_repo_root=expected_repo_root,
        expected_repo_head_sha=expected_repo_head_sha,
        expected_generation_id=expected_generation_id,
        expected_receipt_digest=expected_receipt_digest, max_bytes=max_bytes,
    )
    with proof:
        proof.revalidate()
        try:
            mismatches = verifier(
                proof.receipt, ssd_path=expected_ssd_path,
                repo_root=expected_repo_root, timeout_seconds=timeout_seconds,
                runtime_site_packages=runtime_site_packages,
                base_executable_proof=base_executable_proof,
            )
        finally:
            proof.revalidate()
        if mismatches:
            return False
    return True


__all__ = [
    "FreshnessReceiptProof",
    "open_freshness_receipt_proof",
    "verify_freshness_receipt_snapshot",
]
