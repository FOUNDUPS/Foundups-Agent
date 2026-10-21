"""Same-generation parent and effect join; OS/model seams are explicitly synthetic."""

from copy import deepcopy
from dataclasses import replace
import pytest

from .reddog_parent_consensus_test_support import setup
from modules.communication.moltbot_bridge.src.reddog_parent_consent_contract import ParentConsentEvidence
from modules.communication.moltbot_bridge.src.reddog_elevated_consensus_signer_reservation import (
    commit_elevated_consensus_nonce, elevated_consensus_reservation_current,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant_contract import signer_secret_access_request_digest


def test_one_generation_verifies_parent_and_effect_then_current_nonce_commit(monkeypatch, tmp_path):
    state = setup(monkeypatch, tmp_path)
    result = state.parent_authority.verify(state.parent_proof)
    assert result is not None and type(result[4]) is ParentConsentEvidence
    assert state.lease.entered == state.lease.exited == 1
    permit = state.signing.prepare_permit(state.proof)
    assert permit is not None
    assert state.lease.entered == state.lease.exited == 2
    assert not state.lease.active
    reservation = state.signing.reserve(state.proof,
        signing_request_digest=signer_secret_access_request_digest(state.kw['target'].to_dict()),
        now=state.now, grant_expires_at=1010)
    assert reservation is not None and elevated_consensus_reservation_current(reservation)
    assert commit_elevated_consensus_nonce(reservation)
    assert len(state.nonces.consumed) == 1 and not state.nonces.reserved


@pytest.mark.parametrize('fault', ['parent_domain', 'effect_domain', 'withdraw', 'policy', 'model', 'entry', 'generation'])
def test_parent_effect_join_rejects_missing_or_changed_current_inputs(monkeypatch, tmp_path, fault):
    state = setup(monkeypatch, tmp_path)
    if fault == 'parent_domain': state.owner['parent_reviewer_designation_authority'] = state.owner['reviewer_designation_authority']
    elif fault == 'effect_domain': state.owner['reviewer_designation_authority'] = state.owner['parent_reviewer_designation_authority']
    elif fault == 'withdraw': state.owner.pop('parent_consent_authority')
    elif fault == 'policy': state.proof['parent_consensus_proof']['policy']['authority_principal_id'] = 'rebound'
    elif fault == 'model': state.runtime_records.clear()
    elif fault == 'entry': state.lease_error = True
    else: state.selection['generation'] += 1
    assert state.signing.prepare_permit(state.proof) is None
    assert not state.lease.active and not state.nonces.reserved


def test_nonce_commit_revalidates_withdrawal_and_rolls_back(monkeypatch, tmp_path):
    state = setup(monkeypatch, tmp_path)
    reservation = state.signing.reserve(state.proof,
        signing_request_digest=signer_secret_access_request_digest(state.kw['target'].to_dict()),
        now=state.now, grant_expires_at=1010)
    assert reservation is not None
    state.owner['parent_consent_authority']['issuer_key_epoch'] = 'rotated'
    assert not commit_elevated_consensus_nonce(reservation)
    assert not state.nonces.reserved and not state.nonces.consumed


def test_actual_signed_model_files_parent_and_effect_join(monkeypatch, tmp_path):
    state = setup(monkeypatch, tmp_path, real_models=True)
    assert state.parent_authority.verify(state.parent_proof) is not None
    assert state.signing.prepare_permit(state.proof) is not None
    assert state.lease.entered == state.lease.exited == 2


@pytest.mark.parametrize('phase', ['prepare', 'reserved', 'commit'])
def test_failed_lease_exit_withholds_result_and_rolls_back_only_owned_nonce(monkeypatch, tmp_path, phase):
    from contextlib import contextmanager
    state = setup(monkeypatch, tmp_path)
    original = state.lease._lease_current
    fail = [phase == 'prepare']
    @contextmanager
    def lease(token):
        with original(token) as selected:
            yield selected
        if fail[0]: raise RuntimeError('synthetic failed lease exit')
    monkeypatch.setattr(state.lease, '_lease_current', lease)
    foreign = state.nonces.reserve('foreign', expires_at=1020, subject='foreign')
    if phase == 'prepare':
        assert state.parent_authority.prepare(state.parent_proof) is None
        assert state.signing.prepare_permit(state.proof) is None
    else:
        reserve = state.nonces.reserve
        def after_reserve(*args, **kwargs):
            result = reserve(*args, **kwargs)
            if phase == 'reserved': fail[0] = True
            return result
        monkeypatch.setattr(state.nonces, 'reserve', after_reserve)
        reservation = state.signing.reserve(state.proof,
            signing_request_digest=signer_secret_access_request_digest(state.kw['target'].to_dict()),
            now=state.now, grant_expires_at=1010)
        if phase == 'reserved': assert reservation is None
        else:
            assert reservation is not None
            fail[0] = True
            assert not commit_elevated_consensus_nonce(reservation)
    assert len(state.nonces.reserved) == 1 and not state.nonces.consumed
    state.nonces.rollback(foreign)
    assert not state.nonces.reserved and not state.lease.active
