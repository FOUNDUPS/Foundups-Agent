# -*- coding: utf-8 -*-
"""HoloIndex per-collection embedding backend routing (TQ3 slice).

TQ2 (docs/audits/holoindex_turboquant/TQ2_FP32_INT8_REAL_CORPUS_AUDIT.md)
measured that the HIA3 TurboQuant ONNX int8 backend is retrieval-equivalent
to fp32 on every production navigation collection *except*
``navigation_vocabulary`` (30-doc corpus; top-5 set-agreement 43.3% vs the
95% gate). Rather than holding int8 off entirely or promoting it globally,
TQ3 adds per-collection routing: int8 where TQ2 proved equivalence, fp32
where it did not.

Contract (WSP 97 truth distinction):

  * Routing is **opt-in**: inactive unless ``HOLO_USE_TURBOQUANT=1``.
  * Routing is **safe**: inactive unless *both* backends loaded cleanly.
  * The fp32 ``SentenceTransformer`` path is always treated as the
    authoritative baseline (it built every row currently in ChromaDB).
  * Collections not listed in the routing map fall back to the fp32
    baseline. Adding a collection to the int8 lane is a deliberate
    policy choice that MUST be backed by a gate re-run (see TQ3 report).
"""
from __future__ import annotations

from typing import Dict, Optional

# Canonical backend keys. Must match ``embedding_backend`` values the rest
# of holo_index surfaces (see holo_index.core.search_engine).
BACKEND_SENTENCE_TRANSFORMERS = "sentence_transformers"
BACKEND_TURBOQUANT = "turboquant_onnx_int8"

# Per-collection routing policy (TQ3 Phase 1).
#
# Every entry here MUST have TQ-series evidence supporting the choice. Today:
#   * code / wsp / skills / symbols  -> int8 (TQ2 measured 100% top-1 +
#                                              100% top-5 + Jaccard 1.0 +
#                                              Kendall tau 1.0 across
#                                              23,801 docs total).
#   * vocabulary                     -> fp32 (TQ2 measured 86.7% top-1 and
#                                              43.3% top-5 on 30 docs;
#                                              blocker for int8 promotion).
#
# ``navigation_tests`` is intentionally omitted because TQ2 could not
# audit it (empty collection at audit time). It therefore falls through
# to the safe default via :func:`resolve_backend_for_collection`.
COLLECTION_BACKEND_ROUTING: Dict[str, str] = {
    "navigation_code": BACKEND_TURBOQUANT,
    "navigation_wsp": BACKEND_TURBOQUANT,
    "navigation_skills": BACKEND_TURBOQUANT,
    "navigation_symbols": BACKEND_TURBOQUANT,
    "navigation_vocabulary": BACKEND_SENTENCE_TRANSFORMERS,
}

# Default backend for collections not explicitly listed above. Stays on
# fp32 because fp32 is the embedder that built every live collection —
# any unaudited collection must default to the authoritative baseline.
DEFAULT_BACKEND: str = BACKEND_SENTENCE_TRANSFORMERS


def resolve_backend_for_collection(
    collection_name: str,
    routing_active: bool,
    available_backends: Optional[Dict[str, object]] = None,
) -> str:
    """Return the ``embedding_backend`` key to use for *collection_name*.

    Args:
        collection_name: Name of the Chroma collection being queried.
        routing_active: True only when ``HOLO_USE_TURBOQUANT=1`` *and*
            both fp32 and int8 backends loaded cleanly on this
            HoloIndex instance.
        available_backends: Optional dict of loaded backends keyed by
            backend name. If provided, the resolver guarantees it will
            only return a key that is present — if the routed choice is
            not loaded, it falls back to whatever single backend IS
            loaded (or to ``DEFAULT_BACKEND`` as a last resort).

    Returns:
        One of the ``BACKEND_*`` constants. Caller is responsible for
        mapping that key to a concrete embedder instance.

    WSP 97: The resolver MUST NOT silently hide a missing backend. If
    the routing map says ``turboquant`` but int8 is unavailable, the
    returned value reflects the actual backend used (fp32 fallback), so
    downstream metadata surfaces the truth.
    """
    # Even with routing inactive, we must honor available_backends — if only
    # int8 loaded (degraded mode), return int8 truthfully instead of claiming
    # fp32 (WSP 97: never lie about the backend that will actually encode).
    if not routing_active:
        if available_backends is not None and DEFAULT_BACKEND not in available_backends:
            # Degraded mode: fp32 unavailable. Return whatever IS loaded.
            for key in (BACKEND_TURBOQUANT,):
                if key in available_backends:
                    return key
        return DEFAULT_BACKEND
    requested = COLLECTION_BACKEND_ROUTING.get(collection_name, DEFAULT_BACKEND)
    if available_backends is not None and requested not in available_backends:
        for key in (DEFAULT_BACKEND, BACKEND_TURBOQUANT):
            if key in available_backends:
                return key
        return DEFAULT_BACKEND
    return requested


def build_collection_backend_map(
    collection_names,
    routing_active: bool,
    available_backends: Optional[Dict[str, object]] = None,
) -> Dict[str, str]:
    """Return the full ``{collection_name: backend_key}`` map.

    Emitted on every search response so callers can verify per-collection
    backend truth without re-deriving the routing policy.
    """
    return {
        name: resolve_backend_for_collection(
            name, routing_active, available_backends
        )
        for name in collection_names
    }
