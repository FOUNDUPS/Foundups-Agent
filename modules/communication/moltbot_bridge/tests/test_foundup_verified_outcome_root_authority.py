"""Root-authority and replay tests for verified FoundUp outcomes."""

from __future__ import annotations

import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import (
    DESCRIPTOR_SCHEMA,
    HELD_OUT_VERIFIER_CLASS,
    VERIFIER_CLASS,
    authorization_id_for,
    authority_context_digest_for,
    canonical_held_out_authorization_input,
    canonical_verifier_authorization_input,
    create_root_verified_outcome_signing_authority,
    descriptor_id_for,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
    encode_ed25519_signature,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)


pytest.importorskip("cryptography")
REPO_ROOT = Path(__file__).resolve().parents[4]
NOW = 1_800_000_000


def _private_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    return Ed25519PrivateKey.generate()


def _public_text(private_key) -> str:
    from cryptography.hazmat.primitives import serialization

    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return encode_ed25519_public_key(raw)


def _sign(private_key, value: str) -> str:
    return encode_ed25519_signature(private_key.sign(value.encode("utf-8")))


def _sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _store(tmp_path: Path, *, suffix: str = "one") -> SqliteMonotonicAuthorityStore:
    root = tmp_path / f"replay-{suffix}"
    store = SqliteMonotonicAuthorityStore(
        root / "authority.sqlite3",
        allowed_root=root,
        repo_root=REPO_ROOT,
        store_id=f"verified-outcome-replay-{suffix}",
        durability_receipt_id=_sha(f"durability-{suffix}"),
    )
    anchor = _sha(f"anchor-{suffix}")
    store.advance(
        anchor,
        expected=None,
        next_value=ProposalReplayHighWater(
            1, hashlib.sha256(anchor.encode()).hexdigest()
        ),
    )
    return store


def _descriptor(tmp_path: Path, *, grant_overrides: dict[str, object] | None = None):
    signer_key = _private_key()
    verifier_key = _private_key()
    held_out_key = _private_key()
    store = _store(tmp_path)
    anchor_binding = _sha("anchor-one")
    anchor = store.load(anchor_binding)
    assert anchor is not None
    descriptor = {
        "schema_version": DESCRIPTOR_SCHEMA,
        "descriptor_id": "pending",
        "authority_generation_id": "verified-outcome-authority-generation-1",
        "issuer_principal_id": "github:012",
        "reddog_id": "reddog-0102",
        "foundup_id": "foundups-agent",
        "authority_tier": "HIGH",
        "consensus_receipt_digest": _sha("consensus"),
        "signer_public_key": _public_text(signer_key),
        "signer_key_epoch": "epoch-1",
        "signer_run_packet_id": _sha("run-packet"),
        "signer_config_digest": _sha("signer-config"),
        "signer_session_id": "signer-session-1",
        "signer_manifest_id": _sha("signer-manifest"),
        "signer_artifact_generation_digest": _sha("signer-generation"),
        "replay_store_id": store.store_id,
        "replay_store_durability_receipt_id": store.durability_receipt_id,
        "replay_anchor_binding_digest": anchor_binding,
        "replay_anchor_sequence": anchor.sequence,
        "replay_anchor_revision": anchor.state_revision,
        "issued_at": NOW - 2,
        "expires_at": NOW + 301,
        "grants": [],
        "revoked_authorization_ids": [],
        "revoked_verifier_fingerprints": [],
    }
    grant = {
        "authorization_id": "pending",
        "authority_context_digest": authority_context_digest_for(descriptor),
        "receipt_id": "verified-outcome-test",
        "evidence_digest": _sha("evidence"),
        "foundup_id": "foundups-agent",
        "snapshot_id": _sha("snapshot"),
        "snapshot_content_digest": _sha("snapshot-content"),
        "work_order_id": "work-order-1",
        "slice_id": "FOUNDUP_VERIFIED_OUTCOME_ROOT_AUTHORITY_SUPPLY_PHASE1",
        "job_id": "job-1",
        "head_sha": "a" * 40,
        "content_digest": _sha("content"),
        "worker_id": "author-worker",
        "verifier_id": "independent-verifier",
        "verifier_class": VERIFIER_CLASS,
        "verifier_public_key": _public_text(verifier_key),
        "verification_receipt_digest": _sha("verification-receipt"),
        "verification_signature": "pending",
        "held_out_verifier_id": "held-out-verifier",
        "held_out_verifier_class": HELD_OUT_VERIFIER_CLASS,
        "held_out_verifier_public_key": _public_text(held_out_key),
        "held_out_receipt_digest": _sha("held-out-receipt"),
        "held_out_signature": "pending",
        "runtime_binding_receipt_id": "runtime-binding-1",
        "runtime_binding_digest": _sha("runtime-binding"),
        "pattern_memory_record_digest": _sha("pattern-memory-record"),
        "issued_at": NOW - 1,
        "expires_at": NOW + 300,
    }
    if grant_overrides:
        grant.update(grant_overrides)
    grant["authorization_id"] = authorization_id_for(grant)
    grant["verification_signature"] = _sign(
        verifier_key, canonical_verifier_authorization_input(grant)
    )
    grant["held_out_signature"] = _sign(
        held_out_key, canonical_held_out_authorization_input(grant)
    )
    descriptor["grants"] = [grant]
    descriptor["descriptor_id"] = descriptor_id_for(descriptor)
    return descriptor, grant, store


