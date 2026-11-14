"""Real review/consent signatures, synthetic protected owner and model-verifier seams."""

from copy import deepcopy
from dataclasses import asdict, replace
from types import SimpleNamespace

from . import reddog_effect_signing_test_support as effects
from . import reddog_effect_consent_test_support as consent
from . import reddog_reviewer_authority_test_support as keys
from .reddog_elevated_consensus_test_support import _principal_for_request
from modules.communication.moltbot_bridge.src import reddog_current_parent_consensus_authority as current
from modules.communication.moltbot_bridge.src import reddog_parent_consent_contract as parent_contract
from modules.communication.moltbot_bridge.src import reddog_reviewer_designation_contract as domains
from modules.communication.moltbot_bridge.src import reddog_elevated_authority_consensus_contract as wire
from modules.communication.moltbot_bridge.src.reddog_parent_consensus_proof import build_parent_consensus_proof
from modules.communication.moltbot_bridge.src.reddog_effect_consensus_proof import build_effect_consensus_proof
from modules.communication.moltbot_bridge.src.reddog_delegated_authority_signing_plan import build_delegated_authority_signing_requests
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_evidence import build_effect_target_binding
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_effect_context import canonical_effect_approval_context_digest


def _consent(state):
    parent, prior = state.kw['parent'], state.authority
    authority = dict(schema_version=parent_contract.AUTHORITY_SCHEMA, privilege=parent_contract.PRIVILEGE,
        issuer_principal_id=prior['issuer_principal_id'], issuer_principal_provider=prior['issuer_principal_provider'],
        issuer_public_key=prior['issuer_public_key'], issuer_key_epoch=prior['issuer_key_epoch'],
        beneficiary_principal_id=parent.principal_id, beneficiary_principal_provider=parent.principal_provider,
        beneficiary_public_key=parent.principal_public_key, reddog_id=parent.reddog_id,
        reddog_public_key=parent.reddog_public_key, reddog_key_epoch=parent.key_epoch,
        repo_full_name=parent.repo_full_name, foundup_id=parent.foundup_id, policy_digest=state.kw['policy'].policy_digest,
        authority_tier='HIGH', requested_operation='worktree_create', issued_at=900, expires_at=1100)
    state.owner['parent_consent_authority'] = authority
    assertion = dict(authority, schema_version=parent_contract.ASSERTION_SCHEMA,
        issued_at=1000, expires_at=1020, owner_authority_digest=parent_contract.parent_consent_authority_digest(authority),
        authority_request_digest=wire.canonical_authority_request_digest(parent),
        **{key: state.selection[key] for key in parent_contract.CURRENT_FIELDS})
    message = keys.sign(assertion, state.issuer, parent_contract.SIGNING_PREFIX)
    state.parent_assertion = assertion
    state.kw['parent'] = replace(parent, sovereign_authorization_digest=current.consent.raw_digest(message.encode('ascii')))


def _reviewers(state):
    authority = state.owner['reviewer_designation_authority']
    issuer = keys.Ed25519PrivateKey.generate()
    authority['issuer_public_key'] = keys.public(issuer)
    state.artifact['principals']['test|issuer:test'] = consent.record(state, 'issuer:test', 'test', keys.public(issuer))
    designation = state.artifact['reviewer_authorizations'][0]
    state.review_keys = [keys.Ed25519PrivateKey.generate() for _ in range(2)]
    for entry, decision, key in zip(designation['reviewers'], state.decisions, state.review_keys):
        entry['public_key'] = decision['reviewer_public_key'] = keys.public(key)
        pair = entry['principal_provider'] + '|' + entry['principal_id']
        state.artifact['principals'][pair]['principal_public_key'] = keys.public(key)
    designation['owner_authority_digest'] = keys.digest(authority)
    keys.sign(designation, issuer)
    parent_authority = dict(authority, schema_version=domains.PARENT_AUTHORITY_SCHEMA,
        privilege=domains.PARENT_PRIVILEGE, decision_schema_version=domains.PARENT_DECISION_SCHEMA)
    parent_designation = deepcopy(designation)
    parent_designation.update(schema_version=domains.PARENT_DESIGNATION_SCHEMA, privilege=domains.PARENT_PRIVILEGE,
        decision_schema_version=domains.PARENT_DECISION_SCHEMA, owner_authority_digest=keys.digest(parent_authority))
    keys.sign(parent_designation, issuer, domains.PARENT_SIGNING_PREFIX)
    state.owner['parent_reviewer_designation_authority'] = parent_authority
    state.artifact.update(schema_version='reddog_authority_runtime_resolver_supply.v3',
                          reviewer_authorizations=[designation, parent_designation])


