#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
p.fMALL Catalog Integration for OpenClaw

Provides manifest discovery, state overlay consumption, and catalog
operations for the FOUNDUP intent route.

Architecture:
  - Consumes static manifests from foundup_manifest.json files
  - Consumes dynamic state via StateOverlayProvider interface
  - Degrades gracefully when overlay unavailable

WSP Compliance:
  WSP 11  : Interface contract (provider abstraction)
  WSP 72  : Module independence (no simulator internals)
  WSP 84  : Code Reuse (reuses manifest schema)

Contract References:
  - PFMALL_FOUNDUP_MANIFEST_SCHEMA.md (static contract)
  - PFMALL_STATE_OVERLAY_CONTRACT.md (dynamic contract)
  - PFMALL_ROUTING_DISCOVERY_MODEL.md (routing targets)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger("pfmall_catalog")


# ---------------------------------------------------------------------------
# State Overlay Provider Protocol (per PFMALL_STATE_OVERLAY_CONTRACT.md)
# ---------------------------------------------------------------------------

@dataclass
class FoundUpStateOverlay:
    """Dynamic state overlay for a FoundUp.

    Per PFMALL_STATE_OVERLAY_CONTRACT.md Section 3.
    """

    foundup_id: str
    health_status: str = "unknown"  # healthy | degraded | offline | unknown
    availability: str = "unknown"   # online | maintenance | suspended
    cabr_score: float = 0.0
    cabr_trend: str = "unknown"     # rising | stable | falling | unknown
    lifecycle_progress: Dict[str, Any] = field(default_factory=dict)
    agent_activity: Dict[str, Any] = field(default_factory=dict)
    reserve_summary: Dict[str, Any] = field(default_factory=dict)
    last_updated_at: str = ""
    state_provider: str = "none"
    freshness_ttl: int = 0


class StateOverlayProvider(Protocol):
    """Abstract state overlay provider per PFMALL_STATE_OVERLAY_CONTRACT.md."""

    def get_foundup_state(self, foundup_id: str) -> Optional[FoundUpStateOverlay]:
        """Get current state for one FoundUp."""
        ...

    def list_foundup_states(self) -> List[FoundUpStateOverlay]:
        """Get current state for all known FoundUps."""
        ...

    def get_state_freshness(self, foundup_id: str) -> Optional[int]:
        """Get seconds until state is considered stale."""
        ...

    @property
    def provider_id(self) -> str:
        """Unique identifier for this provider."""
        ...


# ---------------------------------------------------------------------------
# Manifest Entry (subset of full manifest for catalog display)
# ---------------------------------------------------------------------------

@dataclass
class CatalogEntry:
    """Catalog entry for a FoundUp (display subset of manifest).

    Per PFMALL_ROUTING_DISCOVERY_MODEL.md Section 3.1.
    """

    foundup_id: str
    name: str
    tagline: str = ""
    description: str = ""
    category: str = "uncategorized"
    tier: str = "F0_DAE"
    lifecycle_stage: str = "incubating"
    required_subscription_tier: str = "free"
    is_invite_only: bool = True
    icon_url: str = ""
    entry_url: str = ""
    routing_prefix: str = ""
    token_symbol: str = ""
    owner_id: str = ""


# ---------------------------------------------------------------------------
# Known FoundUps Registry (PoC - until real manifests exist)
# ---------------------------------------------------------------------------

