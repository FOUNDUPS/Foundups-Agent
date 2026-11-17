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


# A07/B02 frozen process-local replay/atomicity acceptance.
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal
from threading import Barrier, Event
from modules.foundups.simulator.economics import epoch_ledger as lm
from modules.foundups.simulator.economics import pool_distribution as pm
from modules.foundups.simulator.economics.epoch_ledger import EpochLedger
from modules.foundups.simulator.economics.pool_distribution import (
    PoolDistributor, ParticipantType as PT, ActivityLevel as AL, StakerPosition)
from modules.foundups.agent_market.src.fam_daemon import FAMDaemon
from modules.foundups.simulator.config import SimulatorConfig
from modules.foundups.simulator.mesa_model import FoundUpsModel


def _a07_pool(ledger=None):
    pool = PoolDistributor() if ledger is None else PoolDistributor(ledger=ledger)
    p = pool.register_participant("alice", PT.DU, AL.DU,
        staker_position=StakerPosition(original_stake_btc=0.001))
    return pool, p

def _a07_state(pool, ledger=None):
    people = {k: (id(p), int(p.activity_level), p.ups_balance,
        dict(p.foundup_tokens), None if p.staker_position is None else
        (id(p.staker_position), dict(vars(p.staker_position))))
        for k, p in pool.participants.items()}
    evidence = None if ledger is None else (
        [(e.to_dict(), dict(e.participant_rewards)) for e in ledger.entries],
        dict(ledger.merkle_roots), dict(ledger.merkle_trees))
    return deepcopy((pool.accumulated_fund, pool.total_drip_distributed,
                     people, evidence))

def test_a09_bound_ledger_tree_failure_has_no_economic_or_evidence_commit(monkeypatch):
    ledger = EpochLedger("a")
    pool, _ = _a07_pool(ledger)
    before = _a07_state(pool, ledger)
    with monkeypatch.context() as m:
        m.setattr(lm, "_build_tree", lambda *a: (_ for _ in ()).throw(RuntimeError("tree")))
        with pytest.raises(RuntimeError): pool.distribute_epoch(1, 100, "a")
    assert _a07_state(pool, ledger) == before
    result = pool.distribute_epoch(1, 100, "a")
    assert ledger.verify_chain() and len(ledger.entries) == 1
    assert dict(ledger.entries[0].participant_rewards) == result.participant_rewards
    before = _a07_state(pool, ledger)
    pool.distribute_epoch(1, 100.0, "a")
    assert _a07_state(pool, ledger) == before

def test_a10_external_ledger_entry_does_not_prove_pool_credit():
    ledger = EpochLedger("a")
    ledger.record_epoch(1, 100, {"fund": 4}, {"alice": 76.8})
    pool, _ = _a07_pool(ledger)
    before = _a07_state(pool, ledger)
    with pytest.raises(ValueError): pool.distribute_epoch(1, 100, "a")
    assert _a07_state(pool, ledger) == before

def test_a11_bound_context_mismatch_rejects_before_effects():
    ledger = EpochLedger("a")
    pool, _ = _a07_pool(ledger)
    before = _a07_state(pool, ledger)
    with pytest.raises(ValueError): pool.distribute_epoch(1, 100, "b")
    assert _a07_state(pool, ledger) == before

@pytest.mark.parametrize("operation", ["register", "activity"])
def test_a14_owner_api_serializes_against_prepared_ledger_commit(monkeypatch, operation):
    ledger = EpochLedger("a")
    pool, _ = _a07_pool(ledger)
    entered, release, attempted, completed = Event(), Event(), Event(), Event()
    original = lm._build_tree
    def pause(*args):
        entered.set()
        assert release.wait(3)
        return original(*args)
    monkeypatch.setattr(lm, "_build_tree", pause)
    def alter():
        attempted.set()
        if operation == "register": pool.register_participant("new", PT.UN, AL.UN)
        else: pool.update_activity("alice", AL.UN)
        completed.set()
    with ThreadPoolExecutor(2) as executor:
        first = executor.submit(pool.distribute_epoch, 1, 100, "a")
        try:
            assert entered.wait(3)
            change = executor.submit(alter)
            assert attempted.wait(3)
            assert not completed.wait(0.1)
        finally: release.set()
        receipt = first.result(timeout=3)
        change.result(timeout=3)
    assert receipt.participant_rewards["alice"] == pytest.approx(76.8)
    assert "new" not in receipt.participant_rewards and ledger.verify_chain()

