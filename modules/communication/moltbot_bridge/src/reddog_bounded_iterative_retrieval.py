"""Bounded deterministic HoloIndex query refinement for RedDog grounding."""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from holo_index.cli.repo_audit_discovery import (
    MAX_SELECTED_PATHS,
    PER_FILE_READ_BYTES,
    TOTAL_READ_BUDGET_BYTES,
    secure_read_repo_head_file,
)
from holo_index.freshness_receipt import read_git_head_sha
from holo_index.repository_state import repository_root_digest
from modules.communication.moltbot_bridge.src.reddog_holoindex_query_adapter import (
    holoindex_hits,
)


SCHEMA_VERSION = "reddog_bounded_iterative_retrieval.v1"
MAX_QUERY_ROUNDS = 2
MAX_QUERY_CHARS = 240
MIN_TOKEN_CHARS = 3
MAX_TOTAL_OWNER_QUERIES = 16
MAX_TOTAL_GROUNDING_SECONDS = 30.0
POLICY = {
    "schema_version": "reddog_bounded_retrieval_policy.v1",
    "max_query_rounds": MAX_QUERY_ROUNDS,
    "max_query_chars": MAX_QUERY_CHARS,
    "refinement_mode": "deterministic_tokens_then_evidence_roles",
    "owner_query_only": True,
}
STOPWORDS = frozenset({
    "analyze", "analyse", "assess", "audit", "build", "code", "codebase", "compare",
    "current", "determine", "evaluate", "fix", "foundups", "grounding",
    "implement", "inspect", "investigate", "module", "repo", "repository",
    "review", "system", "that",
    "the", "this", "verify", "with", "work",
})
BROAD_SCOPE_RE = re.compile(
    r"\b(?:architecture|codebase|cross[- ]module|deep\s+dive|entire|full|"
    r"multi[- ](?:module|surface)|repo(?:sitory)?|runtime|system|whole)\b",
    re.IGNORECASE,
)
NARROW_LOOKUP_RE = re.compile(
    r"^\s*(?:find|locate|show|where\s+is)\b", re.IGNORECASE
)

CoverageEvaluator = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]
OwnerQuery = Callable[[str], Mapping[str, Any]]


@dataclass(frozen=True)
class BoundedRetrievalResult:
    accepted: bool
    owner_result: Mapping[str, Any] = field(default_factory=dict)
    coverage: Mapping[str, Any] = field(default_factory=dict)
    receipt: Mapping[str, Any] = field(default_factory=dict)
    rejection_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class SemanticGroundingState:
    coverage: tuple[Mapping[str, Any], ...]
    owner_results: tuple[Mapping[str, Any], ...]
    retrieval_traces: tuple[Mapping[str, Any], ...]
    rejection_reasons: tuple[str, ...]
    read_attempts: tuple[Mapping[str, Any], ...]
    attempted_read_bytes: int


@dataclass
class _SemanticReadBudget:
    remaining: int = TOTAL_READ_BUDGET_BYTES
    attempts: list[Mapping[str, Any]] = field(default_factory=list)
    seen_paths: set[str] = field(default_factory=set)
    cached_reads: dict[str, Mapping[str, Any]] = field(default_factory=dict)
    path_targets: dict[str, str] = field(default_factory=dict)

    @property
    def consumed(self) -> int:
        return TOTAL_READ_BUDGET_BYTES - self.remaining


