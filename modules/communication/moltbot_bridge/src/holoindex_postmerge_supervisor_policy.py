"""OpenClaw policy for the exact-SHA HoloIndex post-merge task family."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Mapping, Sequence


HOLOINDEX_POSTMERGE_SOURCE = "holoindex_postmerge_coordinator"


def holoindex_postmerge_enabled(
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Keep exact-SHA index maintenance active unless explicitly disabled."""

    env = os.environ if environ is None else environ
    return str(env.get("HOLOINDEX_POSTMERGE_COORDINATOR_ENABLED", "1")) == "1"


def is_holoindex_postmerge_task(task: Mapping[str, Any]) -> bool:
    context = task.get("context")
    return bool(
        isinstance(context, Mapping)
        and str(context.get("source") or "") == HOLOINDEX_POSTMERGE_SOURCE
    )


def maintenance_candidates(
    tasks: Sequence[Mapping[str, Any]],
    *,
    general_maintenance_enabled: bool,
    postmerge_enabled: bool,
) -> List[Dict[str, Any]]:
    """Limit default maintenance authority to the post-merge family."""

    if general_maintenance_enabled:
        return [dict(task) for task in tasks]
    if not postmerge_enabled:
        return []
    return [dict(task) for task in tasks if is_holoindex_postmerge_task(task)]


def exclude_holoindex_postmerge_tasks(
    tasks: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Keep exact-SHA maintenance out of the generic task executor."""

    return [dict(task) for task in tasks if not is_holoindex_postmerge_task(task)]


__all__ = [
    "exclude_holoindex_postmerge_tasks",
    "holoindex_postmerge_enabled",
    "is_holoindex_postmerge_task",
    "maintenance_candidates",
]
