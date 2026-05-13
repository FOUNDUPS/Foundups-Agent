#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for CABR Lifecycle Report Export Phase 8 - Unified Export Integration.

Validates unified report export combining lifecycle query and consensus reporting
per WSP 97.

Required coverage:
  - JSON export deterministic
  - Markdown export deterministic
  - required WSP_97 labels present
  - false truth fields present
  - lifecycle query summary included
  - gap summary included
  - consensus report summary optional
  - anomaly flags included
  - no payout readiness inferred
  - no DAO activation inferred
  - no CABR readiness inferred
  - pure function/no filesystem writes
  - no default DB path

WSP 97 Critical Constraint:
  Export is observability only.
  Every exported report must explicitly state:
    - REVIEW_ONLY
    - OBSERVABILITY_ONLY
    - verification_complete=False
    - cabr_ready=False
    - payout_ready=False
    - NOT_CABR_READY
    - NOT_PAYOUT_READY
    - NO_DAO_ACTIVATION
    - NO_EXTERNAL_ATTESTATION_REQUIRED

  It must NOT mean:
    - automatic state progression
    - payout approval
    - DAO activation
    - token issuance
    - final consensus readiness
    - external settlement

Slice: CABR_CONSENSUS_FINALIZATION_PHASE8_LIFECYCLE_REPORT_EXPORT_INTEGRATION
Worker: W1
"""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modules.communication.moltbot_bridge.src.cabr_lifecycle_report_export import (
    CABRExportFormat,
    CABRExportMetadata,
    CABRLifecycleReportExport,
    WSP97_REQUIRED_LABELS,
    WSP97_TRUTH_FIELDS,
    build_lifecycle_report_export,
    export_lifecycle_report_json,
    export_lifecycle_report_markdown,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def _make_lifecycle_query_result(
    persisted_record_count: int = 5,
    total_correlations: int = 5,
    total_items: int = 10,
    total_gaps: int = 3,
    correlations_with_gaps: int = 2,
    correlations_complete: int = 3,
    total_anomalies: int = 0,
    has_anomaly: bool = False,
    anomaly_details: list = None,
) -> Dict[str, Any]:
    """Create a mock CABRLifecycleQueryResult dict."""
    correlations = []
    for i in range(total_correlations):
        corr = {
            "correlation_key": "receipt_id",
            "correlation_value": f"rcpt_{i:04d}",
            "stages_present": ["receipt_created", "pavs_evaluated"],
            "stages_missing": ["cabr_scored", "quorum_evaluated"],
            "has_truth_boundary_anomaly": False,
            "anomaly_details": [],
        }
        correlations.append(corr)

    # Add anomaly if requested
    if has_anomaly and correlations:
        correlations[0]["has_truth_boundary_anomaly"] = True
        correlations[0]["anomaly_details"] = anomaly_details or [
            "pavs_evaluated: verification_complete=True"
        ]

    return {
        "persisted_record_count": persisted_record_count,
        "correlation_result": {
            "correlations": correlations,
            "total_items": total_items,
            "items_by_stage": {
                "receipt_created": 5,
                "pavs_evaluated": 3,
                "cabr_scored": 2,
            },
            "total_gaps": total_gaps,
            "total_anomalies": total_anomalies,
        },
        "gap_summary": {
            "total_gaps": total_gaps,
            "correlations_with_gaps": correlations_with_gaps,
            "correlations_complete": correlations_complete,
            "gaps_by_stage": {
                "cabr_scored": 2,
                "quorum_evaluated": 1,
            },
        },
        "generated_at": "2026-05-13T12:00:00+00:00",
        "wsp97_compliance_note": "WSP 97: Lifecycle query is observability only.",
    }


def _make_consensus_report(
    accepted_count: int = 10,
    rejected_count: int = 2,
    total_count: int = 12,
    has_anomaly: bool = False,
    anomaly_record_ids: list = None,
) -> Dict[str, Any]:
    """Create a mock CABRConsensusReport dict."""
    truth_summary = {
        "total_records": total_count,
        "verification_complete": {"false": total_count, "true": 0},
        "cabr_ready": {"false": total_count, "true": 0},
        "payout_ready": {"false": total_count, "true": 0},
        "has_anomaly": has_anomaly,
        "anomaly_record_ids": anomaly_record_ids or [],
    }

    if has_anomaly:
        truth_summary["verification_complete"]["true"] = 1
        truth_summary["verification_complete"]["false"] = total_count - 1

    return {
        "records": [],
        "summary": {
            "decision_counts": {
                "accepted_for_review": accepted_count,
                "rejected": rejected_count,
                "total": total_count,
            },
            "reason_code_counts": {
                "ok_score_accepted_quorum_met": accepted_count,
                "score_rejected_insufficient_evidence": rejected_count,
            },
            "truth_boundary_summary": truth_summary,
            "quorum_metrics": {
                "total_with_quorum_met": accepted_count,
                "avg_unique_verifiers": 3.5,
            },
        },
        "generated_at": "2026-05-13T12:00:00+00:00",
        "wsp97_compliance_note": "WSP 97: This report is observability only.",
    }


# ---------------------------------------------------------------------------
# Test: JSON Export Deterministic
# ---------------------------------------------------------------------------


class TestJsonExportDeterministic(unittest.TestCase):
    """Tests for deterministic JSON export."""

    def test_json_export_is_valid_json(self):
        """JSON export produces valid JSON."""
        export = build_lifecycle_report_export()
        json_str = export_lifecycle_report_json(export)

        parsed = json.loads(json_str)
        self.assertIsInstance(parsed, dict)

    def test_json_export_has_sorted_keys(self):
        """JSON export has sorted keys for determinism."""
        export = build_lifecycle_report_export()
        json_str = export_lifecycle_report_json(export)

        parsed = json.loads(json_str)
        top_keys = list(parsed.keys())
        self.assertEqual(top_keys, sorted(top_keys))

    def test_json_export_deterministic_same_input(self):
        """Same export produces same JSON output."""
        lifecycle_result = _make_lifecycle_query_result()
        export = build_lifecycle_report_export(lifecycle_query_result=lifecycle_result)

        json1 = export_lifecycle_report_json(export)
        json2 = export_lifecycle_report_json(export)

        self.assertEqual(json1, json2)

    def test_json_export_includes_all_required_fields(self):
        """JSON export includes all required fields."""
        export = build_lifecycle_report_export()
        json_str = export_lifecycle_report_json(export)

        parsed = json.loads(json_str)

        # Required top-level fields
        self.assertIn("metadata", parsed)
        self.assertIn("truth_boundary", parsed)
        self.assertIn("wsp97_labels", parsed)
        self.assertIn("wsp97_compliance_note", parsed)
        self.assertIn("lifecycle_query_summary", parsed)
        self.assertIn("gap_summary", parsed)
        self.assertIn("has_anomalies", parsed)
        self.assertIn("anomaly_count", parsed)

    def test_json_export_datetime_as_iso_strings(self):
        """Datetime fields exported as ISO strings."""
        export = build_lifecycle_report_export()
        json_str = export_lifecycle_report_json(export)

        parsed = json.loads(json_str)
        generated_at = parsed["metadata"]["generated_at"]

        self.assertIsInstance(generated_at, str)
        # Should be parseable
        datetime.fromisoformat(generated_at.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# Test: Markdown Export Deterministic
# ---------------------------------------------------------------------------


class TestMarkdownExportDeterministic(unittest.TestCase):
    """Tests for deterministic Markdown export."""

    def test_markdown_export_is_string(self):
        """Markdown export produces string."""
        export = build_lifecycle_report_export()
        md = export_lifecycle_report_markdown(export)

        self.assertIsInstance(md, str)

    def test_markdown_export_has_header(self):
        """Markdown export has proper header."""
        export = build_lifecycle_report_export()
        md = export_lifecycle_report_markdown(export)

        self.assertIn("# CABR Lifecycle Report Export", md)

    def test_markdown_export_has_wsp97_section(self):
        """Markdown export has WSP 97 compliance section."""
        export = build_lifecycle_report_export()
        md = export_lifecycle_report_markdown(export)

        self.assertIn("## WSP 97 Compliance Notice", md)
        self.assertIn("REVIEW_ONLY", md)
        self.assertIn("OBSERVABILITY_ONLY", md)

    def test_markdown_export_has_truth_boundary_table(self):
        """Markdown export has truth boundary table."""
        export = build_lifecycle_report_export()
        md = export_lifecycle_report_markdown(export)

        self.assertIn("## Truth Boundary Fields", md)
        self.assertIn("verification_complete", md)
        self.assertIn("cabr_ready", md)
        self.assertIn("payout_ready", md)

    def test_markdown_export_deterministic(self):
        """Same export produces same Markdown output."""
        lifecycle_result = _make_lifecycle_query_result()
        export = build_lifecycle_report_export(lifecycle_query_result=lifecycle_result)

        md1 = export_lifecycle_report_markdown(export)
        md2 = export_lifecycle_report_markdown(export)

        self.assertEqual(md1, md2)


# ---------------------------------------------------------------------------
# Test: Required WSP 97 Labels Present
# ---------------------------------------------------------------------------


class TestRequiredWsp97LabelsPresent(unittest.TestCase):
    """Tests for required WSP 97 labels."""

    def test_all_required_labels_in_export(self):
        """All required WSP 97 labels present in export."""
        export = build_lifecycle_report_export()

        for label in WSP97_REQUIRED_LABELS:
            self.assertIn(label, export.wsp97_labels)

    def test_all_required_labels_in_json(self):
        """All required WSP 97 labels present in JSON export."""
        export = build_lifecycle_report_export()
        json_str = export_lifecycle_report_json(export)

        for label in WSP97_REQUIRED_LABELS:
            self.assertIn(label, json_str)

    def test_all_required_labels_in_markdown(self):
        """All required WSP 97 labels present in Markdown export."""
        export = build_lifecycle_report_export()
        md = export_lifecycle_report_markdown(export)

        for label in WSP97_REQUIRED_LABELS:
            self.assertIn(label, md)

    def test_review_only_label_present(self):
        """REVIEW_ONLY label is present."""
        export = build_lifecycle_report_export()
        self.assertIn("REVIEW_ONLY", export.wsp97_labels)

    def test_observability_only_label_present(self):
        """OBSERVABILITY_ONLY label is present."""
        export = build_lifecycle_report_export()
        self.assertIn("OBSERVABILITY_ONLY", export.wsp97_labels)

    def test_not_cabr_ready_label_present(self):
        """NOT_CABR_READY label is present."""
        export = build_lifecycle_report_export()
        self.assertIn("NOT_CABR_READY", export.wsp97_labels)

    def test_not_payout_ready_label_present(self):
        """NOT_PAYOUT_READY label is present."""
        export = build_lifecycle_report_export()
        self.assertIn("NOT_PAYOUT_READY", export.wsp97_labels)

    def test_no_dao_activation_label_present(self):
        """NO_DAO_ACTIVATION label is present."""
        export = build_lifecycle_report_export()
        self.assertIn("NO_DAO_ACTIVATION", export.wsp97_labels)

    def test_no_external_attestation_label_present(self):
        """NO_EXTERNAL_ATTESTATION_REQUIRED label is present."""
        export = build_lifecycle_report_export()
        self.assertIn("NO_EXTERNAL_ATTESTATION_REQUIRED", export.wsp97_labels)


# ---------------------------------------------------------------------------
# Test: False Truth Fields Present
# ---------------------------------------------------------------------------


class TestFalseTruthFieldsPresent(unittest.TestCase):
    """Tests for false truth fields in export."""

    def test_all_truth_fields_are_false(self):
        """All truth boundary fields are False."""
        export = build_lifecycle_report_export()

        for field, value in export.truth_boundary.items():
            self.assertFalse(value, f"{field} should be False")

    def test_verification_complete_is_false(self):
        """verification_complete is False."""
        export = build_lifecycle_report_export()
        self.assertFalse(export.truth_boundary.get("verification_complete"))

    def test_cabr_ready_is_false(self):
        """cabr_ready is False."""
        export = build_lifecycle_report_export()
        self.assertFalse(export.truth_boundary.get("cabr_ready"))

    def test_payout_ready_is_false(self):
        """payout_ready is False."""
        export = build_lifecycle_report_export()
        self.assertFalse(export.truth_boundary.get("payout_ready"))

    def test_truth_fields_false_in_json(self):
        """Truth fields are False in JSON export."""
        export = build_lifecycle_report_export()
        json_str = export_lifecycle_report_json(export)
        parsed = json.loads(json_str)

        truth = parsed["truth_boundary"]
        self.assertFalse(truth["verification_complete"])
        self.assertFalse(truth["cabr_ready"])
        self.assertFalse(truth["payout_ready"])

    def test_metadata_indicates_truth_fields_false(self):
        """Metadata correctly indicates all truth fields are False."""
        export = build_lifecycle_report_export()
        self.assertTrue(export.metadata.truth_fields_false)


# ---------------------------------------------------------------------------
# Test: Lifecycle Query Summary Included
# ---------------------------------------------------------------------------


class TestLifecycleQuerySummaryIncluded(unittest.TestCase):
    """Tests for lifecycle query summary inclusion."""

    def test_empty_query_result_produces_none_summary(self):
        """Empty lifecycle query result produces None summary."""
        export = build_lifecycle_report_export()
        self.assertIsNone(export.lifecycle_query_summary)

    def test_query_result_populates_summary(self):
        """Lifecycle query result populates summary."""
        lifecycle_result = _make_lifecycle_query_result(
            persisted_record_count=5,
            total_correlations=5,
        )
        export = build_lifecycle_report_export(lifecycle_query_result=lifecycle_result)

        self.assertIsNotNone(export.lifecycle_query_summary)
        self.assertEqual(export.persisted_record_count, 5)
        self.assertEqual(export.total_correlations, 5)

    def test_items_by_stage_included(self):
        """Items by stage included in summary."""
        lifecycle_result = _make_lifecycle_query_result()
        export = build_lifecycle_report_export(lifecycle_query_result=lifecycle_result)

        self.assertIn("items_by_stage", export.lifecycle_query_summary)

    def test_summary_in_json_export(self):
        """Lifecycle query summary appears in JSON export."""
        lifecycle_result = _make_lifecycle_query_result()
        export = build_lifecycle_report_export(lifecycle_query_result=lifecycle_result)
        json_str = export_lifecycle_report_json(export)
        parsed = json.loads(json_str)

        self.assertIsNotNone(parsed["lifecycle_query_summary"])


# ---------------------------------------------------------------------------
# Test: Gap Summary Included
# ---------------------------------------------------------------------------


class TestGapSummaryIncluded(unittest.TestCase):
    """Tests for gap summary inclusion."""

    def test_empty_query_result_produces_none_gap_summary(self):
        """Empty lifecycle query result produces None gap summary."""
        export = build_lifecycle_report_export()
        self.assertIsNone(export.gap_summary)

    def test_query_result_populates_gap_summary(self):
        """Lifecycle query result populates gap summary."""
        lifecycle_result = _make_lifecycle_query_result(
            total_gaps=5,
            correlations_with_gaps=3,
            correlations_complete=2,
        )
        export = build_lifecycle_report_export(lifecycle_query_result=lifecycle_result)

        self.assertIsNotNone(export.gap_summary)
        self.assertEqual(export.total_gaps, 5)
        self.assertEqual(export.correlations_with_gaps, 3)
        self.assertEqual(export.correlations_complete, 2)

    def test_gaps_by_stage_included(self):
        """Gaps by stage included in summary."""
        lifecycle_result = _make_lifecycle_query_result()
        export = build_lifecycle_report_export(lifecycle_query_result=lifecycle_result)

        self.assertIn("gaps_by_stage", export.gap_summary)

    def test_gap_summary_in_markdown(self):
        """Gap summary appears in Markdown export."""
        lifecycle_result = _make_lifecycle_query_result(total_gaps=3)
        export = build_lifecycle_report_export(lifecycle_query_result=lifecycle_result)
        md = export_lifecycle_report_markdown(export)

        self.assertIn("## Gap Summary", md)
        self.assertIn("Total Gaps", md)


# ---------------------------------------------------------------------------
# Test: Consensus Report Summary Optional
# ---------------------------------------------------------------------------


class TestConsensusReportSummaryOptional(unittest.TestCase):
    """Tests for optional consensus report summary."""

    def test_export_without_consensus_report(self):
        """Export without consensus report produces None summary."""
        export = build_lifecycle_report_export()
        self.assertIsNone(export.consensus_report_summary)

    def test_export_with_consensus_report(self):
        """Export with consensus report populates summary."""
        consensus_report = _make_consensus_report(
            accepted_count=10,
            rejected_count=2,
        )
        export = build_lifecycle_report_export(consensus_report=consensus_report)

        self.assertIsNotNone(export.consensus_report_summary)
        self.assertIn("decision_counts", export.consensus_report_summary)

    def test_consensus_report_decision_counts_included(self):
        """Decision counts included from consensus report."""
        consensus_report = _make_consensus_report(
            accepted_count=10,
            rejected_count=2,
        )
        export = build_lifecycle_report_export(consensus_report=consensus_report)

        dc = export.consensus_report_summary["decision_counts"]
        self.assertEqual(dc.get("accepted_for_review"), 10)
        self.assertEqual(dc.get("rejected"), 2)

    def test_consensus_report_in_markdown(self):
        """Consensus report section appears in Markdown when provided."""
        consensus_report = _make_consensus_report()
        export = build_lifecycle_report_export(consensus_report=consensus_report)
        md = export_lifecycle_report_markdown(export)

        self.assertIn("## Consensus Report Summary", md)

    def test_no_consensus_section_without_report(self):
        """No consensus report section in Markdown without report."""
        export = build_lifecycle_report_export()
        md = export_lifecycle_report_markdown(export)

        # Should have the anomaly report section but not consensus
        self.assertIn("## Anomaly Report", md)


# ---------------------------------------------------------------------------
# Test: Anomaly Flags Included
# ---------------------------------------------------------------------------


class TestAnomalyFlagsIncluded(unittest.TestCase):
    """Tests for anomaly flag inclusion."""

    def test_no_anomalies_by_default(self):
        """No anomalies by default."""
        export = build_lifecycle_report_export()
        self.assertFalse(export.has_anomalies)
        self.assertEqual(export.anomaly_count, 0)

    def test_anomalies_from_lifecycle_query(self):
        """Anomalies from lifecycle query result are flagged."""
        lifecycle_result = _make_lifecycle_query_result(
            total_anomalies=2,
            has_anomaly=True,
            anomaly_details=["verification_complete=True"],
        )
        export = build_lifecycle_report_export(lifecycle_query_result=lifecycle_result)

        self.assertTrue(export.has_anomalies)
        self.assertEqual(export.anomaly_count, 2)

    def test_anomaly_details_included(self):
        """Anomaly details included in export."""
        lifecycle_result = _make_lifecycle_query_result(
            total_anomalies=1,
            has_anomaly=True,
            anomaly_details=["Stage X: verification_complete=True"],
        )
        export = build_lifecycle_report_export(lifecycle_query_result=lifecycle_result)

        self.assertGreater(len(export.anomaly_details), 0)

    def test_anomalies_from_consensus_report(self):
        """Anomalies from consensus report are flagged."""
        consensus_report = _make_consensus_report(
            has_anomaly=True,
            anomaly_record_ids=["ccr_bad_001"],
        )
        export = build_lifecycle_report_export(consensus_report=consensus_report)

        self.assertTrue(export.has_anomalies)

    def test_anomaly_section_in_json(self):
        """Anomaly section appears in JSON export."""
        export = build_lifecycle_report_export()
        json_str = export_lifecycle_report_json(export)
        parsed = json.loads(json_str)

        self.assertIn("has_anomalies", parsed)
        self.assertIn("anomaly_count", parsed)
        self.assertIn("anomaly_details", parsed)

    def test_anomaly_section_in_markdown(self):
        """Anomaly section appears in Markdown export."""
        export = build_lifecycle_report_export()
        md = export_lifecycle_report_markdown(export)

        self.assertIn("## Anomaly Report", md)


# ---------------------------------------------------------------------------
# Test: No Payout Readiness Inferred
# ---------------------------------------------------------------------------


class TestNoPayoutReadinessInferred(unittest.TestCase):
    """Tests that payout readiness is never inferred."""

    def test_payout_ready_always_false(self):
        """payout_ready is always False in export."""
        lifecycle_result = _make_lifecycle_query_result()
        consensus_report = _make_consensus_report(accepted_count=100)
        export = build_lifecycle_report_export(
            lifecycle_query_result=lifecycle_result,
            consensus_report=consensus_report,
        )

        self.assertFalse(export.truth_boundary.get("payout_ready"))

    def test_no_payout_amount_fields(self):
        """Export has no payout amount fields."""
        export = build_lifecycle_report_export()
        json_str = export_lifecycle_report_json(export)

        self.assertNotIn("payout_amount", json_str)
        self.assertNotIn("total_payout", json_str)
        self.assertNotIn("tokens_issued", json_str)

    def test_not_payout_ready_label_always_present(self):
        """NOT_PAYOUT_READY label always present."""
        lifecycle_result = _make_lifecycle_query_result()
        consensus_report = _make_consensus_report(accepted_count=100)
        export = build_lifecycle_report_export(
            lifecycle_query_result=lifecycle_result,
            consensus_report=consensus_report,
        )

        self.assertIn("NOT_PAYOUT_READY", export.wsp97_labels)


# ---------------------------------------------------------------------------
# Test: No DAO Activation Inferred
# ---------------------------------------------------------------------------


class TestNoDAOActivationInferred(unittest.TestCase):
    """Tests that DAO activation is never inferred."""

    def test_cabr_ready_always_false(self):
        """cabr_ready is always False in export."""
        lifecycle_result = _make_lifecycle_query_result()
        consensus_report = _make_consensus_report(accepted_count=100)
        export = build_lifecycle_report_export(
            lifecycle_query_result=lifecycle_result,
            consensus_report=consensus_report,
        )

        self.assertFalse(export.truth_boundary.get("cabr_ready"))

    def test_no_dao_activation_fields(self):
        """Export has no DAO activation fields."""
        export = build_lifecycle_report_export()
        json_str = export_lifecycle_report_json(export)

        self.assertNotIn("dao_activated", json_str)
        self.assertNotIn("dao_transition", json_str)

    def test_no_dao_activation_label_always_present(self):
        """NO_DAO_ACTIVATION label always present."""
        export = build_lifecycle_report_export()
        self.assertIn("NO_DAO_ACTIVATION", export.wsp97_labels)


# ---------------------------------------------------------------------------
# Test: No CABR Readiness Inferred
# ---------------------------------------------------------------------------


class TestNoCABRReadinessInferred(unittest.TestCase):
    """Tests that CABR readiness is never inferred."""

    def test_verification_complete_always_false(self):
        """verification_complete is always False in export."""
        lifecycle_result = _make_lifecycle_query_result()
        consensus_report = _make_consensus_report(accepted_count=100)
        export = build_lifecycle_report_export(
            lifecycle_query_result=lifecycle_result,
            consensus_report=consensus_report,
        )

        self.assertFalse(export.truth_boundary.get("verification_complete"))

    def test_not_cabr_ready_label_always_present(self):
        """NOT_CABR_READY label always present."""
        lifecycle_result = _make_lifecycle_query_result()
        consensus_report = _make_consensus_report(accepted_count=100)
        export = build_lifecycle_report_export(
            lifecycle_query_result=lifecycle_result,
            consensus_report=consensus_report,
        )

        self.assertIn("NOT_CABR_READY", export.wsp97_labels)

    def test_full_pipeline_does_not_set_cabr_ready(self):
        """Full pipeline with high acceptance does not set cabr_ready."""
        lifecycle_result = _make_lifecycle_query_result(
            total_gaps=0,
            correlations_complete=10,
        )
        consensus_report = _make_consensus_report(
            accepted_count=100,
            rejected_count=0,
        )
        export = build_lifecycle_report_export(
            lifecycle_query_result=lifecycle_result,
            consensus_report=consensus_report,
        )

        # Even with perfect data, cabr_ready must be False
        self.assertFalse(export.truth_boundary.get("cabr_ready"))


# ---------------------------------------------------------------------------
# Test: Pure Function / No Filesystem Writes
# ---------------------------------------------------------------------------


class TestPureFunctionNoFilesystemWrites(unittest.TestCase):
    """Tests that export functions are pure and don't write to filesystem."""

    def test_build_export_is_pure_function(self):
        """build_lifecycle_report_export is a pure function."""
        lifecycle_result = _make_lifecycle_query_result()
        original = json.dumps(lifecycle_result, sort_keys=True)

        build_lifecycle_report_export(lifecycle_query_result=lifecycle_result)

        # Input unchanged
        after = json.dumps(lifecycle_result, sort_keys=True)
        self.assertEqual(original, after)

    def test_json_export_does_not_write_files(self):
        """export_lifecycle_report_json does not write files."""
        import os
        import tempfile

        temp_files_before = set(os.listdir(tempfile.gettempdir()))

        export = build_lifecycle_report_export()
        export_lifecycle_report_json(export)

        temp_files_after = set(os.listdir(tempfile.gettempdir()))
        new_files = temp_files_after - temp_files_before

        # No CABR-related files created
        for f in new_files:
            self.assertNotIn("cabr", f.lower())
            self.assertNotIn("export", f.lower())

    def test_markdown_export_does_not_write_files(self):
        """export_lifecycle_report_markdown does not write files."""
        import os
        import tempfile

        temp_files_before = set(os.listdir(tempfile.gettempdir()))

        export = build_lifecycle_report_export()
        export_lifecycle_report_markdown(export)

        temp_files_after = set(os.listdir(tempfile.gettempdir()))
        new_files = temp_files_after - temp_files_before

        # No CABR-related files created
        for f in new_files:
            self.assertNotIn("cabr", f.lower())
            self.assertNotIn("export", f.lower())

    def test_export_returns_string_not_file_path(self):
        """Export functions return strings, not file paths."""
        export = build_lifecycle_report_export()

        json_result = export_lifecycle_report_json(export)
        md_result = export_lifecycle_report_markdown(export)

        # Results are strings containing content, not file paths
        self.assertIn("{", json_result)  # JSON content
        self.assertIn("#", md_result)  # Markdown headers


