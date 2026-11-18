#!/usr/bin/env python3
"""
reschedule_plan - module entrypoint for agent/DAE invocation.

This is the surface the --agent-command path spawns (DRY-RUN, read-only,
agent-invoked):
    youtube action reschedule_plan
        -> python -m ...skillz.reschedule_plan.run_skill --json

It is NOT a manual-012 menu and it NEVER mutates a schedule (no browser, no live
model). 012 only observes the emitted breadcrumb / outcome and the JSON plan
printed here. The daemon/Qwen consumes the JSON plan; the mutating apply is a
separate Phase-2 slice.
"""

from __future__ import annotations

import argparse
import json
import sys

# UTF-8 enforcement (WSP 90) - entry point only
if sys.platform.startswith("win"):  # pragma: no cover - platform guard
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)

from modules.platform_integration.youtube_shorts_scheduler.skillz.reschedule_plan.executor import (
    run_skill,
)
from modules.platform_integration.youtube_shorts_scheduler.src.reschedule_planner import (
    DEFAULT_HORIZON_DAYS,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "reschedule_plan SKILLz - dry-run rebalance PLAN for over-crowded "
            "schedule days (read-only, agent-invoked; apply is Phase 2)."
        )
    )
    parser.add_argument(
        "--horizon-days",
        type=int,
        default=DEFAULT_HORIZON_DAYS,
        help=f"How far ahead to search for under-target days (default {DEFAULT_HORIZON_DAYS}).",
    )
    parser.add_argument(
        "--no-signals",
        action="store_true",
        help="Skip breadcrumb + PatternMemory emission (diagnostic only).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON (agent consumption).",
    )
    args = parser.parse_args(argv)

    result = run_skill(
        horizon_days=args.horizon_days,
        emit_signals=not args.no_signals,
    )

    # Always print a single JSON line last so the adapter's _extract_json_tail can
    # parse it deterministically.
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