def _authority(descriptor, store, *, supplier=None, clock=None):
    return create_root_verified_outcome_signing_authority(
        descriptor,
        replay_store=store,
        now_epoch=NOW,
        owner_config_id=_sha("owner-config"),
        current_descriptor_supplier=supplier or (lambda: descriptor),
        clock=clock or (lambda: NOW),
    )


def _reserve(authority, grant):
    return authority.reserve(
        receipt_id=grant["receipt_id"],
        work_order_id=grant["work_order_id"],
        evidence_digest=grant["evidence_digest"],
        issued_at=NOW,
    )


def test_root_authority_burns_exact_grant_across_instances(tmp_path: Path) -> None:
    descriptor, grant, store = _descriptor(tmp_path)
    first = _authority(descriptor, store)
    reservation = _reserve(first, grant)
    first.commit(reservation)

    reopened = SqliteMonotonicAuthorityStore(
        tmp_path / "replay-one" / "authority.sqlite3",
        allowed_root=tmp_path / "replay-one",
        repo_root=REPO_ROOT,
        store_id=store.store_id,
        durability_receipt_id=store.durability_receipt_id,
    )
    second = _authority(descriptor, reopened)

    assert reservation is not None
    assert _reserve(first, grant) is None
    assert _reserve(second, grant) is None


def test_concurrent_reservation_has_exactly_one_winner(tmp_path: Path) -> None:
    descriptor, grant, store = _descriptor(tmp_path)
    authorities = tuple(_authority(descriptor, store) for _ in range(8))
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = tuple(pool.map(lambda item: _reserve(item, grant), authorities))
    assert sum(item is not None for item in results) == 1


def test_duplicate_grants_reject(tmp_path: Path) -> None:
    descriptor, grant, store = _descriptor(tmp_path)
    duplicate = copy.deepcopy(descriptor)
    duplicate["grants"] = [grant, copy.deepcopy(grant)]
    duplicate["descriptor_id"] = descriptor_id_for(duplicate)

    with pytest.raises(ValueError, match="authorization_duplicate"):
        _authority(duplicate, store)


@pytest.mark.parametrize(
    "issued_at,expires_at",
    ((NOW - 10, NOW - 1), (NOW + 1, NOW + 100)),
)
def test_signed_stale_or_future_grant_rejects(
    tmp_path: Path, issued_at: int, expires_at: int
) -> None:
    descriptor, _grant, store = _descriptor(
        tmp_path,
        grant_overrides={"issued_at": issued_at, "expires_at": expires_at},
    )

    with pytest.raises(ValueError, match="authority_expired"):
        _authority(descriptor, store)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("foundup_id", "attacker-foundup"),
        ("snapshot_id", _sha("attacker-snapshot")),
        ("work_order_id", "attacker-work-order"),
        ("head_sha", "b" * 40),
        ("runtime_binding_digest", _sha("attacker-runtime")),
        ("pattern_memory_record_digest", _sha("attacker-record")),
    ),
)
def test_rehashed_tampering_cannot_reuse_verifier_signatures(
    tmp_path: Path, field: str, replacement: str
) -> None:
    descriptor, _grant, store = _descriptor(tmp_path)
    forged = copy.deepcopy(descriptor)
    forged["grants"][0][field] = replacement
    forged["grants"][0]["authorization_id"] = authorization_id_for(forged["grants"][0])
    forged["descriptor_id"] = descriptor_id_for(forged)
    with pytest.raises(ValueError, match="signature_invalid|foundup_scope_invalid"):
        _authority(forged, store)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("authority_generation_id", "attacker-generation"),
        ("issuer_principal_id", "github:attacker"),
        ("reddog_id", "attacker-reddog"),
        ("foundup_id", "attacker-foundup"),
        ("authority_tier", "LOW"),
        ("consensus_receipt_digest", _sha("attacker-consensus")),
        ("signer_public_key", _public_text(_private_key())),
        ("signer_key_epoch", "epoch-attacker"),
        ("signer_run_packet_id", _sha("attacker-run-packet")),
        ("signer_config_digest", _sha("attacker-config")),
        ("signer_session_id", "attacker-session"),
        ("signer_manifest_id", _sha("attacker-manifest")),
        ("signer_artifact_generation_digest", _sha("attacker-generation")),
        ("issued_at", NOW - 3),
        ("expires_at", NOW + 302),
    ),
)
def test_cosigned_grant_cannot_move_to_another_authority_context(
    tmp_path: Path, field: str, replacement: object
) -> None:
    descriptor, _grant, store = _descriptor(tmp_path)
    transplanted = copy.deepcopy(descriptor)
    transplanted[field] = replacement
    grant = transplanted["grants"][0]
    if field == "foundup_id":
        grant["foundup_id"] = replacement
    grant["authority_context_digest"] = authority_context_digest_for(transplanted)
    grant["authorization_id"] = authorization_id_for(grant)
    transplanted["descriptor_id"] = descriptor_id_for(transplanted)

    with pytest.raises(ValueError, match="signature_invalid"):
        _authority(transplanted, store)


