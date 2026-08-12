from __future__ import annotations

import ast
import hashlib
import multiprocessing
import sqlite3
import threading
from dataclasses import fields, replace
from pathlib import Path
from typing import Any, Mapping

import pytest

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_state import (
    INSTALLATION_BINDING,
    RootVerifiedOutcomeAuthorityState,
    root_authority_state_binding_digest,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    STORE_SCHEMA,
    SignerGrantRevocationAuthorityBinding,
    expected_snapshot_binding,
    revocation_authority_binding_from_policy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_store import (
    SignerGrantRevocationAuthorityStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_supply import (
    UncomposedDurableSignerGrantRevocationAuthoritySupply,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_contract import (
    SNAPSHOT_SCHEMA,
    canonical_signer_grant_revocation_snapshot_input,
    signer_grant_revocation_snapshot_id,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_durable_oracle import (
    UncomposedDurableSignerGrantRevocationOracle,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_root_anchor import (
    require_revocation_root_anchor,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityStore,
)

NOW = 1_780_000_000
REPO_ROOT = Path(__file__).parents[4]
SOURCE_ROOT = REPO_ROOT / "modules/communication/moltbot_bridge/src"
SLICE_MODULES = (
    "reddog_signer_secret_grant_revocation_authority_binding.py",
    "reddog_signer_secret_grant_revocation_authority_reader.py",
    "reddog_signer_secret_grant_revocation_authority_store.py",
    "reddog_signer_secret_grant_revocation_authority_supply.py",
    "reddog_signer_secret_grant_revocation_durable_oracle.py",
    "reddog_signer_secret_grant_revocation_root_anchor.py",
    "reddog_signer_secret_grant_revocation_snapshot_validation.py",
    "reddog_signer_secret_grant_revocation_store_codec.py",
)
UNCOMPOSED_MODULES = (
    "reddog_signer_secret_grant_revocation_authority_supply.py",
    "reddog_signer_secret_grant_revocation_durable_oracle.py",
)


def _digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("ascii")).hexdigest()


def _policy(tmp_path: Path) -> dict[str, Any]:
    primary, witness, signer = (
        tmp_path / "primary", tmp_path / "witness", tmp_path / "signer"
    )
    anchor_roots = {
        "state": tmp_path / "anchor-primary",
        "state_witness": tmp_path / "anchor-witness",
        "installation": tmp_path / "anchor-installation",
    }
    for root in (primary, witness, signer, *anchor_roots.values()):
        root.mkdir()
    anchor_bindings = {
        name: {
            "root": str(root.resolve()),
            "path": str((root / f"{name}.sqlite3").resolve()),
            "store_id": f"revocation-anchor-{name}",
            "durability_receipt_id": _digest(f"anchor-{name}-durable"),
        }
        for name, root in anchor_roots.items()
    }
    return {
        "policy_id": _digest("policy"), "owner_config_id": _digest("owner"),
        "manifest_id": _digest("manifest"),
        "artifact_generation_digest": _digest("generation"),
        "revocation_authority_principal_id": "principal:revocation-admin",
        "revocation_authority_principal_provider": "github",
        "revocation_authority_public_key": "public-key-v1:revocation-admin",
        "target_signer_agent_id": "signer:reddog",
        "target_signer_profile_id": "reddog-work-authority",
        "target_signer_public_key": "public-key-v1:target",
        "target_signer_key_epoch": "target-epoch-1",
        "target_signer_generation_id": _digest("signer-generation"),
        "revocation_root": str(primary.resolve()),
        "revocation_path": str((primary / "revocations.sqlite3").resolve()),
        "revocation_store_id": "signer-grant-revocations",
        "revocation_store_durability_receipt_id": _digest("primary-durable"),
        "revocation_snapshot_schema": SNAPSHOT_SCHEMA,
        "revocation_store_schema": STORE_SCHEMA,
        "revocation_witness_root": str(witness.resolve()),
        "revocation_witness_path": str((witness / "high-water.sqlite3").resolve()),
        "revocation_witness_store_id": "signer-grant-revocation-witness",
        "revocation_witness_store_durability_receipt_id": _digest("witness-durable"),
        "revocation_anchor_store_id": anchor_bindings["state"]["store_id"],
        "revocation_anchor_store_durability_receipt_id": (
            anchor_bindings["state"]["durability_receipt_id"]
        ),
        "revocation_anchor_state_binding_digest": (
            root_authority_state_binding_digest(anchor_bindings)
        ),
        "revocation_lock_path": str(
            (primary / "revocations.sqlite3.authority.lock").resolve()
        ),
        "signer_runtime_root": signer,
    }


class _Resolver:
    @staticmethod
    def resolve(principal_id: str, provider: str) -> str | None:
        if (principal_id, provider) == ("principal:revocation-admin", "github"):
            return "public-key-v1:revocation-admin"
        return None


class _Verifier:
    @staticmethod
    def verify(public_key: str, signing_input: str, signature: str) -> bool:
        return (
            public_key == "public-key-v1:revocation-admin"
            and signature == _digest(signing_input)
        )


def _snapshot(
    policy: Mapping[str, Any], binding: SignerGrantRevocationAuthorityBinding,
    *, sequence: int = 1, grant_ids: tuple[str, ...] = (),
    key_epochs: tuple[str, ...] = (), expires_at: int = NOW + 100,
) -> dict[str, Any]:
    expected = expected_snapshot_binding(policy, binding)
    value = {
        "schema_version": SNAPSHOT_SCHEMA, "snapshot_id": _digest("pending"),
        **{item.name: getattr(expected, item.name) for item in fields(expected)},
        "sequence": sequence, "issued_at": NOW - 10, "expires_at": expires_at,
        "revoked_grant_ids": sorted(grant_ids),
        "revoked_key_epochs": sorted(key_epochs), "signature": "pending",
    }
    value["snapshot_id"] = signer_grant_revocation_snapshot_id(value)
    value["signature"] = _digest(canonical_signer_grant_revocation_snapshot_input(value))
    return value


def _open_runtime(policy: Mapping[str, Any]):
    binding = revocation_authority_binding_from_policy(
        policy, repo_root=REPO_ROOT, signer_runtime_root=policy["signer_runtime_root"]
    )
    store = SignerGrantRevocationAuthorityStore(binding, repo_root=REPO_ROOT)
    witness = SqliteMonotonicAuthorityStore(
        binding.witness_path, allowed_root=binding.witness_root,
        repo_root=REPO_ROOT, store_id=binding.witness_store_id,
        durability_receipt_id=binding.witness_durability_receipt_id,
    )
    anchor = _open_anchor(policy)
    supply = UncomposedDurableSignerGrantRevocationAuthoritySupply(
        binding=binding, policy=policy, store=store, witness=witness, anchor=anchor,
        principal_key_resolver=_Resolver(), signature_verifier=_Verifier(),
    )
    return binding, store, witness, anchor, supply


def _open_anchor(policy: Mapping[str, Any]) -> RootVerifiedOutcomeAuthorityState:
    parent = Path(policy["revocation_root"]).parent
    values = []
    root_names = {
        "state": "anchor-primary",
        "state_witness": "anchor-witness",
        "installation": "anchor-installation",
    }
    for name in ("state", "state_witness", "installation"):
        root = parent / root_names[name]
        values.append(
            SqliteMonotonicAuthorityStore(
                root / f"{name}.sqlite3", allowed_root=root,
                repo_root=REPO_ROOT, store_id=f"revocation-anchor-{name}",
                durability_receipt_id=_digest(f"anchor-{name}-durable"),
            )
        )
    state = RootVerifiedOutcomeAuthorityState(
        *values, repo_root=REPO_ROOT, require_root_ownership=False,
    )
    if values[2].load(INSTALLATION_BINDING) is None:
        state.initialize(
            generation=ProposalReplayHighWater(1, _digest("anchor-owner")[7:]),
            replay_binding=_digest("anchor-bootstrap-binding"),
            replay_anchor=ProposalReplayHighWater(
                1, _digest("anchor-bootstrap")[7:]
            ),
            installation_revision=_digest("anchor-installation")[7:],
        )
    return state


def _runtime(tmp_path: Path):
    policy = _policy(tmp_path)
    return (policy, *_open_runtime(policy))


def _recover_in_process(
    policy: Mapping[str, Any], now_epoch: int, output: Any,
) -> None:
    try:
        _binding, _store, _witness, _anchor, supply = _open_runtime(policy)
        recovered = supply.recover(now_epoch=now_epoch)
        output.put(("ok", None if recovered is None else recovered["snapshot_id"]))
    except Exception as exc:
        output.put(("error", type(exc).__name__))


def _publish_in_process(
    policy: Mapping[str, Any], snapshot: Mapping[str, Any],
    attempting: Any, done: Any, output: Any,
) -> None:
    try:
        _binding, _store, _witness, _anchor, supply = _open_runtime(policy)
        attempting.set()
        published = supply.publish(snapshot, now_epoch=NOW)
        output.put(("ok", published["snapshot_id"]))
    except Exception as exc:
        output.put(("error", type(exc).__name__))
    finally:
        done.set()


def _oracle(policy, binding, store, witness, anchor, *, now: int = NOW):
    return UncomposedDurableSignerGrantRevocationOracle(
        binding=binding, policy=policy, reader=store.reader(),
        witness=witness.reader(), anchor=anchor, principal_key_resolver=_Resolver(),
        signature_verifier=_Verifier(), clock=lambda: now,
    )


def test_signed_policy_freezes_exact_disjoint_topology(tmp_path: Path) -> None:
    policy, binding, store, witness, anchor, _supply = _runtime(tmp_path)
    assert store.path == Path(policy["revocation_path"])
    assert witness.path == Path(policy["revocation_witness_path"])
    assert binding.operation_lock_path == policy["revocation_lock_path"]
    policy["revocation_witness_root"] = policy["revocation_root"]
    policy["revocation_witness_path"] = str(
        Path(policy["revocation_root"]) / "high-water.sqlite3"
    )
    with pytest.raises(ValueError, match="domains_overlap"):
        revocation_authority_binding_from_policy(
            policy, repo_root=REPO_ROOT,
            signer_runtime_root=policy["signer_runtime_root"],
        )


def test_publish_is_monotonic_and_visible_to_fresh_reader(tmp_path: Path) -> None:
    policy, binding, store, witness, anchor, supply = _runtime(tmp_path)
    first = _snapshot(policy, binding, grant_ids=(_digest("grant-a"),))
    assert supply.publish(first, now_epoch=NOW) == first
    assert store.reader().state().current == first
    second = _snapshot(
        policy, binding, sequence=2,
        grant_ids=(_digest("grant-a"), _digest("grant-b")),
    )
    assert supply.publish(second, now_epoch=NOW) == second
    assert _oracle(policy, binding, store, witness, anchor).is_revoked(
        grant_id=_digest("grant-b"), key_epoch="other", at_epoch=NOW
    ) is True


def test_unrevocation_and_wrong_sequence_fail_closed(tmp_path: Path) -> None:
    policy, binding, _store, _witness, _anchor, supply = _runtime(tmp_path)
    first = _snapshot(policy, binding, grant_ids=(_digest("grant-a"),))
    supply.publish(first, now_epoch=NOW)
    with pytest.raises(ValueError, match="unrevocation"):
        supply.publish(_snapshot(policy, binding, sequence=2), now_epoch=NOW)
    with pytest.raises(ValueError, match="sequence_invalid"):
        supply.publish(
            _snapshot(policy, binding, sequence=3, grant_ids=(_digest("grant-a"),)),
            now_epoch=NOW,
        )


@pytest.mark.parametrize("crash_stage", ["prepared", "witness", "anchor"])
def test_crash_recovery_rolls_forward_exact_pending_snapshot(
    tmp_path: Path, crash_stage: str,
) -> None:
    policy, binding, store, witness, anchor, supply = _runtime(tmp_path)
    pending = _snapshot(policy, binding)
    store._prepare_under_lock(pending)
    if crash_stage in {"witness", "anchor"}:
        witness.advance(
            binding.witness_binding_digest(), expected=None,
            next_value=_high_water(pending),
        )
    if crash_stage == "anchor":
        anchor.advance(
            binding.anchor_binding_digest(), expected=None,
            next_value=_high_water(pending),
        )
    context = multiprocessing.get_context("spawn")
    output = context.Queue()
    process = context.Process(
        target=_recover_in_process, args=(policy, NOW, output)
    )
    process.start()
    process.join(10)
    assert process.exitcode == 0
    assert output.get(timeout=5) == ("ok", pending["snapshot_id"])
    assert store.state().pending is None
    assert supply.recover(now_epoch=NOW) == pending


def test_reader_rejects_status_tamper_and_witness_rollback(tmp_path: Path) -> None:
    policy, binding, store, witness, anchor, supply = _runtime(tmp_path)
    current = _snapshot(policy, binding)
    supply.publish(current, now_epoch=NOW)
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE snapshots SET status='PREPARED'")
    with pytest.raises(ValueError, match="snapshot_missing"):
        store.reader().state()
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE snapshots SET status='COMMITTED'")
    with sqlite3.connect(witness.path) as connection:
        connection.execute("DELETE FROM high_water")
    with pytest.raises(RuntimeError, match="witness_mismatch"):
        _oracle(policy, binding, store, witness, anchor).is_revoked(
            grant_id=_digest("none"), key_epoch="none", at_epoch=NOW
        )


def test_coordinated_local_rollback_rejects_against_root_anchor(
    tmp_path: Path,
) -> None:
    policy, binding, store, witness, anchor, supply = _runtime(tmp_path)
    first = _snapshot(policy, binding, grant_ids=(_digest("grant-a"),))
    second = _snapshot(
        policy, binding, sequence=2,
        grant_ids=(_digest("grant-a"), _digest("grant-b")),
    )
    supply.publish(first, now_epoch=NOW)
    supply.publish(second, now_epoch=NOW)
    with sqlite3.connect(store.path) as connection:
        connection.execute("DELETE FROM snapshots WHERE sequence=2")
        connection.execute(
            "UPDATE state SET current_snapshot_id=?, pending_snapshot_id=NULL "
            "WHERE singleton=1",
            (first["snapshot_id"],),
        )
    with sqlite3.connect(witness.path) as connection:
        connection.execute("DELETE FROM high_water")
    reset_witness = SqliteMonotonicAuthorityStore(
        binding.witness_path, allowed_root=binding.witness_root,
        repo_root=REPO_ROOT, store_id=binding.witness_store_id,
        durability_receipt_id=binding.witness_durability_receipt_id,
    )
    reset_witness.advance(
        binding.witness_binding_digest(), expected=None,
        next_value=_high_water(first),
    )
    with pytest.raises(RuntimeError, match="anchor_mismatch"):
        supply.recover(now_epoch=NOW)
    assert anchor.load(binding.anchor_binding_digest()) == _high_water(second)


def test_coordinated_root_mirror_rollback_is_explicit_residual(
    tmp_path: Path,
) -> None:
    policy, binding, store, witness, anchor, supply = _runtime(tmp_path)
    first = _snapshot(policy, binding, grant_ids=(_digest("grant-a"),))
    second = _snapshot(
        policy, binding, sequence=2,
        grant_ids=(_digest("grant-a"), _digest("grant-b")),
    )
    supply.publish(first, now_epoch=NOW)
    supply.publish(second, now_epoch=NOW)
    installation_path = tmp_path / "anchor-installation/installation.sqlite3"
    installation_before = _sqlite_high_water(
        installation_path, INSTALLATION_BINDING,
    )
    with sqlite3.connect(store.path) as connection:
        connection.execute("DELETE FROM snapshots WHERE sequence=2")
        connection.execute(
            "UPDATE state SET current_snapshot_id=?, pending_snapshot_id=NULL",
            (first["snapshot_id"],),
        )
    _overwrite_high_water(
        witness.path, binding.witness_binding_digest(), _high_water(first),
    )
    for path in (
        tmp_path / "anchor-primary/state.sqlite3",
        tmp_path / "anchor-witness/state_witness.sqlite3",
    ):
        _overwrite_high_water(
            path, binding.anchor_binding_digest(), _high_water(first),
        )
    assert _sqlite_high_water(installation_path, INSTALLATION_BINDING) == installation_before
    assert anchor.load(binding.anchor_binding_digest()) == _high_water(first)
    assert _oracle(policy, binding, store, witness, anchor).is_revoked(
        grant_id=_digest("grant-b"), key_epoch="other", at_epoch=NOW,
    ) is False


def test_substituted_root_anchor_identity_rejects_before_publication(
    tmp_path: Path,
) -> None:
    policy, binding, store, witness, anchor, _supply = _runtime(tmp_path)
    other_root = tmp_path / "other"
    other_root.mkdir()
    substituted = _open_anchor(_policy(other_root))
    with pytest.raises(ValueError, match="root_anchor_invalid"):
        UncomposedDurableSignerGrantRevocationAuthoritySupply(
            binding=binding, policy=policy, store=store, witness=witness,
            anchor=substituted, principal_key_resolver=_Resolver(),
            signature_verifier=_Verifier(),
        )
    assert store.state().current is None


def test_self_asserted_anchor_interface_rejects_before_publication(
    tmp_path: Path,
) -> None:
    policy, binding, store, witness, _anchor, _supply = _runtime(tmp_path)
    asserted = type(
        "SelfAssertedAnchor",
        (),
        {
            "durable": True,
            "store_id": binding.anchor_store_id,
            "durability_receipt_id": binding.anchor_durability_receipt_id,
            "state_binding_digest": binding.anchor_state_binding_digest,
            "rollback_domain_roots": (),
        },
    )()
    with pytest.raises(ValueError, match="root_anchor_invalid"):
        UncomposedDurableSignerGrantRevocationAuthoritySupply(
            binding=binding, policy=policy, store=store, witness=witness,
            anchor=asserted, principal_key_resolver=_Resolver(),
            signature_verifier=_Verifier(),
        )
    assert store.state().current is None


def test_root_anchor_rollback_domain_must_not_overlap_revocation_state(
    tmp_path: Path,
) -> None:
    policy, binding, _store, _witness, _anchor, _supply = _runtime(tmp_path)
    roots = (
        Path(binding.primary_root) / "overlapping-root-state",
        tmp_path / "independent-root-witness",
        tmp_path / "independent-root-installation",
    )
    stores = []
    for index, root in enumerate(roots):
        root.mkdir()
        stores.append(
            SqliteMonotonicAuthorityStore(
                root / "state.sqlite3", allowed_root=root,
                repo_root=REPO_ROOT, store_id=f"overlap-anchor-{index}",
                durability_receipt_id=_digest(f"overlap-anchor-{index}"),
            )
        )
    overlapping = RootVerifiedOutcomeAuthorityState(
        *stores, repo_root=REPO_ROOT, require_root_ownership=False,
    )
    matching = replace(
        binding, anchor_store_id=overlapping.store_id,
        anchor_durability_receipt_id=overlapping.durability_receipt_id,
        anchor_state_binding_digest=overlapping.state_binding_digest,
    )
    with pytest.raises(ValueError, match="root_anchor_invalid"):
        require_revocation_root_anchor(matching, overlapping)


def test_recovery_rejects_attacker_rehashed_unsigned_pending(tmp_path: Path) -> None:
    policy, binding, store, witness, anchor, supply = _runtime(tmp_path)
    pending = _snapshot(policy, binding)
    pending["revoked_grant_ids"] = [_digest("attacker")]
    pending["snapshot_id"] = signer_grant_revocation_snapshot_id(pending)
    store._prepare_under_lock(pending)
    with pytest.raises(ValueError, match="authority_invalid"):
        supply.recover(now_epoch=NOW)
    assert witness.load(binding.witness_binding_digest()) is None
    assert store.state().pending == pending


def test_recovery_revalidates_committed_payload_before_consensus(tmp_path: Path) -> None:
    policy, binding, store, _witness, _anchor, supply = _runtime(tmp_path)
    current = _snapshot(policy, binding)
    supply.publish(current, now_epoch=NOW)
    forged = dict(current)
    forged["revoked_key_epochs"] = ["attacker-epoch"]
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "UPDATE snapshots SET payload_json=? WHERE snapshot_id=?",
            (_canonical(forged), current["snapshot_id"]),
        )
    with pytest.raises(ValueError, match="snapshot_invalid"):
        supply.recover(now_epoch=NOW)


@pytest.mark.parametrize("witness_advanced", [False, True])
def test_recovery_cannot_remove_committed_revocation(
    tmp_path: Path, witness_advanced: bool,
) -> None:
    policy, binding, store, witness, anchor, supply = _runtime(tmp_path)
    first = _snapshot(policy, binding, grant_ids=(_digest("grant-a"),))
    supply.publish(first, now_epoch=NOW)
    pending = _snapshot(policy, binding, sequence=2)
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "INSERT INTO snapshots VALUES (?, ?, ?, 'PREPARED')",
            (pending["snapshot_id"], 2, _canonical(pending)),
        )
        connection.execute(
            "UPDATE state SET pending_snapshot_id=? WHERE singleton=1",
            (pending["snapshot_id"],),
        )
    if witness_advanced:
        witness.advance(
            binding.witness_binding_digest(), expected=_high_water(first),
            next_value=_high_water(pending),
        )
    with pytest.raises(ValueError, match="unrevocation"):
        supply.recover(now_epoch=NOW)
    assert store.state().pending == pending


def test_expired_pending_snapshot_never_rolls_forward(tmp_path: Path) -> None:
    policy, binding, store, witness, anchor, supply = _runtime(tmp_path)
    pending = _snapshot(policy, binding, expires_at=NOW + 1)
    store._prepare_under_lock(pending)
    with pytest.raises(ValueError, match="time_invalid"):
        supply.recover(now_epoch=NOW + 2)
    assert witness.load(binding.witness_binding_digest()) is None
    assert store.state().pending == pending


def test_expired_current_can_be_superseded_by_fresh_snapshot(
    tmp_path: Path,
) -> None:
    policy, binding, _store, _witness, _anchor, supply = _runtime(tmp_path)
    first = _snapshot(
        policy, binding, grant_ids=(_digest("grant-a"),), expires_at=NOW + 1,
    )
    supply.publish(first, now_epoch=NOW)
    second = _snapshot(
        policy, binding, sequence=2,
        grant_ids=(_digest("grant-a"), _digest("grant-b")),
    )
    assert supply.publish(second, now_epoch=NOW + 2) == second


@pytest.mark.parametrize("witness_advanced", [False, True])
def test_publish_recovers_expired_pending_before_fresh_successor(
    tmp_path: Path, witness_advanced: bool,
) -> None:
    policy, binding, store, witness, anchor, supply = _runtime(tmp_path)
    pending = _snapshot(
        policy, binding, grant_ids=(_digest("grant-a"),), expires_at=NOW + 1,
    )
    store._prepare_under_lock(pending)
    if witness_advanced:
        witness.advance(
            binding.witness_binding_digest(), expected=None,
            next_value=_high_water(pending),
        )
    successor = _snapshot(
        policy, binding, sequence=2,
        grant_ids=(_digest("grant-a"), _digest("grant-b")),
    )
    assert supply.publish(successor, now_epoch=NOW + 2) == successor
    assert store.state().pending is None


def test_store_metadata_substitution_fails_before_read(tmp_path: Path) -> None:
    policy, binding, store, _witness, _anchor, supply = _runtime(tmp_path)
    supply.publish(_snapshot(policy, binding), now_epoch=NOW)
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE metadata SET store_id='attacker-store'")
    with pytest.raises(ValueError, match="identity_mismatch"):
        store.reader()


def test_orphan_or_deleted_history_fails_graph_validation(tmp_path: Path) -> None:
    policy, binding, store, _witness, _anchor, supply = _runtime(tmp_path)
    first = _snapshot(policy, binding)
    supply.publish(first, now_epoch=NOW)
    orphan = _snapshot(policy, binding, sequence=2)
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "INSERT INTO snapshots VALUES (?, ?, ?, 'COMMITTED')",
            (orphan["snapshot_id"], 2, _canonical(orphan)),
        )
    with pytest.raises(ValueError, match="graph_invalid"):
        store.reader().state()
    with sqlite3.connect(store.path) as connection:
        connection.execute("DELETE FROM snapshots WHERE sequence=2")
        connection.execute("DELETE FROM snapshots WHERE sequence=1")
    with pytest.raises(ValueError, match="snapshot_missing"):
        store.reader().state()


def test_expired_current_snapshot_blocks_oracle(tmp_path: Path) -> None:
    policy, binding, store, witness, anchor, supply = _runtime(tmp_path)
    supply.publish(_snapshot(policy, binding, expires_at=NOW + 1), now_epoch=NOW)
    oracle = _oracle(policy, binding, store, witness, anchor, now=NOW + 2)
    with pytest.raises(ValueError, match="time_invalid"):
        oracle.is_revoked(
            grant_id=_digest("none"), key_epoch="none", at_epoch=NOW + 2
        )


def test_exact_topology_rejects_substituted_witness_path(tmp_path: Path) -> None:
    policy, binding, store, witness, anchor, _supply = _runtime(tmp_path)
    forged = replace(binding, witness_path=str(tmp_path / "other.sqlite3"))
    with pytest.raises(ValueError, match="topology_invalid"):
        UncomposedDurableSignerGrantRevocationAuthoritySupply(
            binding=forged, policy=policy, store=store, witness=witness,
            anchor=anchor,
            principal_key_resolver=_Resolver(), signature_verifier=_Verifier(),
        )


def test_concurrent_publishers_cannot_both_commit(tmp_path: Path) -> None:
    policy, binding, store, _witness, _anchor, supply = _runtime(tmp_path)
    snapshots = (
        _snapshot(policy, binding, grant_ids=(_digest("grant-a"),)),
        _snapshot(policy, binding, grant_ids=(_digest("grant-b"),)),
    )
    results: list[tuple[str, str]] = []

    def publish(snapshot: Mapping[str, Any]) -> None:
        try:
            supply.publish(snapshot, now_epoch=NOW)
            results.append(("ok", str(snapshot["snapshot_id"])))
        except Exception as exc:
            results.append(("error", type(exc).__name__))

    threads = [threading.Thread(target=publish, args=(item,)) for item in snapshots]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(5)
    assert sorted(item[0] for item in results) == ["error", "ok"]
    assert store.state().current["snapshot_id"] in {
        item["snapshot_id"] for item in snapshots
    }


def test_oracle_holds_publication_lock_across_action(tmp_path: Path) -> None:
    policy, binding, store, witness, anchor, supply = _runtime(tmp_path)
    supply.publish(_snapshot(policy, binding), now_epoch=NOW)
    oracle = _oracle(policy, binding, store, witness, anchor)
    action_started, release_action = threading.Event(), threading.Event()

    def action() -> None:
        action_started.set()
        assert release_action.wait(5)

    action_thread = threading.Thread(
        target=lambda: oracle.authorize_use(
            grant_id=_digest("none"), key_epoch="none", at_epoch=NOW,
            action=action,
        )
    )
    action_thread.start()
    assert action_started.wait(5)
    context = multiprocessing.get_context("spawn")
    attempting, publish_done, output = context.Event(), context.Event(), context.Queue()
    publish_process = context.Process(
        target=_publish_in_process,
        args=(
            policy, _snapshot(policy, binding, sequence=2),
            attempting, publish_done, output,
        ),
    )
    publish_process.start()
    assert attempting.wait(5)
    assert publish_done.wait(0.2) is False
    release_action.set()
    action_thread.join(5)
    publish_process.join(10)
    assert publish_process.exitcode == 0
    assert publish_done.is_set()
    assert output.get(timeout=5)[0] == "ok"


def test_reader_and_oracle_expose_no_mutation_surface(tmp_path: Path) -> None:
    policy, binding, store, witness, anchor, supply = _runtime(tmp_path)
    supply.publish(_snapshot(policy, binding), now_epoch=NOW)
    reader = store.reader()
    oracle = _oracle(policy, binding, store, witness, anchor)
    for name in ("prepare", "finalize", "advance", "revoke", "replace_revocations"):
        assert not hasattr(store, name)
        assert not hasattr(reader, name)
        assert not hasattr(oracle, name)


def test_oracle_samples_clock_once_per_validation(tmp_path: Path) -> None:
    policy, binding, store, witness, anchor, supply = _runtime(tmp_path)
    supply.publish(_snapshot(policy, binding), now_epoch=NOW)
    calls: list[int] = []

    def clock() -> int:
        calls.append(NOW)
        return NOW

    oracle = UncomposedDurableSignerGrantRevocationOracle(
        binding=binding, policy=policy, reader=store.reader(),
        witness=witness.reader(), anchor=anchor,
        principal_key_resolver=_Resolver(),
        signature_verifier=_Verifier(), clock=clock,
    )
    assert oracle.is_revoked(
        grant_id=_digest("none"), key_epoch="none", at_epoch=NOW
    ) is False
    assert calls == [NOW]


def test_slice_is_bounded_effect_free_and_not_production_composed() -> None:
    banned_imports = {"subprocess", "socket", "requests", "httpx", "cryptography"}
    for filename in SLICE_MODULES:
        source = (SOURCE_ROOT / filename).read_text(encoding="ascii")
        assert len(source.splitlines()) <= 200
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree) if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            str(node.module or "").split(".")[0]
            for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        )
        assert imports.isdisjoint(banned_imports)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 50
    references = []
    for path in SOURCE_ROOT.glob("*.py"):
        if path.name in SLICE_MODULES:
            continue
        text = path.read_text(encoding="utf-8")
        if any(name.removesuffix(".py") in text for name in UNCOMPOSED_MODULES):
            references.append(path.name)
    assert references == []
    freshness_bypass = [
        path.name for path in SOURCE_ROOT.glob("*.py")
        if "require_freshness=False" in path.read_text(encoding="utf-8")
    ]
    assert freshness_bypass == [
        "reddog_signer_secret_grant_revocation_authority_supply.py"
    ]


def _high_water(snapshot: Mapping[str, Any]):
    from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
        ProposalReplayHighWater,
    )

    return ProposalReplayHighWater(
        sequence=int(snapshot["sequence"]),
        state_revision=str(snapshot["snapshot_id"]).removeprefix("sha256:"),
    )


def _overwrite_high_water(path: Path, binding: str, value: Any) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE high_water SET sequence=?, state_revision=? "
            "WHERE binding_digest=?",
            (value.sequence, value.state_revision, binding),
        )


def _sqlite_high_water(path: Path, binding: str) -> tuple[int, str] | None:
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT sequence, state_revision FROM high_water "
            "WHERE binding_digest=?", (binding,),
        ).fetchone()
    return None if row is None else (int(row[0]), str(row[1]))


def _canonical(value: Mapping[str, Any]) -> str:
    import json

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
