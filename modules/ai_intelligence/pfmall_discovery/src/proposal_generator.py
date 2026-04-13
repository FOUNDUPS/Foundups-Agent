"""
Proposal Generator - Generate reviewable discovery proposal artifacts.

Combines YouTube search with FoundUp matching to produce proposals
for human review. Does NOT mutate the catalog.

WSP References:
- WSP 3: AI Intelligence domain
- WSP 97: Truthful proposals (no auto-apply)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.ai_intelligence.pfmall_discovery.src.youtube_discovery import (
    DiscoveryProposal,
    search_youtube,
    search_by_topic,
)
from modules.ai_intelligence.pfmall_discovery.src.foundup_matcher import (
    load_catalog_targets,
    match_proposals,
)

logger = logging.getLogger(__name__)

# Default output path
DEFAULT_PROPOSAL_PATH = Path("docs/audits/pfmall_youtube_ingest/youtube_discovery_proposals.json")


def generate_discovery_proposals(
    youtube_service,
    query: str,
    search_type: str = "video",
    max_results: int = 25,
    include_channels: bool = False,
) -> Dict[str, Any]:
    """
    Generate discovery proposals for a query.

    Args:
        youtube_service: Authenticated YouTube service
        query: Search query
        search_type: "video" or "channel" (default "video")
        max_results: Max results to return
        include_channels: Also search for channels (when search_type="video")

    Returns:
        Proposal report dict
    """
    proposals: List[DiscoveryProposal] = []

    # Search YouTube
    if search_type == "video":
        proposals = search_by_topic(
            youtube_service,
            query,
            include_videos=True,
            include_channels=include_channels,
            max_results=max_results,
        )
    else:
        proposals = search_youtube(youtube_service, query, max_results, search_type)

    # Match to existing FoundUps
    targets = load_catalog_targets()
    matched_proposals = match_proposals(proposals, targets)

    # Build report
    matched_count = sum(1 for p in matched_proposals if p.matched_foundup_id)
    unmatched_count = len(matched_proposals) - matched_count

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "query": query,
        "search_type": search_type,
        "summary": {
            "total_proposals": len(matched_proposals),
            "matched_to_foundup": matched_count,
            "unmatched": unmatched_count,
            "catalog_targets": len(targets),
        },
        "proposals": [p.to_dict() for p in matched_proposals],
    }

    return report


def write_proposal_artifact(
    report: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> Path:
    """
    Write proposal artifact to JSON file.

    Args:
        report: Proposal report dict
        output_path: Output path (default: docs/audits/pfmall_youtube_ingest/)

    Returns:
        Path written to
    """
    path = output_path or DEFAULT_PROPOSAL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"[DISCOVERY] Wrote proposal artifact to {path}")
    return path


def format_proposal_summary(report: Dict[str, Any]) -> str:
    """
    Format proposal report for terminal display.

    Args:
        report: Proposal report dict

    Returns:
        Formatted string
    """
    lines = [
        "=" * 60,
        "YOUTUBE DISCOVERY PROPOSAL REPORT",
        f"Generated: {report.get('generated_at', 'unknown')}",
        f"Query: {report.get('query', 'unknown')}",
        "=" * 60,
        "",
        f"Total proposals: {report['summary']['total_proposals']}",
        f"Matched to FoundUp: {report['summary']['matched_to_foundup']}",
        f"Unmatched: {report['summary']['unmatched']}",
        f"Catalog targets: {report['summary']['catalog_targets']}",
        "",
    ]

    # Show matched proposals first
    matched = [p for p in report.get("proposals", []) if p.get("matched_foundup_id")]
    if matched:
        lines.append("--- MATCHED PROPOSALS ---")
        for p in matched[:5]:
            lines.append(f"  [{p['candidate_type']}] {p['title'][:50]}...")
            lines.append(f"    -> {p['matched_foundup_id']} ({p['match_reason']}, conf={p['confidence']:.2f})")
        if len(matched) > 5:
            lines.append(f"  ... and {len(matched) - 5} more matched")
        lines.append("")

    # Show unmatched proposals
    unmatched = [p for p in report.get("proposals", []) if not p.get("matched_foundup_id")]
    if unmatched:
        lines.append("--- UNMATCHED PROPOSALS ---")
        for p in unmatched[:5]:
            lines.append(f"  [{p['candidate_type']}] {p['title'][:50]}...")
            lines.append(f"    channel: {p.get('channel_title', 'unknown')}")
        if len(unmatched) > 5:
            lines.append(f"  ... and {len(unmatched) - 5} more unmatched")
        lines.append("")

    lines.append("=" * 60)
    lines.append("Review status: All proposals marked as 'proposed'")
    lines.append("Next step: Human review before any catalog apply")
    lines.append("=" * 60)

    return "\n".join(lines)
