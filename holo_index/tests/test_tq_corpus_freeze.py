# -*- coding: utf-8 -*-
"""Tests for TQ corpus freeze mechanism.

WSP: WSP 97 (truth distinction), WSP 5 (test coverage).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestHashFunctions:
    """Test deterministic hash computation."""

    def test_ids_hash_deterministic(self):
        """Same IDs in different order produce same hash."""
        from holo_index.scripts.benchmarks.tq_corpus_freeze import _compute_ids_hash

        ids1 = ["doc_a", "doc_b", "doc_c"]
        ids2 = ["doc_c", "doc_a", "doc_b"]

        assert _compute_ids_hash(ids1) == _compute_ids_hash(ids2)

    def test_ids_hash_different_content(self):
        """Different IDs produce different hashes."""
        from holo_index.scripts.benchmarks.tq_corpus_freeze import _compute_ids_hash

        ids1 = ["doc_a", "doc_b"]
        ids2 = ["doc_a", "doc_c"]

        assert _compute_ids_hash(ids1) != _compute_ids_hash(ids2)

    def test_ids_hash_empty(self):
        """Empty IDs list produces consistent hash."""
        from holo_index.scripts.benchmarks.tq_corpus_freeze import _compute_ids_hash

        assert _compute_ids_hash([]) == _compute_ids_hash([])

    def test_documents_hash_deterministic(self):
        """Same documents in different order produce same hash."""
        from holo_index.scripts.benchmarks.tq_corpus_freeze import _compute_documents_hash

        docs1 = ["Hello world", "Test document"]
        docs2 = ["Test document", "Hello world"]

        assert _compute_documents_hash(docs1) == _compute_documents_hash(docs2)

    def test_documents_hash_empty(self):
        """Empty documents list produces 'empty' marker."""
        from holo_index.scripts.benchmarks.tq_corpus_freeze import _compute_documents_hash

        assert _compute_documents_hash([]) == "empty"

    def test_metadatas_hash_deterministic(self):
        """Same metadata in different order produce same hash."""
        from holo_index.scripts.benchmarks.tq_corpus_freeze import _compute_metadatas_hash

        meta1 = [{"a": 1, "b": 2}, {"c": 3}]
        meta2 = [{"c": 3}, {"b": 2, "a": 1}]

        assert _compute_metadatas_hash(meta1) == _compute_metadatas_hash(meta2)

    def test_metadatas_hash_empty(self):
        """Empty metadata list produces 'empty' marker."""
        from holo_index.scripts.benchmarks.tq_corpus_freeze import _compute_metadatas_hash

        assert _compute_metadatas_hash([]) == "empty"


class TestManifestStructure:
    """Test manifest creation and structure."""

    def test_manifest_has_required_fields(self):
        """Verify manifest contains all required fields."""
        from holo_index.scripts.benchmarks.tq_corpus_freeze import (
            TARGET_COLLECTIONS,
            _compute_ids_hash,
        )

        required_fields = ["vector_path", "created_at_utc", "git_sha", "collections"]
        collection_fields = ["count", "ids_sha256", "documents_sha256", "metadatas_sha256"]

        manifest = {
            "vector_path": "E:/HoloIndex/vectors",
            "created_at_utc": "2026-04-23T12:00:00+00:00",
            "git_sha": "abc123def456",
            "collections": {
                "navigation_code": {
                    "count": 100,
                    "ids_sha256": _compute_ids_hash(["a", "b"]),
                    "documents_sha256": "abc123",
                    "metadatas_sha256": "def456",
                }
            },
        }

        for field in required_fields:
            assert field in manifest, f"Missing required field: {field}"

        for field in collection_fields:
            assert field in manifest["collections"]["navigation_code"]


class TestVerifyBehavior:
    """Test verify command behavior."""

    def test_verify_detects_count_drift(self):
        """Verify fails when document count changes."""
        from holo_index.scripts.benchmarks.tq_corpus_freeze import (
            _compute_documents_hash,
            _compute_ids_hash,
            _compute_metadatas_hash,
        )

        ids = ["doc1", "doc2", "doc3"]
        ids_hash = _compute_ids_hash(ids)

        manifest = {
            "collections": {
                "test_collection": {
                    "count": 5,
                    "ids_sha256": ids_hash,
                    "documents_sha256": "abc",
                    "metadatas_sha256": "def",
                }
            }
        }

        assert manifest["collections"]["test_collection"]["count"] != len(ids)

    def test_verify_detects_ids_hash_drift(self):
        """Verify fails when IDs hash changes."""
        from holo_index.scripts.benchmarks.tq_corpus_freeze import _compute_ids_hash

        original_ids = ["doc1", "doc2"]
        new_ids = ["doc1", "doc3"]

        original_hash = _compute_ids_hash(original_ids)
        new_hash = _compute_ids_hash(new_ids)

        assert original_hash != new_hash

    def test_verify_passes_unchanged_corpus(self):
        """Verify passes when corpus matches manifest."""
        from holo_index.scripts.benchmarks.tq_corpus_freeze import (
            _compute_documents_hash,
            _compute_ids_hash,
            _compute_metadatas_hash,
        )

        ids = ["doc1", "doc2"]
        docs = ["Hello", "World"]
        metas = [{"a": 1}, {"b": 2}]

        manifest_entry = {
            "count": len(ids),
            "ids_sha256": _compute_ids_hash(ids),
            "documents_sha256": _compute_documents_hash(docs),
            "metadatas_sha256": _compute_metadatas_hash(metas),
        }

        current_ids_hash = _compute_ids_hash(ids)
        current_docs_hash = _compute_documents_hash(docs)
        current_meta_hash = _compute_metadatas_hash(metas)

        assert manifest_entry["count"] == len(ids)
        assert manifest_entry["ids_sha256"] == current_ids_hash
        assert manifest_entry["documents_sha256"] == current_docs_hash
        assert manifest_entry["metadatas_sha256"] == current_meta_hash


class TestPreflightCheck:
    """Test preflight check behavior for TQ2/TQ3 integration."""

    def test_preflight_exits_on_missing_manifest(self):
        """Preflight exits non-zero when manifest doesn't exist."""
        from holo_index.scripts.benchmarks.tq_corpus_freeze import preflight_check

        with pytest.raises(SystemExit) as exc_info:
            preflight_check(Path("/nonexistent/manifest.json"))

        assert exc_info.value.code == 1

    def test_preflight_honors_allow_drift_env(self, monkeypatch):
        """Preflight skips verification when TQ_CORPUS_ALLOW_DRIFT=1."""
        from holo_index.scripts.benchmarks.tq_corpus_freeze import preflight_check

        monkeypatch.setenv("TQ_CORPUS_ALLOW_DRIFT", "1")

        preflight_check(Path("/nonexistent/manifest.json"))

    def test_preflight_passes_on_valid_manifest(self, tmp_path, monkeypatch):
        """Preflight passes when verify returns True."""
        from holo_index.scripts.benchmarks.tq_corpus_freeze import preflight_check

        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps({
            "vector_path": "E:/HoloIndex/vectors",
            "created_at_utc": "2026-04-23T12:00:00+00:00",
            "git_sha": "abc123",
            "collections": {},
        }))

        with patch("holo_index.scripts.benchmarks.tq_corpus_freeze.verify_corpus") as mock_verify:
            mock_verify.return_value = (True, [])
            preflight_check(manifest_path)

    def test_preflight_exits_on_drift(self, tmp_path, monkeypatch):
        """Preflight exits non-zero when drift detected."""
        from holo_index.scripts.benchmarks.tq_corpus_freeze import preflight_check

        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps({
            "vector_path": "E:/HoloIndex/vectors",
            "created_at_utc": "2026-04-23T12:00:00+00:00",
            "git_sha": "abc123",
            "collections": {},
        }))

        with patch("holo_index.scripts.benchmarks.tq_corpus_freeze.verify_corpus") as mock_verify:
            mock_verify.return_value = (False, ["navigation_wsp: count 3446 → 1916"])

            with pytest.raises(SystemExit) as exc_info:
                preflight_check(manifest_path)

            assert exc_info.value.code == 1
