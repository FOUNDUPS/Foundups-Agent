"""
Rotation Checkpoint - Persist rotation state for crash recovery.

YouTube Domain Agent Phase 1 (G2): Enables crash resilience by persisting
rotation state to JSON. On restart, rotation can resume from the last
successfully processed channel instead of starting over.

WSP 91: Observability
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)

CHECKPOINT_PATH = Path("data/youtube_rotation_checkpoint.json")


def save_checkpoint(
    browser: str,
    processed_channels: Set[str],
    current_channel: Optional[str],
    operation: str,
    cycle_started_at: str,
) -> None:
    """
    Save rotation state to checkpoint file.

    Args:
        browser: Browser being used (chrome/edge)
        processed_channels: Set of channel names already processed
        current_channel: Channel currently being processed (or None)
        operation: Operation type (comments/shorts/indexing)
        cycle_started_at: ISO timestamp when cycle started
    """
    try:
        CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "browser": browser,
            "processed_channels": list(processed_channels),
            "current_channel": current_channel,
            "operation": operation,
            "cycle_started_at": cycle_started_at,
            "updated_at": datetime.utcnow().isoformat(),
        }
        CHECKPOINT_PATH.write_text(json.dumps(data, indent=2))
        logger.debug(f"[CHECKPOINT] Saved: {len(processed_channels)} channels processed")
    except Exception as e:
        logger.warning(f"[CHECKPOINT] Failed to save: {e}")


def load_checkpoint() -> Optional[Dict]:
    """
    Load rotation state from checkpoint file.

    Returns:
        Dict with checkpoint data, or None if no checkpoint exists
    """
    if not CHECKPOINT_PATH.exists():
        return None
    try:
        data = json.loads(CHECKPOINT_PATH.read_text())
        logger.info(f"[CHECKPOINT] Loaded: {len(data.get('processed_channels', []))} channels already processed")
        return data
    except Exception as e:
        logger.warning(f"[CHECKPOINT] Failed to load: {e}")
        return None


def clear_checkpoint() -> None:
    """
    Clear checkpoint after successful rotation cycle.

    Call this after rotation completes successfully to prevent
    stale checkpoint data on next startup.
    """
    if CHECKPOINT_PATH.exists():
        try:
            CHECKPOINT_PATH.unlink()
            logger.info("[CHECKPOINT] Cleared after successful rotation")
        except Exception as e:
            logger.warning(f"[CHECKPOINT] Failed to clear: {e}")


def get_remaining_channels(
    all_channels: List[str],
    checkpoint: Optional[Dict] = None,
) -> List[str]:
    """
    Get channels remaining to process, accounting for checkpoint.

    Args:
        all_channels: Full list of channels to process
        checkpoint: Loaded checkpoint data (or None)

    Returns:
        List of channels not yet processed
    """
    if not checkpoint:
        return all_channels

    processed = set(checkpoint.get("processed_channels", []))
    remaining = [ch for ch in all_channels if ch not in processed]

    if len(remaining) < len(all_channels):
        logger.info(f"[CHECKPOINT] Resuming: {len(remaining)}/{len(all_channels)} channels remaining")

    return remaining
