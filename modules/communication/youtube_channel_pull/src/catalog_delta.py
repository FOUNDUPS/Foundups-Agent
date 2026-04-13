"""
Catalog Delta Generator - Compare pulled videos against existing catalog.

Produces a reviewable delta artifact showing:
- Videos already present (skipped)
- New candidate videos (to review)
- Duplicates detected

WSP References:
- WSP 3: Communication domain
- WSP 97: Truthful output (no blind mutation)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


def get_existing_video_ids(catalog_entry: Dict[str, Any]) -> Set[str]:
    """
    Extract all video_id values from a catalog entry's videos array.

    Args:
        catalog_entry: Single entry from mall-video-catalog.json

    Returns:
        Set of video_id strings
    """
    videos = catalog_entry.get("videos", [])
    return {v.get("video_id", "") for v in videos if v.get("video_id")}


def compute_delta(
    foundup_id: str,
    existing_video_ids: Set[str],
    pulled_videos: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compute delta between pulled videos and existing catalog.

    Args:
        foundup_id: FoundUp identifier
        existing_video_ids: Set of video IDs already in catalog
        pulled_videos: List of video dicts from API pull

    Returns:
        Delta dict with new_videos, existing_count, skipped_count
    """
    new_videos = []
    skipped_ids = []

    for video in pulled_videos:
        video_id = video.get("video_id", "")
        if video_id in existing_video_ids:
            skipped_ids.append(video_id)
        else:
            new_videos.append(video)

    return {
        "foundup_id": foundup_id,
        "existing_count": len(existing_video_ids),
        "pulled_count": len(pulled_videos),
        "new_count": len(new_videos),
        "skipped_count": len(skipped_ids),
        "new_videos": new_videos,
        "skipped_ids": skipped_ids,
    }


def generate_full_delta(
    catalog: List[Dict[str, Any]],
    pulled_by_foundup: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Generate full delta report across all FoundUps.

    Args:
        catalog: Full mall-video-catalog.json content
        pulled_by_foundup: Dict mapping foundup_id -> pulled videos list

    Returns:
        Full delta report
    """
    # Build lookup of existing videos by foundup_id
    catalog_by_id = {entry.get("foundup_id", ""): entry for entry in catalog}

    deltas = []
    total_new = 0
    total_skipped = 0

    for foundup_id, pulled_videos in pulled_by_foundup.items():
        catalog_entry = catalog_by_id.get(foundup_id, {})
        existing_ids = get_existing_video_ids(catalog_entry)

        delta = compute_delta(foundup_id, existing_ids, pulled_videos)
        deltas.append(delta)
        total_new += delta["new_count"]
        total_skipped += delta["skipped_count"]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "summary": {
            "foundups_checked": len(deltas),
            "total_new_videos": total_new,
            "total_skipped": total_skipped,
        },
        "deltas": deltas,
    }


def write_delta_artifact(
    delta: Dict[str, Any],
    output_path: Path,
) -> Path:
    """
    Write delta artifact to JSON file.

    Args:
        delta: Delta report dict
        output_path: Path to write JSON

    Returns:
        Path written to
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(delta, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"[DELTA] Wrote delta artifact to {output_path}")
    return output_path


def format_delta_summary(delta: Dict[str, Any]) -> str:
    """
    Format delta for human review in terminal.

    Args:
        delta: Full delta report

    Returns:
        Formatted string
    """
    lines = [
        "=" * 60,
        "YOUTUBE CHANNEL PULL DELTA REPORT",
        f"Generated: {delta.get('generated_at', 'unknown')}",
        "=" * 60,
        "",
        f"FoundUps checked: {delta['summary']['foundups_checked']}",
        f"Total new videos:  {delta['summary']['total_new_videos']}",
        f"Total skipped:     {delta['summary']['total_skipped']}",
        "",
    ]

    for d in delta.get("deltas", []):
        lines.append(f"--- {d['foundup_id']} ---")
        lines.append(f"  Existing: {d['existing_count']} | Pulled: {d['pulled_count']}")
        lines.append(f"  New: {d['new_count']} | Skipped: {d['skipped_count']}")
        if d["new_videos"]:
            lines.append("  New videos:")
            for v in d["new_videos"][:5]:  # Show first 5
                lines.append(f"    - {v['video_id']}: {v['title'][:50]}...")
            if len(d["new_videos"]) > 5:
                lines.append(f"    ... and {len(d['new_videos']) - 5} more")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
