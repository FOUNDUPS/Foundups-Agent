"""Focused key-epoch use tests for the durable revocation authority."""

from __future__ import annotations

import multiprocessing
import threading
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
