"""Query-only runtime adapter for the Holo retrieval benchmark Skillz."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from holo_index.authority_worktree import resolve_holoindex_authority_root
from holo_index.query_receipt import digest_json, file_digest
from holo_index.retrieval_runtime_binding import (
    is_retrieval_runtime_digest,
    retrieval_ranker_digest_for_root,
)
from holo_index.storage_contract import resolve_holoindex_ssd_path
from holo_index.retrieval_autoresearch import (
    RetrievalCandidateBinding,
    RetrievalCase,
    RetrievalRelevance,
    build_retrieval_corpus,
    retrieval_candidate_id,
    run_generation_bound_benchmark,
    verify_generation_bound_benchmark,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_acquisition import (
    build_owner_query_environment,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_bootstrap import (
    cleanup_reddog_holoindex_owner,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_replica_route import (
    resolve_query_replica_owner_route,
)
from scripts.reddog_holoindex_owner_query_once import query_once as query_holoindex_owner_once
from .m2m_holo_retrieval_grade_gate import (
    HoloRetrievalGradeGateReceipt,
    HoloRetrievalGradePolicy,
    IndependentRetrievalSignatureVerifier,
    _evaluate_holo_retrieval_a_grade,
)


CORPUS_SCHEMA = "holoindex_retrieval_corpus_source.v1"
CORPUS_PATH = Path(
    "modules/ai_intelligence/ai_overseer/skillz/"
    "m2m_holo_retrieval_benchmark/retrieval_corpus_v1.json"
)
QUALITY_THRESHOLD = 0.95


def _retain_owner() -> None:
    """Keep the benchmark's authenticated owner resident until final cleanup."""


def _case(value: Any) -> RetrievalCase:
    if not isinstance(value, Mapping):
        raise ValueError("invalid_corpus_case")
    relevance = value.get("relevance")
    if not isinstance(relevance, list):
        raise ValueError("invalid_corpus_relevance")
    if any(
        not isinstance(item, Mapping) or type(item.get("grade")) is not int
        for item in relevance
    ):
        raise ValueError("invalid_corpus_relevance")
    return RetrievalCase(
        case_id=str(value.get("case_id") or ""),
        query=str(value.get("query") or ""),
        relevance=tuple(
            RetrievalRelevance(str(item.get("path") or ""), item["grade"])
            for item in relevance
        ),
    )


def _load_corpus(repo_root: Path):
    path = repo_root / CORPUS_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or payload.get("schema_version") != CORPUS_SCHEMA:
        raise ValueError("invalid_corpus_source_schema")
    train = payload.get("train_cases")
    heldout = payload.get("heldout_cases")
    if not isinstance(train, list) or not isinstance(heldout, list):
        raise ValueError("invalid_corpus_source_cases")
    corpus = build_retrieval_corpus(
        train_cases=tuple(_case(item) for item in train),
        heldout_cases=tuple(_case(item) for item in heldout),
    )
    _validate_corpus_paths(repo_root, corpus)
    return corpus, file_digest(path)


def _exact_file(repo_root: Path, relative_path: str) -> bool:
    root = repo_root.resolve()
    current = root
    for part in relative_path.split("/"):
        try:
            names = {entry.name for entry in current.iterdir()}
        except OSError:
            return False
        if part not in names:
            return False
        current = current / part
        if current.is_symlink() or (
            hasattr(os.path, "isjunction") and os.path.isjunction(current)
        ):
            return False
    try:
        resolved = current.resolve(strict=True)
    except OSError:
        return False
    return resolved.is_relative_to(root) and resolved.is_file()


def _validate_corpus_paths(repo_root: Path, corpus) -> None:
    for case in corpus.train_cases + corpus.heldout_cases:
        for relevance in case.relevance:
            if not _exact_file(repo_root, relevance.path):
                raise ValueError("corpus_path_not_exact_repository_file")


def _limit(payload: Mapping[str, Any]) -> int:
    try:
        limit = int(payload.get("limit", 8))
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_benchmark_limit") from exc
    if limit < 1 or limit > 20:
        raise ValueError("invalid_benchmark_limit")
    return limit


def _runtime_probe(
    repo_root: Path, environment: Mapping[str, str],
    binding: Any, ranker_digest: str,
) -> str:
    probe = query_holoindex_owner_once(
        {
            "query": "HoloIndex retrieval runtime binding", "limit": 1,
            "retrieval_mode": "semantic",
        },
        repo_root=repo_root, query_environment=environment,
        cleanup_owner=_retain_owner,
    )
    if probe.get("ok") is not True:
        raise ValueError(str(probe.get("error") or "owner_query_failed"))
    if probe.get("repo_root_digest") != binding.canonical_repo_root_digest:
        raise ValueError("query_owner_repo_root_mismatch")
    if probe.get("retrieval_runtime_ranker_digest") != ranker_digest:
        raise ValueError("query_owner_ranker_runtime_mismatch")
    digest = str(probe.get("runtime_environment_digest") or "")
    if not is_retrieval_runtime_digest(digest):
        raise ValueError("query_owner_environment_runtime_invalid")
    return digest


