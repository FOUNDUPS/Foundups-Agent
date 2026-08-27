"""Acceptance and adversarial tests for retrieval AutoResearch evidence."""

from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from holo_index.query_receipt import digest_json
from holo_index.retrieval_autoresearch import (
    RetrievalCandidateBinding,
    RetrievalCase,
    RetrievalRelevance,
    build_retrieval_corpus,
    compare_verified_runs,
    retrieval_candidate_id,
    run_generation_bound_benchmark,
    verify_generation_bound_benchmark,
)


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64
SHA = "1" * 40
ROOT_DIGEST = "sha256:" + "d" * 64


def _case(case_id: str, query: str, path: str, grade: int = 3) -> RetrievalCase:
    return RetrievalCase(case_id, query, (RetrievalRelevance(path, grade),))


def _corpus():
    return build_retrieval_corpus(
        train_cases=(_case("train-1", "training query", "train.py"),),
        heldout_cases=(
            _case("held-1", "first heldout", "alpha.py"),
            _case("held-2", "second heldout", "beta.py"),
        ),
    )


def _binding(candidate: str = "baseline", generation: str = "gen-a"):
    ranker_digest = digest_json({"ranker": candidate})
    fields = {
        "generation_id": digest_json({"generation": generation}),
        "freshness_receipt_digest": DIGEST_A,
        "repo_head_sha": SHA,
        "repo_root_digest": ROOT_DIGEST,
        "config_digest": DIGEST_B,
        "ranker_digest": ranker_digest,
        "runtime_environment_digest": digest_json({"runtime": candidate}),
    }
    return RetrievalCandidateBinding(
        candidate_id=retrieval_candidate_id(**fields),
        **fields,
    )


def _runner(paths: dict[str, list[str]], latency: float = 10.0):
    def run(query: str, limit: int, binding: RetrievalCandidateBinding):
        hits = [
            {"path": path, "title": path, "score": 1.0 - index / 10}
            for index, path in enumerate(paths.get(query, ()))
        ][:limit]
        return {
            "ok": True,
            "query": query,
            "freshness": "CURRENT",
            "hits": hits,
            "raw_result": {"code_hits": hits},
            "freshness_generation_id": binding.generation_id,
            "freshness_receipt_digest": binding.freshness_receipt_digest,
            "repo_head_sha": binding.repo_head_sha,
            "repo_root_digest": binding.repo_root_digest,
            "retrieval_runtime_ranker_digest": binding.ranker_digest,
            "runtime_environment_digest": binding.runtime_environment_digest,
            "latency_ms": latency,
            "index_gap_detected": False,
            "stale_reasons": [],
            "no_holoindex_reindex_performed": True,
        }

    return run


def _run(candidate: str = "baseline", latency: float = 10.0):
    return run_generation_bound_benchmark(
        corpus=_corpus(),
        split="heldout",
        binding=_binding(candidate, f"gen-{candidate}"),
        query_runner=_runner({
            "first heldout": ["alpha.py"],
            "second heldout": ["beta.py"],
        }, latency),
        k=5,
        corpus_source_digest=DIGEST_A,
    )


def _verify(run, expected_binding=None):
    binding = expected_binding or RetrievalCandidateBinding(**run["candidate_binding"])
    return verify_generation_bound_benchmark(
        corpus=_corpus(), run=run, verifier_digest=DIGEST_B,
        expected_candidate_binding=binding,
    )


def _compare(baseline, candidate, **kwargs):
    expected_baseline = kwargs.pop(
        "expected_baseline_binding",
        RetrievalCandidateBinding(**baseline["candidate_binding"]),
    )
    expected_candidate = kwargs.pop(
        "expected_candidate_binding",
        RetrievalCandidateBinding(**candidate["candidate_binding"]),
    )
    return compare_verified_runs(
        corpus=_corpus(),
        baseline=baseline,
        candidate=candidate,
        baseline_verification=kwargs.pop(
            "baseline_verification", _verify(baseline)
        ),
        candidate_verification=kwargs.pop(
            "candidate_verification", _verify(candidate)
        ),
        verifier_digest=DIGEST_B,
        expected_corpus_source_digest=DIGEST_A,
        expected_baseline_binding=expected_baseline,
        expected_candidate_binding=expected_candidate,
        **kwargs,
    )


