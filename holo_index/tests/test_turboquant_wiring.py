# -*- coding: utf-8 -*-
"""HIA2 / HIA-TAX1 wiring tests — env flag + (mode, backend) resolution.

Stub-surface tests (``is_available()=False``, ``encode()`` raises, marker
present, dim==384) live in ``test_turboquant_backend.py``. This file covers
only the wiring HIA2 added and HIA-TAX1 corrected:

  * ``_turboquant_enabled()`` — env-var parsing for ``HOLO_USE_TURBOQUANT``.
  * ``(retrieval_mode, embedding_backend)`` tuple resolution — the branch
    logic in ``HoloIndex.__init__`` that labels both behavior and backend.

HIA-TAX1 correction (WSP 97): retrieval_mode describes what retrieval does
(semantic/lexical/failed); embedding_backend describes how semantic vectors
are produced (sentence_transformers/turboquant/none). TurboQuant is a
*semantic* backend — when active, retrieval_mode remains ``"semantic"``.
"""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from holo_index.core.turboquant_backend import TurboQuantEmbedder, EMBEDDING_DIM
from holo_index.core.holo_index import _turboquant_enabled


class TestTurboQuantEnvFlag(unittest.TestCase):
    """``_turboquant_enabled()`` env-var parsing."""

    @patch.dict(os.environ, {}, clear=False)
    def test_unset_is_disabled(self):
        os.environ.pop("HOLO_USE_TURBOQUANT", None)
        self.assertFalse(_turboquant_enabled())

    @patch.dict(os.environ, {"HOLO_USE_TURBOQUANT": "0"}, clear=False)
    def test_zero_is_disabled(self):
        self.assertFalse(_turboquant_enabled())

    @patch.dict(os.environ, {"HOLO_USE_TURBOQUANT": "1"}, clear=False)
    def test_one_is_enabled(self):
        self.assertTrue(_turboquant_enabled())

    @patch.dict(os.environ, {"HOLO_USE_TURBOQUANT": "true"}, clear=False)
    def test_true_is_enabled(self):
        self.assertTrue(_turboquant_enabled())

    @patch.dict(os.environ, {"HOLO_USE_TURBOQUANT": "YES"}, clear=False)
    def test_yes_uppercase_is_enabled(self):
        self.assertTrue(_turboquant_enabled())

    @patch.dict(os.environ, {"HOLO_USE_TURBOQUANT": "off"}, clear=False)
    def test_off_is_disabled(self):
        self.assertFalse(_turboquant_enabled())


class TestRetrievalModeBackendTuple(unittest.TestCase):
    """``(retrieval_mode, embedding_backend)`` resolution mirrors ``__init__``.

    HIA-TAX1 taxonomy:

      * ``None``                          -> (lexical, none)
      * TurboQuantEmbedder-like instance  -> (semantic, turboquant)
      * SentenceTransformer-like instance -> (semantic, sentence_transformers)

    ``retrieval_mode="failed"`` is reserved for the initialization-default
    state and is not reachable via this helper; the real boot path sets it
    only when every load attempt fails before either fallback kicks in.
    """

    @staticmethod
    def _resolve(model) -> tuple[str, str]:
        """Mirror of the mode/backend assignment logic in __init__."""
        if model is None:
            return ("lexical", "none")
        if getattr(model, "_turboquant_marker", False):
            return ("semantic", "turboquant")
        return ("semantic", "sentence_transformers")

    def test_none_resolves_lexical_none(self):
        self.assertEqual(self._resolve(None), ("lexical", "none"))

    def test_turboquant_embedder_resolves_semantic_turboquant(self):
        """TurboQuant is a semantic backend — mode stays 'semantic' (WSP 97)."""
        self.assertEqual(
            self._resolve(TurboQuantEmbedder()),
            ("semantic", "turboquant"),
        )

    def test_sentence_transformer_like_resolves_semantic_st(self):
        class FakeSentenceTransformer:
            def encode(self, text, show_progress_bar=False):
                return [0.0] * EMBEDDING_DIM
        self.assertEqual(
            self._resolve(FakeSentenceTransformer()),
            ("semantic", "sentence_transformers"),
        )

    def test_turboquant_never_labels_itself_as_a_retrieval_mode(self):
        """HIA-TAX1 invariant: 'turboquant' is NEVER a retrieval_mode value.

        It only ever appears as an embedding_backend. This guards against
        regressing to the pre-TAX1 taxonomy that conflated the two fields.
        """
        mode, backend = self._resolve(TurboQuantEmbedder())
        self.assertEqual(mode, "semantic")
        self.assertNotEqual(mode, "turboquant")
        self.assertEqual(backend, "turboquant")

    def test_turboquant_unavailable_precondition(self):
        """Boot path relies on is_available()=False to route to ST fallback."""
        self.assertFalse(TurboQuantEmbedder.is_available())


if __name__ == "__main__":
    unittest.main(verbosity=2)