def _candidate(
    repo_root: Path, limit: int
) -> tuple[RetrievalCandidateBinding, dict[str, str]]:
    environment = build_owner_query_environment()
    authority = resolve_holoindex_authority_root(
        repo_root, environment=environment
    )
    if not authority.accepted:
        raise ValueError(authority.error or "holoindex_authority_unavailable")
    canonical_ssd_path = resolve_holoindex_ssd_path(environ=environment)
    route = resolve_query_replica_owner_route(
        canonical_repo_root=authority.selected_root,
        canonical_ssd_path=canonical_ssd_path,
        environment=environment,
    )
    binding = route.revalidate()
    if (
        binding.canonical_repo_head_sha != authority.authority_head_sha
        or binding.canonical_repo_root_digest != authority.authority_root_digest
    ):
        raise ValueError("query_replica_authority_mismatch")
    config_digest = digest_json({
        "limit": limit,
        "doc_type": "all",
        "retrieval_mode": "semantic",
    })
    ranker_digest = retrieval_ranker_digest_for_root(authority.selected_root)
    environment_digest = _runtime_probe(
        repo_root, environment, binding, ranker_digest,
    )
    fields = {
        "generation_id": binding.generation_id,
        "freshness_receipt_digest": binding.canonical_receipt_digest,
        "repo_head_sha": binding.canonical_repo_head_sha,
        "repo_root_digest": binding.canonical_repo_root_digest,
        "config_digest": config_digest,
        "ranker_digest": ranker_digest,
        "runtime_environment_digest": environment_digest,
    }
    return (
        RetrievalCandidateBinding(
            candidate_id=retrieval_candidate_id(**fields),
            **fields,
        ),
        environment,
    )


def _query(
    repo_root: Path,
    query: str,
    limit: int,
    binding: RetrievalCandidateBinding,
    query_environment: Mapping[str, str],
):
    result = query_holoindex_owner_once(
        {"query": query, "limit": limit, "retrieval_mode": "semantic"},
        repo_root=repo_root,
        query_environment=query_environment,
        cleanup_owner=_retain_owner,
    )
    if result.get("ok") is not True:
        raise ValueError(str(result.get("error") or "owner_query_failed"))
    if result.get("repo_root_digest") != binding.repo_root_digest:
        raise ValueError("query_owner_repo_root_mismatch")
    if result.get("retrieval_runtime_ranker_digest") != binding.ranker_digest:
        raise ValueError("query_owner_ranker_runtime_mismatch")
    if result.get("runtime_environment_digest") != binding.runtime_environment_digest:
        raise ValueError("query_owner_environment_runtime_mismatch")
    return result


def _run_verified_benchmark(repo_root: Path, limit: int):
    corpus, source_digest = _load_corpus(repo_root)
    try:
        candidate, query_environment = _candidate(repo_root, limit)
        run = run_generation_bound_benchmark(
            corpus=corpus, split="heldout", binding=candidate,
            query_runner=lambda query, k, binding: _query(
                repo_root, query, k, binding, query_environment
            ),
            k=limit, corpus_source_digest=source_digest,
        )
        verification = verify_generation_bound_benchmark(
            corpus=corpus, run=run,
            verifier_digest=file_digest(
                repo_root / "holo_index" / "retrieval_autoresearch.py"
            ),
            expected_corpus_source_digest=source_digest,
            expected_candidate_binding=candidate,
        )
        return run, verification
    finally:
        cleanup_reddog_holoindex_owner()


def _result(run: Mapping[str, Any], verification: Mapping[str, Any]) -> dict[str, Any]:
    metrics = run["metrics"]
    quality_passed = all(
        metrics[name] >= QUALITY_THRESHOLD
        for name in ("recall_at_k", "mrr", "ndcg_at_k")
    )
    verification_passed = verification["accepted"] is True
    success = verification_passed and quality_passed
    error = ""
    if not verification_passed:
        error = "benchmark_verification_failed"
    elif not quality_passed:
        error = "quality_below_policy"
    return {
        "success": success,
        "error": error,
        "benchmark_run": run,
        "verification": verification,
        "quality_threshold": QUALITY_THRESHOLD,
        "quality_gate_passed": quality_passed,
        "public_regression_corpus_not_independent_heldout": True,
        "no_holoindex_reindex_performed": True,
        "no_generation_promotion_performed": True,
        "no_repository_artifact_written": True,
    }


def execute_m2m_holo_retrieval_benchmark(
    *, repo_root: Path, payload: Mapping[str, Any]
) -> dict[str, Any]:
    """Run one held-out benchmark against the active pinned query owner."""

    if payload.get("reindex") is True:
        return {
            "success": False,
            "error": "runtime_reindex_forbidden",
            "no_holoindex_reindex_performed": True,
        }
    if "queries" in payload or "required_paths" in payload or "corpus_path" in payload:
        return {
            "success": False,
            "error": "runtime_corpus_override_forbidden",
            "no_holoindex_reindex_performed": True,
        }
    try:
        limit = _limit(payload)
        run, verification = _run_verified_benchmark(repo_root, limit)
    except (OSError, TypeError, ValueError) as exc:
        return {
            "success": False,
            "error": str(exc),
            "no_holoindex_reindex_performed": True,
        }
    return _result(run, verification)


def evaluate_m2m_holo_retrieval_a_grade(
    *,
    repo_root: Path,
    payload: Mapping[str, Any],
    independent_evaluation: Mapping[str, Any],
    signature_envelope: Mapping[str, Any],
    signature_verifier: IndependentRetrievalSignatureVerifier,
    policy: HoloRetrievalGradePolicy = HoloRetrievalGradePolicy(),
) -> HoloRetrievalGradeGateReceipt:
    """Re-run public regressions, then evaluate independent candidate evidence."""

    return _evaluate_holo_retrieval_a_grade(
        public_result=execute_m2m_holo_retrieval_benchmark(
            repo_root=repo_root,
            payload=payload,
        ),
        independent_evaluation=independent_evaluation,
        signature_envelope=signature_envelope,
        signature_verifier=signature_verifier,
        policy=policy,
    )


__all__ = [
    "evaluate_m2m_holo_retrieval_a_grade",
    "execute_m2m_holo_retrieval_benchmark",
]
