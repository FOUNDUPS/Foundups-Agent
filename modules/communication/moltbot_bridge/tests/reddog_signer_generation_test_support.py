"""Test support for a real signed read-only signer generation."""

from __future__ import annotations

import hashlib
from pathlib import Path

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
    VerifiedSignerRuntimeGenerationHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_reader import (
    DurableSignerRuntimeGenerationReader,
    create_signer_runtime_generation_high_water_reader_authority,
    create_signer_runtime_generation_reader_authority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_verifier_authority import (
    create_signer_runtime_generation_verifier_authority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_witness_binding import (
    SignerRuntimeGenerationWitnessBinding,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)


class GenerationSigner:
    def __init__(self, private_key=None) -> None:
        self.private_key = private_key or Ed25519PrivateKey.generate()
        public = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_key = encode_ed25519_public_key(public)
        self.verifier_authority, self.verifier_boundary = (
            create_signer_runtime_generation_verifier_authority(
                self.public_key
            )
        )
        self.authenticator_id = self.verifier.authenticator_id

    @property
    def verifier(self):
        return self.verifier_boundary.require(self.verifier_authority)

    def authenticate(self, payload: bytes) -> str:
        return encode_ed25519_signature(self.private_key.sign(payload))


class HighWaterBoundary:
    def __init__(self, store) -> None:
        self.capability = object()
        self.verified = VerifiedSignerRuntimeGenerationHighWater(
            store=store,
            store_id=store.store_id,
            durability_receipt_id=store.durability_receipt_id,
        )

    def require(self, value: object):
        if value is not self.capability:
            raise ValueError("test_high_water_authority_invalid")
        return self.verified


def generation_witness_binding(
    *,
    authenticator_id: str,
    runtime_root: Path,
    high_water_store_id: str,
    high_water_durability_receipt_id: str,
    witness_store_id: str,
    witness_durability_receipt_id: str,
) -> SignerRuntimeGenerationWitnessBinding:
    return SignerRuntimeGenerationWitnessBinding(
        authenticator_id=authenticator_id,
        signer_public_key_fingerprint=_digest_text(authenticator_id),
        key_epoch="test-key-epoch:v1",
        runtime_root_digest=_digest_text(str(runtime_root.resolve())),
        high_water_store_id=high_water_store_id,
        high_water_durability_receipt_id=high_water_durability_receipt_id,
        witness_store_id=witness_store_id,
        witness_durability_receipt_id=witness_durability_receipt_id,
    )


def create_lifecycle_generation_authority(
    repo: Path,
    values: dict[str, object],
    *,
    manifest_id: str | None = None,
    return_writer: bool = False,
):
    runtime = Path(str(values["runtime_root"]))
    authority_root = runtime.parent / "signer-authority"
    authority_root.mkdir(exist_ok=True)
    signing = GenerationSigner()
    high_water = _high_water_store(repo, authority_root, signing)
    high_water_boundary = HighWaterBoundary(high_water)
    writer = DurableSignerRuntimeGenerationAnchor(
        runtime / "generation-anchor.json",
        allowed_root=runtime,
        repo_root=repo,
        anchor_id="reddog-signer:production",
        signer=signing,
        verifier=signing.verifier,
        high_water_authority=high_water_boundary.capability,
        high_water_authority_boundary=high_water_boundary,
    )
    writer.activate(
        _binding(values, manifest_id=manifest_id),
        expected_revision=None,
    )
    high_reader = AtomicSignerRuntimeGenerationHighWaterReader(
        authority_root / "high-water.json",
        allowed_root=authority_root,
        repo_root=repo,
        store_id=high_water.store_id,
        durability_receipt_id=high_water.durability_receipt_id,
        verifier_authority=signing.verifier_authority,
        verifier_authority_boundary=signing.verifier_boundary,
        generation_witness_reader=high_water._witness.reader(),
        generation_witness_binding=high_water._witness_binding,
    )
    high_authority, high_boundary = (
        create_signer_runtime_generation_high_water_reader_authority(
            high_reader
        )
    )
    reader = DurableSignerRuntimeGenerationReader(
        runtime / "generation-anchor.json",
        allowed_root=runtime,
        repo_root=repo,
        anchor_id="reddog-signer:production",
        verifier_authority=signing.verifier_authority,
        verifier_authority_boundary=signing.verifier_boundary,
        high_water_authority=high_authority,
        high_water_authority_boundary=high_boundary,
    )
    authority = create_signer_runtime_generation_reader_authority(reader)
    if return_writer:
        return (*authority, writer)
    return authority


def _high_water_store(
    repo: Path,
    authority_root: Path,
    signing: GenerationSigner,
):
    witness_root = authority_root.parent / "signer-generation-witness"
    witness_root.mkdir(exist_ok=True)
    witness = SqliteMonotonicAuthorityStore(
        witness_root / "generation.sqlite3",
        allowed_root=witness_root,
        repo_root=repo,
        store_id="signer-generation-witness:v1",
        durability_receipt_id="sha256:" + "7" * 64,
    )
    return AtomicSignerRuntimeGenerationHighWaterStore(
        authority_root / "high-water.json",
        allowed_root=authority_root,
        repo_root=repo,
        store_id="signer-high-water:v1",
        durability_receipt_id="sha256:" + "8" * 64,
        signer=signing,
        verifier=signing.verifier,
        generation_witness_store=witness,
        generation_witness_binding=generation_witness_binding(
            authenticator_id=signing.authenticator_id,
            runtime_root=authority_root.parent / "signer-runtime",
            high_water_store_id="signer-high-water:v1",
            high_water_durability_receipt_id="sha256:" + "8" * 64,
            witness_store_id=witness.store_id,
            witness_durability_receipt_id=witness.durability_receipt_id,
        ),
    )


def _digest_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _binding(
    values: dict[str, object],
    *,
    manifest_id: str | None,
) -> SignerRuntimeGenerationBinding:
    return SignerRuntimeGenerationBinding(
        generation=1,
        manifest_id=manifest_id or str(values["manifest_id"]),
        artifact_generation_digest=str(values["artifact_generation_digest"]),
        config_digest=str(values["config_digest"]),
        config_raw_digest=str(values["config_raw_digest"]),
        run_packet_digest=str(values["run_packet_digest"]),
    )


__all__ = [
    "GenerationSigner",
    "HighWaterBoundary",
    "create_lifecycle_generation_authority",
    "generation_witness_binding",
]
