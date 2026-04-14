"""
AI Overseer Perception Tools for FoundUps MCP Bridge.

Read-only access to Overseer state: missions, patterns, violations, coordination.

WSP References:
- WSP 48: Recursive Self-Improvement (pattern memory)
- WSP 77: Agent Coordination (mission state)
- WSP 97: Truthful verification
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .response_schema import ok_response, error_response

logger = logging.getLogger(__name__)

# Overseer memory locations
OVERSEER_MEMORY = "modules/ai_intelligence/ai_overseer/memory"
PATTERN_MEMORY = "holo_index/adaptive_learning"


def get_mission_history(repo_root: Path, limit: int = 20) -> Dict[str, Any]:
    """
    Get recent AI Overseer mission history.

    Args:
        repo_root: Repository root path
        limit: Maximum missions (default 20)

    Returns:
        MCPResponse with mission records
    """
    try:
        missions = []

        # Check SQLite database (WSP 78 persistence)
        db_path = repo_root / OVERSEER_MEMORY / "overseer.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            try:
                cur.execute("""
                    SELECT mission_id, mission_type, status, created_at, completed_at,
                           phases_completed, phases_failed, error_count
                    FROM missions
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))

                for row in cur.fetchall():
                    missions.append(dict(row))
            except sqlite3.OperationalError:
                # Table may not exist yet
                pass
            finally:
                conn.close()

        # Also check JSONL history
        history_path = repo_root / OVERSEER_MEMORY / "mission_history.jsonl"
        if history_path.exists() and len(missions) < limit:
            lines = history_path.read_text(encoding="utf-8").strip().split("\n")
            for line in reversed(lines[-limit:]):
                try:
                    mission = json.loads(line)
                    if mission.get("mission_id") not in [m.get("mission_id") for m in missions]:
                        missions.append(mission)
                except json.JSONDecodeError:
                    continue

        missions = missions[:limit]

        return ok_response(
            {
                "missions": missions,
                "count": len(missions),
                "sources": ["sqlite", "jsonl"],
            },
            source="overseer",
            limit=limit,
        )

    except Exception as e:
        logger.error(f"[MCP] get_mission_history error: {e}")
        return error_response(str(e))


def get_pattern_memory(repo_root: Path, limit: int = 50) -> Dict[str, Any]:
    """
    Get AI Overseer learned patterns (WSP 48 recursive improvement).

    Args:
        repo_root: Repository root path
        limit: Maximum patterns (default 50)

    Returns:
        MCPResponse with pattern records
    """
    try:
        patterns = []

        # Check adaptive learning patterns
        pattern_files = [
            repo_root / PATTERN_MEMORY / "ai_overseer_patterns.json",
            repo_root / PATTERN_MEMORY / "refactoring_patterns.json",
            repo_root / PATTERN_MEMORY / "error_patterns.json",
        ]

        for pfile in pattern_files:
            if not pfile.exists():
                continue

            try:
                data = json.loads(pfile.read_text(encoding="utf-8"))
                source_name = pfile.stem

                if isinstance(data, list):
                    for pattern in data[:limit]:
                        pattern["_source"] = source_name
                        patterns.append(pattern)
                elif isinstance(data, dict):
                    # May be keyed by pattern type
                    for key, value in data.items():
                        if isinstance(value, list):
                            for pattern in value[:limit]:
                                if isinstance(pattern, dict):
                                    pattern["_source"] = source_name
                                    pattern["_category"] = key
                                    patterns.append(pattern)
                        elif isinstance(value, dict):
                            value["_source"] = source_name
                            value["_category"] = key
                            patterns.append(value)
            except json.JSONDecodeError:
                continue

        patterns = patterns[:limit]

        return ok_response(
            {
                "patterns": patterns,
                "count": len(patterns),
                "sources": [str(p.relative_to(repo_root)) for p in pattern_files if p.exists()],
            },
            source="overseer",
            limit=limit,
        )

    except Exception as e:
        logger.error(f"[MCP] get_pattern_memory error: {e}")
        return error_response(str(e))


