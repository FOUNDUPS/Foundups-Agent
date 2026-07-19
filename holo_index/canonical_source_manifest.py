"""Read-only canonical source-manifest probes for baseline HoloIndex collections."""

from __future__ import annotations

import glob
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from holo_index.core.indexing_engine import (
    _discover_web_assets,
    _has_dotfile_in_relative_path,
    _navigation_source_evidence,
    _wsp_source_set,
    source_file_manifest_digest,
    source_manifest_digest,
)
from holo_index.source_scope import (
    CanonicalSourceScopeError,
    canonical_source_scope_id,
    filter_git_tracked_files,
)
from holo_index.symbol_indexer import (
    _discover_symbol_source,
    _symbol_source_manifest,
)
from holo_index.test_registry_indexer import _registry_source_manifest


class CanonicalSourceManifestError(RuntimeError):
    """A complete canonical source manifest could not be proven."""


@dataclass(frozen=True)
class CanonicalSourceManifest:
    collection_name: str
    digest: str
    source_scope_id: str


def _tracked_manifest(
    holo: Any,
    collection_name: str,
    files: Iterable[Path],
) -> CanonicalSourceManifest:
    try:
        tracked = filter_git_tracked_files(holo.project_root, files)
        digest = source_file_manifest_digest(
            tracked,
            project_root=holo.project_root,
        )
    except (CanonicalSourceScopeError, OSError) as exc:
        raise CanonicalSourceManifestError(
            f"canonical_source_manifest_unavailable:{collection_name}"
        ) from exc
    if not tracked or not digest:
        raise CanonicalSourceManifestError(
            f"canonical_source_manifest_empty:{collection_name}"
        )
    return CanonicalSourceManifest(
        collection_name=collection_name,
        digest=digest,
        source_scope_id=canonical_source_scope_id(collection_name),
    )


def _code_manifest(holo: Any) -> CanonicalSourceManifest:
    web = _discover_web_assets(holo)
    nav_manifest, nav_failed, nav_warning = _navigation_source_evidence(holo)
    if (
        nav_failed
        or nav_warning
        or web.failed_count
        or web.processed_count != web.discovered_count
        or not nav_manifest
        or not web.source_manifest_digest
        or web.source_scope_id != canonical_source_scope_id("navigation_code")
    ):
        raise CanonicalSourceManifestError(
            "canonical_source_manifest_unavailable:navigation_code"
        )
    digest = source_manifest_digest(
        {
            "navigation": sorted(holo.need_to.items()),
            "navigation_source_manifest": nav_manifest,
            "web_asset_source_manifest": web.source_manifest_digest,
        }
    )
    return CanonicalSourceManifest(
        collection_name="navigation_code",
        digest=digest,
        source_scope_id=web.source_scope_id,
    )


def _symbols_manifest(holo: Any) -> CanonicalSourceManifest:
    files, scope_id, failure = _discover_symbol_source(holo, None)
    if failure is not None or scope_id != canonical_source_scope_id(
        "navigation_symbols"
    ):
        raise CanonicalSourceManifestError(
            "canonical_source_manifest_unavailable:navigation_symbols"
        )
    digest, failure = _symbol_source_manifest(holo, files, scope_id=scope_id)
    if failure is not None or not digest:
        raise CanonicalSourceManifestError(
            "canonical_source_manifest_unavailable:navigation_symbols"
        )
    return CanonicalSourceManifest("navigation_symbols", digest, scope_id)


def _wsp_manifest(holo: Any) -> CanonicalSourceManifest:
    files, scope_id, error = _wsp_source_set(holo, None)
    if error or scope_id != canonical_source_scope_id("navigation_wsp"):
        raise CanonicalSourceManifestError(
            "canonical_source_manifest_unavailable:navigation_wsp"
        )
    result = _tracked_manifest(holo, "navigation_wsp", files)
    return CanonicalSourceManifest(result.collection_name, result.digest, scope_id)