def test_cosigned_grant_cannot_move_to_another_replay_anchor(tmp_path: Path) -> None:
    descriptor, _grant, store = _descriptor(tmp_path)
    binding = _sha("replacement-anchor")
    revision = hashlib.sha256(binding.encode()).hexdigest()
    store.advance(
        binding,
        expected=None,
        next_value=ProposalReplayHighWater(1, revision),
    )
    transplanted = copy.deepcopy(descriptor)
    transplanted["replay_anchor_binding_digest"] = binding
    transplanted["replay_anchor_revision"] = revision
    grant = transplanted["grants"][0]
    grant["authority_context_digest"] = authority_context_digest_for(transplanted)
    grant["authorization_id"] = authorization_id_for(grant)
    transplanted["descriptor_id"] = descriptor_id_for(transplanted)

    with pytest.raises(ValueError, match="signature_invalid"):
        _authority(transplanted, store)


def test_revoked_verifier_and_authorization_reject(tmp_path: Path) -> None:
    descriptor, grant, store = _descriptor(tmp_path)
    by_id = copy.deepcopy(descriptor)
    by_id["revoked_authorization_ids"] = [grant["authorization_id"]]
    by_id["descriptor_id"] = descriptor_id_for(by_id)
    by_key = copy.deepcopy(descriptor)
    by_key["revoked_verifier_fingerprints"] = [
        public_key_fingerprint(grant["verifier_public_key"])
    ]
    by_key["descriptor_id"] = descriptor_id_for(by_key)
    by_held_out_key = copy.deepcopy(descriptor)
    by_held_out_key["revoked_verifier_fingerprints"] = [
        public_key_fingerprint(grant["held_out_verifier_public_key"])
    ]
    by_held_out_key["descriptor_id"] = descriptor_id_for(by_held_out_key)
    with pytest.raises(ValueError, match="grant_revoked"):
        _authority(by_id, store)
    with pytest.raises(ValueError, match="grant_revoked"):
        _authority(by_key, store)
    with pytest.raises(ValueError, match="grant_revoked"):
        _authority(by_held_out_key, store)


def test_live_root_revocation_blocks_unused_loaded_grant(tmp_path: Path) -> None:
    descriptor, grant, store = _descriptor(tmp_path)
    current = {"descriptor": descriptor}
    authority = _authority(
        descriptor,
        store,
        supplier=lambda: current["descriptor"],
    )
    revoked = copy.deepcopy(descriptor)
    revoked["revoked_authorization_ids"] = [grant["authorization_id"]]
    revoked["descriptor_id"] = descriptor_id_for(revoked)
    current["descriptor"] = revoked

    assert _reserve(authority, grant) is None


def test_fresh_clock_blocks_grant_after_expiry(tmp_path: Path) -> None:
    descriptor, grant, store = _descriptor(
        tmp_path,
        grant_overrides={"expires_at": NOW + 100},
    )
    clock = {"now": NOW}
    authority = _authority(descriptor, store, clock=lambda: clock["now"])
    clock["now"] = NOW + 159

    assert _reserve(authority, grant) is None


