# -*- coding: utf-8 -*-
"""TurboQuant Embedding Backend — Scaffold (HIA2 Phase 1).

Opt-in int8-quantized embedding backend for HoloIndex. Selected at boot via
``HOLO_USE_TURBOQUANT=1``. When unavailable (this scaffold always reports
unavailable until a real backend is wired by a later slice), ``HoloIndex``
falls back to the ``SentenceTransformer`` path.

Contract the concrete backend MUST satisfy (derived from current call-sites in
``holo_index/core/holo_index.py`` and ``holo_index/core/search_engine.py``):

  * ``encode(text: str, show_progress_bar: bool = False) -> numpy.ndarray``
      Must return a 1-D ``float32`` array with the same dimensionality as the
      ChromaDB-stored vectors. All collections were populated with
      ``all-MiniLM-L6-v2`` at **384 dims**; changing the dim requires a full
      reindex of ``navigation_code``, ``navigation_wsp``, ``navigation_tests``,
      ``navigation_skills``, and ``navigation_symbols``. This scaffold does
      not change the dim.

B1 (HIA1 finding): 384-dim float32 vector contract is pinned.
B4 (HIA1 finding): ``HoloIndex`` caches the loaded model in a class-level
    ``_shared_state``; swapping backends at runtime is not supported. Restart
    the process or reset ``HoloIndex._initialized`` to switch backends.

WSP Compliance: WSP 97 (truth distinction), WSP 49 (module structure).
"""
from __future__ import annotations

from typing import Any


EMBEDDING_DIM = 384  # must match ChromaDB-stored vectors; see B1 above


class TurboQuantEmbedder:
    """Stub for int8-quantized embedder.

    This class intentionally raises on ``encode`` until a real backend is
    wired. ``is_available()`` returns ``False`` so the boot path in
    ``HoloIndex.__init__`` falls back to ``SentenceTransformer``.
    """

    # Marker used by ``_determine_retrieval_mode`` to tag the backend without
    # importing this module at the callsite (duck-typed).
    _turboquant_marker: bool = True

    @classmethod
    def is_available(cls) -> bool:
        """Return ``True`` only when a real quantized backend is wired.

        Phase 1 scaffold: always ``False``. A later slice (post-W6 research)
        will import the chosen backend library here, verify model weights
        are present on disk, and flip this to ``True`` when ready.
        """
        return False

    def encode(self, text: str, show_progress_bar: bool = False) -> Any:  # noqa: ARG002
        """Return a 384-dim float32 embedding.

        Phase 1 scaffold: raises ``NotImplementedError``. The contract is
        documented here so the future implementer has no ambiguity about
        shape, dtype, or the ``show_progress_bar`` parameter.
        """
        raise NotImplementedError(
            "TurboQuant backend not yet implemented. "
            "HOLO_USE_TURBOQUANT=1 was set, but is_available() is False; "
            "HoloIndex will fall back to SentenceTransformer."
        )
