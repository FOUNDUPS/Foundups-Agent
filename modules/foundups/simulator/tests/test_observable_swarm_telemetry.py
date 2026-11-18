"""Tests for Observable Swarm Orchestration vertical slice (WSP 97 / WSP 110).

Verifies:
- Strictly read-only SQLite telemetry provider (`?mode=ro` + `PRAGMA query_only = ON`)
  across AgentDB and PatternMemory tables, preserving SHA-256 DB invariance.
- Complete 8-state canonical mapping (`spawn`, `claim`, `progress`, `complete`,
  `fail`, `cancel`, `stale`, `unknown`).
- Honest unknown/stale reporting for missing stores, expired leases/TTLs, and
  missing completion `_effect_evidence`.
- Path and secret redaction.
- GET-only `/api/work-telemetry` endpoint with auth gate and `work_telemetry_sync`
  in `STREAMABLE_EVENT_TYPES`.
- Client `public/js/foundup-cube.js` observation-only mode via Node VM:
  non-monotonic block fill shrinkage, disabled Firestore writes & agent click
  promotion, TTL stale transition, and explicit `"OBSERVATION ONLY"` / `"NO AUTHORITY"`
  canvas indicators.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import sqlite3
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict

import pytest

from modules.foundups.simulator import sse_server
from modules.foundups.simulator.adapters.work_telemetry_provider import (
    get_work_telemetry_snapshot,
    redact_sensitive_text,
)
from modules.foundups.simulator.frame_schema import (
    CANONICAL_WORK_STATES,
    WorkTelemetrySnapshot,
    WorkUnitFrame,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
_OUTPUTS_BASE = (
    REPO_ROOT.parents[1]
    if REPO_ROOT.parent.name == ".worktrees" and (REPO_ROOT.parents[1] / "outputs").exists()
    else REPO_ROOT
)
CUBE_JS_PATH = REPO_ROOT / "public" / "js" / "foundup-cube.js"
SPRINT4_PATTERN_DB = (
    _OUTPUTS_BASE
    / "outputs"
    / "tertia_reconciliation_20261115"
    / "sprint4_artifacts"
    / "sprint4_pattern_memory.db"
)
SPRINT5_AGENT_DB = (
    _OUTPUTS_BASE
    / "outputs"
    / "tertia_reconciliation_20261115"
    / "sprint5_artifacts"
    / "sprint5_soak_agentdb.db"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _create_sample_dbs(tmp_path: Path, now: datetime) -> tuple[Path, Path]:
    agent_db = tmp_path / "agent.db"
    pattern_db = tmp_path / "pattern.db"

    fresh_ts = (now - timedelta(seconds=15)).isoformat()
    old_ts = (now - timedelta(seconds=900)).isoformat()
    expired_lease_ts = (now - timedelta(seconds=60)).isoformat()
    valid_lease_ts = (now + timedelta(seconds=600)).isoformat()

    aconn = sqlite3.connect(agent_db)
    aconn.execute(
        """
        CREATE TABLE agents_autonomous_tasks (
            task_id TEXT PRIMARY KEY,
            description TEXT,
            required_skills TEXT,
            estimated_complexity REAL,
            priority_score REAL,
            discovered_by TEXT,
            discovered_at TEXT,
            context TEXT,
            assigned_to TEXT,
            assigned_at TEXT,
            retry_not_before TEXT,
            status TEXT,
            completed_at TEXT,
            origin_continuity_id TEXT
        )
        """
    )
    aconn.execute(
        """
        CREATE TABLE agents_signed_worker_execution_leases (
            task_id TEXT PRIMARY KEY,
            claim_receipt_id TEXT,
            use_receipt_id TEXT,
            assigned_to TEXT,
            initial_claimed_at TEXT,
            lease_expires_at TEXT,
            max_expires_at TEXT,
            renewal_count INTEGER,
            updated_at TEXT
        )
        """
    )
    aconn.execute(
        """
        CREATE TABLE agents_independent_assurance_reservations (
            reservation_id TEXT PRIMARY KEY,
            author_task_id TEXT,
            author_principal_id TEXT,
            verifier_task_id TEXT,
            verifier_principal_id TEXT,
            reserved_at TEXT,
            expires_at TEXT,
            status TEXT,
            terminal_receipt_id TEXT,
            terminal_receipt_digest TEXT,
            terminal_status TEXT,
            completed_at TEXT,
            revoked_at TEXT
        )
        """
    )

    tasks = [
        # 1. spawn
        ("task_spawn", "Queued work item", "[]", 1.0, 1.0, "planner", fresh_ts, "{}", None, None, None, "pending", None, None),
        # 2. claim
        ("task_claim", "Claimed work item", "[]", 1.0, 1.0, "planner", fresh_ts, "{}", "worker-1", fresh_ts, None, "claimed", None, None),
        # 3. progress
        ("task_progress", "Running task with valid lease", "[]", 1.0, 1.0, "planner", fresh_ts, "{}", "worker-2", fresh_ts, None, "executing", None, "task_spawn"),
        # 4. complete (with evidence)
        (
            "task_complete",
            "Finished C:\\Users\\secret\\repo\\file.py with " + "AIza" + "SyDummySample123456",
            "[]", 1.0, 1.0, "planner", fresh_ts, '{"_effect_evidence": true}', "worker-2", fresh_ts, None, "completed", fresh_ts, "task_progress",
        ),
        # 5. fail
        (
            "task_fail",
            "Failed with tok" + "en=" + "sk-" + "dummySampleValue9999",
            "[]", 1.0, 1.0, "planner", fresh_ts, "{}", "worker-3", fresh_ts, None, "failed", fresh_ts, None,
        ),
        # 6. cancel
        ("task_cancel", "Cancelled lane", "[]", 1.0, 1.0, "planner", fresh_ts, "{}", "worker-4", fresh_ts, None, "cancelled", fresh_ts, None),
        # 7. stale (expired lease)
        ("task_stale", "Expired executing lease", "[]", 1.0, 1.0, "planner", old_ts, "{}", "worker-5", old_ts, None, "executing", None, None),
        # 8. unknown (completed claim missing effect evidence)
        ("task_unknown", "No effect evidence task", "[]", 1.0, 1.0, "planner", fresh_ts, '{"_effect_evidence": false}', "worker-6", fresh_ts, None, "completed", fresh_ts, None),
    ]
    aconn.executemany(
        "INSERT INTO agents_autonomous_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        tasks,
    )
    aconn.execute(
        "INSERT INTO agents_signed_worker_execution_leases VALUES (?,?,?,?,?,?,?,?,?)",
        ("task_progress", "claim-1", "use-1", "worker-2", fresh_ts, valid_lease_ts, valid_lease_ts, 1, fresh_ts),
    )
    aconn.execute(
        "INSERT INTO agents_signed_worker_execution_leases VALUES (?,?,?,?,?,?,?,?,?)",
        ("task_stale", "claim-2", "use-2", "worker-5", old_ts, expired_lease_ts, expired_lease_ts, 0, old_ts),
    )
    aconn.execute(
        "INSERT INTO agents_independent_assurance_reservations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("res-1", "task_complete", "worker-2", "task_verify_1", "obs-slice-verifier", fresh_ts, valid_lease_ts, "completed", "rcpt-1", "digest-1", "approved", fresh_ts, None),
    )
    aconn.commit()
    aconn.close()

    pconn = sqlite3.connect(pattern_db)
    pconn.execute(
        """
        CREATE TABLE skill_outcomes (
            execution_id TEXT PRIMARY KEY,
            skill_name TEXT,
            agent TEXT,
            timestamp TEXT,
            input_context TEXT,
            output_result TEXT,
            success INTEGER,
            pattern_fidelity REAL,
            outcome_quality REAL,
            execution_time_ms INTEGER,
            step_count INTEGER,
            failed_at_step INTEGER,
            notes TEXT
        )
        """
    )
    pconn.execute(
        "INSERT INTO skill_outcomes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("exec-1", "wsp_verify", "qwen-worker", fresh_ts, "/Users/admin/secret/ctx", "ok", 1, 0.95, 0.92, 120, 4, None, '{"_effect_evidence": true}'),
    )
    pconn.execute(
        "INSERT INTO skill_outcomes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("exec-2", "wsp_verify", "gemma-worker", fresh_ts, "ctx", "done", 1, 0.80, 0.80, 80, 2, None, '{"_effect_evidence": false}'),
    )
    pconn.commit()
    pconn.close()
    return agent_db, pattern_db


def test_canonical_eight_states_and_redaction(tmp_path: Path) -> None:
    now = datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc)
    agent_db, pattern_db = _create_sample_dbs(tmp_path, now)

    before_agent_sha = _sha256(agent_db)
    before_pattern_sha = _sha256(pattern_db)

    payload = get_work_telemetry_snapshot(
        agent_db_path=agent_db,
        pattern_db_path=pattern_db,
        ttl_seconds=300.0,
        limit=50,
        now=now,
    )

    assert payload["observation_only"] is True
    assert payload["authority"] == "none"
    assert payload["source_mode"] == "live_readonly"
    assert payload["freshness"] == "fresh"
    assert tuple(payload["canonical_states"]) == CANONICAL_WORK_STATES

    by_id: Dict[str, dict] = {u["work_id"]: u for u in payload["work_units"]}
    assert by_id["task_spawn"]["canonical_state"] == "spawn"
    assert by_id["task_claim"]["canonical_state"] == "claim"
    assert by_id["task_progress"]["canonical_state"] == "progress"
    assert by_id["task_complete"]["canonical_state"] == "complete"
    assert by_id["task_complete"]["verifier_agent"] == "obs-slice-verifier"
    assert by_id["task_fail"]["canonical_state"] == "fail"
    assert by_id["task_cancel"]["canonical_state"] == "cancel"
    assert by_id["task_stale"]["canonical_state"] == "stale"
    assert by_id["task_unknown"]["canonical_state"] == "unknown"
    assert by_id["task_unknown"]["effect_evidence"] is False
    assert by_id["task_unknown"]["unknown_reason"] == "missing_effect_evidence"

    # Counts match across all 8 canonical states
    for state in CANONICAL_WORK_STATES:
        assert payload["counts_by_state"][state] == 1

    # Strict path and secret redaction
    assert "C:\\Users" not in by_id["task_complete"]["title"]
    assert "AIza" not in by_id["task_complete"]["title"]
    assert "[REDACTED_PATH]" in by_id["task_complete"]["title"]
    assert "[REDACTED_SECRET]" in by_id["task_complete"]["title"]
    assert ("sk-" + "dummySampleValue9999") not in by_id["task_fail"]["title"]
    assert "[REDACTED_SECRET]" in by_id["task_fail"]["title"]

    # PatternMemory outcome with _effect_evidence=false stays unknown
    outcomes_by_id = {o["execution_id"]: o for o in payload["outcomes_summary"]["recent"]}
    assert outcomes_by_id["exec-1"]["canonical_state"] == "complete"
    assert outcomes_by_id["exec-2"]["canonical_state"] == "unknown"

    # Read-only DB byte invariance
    assert _sha256(agent_db) == before_agent_sha
    assert _sha256(pattern_db) == before_pattern_sha


def test_missing_dbs_report_honest_unknown(tmp_path: Path) -> None:
    payload = get_work_telemetry_snapshot(
        agent_db_path=tmp_path / "does_not_exist_agent.db",
        pattern_db_path=tmp_path / "does_not_exist_pattern.db",
    )
    assert payload["observation_only"] is True
    assert payload["authority"] == "none"
    assert payload["source_mode"] == "unknown"
    assert payload["freshness"] == "unknown"
    assert payload["total_work_units"] == 0
    assert payload["work_units"] == []
    assert "agent_db:db_missing" in payload["errors"]
    assert "pattern_db:db_missing" in payload["errors"]


def test_stale_snapshot_ttl_transition(tmp_path: Path) -> None:
    created = datetime(2026, 11, 15, 10, 0, 0, tzinfo=timezone.utc)
    agent_db, pattern_db = _create_sample_dbs(tmp_path, created)
    later = created + timedelta(seconds=600)

    payload = get_work_telemetry_snapshot(
        agent_db_path=agent_db,
        pattern_db_path=pattern_db,
        ttl_seconds=120.0,
        now=later,
    )
    assert payload["freshness"] == "stale"
    assert payload["source_mode"] == "stale"
    assert payload["age_seconds"] is not None and payload["age_seconds"] > 120.0


def test_redact_sensitive_text_patterns() -> None:
    raw = (
        "Failed at /Users/012/secret/key.txt and \\\\server\\share\\file.db "
        + "with Bear" + "er abcdef123456 and "
        + "ghp_" + "0123456789abcdef and "
        + "pass" + "word=placeholderVal"
    )
    clean = redact_sensitive_text(raw, max_len=240)
    assert "/Users/012" not in clean
    assert "\\\\server" not in clean
    assert "abcdef123456" not in clean
    assert "ghp_" not in clean
    assert "placeholderVal" not in clean
    assert "[REDACTED_PATH]" in clean
    assert "[REDACTED_SECRET]" in clean


def test_live_sprint_sqlite_sha256_invariance(tmp_path: Path) -> None:
    """Verify multi-table SQLite telemetry reads leave DB bytes untouched with zero skips."""
    now = datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc)
    seeded_agent_db, seeded_pattern_db = _create_sample_dbs(tmp_path, now)

    before_seeded_agent = _sha256(seeded_agent_db)
    before_seeded_pattern = _sha256(seeded_pattern_db)

    for call_limit in (5, 25, 50):
        seeded_payload = get_work_telemetry_snapshot(
            agent_db_path=seeded_agent_db,
            pattern_db_path=seeded_pattern_db,
            ttl_seconds=300.0,
            limit=call_limit,
            now=now,
        )
        assert seeded_payload["observation_only"] is True
        assert seeded_payload["authority"] == "none"
        assert seeded_payload["total_work_units"] > 0
        assert seeded_payload["outcomes_summary"]["count"] > 0

    assert _sha256(seeded_agent_db) == before_seeded_agent
    assert _sha256(seeded_pattern_db) == before_seeded_pattern
    for db_file in (seeded_agent_db, seeded_pattern_db):
        for suffix in ("-wal", "-shm", "-journal"):
            assert not Path(f"{db_file}{suffix}").exists()

    if SPRINT5_AGENT_DB.exists() and SPRINT4_PATTERN_DB.exists():
        before_agent = _sha256(SPRINT5_AGENT_DB)
        before_pattern = _sha256(SPRINT4_PATTERN_DB)
        before_sidecars = {}
        for live_db in (SPRINT5_AGENT_DB, SPRINT4_PATTERN_DB):
            for suffix in ("-wal", "-shm", "-journal"):
                sidecar = Path(f"{live_db}{suffix}")
                before_sidecars[sidecar] = _sha256(sidecar) if sidecar.exists() else None

        for call_limit in (10, 25):
            payload = get_work_telemetry_snapshot(
                agent_db_path=SPRINT5_AGENT_DB,
                pattern_db_path=SPRINT4_PATTERN_DB,
                limit=call_limit,
            )
            assert payload["observation_only"] is True
            assert payload["authority"] == "none"
            assert payload["total_work_units"] > 0
            assert payload["outcomes_summary"]["count"] > 0

        assert _sha256(SPRINT5_AGENT_DB) == before_agent
        assert _sha256(SPRINT4_PATTERN_DB) == before_pattern
        for sidecar, prev_digest in before_sidecars.items():
            if prev_digest is None:
                assert not sidecar.exists()
            else:
                assert sidecar.exists()
                assert _sha256(sidecar) == prev_digest


def test_clean_checkout_sqlite_sha256_invariance_without_live_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify clean checkouts without untracked Sprint 4/5 DBs still execute invariance checks."""
    monkeypatch.setitem(
        globals(),
        "SPRINT5_AGENT_DB",
        tmp_path / "absent_sprint5_agentdb.db",
    )
    monkeypatch.setitem(
        globals(),
        "SPRINT4_PATTERN_DB",
        tmp_path / "absent_sprint4_pattern.db",
    )
    seeded_dir = tmp_path / "clean_checkout_seeded"
    seeded_dir.mkdir()
    test_live_sprint_sqlite_sha256_invariance(seeded_dir)


