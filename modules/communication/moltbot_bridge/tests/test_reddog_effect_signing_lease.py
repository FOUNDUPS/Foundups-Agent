"""Connected lease issuance with real signatures and synthetic owner/custody seams."""

from contextlib import contextmanager
from dataclasses import replace
import json

from .reddog_effect_signing_test_support import setup, reset_owner_reads
from .test_reddog_effect_signing_grant import provider_route, fixtures
from . import test_reddog_external_signer_authoritative_use_lease as existing
from .reddog_elevated_consensus_e2e_support import _target_client
from modules.communication.moltbot_bridge.src import reddog_external_signer_authoritative_use_lease as issuer_module
from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease import (
    consume_authoritative_use_lease, is_authoritative_use_lease,
)


def current_authority(monkeypatch, root, payload):
    kind = issuer_module.SignerCurrentGenerationRuntimeAuthority
    initial = existing._current_generation()
    binding = replace(initial, **{k: payload[k] for k in initial.__dataclass_fields__ if k in payload},
                      selection_expires_at=1100)
    @contextmanager
    def lease(self, **kwargs):
        assert kwargs["now_epoch"] == 1000
        assert kwargs["signer_profile_id"] == payload["signer_profile_id"]
        yield binding
    monkeypatch.setattr(kind, "lease", lease)
    return kind(root, root)


def test_effect_proof_reaches_verified_one_use_lease(monkeypatch, tmp_path):
    monkeypatch.setitem(fixtures._store.__globals__, "NOW", 1000)
    store = fixtures._store(tmp_path / "store")
    target_key = fixtures.Ed25519PrivateKey.generate()
    overrides = dict(existing._replay_binding(store), signer_public_key=fixtures._public(target_key),
                     socket_path_digest=existing.digest_text(existing._binding().socket_path))
    state = setup(monkeypatch, tmp_path / "approval", target_overrides=overrides)
    provider, _ = provider_route(monkeypatch, tmp_path / "grant", state, store=store)
    payload = json.loads(state.kw["target"].signing_input.split(".", 2)[2])
    monkeypatch.setitem(_target_client.__globals__, "NOW", 1000)
    signer = _target_client(tmp_path, store, state.grant_binding, target_key, synthetic_owner_unit=True)
    unit = next(cell.cell_contents for cell in signer.connector.__closure__
                if hasattr(cell.cell_contents, "backend_factory"))
    peer = existing._binding()
    peer = replace(peer, **{k: payload[k] for k in peer.__dataclass_fields__ if k in payload},
        signer_profiles=(replace(peer.signer_profiles[0],
        signer_public_key=state.kw["target"].signer_public_key),))
    unit.backend_factory.backend = replace(unit.backend_factory.backend, signer_peer_instance_binding=peer)
    monkeypatch.setattr(issuer_module.time, "time", lambda: 1000)
    issuer = issuer_module.ExternalSignerAuthoritativeUseLeaseIssuer(
        signer=signer, grant_provider=provider, replay_store=store,
        current_generation_authority=current_authority(monkeypatch, tmp_path, payload))
    assert issuer.prepare_request(payload=payload, authority_tier="HIGH") == state.kw["target"]
    permit = state.signing.prepare_permit(state.proof)
    assert permit is not None
    reset_owner_reads(state)
    lease = issuer.issue(payload=payload, authority_tier="HIGH", effect_signing_permit=permit)
    expected = dict(effect_kind="worktree_create", effect_request_digest=payload["effect_request_digest"])
    assert is_authoritative_use_lease(lease, **expected)
    assert consume_authoritative_use_lease(lease, **expected)
    assert not consume_authoritative_use_lease(lease, **expected)
    assert len(state.nonces.consumed) == 1
