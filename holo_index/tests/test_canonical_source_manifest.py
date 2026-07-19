"""Contract tests for exact read-only HoloIndex source manifests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import holo_index.canonical_source_manifest as manifest_module
from holo_index.canonical_source_manifest import probe_canonical_source_manifests
from holo_index.core.indexing_engine import (
    WebAssetDiscovery,
    source_file_manifest_digest,
    source_manifest_digest,
)
from holo_index.source_scope import (
    CANONICAL_WEB_EXTENSIONS,
    canonical_source_scope_id,
)


@pytest.mark.parametrize(
    ("collection_name", "discovery_name"),
    (
        ("navigation_docs", "_docs_source_files"),
        ("navigation_knowledge", "_knowledge_source_files"),
        ("navigation_skills", "_skill_source_files"),
    ),
)
def test_file_manifest_probe_uses_indexer_source_set_exactly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    collection_name: str,
    discovery_name: str,
) -> None:
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    files = [first, second]
    monkeypatch.setattr(manifest_module, discovery_name, lambda _holo: files)
    monkeypatch.setattr(
        manifest_module,
        "filter_git_tracked_files",
        lambda _root, values: list(values),
    )
    holo = SimpleNamespace(project_root=tmp_path)

    result = probe_canonical_source_manifests(holo, [collection_name])[collection_name]

    assert result.digest == source_file_manifest_digest(files, project_root=tmp_path)
    assert result.source_scope_id == canonical_source_scope_id(collection_name)


def test_code_probe_matches_code_indexer_manifest_formula(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    web = WebAssetDiscovery(
        entries=[],
        discovered_count=2,
        processed_count=2,
        failed_count=0,
        source_manifest_digest="sha256:" + ("a" * 64),
        source_scope_id=canonical_source_scope_id("navigation_code"),
    )
    nav_manifest = "sha256:" + ("b" * 64)
    monkeypatch.setattr(manifest_module, "_discover_web_assets", lambda _holo: web)
    monkeypatch.setattr(
        manifest_module,
        "_navigation_source_evidence",
        lambda _holo: (nav_manifest, 0, ""),
    )
    holo = SimpleNamespace(need_to={"beta": "b.py", "alpha": "a.py"})

    result = probe_canonical_source_manifests(holo, ["navigation_code"])[
        "navigation_code"
    ]

    assert result.digest == source_manifest_digest(
        {
            "navigation": sorted(holo.need_to.items()),
            "navigation_source_manifest": nav_manifest,
            "web_asset_source_manifest": web.source_manifest_digest,
        }
    )


def test_canonical_code_scope_includes_modern_javascript_modules() -> None:
    assert {".mjs", ".cjs"}.issubset(CANONICAL_WEB_EXTENSIONS)
