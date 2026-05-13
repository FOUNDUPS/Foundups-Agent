#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for CABR Consensus Reporting Phase 5 - Time-Range Query and Receipt Correlation.

Validates time-range filtering and receipt correlation per WSP 97.

Required coverage:
  - Time filter validation (start < end, start == end, start > end)
  - Time-range query with start_time only
  - Time-range query with end_time only
  - Time-range query with both start and end
  - Time-range query with limit
  - Time-range query returns records sorted by finalized_at descending
  - Empty store returns empty list
  - Receipt correlation all matched
  - Receipt correlation some unmatched
  - Receipt correlation no matches
  - Receipt correlation empty records
  - Receipt correlation empty receipts
  - Correlation report with matches and mismatches
  - Correlation report with time filter
  - Correlation report statistics accurate
  - Correlation report generated_at is set
  - JSON export is valid JSON
  - JSON export keys sorted deterministically
  - JSON export datetime as ISO strings

WSP 97 Critical Constraint:
  Time-range queries and receipt correlations are observability only.
  They do NOT mean:
    - automatic state progression
    - verification_complete=True
    - cabr_ready=True
    - payout_ready=True
    - payout approval
    - DAO activation
    - token issuance
    - external settlement

Slice: CABR_CONSENSUS_FINALIZATION_PHASE5_TIME_RANGE_RECEIPT_CORRELATION
Worker: W1
"""

from __future__ import annotations

import gc
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modules.communication.moltbot_bridge.src.cabr_consensus_reporting import (
    CABRReceiptCorrelation,
    CABRReceiptCorrelationReport,
    CABRTimeRangeFilter,
    correlate_consensus_records_to_receipts,
    export_receipt_correlation_report_json,
    generate_receipt_correlation_report,
    query_consensus_records_by_time,
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


# ---------------------------------------------------------------------------
# Test: Time Filter Validation
# ---------------------------------------------------------------------------


class TestTimeFilterValidation(unittest.TestCase):
    """Time filter validation tests."""

    def test_filter_valid_start_before_end(self):
        """Valid filter when start < end."""
        time_filter = CABRTimeRangeFilter(
            start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2026, 12, 31, tzinfo=timezone.utc),
        )
        self.assertTrue(time_filter.validate())

    def test_filter_valid_start_equals_end(self):
        """Valid filter when start == end (same moment)."""
        same_time = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        time_filter = CABRTimeRangeFilter(
            start_time=same_time,
            end_time=same_time,
        )
        self.assertTrue(time_filter.validate())

    def test_filter_invalid_start_after_end(self):
        """Invalid filter when start > end."""
        time_filter = CABRTimeRangeFilter(
            start_time=datetime(2026, 12, 31, tzinfo=timezone.utc),
            end_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        self.assertFalse(time_filter.validate())

    def test_filter_valid_start_only(self):
        """Valid filter with start_time only."""
        time_filter = CABRTimeRangeFilter(
            start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        self.assertTrue(time_filter.validate())

    def test_filter_valid_end_only(self):
        """Valid filter with end_time only."""
        time_filter = CABRTimeRangeFilter(
            end_time=datetime(2026, 12, 31, tzinfo=timezone.utc),
        )
        self.assertTrue(time_filter.validate())

    def test_filter_valid_empty(self):
        """Valid filter with no constraints."""
        time_filter = CABRTimeRangeFilter()
        self.assertTrue(time_filter.validate())

    def test_invalid_filter_raises_value_error(self):
        """Invalid time filter raises ValueError in query."""
        tmp_dir = TemporaryDirectory()
        try:
            db_path = Path(tmp_dir.name) / "test_consensus.db"
            store = CABRConsensusStore(db_path)
            store.initialize_schema()

            time_filter = CABRTimeRangeFilter(
                start_time=datetime(2026, 12, 31, tzinfo=timezone.utc),
                end_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

            with self.assertRaises(ValueError) as ctx:
                query_consensus_records_by_time(store, time_filter)

            self.assertIn("Invalid time filter", str(ctx.exception))
            store.close()
            gc.collect()
        finally:
            tmp_dir.cleanup()


# ---------------------------------------------------------------------------
# Test: Time-Range Query
# ---------------------------------------------------------------------------


class TestTimeRangeQuery(unittest.TestCase):
    """Time-range query tests."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert records with different finalized_at timestamps
        self.store.save_record(_make_consensus_record(
            record_id="ccr_jan",
            receipt_id="rcpt_jan",
            finalized_at="2026-01-15T10:00:00+00:00",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_mar",
            receipt_id="rcpt_mar",
            finalized_at="2026-03-15T10:00:00+00:00",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_jun",
            receipt_id="rcpt_jun",
            finalized_at="2026-06-15T10:00:00+00:00",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_sep",
            receipt_id="rcpt_sep",
            finalized_at="2026-09-15T10:00:00+00:00",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_dec",
            receipt_id="rcpt_dec",
            finalized_at="2026-12-15T10:00:00+00:00",
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_query_with_start_time_only(self):
        """Query with start_time only returns records >= start."""
        time_filter = CABRTimeRangeFilter(
            start_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        records = query_consensus_records_by_time(self.store, time_filter)

        # Should return Jun, Sep, Dec
        self.assertEqual(len(records), 3)
        record_ids = [r["record_id"] for r in records]
        self.assertIn("ccr_jun", record_ids)
        self.assertIn("ccr_sep", record_ids)
        self.assertIn("ccr_dec", record_ids)

    def test_query_with_end_time_only(self):
        """Query with end_time only returns records <= end."""
        time_filter = CABRTimeRangeFilter(
            end_time=datetime(2026, 4, 1, tzinfo=timezone.utc),
        )
        records = query_consensus_records_by_time(self.store, time_filter)

        # Should return Jan, Mar
        self.assertEqual(len(records), 2)
        record_ids = [r["record_id"] for r in records]
        self.assertIn("ccr_jan", record_ids)
        self.assertIn("ccr_mar", record_ids)

    def test_query_with_both_start_and_end(self):
        """Query with both start and end returns records in range."""
        time_filter = CABRTimeRangeFilter(
            start_time=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end_time=datetime(2026, 9, 30, tzinfo=timezone.utc),
        )
        records = query_consensus_records_by_time(self.store, time_filter)

        # Should return Mar, Jun, Sep
        self.assertEqual(len(records), 3)
        record_ids = [r["record_id"] for r in records]
        self.assertIn("ccr_mar", record_ids)
        self.assertIn("ccr_jun", record_ids)
        self.assertIn("ccr_sep", record_ids)
        self.assertNotIn("ccr_jan", record_ids)
        self.assertNotIn("ccr_dec", record_ids)

    def test_query_with_limit(self):
        """Query with limit returns at most limit records."""
        time_filter = CABRTimeRangeFilter(
            limit=2,
        )
        records = query_consensus_records_by_time(self.store, time_filter)

        # Should return 2 most recent
        self.assertEqual(len(records), 2)

    def test_query_sorted_descending(self):
        """Query returns records sorted by finalized_at descending."""
        records = query_consensus_records_by_time(self.store)

        # Dec should be first (most recent), Jan should be last
        self.assertEqual(len(records), 5)
        self.assertEqual(records[0]["record_id"], "ccr_dec")
        self.assertEqual(records[-1]["record_id"], "ccr_jan")

    def test_query_none_filter_returns_all(self):
        """Query with None filter returns all records."""
        records = query_consensus_records_by_time(self.store, None)

        self.assertEqual(len(records), 5)

    def test_query_empty_store_returns_empty_list(self):
        """Query on empty store returns empty list."""
        tmp_dir = TemporaryDirectory()
        try:
            db_path = Path(tmp_dir.name) / "empty_consensus.db"
            empty_store = CABRConsensusStore(db_path)
            empty_store.initialize_schema()

            records = query_consensus_records_by_time(empty_store)

            self.assertEqual(len(records), 0)
            empty_store.close()
            gc.collect()
        finally:
            tmp_dir.cleanup()

    def test_query_no_matches_in_range(self):
        """Query with no matches in range returns empty list."""
        time_filter = CABRTimeRangeFilter(
            start_time=datetime(2027, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2027, 12, 31, tzinfo=timezone.utc),
        )
        records = query_consensus_records_by_time(self.store, time_filter)

        self.assertEqual(len(records), 0)


# ---------------------------------------------------------------------------
# Test: Receipt Correlation
# ---------------------------------------------------------------------------


class TestReceiptCorrelation(unittest.TestCase):
    """Receipt correlation tests."""

    def test_correlate_all_matched(self):
        """All records have matching receipts."""
        records = [
            _make_consensus_record(
                record_id="ccr_001",
                receipt_id="rcpt_001",
            ),
            _make_consensus_record(
                record_id="ccr_002",
                receipt_id="rcpt_002",
            ),
        ]
        receipts = {
            "rcpt_001": {"data": "receipt 1"},
            "rcpt_002": {"data": "receipt 2"},
        }

        correlations = correlate_consensus_records_to_receipts(records, receipts)

        self.assertEqual(len(correlations), 2)
        for c in correlations:
            self.assertTrue(c.matched)

    def test_correlate_some_unmatched(self):
        """Some records have no matching receipts."""
        records = [
            _make_consensus_record(
                record_id="ccr_001",
                receipt_id="rcpt_001",
            ),
            _make_consensus_record(
                record_id="ccr_002",
                receipt_id="rcpt_missing",
            ),
            _make_consensus_record(
                record_id="ccr_003",
                receipt_id="rcpt_003",
            ),
        ]
        receipts = {
            "rcpt_001": {"data": "receipt 1"},
            "rcpt_003": {"data": "receipt 3"},
        }

        correlations = correlate_consensus_records_to_receipts(records, receipts)

        self.assertEqual(len(correlations), 3)
        self.assertTrue(correlations[0].matched)
        self.assertFalse(correlations[1].matched)
        self.assertTrue(correlations[2].matched)

    def test_correlate_none_matched(self):
        """No records have matching receipts."""
        records = [
            _make_consensus_record(
                record_id="ccr_001",
                receipt_id="rcpt_001",
            ),
            _make_consensus_record(
                record_id="ccr_002",
                receipt_id="rcpt_002",
            ),
        ]
        receipts = {
            "rcpt_other_001": {"data": "other receipt"},
        }

        correlations = correlate_consensus_records_to_receipts(records, receipts)

        self.assertEqual(len(correlations), 2)
        for c in correlations:
            self.assertFalse(c.matched)

    def test_correlate_empty_records(self):
        """Empty records list returns empty correlations."""
        receipts = {
            "rcpt_001": {"data": "receipt 1"},
        }

        correlations = correlate_consensus_records_to_receipts([], receipts)

        self.assertEqual(len(correlations), 0)

    def test_correlate_empty_receipts(self):
        """Empty receipts dict results in no matches."""
        records = [
            _make_consensus_record(
                record_id="ccr_001",
                receipt_id="rcpt_001",
            ),
        ]

        correlations = correlate_consensus_records_to_receipts(records, {})

        self.assertEqual(len(correlations), 1)
        self.assertFalse(correlations[0].matched)

    def test_correlate_preserves_order(self):
        """Correlations are in same order as input records."""
        records = [
            _make_consensus_record(record_id="ccr_aaa", receipt_id="rcpt_aaa"),
            _make_consensus_record(record_id="ccr_zzz", receipt_id="rcpt_zzz"),
            _make_consensus_record(record_id="ccr_mmm", receipt_id="rcpt_mmm"),
        ]
        receipts = {"rcpt_aaa": {}, "rcpt_zzz": {}, "rcpt_mmm": {}}

        correlations = correlate_consensus_records_to_receipts(records, receipts)

        self.assertEqual(correlations[0].record_id, "ccr_aaa")
        self.assertEqual(correlations[1].record_id, "ccr_zzz")
        self.assertEqual(correlations[2].record_id, "ccr_mmm")

    def test_correlation_has_decision(self):
        """Correlation includes decision value."""
        records = [
            _make_consensus_record(
                record_id="ccr_001",
                receipt_id="rcpt_001",
                decision="rejected",
            ),
        ]
        receipts = {"rcpt_001": {}}

        correlations = correlate_consensus_records_to_receipts(records, receipts)

        self.assertEqual(correlations[0].decision, "rejected")

    def test_correlation_has_finalized_at(self):
        """Correlation includes finalized_at datetime."""
        records = [
            _make_consensus_record(
                record_id="ccr_001",
                receipt_id="rcpt_001",
                finalized_at="2026-05-13T15:30:00+00:00",
            ),
        ]
        receipts = {"rcpt_001": {}}

        correlations = correlate_consensus_records_to_receipts(records, receipts)

        self.assertEqual(
            correlations[0].finalized_at,
            datetime(2026, 5, 13, 15, 30, 0, tzinfo=timezone.utc),
        )


# ---------------------------------------------------------------------------
# Test: Correlation Report
# ---------------------------------------------------------------------------


class TestCorrelationReport(unittest.TestCase):
    """Correlation report tests."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert records
        self.store.save_record(_make_consensus_record(
            record_id="ccr_001",
            receipt_id="rcpt_001",
            finalized_at="2026-03-15T10:00:00+00:00",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_002",
            receipt_id="rcpt_002",
            finalized_at="2026-06-15T10:00:00+00:00",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_003",
            receipt_id="rcpt_003",
            finalized_at="2026-09-15T10:00:00+00:00",
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_report_with_matches_and_mismatches(self):
        """Report correctly counts matches and mismatches."""
        receipts = {
            "rcpt_001": {"data": "receipt 1"},
            "rcpt_003": {"data": "receipt 3"},
        }

        report = generate_receipt_correlation_report(self.store, receipts)

        self.assertEqual(report.total_records, 3)
        self.assertEqual(report.matched_records, 2)
        self.assertEqual(report.unmatched_records, 1)

    def test_report_with_time_filter(self):
        """Report with time filter only includes filtered records."""
        receipts = {
            "rcpt_001": {},
            "rcpt_002": {},
            "rcpt_003": {},
        }
        time_filter = CABRTimeRangeFilter(
            start_time=datetime(2026, 5, 1, tzinfo=timezone.utc),
        )

        report = generate_receipt_correlation_report(
            self.store,
            receipts,
            time_filter=time_filter,
        )

        # Only Jun and Sep records
        self.assertEqual(report.total_records, 2)
        self.assertEqual(report.matched_records, 2)

    def test_report_statistics_accurate(self):
        """Report statistics match correlations list."""
        receipts = {"rcpt_001": {}}

        report = generate_receipt_correlation_report(self.store, receipts)

        # Verify stats match actual correlations
        actual_matched = sum(1 for c in report.correlations if c.matched)
        actual_unmatched = sum(1 for c in report.correlations if not c.matched)

        self.assertEqual(report.matched_records, actual_matched)
        self.assertEqual(report.unmatched_records, actual_unmatched)
        self.assertEqual(report.total_records, len(report.correlations))

    def test_report_generated_at_is_set(self):
        """Report has generated_at timestamp."""
        report = generate_receipt_correlation_report(self.store, {})

        self.assertIsNotNone(report.generated_at)
        self.assertIsInstance(report.generated_at, datetime)

    def test_report_has_wsp97_note(self):
        """Report includes WSP 97 compliance note."""
        report = generate_receipt_correlation_report(self.store, {})

        self.assertIn("WSP 97", report.wsp97_compliance_note)
        self.assertIn("observability only", report.wsp97_compliance_note)

    def test_report_time_filter_preserved(self):
        """Report preserves time filter in output."""
        time_filter = CABRTimeRangeFilter(
            start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2026, 12, 31, tzinfo=timezone.utc),
            limit=10,
        )

        report = generate_receipt_correlation_report(
            self.store,
            {},
            time_filter=time_filter,
        )

        self.assertIsNotNone(report.time_filter)
        self.assertEqual(report.time_filter.start_time, time_filter.start_time)
        self.assertEqual(report.time_filter.end_time, time_filter.end_time)
        self.assertEqual(report.time_filter.limit, time_filter.limit)


# ---------------------------------------------------------------------------
# Test: JSON Export
# ---------------------------------------------------------------------------


class TestReceiptCorrelationJsonExport(unittest.TestCase):
    """JSON export tests for receipt correlation report."""

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

    def test_export_is_valid_json(self):
        """Export produces valid JSON."""
        receipts = {"rcpt_001": {}}
        report = generate_receipt_correlation_report(self.store, receipts)
        json_str = export_receipt_correlation_report_json(report)

        parsed = json.loads(json_str)
        self.assertIn("total_records", parsed)
        self.assertIn("matched_records", parsed)
        self.assertIn("unmatched_records", parsed)
        self.assertIn("correlations", parsed)

    def test_export_keys_sorted_deterministically(self):
        """JSON export has sorted keys for determinism."""
        receipts = {"rcpt_001": {}}
        report = generate_receipt_correlation_report(self.store, receipts)
        json_str = export_receipt_correlation_report_json(report)

        parsed = json.loads(json_str)
        top_keys = list(parsed.keys())
        self.assertEqual(top_keys, sorted(top_keys))

    def test_export_datetime_as_iso_strings(self):
        """Datetime fields exported as ISO strings."""
        receipts = {"rcpt_001": {}}
        report = generate_receipt_correlation_report(self.store, receipts)
        json_str = export_receipt_correlation_report_json(report)

        parsed = json.loads(json_str)

        # generated_at should be ISO string
        generated_at = parsed["generated_at"]
        self.assertIsInstance(generated_at, str)
        # Should be parseable
        datetime.fromisoformat(generated_at.replace("Z", "+00:00"))

        # Correlation finalized_at should be ISO string
        if parsed["correlations"]:
            finalized_at = parsed["correlations"][0]["finalized_at"]
            self.assertIsInstance(finalized_at, str)

    def test_export_deterministic(self):
        """Same report produces same JSON output."""
        receipts = {"rcpt_001": {}}
        report = generate_receipt_correlation_report(self.store, receipts)

        json1 = export_receipt_correlation_report_json(report)
        json2 = export_receipt_correlation_report_json(report)

        self.assertEqual(json1, json2)

    def test_export_includes_time_filter(self):
        """Export includes time filter when present."""
        time_filter = CABRTimeRangeFilter(
            start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2026, 12, 31, tzinfo=timezone.utc),
        )
        receipts = {"rcpt_001": {}}
        report = generate_receipt_correlation_report(
            self.store,
            receipts,
            time_filter=time_filter,
        )
        json_str = export_receipt_correlation_report_json(report)

        parsed = json.loads(json_str)
        self.assertIsNotNone(parsed["time_filter"])
        self.assertIn("start_time", parsed["time_filter"])
        self.assertIn("end_time", parsed["time_filter"])

    def test_export_time_filter_none(self):
        """Export handles None time filter."""
        receipts = {"rcpt_001": {}}
        report = generate_receipt_correlation_report(self.store, receipts)
        json_str = export_receipt_correlation_report_json(report)

        parsed = json.loads(json_str)
        self.assertIsNone(parsed["time_filter"])

    def test_export_includes_wsp97_note(self):
        """JSON export includes WSP 97 compliance note."""
        receipts = {}
        report = generate_receipt_correlation_report(self.store, receipts)
        json_str = export_receipt_correlation_report_json(report)

        parsed = json.loads(json_str)
        self.assertIn("WSP 97", parsed["wsp97_compliance_note"])


# ---------------------------------------------------------------------------
# Test: Correlation Dataclass
# ---------------------------------------------------------------------------


class TestCorrelationDataclass(unittest.TestCase):
    """Correlation dataclass tests."""

    def test_correlation_to_dict(self):
        """CABRReceiptCorrelation serializes to dict."""
        correlation = CABRReceiptCorrelation(
            record_id="ccr_001",
            receipt_id="rcpt_001",
            matched=True,
            decision="accepted_for_review",
            finalized_at=datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc),
        )

        d = correlation.to_dict()

        self.assertEqual(d["record_id"], "ccr_001")
        self.assertEqual(d["receipt_id"], "rcpt_001")
        self.assertTrue(d["matched"])
        self.assertEqual(d["decision"], "accepted_for_review")
        self.assertIn("2026-05-13", d["finalized_at"])

    def test_correlation_receipt_id_none(self):
        """Correlation handles None receipt_id."""
        correlation = CABRReceiptCorrelation(
            record_id="ccr_001",
            receipt_id=None,
            matched=False,
            decision="rejected",
            finalized_at=datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc),
        )

        d = correlation.to_dict()

        self.assertIsNone(d["receipt_id"])
        self.assertFalse(d["matched"])


# ---------------------------------------------------------------------------
# Test: Correlation Report Dataclass
# ---------------------------------------------------------------------------


class TestCorrelationReportDataclass(unittest.TestCase):
    """Correlation report dataclass tests."""

    def test_report_to_dict(self):
        """CABRReceiptCorrelationReport serializes to dict."""
        correlation = CABRReceiptCorrelation(
            record_id="ccr_001",
            receipt_id="rcpt_001",
            matched=True,
            decision="accepted_for_review",
            finalized_at=datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc),
        )
        report = CABRReceiptCorrelationReport(
            time_filter=None,
            total_records=1,
            matched_records=1,
            unmatched_records=0,
            correlations=[correlation],
        )

        d = report.to_dict()

        self.assertIsNone(d["time_filter"])
        self.assertEqual(d["total_records"], 1)
        self.assertEqual(d["matched_records"], 1)
        self.assertEqual(d["unmatched_records"], 0)
        self.assertEqual(len(d["correlations"]), 1)
        self.assertIn("generated_at", d)
        self.assertIn("wsp97_compliance_note", d)

    def test_report_to_dict_with_time_filter(self):
        """Report to_dict includes time filter details."""
        time_filter = CABRTimeRangeFilter(
            start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2026, 12, 31, tzinfo=timezone.utc),
            limit=100,
        )
        report = CABRReceiptCorrelationReport(
            time_filter=time_filter,
            total_records=0,
            matched_records=0,
            unmatched_records=0,
            correlations=[],
        )

        d = report.to_dict()

        self.assertIsNotNone(d["time_filter"])
        self.assertIn("start_time", d["time_filter"])
        self.assertIn("end_time", d["time_filter"])
        self.assertEqual(d["time_filter"]["limit"], 100)


# ---------------------------------------------------------------------------
# Test: WSP 97 Truth Boundaries
# ---------------------------------------------------------------------------


class TestWSP97TruthBoundaries(unittest.TestCase):
    """WSP 97 truth boundary tests for Phase 5."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert records with all truth fields False
        for i in range(3):
            self.store.save_record(_make_consensus_record(
                record_id=f"ccr_{i:03d}",
                receipt_id=f"rcpt_{i:03d}",
                verification_complete=False,
                cabr_ready=False,
                payout_ready=False,
            ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_correlation_report_does_not_set_verification_complete(self):
        """Correlation report does not imply verification_complete=True."""
        receipts = {"rcpt_000": {}, "rcpt_001": {}, "rcpt_002": {}}
        report = generate_receipt_correlation_report(self.store, receipts)

        # All matched, but still no verification_complete
        self.assertEqual(report.matched_records, 3)
        # Report has no verification_complete field
        d = report.to_dict()
        self.assertNotIn("verification_complete", d)

    def test_correlation_report_does_not_set_cabr_ready(self):
        """Correlation report does not imply cabr_ready=True."""
        receipts = {"rcpt_000": {}, "rcpt_001": {}, "rcpt_002": {}}
        report = generate_receipt_correlation_report(self.store, receipts)

        d = report.to_dict()
        self.assertNotIn("cabr_ready", d)

    def test_correlation_report_does_not_set_payout_ready(self):
        """Correlation report does not imply payout_ready=True."""
        receipts = {"rcpt_000": {}, "rcpt_001": {}, "rcpt_002": {}}
        report = generate_receipt_correlation_report(self.store, receipts)

        d = report.to_dict()
        self.assertNotIn("payout_ready", d)

    def test_json_export_has_no_payout_fields(self):
        """JSON export does not include payout fields."""
        receipts = {"rcpt_000": {}}
        report = generate_receipt_correlation_report(self.store, receipts)
        json_str = export_receipt_correlation_report_json(report)

        self.assertNotIn("payout_amount", json_str)
        self.assertNotIn("total_payout", json_str)
        self.assertNotIn("tokens_issued", json_str)


# ---------------------------------------------------------------------------
# Test: Generate Requires Store
# ---------------------------------------------------------------------------


class TestGenerateRequiresStore(unittest.TestCase):
    """Tests that functions require store parameter."""

    def test_generate_correlation_report_requires_store(self):
        """generate_receipt_correlation_report requires store parameter."""
        with self.assertRaises(TypeError):
            generate_receipt_correlation_report(receipts={})  # type: ignore

    def test_query_by_time_requires_store(self):
        """query_consensus_records_by_time requires store parameter."""
        with self.assertRaises(TypeError):
            query_consensus_records_by_time()  # type: ignore


if __name__ == "__main__":
    unittest.main(verbosity=2)
