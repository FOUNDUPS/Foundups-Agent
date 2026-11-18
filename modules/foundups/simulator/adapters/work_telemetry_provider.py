"""Read-only SQLite telemetry provider for observable swarm orchestration.

WSP 97 / ADDENDUM: OBSERVABLE_SWARM_ORCHESTRATION:
- Reads live AgentDB and PatternMemory SQLite tables using `?mode=ro` and
  `PRAGMA query_only = ON` (never mutates backing stores or triggers side effects).
- Normalizes work units into the 8 canonical states:
  spawn, claim, progress, complete, fail, cancel, stale, unknown.
- Enforces honest unknown/stale state transitions when backing stores are missing,
  leases/TTLs are expired, or completion lacks effect evidence.
- Strictly redacts local filesystem paths, credentials, and tokens.
- Marks every payload with `observation_only=True` and `authority="none"`.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from modules.foundups.simulator.frame_schema import (
    CANONICAL_WORK_STATES,
    WorkTelemetrySnapshot,
    WorkUnitFrame,
)

DEFAULT_TTL_SECONDS = 300.0
DEFAULT_LIMIT = 50
MAX_SUMMARY_LEN = 160

_WIN_PATH_RE = re.compile(r"[A-Za-z]:(?:\\|/)[^\s\"'<>|]+")
_POSIX_PATH_RE = re.compile(
    r"(?:^|(?<=[\s(\"'=:,]))/(?:Users|home|etc|var|tmp|opt|mnt|root|app|srv|private|Library)[^\s\"'<>|]*"
)
_UNC_PATH_RE = re.compile(r"\\\\[^\s\"'<>|]+")
_SECRET_PREFIX_RE = re.compile(
    r"\b(?:AIza[0-9A-Za-z_-]{8,}|sk-[0-9A-Za-z_-]{8,}|gh[pousr]_[0-9A-Za-z_]{8,}|xox[baprs]-[0-9A-Za-z-]+|oauth_token[^\s,;]*)\b"
)
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{6,}", re.IGNORECASE)
_KV_SECRET_RE = re.compile(
    r"\b(api[_-]?key|secret|token|password|passwd|credential|authorization)\s*([:=])\s*([^\s,;\"']+)",
    re.IGNORECASE,
)


def redact_sensitive_text(value: Any, max_len: int = MAX_SUMMARY_LEN) -> str:
    """Strip local paths, tokens, and secrets before exposing text telemetry."""
    if value is None:
        return ""
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    if not text:
        return ""
    text = _SECRET_PREFIX_RE.sub("[REDACTED_SECRET]", text)
    text = _BEARER_RE.sub("Bearer [REDACTED_SECRET]", text)
    text = _KV_SECRET_RE.sub(r"\1\2[REDACTED_SECRET]", text)
    text = _UNC_PATH_RE.sub("[REDACTED_PATH]", text)
    text = _WIN_PATH_RE.sub("[REDACTED_PATH]", text)
    text = _POSIX_PATH_RE.sub("[REDACTED_PATH]", text)
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return text


def _parse_iso_ts(value: Any) -> Optional[datetime]:
    """Parse ISO-8601 or epoch-like timestamp into aware UTC datetime."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass
    try:
        return datetime.fromtimestamp(float(raw), tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


def _connect_readonly(db_path: Optional[Path]) -> Tuple[Optional[sqlite3.Connection], Optional[str]]:
    """Open SQLite strictly in read-only mode, returning error code if unavailable."""
    if db_path is None:
        return None, "db_unconfigured"
    if not db_path.exists() or not db_path.is_file():
        return None, "db_missing"
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=2.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON;")
        return conn, None
    except sqlite3.Error:
        return None, "db_unreadable"


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(r["name"]) for r in rows}


def _safe_json_dict(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw or not isinstance(raw, str):
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, TypeError):
        return {}


def _scalar_redacted_or_none(value: Any, max_len: int = 64) -> Optional[str]:
    if value is None or isinstance(value, bool):
        return None
    if not isinstance(value, (str, int, float)):
        return None
    cleaned = redact_sensitive_text(value, max_len)
    return cleaned or None