@pytest.mark.parametrize("bound", [False, True])
def test_a21_large_integer_request_identity_is_not_rounded(bound):
    ledger = EpochLedger("a") if bound else None
    pool, _ = _a07_pool(ledger)
    total = 2 ** 53
    receipt = pool.distribute_epoch(1, total, "a")
    assert type(receipt.total_rewards) is int and receipt.total_rewards == total
    before = _a07_state(pool, ledger)
    with pytest.raises(ValueError):
        pool.distribute_epoch(1, total + 1, "a")
    assert _a07_state(pool, ledger) == before


# P4 prospective micro-UPS policy acceptance (independently frozen).
import hashlib
import json
import random
from copy import deepcopy
from decimal import localcontext
from fractions import Fraction as F
import pytest
from modules.foundups.simulator.economics import pool_distribution as pm
from modules.foundups.simulator.economics.epoch_ledger import EpochLedger
from modules.foundups.agent_market.src.fam_daemon import FAMDaemon
from modules.foundups.simulator.config import SimulatorConfig
from modules.foundups.simulator.mesa_model import FoundUpsModel

AP_MAX = 2**63 - 1

def _ap_full():
    return [(f'p{pt}{al}', pt, al) for pt in range(3) for al in range(3)]


def _ap_pool(rows, ledger=None):
    pool = pm.PoolDistributor(ledger=ledger)
    for pid, pt, al in rows:
        pool.register_participant(pid, pm.ParticipantType(pt), pm.ActivityLevel(al))
    return pool


def _ap_expected(rows, amount):
    pools, tiers = (F(3, 5), F(4, 25), F(1, 25)), (F(1, 25), F(4, 25), F(4, 5))
    rewards = []
    for pid, pt, al in rows:
        stake = sum((amount * pools[k] * tiers[al] /
                     sum(other >= k and level == al for _, other, level in rows)
                     for k in range(pt + 1)), F(0))
        network = amount * F(4, 25) * tiers[al] / sum(level == al for _, _, level in rows)
        rewards.append((pid, int(stake) + int(network)))
    fund = amount // 25
    return tuple(sorted(rewards)), fund, amount - fund - sum(n for _, n in rewards)


def _ap_snapshot(pool):
    cache = [(epoch, value[0], value[1], vars(value[2]) | {
        'participant_rewards': dict(value[2].participant_rewards)})
        for epoch, value in pool._epochs.items()]
    funding = pool._funding
    source = None if funding is None else (funding._source.pavs_treasury_balance,
                                           dict(funding._settlements), funding._liabilities)
    return _a07_state(pool, pool._ledger), deepcopy(cache), deepcopy(source)


@pytest.mark.parametrize('text,expected', [('0', 0), ('0.0', 0), ('0.000000', 0),
    ('1', 1000000), ('1.0', 1000000), ('1.000000', 1000000), ('0.1', 100000),
    ('0.000001', 1), ('1.234567', 1234567), ('9223372036854.775807', AP_MAX)])
def test_ap_decimal_ingress_is_exact_and_context_independent(text, expected):
    with localcontext() as context:
        context.prec = 3
        before = context.copy()
        actual = pm.parse_ups_atoms(text)
        assert type(actual) is int and actual == expected
        assert context.prec == before.prec and context.flags == before.flags


@pytest.mark.parametrize('text', ['', '00', '01', '.1', '1.', '+1', '-0', ' 1',
    '1 ', '1\n', '1e0', 'NaN', 'Infinity', '1.0000000', '0.0000001', '１', '١',
    '9223372036854.775808', '9999999999999.999999', '10000000000000', pytest.param('1' * 100000, id='overlong_decimal')])
def test_ap_decimal_ingress_refuses_without_rounding(text):
    with pytest.raises(ValueError):
        pm.parse_ups_atoms(text)


