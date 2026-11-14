#!/usr/bin/env python3
"""
reschedule_apply - module entrypoint for agent/DAE invocation.

This is the surface the --agent-command path spawns:
    youtube action reschedule_apply
        -> python -m ...skillz.reschedule_apply.run_skill --json

DEFAULT = DRY-RUN. It NEVER mutates a schedule unless env YT_RESCHEDULE_APPLY=="1"
AND a live DOM driver is connected. Via this subprocess surface there is no live
browser supplied, so it is dry-run by construction here; 012 wires a live driver
through the daemon path and flips YT_RESCHEDULE_APPLY to enable real apply. 012
only observes the emitted breadcrumb / outcomes and the JSON printed here.
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

from modules.platform_integration.youtube_shorts_scheduler.skillz.reschedule_apply.executor import (
    run_skill,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "reschedule_apply SKILLz - flag-gated apply of the reschedule plan. "
            "DEFAULT DRY-RUN: logs would-apply moves, zero mutation. Real apply "
            "only when YT_RESCHEDULE_APPLY=1 and a live driver is connected."
        )
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

    # No live DOM driver is supplied through the subprocess surface -> dry-run by
    # construction (apply_moves never touches a browser without a driver).
    result = run_skill(emit_signals=not args.no_signals)

    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
