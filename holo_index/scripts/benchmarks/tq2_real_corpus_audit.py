# -*- coding: utf-8 -*-
"""TQ2 — fp32 vs int8 real-corpus retrieval audit for HoloIndex.

Purpose:
    Produce hard-metrics evidence on whether the HIA3 TurboQuant ONNX int8
    backend can be promoted from ``backend_quality="experimental"`` to
    default. Replaces TQ1's synthetic query-vs-query agreement with a
    real-corpus A/B against the live ChromaDB collections that HoloIndex
    serves in production.

Method (WSP 97, truthful-assessment):

    1. fp32 side = ``SentenceTransformer('all-MiniLM-L6-v2')`` — the exact
       model that built the live corpus. This is the production baseline
       and the ground-truth-by-definition for any retrieval disagreement.
    2. int8 side = ``TurboQuantEmbedder`` from
       ``holo_index.core.turboquant_backend``, unchanged from HIA3.
    3. Corpus stays fp32-indexed (no reindex; HIA3 deferred full reindex
       explicitly). The audit only swaps the *query* embedding backend.
       This mirrors the real-world behavior of flipping
       ``HOLO_USE_TURBOQUANT=1`` in production.
    4. For each (collection, query) pair, compute top-k ids from both
       backends and emit:
         - top-1 agreement (exact match on the top-1 id)
         - top-5 agreement (set-equality on top-5 ids)
         - Jaccard@1/3/5/10
         - Kendall tau on overlapping ranked items
         - p50 / p95 latency per side (encode + chroma query)
         - cold / warm timings
    5. Flag every query where top-1 differs and write to
       ``tq2_divergent_queries.json`` for manual review.
    6. Apply the TQ2 promotion gate and emit
       ``tq2_metrics.json`` + ``TQ2_FP32_INT8_REAL_CORPUS_AUDIT.md``.

TQ1 provenance:
    Query set and agreement helpers adapted from commit ``bf7c18069``
    (``chore: commit prior session research artifacts and benchmarks``) —
    specifically ``holo_index/scripts/benchmarks/tq1_queries.py`` and
    ``tq1_retrieval_agreement.py``. That commit is not reachable from
    ``origin/main``, so this slice commits a baseline snapshot at
    ``docs/audits/holoindex_turboquant/TQ1_BASELINE_SNAPSHOT.md``.

Tokenizer note:
    The existing TQ1 int8 export dir at
    ``E:/HoloIndex/models/tq1_onnx_int8/`` ships ``model_int8.onnx`` +
    ``config.json`` but no tokenizer files. TurboQuantEmbedder therefore
    reports ``is_available()=False`` on a bare install. The audit script
    uses a staging dir that co-locates ``model_int8.onnx`` with the
    tokenizer pulled from the HuggingFace cache snapshot. No mutation of
    the original TQ1 export dir.

Usage::

    python holo_index/scripts/benchmarks/tq2_real_corpus_audit.py

Outputs (all committed on the research branch):

    docs/audits/holoindex_turboquant/tq2_metrics.json
    docs/audits/holoindex_turboquant/tq2_divergent_queries.json

WSP: WSP 15 (P0 scoring), WSP 97 (truth distinction).
"""
from __future__ import annotations

import json
import os
import shutil
import statistics
import time
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Query set — TQ1-derived, frozen for TQ2 reproducibility
# ---------------------------------------------------------------------------
# Source: bf7c18069:holo_index/scripts/benchmarks/tq1_queries.py
# Inlined here so TQ2 does not depend on an untracked-on-main file.

