#!/usr/bin/env python3
"""
Refresh the OpenClaw external ecosystem watchlist against official-source URLs.

This tracks external agent-infrastructure systems that may influence OpenClaw
architecture decisions without becoming default runtime dependencies.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from refresh_grant_watchlist import (
    REPO_ROOT,
    build_status_report,
    refresh_item,
    utc_now_iso,
)


WATCHLIST_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "workspace"
    / "reports"
    / "openclaw_external_ecosystem_watchlist.json"
)
STATUS_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "workspace"
    / "reports"
    / "openclaw_external_ecosystem_watchlist_status.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh the OpenClaw external ecosystem watchlist."
    )
    parser.add_argument(
        "--watchlist",
        type=Path,
        default=WATCHLIST_PATH,
        help="Path to the watchlist JSON",
    )
    parser.add_argument(
        "--status-out",
        type=Path,
        default=STATUS_PATH,
        help="Path to write status snapshot JSON",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit on number of watchlist items to refresh",
    )
    args = parser.parse_args()

    watchlist_path = args.watchlist
    if not watchlist_path.exists():
        print(f"[FAIL] Watchlist not found: {watchlist_path}")
        return 1

    watchlist = json.loads(watchlist_path.read_text(encoding="utf-8"))
    items = watchlist.get("items", [])
    target_items = items[: args.limit] if args.limit > 0 else items

    for item in target_items:
        refresh_item(item)

    watchlist["last_full_refresh_attempt"] = utc_now_iso()
    watchlist_path.write_text(
        json.dumps(watchlist, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    status_report = build_status_report(watchlist)
    status_report["watch_type"] = "openclaw_external_ecosystem"
    args.status_out.write_text(
        json.dumps(status_report, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    print(f"[OK] Refreshed {len(target_items)} watchlist item(s)")
    print(f"[OK] Status written to {args.status_out}")
    print(f"[OK] Changed items: {status_report['changed_count']}")
    print(f"[OK] Error items: {status_report['error_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