def get_overseer_status(repo_root: Path) -> Dict[str, Any]:
    """
    Get current AI Overseer system status.

    Args:
        repo_root: Repository root path

    Returns:
        MCPResponse with overseer status
    """
    try:
        status = {
            "available": False,
            "db_exists": False,
            "pattern_memory_exists": False,
            "security_monitor_active": False,
            "wsp_audit_status": None,
            "last_mission": None,
        }

        # Check DB
        db_path = repo_root / OVERSEER_MEMORY / "overseer.db"
        status["db_exists"] = db_path.exists()

        # Check pattern memory
        pattern_path = repo_root / PATTERN_MEMORY / "ai_overseer_patterns.json"
        status["pattern_memory_exists"] = pattern_path.exists()

        # Check WSP audit status
        audit_cache = repo_root / OVERSEER_MEMORY / "wsp_framework_audit_cache.json"
        if audit_cache.exists():
            try:
                audit_data = json.loads(audit_cache.read_text(encoding="utf-8"))
                status["wsp_audit_status"] = {
                    "severity": audit_data.get("severity"),
                    "drift_count": audit_data.get("drift_count"),
                    "checked_at": audit_data.get("checked_at"),
                }
            except json.JSONDecodeError:
                pass

        # Check OpenClaw security cache
        security_cache = repo_root / OVERSEER_MEMORY / "openclaw_security_cache.json"
        if security_cache.exists():
            try:
                sec_data = json.loads(security_cache.read_text(encoding="utf-8"))
                status["security_monitor_active"] = sec_data.get("passed", False)
            except json.JSONDecodeError:
                pass

        # Get last mission
        if status["db_exists"]:
            try:
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("""
                    SELECT mission_id, mission_type, status, created_at
                    FROM missions
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                row = cur.fetchone()
                if row:
                    status["last_mission"] = dict(row)
                conn.close()
            except sqlite3.OperationalError:
                pass

        status["available"] = status["db_exists"] or status["pattern_memory_exists"]

        return ok_response(status, source="overseer")

    except Exception as e:
        logger.error(f"[MCP] get_overseer_status error: {e}")
        return error_response(str(e))


def get_coordination_state(repo_root: Path) -> Dict[str, Any]:
    """
    Get current agent coordination state (WSP 77).

    Args:
        repo_root: Repository root path

    Returns:
        MCPResponse with coordination state
    """
    try:
        state = {
            "active_teams": [],
            "pending_approvals": [],
            "recent_phases": [],
        }

        db_path = repo_root / OVERSEER_MEMORY / "overseer.db"
        if not db_path.exists():
            return ok_response(state, source="overseer", note="No coordination database found")

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        try:
            # Active teams (missions not completed)
            cur.execute("""
                SELECT mission_id, mission_type, status, created_at
                FROM missions
                WHERE status NOT IN ('completed', 'failed', 'cancelled')
                ORDER BY created_at DESC
                LIMIT 10
            """)
            state["active_teams"] = [dict(row) for row in cur.fetchall()]

            # Recent phases
            cur.execute("""
                SELECT mission_id, phase_number, phase_name, status, started_at, completed_at
                FROM phases
                ORDER BY started_at DESC
                LIMIT 20
            """)
            state["recent_phases"] = [dict(row) for row in cur.fetchall()]

        except sqlite3.OperationalError as e:
            state["error"] = f"Database query failed: {e}"
        finally:
            conn.close()

        return ok_response(state, source="overseer")

    except Exception as e:
        logger.error(f"[MCP] get_coordination_state error: {e}")
        return error_response(str(e))


def get_known_failure_patterns(repo_root: Path, limit: int = 30) -> Dict[str, Any]:
    """
    Get known failure patterns for error avoidance (WSP 48).

    Args:
        repo_root: Repository root path
        limit: Maximum patterns (default 30)

    Returns:
        MCPResponse with failure patterns
    """
    try:
        failures = []

        # Check error patterns file
        error_patterns_path = repo_root / PATTERN_MEMORY / "error_patterns.json"
        if error_patterns_path.exists():
            try:
                data = json.loads(error_patterns_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    failures.extend(data[:limit])
                elif isinstance(data, dict):
                    for category, patterns in data.items():
                        if isinstance(patterns, list):
                            for p in patterns:
                                if isinstance(p, dict):
                                    p["_category"] = category
                                    failures.append(p)
            except json.JSONDecodeError:
                pass

        # Check self-audit task log
        task_log = repo_root / OVERSEER_MEMORY / "self_audit_tasks.jsonl"
        if task_log.exists():
            lines = task_log.read_text(encoding="utf-8").strip().split("\n")
            for line in reversed(lines[-limit:]):
                try:
                    task = json.loads(line)
                    if task.get("auto_fix_result") == "failed":
                        failures.append({
                            "type": "self_audit_failure",
                            "signature": task.get("signature"),
                            "source_file": task.get("source_file"),
                            "recommended_fix": task.get("recommended_fix"),
                        })
                except json.JSONDecodeError:
                    continue

        # Check incident alerts
        incidents_path = repo_root / OVERSEER_MEMORY / "openclaw_incident_alerts.jsonl"
        if incidents_path.exists():
            lines = incidents_path.read_text(encoding="utf-8").strip().split("\n")
            for line in reversed(lines[-limit:]):
                try:
                    incident = json.loads(line)
                    failures.append({
                        "type": "incident",
                        "incident_id": incident.get("incident_id"),
                        "severity": incident.get("severity"),
                        "policy_trigger": incident.get("policy_trigger"),
                    })
                except json.JSONDecodeError:
                    continue

        failures = failures[:limit]

        return ok_response(
            {"failures": failures, "count": len(failures)},
            source="overseer",
            limit=limit,
        )

    except Exception as e:
        logger.error(f"[MCP] get_known_failure_patterns error: {e}")
        return error_response(str(e))
