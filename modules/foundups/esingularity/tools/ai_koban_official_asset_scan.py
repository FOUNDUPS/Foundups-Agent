#!/usr/bin/env python3
"""Bounded, read-only official-source pulse for AI Koban public-facility leads.

No automatic email, scraping expansion, CRM mutation or site-status promotion.
Run offline by default. Network calls require --fetch, and obey robots.txt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

SOURCE = Path(__file__).resolve().parents[1] / "docs" / "AI_KOBAN_REGIONAL_PUBLIC_ASSET_LEADS.json"
USER_AGENT = "AIKobanOfficialAssetResearch/0.1 (manual, policy-bound)"
APPROVED_HOSTS = {"www.city.fukui.lg.jp", "www.city.ono.fukui.jp", "www.city.nanao.lg.jp"}
MAX_BYTES = 1000000


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.fragments: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data: str) -> None:
        if not self.hidden and data.strip():
            self.fragments.append(data.strip())


def fetch_text(url: str, robots: dict[str, RobotFileParser]) -> str:
    parts = urlparse(url)
    if parts.scheme != "https" or parts.hostname not in APPROVED_HOSTS:
        raise ValueError("source host outside explicit official allowlist")
    host = parts.hostname
    if host not in robots:
        parser = RobotFileParser()
        parser.set_url("https://" + host + "/robots.txt")
        try:
            with urlopen(Request(parser.url, headers={"User-Agent": USER_AGENT}), timeout=12) as response:
                body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("oversized robots.txt")
            parser.parse(body.decode("utf-8", "replace").splitlines())
        except Exception as exc:
            raise RuntimeError(f"robots policy unavailable for {host}: {exc}") from exc
        robots[host] = parser
    if not robots[host].can_fetch(USER_AGENT, url):
        raise PermissionError("robots.txt disallows this source")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with urlopen(request, timeout=15) as response:
        ct = response.headers.get("Content-Type", "")
        if "text/html" not in ct:
            raise ValueError(f"non-HTML source: {ct}")
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("page too large")
        markup = raw.decode("utf-8", "replace")
    parser = VisibleText()
    parser.feed(markup)
    return re.sub(r"\\s+", " ", unescape(" ".join(parser.fragments))).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch", action="store_true", help="allow bounded live official-page checks; never modifies CRM")
    ap.add_argument("--output", type=Path, help="local JSON result path, never auto-sync to canonical register")
    args = ap.parse_args()
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = data["leads"]
    ids = [x["id"] for x in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate stable facility identifier")
    for row in rows:
        parts = urlparse(row["source_url"])
        if parts.scheme != "https" or parts.hostname not in APPROVED_HOSTS:
            raise ValueError(f"invalid official source for {row['id']}")
        if row.get("power_capacity_verified") or row.get("site_rights_verified"):
            raise ValueError("source discovery cannot certify site/power rights")
    result: dict = {
        "scan_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "MANUAL_NETWORK" if args.fetch else "OFFLINE_VALIDATE",
        "lead_count": len(rows),
        "sources": [],
        "interpretation": "Source changed/unchanged is not facility availability, site permission, power or award.",
    }
    if args.fetch:
        robots: dict[str, RobotFileParser] = {}
        urls = sorted({x["source_url"] for x in rows})
        if len(urls) > 10:
            raise ValueError("max 10 exact official sources per run")
        for i, url in enumerate(urls):
            if i:
                time.sleep(2.0)
            record = {"source_url": url, "linked_leads": [x["id"] for x in rows if x["source_url"] == url]}
            try:
                visible = fetch_text(url, robots)
                record.update(text_sha256=hashlib.sha256(visible.encode("utf-8")).hexdigest(),
                              visible_excerpt=visible[:280],
                              outcome="REVIEW_SOURCE_TEXT_NO_AUTO_STATUS")
            except Exception as exc:
                record.update(outcome="FETCH_BLOCKED_OR_FAILED", reason=str(exc)[:320])
            result["sources"].append(record)
    else:
        result["sources"] = [{"source_url": u, "outcome": "NOT_FETCHED_OFFLINE"}
                             for u in sorted({x["source_url"] for x in rows})]
    out = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(out + "\n", encoding="utf-8")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
