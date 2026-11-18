"""Tests for Independent Repair Verifier & Context Firewall.

Governed by WSP_00, WSP_50, WSP_80, WSP_97 (Issue #1522 / Slice 2).
"""

import pytest

from modules.ai_intelligence.ai_gateway.src.independent_repair_verifier import (
    IndependenceTier,
    IndependentVerifierReceipt,
    ModelIndependencePolicy,
    VerifierContextFirewall,
    VerifierDisposition,
    VerifierEvidencePacket,
)
from modules.infrastructure.wre_core.src.repair_operation_contract import (
    CounterexampleReceipt,
)


def test_verifier_context_firewall_strips_persuasive_narrative() -> None:
    """Proves that builder thoughts, self-assessments, and persuasive phrases are strictly stripped."""
    raw_pain = "FastMCP auth fails open. Model A believes this is due to missing check."
    raw_outcome = "FastMCP fails closed. <thought>I am confident this is optimal</thought>"
    research = ["FastMCP 0.4.x docs. Model A concluded this resolves it."]

    packet = VerifierContextFirewall.project_evidence_packet(
        pain=raw_pain,
        desired_outcome=raw_outcome,
        baseline_receipt_id="sha256:11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
        candidate_diff="diff --git a/file.py b/file.py...",
        changed_files=["file.py"],
        research_evidence=research,
    )

    assert isinstance(packet, VerifierEvidencePacket)
    assert "Model A believes" not in packet.pain
    assert "<thought>" not in packet.desired_outcome
    assert "Model A concluded" not in packet.research_evidence[0]
    assert packet.builder_identity == "builder_model_a"


def test_verifier_context_firewall_enforces_pure_allowlist_signature() -> None:
    """Proves unallowlisted builder scratchpad/rationale kwargs are rejected at call boundary."""
    with pytest.raises(TypeError):
        VerifierContextFirewall.project_evidence_packet(  # type: ignore[call-arg]
            pain="Auth fails open",
            desired_outcome="Auth fails closed",
            baseline_receipt_id="sha256:" + "1" * 64,
            candidate_diff="diff --git a/x.py b/x.py",
            changed_files=["x.py"],
            builder_scratchpad="Trust me, this works",
        )


def test_model_independence_policy_enforcement() -> None:
    """Proves that identical builder/verifier identities are blocked and risk tiers enforce family separation."""
    admitted, _tier, _reason = ModelIndependencePolicy.evaluate_independence(
        builder_identity="qwen-coder-7b",
        verifier_identity="qwen-coder-7b",
    )
    assert admitted is False

    admitted, tier, _reason = ModelIndependencePolicy.evaluate_independence(
        builder_identity="qwen-coder-7b",
        verifier_identity="gemma-270m",
        risk_tier="HIGH",
    )
    assert admitted is True
    assert tier == IndependenceTier.DIFFERENT_MODEL_FAMILY

    admitted, tier, _reason = ModelIndependencePolicy.evaluate_independence(
        builder_identity="qwen-coder-7b",
        verifier_identity="qwen-coder-14b",
        risk_tier="STANDARD",
    )
    assert admitted is True
    assert tier == IndependenceTier.SAME_FAMILY_SEPARATE_SESSION

    admitted, _tier, _reason = ModelIndependencePolicy.evaluate_independence(
        builder_identity="qwen-coder-7b",
        verifier_identity="qwen-coder-14b",
        risk_tier="HIGH",
    )
    assert admitted is False


def test_independent_verifier_receipt_accept_and_integrity() -> None:
    """Proves IndependentVerifierReceipt verifies canonical digest and detects tampering."""
    receipt = IndependentVerifierReceipt.create(
        receipt_id="vr-001",
        operation_id="op-001",
        disposition=VerifierDisposition.ACCEPT,
        verifier_identity="gemma-270m",
        builder_identity="qwen-coder-7b",
        independence_tier=IndependenceTier.DIFFERENT_MODEL_FAMILY,
        evidence_summary="All 11 unit tests passed with no regression in error handling boundary.",
    )

    assert receipt.verify_integrity() is True
    assert receipt.disposition == VerifierDisposition.ACCEPT

    tampered = IndependentVerifierReceipt(
        schema_version=receipt.schema_version,
        receipt_id=receipt.receipt_id,
        operation_id=receipt.operation_id,
        disposition=VerifierDisposition.REJECT,
        verifier_identity=receipt.verifier_identity,
        builder_identity=receipt.builder_identity,
        independence_tier=receipt.independence_tier,
        evidence_summary=receipt.evidence_summary,
        counterexample=receipt.counterexample,
        missing_evidence=receipt.missing_evidence,
        evaluated_at=receipt.evaluated_at,
        receipt_digest=receipt.receipt_digest,
    )
    assert tampered.verify_integrity() is False


def test_independent_verifier_receipt_rejection_with_counterexample() -> None:
    """Proves rejection emits a structured CounterexampleReceipt."""
    ce = CounterexampleReceipt.create(
        objection_id="obj-101",
        category="regression",
        claim="Missing token on WebSocket endpoint fails open.",
        evidence="WebSocket handler lacks Authorization header check.",
        requested_test="test_websocket_missing_auth",
    )

    receipt = IndependentVerifierReceipt.create(
        receipt_id="vr-002",
        operation_id="op-002",
        disposition=VerifierDisposition.REJECT,
        verifier_identity="deepseek-coder",
        builder_identity="qwen-coder-7b",
        independence_tier=IndependenceTier.DIFFERENT_MODEL_FAMILY,
        evidence_summary="Candidate diff fails on WebSocket transport.",
        counterexample=ce,
    )

    assert receipt.verify_integrity() is True
    assert receipt.disposition == VerifierDisposition.REJECT
    assert receipt.counterexample is not None
    assert receipt.counterexample.objection_id == "obj-101"
