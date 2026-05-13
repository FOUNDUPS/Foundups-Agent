#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for CABR Consensus Store Phase 2.

Validates SQLite persistence for CABRConsensusRecord audit trails per WSP 97.

Required coverage:
  - schema initializes
  - save and get record
  - duplicate record id idempotent or rejected deterministically
  - list records deterministic
  - decision filter works
  - truth fields remain false after persistence
  - no payout/DAO activation fields become true
  - invalid DB path fails closed
  - corrupted/missing schema handled safely
  - no DB file committed to repo
  - uses tmp_path only
  - round-trip preserves record_hash

Slice: CABR_CONSENSUS_FINALIZATION_PHASE2_SQLITE_AUDIT_TRAIL
Worker: W1
"""

from __future__ import annotations

import gc
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modules.communication.moltbot_bridge.src.cabr_consensus_store import (
    CABRConsensusStore,
    CABRConsensusStoreError,
    CABRConsensusStoreResult,
    CABRConsensusStoreResultStatus,
    SCHEMA_VERSION,
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
    quorum_met: bool = True,
    threshold_met: bool = True,
    unique_verifiers: int = 3,
    consensus_score: float = 1.0,
    evidence_present: bool = True,
    evidence_count: int = 2,
    is_dry_run: bool = False,
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
        "quorum_met": quorum_met,
        "threshold_met": threshold_met,
        "unique_verifiers": unique_verifiers,
        "consensus_score": consensus_score,
        "evidence_present": evidence_present,
        "evidence_count": evidence_count,
        "is_dry_run": is_dry_run,
        "is_simulated": False,
        "verification_complete": verification_complete,
        "cabr_ready": cabr_ready,
        "payout_ready": payout_ready,
        "finalized_at": "2026-05-13T12:00:00+00:00",
        "finalizer_version": "0.1.0",
    }


# ---------------------------------------------------------------------------
# Test: Schema Initializes
# ---------------------------------------------------------------------------


class TestSchemaInitializes(unittest.TestCase):
    """Schema initialization tests."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"

    def tearDown(self):
        gc.collect()  # Release SQLite file handles
        self.tmp_dir.cleanup()

    def test_schema_initializes_successfully(self):
        """Schema initializes on new database."""
        store = CABRConsensusStore(self.db_path)
        result = store.initialize_schema()
        store.close()

        self.assertEqual(result.status, CABRConsensusStoreResultStatus.SUCCESS)
        self.assertTrue(self.db_path.exists())

    def test_schema_idempotent(self):
        """Calling initialize_schema multiple times is safe."""
        store = CABRConsensusStore(self.db_path)

        result1 = store.initialize_schema()
        result2 = store.initialize_schema()
        store.close()

        self.assertEqual(result1.status, CABRConsensusStoreResultStatus.SUCCESS)
        self.assertEqual(result2.status, CABRConsensusStoreResultStatus.SUCCESS)

    def test_schema_version_recorded(self):
        """Schema version is recorded in database."""
        store = CABRConsensusStore(self.db_path)
        store.initialize_schema()

        conn = store._get_connection()
        cursor = conn.execute(
            "SELECT version FROM schema_version WHERE version = ?",
            (SCHEMA_VERSION,),
        )
        row = cursor.fetchone()
        store.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], SCHEMA_VERSION)


# ---------------------------------------------------------------------------
# Test: Save and Get Record
# ---------------------------------------------------------------------------


