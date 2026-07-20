"""Bind deterministic repository-audit evidence after HoloIndex cannot ground it."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from holo_index.cli.repo_audit_discovery import (
    MAX_CONTENT_SCAN_BYTES,
    MAX_CONTENT_SCAN_TOTAL_BYTES,
    MAX_DISCOVERY_ENTRIES,
    MAX_FILE_SIZE_BYTES,
    MAX_SELECTED_PATHS,
    PER_FILE_READ_BYTES,
    TOTAL_READ_BUDGET_BYTES,
    build_repo_audit_grounding,
    detect_repo_audit_intent,
    repo_audit_category,
    repo_audit_path_supports_entity,
    secure_read_repo_file,
)
from holo_index.freshness_receipt import read_git_head_sha


SCHEMA_VERSION = "reddog_repo_audit_fallback.v1"
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
REPO_AUDIT_POLICY = {
    "schema_version": "repo_audit_fixed_policy.v1",
    "max_selected_paths": MAX_SELECTED_PATHS,
    "total_read_budget_bytes": TOTAL_READ_BUDGET_BYTES,
    "per_file_read_bytes": PER_FILE_READ_BYTES,
    "max_file_size_bytes": MAX_FILE_SIZE_BYTES,
    "max_discovery_entries": MAX_DISCOVERY_ENTRIES,
    "max_content_scan_bytes": MAX_CONTENT_SCAN_BYTES,
    "max_content_scan_total_bytes": MAX_CONTENT_SCAN_TOTAL_BYTES,
    "path_policy": "repo_audit_discovery_pruned_confined.v1",
}
NO_ACTION_FIELDS = (
    "no_model_call_performed",
    "no_shell_command_executed",
    "no_holoindex_reindex_performed",
    "no_repo_mutation_performed",
    "no_external_research_performed",
    "no_execution_authority_granted",
)


class RepoAuditFallbackReason:
    EVIDENCE = "repo_audit_source_and_independent_verification_required"
    REPO_STATE = "repo_audit_repository_state_unavailable_or_changed"


@dataclass(frozen=True)
class RepoAuditFallbackResult:
    applied: bool
    accepted: bool
    repo_file_targets: tuple[str, ...] = ()
    receipt: Mapping[str, Any] = field(default_factory=dict)
    rejection_reasons: tuple[str, ...] = ()


def build_bound_repo_audit_fallback(
    *,
    repo_root: Path,
    work_focus: str,
    owner_results: Sequence[Mapping[str, Any]],
) -> RepoAuditFallbackResult:
    """Read bounded local evidence only for a detected entity-scoped audit."""
    intent = detect_repo_audit_intent(work_focus)
    if intent.get("audit_intent") is not True:
        return RepoAuditFallbackResult(applied=False, accepted=False)
    before_head = read_git_head_sha(repo_root)
    try:
        result = build_repo_audit_grounding(
            repo_root,
            work_focus,
            _owner_search_payload(owner_results),
        )
    except Exception:
        result = {}
    after_head = read_git_head_sha(repo_root)
    audit = result.get("receipt") if isinstance(result.get("receipt"), Mapping) else {}
    selected = _selected_records(audit)
    reasons = _fallback_reasons(before_head, after_head, intent, audit, selected)
    receipt = _build_receipt(
        work_focus=work_focus,
        expected_entity=str(intent.get("entity") or ""),
        audit=audit,
        selected=selected,
        repo_head_sha=after_head,
        owner_results=owner_results,
        rejection_reasons=reasons,
    )
    return RepoAuditFallbackResult(
        applied=True,
        accepted=not reasons,
        repo_file_targets=tuple(str(item["path"]) for item in selected) if not reasons else (),
        receipt=receipt,
        rejection_reasons=tuple(reasons),
    )


def _owner_search_payload(owner_results: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    if len(owner_results) != 1:
        return {}
    raw = owner_results[0].get("raw_result")
    return dict(raw) if isinstance(raw, Mapping) else {}


def _selected_records(audit: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    selected = audit.get("selected")
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes)):
        return []
    return [dict(item) for item in selected if isinstance(item, Mapping)]


def _fallback_reasons(
    before_head: str,
    after_head: str,
    intent: Mapping[str, Any],
    audit: Mapping[str, Any],
    selected: Sequence[Mapping[str, Any]],
) -> list[str]:
    reasons: list[str] = []
    if not GIT_SHA_RE.fullmatch(before_head) or before_head != after_head:
        reasons.append(RepoAuditFallbackReason.REPO_STATE)
    entity = str(intent.get("entity") or "")
    categories = {repo_audit_category(str(item.get("path") or "")) for item in selected}
    coverage = audit.get("coverage") if isinstance(audit.get("coverage"), Mapping) else {}
    if (
        audit.get("schema_version") != "repo_audit_grounding.v1"
        or audit.get("applied") is not True
        or audit.get("holo_first") is not True
        or audit.get("audit_intent") is not True
        or str(audit.get("entity") or "") != entity
        or len(selected) > MAX_SELECTED_PATHS
        or sum(int(item.get("bytes") or 0) for item in selected) > TOTAL_READ_BUDGET_BYTES
        or any(str(item.get("category") or "") != repo_audit_category(str(item.get("path") or "")) for item in selected)
        or any(not repo_audit_path_supports_entity(str(item.get("path") or ""), entity) for item in selected)
        or coverage.get("verdict") != "PASS"
        or "implementation_source" not in categories
        or not categories.intersection({"test", "contract"})
    ):
        reasons.append(RepoAuditFallbackReason.EVIDENCE)
    return reasons


def _build_receipt(
    *,
    work_focus: str,
    expected_entity: str,
    audit: Mapping[str, Any],
    selected: Sequence[Mapping[str, Any]],
    repo_head_sha: str,
    owner_results: Sequence[Mapping[str, Any]],
    rejection_reasons: Sequence[str],
) -> Mapping[str, Any]:
    audit_value = dict(audit)
    evidence_digest = canonical_digest({"selected": list(selected)})
    focus_digest = canonical_digest({"work_focus": work_focus})
    policy_digest = canonical_digest(REPO_AUDIT_POLICY)
    state = {
        "repo_head_sha": repo_head_sha,
        "evidence_digest": evidence_digest,
        "expected_entity": expected_entity,
        "search_mode": str(audit_value.get("search_mode") or ""),
        "work_focus_digest": focus_digest,
        "policy_digest": policy_digest,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "applied": True,
        "accepted": not rejection_reasons,
        "holo_owner_attempted_first": bool(owner_results),
        "holo_owner_evidence_usable": False,
        "work_focus_digest": focus_digest,
        "expected_entity": expected_entity,
        "fixed_policy": dict(REPO_AUDIT_POLICY),
        "fixed_policy_digest": policy_digest,
        "repo_head_sha": repo_head_sha,
        "repo_audit_grounding": audit_value,
        "repo_audit_grounding_digest": canonical_digest(audit_value),
        "selected_evidence_digest": evidence_digest,
        "repository_state_digest": canonical_digest(state),
        "rejection_reasons": list(rejection_reasons),
        "no_model_call_performed": True,
        "no_shell_command_executed": True,
        "no_holoindex_reindex_performed": True,
        "no_repo_mutation_performed": True,
        "no_external_research_performed": True,
        "no_execution_authority_granted": True,
    }


def reread_bound_repo_audit_evidence(
    repo_root: Path,
    fallback: Mapping[str, Any],
) -> tuple[tuple[Mapping[str, Any], ...], tuple[str, ...]]:
    """Confined re-read requiring exact equality with every selected record."""
    audit = fallback.get("repo_audit_grounding")
    audit_mapping = dict(audit) if isinstance(audit, Mapping) else {}
    selected = _selected_records(audit_mapping)
    if not selected or len(selected) > MAX_SELECTED_PATHS:
        return (), (RepoAuditFallbackReason.EVIDENCE,)
    reads: list[Mapping[str, Any]] = []
    remaining = TOTAL_READ_BUDGET_BYTES
    for expected in selected:
        path = str(expected.get("path") or "")
        read = secure_read_repo_file(
            repo_root,
            path,
            byte_cap=PER_FILE_READ_BYTES,
            remaining_budget=remaining,
        )
        if not read.get("ok") or not _read_matches_selected(read, expected):
            return (), ("repo_audit_selected_evidence_changed",)
        remaining -= int(read["bytes"])
        reads.append(read)
    return tuple(reads), ()


def _read_matches_selected(read: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return all((
        str(read.get("path") or "") == str(expected.get("path") or ""),
        str(read.get("digest") or "") == str(expected.get("digest") or ""),
        int(read.get("bytes") or -1) == int(expected.get("bytes") or -2),
        bool(read.get("truncated")) is bool(expected.get("truncated")),
        str(expected.get("category") or "") == repo_audit_category(str(read.get("path") or "")),
    ))


def canonical_digest(payload: Any) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


__all__ = [
    "RepoAuditFallbackReason",
    "RepoAuditFallbackResult",
    "NO_ACTION_FIELDS",
    "REPO_AUDIT_POLICY",
    "SCHEMA_VERSION",
    "build_bound_repo_audit_fallback",
    "canonical_digest",
    "reread_bound_repo_audit_evidence",
]
