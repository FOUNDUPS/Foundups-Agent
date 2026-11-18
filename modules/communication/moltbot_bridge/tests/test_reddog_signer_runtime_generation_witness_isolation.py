"""Witness-reader ownership regressions for signer generations."""

from __future__ import annotations

from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water import (
    AtomicSignerRuntimeGenerationHighWaterReader,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    SignerRuntimeGenerationHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_runtime_generation_reader import (
    Ed25519GenerationSigner,
    _roots,
    _sha,
    _witness,
    _witness_binding,
)


def test_high_water_reader_does_not_retain_caller_witness(
    tmp_path: Path,
) -> None:
    repo, _, authority = _roots(tmp_path)
    signing = Ed25519GenerationSigner()
    witness = _witness(repo, authority)
    binding = _witness_binding(signing.authenticator_id, authority)
    anchor_id = "reddog-signer:production"
    witness_digest = binding.anchor_binding_digest(anchor_id)
    witness.advance(
        witness_digest,
        expected=None,
        next_value=ProposalReplayHighWater(1, "1" * 64),
    )
    supplied_reader = witness.reader()
    high_reader = AtomicSignerRuntimeGenerationHighWaterReader(
        authority / "high-water.json",
        allowed_root=authority,
        repo_root=repo,
        store_id="high-water:production",
        durability_receipt_id=_sha("e"),
        verifier_authority=signing.verifier_authority,
        verifier_authority_boundary=signing.verifier_boundary,
        generation_witness_reader=supplied_reader,
        generation_witness_binding=binding,
    )
    attacker = SqliteMonotonicAuthorityStore(
        witness.rollback_domain_root / "attacker.sqlite3",
        allowed_root=witness.rollback_domain_root,
        repo_root=repo,
        store_id=witness.store_id,
        durability_receipt_id=witness.durability_receipt_id,
    )
    attacker.advance(
        witness_digest,
        expected=None,
        next_value=ProposalReplayHighWater(1, "2" * 64),
    )

    object.__setattr__(supplied_reader, "_path", attacker._path)

    assert high_reader.witness_load(anchor_id) == (
        SignerRuntimeGenerationHighWater(1, "1" * 64)
    )