def _resign(mapping: dict) -> None:
    mapping["receipt_id"] = digest_json({
        key: value for key, value in mapping.items() if key != "receipt_id"
    })


def test_corpus_has_deterministic_split_and_corpus_digests():
    assert _corpus() == _corpus()
    assert _corpus().train_digest != _corpus().heldout_digest


def test_corpus_rejects_train_heldout_leakage():
    with pytest.raises(ValueError, match="train_heldout_query_overlap"):
        build_retrieval_corpus(
            train_cases=(_case("a", "same", "a.py"),),
            heldout_cases=(_case("b", "same", "b.py"),),
        )


def test_corpus_rejects_duplicate_query_within_split():
    with pytest.raises(ValueError, match="duplicate_benchmark_query"):
        build_retrieval_corpus(heldout_cases=(
            _case("a", "same", "a.py"),
            _case("b", "same", "b.py"),
        ))


def test_corpus_rejects_traversal_relevance_path():
    with pytest.raises(ValueError, match="invalid_retrieval_path"):
        build_retrieval_corpus(
            heldout_cases=(_case("a", "query", "../outside.py"),)
        )


@pytest.mark.parametrize("grade", [0, 4])
def test_corpus_rejects_invalid_relevance_grade(grade: int):
    with pytest.raises(ValueError, match="invalid_relevance_judgment"):
        build_retrieval_corpus(heldout_cases=(_case("a", "q", "a.py", grade),))


@pytest.mark.parametrize("grade", [True, 1.5, "3"])
def test_corpus_rejects_non_integer_relevance_grade(grade):
    with pytest.raises(ValueError, match="invalid_relevance_judgment"):
        build_retrieval_corpus(heldout_cases=(_case("a", "q", "a.py", grade),))


def test_corpus_rejects_control_character_path():
    with pytest.raises(ValueError, match="invalid_retrieval_path"):
        build_retrieval_corpus(
            heldout_cases=(_case("a", "query", "safe.py\nother.py"),)
        )


@pytest.mark.parametrize("path", ["./alpha.py", "dir\\alpha.py", " alpha.py"])
def test_corpus_rejects_noncanonical_path_spelling(path: str):
    with pytest.raises(ValueError, match="invalid_retrieval_path"):
        build_retrieval_corpus(heldout_cases=(_case("a", "query", path),))


def test_benchmark_emits_generation_bound_query_receipts_and_metrics():
    run = _run()
    assert run["metrics"] == {
        "recall_at_k": 1.0,
        "mrr": 1.0,
        "ndcg_at_k": 1.0,
        "mean_latency_ms": 10.0,
        "p95_latency_ms": 10.0,
    }
    assert all(
        item["query_receipt"]["freshness_generation_id"]
        == digest_json({"generation": "gen-baseline"})
        for item in run["evaluations"]
    )
    assert run["no_holoindex_reindex_performed"] is True
    assert run["no_generation_promotion_performed"] is True


def test_benchmark_rejects_generation_mismatch():
    runner = _runner({"first heldout": ["alpha.py"], "second heldout": ["beta.py"]})

    def mismatched(query, limit, binding):
        result = dict(runner(query, limit, binding))
        result["freshness_generation_id"] = "other"
        return result

    with pytest.raises(ValueError, match="invalid_generation_bound_query_receipt"):
        run_generation_bound_benchmark(
            corpus=_corpus(), split="heldout", binding=_binding(),
            query_runner=mismatched,
        )


def test_benchmark_rejects_duplicate_ranked_path():
    with pytest.raises(ValueError, match="duplicate_ranked_path"):
        run_generation_bound_benchmark(
            corpus=_corpus(),
            split="heldout",
            binding=_binding(),
            query_runner=_runner({
                "first heldout": ["alpha.py", "alpha.py"],
                "second heldout": ["beta.py"],
            }),
        )


