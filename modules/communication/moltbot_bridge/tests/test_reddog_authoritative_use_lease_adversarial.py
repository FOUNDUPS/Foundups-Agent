"""Replay, signer-substitution, expiry, and capability attacks."""

from __future__ import annotations

import copy
import json
import pickle
from dataclasses import replace
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src import reddog_authoritative_use_lease as lease_module
from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease import AuthoritativeUseLease
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import encode_ed25519_public_key
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    Ed25519SignerBackend,
    bind_exact_signing_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_mutual_peer_handshake import SignerPeerProfileBinding
from modules.communication.moltbot_bridge.tests.test_reddog_external_signer_authoritative_use_lease import (
    NOW,
    _AuditMac,
    _authority,
    _backend,
    _binding,
    _consume_lease,
    _current_generation,
    _is_lease,
    _lease,
    _payload,
    _peer,
    _request,
    _store,
)


def test_signed_response_replay_is_rejected_durably(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lease_module.time, "time", lambda: NOW)
    store = _store(tmp_path)
    request = _request(store)
    response = _backend(request, exact=True).sign(request, _peer())
    values = {
        "request": request,
        "response": response,
        "current_generation_authority": _authority(tmp_path, monkeypatch),
        "replay_store": store,
        "now_epoch": NOW,
    }
    assert lease_module._rehydrate_external_authoritative_use_lease(**values)
    assert lease_module._rehydrate_external_authoritative_use_lease(**values) is None


def test_signed_response_cannot_cross_durable_replay_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lease_module.time, "time", lambda: NOW)
    first = _store(tmp_path / "first")
    second = _store(tmp_path / "second")
    request = _request(first)
    response = _backend(request, exact=True).sign(request, _peer())
    authority = _authority(tmp_path, monkeypatch)
    accepted = lease_module._rehydrate_external_authoritative_use_lease(
        request=request,
        response=response,
        current_generation_authority=authority,
        replay_store=first,
        now_epoch=NOW,
    )
    rejected = lease_module._rehydrate_external_authoritative_use_lease(
        request=request,
        response=response,
        current_generation_authority=authority,
        replay_store=second,
        now_epoch=NOW,
    )
    assert _is_lease(accepted)
    assert rejected is None


def test_unrelated_local_signer_cannot_mint_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lease_module.time, "time", lambda: NOW)
    store = _store(tmp_path)
    attacker_private = Ed25519PrivateKey.generate()
    attacker_public = encode_ed25519_public_key(
        attacker_private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )
    request = _request(store, signer_public_key=attacker_public)
    attacker = Ed25519SignerBackend(
        private_key=attacker_private,
        public_key=attacker_public,
        key_epoch="epoch-1",
        audit_mac_builder=_AuditMac(),
        proposal_clock=lambda: NOW,
        signer_peer_instance_binding=replace(
            _binding(),
            signer_profiles=(
                SignerPeerProfileBinding("reddog-work-authority", attacker_public, "epoch-1"),
            ),
        ),
    )
    response = bind_exact_signing_request(attacker, request).sign(request, _peer())
    assert response.accepted
    assert lease_module._rehydrate_external_authoritative_use_lease(
        request=request,
        response=response,
        current_generation_authority=_authority(tmp_path, monkeypatch),
        replay_store=store,
        now_epoch=NOW,
    ) is None


def test_lease_cannot_outlive_current_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lease_module.time, "time", lambda: NOW)
    store = _store(tmp_path)
    request = _request(store, expires_at=NOW + 20)
    response = _backend(request, exact=True).sign(request, _peer())
    binding = replace(_current_generation(), selection_expires_at=NOW + 10)
    assert lease_module._rehydrate_external_authoritative_use_lease(
        request=request,
        response=response,
        current_generation_authority=_authority(tmp_path, monkeypatch, binding),
        replay_store=store,
        now_epoch=NOW,
    ) is None


def test_expired_lease_rejects_without_consuming(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, lease = _lease(tmp_path, monkeypatch)
    monkeypatch.setattr(lease_module.time, "time", lambda: NOW + 20)
    assert not _is_lease(lease)
    assert not _consume_lease(lease)


def test_expired_lease_does_not_revive_after_clock_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, lease = _lease(tmp_path, monkeypatch)
    monkeypatch.setattr(lease_module.time, "time", lambda: NOW + 20)
    assert not _is_lease(lease)
    monkeypatch.setattr(lease_module.time, "time", lambda: NOW)
    assert not _is_lease(lease)
    assert not _consume_lease(lease)


def test_capability_has_no_public_mint_or_fabrication_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert "rehydrate_external_authoritative_use_lease" not in lease_module.__all__
    with pytest.raises(TypeError):
        AuthoritativeUseLease()
    fabricated = object.__new__(AuthoritativeUseLease)
    assert not _is_lease(fabricated)
    _, _, lease = _lease(tmp_path, monkeypatch)
    assert lease is not None
    with pytest.raises(TypeError):
        copy.copy(lease)
    with pytest.raises(TypeError):
        copy.deepcopy(lease)
    with pytest.raises(TypeError):
        pickle.dumps(lease)


def test_contract_has_no_execution_or_secret_surface() -> None:
    root = Path(__file__).parents[1]
    paths = (
        root / "src" / "reddog_authoritative_use_lease.py",
        root / "src" / "reddog_authoritative_use_lease_contract.py",
        root / "src" / "reddog_external_signer_authoritative_use_lease.py",
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    for forbidden in (
        "subprocess",
        "os.system",
        "shell=True",
        "private_key",
        "HoloIndex.reindex",
        "commit_all",
        "gh pr",
    ):
        assert forbidden not in combined
    assert json.dumps(_payload(), sort_keys=True, ensure_ascii=True).isascii()
