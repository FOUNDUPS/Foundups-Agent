"""
p.fMALL Shell Core — manifest discovery, catalog, routing, overlay merge.

p.fMALL is an AI interaction space for engaging with everything — video,
documents, community, FoundUps. Video is the default catalog layer; the same
interaction paradigm (pinch, zoom, navigate) extends to any content type,
with AI mediating all engagement.

Public API (shell core):
    create_pfmall_shell(search_paths, state_provider) -> PfmallShell
    load_manifest(source) -> FoundUpManifest | None
    validate_manifest(data) -> list[str]
    discover_manifests(search_paths) -> list[Path]
    resolve_route(path, catalog) -> RouteTarget
    build_foundup_tile(manifest, overlay) -> FoundUpTile

Public API (adapter):
    get_default_shell() -> PfmallShell
    list_foundups(category) -> list[dict]
    get_foundup(foundup_id) -> dict | None
    resolve_foundup_route(path) -> dict
"""

from modules.foundups.pfmall.shell_core import (
    create_pfmall_shell,
    discover_manifests,
    load_manifest,
    validate_manifest,
    resolve_route,
    build_foundup_tile,
    FoundUpManifest,
    FoundUpTile,
    FoundUpStateOverlay,
    RouteKind,
    RouteTarget,
    ShellCatalog,
    ShellConfig,
    PfmallShell,
    VALID_READINESS,
)

from modules.foundups.pfmall.api import (
    get_default_shell,
    list_foundups,
    get_foundup,
    resolve_foundup_route,
    reset_default_shell,
    DEFAULT_SEARCH_PATHS,
)

__all__ = [
    # Shell core
    "create_pfmall_shell",
    "discover_manifests",
    "load_manifest",
    "validate_manifest",
    "resolve_route",
    "build_foundup_tile",
    "FoundUpManifest",
    "FoundUpTile",
    "FoundUpStateOverlay",
    "RouteKind",
    "RouteTarget",
    "ShellCatalog",
    "ShellConfig",
    "PfmallShell",
    "VALID_READINESS",
    # Adapter
    "get_default_shell",
    "list_foundups",
    "get_foundup",
    "resolve_foundup_route",
    "reset_default_shell",
    "DEFAULT_SEARCH_PATHS",
]