def test_ndcg_uses_k_not_returned_hit_count_for_ideal_ranking():
    corpus = build_retrieval_corpus(heldout_cases=(RetrievalCase(
        "graded",
        "graded query",
        (RetrievalRelevance("best.py", 3), RetrievalRelevance("lower.py", 2)),
    ),))
    run = run_generation_bound_benchmark(
        corpus=corpus,
        split="heldout",
        binding=_binding(),
        query_runner=_runner({"graded query": ["lower.py"]}),
        k=5,
        corpus_source_digest=DIGEST_A,
    )
    assert run["metrics"]["ndcg_at_k"] == 0.33735197


def test_benchmark_preserves_relevant_hit_beyond_legacy_top_eight():
    corpus = build_retrieval_corpus(
        heldout_cases=(_case("rank-nine", "deep query", "target.py"),)
    )
    paths = [f"decoy-{index}.py" for index in range(8)] + ["target.py"]
    run = run_generation_bound_benchmark(
        corpus=corpus,
        split="heldout",
        binding=_binding(),
        query_runner=_runner({"deep query": paths}),
        k=20,
        corpus_source_digest=DIGEST_A,
    )
    assert run["metrics"]["recall_at_k"] == 1.0
    assert run["evaluations"][0]["ranked_paths"][8] == "target.py"


@pytest.mark.parametrize("field,value", [
    ("freshness_receipt_digest", DIGEST_C),
    ("repo_head_sha", "2" * 40),
    ("index_gap_detected", True),
    ("no_holoindex_reindex_performed", False),
])
def test_benchmark_rejects_untrusted_query_binding(field: str, value):
    runner = _runner({"first heldout": ["alpha.py"], "second heldout": ["beta.py"]})

    def changed(query, limit, binding):
        result = dict(runner(query, limit, binding))
        result[field] = value
        return result

    expected = (
        "query_runner_reindex_boundary_unproven"
        if field == "no_holoindex_reindex_performed"
        else "invalid_generation_bound_query_receipt"
    )
    with pytest.raises(ValueError, match=expected):
        run_generation_bound_benchmark(
            corpus=_corpus(), split="heldout", binding=_binding(),
            query_runner=changed,
        )


def test_verifier_accepts_valid_round_trip():
    verification = _verify(_run())
    assert verification["accepted"] is True
    assert verification["rejection_reasons"] == []


def test_verifier_rejects_tampered_metric_even_when_outer_receipt_recomputed():
    run = copy.deepcopy(_run())
    run["metrics"]["mrr"] = 0.5
    _resign(run)
    verification = _verify(run)
    assert verification["accepted"] is False
    assert "benchmark_metrics_mismatch" in verification["rejection_reasons"]


def test_verifier_rejects_latency_changed_outside_query_receipt():
    run = copy.deepcopy(_run())
    run["evaluations"][0]["latency_ms"] = 0.001
    run["metrics"]["mean_latency_ms"] = 5.001
    _resign(run)
    verification = _verify(run)
    assert verification["accepted"] is False
    assert "benchmark_evaluation_metric_mismatch" in verification["rejection_reasons"]


@pytest.mark.parametrize("field,value", [
    ("latency_ms", 0.001),
    ("recall_at_k", 0.0),
    ("reciprocal_rank", 0.0),
    ("ndcg_at_k", 0.0),
])
def test_verifier_rejects_tampered_per_query_metric(field: str, value: float):
    run = copy.deepcopy(_run())
    run["evaluations"][0][field] = value
    _resign(run)
    verification = _verify(run)
    assert verification["accepted"] is False
    assert "benchmark_evaluation_metric_mismatch" in verification["rejection_reasons"]


