#!/usr/bin/env python3
"""
YouTube Channel Refresh Scheduler - Scheduled/triggered refresh for known channels.

This module provides a scheduler-ready entrypoint for refreshing YouTube channel
content in pfMALL. It wraps the existing pull_cli logic and can be triggered:
- Manually by operator
- Via Windows Task Scheduler
- Via cron (Linux)
- Via CI/CD pipeline or task runner

Default behavior is review-first: generates delta artifact, no catalog mutation.

Usage:
    # Manual trigger (dry-run, all channels)
    python -m modules.communication.youtube_channel_pull.src.refresh_scheduler

    # Trigger specific FoundUp
    python -m modules.communication.youtube_channel_pull.src.refresh_scheduler --foundup move2japan

    # Run as scheduled task (same behavior, just triggered by scheduler)
    python -m modules.communication.youtube_channel_pull.src.refresh_scheduler --scheduled

WSP References:
- WSP 3: Communication domain
- WSP 97: Truthful guarantees (review-first, no blind mutation)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
CATALOG_PATH = REPO_ROOT / "public" / "member" / "mall-video-catalog.json"
DELTA_PATH = REPO_ROOT / "docs" / "audits" / "pfmall_youtube_ingest" / "youtube_channel_pull_delta.json"
REFRESH_LOG_PATH = REPO_ROOT / "docs" / "audits" / "pfmall_youtube_ingest" / "refresh_log.json"


class RefreshResult:
    """Result of a refresh operation."""

    def __init__(
        self,
        success: bool,
        foundups_checked: int = 0,
        new_videos_found: int = 0,
        delta_path: Optional[Path] = None,
        error: Optional[str] = None,
        triggered_at: Optional[str] = None,
        trigger_mode: str = "manual",
    ):
        self.success = success
        self.foundups_checked = foundups_checked
        self.new_videos_found = new_videos_found
        self.delta_path = delta_path
        self.error = error
        self.triggered_at = triggered_at or datetime.now(timezone.utc).isoformat()
        self.trigger_mode = trigger_mode

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "foundups_checked": self.foundups_checked,
            "new_videos_found": self.new_videos_found,
            "delta_path": str(self.delta_path) if self.delta_path else None,
            "error": self.error,
            "triggered_at": self.triggered_at,
            "trigger_mode": self.trigger_mode,
        }


def load_catalog() -> List[Dict[str, Any]]:
    """Load mall-video-catalog.json."""
    if not CATALOG_PATH.exists():
        logger.error(f"[REFRESH] Catalog not found: {CATALOG_PATH}")
        return []
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def get_youtube_service():
    """Get authenticated YouTube API service."""
    try:
        from modules.platform_integration.youtube_auth.src.youtube_auth import (
            get_authenticated_service,
        )
        return get_authenticated_service()
    except Exception as e:
        logger.warning(f"[REFRESH] YouTube auth unavailable: {e}")
        return None


def run_refresh(
    foundup_filter: Optional[str] = None,
    max_results: int = 50,
    trigger_mode: str = "manual",
) -> RefreshResult:
    """
    Run the channel refresh workflow.

    This is the main entrypoint for scheduled/triggered refresh.
    It reuses the existing pull logic - no duplication.

    Args:
        foundup_filter: Optional FoundUp ID to filter (default: all)
        max_results: Max videos per channel (default: 50)
        trigger_mode: How this was triggered ("manual", "scheduled", "ci")

    Returns:
        RefreshResult with operation details
    """
    triggered_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    logger.info(f"[REFRESH] Starting channel refresh (mode: {trigger_mode})")

    # Load catalog
    catalog = load_catalog()
    if not catalog:
        return RefreshResult(
            success=False,
            error="Empty or missing catalog",
            triggered_at=triggered_at,
            trigger_mode=trigger_mode,
        )

    # Import pull components
    try:
        from modules.communication.youtube_channel_pull.src.channel_puller import (
            fetch_channel_videos,
            get_channel_ids_from_catalog,
        )
        from modules.communication.youtube_channel_pull.src.catalog_delta import (
            generate_full_delta,
            write_delta_artifact,
            format_delta_summary,
        )
    except ImportError as e:
        return RefreshResult(
            success=False,
            error=f"Failed to import pull components: {e}",
            triggered_at=triggered_at,
            trigger_mode=trigger_mode,
        )

    # Get channel mappings
    channel_map = get_channel_ids_from_catalog(catalog)
    logger.info(f"[REFRESH] Found {len(channel_map)} YouTube-backed FoundUps")

    # Filter if requested
    if foundup_filter:
        if foundup_filter not in channel_map:
            return RefreshResult(
                success=False,
                error=f"FoundUp '{foundup_filter}' not found or not YouTube-backed",
                triggered_at=triggered_at,
                trigger_mode=trigger_mode,
            )
        channel_map = {foundup_filter: channel_map[foundup_filter]}
        logger.info(f"[REFRESH] Filtering to: {foundup_filter}")

    # Get YouTube service
    youtube = get_youtube_service()
    if not youtube:
        logger.warning("[REFRESH] YouTube API unavailable - generating empty delta")
        pulled_by_foundup = {fid: [] for fid in channel_map.keys()}
    else:
        # Fetch videos from each channel
        pulled_by_foundup = {}
        for foundup_id, channel_id in channel_map.items():
            logger.info(f"[REFRESH] Pulling {foundup_id} (channel: {channel_id})")
            try:
                videos = fetch_channel_videos(youtube, channel_id, max_results=max_results)
                pulled_by_foundup[foundup_id] = videos
            except Exception as e:
                logger.error(f"[REFRESH] Failed to pull {foundup_id}: {e}")
                pulled_by_foundup[foundup_id] = []

    # Generate delta
    delta = generate_full_delta(catalog, pulled_by_foundup)

    # Write artifact
    write_delta_artifact(delta, DELTA_PATH)

    # Log summary
    summary = delta.get("summary", {})
    new_count = summary.get("total_new_videos", 0)
    foundups_count = summary.get("foundups_checked", 0)

    logger.info(f"[REFRESH] Complete: {foundups_count} FoundUps, {new_count} new videos")
    logger.info(f"[REFRESH] Delta artifact: {DELTA_PATH}")
    logger.info("[REFRESH] Next step: Review delta, then apply approved videos to catalog")

    # Print summary to console
    try:
        print(format_delta_summary(delta))
    except UnicodeEncodeError:
        # Windows console fallback
        print(format_delta_summary(delta).encode("ascii", errors="replace").decode("ascii"))

    return RefreshResult(
        success=True,
        foundups_checked=foundups_count,
        new_videos_found=new_count,
        delta_path=DELTA_PATH,
        triggered_at=triggered_at,
        trigger_mode=trigger_mode,
    )


def log_refresh_result(result: RefreshResult) -> None:
    """
    Append refresh result to the refresh log.

    This provides observability for scheduled runs.
    """
    REFRESH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Load existing log
    if REFRESH_LOG_PATH.exists():
        try:
            log_data = json.loads(REFRESH_LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            log_data = {"runs": []}
    else:
        log_data = {"runs": []}

    # Append new result
    log_data["runs"].append(result.to_dict())

    # Keep last 100 runs
    log_data["runs"] = log_data["runs"][-100:]

    # Write back
    REFRESH_LOG_PATH.write_text(
        json.dumps(log_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info(f"[REFRESH] Logged result to {REFRESH_LOG_PATH}")


def main():
    """CLI entrypoint for refresh scheduler."""
    parser = argparse.ArgumentParser(
        description="YouTube Channel Refresh Scheduler - Scheduled/triggered refresh for known channels"
    )
    parser.add_argument(
        "--foundup",
        type=str,
        default=None,
        help="Refresh only specified FoundUp by foundup_id",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=50,
        help="Max videos per channel (default: 50)",
    )
    parser.add_argument(
        "--scheduled",
        action="store_true",
        help="Mark this run as scheduled (vs manual)",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Skip logging result to refresh_log.json",
    )
    args = parser.parse_args()

    trigger_mode = "scheduled" if args.scheduled else "manual"

    # Run refresh
    result = run_refresh(
        foundup_filter=args.foundup,
        max_results=args.max_results,
        trigger_mode=trigger_mode,
    )

    # Log result unless disabled
    if not args.no_log:
        log_refresh_result(result)

    # Exit code
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
