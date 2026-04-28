# -*- coding: utf-8 -*-
"""TQ4 backend-routing unit tests.

Covers ``holo_index.core.backend_routing`` — the policy module that decides,
per collection, whether a query is served by fp32 SentenceTransformer or int8
TurboQuant.

These tests intentionally avoid instantiating ``HoloIndex`` so they stay fast
and work without ChromaDB, ONNX, or the MiniLM model on disk. The taxonomy
contract they lock in:

  * Routing is OFF unless ``routing_active=True``.
  * Every routed choice must be in ``available_backends`` (when supplied);
    otherwise the resolver falls through to whatever IS loaded — never
    silently returns a backend that cannot encode.
  * W3/TQ4: Conservative routing — only collections that passed both gates
    (top-1 >= 90%, top-5 >= 95%) may use int8:
    - ``navigation_symbols`` and ``navigation_skills`` -> int8 (gate-passing)
    - All others -> fp32 (gate-failing or unaudited)
"""
from __future__ import annotations

import unittest

from holo_index.core.backend_routing import (
    BACKEND_SENTENCE_TRANSFORMERS,
    BACKEND_TURBOQUANT,
    COLLECTION_BACKEND_ROUTING,
    DEFAULT_BACKEND,
    build_collection_backend_map,
    resolve_backend_for_collection,
)


class _Sentinel:
    """Stand-in for a loaded embedder — identity is all the resolver checks."""


class TestRoutingPolicyMap(unittest.TestCase):
    """The static policy table is the artifact TQ2 evidence supports."""

    def test_int8_lane_is_symbols_and_skills_only(self):
        """W3/TQ4: Only gate-passing collections may use int8."""
        int8_lane = {
            name
            for name, backend in COLLECTION_BACKEND_ROUTING.items()
            if backend == BACKEND_TURBOQUANT
        }
        self.assertEqual(
            int8_lane,
            {
                "navigation_skills",
                "navigation_symbols",
            },
        )

    def test_vocabulary_is_fp32(self):
        """TQ2 gate blocker — failed top-5 agreement."""
        self.assertEqual(
            COLLECTION_BACKEND_ROUTING["navigation_vocabulary"],
            BACKEND_SENTENCE_TRANSFORMERS,
        )

    def test_code_and_wsp_are_fp32(self):
        """W3/TQ4: code and wsp failed gates after CFZ4 separation."""
        self.assertEqual(
            COLLECTION_BACKEND_ROUTING["navigation_code"],
            BACKEND_SENTENCE_TRANSFORMERS,
        )
        self.assertEqual(
            COLLECTION_BACKEND_ROUTING["navigation_wsp"],
            BACKEND_SENTENCE_TRANSFORMERS,
        )

    def test_navigation_tests_is_fp32(self):
        """TQ4: navigation_tests explicitly set to fp32 (unaudited)."""
        self.assertEqual(
            COLLECTION_BACKEND_ROUTING["navigation_tests"],
            BACKEND_SENTENCE_TRANSFORMERS,
        )

    def test_default_backend_is_fp32(self):
        """Default must be the backend that built every live Chroma row."""
        self.assertEqual(DEFAULT_BACKEND, BACKEND_SENTENCE_TRANSFORMERS)


