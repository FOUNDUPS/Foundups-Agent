"""Multiprocess support for signer runtime atomic provisioning tests."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water import (
    AtomicSignerRuntimeGenerationHighWaterStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning import (
    provision_signer_runtime_generation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning_contract import (
    create_signer_runtime_atomic_provisioning_context,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    DurableSignerRuntimeGenerationAnchor,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)
from modules.communication.moltbot_bridge.tests.reddog_signer_generation_test_support import (
    GenerationSigner,
    HighWaterBoundary,
    generation_witness_binding,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import (
    NOW,
    _issue_harness_authority,
    _manifest_signing_context,
)


def process_provision(values: dict, output) -> None:
    import modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning as target

    target._trusted_now = lambda: NOW
    if os.name != "nt":
        target.runtime_artifact_activation_lease = (
            _test_only_activation_lease
        )
    repo = Path(values["repo_root"])
    runtime = Path(values["runtime_root"])
    reddog_private = Ed25519PrivateKey.from_private_bytes(
        values["reddog_private"]
    )
    generation_signer = GenerationSigner(
        Ed25519PrivateKey.from_private_bytes(values["generation_private"])
    )
    _, boundary, authority = _issue_harness_authority(
        repo,
        runtime,
        values["work_state"],
        values["principal_public"],
        values["identity"],
        values["work_authority"],
        values["queue_item_id"],
    )
    _, signing_context = _manifest_signing_context(
        authority,
        boundary,
        reddog_private,
        values["reddog_public"],
    )
    anchor = _process_generation_anchor(values, repo, generation_signer)
    result = provision_signer_runtime_generation(
        nonce="process-provision-generation-1",
        ttl_seconds=120,
        context=create_signer_runtime_atomic_provisioning_context(
            manifest_signing=signing_context,
            generation_anchor=anchor,
        ),
    )
    output.put(result.to_dict())


@contextmanager
def _test_only_activation_lease(*_args, **_kwargs):
    """Exercise transaction concurrency without claiming a POSIX lease."""

    yield


def _process_generation_anchor(values, repo, generation_signer):
    witness = SqliteMonotonicAuthorityStore(
        Path(values["witness_root"]) / "generation.sqlite3",
        allowed_root=values["witness_root"],
        repo_root=repo,
        store_id="process-generation-witness:v1",
        durability_receipt_id="sha256:" + "7" * 64,
    )
    high_water = AtomicSignerRuntimeGenerationHighWaterStore(
        Path(values["authority_root"]) / "high-water.json",
        allowed_root=values["authority_root"],
        repo_root=repo,
        store_id="process-high-water:v1",
        durability_receipt_id="sha256:" + "6" * 64,
        signer=generation_signer,
        verifier=generation_signer.verifier,
        generation_witness_store=witness,
        generation_witness_binding=generation_witness_binding(
            authenticator_id=generation_signer.authenticator_id,
            runtime_root=Path(values["runtime_root"]),
            high_water_store_id="process-high-water:v1",
            high_water_durability_receipt_id="sha256:" + "6" * 64,
            witness_store_id=witness.store_id,
            witness_durability_receipt_id=witness.durability_receipt_id,
        ),
    )
    boundary = HighWaterBoundary(high_water)
    return DurableSignerRuntimeGenerationAnchor(
        Path(values["anchor_root"]) / "generation-anchor.json",
        allowed_root=values["anchor_root"],
        repo_root=repo,
        anchor_id="reddog-signer:process-test",
        signer=generation_signer,
        verifier=generation_signer.verifier,
        high_water_authority=boundary.capability,
        high_water_authority_boundary=boundary,
    )


__all__ = ["process_provision"]