def test_verifier_rejects_tampered_query_receipt_and_ranked_paths():
    run = copy.deepcopy(_run())
    evaluation = run["evaluations"][0]
    evaluation["query_receipt"]["hits"][0]["path"] = "attacker.py"
    evaluation["ranked_paths"] = ["attacker.py"]
    _resign(run)
    verification = _verify(run)
    assert verification["accepted"] is False
    assert "invalid_generation_bound_query_receipt" in verification["rejection_reasons"]


def test_verifier_rejects_changed_corpus():
    changed = build_retrieval_corpus(
        heldout_cases=(_case("other", "other query", "other.py"),)
    )
    verification = verify_generation_bound_benchmark(
        corpus=changed, run=_run(), verifier_digest=DIGEST_B,
        expected_candidate_binding=_binding(),
    )
    assert verification["accepted"] is False
    assert "benchmark_corpus_mismatch" in verification["rejection_reasons"]


def test_verifier_rejects_candidate_metadata_changed_after_execution():
    run = copy.deepcopy(_run())
    expected = RetrievalCandidateBinding(**run["candidate_binding"])
    run["candidate_binding"]["config_digest"] = DIGEST_C
    _resign(run)
    verification = _verify(run, expected_binding=expected)
    assert verification["accepted"] is False
    assert "candidate_id_binding_mismatch" in verification["rejection_reasons"]


def test_verifier_rejects_removed_no_promotion_attestation():
    run = copy.deepcopy(_run())
    run["no_generation_promotion_performed"] = False
    _resign(run)
    verification = _verify(run)
    assert verification["accepted"] is False
    assert "benchmark_promotion_boundary_unproven" in verification["rejection_reasons"]


def test_compare_promotes_verified_non_regressing_candidate():
    baseline, candidate = _run("base", 10.0), _run("candidate", 9.0)
    decision = _compare(
        baseline=baseline,
        candidate=candidate,
        baseline_verification=_verify(baseline),
        candidate_verification=_verify(candidate),
    )
    assert decision["outcome"] == "MEASURED_BETTER_ON_REGRESSION_CORPUS"
    assert decision["no_generation_promotion_performed"] is True
    assert decision["independent_promotion_evaluation_required"] is True


def test_compare_keeps_baseline_on_quality_regression():
    baseline = _run("base")
    candidate = run_generation_bound_benchmark(
        corpus=_corpus(), split="heldout", binding=_binding("candidate", "gen-candidate"),
        query_runner=_runner({"first heldout": ["alpha.py"], "second heldout": []}),
        corpus_source_digest=DIGEST_A,
    )
    decision = _compare(
        baseline=baseline,
        candidate=candidate,
        baseline_verification=_verify(baseline),
        candidate_verification=_verify(candidate),
    )
    assert decision["outcome"] == "KEEP_BASELINE"
    assert "candidate_quality_regression" in decision["reasons"]


def test_compare_rejects_forged_verification():
    baseline, candidate = _run("base"), _run("candidate")
    forged = dict(_verify(candidate))
    forged["accepted"] = False
    decision = _compare(
        baseline=baseline,
        candidate=candidate,
        baseline_verification=_verify(baseline),
        candidate_verification=forged,
    )
    assert decision["outcome"] == "KEEP_BASELINE"
    assert "candidate_reverification_invalid" in decision["reasons"]


def test_compare_recomputes_after_attacker_resigns_run_and_verification():
    baseline, candidate = _run("base"), copy.deepcopy(_run("candidate"))
    expected = RetrievalCandidateBinding(**candidate["candidate_binding"])
    candidate["candidate_binding"]["repo_root_digest"] = DIGEST_C
    _resign(candidate)
    forged = _verify(
        candidate,
        expected_binding=RetrievalCandidateBinding(
            **candidate["candidate_binding"]
        ),
    )
    assert forged["accepted"] is False
    forged["accepted"] = True
    forged["rejection_reasons"] = []
    _resign(forged)

    decision = _compare(
        baseline,
        candidate,
        candidate_verification=forged,
        expected_candidate_binding=expected,
    )

    assert decision["outcome"] == "KEEP_BASELINE"
    assert "candidate_reverification_invalid" in decision["reasons"]


