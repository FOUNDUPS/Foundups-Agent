#!/usr/bin/env python3
"""
Refresh the OpenClaw grant watchlist against official-source URLs.

This is a lightweight change detector, not a full scraper. It records:
- HTTP status
- page title
- content hash
- last checked timestamp
- whether the page changed since the last refresh

Outputs:
- updates the watchlist JSON in place
- writes a status snapshot JSON for OpenClaw review
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
WATCHLIST_PATH = REPO_ROOT / "modules" / "communication" / "moltbot_bridge" / "workspace" / "reports" / "web3_grants_0102_watchlist.json"
STATUS_PATH = REPO_ROOT / "modules" / "communication" / "moltbot_bridge" / "workspace" / "reports" / "web3_grants_0102_watchlist_status.json"
USER_AGENT = "OpenClawGrantWatch/1.0 (+https://foundups.org)"


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def extract_title(html_text: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return title[:300] if title else None


def fetch_url(url: str, timeout: int = 20) -> Dict[str, Any]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            body = response.read()
        text = body.decode("utf-8", errors="replace")
        return {
            "url": url,
            "ok": True,
            "http_status": status,
            "title": extract_title(text),
            "content_hash": hashlib.sha256(body).hexdigest(),
            "error": None,
        }
    except HTTPError as exc:
        return {
            "url": url,
            "ok": False,
            "http_status": exc.code,
            "title": None,
            "content_hash": None,
            "error": f"HTTPError: {exc.code}",
        }
    except URLError as exc:
        return {
            "url": url,
            "ok": False,
            "http_status": None,
            "title": None,
            "content_hash": None,
            "error": f"URLError: {exc.reason}",
        }
    except Exception as exc:
        return {
            "url": url,
            "ok": False,
            "http_status": None,
            "title": None,
            "content_hash": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def refresh_item(item: Dict[str, Any]) -> Dict[str, Any]:
    previous_sources = item.get("last_sources") or []
    previous_hashes = {source.get("url"): source.get("content_hash") for source in previous_sources if isinstance(source, dict)}

    refreshed_sources: List[Dict[str, Any]] = []
    change_detected = False

    for url in item.get("official_urls", []):
        result = fetch_url(url)
        previous_hash = previous_hashes.get(url)
        current_hash = result.get("content_hash")
        if previous_hash and current_hash and previous_hash != current_hash:
            change_detected = True
        refreshed_sources.append(result)

    if not refreshed_sources:
        refresh_result = "no_urls"
    elif any(not source.get("ok") for source in refreshed_sources):
        refresh_result = "partial_error" if any(source.get("ok") for source in refreshed_sources) else "error"
    elif not previous_sources:
        refresh_result = "first_seen"
    elif change_detected:
        refresh_result = "changed"
    else:
        refresh_result = "unchanged"

    item["last_checked"] = utc_now_iso()
    item["last_refresh_result"] = refresh_result
    item["last_sources"] = refreshed_sources
    return item


def build_status_report(watchlist: Dict[str, Any]) -> Dict[str, Any]:
    items = watchlist.get("items", [])
    changed = [item["name"] for item in items if item.get("last_refresh_result") == "changed"]
    errored = [
        item["name"]
        for item in items
        if item.get("last_refresh_result") in {"error", "partial_error", "no_urls"}
    ]
    return {
        "generated_on": utc_now_iso(),
        "watch_count": len(items),
        "changed_count": len(changed),
        "error_count": len(errored),
        "changed_items": changed,
        "error_items": errored,
        "items": [
            {
                "name": item.get("name"),
                "ecosystem": item.get("ecosystem"),
                "last_checked": item.get("last_checked"),
                "last_refresh_result": item.get("last_refresh_result"),
                "sources": item.get("last_sources", []),
            }
            for item in items
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh the OpenClaw grant watchlist.")
    parser.add_argument("--watchlist", type=Path, default=WATCHLIST_PATH, help="Path to the watchlist JSON")
    parser.add_argument("--status-out", type=Path, default=STATUS_PATH, help="Path to write status snapshot JSON")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit on number of watchlist items to refresh")
    args = parser.parse_args()

    watchlist_path = args.watchlist
    if not watchlist_path.exists():
        print(f"[FAIL] Watchlist not found: {watchlist_path}")
        return 1

    watchlist = json.loads(watchlist_path.read_text(encoding="utf-8"))
    items = watchlist.get("items", [])
    if args.limit > 0:
        target_items = items[: args.limit]
    else:
        target_items = items

    for item in target_items:
        refresh_item(item)

    watchlist["last_full_refresh_attempt"] = utc_now_iso()
    watchlist_path.write_text(json.dumps(watchlist, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    status_report = build_status_report(watchlist)
    args.status_out.write_text(json.dumps(status_report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(f"[OK] Refreshed {len(target_items)} watchlist item(s)")
    print(f"[OK] Status written to {args.status_out}")
    print(f"[OK] Changed items: {status_report['changed_count']}")
    print(f"[OK] Error items: {status_report['error_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
