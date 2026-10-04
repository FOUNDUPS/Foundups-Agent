#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Post-commit social runner.

Fast local git hooks should call this script in the background instead of
posting directly. The runner builds a durable git_push event, appends it to a
JSONL spool. Dispatch through SocialMediaEventRouter requires explicit opt-in.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _run_git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return result.stdout.strip()


def collect_git_context(repo_root: Path) -> Dict[str, Any]:
    changed_files = [
        line.strip()
        for line in _run_git(repo_root, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()
        if line.strip()
    ]
    commit_hash = _run_git(repo_root, "rev-parse", "--short", "HEAD")
    subject = _run_git(repo_root, "log", "-1", "--pretty=%s")
    message = _run_git(repo_root, "log", "-1", "--pretty=%B")
    branch = _run_git(repo_root, "branch", "--show-current")
    repository = repo_root.name

    return {
        "repository": repository,
        "branch": branch,
        "commits": [
            {
                "hash": commit_hash,
                "subject": subject,
                "message": message.strip(),
                "files_changed": len(changed_files),
                "files": changed_files,
            }
        ],
    }


def build_git_push_event(repo_root: Path) -> Dict[str, Any]:
    payload = collect_git_context(repo_root)
    commit = payload["commits"][0]
    dedupe_key = f"git_push:{payload['branch']}:{commit['hash']}"
    return {
        "event": "git_push",
        "event_type": "git_push",
        "source_daemon": "git_hook",
        "timestamp": datetime.now().isoformat(),
        "priority": 1,
        "dedupe_key": dedupe_key,
        "payload": payload,
    }


def append_jsonl_record(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _get_social_media_router_class():
    from modules.platform_integration.social_media_orchestrator.src.multi_account_manager import (
        SocialMediaEventRouter,
    )

    return SocialMediaEventRouter


async def dispatch_git_push_event(event: Dict[str, Any]) -> Dict[str, Any]:
    router_class = _get_social_media_router_class()
    router = router_class()
    return await router.handle_event("git_push", event["payload"])


async def run_runner(
    repo_root: Path,
    events_file: Path,
    results_file: Path,
    enqueue_only: bool = True,
) -> int:
    event = build_git_push_event(repo_root)
    append_jsonl_record(events_file, event)
    print(f"[0102] post-commit runner: queued {event['dedupe_key']}")

    if enqueue_only:
        return 0

    try:
        result = await dispatch_git_push_event(event)
        append_jsonl_record(
            results_file,
            {
                "timestamp": datetime.now().isoformat(),
                "dedupe_key": event["dedupe_key"],
                "result": result,
            },
        )
        print("[0102] post-commit runner: dispatch complete")
        return 0
    except Exception as exc:
        append_jsonl_record(
            results_file,
            {
                "timestamp": datetime.now().isoformat(),
                "dedupe_key": event["dedupe_key"],
                "error": str(exc),
            },
        )
        print(f"[0102] post-commit runner: dispatch error: {exc}")
        return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Queue and dispatch post-commit social events.")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--events-file", default=None, help="JSONL spool file for git_push events")
    parser.add_argument("--results-file", default=None, help="JSONL file for dispatch results")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--enqueue-only", dest="enqueue_only", action="store_true",
                      help="Only queue the event (default); do not dispatch")
    mode.add_argument("--dispatch", dest="enqueue_only", action="store_false",
                      help="Queue and explicitly dispatch through the social router")
    parser.set_defaults(enqueue_only=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    events_file = Path(args.events_file) if args.events_file else repo_root / "memory" / "git_push_events.jsonl"
    results_file = Path(args.results_file) if args.results_file else repo_root / "memory" / "git_push_dispatch_results.jsonl"
    return asyncio.run(run_runner(repo_root, events_file, results_file, enqueue_only=args.enqueue_only))


if __name__ == "__main__":
    raise SystemExit(main())
