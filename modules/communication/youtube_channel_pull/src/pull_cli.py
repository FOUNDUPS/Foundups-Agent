#!/usr/bin/env python3
"""
YouTube Channel Pull CLI - Fetch latest videos and generate reviewable delta.

Usage:
    python -m modules.communication.youtube_channel_pull.src.pull_cli [--dry-run] [--foundup FOUNDUP_ID]

Options:
    --dry-run       Default mode. Generate delta without catalog mutation.
    --foundup ID    Pull only specified FoundUp (by foundup_id)
    --max-results N Max videos per channel (default: 50)
    --output PATH   Output path for delta JSON

WSP References:
- WSP 3: Communication domain
- WSP 97: Truthful verification
"""

from __future__ import annotations

import argparse
import json
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
CATALOG_PATH = REPO_ROOT / "public" / "member" / "mall-video-catalog.json"
DEFAULT_DELTA_PATH = REPO_ROOT / "docs" / "audits" / "pfmall_youtube_ingest" / "youtube_channel_pull_delta.json"


def load_catalog() -> list:
    """Load mall-video-catalog.json."""
    if not CATALOG_PATH.exists():
        logger.error(f"[PULL] Catalog not found: {CATALOG_PATH}")
        return []
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


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
        logger.warning(f"[PULL] YouTube auth unavailable: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Channel Pull - Fetch latest videos, generate reviewable delta"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Generate delta without catalog mutation (default: True)",
    )
    parser.add_argument(
        "--foundup",
        type=str,
        default=None,
        help="Pull only specified FoundUp by foundup_id",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=50,
        help="Max videos per channel (default: 50)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help=f"Output path for delta JSON (default: {DEFAULT_DELTA_PATH})",
    )
    args = parser.parse_args()

    output_path = Path(args.output) if args.output else DEFAULT_DELTA_PATH

    # Load catalog
    logger.info(f"[PULL] Loading catalog from {CATALOG_PATH}")
    catalog = load_catalog()
    if not catalog:
        logger.error("[PULL] Empty or missing catalog. Exiting.")
        sys.exit(1)

    # Import after path setup
    from modules.communication.youtube_channel_pull.src.channel_puller import (
        fetch_channel_videos,
        get_channel_ids_from_catalog,
    )
    from modules.communication.youtube_channel_pull.src.catalog_delta import (
        generate_full_delta,
        write_delta_artifact,
        format_delta_summary,
    )

    # Get channel mappings from catalog
    channel_map = get_channel_ids_from_catalog(catalog)
    logger.info(f"[PULL] Found {len(channel_map)} YouTube-backed FoundUps in catalog")

    # Filter to specific FoundUp if requested
    if args.foundup:
        if args.foundup not in channel_map:
            logger.error(f"[PULL] FoundUp '{args.foundup}' not found or not YouTube-backed")
            sys.exit(1)
        channel_map = {args.foundup: channel_map[args.foundup]}
        logger.info(f"[PULL] Filtering to single FoundUp: {args.foundup}")

    # Get YouTube service
    youtube = get_youtube_service()
    if not youtube:
        logger.warning("[PULL] YouTube API unavailable - generating fixture-based delta")
        logger.warning("[PULL] To enable live API: configure YOUTUBE_SCOPES and OAuth tokens in .env")
        # Generate empty delta to show the workflow works
        pulled_by_foundup = {fid: [] for fid in channel_map.keys()}
    else:
        # Fetch videos from each channel
        pulled_by_foundup = {}
        for foundup_id, channel_id in channel_map.items():
            logger.info(f"[PULL] Fetching videos for {foundup_id} (channel: {channel_id})")
            videos = fetch_channel_videos(youtube, channel_id, max_results=args.max_results)
            pulled_by_foundup[foundup_id] = videos

    # Generate delta
    delta = generate_full_delta(catalog, pulled_by_foundup)

    # Write artifact
    write_delta_artifact(delta, output_path)

    # Print summary (handle Windows console encoding)
    try:
        print(format_delta_summary(delta))
    except UnicodeEncodeError:
        # Fallback for Windows consoles that can't handle emojis
        summary = format_delta_summary(delta)
        print(summary.encode("ascii", errors="replace").decode("ascii"))

    logger.info(f"[PULL] Delta artifact written to: {output_path}")
    logger.info("[PULL] Review the delta, then manually merge approved videos into catalog.")


if __name__ == "__main__":
    main()
