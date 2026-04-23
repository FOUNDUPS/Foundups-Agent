# -*- coding: utf-8 -*-
"""Tests for turboquant_backend.py — HIA3 ONNX Runtime int8 backend.

All tests run without real model artifacts. The optional real-model
smoke test is skipped unless ``HOLO_TURBOQUANT_SMOKE=1`` and the
artifacts are present on disk.

WSP Compliance:
    WSP 5  (Test Coverage)
    WSP 97 (Truth Distinction — backend quality gating)
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from holo_index.core import turboquant_backend as tq
from holo_index.core.turboquant_backend import (
    BACKEND_NAME,
    BACKEND_QUALITY,
    DEFAULT_MODEL_DIR,
    EMBEDDING_DIM,
    MODEL_FILENAME,
    QUALITY_GATE,
    TurboQuantEmbedder,
    _resolve_model_dir,
    _tokenizer_files_present,
)


# ---------------------------------------------------------------------------
# Module-level constants (WSP 97 truth distinction surface)
# ---------------------------------------------------------------------------

class TestTurboQuantConstants:
    def test_embedding_dim_is_384(self):
        """ChromaDB-stored vectors are 384-dim; dim must not drift."""
        assert EMBEDDING_DIM == 384

    def test_backend_name_is_turboquant_onnx_int8(self):
        """Surfaced through search_engine.py as the embedding_backend value."""
        assert BACKEND_NAME == "turboquant_onnx_int8"

    def test_backend_quality_is_experimental(self):
        """HIA3 ships experimental until static calibration closes the drift."""
        assert BACKEND_QUALITY == "experimental"

    def test_quality_gate_is_not_default_ready(self):
        """HIA3 is opt-in only; default remains SentenceTransformer."""
        assert QUALITY_GATE == "not_default_ready"

    def test_default_model_dir_string(self):
        assert isinstance(DEFAULT_MODEL_DIR, str)
        assert Path(DEFAULT_MODEL_DIR).name == "tq1_onnx_int8"

    def test_model_filename_is_int8(self):
        assert MODEL_FILENAME == "model_int8.onnx"


# ---------------------------------------------------------------------------
# Duck-typed marker for HoloIndex branch detection
# ---------------------------------------------------------------------------

class TestTurboQuantMarker:
    def test_turboquant_marker_exists(self):
        assert hasattr(TurboQuantEmbedder, "_turboquant_marker")
        assert TurboQuantEmbedder._turboquant_marker is True


# ---------------------------------------------------------------------------
# Model-dir resolution (env var override)
# ---------------------------------------------------------------------------

class TestResolveModelDir:
    def test_defaults_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("HOLO_TURBOQUANT_MODEL_DIR", raising=False)
        assert _resolve_model_dir() == Path(DEFAULT_MODEL_DIR)

    def test_honors_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOLO_TURBOQUANT_MODEL_DIR", str(tmp_path))
        assert _resolve_model_dir() == tmp_path


# ---------------------------------------------------------------------------
# Tokenizer artifact probe
# ---------------------------------------------------------------------------

class TestTokenizerFilesPresent:
    def test_returns_false_on_empty_dir(self, tmp_path):
        assert _tokenizer_files_present(tmp_path) is False

    def test_returns_true_for_fast_tokenizer(self, tmp_path):
        (tmp_path / "tokenizer.json").write_text("{}", encoding="utf-8")
        assert _tokenizer_files_present(tmp_path) is True

    def test_returns_true_for_legacy_pair(self, tmp_path):
        (tmp_path / "vocab.txt").write_text("", encoding="utf-8")
        (tmp_path / "tokenizer_config.json").write_text("{}", encoding="utf-8")
        assert _tokenizer_files_present(tmp_path) is True

    def test_returns_false_when_only_vocab_present(self, tmp_path):
        (tmp_path / "vocab.txt").write_text("", encoding="utf-8")
        assert _tokenizer_files_present(tmp_path) is False


# ---------------------------------------------------------------------------
# is_available() — never raises, returns False on any missing precondition
# ---------------------------------------------------------------------------

class TestIsAvailable:
    def test_false_when_onnxruntime_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tq, "_onnxruntime_available", lambda: False)
        monkeypatch.setattr(tq, "_transformers_available", lambda: True)
        assert TurboQuantEmbedder.is_available(model_dir=tmp_path) is False

    def test_false_when_transformers_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tq, "_onnxruntime_available", lambda: True)
        monkeypatch.setattr(tq, "_transformers_available", lambda: False)
        assert TurboQuantEmbedder.is_available(model_dir=tmp_path) is False

    def test_false_when_model_dir_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tq, "_onnxruntime_available", lambda: True)
        monkeypatch.setattr(tq, "_transformers_available", lambda: True)
        missing = tmp_path / "does_not_exist"
        assert TurboQuantEmbedder.is_available(model_dir=missing) is False

    def test_false_when_model_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tq, "_onnxruntime_available", lambda: True)
        monkeypatch.setattr(tq, "_transformers_available", lambda: True)
        (tmp_path / "tokenizer.json").write_text("{}", encoding="utf-8")
        assert TurboQuantEmbedder.is_available(model_dir=tmp_path) is False

    def test_false_when_tokenizer_files_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tq, "_onnxruntime_available", lambda: True)
        monkeypatch.setattr(tq, "_transformers_available", lambda: True)
        (tmp_path / MODEL_FILENAME).write_bytes(b"")
        assert TurboQuantEmbedder.is_available(model_dir=tmp_path) is False

    def test_true_when_all_preconditions_met(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tq, "_onnxruntime_available", lambda: True)
        monkeypatch.setattr(tq, "_transformers_available", lambda: True)
        (tmp_path / MODEL_FILENAME).write_bytes(b"")
        (tmp_path / "tokenizer.json").write_text("{}", encoding="utf-8")
        assert TurboQuantEmbedder.is_available(model_dir=tmp_path) is True

    def test_never_raises_on_unexpected_state(self, monkeypatch):
        """Defensive guard: any OSError -> False, not propagated."""
        def _boom():
            raise OSError("disk exploded")
        monkeypatch.setattr(tq, "_onnxruntime_available", _boom)
        assert TurboQuantEmbedder.is_available() is False


# ---------------------------------------------------------------------------
# _ensure_loaded() — actionable RuntimeError per failure mode
# ---------------------------------------------------------------------------

class TestEnsureLoadedFailureModes:
    def test_raises_when_onnxruntime_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tq, "_onnxruntime_available", lambda: False)
        embedder = TurboQuantEmbedder(model_dir=tmp_path)
        with pytest.raises(RuntimeError, match="onnxruntime"):
            embedder._ensure_loaded()

    def test_raises_when_transformers_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tq, "_onnxruntime_available", lambda: True)
        monkeypatch.setattr(tq, "_transformers_available", lambda: False)
        embedder = TurboQuantEmbedder(model_dir=tmp_path)
        with pytest.raises(RuntimeError, match="transformers"):
            embedder._ensure_loaded()

    def test_raises_when_model_dir_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tq, "_onnxruntime_available", lambda: True)
        monkeypatch.setattr(tq, "_transformers_available", lambda: True)
        embedder = TurboQuantEmbedder(model_dir=tmp_path / "nope")
        with pytest.raises(RuntimeError, match="model dir not found"):
            embedder._ensure_loaded()

    def test_raises_when_model_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tq, "_onnxruntime_available", lambda: True)
        monkeypatch.setattr(tq, "_transformers_available", lambda: True)
        embedder = TurboQuantEmbedder(model_dir=tmp_path)
        with pytest.raises(RuntimeError, match="model file not found"):
            embedder._ensure_loaded()

    def test_raises_when_tokenizer_files_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tq, "_onnxruntime_available", lambda: True)
        monkeypatch.setattr(tq, "_transformers_available", lambda: True)
        (tmp_path / MODEL_FILENAME).write_bytes(b"")
        embedder = TurboQuantEmbedder(model_dir=tmp_path)
        with pytest.raises(RuntimeError, match="tokenizer files not found"):
            embedder._ensure_loaded()


# ---------------------------------------------------------------------------
# encode() contract — 1-D float32, length 384, L2-normalized
# ---------------------------------------------------------------------------

class TestEncodeContract:
    def _make_embedder_with_mocks(self):
        """Pre-populate session + tokenizer so _ensure_loaded short-circuits."""
        embedder = TurboQuantEmbedder(model_dir=Path("."))

        seq_len = 4
        hidden = EMBEDDING_DIM
        token_embeddings = np.ones((1, seq_len, hidden), dtype=np.float32)
        token_embeddings[:, 2:, :] = 0.0  # last two tokens masked

        session = MagicMock()
        session.run.return_value = [token_embeddings]
        session.get_inputs.return_value = [
            MagicMock(name="input_ids"),
            MagicMock(name="attention_mask"),
        ]

        tokenizer_output = {
            "input_ids": np.array([[1, 2, 3, 4]], dtype=np.int64),
            "attention_mask": np.array([[1, 1, 0, 0]], dtype=np.int64),
        }
        tokenizer = MagicMock(return_value=tokenizer_output)

        embedder._session = session
        embedder._tokenizer = tokenizer
        embedder._input_names = {"input_ids", "attention_mask"}
        return embedder

    def test_encode_returns_1d_float32_vector(self):
        embedder = self._make_embedder_with_mocks()
        vec = embedder.encode("hello world")
        assert isinstance(vec, np.ndarray)
        assert vec.dtype == np.float32
        assert vec.ndim == 1
        assert vec.shape[0] == EMBEDDING_DIM

    def test_encode_is_l2_normalized(self):
        embedder = self._make_embedder_with_mocks()
        vec = embedder.encode("hello world")
        norm = float(np.linalg.norm(vec))
        assert abs(norm - 1.0) < 1e-5

    def test_encode_accepts_show_progress_bar_kwarg(self):
        """Signature compatibility with SentenceTransformer.encode."""
        embedder = self._make_embedder_with_mocks()
        vec = embedder.encode("hello", show_progress_bar=True)
        assert vec.shape == (EMBEDDING_DIM,)

    def test_encode_filters_unexpected_input_names(self):
        """Tokenizer keys the ORT session doesn't expose must be dropped."""
        embedder = self._make_embedder_with_mocks()
        embedder._input_names = {"input_ids"}
        embedder._tokenizer = MagicMock(return_value={
            "input_ids": np.array([[1, 2]], dtype=np.int64),
            "attention_mask": np.array([[1, 1]], dtype=np.int64),
            "token_type_ids": np.array([[0, 0]], dtype=np.int64),
        })
        token_embeddings = np.ones((1, 2, EMBEDDING_DIM), dtype=np.float32)
        embedder._session.run.return_value = [token_embeddings]

        vec = embedder.encode("x")
        assert vec.shape == (EMBEDDING_DIM,)
        passed_inputs = embedder._session.run.call_args[0][1]
        assert set(passed_inputs.keys()) == {"input_ids"}


