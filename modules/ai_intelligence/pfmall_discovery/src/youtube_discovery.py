"""
YouTube Discovery - Search YouTube for candidate videos/channels.

Provides exploratory search beyond known channels in the catalog.
Results are proposals for human review, not direct catalog mutations.

WSP References:
- WSP 3: AI Intelligence domain
- WSP 97: Truthful discovery (reports blockers honestly)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryProposal:
    """A discovered video/channel proposal for review."""

    query: str
    candidate_type: str  # "video" or "channel"
    video_id: Optional[str] = None
    channel_id: str = ""
    channel_title: str = ""
    title: str = ""
    description: str = ""
    thumbnail_url: str = ""
    embed_url: str = ""
    source_url: str = ""
    published_at: str = ""
    # Matching info
    matched_foundup_id: Optional[str] = None
    match_reason: str = ""
    confidence: float = 0.0
    ambiguous_candidates: List[str] = field(default_factory=list)
    # Review status
    review_status: str = "proposed"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "query": self.query,
            "candidate_type": self.candidate_type,
            "video_id": self.video_id,
            "channel_id": self.channel_id,
            "channel_title": self.channel_title,
            "title": self.title,
            "description": self.description,
            "thumbnail_url": self.thumbnail_url,
            "embed_url": self.embed_url,
            "source_url": self.source_url,
            "published_at": self.published_at,
            "matched_foundup_id": self.matched_foundup_id,
            "match_reason": self.match_reason,
            "confidence": self.confidence,
            "ambiguous_candidates": self.ambiguous_candidates,
            "review_status": self.review_status,
        }


def search_youtube(
    youtube_service,
    query: str,
    max_results: int = 25,
    search_type: str = "video",
) -> List[DiscoveryProposal]:
    """
    Search YouTube for videos or channels matching a query.

    Args:
        youtube_service: Authenticated googleapiclient YouTube service
        query: Search query string
        max_results: Maximum results to return (default 25)
        search_type: "video" or "channel" (default "video")

    Returns:
        List of DiscoveryProposal objects
    """
    if not youtube_service:
        logger.error("[DISCOVERY] No YouTube service provided")
        return []

    if not query or not query.strip():
        logger.error("[DISCOVERY] Empty search query")
        return []

    query = query.strip()
    proposals: List[DiscoveryProposal] = []

    try:
        # Build search request
        request = youtube_service.search().list(
            part="snippet",
            q=query,
            type=search_type,
            order="relevance",
            maxResults=min(max_results, 50),
        )
        response = request.execute()

        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            item_id = item.get("id", {})

            # Get best thumbnail
            thumbnails = snippet.get("thumbnails", {})
            thumbnail_url = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url")
                or ""
            )

            if search_type == "video":
                video_id = item_id.get("videoId")
                if not video_id:
                    continue

                proposal = DiscoveryProposal(
                    query=query,
                    candidate_type="video",
                    video_id=video_id,
                    channel_id=snippet.get("channelId", ""),
                    channel_title=snippet.get("channelTitle", ""),
                    title=snippet.get("title", ""),
                    description=snippet.get("description", ""),
                    thumbnail_url=thumbnail_url,
                    embed_url=f"https://www.youtube.com/embed/{video_id}",
                    source_url=f"https://www.youtube.com/watch?v={video_id}",
                    published_at=snippet.get("publishedAt", ""),
                )
                proposals.append(proposal)

            elif search_type == "channel":
                channel_id = item_id.get("channelId")
                if not channel_id:
                    continue

                proposal = DiscoveryProposal(
                    query=query,
                    candidate_type="channel",
                    channel_id=channel_id,
                    channel_title=snippet.get("channelTitle", ""),
                    title=snippet.get("title", ""),
                    description=snippet.get("description", ""),
                    thumbnail_url=thumbnail_url,
                    source_url=f"https://www.youtube.com/channel/{channel_id}",
                    published_at=snippet.get("publishedAt", ""),
                )
                proposals.append(proposal)

        logger.info(f"[DISCOVERY] Found {len(proposals)} {search_type}s for query: {query}")

    except Exception as e:
        logger.error(f"[DISCOVERY] Search failed for query '{query}': {e}")

    return proposals


def search_by_topic(
    youtube_service,
    topic: str,
    include_videos: bool = True,
    include_channels: bool = False,
    max_results: int = 25,
) -> List[DiscoveryProposal]:
    """
    Search YouTube by topic, optionally including both videos and channels.

    Args:
        youtube_service: Authenticated YouTube service
        topic: Topic to search for
        include_videos: Include video results (default True)
        include_channels: Include channel results (default False)
        max_results: Max results per type

    Returns:
        Combined list of proposals
    """
    proposals = []

    if include_videos:
        proposals.extend(search_youtube(youtube_service, topic, max_results, "video"))

    if include_channels:
        proposals.extend(search_youtube(youtube_service, topic, max_results, "channel"))

    return proposals
