"""Neutral AgentDB reader for architect determinations by receipt ID."""

from __future__ import annotations

import json
from typing import Any, Callable, Mapping, Optional


def load_agentdb_architect_determination(
    determination_id: str,
    *,
    agent_db_factory: Optional[Callable[[], Any]] = None,
) -> Mapping[str, Any] | None:
    """Read one immutable determination without creating authority state."""

    if not str(determination_id or "").strip():
        return None
    if agent_db_factory is None:
        from modules.infrastructure.database.src.agent_db import AgentDB

        agent_db_factory = AgentDB
    db = agent_db_factory()
    if not db.db.table_exists("reddog_architect_determinations"):
        return None
    rows = db.db.execute_query(
        "SELECT determination_json FROM reddog_architect_determinations "
        "WHERE determination_receipt_id = ?",
        (determination_id,),
    )
    if not rows:
        return None
    try:
        value = json.loads(str(rows[0]["determination_json"]))
    except (TypeError, ValueError, json.JSONDecodeError, KeyError):
        return None
    return value if isinstance(value, Mapping) else None


__all__ = ["load_agentdb_architect_determination"]
