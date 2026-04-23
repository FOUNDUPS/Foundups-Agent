# -*- coding: utf-8 -*-
"""TQ1 retrieval-agreement probe — does int8 drift destabilize ranking?

Cosine drift of 3.65% (mean) is above the 2% "same-model" threshold in the
brief, so we must measure whether the drift actually changes retrieval
outcomes. Uses the 30-query set as both queries and corpus: for each query,
rank the other 29 by cosine similarity with each backend, then compute top-k
agreement (Jaccard on unordered sets, Kendall-tau on ordered ranks).

This is a synthetic probe — it doesn't replace a full ChromaDB-backed A/B on
the real corpus, but it's cheap and it isolates whether ranking stability
survives quantization on text that looks like real HoloIndex queries.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path


def _cosine_matrix(vecs):
    import numpy as np
    arr = np.asarray(vecs, dtype="float32")
    norms = np.linalg.norm(arr, axis=1, keepdims=True).clip(min=1e-12)
    normed = arr / norms
    return normed @ normed.T


def _topk_indices(sim_row, k: int, exclude_self: int) -> list[int]:
    """Return indices of top-k excluding the self index."""
    import numpy as np
    row = sim_row.copy()
    row[exclude_self] = -1e9
    return np.argsort(-row)[:k].tolist()


def _jaccard(a: list[int], b: list[int]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def _kendall_tau_on_common(a: list[int], b: list[int]) -> float:
    """Kendall tau on items in both lists; returns 1.0 if <2 common items."""
    common = [x for x in a if x in b]
    if len(common) < 2:
        return 1.0
    pos_a = {x: i for i, x in enumerate(a)}
    pos_b = {x: i for i, x in enumerate(b)}
    concordant = 0
    discordant = 0
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


def main() -> None:
    baseline_path = Path(__file__).parent / "tq1_baseline_vectors.json"
    int8_path = Path(__file__).parent / "tq1_int8_vectors.json"

    # The int8 bench didn't persist vectors; re-encode here from the cached model.
    import onnxruntime as ort
    from transformers import AutoTokenizer
    import numpy as np
    from holo_index.scripts.benchmarks.tq1_queries import TQ1_QUERIES

    tokenizer = AutoTokenizer.from_pretrained(
        "sentence-transformers/all-MiniLM-L6-v2",
        cache_dir="E:/HoloIndex/models",
    )
    session = ort.InferenceSession(
        "E:/HoloIndex/models/tq1_onnx_int8/model_int8.onnx",
        providers=["CPUExecutionProvider"],
    )
    enc = tokenizer(TQ1_QUERIES, return_tensors="np", padding=True, truncation=True, max_length=256)
    inputs = {k: v for k, v in enc.items() if k in {i.name for i in session.get_inputs()}}
    outs = session.run(None, inputs)
    mask = enc["attention_mask"][..., None].astype("float32")
    summed = (outs[0] * mask).sum(axis=1)
    counts = mask.sum(axis=1).clip(min=1e-9)
    pooled = summed / counts
    norms = np.linalg.norm(pooled, axis=1, keepdims=True).clip(min=1e-12)
    int8_vecs = (pooled / norms).tolist()

    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)
    fp32_vecs = baseline["vectors"]

    sim_fp32 = _cosine_matrix(fp32_vecs)
    sim_int8 = _cosine_matrix(int8_vecs)

    record: dict = {
        "probe": "synthetic_top_k_agreement_on_query_set",
        "n_queries": len(TQ1_QUERIES),
        "note": "each query ranked against the other 29 in both backends",
    }
    for k in (1, 3, 5, 10):
        jaccards = []
        taus = []
        for i in range(len(TQ1_QUERIES)):
            top_a = _topk_indices(sim_fp32[i], k, exclude_self=i)
            top_b = _topk_indices(sim_int8[i], k, exclude_self=i)
            jaccards.append(_jaccard(top_a, top_b))
            taus.append(_kendall_tau_on_common(top_a, top_b))
        record[f"top{k}_jaccard_mean"] = statistics.mean(jaccards)
        record[f"top{k}_jaccard_min"] = min(jaccards)
        record[f"top{k}_exact_match_pct"] = sum(1 for j in jaccards if j == 1.0) / len(jaccards) * 100
        record[f"top{k}_kendall_tau_mean"] = statistics.mean(taus)

    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