def _docs_source_files(holo: Any) -> list[Path]:
    """Return the exact tracked source set consumed by the docs indexer."""

    bases = (
        holo.project_root / "modules",
        holo.project_root / "docs",
        holo.project_root / "holo_index" / "docs",
        holo.project_root / "WSP_framework" / "docs",
    )
    files: list[Path] = []
    for base in bases:
        if not base.exists():
            continue
        files.extend(
            file_path
            for file_path in sorted(base.rglob("*.md"))
            if "node_modules" not in str(file_path)
            and "CHANGELOG" not in file_path.name.upper()
            and "package-lock" not in file_path.name.lower()
            and not _has_dotfile_in_relative_path(file_path, base)
            and "_backup" not in str(file_path).lower()
            and "/archive/" not in file_path.as_posix().lower()
        )
    return filter_git_tracked_files(holo.project_root, files)


def _knowledge_source_files(holo: Any) -> list[Path]:
    """Return the exact tracked source set consumed by the knowledge indexer."""

    base = holo.project_root / "WSP_knowledge" / "docs" / "Papers"
    if not base.exists():
        return []
    files = [
        file_path
        for file_path in sorted(base.rglob("*.md"))
        if not _has_dotfile_in_relative_path(file_path, base)
        and "_backup" not in str(file_path).lower()
        and "/archive/" not in file_path.as_posix().lower()
    ]
    return filter_git_tracked_files(holo.project_root, files)


def _skill_source_files(holo: Any) -> list[Path]:
    """Return the exact tracked source set consumed by the Skillz indexer."""

    patterns = (
        holo.project_root / "modules" / "**" / "skills" / "*" / "SKILLz.md",
        holo.project_root / "modules" / "**" / "skillz" / "*" / "SKILLz.md",
        holo.project_root / "holo_index" / "skillz" / "*" / "SKILLz.md",
        holo.project_root / "holo_index" / "qwen_advisor" / "skills" / "*" / "SKILLz.md",
        holo.project_root / ".claude" / "skills" / "*" / "SKILLz.md",
        holo.project_root / ".claude" / "skillz" / "*" / "SKILLz.md",
    )
    files = [
        Path(file_path)
        for pattern in patterns
        for file_path in glob.glob(str(pattern), recursive=True)
    ]
    return filter_git_tracked_files(holo.project_root, files)


def _tests_manifest(holo: Any) -> CanonicalSourceManifest:
    digest, error = _registry_source_manifest(
        holo,
        holo.project_root / "WSP_knowledge" / "WSP_Test_Registry.json",
    )
    if error or not digest:
        raise CanonicalSourceManifestError(
            "canonical_source_manifest_unavailable:navigation_tests"
        )
    return CanonicalSourceManifest(
        "navigation_tests",
        digest,
        canonical_source_scope_id("navigation_tests"),
    )


_PROBES: dict[str, Callable[[Any], CanonicalSourceManifest]] = {
    "navigation_code": _code_manifest,
    "navigation_symbols": _symbols_manifest,
    "navigation_wsp": _wsp_manifest,
    "navigation_tests": _tests_manifest,
    "navigation_skills": lambda holo: _tracked_manifest(
        holo, "navigation_skills", _skill_source_files(holo)
    ),
    "navigation_docs": lambda holo: _tracked_manifest(
        holo, "navigation_docs", _docs_source_files(holo)
    ),
    "navigation_knowledge": lambda holo: _tracked_manifest(
        holo, "navigation_knowledge", _knowledge_source_files(holo)
    ),
}


def probe_canonical_source_manifests(
    holo: Any,
    collection_names: Iterable[str],
) -> dict[str, CanonicalSourceManifest]:
    manifests: dict[str, CanonicalSourceManifest] = {}
    for name in sorted(set(collection_names)):
        probe = _PROBES.get(name)
        if probe is None:
            raise CanonicalSourceManifestError(
                f"canonical_source_probe_missing:{name}"
            )
        manifest = probe(holo)
        if manifest.source_scope_id != canonical_source_scope_id(name):
            raise CanonicalSourceManifestError(
                f"canonical_source_scope_mismatch:{name}"
            )
        manifests[name] = manifest
    return manifests


__all__ = [
    "CanonicalSourceManifest",
    "CanonicalSourceManifestError",
    "_docs_source_files",
    "_knowledge_source_files",
    "_skill_source_files",
    "probe_canonical_source_manifests",
]
