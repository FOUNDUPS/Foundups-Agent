"""Rehydrate RedDog grounding evidence from immutable Git objects."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from holo_index.cli.repo_audit_discovery import (
    PER_FILE_READ_BYTES,
    secure_read_repo_head_file,
)
from holo_index.freshness_receipt import read_git_head_sha
from holo_index.repository_state import repository_root_digest
from modules.communication.moltbot_bridge.src.reddog_bounded_iterative_retrieval import (
    MAX_TOTAL_GROUNDING_SECONDS,
    TOTAL_READ_BUDGET_BYTES,
    _dedupe,
    _evidence_category,
    _text_supports_tokens,
    canonical_digest,
    requires_broad_semantic_evidence,
    semantic_query_tokens,
    split_quoted_reference_blocks,
)


@dataclass(frozen=True)
class RehydratedSemanticEvidenceRecord:
    target: str
    path: str
    digest: str
    bytes: int
    category: str
    truncated: bool
    repo_head_sha: str
    git_mode: str
    blob_oid: str
    content: str


@dataclass(frozen=True)
class VerifiedGroundedSemanticEvidence:
    grounding_receipt_id: str
    repo_root_digest: str
    repo_head_sha: str
    holoindex_generation_id: str
    holoindex_freshness_receipt_digest: str
    records: tuple[RehydratedSemanticEvidenceRecord, ...]


def rehydrate_semantic_receipt_evidence(
    data: Mapping[str, Any], *, repo_root: Path | str,
    receipt_id: str, work_focus: str,
) -> VerifiedGroundedSemanticEvidence:
    """Rebuild v2 semantic evidence from immutable Git objects and its ledger."""

    root = Path(repo_root).resolve(strict=False)
    root_digest = repository_root_digest(root)
    head = read_git_head_sha(root)
    if root_digest != data.get("holoindex_repo_root_digest"):
        raise ValueError("grounding_semantic_rehydration_root_mismatch")
    if head != data.get("holoindex_repo_head_sha") or head != data.get("repo_state_head_sha"):
        raise ValueError("grounding_semantic_rehydration_head_mismatch")
    if not _rehydration_binding_valid(data, root_digest, head):
        raise ValueError("grounding_semantic_rehydration_binding_mismatch")
    coverage = _mapping_sequence(data.get("semantic_target_coverage"))
    attempts = _mapping_sequence(data.get("semantic_direct_read_attempts"))
    if not _rehydration_ledger_valid(data, coverage, attempts):
        raise ValueError("grounding_semantic_rehydration_ledger_mismatch")
    records = _rehydrate_attempts(root, coverage, attempts, work_focus, head)
    if tuple(data.get("semantic_direct_read_paths") or ()) != tuple(
        record.path for record in records
    ):
        raise ValueError("grounding_semantic_rehydration_evidence_mismatch")
    return VerifiedGroundedSemanticEvidence(
        grounding_receipt_id=receipt_id, repo_root_digest=root_digest,
        repo_head_sha=head,
        holoindex_generation_id=str(data.get("holoindex_generation_id") or ""),
        holoindex_freshness_receipt_digest=str(
            data.get("holoindex_freshness_receipt_digest") or ""
        ),
        records=records,
    )


def _rehydration_binding_valid(data: Mapping[str, Any], root_digest: str, head: str) -> bool:
    return bool(
        root_digest == data.get("holoindex_repo_root_digest")
        and root_digest == data.get("repo_state_root_digest")
        and head == data.get("holoindex_repo_head_sha")
        and head == data.get("repo_state_head_sha")
        and data.get("holoindex_freshness") == "CURRENT"
        and data.get("holoindex_index_gap_detected") is False
        and data.get("no_holoindex_reindex_performed") is True
        and str(data.get("holoindex_generation_id") or "").startswith("sha256:")
        and str(data.get("holoindex_freshness_receipt_digest") or "").startswith("sha256:")
    )


def _rehydration_ledger_valid(data, coverage, attempts) -> bool:
    typed = data.get("typed_targets") if isinstance(data.get("typed_targets"), Mapping) else {}
    targets = tuple(str(value) for value in typed.get("semantic_targets", ()))
    paths = tuple(str(item.get("path") or "") for item in attempts)
    byte_total = sum(int(item.get("bytes") or 0) for item in attempts)
    return bool(
        targets == tuple(str(item.get("target") or "") for item in coverage)
        and len(paths) == len(set(paths))
        and all(path and str(item.get("target") or "") in targets for path, item in zip(paths, attempts))
        and data.get("semantic_direct_read_attempts_digest")
        == canonical_digest({"semantic_direct_read_attempts": list(attempts)})
        and data.get("semantic_direct_read_bytes_total") == byte_total
        and data.get("semantic_direct_read_budget_bytes") == TOTAL_READ_BUDGET_BYTES
        and 0 <= byte_total <= TOTAL_READ_BUDGET_BYTES
        and data.get("semantic_target_coverage_digest")
        == canonical_digest({"semantic_target_coverage": list(coverage)})
    )


def _rehydrate_attempts(root, coverage, attempts, work_focus, head):
    coverage_by_target = {str(item.get("target") or ""): item for item in coverage}
    evidence_by_path = _evidence_by_unique_path(coverage)
    remaining = TOTAL_READ_BUDGET_BYTES
    deadline = time.monotonic() + MAX_TOTAL_GROUNDING_SECONDS
    records = []
    for attempt in attempts:
        target, path = str(attempt.get("target") or ""), str(attempt.get("path") or "")
        expected_bytes = int(attempt.get("bytes") or 0)
        read = secure_read_repo_head_file(
            root, path, byte_cap=PER_FILE_READ_BYTES, remaining_budget=remaining,
            timeout_seconds=max(0.0, deadline - time.monotonic()),
        )
        if read.get("ok") is not True:
            actual_bytes = int(read.get("attempted_bytes") or 0)
            if actual_bytes != expected_bytes or attempt.get("reason") != read.get("reason"):
                raise ValueError("grounding_semantic_rehydration_failure_mismatch")
            remaining -= actual_bytes
            continue
        if not _read_matches_attempt(read, attempt, expected_bytes, head):
            raise ValueError("grounding_semantic_rehydration_evidence_mismatch")
        remaining -= expected_bytes
        supportive = _text_supports_tokens(
            f"{path} {read.get('content') or ''}", semantic_query_tokens(target)
        )
        if attempt.get("reason") != ("" if supportive else "content_not_supportive"):
            raise ValueError("grounding_semantic_rehydration_support_mismatch")
        if supportive:
            records.append(_rehydrated_semantic_record(
                target, read, evidence_by_path.get(path), path
            ))
    if set(evidence_by_path) != {record.path for record in records}:
        raise ValueError("grounding_semantic_rehydration_evidence_mismatch")
    _validate_rehydrated_coverage(
        coverage_by_target, records, split_quoted_reference_blocks(work_focus)[1]
    )
    return tuple(records)


def _evidence_by_unique_path(coverage):
    records = [
        record for item in coverage for record in item.get("evidence_records", ())
        if isinstance(record, Mapping)
    ]
    paths = [str(record.get("path") or "") for record in records]
    if not paths or len(paths) != len(set(paths)):
        raise ValueError("grounding_semantic_rehydration_duplicate_path")
    return dict(zip(paths, records))


def _read_matches_attempt(read, attempt, expected_bytes, head) -> bool:
    return bool(
        0 < expected_bytes <= PER_FILE_READ_BYTES
        and read.get("ok") is True and read.get("bytes") == expected_bytes
        and read.get("repo_head_sha") == head
        and str(read.get("git_mode") or "") in {"100644", "100755"}
        and re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", str(read.get("blob_oid") or ""))
        and str(attempt.get("path") or "") == str(read.get("path") or "")
    )


def _rehydrated_semantic_record(target, read, expected, path):
    fields = ("digest", "bytes", "truncated", "repo_head_sha", "git_mode", "blob_oid")
    category = _evidence_category(path)
    if not isinstance(expected, Mapping) or any(read.get(field) != expected.get(field) for field in fields):
        raise ValueError("grounding_semantic_rehydration_evidence_mismatch")
    if expected.get("category") != category:
        raise ValueError("grounding_semantic_rehydration_category_mismatch")
    return RehydratedSemanticEvidenceRecord(
        target=target, path=path, digest=str(read["digest"]), bytes=int(read["bytes"]),
        category=category, truncated=bool(read["truncated"]),
        repo_head_sha=str(read["repo_head_sha"]), git_mode=str(read["git_mode"]),
        blob_oid=str(read["blob_oid"]), content=str(read.get("content") or ""),
    )


def _validate_rehydrated_coverage(coverage_by_target, records, work_focus) -> None:
    broad = requires_broad_semantic_evidence(work_focus)
    for target, item in coverage_by_target.items():
        selected = [record for record in records if record.target == target]
        quality = item.get("evidence_quality") if isinstance(item.get("evidence_quality"), Mapping) else {}
        categories = _dedupe(record.category for record in selected)
        enough = bool(selected) and (
            not broad
            or ("implementation" in categories and bool({"verification", "authoritative"} & set(categories)))
        )
        if not (
            item.get("verdict") == "SUFFICIENT" and enough
            and list(item.get("evidence_refs") or ()) == [record.path for record in selected]
            and quality.get("required") is broad and quality.get("passed") is True
            and quality.get("repository_state_bound") is True
            and list(quality.get("categories") or ()) == categories
            and list(quality.get("target_tokens") or ()) == semantic_query_tokens(target)
        ):
            raise ValueError("grounding_semantic_rehydration_coverage_mismatch")


def _mapping_sequence(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


__all__ = [
    "RehydratedSemanticEvidenceRecord", "VerifiedGroundedSemanticEvidence",
    "rehydrate_semantic_receipt_evidence",
]
