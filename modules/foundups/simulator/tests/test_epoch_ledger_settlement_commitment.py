"""Tests for pre-settlement commitment payloads in epoch ledger."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from modules.foundups.simulator.economics import epoch_ledger as ledger_module
from modules.foundups.simulator.economics.epoch_ledger import EpochLedger


def test_prepare_settlement_commitment_returns_none_when_epoch_missing() -> None:
    ledger = EpochLedger("foundup_x")
    assert ledger.prepare_settlement_commitment(1) is None


def test_prepare_settlement_commitment_contains_expected_fields() -> None:
    ledger = EpochLedger("foundup_001")
    ledger.record_epoch(
        epoch=1,
        total=123.45,
        pool_allocations={"un": 60.0, "dao": 16.0, "du": 4.0, "network": 20.0, "fund": 0.0},
        participant_rewards={"alice": 70.0, "bob": 53.45},
    )

    commitment = ledger.prepare_settlement_commitment(1)
    assert commitment is not None
    assert commitment["status"] == "pre_settlement"
    assert commitment["wsp_78_layer"] == "D_pending"
    assert commitment["requires"] == "external_btc_anchor_connector"
    assert commitment["foundup_id"] == "foundup_001"
    assert commitment["epoch"] == 1
    assert len(commitment["anchor_hex"]) == 40
    assert commitment["participant_count"] == 2
    assert float(commitment["total_distributed"]) == 123.45


def _record(ledger, epoch=1, amount=10, **overrides):
    payload = {"epoch": epoch, "total": amount,
               "pool_allocations": {"un": amount},
               "participant_rewards": {"alice": amount}}
    payload.update(overrides)
    return ledger.record_epoch(**payload)


def _state(ledger):
    return ([(e.epoch_number, e.timestamp, e.entry_hash, e.prev_hash,
              dict(e.pool_allocations), dict(e.participant_rewards)) for e in ledger.entries],
            dict(ledger.merkle_roots),
            {epoch: tuple(tuple(level) for level in tree)
             for epoch, tree in ledger.merkle_trees.items()})


def _expectations(ledger, epoch=1, participant="alice"):
    return {"expected_root": ledger.merkle_roots[epoch],
            "expected_foundup_id": ledger.foundup_id,
            "expected_epoch": epoch, "expected_participant_id": participant}


@pytest.mark.parametrize("count", [1, 2, 3, 5])
def test_proofs_verify_every_actual_reward_including_odd_trees(count):
    ledger = EpochLedger("project_a")
    rewards = {f"person_{i}": i + 1 for i in range(count)}
    _record(ledger, participant_rewards=rewards)
    for participant, amount in rewards.items():
        proof = ledger.get_merkle_proof(1, participant)
        assert proof.amount == amount
        assert proof.verify(**_expectations(ledger, participant=participant))
    assert ledger.get_merkle_proof(1, "absent") is None
    assert ledger.get_merkle_proof(2, "person_0") is None


def test_proof_verification_cannot_pass_without_all_trusted_expectations():
    ledger = EpochLedger("project_a")
    _record(ledger)
    proof = ledger.get_merkle_proof(1, "alice")
    for missing in (None, *_expectations(ledger)):
        expected = _expectations(ledger) if missing else {}
        if missing:
            expected.pop(missing)
        try:
            accepted = proof.verify(**expected)
        except TypeError:
            accepted = False
        assert accepted is False


@pytest.mark.parametrize("change", [
    {"amount": 11}, {"participant_id": "mallory"}, {"epoch_number": 2},
    {"foundup_id": "project_b"}, {"format_version": "unsupported"},
    {"leaf_hash": "0" * 64}, {"merkle_root": "f" * 64},
])
def test_proof_rejects_tampered_claim_metadata(change):
    ledger = EpochLedger("project_a")
    _record(ledger)
    proof = replace(ledger.get_merkle_proof(1, "alice"), **change)
    assert proof.verify(**_expectations(ledger)) is False


@pytest.mark.parametrize("change", [
    {"expected_root": "f" * 64}, {"expected_foundup_id": "project_b"},
    {"expected_epoch": 2}, {"expected_participant_id": "mallory"},
    {"expected_epoch": True}, {"expected_root": None},
])
def test_proof_rejects_wrong_external_checkpoint_or_subject(change):
    ledger = EpochLedger("project_a")
    _record(ledger)
    expected = _expectations(ledger)
    expected.update(change)
    assert ledger.get_merkle_proof(1, "alice").verify(**expected) is False


@pytest.mark.parametrize("path", [
    [("a" * 64, "up")], [("short", "left")], [("G" * 64, "right")],
    [("a" * 64, True)], [("a" * 64,)], ["not-a-pair"], None,
])
def test_proof_rejects_malformed_or_ambiguous_path(path):
    ledger = EpochLedger("project_a")
    _record(ledger, participant_rewards={"alice": 4, "bob": 6})
    proof = replace(ledger.get_merkle_proof(1, "alice"), proof_path=path)
    assert proof.verify(**_expectations(ledger)) is False


def test_roots_bind_foundup_epoch_and_empty_epoch_context():
    first, other = EpochLedger("project_a"), EpochLedger("project_b")
    for ledger in (first, other):
        _record(ledger, epoch=1)
        _record(ledger, epoch=3)
        _record(ledger, epoch=4, amount=0, participant_rewards={})
        _record(ledger, epoch=6, amount=0, participant_rewards={})
    assert first.merkle_roots[1] != other.merkle_roots[1]
    assert first.merkle_roots[1] != first.merkle_roots[3]
    assert first.merkle_roots[4] != other.merkle_roots[4]
    assert first.merkle_roots[4] != first.merkle_roots[6]
    assert first.get_merkle_proof(4, "alice") is None


@pytest.mark.parametrize("field", ["total", "pool", "reward"])
@pytest.mark.parametrize("value", [True, False, -1, -0.5, float("nan"),
                                  float("inf"), float("-inf"), "1", None, [], {}])
def test_record_rejects_invalid_amount_without_state_change(field, value):
    ledger = EpochLedger("project_a")
    _record(ledger)
    before = _state(ledger)
    payload = {"total": 10, "pool_allocations": {"un": 10},
               "participant_rewards": {"alice": 10}}
    if field == "total":
        payload["total"] = value
    else:
        payload["pool_allocations" if field == "pool" else "participant_rewards"] = {"alice": value}
    with pytest.raises(ValueError):
        ledger.record_epoch(epoch=2, **payload)
    assert _state(ledger) == before


@pytest.mark.parametrize("epoch", [True, -1, 1.0, "1", None])
def test_record_rejects_invalid_epoch_without_state_change(epoch):
    ledger = EpochLedger("project_a")
    with pytest.raises(ValueError):
        _record(ledger, epoch=epoch)
    assert _state(ledger) == ([], {}, {})


@pytest.mark.parametrize("field", ["pool_allocations", "participant_rewards"])
@pytest.mark.parametrize("value", [{"": 1}, {1: 1}, {"alice": 1, 2: 2}, [], None])
def test_record_rejects_invalid_mapping_without_partial_append(field, value):
    ledger = EpochLedger("project_a")
    with pytest.raises(ValueError):
        _record(ledger, **{field: value})
    assert _state(ledger) == ([], {}, {})


def test_numeric_equivalence_preserves_huge_integers_and_exact_retry():
    ledger = EpochLedger("project_a")
    huge = 2 ** 100 + 1
    entry = _record(ledger, amount=huge,
                    pool_allocations={"un": 1.0, "fund": -0.0},
                    participant_rewards={"alice": huge, "bob": 0.0})
    replay = _record(ledger, amount=huge,
                     pool_allocations={"fund": 0, "un": 1},
                     participant_rewards={"bob": -0.0, "alice": huge})
    assert replay == entry
    assert len(ledger.entries) == 1
    proof = ledger.get_merkle_proof(1, "alice")
    assert type(proof.amount) is int and proof.amount == huge
    assert proof.verify(**_expectations(ledger))
    with pytest.raises(ValueError):
        _record(ledger, amount=huge + 1,
                pool_allocations={"un": 1, "fund": 0},
                participant_rewards={"alice": huge + 1, "bob": 0})


def test_exact_old_retry_is_stable_and_new_epoch_order_allows_gaps():
    ledger = EpochLedger("project_a")
    original = _record(ledger, epoch=0)
    _record(ledger, epoch=3)
    before = _state(ledger)
    assert _record(ledger, epoch=0, amount=10.0) == original
    assert _state(ledger) == before
    with pytest.raises(ValueError):
        _record(ledger, epoch=2)
    assert _state(ledger) == before
    _record(ledger, epoch=8)
    assert [entry.epoch_number for entry in ledger.entries] == [0, 3, 8]


@pytest.mark.parametrize("change", [
    {"total": 11}, {"pool_allocations": {"un": 11}},
    {"participant_rewards": {"alice": 11}},
])
def test_conflicting_epoch_retry_rejects_without_overwriting_tree(change):
    ledger = EpochLedger("project_a")
    _record(ledger)
    before = _state(ledger)
    with pytest.raises(ValueError):
        _record(ledger, **change)
    assert _state(ledger) == before
    assert ledger.get_merkle_proof(1, "alice").verify(**_expectations(ledger))


def test_input_and_all_exposed_snapshots_cannot_mutate_finalized_state():
    ledger = EpochLedger("project_a")
    pools, rewards = {"un": 10}, {"alice": 10}
    entry = _record(ledger, pool_allocations=pools, participant_rewards=rewards)
    before = _state(ledger)
    pools["un"] = rewards["alice"] = 99
    mutations = [lambda: entry.participant_rewards.__setitem__("alice", 99),
                 lambda: entry.pool_allocations.__setitem__("un", 99),
                 lambda: setattr(entry, "entry_hash", "f" * 64),
                 lambda: ledger.entries.clear(),
                 lambda: ledger.merkle_roots.__setitem__(1, "f" * 64),
                 lambda: ledger.merkle_trees[1][0].__setitem__(0, "f" * 64)]
    for mutate in mutations:
        try:
            mutate()
        except (AttributeError, TypeError, FrozenInstanceError):
            pass
        assert _state(ledger) == before
    exported = entry.to_dict()
    exported["pool_allocations"]["un"] = 77
    assert _state(ledger) == before
    assert ledger.verify_chain()


def test_failed_tree_build_publishes_no_partial_epoch(monkeypatch):
    ledger = EpochLedger("project_a")
    _record(ledger)
    before = _state(ledger)
    original = ledger_module.hashlib.sha256
    calls = 0
    def fail_after_one_hash(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise RuntimeError("injected hash failure")
        return original(*args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(ledger_module, "hashlib", SimpleNamespace(sha256=fail_after_one_hash))
        with pytest.raises(RuntimeError, match="injected hash failure"):
            _record(ledger, epoch=2, participant_rewards={"alice": 4, "bob": 6})
    assert _state(ledger) == before


def test_concurrent_exact_retries_finalize_once():
    ledger = EpochLedger("project_a")
    with ThreadPoolExecutor(max_workers=8) as workers:
        entries = list(workers.map(lambda _: _record(ledger), range(24)))
    assert len(ledger.entries) == 1
    assert all(entry == entries[0] for entry in entries)
    assert ledger.verify_chain()


def test_concurrent_conflicts_publish_only_one_coherent_payload():
    ledger = EpochLedger("project_a")
    def attempt(amount):
        try:
            return _record(ledger, amount=amount)
        except ValueError:
            return None
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(attempt, [10, 20]))
    assert sum(result is not None for result in results) == 1
    assert len(ledger.entries) == 1
    entry = ledger.entries[0]
    assert entry.total_fi_distributed == entry.pool_allocations["un"] == entry.participant_rewards["alice"]
    assert ledger.get_merkle_proof(1, "alice").verify(**_expectations(ledger))


def test_commitment_uses_original_time_and_detached_versioned_payload(monkeypatch):
    calls = 0
    class MovingClock:
        @staticmethod
        def now(tz=None):
            nonlocal calls
            calls += 1
            return datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=calls)
    monkeypatch.setattr(ledger_module, "datetime", MovingClock)
    ledger = EpochLedger("project_a")
    entry = _record(ledger)
    first = ledger.prepare_settlement_commitment(1)
    second = ledger.prepare_settlement_commitment(1)
    assert first == second
    assert first["timestamp"] == entry.timestamp
    assert first["format_version"] == "foundups.epoch.v2"
    assert ledger.get_merkle_proof(1, "alice").format_version == first["format_version"]
    first["merkle_root"] = "f" * 64
    assert ledger.prepare_settlement_commitment(1) == second


@pytest.mark.parametrize("recompute_entry_hash", [False, True], ids=["stale-hash", "recomputed-hash"])
def test_verify_chain_rejects_private_list_index_divergence(recompute_entry_hash):
    """Private corruption must not let the checker certify a different indexed entry."""
    ledger = EpochLedger("project_a")
    original = _record(ledger)
    assert ledger.verify_chain()
    changed = replace(original, total_fi_distributed=999)
    if recompute_entry_hash:
        changed = replace(changed, entry_hash=changed.compute_hash())
    assert (changed.entry_hash == changed.compute_hash()) is recompute_entry_hash
    ledger._entries[0] = changed
    assert ledger._by_epoch[1] is original
    assert original.entry_hash == original.compute_hash()
    assert ledger.verify_chain() is False
