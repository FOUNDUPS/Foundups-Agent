"""Inert single-review contracts; mock verification establishes no authority."""

from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import importlib
import json

import pytest


PREFIX = "reddog-effect-consensus-review.v1."
GOLDEN_PREIMAGE = (
    'reddog-effect-consensus-review.v1.{"consensus_context_digest":"sha256:7be8299af2a715cea19e7a2c616ce73248a4d7e4'
    '5bca2f23b82d65f6d6c684e5","decision":"APPROVE","decision_id":"decision:fixture","model_runtime_binding_digest"'
    ':"sha256:9999999999999999999999999999999999999999999999999999999999999999","model_runtime_binding_receipt_id":'
    '"runtime:reviewer","model_selection_digest":"sha256:8888888888888888888888888888888888888888888888888888888888'
    '888888","model_selection_receipt_id":"selection:reviewer","reviewer_key_epoch":"reviewer-epoch","reviewer_mode'
    'l_id":"model:reviewer","reviewer_principal_id":"reviewer:test","reviewer_principal_provider":"test","reviewer_'
    'public_key":"inert-reviewer-key","reviewer_role":"critic","schema_version":"reddog_effect_reviewer_decision.v1'
    '"}'
)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value):
    return "sha256:" + hashlib.sha256(_json(value).encode("ascii")).hexdigest()


def _preimage(decision):
    return PREFIX + _json({k: v for k, v in decision.items() if k != "signature"})


class _Resolver:
    def __init__(self, value):
        self.value, self.calls, self.error = value, [], False

    def resolve(self, *args):
        self.calls.append(args)
        if self.error:
            raise RuntimeError("inert resolver failure")
        return self.value


class _Verifier(_Resolver):
    def verify(self, *args):
        self.calls.append(args)
        if self.error:
            raise RuntimeError("inert verifier failure")
        return args == ("inert-reviewer-key", GOLDEN_PREIMAGE, "opaque-fixture-signature") if self.value == "bound" else self.value


def _bind_decision_context(kw):
    encoded = b"reddog-effect-approval-context.v1." + _json(kw["context"].to_dict()).encode("ascii")
    kw["decision"]["consensus_context_digest"] = "sha256:" + hashlib.sha256(encoded).hexdigest()


def _sync(kw):
    policy = asdict(kw["policy"])
    policy.pop("policy_digest")
    kw["policy"] = replace(kw["policy"], policy_digest=_digest(policy))
    parent = kw["authority_request"].to_dict()
    for key in ("consensus_receipt_digest", "sovereign_authorization_digest"):
        parent.pop(key, None)
    kw["context"] = replace(kw["context"], consensus_policy_digest=kw["policy"].policy_digest,
                            parent_authority_request_digest=_digest(parent))
    _bind_decision_context(kw)


def _case(monkeypatch):
    owner = importlib.import_module("modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_verification")
    verify = getattr(owner, "verify_effect_reviewer_decision", None)
    assert callable(verify), "verify_effect_reviewer_decision_api_missing"
    from modules.communication.moltbot_bridge.tests import test_reddog_elevated_authority_consensus_canonicalization as fixture
    from modules.communication.moltbot_bridge.src import reddog_elevated_authority_consensus_effect_context as contexts
    from modules.communication.moltbot_bridge.src import reddog_elevated_authority_consensus_policy as policies
    args, _ = fixture._binding_inputs(monkeypatch)
    golden = fixture._BINDING_GOLDEN
    context = contexts.EffectApprovalContext(
        "reddog_effect_approval_context.v1", golden["schema_version"],
        golden["parent_authority_request_digest"], golden["target_signing_request_digest"],
        golden["effect_request_digest"], "sha256:" + "e" * 64, "sha256:" + "f" * 64,
        2, ("critic", "verifier"), "inert-review-context", 1000, 1020)
    policy = policies.ElevatedConsensusPolicy("elevated-consensus-policy:fixture", "pending", "authority:fixture",
        (("reviewer:test", "test", "critic"), ("reviewer:second", "test", "verifier")), 2, ("critic", "verifier"), 20, 0)
    decision = dict(schema_version="reddog_effect_reviewer_decision.v1", decision_id="decision:fixture",
        reviewer_principal_id="reviewer:test", reviewer_principal_provider="test", reviewer_public_key="inert-reviewer-key",
        reviewer_key_epoch="reviewer-epoch", reviewer_role="critic", reviewer_model_id="model:reviewer",
        model_selection_receipt_id="selection:reviewer", model_selection_digest="sha256:" + "8" * 64,
        model_runtime_binding_receipt_id="runtime:reviewer", model_runtime_binding_digest="sha256:" + "9" * 64,
        consensus_context_digest="pending", decision="APPROVE", signature="opaque-fixture-signature")
    key = policies.ReviewerKeyAuthority("inert-reviewer-key", "reviewer-epoch", 1020)
    runtime = policies.ReviewerRuntimeEvidence("model:reviewer", "selection:reviewer", "sha256:" + "8" * 64,
        "runtime:reviewer", "sha256:" + "9" * 64, 1020)
    kw = dict(decision=decision, context=context, authority_request=args["parent"], target=args["target"],
        expected_target=args["expected_target"], policy=policy, signature_verifier=_Verifier(True),
        reviewer_key_resolver=_Resolver(key), runtime_evidence_resolver=_Resolver(runtime), now=1000)
    _sync(kw)
    return verify, kw


