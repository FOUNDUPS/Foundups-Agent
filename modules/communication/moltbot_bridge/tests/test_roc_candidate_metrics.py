#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for ROC Candidate Metrics -- Observability-Only Counter

Validates:
  - Empty input count = 0
  - Accepted-for-review candidate increments count
  - Rejected record does not increment
  - Pending quorum does not increment
  - Malformed record counted as anomaly
  - Missing evidence does not infer candidacy
  - All required WSP 97 labels present
  - Forbidden consumers present
  - Export JSON deterministic
  - Pure function / no filesystem writes
  - No state mutation
  - No payout readiness inferred
  - No DAO activation inferred
  - No CABR readiness inferred

WSP Compliance:
  WSP 91  : Observability testing
  WSP 97  : Truth boundary verification

Slice: ROC_CANDIDATE_METRIC_IMPL_PHASE1
Worker: W1
"""

import json
import pytest
from datetime import datetime, timezone
from typing import Dict, Any, List

from modules.communication.moltbot_bridge.src.roc_candidate_metrics import (
    ROCCandidateMetricInput,
    ROCCandidateMetricSnapshot,
    count_roc_candidates,
    export_roc_candidate_metric_json,
    export_roc_candidate_metric_markdown,
    WSP97_REQUIRED_LABELS,
    FORBIDDEN_CONSUMERS,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def _make_candidate_record(
    record_id: str = "rec_001",
    tenant_id: str = "tenant_001",
    **overrides: Any,
) -> Dict[str, Any]:
    """Create a record that meets ROC_CANDIDATE criteria."""
    record = {
        "record_id": record_id,
        "tenant_id": tenant_id,
        "decision": "accepted_for_review",
        "quorum_met": True,
        "threshold_met": True,
        "evidence_present": True,
        "verification_complete": False,
        "cabr_ready": False,
        "payout_ready": False,
    }
    record.update(overrides)
    return record


def _make_rejected_record(
    record_id: str = "rec_002",
    tenant_id: str = "tenant_001",
) -> Dict[str, Any]:
    """Create a rejected record."""
    return {
        "record_id": record_id,
        "tenant_id": tenant_id,
        "decision": "rejected",
        "quorum_met": False,
        "threshold_met": False,
        "evidence_present": False,
        "verification_complete": False,
        "cabr_ready": False,
        "payout_ready": False,
    }


def _make_pending_quorum_record(
    record_id: str = "rec_003",
    tenant_id: str = "tenant_001",
) -> Dict[str, Any]:
    """Create a pending quorum record."""
    return {
        "record_id": record_id,
        "tenant_id": tenant_id,
        "decision": "pending_quorum",
        "quorum_met": False,
        "threshold_met": False,
        "evidence_present": True,
        "verification_complete": False,
        "cabr_ready": False,
        "payout_ready": False,
    }


# ---------------------------------------------------------------------------
# Basic Count Tests
# ---------------------------------------------------------------------------


class TestEmptyInput:
    """Test empty input handling."""

    def test_empty_list_returns_zero_count(self):
        """Empty list should return count = 0."""
        result = count_roc_candidates([])
        assert result.roc_candidate_count == 0
        assert result.total_records == 0
        assert result.anomaly_count == 0

    def test_empty_pipeline_result_returns_zero_count(self):
        """Empty pipeline result should return count = 0."""
        result = count_roc_candidates({"consensus_records": []})
        assert result.roc_candidate_count == 0
        assert result.total_records == 0

    def test_empty_metric_input_returns_zero_count(self):
        """Empty ROCCandidateMetricInput should return count = 0."""
        metric_input = ROCCandidateMetricInput(records=[])
        result = count_roc_candidates(metric_input)
        assert result.roc_candidate_count == 0


class TestCandidateCounting:
    """Test ROC_CANDIDATE counting logic."""

    def test_accepted_for_review_increments_count(self):
        """Record meeting all criteria should increment count."""
        records = [_make_candidate_record()]
        result = count_roc_candidates(records)
        assert result.roc_candidate_count == 1
        assert result.total_records == 1

    def test_multiple_candidates_counted(self):
        """Multiple qualifying records should all be counted."""
        records = [
            _make_candidate_record(record_id="rec_001"),
            _make_candidate_record(record_id="rec_002"),
            _make_candidate_record(record_id="rec_003"),
        ]
        result = count_roc_candidates(records)
        assert result.roc_candidate_count == 3

    def test_rejected_record_does_not_increment(self):
        """Rejected record should not increment candidate count."""
        records = [_make_rejected_record()]
        result = count_roc_candidates(records)
        assert result.roc_candidate_count == 0
        assert result.rejected_count == 1

    def test_pending_quorum_does_not_increment(self):
        """Pending quorum record should not increment candidate count."""
        records = [_make_pending_quorum_record()]
        result = count_roc_candidates(records)
        assert result.roc_candidate_count == 0
        assert result.pending_quorum_count == 1

    def test_mixed_records_counted_correctly(self):
        """Mixed records should be categorized correctly."""
        records = [
            _make_candidate_record(record_id="rec_001"),
            _make_rejected_record(record_id="rec_002"),
            _make_pending_quorum_record(record_id="rec_003"),
            _make_candidate_record(record_id="rec_004"),
        ]
        result = count_roc_candidates(records)
        assert result.roc_candidate_count == 2
        assert result.rejected_count == 1
        assert result.pending_quorum_count == 1
        assert result.total_records == 4


class TestCriteriaEnforcement:
    """Test that all ROC_CANDIDATE criteria are enforced."""

    def test_quorum_not_met_excludes_candidate(self):
        """Record with quorum_met=False should not be counted."""
        records = [_make_candidate_record(quorum_met=False)]
        result = count_roc_candidates(records)
        assert result.roc_candidate_count == 0

    def test_threshold_not_met_excludes_candidate(self):
        """Record with threshold_met=False should not be counted."""
        records = [_make_candidate_record(threshold_met=False)]
        result = count_roc_candidates(records)
        assert result.roc_candidate_count == 0

    def test_missing_evidence_does_not_infer_candidacy(self):
        """Record with evidence_present=False should not be counted."""
        records = [_make_candidate_record(evidence_present=False)]
        result = count_roc_candidates(records)
        assert result.roc_candidate_count == 0

    def test_verification_complete_true_excludes_candidate(self):
        """Record with verification_complete=True should not be counted."""
        records = [_make_candidate_record(verification_complete=True)]
        result = count_roc_candidates(records)
        assert result.roc_candidate_count == 0

    def test_cabr_ready_true_excludes_candidate(self):
        """Record with cabr_ready=True should not be counted."""
        records = [_make_candidate_record(cabr_ready=True)]
        result = count_roc_candidates(records)
        assert result.roc_candidate_count == 0

    def test_payout_ready_true_excludes_candidate(self):
        """Record with payout_ready=True should not be counted."""
        records = [_make_candidate_record(payout_ready=True)]
        result = count_roc_candidates(records)
        assert result.roc_candidate_count == 0

    def test_missing_quorum_met_field_excludes_candidate(self):
        """Record missing quorum_met field should not be counted."""
        record = _make_candidate_record()
        del record["quorum_met"]
        result = count_roc_candidates([record])
        assert result.roc_candidate_count == 0

    def test_missing_decision_field_is_anomaly(self):
        """Record missing decision field should be anomaly."""
        record = _make_candidate_record()
        del record["decision"]
        result = count_roc_candidates([record])
        assert result.roc_candidate_count == 0
        assert result.anomaly_count == 1


class TestAnomalyDetection:
    """Test anomaly detection for malformed records."""

    def test_malformed_record_counted_as_anomaly(self):
        """Malformed record should be counted as anomaly."""
        records = [{"invalid": "record"}]  # Missing record_id and decision
        result = count_roc_candidates(records)
        assert result.anomaly_count == 1
        assert result.roc_candidate_count == 0

    def test_missing_record_id_is_anomaly(self):
        """Record missing record_id should be anomaly."""
        record = _make_candidate_record()
        del record["record_id"]
        result = count_roc_candidates([record])
        assert result.anomaly_count == 1

    def test_invalid_decision_value_is_anomaly(self):
        """Record with invalid decision value should be anomaly."""
        record = _make_candidate_record(decision="invalid_decision")
        result = count_roc_candidates([record])
        assert result.anomaly_count == 1

    def test_non_dict_record_is_anomaly(self):
        """Non-dict record should be anomaly."""
        records = ["not_a_dict", 123, None]
        result = count_roc_candidates(records)
        assert result.anomaly_count == 3

    def test_anomaly_record_ids_captured(self):
        """Anomaly record IDs should be captured when requested."""
        records = [
            _make_candidate_record(record_id=""),  # Empty record_id = anomaly
            {"record_id": "bad_001", "decision": "invalid"},  # Invalid decision
        ]
        result = count_roc_candidates(records, include_record_ids=True)
        assert result.anomaly_count == 2
        assert "bad_001" in result.anomaly_record_ids


# ---------------------------------------------------------------------------
# WSP 97 Compliance Tests
# ---------------------------------------------------------------------------


class TestWSP97Labels:
    """Test WSP 97 required labels are present."""

    def test_all_required_wsp97_labels_present(self):
        """All required WSP 97 labels must be present."""
        result = count_roc_candidates([])
        assert set(WSP97_REQUIRED_LABELS).issubset(set(result.wsp97_labels))

    def test_observability_only_label_present(self):
        """OBSERVABILITY_ONLY label must be present."""
        result = count_roc_candidates([])
        assert "OBSERVABILITY_ONLY" in result.wsp97_labels

    def test_review_only_label_present(self):
        """REVIEW_ONLY label must be present."""
        result = count_roc_candidates([])
        assert "REVIEW_ONLY" in result.wsp97_labels

    def test_roc_candidate_only_label_present(self):
        """ROC_CANDIDATE_ONLY label must be present."""
        result = count_roc_candidates([])
        assert "ROC_CANDIDATE_ONLY" in result.wsp97_labels

    def test_not_roc_validated_label_present(self):
        """NOT_ROC_VALIDATED label must be present."""
        result = count_roc_candidates([])
        assert "NOT_ROC_VALIDATED" in result.wsp97_labels

    def test_not_cabr_ready_label_present(self):
        """NOT_CABR_READY label must be present."""
        result = count_roc_candidates([])
        assert "NOT_CABR_READY" in result.wsp97_labels

    def test_not_payout_ready_label_present(self):
        """NOT_PAYOUT_READY label must be present."""
        result = count_roc_candidates([])
        assert "NOT_PAYOUT_READY" in result.wsp97_labels

    def test_no_daemon_trigger_label_present(self):
        """NO_DAEMON_TRIGGER label must be present."""
        result = count_roc_candidates([])
        assert "NO_DAEMON_TRIGGER" in result.wsp97_labels


class TestForbiddenConsumers:
    """Test forbidden consumers are documented."""

    def test_forbidden_consumers_present(self):
        """Forbidden consumers list must be present."""
        result = count_roc_candidates([])
        assert len(result.forbidden_consumers) > 0

    def test_payout_engine_forbidden(self):
        """payout_engine must be forbidden."""
        result = count_roc_candidates([])
        assert "payout_engine" in result.forbidden_consumers

    def test_dao_transition_forbidden(self):
        """dao_transition must be forbidden."""
        result = count_roc_candidates([])
        assert "dao_transition" in result.forbidden_consumers

    def test_token_issuance_forbidden(self):
        """token_issuance must be forbidden."""
        result = count_roc_candidates([])
        assert "token_issuance" in result.forbidden_consumers

    def test_cabr_ready_gate_forbidden(self):
        """cabr_ready_gate must be forbidden."""
        result = count_roc_candidates([])
        assert "cabr_ready_gate" in result.forbidden_consumers


class TestTruthBoundaries:
    """Test truth boundary fields are always False."""

    def test_no_payout_readiness_inferred(self):
        """payout_ready must always be False."""
        records = [_make_candidate_record()]
        result = count_roc_candidates(records)
        assert result.payout_ready is False

    def test_no_cabr_readiness_inferred(self):
        """cabr_ready must always be False."""
        records = [_make_candidate_record()]
        result = count_roc_candidates(records)
        assert result.cabr_ready is False

    def test_no_roc_validated_inferred(self):
        """roc_validated must always be False."""
        records = [_make_candidate_record()]
        result = count_roc_candidates(records)
        assert result.roc_validated is False

    def test_no_dao_activation_inferred(self):
        """dao_activated must always be False."""
        records = [_make_candidate_record()]
        result = count_roc_candidates(records)
        assert result.dao_activated is False

    def test_no_dae_maturity_inferred(self):
        """dae_mature must always be False."""
        records = [_make_candidate_record()]
        result = count_roc_candidates(records)
        assert result.dae_mature is False


# ---------------------------------------------------------------------------
# Export Tests
# ---------------------------------------------------------------------------


class TestJSONExport:
    """Test JSON export functionality."""

    def test_export_json_deterministic(self):
        """JSON export should be deterministic (sorted keys)."""
        records = [_make_candidate_record()]
        result = count_roc_candidates(records)

        # Export twice and compare
        export1 = export_roc_candidate_metric_json(result)
        export2 = export_roc_candidate_metric_json(result)

        # Parse and compare (timestamps will differ but structure same)
        data1 = json.loads(export1)
        data2 = json.loads(export2)

        # Remove timestamp for comparison
        del data1["evaluated_at"]
        del data2["evaluated_at"]

        assert data1 == data2

    def test_export_json_contains_wsp97_labels(self):
        """JSON export should contain WSP 97 labels."""
        records = [_make_candidate_record()]
        result = count_roc_candidates(records)
        export = export_roc_candidate_metric_json(result)
        data = json.loads(export)

        assert "wsp97_labels" in data
        assert "OBSERVABILITY_ONLY" in data["wsp97_labels"]

    def test_export_json_contains_forbidden_consumers(self):
        """JSON export should contain forbidden consumers."""
        records = [_make_candidate_record()]
        result = count_roc_candidates(records)
        export = export_roc_candidate_metric_json(result)
        data = json.loads(export)

        assert "forbidden_consumers" in data
        assert "payout_engine" in data["forbidden_consumers"]

    def test_export_json_truth_boundaries_false(self):
        """JSON export should have all truth boundaries as False."""
        records = [_make_candidate_record()]
        result = count_roc_candidates(records)
        export = export_roc_candidate_metric_json(result)
        data = json.loads(export)

        assert data["roc_validated"] is False
        assert data["cabr_ready"] is False
        assert data["payout_ready"] is False
        assert data["dae_mature"] is False
        assert data["dao_activated"] is False


class TestMarkdownExport:
    """Test Markdown export functionality."""

    def test_export_markdown_contains_warning(self):
        """Markdown export should contain observability warning."""
        result = count_roc_candidates([])
        export = export_roc_candidate_metric_markdown(result)
        assert "OBSERVABILITY ONLY" in export

    def test_export_markdown_contains_wsp97_labels(self):
        """Markdown export should contain WSP 97 labels section."""
        result = count_roc_candidates([])
        export = export_roc_candidate_metric_markdown(result)
        assert "WSP 97 Labels" in export
        assert "OBSERVABILITY_ONLY" in export

    def test_export_markdown_contains_forbidden_consumers(self):
        """Markdown export should contain forbidden consumers section."""
        result = count_roc_candidates([])
        export = export_roc_candidate_metric_markdown(result)
        assert "Forbidden Consumers" in export
        assert "payout_engine" in export


# ---------------------------------------------------------------------------
# Pure Function Tests
# ---------------------------------------------------------------------------


class TestPureFunctionBehavior:
    """Test that count_roc_candidates is a pure function."""

    def test_no_state_mutation(self):
        """Function should not mutate input."""
        records = [_make_candidate_record()]
        original = json.dumps(records)

        count_roc_candidates(records)

        assert json.dumps(records) == original

    def test_multiple_calls_same_result(self):
        """Multiple calls with same input should give same result (except timestamps)."""
        records = [_make_candidate_record()]

        result1 = count_roc_candidates(records)
        result2 = count_roc_candidates(records)

        assert result1.roc_candidate_count == result2.roc_candidate_count
        assert result1.total_records == result2.total_records
        assert result1.wsp97_labels == result2.wsp97_labels


# ---------------------------------------------------------------------------
# Input Type Tests
# ---------------------------------------------------------------------------


class TestInputTypes:
    """Test different input type handling."""

    def test_accepts_list_of_records(self):
        """Function should accept list of record dicts."""
        records = [_make_candidate_record()]
        result = count_roc_candidates(records)
        assert result.roc_candidate_count == 1

    def test_accepts_pipeline_result_dict(self):
        """Function should accept pipeline result dict."""
        pipeline_result = {
            "consensus_records": [_make_candidate_record()],
            "success": True,
        }
        result = count_roc_candidates(pipeline_result)
        assert result.roc_candidate_count == 1

    def test_accepts_metric_input_object(self):
        """Function should accept ROCCandidateMetricInput object."""
        metric_input = ROCCandidateMetricInput(
            records=[_make_candidate_record()]
        )
        result = count_roc_candidates(metric_input)
        assert result.roc_candidate_count == 1

    def test_metric_input_with_pipeline_result(self):
        """ROCCandidateMetricInput should extract from pipeline_result."""
        metric_input = ROCCandidateMetricInput(
            pipeline_result={"consensus_records": [_make_candidate_record()]}
        )
        result = count_roc_candidates(metric_input)
        assert result.roc_candidate_count == 1


class TestTenantFiltering:
    """Test tenant filtering functionality."""

    def test_tenant_filter_applies(self):
        """Tenant filter should limit counts to specified tenant."""
        records = [
            _make_candidate_record(record_id="rec_001", tenant_id="tenant_A"),
            _make_candidate_record(record_id="rec_002", tenant_id="tenant_B"),
            _make_candidate_record(record_id="rec_003", tenant_id="tenant_A"),
        ]
        result = count_roc_candidates(records, tenant_filter="tenant_A")
        assert result.roc_candidate_count == 2

    def test_tenant_breakdown_tracked(self):
        """Tenant breakdown should be tracked in by_tenant."""
        records = [
            _make_candidate_record(record_id="rec_001", tenant_id="tenant_A"),
            _make_candidate_record(record_id="rec_002", tenant_id="tenant_B"),
            _make_candidate_record(record_id="rec_003", tenant_id="tenant_A"),
        ]
        result = count_roc_candidates(records)
        assert result.by_tenant.get("tenant_A") == 2
        assert result.by_tenant.get("tenant_B") == 1


class TestRecordIdTracking:
    """Test record ID tracking functionality."""

    def test_candidate_record_ids_captured_when_requested(self):
        """Candidate record IDs should be captured when include_record_ids=True."""
        records = [_make_candidate_record(record_id="rec_001")]
        result = count_roc_candidates(records, include_record_ids=True)
        assert "rec_001" in result.candidate_record_ids

    def test_candidate_record_ids_not_captured_by_default(self):
        """Candidate record IDs should not be captured by default."""
        records = [_make_candidate_record(record_id="rec_001")]
        result = count_roc_candidates(records)
        assert len(result.candidate_record_ids) == 0


# ---------------------------------------------------------------------------
# Serialization Tests
# ---------------------------------------------------------------------------


class TestSerialization:
    """Test snapshot serialization/deserialization."""

    def test_to_dict_round_trip(self):
        """Snapshot should survive to_dict/from_dict round trip."""
        records = [_make_candidate_record()]
        result = count_roc_candidates(records)

        data = result.to_dict()
        restored = ROCCandidateMetricSnapshot.from_dict(data)

        assert restored.roc_candidate_count == result.roc_candidate_count
        assert restored.total_records == result.total_records
        assert restored.wsp97_labels == result.wsp97_labels
        assert restored.forbidden_consumers == result.forbidden_consumers
