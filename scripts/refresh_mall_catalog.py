#!/usr/bin/env python3
"""
Refresh Mall Video Catalog - Update channel avatars and video counts.

SAFETY: Dry-run by default. Use --apply to actually write changes.

Usage:
    python scripts/refresh_mall_catalog.py --public-pages-only        # Preview bounded public assets offline
    python scripts/refresh_mall_catalog.py --public-pages-only --apply # Write only derived discovery pages
    python scripts/refresh_mall_catalog.py --scoped-only --apply # Build reviewed public video projections offline
    python scripts/refresh_mall_catalog.py --audit-scoped-source hpc # Read-only candidate reconciliation
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
import hashlib
import logging
import os
import re
import sys
import tempfile
from pathlib import Path
from datetime import datetime
from urllib.parse import parse_qsl, urlsplit

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

CATALOG_PATH = REPO_ROOT / "public" / "member" / "mall-video-catalog.json"
SCOPED_CATALOG_PATH = CATALOG_PATH.with_name("mall-public-video-catalog.json")
SCOPED_PROJECTIONS = ("modules/foundups/hpc/mall_projection.json",)
SCHUMER_OUT = re.compile(r"\bschumer[\s_-]*out\b", re.IGNORECASE)
PUBLIC_DISCOVERY_PAGE_SIZE = 6
PUBLIC_DISCOVERY_PREFIX = "/member/discovery/"
PUBLIC_DISCOVERY_METADATA_FIELDS = (
    "foundup_id", "canonical_foundup_id", "name", "title", "creator",
    "creator_display", "entity", "source_type", "source_id", "source_handle",
    "category", "tags", "geo", "status", "display_order", "poster_url",
    "channel_avatar_url", "theme", "tagline", "one_sentence_pitch", "description",
    "tier", "lifecycle_stage", "launch_readiness", "entry_copy", "discovery_kind",
    "public_plan_url", "public_poc_url", "external_url", "routing_prefix",
    "topic_family", "related_lanes", "parent_channels", "derivation_method",
    "outcome", "solution", "pain", "linkedin_url",
)
PUBLIC_DISCOVERY_VIDEO_FIELDS = (
    "video_id", "title", "thumbnail_url", "embed_url", "source_url", "timestamp",
    "duration_seconds", "editorial_label", "source_label",
)
_DISCOVERY_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_DISCOVERY_RESERVED_IDS = {"__proto__", "constructor", "prototype"}
_DISCOVERY_URL_FIELDS = {
    "poster_url", "channel_avatar_url", "public_plan_url", "public_poc_url",
    "external_url", "routing_prefix", "thumbnail_url", "embed_url", "source_url",
    "linkedin_url",
}
_DISCOVERY_LIST_FIELDS = {"tags", "related_lanes", "parent_channels"}
_DISCOVERY_ASSET_PATH = re.compile(
    r"(?:catalog\.json|[0-9a-f]{64}/(?:catalog/[0-9]{4,}\.json|"
    r"videos/[A-Za-z0-9][A-Za-z0-9_-]{0,63}/catalog/[0-9]{4,}\.json))\Z"
)


def _discovery_id(value):
    if (not isinstance(value, str) or not _DISCOVERY_ID.fullmatch(value)
            or value.lower() in _DISCOVERY_RESERVED_IDS):
        raise ValueError("Invalid public discovery record identity")
    return value


def _discovery_value(field, value):
    """Copy only declared public values, rejecting nested/runtime payloads."""
    if value is None:
        return None
    if field in _DISCOVERY_LIST_FIELDS:
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError("Invalid public discovery list")
        return list(value)
    if field in {"display_order", "duration_seconds"}:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError("Invalid public discovery numeric value")
        # Reject NaN/Infinity before these values enter a digest or JSON asset.
        if not float("-inf") < value < float("inf"):
            raise ValueError("Non-finite public discovery numeric value")
        return value
    if not isinstance(value, str):
        raise ValueError("Invalid public discovery text")
    if field in _DISCOVERY_URL_FIELDS and value:
        if any(ord(char) < 32 for char in value) or "\\" in value:
            raise ValueError("Invalid public discovery URL")
        parsed = urlsplit(value)
        if parsed.username or parsed.password or (
            (parsed.scheme == "https" and not parsed.hostname) or
            parsed.scheme != "https" and not (
                not parsed.scheme and not parsed.netloc and value.startswith("/")
                and not value.startswith("//")
            )
        ):
            raise ValueError("Public discovery URL must be HTTPS or same-origin")
        if any(re.search(r"token|password|secret|credential|signature|api.?key", key, re.I)
               for key, _ in parse_qsl(parsed.query, keep_blank_values=True)):
            raise ValueError("Credential-bearing public discovery URL rejected")
    return value


def _discovery_json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def build_public_discovery_pages(catalog):
    """Pure, deterministic six-item assets from the reviewed source catalog.

    Public card metadata never embeds videos or member/runtime fields. Video
    pages contain only one selected record in its existing catalog order. No
    popularity order is advertised without actual per-video metrics.
    """
    if not isinstance(catalog, list):
        raise ValueError("Public discovery source must be a list")
    records, seen = [], set()
    for source in catalog:
        if not isinstance(source, dict):
            raise ValueError("Invalid public discovery source record")
        record_id = _discovery_id(source.get("foundup_id"))
        if record_id.casefold() in seen:
            raise ValueError("Duplicate public discovery record identity")
        seen.add(record_id.casefold())
        metadata = {
            field: _discovery_value(field, source[field])
            for field in PUBLIC_DISCOVERY_METADATA_FIELDS if field in source
        }
        canonical = source.get("canonical_foundup_id")
        metadata["canonical_foundup_id"] = _discovery_id(canonical) if canonical is not None else None
        source_videos = source.get("videos", [])
        if not isinstance(source_videos, list):
            raise ValueError("Public discovery videos must be a list")
        videos, video_ids = [], set()
        for source_video in source_videos:
            if not isinstance(source_video, dict):
                raise ValueError("Invalid public discovery video")
            video_id = source_video.get("video_id")
            if not isinstance(video_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                raise ValueError("Invalid public discovery video identity")
            if video_id in video_ids:
                raise ValueError("Duplicate video identity within public discovery record")
            video_ids.add(video_id)
            videos.append({
                field: _discovery_value(field, source_video[field])
                for field in PUBLIC_DISCOVERY_VIDEO_FIELDS if field in source_video
            })
        metadata["video_count"] = len(videos)
        metadata["available_orders"] = ["catalog"]
        records.append({"metadata": metadata, "videos": videos})

    generation = hashlib.sha256(_discovery_json_bytes({
        "schema_version": 1, "page_size": PUBLIC_DISCOVERY_PAGE_SIZE, "records": records,
    })).hexdigest()
    assets, metadata_records = {}, []

    def add_pages(items, kind, record_id=None):
        count = max(1, (len(items) + PUBLIC_DISCOVERY_PAGE_SIZE - 1) // PUBLIC_DISCOVERY_PAGE_SIZE)
        folder = f"{generation}/catalog" if kind == "catalog" else f"{generation}/videos/{record_id}/catalog"
        for page in range(count):
            payload = {
                "schema_version": 1, "generation": generation, "kind": kind,
                "record_id": record_id, "order": "catalog", "page": page,
                "page_size": PUBLIC_DISCOVERY_PAGE_SIZE, "total": len(items),
                "items": items[page * PUBLIC_DISCOVERY_PAGE_SIZE:(page + 1) * PUBLIC_DISCOVERY_PAGE_SIZE],
                "next": PUBLIC_DISCOVERY_PREFIX + f"{folder}/{page + 1:04d}.json" if page + 1 < count else None,
            }
            if kind == "videos":
                payload["available_orders"] = ["catalog"]
            relative = "catalog.json" if kind == "catalog" and page == 0 else f"{folder}/{page:04d}.json"
            assets[relative] = payload

    for record in records:
        metadata, videos = record["metadata"], record["videos"]
        record_id = metadata["foundup_id"]
        metadata_records.append({**metadata, "video_pages": {"catalog": (
            PUBLIC_DISCOVERY_PREFIX + f"{generation}/videos/{record_id}/catalog/0000.json"
            if videos else None
        )}})
        if videos:
            add_pages(videos, "videos", record_id)
    add_pages(metadata_records, "catalog")
    return assets


def write_public_discovery_pages(assets, repo_root=REPO_ROOT, dry_run=True):
    """Write known generated paths only, with the root catalog published last.

    Old generations are deliberately retained; release maintenance owns cleanup
    after confirming no deployed page references them. This exporter never
    recursively deletes files or changes the source/legacy catalog.
    """
    repo_root = Path(repo_root).resolve()
    output_root = repo_root / "public" / "member" / "discovery"
    if output_root.resolve() != output_root:
        raise ValueError("Public discovery generated directory must not be redirected")
    prepared = []
    for relative, payload in assets.items():
        if not isinstance(relative, str) or not _DISCOVERY_ASSET_PATH.fullmatch(relative):
            raise ValueError("Invalid generated public discovery path")
        target = output_root / relative
        if target.resolve() != target:
            raise ValueError("Public discovery output escaped generated directory")
        prepared.append((target, _discovery_json_bytes(payload)))
    if dry_run:
        logger.info("[DRY-RUN] Would write %d public discovery assets", len(prepared))
        return len(prepared)
    # Publish all immutable generation pages before changing the root pointer.
    for target, content in sorted(prepared, key=lambda item: item[0].name == "catalog.json"):
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".discovery-", delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(content)
            os.replace(temporary, target)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
    logger.info("Wrote %d public discovery assets; obsolete generations retained", len(prepared))
    return len(prepared)


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
                "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/oardefault.jpg",
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
            "canonical_foundup_id": entry["foundup_id"],
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
            "tags": ["012-lane", "political-media", config["topic"].lstrip("#").lower()],
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
        narrative_fields = {
            k: previous[k]
            for k in ("outcome", "solution", "pain")
            if previous and k in previous
        }
        lanes[foundup_id] = {
            **lane,
            "videos": [],
            "video_count": 0,
            "public_poc_url": entry["poc_url"],
            **narrative_fields,
        }
        scoped[foundup_id] = {
            "lane": lane,
            "identity": config["identity"],
            "topic": config["topic"],
            "credit": source["entity"],
            "voice_resource_url": config["voice_resource_url"],
            "disclosure": config["disclosure"],
        }
    return list(lanes.values()), scoped


def audit_scoped_youtube_source(youtube, channel_id: str) -> dict:
    """Enumerate public uploads and inspect all available snippets in 50-ID batches."""
    channels = youtube.channels().list(
        part="contentDetails,statistics", id=channel_id,
    ).execute()["items"]
    if len(channels) != 1:
        raise ValueError("Expected one public source channel")
    channel = channels[0]
    playlist = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, seen, duplicates, page_tokens = [], set(), [], set()
    token, pages, raw_count = None, 0, 0
    while True:
        params = {"part": "contentDetails", "playlistId": playlist, "maxResults": 50}
        if token:
            params["pageToken"] = token
        response = youtube.playlistItems().list(**params).execute()
        pages += 1
        for item in response.get("items", []):
            raw_count += 1
            video_id = item["contentDetails"]["videoId"]
            if video_id in seen:
                duplicates.append(video_id)
            else:
                ids.append(video_id)
                seen.add(video_id)
        token = response.get("nextPageToken")
        if not token:
            break
        if token in page_tokens:
            raise ValueError("Repeated uploads page token")
        page_tokens.add(token)

    returned, candidates = set(), []
    non_public_count = 0
    for offset in range(0, len(ids), 50):
        batch = ids[offset:offset + 50]
        response = youtube.videos().list(
            part="snippet,status,contentDetails", id=",".join(batch),
        ).execute()
        for video in response.get("items", []):
            video_id = video["id"]
            if video_id not in batch or video_id in returned:
                raise ValueError("Unexpected YouTube video metadata response")
            returned.add(video_id)
            status = video["status"]
            if status.get("privacyStatus") != "public":
                non_public_count += 1
                continue
            snippet = video["snippet"]
            fields = [
                key for key in ("title", "description")
                if SCHUMER_OUT.search(snippet.get(key, ""))
            ]
            if any(SCHUMER_OUT.search(tag) for tag in snippet.get("tags", [])):
                fields.append("tags")
            if not fields:
                continue
            candidates.append({
                "video_id": video_id, "title": snippet["title"], "timestamp": snippet["publishedAt"],
                "matched_fields": fields, "source_channel_match": snippet.get("channelId") == channel_id,
                "privacy": status.get("privacyStatus"), "embeddable": status.get("embeddable"),
                "duration": video["contentDetails"].get("duration"),
                "region_restriction": video["contentDetails"].get("regionRestriction"),
                "shorts_candidate_url": f"https://www.youtube.com/shorts/{video_id}",
            })
    return {
        "source_channel_id": channel_id, "uploads_playlist": playlist,
        "channel_video_count": int(channel.get("statistics", {}).get("videoCount", 0)),
        "pages": pages, "playlist_items": raw_count, "unique_ids": len(ids),
        "duplicate_ids": duplicates, "missing_metadata_ids": [v for v in ids if v not in returned],
        "non_public_metadata_count": non_public_count,
        "candidates": sorted(candidates, key=lambda v: v["timestamp"], reverse=True),
    }


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
    parser.add_argument("--public-pages-only", action="store_true", help="Build six-item public discovery pages offline, without YouTube credentials")
    parser.add_argument("--scoped-only", action="store_true", help="Project reviewed public lanes without YouTube credentials")
    parser.add_argument("--audit-scoped-source", choices=("hpc",), help="Read-only official YouTube candidate audit")
    parser.add_argument("--full", action="store_true", help="Fetch ALL videos (quota heavy)")
    parser.add_argument("--info-only", action="store_true", help="Only fetch channel info (cheap) - RUN ONCE")
    parser.add_argument("--delta", action="store_true", help="Only fetch NEW videos since last run (efficient)")
    parser.add_argument("--apply", action="store_true", help="Actually write changes (default is dry-run)")
    args = parser.parse_args()

    dry_run = not args.apply
    mode_suffix = "" if args.apply else " [DRY-RUN]"

    if args.public_pages_only:
        if args.scoped_only or args.audit_scoped_source or args.info_only or args.delta or args.full:
            parser.error("--public-pages-only must not be combined with source refresh modes")
        if not CATALOG_PATH.is_file():
            parser.error("Public discovery source catalog is missing")
        assets = build_public_discovery_pages(load_catalog())
        write_public_discovery_pages(assets, repo_root=REPO_ROOT, dry_run=dry_run)
        logger.info("Public discovery generation: %s%s", assets["catalog.json"]["generation"], mode_suffix)
    elif args.audit_scoped_source:
        if args.scoped_only or args.info_only or args.delta or args.full or args.apply:
            parser.error("--audit-scoped-source is read-only and must run alone")
        configs = [json.loads((REPO_ROOT / path).read_text(encoding="utf-8")) for path in SCOPED_PROJECTIONS]
        config = next((item for item in configs if item["foundup_id"] == args.audit_scoped_source), None)
        if not config:
            parser.error("Unknown scoped projection")
        source = next((item for item in load_catalog() if item["foundup_id"] == config["source_foundup_id"]), None)
        if not source or source["source_type"] != "youtube_channel":
            parser.error("The configured source is not a public YouTube channel lane")
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if not api_key:
            parser.error("--audit-scoped-source requires an existing public Data API key in YOUTUBE_API_KEY")
        try:
            from googleapiclient.discovery import build

            # Public Data API only. This audit never loads owner OAuth sessions.
            youtube = build("youtube", "v3", developerKey=api_key, cache_discovery=False)
            print(json.dumps(audit_scoped_youtube_source(youtube, source["source_id"]), indent=2))
        except Exception as error:
            parser.exit(1, f"Scoped source audit incomplete: {type(error).__name__}\n")
    elif args.scoped_only:
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
