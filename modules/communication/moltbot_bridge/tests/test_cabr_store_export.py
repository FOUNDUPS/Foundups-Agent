#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for CABR Store Export Phase 9 - Store-to-Export Integration.

Validates caller-driven store-to-export integration helper per WSP 97.

Required coverage:
  - no store provided fails closed
  - provided empty store exports deterministic JSON/Markdown
  - store with persisted records exports deterministic JSON/Markdown
  - include_json/include_markdown toggles work
  - invalid time range fails closed
  - missing receipts produce gaps
  - required WSP_97 labels present
  - no filesystem writes
  - no default DB path
  - no payout readiness inferred
  - no DAO activation inferred
  - no CABR readiness inferred
  - truth anomaly propagation

WSP 97 Critical Constraint:
  Store export is observability only.
  It must NOT mean:
    - automatic state progression
    - verification_complete=True
    - cabr_ready=True
    - payout_ready=True
    - payout approval
    - DAO activation
    - token issuance
    - final consensus readiness
    - external settlement

Slice: CABR_CONSENSUS_FINALIZATION_PHASE9_STORE_EXPORT_INTEGRATION
Worker: W1
"""

from __future__ import annotations

import gc
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modules.communication.moltbot_bridge.src.cabr_store_export import (
    CABRStoreExportRequest,
    CABRStoreExportResult,
    build_store_export,
    build_store_export_json,
    build_store_export_markdown,
)
from modules.communication.moltbot_bridge.src.cabr_lifecycle_report_export import (
    WSP97_REQUIRED_LABELS,
    WSP97_TRUTH_FIELDS,
)
from modules.communication.moltbot_bridge.src.cabr_consensus_store import (
    CABRConsensusStore,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def _make_consensus_record(
    record_id: str = "ccr_test_18a3b2c1_abc123",
    record_hash: str = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    receipt_id: str = "rcpt_test_001",
    job_id: str = "j_test_001",
    tenant_id: str = "t_test",
    decision: str = "accepted_for_review",
    reason_code: str = "ok_score_accepted_quorum_met",
    finalized_at: str = "2026-05-13T12:00:00+00:00",
    verification_complete: bool = False,
    cabr_ready: bool = False,
    payout_ready: bool = False,
) -> Dict[str, Any]:
    """Create a mock CABRConsensusRecord dict."""
    return {
        "record_id": record_id,
        "record_hash": record_hash,
        "receipt_id": receipt_id,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "score_id": f"cabr_{receipt_id}",
        "score_decision": "accepted_for_review",
        "score_reason_code": "ok_evidence_present_quorum_met",
        "quorum_id": f"qv_{receipt_id}",
        "quorum_decision": "consensus_accepted_for_review",
        "quorum_reason_code": "ok_quorum_met_threshold_met",
        "decision": decision,
        "reason_code": reason_code,
        "reason_human": f"Test record: {decision}",
        "quorum_met": True,
        "threshold_met": True,
        "unique_verifiers": 3,
        "consensus_score": 1.0,
        "evidence_present": True,
        "evidence_count": 2,
        "is_dry_run": False,
        "is_simulated": False,
        "verification_complete": verification_complete,
        "cabr_ready": cabr_ready,
        "payout_ready": payout_ready,
        "finalized_at": finalized_at,
        "finalizer_version": "0.1.0",
    }


def _make_receipt(
    receipt_id: str = "rcpt_test_001",
    job_id: str = "j_test_001",
    verification_status: str = "pending_pavs",
) -> Dict[str, Any]:
    """Create a mock ProofOfComputeReceipt dict."""
    return {
        "receipt_id": receipt_id,
        "job_id": job_id,
        "tenant_id": "t_test",
        "verification_status": verification_status,
        "status_reason_code": "OK",
        "created_at": "2026-05-13T10:00:00+00:00",
    }


def _make_pavs_result(
    receipt_id: str = "rcpt_test_001",
    job_id: str = "j_test_001",
    decision: str = "accepted_for_review",
    verification_complete: bool = False,
    cabr_ready: bool = False,
    payout_ready: bool = False,
) -> Dict[str, Any]:
    """Create a mock PAVSVerificationResult dict."""
    return {
        "verification_id": f"pv_{receipt_id}",
        "receipt_id": receipt_id,
        "job_id": job_id,
        "tenant_id": "t_test",
        "decision": decision,
        "reason_code": "ok_evidence_present",
        "evidence_refs": ["ref1"],
        "evidence_count": 1,
        "verification_complete": verification_complete,
        "cabr_ready": cabr_ready,
        "payout_ready": payout_ready,
        "created_at": "2026-05-13T10:01:00+00:00",
    }


def _make_score_result(
    receipt_id: str = "rcpt_test_001",
    job_id: str = "j_test_001",
    decision: str = "accepted_for_review",
    verification_complete: bool = False,
    cabr_ready: bool = False,
    payout_ready: bool = False,
) -> Dict[str, Any]:
    """Create a mock CABRScoreResult dict."""
    return {
        "score_id": f"cabr_{receipt_id}",
        "receipt_id": receipt_id,
        "job_id": job_id,
        "tenant_id": "t_test",
        "decision": decision,
        "reason_code": "ok_evidence_present_quorum_met",
        "verification_complete": verification_complete,
        "cabr_ready": cabr_ready,
        "payout_ready": payout_ready,
        "scored_at": "2026-05-13T10:02:00+00:00",
    }


def _make_quorum_result(
    receipt_id: str = "rcpt_test_001",
    job_id: str = "j_test_001",
    decision: str = "consensus_accepted_for_review",
    verification_complete: bool = False,
    cabr_ready: bool = False,
    payout_ready: bool = False,
) -> Dict[str, Any]:
    """Create a mock QuorumVerificationResult dict."""
    return {
        "quorum_id": f"qv_{receipt_id}",
        "receipt_id": receipt_id,
        "job_id": job_id,
        "tenant_id": "t_test",
        "decision": decision,
        "reason_code": "ok_quorum_met_threshold_met",
        "quorum_met": True,
        "threshold_met": True,
        "verification_complete": verification_complete,
        "cabr_ready": cabr_ready,
        "payout_ready": payout_ready,
        "evaluated_at": "2026-05-13T10:03:00+00:00",
    }


# ---------------------------------------------------------------------------
# Test: No Store Provided Fails Closed
# ---------------------------------------------------------------------------


class TestNoStoreProvidedFailsClosed(unittest.TestCase):
    """Tests that missing store raises error."""

    def test_build_store_export_raises_without_store(self):
        """build_store_export raises ValueError without store."""
        with self.assertRaises(ValueError) as ctx:
            build_store_export(store=None)

        self.assertIn("store is required", str(ctx.exception))

    def test_build_store_export_json_raises_without_store(self):
        """build_store_export_json raises ValueError without store."""
        with self.assertRaises(ValueError) as ctx:
            build_store_export_json(store=None)

        self.assertIn("store is required", str(ctx.exception))

    def test_build_store_export_markdown_raises_without_store(self):
        """build_store_export_markdown raises ValueError without store."""
        with self.assertRaises(ValueError) as ctx:
            build_store_export_markdown(store=None)

        self.assertIn("store is required", str(ctx.exception))

    def test_request_validation_fails_without_store(self):
        """Request validation fails without store."""
        request = CABRStoreExportRequest(store=None)
        self.assertFalse(request.validate())


# ---------------------------------------------------------------------------
# Test: Provided Empty Store Exports Deterministic JSON/Markdown
# ---------------------------------------------------------------------------


class TestProvidedEmptyStoreExportsDeterministic(unittest.TestCase):
    """Tests for empty store exports."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_empty_store_exports_valid_json(self):
        """Empty store exports valid JSON."""
        result = build_store_export(self.store)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.json_export)
        parsed = json.loads(result.json_export)
        self.assertIsInstance(parsed, dict)

    def test_empty_store_exports_valid_markdown(self):
        """Empty store exports valid Markdown."""
        result = build_store_export(self.store)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.markdown_export)
        self.assertIn("# CABR Lifecycle Report Export", result.markdown_export)

    def test_empty_store_json_deterministic(self):
        """Empty store produces deterministic JSON."""
        result1 = build_store_export(self.store)
        result2 = build_store_export(self.store)

        # Parse and compare (generated_at will differ)
        parsed1 = json.loads(result1.json_export)
        parsed2 = json.loads(result2.json_export)

        # Core structure should match
        self.assertEqual(parsed1["persisted_record_count"], parsed2["persisted_record_count"])
        self.assertEqual(parsed1["truth_boundary"], parsed2["truth_boundary"])

    def test_empty_store_has_zero_records(self):
        """Empty store reports zero records."""
        result = build_store_export(self.store)

        self.assertEqual(result.persisted_record_count, 0)

    def test_empty_store_json_has_sorted_keys(self):
        """Empty store JSON has sorted keys."""
        result = build_store_export(self.store)
        parsed = json.loads(result.json_export)

        top_keys = list(parsed.keys())
        self.assertEqual(top_keys, sorted(top_keys))


