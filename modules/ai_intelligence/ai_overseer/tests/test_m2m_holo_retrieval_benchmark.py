"""Runtime boundary tests for the Holo retrieval benchmark Skillz."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from holo_index.query_receipt import digest_json
from modules.ai_intelligence.ai_overseer.src import m2m_holo_retrieval_benchmark as runtime
from modules.ai_intelligence.ai_overseer.src import m2m_holo_retrieval_grade_gate as grade_gate


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
SHA = "1" * 40
ROOT_DIGEST = "sha256:" + "c" * 64
RANKER_DIGEST = "sha256:" + "d" * 64


def _owner_query(*, repo_root, query, limit):
    del repo_root, limit
    path = "alpha.py" if query == "alpha query" else "beta.py"
    hits = [{"path": path, "title": path, "score": 1.0}]
    return {
        "ok": True,
        "query": query,
        "freshness": "CURRENT",
        "hits": hits,
        "raw_result": {"code_hits": hits},
        "freshness_generation_id": DIGEST_B,
        "freshness_receipt_digest": DIGEST_A,
        "repo_head_sha": SHA,
        "repo_root_digest": ROOT_DIGEST,
        "retrieval_runtime_ranker_digest": RANKER_DIGEST,
        "latency_ms": 5.0,
        "index_gap_detected": False,
        "stale_reasons": [],
        "no_holoindex_reindex_performed": True,
    }


def _replica_binding(*, repo_head_sha: str = SHA):
    return SimpleNamespace(
        generation_id=DIGEST_B,
        canonical_receipt_digest=DIGEST_A,
        canonical_repo_head_sha=repo_head_sha,
        canonical_repo_root_digest=ROOT_DIGEST,
    )


def _replica_route(*, repo_head_sha: str = SHA):
    binding = _replica_binding(repo_head_sha=repo_head_sha)
    return SimpleNamespace(revalidate=lambda: binding)


def _owner_query_once(payload, *, repo_root, query_environment):
    assert query_environment == {"route": "configured"}
    assert payload["retrieval_mode"] == "semantic"
    return _owner_query(
        repo_root=repo_root,
        query=payload["query"],
        limit=payload["limit"],
    )


def _configure(monkeypatch):
    monkeypatch.setattr(
        runtime,
        "build_owner_query_environment",
        lambda: {"route": "configured"},
    )
    monkeypatch.setattr(
        runtime,
        "resolve_holoindex_authority_root",
        lambda repo_root, environment: SimpleNamespace(
            accepted=True,
            error="",
            selected_root=repo_root,
            authority_head_sha=SHA,
            authority_root_digest=ROOT_DIGEST,
        ),
    )
    monkeypatch.setattr(
        runtime,
        "resolve_query_replica_owner_route",
        lambda **_kwargs: _replica_route(),
    )
    monkeypatch.setattr(runtime, "file_digest", lambda path: DIGEST_B)
    monkeypatch.setattr(
        runtime,
        "retrieval_ranker_digest_for_root",
        lambda _root: RANKER_DIGEST,
    )
    monkeypatch.setattr(
        runtime,
        "resolve_holoindex_ssd_path",
        lambda **_kwargs: Path("E:/HoloIndex"),
    )
    monkeypatch.setattr(runtime, "query_holoindex_owner_once", _owner_query_once)
    corpus = runtime.build_retrieval_corpus(heldout_cases=(
        runtime.RetrievalCase(
            "alpha", "alpha query", (runtime.RetrievalRelevance("alpha.py", 3),)
        ),
        runtime.RetrievalCase(
            "beta", "beta query", (runtime.RetrievalRelevance("beta.py", 3),)
        ),
    ))
    monkeypatch.setattr(runtime, "_load_corpus", lambda repo_root: (corpus, DIGEST_B))


def _payload():
    return {"limit": 5}


class _SignatureVerifier:
    def __init__(self, accepted: bool = True) -> None:
        self.accepted = accepted
        self.calls = 0

    def verify(self, receipt, signature_envelope) -> bool:
        self.calls += 1
        return self.accepted and bool(receipt) and bool(signature_envelope)


def _independent_evaluation(public_result, **overrides):
    binding = public_result["benchmark_run"]["candidate_binding"]
    payload = {
        "schema_version": grade_gate.INDEPENDENT_SCHEMA,
        **binding,
        "accepted": True,
        "sealed_corpus_id": "sealed-holo-grade-v1",
        "sealed_corpus_digest": DIGEST_A,
        "sealed_corpus_case_count": 30,
        "corpus_disjoint_from_public_regression": True,
        "proposer_principal_id": "ranker-proposer",
        "evaluator_principal_id": "independent-evaluator",
        "metrics": {
            "recall_at_k": 0.97,
            "mrr": 0.97,
            "ndcg_at_k": 0.97,
            "p95_latency_ms": 4000.0,
        },
        "no_holoindex_reindex_performed": True,
        "no_generation_promotion_performed": True,
    }
    payload.update(overrides)
    return {**payload, "receipt_id": digest_json(payload)}


def _signature_envelope(independent):
    return {
        "signed_receipt_id": independent["receipt_id"],
        "signer_principal_id": independent["evaluator_principal_id"],
        "algorithm": "test-only",
    }


def test_runtime_returns_verified_generation_bound_evidence(monkeypatch, tmp_path: Path):
    _configure(monkeypatch)
    result = runtime.execute_m2m_holo_retrieval_benchmark(
        repo_root=tmp_path, payload=_payload()
    )
    assert result["success"] is True
    assert result["verification"]["accepted"] is True
    assert result["no_holoindex_reindex_performed"] is True
    assert result["no_generation_promotion_performed"] is True
    assert result["no_repository_artifact_written"] is True
    assert list(tmp_path.iterdir()) == []


def test_checked_in_corpus_is_valid_and_split():
    repo_root = Path(__file__).resolve().parents[4]
    corpus, source_digest = runtime._load_corpus(repo_root)

    assert len(corpus.train_cases) == 2
    assert len(corpus.heldout_cases) == 6
    assert corpus.train_digest != corpus.heldout_digest
    assert source_digest.startswith("sha256:")


def test_m2m_sentinel_query_uses_intent_aligned_graded_relevance():
    repo_root = Path(__file__).resolve().parents[4]
    corpus, _source_digest = runtime._load_corpus(repo_root)
    case = next(
        item for item in corpus.heldout_cases
        if item.case_id == "heldout-m2m-compiler"
    )

    assert case.relevance == (
        runtime.RetrievalRelevance(
            "modules/ai_intelligence/ai_overseer/src/"
            "m2m_compression_sentinel.py",
            3,
        ),
        runtime.RetrievalRelevance("prompt/swarm/m2m_compiler.py", 1),
    )


def test_runtime_rejects_reindex_before_query(monkeypatch, tmp_path: Path):
    result = runtime.execute_m2m_holo_retrieval_benchmark(
        repo_root=tmp_path, payload={**_payload(), "reindex": True},
    )
    assert result == {
        "success": False,
        "error": "runtime_reindex_forbidden",
        "no_holoindex_reindex_performed": True,
    }


def test_runtime_rejects_caller_corpus_override(monkeypatch, tmp_path: Path):
    _configure(monkeypatch)
    result = runtime.execute_m2m_holo_retrieval_benchmark(
        repo_root=tmp_path,
        payload={"queries": ["unknown"], "required_paths": {}},
    )
    assert result["success"] is False
    assert result["error"] == "runtime_corpus_override_forbidden"


def test_runtime_fails_closed_on_stale_owner(monkeypatch, tmp_path: Path):
    _configure(monkeypatch)

    def stale(**kwargs):
        result = dict(_owner_query(**kwargs))
        result.update({"freshness": "STALE", "index_gap_detected": True})
        return result

    monkeypatch.setattr(
        runtime,
        "query_holoindex_owner_once",
        lambda payload, *, repo_root, query_environment: stale(
            repo_root=repo_root,
            query=payload["query"],
            limit=payload["limit"],
        ),
    )

    result = runtime.execute_m2m_holo_retrieval_benchmark(
        repo_root=tmp_path, payload=_payload()
    )
    assert result["success"] is False
    assert result["error"] == "invalid_generation_bound_query_receipt"


def test_runtime_rejects_owner_response_for_other_repository(monkeypatch, tmp_path: Path):
    _configure(monkeypatch)

    def wrong_root(**kwargs):
        result = dict(_owner_query(**kwargs))
        result["repo_root_digest"] = "sha256:" + "f" * 64
        return result

    monkeypatch.setattr(
        runtime,
        "query_holoindex_owner_once",
        lambda payload, *, repo_root, query_environment: wrong_root(
            repo_root=repo_root,
            query=payload["query"],
            limit=payload["limit"],
        ),
    )
    result = runtime.execute_m2m_holo_retrieval_benchmark(
        repo_root=tmp_path, payload=_payload()
    )
    assert result["success"] is False
    assert result["error"] == "query_owner_repo_root_mismatch"


def test_runtime_rejects_freshness_receipt_for_other_head(monkeypatch, tmp_path: Path):
    _configure(monkeypatch)
    monkeypatch.setattr(
        runtime,
        "resolve_query_replica_owner_route",
        lambda **_kwargs: _replica_route(repo_head_sha="2" * 40),
    )
    result = runtime.execute_m2m_holo_retrieval_benchmark(
        repo_root=tmp_path, payload=_payload()
    )
    assert result["success"] is False
    assert result["error"] == "query_replica_authority_mismatch"


def test_exact_repository_file_rejects_wrong_case(tmp_path: Path):
    module = tmp_path / "Module.py"
    module.write_text("pass\n", encoding="utf-8")
    assert runtime._exact_file(tmp_path, "Module.py") is True
    assert runtime._exact_file(tmp_path, "module.py") is False


def test_exact_repository_file_rejects_reparse_component(
    monkeypatch, tmp_path: Path
):
    module = tmp_path / "Module.py"
    module.write_text("pass\n", encoding="utf-8")
    monkeypatch.setattr(
        runtime.os.path,
        "isjunction",
        lambda path: Path(path).name == "Module.py",
        raising=False,
    )
    assert runtime._exact_file(tmp_path, "Module.py") is False


def test_candidate_id_is_deterministic(monkeypatch, tmp_path: Path):
    _configure(monkeypatch)
    first, first_environment = runtime._candidate(tmp_path, 5)
    second, second_environment = runtime._candidate(tmp_path, 5)
    assert first == second
    assert first_environment == second_environment == {"route": "configured"}
    assert first.candidate_id == digest_json({
        "generation_id": DIGEST_B,
        "freshness_receipt_digest": DIGEST_A,
        "repo_head_sha": SHA,
        "repo_root_digest": ROOT_DIGEST,
        "config_digest": digest_json({
            "limit": 5,
            "doc_type": "all",
            "retrieval_mode": "semantic",
        }),
        "ranker_digest": RANKER_DIGEST,
    })


def test_runtime_rejects_owner_executing_other_ranker(monkeypatch, tmp_path: Path):
    _configure(monkeypatch)

    def other_ranker(**kwargs):
        result = dict(_owner_query(**kwargs))
        result["retrieval_runtime_ranker_digest"] = DIGEST_A
        return result

    monkeypatch.setattr(
        runtime,
        "query_holoindex_owner_once",
        lambda payload, *, repo_root, query_environment: other_ranker(
            repo_root=repo_root,
            query=payload["query"],
            limit=payload["limit"],
        ),
    )
    result = runtime.execute_m2m_holo_retrieval_benchmark(
        repo_root=tmp_path, payload=_payload()
    )
    assert result["success"] is False
    assert result["error"] == "query_owner_ranker_runtime_mismatch"


def test_runtime_quality_gate_rejects_zero_hit_run(monkeypatch, tmp_path: Path):
    _configure(monkeypatch)

    def empty(**kwargs):
        result = dict(_owner_query(**kwargs))
        result.update({"hits": [], "raw_result": {"code_hits": []}})
        return result

    monkeypatch.setattr(
        runtime,
        "query_holoindex_owner_once",
        lambda payload, *, repo_root, query_environment: empty(
            repo_root=repo_root,
            query=payload["query"],
            limit=payload["limit"],
        ),
    )

    result = runtime.execute_m2m_holo_retrieval_benchmark(
        repo_root=tmp_path, payload=_payload()
    )
    assert result["verification"]["accepted"] is True
    assert result["quality_gate_passed"] is False
    assert result["success"] is False
    assert result["error"] == "quality_below_policy"


def test_result_distinguishes_verification_failure_from_quality_failure():
    result = runtime._result(
        {"metrics": {"recall_at_k": 1.0, "mrr": 1.0, "ndcg_at_k": 1.0}},
        {"accepted": False},
    )
    assert result["success"] is False
    assert result["quality_gate_passed"] is True
    assert result["error"] == "benchmark_verification_failed"


def test_runtime_does_not_accept_arbitrary_query_runner(monkeypatch, tmp_path: Path):
    _configure(monkeypatch)
    try:
        runtime.execute_m2m_holo_retrieval_benchmark(
            repo_root=tmp_path,
            payload=_payload(),
            query_runner=lambda *_: {},
        )
    except TypeError as exc:
        assert "query_runner" in str(exc)
    else:
        raise AssertionError("arbitrary query runner was accepted")


def test_raw_grade_composer_is_not_exported() -> None:
    assert "evaluate_holo_retrieval_a_grade" not in grade_gate.__all__
    assert runtime.__all__ == [
        "evaluate_m2m_holo_retrieval_a_grade",
        "execute_m2m_holo_retrieval_benchmark",
    ]


def test_a_grade_gate_accepts_independent_evidence_without_promotion(
    monkeypatch, tmp_path: Path,
):
    _configure(monkeypatch)
    public = runtime.execute_m2m_holo_retrieval_benchmark(
        repo_root=tmp_path, payload=_payload()
    )
    independent = _independent_evaluation(public)

    receipt = runtime.evaluate_m2m_holo_retrieval_a_grade(
        repo_root=tmp_path,
        payload=_payload(),
        independent_evaluation=independent,
        signature_envelope=_signature_envelope(independent),
        signature_verifier=_SignatureVerifier(),
    )

    assert receipt.accepted is True
    assert receipt.decision == grade_gate.GRADE_ACCEPT
    assert receipt.a_grade_evidence_accepted is True
    assert receipt.promotion_authorized is False
    assert receipt.promotion_to_holoindex_performed is False
    assert receipt.signature_verifier_invoked is True
    assert receipt.external_verifier_effects_attested is False
    payload = receipt.to_dict()
    claimed = payload.pop("receipt_id")
    assert claimed == digest_json(payload)


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"sealed_corpus_case_count": 29}, "independent_corpus_too_small"),
        (
            {"corpus_disjoint_from_public_regression": False},
            "independent_corpus_separation_unproven",
        ),
        (
            {"evaluator_principal_id": "ranker-proposer"},
            "independent_evaluator_separation_invalid",
        ),
        (
            {
                "metrics": {
                    "recall_at_k": 0.97,
                    "mrr": 0.97,
                    "ndcg_at_k": 0.94,
                    "p95_latency_ms": 4000.0,
                }
            },
            "independent_ndcg_at_k_below_policy",
        ),
        (
            {
                "metrics": {
                    "recall_at_k": 0.97,
                    "mrr": 0.97,
                    "ndcg_at_k": 0.97,
                    "p95_latency_ms": 5000.1,
                }
            },
            "independent_latency_above_policy",
        ),
    ],
)
def test_a_grade_gate_rejects_weak_or_nonindependent_evidence(
    monkeypatch, tmp_path: Path, overrides, reason,
):
    _configure(monkeypatch)
    public = runtime.execute_m2m_holo_retrieval_benchmark(
        repo_root=tmp_path, payload=_payload()
    )
    independent = _independent_evaluation(public, **overrides)
    receipt = grade_gate._evaluate_holo_retrieval_a_grade(
        public_result=public,
        independent_evaluation=independent,
        signature_envelope=_signature_envelope(independent),
        signature_verifier=_SignatureVerifier(),
    )

    assert receipt.accepted is False
    assert reason in receipt.rejection_reasons
    assert receipt.promotion_authorized is False


def test_a_grade_gate_rejects_invalid_signature(monkeypatch, tmp_path: Path):
    _configure(monkeypatch)
    public = runtime.execute_m2m_holo_retrieval_benchmark(
        repo_root=tmp_path, payload=_payload()
    )
    independent = _independent_evaluation(public)

    receipt = grade_gate._evaluate_holo_retrieval_a_grade(
        public_result=public,
        independent_evaluation=independent,
        signature_envelope=_signature_envelope(independent),
        signature_verifier=_SignatureVerifier(False),
    )

    assert receipt.accepted is False
    assert "independent_signature_invalid" in receipt.rejection_reasons


def test_a_grade_policy_cannot_be_weakened_below_fixed_floors(
    monkeypatch, tmp_path: Path,
):
    _configure(monkeypatch)
    public = runtime.execute_m2m_holo_retrieval_benchmark(
        repo_root=tmp_path, payload=_payload()
    )
    independent = _independent_evaluation(public)
    weakened = grade_gate.HoloRetrievalGradePolicy(
        min_case_count=1,
        min_recall_at_k=0.0,
        min_mrr=0.0,
        min_ndcg_at_k=0.0,
        max_p95_latency_ms=1_000_000.0,
    )

    with pytest.raises(ValueError, match="invalid_holo_retrieval_grade_policy"):
        grade_gate._evaluate_holo_retrieval_a_grade(
            public_result=public,
            independent_evaluation=independent,
            signature_envelope=_signature_envelope(independent),
            signature_verifier=_SignatureVerifier(),
            policy=weakened,
        )


def test_a_grade_gate_rejects_failed_public_regression(monkeypatch, tmp_path: Path):
    _configure(monkeypatch)
    public = runtime.execute_m2m_holo_retrieval_benchmark(
        repo_root=tmp_path, payload=_payload()
    )
    public["success"] = False
    public["quality_gate_passed"] = False
    independent = _independent_evaluation(public)

    verifier = _SignatureVerifier()
    receipt = grade_gate._evaluate_holo_retrieval_a_grade(
        public_result=public,
        independent_evaluation=independent,
        signature_envelope=_signature_envelope(independent),
        signature_verifier=verifier,
    )

    assert receipt.accepted is False
    assert "public_regression_not_accepted" in receipt.rejection_reasons
    assert receipt.signature_verifier_invoked is False
    assert verifier.calls == 0


def test_a_grade_gate_rejects_tampered_independent_receipt(
    monkeypatch, tmp_path: Path,
):
    _configure(monkeypatch)
    public = runtime.execute_m2m_holo_retrieval_benchmark(
        repo_root=tmp_path, payload=_payload()
    )
    independent = _independent_evaluation(public)
    independent["metrics"]["mrr"] = 0.99

    receipt = grade_gate._evaluate_holo_retrieval_a_grade(
        public_result=public,
        independent_evaluation=independent,
        signature_envelope=_signature_envelope(independent),
        signature_verifier=_SignatureVerifier(),
    )

    assert receipt.accepted is False
    assert "independent_receipt_integrity_invalid" in receipt.rejection_reasons


def test_a_grade_gate_rejects_resigned_candidate_mismatch(
    monkeypatch, tmp_path: Path,
):
    _configure(monkeypatch)
    public = runtime.execute_m2m_holo_retrieval_benchmark(
        repo_root=tmp_path, payload=_payload()
    )
    independent = _independent_evaluation(public, candidate_id=DIGEST_A)

    receipt = grade_gate._evaluate_holo_retrieval_a_grade(
        public_result=public,
        independent_evaluation=independent,
        signature_envelope=_signature_envelope(independent),
        signature_verifier=_SignatureVerifier(),
    )

    assert receipt.accepted is False
    assert "independent_candidate_binding_mismatch" in receipt.rejection_reasons


def test_a_grade_gate_rejects_forged_public_receipts(monkeypatch, tmp_path: Path):
    _configure(monkeypatch)
    public = runtime.execute_m2m_holo_retrieval_benchmark(
        repo_root=tmp_path, payload=_payload()
    )
    public["benchmark_run"]["metrics"]["mrr"] = 0.99
    independent = _independent_evaluation(public)

    receipt = grade_gate._evaluate_holo_retrieval_a_grade(
        public_result=public,
        independent_evaluation=independent,
        signature_envelope=_signature_envelope(independent),
        signature_verifier=_SignatureVerifier(),
    )

    assert receipt.accepted is False
    assert "public_run_integrity_invalid" in receipt.rejection_reasons


def test_a_grade_gate_recomputes_public_quality_instead_of_trusting_flags(
    monkeypatch, tmp_path: Path,
):
    _configure(monkeypatch)
    public = runtime.execute_m2m_holo_retrieval_benchmark(
        repo_root=tmp_path, payload=_payload()
    )
    payload = {
        **public["benchmark_run"],
        "metrics": {
            **public["benchmark_run"]["metrics"],
            "ndcg_at_k": 0.94,
        },
    }
    public["benchmark_run"] = {
        **payload,
        "receipt_id": digest_json({
            key: value for key, value in payload.items() if key != "receipt_id"
        }),
    }
    public["success"] = True
    public["quality_gate_passed"] = True
    independent = _independent_evaluation(public)

    receipt = grade_gate._evaluate_holo_retrieval_a_grade(
        public_result=public,
        independent_evaluation=independent,
        signature_envelope=_signature_envelope(independent),
        signature_verifier=_SignatureVerifier(),
    )

    assert receipt.accepted is False
    assert "public_quality_policy_not_met" in receipt.rejection_reasons
    assert "public_quality_status_mismatch" in receipt.rejection_reasons