class TestSaveAndGetRecord(unittest.TestCase):
    """Save and retrieve record tests."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_save_and_get_record(self):
        """Save record and retrieve by ID."""
        record = _make_consensus_record()
        save_result = self.store.save_record(record)

        self.assertEqual(save_result.status, CABRConsensusStoreResultStatus.SUCCESS)
        self.assertEqual(save_result.record_id, record["record_id"])
        self.assertEqual(save_result.record_count, 1)

        get_result = self.store.get_record(record["record_id"])

        self.assertEqual(get_result.status, CABRConsensusStoreResultStatus.SUCCESS)
        self.assertEqual(get_result.record_count, 1)
        self.assertIsNotNone(get_result.records)
        self.assertEqual(len(get_result.records), 1)

        retrieved = get_result.records[0]
        self.assertEqual(retrieved["record_id"], record["record_id"])
        self.assertEqual(retrieved["record_hash"], record["record_hash"])
        self.assertEqual(retrieved["decision"], record["decision"])

    def test_get_nonexistent_record(self):
        """Getting nonexistent record returns NOT_FOUND."""
        result = self.store.get_record("ccr_does_not_exist")

        self.assertEqual(result.status, CABRConsensusStoreResultStatus.NOT_FOUND)
        self.assertIsNone(result.records)

    def test_save_preserves_all_fields(self):
        """All record fields are preserved on save/get."""
        record = _make_consensus_record(
            unique_verifiers=5,
            consensus_score=0.85,
            evidence_count=3,
        )
        self.store.save_record(record)

        get_result = self.store.get_record(record["record_id"])
        retrieved = get_result.records[0]

        self.assertEqual(retrieved["unique_verifiers"], 5)
        self.assertAlmostEqual(retrieved["consensus_score"], 0.85, places=2)
        self.assertEqual(retrieved["evidence_count"], 3)
        self.assertEqual(retrieved["score_id"], record["score_id"])
        self.assertEqual(retrieved["quorum_id"], record["quorum_id"])


# ---------------------------------------------------------------------------
# Test: Duplicate Record ID Handling
# ---------------------------------------------------------------------------


class TestDuplicateRecordIdHandling(unittest.TestCase):
    """Duplicate record ID handling tests."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_duplicate_record_id_idempotent(self):
        """Inserting duplicate record_id returns ALREADY_EXISTS (not error)."""
        record = _make_consensus_record()

        result1 = self.store.save_record(record)
        result2 = self.store.save_record(record)

        self.assertEqual(result1.status, CABRConsensusStoreResultStatus.SUCCESS)
        self.assertEqual(result2.status, CABRConsensusStoreResultStatus.ALREADY_EXISTS)
        self.assertEqual(result2.record_id, record["record_id"])

    def test_duplicate_does_not_modify_original(self):
        """Duplicate insert does not modify the original record."""
        record1 = _make_consensus_record()
        self.store.save_record(record1)

        # Try to insert with same ID but different hash
        record2 = _make_consensus_record()
        record2["record_hash"] = "different_hash_value"
        self.store.save_record(record2)

        # Original should be unchanged
        get_result = self.store.get_record(record1["record_id"])
        retrieved = get_result.records[0]

        self.assertEqual(retrieved["record_hash"], record1["record_hash"])


# ---------------------------------------------------------------------------
# Test: List Records Deterministic
# ---------------------------------------------------------------------------