@pytest.mark.parametrize('target', ['parser', 'amount', 'epoch', 'context', 'classification'])
def test_ap_nonbuiltin_admission_invokes_no_conversion_or_metaclass_hooks(target):
    calls = []
    class Meta(type):
        def __eq__(cls, other):
            calls.append('type_eq')
            raise AssertionError('type hook')
    class Hook(metaclass=Meta):
        def __int__(self):
            calls.append('int')
            raise AssertionError('conversion hook')
    pool = _ap_pool([('alice', 0, 0)])
    bad = Hook()
    if target == 'classification':
        pool.participants['alice'].participant_type = bad
    with pytest.raises(ValueError):
        if target == 'parser':
            pm.parse_ups_atoms(bad)
        else:
            pool.plan_atom_epoch(bad if target == 'epoch' else 1,
                bad if target == 'amount' else 100, foundup_id=bad if target == 'context' else 'a')
    assert calls == [] and pool.participants['alice'].ups_balance == 0
    assert not pool._epochs and pool.accumulated_fund == pool.total_drip_distributed == 0


@pytest.mark.parametrize('target,value', [('amount', True), ('amount', 1.0),
    ('amount', -1), ('amount', AP_MAX + 1), ('epoch', False), ('epoch', 0.0),
    ('epoch', -1), ('epoch', AP_MAX + 1), ('parser', 1), ('parser', b'1')])
def test_ap_scalar_types_and_bounds_reject(target, value):
    pool = _ap_pool([('alice', 0, 0)])
    before = _ap_snapshot(pool)
    with pytest.raises(ValueError):
        if target == 'parser':
            pm.parse_ups_atoms(value)
        else:
            pool.plan_atom_epoch(value if target == 'epoch' else 1,
                value if target == 'amount' else 1, foundup_id='a')
    assert _ap_snapshot(pool) == before


@pytest.mark.parametrize('rows,amount,expected', [(_ap_full, 100000,
    ((1013, 4053, 20266, 1333, 5333, 26666, 1493, 5973, 29866), 4000, 4)),
    (_ap_full, 300000, None), (_ap_full, 1, None), (_ap_full, 0, None),
    (_ap_full, AP_MAX, None), (None, 25, ((), 1, 24)), (None, 0, ((), 0, 0))])
def test_ap_full_cohort_and_empty_goldens(rows, amount, expected):
    roster = [] if rows is None else rows()
    pool = _ap_pool(roster)
    before = _ap_snapshot(pool)
    plan = pool.plan_atom_epoch(AP_MAX, amount, foundup_id='a')
    assert type(plan) is pm.UPSAtomPlan
    assert (plan.participant_rewards_atoms, plan.fund_atoms, plan.source_retained_atoms) == _ap_expected(roster, amount)
    if expected is not None:
        assert (tuple(n for _, n in plan.participant_rewards_atoms), plan.fund_atoms,
                plan.source_retained_atoms) == expected
    assert plan.epoch == AP_MAX and plan.total_reward_atoms == amount and plan.foundup_id == 'a'
    assert _ap_snapshot(pool) == before


@pytest.mark.parametrize('pt,al,amount,reward,retained', [(2, 2, 7, 4, 3), (0, 2, 13, 7, 6)])
def test_ap_stake_sum_final_floor_and_separate_network_lane(pt, al, amount, reward, retained):
    plan = _ap_pool([('alice', pt, al)]).plan_atom_epoch(0, amount, foundup_id='a')
    assert plan.participant_rewards_atoms == (('alice', reward),)
    assert (plan.fund_atoms, plan.source_retained_atoms) == (0, retained)


