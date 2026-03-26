#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI for managing natural-language OpenClaw scheduled routines.

Usage:
    python scripts/manage_schedules.py add "run self research daily"
    python scripts/manage_schedules.py list
    python scripts/manage_schedules.py remove <schedule_id>
    python scripts/manage_schedules.py disable <schedule_id>
    python scripts/manage_schedules.py enable <schedule_id>
    python scripts/manage_schedules.py due
    python scripts/manage_schedules.py phrases
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from modules.infrastructure.idle_automation.src.schedule_evaluator import (
    ScheduleEvaluator,
    ScheduleParser,
    get_supported_phrases,
)


def cmd_add(args: argparse.Namespace) -> int:
    """Add a new schedule from a natural-language phrase."""
    phrase = " ".join(args.phrase)

    # Validate first
    parsed = ScheduleParser.parse(phrase)
    if parsed is None:
        print(f"[ERROR] Could not parse phrase: {phrase!r}")
        print("\nSupported phrases:")
        for ex in get_supported_phrases()[:6]:
            print(f"  {ex}")
        return 1

    evaluator = ScheduleEvaluator()
    spec = evaluator.add_schedule(phrase)

    if spec:
        print(f"[OK] Schedule added: {spec.id}")
        print(f"     Phrase: {spec.phrase}")
        print(f"     Routine: {spec.routine}")
        print(f"     Cadence: {spec.cadence}")
        return 0
    return 1


def cmd_list(args: argparse.Namespace) -> int:
    """List all schedules."""
    evaluator = ScheduleEvaluator()
    schedules = evaluator.list_schedules()

    if not schedules:
        print("[INFO] No schedules configured")
        return 0

    print(f"[OK] {len(schedules)} schedule(s):\n")
    for spec in schedules:
        status = "enabled" if spec.enabled else "DISABLED"
        last_run = spec.last_run[:19] if spec.last_run else "never"
        print(f"  {spec.id}  [{status}]")
        print(f"    Phrase: {spec.phrase}")
        print(f"    Routine: {spec.routine} | Cadence: {spec.cadence}")
        print(f"    Last run: {last_run}")
        if spec.last_result:
            print(f"    Result: {spec.last_result}")
        print()

    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    """Remove a schedule by ID."""
    evaluator = ScheduleEvaluator()

    if evaluator.remove_schedule(args.schedule_id):
        print(f"[OK] Schedule removed: {args.schedule_id}")
        return 0

    print(f"[ERROR] Schedule not found: {args.schedule_id}")
    return 1


def cmd_enable(args: argparse.Namespace) -> int:
    """Enable a schedule."""
    evaluator = ScheduleEvaluator()

    if evaluator.set_enabled(args.schedule_id, True):
        print(f"[OK] Schedule enabled: {args.schedule_id}")
        return 0

    print(f"[ERROR] Schedule not found: {args.schedule_id}")
    return 1


def cmd_disable(args: argparse.Namespace) -> int:
    """Disable a schedule."""
    evaluator = ScheduleEvaluator()

    if evaluator.set_enabled(args.schedule_id, False):
        print(f"[OK] Schedule disabled: {args.schedule_id}")
        return 0

    print(f"[ERROR] Schedule not found: {args.schedule_id}")
    return 1


def cmd_due(args: argparse.Namespace) -> int:
    """Show schedules that are currently due."""
    evaluator = ScheduleEvaluator()
    due = evaluator.get_due_schedules()

    if not due:
        print("[INFO] No schedules currently due")
        return 0

    print(f"[OK] {len(due)} schedule(s) due:\n")
    for spec in due:
        print(f"  {spec.id}: {spec.routine} ({spec.cadence})")
        print(f"    Phrase: {spec.phrase}")
        print()

    return 0


def cmd_phrases(args: argparse.Namespace) -> int:
    """Show all supported schedule phrases."""
    print("[OK] Supported schedule phrases:\n")
    for phrase in get_supported_phrases():
        print(f"  {phrase}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manage natural-language OpenClaw scheduled routines"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # add
    add_parser = subparsers.add_parser("add", help="Add a new schedule")
    add_parser.add_argument("phrase", nargs="+", help="Natural-language schedule phrase")
    add_parser.set_defaults(func=cmd_add)

    # list
    list_parser = subparsers.add_parser("list", help="List all schedules")
    list_parser.set_defaults(func=cmd_list)

    # remove
    remove_parser = subparsers.add_parser("remove", help="Remove a schedule")
    remove_parser.add_argument("schedule_id", help="Schedule ID to remove")
    remove_parser.set_defaults(func=cmd_remove)

    # enable
    enable_parser = subparsers.add_parser("enable", help="Enable a schedule")
    enable_parser.add_argument("schedule_id", help="Schedule ID to enable")
    enable_parser.set_defaults(func=cmd_enable)

    # disable
    disable_parser = subparsers.add_parser("disable", help="Disable a schedule")
    disable_parser.add_argument("schedule_id", help="Schedule ID to disable")
    disable_parser.set_defaults(func=cmd_disable)

    # due
    due_parser = subparsers.add_parser("due", help="Show due schedules")
    due_parser.set_defaults(func=cmd_due)

    # phrases
    phrases_parser = subparsers.add_parser("phrases", help="Show supported phrases")
    phrases_parser.set_defaults(func=cmd_phrases)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
