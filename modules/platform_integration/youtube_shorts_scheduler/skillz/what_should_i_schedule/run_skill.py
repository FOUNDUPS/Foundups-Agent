#!/usr/bin/env python3
"""
what_should_i_schedule - module entrypoint for agent/DAE invocation.

This is the surface the --agent-command path spawns (read-only, agent-invoked):
    youtube action schedule_priority upcoming_days=7
        -> python -m ...skillz.what_should_i_schedule.run_skill --upcoming-days 7 --json

It is NOT a manual-012 menu. 012 only observes the emitted breadcrumb / outcome and
the JSON tail printed here. The daemon/Qwen consumes the JSON ranking to decide which
channel to schedule next.
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

from modules.platform_integration.youtube_shorts_scheduler.skillz.what_should_i_schedule.executor import (
    DEFAULT_UPCOMING_DAYS,
    run_skill,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "what_should_i_schedule SKILLz - rank channels by scheduling need "
            "(read-only, agent-invoked)."
        )
    )
    parser.add_argument(
        "--upcoming-days",
        type=int,
        default=DEFAULT_UPCOMING_DAYS,
        help=f"Upcoming days to inspect per channel (default {DEFAULT_UPCOMING_DAYS}).",
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
        upcoming_days=args.upcoming_days,
        emit_signals=not args.no_signals,
    )

    # Always print a single JSON line last so the adapter's _extract_json_tail can
    # parse it deterministically.
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
