"""Japan Hyperscaler Report (JHR) bounded research assessor.

WSP 97 boundary: discovery is not publication. This module records evidence,
scores significance, and creates a research packet. It never edits the public
site or claims a report was published.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
from pathlib import Path
import re
import threading
from typing import Iterable
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

JHR_SCHEMA = "jhr_assessment.v1"
DEFAULT_INTERVAL_HOURS = 24
DEFAULT_THRESHOLD = 8
DEFAULT_MAX_ITEMS = 40

SEARCH_QUERIES = (
    "日本 データセンター ハイパースケール GX 戦略地域",
    "印西 データセンター 住民 騒音 景観 農地",
    "千葉 データセンター 開発 住民 説明会",
    "福井 データセンター GX ワット ビット",
    "Japan hyperscale data center Inzai community grid",
)

HIGH_SIGNAL_TERMS = {
    "gx戦略地域": 4,
    "データセンター集積": 4,
    "ワット・ビット": 4,
    "ワットビット": 4,
    "gigawatt": 4,
    "gw": 3,
    "変電所": 3,
    "送電": 3,
    "条例": 3,
    "地区計画": 3,
    "景観": 2,
    "騒音": 2,
    "住民": 2,
    "農地": 2,
    "農家": 2,
    "寺": 2,
    "寺院": 2,
    "印西": 2,
    "福井": 2,
    "小浜": 2,
    "data center": 2,
    "hyperscale": 3,
}

PRIMARY_SUFFIXES = (".go.jp", ".lg.jp")


@dataclass(frozen=True)
class EvidenceItem:
    title: str
    url: str
    published_at: str
    source_host: str
    query: str
    primary_source: bool
    signal_score: int
    fingerprint: str


@dataclass(frozen=True)
class Assessment:
    schema: str
    assessed_at: str
    status: str
    significance_score: int
    evidence_count: int
    primary_source_count: int
    publish_candidate: bool
    reasons: tuple[str, ...]
    evidence: tuple[EvidenceItem, ...]


def _runtime_root(repo_root: Path) -> Path:
    configured = os.getenv("JHR_RUNTIME_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return repo_root / ".runtime" / "esingularity" / "jhr"


def _state_path(repo_root: Path) -> Path:
    return _runtime_root(repo_root) / "state.json"


def _read_state(repo_root: Path) -> dict:
    try:
        return json.loads(_state_path(repo_root).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def assessment_due(repo_root: Path, *, now: datetime | None = None) -> bool:
    if os.getenv("JHR_ENABLED", "1") == "0":
        return False
    now = now or datetime.now(timezone.utc)
    try:
        hours = max(1, int(os.getenv("JHR_ASSESS_INTERVAL_HOURS", str(DEFAULT_INTERVAL_HOURS))))
    except ValueError:
        hours = DEFAULT_INTERVAL_HOURS
    raw = _read_state(repo_root).get("last_assessed_at")
    if not raw:
        return True
    try:
        previous = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return True
    return now - previous >= timedelta(hours=hours)


def _news_rss_url(query: str) -> str:
    return (
        "https://news.google.com/rss/search?q="
        + quote(query)
        + "&hl=ja&gl=JP&ceid=JP:ja"
    )


def _fetch(url: str, timeout: int = 12) -> bytes:
    request = Request(url, headers={"User-Agent": "eSingularity-JHR/1.0 (+https://esingularity.ai/)"})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS discovery endpoint
        return response.read(2_000_000)


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().rstrip(".")


def _is_primary(host: str) -> bool:
    return any(host.endswith(suffix) for suffix in PRIMARY_SUFFIXES)


def _score_text(text: str) -> int:
    lowered = text.lower()
    return sum(weight for term, weight in HIGH_SIGNAL_TERMS.items() if term in lowered)


def _fingerprint(title: str, url: str) -> str:
    return hashlib.sha256(f"{title.strip()}\n{url.strip()}".encode("utf-8")).hexdigest()[:20]


def _parse_date(raw: str) -> str:
    try:
        return parsedate_to_datetime(raw).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return ""


def discover(query: str) -> list[EvidenceItem]:
    root = ET.fromstring(_fetch(_news_rss_url(query)))
    items: list[EvidenceItem] = []
    for node in root.findall("./channel/item"):
        title = (node.findtext("title") or "").strip()
        url = (node.findtext("link") or "").strip()
        published = _parse_date((node.findtext("pubDate") or "").strip())
        if not title or not url:
            continue
        host = _host(url)
        score = _score_text(title + " " + query)
        items.append(
            EvidenceItem(
                title=title,
                url=url,
                published_at=published,
                source_host=host,
                query=query,
                primary_source=_is_primary(host),
                signal_score=score,
                fingerprint=_fingerprint(title, url),
            )
        )
    return items


def _dedupe(items: Iterable[EvidenceItem]) -> list[EvidenceItem]:
    seen: set[str] = set()
    result: list[EvidenceItem] = []
    for item in items:
        if item.fingerprint in seen:
            continue
        seen.add(item.fingerprint)
        result.append(item)
    return result


def assess(repo_root: Path, *, now: datetime | None = None) -> Assessment:
    now = now or datetime.now(timezone.utc)
    discovered: list[EvidenceItem] = []
    failures: list[str] = []
    for query in SEARCH_QUERIES:
        try:
            discovered.extend(discover(query))
        except Exception as exc:  # fail-open research lane; receipt records degraded discovery
            failures.append(f"discovery_failed:{query}:{type(exc).__name__}")

    items = sorted(
        _dedupe(discovered),
        key=lambda item: (item.signal_score, item.published_at),
        reverse=True,
    )[:DEFAULT_MAX_ITEMS]
    primary_count = sum(1 for item in items if item.primary_source)
    top_scores = sorted((item.signal_score for item in items), reverse=True)[:5]
    score = sum(top_scores)
    try:
        threshold = max(1, int(os.getenv("JHR_SIGNIFICANCE_THRESHOLD", str(DEFAULT_THRESHOLD))))
    except ValueError:
        threshold = DEFAULT_THRESHOLD

    reasons: list[str] = list(failures)
    if not items:
        status = "NO_EVIDENCE"
        reasons.append("no_discovery_evidence")
    elif score < threshold:
        status = "NO_REPORT"
        reasons.append(f"significance_below_threshold:{score}<{threshold}")
    else:
        status = "RESEARCH_CANDIDATE"
        reasons.append(f"significance_threshold_met:{score}>={threshold}")

    # WSP 97: discovery feeds a research candidate only. Public promotion still
    # requires claim-level verification; no RSS result can satisfy that alone.
    publish_candidate = status == "RESEARCH_CANDIDATE"
    if publish_candidate and primary_count == 0:
        reasons.append("primary_source_verification_required")

    return Assessment(
        schema=JHR_SCHEMA,
        assessed_at=now.isoformat(),
        status=status,
        significance_score=score,
        evidence_count=len(items),
        primary_source_count=primary_count,
        publish_candidate=publish_candidate,
        reasons=tuple(reasons),
        evidence=tuple(items),
    )


def _persist(repo_root: Path, assessment: Assessment) -> Path:
    root = _runtime_root(repo_root)
    root.mkdir(parents=True, exist_ok=True)
    receipt_id = hashlib.sha256(
        f"{assessment.assessed_at}|{assessment.significance_score}|{assessment.evidence_count}".encode("utf-8")
    ).hexdigest()[:16]
    receipt_path = root / f"assessment-{receipt_id}.json"
    payload = asdict(assessment)
    payload["receipt_id"] = receipt_id
    receipt_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _state_path(repo_root).write_text(
        json.dumps(
            {
                "schema": JHR_SCHEMA,
                "last_assessed_at": assessment.assessed_at,
                "last_status": assessment.status,
                "last_receipt": str(receipt_path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return receipt_path


def run_once(repo_root: Path) -> Assessment:
    result = assess(repo_root)
    _persist(repo_root, result)
    return result


def maybe_start_background(repo_root: Path) -> bool:
    """Start one bounded assessment when due; never block main.py startup."""
    if not assessment_due(repo_root):
        return False

    def _worker() -> None:
        try:
            result = run_once(repo_root)
            print(
                "[JHR] assessment="
                f"{result.status} score={result.significance_score} "
                f"evidence={result.evidence_count} public_published=False"
            )
        except Exception as exc:
            print(f"[JHR] assessment=WARN error={type(exc).__name__} public_published=False")

    threading.Thread(target=_worker, daemon=True, name="jhr-assessment").start()
    return True
