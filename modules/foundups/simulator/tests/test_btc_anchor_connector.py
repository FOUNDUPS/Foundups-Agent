"""Tests for Layer-D BTC Anchor Connector."""

from __future__ import annotations

import tempfile
import copy
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pathlib import Path

import pytest

from modules.foundups.simulator.economics.btc_anchor_connector import (
    AnchorMode,
    AnchorStatus,
    BTCAnchorConnector,
    get_anchor_connector,
    reset_anchor_connector,
)
from modules.foundups.simulator.economics.epoch_ledger import EpochLedger
from modules.foundups.simulator.economics import btc_anchor_connector as anchor_module


@pytest.fixture
def temp_db():
    """Provide temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yield Path(f.name)


@pytest.fixture
def connector(temp_db):
    """Create test connector with temp database."""
    reset_anchor_connector()
    conn = BTCAnchorConnector(mode=AnchorMode.MOCK, db_path=temp_db)
    yield conn
    reset_anchor_connector()


@pytest.fixture
def sample_commitment():
    """Sample pre-settlement commitment payload."""
    return {
        "format_version": "foundups.epoch.v2",
        "status": "pre_settlement",
        "wsp_78_layer": "D_pending",
        "requires": "external_btc_anchor_connector",
        "foundup_id": "foundup_test",
        "epoch": 1,
        "anchor_hex": "a" * 40,  # 40 hex chars
        "merkle_root": "b" * 64,
        "entry_hash": "c" * 64,
        "total_distributed": 1000.0,
        "participant_count": 5,
        "timestamp": "2026-02-22T12:00:00Z",
    }


class TestMockPublishing:
    """Tests for mock publishing mode."""

    def test_publish_commitment_returns_success(self, connector, sample_commitment):
        """Mock publishing should succeed and return tx_ref."""
        result = connector.publish_commitment(sample_commitment)

        assert result["success"] is True
        assert result["tx_ref"] is not None
        assert len(result["tx_ref"]) == 64  # SHA-256 hex
        assert result["status"] == AnchorStatus.PUBLISHED.value
        assert result["idempotent_hit"] is False

    def test_publish_generates_deterministic_tx_ref(self, connector, sample_commitment):
        """Same commitment should generate same tx_ref."""
        result1 = connector.publish_commitment(sample_commitment)
        tx_ref1 = result1["tx_ref"]

        # Create new connector with same data - should get same mock tx_ref
        reset_anchor_connector()
        connector2 = BTCAnchorConnector(mode=AnchorMode.MOCK, db_path=connector.db_path)
        result2 = connector2.publish_commitment(sample_commitment, force=True)
        tx_ref2 = result2["tx_ref"]

        assert tx_ref1 == tx_ref2

    def test_invalid_commitment_status_fails(self, connector):
        """Commitment with wrong status should fail."""
        invalid = {"status": "invalid", "foundup_id": "x", "epoch": 1}
        result = connector.publish_commitment(invalid)

        assert result["success"] is False
        assert "pre_settlement" in result["error"]

    def test_invalid_anchor_hex_fails(self, connector, sample_commitment):
        """Commitment with wrong anchor_hex length should fail."""
        sample_commitment["anchor_hex"] = "short"
        result = connector.publish_commitment(sample_commitment)

        assert result["success"] is False
        assert "anchor_hex" in result["error"]


class TestIdempotentReplayGuard:
    """Tests for idempotent replay guard."""

    def test_second_publish_returns_existing_tx_ref(self, connector, sample_commitment):
        """Re-publishing same epoch should return existing tx_ref."""
        result1 = connector.publish_commitment(sample_commitment)
        tx_ref1 = result1["tx_ref"]

        result2 = connector.publish_commitment(sample_commitment)

        assert result2["success"] is True
        assert result2["tx_ref"] == tx_ref1
        assert result2["idempotent_hit"] is True
        assert result2["status"] == AnchorStatus.PUBLISHED.value

    def test_replay_guard_increments_stats(self, connector, sample_commitment):
        """Replay guard should increment statistics."""
        connector.publish_commitment(sample_commitment)
        connector.publish_commitment(sample_commitment)
        connector.publish_commitment(sample_commitment)

        stats = connector.get_stats()
        assert stats["replay_guards_triggered"] == 2
        assert stats["total_published"] == 1

    def test_force_bypasses_replay_guard(self, connector, sample_commitment):
        """Force flag should allow re-publishing."""
        result1 = connector.publish_commitment(sample_commitment)
        result2 = connector.publish_commitment(sample_commitment, force=True)

        assert result2["success"] is True
        assert result2["idempotent_hit"] is False
        # Stats show 2 publishes
        stats = connector.get_stats()
        assert stats["total_published"] == 2

    def test_different_epochs_not_blocked(self, connector, sample_commitment):
        """Different epochs should not trigger replay guard."""
        result1 = connector.publish_commitment(sample_commitment)

        sample_commitment["epoch"] = 2
        result2 = connector.publish_commitment(sample_commitment)

        assert result1["success"] is True
        assert result2["success"] is True
        assert result1["tx_ref"] != result2["tx_ref"]
        assert result2["idempotent_hit"] is False


class TestTxRefPersistence:
    """Tests for tx_ref persistence."""

    def test_tx_ref_persists_across_restarts(self, temp_db, sample_commitment):
        """tx_ref should persist when connector is recreated."""
        connector1 = BTCAnchorConnector(mode=AnchorMode.MOCK, db_path=temp_db)
        result1 = connector1.publish_commitment(sample_commitment)
        tx_ref1 = result1["tx_ref"]

        # "Restart" - create new connector
        connector2 = BTCAnchorConnector(mode=AnchorMode.MOCK, db_path=temp_db)
        records = connector2.get_anchor_status("foundup_test", epoch=1)

        assert len(records) == 1
        assert records[0]["tx_ref"] == tx_ref1
        assert records[0]["status"] == AnchorStatus.PUBLISHED.value

    def test_get_anchor_status_returns_all_epochs(self, connector, sample_commitment):
        """get_anchor_status without epoch returns all."""
        for epoch in [1, 2, 3]:
            sample_commitment["epoch"] = epoch
            connector.publish_commitment(sample_commitment)

        records = connector.get_anchor_status("foundup_test")

        assert len(records) == 3
        assert [r["epoch"] for r in records] == [1, 2, 3]


class TestConfirmationChecking:
    """Tests for confirmation checking."""

    def test_check_confirmation_on_unpublished(self, connector):
        """Checking unpublished epoch returns not found."""
        result = connector.check_confirmation("foundup_x", epoch=99)

        assert result["found"] is False

    def test_mock_confirmation_increments(self, connector, sample_commitment):
        """Mock mode should increment confirmations on each check."""
        connector.publish_commitment(sample_commitment)

        result1 = connector.check_confirmation("foundup_test", epoch=1)
        assert result1["confirmations"] == 1
        assert result1["confirmed"] is False

        result2 = connector.check_confirmation("foundup_test", epoch=1)
        assert result2["confirmations"] == 2

    def test_confirmation_threshold_triggers_confirmed_status(
        self, connector, sample_commitment
    ):
        """Reaching min_confirmations should set CONFIRMED status."""
        connector.publish_commitment(sample_commitment)

        # Check 6 times to reach threshold
        for i in range(6):
            result = connector.check_confirmation(
                "foundup_test", epoch=1, min_confirmations=6
            )

        assert result["confirmed"] is True
        assert result["status"] == AnchorStatus.CONFIRMED.value

        # Stats updated
        stats = connector.get_stats()
        assert stats["total_confirmed"] == 1


class TestEpochLedgerIntegration:
    """Tests for integration with EpochLedger."""

    def test_publish_from_epoch_ledger_commitment(self, connector):
        """Connector should work with real epoch_ledger commitment."""
        ledger = EpochLedger("foundup_integration")
        ledger.record_epoch(
            epoch=1,
            total=500.0,
            pool_allocations={"un": 300, "dao": 80, "du": 20, "network": 100},
            participant_rewards={"alice": 200, "bob": 150, "carol": 150},
        )

        commitment = ledger.prepare_settlement_commitment(epoch=1)
        assert commitment is not None

        result = connector.publish_commitment(commitment)

        assert result["success"] is True
        assert result["foundup_id"] == "foundup_integration"
        assert result["epoch"] == 1
        assert len(result["tx_ref"]) == 64


class TestFeatureFlag:
    """Tests for LAYER_D_ENABLED feature flag."""

    def test_mock_mode_works_without_flag(self, temp_db):
        """Mock mode should work regardless of feature flag."""
        connector = BTCAnchorConnector(mode=AnchorMode.MOCK, db_path=temp_db)

        commitment = {
            "format_version": "foundups.epoch.v2",
            "status": "pre_settlement",
            "wsp_78_layer": "D_pending",
            "requires": "external_btc_anchor_connector",
            "foundup_id": "test",
            "epoch": 1,
            "anchor_hex": "f" * 40,
            "merkle_root": "0" * 64,
            "entry_hash": "1" * 64,
            "total_distributed": 0,
            "participant_count": 0,
            "timestamp": "2026-02-22T12:00:00Z",
        }

        result = connector.publish_commitment(commitment)
        assert result["success"] is True

    def test_testnet_requires_flag(self, temp_db):
        """Absent real publishing must reject rather than select simulation."""
        with pytest.raises(ValueError):
            BTCAnchorConnector(mode=AnchorMode.TESTNET, db_path=temp_db)


def _rows(connector):
    with sqlite3.connect(str(connector.db_path)) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute("SELECT * FROM anchor_records ORDER BY id")]


@pytest.mark.parametrize("change", [
    {"format_version": None}, {"format_version": "unknown"},
    {"extra": {"unexpected": True}}, {"foundup_id": ""}, {"foundup_id": 1},
    {"epoch": True}, {"epoch": -1}, {"epoch": 1.0}, {"epoch": 2**63},
    {"anchor_hex": "z"*40}, {"merkle_root": "z"*64}, {"entry_hash": "C"*64},
    {"participant_count": True}, {"participant_count": -1}, {"participant_count": 1.0},
    {"total_distributed": True}, {"total_distributed": -1},
    {"total_distributed": float("nan")}, {"total_distributed": float("inf")},
    {"timestamp": "2026-02-22T12:00:00"}, {"timestamp": "2026-02-22T12:00:00+01:00"},
    {"timestamp": ""}, {"timestamp": 1}, {"wsp_78_layer": "D_confirmed"},
    {"requires": "another_connector"}, {"total_distributed": []},
], ids=["missing-version", "unknown-version", "extra-field", "empty-id", "numeric-id",
        "bool-epoch", "negative-epoch", "float-epoch", "sqlite-epoch-overflow",
        "nonhex-anchor", "nonhex-root", "uppercase-entry", "bool-count", "negative-count",
        "float-count", "bool-amount", "negative-amount", "nan", "infinity", "naive-time",
        "nonutc-time", "empty-time", "numeric-time", "wrong-layer", "wrong-requires", "nested-amount"])
def test_invalid_v2_payload_rejects_before_dispatch(connector, sample_commitment, monkeypatch, change):
    calls = []
    monkeypatch.setattr(connector, "_mock_publish", lambda row: calls.append(row) or {"success": True})
    sample_commitment.update(change)
    before = _rows(connector)
    result = connector.publish_commitment(sample_commitment)
    assert result["success"] is False
    assert calls == [] and _rows(connector) == before


@pytest.mark.parametrize("payload", [None, [], "payload", 1])
def test_non_dictionary_payload_is_a_rejection(connector, payload):
    assert connector.publish_commitment(payload)["success"] is False
    assert _rows(connector) == []


def test_unversioned_and_incomplete_payloads_reject(connector, sample_commitment):
    for key in ("format_version", "total_distributed", "participant_count", "timestamp"):
        payload = dict(sample_commitment)
        del payload[key]
        assert connector.publish_commitment(payload)["success"] is False
        assert _rows(connector) == []


def test_json_integer_conversion_failure_has_no_partial_record(connector, sample_commitment):
    sample_commitment["total_distributed"] = 10**5000
    assert connector.publish_commitment(sample_commitment)["success"] is False
    assert _rows(connector) == []


@pytest.mark.parametrize("force", [None, 0, 1, "true", [], {}])
def test_force_requires_exact_boolean(connector, sample_commitment, force):
    assert connector.publish_commitment(sample_commitment, force=force)["success"] is False
    assert _rows(connector) == []


@pytest.mark.parametrize("field,value", [("anchor_hex", "d"*40), ("merkle_root", "d"*64),
    ("entry_hash", "d"*64), ("total_distributed", 1001), ("participant_count", 6),
    ("timestamp", "2026-02-22T12:00:00+00:00")])
@pytest.mark.parametrize("force", [False, True])
def test_existing_identity_cannot_be_overwritten(connector, sample_commitment, field, value, force):
    first = connector.publish_commitment(sample_commitment)
    before = _rows(connector)
    changed = dict(sample_commitment, **{field: value})
    assert connector.publish_commitment(changed, force=force)["success"] is False
    assert _rows(connector) == before
    assert connector.publish_commitment(sample_commitment)["tx_ref"] == first["tx_ref"]
    assert connector.get_stats()["total_published"] == 1


def test_numeric_equivalence_and_large_integer_are_content_bound(connector, sample_commitment):
    sample_commitment["total_distributed"] = 2**256+1
    first = connector.publish_commitment(sample_commitment)
    assert first["success"] is True
    assert connector.publish_commitment(dict(sample_commitment))["idempotent_hit"] is True
    zero = dict(sample_commitment, epoch=2, total_distributed=-0.0)
    assert connector.publish_commitment(zero)["success"] is True
    zero["total_distributed"] = 0
    assert connector.publish_commitment(zero)["idempotent_hit"] is True
    integral = dict(sample_commitment, epoch=3, total_distributed=1000.0)
    assert connector.publish_commitment(integral)["success"] is True
    integral["total_distributed"] = 1000
    assert connector.publish_commitment(integral)["idempotent_hit"] is True


def test_force_keeps_confirmed_receipt_history(connector, sample_commitment):
    first = connector.publish_commitment(sample_commitment)
    connector.check_confirmation("foundup_test", 1, min_confirmations=1)
    before = _rows(connector)
    result = connector.publish_commitment(sample_commitment, force=True)
    assert result["success"] is True and result["idempotent_hit"] is False
    assert result["tx_ref"] == first["tx_ref"]
    assert _rows(connector) == before
    assert connector.get_stats()["total_published"] == 2


def _legacy_db(path):
    with sqlite3.connect(str(path)) as db:
        db.execute("CREATE TABLE anchor_records (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "foundup_id TEXT NOT NULL, epoch INTEGER NOT NULL, anchor_hex TEXT NOT NULL, "
            "merkle_root TEXT NOT NULL, entry_hash TEXT NOT NULL, status TEXT NOT NULL, "
            "tx_ref TEXT, confirmations INTEGER DEFAULT 0, published_at TEXT, confirmed_at TEXT, "
            "created_at TEXT NOT NULL, UNIQUE(foundup_id,epoch))")
        db.execute("INSERT INTO anchor_records VALUES (1,?,?,?,?,?,?,?,?,?,?,?)",
            ("foundup_test", 1, "a"*40, "b"*64, "c"*64, "published", "d"*64,
             3, "old-published", None, "old-created"))


def test_legacy_migration_preserves_visible_rows_without_classification(tmp_path, sample_commitment):
    path = tmp_path / "old.db"
    _legacy_db(path)
    conn = BTCAnchorConnector(db_path=path)
    rows = _rows(conn)
    assert len(rows) == 1 and rows[0]["created_at"] == "old-created"
    assert all(rows[0][key] is None for key in
        ("format_version", "anchor_realm", "commitment_digest", "commitment_json"))
    for force in (False, True):
        assert conn.publish_commitment(sample_commitment, force=force)["success"] is False
    result = conn.check_confirmation("foundup_test", 1)
    assert result["confirmed"] is False and _rows(conn) == rows
    reopened = BTCAnchorConnector(db_path=path)
    assert _rows(reopened) == rows and len(reopened.get_anchor_status("foundup_test")) == 1


@pytest.mark.parametrize("column,value", [("status", "failed"), ("status", "pending"),
    ("status", "unknown"), ("tx_ref", None), ("tx_ref", "e"*64),
    ("anchor_realm", "bitcoin:testnet"), ("commitment_digest", "f"*64),
    ("commitment_json", "{}"), ("format_version", None), ("anchor_hex", "e"*40)])
def test_unbound_or_unpublished_record_cannot_gain_confirmation(connector, sample_commitment, column, value):
    connector.publish_commitment(sample_commitment)
    with sqlite3.connect(str(connector.db_path)) as db:
        db.execute(f"UPDATE anchor_records SET {column}=? WHERE epoch=1", (value,))
    before = _rows(connector)
    result = connector.check_confirmation("foundup_test", 1, min_confirmations=1)
    assert result["confirmed"] is False and _rows(connector) == before
    assert connector.publish_commitment(sample_commitment, force=True)["success"] is False
    assert _rows(connector) == before


@pytest.mark.parametrize("count", [0, -1, True, 1.0, "1"])
def test_invalid_confirmation_threshold_has_no_effect(connector, sample_commitment, count):
    connector.publish_commitment(sample_commitment)
    before = _rows(connector)
    assert connector.check_confirmation("foundup_test", 1, min_confirmations=count)["confirmed"] is False
    assert _rows(connector) == before


@pytest.mark.parametrize("same", [True, False])
def test_two_instances_admit_one_immutable_identity(tmp_path, sample_commitment, same):
    path = tmp_path / "race.db"
    a, b = BTCAnchorConnector(db_path=path), BTCAnchorConnector(db_path=path)
    start = Barrier(2)
    def publish(conn, payload):
        start.wait(timeout=5)
        return conn.publish_commitment(payload)
    other = dict(sample_commitment, entry_hash=sample_commitment["entry_hash"] if same else "d"*64)
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(publish, a, sample_commitment), pool.submit(publish, b, other)]
        results = [job.result(timeout=10) for job in jobs]
    assert sum(result["success"] for result in results) == (2 if same else 1)
    assert len(_rows(a)) == 1
    assert a.get_stats()["total_published"] + b.get_stats()["total_published"] == 1
    assert sum(result.get("idempotent_hit", False) for result in results) == (1 if same else 0)


def test_payload_detached_before_mock_dispatch(connector, sample_commitment, monkeypatch):
    original = copy.deepcopy(sample_commitment)
    publish = connector._mock_publish
    def change_caller(record):
        sample_commitment["entry_hash"] = "e"*64
        return publish(record)
    monkeypatch.setattr(connector, "_mock_publish", change_caller)
    assert connector.publish_commitment(sample_commitment)["success"] is True
    stored = _rows(connector)[0]
    assert original["entry_hash"] in stored["commitment_json"]
    assert connector.publish_commitment(original)["idempotent_hit"] is True


@pytest.mark.parametrize("mode", [AnchorMode.TESTNET, AnchorMode.MAINNET, "mock", None])
@pytest.mark.parametrize("enabled", [False, True])
def test_unsupported_selection_rejects_before_database(tmp_path, monkeypatch, mode, enabled):
    monkeypatch.setattr(anchor_module, "LAYER_D_ENABLED", enabled)
    path = tmp_path / "not-created" / "anchor.db"
    with pytest.raises(ValueError):
        BTCAnchorConnector(mode=mode, db_path=path)
    assert not path.parent.exists()


def test_singleton_rejects_explicit_mode_or_path_mismatch(tmp_path):
    reset_anchor_connector()
    try:
        first = get_anchor_connector(db_path=tmp_path / "a.db")
        assert get_anchor_connector() is first
        assert get_anchor_connector(mode=AnchorMode.MOCK, db_path=tmp_path / "a.db") is first
        with pytest.raises(ValueError):
            get_anchor_connector(mode=AnchorMode.TESTNET)
        with pytest.raises(ValueError):
            get_anchor_connector(db_path=tmp_path / "b.db")
        assert not (tmp_path / "b.db").exists()
    finally:
        reset_anchor_connector()


def test_public_configuration_cannot_retarget_connector(connector, sample_commitment, tmp_path):
    original_path = connector.db_path
    with pytest.raises(AttributeError):
        connector.mode = AnchorMode.TESTNET
    with pytest.raises(AttributeError):
        connector.db_path = tmp_path / "another.db"
    assert connector.db_path == original_path
    assert connector.get_stats()["mode"] == "mock"
    assert connector.publish_commitment(sample_commitment)["mode"] == "mock"


class _StringSubclass(str):
    pass


@pytest.mark.parametrize("field", ["status", "format_version", "wsp_78_layer", "requires"])
def test_literal_fields_require_builtin_strings(connector, sample_commitment, field):
    sample_commitment[field] = _StringSubclass(sample_commitment[field])
    assert connector.publish_commitment(sample_commitment)["success"] is False
    assert _rows(connector) == []


class _ConnectionFault:
    def __init__(self, connection, stage):
        self.connection, self.stage = connection, stage

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, *args):
        outcome = self.connection.__exit__(*args)
        if self.stage == "after-commit" and args[0] is None:
            raise sqlite3.OperationalError("fixture response lost after commit")
        return outcome

    def execute(self, sql, *args):
        if self.stage == "insert" and sql.startswith("INSERT INTO anchor_records"):
            raise sqlite3.OperationalError("fixture insert failure")
        return self.connection.execute(sql, *args)

    def close(self):
        self.connection.close()


@pytest.mark.parametrize("stage", ["insert", "after-commit"])
def test_publication_transaction_failure_and_response_loss(connector, sample_commitment, monkeypatch, stage):
    connect, publish = connector._connect, connector._mock_publish
    calls = []
    def counted(record):
        calls.append(record.commitment_digest)
        return publish(record)
    monkeypatch.setattr(connector, "_mock_publish", counted)
    monkeypatch.setattr(connector, "_connect", lambda: _ConnectionFault(connect(), stage))
    assert connector.publish_commitment(sample_commitment)["success"] is False
    assert len(_rows(connector)) == (1 if stage == "after-commit" else 0)
    monkeypatch.setattr(connector, "_connect", connect)
    result = connector.publish_commitment(sample_commitment)
    assert result["success"] is True
    assert result["idempotent_hit"] is (stage == "after-commit")
    assert len(calls) == (1 if stage == "after-commit" else 2)
    assert len(_rows(connector)) == 1


def test_partial_and_concurrent_legacy_migration_remains_unclassified(tmp_path):
    path = tmp_path / "partial.db"
    _legacy_db(path)
    with sqlite3.connect(str(path)) as db:
        db.execute("ALTER TABLE anchor_records ADD COLUMN format_version TEXT")
    start = Barrier(2)
    def open_database():
        start.wait(timeout=5)
        return BTCAnchorConnector(db_path=path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = [job.result(timeout=10) for job in [pool.submit(open_database), pool.submit(open_database)]]
    assert _rows(a) == _rows(b)
    assert all(_rows(a)[0][key] is None for key in
        ("format_version", "anchor_realm", "commitment_digest", "commitment_json"))
    assert a.get_anchor_status("foundup_test")[0]["identity_status"] == "legacy_unclassified"


@pytest.mark.parametrize("result", [
    {"success": True, "tx_ref": "d"*64, "mode": "mock"},
    {"success": True, "tx_ref": "d"*64, "mode": "testnet"},
    {"success": 1, "tx_ref": "d"*64, "mode": "mock"},
])
def test_mismatched_mock_result_never_becomes_receipt(connector, sample_commitment, monkeypatch, result):
    monkeypatch.setattr(connector, "_mock_publish", lambda record: dict(result))
    assert connector.publish_commitment(sample_commitment)["success"] is False
    assert _rows(connector)[0]["status"] == "failed"
    assert _rows(connector)[0]["tx_ref"] is None
    assert connector.check_confirmation("foundup_test", 1, 1)["confirmed"] is False


@pytest.mark.parametrize("malformed", ["missing-column", "wrong-epoch-type", "no-unique", "partial-unique", "wider-unique"])
def test_unsupported_persisted_schema_rejects_without_migration(tmp_path, malformed):
    path = tmp_path / "unsupported.db"
    fields = ["id INTEGER PRIMARY KEY", "foundup_id TEXT NOT NULL", "epoch INTEGER NOT NULL",
        "anchor_hex TEXT NOT NULL", "merkle_root TEXT NOT NULL", "entry_hash TEXT NOT NULL",
        "status TEXT NOT NULL", "tx_ref TEXT", "confirmations INTEGER DEFAULT 0",
        "published_at TEXT", "confirmed_at TEXT", "created_at TEXT NOT NULL"]
    if malformed == "missing-column":
        fields.remove("merkle_root TEXT NOT NULL")
    if malformed == "wrong-epoch-type":
        fields[2] = "epoch TEXT NOT NULL"
    if malformed in ("missing-column", "wrong-epoch-type"):
        fields.append("UNIQUE(foundup_id,epoch)")
    if malformed == "wider-unique":
        fields.append("UNIQUE(foundup_id,epoch,entry_hash)")
    with sqlite3.connect(str(path)) as db:
        db.execute("CREATE TABLE anchor_records (" + ",".join(fields) + ")")
        if malformed == "partial-unique":
            db.execute("CREATE UNIQUE INDEX partial_identity ON anchor_records(foundup_id,epoch) WHERE epoch>0")
        before = list(db.execute("SELECT name,sql FROM sqlite_master ORDER BY name"))
    with pytest.raises(ValueError):
        BTCAnchorConnector(db_path=path)
    with sqlite3.connect(str(path)) as db:
        assert list(db.execute("SELECT name,sql FROM sqlite_master ORDER BY name")) == before


def test_duplicate_current_rows_in_unsupported_schema_cannot_replay(tmp_path, sample_commitment):
    sources = [BTCAnchorConnector(db_path=tmp_path / f"source_{i}.db") for i in range(2)]
    for i, source in enumerate(sources):
        assert source.publish_commitment(dict(sample_commitment, total_distributed=1000+i))["success"] is True
    rows = [_rows(source)[0] for source in sources]
    path = tmp_path / "duplicated.db"
    with sqlite3.connect(str(path)) as db:
        for i, row in enumerate(rows):
            if i == 0:
                columns = ",".join(f"{key} {'INTEGER' if key in ('id','epoch','confirmations') else 'TEXT'}" for key in row)
                db.execute("CREATE TABLE anchor_records (" + columns + ")")
            row["id"] = i+1
            db.execute("INSERT INTO anchor_records VALUES (" + ",".join("?" for _ in row) + ")", tuple(row.values()))
        before = list(db.execute("SELECT * FROM anchor_records ORDER BY id"))
    with pytest.raises(ValueError):
        BTCAnchorConnector(db_path=path)
    with sqlite3.connect(str(path)) as db:
        assert list(db.execute("SELECT * FROM anchor_records ORDER BY id")) == before
