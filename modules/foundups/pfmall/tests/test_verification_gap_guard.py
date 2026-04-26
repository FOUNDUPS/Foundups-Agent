#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for VerificationGapGuard — Policy Enforcement for Protected Decisions

Verifies:
  - Protected classes require human review
  - Allowed actions are not blocked
  - Blocked actions return BlockedActionResult with truthful reason
  - Local/browser AI cannot perform protected actions
  - Evidence refs are preserved
  - WSP 97 reason_human explains blocked actions truthfully
  - No payout/CABR/finality claims exist

WSP 97 TRUTH BOUNDARIES:
  - Tests verify policy enforcement, NOT fraud detection
  - Tests verify blocking, NOT punishment
  - Tests verify evidence preservation, NOT evidence judgment
"""

import unittest
from datetime import datetime, timezone

from modules.foundups.pfmall.verification_gap_guard import (
    ALLOWED_ACTIONS,
    BLOCKED_ACTIONS,
    LOCAL_AI_SOURCES,
    AgentAction,
    AnomalyType,
    BlockedActionResult,
    ProtectedClass,
    VerificationGapEvent,
    block_protected_action,
    create_gap_event,
    is_protected_action,
    requires_human_review,
)


class TestProtectedClasses(unittest.TestCase):
    """Verify protected decision classes require human review."""

    def test_all_protected_classes_exist(self):
        """Contract defines 10 protected classes."""
        expected = {
            "fraud_accusation",
            "scam_accusation",
            "deepfake_accusation",
            "reward_denial",
            "reputation_impact",
            "legal_exposure",
            "identity_risk",
            "trust_ledger_publication",
            "wallet_action",
            "payout_finality",
        }
        actual = {pc.value for pc in ProtectedClass}
        self.assertEqual(actual, expected)

    def test_protected_class_events_require_human_review(self):
        """All protected class events require human review."""
        for pc in ProtectedClass:
            event = create_gap_event(
                foundup_id="test-foundup",
                tenant_id="test-tenant",
                anomaly_type=AnomalyType.PATTERN_MISMATCH,
                risk_class=pc,
            )
            self.assertTrue(
                requires_human_review(event),
                f"Protected class {pc.value} must require human review",
            )

    def test_event_requires_human_review_flag_true_for_protected(self):
        """VerificationGapEvent.requires_human_review is True for protected classes."""
        for pc in ProtectedClass:
            event = VerificationGapEvent(
                foundup_id="test",
                tenant_id="test",
                anomaly_type=AnomalyType.CONTENT_FLAG,
                risk_class=pc,
            )
            self.assertTrue(event.requires_human_review)


class TestAgentActions(unittest.TestCase):
    """Verify allowed vs blocked action boundaries."""

    def test_allowed_actions_set(self):
        """Contract defines 7 allowed actions."""
        expected = {
            AgentAction.SURFACE_ANOMALY,
            AgentAction.SUMMARIZE_EVIDENCE,
            AgentAction.OPEN_PANEL,
            AgentAction.REQUEST_REVIEW,
            AgentAction.COMPUTE_CONFIDENCE,
            AgentAction.LOG_AUDIT,
            AgentAction.NOTIFY_REDDOG,
        }
        self.assertEqual(ALLOWED_ACTIONS, expected)

    def test_blocked_actions_set(self):
        """Contract defines 7 blocked actions."""
        expected = {
            AgentAction.DENY_REWARD,
            AgentAction.PUBLISH_ACCUSATION,
            AgentAction.WRITE_TRUST_LEDGER,
            AgentAction.EXECUTE_PAYOUT,
            AgentAction.FINALIZE_REPUTATION,
            AgentAction.TRIGGER_LEGAL,
            AgentAction.SUSPEND_IDENTITY,
        }
        self.assertEqual(BLOCKED_ACTIONS, expected)

    def test_allowed_and_blocked_are_disjoint(self):
        """Allowed and blocked action sets must not overlap."""
        overlap = ALLOWED_ACTIONS & BLOCKED_ACTIONS
        self.assertEqual(overlap, set())

    def test_all_actions_are_categorized(self):
        """Every AgentAction must be in allowed or blocked set."""
        all_actions = set(AgentAction)
        categorized = ALLOWED_ACTIONS | BLOCKED_ACTIONS
        self.assertEqual(all_actions, categorized)


class TestIsProtectedAction(unittest.TestCase):
    """Verify is_protected_action() correctly identifies blocked actions."""

    def test_allowed_actions_are_not_protected(self):
        """Allowed actions should return False."""
        for action in ALLOWED_ACTIONS:
            self.assertFalse(
                is_protected_action(action),
                f"Allowed action {action.value} should not be protected",
            )

    def test_blocked_actions_are_protected(self):
        """Blocked actions should return True."""
        for action in BLOCKED_ACTIONS:
            self.assertTrue(
                is_protected_action(action),
                f"Blocked action {action.value} should be protected",
            )

    def test_string_action_names_work(self):
        """Function accepts string action names."""
        self.assertTrue(is_protected_action("deny_reward"))
        self.assertFalse(is_protected_action("surface_anomaly"))

    def test_unknown_action_is_protected(self):
        """Unknown actions are treated as protected (fail-safe)."""
        self.assertTrue(is_protected_action("unknown_action"))


class TestBlockProtectedAction(unittest.TestCase):
    """Verify block_protected_action() returns correct results."""

    def setUp(self):
        """Create a test event."""
        self.event = create_gap_event(
            foundup_id="test-foundup",
            tenant_id="test-tenant",
            anomaly_type=AnomalyType.PATTERN_MISMATCH,
            risk_class=ProtectedClass.FRAUD_ACCUSATION,
        )

    def test_allowed_actions_not_blocked(self):
        """Allowed actions should return blocked=False."""
        for action in ALLOWED_ACTIONS:
            result = block_protected_action(self.event, action)
            self.assertFalse(
                result.blocked,
                f"Allowed action {action.value} should not be blocked",
            )
            self.assertEqual(result.reason_code, "ACTION_ALLOWED")

    def test_blocked_actions_are_blocked(self):
        """Blocked actions should return blocked=True."""
        for action in BLOCKED_ACTIONS:
            result = block_protected_action(self.event, action)
            self.assertTrue(
                result.blocked,
                f"Blocked action {action.value} should be blocked",
            )
            self.assertTrue(result.requires_human_review)

    def test_blocked_result_has_truthful_reason(self):
        """WSP 97: reason_human must explain why action was blocked."""
        result = block_protected_action(self.event, AgentAction.DENY_REWARD)

        self.assertIn("blocked", result.reason_human.lower())
        self.assertIn("human review", result.reason_human.lower())
        self.assertIn("fraud_accusation", result.reason_code.lower())

    def test_blocked_result_suggests_request_review(self):
        """Blocked actions should suggest routing to human review."""
        result = block_protected_action(self.event, AgentAction.EXECUTE_PAYOUT)
        self.assertEqual(result.suggested_action, "request_review")

    def test_string_action_names_work(self):
        """Function accepts string action names."""
        result = block_protected_action(self.event, "deny_reward")
        self.assertTrue(result.blocked)

        result = block_protected_action(self.event, "surface_anomaly")
        self.assertFalse(result.blocked)

    def test_unknown_action_is_blocked(self):
        """Unknown actions are blocked with UNKNOWN_ACTION reason."""
        result = block_protected_action(self.event, "totally_fake_action")
        self.assertTrue(result.blocked)
        self.assertEqual(result.reason_code, "UNKNOWN_ACTION")


class TestLocalAIBoundary(unittest.TestCase):
    """Verify browser/local AI sources are advisory only."""

    def test_local_ai_sources_defined(self):
        """Contract defines local AI source identifiers."""
        expected = {"local_gemma", "browser_gemma", "webgpu_gemma", "on_device", "local_model"}
        self.assertEqual(LOCAL_AI_SOURCES, expected)

    def test_local_ai_event_requires_review(self):
        """Events from local AI always require human review."""
        for source in LOCAL_AI_SOURCES:
            event = create_gap_event(
                foundup_id="test",
                tenant_id="test",
                anomaly_type=AnomalyType.CONTENT_FLAG,
                risk_class=ProtectedClass.SCAM_ACCUSATION,
                source_panel=source,
            )
            self.assertTrue(
                requires_human_review(event),
                f"Local AI source '{source}' must require human review",
            )
            self.assertTrue(event.is_from_local_ai())

    def test_local_ai_cannot_perform_protected_actions(self):
        """Local AI sources are blocked from protected actions with specific reason."""
        event = create_gap_event(
            foundup_id="test",
            tenant_id="test",
            anomaly_type=AnomalyType.PATTERN_MISMATCH,
            risk_class=ProtectedClass.REWARD_DENIAL,
            source_panel="local_gemma",
        )

        result = block_protected_action(event, AgentAction.DENY_REWARD)

        self.assertTrue(result.blocked)
        self.assertEqual(result.reason_code, "LOCAL_AI_ADVISORY_ONLY")
        self.assertIn("advisory only", result.reason_human.lower())
        self.assertIn("local", result.reason_human.lower())

    def test_server_side_agent_not_flagged_as_local(self):
        """Server-side agents are not flagged as local AI."""
        event = create_gap_event(
            foundup_id="test",
            tenant_id="test",
            anomaly_type=AnomalyType.VELOCITY_ANOMALY,
            risk_class=ProtectedClass.IDENTITY_RISK,
            source_panel="agent_surface",
        )
        self.assertFalse(event.is_from_local_ai())


class TestEvidencePreservation(unittest.TestCase):
    """Verify evidence refs are preserved through the guard."""

    def test_evidence_refs_preserved_in_event(self):
        """Evidence refs passed to factory are preserved."""
        refs = ["artifact_001", "artifact_002", "screenshot_003"]
        event = create_gap_event(
            foundup_id="test",
            tenant_id="test",
            anomaly_type=AnomalyType.EVIDENCE_INCOMPLETE,
            risk_class=ProtectedClass.LEGAL_EXPOSURE,
            evidence_refs=refs,
        )
        self.assertEqual(event.evidence_refs, refs)

    def test_evidence_refs_in_serialized_dict(self):
        """Evidence refs appear in serialized output."""
        refs = ["ref_a", "ref_b"]
        event = create_gap_event(
            foundup_id="test",
            tenant_id="test",
            anomaly_type=AnomalyType.EXTERNAL_REPORT,
            risk_class=ProtectedClass.TRUST_LEDGER_PUBLICATION,
            evidence_refs=refs,
        )
        d = event.to_dict()
        self.assertEqual(d["evidence_refs"], refs)

    def test_evidence_summary_preserved(self):
        """Evidence summary is preserved."""
        summary = "3 of 5 validators flagged this submission"
        event = create_gap_event(
            foundup_id="test",
            tenant_id="test",
            anomaly_type=AnomalyType.DUPLICATE_SUBMISSION,
            risk_class=ProtectedClass.REPUTATION_IMPACT,
            evidence_summary=summary,
        )
        self.assertEqual(event.evidence_summary, summary)
        self.assertEqual(event.to_dict()["evidence_summary"], summary)


class TestWSP97TruthBoundaries(unittest.TestCase):
    """Verify WSP 97 truth boundaries are maintained."""

    def test_no_cabr_ready_claim(self):
        """Events must NOT claim cabr_ready status."""
        event = create_gap_event(
            foundup_id="test",
            tenant_id="test",
            anomaly_type=AnomalyType.PATTERN_MISMATCH,
            risk_class=ProtectedClass.PAYOUT_FINALITY,
        )
        d = event.to_dict()
        self.assertNotIn("cabr_ready", d)

    def test_no_payout_ready_claim(self):
        """Events must NOT claim payout_ready status."""
        event = create_gap_event(
            foundup_id="test",
            tenant_id="test",
            anomaly_type=AnomalyType.CONFIDENCE_BELOW_THRESHOLD,
            risk_class=ProtectedClass.WALLET_ACTION,
        )
        d = event.to_dict()
        self.assertNotIn("payout_ready", d)

    def test_no_verification_complete_claim(self):
        """Events must NOT claim verification_complete status."""
        event = create_gap_event(
            foundup_id="test",
            tenant_id="test",
            anomaly_type=AnomalyType.IDENTITY_MISMATCH,
            risk_class=ProtectedClass.DEEPFAKE_ACCUSATION,
        )
        d = event.to_dict()
        self.assertNotIn("verification_complete", d)

    def test_human_decision_fields_none_by_default(self):
        """Human decision fields must be None until human acts."""
        event = create_gap_event(
            foundup_id="test",
            tenant_id="test",
            anomaly_type=AnomalyType.CONTENT_FLAG,
            risk_class=ProtectedClass.FRAUD_ACCUSATION,
        )
        self.assertIsNone(event.human_reviewer_id)
        self.assertIsNone(event.human_decision)
        self.assertIsNone(event.human_decision_at)
        self.assertIsNone(event.human_decision_reason)

    def test_blocked_result_does_not_claim_action_executed(self):
        """BlockedActionResult must not claim the action was executed."""
        event = create_gap_event(
            foundup_id="test",
            tenant_id="test",
            anomaly_type=AnomalyType.VELOCITY_ANOMALY,
            risk_class=ProtectedClass.REWARD_DENIAL,
        )
        result = block_protected_action(event, AgentAction.DENY_REWARD)

        self.assertTrue(result.blocked)
        # The reason should explain blocking, not execution
        self.assertNotIn("denied", result.reason_human.lower())
        self.assertNotIn("executed", result.reason_human.lower())
        self.assertIn("blocked", result.reason_human.lower())


class TestEventSerialization(unittest.TestCase):
    """Verify event serialization is correct."""

    def test_event_id_is_deterministic(self):
        """Event ID is deterministic from identity fields."""
        event1 = VerificationGapEvent(
            foundup_id="fp-001",
            tenant_id="t-001",
            anomaly_type=AnomalyType.PATTERN_MISMATCH,
            risk_class=ProtectedClass.FRAUD_ACCUSATION,
            created_at=datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc),
        )
        event2 = VerificationGapEvent(
            foundup_id="fp-001",
            tenant_id="t-001",
            anomaly_type=AnomalyType.PATTERN_MISMATCH,
            risk_class=ProtectedClass.FRAUD_ACCUSATION,
            created_at=datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(event1.event_id, event2.event_id)

    def test_event_id_is_16_chars(self):
        """Event ID is 16 character hex string."""
        event = create_gap_event(
            foundup_id="test",
            tenant_id="test",
            anomaly_type=AnomalyType.CONTENT_FLAG,
            risk_class=ProtectedClass.SCAM_ACCUSATION,
        )
        self.assertEqual(len(event.event_id), 16)
        # Verify it's hex
        int(event.event_id, 16)

    def test_to_dict_includes_all_fields(self):
        """to_dict() includes all required fields."""
        event = create_gap_event(
            foundup_id="fp-test",
            tenant_id="t-test",
            anomaly_type=AnomalyType.DUPLICATE_SUBMISSION,
            risk_class=ProtectedClass.REPUTATION_IMPACT,
            confidence=0.87,
        )
        d = event.to_dict()

        required_fields = {
            "event_id", "foundup_id", "tenant_id", "source_panel",
            "anomaly_type", "risk_class", "confidence", "evidence_refs",
            "requires_human_review", "allowed_agent_actions",
            "blocked_agent_actions", "created_at", "updated_at",
        }
        for field in required_fields:
            self.assertIn(field, d, f"Missing required field: {field}")

    def test_blocked_result_to_dict(self):
        """BlockedActionResult.to_dict() serializes correctly."""
        result = BlockedActionResult(
            blocked=True,
            action=AgentAction.DENY_REWARD,
            reason_code="PROTECTED_CLASS_REWARD_DENIAL",
            reason_human="Action blocked for testing.",
            event_id="abc123",
        )
        d = result.to_dict()

        self.assertEqual(d["blocked"], True)
        self.assertEqual(d["action"], "deny_reward")
        self.assertEqual(d["reason_code"], "PROTECTED_CLASS_REWARD_DENIAL")
        self.assertEqual(d["event_id"], "abc123")


if __name__ == "__main__":
    unittest.main(verbosity=2)
