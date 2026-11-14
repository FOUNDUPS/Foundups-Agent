"""Tests for the separate one-time root authority installer."""

from __future__ import annotations

import json
from types import SimpleNamespace

from modules.communication.moltbot_bridge.src import (
    foundup_verified_outcome_root_authority_provision_entrypoint as provision,
)


def _args() -> list[str]:
    return [
        "--repo-root",
        "O:/Foundups-Agent",
        "--owner-authority-config",
        "C:/ProgramData/Foundups/reddog-owner.json",
    ]


def test_provision_entrypoint_initializes_exact_root_state_once(
    monkeypatch,
) -> None:
    state = object()
    snapshot = object()
    calls: list[tuple[object, object]] = []
    monkeypatch.setattr(
        provision,
        "load_root_authority_service_dependencies",
        lambda *_args, **_kwargs: SimpleNamespace(
            state=state, snapshot_supplier=lambda: snapshot
        ),
    )
    monkeypatch.setattr(
        provision,
        "initialize_root_authority_state",
        lambda supplied_state, supplied_snapshot, **_kwargs: calls.append(
            (supplied_state, supplied_snapshot)
        ),
    )
    emitted: list[str] = []

    assert provision.run_entrypoint(_args(), emit=emitted.append) == 0
    assert calls == [(state, snapshot)]
    assert json.loads(emitted[0])["status"] == "ROOT_AUTHORITY_PROVISION_ACCEPT"


def test_provision_entrypoint_rejects_without_leaking_failure(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        provision,
        "load_root_authority_service_dependencies",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("secret-shaped installer detail")
        ),
    )
    emitted: list[str] = []

    assert provision.run_entrypoint(_args(), emit=emitted.append) == 2
    payload = json.loads(emitted[0])
    assert payload["rejection_reasons"] == ["root_authority_provision_rejected"]
    assert "secret-shaped" not in emitted[0]
