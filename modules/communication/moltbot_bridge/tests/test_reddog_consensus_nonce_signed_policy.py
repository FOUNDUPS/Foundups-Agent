"""Real signed E0/config/principal files; only OS owner/selection/credential IO seams."""
from pathlib import Path
import pytest
from .consensus_nonce_test_support import case, load, current, NONCE, SUBJECT
from . import test_reddog_signer_owner_controlled_e0_admission as e0


def signed_case(monkeypatch, tmp_path, *, operations=None, tier='HIGH'):
    (tmp_path/'owner').mkdir()
    state = case(monkeypatch, tmp_path/'owner')
    root = tmp_path/'signed'
    root.mkdir()
    signed = e0._fixture(root)
    signed['policy'].update(owner_config_id=state.owner['config_id'],
        allowed_operations=operations or ['delegate_reddog_identity', 'worktree_create'],
        allowed_authority_tiers=[tier], consensus_required_tiers=[tier])
    signed['selection'].update(owner_config_id=state.owner['config_id'],
        repo_root=str(state.values['repo'].resolve()),
        selection_issued_at=int(state.wall)-1, selection_expires_at=int(state.wall)+30)
    e0._rebind_config_and_sign(signed, signed['grant_private'])
    state.policy, state.selection = signed['policy'], signed['selection']
    def selection(**kwargs):
        capability = object()
        return capability, e0._SelectionBoundary(capability, state.selection)
    monkeypatch.setattr(e0.current_selection_module, 'load_system_service_manifest_selection', selection)
    original = e0.current_selection_module.lease_validated_owner_e0_current_admission
    from contextlib import contextmanager
    @contextmanager
    def lease(**kwargs):
        with original(**kwargs) as selected:
            state.active += 1
            try: yield selected
            finally: state.active -= 1
    monkeypatch.setattr(current, 'lease_validated_owner_e0_current_admission', lease)
    return state


def test_real_signed_policy_config_and_principal_validation_before_reservation(monkeypatch, tmp_path):
    state = signed_case(monkeypatch, tmp_path)
    store = load(state)
    token = store.reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT)
    assert token
    store.commit(token)
    assert load(state).reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT) is None


@pytest.mark.parametrize('fault', ['signature', 'principal', 'selection', 'policy', 'operation', 'identity_only', 'LOW', 'ULTRA'])
def test_signed_policy_and_exact_scope_fail_closed_before_credential(monkeypatch, tmp_path, fault):
    operations = ['other_operation', 'worktree_create'] if fault == 'operation' else None
    if fault == 'identity_only': operations = ['delegate_reddog_identity']
    state = signed_case(monkeypatch, tmp_path, operations=operations, tier=fault if fault in ('LOW','ULTRA') else 'HIGH')
    if fault == 'signature': state.policy['signature'] = 'invalid'
    elif fault == 'principal': Path(state.selection['principal_authority_records_path']).write_bytes(b'{}')
    elif fault == 'selection': state.selection['generation'] += 1
    elif fault == 'policy': state.policy['rate_limit_max_requests'] += 1
    with pytest.raises(ValueError): load(state)
    assert state.reads == 0
