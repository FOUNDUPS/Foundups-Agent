# -*- coding: utf-8 -*-
"""TQ3 — routed (per-collection) retrieval audit for HoloIndex.

Purpose:
    Re-run the TQ2 A/B gate **under per-collection routing**. TQ2 audited
    pure-int8 vs pure-fp32 and returned ``HOLD_INT8`` because
    ``navigation_vocabulary`` (30 docs) drove the overall top-5
    set-agreement to 88.7%, below the 95% gate. Every other collection
    (code/wsp/skills/symbols) scored 100% / 100% / Jaccard 1.0 / Kendall
    tau 1.0 on 23,801 docs combined.

    TQ3 introduces ``holo_index.core.backend_routing``: int8 serves the
    four equivalent collections; fp32 serves ``navigation_vocabulary``.
    The "routed" side of this audit asks: under that policy, does the
    overall retrieval behavior match pure-fp32 well enough to promote
    the routing policy (not the raw int8 backend) to default-ready?

Method (WSP 97 truthful-assessment):

    * fp32 baseline = ``SentenceTransformer('all-MiniLM-L6-v2')``, the
      production baseline that built every Chroma row.
    * Routed side = for each collection, use the backend that
      ``resolve_backend_for_collection`` returns **as if**
      ``routing_active=True`` with both backends loaded. In practice:
        - navigation_code / wsp / skills / symbols -> int8
        - navigation_vocabulary                    -> fp32
        - navigation_tests                         -> fp32 (unlisted)
    * Corpus stays fp32-indexed (same ``HOLD_INT8`` constraint as TQ2).
    * Query set, sentinels, gate, and metric definitions are all frozen
      identical to TQ2 so the routed number is directly comparable.

Promotion gate (same thresholds as TQ2):

    * overall top-1 agreement >= 90%
    * overall top-5 set-agreement >= 95%
    * all sentinel queries: top-1 agrees with fp32

    Emits ``PROMOTE_ROUTING`` or ``HOLD_ROUTING``.

Expected result: PROMOTE_ROUTING. Vocabulary is served by fp32 under
routing, so its 100% self-agreement replaces the 86.7% / 43.3% score
that blocked TQ2. No regression is expected on the other collections.

Usage::

    HOLO_USE_TURBOQUANT=1 python holo_index/scripts/benchmarks/tq3_routed_corpus_audit.py

Outputs:

    docs/audits/holoindex_turboquant/tq3_metrics.json
    docs/audits/holoindex_turboquant/tq3_divergent_queries.json

WSP: WSP 15, WSP 97.
"""
from __future__ import annotations

import json
import os
import statistics
import time
from pathlib import Path
from typing import Any

# Reuse the frozen query set, sentinels, helpers, and staging logic from TQ2
# so TQ3 is a policy-overlay on identical evidence (WSP 97: do not drift the
# measurement tool between slices).
from holo_index.scripts.benchmarks.tq2_real_corpus_audit import (
    CHROMA_PATH,
    SENTINEL_COLLECTION_MAP,  # W3: collection-aware sentinel routing
    SENTINEL_QUERIES,
    TQ2_QUERIES,
    _jaccard,
    _kendall_tau_on_common,
    _percentile,
    _stage_int8_with_tokenizer,
)
from holo_index.core.backend_routing import (
    BACKEND_SENTENCE_TRANSFORMERS,
    BACKEND_TURBOQUANT,
    resolve_backend_for_collection,
)

# CFZ1: Corpus freeze manifest path
CORPUS_MANIFEST = Path(__file__).parent.parent.parent.parent / "docs/audits/holoindex_turboquant/corpus_freeze_manifest.json"


