"""Connected lease issuance with real signatures and synthetic owner/custody seams."""

from contextlib import contextmanager
from dataclasses import replace
import json
from types import SimpleNamespace
import pytest

from .reddog_effect_signing_test_support import setup, reset_owner_reads, resident_case, resident_proof_supplier
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


def connected_issuer(monkeypatch, tmp_path, *, target_overrides=None, parent_overrides=None):
    monkeypatch.setitem(fixtures._store.__globals__, "NOW", 1000)
    store = fixtures._store(tmp_path / "store")
    target_key = fixtures.Ed25519PrivateKey.generate()
    overrides = dict(existing._replay_binding(store), signer_public_key=fixtures._public(target_key),
                     socket_path_digest=existing.digest_text(existing._binding().socket_path))
    overrides.update(target_overrides or {})
    state = setup(monkeypatch, tmp_path / "approval", target_overrides=overrides,
                  parent_overrides=parent_overrides)
    state.runtime_records["reviewer:test"] = replace(state.runtime_records["reviewer:test"], expires_at=1001)
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
    return issuer, state, payload


@pytest.mark.parametrize("delayed", [False, True])
def test_effect_proof_reaches_verified_one_use_lease(monkeypatch, tmp_path, delayed):
    issuer, state, payload = connected_issuer(monkeypatch, tmp_path)
    provider = issuer.grant_provider
    if delayed:
        def issue_grant(*args, **kwargs):
            grant = provider.issue_grant(*args, **kwargs)
            monkeypatch.setitem(_target_client.__globals__, "NOW", 1002)
            return grant
        issuer = replace(issuer, grant_provider=SimpleNamespace(issue_grant=issue_grant))
    assert issuer.prepare_request(payload=payload, authority_tier="HIGH") == state.kw["target"]
    permit = state.signing.prepare_permit(state.proof)
    assert permit is not None
    reset_owner_reads(state)
    lease = issuer.issue(payload=payload, authority_tier="HIGH", effect_signing_permit=permit)
    if delayed:
        assert lease is None
        return
    expected = dict(effect_kind="worktree_create", effect_request_digest=payload["effect_request_digest"])
    assert is_authoritative_use_lease(lease, **expected)
    assert consume_authoritative_use_lease(lease, **expected)
    assert not consume_authoritative_use_lease(lease, **expected)
    assert len(state.nonces.consumed) == 1


def _resident_target(monkeypatch, tmp_path, change):
    from modules.communication.moltbot_bridge.src import reddog_resident_queue_execution_valve_handler as handler_module
    from modules.communication.moltbot_bridge.src.reddog_worktree_admission_capability import authoritative_worktree_effect_payload
    from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease_contract import digest_mapping
    handler, request, registry, store = resident_case(monkeypatch, tmp_path / "resident")
    captured = {}
    real_invoke = handler_module.invoke_reddog_wre_queue_authorized_execution_valve
    def capture(**kwargs):
        result = real_invoke(**kwargs)
        captured["result"] = result
        return result
    monkeypatch.setattr(handler_module, "invoke_reddog_wre_queue_authorized_execution_valve", capture)
    # Compute the actual canonical decision; lack of a lease must reject admission.
    initial = handler(request)
    assert captured["result"].decision == handler_module.QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT, initial.get("rejection_reasons")
    assert initial["decision"] == handler_module.QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
    decision = captured["result"].valve_decision.to_dict()
    order = handler.work_order_resolver.work_order
    stages = store.load()["stage_results"]
    plan = stages["executor_plan"]
    parent = stages["authority_runtime"]["authority_result"]
    resolution = handler.governed_use_time_authority_resolver.result
    effect = authoritative_worktree_effect_payload(request.queue_item_id, request.selected_slice, order, plan, decision)
    overrides = dict(effect_payload=effect, work_authority_digest=digest_mapping(parent["work_authority"]),
                     identity_digest=digest_mapping(parent["identity"]), expected_bindings_digest=digest_mapping(resolution.expected_bindings))
    wrong_fields = dict(wrong_authority="work_authority_digest", wrong_identity="identity_digest",
                        wrong_bindings="expected_bindings_digest")
    if change in wrong_fields:
        overrides[wrong_fields[change]] = digest_mapping({"different": change})
    elif change == "wrong_decision":
        overrides["effect_payload"] = dict(effect, valve_decision_digest=digest_mapping({"different": "decision"}))
    return handler, request, registry, store, decision, order, plan, resolution, effect, overrides


