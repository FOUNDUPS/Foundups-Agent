"""
YouTube Channel Puller - Fetch latest videos from a YouTube channel.

Reads channel identity from catalog source_id or youtube_channel_registry,
fetches latest N videos via YouTube Data API, returns structured video list.

WSP References:
- WSP 3: Communication domain
- WSP 97: Browser-verified (truthful API response, no fake data)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def fetch_channel_videos(
    youtube_service,
    channel_id: str,
    max_results: int = 50,
) -> List[Dict[str, Any]]:
    """
    Fetch latest videos from a YouTube channel via Data API.

    Args:
        youtube_service: Authenticated googleapiclient YouTube service
        channel_id: YouTube channel ID (e.g., "UC-LSSlOZwpGIRIYihaz8zCw")
        max_results: Maximum videos to fetch (default 50, max 50 per request)

    Returns:
        List of video dicts with: video_id, title, thumbnail_url, embed_url, published_at
    """
    if not youtube_service:
        logger.error("[PULL] No YouTube service provided")
        return []
    if not channel_id or not channel_id.startswith("UC"):
        logger.error(f"[PULL] Invalid channel_id: {channel_id}")
        return []

    videos: List[Dict[str, Any]] = []

    try:
        # Search for videos from this channel (ordered by date, newest first)
        request = youtube_service.search().list(
            part="snippet",
            channelId=channel_id,
            type="video",
            order="date",
            maxResults=min(max_results, 50),
        )
        response = request.execute()

        for item in response.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if not video_id:
                continue

            snippet = item.get("snippet", {})
            published_at = snippet.get("publishedAt", "")

            # Get best available thumbnail
            thumbnails = snippet.get("thumbnails", {})
            thumbnail_url = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url")
                or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            )

            videos.append({
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "thumbnail_url": thumbnail_url,
                "embed_url": f"https://www.youtube.com/embed/{video_id}",
                "source_url": f"https://www.youtube.com/watch?v={video_id}",
                "published_at": published_at,
                "channel_id": channel_id,
            })

        logger.info(f"[PULL] Fetched {len(videos)} videos from channel {channel_id}")

    except Exception as e:
        logger.error(f"[PULL] API error for channel {channel_id}: {e}")

    return videos


def get_channel_id_from_catalog(catalog_entry: Dict[str, Any]) -> Optional[str]:
    """
    Extract YouTube channel ID from a catalog entry.

    Looks for source_id field where source_type is 'youtube_channel'.

    Args:
        catalog_entry: Single entry from mall-video-catalog.json

    Returns:
        Channel ID string or None
    """
    source_type = catalog_entry.get("source_type", "")
    if source_type != "youtube_channel":
        return None

    source_id = catalog_entry.get("source_id", "")
    if source_id and source_id.startswith("UC"):
        return source_id

    return None


def get_channel_ids_from_catalog(catalog: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Extract all YouTube channel IDs from catalog.

    Returns:
        Dict mapping foundup_id -> channel_id
    """
    mapping = {}
    for entry in catalog:
        foundup_id = entry.get("foundup_id", "")
        channel_id = get_channel_id_from_catalog(entry)
        if foundup_id and channel_id:
            mapping[foundup_id] = channel_id
    return mapping
