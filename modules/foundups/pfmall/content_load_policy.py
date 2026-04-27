#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Content Load Policy — Interface Stubs for Intelligent Grid Loading

Defines policy interfaces for tile loading states, content trust signals,
and load prioritization without implementing actual IntersectionObserver
or service worker logic.

WSP 97 TRUTH BOUNDARIES:
  DOES:
    - Define TileLoadState enum/dataclass
    - Define ContentLoadPolicy interface
    - Define ContentTrustSignal with ALLOWED_LABELS and BLOCKED_LABELS
    - Align BLOCKED_LABELS with VerificationGapGuard protected classes

  DOES NOT:
    - Implement IntersectionObserver
    - Modify mall-tile-field.js
    - Modify member-sw.js
    - Execute tile loading logic
    - Make content trust decisions

Contract Reference:
  modules/foundups/docs/VERIFICATION_GAP_GUARD_CONTRACT.md
  modules/foundups/docs/PFMALL_DEVICE_MODEL_ROUTING_CONTRACT.md

WSP Compliance:
  WSP 11  : Interface contract (typed API)
  WSP 97  : System Execution Prompting (truth boundaries)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# Tile Load State
# ---------------------------------------------------------------------------


class TileLoadState(str, Enum):
    """
    Load state for a single tile in the intelligent grid.

    Lifecycle: PENDING -> VISIBLE -> LOADING -> LOADED | FAILED
    """

    PENDING = "pending"
    """Tile is in DOM but not yet visible in viewport."""

    VISIBLE = "visible"
    """Tile has entered viewport, ready for load."""

    LOADING = "loading"
    """Tile content is being fetched."""

    LOADED = "loaded"
    """Tile content successfully loaded."""

    FAILED = "failed"
    """Tile content failed to load."""

    PLACEHOLDER = "placeholder"
    """Tile is showing placeholder content."""


# ---------------------------------------------------------------------------
# Content Trust Signal
# ---------------------------------------------------------------------------


class ContentTrustSignal:
    """
    Trust signal labels for content classification.

    ALLOWED_LABELS: Safe to display in UI without human review.
    BLOCKED_LABELS: Protected decision classes that cannot appear in UI
                    without human review (aligned with VerificationGapGuard).

    WSP 97: UI must NEVER display BLOCKED_LABELS as automated decisions.
    """

    # Labels safe for automated display
    ALLOWED_LABELS: frozenset[str] = frozenset({
        "verified",
        "pending_review",
        "community_flagged",
        "new_submission",
        "popular",
        "trending",
        "featured",
        "recommended",
        "recently_updated",
        "staff_pick",
    })

    # Protected decision class labels - NEVER display as automated
    # Aligned with VerificationGapGuard protected classes
    BLOCKED_LABELS: frozenset[str] = frozenset({
        # Accusation labels
        "fraud",
        "fraudulent",
        "scam",
        "scammer",
        "deepfake",
        "fake",
        "suspicious",
        # Punishment labels
        "banned",
        "suspended",
        "blocked",
        "denied",
        "rejected",
        # Finality labels
        "confirmed_fraud",
        "payout_denied",
        "reputation_damaged",
        "trust_revoked",
    })

    @classmethod
    def is_allowed(cls, label: str) -> bool:
        """Check if a label is safe for automated display."""
        return label.lower() in cls.ALLOWED_LABELS

    @classmethod
    def is_blocked(cls, label: str) -> bool:
        """Check if a label requires human review before display."""
        normalized = label.lower()
        # Check exact match
        if normalized in cls.BLOCKED_LABELS:
            return True
        # Check substring match for compound labels
        for blocked in cls.BLOCKED_LABELS:
            if blocked in normalized:
                return True
        return False


# ---------------------------------------------------------------------------
# Content Load Policy
# ---------------------------------------------------------------------------


@dataclass
class ContentLoadPolicy:
    """
    Policy configuration for intelligent grid loading.

    WSP 97: This is a policy interface. It does NOT implement loading logic.
    """

    # Viewport thresholds
    viewport_margin_px: int = 200
    """Extra margin around viewport for pre-loading."""

    load_batch_size: int = 6
    """Number of tiles to load per batch."""

    # Timing
    debounce_ms: int = 100
    """Debounce time for scroll events."""

    retry_delay_ms: int = 1000
    """Delay before retrying failed loads."""

    max_retries: int = 2
    """Maximum retry attempts per tile."""

    # Priority
    prioritize_visible: bool = True
    """Load visible tiles before off-screen tiles."""

    prefetch_next_row: bool = True
    """Prefetch tiles in the next row."""

    # Trust filtering
    filter_blocked_labels: bool = True
    """Filter out content with blocked trust labels."""

    require_verification_for_display: bool = False
    """Require verification before displaying content."""

    def to_dict(self) -> dict:
        """Serialize to dictionary for JS interop."""
        return {
            "viewportMarginPx": self.viewport_margin_px,
            "loadBatchSize": self.load_batch_size,
            "debounceMs": self.debounce_ms,
            "retryDelayMs": self.retry_delay_ms,
            "maxRetries": self.max_retries,
            "prioritizeVisible": self.prioritize_visible,
            "prefetchNextRow": self.prefetch_next_row,
            "filterBlockedLabels": self.filter_blocked_labels,
            "requireVerificationForDisplay": self.require_verification_for_display,
        }


# ---------------------------------------------------------------------------
# Tile Load Context (for future implementation)
# ---------------------------------------------------------------------------


@dataclass
class TileLoadContext:
    """
    Context for a tile load operation.

    WSP 97: Interface stub only. Does not execute loads.
    """

    tile_id: str
    foundup_id: str
    state: TileLoadState = TileLoadState.PENDING
    trust_labels: List[str] = field(default_factory=list)
    retry_count: int = 0
    error_message: Optional[str] = None

    def has_blocked_label(self) -> bool:
        """Check if any trust label is blocked."""
        return any(ContentTrustSignal.is_blocked(label) for label in self.trust_labels)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "tileId": self.tile_id,
            "foundupId": self.foundup_id,
            "state": self.state.value,
            "trustLabels": self.trust_labels,
            "retryCount": self.retry_count,
            "errorMessage": self.error_message,
            "hasBlockedLabel": self.has_blocked_label(),
        }