def test_context_lineage_dependencies_and_lease_redaction(tmp_path: Path) -> None:
    """Verify parent_task_id, depends_on, work_order_id, swarm_lane, lease_active, and dedup."""
    now = datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc)
    fresh_ts = (now - timedelta(seconds=10)).isoformat()
    valid_lease_ts = (now + timedelta(seconds=600)).isoformat()
    expired_lease_ts = (now - timedelta(seconds=60)).isoformat()

    agent_db = tmp_path / "lineage_agent.db"
    aconn = sqlite3.connect(agent_db)
    aconn.execute(
        """
        CREATE TABLE agents_autonomous_tasks (
            task_id TEXT PRIMARY KEY,
            description TEXT,
            required_skills TEXT,
            estimated_complexity REAL,
            priority_score REAL,
            discovered_by TEXT,
            discovered_at TEXT,
            context TEXT,
            assigned_to TEXT,
            assigned_at TEXT,
            retry_not_before TEXT,
            status TEXT,
            completed_at TEXT,
            origin_continuity_id TEXT
        )
        """
    )
    aconn.execute(
        """
        CREATE TABLE agents_signed_worker_execution_leases (
            task_id TEXT PRIMARY KEY,
            claim_receipt_id TEXT,
            use_receipt_id TEXT,
            assigned_to TEXT,
            initial_claimed_at TEXT,
            lease_expires_at TEXT,
            max_expires_at TEXT,
            renewal_count INTEGER,
            updated_at TEXT
        )
        """
    )
    secret_tok = "ghp_" + "SecretTokenValue987654321"
    ctx_child_list = json.dumps(
        {
            "parent_task_id": "task_root",
            "depends_on": ["dep_alpha", "dep_beta", "dep_alpha", "task_child_list"],
            "work_order_id": f"wo-list-{secret_tok}",
            "swarm_lane": "lane-obs-3-" + ("x" * 80),
        }
    )
    ctx_child_str = json.dumps(
        {
            "parent_task_id": "C:\\secret_dir\\parent_node",
            "depends_on": "dep_gamma, dep_delta, dep_gamma",
            "work_order_id": "wo-str-01",
            "swarm_lane": "lane-truth-2",
        }
    )
    ctx_done = json.dumps(
        {
            "_effect_evidence": True,
            "parent_task_id": "task_child_list",
            "work_order_id": "wo-done-02",
            "swarm_lane": "lane-truth-2",
        }
    )
    rows = [
        ("task_root", "Root planner work", "[]", 1.0, 1.0, "0102", fresh_ts, "{}", None, None, None, "pending", None, None),
        ("task_child_list", "Active leased lane work", "[]", 1.0, 1.0, "0102", fresh_ts, ctx_child_list, "worker-a", fresh_ts, None, "executing", None, None),
        ("task_child_str", "Expired lease lane work", "[]", 1.0, 1.0, "0102", fresh_ts, ctx_child_str, "worker-b", fresh_ts, None, "claimed", None, None),
        ("task_done_leaf", "Completed leaf with stale row", "[]", 1.0, 1.0, "0102", fresh_ts, ctx_done, "worker-c", fresh_ts, None, "completed", fresh_ts, None),
    ]
    aconn.executemany(
        "INSERT INTO agents_autonomous_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    aconn.execute(
        "INSERT INTO agents_signed_worker_execution_leases VALUES (?,?,?,?,?,?,?,?,?)",
        ("task_child_list", "c1", "u1", "worker-a", fresh_ts, valid_lease_ts, valid_lease_ts, 0, fresh_ts),
    )
    aconn.execute(
        "INSERT INTO agents_signed_worker_execution_leases VALUES (?,?,?,?,?,?,?,?,?)",
        ("task_child_str", "c2", "u2", "worker-b", fresh_ts, expired_lease_ts, expired_lease_ts, 0, fresh_ts),
    )
    aconn.execute(
        "INSERT INTO agents_signed_worker_execution_leases VALUES (?,?,?,?,?,?,?,?,?)",
        ("task_done_leaf", "c3", "u3", "worker-c", fresh_ts, valid_lease_ts, valid_lease_ts, 0, fresh_ts),
    )
    aconn.commit()
    aconn.close()

    payload = get_work_telemetry_snapshot(
        agent_db_path=agent_db,
        pattern_db_path=None,
        ttl_seconds=300.0,
        limit=50,
        now=now,
    )
    assert payload["observation_only"] is True
    assert payload["authority"] == "none"
    assert payload["active_lease_count"] == 1

    units = {u["work_id"]: u for u in payload["work_units"]}
    u_list = units["task_child_list"]
    assert u_list["parent_work_id"] == "task_root"
    assert u_list["lease_active"] is True
    assert "[REDACTED_SECRET]" in u_list["work_order_id"]
    assert secret_tok not in u_list["work_order_id"]
    assert len(u_list["swarm_lane"]) <= 64
    assert u_list["swarm_lane"].startswith("lane-obs-3-")

    u_str = units["task_child_str"]
    assert u_str["canonical_state"] == "stale"
    assert u_str["lease_active"] is False
    assert "[REDACTED_PATH]" in u_str["parent_work_id"]
    assert "C:\\secret_dir" not in u_str["parent_work_id"]
    assert u_str["work_order_id"] == "wo-str-01"
    assert u_str["swarm_lane"] == "lane-truth-2"

    u_done = units["task_done_leaf"]
    assert u_done["canonical_state"] == "complete"
    assert u_done["lease_active"] is False
    assert u_done["parent_work_id"] == "task_child_list"

    deps = payload["dependencies"]
    dep_tuples = [(d["from"], d["to"], d["relation"]) for d in deps]
    # Exact deduplication & self-edge exclusion
    assert len(dep_tuples) == len(set(dep_tuples))
    assert ("task_child_list", "task_child_list", "depends_on") not in dep_tuples
    assert ("dep_alpha", "task_child_list", "depends_on") in dep_tuples
    assert ("dep_beta", "task_child_list", "depends_on") in dep_tuples
    assert ("task_root", "task_child_list", "parent_task") in dep_tuples
    assert ("dep_gamma", "task_child_str", "depends_on") in dep_tuples
    assert ("dep_delta", "task_child_str", "depends_on") in dep_tuples
    assert ("[REDACTED_PATH]", "task_child_str", "parent_task") in dep_tuples
    assert ("task_child_list", "task_done_leaf", "parent_task") in dep_tuples
    assert len(payload["swarm_lanes"]) == 2


