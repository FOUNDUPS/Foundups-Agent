#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
p.fMALL Shell Core Scaffold

Minimal shell runtime providing manifest discovery, catalog assembly,
route resolution, and manifest+overlay merge. Non-UI scaffold only.

Architecture:
  - Discovers FoundUps from foundup_manifest.json files
  - Builds a bounded launch catalog from validated manifests
  - Resolves shell routes to tenant entries (Phase 1: no module federation)
  - Merges static manifest with optional dynamic overlay
  - Consumes overlay only through StateOverlayProvider boundary

WSP Compliance:
  WSP 11  : Interface contract (typed shell API)
  WSP 72  : Module independence (no simulator internals)
  WSP 84  : Code Reuse (overlay provider protocol)

Contract References:
  - PFMALL_SHELL_CONTRACT.md (shell responsibilities)
  - PFMALL_FOUNDUP_MANIFEST_SCHEMA.md (manifest schema)
  - PFMALL_ROUTING_DISCOVERY_MODEL.md (routing model)
  - PFMALL_STATE_OVERLAY_CONTRACT.md (overlay contract)
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Union

logger = logging.getLogger("pfmall_shell")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_TIERS = frozenset({
    "F0_DAE", "F1_OPO", "F2_GROWTH", "F3_INFRA", "F4_MEGA", "F5_SYSTEMIC",
})

VALID_STAGES = frozenset({
    # Simulator stages
    "idea", "poc", "soft-proto", "proto", "mvp", "launch",
    # Exfoliation protocol stages (per PFMALL_FOUNDUP_MANIFEST_SCHEMA.md)
    "incubating", "externalized", "federated",
})

VALID_READINESS = frozenset({
    "ready",              # Frontend exists, tests pass, can be loaded in shell
    "conditional",        # Frontend exists but has known gaps
    "discoverable_only",  # No frontend, catalog info card only
})

SHELL_ROUTES = frozenset({
    "/", "/discover", "/wallet", "/search", "/settings", "/auth/callback",
})

REQUIRED_MANIFEST_FIELDS = frozenset({
    "foundup_id", "name", "version", "tier", "lifecycle_stage",
})


class RouteKind(Enum):
    """Route resolution result types."""
    SHELL = "shell"
    FOUNDUP = "foundup"
    NOT_FOUND = "not_found"


# ---------------------------------------------------------------------------
# State Overlay Types (per PFMALL_STATE_OVERLAY_CONTRACT.md)
# ---------------------------------------------------------------------------

@dataclass
class FoundUpStateOverlay:
    """Dynamic state overlay for a FoundUp.

    Defined locally to avoid cross-domain import. Schema matches
    PFMALL_STATE_OVERLAY_CONTRACT.md Section 3.
    """

    foundup_id: str
    health_status: str = "unknown"
    availability: str = "unknown"
    cabr_score: float = 0.0
    cabr_trend: str = "unknown"
    lifecycle_progress: Dict[str, Any] = field(default_factory=dict)
    agent_activity: Dict[str, Any] = field(default_factory=dict)
    reserve_summary: Dict[str, Any] = field(default_factory=dict)
    last_updated_at: str = ""
    state_provider: str = "none"
    freshness_ttl: int = 0


class StateOverlayProvider(Protocol):
    """Abstract state overlay provider."""

    def get_foundup_state(self, foundup_id: str) -> Optional[FoundUpStateOverlay]:
        ...

    def list_foundup_states(self) -> List[FoundUpStateOverlay]:
        ...

    def get_state_freshness(self, foundup_id: str) -> Optional[int]:
        ...

    @property
    def provider_id(self) -> str:
        ...


# ---------------------------------------------------------------------------
# FoundUp Manifest (per PFMALL_FOUNDUP_MANIFEST_SCHEMA.md)
# ---------------------------------------------------------------------------