# ---------------------------------------------------------------------------
# Test: Store With Persisted Records Exports Deterministic JSON/Markdown
# ---------------------------------------------------------------------------


class TestStoreWithPersistedRecordsExportsDeterministic(unittest.TestCase):
    """Tests for store with records exports."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert records
        for i in range(5):
            self.store.save_record(_make_consensus_record(
                record_id=f"ccr_{i:04d}",
                receipt_id=f"rcpt_{i:04d}",
                finalized_at=f"2026-0{i + 1}-15T10:00:00+00:00",
            ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_store_with_records_exports_valid_json(self):
        """Store with records exports valid JSON."""
        result = build_store_export(self.store)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.json_export)
        parsed = json.loads(result.json_export)
        self.assertIsInstance(parsed, dict)

    def test_store_with_records_exports_valid_markdown(self):
        """Store with records exports valid Markdown."""
        result = build_store_export(self.store)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.markdown_export)
        self.assertIn("# CABR Lifecycle Report Export", result.markdown_export)

    def test_store_with_records_reports_correct_count(self):
        """Store with records reports correct record count."""
        result = build_store_export(self.store)

        self.assertEqual(result.persisted_record_count, 5)

    def test_store_with_records_has_correlations(self):
        """Store with records has correlations."""
        result = build_store_export(self.store)

        self.assertEqual(result.total_correlations, 5)

    def test_json_convenience_function(self):
        """build_store_export_json returns JSON string."""
        json_str = build_store_export_json(self.store)

        parsed = json.loads(json_str)
        self.assertIn("persisted_record_count", parsed)

    def test_markdown_convenience_function(self):
        """build_store_export_markdown returns Markdown string."""
        md = build_store_export_markdown(self.store)

        self.assertIn("# CABR Lifecycle Report Export", md)


# ---------------------------------------------------------------------------
# Test: Include JSON/Markdown Toggles Work
# ---------------------------------------------------------------------------


class TestIncludeTogglesWork(unittest.TestCase):
    """Tests for include_json/include_markdown toggles."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_both_exports_enabled_by_default(self):
        """Both JSON and Markdown enabled by default."""
        result = build_store_export(self.store)

        self.assertIsNotNone(result.json_export)
        self.assertIsNotNone(result.markdown_export)

    def test_json_only(self):
        """Only JSON when include_markdown=False."""
        result = build_store_export(
            self.store,
            include_json=True,
            include_markdown=False,
        )

        self.assertIsNotNone(result.json_export)
        self.assertIsNone(result.markdown_export)

    def test_markdown_only(self):
        """Only Markdown when include_json=False."""
        result = build_store_export(
            self.store,
            include_json=False,
            include_markdown=True,
        )

        self.assertIsNone(result.json_export)
        self.assertIsNotNone(result.markdown_export)

    def test_neither_export(self):
        """No exports when both disabled."""
        result = build_store_export(
            self.store,
            include_json=False,
            include_markdown=False,
        )

        self.assertIsNone(result.json_export)
        self.assertIsNone(result.markdown_export)
        # But result should still be successful
        self.assertTrue(result.success)