def _parent_proof(state):
    parent, policy = state.kw['parent'], state.kw['policy']
    plan = build_delegated_authority_signing_requests(parent, _principal_for_request(parent),
        authority_tier='HIGH', has_runtime_binding=True)
    context = wire.ElevatedAuthorityConsensusContext(wire.CONSENSUS_SCHEMA_VERSION,
        wire.canonical_authority_request_digest(parent), parent.sovereign_authorization_digest,
        policy.policy_digest, tuple(wire.canonical_elevated_signing_request_digest(item) for item in plan[2:]),
        policy.minimum_approvals, policy.required_roles, 'synthetic-parent-consensus', 1000, 1020)
    decisions = []
    for original, key in zip(state.decisions, state.review_keys):
        decision = dict(original, schema_version=wire.DECISION_SCHEMA_VERSION,
                        consensus_context_digest=wire.canonical_consensus_context_digest(context))
        keys.sign(decision, key, wire.DECISION_SIGNING_PREFIX + '.')
        decisions.append(wire.ElevatedAuthorityReviewerDecision(**decision))
    receipt = wire.ElevatedAuthorityConsensusReceipt(wire.CONSENSUS_SCHEMA_VERSION, 'pending', context, tuple(decisions))
    receipt = replace(receipt, receipt_id=wire.canonical_consensus_receipt_digest(receipt))
    state.kw['parent'] = replace(parent, consensus_receipt_digest=receipt.receipt_id)
    state.parent_proof = build_parent_consensus_proof(receipt=receipt, parent=state.kw['parent'],
        assertion=state.parent_assertion, policy=policy)
    state.signing_requests = build_delegated_authority_signing_requests(state.kw['parent'],
        _principal_for_request(state.kw['parent']), authority_tier='HIGH', has_runtime_binding=True)[2:]


def _effect_proof(state):
    parent = state.kw['parent']
    evidence = current.consent._evidence(state.parent_assertion, parent,
        parent_contract.canonical_parent_consent_signing_input({k: v for k, v in state.parent_assertion.items() if k != 'signature'}))
    binding = build_effect_target_binding(parent=parent, target=state.kw['target'],
        expected_target=state.kw['target'].to_dict(), now=state.now)
    state.assertion.update(schema_version='reddog_effect_consent.v2', parent_authorization=asdict(evidence),
                           **{k: v for k, v in binding.items() if k != 'schema_version'})
    message = keys.sign(state.assertion, state.issuer, 'reddog-effect-consent.v2.')
    state.kw['context'] = replace(state.kw['context'], **{k: v for k, v in binding.items() if k != 'schema_version'},
        sovereign_authorization_digest=current.consent.raw_digest(message.encode('ascii')))
    for decision, key in zip(state.decisions, state.review_keys):
        decision['consensus_context_digest'] = canonical_effect_approval_context_digest(state.kw['context'])
        keys.sign(decision, key, 'reddog-effect-consensus-review.v1.')
    state.proof = build_effect_consensus_proof(context=state.kw['context'], decisions=state.decisions,
        consent=state.assertion, parent=parent, target=state.kw['target'], parent_consensus_proof=state.parent_proof)


