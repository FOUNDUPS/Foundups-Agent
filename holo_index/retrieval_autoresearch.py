"""Generation-bound retrieval benchmark and verification primitives.

This module evaluates pinned HoloIndex generations. It never indexes, changes
ranking configuration, promotes a generation, or writes benchmark outcomes.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping, Sequence

from holo_index.query_receipt import (
    FRESHNESS_STATES,
    SCHEMA_VERSION as QUERY_RECEIPT_SCHEMA,
    build_query_receipt,
    digest_json,
)


CORPUS_SCHEMA = "holoindex_retrieval_corpus.v1"
RUN_SCHEMA = "holoindex_retrieval_benchmark_run.v1"
VERIFICATION_SCHEMA = "holoindex_retrieval_benchmark_verification.v1"
DECISION_SCHEMA = "holoindex_retrieval_autoresearch_decision.v1"
DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
SHA_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
QueryRunner = Callable[[str, int, "RetrievalCandidateBinding"], Mapping[str, Any]]


@dataclass(frozen=True)
class RetrievalRelevance:
    """One graded path judgment for a benchmark query."""

    path: str
    grade: int = 1


@dataclass(frozen=True)
class RetrievalCase:
    """One immutable retrieval benchmark case."""

    case_id: str
    query: str
    relevance: tuple[RetrievalRelevance, ...]


@dataclass(frozen=True)
class RetrievalCorpus:
    """Train/held-out query corpus with deterministic split digests."""

    schema_version: str
    train_cases: tuple[RetrievalCase, ...]
    heldout_cases: tuple[RetrievalCase, ...]
    train_digest: str
    heldout_digest: str
    corpus_digest: str


@dataclass(frozen=True)
class RetrievalCandidateBinding:
    """Immutable generation and ranking configuration under evaluation."""

    candidate_id: str
    generation_id: str
    freshness_receipt_digest: str
    repo_head_sha: str
    repo_root_digest: str
    config_digest: str
    ranker_digest: str
    runtime_environment_digest: str


def retrieval_candidate_id(
    *,
    generation_id: str,
    freshness_receipt_digest: str,
    repo_head_sha: str,
    repo_root_digest: str,
    config_digest: str,
    ranker_digest: str,
    runtime_environment_digest: str,
) -> str:
    """Derive candidate identity from the currently sealed source bindings."""

    return digest_json({
        "generation_id": generation_id,
        "freshness_receipt_digest": freshness_receipt_digest,
        "repo_head_sha": repo_head_sha,
        "repo_root_digest": repo_root_digest,
        "config_digest": config_digest,
        "ranker_digest": ranker_digest,
        "runtime_environment_digest": runtime_environment_digest,
    })


def _clean_path(value: Any) -> str:
    raw = str(value or "")
    path = raw.strip()
    parts = path.split("/")
    if (
        not path
        or raw != path
        or "\\" in path
        or path.startswith("./")
        or path.startswith("/")
        or re.match(r"^[A-Za-z]:", path)
        or any(part in {"", ".", ".."} for part in parts)
        or any(unicodedata.category(char).startswith("C") for char in path)
    ):
        raise ValueError("invalid_retrieval_path")
    return path


def _canonical_case(case: RetrievalCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "query": case.query,
        "relevance": [asdict(item) for item in case.relevance],
    }


def _split_digest(cases: Sequence[RetrievalCase]) -> str:
    return digest_json([_canonical_case(case) for case in cases])


def _validate_case(case: RetrievalCase) -> RetrievalCase:
    case_id = str(case.case_id or "").strip()
    query = str(case.query or "").strip()
    if not case_id or not query or not case.relevance:
        raise ValueError("invalid_retrieval_case")
    if any(type(item.grade) is not int for item in case.relevance):
        raise ValueError("invalid_relevance_judgment")
    normalized = tuple(
        RetrievalRelevance(_clean_path(item.path), item.grade)
        for item in case.relevance
    )
    if any(not item.path or item.grade < 1 or item.grade > 3 for item in normalized):
        raise ValueError("invalid_relevance_judgment")
    if len({item.path for item in normalized}) != len(normalized):
        raise ValueError("duplicate_relevance_path")
    return RetrievalCase(case_id=case_id, query=query, relevance=normalized)


def build_retrieval_corpus(
    *,
    train_cases: Sequence[RetrievalCase] = (),
    heldout_cases: Sequence[RetrievalCase],
) -> RetrievalCorpus:
    """Build a deterministic corpus and reject train/held-out leakage."""

    train = tuple(_validate_case(case) for case in train_cases)
    heldout = tuple(_validate_case(case) for case in heldout_cases)
    if not heldout:
        raise ValueError("heldout_cases_required")
    all_cases = train + heldout
    if len({case.case_id.casefold() for case in all_cases}) != len(all_cases):
        raise ValueError("duplicate_case_id")
    train_queries = [case.query.casefold() for case in train]
    heldout_queries = [case.query.casefold() for case in heldout]
    if len(set(train_queries)) != len(train_queries) or len(set(heldout_queries)) != len(heldout_queries):
        raise ValueError("duplicate_benchmark_query")
    if set(train_queries).intersection(heldout_queries):
        raise ValueError("train_heldout_query_overlap")
    train_digest, heldout_digest = _split_digest(train), _split_digest(heldout)
    corpus_payload = {
        "schema_version": CORPUS_SCHEMA,
        "train_digest": train_digest,
        "heldout_digest": heldout_digest,
    }
    return RetrievalCorpus(
        CORPUS_SCHEMA, train, heldout, train_digest, heldout_digest,
        digest_json(corpus_payload),
    )


def _validate_binding(binding: RetrievalCandidateBinding) -> None:
    values = asdict(binding)
    if not all(str(value or "").strip() for value in values.values()):
        raise ValueError("incomplete_candidate_binding")
    for name in (
        "freshness_receipt_digest", "config_digest", "ranker_digest",
        "runtime_environment_digest",
    ):
        if not DIGEST_PATTERN.fullmatch(str(values[name])):
            raise ValueError(f"invalid_{name}")
    if not DIGEST_PATTERN.fullmatch(binding.candidate_id):
        raise ValueError("invalid_candidate_id")
    if not DIGEST_PATTERN.fullmatch(binding.generation_id):
        raise ValueError("invalid_generation_id")
    if not SHA_PATTERN.fullmatch(binding.repo_head_sha):
        raise ValueError("invalid_repo_head_sha")
    expected_id = retrieval_candidate_id(
        **{
            name: value
            for name, value in values.items()
            if name != "candidate_id"
        }
    )
    if binding.candidate_id != expected_id:
        raise ValueError("candidate_id_binding_mismatch")


def _query_receipt_integrity_ok(receipt: Mapping[str, Any]) -> bool:
    payload = {key: value for key, value in receipt.items() if key != "receipt_id"}
    return (
        receipt.get("schema_version") == QUERY_RECEIPT_SCHEMA
        and receipt.get("receipt_id") == digest_json(payload)
    )


def _validate_query_receipt(
    receipt: Mapping[str, Any], binding: RetrievalCandidateBinding
) -> None:
    checks = (
        _query_receipt_integrity_ok(receipt),
        receipt.get("ok") is True,
        receipt.get("freshness") in FRESHNESS_STATES,
        receipt.get("freshness_generation_id") == binding.generation_id,
        receipt.get("freshness_receipt_digest") == binding.freshness_receipt_digest,
        receipt.get("repo_head_sha") == binding.repo_head_sha,
        receipt.get("repo_root_digest") == binding.repo_root_digest,
        receipt.get("retrieval_runtime_ranker_digest") == binding.ranker_digest,
        receipt.get("runtime_environment_digest")
        == binding.runtime_environment_digest,
        receipt.get("no_holoindex_reindex_performed") is True,
        receipt.get("index_gap_detected") is False,
    )
    if not all(checks):
        raise ValueError("invalid_generation_bound_query_receipt")


def _ranked_paths(receipt: Mapping[str, Any], k: int) -> tuple[str, ...]:
    hits = receipt.get("hits")
    if isinstance(hits, (str, bytes)) or not isinstance(hits, Sequence):
        return ()
    paths = tuple(
        _clean_path(hit.get("path"))
        for hit in hits[:k]
        if isinstance(hit, Mapping) and _clean_path(hit.get("path"))
    )
    if len(set(paths)) != len(paths):
        raise ValueError("duplicate_ranked_path")
    return paths


def _dcg(grades: Sequence[int]) -> float:
    return sum(
        (2**grade - 1) / math.log2(rank + 2)
        for rank, grade in enumerate(grades)
    )


def _query_metrics(
    case: RetrievalCase, ranked_paths: Sequence[str], *, k: int
) -> dict[str, float]:
    grades = {item.path: item.grade for item in case.relevance}
    observed = [grades.get(path, 0) for path in ranked_paths]
    relevant = sum(1 for grade in observed if grade > 0)
    first_rank = next((index + 1 for index, grade in enumerate(observed) if grade), 0)
    ideal = sorted(grades.values(), reverse=True)[:k]
    ideal_dcg = _dcg(ideal)
    return {
        "recall_at_k": round(relevant / len(grades), 8),
        "reciprocal_rank": round(1 / first_rank, 8) if first_rank else 0.0,
        "ndcg_at_k": round(_dcg(observed) / ideal_dcg, 8) if ideal_dcg else 0.0,
    }


def _latency(value: Any) -> float:
    try:
        latency = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_query_latency") from exc
    if not math.isfinite(latency) or latency < 0:
        raise ValueError("invalid_query_latency")
    return round(latency, 3)


def _aggregate(evaluations: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    count = len(evaluations)
    if not count:
        raise ValueError("benchmark_evaluations_required")
    latencies = sorted(float(item["latency_ms"]) for item in evaluations)
    p95_index = min(count - 1, max(0, math.ceil(count * 0.95) - 1))
    return {
        "recall_at_k": round(sum(item["recall_at_k"] for item in evaluations) / count, 8),
        "mrr": round(sum(item["reciprocal_rank"] for item in evaluations) / count, 8),
        "ndcg_at_k": round(sum(item["ndcg_at_k"] for item in evaluations) / count, 8),
        "mean_latency_ms": round(sum(latencies) / count, 3),
        "p95_latency_ms": round(latencies[p95_index], 3),
    }


def _split_cases(corpus: RetrievalCorpus, split: str) -> tuple[RetrievalCase, ...]:
    if split == "train":
        if not corpus.train_cases:
            raise ValueError("train_cases_required")
        return corpus.train_cases
    if split == "heldout":
        return corpus.heldout_cases
    raise ValueError("unsupported_benchmark_split")


def _run_case(
    case: RetrievalCase,
    *,
    binding: RetrievalCandidateBinding,
    query_runner: QueryRunner,
    k: int,
) -> dict[str, Any]:
    raw = query_runner(case.query, k, binding)
    if not isinstance(raw, Mapping):
        raise ValueError("invalid_query_runner_result")
    if raw.get("no_holoindex_reindex_performed") is not True:
        raise ValueError("query_runner_reindex_boundary_unproven")
    receipt = build_query_receipt(
        source="holoindex_retrieval_autoresearch",
        source_class="holoindex",
        query=case.query,
        result=raw,
        require_generation=True,
        hit_limit=k,
    )
    _validate_query_receipt(receipt, binding)
    paths = _ranked_paths(receipt, k)
    return {
        "case_id": case.case_id,
        "query_digest": digest_json(case.query),
        "query_receipt": receipt,
        "candidate_binding_digest": digest_json(asdict(binding)),
        "ranked_paths": list(paths),
        "latency_ms": _latency(receipt.get("observed_latency_ms")),
        **_query_metrics(case, paths, k=k),
    }


def run_generation_bound_benchmark(
    *,
    corpus: RetrievalCorpus,
    split: str,
    binding: RetrievalCandidateBinding,
    query_runner: QueryRunner,
    k: int = 5,
    corpus_source_digest: str = "",
) -> dict[str, Any]:
    """Evaluate one pinned generation without mutating or promoting it."""

    _validate_binding(binding)
    if k < 1 or k > 20:
        raise ValueError("invalid_benchmark_k")
    if corpus_source_digest and not DIGEST_PATTERN.fullmatch(corpus_source_digest):
        raise ValueError("invalid_corpus_source_digest")
    cases = _split_cases(corpus, split)
    evaluations = [
        _run_case(case, binding=binding, query_runner=query_runner, k=k)
        for case in cases
    ]
    payload = {
        "schema_version": RUN_SCHEMA,
        "corpus_digest": corpus.corpus_digest,
        "corpus_source_digest": corpus_source_digest,
        "split": split,
        "split_digest": _split_digest(cases),
        "candidate_binding": asdict(binding),
        "k": k,
        "metrics": _aggregate(evaluations),
        "evaluations": evaluations,
        "no_holoindex_reindex_performed": True,
        "no_generation_promotion_performed": True,
    }
    return {**payload, "receipt_id": digest_json(payload)}


def _evaluation_by_case(run: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    values = run.get("evaluations")
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError("invalid_benchmark_evaluations")
    result = {
        str(item.get("case_id") or ""): item
        for item in values
        if isinstance(item, Mapping)
    }
    if not result or len(result) != len(values) or "" in result:
        raise ValueError("invalid_benchmark_evaluations")
    return result


def _verify_evaluation(
    case: RetrievalCase,
    evaluation: Mapping[str, Any],
    *,
    binding: RetrievalCandidateBinding,
    k: int,
) -> dict[str, Any]:
    if evaluation.get("query_digest") != digest_json(case.query):
        raise ValueError("query_digest_mismatch")
    if evaluation.get("candidate_binding_digest") != digest_json(asdict(binding)):
        raise ValueError("candidate_binding_digest_mismatch")
    receipt = evaluation.get("query_receipt")
    if not isinstance(receipt, Mapping):
        raise ValueError("missing_query_receipt")
    _validate_query_receipt(receipt, binding)
    paths = _ranked_paths(receipt, k)
    if list(paths) != list(evaluation.get("ranked_paths") or []):
        raise ValueError("ranked_paths_mismatch")
    recomputed = {
        "latency_ms": _latency(receipt.get("observed_latency_ms")),
        **_query_metrics(case, paths, k=k),
    }
    if any(evaluation.get(key) != value for key, value in recomputed.items()):
        raise ValueError("benchmark_evaluation_metric_mismatch")
    return recomputed


def _binding_from_mapping(value: Any) -> RetrievalCandidateBinding:
    if not isinstance(value, Mapping):
        raise ValueError("missing_candidate_binding")
    try:
        binding = RetrievalCandidateBinding(**{
            name: str(value.get(name) or "")
            for name in RetrievalCandidateBinding.__dataclass_fields__
        })
    except TypeError as exc:
        raise ValueError("invalid_candidate_binding") from exc
    _validate_binding(binding)
    return binding


def _run_integrity_ok(run: Mapping[str, Any]) -> bool:
    payload = {key: value for key, value in run.items() if key != "receipt_id"}
    return run.get("schema_version") == RUN_SCHEMA and run.get("receipt_id") == digest_json(payload)


def _verify_run_or_raise(
    corpus: RetrievalCorpus,
    run: Mapping[str, Any],
    *,
    verifier_digest: str,
    expected_corpus_source_digest: str,
    expected_candidate_binding: RetrievalCandidateBinding,
) -> None:
    if not DIGEST_PATTERN.fullmatch(str(verifier_digest or "")):
        raise ValueError("invalid_verifier_digest")
    if not _run_integrity_ok(run):
        raise ValueError("benchmark_run_integrity_mismatch")
    if run.get("corpus_digest") != corpus.corpus_digest:
        raise ValueError("benchmark_corpus_mismatch")
    source_digest = str(run.get("corpus_source_digest") or "")
    if source_digest and not DIGEST_PATTERN.fullmatch(source_digest):
        raise ValueError("invalid_corpus_source_digest")
    if expected_corpus_source_digest and source_digest != expected_corpus_source_digest:
        raise ValueError("benchmark_corpus_source_mismatch")
    cases = _split_cases(corpus, str(run.get("split") or ""))
    if run.get("split_digest") != _split_digest(cases):
        raise ValueError("benchmark_split_mismatch")
    binding = _binding_from_mapping(run.get("candidate_binding"))
    if binding != expected_candidate_binding:
        raise ValueError("benchmark_candidate_binding_mismatch")
    k = int(run.get("k"))
    if k < 1 or k > 20:
        raise ValueError("invalid_benchmark_k")
    if run.get("no_holoindex_reindex_performed") is not True:
        raise ValueError("benchmark_reindex_boundary_unproven")
    if run.get("no_generation_promotion_performed") is not True:
        raise ValueError("benchmark_promotion_boundary_unproven")
    indexed = _evaluation_by_case(run)
    if set(indexed) != {case.case_id for case in cases}:
        raise ValueError("benchmark_case_set_mismatch")
    recomputed = [
        _verify_evaluation(case, indexed[case.case_id], binding=binding, k=k)
        for case in cases
    ]
    if _aggregate(recomputed) != run.get("metrics"):
        raise ValueError("benchmark_metrics_mismatch")


def verify_generation_bound_benchmark(
    *,
    corpus: RetrievalCorpus,
    run: Mapping[str, Any],
    verifier_digest: str,
    expected_candidate_binding: RetrievalCandidateBinding,
    expected_corpus_source_digest: str = "",
) -> dict[str, Any]:
    """Deterministically recompute query and aggregate metrics from receipts."""

    reasons: list[str] = []
    try:
        _verify_run_or_raise(
            corpus, run, verifier_digest=verifier_digest,
            expected_corpus_source_digest=expected_corpus_source_digest,
            expected_candidate_binding=expected_candidate_binding,
        )
    except (TypeError, ValueError) as exc:
        reasons.append(str(exc))
    payload = {
        "schema_version": VERIFICATION_SCHEMA,
        "benchmark_run_receipt_id": str(run.get("receipt_id") or ""),
        "verifier_digest": str(verifier_digest or ""),
        "candidate_binding_digest": digest_json(asdict(expected_candidate_binding)),
        "accepted": not reasons,
        "rejection_reasons": reasons,
        "integrity_evidence_only": True,
        "not_promotion_authority": True,
    }
    return {**payload, "receipt_id": digest_json(payload)}


def _verification_matches(
    supplied: Mapping[str, Any], recomputed: Mapping[str, Any]
) -> bool:
    """Require the supplied envelope to equal deterministic re-verification."""

    return supplied == recomputed and recomputed.get("accepted") is True


def _metric_values(value: Any) -> dict[str, float]:
    if not isinstance(value, Mapping):
        raise ValueError("comparison_metrics_missing")
    metrics: dict[str, float] = {}
    for key in ("recall_at_k", "mrr", "ndcg_at_k", "p95_latency_ms"):
        try:
            metric = float(value.get(key))
        except (TypeError, ValueError) as exc:
            raise ValueError("comparison_metrics_invalid") from exc
        if not math.isfinite(metric) or metric < 0:
            raise ValueError("comparison_metrics_invalid")
        metrics[key] = metric
    return metrics


def _base_comparison_reasons(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    baseline_verification: Mapping[str, Any],
    candidate_verification: Mapping[str, Any],
    recomputed_baseline: Mapping[str, Any],
    recomputed_candidate: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    checks = (
        (_run_integrity_ok(baseline), "baseline_run_integrity_mismatch"),
        (_run_integrity_ok(candidate), "candidate_run_integrity_mismatch"),
        (_verification_matches(baseline_verification, recomputed_baseline), "baseline_reverification_invalid"),
        (_verification_matches(candidate_verification, recomputed_candidate), "candidate_reverification_invalid"),
    )
    reasons.extend(reason for accepted, reason in checks if not accepted)
    for key in ("corpus_digest", "corpus_source_digest", "split", "split_digest", "k"):
        if baseline.get(key) != candidate.get(key):
            reasons.append(f"comparison_{key}_mismatch")
    if baseline.get("split") != "heldout":
        reasons.append("recommendation_requires_heldout_split")
    if not DIGEST_PATTERN.fullmatch(str(baseline.get("corpus_source_digest") or "")):
        reasons.append("recommendation_requires_tracked_corpus_source")
    if baseline.get("candidate_binding") == candidate.get("candidate_binding"):
        reasons.append("candidate_not_distinct")
    return reasons


def _metric_comparison_reasons(
    baseline_metrics: Mapping[str, float],
    candidate_metrics: Mapping[str, float],
    *,
    min_ndcg_gain: float,
    max_latency_regression_ratio: float,
) -> list[str]:
    reasons: list[str] = []
    quality_keys = ("recall_at_k", "mrr", "ndcg_at_k")
    if any(candidate_metrics[key] < baseline_metrics[key] for key in quality_keys):
        reasons.append("candidate_quality_regression")
    if candidate_metrics["ndcg_at_k"] - baseline_metrics["ndcg_at_k"] < min_ndcg_gain:
        reasons.append("candidate_ndcg_gain_below_policy")
    baseline_latency = max(baseline_metrics["p95_latency_ms"], 0.001)
    if candidate_metrics["p95_latency_ms"] > baseline_latency * (1 + max_latency_regression_ratio):
        reasons.append("candidate_latency_regression")
    strict_quality = any(candidate_metrics[key] > baseline_metrics[key] for key in quality_keys)
    strict_latency = candidate_metrics["p95_latency_ms"] < baseline_metrics["p95_latency_ms"]
    if not strict_quality and not strict_latency:
        reasons.append("candidate_no_measured_improvement")
    return reasons


def _comparison_policy(
    min_ndcg_gain: Any, max_latency_regression_ratio: Any
) -> tuple[float, float, list[str]]:
    try:
        gain = float(min_ndcg_gain)
        latency = float(max_latency_regression_ratio)
    except (TypeError, ValueError):
        return 0.0, 0.0, ["invalid_comparison_policy"]
    if any(not math.isfinite(value) or value < 0 for value in (gain, latency)):
        return 0.0, 0.0, ["invalid_comparison_policy"]
    return gain, latency, []


def _recomputed_verifications(
    corpus: RetrievalCorpus,
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    verifier_digest: str,
    corpus_source_digest: str,
    baseline_binding: RetrievalCandidateBinding,
    candidate_binding: RetrievalCandidateBinding,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    common = {
        "corpus": corpus,
        "verifier_digest": verifier_digest,
        "expected_corpus_source_digest": corpus_source_digest,
    }
    return (
        verify_generation_bound_benchmark(
            run=baseline,
            expected_candidate_binding=baseline_binding,
            **common,
        ),
        verify_generation_bound_benchmark(
            run=candidate,
            expected_candidate_binding=candidate_binding,
            **common,
        ),
    )


def _comparison_receipt(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    baseline_verification: Mapping[str, Any],
    candidate_verification: Mapping[str, Any],
    reasons: Sequence[str],
) -> dict[str, Any]:
    payload = {
        "schema_version": DECISION_SCHEMA,
        "baseline_run_receipt_id": str(baseline.get("receipt_id") or ""),
        "candidate_run_receipt_id": str(candidate.get("receipt_id") or ""),
        "baseline_verification_receipt_id": str(baseline_verification.get("receipt_id") or ""),
        "candidate_verification_receipt_id": str(candidate_verification.get("receipt_id") or ""),
        "outcome": (
            "MEASURED_BETTER_ON_REGRESSION_CORPUS"
            if not reasons
            else "KEEP_BASELINE"
        ),
        "reasons": list(reasons),
        "no_generation_promotion_performed": True,
        "independent_promotion_evaluation_required": True,
        "public_regression_corpus_not_independent_heldout": True,
        "integrity_evidence_only": True,
        "not_promotion_authority": True,
    }
    return {**payload, "receipt_id": digest_json(payload)}


def compare_verified_runs(
    *,
    corpus: RetrievalCorpus,
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    baseline_verification: Mapping[str, Any],
    candidate_verification: Mapping[str, Any],
    verifier_digest: str,
    expected_corpus_source_digest: str,
    expected_baseline_binding: RetrievalCandidateBinding,
    expected_candidate_binding: RetrievalCandidateBinding,
    min_ndcg_gain: float = 0.0,
    max_latency_regression_ratio: float = 0.10,
) -> dict[str, Any]:
    """Recommend a candidate after deterministic held-out non-regression."""

    recomputed_baseline, recomputed_candidate = _recomputed_verifications(
        corpus, baseline, candidate, verifier_digest,
        expected_corpus_source_digest, expected_baseline_binding,
        expected_candidate_binding,
    )
    reasons = _base_comparison_reasons(
        baseline,
        candidate,
        baseline_verification,
        candidate_verification,
        recomputed_baseline,
        recomputed_candidate,
    )
    gain, latency_ratio, policy_reasons = _comparison_policy(
        min_ndcg_gain, max_latency_regression_ratio
    )
    reasons.extend(policy_reasons)
    try:
        baseline_metrics = _metric_values(baseline.get("metrics"))
        candidate_metrics = _metric_values(candidate.get("metrics"))
    except ValueError as exc:
        reasons.append(str(exc))
        baseline_metrics = {"recall_at_k": 0, "mrr": 0, "ndcg_at_k": 0, "p95_latency_ms": 0.001}
        candidate_metrics = {"recall_at_k": 0, "mrr": 0, "ndcg_at_k": 0, "p95_latency_ms": math.inf}
    reasons.extend(_metric_comparison_reasons(
        baseline_metrics,
        candidate_metrics,
        min_ndcg_gain=gain,
        max_latency_regression_ratio=latency_ratio,
    ))
    return _comparison_receipt(
        baseline, candidate, baseline_verification, candidate_verification,
        reasons,
    )


__all__ = [
    "CORPUS_SCHEMA",
    "DECISION_SCHEMA",
    "RUN_SCHEMA",
    "VERIFICATION_SCHEMA",
    "RetrievalCandidateBinding",
    "RetrievalCase",
    "RetrievalCorpus",
    "RetrievalRelevance",
    "build_retrieval_corpus",
    "compare_verified_runs",
    "retrieval_candidate_id",
    "run_generation_bound_benchmark",
    "verify_generation_bound_benchmark",
]