def canonical_digest(payload: Any) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def semantic_query_tokens(value: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", str(value or "").lower().replace("_", " "))
    return list(dict.fromkeys(
        token for token in tokens if len(token) >= MIN_TOKEN_CHARS and token not in STOPWORDS
    ))


def requires_broad_semantic_evidence(work_focus: str) -> bool:
    """Default semantic work to broad evidence unless it is an explicit lookup."""

    focus = " ".join(str(work_focus or "").split())
    if BROAD_SCOPE_RE.search(focus):
        return True
    return NARROW_LOOKUP_RE.search(focus) is None


def split_quoted_reference_blocks(text: str) -> tuple[list[Mapping[str, str]], str]:
    """Separate fenced and blockquoted data from operator instructions."""

    blocks: list[Mapping[str, str]] = []
    kept: list[str] = []
    current: list[str] = []
    in_fence = False

    def flush(kind: str) -> None:
        if current:
            blocks.append({"kind": kind, "text": "\n".join(current)})
            current.clear()

    for line in str(text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            flush("fenced_block" if in_fence else "blockquote")
            in_fence = not in_fence
        elif in_fence:
            current.append(line)
        elif stripped.startswith(">"):
            current.append(stripped[1:].lstrip())
        else:
            flush("blockquote")
            kept.append(line)
    flush("fenced_block" if in_fence else "blockquote")
    return blocks, "\n".join(kept)


def deterministic_query_variants(target: str) -> tuple[str, ...]:
    original = " ".join(str(target or "").split())[:MAX_QUERY_CHARS]
    tokens = semantic_query_tokens(original)
    candidates = [original]
    if tokens:
        candidates.append(" ".join([*tokens, "implementation", "tests", "contract"]))
    return tuple(dict.fromkeys(item[:MAX_QUERY_CHARS] for item in candidates if item))[
        :MAX_QUERY_ROUNDS
    ]


def run_bounded_iterative_retrieval(
    target: str,
    *,
    owner_query: OwnerQuery,
    coverage_evaluator: CoverageEvaluator,
    max_rounds: int = MAX_QUERY_ROUNDS,
    deadline_monotonic: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> BoundedRetrievalResult:
    """Query HoloIndex with fixed refinements and return one selected result."""

    rounds = max(0, min(int(max_rounds), MAX_QUERY_ROUNDS))
    variants = deterministic_query_variants(target)[:rounds]
    state = _collect_attempts(
        target, variants, owner_query, coverage_evaluator,
        deadline_monotonic, clock,
    )
    attempts, selected_result, selected_coverage = state[:3]
    fallback_result, fallback_coverage, reasons = state[3:]
    if not attempts and not reasons:
        reasons.append("bounded_retrieval_query_budget_exhausted")
    elif not selected_result and not reasons:
        reasons.append("bounded_retrieval_evidence_insufficient")
    accepted = bool(selected_result) and not reasons
    receipt = _build_receipt(target, variants, attempts, accepted, reasons)
    return BoundedRetrievalResult(
        accepted=accepted,
        owner_result=selected_result or fallback_result,
        coverage=selected_coverage or fallback_coverage,
        receipt=receipt,
        rejection_reasons=tuple(reasons),
    )


def ground_semantic_targets(
    repo_root: Path,
    targets: Sequence[str],
    *,
    owner_query: OwnerQuery,
    deadline_monotonic: float,
    broad_request: bool,
    max_owner_queries: int = MAX_TOTAL_OWNER_QUERIES,
) -> SemanticGroundingState:
    """Ground all semantic targets under one query, time, and read budget."""

    budget = _SemanticReadBudget()
    coverages: list[Mapping[str, Any]] = []
    owner_results: list[Mapping[str, Any]] = []
    traces: list[Mapping[str, Any]] = []
    reasons: list[str] = []
    remaining_queries = max(0, min(int(max_owner_queries), MAX_TOTAL_OWNER_QUERIES))
    for target in targets:
        retrieval = run_bounded_iterative_retrieval(
            target,
            owner_query=owner_query,
            coverage_evaluator=lambda item, result: evaluate_semantic_coverage(
                repo_root, item, result, broad_request=broad_request, budget=budget,
                deadline_monotonic=deadline_monotonic,
            ),
            max_rounds=min(MAX_QUERY_ROUNDS, remaining_queries),
            deadline_monotonic=deadline_monotonic,
        )
        remaining_queries -= len(retrieval.receipt.get("attempts") or ())
        result, coverage = dict(retrieval.owner_result), dict(retrieval.coverage)
        owner_results.append(result)
        coverages.append(coverage)
        traces.append(dict(retrieval.receipt))
        reasons.extend(_semantic_retrieval_reasons(result, coverage, retrieval))
    if not _consistent_owner_bindings(owner_results):
        reasons.append("grounding_holoindex_generation_not_current")
    return SemanticGroundingState(
        coverage=tuple(coverages),
        owner_results=tuple(owner_results),
        retrieval_traces=tuple(traces),
        rejection_reasons=tuple(dict.fromkeys(reasons)),
        read_attempts=tuple(budget.attempts),
        attempted_read_bytes=budget.consumed,
    )


def evaluate_semantic_coverage(
    repo_root: Path,
    target: str,
    result: Mapping[str, Any],
    *,
    broad_request: bool,
    budget: _SemanticReadBudget | None = None,
    deadline_monotonic: float | None = None,
) -> Mapping[str, Any]:
    """Bind Holo candidates to direct immutable-HEAD evidence."""

    ledger = budget or _SemanticReadBudget()
    raw = result.get("raw_result") if isinstance(result.get("raw_result"), Mapping) else {}
    target_tokens = semantic_query_tokens(target)
    candidates = _semantic_candidates(holoindex_hits(raw), target_tokens)
    evidence, rejected = _read_semantic_evidence(
        repo_root, target, candidates, target_tokens, ledger, deadline_monotonic
    )
    refs = [str(item["path"]) for item in evidence]
    categories = _dedupe(str(item["category"]) for item in evidence)
    state_bound = _evidence_is_state_bound(repo_root, result, evidence)
    implementation = "implementation" in categories
    corroborated = bool({"verification", "authoritative"}.intersection(categories))
    enough = state_bound and bool(evidence) and (
        not broad_request or (implementation and corroborated)
    )
    return {
        "target": target,
        "verdict": "SUFFICIENT" if enough else "UNSAFE_TO_ACT",
        "evidence_refs": refs[:20],
        "evidence_records": evidence,
        "evidence_records_digest": canonical_digest({"evidence_records": evidence}),
        "read_rejections": rejected,
        "evidence_quality": {
            "required": broad_request, "passed": enough, "categories": categories,
            "target_tokens": target_tokens, "repository_state_bound": state_bound,
        },
        "rejection_reasons": [] if enough else ["grounding_semantic_evidence_insufficient"],
    }


def _semantic_retrieval_reasons(
    result: Mapping[str, Any], coverage: Mapping[str, Any], retrieval: BoundedRetrievalResult
) -> list[str]:
    reasons: list[str] = []
    if result.get("ok") is not True:
        reasons.append("grounding_holoindex_owner_query_failed")
    if not _current_owner_result(result):
        reasons.append("grounding_holoindex_generation_not_current")
    if coverage.get("verdict") != "SUFFICIENT":
        reasons.append("grounding_semantic_evidence_insufficient")
    if "bounded_retrieval_owner_binding_changed" in retrieval.rejection_reasons:
        reasons.append("grounding_holoindex_generation_not_current")
    return reasons


def _semantic_candidates(
    hits: Sequence[Mapping[str, Any]], target_tokens: Sequence[str]
) -> list[str]:
    supported = [item for item in hits if _hit_supports_tokens(item, target_tokens)]
    return _dedupe(
        str(item.get("path") or "").replace("\\", "/")
        for item in supported
        if item.get("path") and not Path(str(item.get("path"))).is_absolute()
    )


def _read_semantic_evidence(
    repo_root: Path,
    target: str,
    candidates: Sequence[str],
    target_tokens: Sequence[str],
    budget: _SemanticReadBudget,
    deadline_monotonic: float | None,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    evidence: list[Mapping[str, Any]] = []
    rejected: list[Mapping[str, Any]] = []
    for path in candidates[:MAX_SELECTED_PATHS]:
        remaining_seconds = (
            None if deadline_monotonic is None else deadline_monotonic - time.monotonic()
        )
        if remaining_seconds is not None and remaining_seconds <= 0:
            rejected.append({"path": path, "reason": "grounding_deadline_exhausted", "bytes": 0})
            break
        read, first_read, duplicate = _budgeted_semantic_read(
            repo_root, target, path, budget, remaining_seconds
        )
        if duplicate:
            rejected.append({"path": path, "reason": "duplicate_path", "bytes": 0})
            continue
        if read.get("ok") is not True:
            rejected.append({
                "path": path, "reason": str(read.get("reason") or "read_rejected"),
                "bytes": int(read.get("attempted_bytes") or 0),
            })
            continue
        read_bytes = int(read["bytes"])
        supportive = _text_supports_tokens(
            f"{path} {read.get('content') or ''}", target_tokens
        )
        reason = "" if supportive else "content_not_supportive"
        if first_read and budget.attempts and budget.attempts[-1]["path"] == path:
            budget.attempts[-1]["reason"] = reason
        if not supportive:
            rejected.append({"path": path, "reason": reason, "bytes": read_bytes})
            continue
        evidence.append(_semantic_evidence_record(path, read))
    return evidence, rejected


def _budgeted_semantic_read(repo_root, target, path, budget, remaining_seconds):
    first_read = path not in budget.seen_paths
    if not first_read:
        if budget.path_targets.get(path) != target:
            return {}, False, True
        return budget.cached_reads[path], False, False
    budget.seen_paths.add(path)
    budget.path_targets[path] = target
    read = secure_read_repo_head_file(
        repo_root, path, byte_cap=PER_FILE_READ_BYTES,
        remaining_budget=budget.remaining, timeout_seconds=remaining_seconds,
    )
    budget.cached_reads[path] = dict(read)
    attempted = int(read.get("attempted_bytes") or read.get("bytes") or 0)
    budget.remaining = max(0, budget.remaining - attempted)
    if attempted or read.get("ok") is True:
        budget.attempts.append({
            "target": target, "path": path, "bytes": attempted,
            "reason": str(read.get("reason") or "") if read.get("ok") is not True else "",
        })
    return read, True, False


def _semantic_evidence_record(path: str, read: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        "path": path,
        "digest": str(read["digest"]),
        "bytes": int(read["bytes"]),
        "category": _evidence_category(path),
        "truncated": bool(read["truncated"]),
        "repo_head_sha": str(read["repo_head_sha"]),
        "git_mode": str(read["git_mode"]),
        "blob_oid": str(read["blob_oid"]),
    }


def _evidence_is_state_bound(
    repo_root: Path, result: Mapping[str, Any], evidence: Sequence[Mapping[str, Any]]
) -> bool:
    return bool(
        evidence
        and all(
            str(item.get("repo_head_sha") or "") == str(result.get("repo_head_sha") or "")
            for item in evidence
        )
        and str(result.get("repo_root_digest") or "") == repository_root_digest(repo_root)
    )


def _text_supports_tokens(value: str, target_tokens: Sequence[str]) -> bool:
    normalized = _normalized_evidence_text(value)
    matched = [token for token in target_tokens if token in normalized]
    required = len(target_tokens) if len(target_tokens) <= 2 else max(
        2, math.ceil(len(target_tokens) * 0.5)
    )
    return bool(matched and len(matched) >= required and any(len(token) >= 4 for token in matched))


def _hit_supports_tokens(hit: Mapping[str, Any], target_tokens: Sequence[str]) -> bool:
    if not target_tokens:
        return False
    text = " ".join(str(hit.get(key) or "") for key in ("path", "title", "summary", "preview"))
    normalized = _normalized_evidence_text(text)
    matched = [token for token in target_tokens if token in normalized]
    required = len(target_tokens) if len(target_tokens) <= 2 else max(
        2, math.ceil(len(target_tokens) * 0.5)
    )
    return len(matched) >= required and any(len(token) >= 4 for token in matched)


def _normalized_evidence_text(value: str) -> str:
    return str(value or "").lower().replace("_", " ").replace("/", " ").replace("-", " ")


def _evidence_category(path: str) -> str:
    normalized = str(path or "").replace("\\", "/").lower()
    name = normalized.rsplit("/", 1)[-1]
    if normalized.startswith("wsp_framework/"):
        return "authoritative"
    if _is_verification_path(normalized, name):
        return "verification"
    if normalized.endswith((".py", ".js", ".ts", ".rs", ".go", ".java")):
        return "implementation"
    return "supporting"


def _is_verification_path(normalized: str, name: str) -> bool:
    return bool(
        "/tests/" in f"/{normalized}"
        or name.startswith("test_")
        or name.endswith(".test.js")
        or "/contracts/" in f"/{normalized}"
        or "contract" in name
    )


def _consistent_owner_bindings(results: Sequence[Mapping[str, Any]]) -> bool:
    if not results:
        return True
    fields = (
        "freshness_generation_id", "freshness_receipt_digest",
        "repo_head_sha", "repo_root_digest",
    )
    return all(
        len(values) == 1 and bool(next(iter(values)))
        for values in ({str(item.get(field) or "") for item in results} for field in fields)
    )


def _dedupe(values: Sequence[str] | Any) -> list[str]:
    return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _collect_attempts(
    target: str,
    variants: Sequence[str],
    owner_query: OwnerQuery,
    coverage_evaluator: CoverageEvaluator,
    deadline_monotonic: float | None,
    clock: Callable[[], float],
) -> tuple[Any, ...]:
    attempts: list[dict[str, Any]] = []
    first_binding: tuple[str, ...] | None = None
    selected_result: Mapping[str, Any] = {}
    selected_coverage: Mapping[str, Any] = {}
    fallback_result: Mapping[str, Any] = {}
    fallback_coverage: Mapping[str, Any] = {
        "target": target, "verdict": "UNSAFE_TO_ACT", "evidence_refs": []
    }
    reasons: list[str] = []
    coverage_fingerprints: set[str] = set()
    for round_index, query in enumerate(variants, start=1):
        if deadline_monotonic is not None and clock() >= deadline_monotonic:
            reasons.append("bounded_retrieval_deadline_exhausted")
            break
        result, coverage, attempt, binding = _run_attempt(
            target, query, round_index, owner_query, coverage_evaluator, first_binding)
        fallback_result, fallback_coverage = result, coverage
        if attempt["owner_current"] and first_binding is None:
            first_binding = binding
            attempt["binding_matches_first"] = True
        attempts.append(attempt)
        if deadline_monotonic is not None and clock() >= deadline_monotonic:
            reasons.append("bounded_retrieval_deadline_exhausted")
            break
        if not attempt["owner_current"]:
            reasons.append("bounded_retrieval_owner_not_current")
            break
        if not attempt["binding_matches_first"]:
            reasons.append("bounded_retrieval_owner_binding_changed")
            break
        coverage_fingerprint = attempt["coverage_digest"]
        if coverage_fingerprint in coverage_fingerprints:
            reasons.append("bounded_retrieval_no_progress")
            break
        coverage_fingerprints.add(coverage_fingerprint)
        if attempt["coverage_verdict"] == "SUFFICIENT":
            selected_result, selected_coverage = result, coverage
            break
    return (
        attempts, selected_result, selected_coverage,
        fallback_result, fallback_coverage, reasons,
    )


def _run_attempt(
    target: str,
    query: str,
    round_index: int,
    owner_query: OwnerQuery,
    coverage_evaluator: CoverageEvaluator,
    first_binding: tuple[str, ...] | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], tuple[str, ...]]:
    try:
        result = dict(owner_query(query))
        owner_digest = canonical_digest(result)
    except Exception:
        result = {}
        owner_digest = canonical_digest(result)
    try:
        coverage = dict(coverage_evaluator(target, result))
        coverage_digest = canonical_digest(coverage)
    except Exception:
        coverage = {
            "target": target, "verdict": "UNSAFE_TO_ACT", "evidence_refs": []
        }
        coverage_digest = canonical_digest(coverage)
    binding = _binding(result)
    current = _current_owner_result(result)
    evidence_refs = coverage.get("evidence_refs")
    attempt = {
        "round": round_index,
        "query": query,
        "query_digest": canonical_digest({"query": query}),
        "owner_result_digest": owner_digest,
        "coverage_digest": coverage_digest,
        "owner_current": current,
        "binding_matches_first": current and binding == first_binding,
        "coverage_verdict": str(coverage.get("verdict") or ""),
        "evidence_refs": list(evidence_refs) if _string_sequence(evidence_refs) else [],
    }
    return result, coverage, attempt, binding


def validate_bounded_retrieval_receipt(
    receipt: Mapping[str, Any] | None, *, target: str
) -> bool:
    if not isinstance(receipt, Mapping):
        return False
    data = dict(receipt)
    receipt_id = data.pop("receipt_id", None)
    attempts = data.get("attempts")
    variants = deterministic_query_variants(target)
    records = list(attempts) if _sequence(attempts) else []
    expected_queries = list(variants[: len(records)])
    return bool(
        set(receipt) == {
            "schema_version", "policy", "policy_digest", "target_digest",
            "query_variants", "attempts", "accepted", "selected_round",
            "rejection_reasons", "no_model_call_performed",
            "no_shell_command_executed", "no_holoindex_reindex_performed",
            "no_repo_mutation_performed", "receipt_id",
        }
        and receipt_id == canonical_digest(data)
        and data.get("schema_version") == SCHEMA_VERSION
        and data.get("policy") == POLICY
        and data.get("policy_digest") == canonical_digest(POLICY)
        and data.get("target_digest") == canonical_digest({"target": target})
        and data.get("query_variants") == list(variants[: len(data.get("query_variants") or ())])
        and len(records) <= len(data.get("query_variants") or ()) <= MAX_QUERY_ROUNDS
        and 0 < len(records) <= MAX_QUERY_ROUNDS
        and [item.get("query") for item in records if isinstance(item, Mapping)] == expected_queries
        and all(_valid_attempt(item, index) for index, item in enumerate(records, start=1))
        and _valid_outcome(data, records)
        and data.get("no_model_call_performed") is True
        and data.get("no_shell_command_executed") is True
        and data.get("no_holoindex_reindex_performed") is True
        and data.get("no_repo_mutation_performed") is True
    )


def _binding(result: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return tuple(str(result.get(key) or "") for key in (
        "freshness_generation_id", "freshness_receipt_digest",
        "repo_head_sha", "repo_root_digest",
    ))


def _current_owner_result(result: Mapping[str, Any]) -> bool:
    return bool(
        result.get("ok") is True
        and result.get("freshness") == "CURRENT"
        and result.get("index_gap_detected") is False
        and result.get("no_holoindex_reindex_performed") is True
        and all(_binding(result))
    )


def _build_receipt(target, variants, attempts, accepted, reasons):
    payload = {
        "schema_version": SCHEMA_VERSION,
        "policy": dict(POLICY),
        "policy_digest": canonical_digest(POLICY),
        "target_digest": canonical_digest({"target": target}),
        "query_variants": list(variants),
        "attempts": attempts,
        "accepted": accepted,
        "selected_round": next((item["round"] for item in attempts if item["coverage_verdict"] == "SUFFICIENT"), None),
        "rejection_reasons": list(reasons),
        "no_model_call_performed": True,
        "no_shell_command_executed": True,
        "no_holoindex_reindex_performed": True,
        "no_repo_mutation_performed": True,
    }
    return {**payload, "receipt_id": canonical_digest(payload)}


def _valid_attempt(value: Any, expected_round: int) -> bool:
    if not isinstance(value, Mapping):
        return False
    query = str(value.get("query") or "")
    return bool(
        set(value) == {
            "round", "query", "query_digest", "owner_result_digest",
            "coverage_digest", "owner_current", "binding_matches_first",
            "coverage_verdict", "evidence_refs",
        }
        and
        value.get("round") == expected_round
        and 0 < len(query) <= MAX_QUERY_CHARS
        and value.get("query_digest") == canonical_digest({"query": query})
        and re.fullmatch(r"sha256:[0-9a-f]{64}", str(value.get("owner_result_digest") or ""))
        and re.fullmatch(r"sha256:[0-9a-f]{64}", str(value.get("coverage_digest") or ""))
        and isinstance(value.get("owner_current"), bool)
        and isinstance(value.get("binding_matches_first"), bool)
        and value.get("coverage_verdict") in {"SUFFICIENT", "UNSAFE_TO_ACT"}
        and _string_sequence(value.get("evidence_refs"))
    )


def _valid_outcome(data: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> bool:
    accepted = data.get("accepted") is True
    selected = data.get("selected_round")
    sufficient = [item.get("round") for item in records if item.get("coverage_verdict") == "SUFFICIENT"]
    reasons = data.get("rejection_reasons")
    return bool(
        _string_sequence(reasons)
        and ((accepted and sufficient == [selected] and not reasons) or (not accepted and not sufficient and reasons))
    )


def _sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _string_sequence(value: Any) -> bool:
    return _sequence(value) and all(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


__all__ = [
    "BoundedRetrievalResult", "SemanticGroundingState",
    "MAX_TOTAL_GROUNDING_SECONDS", "MAX_TOTAL_OWNER_QUERIES",
    "TOTAL_READ_BUDGET_BYTES", "POLICY", "SCHEMA_VERSION",
    "deterministic_query_variants", "evaluate_semantic_coverage",
    "ground_semantic_targets", "run_bounded_iterative_retrieval",
    "requires_broad_semantic_evidence",
    "semantic_query_tokens", "split_quoted_reference_blocks",
    "validate_bounded_retrieval_receipt",
]
