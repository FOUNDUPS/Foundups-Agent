# -*- coding: utf-8 -*-
"""TurboQuant Embedding Backend — ONNX Runtime int8 (HIA3 beta).

Opt-in int8-quantized embedding backend for HoloIndex. Selected at boot via
``HOLO_USE_TURBOQUANT=1``. When unavailable (dependency or model artifacts
missing), ``HoloIndex`` falls back to the ``SentenceTransformer`` path.

HIA3 status (WSP 97 truth distinction):

  * **Performance accepted** — TQ1 benchmark measured 5.6x cold-start,
    6.6x load, 8.8x single-query median, 4.0x smaller artifact vs the
    fp32 ``SentenceTransformer`` baseline on the same MiniLM-L6-v2 model.
  * **Quality gated** — TQ1 measured 3.65% mean cosine drift vs fp32
    (above the 2% same-model threshold) and 76.7% synthetic top-1
    retrieval agreement (~23% flip rate). This backend is therefore
    marked ``backend_quality="experimental"`` and
    ``quality_gate="not_default_ready"``. Static calibration and
    real-corpus A/B gating are TQ2 / HIA-followup slice work; HIA3
    builds only the safe backend seam.
  * **Default unchanged** — ``HOLO_USE_TURBOQUANT=0`` (the default)
    keeps HoloIndex on the ``SentenceTransformer`` path, bit-identical
    to pre-HIA2 behavior.

Dependencies:

  * ``onnxruntime`` — optional runtime dep. Imported lazily inside
    ``is_available()`` / ``_ensure_loaded()``; import failure returns
    ``False`` rather than raising. Not added to
    ``holo_index/requirements.txt`` as a hard dep in HIA3.
  * ``transformers`` — already transitively required via
    ``sentence-transformers>=2.2.0``; used for the MiniLM tokenizer.

Model artifacts:

  * Location: ``HOLO_TURBOQUANT_MODEL_DIR`` (env), default
    ``E:/HoloIndex/models/tq1_onnx_int8/``.
  * Required files: ``model_int8.onnx`` plus tokenizer files
    (``tokenizer.json`` or the ``vocab.txt`` + ``tokenizer_config.json``
    pair). Missing files -> ``is_available()`` returns ``False``.
  * Artifacts are NOT committed to the repo. They are produced by
    ``holo_index/scripts/benchmarks/tq1_onnx_int8_bench.py`` or any
    equivalent export pipeline.

Contract (must stay consistent with current ``HoloIndex._get_embedding``
call-site in ``holo_index/core/holo_index.py``):

  * ``encode(text: str, show_progress_bar: bool = False) -> numpy.ndarray``
      Returns a 1-D ``float32`` array of length ``EMBEDDING_DIM`` (384).
      All ChromaDB collections were populated with ``all-MiniLM-L6-v2``
      at 384 dims; changing the dim would require a full reindex of
      ``navigation_code``, ``navigation_wsp``, ``navigation_tests``,
      ``navigation_skills``, and ``navigation_symbols``. This backend
      preserves the dim.

B1 (HIA1 finding): 384-dim float32 vector contract is pinned.
B4 (HIA1 finding): ``HoloIndex`` caches the loaded model in a class-level
    ``_shared_state``; swapping backends at runtime is not supported.
    Restart the process or reset ``HoloIndex._initialized`` to switch.

WSP Compliance: WSP 97 (truth distinction), WSP 49 (module structure),
WSP 50 (pre-action verification — dependency policy explicit).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional


EMBEDDING_DIM = 384  # must match ChromaDB-stored vectors; see B1 above
DEFAULT_MODEL_DIR = "E:/HoloIndex/models/tq1_onnx_int8"
MODEL_FILENAME = "model_int8.onnx"

# Metadata surfaced through search_engine.py (WSP 97 truth distinction).
BACKEND_NAME = "turboquant_onnx_int8"
BACKEND_QUALITY = "experimental"
QUALITY_GATE = "not_default_ready"

_logger = logging.getLogger(__name__)


def _resolve_model_dir() -> Path:
    """Return the configured model directory.

    Honors ``HOLO_TURBOQUANT_MODEL_DIR`` env var; falls back to
    ``DEFAULT_MODEL_DIR``. This function does NOT check for existence —
    call ``_tokenizer_files_present()`` and the ``MODEL_FILENAME`` check
    separately so ``is_available()`` can return False cleanly.
    """
    return Path(os.getenv("HOLO_TURBOQUANT_MODEL_DIR", DEFAULT_MODEL_DIR))


def _tokenizer_files_present(model_dir: Path) -> bool:
    """Check for the tokenizer artifact set the MiniLM tokenizer needs.

    HuggingFace tokenizers can load from either:
      * a ``tokenizer.json`` fast-tokenizer file, OR
      * the legacy ``vocab.txt`` + ``tokenizer_config.json`` pair.

    We accept either combination. Missing -> backend unavailable.
    Defensive: returns False rather than raising on any OSError.
    """
    try:
        fast = (model_dir / "tokenizer.json").exists()
        legacy = (
            (model_dir / "vocab.txt").exists()
            and (model_dir / "tokenizer_config.json").exists()
        )
        return fast or legacy
    except (OSError, ValueError):
        return False


def _onnxruntime_available() -> bool:
    """Return True if ``onnxruntime`` is importable.

    Optional-import guard. Never raises — missing dependency is a valid
    state that routes HoloIndex to the SentenceTransformer fallback.
    """
    try:
        import onnxruntime  # noqa: F401
        return True
    except Exception:  # pragma: no cover - import-failure surface
        return False


def _transformers_available() -> bool:
    """Return True if ``transformers`` is importable.

    Transitively required via ``sentence-transformers>=2.2.0`` in
    ``holo_index/requirements.txt``, but guarded anyway so the backend
    fails cleanly if the dep graph ever changes.
    """
    try:
        from transformers import AutoTokenizer  # noqa: F401
        return True
    except Exception:  # pragma: no cover - import-failure surface
        return False


class TurboQuantEmbedder:
    """ONNX Runtime int8 embedder for MiniLM-L6-v2.

    Lazy-loads the ONNX session + tokenizer on first ``encode()`` call
    (or eagerly via ``_ensure_loaded()``). ``is_available()`` is a
    classmethod that reports readiness without touching module state,
    so ``HoloIndex`` can probe before constructing.
    """

    # Marker used by ``HoloIndex.__init__`` to tag the backend without
    # importing this module at the callsite (duck-typed).
    _turboquant_marker: bool = True

    def __init__(self, model_dir: Optional[Path] = None) -> None:
        self.model_dir: Path = model_dir if model_dir is not None else _resolve_model_dir()
        self._session = None
        self._tokenizer = None
        self._input_names: Optional[set] = None

    # -- availability probe --------------------------------------------------

    @classmethod
    def is_available(cls, model_dir: Optional[Path] = None) -> bool:
        """Return True iff the full backend stack can load.

        Checks:
          1. ``onnxruntime`` importable.
          2. ``transformers`` importable.
          3. Model dir exists.
          4. ``model_int8.onnx`` present in model dir.
          5. Tokenizer artifacts present in model dir.

        Never raises. Missing any precondition -> False.
        """
        try:
            if not _onnxruntime_available():
                return False
            if not _transformers_available():
                return False
            mdir = model_dir if model_dir is not None else _resolve_model_dir()
            if not mdir.exists():
                return False
            if not (mdir / MODEL_FILENAME).exists():
                return False
            if not _tokenizer_files_present(mdir):
                return False
            return True
        except (OSError, ValueError):
            return False

    # -- lazy loader ---------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """Load session + tokenizer on first use.

        Separated from ``__init__`` so ``is_available()`` can be called
        cheaply and so tests can construct without triggering any model
        I/O. Raises ``RuntimeError`` with a clear message if any step
        fails — the caller (HoloIndex) catches and falls back.
        """
        if self._session is not None and self._tokenizer is not None:
            return

        if not _onnxruntime_available():
            raise RuntimeError(
                "TurboQuant: onnxruntime is not installed. "
                "Install via `pip install onnxruntime` or unset HOLO_USE_TURBOQUANT."
            )
        if not _transformers_available():
            raise RuntimeError(
                "TurboQuant: transformers is not installed. "
                "Check holo_index/requirements.txt (sentence-transformers pulls it)."
            )
        if not self.model_dir.exists():
            raise RuntimeError(
                f"TurboQuant: model dir not found: {self.model_dir}. "
                "Set HOLO_TURBOQUANT_MODEL_DIR or export model artifacts."
            )
        model_path = self.model_dir / MODEL_FILENAME
        if not model_path.exists():
            raise RuntimeError(
                f"TurboQuant: model file not found: {model_path}"
            )
        if not _tokenizer_files_present(self.model_dir):
            raise RuntimeError(
                f"TurboQuant: tokenizer files not found in {self.model_dir}"
            )

        import onnxruntime as ort
        from transformers import AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir))
        self._session = ort.InferenceSession(
            str(model_path),
            providers=["CPUExecutionProvider"],
        )
        self._input_names = {i.name for i in self._session.get_inputs()}

    # -- encode --------------------------------------------------------------

    def encode(self, text: str, show_progress_bar: bool = False) -> Any:  # noqa: ARG002
        """Return a 1-D ``float32`` numpy array of length ``EMBEDDING_DIM``.

        Mirrors the fp32 ``SentenceTransformer`` contract used in
        ``HoloIndex._get_embedding`` so callers do not need branch logic.
        ``show_progress_bar`` is accepted for signature compatibility
        but is a no-op here.

        Pipeline: tokenize -> ORT forward -> mean-pool over tokens
        (attention-mask weighted) -> L2 normalize. L2 normalization
        matches the normalized output of the MiniLM-L6-v2 pipeline used
        in the TQ1 baseline benchmark.
        """
        self._ensure_loaded()

        import numpy as np

        enc = self._tokenizer(
            text,
            return_tensors="np",
            padding=True,
            truncation=True,
            max_length=256,
        )
        inputs = {k: v for k, v in enc.items() if k in (self._input_names or set())}
        outputs = self._session.run(None, inputs)
        token_embeddings = outputs[0]  # (batch, seq, hidden)
        mask = enc["attention_mask"][..., None].astype("float32")
        summed = (token_embeddings * mask).sum(axis=1)
        counts = mask.sum(axis=1).clip(min=1e-9)
        pooled = summed / counts
        norms = np.linalg.norm(pooled, axis=1, keepdims=True).clip(min=1e-12)
        normalized = (pooled / norms).astype("float32")
        return normalized[0]