def _check(verify, kw, expected, early=False):
    data = lambda: {k: v for k, v in kw.items() if k not in ("signature_verifier", "reviewer_key_resolver", "runtime_evidence_resolver")}
    before = deepcopy(data())
    assert verify(**kw) is expected
    assert data() == before
    if early:
        assert all(not kw[name].calls for name in ("signature_verifier", "reviewer_key_resolver", "runtime_evidence_resolver"))


@pytest.mark.parametrize("case", ["golden", "last_current", "evidence_boundary", "arbitrary_sovereign"])
def test_effect_review_connected_positive_and_exact_preimage(monkeypatch, case):
    verify, kw = _case(monkeypatch)
    assert _preimage(kw["decision"]) == GOLDEN_PREIMAGE
    if case == "last_current":
        kw["now"] = 1019
    elif case == "evidence_boundary":
        for name in ("reviewer_key_resolver", "runtime_evidence_resolver"):
            kw[name].value = replace(kw[name].value, expires_at=1001)
    elif case == "arbitrary_sovereign":
        kw["context"] = replace(kw["context"], sovereign_authorization_digest="sha256:" + "a" * 64)
        _sync(kw)
    _check(verify, kw, True)
    assert kw["reviewer_key_resolver"].calls == [("reviewer:test", "test")]
    assert kw["runtime_evidence_resolver"].calls == [("reviewer:test", "selection:reviewer", "runtime:reviewer")]
    assert kw["signature_verifier"].calls == [("inert-reviewer-key", _preimage(kw["decision"]), "opaque-fixture-signature")]
    assert kw["policy"].minimum_approvals == 2  # One review is valid without claiming quorum.


@pytest.mark.parametrize("case", ["none", "mapping_type", "missing", "extra", "legacy", "unknown_schema", "empty", "non_ascii",
    "non_string", "long_field", "oversize", "selection_digest", "runtime_digest", "context_digest", "context_mismatch", "reject"])
def test_effect_review_rejects_invalid_wire_before_collaborators(monkeypatch, case):
    verify, kw = _case(monkeypatch)
    decision = kw["decision"]
    if case == "none":
        kw["decision"] = None
    elif case == "mapping_type":
        kw["decision"] = type("DecisionSubclass", (dict,), {})(decision)
    elif case == "missing":
        decision.pop("signature")
    elif case == "extra":
        decision["approved"] = True
    elif case == "oversize":
        decision.update(decision_id="d" * 4096, signature="s" * 4096)
        assert len(_json(decision).encode()) > 8192
    else:
        changes = {"legacy": ("schema_version", "reddog_elevated_authority_reviewer_decision.v1"),
            "unknown_schema": ("schema_version", "effect.v2"), "empty": ("signature", ""),
            "non_ascii": ("decision_id", "\u00e9"), "non_string": ("decision_id", 1), "long_field": ("decision_id", "d" * 4097),
            "selection_digest": ("model_selection_digest", "sha256:bad"), "runtime_digest": ("model_runtime_binding_digest", "sha256:bad"),
            "context_digest": ("consensus_context_digest", "sha256:bad"),
            "context_mismatch": ("consensus_context_digest", "sha256:" + "0" * 64), "reject": ("decision", "REJECT")}
        field, value = changes[case]
        decision[field] = value
    _check(verify, kw, False, early=True)


@pytest.mark.parametrize("case", ["false", "truthy", "exception", "signature", "preimage"])
def test_effect_review_requires_actual_exact_true_signature_result(monkeypatch, case):
    verify, kw = _case(monkeypatch)
    verifier = kw["signature_verifier"]
    verifier.value = {"false": False, "truthy": 1, "exception": True, "signature": "bound", "preimage": "bound"}[case]
    verifier.error = case == "exception"
    if case in {"signature", "preimage"}:
        kw["decision"]["signature" if case == "signature" else "decision_id"] = "altered"
    _check(verify, kw, False)
    assert verifier.calls == [("inert-reviewer-key", _preimage(kw["decision"]), kw["decision"]["signature"])]


def test_effect_review_preserves_legacy_decoder_and_signing_domain(monkeypatch):
    _, kw = _case(monkeypatch)
    from modules.communication.moltbot_bridge.src import reddog_elevated_authority_consensus_rehydration as wire
    from modules.communication.moltbot_bridge.src import reddog_elevated_authority_consensus_contract as contract
    effect = kw["decision"]
    with pytest.raises(ValueError):
        wire._rehydrate_decision(effect)
    legacy = dict(effect, schema_version="reddog_elevated_authority_reviewer_decision.v1")
    parsed = wire._rehydrate_decision(legacy)
    expected = "reddog-elevated-consensus-review.v1." + _json({k: v for k, v in legacy.items() if k != "signature"})
    assert parsed.to_dict() == legacy
    assert contract.canonical_reviewer_decision_signing_input(parsed) == expected
    assert expected != _preimage(effect)
    from modules.communication.moltbot_bridge.src import reddog_elevated_authority_consensus_reviewer_evidence as evidence
    key, runtime = evidence._verified_decision_evidence(
        parsed, legacy["consensus_context_digest"], kw["signature_verifier"],
        kw["reviewer_key_resolver"], kw["runtime_evidence_resolver"], kw["now"], frozenset(),
    )
    assert key is kw["reviewer_key_resolver"].value
    assert runtime is kw["runtime_evidence_resolver"].value
    assert kw["signature_verifier"].calls == [("inert-reviewer-key", expected, legacy["signature"])]
