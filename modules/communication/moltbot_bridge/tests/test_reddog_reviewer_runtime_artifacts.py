"""Current-review composition: real review signatures, synthetic model evidence.

Owner/lease seams are inert; model signatures use the existing deterministic
fixture verifier. No production enrollment, reviewer execution or permit proof.
"""

from dataclasses import replace

import pytest

from modules.ai_intelligence.ai_gateway.tests import model_signed_evidence_test_helpers as signed
from modules.communication.moltbot_bridge.src import reddog_model_runtime_verifier_bootstrap as owner
from modules.communication.moltbot_bridge.tests import model_runtime_binding_receipt_test_helpers as models
from modules.communication.moltbot_bridge.tests.reddog_reviewer_authority_test_support import sign
from modules.communication.moltbot_bridge.tests.reddog_reviewer_quorum_test_support import (
    closed, quorum_setup, reset,
)


def case(monkeypatch, tmp_path):
    record_type = getattr(owner, "ReviewerRuntimeArtifacts", None)
    resolver_type = getattr(owner, "ModelRuntimeReviewerEvidenceResolver", None)
    assert record_type and resolver_type, "verified reviewer runtime adapter missing"
    verify, state = quorum_setup(monkeypatch, tmp_path)
    monkeypatch.setattr(signed, "NOW", state.now)
    records = {}
    for decision, key in zip(state.call["decisions"], (state.reviewer, state.second_key)):
        selection, binding = models.model_selection_and_runtime_binding_receipts(
            runtime_surface="effect-reviewer-test", model_id=decision["reviewer_model_id"],
            verified_at_epoch=state.now,
        )
        receipt = models.verified_runtime_binding_receipt(binding)
        verifier = replace(models.model_runtime_binding_test_verifier(binding), trusted_now_epoch=lambda: state.now)
        decision.update(model_selection_receipt_id=receipt.selection_receipt_id,
            model_selection_digest=receipt.selection_receipt_digest,
            model_runtime_binding_receipt_id=receipt.runtime_binding_receipt_id,
            model_runtime_binding_digest=receipt.runtime_binding_digest)
        sign(decision, key, "reddog-effect-consensus-review.v1.")
        records[decision["reviewer_principal_id"]] = record_type(
            decision["reviewer_model_id"], selection, binding, verifier)
    state.artifacts = records
    state.call["runtime_evidence_resolver"] = resolver_type(records)
    return verify, state


def test_current_quorum_consumes_exact_verified_capabilities(monkeypatch, tmp_path):
    verify, state = case(monkeypatch, tmp_path)
    consume = owner.consume_verified_runtime_binding_capability
    observed = []

    def observe(capability, **kwargs):
        assert state.lease.active
        result = consume(capability, **kwargs)
        assert result is not None
        assert consume(capability, **kwargs) is None
        observed.append(result)
        return result

    monkeypatch.setattr(owner, "consume_verified_runtime_binding_capability", observe)
    assert verify(**state.call) is True
    assert len(observed) == 2
    assert [r.runtime_binding_receipt_id for r in observed] == [
        d["model_runtime_binding_receipt_id"] for d in state.call["decisions"]]
    closed(state)


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("fault", ["selection", "binding", "signature", "model", "lookup", "verifier"])
def test_current_quorum_rejects_invalid_model_artifacts(monkeypatch, tmp_path, index, fault):
    verify, state = case(monkeypatch, tmp_path)
    decision = state.call["decisions"][index]
    principal = decision["reviewer_principal_id"]
    record = state.artifacts[principal]
    if fault == "selection":
        record.selection["receipt_id"] = "forged-selection"
    elif fault == "binding":
        record.binding["verification_receipt"]["runtime_binding_digest"] = "sha256:" + "0" * 64
    elif fault == "signature":
        record.verifier.verified_evidence_bundle["entries"][0]["benchmark_signature_receipt"]["signature"] = "forged"
    elif fault == "model":
        state.artifacts[principal] = replace(record, model_id="unqualified-model")
    elif fault == "lookup":
        decision["model_selection_receipt_id"] = "unbound-selection"
        sign(decision, (state.reviewer, state.second_key)[index], "reddog-effect-consensus-review.v1.")
    else:
        state.artifacts[principal] = replace(record, verifier=object())
    state.call["runtime_evidence_resolver"] = owner.ModelRuntimeReviewerEvidenceResolver(state.artifacts)
    assert verify(**state.call) is False
    closed(state)