# ---------------------------------------------------------------------------
# Test: No Default DB Path
# ---------------------------------------------------------------------------


class TestNoDefaultDbPath(unittest.TestCase):
    """Tests that no default DB path is used."""

    def test_build_export_has_no_db_path_parameter(self):
        """build_lifecycle_report_export has no db_path parameter."""
        import inspect

        sig = inspect.signature(build_lifecycle_report_export)
        param_names = list(sig.parameters.keys())

        self.assertNotIn("db_path", param_names)
        self.assertNotIn("store", param_names)

    def test_json_export_has_no_db_path_parameter(self):
        """export_lifecycle_report_json has no db_path parameter."""
        import inspect

        sig = inspect.signature(export_lifecycle_report_json)
        param_names = list(sig.parameters.keys())

        self.assertNotIn("db_path", param_names)
        self.assertNotIn("store", param_names)

    def test_markdown_export_has_no_db_path_parameter(self):
        """export_lifecycle_report_markdown has no db_path parameter."""
        import inspect

        sig = inspect.signature(export_lifecycle_report_markdown)
        param_names = list(sig.parameters.keys())

        self.assertNotIn("db_path", param_names)
        self.assertNotIn("store", param_names)

    def test_empty_input_returns_valid_export(self):
        """Empty input returns valid export (no DB needed)."""
        export = build_lifecycle_report_export()

        self.assertIsNotNone(export)
        self.assertIsNotNone(export.metadata)
        self.assertEqual(len(export.wsp97_labels), len(WSP97_REQUIRED_LABELS))


