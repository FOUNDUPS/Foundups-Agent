# -*- coding: utf-8 -*-
"""TQ1 baseline benchmark — SentenceTransformer MiniLM float32.

Measures cold-import, model-load, and per-query encode latency for the
current HoloIndex semantic backend. Writes a JSON record to stdout that
the TQ1 report consumes.

Run:
    python -m holo_index.scripts.benchmarks.tq1_baseline_bench > baseline.json

WSP 97: measured values are reported truthfully; estimated values are
labeled as such.
"""
from __future__ import annotations

import json
import os
import platform
import statistics
import subprocess
import sys
import time


def measure_cold_import() -> float:
    """Measure cold import time for sentence_transformers in a fresh subprocess."""
    code = (
        "import time\n"
        "t = time.perf_counter()\n"
        "from sentence_transformers import SentenceTransformer\n"
        "print(time.perf_counter() - t)\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return float(out.stdout.strip())


def main() -> None:
    from holo_index.scripts.benchmarks.tq1_queries import TQ1_QUERIES

    record: dict = {
        "option": "baseline_sentence_transformers_fp32",
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "platform": platform.platform(),
    }

    try:
        import importlib.metadata as m
        record["deps"] = {
            p: m.version(p) for p in [
                "sentence-transformers", "torch", "transformers", "numpy"
            ]
        }
    except Exception as e:
        record["deps_error"] = str(e)

    # Cold import (subprocess — can't be re-timed in-process)
    t_cold = measure_cold_import()
    record["cold_import_s"] = t_cold

    # Warm import + model load
    t0 = time.perf_counter()
    from sentence_transformers import SentenceTransformer
    t_warm_import = time.perf_counter() - t0

    t0 = time.perf_counter()
    model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2",
        cache_folder="E:/HoloIndex/models",
    )
    t_load = time.perf_counter() - t0
    record["warm_import_s"] = t_warm_import
    record["model_load_s"] = t_load

    # Encode latencies — single-query, 30 queries
    from holo_index.scripts.benchmarks.tq1_queries import TQ1_QUERIES
    single_latencies = []
    vectors = []
    for q in TQ1_QUERIES:
        t0 = time.perf_counter()
        vec = model.encode(q, show_progress_bar=False)
        single_latencies.append(time.perf_counter() - t0)
        vectors.append(vec.tolist())

    record["single_query_count"] = len(single_latencies)
    record["single_query_mean_s"] = statistics.mean(single_latencies)
    record["single_query_median_s"] = statistics.median(single_latencies)
    record["single_query_p95_s"] = sorted(single_latencies)[int(0.95 * len(single_latencies))]
    record["single_query_min_s"] = min(single_latencies)
    record["single_query_max_s"] = max(single_latencies)

    # Batch encode (cheap measurement)
    t0 = time.perf_counter()
    batch_vecs = model.encode(TQ1_QUERIES, show_progress_bar=False, batch_size=32)
    t_batch = time.perf_counter() - t0
    record["batch_30_total_s"] = t_batch
    record["batch_30_per_query_s"] = t_batch / len(TQ1_QUERIES)

    # Vector shape sanity
    record["vector_dim"] = len(vectors[0])
    record["vector_dtype"] = str(batch_vecs.dtype)

    # Persist baseline vectors for later cosine-drift comparison
    baseline_path = os.path.join(
        os.path.dirname(__file__), "tq1_baseline_vectors.json"
    )
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump({"queries": TQ1_QUERIES, "vectors": vectors}, f)
    record["baseline_vectors_path"] = baseline_path

    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