# Per PFMALL_LAUNCH_CATALOG_TAXONOMY.md - known FoundUp modules
_KNOWN_FOUNDUPS: List[CatalogEntry] = [
    CatalogEntry(
        foundup_id="gotjunk_001",
        name="GotJunk",
        tagline="Turn your junk into someone's treasure",
        description="Peer-to-peer marketplace for selling unwanted items",
        category="marketplace",
        tier="F0_DAE",
        lifecycle_stage="proto",
        required_subscription_tier="free",
        is_invite_only=True,
        token_symbol="JUNK",
        owner_id="012",
        routing_prefix="/f/gotjunk_001",
    ),
    CatalogEntry(
        foundup_id="social_twin_001",
        name="Social Twin",
        tagline="Your AI-powered social presence",
        description="Autonomous social engagement across platforms",
        category="media",
        tier="F0_DAE",
        lifecycle_stage="incubating",
        required_subscription_tier="starter",
        is_invite_only=True,
        token_symbol="TWIN",
        owner_id="012",
        routing_prefix="/f/social_twin_001",
    ),
    CatalogEntry(
        foundup_id="pqn_swarm_hub_001",
        name="PQN Swarm Hub",
        tagline="Distributed science research coordination",
        description="Research coordination for PQN experiments",
        category="science",
        tier="F0_DAE",
        lifecycle_stage="incubating",
        required_subscription_tier="pro",
        is_invite_only=True,
        token_symbol="PQN",
        owner_id="012",
        routing_prefix="/f/pqn_swarm_hub_001",
    ),
    CatalogEntry(
        foundup_id="move2japan_001",
        name="Move2Japan",
        tagline="Your guide to relocating to Japan",
        description="Resources and community for Japan relocation",
        category="community",
        tier="F0_DAE",
        lifecycle_stage="proto",
        required_subscription_tier="free",
        is_invite_only=True,
        token_symbol="M2J",
        owner_id="012",
        routing_prefix="/f/move2japan_001",
    ),
    CatalogEntry(
        foundup_id="antifafm_001",
        name="antifaFM",
        tagline="24/7 resistance radio",
        description="Headless broadcaster with visual layers",
        category="media",
        tier="F0_DAE",
        lifecycle_stage="incubating",
        required_subscription_tier="starter",
        is_invite_only=True,
        token_symbol="ANTI",
        owner_id="012",
        routing_prefix="/f/antifafm_001",
    ),
    CatalogEntry(
        foundup_id="magadoom_001",
        name="MAGADOOM",
        tagline="Gamified moderation for live streams",
        description="Whack-a-MAGAT gamification engine",
        category="games",
        tier="F0_DAE",
        lifecycle_stage="proto",
        required_subscription_tier="free",
        is_invite_only=True,
        token_symbol="DOOM",
        owner_id="012",
        routing_prefix="/f/magadoom_001",
    ),
]


# ---------------------------------------------------------------------------
# Catalog Manager
# ---------------------------------------------------------------------------

