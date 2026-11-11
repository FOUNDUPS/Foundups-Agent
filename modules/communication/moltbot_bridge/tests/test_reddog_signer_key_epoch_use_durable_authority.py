"""Focused key-epoch use tests for the durable revocation authority."""

from __future__ import annotations

import multiprocessing
import os
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.tests.test_reddog_signer_secret_grant_revocation_durable_authority import (
    NOW,
    _oracle,
    _publish_in_process,
    _runtime,
    _snapshot,
)


def test_key_epoch_check_does_not_use_grant_id_semantics(tmp_path: Path) -> None:
    policy, binding, store, witness, anchor, supply = _runtime(tmp_path)
    supply.publish(
        _snapshot(policy, binding, key_epochs=("grant-authority-epoch-7",)),
        now_epoch=NOW,
    )
    oracle = _oracle(policy, binding, store, witness, anchor)
    assert oracle.is_key_epoch_revoked(
        key_epoch="grant-authority-epoch-7", at_epoch=NOW
    ) is True
    assert oracle.is_key_epoch_revoked(
        key_epoch="current-epoch", at_epoch=NOW
    ) is False


def test_key_epoch_use_rejects_revoked_or_expired_epoch(tmp_path: Path) -> None:
    policy, binding, store, witness, anchor, supply = _runtime(tmp_path)
    supply.publish(_snapshot(policy, binding), now_epoch=NOW)
    oracle = _oracle(policy, binding, store, witness, anchor)
    assert oracle.authorize_key_epoch_use(
        key_epoch="grant-authority-epoch-7",
        at_epoch=NOW,
        expires_at=NOW + 1,
        action=lambda: "used",
    ) == "used"
    supply.publish(
        _snapshot(
            policy, binding, sequence=2,
            key_epochs=("grant-authority-epoch-7",),
        ),
        now_epoch=NOW,
    )
    with pytest.raises(RuntimeError, match="key_epoch_use_rejected"):
        oracle.authorize_key_epoch_use(
            key_epoch="grant-authority-epoch-7",
            at_epoch=NOW,
            expires_at=NOW + 1,
            action=lambda: "must-not-run",
        )
    with pytest.raises(RuntimeError, match="key_epoch_use_rejected"):
        oracle.authorize_key_epoch_use(
            key_epoch="grant-authority-epoch-7",
            at_epoch=NOW,
            expires_at=NOW,
            action=lambda: "must-not-run",
        )


