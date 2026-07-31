"""Security tests for the verifier-only signer-generation reader."""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water import (
    AtomicSignerRuntimeGenerationHighWaterReader,
    AtomicSignerRuntimeGenerationHighWaterStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    DurableSignerRuntimeGenerationAnchor,
    SignerRuntimeGenerationBinding,
    SignerRuntimeGenerationHighWater,
    VerifiedSignerRuntimeGenerationHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_reader import (
    DurableSignerRuntimeGenerationReader,
    VerifiedSignerRuntimeGenerationHighWaterReader,
)


class HmacCapability:
    authenticator_id = "test-hmac:v1"

    def authenticate(self, payload: bytes) -> str:
        return "hmac-sha256:" + hmac.new(
            b"k" * 32, payload, hashlib.sha256
        ).hexdigest()

    def verify(self, payload: bytes, tag: str) -> bool:
        return hmac.compare_digest(self.authenticate(payload), tag)


class VerifierOnly:
    authenticator_id = "test-hmac:v1"

    def verify(self, payload: bytes, tag: str) -> bool:
        return HmacCapability().verify(payload, tag)


class Boundary:
    def __init__(self, store) -> None:
        self.capability = object()
        self.verified = VerifiedSignerRuntimeGenerationHighWater(
            store=store,
            store_id=store.store_id,
            durability_receipt_id=store.durability_receipt_id,
            rollback_domain_root=store.rollback_domain_root,
        )

    def require(self, value: object):
        if value is not self.capability:
            raise ValueError("test_authority_invalid")
        return self.verified


class ReaderBoundary:
    def __init__(self, reader) -> None:
        self.capability = object()
        self.verified = VerifiedSignerRuntimeGenerationHighWaterReader(
            reader=reader,
            store_id=reader.store_id,
            durability_receipt_id=reader.durability_receipt_id,
            rollback_domain_root=reader.rollback_domain_root,
        )

    def require(self, value: object):
        if value is not self.capability:
            raise ValueError("test_reader_authority_invalid")
        return self.verified


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _roots(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    authority = tmp_path / "authority"
    repo.mkdir()
    runtime.mkdir()
    authority.mkdir()
    return repo, runtime, authority


def _high_water(repo: Path, authority: Path):
    signing = HmacCapability()
    high_water = AtomicSignerRuntimeGenerationHighWaterStore(
        authority / "high-water.json",
        allowed_root=authority,
        repo_root=repo,
        store_id="high-water:production",
        durability_receipt_id=_sha("e"),
        signer=signing,
        verifier=signing,
    )
    return signing, high_water


def _reader(repo: Path, runtime: Path, authority: Path):
    high_water_reader = AtomicSignerRuntimeGenerationHighWaterReader(
        authority / "high-water.json",
        allowed_root=authority,
        repo_root=repo,
        store_id="high-water:production",
        durability_receipt_id=_sha("e"),
        verifier=VerifierOnly(),
    )
    reader_boundary = ReaderBoundary(high_water_reader)
    return DurableSignerRuntimeGenerationReader(
        runtime / "anchor.json",
        allowed_root=runtime,
        repo_root=repo,
        anchor_id="reddog-signer:production",
        verifier=VerifierOnly(),
        high_water_authority=reader_boundary.capability,
        high_water_authority_boundary=reader_boundary,
    )


def test_reader_holds_no_signing_capability_and_reads_active_generation(
    tmp_path: Path,
) -> None:
    repo, runtime, authority = _roots(tmp_path)
    signing, high_water = _high_water(repo, authority)
    boundary = Boundary(high_water)
    anchor_path = runtime / "anchor.json"
    writer = DurableSignerRuntimeGenerationAnchor(
        anchor_path,
        allowed_root=runtime,
        repo_root=repo,
        anchor_id="reddog-signer:production",
        signer=signing,
        verifier=signing,
        high_water_authority=boundary.capability,
        high_water_authority_boundary=boundary,
    )
    writer.activate(
        SignerRuntimeGenerationBinding(
            generation=1,
            manifest_id=_sha("1"),
            artifact_generation_digest=_sha("2"),
            config_digest=_sha("3"),
            config_raw_digest=_sha("4"),
            run_packet_digest=_sha("5"),
        ),
        expected_revision=None,
    )
    reader = _reader(repo, runtime, authority)

    assert reader.load().generation == 1
    assert not hasattr(reader._verifier, "authenticate")
    assert not hasattr(reader._high_water, "_signer")


def test_reader_rejects_authenticated_pending_generation(tmp_path: Path) -> None:
    repo, runtime, authority = _roots(tmp_path)
    _, high_water = _high_water(repo, authority)
    high_water.prepare(
        "reddog-signer:production",
        expected=None,
        next_value=SignerRuntimeGenerationHighWater(
            generation=1, revision="1" * 64
        ),
    )

    with pytest.raises(ValueError, match="pending_transaction"):
        _reader(repo, runtime, authority).load()


def test_reader_rejects_same_rollback_domain(tmp_path: Path) -> None:
    repo, runtime, _ = _roots(tmp_path)
    high_water_reader = AtomicSignerRuntimeGenerationHighWaterReader(
        runtime / "high-water.json",
        allowed_root=runtime,
        repo_root=repo,
        store_id="high-water:production",
        durability_receipt_id=_sha("e"),
        verifier=VerifierOnly(),
    )
    boundary = ReaderBoundary(high_water_reader)

    with pytest.raises(ValueError, match="high_water_domain_overlap"):
        DurableSignerRuntimeGenerationReader(
            runtime / "anchor.json",
            allowed_root=runtime,
            repo_root=repo,
            anchor_id="reddog-signer:production",
            verifier=VerifierOnly(),
            high_water_authority=boundary.capability,
            high_water_authority_boundary=boundary,
        )