def test_reservation_rejects_wrong_scope_and_time_without_burning(tmp_path: Path) -> None:
    descriptor, grant, store = _descriptor(tmp_path)
    authority = _authority(descriptor, store)

    assert authority.reserve(
        receipt_id="wrong-receipt",
        work_order_id=grant["work_order_id"],
        evidence_digest=grant["evidence_digest"],
        issued_at=NOW,
    ) is None
    assert authority.reserve(
        receipt_id=grant["receipt_id"],
        work_order_id="wrong-work-order",
        evidence_digest=grant["evidence_digest"],
        issued_at=NOW,
    ) is None
    assert authority.reserve(
        receipt_id=grant["receipt_id"],
        work_order_id=grant["work_order_id"],
        evidence_digest=_sha("wrong-evidence"),
        issued_at=NOW,
    ) is None
    assert authority.reserve(
        receipt_id=grant["receipt_id"],
        work_order_id=grant["work_order_id"],
        evidence_digest=grant["evidence_digest"],
        issued_at=grant["expires_at"],
    ) is None
    assert _reserve(authority, grant) is not None


def test_descriptor_cannot_cross_foundup_scope(tmp_path: Path) -> None:
    descriptor, _grant, store = _descriptor(tmp_path)
    forged = copy.deepcopy(descriptor)
    forged["foundup_id"] = "attacker-foundup"
    forged["descriptor_id"] = descriptor_id_for(forged)

    with pytest.raises(ValueError, match="foundup_scope_invalid"):
        _authority(forged, store)


def test_signer_verifier_or_worker_verifier_collapse_rejects(tmp_path: Path) -> None:
    descriptor, grant, store = _descriptor(tmp_path)
    collapsed_key = copy.deepcopy(descriptor)
    collapsed_key["signer_public_key"] = grant["verifier_public_key"]
    collapsed_key["descriptor_id"] = descriptor_id_for(collapsed_key)
    collapsed_identity = copy.deepcopy(descriptor)
    collapsed_identity["grants"][0]["worker_id"] = grant["verifier_id"]
    collapsed_identity["grants"][0]["authorization_id"] = authorization_id_for(
        collapsed_identity["grants"][0]
    )
    collapsed_identity["descriptor_id"] = descriptor_id_for(collapsed_identity)
    with pytest.raises(ValueError, match="authority_collapse"):
        _authority(collapsed_key, store)
    with pytest.raises(ValueError, match="grant_id_invalid|authority_collapse"):
        _authority(collapsed_identity, store)


def test_root_cannot_authorize_unknown_verifier_classes(tmp_path: Path) -> None:
    descriptor, _grant, store = _descriptor(tmp_path)
    verifier_key = _private_key()
    forged = copy.deepcopy(descriptor)
    grant = forged["grants"][0]
    grant["verifier_class"] = "caller-selected-verifier"
    grant["verifier_public_key"] = _public_text(verifier_key)
    grant["authorization_id"] = authorization_id_for(grant)
    grant["verification_signature"] = _sign(
        verifier_key, canonical_verifier_authorization_input(grant)
    )
    forged["descriptor_id"] = descriptor_id_for(forged)

    with pytest.raises(ValueError, match="verifier_class_invalid"):
        _authority(forged, store)


def test_expired_or_wrong_store_or_reset_store_rejects(tmp_path: Path) -> None:
    descriptor, _grant, store = _descriptor(tmp_path)
    expired = copy.deepcopy(descriptor)
    expired["issued_at"] = NOW - 700
    expired["expires_at"] = NOW - 1
    expired["descriptor_id"] = descriptor_id_for(expired)
    other = _store(tmp_path, suffix="other")
    reset = SqliteMonotonicAuthorityStore(
        tmp_path / "reset" / "authority.sqlite3",
        allowed_root=tmp_path / "reset",
        repo_root=REPO_ROOT,
        store_id=store.store_id,
        durability_receipt_id=store.durability_receipt_id,
    )
    with pytest.raises(ValueError, match="authority_expired"):
        _authority(expired, store)
    with pytest.raises(ValueError, match="replay_store_invalid"):
        _authority(descriptor, other)
    with pytest.raises(ValueError, match="replay_store_invalid"):
        _authority(descriptor, reset)


def test_unknown_fields_direct_construction_and_forged_reservation_reject(
    tmp_path: Path,
) -> None:
    descriptor, grant, store = _descriptor(tmp_path)
    forged = copy.deepcopy(descriptor)
    forged["caller_authorized"] = True
    with pytest.raises(ValueError, match="shape_invalid"):
        _authority(forged, store)
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import (
        RootVerifiedOutcomeSigningAuthority,
    )

    with pytest.raises(TypeError, match="factory_required"):
        RootVerifiedOutcomeSigningAuthority()
    authority = _authority(descriptor, store)
    with pytest.raises(ValueError, match="reservation_invalid"):
        authority.commit({"receipt_id": grant["receipt_id"]})
