"""Synthetic OS-owner/lease seams; actual Ed25519 and digest-bound artifact IO."""

from copy import deepcopy
from dataclasses import replace

from modules.communication.moltbot_bridge.tests import reddog_effect_consent_test_support as effects
from modules.communication.moltbot_bridge.src import reddog_parent_consent_contract as contract
from modules.communication.moltbot_bridge.src import reddog_current_parent_consent_verification as runtime
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_contract import (
    canonical_authority_request_digest,
)


def setup(monkeypatch, tmp_path):
    _, state = effects.setup(monkeypatch, tmp_path)
    from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor_codec import _state_revision
    # Earlier effect fixtures use a placeholder revision; preserve the actual producer wire shape.
    state.selection["generation_revision"] = _state_revision(state.selection)
    prior, parent = state.authority, state.kw["parent"]
    state.authority = dict(schema_version=contract.AUTHORITY_SCHEMA, privilege=contract.PRIVILEGE,
        issuer_principal_id=prior["issuer_principal_id"], issuer_principal_provider=prior["issuer_principal_provider"],
        issuer_public_key=prior["issuer_public_key"], issuer_key_epoch=prior["issuer_key_epoch"],
        beneficiary_principal_id=parent.principal_id, beneficiary_principal_provider=parent.principal_provider,
        beneficiary_public_key=parent.principal_public_key, reddog_id=parent.reddog_id,
        reddog_public_key=parent.reddog_public_key, reddog_key_epoch=parent.key_epoch,
        repo_full_name=parent.repo_full_name, foundup_id=parent.foundup_id, policy_digest=prior["policy_digest"],
        authority_tier="HIGH", requested_operation="worktree_create", issued_at=900, expires_at=1100)
    state.owner = dict(schema_version=state.loader.SCHEMA_VERSION_V11,
        config_id=state.selection["owner_config_id"], parent_consent_authority=state.authority)
    state.assertion = dict(state.authority, schema_version=contract.ASSERTION_SCHEMA,
        issued_at=1000, expires_at=1020, owner_authority_digest=contract.parent_consent_authority_digest(state.authority),
        authority_request_digest=canonical_authority_request_digest(parent),
        **{key: state.selection[key] for key in contract.CURRENT_FIELDS})
    state.parent = parent
    state.call = dict(owner_config_path=tmp_path / "owner.json", repo_root=state.repo,
                      assertion=state.assertion, parent=parent, policy=state.kw["policy"])
    state.runtime = runtime
    def clock():
        if state.clock_callback:
            state.clock_callback(state)
        return state.now
    monkeypatch.setattr(runtime, "_now_epoch", clock)
    resign(state)
    return runtime.resolve_current_parent_sovereign_authorization, state


def resign(state):
    state.message = effects.sign(state.assertion, state.issuer, contract.SIGNING_PREFIX)


def replace_parent(state, **changes):
    state.call["parent"] = replace(state.call["parent"], **changes)


def closed(state):
    assert not state.lease.active
    assert state.lease.exited == state.lease.entered


def positive(resolve, state):
    result = resolve(**state.call)
    assert type(result) is contract.ParentConsentEvidence
    assert result.consensus_policy_digest == state.call["policy"].policy_digest
    assert result.authority_request_digest == canonical_authority_request_digest(state.parent)
    assert result.authorization_digest == runtime.raw_digest(state.message.encode("ascii"))
    assert result.principal_public_key == state.parent.principal_public_key
    assert result.expires_at == 1020
    assert state.crypto[-1][-1] is True
    assert state.reads == state.artifact_reads == 2
    assert state.lease.selected == state.lease.entered == state.lease.exited == 1
    assert not hasattr(result, "consume") and not hasattr(result, "authority_granted")
    closed(state)
    return result