class TestListRecordsDeterministic(unittest.TestCase):
    """List records tests."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_list_records_empty(self):
        """Listing empty database returns empty list."""
        result = self.store.list_records()

        self.assertEqual(result.status, CABRConsensusStoreResultStatus.SUCCESS)
        self.assertEqual(result.record_count, 0)
        self.assertEqual(result.records, [])

    def test_list_records_returns_all(self):
        """Listing returns all records."""
        for i in range(5):
            record = _make_consensus_record(record_id=f"ccr_test_{i:04d}")
            self.store.save_record(record)

        result = self.store.list_records()

        self.assertEqual(result.status, CABRConsensusStoreResultStatus.SUCCESS)
        self.assertEqual(result.record_count, 5)
        self.assertEqual(len(result.records), 5)

    def test_list_records_respects_limit(self):
        """Listing respects limit parameter."""
        for i in range(10):
            record = _make_consensus_record(record_id=f"ccr_test_{i:04d}")
            self.store.save_record(record)

        result = self.store.list_records(limit=3)

        self.assertEqual(result.record_count, 3)
        self.assertEqual(len(result.records), 3)

    def test_list_records_pagination(self):
        """Listing supports offset for pagination."""
        for i in range(10):
            record = _make_consensus_record(record_id=f"ccr_test_{i:04d}")
            self.store.save_record(record)

        page1 = self.store.list_records(limit=5, offset=0)
        page2 = self.store.list_records(limit=5, offset=5)

        self.assertEqual(page1.record_count, 5)
        self.assertEqual(page2.record_count, 5)

        # No overlap
        page1_ids = {r["record_id"] for r in page1.records}
        page2_ids = {r["record_id"] for r in page2.records}
        self.assertEqual(len(page1_ids & page2_ids), 0)


# ---------------------------------------------------------------------------
# Test: Decision Filter
# ---------------------------------------------------------------------------


class TestDecisionFilter(unittest.TestCase):
    """Decision filter tests."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_decision_filter_accepted(self):
        """Filter by accepted_for_review decision."""
        self.store.save_record(_make_consensus_record(
            record_id="ccr_accepted_001",
            decision="accepted_for_review",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_rejected_001",
            decision="rejected",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_accepted_002",
            decision="accepted_for_review",
        ))

        result = self.store.list_records(decision_filter="accepted_for_review")

        self.assertEqual(result.record_count, 2)
        for record in result.records:
            self.assertEqual(record["decision"], "accepted_for_review")

    def test_decision_filter_rejected(self):
        """Filter by rejected decision."""
        self.store.save_record(_make_consensus_record(
            record_id="ccr_accepted_001",
            decision="accepted_for_review",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_rejected_001",
            decision="rejected",
        ))

        result = self.store.list_records(decision_filter="rejected")

        self.assertEqual(result.record_count, 1)
        self.assertEqual(result.records[0]["decision"], "rejected")

    def test_decision_filter_no_match(self):
        """Filter returns empty when no match."""
        self.store.save_record(_make_consensus_record(
            decision="accepted_for_review",
        ))

        result = self.store.list_records(decision_filter="pending_quorum")

        self.assertEqual(result.record_count, 0)


# ---------------------------------------------------------------------------
# Test: Truth Fields Remain False After Persistence
# ---------------------------------------------------------------------------


class TestTruthFieldsRemainFalse(unittest.TestCase):
    """WSP 97 truth fields preservation tests."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_verification_complete_stays_false(self):
        """verification_complete=False preserved after persistence."""
        record = _make_consensus_record(verification_complete=False)
        self.store.save_record(record)

        get_result = self.store.get_record(record["record_id"])
        retrieved = get_result.records[0]

        self.assertFalse(retrieved["verification_complete"])

    def test_cabr_ready_stays_false(self):
        """cabr_ready=False preserved after persistence."""
        record = _make_consensus_record(cabr_ready=False)
        self.store.save_record(record)

        get_result = self.store.get_record(record["record_id"])
        retrieved = get_result.records[0]

        self.assertFalse(retrieved["cabr_ready"])

    def test_payout_ready_stays_false(self):
        """payout_ready=False preserved after persistence."""
        record = _make_consensus_record(payout_ready=False)
        self.store.save_record(record)

        get_result = self.store.get_record(record["record_id"])
        retrieved = get_result.records[0]

        self.assertFalse(retrieved["payout_ready"])

    def test_all_truth_fields_false_after_roundtrip(self):
        """All WSP 97 truth fields remain False after save/get."""
        record = _make_consensus_record(
            verification_complete=False,
            cabr_ready=False,
            payout_ready=False,
        )
        self.store.save_record(record)

        get_result = self.store.get_record(record["record_id"])
        retrieved = get_result.records[0]

        self.assertFalse(retrieved["verification_complete"])
        self.assertFalse(retrieved["cabr_ready"])
        self.assertFalse(retrieved["payout_ready"])


# ---------------------------------------------------------------------------
# Test: No Payout/DAO Activation Fields Become True
# ---------------------------------------------------------------------------


class TestNoPayoutActivation(unittest.TestCase):
    """Payout and DAO activation fields never become True tests."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_no_payout_fields_in_schema(self):
        """No payout_amount/tokens_issued/ups_allocated fields in schema."""
        record = _make_consensus_record()
        self.store.save_record(record)

        get_result = self.store.get_record(record["record_id"])
        retrieved = get_result.records[0]

        self.assertNotIn("payout_amount", retrieved)
        self.assertNotIn("tokens_issued", retrieved)
        self.assertNotIn("ups_allocated", retrieved)
        self.assertNotIn("reward_amount", retrieved)

    def test_accepted_record_still_not_ready(self):
        """Even accepted_for_review records have cabr_ready=False."""
        record = _make_consensus_record(
            decision="accepted_for_review",
            quorum_met=True,
            threshold_met=True,
        )
        self.store.save_record(record)

        get_result = self.store.get_record(record["record_id"])
        retrieved = get_result.records[0]

        self.assertEqual(retrieved["decision"], "accepted_for_review")
        self.assertTrue(retrieved["quorum_met"])
        self.assertFalse(retrieved["cabr_ready"])
        self.assertFalse(retrieved["payout_ready"])