TQ2_QUERIES: list[str] = [
    "WSP 97 truth distinction protocol",
    "WSP 50 pre-action verification",
    "WSP 22 ModLog update requirements",
    "WSP 87 size limits for modules",
    "WSP 49 module structure conventions",
    "skill registry loader orchestration",
    "SKILLz compliance frontmatter requirements",
    "orphan capability scanner",
    "pfMALL data isolation model",
    "FoundUp agent market CABR engine",
    "FAM DAEmon heartbeat and breadcrumbs",
    "ai_overseer M2M compression sentinel",
    "ai overseer role detection",
    "preflight resolution ironclaw preflight",
    "HOLO_SKIP_MODEL offline bootstrap",
    "HoloIndex retrieval_mode lexical fallback",
    "ChromaDB persistent client vector collections",
    "sentence transformer model load timeout",
    "HOLO_USE_TURBOQUANT environment switch",
    "embedding_backend search metadata",
    "antifaFM broadcaster 24/7 headless launch",
    "YouTube stream resolver livestream detection",
    "modules/ai_intelligence/agent_permissions",
    "AgentPermissionManager.request_permission",
    "modules/platform_integration/youtube_auth",
    "autonomous_refactoring.py WSP 77",
    "how does 0102 recall patterns from 0201",
    "token budget for DAE pattern memory",
    "zen coding principle code is remembered",
    "pytest HOLO_SKIP_MODEL lexical-only tests",
]
assert len(TQ2_QUERIES) == 30

# Sentinels are queries whose fp32 top-1 is semantically unambiguous.
# Any int8 divergence on these = blocker.
SENTINEL_QUERIES: list[str] = [
    "WSP 97 System Execution Prompting Protocol",  # CFZ3: canonical title
    "WSP 87 size limits for modules",
    "AgentPermissionManager.request_permission",
    "modules/ai_intelligence/agent_permissions",
    "modules/platform_integration/youtube_auth",
    "HOLO_USE_TURBOQUANT environment switch",
]

