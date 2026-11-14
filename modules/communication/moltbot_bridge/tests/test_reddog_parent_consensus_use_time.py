"""Parent re-verification is real; prior signed-work/generation evidence is a seam."""

from dataclasses import replace
import pytest

from . import reddog_parent_consensus_test_support as fixtures
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import digest
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_principal_records import parse_principal_artifact
from modules.communication.moltbot_bridge.src.reddog_delegated_authority_signing_plan import build_delegated_authority_signing_requests
from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_runtime_binding import SignerCurrentGenerationRuntimeBinding, _digest as binding_digest
from modules.communication.moltbot_bridge.src import reddog_signer_current_generation_use_time_gate as gate

REASONS = ('canonical_consensus_receipt_verifier_missing', 'canonical_sovereign_authorization_verifier_missing')


def fixture(monkeypatch, tmp_path):
    state = fixtures.setup(monkeypatch, tmp_path, real_models=True)
    record = state.parent_authority.model_artifacts['author']
    work = dict(work_order_id=state.kw['parent'].work_order_id,
        model_selection_receipt=record['selection'], model_runtime_binding_receipt=record['binding'])
    state.kw['parent'] = replace(state.kw['parent'], work_order_digest=digest(work))
    fixtures._consent(state); fixtures._parent_proof(state)
    parent = state.kw['parent']
    records, _ = parse_principal_artifact((state.store / 'principal_authority_records.json').read_bytes())
    principal = records[parent.principal_provider + '|' + parent.principal_id]
    identity, authority, *_ = build_delegated_authority_signing_requests(parent, principal,
        authority_tier='HIGH', has_runtime_binding=True)
    # These unsigned payloads stand in for the separately verified work stage.
    fields = {key: state.selection[key] for key in ('manifest_id', 'artifact_generation_digest',
        'generation', 'generation_revision', 'owner_config_id', 'config_digest')}
    binding = SignerCurrentGenerationRuntimeBinding(True, (), receipt_id='sha256:'+'1'*64,
        **fields, principal_binding_digest=binding_digest(dict(identity=identity, work_authority=authority)),
        model_work_order_digest=digest(work), model_artifact_pair_digest=binding_digest(dict(
            model_selection_receipt=record['selection'], model_runtime_binding_receipt=record['binding'])),
        model_valid_until=1020, manifest_expires_at=1060, selection_expires_at=1060)
    supplier = replace(state.parent_authority, proof=state.parent_proof)
    return state, supplier, binding, identity, authority, work


def test_current_parent_evidence_only_clears_its_two_exact_bound_reasons(monkeypatch, tmp_path):
    state, supplier, binding, identity, authority, work = fixture(monkeypatch, tmp_path)
    monkeypatch.setattr(gate, 'verify_signer_current_generation_runtime_binding', lambda **kw: binding)
    arguments = dict(principal_identity=identity, principal_work_authority=authority, model_work_order=work)
    prior = gate.collect_signer_current_generation_use_time_evidence(True, state.repo, state.store,
        lambda: state.now, **arguments)
    assert not set(REASONS) & set(prior.bound_identity_reasons(identity, authority, work))
    current = gate.collect_signer_current_generation_use_time_evidence(True, state.repo, state.store,
        lambda: state.now, parent_consensus_authority=supplier, **arguments)
    assert set(REASONS) <= set(current.bound_identity_reasons(identity, authority, work))
    assert current.remaining_reasons((*REASONS, 'other_missing'),
        current.bound_identity_reasons(identity, authority, work)) == ('other_missing',)
    assert not binding.authority_granted and not binding.effect_capability_issued
    state.owner.pop('parent_consent_authority')
    assert not set(REASONS) & set(current.bound_identity_reasons(identity, authority, work))


@pytest.mark.parametrize('fault', ['work', 'identity', 'generation', 'model', 'expiry', 'callback', 'repo', 'binding_expiry', 'rollback'])
def test_use_time_parent_substitution_never_clears_reasons(monkeypatch, tmp_path, fault):
    state, supplier, binding, identity, authority, work = fixture(monkeypatch, tmp_path)
    if fault == 'work': work['additional_field'] = True
    elif fault == 'identity': identity['principal_id'] = 'other'
    elif fault == 'generation': binding = replace(binding, generation=binding.generation + 1)
    elif fault == 'model': binding = replace(binding, model_artifact_pair_digest='sha256:'+'f'*64)
    elif fault == 'expiry': state.now = 1020
    elif fault == 'callback': supplier = lambda *_: True
    elif fault == 'repo': supplier = replace(supplier, repo_root=tmp_path / 'foreign')
    elif fault == 'binding_expiry':
        binding = replace(binding, selection_expires_at=1001)
        state.callback = lambda _: setattr(state, 'now', 1001)
    else: state.callback = lambda _: setattr(state, 'now', 999)
    evidence = gate._with_parent(gate.SignerCurrentGenerationUseTimeEvidence(binding), supplier,
        state.repo, identity, authority, work, gate._nondecreasing_clock(lambda: state.now))
    assert not set(REASONS) & set(evidence.bound_identity_reasons(identity, authority, work))


@pytest.mark.parametrize('phase', ['collection', 'reason_use'])
@pytest.mark.parametrize('fault', ['binding_expiry', 'clock_rollback', 'peer_expiry'])
def test_parent_delay_rejects_stale_collection_and_reason_use(monkeypatch, tmp_path, phase, fault):
    state, supplier, binding, identity, authority, work = fixture(monkeypatch, tmp_path)
    if fault == 'binding_expiry':
        binding = replace(binding, selection_expires_at=1001)
    clock = [1000]
    original = type(supplier).verify
    observed = []
    def delayed(self, proof):
        result = original(self, proof)
        assert result is not None
        observed.append(True)
        clock[0] = 999 if fault == 'clock_rollback' else 1002
        return result
    monkeypatch.setattr(gate, 'verify_signer_current_generation_runtime_binding', lambda **kw: binding)
    # Prior peer and signed-work provenance are seams; parent/model verification is real.
    peer = gate.SignerCurrentGenerationUseTimeEvidence(binding, 'sha256:'+'2'*64, peer_valid_until=1001)
    monkeypatch.setattr(gate, '_collect_fresh_peer', lambda *a, **kw: peer)
    if phase == 'collection':
        monkeypatch.setattr(type(supplier), 'verify', delayed)
    evidence = gate.collect_signer_current_generation_use_time_evidence(True, state.repo, state.store,
        lambda: clock[0], principal_identity=identity, principal_work_authority=authority,
        model_work_order=work, parent_consensus_authority=supplier,
        peer_secret_access_grant_supplier=(lambda: None) if fault == 'peer_expiry' else None)
    if phase == 'reason_use':
        assert evidence.receipt_id is not None
        monkeypatch.setattr(type(supplier), 'verify', delayed)
    reasons = evidence.bound_identity_reasons(identity, authority, work)
    assert observed and reasons == ()
    if phase == 'collection':
        assert evidence.receipt_id is None
