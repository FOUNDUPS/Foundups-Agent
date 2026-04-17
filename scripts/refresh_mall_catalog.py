#!/usr/bin/env python3
"""
Refresh Mall Video Catalog - Update channel avatars and video counts.

Usage:
    python scripts/refresh_mall_catalog.py --info-only  # Avatars + counts (13 units) - RUN ONCE
    python scripts/refresh_mall_catalog.py --delta      # Only NEW videos since last fetch (~100 units)
    python scripts/refresh_mall_catalog.py              # 50 latest videos per channel (1300 units)
    python scripts/refresh_mall_catalog.py --full       # ALL videos (quota heavy!) - RARELY NEEDED

Recommended workflow:
    1. Run --info-only ONCE to get avatars (they don't change)
    2. Run --delta periodically to get new videos only
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from modules.platform_integration.youtube_auth.src.youtube_auth import get_authenticated_service
from modules.communication.youtube_channel_pull.src.channel_puller import (
    fetch_channel_info,
    fetch_channel_videos,
)

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

CATALOG_PATH = REPO_ROOT / "public" / "member" / "mall-video-catalog.json"


def load_catalog() -> list:
    """Load existing catalog."""
    if not CATALOG_PATH.exists():
        logger.error(f"Catalog not found: {CATALOG_PATH}")
        return []
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_catalog(catalog: list) -> None:
    """Save catalog back to JSON."""
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved catalog to {CATALOG_PATH}")


def refresh_catalog(fetch_videos: bool = True, fetch_all: bool = False, delta_only: bool = False) -> None:
    """
    Refresh catalog with channel info and optionally videos.

    Args:
        fetch_videos: If True, fetch latest videos for each channel
        fetch_all: If True and fetch_videos, fetch ALL videos (quota heavy)
        delta_only: If True, only fetch videos newer than most recent in catalog
    """
    catalog = load_catalog()
    if not catalog:
        return

    logger.info(f"Loaded {len(catalog)} entries from catalog")

    # Get YouTube service
    try:
        youtube = get_authenticated_service()
        if not youtube:
            logger.error("Failed to get YouTube service")
            return
    except Exception as e:
        logger.error(f"YouTube auth error: {e}")
        return

    updated = 0
    for entry in catalog:
        source_type = entry.get("source_type", "")
        if source_type != "youtube_channel":
            logger.info(f"  Skipping {entry.get('foundup_id')} (not a YouTube channel)")
            continue

        channel_id = entry.get("source_id", "")
        if not channel_id or not channel_id.startswith("UC"):
            logger.warning(f"  Invalid channel_id for {entry.get('foundup_id')}")
            continue

        foundup_id = entry.get("foundup_id", "unknown")
        logger.info(f"\n[{foundup_id}] Fetching channel info...")

        # Fetch channel info (avatar, true video count)
        info = fetch_channel_info(youtube, channel_id)
        if info:
            entry["channel_avatar_url"] = info.get("avatar_url", "")
            entry["true_video_count"] = info.get("video_count", 0)
            entry["subscriber_count"] = info.get("subscriber_count", 0)
            logger.info(f"  Avatar: {info.get('avatar_url', 'N/A')[:50]}...")
            logger.info(f"  True video count: {info.get('video_count', 0)}")
            logger.info(f"  Subscribers: {info.get('subscriber_count', 0)}")

        # Fetch videos
        if fetch_videos:
            existing_videos = entry.get("videos", [])

            if delta_only and existing_videos:
                # Delta mode: only fetch 50 latest, filter to new ones
                logger.info(f"  Delta mode: checking for new videos...")
                latest_ids = {v.get("video_id") for v in existing_videos[:100]}

                new_videos = fetch_channel_videos(youtube, channel_id, max_results=50)
                new_videos = [v for v in new_videos if v.get("video_id") not in latest_ids]

                if new_videos:
                    entry["videos"] = new_videos + existing_videos
                    entry["video_count"] = len(entry["videos"])
                    logger.info(f"  Found {len(new_videos)} NEW videos")
                else:
                    logger.info(f"  No new videos")
            else:
                # Full fetch mode
                max_vids = None if fetch_all else 50
                logger.info(f"  Fetching videos (max={max_vids or 'ALL'})...")

                videos = fetch_channel_videos(
                    youtube,
                    channel_id,
                    max_results=max_vids or 500,
                    fetch_all=fetch_all
                )

                if videos:
                    entry["videos"] = videos
                    entry["video_count"] = len(videos)
                    logger.info(f"  Fetched {len(videos)} videos")

        updated += 1

    logger.info(f"\nUpdated {updated} entries")

    # Add refresh timestamp
    save_catalog(catalog)
    logger.info(f"Catalog refreshed at {datetime.now().isoformat()}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Refresh Mall Video Catalog")
    parser.add_argument("--full", action="store_true", help="Fetch ALL videos (quota heavy)")
    parser.add_argument("--info-only", action="store_true", help="Only fetch channel info (cheap) - RUN ONCE")
    parser.add_argument("--delta", action="store_true", help="Only fetch NEW videos since last run (efficient)")
    args = parser.parse_args()

    if args.info_only:
        logger.info("Mode: Info only (avatars + counts) - ~13 quota units")
        refresh_catalog(fetch_videos=False)
    elif args.delta:
        logger.info("Mode: Delta (new videos only) - ~1300 quota units max")
        refresh_catalog(fetch_videos=True, delta_only=True)
    elif args.full:
        logger.info("Mode: Full refresh (ALL videos - quota heavy!)")
        response = input("This will use significant quota. Continue? [y/N] ")
        if response.lower() == 'y':
            refresh_catalog(fetch_videos=True, fetch_all=True)
        else:
            logger.info("Aborted")
    else:
        logger.info("Mode: Standard refresh (50 latest videos per channel)")
        refresh_catalog(fetch_videos=True, fetch_all=False)


if __name__ == "__main__":
    main()