@pytest.mark.parametrize('seed', [11, 29, 710007])
def test_ap_seeded_rosters_conserve_and_match_independent_rational_oracle(seed):
    rng = random.Random(seed)
    for _ in range(24):
        rows = [(f'p{i}', rng.randrange(3), rng.randrange(3)) for i in range(rng.randrange(25))]
        amount = rng.choice([0, 1, 7, 13, 100000, AP_MAX, rng.randrange(AP_MAX)])
        pool = _ap_pool(rows)
        before = _ap_snapshot(pool)
        plan = pool.plan_atom_epoch(1, amount, foundup_id='a')
        assert (plan.participant_rewards_atoms, plan.fund_atoms, plan.source_retained_atoms) == _ap_expected(rows, amount)
        assert all(type(n) is int and n >= 0 for _, n in plan.participant_rewards_atoms)
        assert sum(n for _, n in plan.participant_rewards_atoms) + plan.fund_atoms + plan.source_retained_atoms == amount
        assert pool.plan_atom_epoch(1, amount, foundup_id='a').to_dict() == plan.to_dict()
        assert _ap_snapshot(pool) == before


def test_ap_wire_identity_is_separate_immutable_detached_and_canonical():
    plan = _ap_pool([('z', 2, 2), ('alice', 0, 1)]).plan_atom_epoch(AP_MAX, AP_MAX, foundup_id='a')
    wire = plan.to_dict()
    assert set(wire) == {'format_version', 'asset', 'decimals', 'unit_policy', 'epoch', 'foundup_id',
        'total_reward_atoms', 'participant_rewards_atoms', 'fund_atoms', 'source_retained_atoms', 'roster', 'identity_sha256'}
    assert (wire['format_version'], wire['asset'], wire['decimals'], wire['unit_policy']) == ('foundups.ups-atom-plan.v1', 'UPS', 6, 'ups_micro_v1')
    assert wire['epoch'] == wire['total_reward_atoms'] == str(AP_MAX)
    assert wire['participant_rewards_atoms'] == [[pid, str(n)] for pid, n in plan.participant_rewards_atoms]
    assert wire['fund_atoms'] == str(plan.fund_atoms) and wire['source_retained_atoms'] == str(plan.source_retained_atoms)
    assert plan.roster == (('alice', 0, 1), ('z', 2, 2)) and wire['roster'] == [list(row) for row in plan.roster]
    identity = wire.pop('identity_sha256')
    assert identity == plan.identity_sha256 == hashlib.sha256(json.dumps(wire, sort_keys=True,
        separators=(',', ':'), ensure_ascii=True).encode('ascii')).hexdigest()
    wire['roster'][0][0] = 'changed'
    assert plan.to_dict()['roster'][0][0] == 'alice'
    with pytest.raises((AttributeError, TypeError)):
        plan.fund_atoms = 7
    assert all(type(n) is int for n in (plan.epoch, plan.total_reward_atoms, plan.fund_atoms, plan.source_retained_atoms))
    assert type(plan.roster) is type(plan.participant_rewards_atoms) is tuple
    assert all(type(row) is tuple for row in plan.roster + plan.participant_rewards_atoms)


def test_ap_sorting_and_zero_roster_context_identity_are_deterministic():
    rows = [('z', 2, 1), ('a', 0, 2), ('m', 1, 0)]
    a = _ap_pool(rows).plan_atom_epoch(1, 100000, foundup_id='a')
    b = _ap_pool(list(reversed(rows))).plan_atom_epoch(1, 100000, foundup_id='a')
    assert a.to_dict() == b.to_dict()
    pool = _ap_pool(rows)
    zero = pool.plan_atom_epoch(1, 0, foundup_id='a')
    pool.register_participant('new', pm.ParticipantType.UN, pm.ActivityLevel.UN)
    assert zero.identity_sha256 != pool.plan_atom_epoch(1, 0, foundup_id='a').identity_sha256
    assert zero.identity_sha256 != pool.plan_atom_epoch(2, 0, foundup_id='a').identity_sha256
    assert zero.identity_sha256 != pool.plan_atom_epoch(1, 0, foundup_id='b').identity_sha256


@pytest.mark.parametrize('bad_id', ['', '_a', 'a/b', 'a b', 'a\n', 'é', 'a' * 129])
def test_ap_context_identifier_grammar_and_bound_ledger_match(bad_id):
    pool = _ap_pool([('alice', 0, 0)], EpochLedger('a'))
    pool.distribute_epoch(1, 100, 'a')
    before = _ap_snapshot(pool)
    with pytest.raises(ValueError):
        pool.plan_atom_epoch(1, 1, foundup_id=bad_id)
    with pytest.raises(ValueError):
        pool.plan_atom_epoch(1, 1, foundup_id='b')
    pool.plan_atom_epoch(2, 0, foundup_id='a')
    assert _ap_snapshot(pool) == before