def _install_real_model_materials(state, material):
    from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import verified_runtime_binding_receipt, verification_receipt_digest
    from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_policy import ReviewerRuntimeEvidence
    from pathlib import Path
    raw, model_authority = material
    for entry in model_authority['entries']:
        for descriptor in entry['inputs'].values():
            old = Path(descriptor['path'])
            new = state.store / old.name
            new.write_bytes(old.read_bytes())
            descriptor['path'] = str(new)
    state.owner.update(runtime_root=str(state.store), model_verifier_authority=model_authority)
    author = verified_runtime_binding_receipt(raw['author']['binding'])
    state.kw['parent'] = replace(state.kw['parent'], model_selection_receipt_id=author.selection_receipt_id,
        model_selection_digest=author.selection_receipt_digest, model_runtime_binding_receipt_id=author.runtime_binding_receipt_id,
        model_runtime_binding_digest=author.runtime_binding_digest, model_runtime_binding_verification_receipt_id=author.receipt_id,
        model_runtime_binding_verification_digest=verification_receipt_digest(author))
    for decision in state.decisions:
        record = raw['reviewers'][decision['reviewer_principal_id']]
        receipt = verified_runtime_binding_receipt(record['binding'])
        evidence = ReviewerRuntimeEvidence(record['model_id'], receipt.selection_receipt_id, receipt.selection_receipt_digest,
            receipt.runtime_binding_receipt_id, receipt.runtime_binding_digest, receipt.valid_until)
        state.runtime_records[decision['reviewer_principal_id']] = evidence
        decision.update(**{key: value for key, value in asdict(evidence).items() if key != 'expires_at'})
    _consent(state); _parent_proof(state); _effect_proof(state)
    return raw


def _install_owner_checks(monkeypatch, state, real_verify):
    def owner(*args, **kwargs):
        state.reads += 1
        if state.owner_callback: state.owner_callback(state)
        if state.owner_error: raise ValueError('synthetic protected owner failure')
        return deepcopy(state.owner)
    def verify(self, key, message, signature):
        if not message.startswith(('reddog-signer-secret-access-grant.', 'reddog-signer-secret-grant-audit.')):
            assert state.lease.active
        result = real_verify(self, key, message, signature)
        if state.callback: state.callback(state)
        return result
    monkeypatch.setattr(state.loader, '_load_owner_config', owner)
    monkeypatch.setattr(current.consent.Ed25519SignatureVerifier, 'verify', verify)
    monkeypatch.setattr(current.consent, '_now_epoch', lambda: state.now)


def setup(monkeypatch, tmp_path, *, real_models=False):
    real_verify = current.consent.Ed25519SignatureVerifier.verify
    material = None
    if real_models:
        from .reddog_parent_model_test_support import model_inputs
        model_root = tmp_path / 'model-inputs'
        model_root.mkdir(parents=True)
        material = model_inputs(monkeypatch, model_root)
    state = effects.setup(monkeypatch, tmp_path)
    from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor_codec import _state_revision
    state.selection['generation_revision'] = _state_revision(state.selection)
    consent.supplied._target(state.kw, generation_revision=state.selection['generation_revision'])
    state.kw['parent'] = replace(state.kw['parent'], queue_consumer_receipt={**state.kw['parent'].queue_consumer_receipt, 'slice_id': 'synthetic-parent-consensus'})
    state.owner['schema_version'] = state.loader.SCHEMA_VERSION_V12
    _consent(state); _reviewers(state); _parent_proof(state); _effect_proof(state)
    if material is not None:
        raw = _install_real_model_materials(state, material)
    consent.refresh(state)
    _install_owner_checks(monkeypatch, state, real_verify)
    # Synthetic model seam is deliberately separate from actual model verifier tests.
    def models(**kwargs):
        assert state.lease.active
        if state.model_callback: state.model_callback(state)
        return (effects.TestAuthorRuntimeEvidenceResolver(state.kw['parent'], state.now).resolve(state.kw['parent'].model_runtime_binding_verification_receipt_id),
                SimpleNamespace(resolve=lambda identity, *_: state.runtime_records.get(identity)))
    state.model_callback = None
    from modules.communication.moltbot_bridge.src import reddog_parent_bound_effect_verification as joined
    if material is None:
        monkeypatch.setattr(current, 'verified_model_evidence', models)
        monkeypatch.setattr(joined, 'verified_model_evidence', models)
        raw = {'author': dict(model_id='synthetic-author', selection={}, binding={}),
               'reviewers': {identity: dict(model_id=value.reviewer_model_id, selection={}, binding={})
                             for identity, value in state.runtime_records.items()}}
    state.parent_authority = current.CurrentParentConsensusAuthority(state.repo, state.call['owner_config_path'], raw)
    state.signing = replace(state.signing, parent_authority=state.parent_authority,
                           policy_resolver=None, runtime_evidence_resolver=None,
                           author_runtime_evidence_resolver=None, sovereign_authorization_resolver=None)
    return state
