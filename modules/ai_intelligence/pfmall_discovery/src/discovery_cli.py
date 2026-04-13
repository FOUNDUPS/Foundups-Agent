#!/usr/bin/env python3
"""
YouTube Discovery CLI - Search YouTube and generate reviewable proposals.

Usage:
    python -m modules.ai_intelligence.pfmall_discovery.src.discovery_cli --query "FFCPLN music"
    python -m modules.ai_intelligence.pfmall_discovery.src.discovery_cli --query "Japan relocation" --type channel

WSP References:
- WSP 3: AI Intelligence domain
- WSP 97: Truthful discovery (no fake claims)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Setup logging before imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Project paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "audits" / "pfmall_youtube_ingest" / "youtube_discovery_proposals.json"


def get_youtube_service():
    """
    Get authenticated YouTube API service.

    Returns None if credentials are not available.
    """
    try:
        from modules.platform_integration.youtube_auth.src.youtube_auth import (
            get_authenticated_service,
        )
        return get_authenticated_service()
    except Exception as e:
        logger.warning(f"[DISCOVERY] YouTube auth unavailable: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Discovery - Search and generate reviewable proposals"
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Search query (e.g., 'FFCPLN music', 'Japan relocation')",
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["video", "channel"],
        default="video",
        help="Search type: video or channel (default: video)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=25,
        help="Maximum results to return (default: 25)",
    )
    parser.add_argument(
        "--include-channels",
        action="store_true",
        help="Also search for channels when type=video",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help=f"Output path for proposal JSON (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    output_path = Path(args.output) if args.output else DEFAULT_OUTPUT

    # Get YouTube service
    youtube = get_youtube_service()
    if not youtube:
        logger.error("[DISCOVERY] YouTube API unavailable")
        logger.error("[DISCOVERY] To enable: configure YOUTUBE_SCOPES and OAuth tokens in .env")
        logger.error("[DISCOVERY] Generating empty proposal artifact to show workflow")

        # Generate empty proposal for workflow demo
        from modules.ai_intelligence.pfmall_discovery.src.proposal_generator import (
            write_proposal_artifact,
            format_proposal_summary,
        )
        from modules.ai_intelligence.pfmall_discovery.src.foundup_matcher import (
            load_catalog_targets,
        )
        from datetime import datetime, timezone

        targets = load_catalog_targets()
        empty_report = {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "query": args.query,
            "search_type": args.type,
            "api_status": "BLOCKED - credentials unavailable",
            "summary": {
                "total_proposals": 0,
                "matched_to_foundup": 0,
                "unmatched": 0,
                "catalog_targets": len(targets),
            },
            "proposals": [],
        }
        write_proposal_artifact(empty_report, output_path)
        print(format_proposal_summary(empty_report))
        sys.exit(1)

    # Import after path setup
    from modules.ai_intelligence.pfmall_discovery.src.proposal_generator import (
        generate_discovery_proposals,
        write_proposal_artifact,
        format_proposal_summary,
    )

    logger.info(f"[DISCOVERY] Searching YouTube for: {args.query}")

    # Generate proposals
    report = generate_discovery_proposals(
        youtube_service=youtube,
        query=args.query,
        search_type=args.type,
        max_results=args.max_results,
        include_channels=args.include_channels,
    )

    # Write artifact
    write_proposal_artifact(report, output_path)

    # Print summary (handle Windows console encoding)
    try:
        print(format_proposal_summary(report))
    except UnicodeEncodeError:
        summary = format_proposal_summary(report)
        print(summary.encode("ascii", errors="replace").decode("ascii"))

    logger.info(f"[DISCOVERY] Proposal artifact written to: {output_path}")
    logger.info("[DISCOVERY] Review proposals, then use channel-pull for matched items.")


if __name__ == "__main__":
    main()
