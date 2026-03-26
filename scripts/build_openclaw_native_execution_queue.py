#!/usr/bin/env python3
"""
Build the canonical OpenClaw native execution queue from machine-readable backlog files.

This locks in prior WSP 97 decisions and shifts later cycles to drift-audit
instead of re-deciding the architecture question every time.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "workspace"
    / "reports"
)
QUEUE_PATH = REPORTS_DIR / "openclaw_native_execution_queue.json"
STATUS_PATH = REPORTS_DIR / "openclaw_native_execution_queue_status.json"


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def priority_rank(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}.get(str(priority).upper(), 9)


def backlog_files() -> List[Path]:
    return sorted(REPORTS_DIR.glob("*_backlog_*.json"))


def latest_mtime_for_path(path: Path) -> datetime | None:
    if not path.exists():
        return None
    latest_ts = path.stat().st_mtime
    if path.is_dir():
        for child in path.rglob("*"):
            try:
                if child.exists():
                    latest_ts = max(latest_ts, child.stat().st_mtime)
            except Exception:
                continue
    return datetime.fromtimestamp(latest_ts, tz=UTC)


def build_queue_item(source_file: Path, source_data: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
    backlog_generated = parse_iso(source_data.get("generated_on"))
    owner_modules = [str(path) for path in item.get("owner_modules", [])]
    missing_owner_paths: List[str] = []
    latest_owner_change: datetime | None = None

    for raw_path in owner_modules:
        path = REPO_ROOT / raw_path if not Path(raw_path).is_absolute() else Path(raw_path)
        if not path.exists():
            missing_owner_paths.append(raw_path)
            continue
        mtime = latest_mtime_for_path(path)
        if mtime and (latest_owner_change is None or mtime > latest_owner_change):
            latest_owner_change = mtime

    repo_changed_since_backlog = bool(
        backlog_generated and latest_owner_change and latest_owner_change > backlog_generated
    )
    drift_state = "audit_required" if (repo_changed_since_backlog or missing_owner_paths) else "ready"

    return {
        "queue_id": f"{source_file.stem}:{item.get('id', 'unknown')}",
        "source_backlog": str(source_file.relative_to(REPO_ROOT)),
        "source_theme": source_data.get("theme", source_file.stem),
        "id": item.get("id"),
        "title": item.get("summary", item.get("id", "unknown")),
        "priority": item.get("priority", "P3"),
        "wsp15": item.get("wsp15", {}),
        "owner_modules": owner_modules,
        "acceptance": item.get("acceptance", []),
        "wsp97_locked": True,
        "redecision_required": False,
        "drift_state": drift_state,
        "repo_changed_since_backlog": repo_changed_since_backlog,
        "latest_owner_change": latest_owner_change.isoformat() if latest_owner_change else None,
        "missing_owner_paths": missing_owner_paths,
        "backlog_generated_on": source_data.get("generated_on"),
    }


def build_queue() -> Dict[str, Any]:
    queue_items: List[Dict[str, Any]] = []
    completed_items: List[Dict[str, Any]] = []
    sources: List[str] = []

    for path in backlog_files():
        try:
            source_data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        sources.append(str(path.relative_to(REPO_ROOT)))
        for item in source_data.get("items", []):
            # Skip completed items from active queue
            if item.get("status") == "completed":
                completed_items.append({
                    "id": item.get("id"),
                    "title": item.get("summary", item.get("id", "unknown")),
                    "completed_by_pr": item.get("completed_by_pr"),
                    "completed_on": item.get("completed_on"),
                })
                continue
            queue_items.append(build_queue_item(path, source_data, item))

    queue_items.sort(
        key=lambda item: (
            priority_rank(item.get("priority", "P4")),
            -int((item.get("wsp15") or {}).get("total", 0)),
            item.get("title", ""),
        )
    )
    ready_items = [item for item in queue_items if item.get("drift_state") == "ready"]
    audit_items = [item for item in queue_items if item.get("drift_state") == "audit_required"]

    return {
        "generated_on": utc_now_iso(),
        "queue_count": len(queue_items),
        "ready_count": len(ready_items),
        "audit_required_count": len(audit_items),
        "completed_count": len(completed_items),
        "sources": sources,
        "items": queue_items,
        "completed_items": completed_items,
        "next_ready": ready_items[:5],
        "next_audit": audit_items[:5],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the OpenClaw native execution queue.")
    parser.add_argument("--queue-out", type=Path, default=QUEUE_PATH)
    parser.add_argument("--status-out", type=Path, default=STATUS_PATH)
    args = parser.parse_args()

    queue = build_queue()
    args.queue_out.write_text(json.dumps(queue, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    status = {
        "generated_on": queue["generated_on"],
        "queue_count": queue["queue_count"],
        "ready_count": queue["ready_count"],
        "audit_required_count": queue["audit_required_count"],
        "completed_count": queue["completed_count"],
        "sources": queue["sources"],
        "next_ready": [
            {"queue_id": item["queue_id"], "title": item["title"], "priority": item["priority"]}
            for item in queue["next_ready"]
        ],
        "next_audit": [
            {
                "queue_id": item["queue_id"],
                "title": item["title"],
                "priority": item["priority"],
                "missing_owner_paths": item["missing_owner_paths"],
                "repo_changed_since_backlog": item["repo_changed_since_backlog"],
            }
            for item in queue["next_audit"]
        ],
        "recently_completed": queue["completed_items"][:5],
    }
    args.status_out.write_text(json.dumps(status, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(f"[OK] Queue written to {args.queue_out}")
    print(f"[OK] Status written to {args.status_out}")
    print(f"[OK] Queue items: {queue['queue_count']}")
    print(f"[OK] Ready: {queue['ready_count']}")
    print(f"[OK] Audit required: {queue['audit_required_count']}")
    print(f"[OK] Completed: {queue['completed_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
