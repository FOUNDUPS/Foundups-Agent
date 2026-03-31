"""
p.fMALL Shell Core — manifest discovery, catalog, routing, overlay merge.

Public API:
    create_pfmall_shell(search_paths, state_provider) -> PfmallShell
    load_manifest(source) -> FoundUpManifest | None
    validate_manifest(data) -> list[str]
    discover_manifests(search_paths) -> list[Path]
    resolve_route(path, catalog) -> RouteTarget
    build_foundup_tile(manifest, overlay) -> FoundUpTile
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

__all__ = [
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
]
