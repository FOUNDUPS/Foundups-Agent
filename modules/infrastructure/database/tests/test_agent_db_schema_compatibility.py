#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for AgentDB schema compatibility migrations."""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import threading
from pathlib import Path

from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager


def _reset_database(db_path: Path) -> None:
    DatabaseManager.reset_for_tests()
    DatabaseManager._db_path = str(db_path)


def test_agent_db_migrates_legacy_autonomous_task_schema() -> None:
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "legacy_foundups.db"
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE agents_autonomous_tasks (
                task_id TEXT PRIMARY KEY,
                description TEXT,
                required_skills JSON,
                estimated_complexity REAL,
                priority_score REAL,
                discovered_by TEXT DEFAULT 'autonomous_discovery',
                discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                context JSON,
                assigned_to TEXT,
                assigned_at DATETIME
            )
            """
        )
        conn.execute(
            """
            INSERT INTO agents_autonomous_tasks (
                task_id, description, required_skills, estimated_complexity, priority_score
            ) VALUES ('legacy-task', 'legacy description', '[]', 0.1, 0.5)
            """
        )
        conn.commit()
        conn.close()

        _reset_database(db_path)
        agent_db = AgentDB()

        columns = {row["name"] for row in agent_db.db.get_table_info("agents_autonomous_tasks")}
        assert "status" in columns
        assert "completed_at" in columns

        tasks = agent_db.get_autonomous_tasks()
        assert len(tasks) == 1
        assert tasks[0]["task_id"] == "legacy-task"
        assert tasks[0]["status"] == "pending"

        assert agent_db.assign_autonomous_task("legacy-task", "0102")
        assigned_rows = agent_db.db.execute_query(
            "SELECT status, assigned_to FROM agents_autonomous_tasks WHERE task_id = ?",
            ("legacy-task",),
        )
        assert assigned_rows[0]["status"] == "assigned"
        assert assigned_rows[0]["assigned_to"] == "0102"

        assert agent_db.complete_autonomous_task("legacy-task")
        completed_rows = agent_db.db.execute_query(
            "SELECT status, completed_at FROM agents_autonomous_tasks WHERE task_id = ?",
            ("legacy-task",),
        )
        assert completed_rows[0]["status"] == "completed"
        assert completed_rows[0]["completed_at"] is not None
    finally:
        DatabaseManager.reset_for_tests()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_agent_db_returns_recent_breadcrumb_agents() -> None:
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "breadcrumbs_foundups.db"
    try:
        _reset_database(db_path)
        agent_db = AgentDB()
        agent_db.add_breadcrumb(session_id="session-a", action="search", agent_id="0102")
        agent_db.add_breadcrumb(session_id="session-b", action="search", agent_id="0201")

        recent_agents = agent_db.get_recent_breadcrumb_agents(minutes=60, limit=10)

        assert "0102" in recent_agents
        assert "0201" in recent_agents
    finally:
        DatabaseManager.reset_for_tests()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_agent_db_persists_coordination_events_and_bounded_task_retry() -> None:
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "postmerge_foundups.db"
    try:
        _reset_database(db_path)
        agent_db = AgentDB()
        assert agent_db.create_coordination_event(
            "event-1",
            "holoindex_postmerge_maintenance",
            "wre",
            ["openclaw_supervisor"],
            {"target_repo_head_sha": "a" * 40},
        )
        event = agent_db.get_coordination_event_by_id("event-1")
        assert event is not None
        assert event["target_agents"] == ["openclaw_supervisor"]
        assert event["payload"]["target_repo_head_sha"] == "a" * 40

        assert agent_db.create_autonomous_task(
            task_id="task-1",
            description="maintenance",
            required_skills=["holo-search"],
            estimated_complexity=3.0,
            priority_score=19.0,
            context={"retry_count": 0},
        )
        assert not agent_db.create_autonomous_task_if_absent(
            task_id="task-1",
            description="must not replace",
            required_skills=[],
            estimated_complexity=0.0,
            priority_score=0.0,
            context={"retry_count": 99},
        )
        assert agent_db.get_autonomous_task_by_id("task-1")["context"] == {
            "retry_count": 0
        }
        agent_db.db.execute_write(
            "UPDATE agents_autonomous_tasks SET status = 'failed' WHERE task_id = ?",
            ("task-1",),
        )
        retry_context = {"retry_count": 1, "retry_not_before": "2026-07-26T00:00:00Z"}
        assert agent_db.schedule_autonomous_task_retry(
            "task-1",
            context=retry_context,
            retry_not_before=retry_context["retry_not_before"],
        )
        waiting = agent_db.get_autonomous_task_by_id("task-1")
        assert waiting is not None
        assert waiting["status"] == "retry_wait"
        assert waiting["context"] == retry_context
        assert agent_db.requeue_autonomous_task(
            "task-1", expected_status="retry_wait"
        )
        assert agent_db.get_autonomous_task_by_id("task-1")["status"] == "pending"
        assert not agent_db.requeue_autonomous_task(
            "task-1", expected_status="retry_wait"
        )
    finally:
        DatabaseManager.reset_for_tests()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_holoindex_postmerge_claim_and_completion_are_atomic() -> None:
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "postmerge_atomic.db"
    try:
        _reset_database(db_path)
        agent_db = AgentDB()
        task_id = "holoindex_postmerge_refresh:" + ("a" * 40)
        request_event_id = "holoindex_postmerge_requested:" + ("a" * 40)
        completion_event_id = "holoindex_postmerge_completed:" + ("a" * 40)
        authority_digest = "sha256:" + ("b" * 64)
        request_payload_digest = "sha256:" + ("c" * 64)
        request_payload = {"payload_digest": request_payload_digest}
        context = {
            "schema_version": "holoindex_postmerge_coordination_v1",
            "source": "holoindex_postmerge_coordinator",
            "target_repo_head_sha": "a" * 40,
            "authority_root_digest": authority_digest,
        }
        assert agent_db.create_coordination_event(
            request_event_id,
            "holoindex_postmerge_maintenance",
            "wre",
            ["openclaw_supervisor"],
            request_payload,
        )
        assert agent_db.create_autonomous_task_if_absent(
            task_id=task_id,
            description="exact SHA maintenance",
            required_skills=["holo-search"],
            estimated_complexity=3.0,
            priority_score=19.0,
            context=context,
        )

        barrier = threading.Barrier(4)
        claims: list[bool] = []
        claims_lock = threading.Lock()

        def claim() -> None:
            barrier.wait()
            accepted = agent_db.claim_holoindex_postmerge_task(
                task_id,
                "openclaw_supervisor",
                expected_source=context["source"],
                expected_schema_version=context["schema_version"],
                expected_target_repo_head_sha=context["target_repo_head_sha"],
                expected_authority_root_digest=authority_digest,
            )
            with claims_lock:
                claims.append(bool(accepted))

        threads = [threading.Thread(target=claim) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        assert claims.count(True) == 1
        assert claims.count(False) == 3
        claimed_task = agent_db.get_autonomous_task_by_id(task_id)
        claim_context = claimed_task["context"]
        claim_id = str(claim_context["claim_id"])
        claim_binding_digest = str(
            claim_context["claim_binding_digest"]
        )
        assert agent_db.start_holoindex_postmerge_execution(
            task_id,
            "openclaw_supervisor",
            claim_id=claim_id,
            claim_binding_digest=claim_binding_digest,
        )
        assert not agent_db.start_holoindex_postmerge_execution(
            task_id,
            "openclaw_supervisor",
            claim_id=claim_id,
            claim_binding_digest=claim_binding_digest,
        )

        completion_payload = {
            "schema_version": "holoindex_postmerge_coordination_v1",
            "payload_digest": "sha256:" + ("d" * 64),
        }
        assert not agent_db.commit_holoindex_postmerge_completion(
            task_id=task_id,
            agent_id="openclaw_supervisor",
            request_event_id=request_event_id,
            request_payload_digest="sha256:" + ("0" * 64),
            completion_event_id=completion_event_id,
            completion_payload=completion_payload,
            claim_id=claim_id,
            claim_binding_digest=claim_binding_digest,
        )
        assert agent_db.get_autonomous_task_by_id(task_id)["status"] == "executing"
        assert (
            agent_db.get_coordination_event_by_id(request_event_id)[
                "resolution_status"
            ]
            == "pending"
        )
        assert agent_db.get_coordination_event_by_id(completion_event_id) is None

        assert agent_db.commit_holoindex_postmerge_completion(
            task_id=task_id,
            agent_id="openclaw_supervisor",
            request_event_id=request_event_id,
            request_payload_digest=request_payload_digest,
            completion_event_id=completion_event_id,
            completion_payload=completion_payload,
            claim_id=claim_id,
            claim_binding_digest=claim_binding_digest,
        )
        assert agent_db.commit_holoindex_postmerge_completion(
            task_id=task_id,
            agent_id="openclaw_supervisor",
            request_event_id=request_event_id,
            request_payload_digest=request_payload_digest,
            completion_event_id=completion_event_id,
            completion_payload=completion_payload,
            claim_id=claim_id,
            claim_binding_digest=claim_binding_digest,
        )
        assert agent_db.get_autonomous_task_by_id(task_id)["status"] == "completed"
        assert (
            agent_db.get_coordination_event_by_id(request_event_id)[
                "resolution_status"
            ]
            == "completed"
        )
        assert (
            agent_db.get_coordination_event_by_id(completion_event_id)["payload"]
            == completion_payload
        )
    finally:
        DatabaseManager.reset_for_tests()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_holoindex_postmerge_reader_cannot_be_starved_by_global_top_ten() -> None:
    from modules.infrastructure.database.src.holoindex_postmerge_task_reader import (
        read_holoindex_postmerge_tasks,
    )

    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "postmerge_reader.db"
    try:
        _reset_database(db_path)
        agent_db = AgentDB()
        for index in range(12):
            assert agent_db.create_autonomous_task_if_absent(
                task_id=f"unrelated-{index}",
                description="higher priority unrelated work",
                required_skills=[],
                estimated_complexity=1.0,
                priority_score=100.0,
                context={"source": "self_audit"},
            )
        task_id = "holoindex_postmerge_refresh:" + ("a" * 40)
        assert agent_db.create_autonomous_task_if_absent(
            task_id=task_id,
            description="exact SHA maintenance",
            required_skills=["holo-search"],
            estimated_complexity=3.0,
            priority_score=19.0,
            context={"source": "holoindex_postmerge_coordinator"},
        )

        assert all(
            task["task_id"] != task_id
            for task in agent_db.get_autonomous_tasks(status="pending", limit=10)
        )
        selected = read_holoindex_postmerge_tasks(agent_db, limit=10)
        assert [task["task_id"] for task in selected] == [task_id]
    finally:
        DatabaseManager.reset_for_tests()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_holoindex_postmerge_assignment_reclaim_is_compare_and_swap() -> None:
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "postmerge_reclaim.db"
    try:
        _reset_database(db_path)
        agent_db = AgentDB()
        task_id = "holoindex_postmerge_refresh:" + ("a" * 40)
        context = {
            "schema_version": "holoindex_postmerge_coordination_v1",
            "source": "holoindex_postmerge_coordinator",
            "target_repo_head_sha": "a" * 40,
            "authority_root_digest": "sha256:" + ("b" * 64),
        }
        assert agent_db.create_autonomous_task_if_absent(
            task_id=task_id,
            description="exact SHA maintenance",
            required_skills=["holo-search"],
            estimated_complexity=3.0,
            priority_score=19.0,
            context=context,
        )
        claim_id = agent_db.claim_holoindex_postmerge_task(
            task_id,
            "openclaw_supervisor",
            expected_source=context["source"],
            expected_schema_version=context["schema_version"],
            expected_target_repo_head_sha=context["target_repo_head_sha"],
            expected_authority_root_digest=context["authority_root_digest"],
        )
        assert claim_id
        assigned = agent_db.get_autonomous_task_by_id(task_id)
        assigned_at = str(assigned["assigned_at"])
        claim_context = dict(assigned["context"])
        tampered_context = dict(claim_context)
        tampered_context["target_repo_head_sha"] = "b" * 40
        agent_db.db.execute_write(
            "UPDATE agents_autonomous_tasks SET context = ? WHERE task_id = ?",
            (json.dumps(tampered_context), task_id),
        )
        assert not agent_db.start_holoindex_postmerge_execution(
            task_id,
            "openclaw_supervisor",
            claim_id=claim_id,
            claim_binding_digest=str(
                claim_context["claim_binding_digest"]
            ),
        )
        agent_db.db.execute_write(
            "UPDATE agents_autonomous_tasks SET context = ? WHERE task_id = ?",
            (json.dumps(claim_context), task_id),
        )

        assert not agent_db.reclaim_expired_holoindex_postmerge_task(
            task_id,
            "openclaw_supervisor",
            expected_assigned_at="wrong",
        )
        assert agent_db.reclaim_expired_holoindex_postmerge_task(
            task_id,
            "openclaw_supervisor",
            expected_assigned_at=assigned_at,
        )
        assert agent_db.get_autonomous_task_by_id(task_id)["status"] == "failed"
        assert not agent_db.reclaim_expired_holoindex_postmerge_task(
            task_id,
            "openclaw_supervisor",
            expected_assigned_at=assigned_at,
        )
    finally:
        DatabaseManager.reset_for_tests()
        shutil.rmtree(temp_dir, ignore_errors=True)
