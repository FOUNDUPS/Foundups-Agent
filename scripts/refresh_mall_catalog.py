#!/usr/bin/env python3
"""
Refresh Mall Video Catalog - Update channel avatars and video counts.

SAFETY: Dry-run by default. Use --apply to actually write changes.

Usage:
    python scripts/refresh_mall_catalog.py --scoped-only --apply # Build reviewed public video projections offline
    python scripts/refresh_mall_catalog.py --info-only          # Preview: avatars + counts (13 units)
    python scripts/refresh_mall_catalog.py --info-only --apply  # Apply: avatars + counts
    python scripts/refresh_mall_catalog.py --delta              # Preview: new videos only (~100 units)
    python scripts/refresh_mall_catalog.py --delta --apply      # Apply: new videos only
    python scripts/refresh_mall_catalog.py --apply              # Apply: 50 latest per channel (1300 units)
    python scripts/refresh_mall_catalog.py --full --apply       # Apply: ALL videos (quota heavy!)

Recommended workflow:
    1. Run --info-only (dry-run) to preview what will change
    2. Run --info-only --apply to save avatars
    3. Run --delta --apply periodically to get new videos
"""

import json
import logging
import re
import sys
from pathlib import Path
from datetime import datetime

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

CATALOG_PATH = REPO_ROOT / "public" / "member" / "mall-video-catalog.json"
SCOPED_CATALOG_PATH = CATALOG_PATH.with_name("mall-public-video-catalog.json")
SCOPED_PROJECTIONS = ("modules/foundups/hpc/mall_projection.json",)


def load_catalog() -> list:
    """Load existing catalog."""
    if not CATALOG_PATH.exists():
        logger.error(f"Catalog not found: {CATALOG_PATH}")
        return []
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_catalog(catalog: list, dry_run: bool = True) -> None:
    """Save catalog back to JSON (or preview in dry-run mode)."""
    if dry_run:
        logger.info(f"[DRY-RUN] Would save catalog to {CATALOG_PATH}")
        logger.info(f"[DRY-RUN] Use --apply to actually write changes")
        return

    # Create backup before writing
    backup_path = CATALOG_PATH.with_suffix(".json.bak")
    if CATALOG_PATH.exists():
        import shutil
        shutil.copy2(CATALOG_PATH, backup_path)
        logger.info(f"Backup saved to {backup_path}")

    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved catalog to {CATALOG_PATH}")


def project_public_video_lanes(catalog: list, repo_root: Path = REPO_ROOT) -> tuple[list, dict]:
    """Build public-only media lanes from reviewed records and canonical identities."""
    def read_json(relative_path):
        return json.loads((repo_root / relative_path).read_text(encoding="utf-8"))

    registry = read_json("modules/foundups/foundup_registry.json")["entities"]
    entries = {entry["foundup_id"]: entry for entry in registry}
    lanes = {entry["foundup_id"]: entry for entry in catalog}
    scoped = {}
    for path in SCOPED_PROJECTIONS:
        config = read_json(path)
        foundup_id = config["foundup_id"]
        entry = entries[foundup_id]
        manifest = read_json(entry["manifest_path"])
        source = lanes[config["source_foundup_id"]]
        if (manifest["foundup_id"] != foundup_id or entry["invite_required"]
                or manifest["entry_url"] or source["source_type"] != "youtube_channel"):
            raise ValueError(f"Invalid public video projection contract for {foundup_id}")

        reviewed = {}
        for video in config["videos"]:
            video_id = video["video_id"]
            if video_id in reviewed or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                raise ValueError(f"Invalid or duplicate YouTube ID for {foundup_id}")
            reviewed[video_id] = {
                "video_id": video_id,
                "title": video["title"],
                "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/oar2.jpg",
                "embed_url": f"https://www.youtube.com/embed/{video_id}",
                "source_url": f"https://www.youtube.com/shorts/{video_id}",
                "timestamp": video["timestamp"],
                "duration_seconds": video["duration_seconds"],
            }
        if not reviewed:
            raise ValueError(f"Public video projection {foundup_id} has no reviewed videos")

        # Relate the derived collection without rewriting the general source feed.
        lanes[source["foundup_id"]] = {
            **source,
            "related_lanes": list(dict.fromkeys([*source["related_lanes"], foundup_id])),
        }
        videos = [
            {
                **reviewed[video["video_id"]],
                "editorial_label": video["editorial_label"],
                "source_label": source["entity"],
            }
            for video in config["videos"]
        ]
        previous = lanes.get(foundup_id)
        lane = {
            "foundup_id": foundup_id,
            "title": manifest["name"],
            "creator": source["creator"],
            "creator_id": source["creator_id"],
            "creator_display": source["creator_display"],
            "entity": entry["display_name"],
            "source_type": "derived",
            "source_id": source["source_id"],
            "source_handle": source["source_handle"],
            "parent_channels": [source["foundup_id"]],
            "derivation_method": "manual_curation",
            "category": manifest["category"],
            "tags": ["012-lane", "political-media", config["topic"].lower()],
            "topic_family": "media",
            "geo": "Global",
            "status": "active",
            "display_order": previous["display_order"] if previous else max(
                item["display_order"] for item in lanes.values()
            ) + 1,
            "related_lanes": [source["foundup_id"]],
            "tagline": manifest["tagline"],
            "description": manifest["description"],
            "tier": manifest["tier"],
            "lifecycle_stage": manifest["lifecycle_stage"],
            "launch_readiness": manifest["launch_readiness"],
            "poster_url": videos[0]["thumbnail_url"],
            "video_count": len(videos),
            "videos": videos,
        }
        # The global Mall offers discovery. Playback belongs to the fixed public field.
        lanes[foundup_id] = {**lane, "videos": [], "video_count": 0, "public_poc_url": entry["poc_url"]}
        scoped[foundup_id] = {
            "lane": lane,
            "identity": config["identity"],
            "topic": config["topic"],
            "credit": source["entity"],
            "voice_resource_url": config["voice_resource_url"],
            "disclosure": config["disclosure"],
        }
    return list(lanes.values()), scoped


