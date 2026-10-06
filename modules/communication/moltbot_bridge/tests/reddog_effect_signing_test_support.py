"""Real disposable approval signatures; explicitly synthetic owner/runtime inputs."""

from copy import deepcopy
from dataclasses import asdict, replace
from types import SimpleNamespace

from . import reddog_effect_consent_test_support as consent
from . import reddog_reviewer_authority_test_support as keys
from .test_reddog_elevated_authority_consensus_effect_reviewer import _case
from .reddog_elevated_consensus_test_support import TestAuthorRuntimeEvidenceResolver
from .reddog_elevated_consensus_test_doubles import TestConsensusNonceAuthority
from modules.communication.moltbot_bridge.src import reddog_current_effect_signing_authority as module
from modules.communication.moltbot_bridge.src.reddog_effect_consensus_proof import build_effect_consensus_proof
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_effect_context import canonical_effect_approval_context_digest


class Resolver:
    def __init__(self, value):
        self.value = value

    def resolve(self, *args):
        return self.value


def _prepare_parent(state):
    state.kw["parent"] = replace(state.kw["parent"],
        model_selection_receipt_id="selection:author", model_selection_digest="sha256:" + "a" * 64,
        model_runtime_binding_receipt_id="reddog_model_runtime_binding:author",
        model_runtime_binding_digest="sha256:" + "b" * 64,
        model_runtime_binding_verification_receipt_id="model_runtime_binding_verification:author",
        model_runtime_binding_verification_digest="sha256:" + "c" * 64)
    state.evidence = consent.supplied._refresh(state.evidence, state.kw)
    state.assertion.update(parent_authorization=asdict(state.evidence.parent_authorization),
        **{k: getattr(state.evidence, k) for k in ("parent_authority_request_digest",
            "target_signing_request_digest", "effect_request_digest")})
    consent.resign(state)


def _prepare_reviewers(state, monkeypatch):
    authority, designation, issuer, reviewer = keys.fixture()
    authority["policy_digest"] = state.kw["policy"].policy_digest
    designation.update(policy_digest=authority["policy_digest"], owner_authority_digest=keys.digest(authority))
    keys.sign(designation, issuer)
    state.owner.update(schema_version="reddog_signer_system_service_owner_config.v7",
                       reviewer_designation_authority=authority)
    state.artifact.update(schema_version="reddog_authority_runtime_resolver_supply.v2",
                          reviewer_authorizations=[designation])
    state.artifact["principals"].update({
        "test|issuer:test": consent.record(state, "issuer:test", "test", keys.public(issuer)),
        "test|reviewer:test": consent.record(state, "reviewer:test", "test", keys.public(reviewer)),
    })
    _, source = _case(monkeypatch)
    decision = deepcopy(source["decision"])
    decision.update(reviewer_public_key=keys.public(reviewer),
        consensus_context_digest=canonical_effect_approval_context_digest(state.kw["context"]))
    keys.sign(decision, reviewer, "reddog-effect-consensus-review.v1.")
    second_key = keys.Ed25519PrivateKey.generate()
    second = dict(decision, decision_id="decision:second", reviewer_principal_id="reviewer:second",
        reviewer_public_key=keys.public(second_key), reviewer_key_epoch="second-epoch",
        reviewer_role="verifier", reviewer_model_id="model:second", model_selection_receipt_id="selection:second",
        model_selection_digest="sha256:" + "6" * 64, model_runtime_binding_receipt_id="runtime:second",
        model_runtime_binding_digest="sha256:" + "7" * 64)
    designation["reviewers"].append(dict(designation["reviewers"][0], principal_id="reviewer:second",
        public_key=keys.public(second_key), key_epoch="second-epoch", authorized_roles=["verifier"]))
    state.artifact["principals"]["test|reviewer:second"] = consent.record(state, "reviewer:second", "test", keys.public(second_key))
    keys.sign(designation, issuer)
    keys.sign(second, second_key, "reddog-effect-consensus-review.v1.")
    first_runtime = source["runtime_evidence_resolver"].value
    second_runtime = replace(first_runtime, **{k: second[k] for k in first_runtime.__dataclass_fields__ if k != "expires_at"})
    state.runtime_records = {"reviewer:test": first_runtime, "reviewer:second": second_runtime}
    state.decisions = [decision, second]


def setup(monkeypatch, tmp_path, *, target_overrides=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    original_verify = module.reviews.Ed25519SignatureVerifier.verify
    _, state = consent.setup(monkeypatch, tmp_path)
    approval_verify = module.reviews.Ed25519SignatureVerifier.verify
    def verify(self, key, message, signature):
        if message.startswith(("reddog-effect-consent.", "reddog-reviewer-designation.", "reddog-effect-consensus-review.")):
            return approval_verify(self, key, message, signature)
        return original_verify(self, key, message, signature)
    monkeypatch.setattr(module.reviews.Ed25519SignatureVerifier, "verify", verify)
    if target_overrides:
        consent.supplied._target(state.kw, **target_overrides)
        state.authority["target_signer_public_key"] = state.kw["target"].signer_public_key
        state.assertion["target_signer_public_key"] = state.kw["target"].signer_public_key
        state.assertion["owner_authority_digest"] = keys.digest(state.authority)
    _prepare_parent(state)
    _prepare_reviewers(state, monkeypatch)
    consent.refresh(state)
    monkeypatch.setattr(module, "_now_epoch", lambda: state.now)
    monkeypatch.setattr(module.reviews, "_now_epoch", lambda: state.now)
    state.nonces = TestConsensusNonceAuthority()
    state.signing = module.CurrentEffectSigningAuthority(
        repo_root=state.repo, owner_config_path=state.call["owner_config_path"],
        policy_resolver=Resolver(state.kw["policy"]),
        runtime_evidence_resolver=SimpleNamespace(resolve=lambda principal, *_: state.runtime_records.get(principal)),
        author_runtime_evidence_resolver=TestAuthorRuntimeEvidenceResolver(state.kw["parent"], state.now),
        sovereign_authorization_resolver=Resolver(state.evidence.parent_authorization),
        nonce_authority=state.nonces,
    )
    state.proof = build_effect_consensus_proof(context=state.kw["context"], decisions=state.decisions,
        consent=state.assertion, parent=state.kw["parent"], target=state.kw["target"])
    state.positive_calls = 0
    return state


def reset_owner_reads(state):
    state.reads = 0