class TestResolveBackendForCollection(unittest.TestCase):
    """``resolve_backend_for_collection`` — per-query backend selection."""

    def test_inactive_routing_returns_default(self):
        for name in COLLECTION_BACKEND_ROUTING:
            self.assertEqual(
                resolve_backend_for_collection(name, routing_active=False),
                DEFAULT_BACKEND,
                msg=f"inactive routing must always return fp32 (got mismatch for {name})",
            )

    def test_inactive_routing_int8_only_returns_int8(self):
        """WSP 97 truth-surface: degraded int8-only mode must report int8, not fp32."""
        only_tq = {BACKEND_TURBOQUANT: _Sentinel()}
        for name in COLLECTION_BACKEND_ROUTING:
            self.assertEqual(
                resolve_backend_for_collection(
                    name, routing_active=False, available_backends=only_tq
                ),
                BACKEND_TURBOQUANT,
                msg=f"inactive routing with only int8 must return int8 for {name}",
            )

    def test_inactive_routing_both_backends_returns_fp32(self):
        """When routing is inactive but both backends are loaded, fp32 (default) wins."""
        both = {
            BACKEND_SENTENCE_TRANSFORMERS: _Sentinel(),
            BACKEND_TURBOQUANT: _Sentinel(),
        }
        for name in COLLECTION_BACKEND_ROUTING:
            self.assertEqual(
                resolve_backend_for_collection(
                    name, routing_active=False, available_backends=both
                ),
                BACKEND_SENTENCE_TRANSFORMERS,
                msg=f"inactive routing with both backends must return fp32 for {name}",
            )

    def test_active_routing_sends_int8_lane_to_turboquant(self):
        """W3/TQ4: Only gate-passing collections route to int8."""
        both = {
            BACKEND_SENTENCE_TRANSFORMERS: _Sentinel(),
            BACKEND_TURBOQUANT: _Sentinel(),
        }
        # Only skills and symbols passed gates
        for name in ("navigation_skills", "navigation_symbols"):
            self.assertEqual(
                resolve_backend_for_collection(
                    name, routing_active=True, available_backends=both,
                ),
                BACKEND_TURBOQUANT,
                msg=f"{name} must route to int8 under active routing",
            )

    def test_active_routing_keeps_code_and_wsp_on_fp32(self):
        """W3/TQ4: code and wsp failed gates, stay on fp32."""
        both = {
            BACKEND_SENTENCE_TRANSFORMERS: _Sentinel(),
            BACKEND_TURBOQUANT: _Sentinel(),
        }
        for name in ("navigation_code", "navigation_wsp"):
            self.assertEqual(
                resolve_backend_for_collection(
                    name, routing_active=True, available_backends=both,
                ),
                BACKEND_SENTENCE_TRANSFORMERS,
                msg=f"{name} must stay on fp32 (gate-failing)",
            )

    def test_active_routing_keeps_vocabulary_on_fp32(self):
        both = {
            BACKEND_SENTENCE_TRANSFORMERS: _Sentinel(),
            BACKEND_TURBOQUANT: _Sentinel(),
        }
        self.assertEqual(
            resolve_backend_for_collection(
                "navigation_vocabulary",
                routing_active=True,
                available_backends=both,
            ),
            BACKEND_SENTENCE_TRANSFORMERS,
        )

    def test_unlisted_collection_falls_through_to_default(self):
        both = {
            BACKEND_SENTENCE_TRANSFORMERS: _Sentinel(),
            BACKEND_TURBOQUANT: _Sentinel(),
        }
        self.assertEqual(
            resolve_backend_for_collection(
                "navigation_tests",
                routing_active=True,
                available_backends=both,
            ),
            BACKEND_SENTENCE_TRANSFORMERS,
        )

    def test_missing_int8_degrades_to_fp32_when_available(self):
        """WSP 97: never return a backend that is not actually loaded."""
        only_fp32 = {BACKEND_SENTENCE_TRANSFORMERS: _Sentinel()}
        self.assertEqual(
            resolve_backend_for_collection(
                "navigation_code",
                routing_active=True,
                available_backends=only_fp32,
            ),
            BACKEND_SENTENCE_TRANSFORMERS,
        )

    def test_missing_fp32_degrades_to_int8_when_available(self):
        """Symmetric fallback: if the only loaded embedder is int8, use it."""
        only_tq = {BACKEND_TURBOQUANT: _Sentinel()}
        # Vocabulary routes to fp32 under policy, but fp32 is not loaded;
        # the resolver must return the actually-loaded int8 rather than lie.
        self.assertEqual(
            resolve_backend_for_collection(
                "navigation_vocabulary",
                routing_active=True,
                available_backends=only_tq,
            ),
            BACKEND_TURBOQUANT,
        )

    def test_no_available_backends_trusts_policy(self):
        """When the caller does not pass a backends dict (e.g. policy-only
        inspection) the resolver trusts the static policy map."""
        # navigation_code is fp32 under TQ4 conservative policy
        self.assertEqual(
            resolve_backend_for_collection(
                "navigation_code", routing_active=True,
            ),
            BACKEND_SENTENCE_TRANSFORMERS,
        )
        # navigation_symbols is int8 (gate-passing)
        self.assertEqual(
            resolve_backend_for_collection(
                "navigation_symbols", routing_active=True,
            ),
            BACKEND_TURBOQUANT,
        )


class TestBuildCollectionBackendMap(unittest.TestCase):
    """``build_collection_backend_map`` — the dict surfaced on search metadata."""

    def test_inactive_routing_all_fp32(self):
        names = [
            "navigation_code", "navigation_wsp", "navigation_tests",
            "navigation_skills", "navigation_symbols", "navigation_vocabulary",
        ]
        result = build_collection_backend_map(names, routing_active=False)
        self.assertEqual(set(result.values()), {BACKEND_SENTENCE_TRANSFORMERS})
        self.assertEqual(set(result.keys()), set(names))

    def test_active_routing_mixed_map(self):
        """W3/TQ4: Only gate-passing collections (skills, symbols) route to int8."""
        names = [
            "navigation_code", "navigation_wsp", "navigation_tests",
            "navigation_skills", "navigation_symbols", "navigation_vocabulary",
        ]
        both = {
            BACKEND_SENTENCE_TRANSFORMERS: _Sentinel(),
            BACKEND_TURBOQUANT: _Sentinel(),
        }
        result = build_collection_backend_map(
            names, routing_active=True, available_backends=both,
        )
        # Gate-failing collections stay on fp32
        self.assertEqual(result["navigation_code"], BACKEND_SENTENCE_TRANSFORMERS)
        self.assertEqual(result["navigation_wsp"], BACKEND_SENTENCE_TRANSFORMERS)
        self.assertEqual(result["navigation_vocabulary"], BACKEND_SENTENCE_TRANSFORMERS)
        self.assertEqual(result["navigation_tests"], BACKEND_SENTENCE_TRANSFORMERS)
        # Gate-passing collections route to int8
        self.assertEqual(result["navigation_skills"], BACKEND_TURBOQUANT)
        self.assertEqual(result["navigation_symbols"], BACKEND_TURBOQUANT)

    def test_degraded_only_fp32_map_is_all_fp32(self):
        """If int8 failed to load, every collection must truthfully show fp32."""
        names = list(COLLECTION_BACKEND_ROUTING.keys())
        only_fp32 = {BACKEND_SENTENCE_TRANSFORMERS: _Sentinel()}
        result = build_collection_backend_map(
            names, routing_active=True, available_backends=only_fp32,
        )
        self.assertEqual(set(result.values()), {BACKEND_SENTENCE_TRANSFORMERS})

    def test_inactive_routing_int8_only_map_is_all_int8(self):
        """WSP 97 truth-surface: degraded int8-only with inactive routing must report int8."""
        names = [
            "navigation_code", "navigation_wsp", "navigation_tests",
            "navigation_skills", "navigation_symbols", "navigation_vocabulary",
        ]
        only_tq = {BACKEND_TURBOQUANT: _Sentinel()}
        result = build_collection_backend_map(
            names, routing_active=False, available_backends=only_tq,
        )
        self.assertEqual(
            set(result.values()),
            {BACKEND_TURBOQUANT},
            msg="inactive routing with only int8 must truthfully report int8 for all collections",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
