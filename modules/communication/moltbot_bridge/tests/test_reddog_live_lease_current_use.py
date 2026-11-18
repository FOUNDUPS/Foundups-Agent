"""Current consent/model/owner withdrawal at actual signer reservation phases."""
from copy import deepcopy
from dataclasses import replace
import pytest

from .reddog_live_lease_composition_support import setup, scope
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_signer_verification import ElevatedConsensusSignerAuthority
from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant_contract import signer_secret_access_request_digest
from modules.communication.moltbot_bridge.src.reddog_elevated_consensus_signer_reservation import (
    elevated_consensus_reservation_current, commit_elevated_consensus_nonce,
    rollback_elevated_consensus_nonce,
)


def reserve(state, token, domain):
    authority = ElevatedConsensusSignerAuthority(None, None, None, None, None, None,
        state.nonces, effect_authority=state.signing, parent_authority=state.parent_authority,
        _live_scope=token)
    target = state.signing_requests[0] if domain == 'parent' else state.kw['target']
    proof = deepcopy(state.parent_proof if domain == 'parent' else state.proof)
    if domain == 'parent':
        proof['target_signing_request'] = target.to_dict()
    return authority.reserve(proof, signing_request_digest=signer_secret_access_request_digest(target.to_dict()),
        now=state.now, grant_expires_at=1010)


@pytest.mark.parametrize('domain', ['parent', 'effect'])
@pytest.mark.parametrize('change', ['consent', 'model', 'expiry', 'generation'])
def test_presign_and_commit_freshly_reject_withdrawal(monkeypatch, tmp_path, domain, change):
    state = setup(monkeypatch, tmp_path)
    with pytest.raises(ValueError):
        with scope(state) as token:
            held = reserve(state, token, domain)
            assert held is not None and len(state.nonces._owned) == 1
            if change == 'consent':
                state.owner['parent_consent_authority']['issuer_key_epoch'] = 'rotated'
            elif change == 'model':
                state.owner['model_verifier_authority']['entries'][0]['selection_receipt_id'] = 'substituted'
            elif change == 'expiry':
                state.now = 1031
            else:
                state.selection['generation_revision'] = 'sha256:'+'f'*64
            assert elevated_consensus_reservation_current(held) is False
            assert commit_elevated_consensus_nonce(held) is False
            assert not state.nonces._owned
    assert not state.lease.active


@pytest.mark.parametrize('domain', ['parent', 'effect'])
def test_expired_scope_cannot_commit_and_owned_rollback_survives(monkeypatch, tmp_path, domain):
    state = setup(monkeypatch, tmp_path)
    with scope(state) as token:
        held = reserve(state, token, domain)
        assert held is not None
    assert elevated_consensus_reservation_current(held) is False
    assert commit_elevated_consensus_nonce(held) is False
    assert not state.nonces._owned
    with scope(state) as new_token:
        retry = reserve(state, new_token, domain)
        assert retry is not None
        rollback_elevated_consensus_nonce(retry)
    assert not state.nonces._owned