@dataclass
class FoundUpManifest:
    """Static manifest for a FoundUp.

    All 26 fields per PFMALL_FOUNDUP_MANIFEST_SCHEMA.md.
    Manifest is authoritative — overlay never overrides these.
    """

    foundup_id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    tagline: str = ""
    icon_url: str = ""
    tier: str = "F0_DAE"
    lifecycle_stage: str = "incubating"
    entry_url: str = ""
    routing_prefix: str = ""
    required_subscription_tier: str = "free"
    capabilities: List[str] = field(default_factory=list)
    agent_routes: List[Dict[str, Any]] = field(default_factory=list)
    cabr_contract: Dict[str, Any] = field(default_factory=dict)
    owner_id: str = ""
    token_symbol: str = ""
    data_namespace: str = ""
    holo_collections: List[str] = field(default_factory=list)
    category: str = "uncategorized"
    is_invite_only: bool = True
    launch_readiness: str = "discoverable_only"
    signature: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic dict serialization of manifest fields."""
        return {
            "foundup_id": self.foundup_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tagline": self.tagline,
            "icon_url": self.icon_url,
            "tier": self.tier,
            "lifecycle_stage": self.lifecycle_stage,
            "entry_url": self.entry_url,
            "routing_prefix": self.routing_prefix,
            "required_subscription_tier": self.required_subscription_tier,
            "capabilities": list(self.capabilities),
            "agent_routes": list(self.agent_routes),
            "cabr_contract": dict(self.cabr_contract),
            "owner_id": self.owner_id,
            "token_symbol": self.token_symbol,
            "data_namespace": self.data_namespace,
            "holo_collections": list(self.holo_collections),
            "category": self.category,
            "is_invite_only": self.is_invite_only,
            "launch_readiness": self.launch_readiness,
            "signature": self.signature,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ---------------------------------------------------------------------------
# FoundUp Tile (merged view model)
# ---------------------------------------------------------------------------

@dataclass
class FoundUpTile:
    """Merged view model: manifest (authoritative) + overlay (advisory).

    Shell UI would render tiles. Overlay fields are advisory badges only —
    they never override manifest authority.
    """

    # Manifest (authoritative)
    foundup_id: str
    name: str
    tagline: str = ""
    description: str = ""
    category: str = "uncategorized"
    tier: str = "F0_DAE"
    lifecycle_stage: str = "incubating"
    routing_prefix: str = ""
    token_symbol: str = ""
    is_invite_only: bool = True
    icon_url: str = ""
    launch_readiness: str = "discoverable_only"

    # Overlay (advisory)
    health_status: str = "unknown"
    availability: str = "unknown"
    cabr_score: float = 0.0
    cabr_trend: str = "unknown"
    active_agents: int = 0
    tasks_in_flight: int = 0
    reserve_health: str = "unknown"
    state_provider: str = "none"
    freshness_ttl: int = 0
    last_updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic dict serialization of tile fields."""
        return {
            "foundup_id": self.foundup_id,
            "name": self.name,
            "tagline": self.tagline,
            "description": self.description,
            "category": self.category,
            "tier": self.tier,
            "lifecycle_stage": self.lifecycle_stage,
            "routing_prefix": self.routing_prefix,
            "token_symbol": self.token_symbol,
            "is_invite_only": self.is_invite_only,
            "icon_url": self.icon_url,
            "launch_readiness": self.launch_readiness,
            "health_status": self.health_status,
            "availability": self.availability,
            "cabr_score": self.cabr_score,
            "cabr_trend": self.cabr_trend,
            "active_agents": self.active_agents,
            "tasks_in_flight": self.tasks_in_flight,
            "reserve_health": self.reserve_health,
            "state_provider": self.state_provider,
            "freshness_ttl": self.freshness_ttl,
            "last_updated_at": self.last_updated_at,
        }


# ---------------------------------------------------------------------------
# Route Target
# ---------------------------------------------------------------------------

