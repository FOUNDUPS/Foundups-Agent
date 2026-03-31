#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
p.fMALL API Adapter — thin read-only surface over shell core.

Provides stable dict-based access to the p.fMALL catalog, tile details,
and route resolution. All operations are read-only. Shell core remains
the underlying authority.

Usage:
    from modules.foundups.pfmall.api import get_default_shell, list_foundups, get_foundup

    shell = get_default_shell()
    catalog = list_foundups()
    tile = get_foundup("gotjunk_001")
    route = resolve_foundup_route("/f/gotjunk_001/listings")
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.foundups.pfmall.shell_core import (
    PfmallShell,
    create_pfmall_shell,
)

logger = logging.getLogger("pfmall_api")


# ---------------------------------------------------------------------------
# Default Search Paths (matches seeded manifest cohort)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]  # modules/foundups/pfmall -> repo root

DEFAULT_SEARCH_PATHS = [
    _REPO_ROOT / "modules" / "foundups",
    _REPO_ROOT / "modules" / "gamification",
    _REPO_ROOT / "modules" / "platform_integration",
]

_default_shell: Optional[PfmallShell] = None


# ---------------------------------------------------------------------------
# Default Shell
# ---------------------------------------------------------------------------

def get_default_shell() -> PfmallShell:
    """Return a booted PfmallShell with standard search paths.

    Boots once on first call, subsequent calls return the same instance.
    Safe for internal callers. No global side effects beyond caching
    the shell instance and bootstrapping catalog state.
    """
    global _default_shell
    if _default_shell is None:
        _default_shell = create_pfmall_shell(search_paths=DEFAULT_SEARCH_PATHS)
        _default_shell.boot()
        logger.info(
            "[PFMALL-API] Default shell booted: %d entries",
            _default_shell.catalog.count,
        )
    return _default_shell


def reset_default_shell() -> None:
    """Reset the cached default shell (for testing only)."""
    global _default_shell
    _default_shell = None


# ---------------------------------------------------------------------------
# Catalog Listing
# ---------------------------------------------------------------------------

def list_foundups(
    category: Optional[str] = None,
    shell: Optional[PfmallShell] = None,
) -> List[Dict[str, Any]]:
    """List FoundUp tiles from the catalog.

    Returns overlay-enriched tiles when a state provider is configured,
    otherwise returns manifest-only tiles with unknown overlay fields.

    Args:
        category: Optional category filter (case-insensitive).
        shell: Optional shell instance. Uses default shell if None.

    Returns:
        List of tile dicts sorted by name.
    """
    sh = shell or get_default_shell()
    manifests = sh.build_catalog(category)
    tiles = []
    for m in manifests:
        tile = sh.build_foundup_tile(m.foundup_id)
        if tile is not None:
            tiles.append(tile.to_dict())
    return tiles


# ---------------------------------------------------------------------------
# Single FoundUp Lookup
# ---------------------------------------------------------------------------

def get_foundup(
    foundup_id: str,
    shell: Optional[PfmallShell] = None,
) -> Optional[Dict[str, Any]]:
    """Get a single FoundUp tile by ID.

    Returns overlay-enriched tile when a state provider is configured,
    otherwise returns manifest-only tile with unknown overlay fields.

    Args:
        foundup_id: Exact FoundUp ID.
        shell: Optional shell instance. Uses default shell if None.

    Returns:
        Tile dict or None if not found.
    """
    sh = shell or get_default_shell()
    tile = sh.build_foundup_tile(foundup_id)
    return tile.to_dict() if tile is not None else None


# ---------------------------------------------------------------------------
# Route Resolution
# ---------------------------------------------------------------------------

def resolve_foundup_route(
    path: str,
    shell: Optional[PfmallShell] = None,
) -> Dict[str, Any]:
    """Resolve a URL path through the shell router.

    Args:
        path: URL path to resolve (e.g. "/f/gotjunk_001/listings").
        shell: Optional shell instance. Uses default shell if None.

    Returns:
        Route target dict with 'kind', 'path', and optional
        'foundup_id', 'foundup_path', or 'error' fields.
    """
    sh = shell or get_default_shell()
    target = sh.resolve_route(path)
    return target.to_dict()