def test_key_epoch_use_holds_publication_lock_across_action(
    tmp_path: Path,
) -> None:
    policy, binding, store, witness, anchor, supply = _runtime(tmp_path)
    supply.publish(_snapshot(policy, binding), now_epoch=NOW)
    oracle = _oracle(policy, binding, store, witness, anchor)
    action_started, release_action = threading.Event(), threading.Event()

    def action() -> None:
        action_started.set()
        assert release_action.wait(5)

    action_thread = threading.Thread(
        target=lambda: oracle.authorize_key_epoch_use(
            key_epoch="none", at_epoch=NOW, expires_at=NOW + 100,
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


@pytest.fixture
def current_use(tmp_path):
    policy, binding, store, witness, anchor, supply = _runtime(tmp_path)
    supply.publish(_snapshot(policy, binding), now_epoch=NOW)
    oracle = _oracle(policy, binding, store, witness, anchor)
    clock = [NOW]
    oracle.clock = lambda: clock[0]
    return oracle, clock, policy, binding, supply


@pytest.mark.skipif(os.name != "posix", reason="Real flock contention requires POSIX")
@pytest.mark.parametrize("current_time", [True, False])
def test_epoch_rollover_while_waiting_for_actual_operation_lock(current_use, monkeypatch, current_time):
    oracle, clock, *_ = current_use
    original_lock = oracle._lock
    waiting, done = threading.Event(), threading.Event()
    sampled, effects, results = [], [], []

    @contextmanager
    def observed_lock():
        waiting.set()
        with original_lock():
            yield

    def sample():
        sampled.append(clock[0])
        return clock[0]

    def worker():
        try:
            kwargs = dict(key_epoch="live", expires_at=NOW + 10, action=lambda: effects.append("effect"))
            if current_time:
                oracle.authorize_current_key_epoch_use(**kwargs)
            else:
                oracle.authorize_key_epoch_use(at_epoch=NOW, **kwargs)
            results.append("accepted")
        except Exception as exc:
            results.append(exc)
        finally:
            done.set()

    monkeypatch.setattr(oracle, "_lock", observed_lock)
    oracle.clock = sample
    thread = threading.Thread(target=worker, daemon=True)
    with original_lock():
        thread.start()
        assert waiting.wait(5)
        assert not done.wait(.05)
        assert sampled == []
        clock[0] = NOW + 1
    thread.join(5)
    assert not thread.is_alive()
    if current_time:
        assert results == ["accepted"] and effects == ["effect"]
        assert sampled == [NOW + 1] * 4
    else:
        assert len(results) == 1 and isinstance(results[0], ValueError)
        assert str(results[0]) == "durable_revocation_oracle_clock_invalid"
        assert effects == []


@pytest.mark.parametrize("invalid", [True, None, "epoch", 1.0, float("nan"), float("inf")])
def test_current_epoch_invalid_clock_never_runs_action(current_use, invalid):
    oracle, clock, *_ = current_use
    clock[0] = invalid
    with pytest.raises(ValueError, match="durable_revocation_oracle_clock_invalid"):
        oracle.authorize_current_key_epoch_use(key_epoch="live", expires_at=NOW + 10,
            action=lambda: pytest.fail("invalid clock must not authorize"))


def test_current_epoch_clock_failure_never_runs_action(current_use):
    oracle, *_ = current_use
    def broken():
        raise OSError("synthetic clock failure")
    oracle.clock = broken
    with pytest.raises(ValueError, match="durable_revocation_oracle_clock_invalid"):
        oracle.authorize_current_key_epoch_use(key_epoch="live", expires_at=NOW + 10,
            action=lambda: pytest.fail("failed clock must not authorize"))


@pytest.mark.parametrize("expires", [NOW - 1, NOW, True, float("nan"), float("inf")])
def test_current_epoch_expiry_rejects_before_action(current_use, expires):
    oracle, *_ = current_use
    with pytest.raises(RuntimeError, match="key_epoch_use_rejected"):
        oracle.authorize_current_key_epoch_use(key_epoch="live", expires_at=expires,
            action=lambda: pytest.fail("expired or invalid window must not authorize"))


def test_current_epoch_revocation_rejects_before_action(current_use):
    oracle, _, policy, binding, supply = current_use
    supply.publish(_snapshot(policy, binding, sequence=2, key_epochs=("revoked",)), now_epoch=NOW)
    with pytest.raises(RuntimeError, match="key_epoch_use_rejected"):
        oracle.authorize_current_key_epoch_use(key_epoch="revoked", expires_at=NOW + 10,
            action=lambda: pytest.fail("revoked epoch must not authorize"))


@pytest.mark.parametrize("after", [NOW - 1, NOW + 10, True, float("nan")])
def test_current_epoch_rechecks_clock_after_action(current_use, after):
    oracle, clock, *_ = current_use
    effects = []
    def action():
        effects.append("effect")
        clock[0] = after
        return "must-not-return"
    with pytest.raises((RuntimeError, ValueError)):
        oracle.authorize_current_key_epoch_use(key_epoch="live", expires_at=NOW + 10, action=action)
    assert effects == ["effect"]


def test_current_epoch_rechecks_revocation_after_action(current_use, monkeypatch):
    oracle, *_ = current_use
    original = oracle._current
    effects = []
    def changed_snapshot(now):
        snapshot = dict(original(now))
        if effects:
            snapshot["revoked_key_epochs"] = ["live"]
        return snapshot
    monkeypatch.setattr(oracle, "_current", changed_snapshot)
    with pytest.raises(RuntimeError, match="key_epoch_use_rejected"):
        oracle.authorize_current_key_epoch_use(key_epoch="live", expires_at=NOW + 10,
            action=lambda: effects.append("effect") or "must-not-return")
    assert effects == ["effect"]


def test_explicit_stale_epoch_still_rejects_before_action(current_use):
    oracle, clock, *_ = current_use
    clock[0] = NOW + 1
    with pytest.raises(ValueError, match="durable_revocation_oracle_clock_invalid"):
        oracle.authorize_key_epoch_use(key_epoch="live", at_epoch=NOW, expires_at=NOW + 10,
            action=lambda: pytest.fail("explicit stale epoch must still reject"))


@pytest.mark.parametrize("read_number", [1, 2])
@pytest.mark.parametrize("changed_epoch", [NOW - 1, NOW + 10, True, float("nan")])
def test_current_epoch_rechecks_after_slow_anchor_load(current_use, monkeypatch, read_number, changed_epoch):
    oracle, clock, *_ = current_use
    original_load = oracle.anchor.load
    reads, effects = [], []
    def delayed_load():
        value = original_load()
        reads.append("read")
        if len(reads) == read_number:
            clock[0] = changed_epoch
        return value
    monkeypatch.setattr(type(oracle.anchor), "load", lambda self: delayed_load())
    with pytest.raises((RuntimeError, ValueError)):
        oracle.authorize_current_key_epoch_use(
            key_epoch="live", expires_at=NOW + 10,
            action=lambda: effects.append("effect") or "must-not-return",
        )
    assert effects == ([] if read_number == 1 else ["effect"])


@pytest.mark.parametrize("read_number", [1, 2])
def test_snapshot_expiry_during_anchor_load_withholds_action_or_result(current_use, monkeypatch, read_number):
    oracle, clock, policy, binding, supply = current_use
    supply.publish(_snapshot(policy, binding, sequence=2, expires_at=NOW + 1), now_epoch=NOW)
    original_load = oracle.anchor.load
    reads, effects = [], []
    def delayed_load():
        value = original_load()
        reads.append("read")
        if len(reads) == read_number:
            clock[0] = NOW + 1
        return value
    monkeypatch.setattr(type(oracle.anchor), "load", lambda self: delayed_load())
    with pytest.raises(RuntimeError, match="key_epoch_use_rejected"):
        oracle.authorize_current_key_epoch_use(
            key_epoch="live", expires_at=NOW + 10,
            action=lambda: effects.append("effect") or "must-not-return",
        )
    assert effects == ([] if read_number == 1 else ["effect"])


@pytest.mark.parametrize("current_time", [True, False])
def test_live_rollover_during_anchor_load_remains_authorized(current_use, monkeypatch, current_time):
    oracle, clock, *_ = current_use
    original_load = oracle.anchor.load
    effects = []
    def delayed_load():
        value = original_load()
        clock[0] += 1
        return value
    monkeypatch.setattr(type(oracle.anchor), "load", lambda self: delayed_load())
    kwargs = dict(key_epoch="live", expires_at=NOW + 10, action=lambda: effects.append(clock[0]) or "accepted")
    if current_time:
        result = oracle.authorize_current_key_epoch_use(**kwargs)
    else:
        result = oracle.authorize_key_epoch_use(at_epoch=NOW, **kwargs)
    assert result == "accepted" and effects == [NOW + 1]


def test_observed_post_action_rollback_cannot_recover_during_next_read(current_use, monkeypatch):
    oracle, clock, *_ = current_use
    original = oracle._current
    reads, effects = [], []
    def recovering_read(now):
        reads.append(now)
        value = original(now)
        clock[0] = NOW
        return value
    def action():
        effects.append("effect")
        clock[0] = NOW - 1
        return "must-not-return"
    monkeypatch.setattr(oracle, "_current", recovering_read)
    with pytest.raises(RuntimeError, match="key_epoch_use_rejected"):
        oracle.authorize_current_key_epoch_use(key_epoch="live", expires_at=NOW + 10, action=action)
    assert effects == ["effect"] and reads == [NOW]