@dataclass
class RouteTarget:
    """Result of route resolution."""

    kind: RouteKind
    path: str = ""
    foundup_id: str = ""
    foundup_path: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic dict serialization of route target."""
        d: Dict[str, Any] = {
            "kind": self.kind.value,
            "path": self.path,
        }
        if self.foundup_id:
            d["foundup_id"] = self.foundup_id
        if self.foundup_path:
            d["foundup_path"] = self.foundup_path
        if self.error:
            d["error"] = self.error
        return d


# ---------------------------------------------------------------------------
# Shell Config
# ---------------------------------------------------------------------------

@dataclass
class ShellConfig:
    """Shell bootstrap configuration."""

    search_paths: List[Path] = field(default_factory=list)
    state_provider: Optional[Any] = None
    default_route: str = "/discover"


# ---------------------------------------------------------------------------
# Manifest Discovery & Validation
# ---------------------------------------------------------------------------

def discover_manifests(search_paths: List[Path]) -> List[Path]:
    """Discover foundup_manifest.json files under search paths.

    Scans one level deep in each search path for subdirectories
    containing a foundup_manifest.json file.

    Returns:
        Sorted list of discovered manifest paths.
    """
    result = []
    for base in search_paths:
        if not base.is_dir():
            continue
        for subdir in sorted(base.iterdir()):
            if not subdir.is_dir():
                continue
            manifest_path = subdir / "foundup_manifest.json"
            if manifest_path.is_file():
                result.append(manifest_path)
    return result


def validate_manifest(data: dict) -> List[str]:
    """Validate manifest data against schema rules.

    Returns:
        List of error strings. Empty list means valid.
    """
    errors = []

    # Required fields
    for fname in REQUIRED_MANIFEST_FIELDS:
        val = data.get(fname)
        if not val:
            errors.append(f"missing required field: {fname}")
        elif not isinstance(val, str):
            errors.append(f"{fname} must be a string")

    # Tier enum
    tier = data.get("tier", "")
    if tier and tier not in VALID_TIERS:
        errors.append(f"invalid tier: {tier}")

    # Lifecycle stage enum (case-insensitive)
    stage = data.get("lifecycle_stage", "")
    if stage and stage.lower() not in VALID_STAGES:
        errors.append(f"invalid lifecycle_stage: {stage}")

    # ID minimum length
    fid = data.get("foundup_id", "")
    if isinstance(fid, str) and fid and len(fid) < 3:
        errors.append("foundup_id too short (minimum 3 characters)")

    # Launch readiness (optional, validated if present)
    readiness = data.get("launch_readiness", "")
    if readiness and readiness not in VALID_READINESS:
        errors.append(f"invalid launch_readiness: {readiness}")

    return errors


def load_manifest(source: Union[Path, dict]) -> Optional[FoundUpManifest]:
    """Load and validate a manifest from a file path or dict.

    Returns None if source is unreadable or manifest is invalid.
    """
    if isinstance(source, Path):
        try:
            with open(source, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("[PFMALL-SHELL] Failed to read manifest %s: %s", source, exc)
            return None
    elif isinstance(source, dict):
        data = source
    else:
        return None

    errors = validate_manifest(data)
    if errors:
        logger.warning("[PFMALL-SHELL] Invalid manifest %s: %s", source, errors)
        return None

    return FoundUpManifest(
        foundup_id=data["foundup_id"],
        name=data["name"],
        version=data.get("version", "0.1.0"),
        description=data.get("description", ""),
        tagline=data.get("tagline", ""),
        icon_url=data.get("icon_url", ""),
        tier=data.get("tier", "F0_DAE"),
        lifecycle_stage=data.get("lifecycle_stage", "incubating"),
        entry_url=data.get("entry_url", ""),
        routing_prefix=data.get("routing_prefix", ""),
        required_subscription_tier=data.get("required_subscription_tier", "free"),
        capabilities=data.get("capabilities", []),
        agent_routes=data.get("agent_routes", []),
        cabr_contract=data.get("cabr_contract", {}),
        owner_id=data.get("owner_id", ""),
        token_symbol=data.get("token_symbol", ""),
        data_namespace=data.get("data_namespace", ""),
        holo_collections=data.get("holo_collections", []),
        category=data.get("category", "uncategorized"),
        is_invite_only=data.get("is_invite_only", True),
        launch_readiness=data.get("launch_readiness", "discoverable_only"),
        signature=data.get("signature", ""),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
    )


# ---------------------------------------------------------------------------
# Shell Catalog
# ---------------------------------------------------------------------------

class ShellCatalog:
    """Registry of discovered FoundUp manifests.

    Indexed by foundup_id. Provides lookup, search, and filtered listing.
    """

    def __init__(self):
        self._entries: Dict[str, FoundUpManifest] = {}

    def register(self, manifest: FoundUpManifest) -> None:
        """Register a manifest in the catalog."""
        self._entries[manifest.foundup_id] = manifest

    def get(self, foundup_id: str) -> Optional[FoundUpManifest]:
        """Get manifest by exact foundup_id."""
        return self._entries.get(foundup_id)

    def find(self, name_or_id: str) -> Optional[FoundUpManifest]:
        """Find manifest by ID or name (case-insensitive)."""
        if name_or_id in self._entries:
            return self._entries[name_or_id]
        needle = name_or_id.lower()
        for manifest in self._entries.values():
            if manifest.name.lower() == needle:
                return manifest
        return None

    def list_entries(self, category: Optional[str] = None) -> List[FoundUpManifest]:
        """List manifests, optionally filtered by category."""
        entries = list(self._entries.values())
        if category:
            cat_lower = category.lower()
            entries = [e for e in entries if e.category.lower() == cat_lower]
        return sorted(entries, key=lambda e: e.name)

    @property
    def count(self) -> int:
        """Number of registered manifests."""
        return len(self._entries)

    @property
    def foundup_ids(self) -> List[str]:
        """All registered FoundUp IDs."""
        return list(self._entries.keys())


# ---------------------------------------------------------------------------
# Route Resolution
# ---------------------------------------------------------------------------

def resolve_route(path: str, catalog: ShellCatalog) -> RouteTarget:
    """Resolve a URL path to a route target.

    Priority per PFMALL_ROUTING_DISCOVERY_MODEL.md:
      1. Shell routes (/, /discover, /wallet, /search, /settings, /auth/callback)
      2. FoundUp routes (/f/{foundup_id}, /f/{foundup_id}/{path})
      3. Not found (fallback)

    Args:
        path: URL path to resolve.
        catalog: Shell catalog for FoundUp lookup.

    Returns:
        RouteTarget with kind, path, and optional FoundUp details.
    """
    clean = path.rstrip("/") or "/"

    # Shell routes
    if clean in SHELL_ROUTES:
        return RouteTarget(kind=RouteKind.SHELL, path=clean)

    # FoundUp routes: /f/{foundup_id} or /f/{foundup_id}/{path}
    if clean.startswith("/f/"):
        remainder = clean[3:]
        if not remainder:
            return RouteTarget(
                kind=RouteKind.NOT_FOUND,
                path=clean,
                error="missing foundup_id in route",
            )

        parts = remainder.split("/", 1)
        foundup_id = parts[0]
        foundup_path = "/" + parts[1] if len(parts) > 1 else "/"

        manifest = catalog.get(foundup_id)
        if manifest is None:
            return RouteTarget(
                kind=RouteKind.NOT_FOUND,
                path=clean,
                error=f"unknown FoundUp: {foundup_id}",
            )

        return RouteTarget(
            kind=RouteKind.FOUNDUP,
            path=clean,
            foundup_id=foundup_id,
            foundup_path=foundup_path,
        )

    # Fallback
    return RouteTarget(
        kind=RouteKind.NOT_FOUND,
        path=clean,
        error="no matching route",
    )


# ---------------------------------------------------------------------------
# Tile Builder (Manifest + Overlay Merge)
# ---------------------------------------------------------------------------

def build_foundup_tile(
    manifest: FoundUpManifest,
    overlay: Optional[FoundUpStateOverlay] = None,
) -> FoundUpTile:
    """Merge manifest (authoritative) with overlay (advisory) into a tile.

    Manifest fields are always authoritative. Overlay fields are advisory
    badges only — they never override manifest data.

    Args:
        manifest: Static manifest (required).
        overlay: Dynamic overlay (optional, graceful degradation if None).

    Returns:
        Merged FoundUpTile for shell display.
    """
    tile = FoundUpTile(
        foundup_id=manifest.foundup_id,
        name=manifest.name,
        tagline=manifest.tagline,
        description=manifest.description,
        category=manifest.category,
        tier=manifest.tier,
        lifecycle_stage=manifest.lifecycle_stage,
        routing_prefix=manifest.routing_prefix or f"/f/{manifest.foundup_id}",
        token_symbol=manifest.token_symbol,
        is_invite_only=manifest.is_invite_only,
        icon_url=manifest.icon_url,
        launch_readiness=manifest.launch_readiness,
    )

    if overlay is not None:
        tile.health_status = overlay.health_status
        tile.availability = overlay.availability
        tile.cabr_score = overlay.cabr_score
        tile.cabr_trend = overlay.cabr_trend
        tile.active_agents = overlay.agent_activity.get("active_agents", 0)
        tile.tasks_in_flight = overlay.agent_activity.get("tasks_in_flight", 0)
        tile.reserve_health = overlay.reserve_summary.get("reserve_health", "unknown")
        tile.state_provider = overlay.state_provider
        tile.freshness_ttl = overlay.freshness_ttl
        tile.last_updated_at = overlay.last_updated_at

    return tile


# ---------------------------------------------------------------------------
# PfmallShell (Main Orchestrator)
# ---------------------------------------------------------------------------

class PfmallShell:
    """Minimal p.fMALL shell core.

    Orchestrates manifest discovery, catalog assembly, route resolution,
    and manifest+overlay merge. Non-UI scaffold.

    Usage:
        shell = create_pfmall_shell(search_paths=[Path("modules/foundups")])
        shell.boot()
        tile = shell.build_foundup_tile("gotjunk_001")
        target = shell.resolve_route("/f/gotjunk_001/listings")
    """

    def __init__(self, config: Optional[ShellConfig] = None):
        self._config = config or ShellConfig()
        self._catalog = ShellCatalog()
        self._state_provider = self._config.state_provider
        self._booted = False

    @property
    def catalog(self) -> ShellCatalog:
        """Access the shell catalog."""
        return self._catalog

    @property
    def state_provider(self):
        """Current state overlay provider (may be None)."""
        return self._state_provider

    @property
    def is_booted(self) -> bool:
        """Whether the shell has completed boot."""
        return self._booted

    def configure_state_provider(self, provider) -> None:
        """Set or replace the state overlay provider."""
        self._state_provider = provider
        logger.info("[PFMALL-SHELL] Provider configured: %s", getattr(provider, "provider_id", "unknown"))

    def discover_foundups(self) -> List[FoundUpManifest]:
        """Discover and load all manifests from configured search paths.

        Returns:
            List of successfully loaded manifests.
        """
        paths = discover_manifests(self._config.search_paths)
        loaded = []
        for path in paths:
            manifest = load_manifest(path)
            if manifest:
                self._catalog.register(manifest)
                loaded.append(manifest)
                logger.info("[PFMALL-SHELL] Loaded: %s (%s)", manifest.name, manifest.foundup_id)
        logger.info("[PFMALL-SHELL] Discovery complete: %d manifests", len(loaded))
        return loaded

    def register_manifest(self, manifest: FoundUpManifest) -> None:
        """Manually register a manifest (for PoC/testing)."""
        self._catalog.register(manifest)

    def build_catalog(self, category: Optional[str] = None) -> List[FoundUpManifest]:
        """Get catalog entries, optionally filtered by category."""
        return self._catalog.list_entries(category)

    def resolve_route(self, path: str) -> RouteTarget:
        """Resolve a URL path to a route target."""
        return resolve_route(path, self._catalog)

    def build_foundup_tile(self, foundup_id: str) -> Optional[FoundUpTile]:
        """Build merged tile for a FoundUp.

        Returns None if FoundUp not in catalog.
        """
        manifest = self._catalog.get(foundup_id)
        if manifest is None:
            return None
        overlay = self._get_overlay(foundup_id)
        return build_foundup_tile(manifest, overlay)

    def _get_overlay(self, foundup_id: str) -> Optional[FoundUpStateOverlay]:
        """Get state overlay with graceful degradation."""
        if self._state_provider is None:
            return None
        try:
            return self._state_provider.get_foundup_state(foundup_id)
        except Exception as exc:
            logger.warning("[PFMALL-SHELL] Provider error for %s: %s", foundup_id, exc)
            return None

    def boot(self) -> None:
        """Bootstrap the shell: discover manifests."""
        if not self._booted:
            self.discover_foundups()
            self._booted = True
            logger.info("[PFMALL-SHELL] Shell booted: %d entries", self._catalog.count)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_pfmall_shell(
    search_paths: Optional[List[Path]] = None,
    state_provider=None,
) -> PfmallShell:
    """Create a PfmallShell instance.

    Args:
        search_paths: Directories to scan for foundup_manifest.json files.
        state_provider: Optional StateOverlayProvider for live state.

    Returns:
        Configured PfmallShell (call .boot() to discover manifests).
    """
    config = ShellConfig(
        search_paths=search_paths or [],
        state_provider=state_provider,
    )
    return PfmallShell(config)
