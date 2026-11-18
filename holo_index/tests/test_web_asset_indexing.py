#!/usr/bin/env python3
"""
Unit tests for web asset indexing in HoloIndex code collection.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from holo_index.source_scope import canonical_source_scope_id

try:
    from holo_index.core.holo_index import HoloIndex
except ImportError:
    pytest.skip("HoloIndex dependencies unavailable", allow_module_level=True)


class DummyCollection:
    def __init__(self):
        self.add_calls = []

    def add(self, ids, embeddings, documents, metadatas):
        self.add_calls.append({
            "ids": ids,
            "embeddings": embeddings,
            "documents": documents,
            "metadatas": metadatas,
        })

    def count(self):
        if not self.add_calls:
            return 0
        return len(self.add_calls[-1]["ids"])


def _make_holo_stub(tmp_path: Path):
    (tmp_path / "NAVIGATION.py").write_text(
        "NEED_TO = {}\n",
        encoding="utf-8",
    )
    holo = HoloIndex.__new__(HoloIndex)
    collection = DummyCollection()
    holo.project_root = tmp_path
    holo.need_to = {}
    holo.code_collection = collection
    holo._reset_collection = lambda name: collection
    holo._log_agent_action = lambda *args, **kwargs: None
    holo._infer_cube_tag = lambda *args, **kwargs: None
    holo._get_embedding = lambda text: [0.0, 0.0]
    return holo, collection


def _canonical_web_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOLO_INDEX_WEB", "1")
    monkeypatch.setenv("HOLO_WEB_INDEX_ROOTS", "public")
    monkeypatch.setenv(
        "HOLO_WEB_INDEX_EXTENSIONS",
        ".html;.js;.mjs;.cjs;.jsx;.ts;.tsx;.css",
    )
    monkeypatch.setenv("HOLO_WEB_INDEX_MAX_FILES", "0")
    monkeypatch.setenv("HOLO_WEB_INDEX_MAX_CHARS", "5000")


def test_collect_web_asset_entries_reads_public_assets(tmp_path, monkeypatch):
    public_dir = tmp_path / "public" / "js"
    public_dir.mkdir(parents=True)
    asset_path = public_dir / "foundup-cube.js"
    asset_path.write_text("const phase = 'planning...';", encoding="utf-8")

    holo, _ = _make_holo_stub(tmp_path)
    monkeypatch.setenv("HOLO_INDEX_WEB", "1")
    monkeypatch.setenv("HOLO_WEB_INDEX_ROOTS", "public")
    monkeypatch.setenv("HOLO_WEB_INDEX_MAX_FILES", "10")
    monkeypatch.setenv("HOLO_WEB_INDEX_MAX_CHARS", "200")
    monkeypatch.setenv("HOLO_WEB_INDEX_EXTENSIONS", ".js;.html")

    entries = holo._collect_web_asset_entries()

    assert entries
    locations = [entry["location"] for entry in entries]
    assert "public/js/foundup-cube.js" in locations
    assert any("planning" in entry["payload"] for entry in entries)


def test_collect_web_asset_entries_respects_disable_toggle(tmp_path, monkeypatch):
    public_dir = tmp_path / "public"
    public_dir.mkdir(parents=True)
    (public_dir / "index.html").write_text("<canvas id='buildCanvas'></canvas>", encoding="utf-8")

    holo, _ = _make_holo_stub(tmp_path)
    monkeypatch.setenv("HOLO_INDEX_WEB", "0")

    entries = holo._collect_web_asset_entries()

    assert entries == []


def test_index_code_entries_merges_navigation_and_web_assets(tmp_path, monkeypatch):
    public_dir = tmp_path / "public" / "js"
    public_dir.mkdir(parents=True)
    (public_dir / "foundup-cube.js").write_text("const status = 'promoting...';", encoding="utf-8")

    holo, collection = _make_holo_stub(tmp_path)
    holo.need_to = {"launch orchestrator": "modules/foundups/agent_market/src/orchestrator.py:launch_foundup"}

    monkeypatch.setenv("HOLO_INDEX_WEB", "1")
    monkeypatch.setenv("HOLO_WEB_INDEX_ROOTS", "public")
    monkeypatch.setenv("HOLO_INDEX_SYMBOLS", "0")

    holo.index_code_entries()

    assert collection.add_calls, "Expected index_code_entries to write to collection"
    payload = collection.add_calls[-1]
    metadatas = payload["metadatas"]
    documents = payload["documents"]

    assert any(meta.get("type") == "code" for meta in metadatas)
    assert any(meta.get("type") == "web_asset" for meta in metadatas)
    assert any(meta.get("keywords") for meta in metadatas if meta.get("type") == "web_asset")
    assert "public/js/foundup-cube.js" in documents


def test_canonical_web_discovery_is_sorted_and_uncapped(tmp_path, monkeypatch):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    (public_dir / "z.js").write_text("const z = 1;", encoding="utf-8")
    (public_dir / "a.js").write_text("const a = 1;", encoding="utf-8")
    holo, _ = _make_holo_stub(tmp_path)
    _canonical_web_env(monkeypatch)

    entries = holo._collect_web_asset_entries()

    assert [entry["location"] for entry in entries] == [
        "public/a.js",
        "public/z.js",
    ]


def test_web_manifest_hashes_full_bytes_beyond_indexed_snippet(tmp_path, monkeypatch):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    asset = public_dir / "app.js"
    asset.write_text("a" * 6000 + "first-tail", encoding="utf-8")
    holo, _ = _make_holo_stub(tmp_path)
    holo.need_to = {"navigation": "NAVIGATION.py"}
    _canonical_web_env(monkeypatch)

    before = holo.index_code_entries()
    asset.write_text("a" * 6000 + "other-tail", encoding="utf-8")
    after = holo.index_code_entries()

    assert before.source_manifest_digest != after.source_manifest_digest
    assert before.source_scope_id == canonical_source_scope_id("navigation_code")
    assert before.complete is True
    assert after.complete is True


def test_web_file_cap_cannot_produce_complete_source_proof(tmp_path, monkeypatch):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    (public_dir / "a.js").write_text("const a = 1;", encoding="utf-8")
    (public_dir / "b.js").write_text("const b = 1;", encoding="utf-8")
    holo, _ = _make_holo_stub(tmp_path)
    holo.need_to = {"navigation": "NAVIGATION.py"}
    _canonical_web_env(monkeypatch)
    monkeypatch.setenv("HOLO_WEB_INDEX_MAX_FILES", "1")

    result = holo.index_code_entries()

    assert result.discovered_count == 3
    assert result.processed_count == 2
    assert result.complete is False
    assert result.source_scope_id == ""
    assert "cap truncated" in (result.warning or "")


def test_web_read_failure_cannot_produce_complete_source_proof(
    tmp_path,
    monkeypatch,
):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    asset = public_dir / "app.js"
    asset.write_text("const app = true;", encoding="utf-8")
    holo, _ = _make_holo_stub(tmp_path)
    holo.need_to = {"navigation": "NAVIGATION.py"}
    _canonical_web_env(monkeypatch)
    original_read_bytes = Path.read_bytes

    def _read_bytes(path: Path) -> bytes:
        if path == asset:
            raise OSError("injected read failure")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", _read_bytes)
    result = holo.index_code_entries()

    assert result.failed_count == 1
    assert result.complete is False
    assert "failed to read" in (result.warning or "")