def _add_dependency(
    dependencies: List[Dict[str, str]],
    seen_edges: set[Tuple[str, str, str]],
    from_id: Any,
    to_id: Any,
    relation: str,
) -> None:
    clean_from = _scalar_redacted_or_none(from_id, 64)
    clean_to = _scalar_redacted_or_none(to_id, 64)
    if not clean_from or not clean_to or clean_from == clean_to:
        return
    edge_key = (clean_from, clean_to, relation)
    if edge_key not in seen_edges:
        seen_edges.add(edge_key)
        dependencies.append(
            {
                "from": clean_from,
                "to": clean_to,
                "relation": relation,
            }
        )


def _extract_context_lineage(
    context_obj: Dict[str, Any],
    res_row: Optional[sqlite3.Row] = None,
) -> Tuple[Optional[str], Optional[str], Optional[str], List[str]]:
    """Extract parent_work_id, work_order_id, swarm_lane, and depends_on IDs."""
    parent_work_id = _scalar_redacted_or_none(context_obj.get("parent_task_id"), 64)

    raw_work_order = context_obj.get("work_order_id")
    if not raw_work_order:
        dispatch_rcpt = context_obj.get("signed_authority_worker_dispatch_receipt")
        if isinstance(dispatch_rcpt, dict):
            intents = dispatch_rcpt.get("dispatch_intents")
            if isinstance(intents, list) and intents and isinstance(intents[0], dict):
                raw_work_order = intents[0].get("work_order_id")
    if (
        not raw_work_order
        and res_row is not None
        and "work_order_id" in res_row.keys()
        and res_row["work_order_id"]
    ):
        raw_work_order = res_row["work_order_id"]
    work_order_id = _scalar_redacted_or_none(raw_work_order, 64)

    swarm_lane = _scalar_redacted_or_none(context_obj.get("swarm_lane"), 64)

    raw_deps = context_obj.get("depends_on")
    dep_ids: List[str] = []
    if isinstance(raw_deps, str):
        for part in raw_deps.split(","):
            cleaned = _scalar_redacted_or_none(part.strip(), 64)
            if cleaned:
                dep_ids.append(cleaned)
    elif isinstance(raw_deps, (list, tuple, set)):
        for item in raw_deps:
            cleaned = _scalar_redacted_or_none(item, 64)
            if cleaned:
                dep_ids.append(cleaned)

    return parent_work_id, work_order_id, swarm_lane, dep_ids


def _check_effect_evidence(
    context_obj: Dict[str, Any],
    reservation: Optional[sqlite3.Row] = None,
) -> Tuple[bool, Optional[str]]:
    """Verify whether recorded completion has credible effect evidence."""
    if context_obj.get("_effect_evidence") is False or context_obj.get("effect_evidence") is False:
        return False, "missing_effect_evidence"
    if reservation is not None:
        term_status = (reservation["terminal_status"] or "").strip().lower() if "terminal_status" in reservation.keys() else ""
        res_status = (reservation["status"] or "").strip().lower() if "status" in reservation.keys() else ""
        if res_status in {"completed", "complete"} and not term_status and not reservation["terminal_receipt_id"]:
            return False, "missing_terminal_receipt"
    return True, None