def _expire_after_issuance(monkeypatch, handler, permission_only, effect):
    from datetime import datetime
    from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease_contract import authoritative_use_effect_digest
    checked = []
    original = issuer_module.ExternalSignerAuthoritativeUseLeaseIssuer.issue_for_worktree
    def expires_after_issuance(self, **kwargs):
        lease = original(self, **kwargs)
        assert lease is not None
        if permission_only:
            expiry = handler.governed_use_time_authority_resolver.result.permission_expires_at
            expired_epoch = int(datetime.fromisoformat(expiry).timestamp()) + 1
            handler.governed_use_time_authority_resolver.trusted_now_epoch = lambda: expired_epoch
            assert is_authoritative_use_lease(lease, effect_kind="worktree_create",
                effect_request_digest=authoritative_use_effect_digest("worktree_create", effect))
        else:
            expired_epoch = lease.expires_at_epoch + 1
            monkeypatch.setattr(issuer_module.time, "time", lambda: expired_epoch)
        checked.append(True)
        return lease
    monkeypatch.setattr(issuer_module.ExternalSignerAuthoritativeUseLeaseIssuer, "issue_for_worktree", expires_after_issuance)
    return checked


@pytest.mark.parametrize("change", [None, "order", "chain", "resolution", "exception", "expired", "permission_expired",
    "wrong_decision", "wrong_authority", "wrong_identity", "wrong_bindings"])
def test_resident_final_decision_reaches_real_grant_and_admission(monkeypatch, tmp_path, change):
    from modules.communication.moltbot_bridge.src import reddog_resident_queue_execution_valve_handler as handler_module
    handler, request, registry, store, decision, order, plan, resolution, effect, overrides = _resident_target(monkeypatch, tmp_path, change)
    issuer, state, _ = connected_issuer(monkeypatch, tmp_path / "issuer", target_overrides=overrides,
        parent_overrides=dict(work_order_id=effect["work_order_id"], work_order_digest=effect["work_order_digest"]))
    proof, calls = resident_proof_supplier(change, effect, order, store, handler, resolution, state)
    issuer = replace(issuer, effect_signing_authority=state.signing, effect_proof_supplier=proof)
    if change and change.startswith("wrong_"):
        from modules.communication.moltbot_bridge.src.reddog_effect_consensus_proof import discard_effect_signing_permit
        valid_other_target = state.signing.prepare_permit(state.proof)
        assert valid_other_target is not None, "negative control must have valid approval for its other target"
        discard_effect_signing_permit(valid_other_target)
        reset_owner_reads(state)
    if change in ("expired", "permission_expired"):
        expiry_checked = _expire_after_issuance(monkeypatch, handler, change == "permission_expired", effect)
    handler = replace(handler, worktree_lease_issuer=issuer)
    result = handler(request)
    if change in ("expired", "permission_expired"):
        assert expiry_checked == [True]
    assert len(calls) == 1
    if change != "exception" and not (change and change.startswith("wrong_")):
        assert len(state.nonces.consumed) == 1, "real grant signing was not reached"
    else:
        assert not state.nonces.consumed
    if change:
        assert result["decision"] == handler_module.QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_REJECT
        assert not registry._capabilities
    else:
        assert result["decision"] == handler_module.QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT, result.get("rejection_reasons")
        args = dict(queue_item_id=request.queue_item_id, selected_slice=request.selected_slice,
                    work_order=order, executor_plan_result=plan, valve_decision=decision)
        assert registry.consume(**args) is not None
        assert registry.consume(**args) is None


@pytest.mark.parametrize("reason", [
    "canonical_consensus_receipt_verifier_missing", "canonical_sovereign_authorization_verifier_missing",
    "canonical_principal_subject_key_attestation_missing", "canonical_model_signed_evidence_trust_anchor_incomplete",
    "canonical_model_selection_signed_evidence_verifier_missing", "canonical_memex_supply_signed_evidence_verifier_missing",
    "canonical_signer_client_peer_handshake_verifier_missing"])
def test_each_unresolved_gate_stops_before_effect_issuer(monkeypatch, tmp_path, reason):
    handler, request, registry, _ = resident_case(monkeypatch, tmp_path)
    resolver = handler.governed_use_time_authority_resolver
    resolver.result = replace(resolver.result, rejection_reasons=(reason,))
    def forbidden(*args, **kwargs):
        pytest.fail("effect issuer called despite unresolved gate")
    monkeypatch.setattr(issuer_module.ExternalSignerAuthoritativeUseLeaseIssuer, "issue_for_worktree", forbidden)
    issuer = issuer_module.ExternalSignerAuthoritativeUseLeaseIssuer(None, None, None, None)
    result = replace(handler, worktree_lease_issuer=issuer)(request)
    assert reason in result["rejection_reasons"]
    assert not registry._capabilities