CHROMA_PATH = "E:/HoloIndex/vectors"
HF_SNAPSHOT_DIR = (
    "E:/HoloIndex/models/models--sentence-transformers--all-MiniLM-L6-v2/snapshots"
)
TQ1_EXPORT_DIR = Path("E:/HoloIndex/models/tq1_onnx_int8")
TQ2_STAGING_DIR = Path("E:/HoloIndex/models/tq2_int8_staging")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    k = (len(s) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 1.0


def _kendall_tau_on_common(a: list[str], b: list[str]) -> float:
    common = [x for x in a if x in b]
    if len(common) < 2:
        return 1.0
    pos_a = {x: i for i, x in enumerate(a)}
    pos_b = {x: i for i, x in enumerate(b)}
    concordant = discordant = 0
    for i in range(len(common)):
        for j in range(i + 1, len(common)):
            x, y = common[i], common[j]
            da = pos_a[x] - pos_a[y]
            db = pos_b[x] - pos_b[y]
            if da * db > 0:
                concordant += 1
            elif da * db < 0:
                discordant += 1
    total = concordant + discordant
    return (concordant - discordant) / total if total else 1.0


def _stage_int8_with_tokenizer() -> Path:
    """Create a staging dir with ``model_int8.onnx`` + tokenizer files.

    TurboQuantEmbedder needs both the ONNX model and tokenizer in a single
    dir (its ``_tokenizer_files_present`` check). The TQ1 export dir has
    the model but not tokenizer; the HF snapshot has tokenizer but not the
    int8 model. Stage them together, idempotently.
    """
    TQ2_STAGING_DIR.mkdir(parents=True, exist_ok=True)
    model_src = TQ1_EXPORT_DIR / "model_int8.onnx"
    model_dst = TQ2_STAGING_DIR / "model_int8.onnx"
    if not model_src.exists():
        raise SystemExit(f"TQ2: missing int8 model at {model_src}")
    if not model_dst.exists() or model_dst.stat().st_size != model_src.stat().st_size:
        shutil.copy2(model_src, model_dst)

    snapshot_root = Path(HF_SNAPSHOT_DIR)
    snapshots = [p for p in snapshot_root.iterdir() if p.is_dir()] if snapshot_root.exists() else []
    if not snapshots:
        raise SystemExit(f"TQ2: no HF snapshot at {HF_SNAPSHOT_DIR}")
    snap = snapshots[0]
    for name in ("tokenizer.json", "tokenizer_config.json", "vocab.txt", "special_tokens_map.json"):
        src = snap / name
        if src.exists():
            dst = TQ2_STAGING_DIR / name
            if not dst.exists():
                shutil.copy2(src, dst)
    return TQ2_STAGING_DIR


# ---------------------------------------------------------------------------
# Corpus freeze preflight (CFZ1)
# ---------------------------------------------------------------------------
CORPUS_MANIFEST = Path(__file__).parent.parent.parent.parent / "docs/audits/holoindex_turboquant/corpus_freeze_manifest.json"


# ---------------------------------------------------------------------------
# Main audit
# ---------------------------------------------------------------------------

def main() -> int:
    # CFZ1: Enforce corpus stability before audit
    from holo_index.scripts.benchmarks.tq_corpus_freeze import preflight_check
    print("[TQ2] preflight — corpus freeze verification")
    preflight_check(CORPUS_MANIFEST)

    print("[TQ2] preflight — staging int8 + tokenizer")
    staging = _stage_int8_with_tokenizer()
    os.environ["HOLO_TURBOQUANT_MODEL_DIR"] = str(staging)

    print("[TQ2] loading fp32 SentenceTransformer (production baseline)")
    t0 = time.perf_counter()
    from sentence_transformers import SentenceTransformer
    fp32 = SentenceTransformer("all-MiniLM-L6-v2", cache_folder="E:/HoloIndex/models")
    fp32_cold = time.perf_counter() - t0

    print("[TQ2] loading int8 TurboQuantEmbedder (HIA3)")
    t0 = time.perf_counter()
    from holo_index.core.turboquant_backend import TurboQuantEmbedder
    if not TurboQuantEmbedder.is_available():
        raise SystemExit("TQ2: TurboQuantEmbedder.is_available() False after staging — abort")
    int8 = TurboQuantEmbedder()
    int8._ensure_loaded()
    int8_cold = time.perf_counter() - t0

    print("[TQ2] opening Chroma client")
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
            print(f"[TQ2] collection {name}: ERROR {e}")

    print(f"[TQ2] collections in audit: {list(collections.keys())}")
    print(f"[TQ2] counts: {counts}")

    fp32_encode_times: list[float] = []
    int8_encode_times: list[float] = []
    fp32_query_times: list[float] = []
    int8_query_times: list[float] = []

    per_collection: dict[str, dict[str, Any]] = {}
    divergent: list[dict[str, Any]] = []
    sentinel_results: list[dict[str, Any]] = []

    K_VALUES = (1, 3, 5, 10)

    for col_name, col in collections.items():
        print(f"[TQ2] auditing {col_name} ({counts[col_name]} docs)")
        top1_matches = 0
        top5_set_matches = 0
        jaccards = {k: [] for k in K_VALUES}
        taus: list[float] = []

        for q in TQ2_QUERIES:
            t = time.perf_counter()
            v_fp32 = fp32.encode(q, show_progress_bar=False)
            fp32_encode_times.append(time.perf_counter() - t)

            t = time.perf_counter()
            v_int8 = int8.encode(q, show_progress_bar=False)
            int8_encode_times.append(time.perf_counter() - t)

            # Chroma accepts python lists; both vectors are 384-dim float32
            t = time.perf_counter()
            r_fp32 = col.query(query_embeddings=[v_fp32.tolist()], n_results=10)
            fp32_query_times.append(time.perf_counter() - t)

            t = time.perf_counter()
            r_int8 = col.query(query_embeddings=[v_int8.tolist()], n_results=10)
            int8_query_times.append(time.perf_counter() - t)

            ids_fp32 = r_fp32["ids"][0]
            ids_int8 = r_int8["ids"][0]

            if ids_fp32 and ids_int8 and ids_fp32[0] == ids_int8[0]:
                top1_matches += 1
            if set(ids_fp32[:5]) == set(ids_int8[:5]):
                top5_set_matches += 1

            for k in K_VALUES:
                jaccards[k].append(_jaccard(ids_fp32[:k], ids_int8[:k]))
            taus.append(_kendall_tau_on_common(ids_fp32, ids_int8))

            if ids_fp32 and ids_int8 and ids_fp32[0] != ids_int8[0]:
                divergent.append({
                    "collection": col_name,
                    "query": q,
                    "fp32_top1": ids_fp32[0],
                    "int8_top1": ids_int8[0],
                    "fp32_top5": ids_fp32[:5],
                    "int8_top5": ids_int8[:5],
                })

            if q in SENTINEL_QUERIES:
                sentinel_results.append({
                    "collection": col_name,
                    "query": q,
                    "fp32_top1": ids_fp32[0] if ids_fp32 else None,
                    "int8_top1": ids_int8[0] if ids_int8 else None,
                    "top1_agree": bool(ids_fp32 and ids_int8 and ids_fp32[0] == ids_int8[0]),
                })

        n = len(TQ2_QUERIES)
        per_collection[col_name] = {
            "doc_count": counts[col_name],
            "queries": n,
            "top1_agreement_pct": top1_matches / n * 100.0,
            "top5_set_agreement_pct": top5_set_matches / n * 100.0,
            "jaccard_mean": {f"k={k}": statistics.mean(jaccards[k]) for k in K_VALUES},
            "jaccard_min": {f"k={k}": min(jaccards[k]) for k in K_VALUES},
            "kendall_tau_mean": statistics.mean(taus),
            "kendall_tau_min": min(taus),
        }

    # Aggregate metrics
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

    # Promotion gate
    GATE_TOP1 = 90.0
    GATE_TOP5 = 95.0
    promote = (
        overall_top1 >= GATE_TOP1
        and overall_top5 >= GATE_TOP5
        and sentinels_pass
    )
    decision = "PROMOTE_INT8" if promote else "HOLD_INT8"
    blockers: list[str] = []
    if overall_top1 < GATE_TOP1:
        blockers.append(f"overall top-1 agreement {overall_top1:.1f}% < {GATE_TOP1}%")
    if overall_top5 < GATE_TOP5:
        blockers.append(f"overall top-5 set-agreement {overall_top5:.1f}% < {GATE_TOP5}%")
    if not sentinels_pass:
        failed = [r for r in sentinel_results if not r["top1_agree"]]
        blockers.append(f"{len(failed)} sentinel query regressions")

    metrics = {
        "slice": "TQ2_FP32_INT8_REAL_CORPUS_AUDIT_PHASE1",
        "chroma_path": CHROMA_PATH,
        "collection_counts": counts,
        "audited_collections": list(collections.keys()),
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
            "int8_encode_p50": _percentile(int8_encode_times, 50) * 1000,
            "int8_encode_p95": _percentile(int8_encode_times, 95) * 1000,
            "fp32_query_p50": _percentile(fp32_query_times, 50) * 1000,
            "fp32_query_p95": _percentile(fp32_query_times, 95) * 1000,
            "int8_query_p50": _percentile(int8_query_times, 50) * 1000,
            "int8_query_p95": _percentile(int8_query_times, 95) * 1000,
        },
        "cold_load_sec": {
            "fp32_sentence_transformer": fp32_cold,
            "int8_turboquant_embedder": int8_cold,
        },
        "decision": decision,
        "blockers": blockers,
    }

    out_dir = Path(__file__).resolve().parents[2] / "docs"
    # TQ2 artifacts live under repo-root/docs/audits/, not holo_index/docs/.
    repo_root = Path(__file__).resolve().parents[3]
    audit_dir = repo_root / "docs" / "audits" / "holoindex_turboquant"
    audit_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = audit_dir / "tq2_metrics.json"
    div_path = audit_dir / "tq2_divergent_queries.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    div_path.write_text(json.dumps({
        "n_divergent": len(divergent),
        "divergent": divergent,
    }, indent=2), encoding="utf-8")

    print(f"[TQ2] metrics: {metrics_path}")
    print(f"[TQ2] divergent: {div_path}")
    print(f"[TQ2] overall top-1 = {overall_top1:.1f}%  top-5 = {overall_top5:.1f}%  sentinels_pass={sentinels_pass}")
    print(f"[TQ2] decision = {decision}")
    if blockers:
        print(f"[TQ2] blockers: {blockers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
