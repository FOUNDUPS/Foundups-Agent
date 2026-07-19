"""Bind deterministic repository-audit evidence after HoloIndex cannot ground it."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from holo_index.cli.repo_audit_discovery import (
    build_repo_audit_grounding,
    detect_repo_audit_intent,
)
from holo_index.freshness_receipt import read_git_head_sha
from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    canonical_digest,
)


SCHEMA_VERSION = "reddog_repo_audit_fallback.v1"
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


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
    reasons = _fallback_reasons(before_head, after_head, audit, selected)
    receipt = _build_receipt(
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
    audit: Mapping[str, Any],
    selected: Sequence[Mapping[str, Any]],
) -> list[str]:
    reasons: list[str] = []
    if not GIT_SHA_RE.fullmatch(before_head) or before_head != after_head:
        reasons.append(RepoAuditFallbackReason.REPO_STATE)
    categories = {str(item.get("category") or "") for item in selected}
    coverage = audit.get("coverage") if isinstance(audit.get("coverage"), Mapping) else {}
    if (
        audit.get("schema_version") != "repo_audit_grounding.v1"
        or audit.get("applied") is not True
        or audit.get("holo_first") is not True
        or coverage.get("verdict") != "PASS"
        or "implementation_source" not in categories
        or not categories.intersection({"test", "contract"})
    ):
        reasons.append(RepoAuditFallbackReason.EVIDENCE)
    return reasons


def _build_receipt(
    *,
    audit: Mapping[str, Any],
    selected: Sequence[Mapping[str, Any]],
    repo_head_sha: str,
    owner_results: Sequence[Mapping[str, Any]],
    rejection_reasons: Sequence[str],
) -> Mapping[str, Any]:
    audit_value = dict(audit)
    evidence_digest = canonical_digest({"selected": list(selected)})
    state = {
        "repo_head_sha": repo_head_sha,
        "evidence_digest": evidence_digest,
        "entity": str(audit_value.get("entity") or ""),
        "search_mode": str(audit_value.get("search_mode") or ""),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "applied": True,
        "accepted": not rejection_reasons,
        "holo_owner_attempted_first": bool(owner_results),
        "holo_owner_evidence_usable": False,
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
    }


__all__ = [
    "RepoAuditFallbackReason",
    "RepoAuditFallbackResult",
    "SCHEMA_VERSION",
    "build_bound_repo_audit_fallback",
]
