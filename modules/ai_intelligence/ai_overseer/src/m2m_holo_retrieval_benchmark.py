"""Query-only runtime adapter for the Holo retrieval benchmark Skillz."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from holo_index.freshness_receipt import read_git_head_sha
from holo_index.query_receipt import digest_json, file_digest, load_generation_binding
from holo_index.repository_state import repository_root_digest
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
from modules.communication.moltbot_bridge.src.reddog_holoindex_owner_query_client import (
    query_holoindex_owner,
)


CORPUS_SCHEMA = "holoindex_retrieval_corpus_source.v1"
CORPUS_PATH = Path(
    "modules/ai_intelligence/ai_overseer/skillz/"
    "m2m_holo_retrieval_benchmark/retrieval_corpus_v1.json"
)
QUALITY_THRESHOLD = 0.95


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


def _candidate(repo_root: Path, limit: int) -> RetrievalCandidateBinding:
    binding = load_generation_binding(ssd_path=resolve_holoindex_ssd_path())
    current_head = read_git_head_sha(repo_root)
    receipt_head = str(binding.get("repo_head_sha") or "")
    if not current_head or current_head != receipt_head:
        raise ValueError("freshness_receipt_repo_head_mismatch")
    root_digest = repository_root_digest(repo_root)
    config_digest = digest_json({"limit": limit, "doc_type": "all"})
    ranker_digest = file_digest(repo_root / "holo_index" / "core" / "holo_index.py")
    fields = {
        "generation_id": str(binding.get("freshness_generation_id") or ""),
        "freshness_receipt_digest": str(
            binding.get("freshness_receipt_digest") or ""
        ),
        "repo_head_sha": current_head,
        "repo_root_digest": root_digest,
        "config_digest": config_digest,
        "ranker_digest": ranker_digest,
    }
    return RetrievalCandidateBinding(
        candidate_id=retrieval_candidate_id(**fields),
        **fields,
    )


def _query(repo_root: Path, query: str, limit: int, binding):
    result = query_holoindex_owner(repo_root=repo_root, query=query, limit=limit)
    if result.get("repo_root_digest") != binding.repo_root_digest:
        raise ValueError("query_owner_repo_root_mismatch")
    return result


def _run_verified_benchmark(repo_root: Path, limit: int):
    corpus, source_digest = _load_corpus(repo_root)
    candidate = _candidate(repo_root, limit)
    run = run_generation_bound_benchmark(
        corpus=corpus,
        split="heldout",
        binding=candidate,
        query_runner=lambda query, k, binding: _query(
            repo_root, query, k, binding
        ),
        k=limit,
        corpus_source_digest=source_digest,
    )
    verification = verify_generation_bound_benchmark(
        corpus=corpus,
        run=run,
        verifier_digest=file_digest(
            repo_root / "holo_index" / "retrieval_autoresearch.py"
        ),
        expected_corpus_source_digest=source_digest,
        expected_candidate_binding=candidate,
    )
    return run, verification


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


__all__ = ["execute_m2m_holo_retrieval_benchmark"]
