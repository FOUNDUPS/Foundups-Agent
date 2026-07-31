"""Starvation-safe reads for canonical HoloIndex post-merge tasks."""

from __future__ import annotations

import json
from typing import Any, Dict, List


def read_holoindex_postmerge_tasks(
    agent_db: Any,
    *,
    status: str = "pending",
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Read the protected task family without relying on a global top-N."""

    if not status or limit <= 0:
        return []
    rows = agent_db.db.execute_query(
        '''
        SELECT * FROM agents_autonomous_tasks
        WHERE status = ? AND task_id LIKE 'holoindex_postmerge_refresh:%'
        ORDER BY priority_score DESC, discovered_at DESC LIMIT ?
        ''',
        (status, limit),
    )
    for row in rows:
        for field in ("required_skills", "context"):
            if row[field] and isinstance(row[field], str):
                row[field] = json.loads(row[field])
    return rows


__all__ = ["read_holoindex_postmerge_tasks"]