def test_readonly_sql_pragma_refuses_writes(tmp_path: Path) -> None:
    """Verify _connect_readonly refuses INSERT/DELETE via ?mode=ro and query_only."""
    from modules.foundups.simulator.adapters.work_telemetry_provider import _connect_readonly

    now = datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc)
    agent_db, _ = _create_sample_dbs(tmp_path, now)
    conn, err = _connect_readonly(agent_db)
    assert err is None and conn is not None
    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("DELETE FROM agents_autonomous_tasks")
    finally:
        conn.close()


async def _asgi_request(
    app,
    method: str,
    path: str,
    query_string: bytes = b"",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[int, dict | str]:
    """Invoke an ASGI app directly without requiring httpx / TestClient."""
    status_code = 0
    body_chunks: list[bytes] = []
    req_headers: list[tuple[bytes, bytes]] = [(b"host", b"testserver")]
    if headers:
        req_headers.extend(headers)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": query_string,
        "headers": req_headers,
        "client": ("10.0.0.1", 12345),
        "server": ("testserver", 80),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = int(message["status"])
        elif message["type"] == "http.response.body":
            body_chunks.append(message.get("body", b""))

    await app(scope, receive, send)
    raw_body = b"".join(body_chunks).decode("utf-8", errors="replace")
    try:
        return status_code, json.loads(raw_body)
    except ValueError:
        return status_code, raw_body


def test_sse_server_work_telemetry_endpoint_and_auth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc)
    agent_db, pattern_db = _create_sample_dbs(tmp_path, now)
    monkeypatch.setenv("FOUNDUPS_AGENT_DB_PATH", str(agent_db))
    monkeypatch.setenv("FOUNDUPS_PATTERN_DB_PATH", str(pattern_db))
    monkeypatch.setenv("FAM_MEMBER_GATE_ENABLED", "0")

    assert "work_telemetry_sync" in sse_server.STREAMABLE_EVENT_TYPES
    assert sse_server.app is not None, "FastAPI/ASGI app unavailable"

    root_status, root_body = asyncio.run(_asgi_request(sse_server.app, "GET", "/"))
    assert root_status == 200
    assert "/api/work-telemetry" in root_body["endpoints"]

    get_status, body = asyncio.run(
        _asgi_request(
            sse_server.app,
            "GET",
            "/api/work-telemetry",
            query_string=b"limit=10&ttl_seconds=99999999",
        )
    )
    assert get_status == 200
    assert body["observation_only"] is True
    assert body["authority"] == "none"
    assert body["total_work_units"] == 8

    # Mutating HTTP verbs MUST be refused
    for verb in ("POST", "PUT", "DELETE"):
        mut_status, _ = asyncio.run(_asgi_request(sse_server.app, verb, "/api/work-telemetry"))
        assert mut_status == 405

    # Auth gate enforced when member auth is required
    invite_key = "test-invite-" + "gate-value"
    monkeypatch.setenv("FAM_MEMBER_GATE_ENABLED", "1")
    monkeypatch.setenv("FAM_MEMBER_INVITE_KEY", invite_key)
    monkeypatch.setenv("FAM_MEMBER_GATE_ALLOW_LOCAL_BYPASS", "0")

    denied_status, _ = asyncio.run(_asgi_request(sse_server.app, "GET", "/api/work-telemetry"))
    assert denied_status == 403

    allowed_status, allowed_body = asyncio.run(
        _asgi_request(
            sse_server.app,
            "GET",
            "/api/work-telemetry",
            headers=[
                (b"x-invite-key", invite_key.encode("ascii")),
                (b"x-member-role", b"observer_012"),
            ],
        )
    )
    assert allowed_status == 200
    assert allowed_body["member_role"] == "observer_012"


