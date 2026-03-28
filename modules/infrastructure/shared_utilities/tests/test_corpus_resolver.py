#!/usr/bin/env python3
"""Tests for the shared training corpus resolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.infrastructure.shared_utilities.corpus_resolver import resolve_corpus_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_env(monkeypatch) -> None:
    monkeypatch.delenv("OPENCLAW_TRAINING_CORPUS", raising=False)


# ---------------------------------------------------------------------------
# 1. Returns None when no candidate exists
# ---------------------------------------------------------------------------

def test_returns_none_when_no_corpus_found(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    result = resolve_corpus_path(tmp_path)
    assert result is None


# ---------------------------------------------------------------------------
# 2. Final fallback: repo_root / "012.txt"
# ---------------------------------------------------------------------------

def test_fallback_to_012_txt(tmp_path, monkeypatch):
    _clear_env(monkeypatch)
    corpus = tmp_path / "012.txt"
    corpus.write_text("line1\n")
    result = resolve_corpus_path(tmp_path)
    assert result == corpus


# ---------------------------------------------------------------------------
# 3. Env var (repo-relative name) takes priority over fallback
# ---------------------------------------------------------------------------

def test_env_var_repo_relative_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_TRAINING_CORPUS", "custom_corpus.txt")
    custom = tmp_path / "custom_corpus.txt"
    custom.write_text("data\n")
    # Also create 012.txt to confirm it is NOT chosen
    (tmp_path / "012.txt").write_text("fallback\n")
    result = resolve_corpus_path(tmp_path)
    assert result == custom


# ---------------------------------------------------------------------------
# 4. Env var absolute path is honoured directly
# ---------------------------------------------------------------------------

def test_env_var_absolute_path(tmp_path, monkeypatch):
    abs_corpus = tmp_path / "absolute_corpus.txt"
    abs_corpus.write_text("abs\n")
    monkeypatch.setenv("OPENCLAW_TRAINING_CORPUS", str(abs_corpus))
    result = resolve_corpus_path(tmp_path)
    assert result == abs_corpus


# ---------------------------------------------------------------------------
# 5. Env var absolute path missing → None (no fallback after absolute)
# ---------------------------------------------------------------------------

def test_env_var_absolute_missing_returns_none(tmp_path, monkeypatch):
    missing = tmp_path / "does_not_exist.txt"
    monkeypatch.setenv("OPENCLAW_TRAINING_CORPUS", str(missing))
    result = resolve_corpus_path(tmp_path)
    assert result is None


# ---------------------------------------------------------------------------
# 6. Secondary candidate: holo_index/data/<name>
# ---------------------------------------------------------------------------

def test_holo_index_data_candidate(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_TRAINING_CORPUS", "corpus.txt")
    holo_data = tmp_path / "holo_index" / "data"
    holo_data.mkdir(parents=True)
    corpus = holo_data / "corpus.txt"
    corpus.write_text("data\n")
    result = resolve_corpus_path(tmp_path)
    assert result == corpus


# ---------------------------------------------------------------------------
# 7. Tertiary candidate: docs/012_moshpit/<name>
# ---------------------------------------------------------------------------

def test_docs_moshpit_candidate(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_TRAINING_CORPUS", "corpus.txt")
    moshpit = tmp_path / "docs" / "012_moshpit"
    moshpit.mkdir(parents=True)
    corpus = moshpit / "corpus.txt"
    corpus.write_text("data\n")
    result = resolve_corpus_path(tmp_path)
    assert result == corpus


# ---------------------------------------------------------------------------
# 8. Priority order: primary > holo_index/data > docs/012_moshpit > 012.txt
# ---------------------------------------------------------------------------

def test_primary_beats_secondary(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_TRAINING_CORPUS", "corpus.txt")
    primary = tmp_path / "corpus.txt"
    primary.write_text("primary\n")
    holo_data = tmp_path / "holo_index" / "data"
    holo_data.mkdir(parents=True)
    (holo_data / "corpus.txt").write_text("secondary\n")
    result = resolve_corpus_path(tmp_path)
    assert result == primary