class PfmallCatalogManager:
    """
    p.fMALL catalog manager for OpenClaw.

    Provides catalog operations without importing simulator internals.
    State overlay is consumed via provider interface with graceful degradation.
    """

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        state_provider: Optional[StateOverlayProvider] = None,
    ):
        """Initialize catalog manager.

        Args:
            repo_root: Repository root for manifest discovery
            state_provider: Optional state overlay provider (degrades if None)
        """
        self._repo_root = repo_root or Path("O:/Foundups-Agent")
        self._state_provider = state_provider
        self._manifest_cache: Dict[str, CatalogEntry] = {}
        self._cache_loaded = False

    def _load_manifests(self) -> None:
        """Load manifests from known locations and registry."""
        if self._cache_loaded:
            return

        # Start with known FoundUps registry (PoC)
        for entry in _KNOWN_FOUNDUPS:
            self._manifest_cache[entry.foundup_id] = entry
            # Also index by name (lowercase, normalized)
            name_key = entry.name.lower().replace(" ", "_").replace("-", "_")
            self._manifest_cache[name_key] = entry

        # Try to load real manifests if they exist
        foundups_dir = self._repo_root / "modules" / "foundups"
        if foundups_dir.exists():
            for subdir in foundups_dir.iterdir():
                if not subdir.is_dir():
                    continue
                manifest_path = subdir / "foundup_manifest.json"
                if manifest_path.exists():
                    try:
                        entry = self._load_manifest_file(manifest_path)
                        if entry:
                            self._manifest_cache[entry.foundup_id] = entry
                            name_key = entry.name.lower().replace(" ", "_")
                            self._manifest_cache[name_key] = entry
                            logger.info(
                                "[PFMALL-CATALOG] Loaded manifest: %s",
                                entry.name,
                            )
                    except Exception as exc:
                        logger.warning(
                            "[PFMALL-CATALOG] Failed to load %s: %s",
                            manifest_path,
                            exc,
                        )

        self._cache_loaded = True
        # Count unique entries by foundup_id
        unique_ids = {e.foundup_id for e in self._manifest_cache.values()}
        logger.info(
            "[PFMALL-CATALOG] Catalog loaded: %d entries",
            len(unique_ids),
        )

    def _load_manifest_file(self, path: Path) -> Optional[CatalogEntry]:
        """Load a manifest JSON file into a CatalogEntry."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return CatalogEntry(
            foundup_id=data.get("foundup_id", ""),
            name=data.get("name", ""),
            tagline=data.get("tagline", ""),
            description=data.get("description", ""),
            category=data.get("category", "uncategorized"),
            tier=data.get("tier", "F0_DAE"),
            lifecycle_stage=data.get("lifecycle_stage", "incubating"),
            required_subscription_tier=data.get("required_subscription_tier", "free"),
            is_invite_only=data.get("is_invite_only", True),
            icon_url=data.get("icon_url", ""),
            entry_url=data.get("entry_url", ""),
            routing_prefix=data.get("routing_prefix", ""),
            token_symbol=data.get("token_symbol", ""),
            owner_id=data.get("owner_id", ""),
        )

    def _get_state_overlay(self, foundup_id: str) -> FoundUpStateOverlay:
        """Get state overlay for a FoundUp, degrading gracefully if unavailable."""
        if self._state_provider is None:
            return FoundUpStateOverlay(
                foundup_id=foundup_id,
                health_status="unknown",
                availability="unknown",
                state_provider="none",
                last_updated_at=datetime.now(timezone.utc).isoformat(),
            )

        try:
            overlay = self._state_provider.get_foundup_state(foundup_id)
            if overlay:
                return overlay
        except Exception as exc:
            logger.warning(
                "[PFMALL-CATALOG] State provider error for %s: %s",
                foundup_id,
                exc,
            )

        return FoundUpStateOverlay(
            foundup_id=foundup_id,
            health_status="unknown",
            availability="unknown",
            state_provider="error",
            last_updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def list_foundups(self) -> List[CatalogEntry]:
        """List all available FoundUps."""
        self._load_manifests()
        # Return unique entries (dedupe by foundup_id)
        seen = set()
        result = []
        for entry in self._manifest_cache.values():
            if entry.foundup_id not in seen:
                seen.add(entry.foundup_id)
                result.append(entry)
        return sorted(result, key=lambda e: e.name)

    def get_catalog(self, category: Optional[str] = None) -> List[CatalogEntry]:
        """Get catalog entries, optionally filtered by category."""
        entries = self.list_foundups()
        if category:
            category_lower = category.lower()
            entries = [e for e in entries if e.category.lower() == category_lower]
        return entries

    def get_foundup(self, name_or_id: str) -> Optional[CatalogEntry]:
        """Get a FoundUp by name or ID."""
        self._load_manifests()
        # Try exact match first
        if name_or_id in self._manifest_cache:
            return self._manifest_cache[name_or_id]
        # Try normalized name
        normalized = name_or_id.lower().replace(" ", "_").replace("-", "_")
        if normalized in self._manifest_cache:
            return self._manifest_cache[normalized]
        # Try partial match
        for key, entry in self._manifest_cache.items():
            if normalized in key or normalized in entry.name.lower():
                return entry
        return None

    def get_status(self, name_or_id: str) -> Optional[Dict[str, Any]]:
        """Get status for a FoundUp (manifest + state overlay)."""
        entry = self.get_foundup(name_or_id)
        if not entry:
            return None

        overlay = self._get_state_overlay(entry.foundup_id)

        return {
            "foundup_id": entry.foundup_id,
            "name": entry.name,
            "tagline": entry.tagline,
            "tier": entry.tier,
            "lifecycle_stage": entry.lifecycle_stage,
            "category": entry.category,
            "token_symbol": entry.token_symbol,
            "routing_prefix": entry.routing_prefix,
            # State overlay (advisory)
            "health_status": overlay.health_status,
            "availability": overlay.availability,
            "cabr_score": overlay.cabr_score,
            "cabr_trend": overlay.cabr_trend,
            "state_provider": overlay.state_provider,
            "state_freshness": "unavailable" if overlay.state_provider == "none" else "live",
        }

    def get_open_target(self, name_or_id: str) -> Optional[str]:
        """Get the routing target URL for a FoundUp."""
        entry = self.get_foundup(name_or_id)
        if not entry:
            return None
        return entry.routing_prefix or f"/f/{entry.foundup_id}"


# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------

_catalog_manager: Optional[PfmallCatalogManager] = None


def _get_catalog_manager() -> PfmallCatalogManager:
    """Get or create the catalog manager singleton."""
    global _catalog_manager
    if _catalog_manager is None:
        _catalog_manager = PfmallCatalogManager()
    return _catalog_manager


def handle_list_foundups() -> str:
    """Handle 'list foundups' command."""
    manager = _get_catalog_manager()
    entries = manager.list_foundups()

    if not entries:
        return "No FoundUps available in catalog."

    lines = ["**p.fMALL Catalog**\n"]
    for entry in entries:
        stage_badge = f"[{entry.lifecycle_stage}]"
        tier_badge = f"({entry.tier})"
        invite_badge = " [Angel]" if entry.is_invite_only else ""
        lines.append(
            f"- **{entry.name}** {stage_badge} {tier_badge}{invite_badge}"
        )
        lines.append(f"  {entry.tagline}")

    lines.append(f"\nTotal: {len(entries)} FoundUps")
    return "\n".join(lines)


def handle_foundup_catalog(category: Optional[str] = None) -> str:
    """Handle 'foundup catalog' command."""
    manager = _get_catalog_manager()
    entries = manager.get_catalog(category)

    if not entries:
        if category:
            return f"No FoundUps in category '{category}'."
        return "No FoundUps available in catalog."

    # Group by category
    by_category: Dict[str, List[CatalogEntry]] = {}
    for entry in entries:
        cat = entry.category or "uncategorized"
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(entry)

    lines = ["**p.fMALL Catalog**\n"]
    for cat, cat_entries in sorted(by_category.items()):
        lines.append(f"### {cat.title()}")
        for entry in cat_entries:
            stage = entry.lifecycle_stage
            lines.append(f"- **{entry.name}** [{stage}] - {entry.tagline}")
        lines.append("")

    lines.append(f"Total: {len(entries)} FoundUps")
    return "\n".join(lines)


def handle_foundup_status(name_or_id: str) -> str:
    """Handle 'foundup status <name>' command."""
    manager = _get_catalog_manager()
    status = manager.get_status(name_or_id)

    if not status:
        return f"FoundUp '{name_or_id}' not found in catalog."

    health = status["health_status"]
    health_badge = {
        "healthy": "[OK]",
        "degraded": "[WARN]",
        "offline": "[DOWN]",
        "unknown": "[?]",
    }.get(health, "[?]")

    lines = [
        f"**{status['name']}** {health_badge}",
        f"  ID: `{status['foundup_id']}`",
        f"  Tier: {status['tier']} | Stage: {status['lifecycle_stage']}",
        f"  Category: {status['category']}",
        f"  Token: {status['token_symbol']}",
        "",
        "**Status** (advisory)",
        f"  Health: {status['health_status']}",
        f"  Availability: {status['availability']}",
        f"  CABR Score: {status['cabr_score']:.2f} ({status['cabr_trend']})",
        f"  State Provider: {status['state_provider']}",
        f"  Freshness: {status['state_freshness']}",
        "",
        f"**Route**: `{status['routing_prefix']}`",
    ]
    return "\n".join(lines)


def handle_open_foundup(name_or_id: str) -> str:
    """Handle 'open <foundup>' command."""
    manager = _get_catalog_manager()
    target = manager.get_open_target(name_or_id)

    if not target:
        return f"FoundUp '{name_or_id}' not found in catalog."

    entry = manager.get_foundup(name_or_id)
    name = entry.name if entry else name_or_id

    return (
        f"**Open {name}**\n"
        f"Route: `{target}`\n"
        f"\n"
        f"In p.fMALL shell: Navigate to `{target}`\n"
        f"Direct URL: `https://foundups.com{target}`"
    )


def parse_catalog_command(message: str) -> Optional[str]:
    """Parse catalog commands from a message.

    Supported commands:
      - list foundups
      - foundup catalog [category]
      - foundup status <name>
      - open <foundup>

    Returns response string or None if not a catalog command.
    """
    msg = message.strip().lower()

    # list foundups
    if msg in ("list foundups", "list foundup", "foundups", "show foundups"):
        return handle_list_foundups()

    # foundup catalog [category]
    if msg.startswith("foundup catalog") or msg.startswith("catalog"):
        parts = msg.split()
        category = None
        if len(parts) > 2:
            category = parts[2]
        elif len(parts) > 1 and parts[0] == "catalog":
            category = parts[1] if parts[1] not in ("foundup", "foundups") else None
        return handle_foundup_catalog(category)

    # foundup status <name>
    if msg.startswith("foundup status") or msg.startswith("status foundup"):
        parts = message.strip().split(maxsplit=2)
        if len(parts) >= 3:
            name = parts[2]
            return handle_foundup_status(name)
        return "Usage: `foundup status <name>`"

    # open <foundup>
    if msg.startswith("open "):
        parts = message.strip().split(maxsplit=1)
        if len(parts) >= 2:
            name = parts[1]
            # Skip if it's "open foundup" without a name
            if name.lower() not in ("foundup", "foundups"):
                return handle_open_foundup(name)
        return "Usage: `open <foundup-name>`"

    return None
