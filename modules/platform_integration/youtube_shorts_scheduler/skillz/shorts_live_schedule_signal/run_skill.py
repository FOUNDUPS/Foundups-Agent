#!/usr/bin/env python3
"""
shorts_live_schedule_signal - module entrypoint for agent/DAE invocation.

This is the surface the --agent-command path spawns (read-only, agent-invoked):
    youtube action live_schedule_signal channel=foundups
        -> python -m ...skillz.shorts_live_schedule_signal.run_skill --channel foundups --json

It is NOT a manual-012 menu. 012 only observes the emitted breadcrumb / outcome and
the JSON tail printed here. The daemon/Qwen consumes the JSON signal:
  - an ACCURATE scheduled_count (or null=UNKNOWN, never a false 0), and
  - the low-viewed shorts list (012: "re-schedule low viewed shorts").

A live browser is required for the real signal; without one (no --connect or no
debug session) the skill returns scheduled_count=null (UNKNOWN), never 0.
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

from modules.platform_integration.youtube_shorts_scheduler.skillz.shorts_live_schedule_signal.executor import (
    DEFAULT_LOW_VIEW_THRESHOLD,
    run_skill,
)


def _connect_driver(browser: str):
    """Connect to an existing logged-in debug browser session (read-only).

    Returns a Selenium WebDriver attached to the running Chrome/Edge debug
    session, or None if connection fails (skill then degrades to UNKNOWN).
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from selenium.webdriver.edge.options import Options as EdgeOptions

        ports = {"chrome": 9222, "edge": 9223}
        port = ports.get(browser.lower(), 9222)
        if browser.lower() == "edge":
            options = EdgeOptions()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            return webdriver.Edge(options=options)
        options = ChromeOptions()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
        return webdriver.Chrome(options=options)
    except Exception:
        return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "shorts_live_schedule_signal SKILLz - read-only live 'Has schedule' "
            "count + per-video view (low-viewed) signal from the Studio shorts list."
        )
    )
    parser.add_argument(
        "--channel",
        required=True,
        help="Channel key (e.g. foundups, antifafm) or a UC... channel ID.",
    )
    parser.add_argument(
        "--low-view-threshold",
        type=int,
        default=DEFAULT_LOW_VIEW_THRESHOLD,
        help=f"Views strictly below this are 'low viewed' (default {DEFAULT_LOW_VIEW_THRESHOLD}).",
    )
    parser.add_argument(
        "--connect",
        choices=["chrome", "edge"],
        default=None,
        help="Connect to an existing debug browser session for a LIVE read.",
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

    driver = _connect_driver(args.connect) if args.connect else None

    result = run_skill(
        channel=args.channel,
        low_view_threshold=args.low_view_threshold,
        driver=driver,
        emit_signals=not args.no_signals,
    )

    # Always print a single JSON line last so the adapter's _extract_json_tail can
    # parse it deterministically.
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