def _classify_task_state(
    task_row: sqlite3.Row,
    lease_row: Optional[sqlite3.Row],
    reservation_row: Optional[sqlite3.Row],
    now: datetime,
    ttl_seconds: float,
) -> Tuple[str, bool, bool, Optional[str], Optional[str], Optional[str]]:
    """Map task + lease + reservation rows into one of CANONICAL_WORK_STATES.

    Returns (canonical_state, effect_evidence, stale, unknown_reason, updated_at, expires_at).
    """
    raw_status = str(task_row["status"] or "").strip().lower()
    context_obj = _safe_json_dict(task_row["context"] if "context" in task_row.keys() else None)
    effect_evidence, unknown_reason = _check_effect_evidence(context_obj, reservation_row)

    discovered_at = task_row["discovered_at"] if "discovered_at" in task_row.keys() else None
    assigned_at = task_row["assigned_at"] if "assigned_at" in task_row.keys() else None
    completed_at = task_row["completed_at"] if "completed_at" in task_row.keys() else None
    lease_updated = lease_row["updated_at"] if (lease_row is not None and "updated_at" in lease_row.keys()) else None
    lease_expires = lease_row["lease_expires_at"] if (lease_row is not None and "lease_expires_at" in lease_row.keys()) else None
    res_expires = reservation_row["expires_at"] if (reservation_row is not None and "expires_at" in reservation_row.keys()) else None

    updated_at = completed_at or lease_updated or assigned_at or discovered_at
    expires_at = lease_expires or res_expires

    if not effect_evidence:
        return "unknown", False, False, unknown_reason, updated_at, expires_at

    # Independent assurance reservation terminal overrides if present
    if reservation_row is not None:
        res_term = str(reservation_row["terminal_status"] or "").strip().lower()
        res_state = str(reservation_row["status"] or "").strip().lower()
        if res_state in {"revoked", "cancelled", "canceled"} or res_term in {"revoked", "cancelled", "canceled"}:
            return "cancel", True, False, None, updated_at, expires_at
        if res_term in {"failed", "fail", "rejected", "changes_requested"}:
            return "fail", True, False, None, updated_at, expires_at

    if raw_status in {"cancelled", "canceled", "revoked", "aborted"}:
        return "cancel", True, False, None, updated_at, expires_at

    if raw_status in {"failed", "fail", "quarantined", "error", "rejected", "timed_out"}:
        return "fail", True, False, None, updated_at, expires_at

    if raw_status in {"completed", "complete", "done", "merged", "approved", "verified"}:
        if context_obj.get("_effect_evidence") is False:
            return "unknown", False, False, "missing_effect_evidence", updated_at, expires_at
        return "complete", True, False, None, updated_at, expires_at

    # Active/in-flight checks with honest lease/TTL expiry -> stale
    exp_dt = _parse_iso_ts(expires_at)
    upd_dt = _parse_iso_ts(updated_at)
    expired_by_lease = exp_dt is not None and exp_dt < now
    expired_by_ttl = (
        ttl_seconds > 0
        and upd_dt is not None
        and (now - upd_dt).total_seconds() > ttl_seconds
    )

    if raw_status in {"executing", "in_progress", "running", "progress", "verifying"}:
        if expired_by_lease or expired_by_ttl:
            return "stale", True, True, "lease_or_ttl_expired", updated_at, expires_at
        return "progress", True, False, None, updated_at, expires_at

    if raw_status in {"claimed", "claim", "assigned", "reserved"}:
        if expired_by_lease or expired_by_ttl:
            return "stale", True, True, "claim_expired", updated_at, expires_at
        return "claim", True, False, None, updated_at, expires_at

    if raw_status in {"pending", "queued", "spawn", "spawned", "open", "ready"}:
        if lease_row is not None:
            if expired_by_lease:
                return "stale", True, True, "lease_expired", updated_at, expires_at
            return "claim", True, False, None, updated_at, expires_at
        if expired_by_ttl:
            return "stale", True, True, "pending_ttl_expired", updated_at, expires_at
        return "spawn", True, False, None, updated_at, expires_at

    if raw_status == "stale":
        return "stale", True, True, "recorded_stale", updated_at, expires_at

    return "unknown", effect_evidence, False, f"unmapped_status:{raw_status or 'empty'}", updated_at, expires_at


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _default_agent_db_path() -> Optional[Path]:
    env_override = os.environ.get("FOUNDUPS_AGENT_DB_PATH")
    if env_override:
        return Path(env_override)
    candidate = _default_repo_root() / "data" / "foundups.db"
    return candidate if candidate.exists() else None


def _default_pattern_db_path() -> Optional[Path]:
    env_override = os.environ.get("FOUNDUPS_PATTERN_DB_PATH")
    if env_override:
        return Path(env_override)
    candidate = (
        _default_repo_root()
        / "modules"
        / "infrastructure"
        / "wre_core"
        / "data"
        / "pattern_memory.db"
    )
    return candidate if candidate.exists() else None


