"""Security tests for the verifier-only signer-generation reader."""

from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water import (
    AtomicSignerRuntimeGenerationHighWaterReader,
    AtomicSignerRuntimeGenerationHighWaterStore,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
    encode_ed25519_signature,
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
    create_signer_runtime_generation_reader_authority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_verifier_authority import (
    create_signer_runtime_generation_verifier_authority,
)


class Ed25519GenerationSigner:
    def __init__(self) -> None:
        self.private_key = Ed25519PrivateKey.generate()
        public = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_key = encode_ed25519_public_key(public)
        authority, boundary = (
            create_signer_runtime_generation_verifier_authority(
                self.public_key
            )
        )
        self.verifier_authority = authority
        self.verifier_boundary = boundary
        self.authenticator_id = boundary.require(authority).authenticator_id

    def authenticate(self, payload: bytes) -> str:
        return encode_ed25519_signature(self.private_key.sign(payload))


class Boundary:
    def __init__(self, store) -> None:
        self.capability = object()
        self.verified = VerifiedSignerRuntimeGenerationHighWater(
            store=store,
            store_id=store.store_id,
            durability_receipt_id=store.durability_receipt_id,
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
    signing = Ed25519GenerationSigner()
    high_water = AtomicSignerRuntimeGenerationHighWaterStore(
        authority / "high-water.json",
        allowed_root=authority,
        repo_root=repo,
        store_id="high-water:production",
        durability_receipt_id=_sha("e"),
        signer=signing,
        verifier=signing.verifier_boundary.require(
            signing.verifier_authority
        ),
    )
    return signing, high_water


def _reader(
    repo: Path,
    runtime: Path,
    authority: Path,
    signing: Ed25519GenerationSigner | None = None,
):
    verifier = signing or Ed25519GenerationSigner()
    high_water_reader = AtomicSignerRuntimeGenerationHighWaterReader(
        authority / "high-water.json",
        allowed_root=authority,
        repo_root=repo,
        store_id="high-water:production",
        durability_receipt_id=_sha("e"),
        verifier_authority=verifier.verifier_authority,
        verifier_authority_boundary=verifier.verifier_boundary,
    )
    reader_boundary = ReaderBoundary(high_water_reader)
    return DurableSignerRuntimeGenerationReader(
        runtime / "anchor.json",
        allowed_root=runtime,
        repo_root=repo,
        anchor_id="reddog-signer:production",
        verifier_authority=verifier.verifier_authority,
        verifier_authority_boundary=verifier.verifier_boundary,
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
        verifier=signing.verifier_boundary.require(
            signing.verifier_authority
        ),
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
    reader = _reader(repo, runtime, authority, signing)

    assert reader.load().generation == 1
    assert not hasattr(reader._verifier, "authenticate")
    assert not hasattr(reader._high_water, "_signer")
    assert not hasattr(reader._store, "commit")


def test_lifecycle_reader_authority_object_graph_has_no_effect_capability(
    tmp_path: Path,
) -> None:
    repo, runtime, authority = _roots(tmp_path)
    signing, _ = _high_water(repo, authority)
    reader = _reader(repo, runtime, authority, signing)
    _, boundary = create_signer_runtime_generation_reader_authority(reader)
    forbidden = {
        "activate",
        "advance",
        "authenticate",
        "commit",
        "commit_prepared",
        "prepare",
        "private_key",
        "sign",
    }

    reachable = [
        boundary,
        reader,
        reader._store,
        reader._verifier,
        reader._high_water,
        reader._high_water._store,
        reader._high_water._verifier,
    ]
    for value in reachable:
        assert not any(
            callable(getattr(value, name, None))
            or getattr(value, name, None) is not None
            for name in forbidden
        )


def test_reader_rejects_authenticated_pending_generation(tmp_path: Path) -> None:
    repo, runtime, authority = _roots(tmp_path)
    signing, high_water = _high_water(repo, authority)
    high_water.prepare(
        "reddog-signer:production",
        expected=None,
        next_value=SignerRuntimeGenerationHighWater(
            generation=1, revision="1" * 64
        ),
    )

    with pytest.raises(ValueError, match="pending_transaction"):
        _reader(repo, runtime, authority, signing).load()


def test_reader_rejects_same_rollback_domain(tmp_path: Path) -> None:
    repo, runtime, _ = _roots(tmp_path)
    signing = Ed25519GenerationSigner()
    high_water_reader = AtomicSignerRuntimeGenerationHighWaterReader(
        runtime / "high-water.json",
        allowed_root=runtime,
        repo_root=repo,
        store_id="high-water:production",
        durability_receipt_id=_sha("e"),
        verifier_authority=signing.verifier_authority,
        verifier_authority_boundary=signing.verifier_boundary,
    )
    boundary = ReaderBoundary(high_water_reader)

    with pytest.raises(ValueError, match="high_water_domain_overlap"):
        DurableSignerRuntimeGenerationReader(
            runtime / "anchor.json",
            allowed_root=runtime,
            repo_root=repo,
            anchor_id="reddog-signer:production",
            verifier_authority=signing.verifier_authority,
            verifier_authority_boundary=signing.verifier_boundary,
            high_water_authority=boundary.capability,
            high_water_authority_boundary=boundary,
        )


def test_reader_rejects_write_capable_high_water(tmp_path: Path) -> None:
    repo, runtime, authority = _roots(tmp_path)
    signing, high_water = _high_water(repo, authority)
    boundary = ReaderBoundary(high_water)

    with pytest.raises(ValueError, match="write_capability"):
        DurableSignerRuntimeGenerationReader(
            runtime / "anchor.json",
            allowed_root=runtime,
            repo_root=repo,
            anchor_id="reddog-signer:production",
            verifier_authority=signing.verifier_authority,
            verifier_authority_boundary=signing.verifier_boundary,
            high_water_authority=boundary.capability,
            high_water_authority_boundary=boundary,
        )


def test_reader_rejects_verifier_with_signing_method(tmp_path: Path) -> None:
    repo, runtime, authority = _roots(tmp_path)
    signing = Ed25519GenerationSigner()
    high_water_reader = AtomicSignerRuntimeGenerationHighWaterReader(
        authority / "high-water.json",
        allowed_root=authority,
        repo_root=repo,
        store_id="high-water:production",
        durability_receipt_id=_sha("e"),
        verifier_authority=signing.verifier_authority,
        verifier_authority_boundary=signing.verifier_boundary,
    )
    boundary = ReaderBoundary(high_water_reader)

    with pytest.raises(ValueError, match="authority_unverified"):
        DurableSignerRuntimeGenerationReader(
            runtime / "anchor.json",
            allowed_root=runtime,
            repo_root=repo,
            anchor_id="reddog-signer:production",
            verifier_authority=object(),
            verifier_authority_boundary=signing.verifier_boundary,
            high_water_authority=boundary.capability,
            high_water_authority_boundary=boundary,
        )
