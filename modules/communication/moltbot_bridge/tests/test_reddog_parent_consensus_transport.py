"""Compact parent transport keeps the production parser bound; no authority seams."""

from copy import deepcopy
import json
import pytest

from .reddog_parent_consensus_test_support import setup
from modules.communication.moltbot_bridge.src import reddog_effect_consensus_proof as wire
from modules.communication.moltbot_bridge.src.reddog_parent_consensus_proof import snapshot_parent_consensus_proof


def rehash(proof):
    proof['consensus_receipt']['receipt_id'] = wire._receipt_id(proof)


def size(proof):
    return len(json.dumps(proof, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8'))


def test_compact_parent_reconstructs_exact_request_under_unchanged_cap(monkeypatch, tmp_path):
    state = setup(monkeypatch, tmp_path)
    assert wire.MAX_EFFECT_PROOF_BYTES == 16384
    assert 'authority_request' not in state.proof['parent_consensus_proof']
    assert wire.parent_proof_from_effect(state.proof) == state.parent_proof
    assert size(state.proof) < 16384
    assert wire.snapshot_effect_consensus_proof(state.proof)[0] == state.proof
    assert state.signing.prepare_permit(state.proof) is not None


@pytest.mark.parametrize('fault', ['outer_change', 'duplicate', 'conflicting', 'missing', 'extra', 'noncanonical'])
def test_compact_parent_tamper_rejects_before_authority(monkeypatch, tmp_path, fault):
    state = setup(monkeypatch, tmp_path)
    proof = deepcopy(state.proof)
    material = proof['parent_consensus_proof']
    if fault == 'outer_change':
        proof['authority_request']['repo_full_name'] = 'different/repository'
    elif fault in ('duplicate', 'conflicting'):
        material['authority_request'] = deepcopy(proof['authority_request'])
        if fault == 'conflicting': material['authority_request']['repo_full_name'] = 'different/repository'
    elif fault == 'missing': material.pop('parent_consent')
    elif fault == 'extra': material['unapproved'] = True
    else: proof['authority_request']['allowed_paths'] = 'not-a-canonical-path-list'
    rehash(proof)
    assert state.signing.prepare_permit(proof) is None
    if fault != 'outer_change':
        with pytest.raises(ValueError): wire.snapshot_effect_consensus_proof(proof)


def test_transport_exact_size_boundary_is_not_authority(monkeypatch, tmp_path):
    state = setup(monkeypatch, tmp_path)
    proof = deepcopy(state.proof)
    queue = proof['authority_request']['queue_consumer_receipt']
    queue['slice_id'] += 'x' * (16384 - size(proof))
    rehash(proof)
    assert size(proof) == 16384
    wire.snapshot_effect_consensus_proof(proof)
    # Rehashed wire data cannot repair the changed signed parent/context binding.
    assert state.signing.prepare_permit(proof) is None
    queue['slice_id'] += 'x'
    rehash(proof)
    assert size(proof) == 16385
    with pytest.raises(ValueError, match='size_invalid'):
        wire.snapshot_effect_consensus_proof(proof)


def test_parent_policy_membership_does_not_coerce_string_rows(monkeypatch, tmp_path):
    state = setup(monkeypatch, tmp_path)
    proof = deepcopy(state.parent_proof)
    proof['policy']['reviewer_membership'] = ['abc']
    with pytest.raises(ValueError, match='policy_shape_invalid'):
        snapshot_parent_consensus_proof(proof)