def test_compare_does_not_promote_identical_candidate():
    baseline = _run("same")
    decision = _compare(
        baseline=baseline,
        candidate=baseline,
        baseline_verification=_verify(baseline),
        candidate_verification=_verify(baseline),
    )
    assert decision["outcome"] == "KEEP_BASELINE"
    assert "candidate_not_distinct" in decision["reasons"]
    assert "candidate_no_measured_improvement" in decision["reasons"]


def test_compare_invalid_policy_fails_closed():
    baseline, candidate = _run("base", 10.0), _run("candidate", 9.0)
    decision = _compare(
        baseline=baseline,
        candidate=candidate,
        baseline_verification=_verify(baseline),
        candidate_verification=_verify(candidate),
        min_ndcg_gain=-1.0,
    )
    assert decision["outcome"] == "KEEP_BASELINE"
    assert "invalid_comparison_policy" in decision["reasons"]


def test_compare_malformed_policy_fails_closed_without_exception():
    baseline, candidate = _run("base", 10.0), _run("candidate", 9.0)
    decision = _compare(
        baseline=baseline,
        candidate=candidate,
        baseline_verification=_verify(baseline),
        candidate_verification=_verify(candidate),
        max_latency_regression_ratio="not-a-number",
    )
    assert decision["outcome"] == "KEEP_BASELINE"
    assert "invalid_comparison_policy" in decision["reasons"]


def test_compare_requires_tracked_corpus_source():
    baseline = run_generation_bound_benchmark(
        corpus=_corpus(), split="heldout", binding=_binding("base", "gen-base"),
        query_runner=_runner({
            "first heldout": ["alpha.py"], "second heldout": ["beta.py"],
        }),
    )
    candidate = copy.deepcopy(baseline)
    candidate["candidate_binding"]["candidate_id"] = digest_json({"candidate": "other"})
    candidate["candidate_binding"]["generation_id"] = digest_json({"generation": "other"})
    candidate["metrics"]["p95_latency_ms"] = 9.0
    candidate["evaluations"][0]["query_receipt"]["freshness_generation_id"] = (
        candidate["candidate_binding"]["generation_id"]
    )
    _resign(candidate)
    decision = _compare(
        baseline=baseline, candidate=candidate,
        baseline_verification=_verify(baseline),
        candidate_verification=_verify(candidate),
    )
    assert decision["outcome"] == "KEEP_BASELINE"
    assert "recommendation_requires_tracked_corpus_source" in decision["reasons"]


def test_binding_rejects_arbitrary_digest_shaped_candidate_id():
    binding = _binding()
    forged = RetrievalCandidateBinding(
        candidate_id=DIGEST_C,
        generation_id=binding.generation_id,
        freshness_receipt_digest=binding.freshness_receipt_digest,
        repo_head_sha=binding.repo_head_sha,
        repo_root_digest=binding.repo_root_digest,
        config_digest=binding.config_digest,
        ranker_digest=binding.ranker_digest,
        runtime_environment_digest=binding.runtime_environment_digest,
    )
    with pytest.raises(ValueError, match="candidate_id_binding_mismatch"):
        run_generation_bound_benchmark(
            corpus=_corpus(),
            split="heldout",
            binding=forged,
            query_runner=_runner({}),
        )


def test_runtime_modules_have_no_index_or_process_mutation_surface():
    root = Path(__file__).resolve().parents[1]
    paths = [
        root / "retrieval_autoresearch.py",
        root.parent / "modules" / "ai_intelligence" / "ai_overseer" / "src"
        / "m2m_holo_retrieval_benchmark.py",
        root.parent / "modules" / "ai_intelligence" / "ai_overseer" / "src"
        / "m2m_holo_retrieval_grade_gate.py",
    ]
    banned_imports = {"subprocess"}
    banned_calls = {"system", "popen", "index_code_entries", "index_wsp_entries"}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            node.names[0].name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom)) and node.names
        }
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert not banned_imports.intersection(imports)
        assert not banned_calls.intersection(calls)
