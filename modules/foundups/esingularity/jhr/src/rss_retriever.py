"""Bounded RSS discovery adapter for Japan Hyperscaler Report.

Discovery is candidate generation only. Google News RSS entries are never
promoted to OFFICIAL evidence by this adapter. WSP_97 verification remains in
jhr_agent.py.
"""

from __future__ import annotations

from email.utils import parsedate_to_datetime
from urllib.parse import quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from modules.foundups.esingularity.jhr.src.jhr_agent import EvidenceRecord

SEARCH_QUERIES = (
    "日本 データセンター ハイパースケール GX 戦略地域",
    "印西 データセンター 住民 騒音 景観 農地",
    "千葉 データセンター 開発 住民 説明会",
    "福井 データセンター GX ワット ビット",
    "Japan hyperscale data center Inzai community grid",
)


def _rss_url(query: str) -> str:
    return "https://news.google.com/rss/search?q=" + quote(query) + "&hl=ja&gl=JP&ceid=JP:ja"


def _fetch(url: str, timeout: int = 12) -> bytes:
    request = Request(url, headers={"User-Agent": "eSingularity-JHR/1.0 (+https://esingularity.ai/)"})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS endpoint
        return response.read(2_000_000)


def _published(raw: str) -> str:
    try:
        return parsedate_to_datetime(raw).isoformat()
    except (TypeError, ValueError):
        return ""


def _event_kind(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in ("地区計画", "条例", "zoning")):
        return "zoning"
    if any(term in lowered for term in ("住民", "農家", "騒音", "景観", "community")):
        return "community_response"
    if any(term in lowered for term in ("送電", "変電所", "grid", "電力")):
        return "grid_capacity"
    if any(term in lowered for term in ("gx戦略地域", "ワット・ビット", "ワットビット")):
        return "national_policy"
    if any(term in lowered for term in ("hyperscale", "ハイパースケール", "データセンター")):
        return "hyperscale_campus"
    return "reported_signal"


def discover_candidates() -> list[EvidenceRecord]:
    """Return bounded reported candidates for downstream verification."""
    records: list[EvidenceRecord] = []
    seen: set[tuple[str, str]] = set()
    for query in SEARCH_QUERIES:
        try:
            root = ET.fromstring(_fetch(_rss_url(query)))
        except Exception:
            continue
        for node in root.findall("./channel/item")[:20]:
            title = (node.findtext("title") or "").strip()
            url = (node.findtext("link") or "").strip()
            if not title or not url:
                continue
            key = (title.lower(), url.lower())
            if key in seen:
                continue
            seen.add(key)
            records.append(
                EvidenceRecord(
                    title=title,
                    url=url,
                    source_class="REPORTED",
                    event_kind=_event_kind(title + " " + query),
                    published_at=_published((node.findtext("pubDate") or "").strip()),
                    jurisdiction="Japan",
                    summary="RSS discovery candidate; primary-source verification required.",
                    materiality=2,
                    corroborated=False,
                )
            )
            if len(records) >= 40:
                return records
    return records