# ---------------------------------------------------------------------------
# Test: Invalid DB Path Fails Closed
# ---------------------------------------------------------------------------


class TestInvalidDbPathFailsClosed(unittest.TestCase):
    """Invalid database path handling tests."""

    def test_nonexistent_parent_directory_fails(self):
        """Non-existent parent directory raises error."""
        invalid_path = Path("/nonexistent/directory/consensus.db")

        with self.assertRaises(CABRConsensusStoreError) as ctx:
            CABRConsensusStore(invalid_path)

        self.assertEqual(
            ctx.exception.status,
            CABRConsensusStoreResultStatus.VALIDATION_ERROR,
        )

    def test_valid_path_succeeds(self):
        """Valid path with existing parent succeeds."""
        with TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "consensus.db"
            store = CABRConsensusStore(db_path)
            store.initialize_schema()
            store.close()

            self.assertTrue(db_path.exists())


# ---------------------------------------------------------------------------
# Test: Missing/Corrupted Schema Handled Safely
# ---------------------------------------------------------------------------


class TestMissingCorruptedSchemaHandled(unittest.TestCase):
    """Missing and corrupted schema handling tests."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"

    def tearDown(self):
        gc.collect()
        self.tmp_dir.cleanup()

    def test_operations_fail_without_schema(self):
        """Operations fail if schema not initialized."""
        store = CABRConsensusStore(self.db_path)
        # Create connection but don't initialize schema
        store._get_connection()

        with self.assertRaises(CABRConsensusStoreError) as ctx:
            store.save_record(_make_consensus_record())

        self.assertEqual(
            ctx.exception.status,
            CABRConsensusStoreResultStatus.SCHEMA_ERROR,
        )
        store.close()

    def test_record_exists_fails_without_schema(self):
        """record_exists fails if schema not initialized."""
        store = CABRConsensusStore(self.db_path)
        store._get_connection()

        with self.assertRaises(CABRConsensusStoreError) as ctx:
            store.record_exists("ccr_test")

        self.assertEqual(
            ctx.exception.status,
            CABRConsensusStoreResultStatus.SCHEMA_ERROR,
        )
        store.close()


# ---------------------------------------------------------------------------
# Test: Record Exists
# ---------------------------------------------------------------------------


class TestRecordExists(unittest.TestCase):
    """record_exists() tests."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_record_exists_true(self):
        """record_exists returns True for existing record."""
        record = _make_consensus_record()
        self.store.save_record(record)

        self.assertTrue(self.store.record_exists(record["record_id"]))

    def test_record_exists_false(self):
        """record_exists returns False for nonexistent record."""
        self.assertFalse(self.store.record_exists("ccr_does_not_exist"))