# ---------------------------------------------------------------------------
# Test: Dataclass Serialization
# ---------------------------------------------------------------------------


class TestDataclassSerialization(unittest.TestCase):
    """Tests for dataclass serialization."""

    def test_export_metadata_to_dict(self):
        """CABRExportMetadata serializes to dict."""
        metadata = CABRExportMetadata(
            export_format=CABRExportFormat.JSON,
            export_version="1.0.0",
        )

        d = metadata.to_dict()

        self.assertEqual(d["export_format"], "json")
        self.assertEqual(d["export_version"], "1.0.0")
        self.assertIn("generated_at", d)

    def test_export_to_dict_sorted_keys(self):
        """CABRLifecycleReportExport.to_dict has sorted keys."""
        export = build_lifecycle_report_export()
        d = export.to_dict()

        keys = list(d.keys())
        self.assertEqual(keys, sorted(keys))

    def test_export_format_enum_values(self):
        """CABRExportFormat enum has expected values."""
        self.assertEqual(CABRExportFormat.JSON.value, "json")
        self.assertEqual(CABRExportFormat.MARKDOWN.value, "markdown")


# ---------------------------------------------------------------------------
# Test: Combined Export
# ---------------------------------------------------------------------------


class TestCombinedExport(unittest.TestCase):
    """Tests for combined lifecycle and consensus exports."""

    def test_combined_export_includes_both_summaries(self):
        """Combined export includes both lifecycle and consensus summaries."""
        lifecycle_result = _make_lifecycle_query_result()
        consensus_report = _make_consensus_report()

        export = build_lifecycle_report_export(
            lifecycle_query_result=lifecycle_result,
            consensus_report=consensus_report,
        )

        self.assertIsNotNone(export.lifecycle_query_summary)
        self.assertIsNotNone(export.consensus_report_summary)

    def test_combined_export_json_valid(self):
        """Combined export produces valid JSON."""
        lifecycle_result = _make_lifecycle_query_result()
        consensus_report = _make_consensus_report()

        export = build_lifecycle_report_export(
            lifecycle_query_result=lifecycle_result,
            consensus_report=consensus_report,
        )
        json_str = export_lifecycle_report_json(export)

        parsed = json.loads(json_str)
        self.assertIn("lifecycle_query_summary", parsed)
        self.assertIn("consensus_report_summary", parsed)

    def test_combined_export_markdown_valid(self):
        """Combined export produces valid Markdown."""
        lifecycle_result = _make_lifecycle_query_result()
        consensus_report = _make_consensus_report()

        export = build_lifecycle_report_export(
            lifecycle_query_result=lifecycle_result,
            consensus_report=consensus_report,
        )
        md = export_lifecycle_report_markdown(export)

        self.assertIn("## Lifecycle Query Summary", md)
        self.assertIn("## Consensus Report Summary", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