def build_work_telemetry_payload(
    *,
    agent_db_path: Optional[Path] = None,
    pattern_db_path: Optional[Path] = None,
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
    limit: int = DEFAULT_LIMIT,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Read real work telemetry in strict read-only mode and return JSON-safe dict."""
    now_dt = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    observed_at = now_dt.isoformat()
    safe_limit = max(1, min(int(limit), 200))
    safe_ttl = max(0.0, float(ttl_seconds))

    resolved_agent_db = agent_db_path if agent_db_path is not None else _default_agent_db_path()
    resolved_pattern_db = pattern_db_path if pattern_db_path is not None else _default_pattern_db_path()

    errors: List[str] = []
    work_units: List[WorkUnitFrame] = []
    dependencies: List[Dict[str, str]] = []
    seen_edges: set[Tuple[str, str, str]] = set()
    agent_map: Dict[str, Dict[str, Any]] = {}
    outcomes: List[Dict[str, Any]] = []
    timestamps: List[datetime] = []

    agent_conn, agent_err = _connect_readonly(resolved_agent_db)
    pattern_conn, pattern_err = _connect_readonly(resolved_pattern_db)

    if agent_err:
        errors.append(f"agent_db:{agent_err}")
    if pattern_err and pattern_err != "db_unconfigured":
        errors.append(f"pattern_db:{pattern_err}")

    try:
        if agent_conn is not None and _table_exists(agent_conn, "agents_autonomous_tasks"):
            leases_by_task: Dict[str, sqlite3.Row] = {}
            if _table_exists(agent_conn, "agents_signed_worker_execution_leases"):
                for lrow in agent_conn.execute(
                    "SELECT * FROM agents_signed_worker_execution_leases"
                ).fetchall():
                    leases_by_task[str(lrow["task_id"])] = lrow

            res_by_author_task: Dict[str, sqlite3.Row] = {}
            standalone_reservations: List[sqlite3.Row] = []
            if _table_exists(agent_conn, "agents_independent_assurance_reservations"):
                res_cols = _table_columns(agent_conn, "agents_independent_assurance_reservations")
                order_col = "reserved_at" if "reserved_at" in res_cols else "rowid"
                res_rows = agent_conn.execute(
                    f"SELECT * FROM agents_independent_assurance_reservations ORDER BY {order_col} DESC LIMIT ?",
                    (safe_limit,),
                ).fetchall()
                for rrow in res_rows:
                    author_tid = str(rrow["author_task_id"]) if "author_task_id" in rrow.keys() and rrow["author_task_id"] else ""
                    verifier_tid = str(rrow["verifier_task_id"]) if "verifier_task_id" in rrow.keys() and rrow["verifier_task_id"] else ""
                    if author_tid and author_tid not in res_by_author_task:
                        res_by_author_task[author_tid] = rrow
                    if author_tid and verifier_tid:
                        _add_dependency(
                            dependencies,
                            seen_edges,
                            author_tid,
                            verifier_tid,
                            "independent_assurance",
                        )
                    if not author_tid:
                        standalone_reservations.append(rrow)

            task_cols = _table_columns(agent_conn, "agents_autonomous_tasks")
            order_col = "discovered_at" if "discovered_at" in task_cols else "rowid"
            task_rows = agent_conn.execute(
                f"SELECT * FROM agents_autonomous_tasks ORDER BY {order_col} DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()

            for trow in task_rows:
                tid = redact_sensitive_text(trow["task_id"], 64) or str(trow["task_id"])
                raw_tid = str(trow["task_id"])
                lease_row = leases_by_task.get(raw_tid)
                res_row = res_by_author_task.get(raw_tid)
                context_obj = _safe_json_dict(
                    trow["context"] if "context" in trow.keys() else None
                )
                (
                    canonical_state,
                    effect_evidence,
                    is_stale,
                    unknown_reason,
                    updated_at,
                    expires_at,
                ) = _classify_task_state(trow, lease_row, res_row, now_dt, safe_ttl)

                (
                    parent_work_id,
                    work_order_id,
                    swarm_lane,
                    dep_ids,
                ) = _extract_context_lineage(context_obj, res_row)

                lease_exp_raw = (
                    lease_row["lease_expires_at"]
                    if (lease_row is not None and "lease_expires_at" in lease_row.keys())
                    else None
                )
                lease_exp_dt = _parse_iso_ts(lease_exp_raw)
                lease_row_active = lease_row is not None and (
                    lease_exp_dt is None or lease_exp_dt >= now_dt
                )
                ctx_lease_active = context_obj.get("lease_active") is True
                lease_active = bool(
                    (lease_row_active or ctx_lease_active)
                    and canonical_state in {"claim", "progress"}
                    and not is_stale
                )

                owner_agent = (
                    (lease_row["assigned_to"] if lease_row is not None else None)
                    or (trow["assigned_to"] if "assigned_to" in trow.keys() else None)
                    or (trow["discovered_by"] if "discovered_by" in trow.keys() else None)
                )
                verifier_agent = (
                    str(res_row["verifier_principal_id"])
                    if (res_row is not None and "verifier_principal_id" in res_row.keys() and res_row["verifier_principal_id"])
                    else None
                )
                raw_desc = trow["description"] if "description" in trow.keys() else tid
                unit = WorkUnitFrame(
                    work_id=tid,
                    title=redact_sensitive_text(raw_desc) or tid,
                    canonical_state=canonical_state,
                    raw_status=str(trow["status"] or "unknown"),
                    source_table="agents_autonomous_tasks",
                    owner_agent=redact_sensitive_text(owner_agent, 64) if owner_agent else None,
                    verifier_agent=redact_sensitive_text(verifier_agent, 64) if verifier_agent else None,
                    updated_at=str(updated_at) if updated_at is not None else None,
                    expires_at=str(expires_at) if expires_at is not None else None,
                    effect_evidence=effect_evidence,
                    stale=is_stale,
                    unknown_reason=unknown_reason,
                    parent_work_id=parent_work_id,
                    work_order_id=work_order_id,
                    swarm_lane=swarm_lane,
                    lease_active=lease_active,
                )
                work_units.append(unit)

                upd_dt = _parse_iso_ts(updated_at)
                if upd_dt is not None:
                    timestamps.append(upd_dt)

                for dep_id in dep_ids:
                    _add_dependency(dependencies, seen_edges, dep_id, tid, "depends_on")
                if parent_work_id:
                    _add_dependency(dependencies, seen_edges, parent_work_id, tid, "parent_task")

                origin_id = trow["origin_continuity_id"] if "origin_continuity_id" in trow.keys() else None
                if origin_id:
                    _add_dependency(
                        dependencies,
                        seen_edges,
                        origin_id,
                        tid,
                        "origin_continuity",
                    )

                if unit.owner_agent:
                    entry = agent_map.setdefault(
                        unit.owner_agent,
                        {
                            "agent_id": unit.owner_agent,
                            "role": "worker",
                            "latest_state": unit.canonical_state,
                            "unit_count": 0,
                        },
                    )
                    entry["unit_count"] += 1
                    entry["latest_state"] = unit.canonical_state
                if unit.verifier_agent:
                    ventry = agent_map.setdefault(
                        unit.verifier_agent,
                        {
                            "agent_id": unit.verifier_agent,
                            "role": "verifier",
                            "latest_state": unit.canonical_state,
                            "unit_count": 0,
                        },
                    )
                    ventry["unit_count"] += 1

            for rrow in standalone_reservations:
                rid = redact_sensitive_text(rrow["reservation_id"], 64) or str(rrow["reservation_id"])
                res_status = str(rrow["status"] or "").strip().lower()
                term_status = str(rrow["terminal_status"] or "").strip().lower() if "terminal_status" in rrow.keys() else ""
                has_ev, ev_reason = _check_effect_evidence({}, rrow)
                if not has_ev:
                    cstate = "unknown"
                elif res_status in {"revoked", "cancelled", "canceled"} or term_status in {"revoked", "cancelled", "canceled"}:
                    cstate = "cancel"
                elif term_status in {"failed", "fail", "rejected"}:
                    cstate = "fail"
                elif res_status in {"completed", "complete"}:
                    cstate = "complete"
                elif res_status in {"reserved", "open", "active"}:
                    exp_dt = _parse_iso_ts(rrow["expires_at"] if "expires_at" in rrow.keys() else None)
                    cstate = "stale" if (exp_dt is not None and exp_dt < now_dt) else "claim"
                else:
                    cstate = "unknown"
                upd_val = (
                    (rrow["completed_at"] if "completed_at" in rrow.keys() else None)
                    or (rrow["revoked_at"] if "revoked_at" in rrow.keys() else None)
                    or (rrow["reserved_at"] if "reserved_at" in rrow.keys() else None)
                )
                v_agent = rrow["verifier_principal_id"] if "verifier_principal_id" in rrow.keys() else None
                res_wo = (
                    _scalar_redacted_or_none(rrow["work_order_id"], 64)
                    if ("work_order_id" in rrow.keys() and rrow["work_order_id"])
                    else None
                )
                work_units.append(
                    WorkUnitFrame(
                        work_id=rid,
                        title=f"assurance:{redact_sensitive_text(rid, 48)}",
                        canonical_state=cstate,
                        raw_status=res_status or "unknown",
                        source_table="agents_independent_assurance_reservations",
                        owner_agent=redact_sensitive_text(v_agent, 64) if v_agent else None,
                        verifier_agent=redact_sensitive_text(v_agent, 64) if v_agent else None,
                        updated_at=str(upd_val) if upd_val is not None else None,
                        expires_at=str(rrow["expires_at"]) if "expires_at" in rrow.keys() and rrow["expires_at"] else None,
                        effect_evidence=has_ev,
                        stale=(cstate == "stale"),
                        unknown_reason=ev_reason,
                        work_order_id=res_wo,
                        lease_active=(cstate == "claim"),
                    )
                )
                upd_dt = _parse_iso_ts(upd_val)
                if upd_dt is not None:
                    timestamps.append(upd_dt)

        if pattern_conn is not None and _table_exists(pattern_conn, "skill_outcomes"):
            orows = pattern_conn.execute(
                "SELECT execution_id, skill_name, agent, timestamp, success, "
                "pattern_fidelity, outcome_quality, execution_time_ms, step_count, failed_at_step, notes "
                "FROM skill_outcomes ORDER BY timestamp DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
            for orow in orows:
                ts_val = orow["timestamp"]
                ts_dt = _parse_iso_ts(ts_val)
                if ts_dt is not None:
                    timestamps.append(ts_dt)
                success_flag = bool(orow["success"])
                notes_obj = _safe_json_dict(orow["notes"])
                if notes_obj.get("_effect_evidence") is False:
                    oc_state = "unknown"
                else:
                    oc_state = "complete" if success_flag else "fail"
                agent_name = redact_sensitive_text(orow["agent"], 64) or "unknown"
                outcomes.append(
                    {
                        "execution_id": redact_sensitive_text(orow["execution_id"], 64),
                        "skill_name": redact_sensitive_text(orow["skill_name"], 64),
                        "agent": agent_name,
                        "timestamp": str(ts_val) if ts_val is not None else None,
                        "canonical_state": oc_state,
                        "success": success_flag,
                        "pattern_fidelity": float(orow["pattern_fidelity"] or 0.0),
                        "outcome_quality": float(orow["outcome_quality"] or 0.0),
                        "execution_time_ms": int(orow["execution_time_ms"] or 0),
                        "step_count": int(orow["step_count"] or 0),
                        "failed_at_step": int(orow["failed_at_step"]) if orow["failed_at_step"] is not None else None,
                    }
                )
                if agent_name != "unknown" and agent_name not in agent_map:
                    agent_map[agent_name] = {
                        "agent_id": agent_name,
                        "role": "skill_runner",
                        "latest_state": oc_state,
                        "unit_count": 1,
                    }
    finally:
        if agent_conn is not None:
            agent_conn.close()
        if pattern_conn is not None:
            pattern_conn.close()

    counts_by_state: Dict[str, int] = {state: 0 for state in CANONICAL_WORK_STATES}
    for unit in work_units:
        key = unit.canonical_state if unit.canonical_state in counts_by_state else "unknown"
        counts_by_state[key] += 1

    latest_dt = max(timestamps) if timestamps else None
    latest_event_at = latest_dt.isoformat() if latest_dt is not None else None
    age_seconds = round(max(0.0, (now_dt - latest_dt).total_seconds()), 3) if latest_dt is not None else None

    if agent_conn is None and pattern_conn is None:
        freshness = "unknown"
        source_mode = "unknown"
    elif not work_units and not outcomes:
        freshness = "unknown"
        source_mode = "unknown" if errors else "empty_live"
    elif latest_dt is not None and safe_ttl > 0 and (now_dt - latest_dt).total_seconds() > safe_ttl:
        freshness = "stale"
        source_mode = "stale"
    elif errors:
        freshness = "fresh"
        source_mode = "degraded_partial"
    else:
        freshness = "fresh"
        source_mode = "live_readonly"

    snapshot = WorkTelemetrySnapshot(
        source_mode=source_mode,
        freshness=freshness,
        observed_at=observed_at,
        ttl_seconds=safe_ttl,
        counts_by_state=counts_by_state,
        work_units=work_units,
        observation_only=True,
        authority="none",
        age_seconds=age_seconds,
        latest_event_at=latest_event_at,
        errors=errors,
    )

    return {
        "schema_version": "1.0.0",
        "observation_only": snapshot.observation_only,
        "authority": snapshot.authority,
        "source_mode": snapshot.source_mode,
        "freshness": snapshot.freshness,
        "observed_at": snapshot.observed_at,
        "latest_event_at": snapshot.latest_event_at,
        "age_seconds": snapshot.age_seconds,
        "ttl_seconds": snapshot.ttl_seconds,
        "canonical_states": list(CANONICAL_WORK_STATES),
        "counts_by_state": snapshot.counts_by_state,
        "total_work_units": len(snapshot.work_units),
        "active_lease_count": sum(1 for u in snapshot.work_units if u.lease_active),
        "swarm_lanes": sorted({u.swarm_lane for u in snapshot.work_units if u.swarm_lane}),
        "work_units": [
            {
                "work_id": u.work_id,
                "title": u.title,
                "canonical_state": u.canonical_state,
                "raw_status": u.raw_status,
                "source_table": u.source_table,
                "owner_agent": u.owner_agent,
                "verifier_agent": u.verifier_agent,
                "updated_at": u.updated_at,
                "expires_at": u.expires_at,
                "effect_evidence": u.effect_evidence,
                "stale": u.stale,
                "unknown_reason": u.unknown_reason,
                "parent_work_id": u.parent_work_id,
                "work_order_id": u.work_order_id,
                "swarm_lane": u.swarm_lane,
                "lease_active": u.lease_active,
            }
            for u in snapshot.work_units
        ],
        "agents": list(agent_map.values()),
        "dependencies": dependencies,
        "outcomes_summary": {
            "count": len(outcomes),
            "success_count": sum(1 for o in outcomes if o["success"]),
            "fail_count": sum(1 for o in outcomes if not o["success"]),
            "recent": outcomes[:20],
        },
        "errors": list(snapshot.errors or []),
    }


def get_work_telemetry_snapshot(
    *,
    agent_db_path: Optional[Path] = None,
    pattern_db_path: Optional[Path] = None,
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
    limit: int = DEFAULT_LIMIT,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Public entrypoint returning a redacted, read-only telemetry payload."""
    return build_work_telemetry_payload(
        agent_db_path=agent_db_path,
        pattern_db_path=pattern_db_path,
        ttl_seconds=ttl_seconds,
        limit=limit,
        now=now,
    )