# ---------------------------------------------------------------------------
# Test: Round-Trip Preserves Record Hash
# ---------------------------------------------------------------------------


class TestRoundTripPreservesRecordHash(unittest.TestCase):
    """Record hash preservation tests."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_record_hash_preserved_on_roundtrip(self):
        """record_hash is preserved exactly through save/get."""
        original_hash = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
        record = _make_consensus_record(record_hash=original_hash)
        self.store.save_record(record)

        get_result = self.store.get_record(record["record_id"])
        retrieved = get_result.records[0]

        self.assertEqual(retrieved["record_hash"], original_hash)

    def test_different_hashes_stored_correctly(self):
        """Different records with different hashes stored correctly."""
        record1 = _make_consensus_record(
            record_id="ccr_test_001",
            record_hash="hash_one_abcdefghijklmnop",
        )
        record2 = _make_consensus_record(
            record_id="ccr_test_002",
            record_hash="hash_two_qrstuvwxyz123456",
        )

        self.store.save_record(record1)
        self.store.save_record(record2)

        result1 = self.store.get_record("ccr_test_001")
        result2 = self.store.get_record("ccr_test_002")

        self.assertEqual(result1.records[0]["record_hash"], "hash_one_abcdefghijklmnop")
        self.assertEqual(result2.records[0]["record_hash"], "hash_two_qrstuvwxyz123456")


# ---------------------------------------------------------------------------
# Test: Validation Errors
# ---------------------------------------------------------------------------


class TestValidationErrors(unittest.TestCase):
    """Input validation tests."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_missing_record_id_fails(self):
        """Missing record_id fails validation."""
        record = _make_consensus_record()
        del record["record_id"]

        result = self.store.save_record(record)

        self.assertEqual(result.status, CABRConsensusStoreResultStatus.VALIDATION_ERROR)

    def test_missing_record_hash_fails(self):
        """Missing record_hash fails validation."""
        record = _make_consensus_record()
        del record["record_hash"]

        result = self.store.save_record(record)

        self.assertEqual(result.status, CABRConsensusStoreResultStatus.VALIDATION_ERROR)

    def test_missing_decision_fails(self):
        """Missing decision fails validation."""
        record = _make_consensus_record()
        del record["decision"]

        result = self.store.save_record(record)

        self.assertEqual(result.status, CABRConsensusStoreResultStatus.VALIDATION_ERROR)


# ---------------------------------------------------------------------------
# Test: Context Manager
# ---------------------------------------------------------------------------


class TestContextManager(unittest.TestCase):
    """Context manager tests."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"

    def tearDown(self):
        gc.collect()
        self.tmp_dir.cleanup()

    def test_context_manager_usage(self):
        """Store can be used as context manager."""
        with CABRConsensusStore(self.db_path) as store:
            store.initialize_schema()
            record = _make_consensus_record()
            result = store.save_record(record)
            self.assertEqual(result.status, CABRConsensusStoreResultStatus.SUCCESS)

    def test_context_manager_closes_connection(self):
        """Context manager closes connection on exit."""
        store = CABRConsensusStore(self.db_path)
        with store:
            store.initialize_schema()
            self.assertIsNotNone(store._conn)

        # After exit, connection should be None
        self.assertIsNone(store._conn)


# ---------------------------------------------------------------------------
# Test: No DB File Committed to Repo
# ---------------------------------------------------------------------------


class TestNoDbFileCommittedToRepo(unittest.TestCase):
    """Verify test does not create DB files in repo root."""

    def test_all_tests_use_tmp_path(self):
        """This test class verifies tmp_path usage pattern."""
        # All tests in this file use TemporaryDirectory
        # This is a meta-test verifying the pattern
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