def main() -> int:
    # CFZ1: Enforce corpus stability before audit
    from holo_index.scripts.benchmarks.tq_corpus_freeze import preflight_check
    print("[TQ3] preflight - corpus freeze verification")
    preflight_check(CORPUS_MANIFEST)

    print("[TQ3] preflight - staging int8 + tokenizer")
    staging = _stage_int8_with_tokenizer()
    os.environ["HOLO_TURBOQUANT_MODEL_DIR"] = str(staging)

    print("[TQ3] loading fp32 SentenceTransformer (baseline AND vocabulary backend)")
    t0 = time.perf_counter()
    from sentence_transformers import SentenceTransformer
    fp32 = SentenceTransformer("all-MiniLM-L6-v2", cache_folder="E:/HoloIndex/models")
    fp32_cold = time.perf_counter() - t0

    print("[TQ3] loading int8 TurboQuantEmbedder (routed code/wsp/skills/symbols)")
    t0 = time.perf_counter()
    from holo_index.core.turboquant_backend import TurboQuantEmbedder
    if not TurboQuantEmbedder.is_available():
        raise SystemExit("TQ3: TurboQuantEmbedder.is_available() False after staging - abort")
    int8 = TurboQuantEmbedder()
    int8._ensure_loaded()
    int8_cold = time.perf_counter() - t0

    # Both backends present -> routing would be active in a real HoloIndex.
    embedders = {
        BACKEND_SENTENCE_TRANSFORMERS: fp32,
        BACKEND_TURBOQUANT: int8,
    }

    print("[TQ3] opening Chroma client")
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    target_cols = [
        "navigation_code",
        "navigation_wsp",
        "navigation_tests",
        "navigation_skills",
        "navigation_symbols",
        "navigation_vocabulary",
    ]
    collections: dict[str, Any] = {}
    counts: dict[str, int] = {}
    for name in target_cols:
        try:
            col = client.get_collection(name)
            c = col.count()
            counts[name] = c
            if c > 0:
                collections[name] = col
        except Exception as e:
            counts[name] = -1
            print(f"[TQ3] collection {name}: ERROR {e}")

    # Per-collection backend routing snapshot for this audit (truth surface).
    collection_backend_map = {
        name: resolve_backend_for_collection(
            name, routing_active=True, available_backends=embedders,
        )
        for name in target_cols
    }
    print(f"[TQ3] collections in audit: {list(collections.keys())}")
    print(f"[TQ3] counts: {counts}")
    print(f"[TQ3] routing policy: {collection_backend_map}")

    fp32_encode_times: list[float] = []
    routed_encode_times: list[float] = []
    fp32_query_times: list[float] = []
    routed_query_times: list[float] = []

    per_collection: dict[str, dict[str, Any]] = {}
    divergent: list[dict[str, Any]] = []
    sentinel_results: list[dict[str, Any]] = []

    K_VALUES = (1, 3, 5, 10)

    for col_name, col in collections.items():
        routed_backend_key = collection_backend_map[col_name]
        routed_embedder = embedders[routed_backend_key]
        print(f"[TQ3] auditing {col_name} ({counts[col_name]} docs) via {routed_backend_key}")

        top1_matches = 0
        top5_set_matches = 0
        jaccards = {k: [] for k in K_VALUES}
        taus: list[float] = []

        for q in TQ2_QUERIES:
            t = time.perf_counter()
            v_fp32 = fp32.encode(q, show_progress_bar=False)
            fp32_encode_times.append(time.perf_counter() - t)

            t = time.perf_counter()
            v_routed = routed_embedder.encode(q, show_progress_bar=False)
            routed_encode_times.append(time.perf_counter() - t)

            t = time.perf_counter()
            r_fp32 = col.query(query_embeddings=[v_fp32.tolist()], n_results=10)
            fp32_query_times.append(time.perf_counter() - t)

            t = time.perf_counter()
            r_routed = col.query(query_embeddings=[v_routed.tolist()], n_results=10)
            routed_query_times.append(time.perf_counter() - t)

            ids_fp32 = r_fp32["ids"][0]
            ids_routed = r_routed["ids"][0]

            if ids_fp32 and ids_routed and ids_fp32[0] == ids_routed[0]:
                top1_matches += 1
            if set(ids_fp32[:5]) == set(ids_routed[:5]):
                top5_set_matches += 1

            for k in K_VALUES:
                jaccards[k].append(_jaccard(ids_fp32[:k], ids_routed[:k]))
            taus.append(_kendall_tau_on_common(ids_fp32, ids_routed))

            if ids_fp32 and ids_routed and ids_fp32[0] != ids_routed[0]:
                divergent.append({
                    "collection": col_name,
                    "routed_backend": routed_backend_key,
                    "query": q,
                    "fp32_top1": ids_fp32[0],
                    "routed_top1": ids_routed[0],
                    "fp32_top5": ids_fp32[:5],
                    "routed_top5": ids_routed[:5],
                })

            # W3: Only record sentinel if this collection is a valid target for this query
            if q in SENTINEL_QUERIES:
                target_collections = SENTINEL_COLLECTION_MAP.get(q, [])
                if col_name in target_collections:
                    sentinel_results.append({
                        "collection": col_name,
                        "routed_backend": routed_backend_key,
                        "query": q,
                        "fp32_top1": ids_fp32[0] if ids_fp32 else None,
                        "routed_top1": ids_routed[0] if ids_routed else None,
                        "top1_agree": bool(ids_fp32 and ids_routed and ids_fp32[0] == ids_routed[0]),
                    })

        n = len(TQ2_QUERIES)
        per_collection[col_name] = {
            "doc_count": counts[col_name],
            "routed_backend": routed_backend_key,
            "queries": n,
            "top1_agreement_pct": top1_matches / n * 100.0,
            "top5_set_agreement_pct": top5_set_matches / n * 100.0,
            "jaccard_mean": {f"k={k}": statistics.mean(jaccards[k]) for k in K_VALUES},
            "jaccard_min": {f"k={k}": min(jaccards[k]) for k in K_VALUES},
            "kendall_tau_mean": statistics.mean(taus),
            "kendall_tau_min": min(taus),
        }

    n_total = sum(per_collection[c]["queries"] for c in per_collection)
    overall_top1 = (
        sum(per_collection[c]["top1_agreement_pct"] * per_collection[c]["queries"]
            for c in per_collection) / n_total
        if n_total else 0.0
    )
    overall_top5 = (
        sum(per_collection[c]["top5_set_agreement_pct"] * per_collection[c]["queries"]
            for c in per_collection) / n_total
        if n_total else 0.0
    )
    sentinels_pass = all(r["top1_agree"] for r in sentinel_results) if sentinel_results else False

    GATE_TOP1 = 90.0
    GATE_TOP5 = 95.0
    promote = (
        overall_top1 >= GATE_TOP1
        and overall_top5 >= GATE_TOP5
        and sentinels_pass
    )
    decision = "PROMOTE_ROUTING" if promote else "HOLD_ROUTING"
    blockers: list[str] = []
    if overall_top1 < GATE_TOP1:
        blockers.append(f"overall top-1 agreement {overall_top1:.1f}% < {GATE_TOP1}%")
    if overall_top5 < GATE_TOP5:
        blockers.append(f"overall top-5 set-agreement {overall_top5:.1f}% < {GATE_TOP5}%")
    if not sentinels_pass:
        failed = [r for r in sentinel_results if not r["top1_agree"]]
        blockers.append(f"{len(failed)} sentinel query regressions")

    metrics = {
        "slice": "TQ3_PER_COLLECTION_BACKEND_ROUTING_PHASE1",
        "chroma_path": CHROMA_PATH,
        "collection_counts": counts,
        "audited_collections": list(collections.keys()),
        "routing_policy": collection_backend_map,
        "n_queries": len(TQ2_QUERIES),
        "n_sentinels": len(SENTINEL_QUERIES),
        "gate_thresholds": {
            "top1_agreement_pct": GATE_TOP1,
            "top5_set_agreement_pct": GATE_TOP5,
            "sentinel_top1_required": "all",
        },
        "overall": {
            "top1_agreement_pct": overall_top1,
            "top5_set_agreement_pct": overall_top5,
            "sentinels_pass": sentinels_pass,
            "sentinel_results": sentinel_results,
        },
        "per_collection": per_collection,
        "latency_ms": {
            "fp32_encode_p50": _percentile(fp32_encode_times, 50) * 1000,
            "fp32_encode_p95": _percentile(fp32_encode_times, 95) * 1000,
            "routed_encode_p50": _percentile(routed_encode_times, 50) * 1000,
            "routed_encode_p95": _percentile(routed_encode_times, 95) * 1000,
            "fp32_query_p50": _percentile(fp32_query_times, 50) * 1000,
            "fp32_query_p95": _percentile(fp32_query_times, 95) * 1000,
            "routed_query_p50": _percentile(routed_query_times, 50) * 1000,
            "routed_query_p95": _percentile(routed_query_times, 95) * 1000,
        },
        "cold_load_sec": {
            "fp32_sentence_transformer": fp32_cold,
            "int8_turboquant_embedder": int8_cold,
        },
        "decision": decision,
        "blockers": blockers,
    }

    repo_root = Path(__file__).resolve().parents[3]
    audit_dir = repo_root / "docs" / "audits" / "holoindex_turboquant"
    audit_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = audit_dir / "tq3_metrics.json"
    div_path = audit_dir / "tq3_divergent_queries.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    div_path.write_text(json.dumps({
        "n_divergent": len(divergent),
        "divergent": divergent,
    }, indent=2), encoding="utf-8")

    print(f"[TQ3] metrics: {metrics_path}")
    print(f"[TQ3] divergent: {div_path}")
    print(f"[TQ3] overall top-1 = {overall_top1:.1f}%  top-5 = {overall_top5:.1f}%  sentinels_pass={sentinels_pass}")
    print(f"[TQ3] decision = {decision}")
    if blockers:
        print(f"[TQ3] blockers: {blockers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
