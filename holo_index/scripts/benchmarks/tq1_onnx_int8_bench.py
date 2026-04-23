# -*- coding: utf-8 -*-
"""TQ1 Option B — ONNX Runtime int8 dynamic quantization of MiniLM-L6-v2.

Pipeline:
  1. Export ``sentence-transformers/all-MiniLM-L6-v2`` to ONNX via optimum.
  2. Apply ``quantize_dynamic`` for int8 weights (activations stay fp32).
  3. Load the quantized model through ``ORTModelForFeatureExtraction``.
  4. Encode the TQ1 query set; compare cosine similarity to baseline.

All exported artifacts go to ``E:/HoloIndex/models/tq1_onnx_int8/`` so
nothing pollutes the repo. Nothing is committed.

WSP 97: measurements are direct. "Option A vs B" distinction: A would be
using ``SentenceTransformer(..., backend="onnx")`` for a pre-exported
ONNX with fp32 weights; B (this script) is the same base model with
*int8* dynamic quantization applied.
"""
from __future__ import annotations

import json
import statistics
import time
from pathlib import Path


EXPORT_DIR = Path("E:/HoloIndex/models/tq1_onnx_int8")
QUANTIZED_PATH = EXPORT_DIR / "model_int8.onnx"
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"


def ensure_export() -> float:
    """Export MiniLM to ONNX and apply dynamic int8 quantization.

    Returns elapsed seconds (0 if already cached).
    """
    if QUANTIZED_PATH.exists():
        return 0.0

    from optimum.onnxruntime import ORTModelForFeatureExtraction
    from onnxruntime.quantization import quantize_dynamic, QuantType

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    # Step 1: export to ONNX fp32
    fp32_dir = EXPORT_DIR / "fp32"
    if not (fp32_dir / "model.onnx").exists():
        model = ORTModelForFeatureExtraction.from_pretrained(MODEL_ID, export=True)
        model.save_pretrained(fp32_dir)

    # Step 2: dynamic int8 quantization (weights only, activations fp32)
    src = fp32_dir / "model.onnx"
    quantize_dynamic(
        model_input=str(src),
        model_output=str(QUANTIZED_PATH),
        weight_type=QuantType.QInt8,
    )
    # Copy tokenizer artifacts alongside
    import shutil
    for name in [
        "tokenizer.json", "tokenizer_config.json", "vocab.txt",
        "special_tokens_map.json", "config.json",
    ]:
        s = fp32_dir / name
        if s.exists():
            shutil.copy(s, EXPORT_DIR / name)
    return time.perf_counter() - t0


def mean_pool_and_normalize(token_embeddings, attention_mask):
    import numpy as np
    mask = attention_mask[..., None].astype("float32")
    summed = (token_embeddings * mask).sum(axis=1)
    counts = mask.sum(axis=1).clip(min=1e-9)
    pooled = summed / counts
    norms = np.linalg.norm(pooled, axis=1, keepdims=True).clip(min=1e-12)
    return pooled / norms


def cosine(a, b) -> float:
    import numpy as np
    a = np.asarray(a, dtype="float32")
    b = np.asarray(b, dtype="float32")
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def main() -> None:
    from holo_index.scripts.benchmarks.tq1_queries import TQ1_QUERIES
    import numpy as np

    record: dict = {
        "option": "B_onnx_runtime_int8_dynamic",
        "model_id": MODEL_ID,
        "quantized_path": str(QUANTIZED_PATH),
    }

    # Deps
    import importlib.metadata as m
    record["deps"] = {
        p: m.version(p) for p in [
            "optimum", "onnxruntime", "onnx", "transformers", "numpy"
        ]
    }

    # Export + quantize (one-time cost)
    t_export = ensure_export()
    record["export_and_quantize_s"] = t_export
    record["export_and_quantize_cached"] = t_export == 0.0

    # Artifact sizes
    if QUANTIZED_PATH.exists():
        record["quantized_size_mb"] = QUANTIZED_PATH.stat().st_size / (1024 * 1024)
    fp32_onnx = EXPORT_DIR / "fp32" / "model.onnx"
    if fp32_onnx.exists():
        record["fp32_onnx_size_mb"] = fp32_onnx.stat().st_size / (1024 * 1024)

    # Cold import + session load (in-process, second run will be warm)
    t0 = time.perf_counter()
    import onnxruntime as ort
    from transformers import AutoTokenizer
    t_import = time.perf_counter() - t0
    record["warm_import_s"] = t_import

    t0 = time.perf_counter()
    # Tokenizer is identical regardless of quantization; load from HF cache.
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID, cache_dir="E:/HoloIndex/models"
    )
    session = ort.InferenceSession(
        str(QUANTIZED_PATH),
        providers=["CPUExecutionProvider"],
    )
    t_load = time.perf_counter() - t0
    record["load_s"] = t_load

    # Encode (single-query latencies)
    single_latencies = []
    vectors = []
    for q in TQ1_QUERIES:
        t0 = time.perf_counter()
        enc = tokenizer(q, return_tensors="np", padding=True, truncation=True, max_length=256)
        inputs = {k: v for k, v in enc.items() if k in {i.name for i in session.get_inputs()}}
        outputs = session.run(None, inputs)
        # First output is token embeddings (last_hidden_state)
        token_embeds = outputs[0]
        pooled = mean_pool_and_normalize(token_embeds, enc["attention_mask"])
        single_latencies.append(time.perf_counter() - t0)
        vectors.append(pooled[0].tolist())

    record["single_query_count"] = len(single_latencies)
    record["single_query_mean_s"] = statistics.mean(single_latencies)
    record["single_query_median_s"] = statistics.median(single_latencies)
    record["single_query_p95_s"] = sorted(single_latencies)[int(0.95 * len(single_latencies))]
    record["single_query_min_s"] = min(single_latencies)
    record["single_query_max_s"] = max(single_latencies)

    # Batch encode
    t0 = time.perf_counter()
    enc_batch = tokenizer(TQ1_QUERIES, return_tensors="np", padding=True, truncation=True, max_length=256)
    inputs_batch = {k: v for k, v in enc_batch.items() if k in {i.name for i in session.get_inputs()}}
    outs = session.run(None, inputs_batch)
    pooled_batch = mean_pool_and_normalize(outs[0], enc_batch["attention_mask"])
    t_batch = time.perf_counter() - t0
    record["batch_30_total_s"] = t_batch
    record["batch_30_per_query_s"] = t_batch / len(TQ1_QUERIES)
    record["vector_dim"] = pooled_batch.shape[1]
    record["vector_dtype"] = str(pooled_batch.dtype)

    # Quality: cosine drift vs fp32 baseline (SAME model, SAME dim -> valid)
    baseline_path = Path(__file__).parent / "tq1_baseline_vectors.json"
    if baseline_path.exists():
        with open(baseline_path, "r", encoding="utf-8") as f:
            baseline = json.load(f)
        assert baseline["queries"] == TQ1_QUERIES, "Query set mismatch vs baseline"
        cosines = [cosine(vectors[i], baseline["vectors"][i]) for i in range(len(vectors))]
        record["cosine_vs_fp32_mean"] = statistics.mean(cosines)
        record["cosine_vs_fp32_median"] = statistics.median(cosines)
        record["cosine_vs_fp32_min"] = min(cosines)
        record["cosine_drift_pct_mean"] = (1.0 - statistics.mean(cosines)) * 100
        record["cosine_drift_pct_max"] = (1.0 - min(cosines)) * 100
    else:
        record["cosine_error"] = "baseline vectors file not found"

    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