# ---------------------------------------------------------------------------
# Instance construction — must not touch model I/O
# ---------------------------------------------------------------------------

class TestConstructionIsSideEffectFree:
    def test_init_does_not_call_ensure_loaded(self, tmp_path):
        embedder = TurboQuantEmbedder(model_dir=tmp_path / "unreadable")
        assert embedder._session is None
        assert embedder._tokenizer is None

    def test_init_defaults_to_resolved_model_dir(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOLO_TURBOQUANT_MODEL_DIR", str(tmp_path))
        embedder = TurboQuantEmbedder()
        assert embedder.model_dir == tmp_path


# ---------------------------------------------------------------------------
# Optional real-model smoke test (skipped by default)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    os.getenv("HOLO_TURBOQUANT_SMOKE") != "1" or not TurboQuantEmbedder.is_available(),
    reason="Real-model smoke test; set HOLO_TURBOQUANT_SMOKE=1 with artifacts on disk.",
)
class TestRealModelSmoke:
    def test_encode_real_model_returns_unit_vector(self):
        embedder = TurboQuantEmbedder()
        vec = embedder.encode("the quick brown fox")
        assert vec.dtype == np.float32
        assert vec.shape == (EMBEDDING_DIM,)
        assert abs(float(np.linalg.norm(vec)) - 1.0) < 1e-3