@pytest.mark.parametrize('kind', ['dict_subclass', 'participant_subclass', 'mismatched_id',
    'bad_id', 'bad_type', 'bad_activity', 'opaque', 'staker_zero', 'staker_native'])
def test_ap_roster_refusal_is_exact_and_has_no_effect(kind):
    pool = _ap_pool([('alice', 0, 0)])
    person = pool.participants['alice']
    if kind == 'dict_subclass':
        pool.participants = type('Mapping', (dict,), {'__len__': lambda s: (_ for _ in ()).throw(AssertionError())})(pool.participants)
    elif kind == 'participant_subclass':
        pool.participants['alice'] = type('Person', (pm.Participant,), {})('alice', pm.ParticipantType.UN, pm.ActivityLevel.UN)
    elif kind == 'mismatched_id':
        person.participant_id = 'other'
    elif kind == 'bad_id':
        person.participant_id = 'bad/id'
    elif kind == 'bad_type':
        person.participant_type = 0
    elif kind == 'bad_activity':
        person.activity_level = False
    elif kind == 'opaque':
        pool.participants['alice'] = object()
    else:
        person.staker_position = 0 if kind == 'staker_zero' else pm.StakerPosition()
    roster = pool.participants
    with pytest.raises(ValueError):
        pool.plan_atom_epoch(1, 100, foundup_id='a')
    assert pool.participants is roster and person.ups_balance == 0
    assert not pool._epochs and pool.accumulated_fund == pool.total_drip_distributed == 0


@pytest.mark.parametrize('size', [10000, 10001])
def test_ap_roster_work_bound(size):
    pool = pm.PoolDistributor()
    pool.participants = {f'p{i}': pm.Participant(f'p{i}', pm.ParticipantType.UN, pm.ActivityLevel.UN) for i in range(size)}
    if size == 10001:
        with pytest.raises(ValueError):
            pool.plan_atom_epoch(1, 1, foundup_id='a')
    else:
        assert len(pool.plan_atom_epoch(1, 1, foundup_id='a').roster) == size


def test_ap_fixed_policy_ignores_native_callbacks_constants_and_book_values(monkeypatch):
    pool = _ap_pool([('alice', 2, 2)])
    bad = object()
    pool.participants['alice'].ups_balance = bad
    for name in ['POOL_PERCENTAGES', 'ACTIVITY_SHARES', 'POOL_ACCESS']:
        monkeypatch.setattr(pm, name, bad)
    monkeypatch.setattr(pm.Participant, 'get_accessible_pools', lambda self: (_ for _ in ()).throw(AssertionError()))
    assert pool.plan_atom_epoch(1, 7, foundup_id='a').participant_rewards_atoms == (('alice', 4),)
    assert pool.participants['alice'].ups_balance is bad and not pool._epochs


def test_ap_real_funded_owner_preview_does_not_admit_or_debit_source(tmp_path):
    daemon = FAMDaemon(data_dir=tmp_path / 'fam', auto_start=False)
    model = FoundUpsModel(config=SimulatorConfig(num_founder_agents=0, num_user_agents=0,
        use_ai=False, layer_d_anchor_enabled=False, epoch_funding_mode='sim_native_epoch_transfer_v1'), fam_daemon=daemon)
    model._demurrage.update_pavs_treasury_balance(0)  # Explicit synthetic test opening.
    pool = model.pool_distributor
    pool.register_participant('alice', pm.ParticipantType.UN, pm.ActivityLevel.UN)
    before = _ap_snapshot(pool)
    plan = pool.plan_atom_epoch(1, 100000, foundup_id=pool._ledger.foundup_id)
    assert sum(n for _, n in plan.participant_rewards_atoms) + plan.fund_atoms > 0
    assert model._demurrage.pavs_treasury_balance == 0 and _ap_snapshot(pool) == before
