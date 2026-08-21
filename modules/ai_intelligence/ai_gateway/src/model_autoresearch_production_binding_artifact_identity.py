"""Retained descriptor and content proofs for production artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .model_autoresearch_configured_gateway_durability import _fsync_directory
from .model_provider_catalog_atomic_io import _open_windows_descriptor

MAX_PRODUCTION_ARTIFACT_BYTES = 1_048_576


@dataclass(frozen=True)
class ProductionArtifactProof:
    device: int
    inode: int
    size: int
    digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "device": self.device,
            "inode": self.inode,
            "size": self.size,
            "digest": self.digest,
        }


@dataclass
class HeldProductionArtifact:
    path: Path
    descriptor: int
    proof: ProductionArtifactProof
    allowed_links: int = 1

    def close(self) -> None:
        if self.descriptor >= 0:
            os.close(self.descriptor)
            self.descriptor = -1


def seal_staged_artifact(path: Path) -> HeldProductionArtifact:
    descriptor = _open_sealable_descriptor(path)
    try:
        named, opened = os.lstat(path), os.fstat(descriptor)
        require_same_identity(opened, named, allowed_links=1)
        if opened.st_size > MAX_PRODUCTION_ARTIFACT_BYTES:
            raise OSError("single_model_production_artifact_too_large")
        os.fsync(descriptor)
        payload = read_descriptor(descriptor, opened.st_size + 1)
        proof = ProductionArtifactProof(
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            hashlib.sha256(payload).hexdigest(),
        )
        held = HeldProductionArtifact(path, descriptor, proof)
        verify_held_artifact(held)
        _fsync_directory(path.parent)
        return held
    except BaseException:
        os.close(descriptor)
        raise


def open_verified_artifact(
    path: Path, proof: ProductionArtifactProof, *, allowed_links: int = 1
) -> HeldProductionArtifact:
    held = HeldProductionArtifact(
        path, _open_sealable_descriptor(path), proof, allowed_links
    )
    try:
        verify_held_artifact(held)
        return held
    except BaseException:
        held.close()
        raise


def verify_held_artifact(held: HeldProductionArtifact) -> bytes:
    opened, named = os.fstat(held.descriptor), os.lstat(held.path)
    require_same_identity(opened, named, allowed_links=held.allowed_links)
    require_proof(opened, held.proof)
    payload = read_descriptor(held.descriptor, held.proof.size + 1)
    if hashlib.sha256(payload).hexdigest() != held.proof.digest:
        raise OSError("single_model_production_artifact_content_changed")
    return payload


def read_held_json(held: HeldProductionArtifact, reason: str) -> Mapping[str, Any]:
    try:
        value = json.loads(verify_held_artifact(held).decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError(reason) from None
    if not isinstance(value, Mapping):
        raise ValueError(reason)
    return value


def proof_from_dict(value: Mapping[str, Any]) -> ProductionArtifactProof:
    try:
        proof = ProductionArtifactProof(
            int(value["device"]),
            int(value["inode"]),
            int(value["size"]),
            str(value["digest"]),
        )
    except (KeyError, TypeError, ValueError):
        raise ValueError("single_model_production_artifact_proof_invalid") from None
    try:
        int(proof.digest, 16)
    except ValueError:
        raise ValueError("single_model_production_artifact_proof_invalid") from None
    if proof.inode <= 0 or proof.size < 0 or len(proof.digest) != 64:
        raise ValueError("single_model_production_artifact_proof_invalid")
    return proof


def verify_path(
    path: Path, proof: ProductionArtifactProof, *, allowed_links: int
) -> None:
    metadata = os.lstat(path)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != allowed_links:
        raise OSError("single_model_production_artifact_identity_invalid")
    require_proof(metadata, proof)


def require_proof(metadata: os.stat_result, proof: ProductionArtifactProof) -> None:
    if (metadata.st_dev, metadata.st_ino) != (
        proof.device,
        proof.inode,
    ) or metadata.st_size != proof.size:
        raise OSError("single_model_production_artifact_identity_invalid")


def require_same_identity(
    first: os.stat_result, second: os.stat_result, *, allowed_links: int
) -> None:
    if (
        not stat.S_ISREG(first.st_mode)
        or not stat.S_ISREG(second.st_mode)
        or first.st_nlink != allowed_links
        or second.st_nlink != allowed_links
        or first.st_ino <= 0
        or (first.st_dev, first.st_ino) != (second.st_dev, second.st_ino)
    ):
        raise OSError("single_model_production_artifact_identity_invalid")


def read_descriptor(descriptor: int, limit: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks, remaining = [], limit
    while remaining:
        chunk = os.read(descriptor, remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _open_sealable_descriptor(path: Path) -> int:
    if os.name == "nt":
        return _open_windows_descriptor(path, 0xC0010000)
    return os.open(path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))


__all__ = [
    "HeldProductionArtifact",
    "ProductionArtifactProof",
    "open_verified_artifact",
    "proof_from_dict",
    "read_held_json",
    "require_proof",
    "seal_staged_artifact",
    "verify_held_artifact",
    "verify_path",
]
