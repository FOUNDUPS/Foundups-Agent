"""Starvation-safe reads for canonical HoloIndex post-merge tasks."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List


TASK_PREFIX = "holoindex_postmerge_refresh:"
TASK_ID_RE = re.compile(r"^holoindex_postmerge_refresh:[0-9a-f]{40}$")
SOURCE = "holoindex_postmerge_coordinator"
SCHEMA_VERSION = "holoindex_postmerge_coordination_v1"


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
        WHERE status = ?
          AND length(task_id) = ?
          AND substr(task_id, 1, ?) = ?
          AND substr(task_id, ?) NOT GLOB '*[^0-9a-f]*'
          AND json_valid(context) = 1
          AND json_extract(context, '$.source') = ?
          AND json_extract(context, '$.schema_version') = ?
        ORDER BY priority_score DESC, discovered_at DESC LIMIT ?
        ''',
        (
            status,
            len(TASK_PREFIX) + 40,
            len(TASK_PREFIX),
            TASK_PREFIX,
            len(TASK_PREFIX) + 1,
            SOURCE,
            SCHEMA_VERSION,
            limit,
        ),
    )
    accepted = []
    for row in rows:
        for field in ("required_skills", "context"):
            if row[field] and isinstance(row[field], str):
                row[field] = json.loads(row[field])
        context = row.get("context")
        if (
            TASK_ID_RE.fullmatch(str(row.get("task_id") or ""))
            and isinstance(context, dict)
            and context.get("source") == SOURCE
            and context.get("schema_version") == SCHEMA_VERSION
        ):
            accepted.append(row)
    return accepted


__all__ = ["read_holoindex_postmerge_tasks"]