def refresh_catalog(
    fetch_videos: bool = True,
    fetch_all: bool = False,
    delta_only: bool = False,
    dry_run: bool = True
) -> None:
    """
    Refresh catalog with channel info and optionally videos.

    Args:
        fetch_videos: If True, fetch latest videos for each channel
        fetch_all: If True and fetch_videos, fetch ALL videos (quota heavy)
        delta_only: If True, only fetch videos newer than most recent in catalog
        dry_run: If True (default), only preview changes without writing
    """
    catalog = load_catalog()
    if not catalog:
        return

    logger.info(f"Loaded {len(catalog)} entries from catalog")

    from modules.communication.youtube_channel_pull.src.channel_puller import (
        fetch_channel_info,
        fetch_channel_videos,
    )
    from modules.platform_integration.youtube_auth.src.youtube_auth import get_authenticated_service

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
    save_catalog(catalog, dry_run=dry_run)
    if not dry_run:
        logger.info(f"Catalog refreshed at {datetime.now().isoformat()}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Refresh Mall Video Catalog")
    parser.add_argument("--scoped-only", action="store_true", help="Project reviewed public lanes without YouTube credentials")
    parser.add_argument("--full", action="store_true", help="Fetch ALL videos (quota heavy)")
    parser.add_argument("--info-only", action="store_true", help="Only fetch channel info (cheap) - RUN ONCE")
    parser.add_argument("--delta", action="store_true", help="Only fetch NEW videos since last run (efficient)")
    parser.add_argument("--apply", action="store_true", help="Actually write changes (default is dry-run)")
    args = parser.parse_args()

    dry_run = not args.apply
    mode_suffix = "" if args.apply else " [DRY-RUN]"

    if args.scoped_only:
        if args.info_only or args.delta or args.full:
            parser.error("--scoped-only cannot be combined with a YouTube refresh")
        catalog, scoped = project_public_video_lanes(load_catalog())
        save_catalog(catalog, dry_run=dry_run)
        if not dry_run:
            SCOPED_CATALOG_PATH.write_text(
                json.dumps(scoped, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        logger.info(f"Public projections: {', '.join(scoped)}{mode_suffix}")
    elif args.info_only:
        logger.info(f"Mode: Info only (avatars + counts) - ~13 quota units{mode_suffix}")
        refresh_catalog(fetch_videos=False, dry_run=dry_run)
    elif args.delta:
        logger.info(f"Mode: Delta (new videos only) - ~1300 quota units max{mode_suffix}")
        refresh_catalog(fetch_videos=True, delta_only=True, dry_run=dry_run)
    elif args.full:
        logger.info(f"Mode: Full refresh (ALL videos - quota heavy!){mode_suffix}")
        if dry_run:
            logger.info("[DRY-RUN] Would fetch all videos. Use --apply to execute.")
        else:
            response = input("This will use significant quota. Continue? [y/N] ")
            if response.lower() == 'y':
                refresh_catalog(fetch_videos=True, fetch_all=True, dry_run=dry_run)
            else:
                logger.info("Aborted")
    else:
        logger.info(f"Mode: Standard refresh (50 latest videos per channel){mode_suffix}")
        refresh_catalog(fetch_videos=True, fetch_all=False, dry_run=dry_run)


if __name__ == "__main__":
    main()
