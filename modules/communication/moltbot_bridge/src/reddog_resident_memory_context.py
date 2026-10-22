"""Reusable resident RedDog memory-context readers.

This module owns bounded read-only projection of Brain, Breadcrumb and workspace
memory inputs used by resident transports. It does not create memory, mutate a
provider, grant execution authority, or replace FoundUp/Principal Memex.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

BreadcrumbSearch = Callable[[str, int], Sequence[Mapping[str, Any]]]


def truthy_env_value(value: str | None) -> bool:
    raw = str(value or "").strip().lower()
    return raw not in {"", "0", "false", "off", "no"}


def digest_payload(payload: Any) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def bounded_json_file(path: Path, *, max_bytes: int = 262_144) -> Any | None:
    try:
        if not path.is_file() or path.stat().st_size > max_bytes:
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def mapping_sequence(
    payload: Any, keys: Sequence[str], *, limit: int
) -> tuple[Mapping[str, Any], ...]:
    source: Any = payload
    if isinstance(payload, Mapping):
        for key in keys:
            candidate = payload.get(key)
            if isinstance(candidate, list):
                source = candidate
                break
    if not isinstance(source, list):
        return ()
    records: list[Mapping[str, Any]] = []
    for item in source:
        if isinstance(item, Mapping):
            records.append(dict(item))
            if len(records) >= limit:
                break
    return tuple(records)


def resident_memory_limit(environ: Mapping[str, str] | None = None) -> int:
    env = os.environ if environ is None else environ
    raw = str(env.get("REDDOG_RESIDENT_MEMORY_MAX_RECORDS", "20")).strip()
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 20
    return value if value > 0 else 20


def resident_brain_state_from_artifacts(
    environ: Mapping[str, str] | None = None,
) -> Mapping[str, Any] | None:
    env = os.environ if environ is None else environ
    if not truthy_env_value(env.get("REDDOG_RESIDENT_BRAIN_CONTEXT", "1")):
        return None

    raw_path = str(env.get("REDDOG_RESIDENT_BRAIN_STATE_PATH", "")).strip()
    if raw_path:
        path = Path(raw_path)
    else:
        try:
            from modules.infrastructure.wre_core.scripts.extract_brain_artifacts import (
                DEFAULT_OUTPUT_DIR,
                DEFAULT_STATE_FILE,
            )
        except Exception:
            return None
        path = DEFAULT_OUTPUT_DIR / DEFAULT_STATE_FILE

    payload = bounded_json_file(path)
    if not isinstance(payload, Mapping):
        return None
    signature = payload.get("signature") if isinstance(payload.get("signature"), Mapping) else {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    record_count = (
        payload.get("conversations")
        or signature.get("conversation_count", 0)
        or summary.get("total_artifacts", 0)
        or 0
    )
    try:
        normalized_count = int(record_count)
    except (TypeError, ValueError):
        normalized_count = 0
    return {
        "available": True,
        "signature_digest": digest_payload(signature),
        "summary_digest": digest_payload(summary),
        "record_count": normalized_count,
        "source": "brain_artifact_state",
        "updated_at": str(payload.get("updated_at", "")),
    }


def resident_breadcrumbs_from_runtime(
    *,
    work_focus: str,
    foundup_id: str,
    environ: Mapping[str, str] | None = None,
    breadcrumb_search: BreadcrumbSearch | None = None,
) -> tuple[Mapping[str, Any], ...]:
    env = os.environ if environ is None else environ
    if not truthy_env_value(env.get("REDDOG_RESIDENT_BREADCRUMBS_CONTEXT", "1")):
        return ()
    limit = resident_memory_limit(env)
    raw_path = str(env.get("REDDOG_RESIDENT_BREADCRUMBS_PATH", "")).strip()
    if raw_path:
        payload = bounded_json_file(Path(raw_path))
        return mapping_sequence(
            payload, ("breadcrumbs", "records", "items"), limit=limit
        )
    search = breadcrumb_search
    if search is None:
        try:
            from modules.communication.moltbot_bridge.src.openclaw_memory_queries import (
                search_breadcrumbs,
            )
        except Exception:
            return ()
        search = search_breadcrumbs
    try:
        topic = (
            str(env.get("REDDOG_RESIDENT_MEMORY_QUERY", "")).strip()
            or work_focus
            or foundup_id
        )
        return tuple(
            dict(item)
            for item in search(topic, limit=limit)
            if isinstance(item, Mapping)
        )
    except Exception:
        return ()


def resident_workspace_memory_notes_from_env(
    environ: Mapping[str, str] | None = None,
) -> tuple[Mapping[str, Any], ...]:
    env = os.environ if environ is None else environ
    raw_path = str(
        env.get("REDDOG_RESIDENT_WORKSPACE_MEMORY_NOTES_PATH", "")
    ).strip()
    if not raw_path:
        return ()
    payload = bounded_json_file(Path(raw_path))
    return mapping_sequence(
        payload,
        ("workspace_memory_notes", "notes", "records", "items"),
        limit=resident_memory_limit(env),
    )


__all__ = [
    "bounded_json_file",
    "digest_payload",
    "mapping_sequence",
    "resident_breadcrumbs_from_runtime",
    "resident_brain_state_from_artifacts",
    "resident_memory_limit",
    "resident_workspace_memory_notes_from_env",
    "truthy_env_value",
]