def test_artifacts_are_reverified_on_later_invocation(monkeypatch, tmp_path):
    verify, state = case(monkeypatch, tmp_path)
    assert verify(**state.call) is True
    reset(state)
    assert verify(**state.call) is True
    reset(state)
    record = next(iter(state.artifacts.values()))
    record.verifier.verified_evidence_bundle["entries"][0]["promotion_signature_receipt"]["signature"] = "forged"
    assert verify(**state.call) is False
    closed(state)


def test_missing_expired_and_mismatched_artifact_queries(monkeypatch, tmp_path):
    _, state = case(monkeypatch, tmp_path)
    resolver = state.call["runtime_evidence_resolver"]
    decision = state.call["decisions"][0]
    args = (decision["reviewer_principal_id"], decision["model_selection_receipt_id"],
            decision["model_runtime_binding_receipt_id"])
    assert resolver.resolve(*args) is not None
    for bad in (("unknown", *args[1:]), (args[0], "wrong", args[2]), (*args[:2], "wrong")):
        assert resolver.resolve(*bad) is None
    state.now = 4600
    assert resolver.resolve(*args) is None


def test_structural_receipt_without_registered_capability_is_rejected(monkeypatch, tmp_path):
    _, state = case(monkeypatch, tmp_path)
    resolver = state.call["runtime_evidence_resolver"]
    decision = state.call["decisions"][0]
    monkeypatch.setattr(owner, "consume_verified_runtime_binding_capability", lambda *a, **kw: None)
    assert resolver.resolve(decision["reviewer_principal_id"], decision["model_selection_receipt_id"],
        decision["model_runtime_binding_receipt_id"]) is None


def test_runtime_record_limit_and_missing_records(monkeypatch, tmp_path):
    _, state = case(monkeypatch, tmp_path)
    record = next(iter(state.artifacts.values()))
    with pytest.raises(ValueError):
        owner.ModelRuntimeReviewerEvidenceResolver({str(i): record for i in range(9)})
    assert owner.ModelRuntimeReviewerEvidenceResolver({}).resolve("a", "b", "c") is None


def test_signed_model_claim_must_match_verified_membership(monkeypatch, tmp_path):
    verify, state = case(monkeypatch, tmp_path)
    decision = state.call["decisions"][0]
    decision["reviewer_model_id"] = "another-model"
    sign(decision, state.reviewer, "reddog-effect-consensus-review.v1.")
    assert verify(**state.call) is False
    closed(state)


@pytest.mark.parametrize("clock", [(True,), (1000.0,), (999,), (1000, 1000, 999), (1000, 1000, 4600)])
def test_runtime_evidence_requires_valid_monotonic_clock(monkeypatch, tmp_path, clock):
    _, state = case(monkeypatch, tmp_path)
    decision = state.call["decisions"][0]
    principal = decision["reviewer_principal_id"]
    record = state.artifacts[principal]
    ticks = iter(clock)
    state.artifacts[principal] = replace(record, verifier=replace(record.verifier, trusted_now_epoch=lambda: next(ticks)))
    resolver = owner.ModelRuntimeReviewerEvidenceResolver(state.artifacts)
    assert resolver.resolve(principal, decision["model_selection_receipt_id"], decision["model_runtime_binding_receipt_id"]) is None


def test_consumer_exception_discards_registered_capability(monkeypatch, tmp_path):
    _, state = case(monkeypatch, tmp_path)
    resolver = state.call["runtime_evidence_resolver"]
    decision = state.call["decisions"][0]
    consume, captured = owner.consume_verified_runtime_binding_capability, []

    def fail(capability, **kwargs):
        captured.append((capability, kwargs))
        raise RuntimeError("test-only consumer failure")

    monkeypatch.setattr(owner, "consume_verified_runtime_binding_capability", fail)
    assert resolver.resolve(decision["reviewer_principal_id"], decision["model_selection_receipt_id"],
        decision["model_runtime_binding_receipt_id"]) is None
    assert len(captured) == 1
    assert consume(captured[0][0], **captured[0][1]) is None