# ---------------------------------------------------------------------------
# Test: Invalid Time Range Fails Closed
# ---------------------------------------------------------------------------


class TestInvalidTimeRangeFailsClosed(unittest.TestCase):
    """Tests for invalid time range handling."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_start_after_end_raises_value_error(self):
        """Invalid time range (start > end) raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            build_store_export(
                self.store,
                start=datetime(2026, 12, 31, tzinfo=timezone.utc),
                end=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

        self.assertIn("Invalid time range", str(ctx.exception))

    def test_json_function_raises_on_invalid_time_range(self):
        """build_store_export_json raises on invalid time range."""
        with self.assertRaises(ValueError) as ctx:
            build_store_export_json(
                self.store,
                start=datetime(2026, 12, 31, tzinfo=timezone.utc),
                end=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

        self.assertIn("Invalid time range", str(ctx.exception))

    def test_markdown_function_raises_on_invalid_time_range(self):
        """build_store_export_markdown raises on invalid time range."""
        with self.assertRaises(ValueError) as ctx:
            build_store_export_markdown(
                self.store,
                start=datetime(2026, 12, 31, tzinfo=timezone.utc),
                end=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

        self.assertIn("Invalid time range", str(ctx.exception))

    def test_request_validation_fails_on_invalid_time_range(self):
        """Request validation fails on invalid time range."""
        request = CABRStoreExportRequest(
            store=self.store,
            start=datetime(2026, 12, 31, tzinfo=timezone.utc),
            end=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        self.assertFalse(request.validate())


# ---------------------------------------------------------------------------
# Test: Missing Receipts Produce Gaps
# ---------------------------------------------------------------------------


class TestMissingReceiptsProduceGaps(unittest.TestCase):
    """Tests for gap reporting with missing receipts."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert records
        self.store.save_record(_make_consensus_record(
            record_id="ccr_001",
            receipt_id="rcpt_001",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_002",
            receipt_id="rcpt_002",
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_no_receipts_produces_gaps(self):
        """No supplied receipts produces gaps."""
        result = build_store_export(self.store)

        # Should have gaps for missing upstream stages
        self.assertGreater(result.total_gaps, 0)

    def test_partial_receipts_produces_gaps(self):
        """Partial receipts produces gaps."""
        result = build_store_export(
            self.store,
            receipts=[_make_receipt(receipt_id="rcpt_001")],
        )

        # One receipt matched, one missing
        self.assertGreater(result.total_gaps, 0)

    def test_full_receipts_reduces_gaps(self):
        """Full receipts reduces gaps."""
        result_without = build_store_export(self.store)

        result_with = build_store_export(
            self.store,
            receipts=[
                _make_receipt(receipt_id="rcpt_001"),
                _make_receipt(receipt_id="rcpt_002"),
            ],
        )

        # Should have fewer gaps with receipts
        self.assertLessEqual(result_with.total_gaps, result_without.total_gaps)

    def test_gap_summary_in_json(self):
        """Gap summary appears in JSON export."""
        result = build_store_export(self.store)
        parsed = json.loads(result.json_export)

        self.assertIn("gap_summary", parsed)

    def test_gap_summary_in_markdown(self):
        """Gap summary appears in Markdown export."""
        result = build_store_export(self.store)

        self.assertIn("## Gap Summary", result.markdown_export)


# ---------------------------------------------------------------------------
# Test: Required WSP_97 Labels Present
# ---------------------------------------------------------------------------


class TestRequiredWsp97LabelsPresent(unittest.TestCase):
    """Tests for required WSP 97 labels."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_all_required_labels_in_result(self):
        """All required WSP 97 labels present in result."""
        result = build_store_export(self.store)

        for label in WSP97_REQUIRED_LABELS:
            self.assertIn(label, result.wsp97_labels)

    def test_all_required_labels_in_json(self):
        """All required WSP 97 labels present in JSON export."""
        result = build_store_export(self.store)

        for label in WSP97_REQUIRED_LABELS:
            self.assertIn(label, result.json_export)

    def test_all_required_labels_in_markdown(self):
        """All required WSP 97 labels present in Markdown export."""
        result = build_store_export(self.store)

        for label in WSP97_REQUIRED_LABELS:
            self.assertIn(label, result.markdown_export)

    def test_review_only_label_present(self):
        """REVIEW_ONLY label is present."""
        result = build_store_export(self.store)
        self.assertIn("REVIEW_ONLY", result.wsp97_labels)

    def test_observability_only_label_present(self):
        """OBSERVABILITY_ONLY label is present."""
        result = build_store_export(self.store)
        self.assertIn("OBSERVABILITY_ONLY", result.wsp97_labels)

    def test_not_cabr_ready_label_present(self):
        """NOT_CABR_READY label is present."""
        result = build_store_export(self.store)
        self.assertIn("NOT_CABR_READY", result.wsp97_labels)

    def test_not_payout_ready_label_present(self):
        """NOT_PAYOUT_READY label is present."""
        result = build_store_export(self.store)
        self.assertIn("NOT_PAYOUT_READY", result.wsp97_labels)

    def test_no_dao_activation_label_present(self):
        """NO_DAO_ACTIVATION label is present."""
        result = build_store_export(self.store)
        self.assertIn("NO_DAO_ACTIVATION", result.wsp97_labels)

    def test_no_external_attestation_label_present(self):
        """NO_EXTERNAL_ATTESTATION_REQUIRED label is present."""
        result = build_store_export(self.store)
        self.assertIn("NO_EXTERNAL_ATTESTATION_REQUIRED", result.wsp97_labels)


# ---------------------------------------------------------------------------
# Test: No Filesystem Writes
# ---------------------------------------------------------------------------


class TestNoFilesystemWrites(unittest.TestCase):
    """Tests that export does not write to filesystem."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_export_does_not_create_files(self):
        """Export does not create files in temp directory."""
        import os
        import tempfile

        temp_files_before = set(os.listdir(tempfile.gettempdir()))

        build_store_export(self.store)

        temp_files_after = set(os.listdir(tempfile.gettempdir()))
        new_files = temp_files_after - temp_files_before

        # No CABR-related files created
        for f in new_files:
            self.assertNotIn("cabr", f.lower())
            self.assertNotIn("export", f.lower())

    def test_json_function_does_not_create_files(self):
        """build_store_export_json does not create files."""
        import os
        import tempfile

        temp_files_before = set(os.listdir(tempfile.gettempdir()))

        build_store_export_json(self.store)

        temp_files_after = set(os.listdir(tempfile.gettempdir()))
        new_files = temp_files_after - temp_files_before

        for f in new_files:
            self.assertNotIn("cabr", f.lower())

    def test_markdown_function_does_not_create_files(self):
        """build_store_export_markdown does not create files."""
        import os
        import tempfile

        temp_files_before = set(os.listdir(tempfile.gettempdir()))

        build_store_export_markdown(self.store)

        temp_files_after = set(os.listdir(tempfile.gettempdir()))
        new_files = temp_files_after - temp_files_before

        for f in new_files:
            self.assertNotIn("cabr", f.lower())

    def test_exports_return_strings_not_paths(self):
        """Export functions return strings, not file paths."""
        result = build_store_export(self.store)

        # Results are strings containing content, not file paths
        self.assertIn("{", result.json_export)  # JSON content
        self.assertIn("#", result.markdown_export)  # Markdown headers


# ---------------------------------------------------------------------------
# Test: No Default DB Path
# ---------------------------------------------------------------------------


class TestNoDefaultDbPath(unittest.TestCase):
    """Tests that no default DB path is used."""

    def test_build_store_export_requires_store(self):
        """build_store_export requires store parameter."""
        with self.assertRaises((TypeError, ValueError)):
            build_store_export()  # type: ignore

    def test_json_function_requires_store(self):
        """build_store_export_json requires store parameter."""
        with self.assertRaises((TypeError, ValueError)):
            build_store_export_json()  # type: ignore

    def test_markdown_function_requires_store(self):
        """build_store_export_markdown requires store parameter."""
        with self.assertRaises((TypeError, ValueError)):
            build_store_export_markdown()  # type: ignore

    def test_no_db_path_parameter_in_function(self):
        """No db_path parameter in export functions."""
        import inspect

        sig = inspect.signature(build_store_export)
        param_names = list(sig.parameters.keys())

        self.assertNotIn("db_path", param_names)


# ---------------------------------------------------------------------------
# Test: No Payout Readiness Inferred
# ---------------------------------------------------------------------------


class TestNoPayoutReadinessInferred(unittest.TestCase):
    """Tests that payout readiness is never inferred."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        self.store.save_record(_make_consensus_record(
            record_id="ccr_001",
            receipt_id="rcpt_001",
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_payout_ready_always_false(self):
        """payout_ready is always False in result."""
        result = build_store_export(self.store)

        self.assertFalse(result.truth_boundary.get("payout_ready"))

    def test_no_payout_amount_fields(self):
        """Export has no payout amount fields."""
        result = build_store_export(self.store)

        self.assertNotIn("payout_amount", result.json_export)
        self.assertNotIn("total_payout", result.json_export)
        self.assertNotIn("tokens_issued", result.json_export)

    def test_not_payout_ready_label_always_present(self):
        """NOT_PAYOUT_READY label always present."""
        result = build_store_export(self.store)

        self.assertIn("NOT_PAYOUT_READY", result.wsp97_labels)


# ---------------------------------------------------------------------------
# Test: No DAO Activation Inferred
# ---------------------------------------------------------------------------


class TestNoDAOActivationInferred(unittest.TestCase):
    """Tests that DAO activation is never inferred."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        self.store.save_record(_make_consensus_record(
            record_id="ccr_001",
            receipt_id="rcpt_001",
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_cabr_ready_always_false(self):
        """cabr_ready is always False in result."""
        result = build_store_export(self.store)

        self.assertFalse(result.truth_boundary.get("cabr_ready"))

    def test_no_dao_activation_fields(self):
        """Export has no DAO activation fields."""
        result = build_store_export(self.store)

        self.assertNotIn("dao_activated", result.json_export)
        self.assertNotIn("dao_transition", result.json_export)

    def test_no_dao_activation_label_always_present(self):
        """NO_DAO_ACTIVATION label always present."""
        result = build_store_export(self.store)

        self.assertIn("NO_DAO_ACTIVATION", result.wsp97_labels)


# ---------------------------------------------------------------------------
# Test: No CABR Readiness Inferred
# ---------------------------------------------------------------------------


class TestNoCABRReadinessInferred(unittest.TestCase):
    """Tests that CABR readiness is never inferred."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        self.store.save_record(_make_consensus_record(
            record_id="ccr_001",
            receipt_id="rcpt_001",
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_verification_complete_always_false(self):
        """verification_complete is always False in result."""
        result = build_store_export(self.store)

        self.assertFalse(result.truth_boundary.get("verification_complete"))

    def test_not_cabr_ready_label_always_present(self):
        """NOT_CABR_READY label always present."""
        result = build_store_export(self.store)

        self.assertIn("NOT_CABR_READY", result.wsp97_labels)


# ---------------------------------------------------------------------------
# Test: Truth Anomaly Propagation
# ---------------------------------------------------------------------------


class TestTruthAnomalyPropagation(unittest.TestCase):
    """Tests for truth boundary anomaly propagation."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        self.store.save_record(_make_consensus_record(
            record_id="ccr_001",
            receipt_id="rcpt_001",
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_anomaly_in_pavs_flagged(self):
        """verification_complete=True in pavs_results is flagged."""
        result = build_store_export(
            self.store,
            pavs_results=[_make_pavs_result(
                receipt_id="rcpt_001",
                verification_complete=True,  # Anomaly
            )],
        )

        self.assertTrue(result.has_anomalies)
        self.assertGreater(result.anomaly_count, 0)

    def test_anomaly_in_score_flagged(self):
        """cabr_ready=True in score_results is flagged."""
        result = build_store_export(
            self.store,
            score_results=[_make_score_result(
                receipt_id="rcpt_001",
                cabr_ready=True,  # Anomaly
            )],
        )

        self.assertTrue(result.has_anomalies)

    def test_anomaly_in_quorum_flagged(self):
        """payout_ready=True in quorum_results is flagged."""
        result = build_store_export(
            self.store,
            quorum_results=[_make_quorum_result(
                receipt_id="rcpt_001",
                payout_ready=True,  # Anomaly
            )],
        )

        self.assertTrue(result.has_anomalies)

    def test_no_anomalies_by_default(self):
        """No anomalies when all truth fields are False."""
        result = build_store_export(self.store)

        self.assertFalse(result.has_anomalies)
        self.assertEqual(result.anomaly_count, 0)

    def test_anomaly_section_in_json(self):
        """Anomaly section appears in JSON export."""
        result = build_store_export(self.store)
        parsed = json.loads(result.json_export)

        self.assertIn("has_anomalies", parsed)
        self.assertIn("anomaly_count", parsed)

    def test_anomaly_section_in_markdown(self):
        """Anomaly section appears in Markdown export."""
        result = build_store_export(self.store)

        self.assertIn("## Anomaly Report", result.markdown_export)


# ---------------------------------------------------------------------------
# Test: Request Dataclass
# ---------------------------------------------------------------------------


class TestRequestDataclass(unittest.TestCase):
    """Tests for CABRStoreExportRequest dataclass."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_valid_request(self):
        """Valid request passes validation."""
        request = CABRStoreExportRequest(store=self.store)
        self.assertTrue(request.validate())

    def test_request_with_time_range(self):
        """Request with valid time range passes validation."""
        request = CABRStoreExportRequest(
            store=self.store,
            start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end=datetime(2026, 12, 31, tzinfo=timezone.utc),
        )
        self.assertTrue(request.validate())

    def test_request_with_all_options(self):
        """Request with all options passes validation."""
        request = CABRStoreExportRequest(
            store=self.store,
            receipts=[_make_receipt()],
            pavs_results=[_make_pavs_result()],
            score_results=[_make_score_result()],
            quorum_results=[_make_quorum_result()],
            start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end=datetime(2026, 12, 31, tzinfo=timezone.utc),
            limit=100,
            include_markdown=True,
            include_json=True,
        )
        self.assertTrue(request.validate())


# ---------------------------------------------------------------------------
# Test: Result Dataclass
# ---------------------------------------------------------------------------


class TestResultDataclass(unittest.TestCase):
    """Tests for CABRStoreExportResult dataclass."""

    def test_result_has_wsp97_fields(self):
        """Result has WSP 97 fields initialized."""
        result = CABRStoreExportResult()

        self.assertIsNotNone(result.wsp97_labels)
        self.assertIsNotNone(result.truth_boundary)
        self.assertIn("WSP 97", result.wsp97_compliance_note)

    def test_result_to_dict(self):
        """Result serializes to dict."""
        result = CABRStoreExportResult(
            success=True,
            persisted_record_count=5,
        )

        d = result.to_dict()

        self.assertTrue(d["success"])
        self.assertEqual(d["persisted_record_count"], 5)
        self.assertIn("wsp97_labels", d)
        self.assertIn("truth_boundary", d)

    def test_result_to_dict_sorted_keys(self):
        """Result.to_dict has sorted keys."""
        result = CABRStoreExportResult()
        d = result.to_dict()

        keys = list(d.keys())
        self.assertEqual(keys, sorted(keys))


if __name__ == "__main__":
    unittest.main(verbosity=2)