def test_frame_schema_work_telemetry_dataclass() -> None:
    snap = WorkTelemetrySnapshot(
        source_mode="live_readonly",
        freshness="fresh",
        observed_at="2026-11-15T12:00:00+00:00",
        ttl_seconds=300.0,
        counts_by_state={s: 0 for s in CANONICAL_WORK_STATES},
        work_units=[
            WorkUnitFrame(
                work_id="t1",
                title="t1",
                canonical_state="spawn",
                raw_status="pending",
                source_table="agents_autonomous_tasks",
            )
        ],
    )
    assert snap.observation_only is True
    assert snap.authority == "none"


def test_foundup_cube_js_observation_only_vm() -> None:
    """Execute public/js/foundup-cube.js in Node VM to verify UI guarantees."""
    if shutil.which("node") is None:
        pytest.skip("Node.js runtime required for foundup-cube.js VM test")

    now_dt = datetime.now(timezone.utc).replace(microsecond=0)
    now_iso = now_dt.isoformat().replace("+00:00", "Z")
    stale_clock_ms = int((now_dt + timedelta(minutes=10)).timestamp() * 1000)

    script = f"""
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const nodeCrypto = require('crypto');

const code = fs.readFileSync({json.dumps(str(CUBE_JS_PATH))}, 'utf8');
const fillTexts = [];
const canvasHandlers = {{}};
let rafCb = null;
let firestoreWrites = 0;

const ctx2dBase = {{
  createLinearGradient() {{ return {{ addColorStop() {{}} }}; }},
  createRadialGradient() {{ return {{ addColorStop() {{}} }}; }},
  measureText(t) {{ return {{ width: String(t).length * 6 }}; }},
  getLineDash() {{ return []; }},
  fillText(txt) {{ fillTexts.push(String(txt)); }},
}};
const ctx2d = new Proxy(ctx2dBase, {{
  get(target, prop) {{
    if (prop in target) return target[prop];
    return () => {{}};
  }},
}});

const canvasEl = {{
  dataset: {{}},
  style: {{}},
  width: 800,
  height: 600,
  getBoundingClientRect() {{ return {{ left: 0, top: 0, width: 800, height: 600 }}; }},
  getContext() {{ return ctx2d; }},
  addEventListener(ev, fn) {{ canvasHandlers[ev] = fn; }},
}};

const fakeDbProxy = new Proxy(() => fakeDbProxy, {{
  get(_target, prop) {{
    if (prop === 'set' || prop === 'add' || prop === 'update') {{
      return () => {{ firestoreWrites += 1; return Promise.resolve(); }};
    }}
    return () => fakeDbProxy;
  }},
}});

const sandbox = {{
  console: {{ log() {{}}, warn() {{}}, error() {{}} }},
  crypto: nodeCrypto,
  Math, Date, Number, String, Boolean, Array, Object, Set, Map, JSON, RegExp, Error,
  parseInt, parseFloat, isFinite, URLSearchParams,
  requestAnimationFrame(cb) {{ rafCb = cb; return 1; }},
  cancelAnimationFrame() {{}},
  setTimeout() {{ return 1; }},
  clearTimeout() {{}},
  setInterval() {{ return 1; }},
  clearInterval() {{}},
  EventSource: undefined,
  window: {{
    devicePixelRatio: 1,
    location: {{ search: '', hostname: 'localhost' }},
    addEventListener() {{}},
    removeEventListener() {{}},
  }},
  document: {{
    getElementById(id) {{ return id === 'buildCanvas' ? canvasEl : null; }},
    addEventListener() {{}},
  }},
}};
sandbox.globalThis = sandbox;
sandbox.window.window = sandbox.window;
sandbox.window.document = sandbox.document;

vm.runInNewContext(code, sandbox);
const cube = sandbox.window.FoundupCube;
assert(cube, 'FoundupCube exported on window');
cube.setFirestore(fakeDbProxy);
cube.init('buildCanvas', {{ useSimEvents: false }});

// First telemetry snapshot: 4 completed -> high block count + lineage/lease/verifier HUD
const res1 = cube.command('workTelemetrySync', {{
  observation_only: true,
  authority: 'none',
  source_mode: 'live_readonly',
  freshness: 'fresh',
  observed_at: {json.dumps(now_iso)},
  latest_event_at: {json.dumps(now_iso)},
  ttl_seconds: 300,
  counts_by_state: {{ spawn: 0, claim: 0, progress: 0, complete: 4, fail: 0, cancel: 0, stale: 0, unknown: 0 }},
  dependencies: [
    {{ from: 'u1', to: 'u2', relation: 'depends_on' }},
    {{ from: 'u2', to: 'u3', relation: 'parent_task' }},
    {{ from: 'u3', to: 'u4', relation: 'independent_assurance' }},
  ],
  work_units: [
    {{ work_id: 'u1', title: 'task 1', canonical_state: 'complete', swarm_lane: 'lane-obs', lease_active: true, verifier_agent: 'verifier-a' }},
    {{ work_id: 'u2', title: 'task 2', canonical_state: 'complete', swarm_lane: 'lane-obs', parent_work_id: 'u1', lease_active: true }},
    {{ work_id: 'u3', title: 'task 3', canonical_state: 'complete', swarm_lane: 'lane-wre', parent_work_id: 'u2', lease_active: false, verifier_agent: 'verifier-b' }},
    {{ work_id: 'u4', title: 'task 4', canonical_state: 'complete', swarm_lane: 'lane-wre', work_order_id: 'wo-9', lease_active: false, verifier_agent: 'verifier-a' }},
  ],
}});
assert.strictEqual(res1.observationOnly, true);
assert.strictEqual(res1.authority, 'none');
assert.strictEqual(res1.dependenciesCount, 3);
assert.strictEqual(res1.activeLeaseCount, 2);
assert.strictEqual(res1.verifierCount, 2);
assert.deepStrictEqual(Array.from(res1.lanes), ['lane-obs', 'lane-wre']);
assert.deepStrictEqual(Array.from(res1.verifiers), ['verifier-a', 'verifier-b']);
const st1 = cube.command('getState');
assert.strictEqual(st1.observationOnly, true);
assert.strictEqual(st1.authority, 'none');
assert.strictEqual(st1.workTelemetry.dependenciesCount, 3);
assert.strictEqual(st1.workTelemetry.activeLeaseCount, 2);
assert(st1.filledBlocks > 16, 'Expected blocks filled for complete tasks');

fillTexts.length = 0;
if (typeof rafCb === 'function') rafCb();
assert(fillTexts.includes('DEPS:3 LEASES:2'), 'Canvas HUD must show dependency and active lease counts');
assert(fillTexts.includes('LANES:2 VERIF:2'), 'Canvas HUD must show lane and verifier summary');
assert(fillTexts.some((t) => t.includes('OBS [FRESH] u:4 deps:3 leases:2 lanes:2 verifiers:2')), 'Ticker must show observation telemetry summary');

// Second telemetry snapshot: non-monotonic rollback (all tasks fail/cancel)
cube.command('workTelemetrySync', {{
  observation_only: true,
  authority: 'none',
  source_mode: 'live_readonly',
  freshness: 'fresh',
  observed_at: {json.dumps(now_iso)},
  latest_event_at: {json.dumps(now_iso)},
  ttl_seconds: 300,
  counts_by_state: {{ spawn: 0, claim: 0, progress: 0, complete: 0, fail: 2, cancel: 2, stale: 0, unknown: 0 }},
  work_units: [
    {{ work_id: 'u1', title: 'task 1', canonical_state: 'fail' }},
    {{ work_id: 'u2', title: 'task 2', canonical_state: 'cancel' }},
  ],
}});
const st2 = cube.command('getState');
assert.strictEqual(st2.filledBlocks, 0, 'Blocks must shrink non-monotonically on fail/cancel');

// Click on rendered agent must not promote or trigger Firestore writes
if (canvasHandlers.mousedown && canvasHandlers.mouseup) {{
  canvasHandlers.mousedown({{ clientX: 510, clientY: 270 }});
  canvasHandlers.mouseup({{ clientX: 510, clientY: 270 }});
}}
assert.strictEqual(firestoreWrites, 0, 'Observation-only mode must not write to Firestore');

// Render frame & check explicit labels
fillTexts.length = 0;
if (typeof rafCb === 'function') rafCb();
assert(fillTexts.includes('OBSERVATION ONLY'), 'Canvas must draw OBSERVATION ONLY');
assert(fillTexts.includes('NO AUTHORITY'), 'Canvas must draw NO AUTHORITY');

// Advance clock past TTL -> stale transition
const staleSummary = cube.command('advanceTelemetryClock', {{ nowMs: {stale_clock_ms} }});
assert.strictEqual(staleSummary.freshness, 'stale');
assert.strictEqual(staleSummary.sourceMode, 'stale');
fillTexts.length = 0;
if (typeof rafCb === 'function') rafCb();
assert(fillTexts.some((t) => t.includes('[STALE]')), 'Canvas must display STALE freshness indicator');

console.log('CUBE_VM_OK');
"""
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, f"Node VM check failed:\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
    assert "CUBE_VM_OK" in proc.stdout
