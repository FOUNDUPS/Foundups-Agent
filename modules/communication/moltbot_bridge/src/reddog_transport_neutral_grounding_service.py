"""Transport-neutral natural-language grounding for resident RedDog clients.

Slice: REDDOG_TRANSPORT_NEUTRAL_GROUNDING_SERVICE_PHASE1

The service converts host-authenticated work focus into the same immutable
``reddog_intent.v2`` consumed by the canonical AgentDB resident cycle. It is a
read-only evidence router: repository targets are containment-checked and
semantic targets require a current generation-bound HoloIndex owner response.
Entity-scoped audits may use bounded local source plus test/contract reads only
after owner evidence fails. Quoted blocks remain data, external research fails
closed, and no model, shell, indexing, or execution path exists.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from holo_index.freshness_receipt import read_git_head_sha
from holo_index.repository_state import repository_root_digest
from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    BOUNDED_SCHEMA_VERSION,
    canonical_digest,
    validate_grounded_target_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_bounded_iterative_retrieval import (
    MAX_TOTAL_GROUNDING_SECONDS,
    MAX_TOTAL_OWNER_QUERIES,
    TOTAL_READ_BUDGET_BYTES,
    ground_semantic_targets,
    requires_broad_semantic_evidence,
    split_quoted_reference_blocks,
)
from modules.communication.moltbot_bridge.src.reddog_holoindex_owner_query_client import (
    query_holoindex_owner,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_task_executor import (
    _resolve_safe_target,
)
from modules.communication.moltbot_bridge.src.reddog_repo_audit_fallback_grounding import (
    RepoAuditFallbackReason,
    build_bound_repo_audit_fallback,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_bootstrap import (
    resolve_reddog_holoindex_owner_handoff,
)


GROUNDING_RESULT_SCHEMA = "reddog_transport_grounding_result.v1"
INTENT_SCHEMA = "reddog_intent.v2"
MAX_WORK_FOCUS_CHARS = 12_000
MAX_TYPED_TARGETS = 16
MAX_SEMANTIC_TARGET_CHARS = 180
MAX_OWNER_QUERIES = MAX_TOTAL_OWNER_QUERIES
MAX_GROUNDING_SECONDS = MAX_TOTAL_GROUNDING_SECONDS

SOURCE_TO_ORIGIN = {
    "editor_thin_client": "extension",
    "hermes_thin_client": "hermes_agent",
    "api_thin_client": "api_client",
    "main_resident_host": "main.py",
}

ACTION_RE = re.compile(
    r"\b(?:analy[sz]e|assess|audit|build|compare|complete|create|debug|design|"
    r"determine|evaluate|fix|harden|implement|improve|inspect|investigate|plan|"
    r"refactor|research|review|update|verify)\b",
    re.IGNORECASE,
)
PATH_RE = re.compile(
    r"(?<![A-Za-z0-9:/])((?:[A-Za-z0-9_.-]+/){1,16}"
    r"[A-Za-z0-9_.@+-]+\.[A-Za-z0-9]{1,12}(?:#[A-Za-z_][A-Za-z0-9_]*)?)"
)
SLASH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9:/])([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+){1,20})"
)
WINDOWS_ABSOLUTE_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]:/[A-Za-z0-9_./-]+)")
POSIX_ABSOLUTE_RE = re.compile(r"(?<![A-Za-z0-9:])(/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+)")
DENIED_BARE_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(\.env(?:\.(?:local|production))?|id_rsa|id_dsa)(?![A-Za-z0-9_.-])",
    re.IGNORECASE,
)
FOUNDUP_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,255}$")
URL_RE = re.compile(r"https://[^\s<>()\[\]{}]+", re.IGNORECASE)
SEMANTIC_HEADER_RE = re.compile(
    r"^(?:semantic(?:\s+targets?)?|concepts?|topics?|research\s+questions?)\s*:\s*(.+)$",
    re.IGNORECASE,
)
DIAGNOSTIC_MARKERS = ("## run trace", "## work trail", "daemon output", "[env-hygiene]")
class GroundingServiceReason:
    REQUEST_INVALID = "grounding_service_request_invalid"
    SOURCE_INVALID = "grounding_service_source_invalid"
    REPO_TARGET_UNSAFE = "grounding_repo_target_unsafe_or_missing"
    TARGET_UNIVERSE_EMPTY = "grounding_target_universe_empty"
    TARGET_LIMIT = "grounding_typed_target_limit_exceeded"
    HOLOINDEX_FAILED = "grounding_holoindex_owner_query_failed"
    HOLOINDEX_STALE = "grounding_holoindex_generation_not_current"
    SEMANTIC_EVIDENCE = "grounding_semantic_evidence_insufficient"
    REPO_AUDIT_EVIDENCE = "grounding_repo_audit_evidence_incomplete"
    REPO_STATE = "grounding_repo_state_unavailable_or_changed"
    EXTERNAL_RESEARCH = "grounding_external_research_adapter_required"
    RECEIPT_INVALID = "grounding_receipt_self_validation_failed"


OwnerQuery = Callable[[str], Mapping[str, Any]]


@dataclass(frozen=True)
class TransportGroundingResult:
    schema_version: str
    accepted: bool
    intent: Mapping[str, Any] = field(default_factory=dict)
    grounding_receipt: Mapping[str, Any] = field(default_factory=dict)
    typed_targets: Mapping[str, Any] = field(default_factory=dict)
    rejection_reasons: tuple[str, ...] = ()
    no_model_call_performed: bool = True
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_external_research_performed: bool = True
    no_execution_authority_granted: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "accepted": self.accepted,
            "intent": dict(self.intent),
            "grounding_receipt": dict(self.grounding_receipt),
            "typed_targets": dict(self.typed_targets),
            "rejection_reasons": list(self.rejection_reasons),
            "no_model_call_performed": self.no_model_call_performed,
            "no_shell_command_executed": self.no_shell_command_executed,
            "no_repo_mutation_performed": self.no_repo_mutation_performed,
            "no_holoindex_reindex_performed": self.no_holoindex_reindex_performed,
            "no_external_research_performed": self.no_external_research_performed,
            "no_execution_authority_granted": self.no_execution_authority_granted,
        }


def ground_transport_work_focus(
    *,
    repo_root: Path | str,
    work_focus: str,
    foundup_id: str,
    authenticated_principal_id: str,
    source_surface: str,
    client_request_id: str,
    owner_query: OwnerQuery | None = None,
    service_url: str | None = None,
    service_token: str | None = None,
    timeout_seconds: float = 15.0,
) -> TransportGroundingResult:
    """Build one verified grounded v2 intent or fail closed."""

    root = Path(repo_root).resolve()
    focus = str(work_focus or "")
    principal = str(authenticated_principal_id or "").strip()
    foundup = str(foundup_id or "").strip()
    request_id = str(client_request_id or "").strip()
    source = str(source_surface or "").strip()
    reasons: list[str] = []
    if (
        not focus.strip()
        or len(focus) > MAX_WORK_FOCUS_CHARS
        or "\x00" in focus
        or not principal
        or len(principal) > 256
        or any(ord(character) < 32 for character in principal)
        or FOUNDUP_ID_RE.fullmatch(foundup) is None
        or REQUEST_ID_RE.fullmatch(request_id) is None
    ):
        reasons.append(GroundingServiceReason.REQUEST_INVALID)
    if source not in SOURCE_TO_ORIGIN:
        reasons.append(GroundingServiceReason.SOURCE_INVALID)
    if reasons:
        return _reject(reasons)

    quoted_blocks, unquoted = _extract_quoted_blocks(focus)
    typed = _extract_typed_targets(unquoted, quoted_blocks)
    if not _typed_targets_within_limit(typed):
        return _reject((GroundingServiceReason.TARGET_LIMIT,))
    repo_targets = list(typed["repo_file_targets"])
    semantic_targets = list(typed["semantic_targets"])
    external_targets = list(typed["external_research_targets"])
    substantive = _is_substantive_request(unquoted)
    broad_request = requires_broad_semantic_evidence(unquoted)
    if substantive and not (repo_targets or semantic_targets or external_targets):
        reasons.append(GroundingServiceReason.TARGET_UNIVERSE_EMPTY)

    direct_paths: list[str] = []
    missing_paths: list[str] = []
    for target in repo_targets:
        path_only = target.split("#", 1)[0]
        safe = _resolve_safe_target(root, path_only)
        if safe is None:
            missing_paths.append(target)
        else:
            direct_paths.append(safe.relative_to(root).as_posix())
    if missing_paths:
        reasons.append(GroundingServiceReason.REPO_TARGET_UNSAFE)

    semantic_coverage: list[Mapping[str, Any]] = []
    owner_results: list[Mapping[str, Any]] = []
    retrieval_traces: list[Mapping[str, Any]] = []
    semantic_read_attempts: list[Mapping[str, Any]] = []
    repo_audit_fallback: Mapping[str, Any] = {}
    if semantic_targets:
        deadline = time.monotonic() + min(
            max(float(timeout_seconds), 1.0), MAX_GROUNDING_SECONDS
        )
        query = owner_query or _owner_query(
            repo_root=root,
            service_url=service_url,
            service_token=service_token,
            timeout_seconds=timeout_seconds,
            deadline_monotonic=deadline,
        )
        semantic_state = ground_semantic_targets(
            root,
            semantic_targets,
            owner_query=query,
            deadline_monotonic=deadline,
            broad_request=broad_request,
            max_owner_queries=MAX_OWNER_QUERIES,
        )
        semantic_coverage = list(semantic_state.coverage)
        owner_results = list(semantic_state.owner_results)
        retrieval_traces = list(semantic_state.retrieval_traces)
        semantic_read_attempts = list(semantic_state.read_attempts)
        reasons.extend(semantic_state.rejection_reasons)

    owner_failure_reasons = {
        GroundingServiceReason.HOLOINDEX_FAILED,
        GroundingServiceReason.HOLOINDEX_STALE,
        GroundingServiceReason.SEMANTIC_EVIDENCE,
    }
    if (
        len(semantic_targets) == 1
        and not repo_targets
        and any(reason in owner_failure_reasons for reason in reasons)
    ):
        fallback = build_bound_repo_audit_fallback(
            repo_root=root,
            work_focus=focus,
            owner_results=owner_results,
        )
        if fallback.applied:
            repo_audit_fallback = fallback.receipt
            if fallback.accepted:
                typed = {
                    **typed,
                    "repo_file_targets": list(fallback.repo_file_targets),
                    "semantic_targets": [],
                }
                repo_targets = list(fallback.repo_file_targets)
                direct_paths = list(fallback.repo_file_targets)
                semantic_coverage = []
                reasons = [reason for reason in reasons if reason not in owner_failure_reasons]
            else:
                if RepoAuditFallbackReason.REPO_STATE in fallback.rejection_reasons:
                    reasons.append(GroundingServiceReason.REPO_STATE)
                if RepoAuditFallbackReason.EVIDENCE in fallback.rejection_reasons:
                    reasons.append(GroundingServiceReason.REPO_AUDIT_EVIDENCE)

    if external_targets:
        reasons.append(GroundingServiceReason.EXTERNAL_RESEARCH)

    reasons = list(dict.fromkeys(reasons))
    receipt = _build_grounding_receipt(
        repo_root=root,
        work_focus=focus,
        source_surface=source,
        typed=typed,
        semantic_coverage=semantic_coverage,
        retrieval_traces=retrieval_traces,
        semantic_read_attempts=semantic_read_attempts,
        owner_results=owner_results,
        direct_paths=direct_paths,
        missing_paths=missing_paths,
        substantive=substantive,
        rejection_reasons=reasons,
        repo_audit_fallback=repo_audit_fallback,
    )
    if reasons:
        return _reject(reasons, typed=typed, receipt=receipt)
    validation = validate_grounded_target_receipt(
        receipt,
        work_focus=focus,
        expected_source_surface=source,
    )
    if not validation.accepted:
        return _reject(
            [GroundingServiceReason.RECEIPT_INVALID, *validation.rejection_reasons],
            typed=typed,
            receipt=receipt,
        )

    intent_payload = {
        "schema_version": INTENT_SCHEMA,
        "source_surface": source,
        "origin": SOURCE_TO_ORIGIN[source],
        "principal_ref": principal,
        "foundup_id": foundup,
        "work_focus": focus,
        "grounding_receipt": receipt,
        "submits_executable_authority": False,
        "client_request_id": request_id,
    }
    intent = {
        **intent_payload,
        "intent_id": canonical_digest(intent_payload),
    }
    return TransportGroundingResult(
        schema_version=GROUNDING_RESULT_SCHEMA,
        accepted=True,
        intent=intent,
        grounding_receipt=receipt,
        typed_targets=typed,
    )


def _extract_quoted_blocks(text: str) -> tuple[list[Mapping[str, str]], str]:
    return split_quoted_reference_blocks(text)


def _typed_targets_within_limit(typed: Mapping[str, Any]) -> bool:
    return sum(
        len(typed[key])
        for key in (
            "repo_file_targets", "semantic_targets", "external_research_targets",
        )
    ) <= MAX_TYPED_TARGETS


def _extract_typed_targets(
    unquoted: str,
    quoted_blocks: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    scan = unquoted.replace("\\", "/")
    external = _dedupe(
        _clean_url(match.group(0)) for match in URL_RE.finditer(scan)
    )
    without_urls = URL_RE.sub(" ", scan)
    repo_candidates = [
        _normalize_repo_target(match.group(1)) for match in PATH_RE.finditer(without_urls)
    ]
    for match in SLASH_TOKEN_RE.finditer(without_urls):
        candidate = _normalize_repo_target(match.group(1))
        parts = candidate.split("/")
        if ".." in parts or (parts and parts[-1].lower() == ".env"):
            repo_candidates.append(candidate)
    repo_candidates.extend(
        _normalize_repo_target(match.group(1))
        for pattern in (WINDOWS_ABSOLUTE_RE, POSIX_ABSOLUTE_RE, DENIED_BARE_RE)
        for match in pattern.finditer(without_urls)
    )
    repo = _dedupe(repo_candidates)
    without_paths = PATH_RE.sub(" ", without_urls)
    semantic: list[str] = []
    for line in without_paths.splitlines():
        match = SEMANTIC_HEADER_RE.match(line.strip())
        if not match:
            continue
        for part in re.split(r"\s*[;,]\s*", match.group(1)):
            value = " ".join(part.split())[:MAX_SEMANTIC_TARGET_CHARS]
            if len(value) >= 4:
                semantic.append(value)
    if not semantic and not repo and not external and _is_substantive_request(without_paths):
        candidate = " ".join(without_paths.split())[:MAX_SEMANTIC_TARGET_CHARS]
        if candidate:
            semantic.append(candidate)
    semantic = _dedupe(semantic)
    return {
        "repo_file_targets": repo,
        "semantic_targets": semantic,
        "external_research_targets": external,
        "quoted_reference_blocks_count": len(quoted_blocks),
        "quoted_reference_blocks_digest": canonical_digest(list(quoted_blocks)),
    }


def _is_substantive_request(unquoted: str) -> bool:
    lowered = unquoted.lower()
    diagnostic = any(marker in lowered for marker in DIAGNOSTIC_MARKERS)
    return ACTION_RE.search(unquoted) is not None and not diagnostic


def _build_grounding_receipt(
    *,
    repo_root: Path,
    work_focus: str,
    source_surface: str,
    typed: Mapping[str, Any],
    semantic_coverage: Sequence[Mapping[str, Any]],
    retrieval_traces: Sequence[Mapping[str, Any]],
    semantic_read_attempts: Sequence[Mapping[str, Any]],
    owner_results: Sequence[Mapping[str, Any]],
    direct_paths: Sequence[str],
    missing_paths: Sequence[str],
    substantive: bool,
    rejection_reasons: Sequence[str],
    repo_audit_fallback: Mapping[str, Any],
) -> Mapping[str, Any]:
    payload = {
        **_base_receipt_fields(
            work_focus, source_surface, typed, substantive, rejection_reasons
        ),
        **_semantic_receipt_fields(
            semantic_coverage, retrieval_traces, semantic_read_attempts
        ),
        **_repo_receipt_fields(
            repo_root, typed, direct_paths, missing_paths, semantic_coverage,
            repo_audit_fallback,
        ),
        **_owner_receipt_fields(owner_results),
    }
    return {**payload, "receipt_id": canonical_digest(payload)}


def _base_receipt_fields(work_focus, source_surface, typed, substantive, reasons):
    return {
        "schema_version": BOUNDED_SCHEMA_VERSION,
        "source_surface": source_surface,
        "work_focus_digest": canonical_digest({"work_focus": work_focus}),
        "typed_targets": dict(typed),
        "typed_targets_digest": canonical_digest(typed),
        "grounding_preflight_applied": True,
        "grounding_preflight_passed": not reasons,
        "grounding_preflight_rejection_reasons": list(reasons),
        "grounding_target_universe_required": substantive,
        "repo_file_targets_count": len(typed.get("repo_file_targets") or ()),
        "semantic_targets_count": len(typed.get("semantic_targets") or ()),
        "external_research_targets_count": len(typed.get("external_research_targets") or ()),
        "quoted_reference_blocks_count": int(typed.get("quoted_reference_blocks_count") or 0),
    }


def _semantic_receipt_fields(coverage, traces, read_attempts):
    query_attempts = sum(
        len(trace.get("attempts") or ()) for trace in traces if isinstance(trace, Mapping)
    )
    attempted_bytes = sum(int(item.get("bytes") or 0) for item in read_attempts)
    return {
        "semantic_target_coverage": list(coverage),
        "semantic_target_coverage_digest": canonical_digest({"semantic_target_coverage": list(coverage)}),
        "semantic_retrieval_traces": list(traces),
        "semantic_retrieval_traces_digest": canonical_digest({"semantic_retrieval_traces": list(traces)}),
        "semantic_owner_query_attempts_total": query_attempts,
        "semantic_owner_query_budget": MAX_OWNER_QUERIES,
        "semantic_grounding_deadline_seconds": MAX_GROUNDING_SECONDS,
        "semantic_direct_read_attempts": list(read_attempts),
        "semantic_direct_read_attempts_digest": canonical_digest({"semantic_direct_read_attempts": list(read_attempts)}),
        "semantic_direct_read_bytes_total": attempted_bytes,
        "semantic_direct_read_budget_bytes": TOTAL_READ_BUDGET_BYTES,
    }


def _repo_receipt_fields(repo_root, typed, direct_paths, missing_paths, coverage, fallback):
    heads = {
        str(record.get("repo_head_sha") or "")
        for item in coverage for record in item.get("evidence_records", ())
        if isinstance(record, Mapping)
    }
    repo_targets = list(typed.get("repo_file_targets") or ())
    semantic_paths = _dedupe(
        str(record.get("path") or "")
        for item in coverage for record in item.get("evidence_records", ())
        if isinstance(record, Mapping)
    )
    return {
        "target_recall_ok": (not missing_paths) if repo_targets else None,
        "required_targets_missing": list(missing_paths),
        "direct_read_paths": list(direct_paths),
        "semantic_direct_read_paths": semantic_paths,
        "repo_audit_fallback_used": bool(fallback),
        "repo_audit_fallback": dict(fallback),
        "repo_audit_fallback_digest": canonical_digest(fallback) if fallback else "",
        "repo_state_head_sha": str(
            fallback.get("repo_head_sha")
            or (next(iter(heads)) if len(heads) == 1 else read_git_head_sha(repo_root))
        ),
        "repo_state_root_digest": repository_root_digest(repo_root),
    }


def _owner_receipt_fields(owner_results):
    owner = owner_results[0] if owner_results else {}
    return {
        "holoindex_owner_query_ok": bool(owner_results) and all(item.get("ok") is True for item in owner_results),
        "holoindex_freshness": str(owner.get("freshness") or "UNKNOWN"),
        "holoindex_generation_id": str(owner.get("freshness_generation_id") or ""),
        "holoindex_freshness_receipt_digest": str(owner.get("freshness_receipt_digest") or ""),
        "holoindex_repo_head_sha": str(owner.get("repo_head_sha") or ""),
        "holoindex_repo_root_digest": str(owner.get("repo_root_digest") or ""),
        "holoindex_query_receipt_id": canonical_digest({"owner_results": list(owner_results)}) if owner_results else "",
        "holoindex_index_gap_detected": any(item.get("index_gap_detected") is not False for item in owner_results),
        "no_holoindex_reindex_performed": all(
            item.get("no_holoindex_reindex_performed") is True for item in owner_results
        ) if owner_results else True,
    }


def _owner_query(
    *,
    repo_root: Path,
    service_url: str | None,
    service_token: str | None,
    timeout_seconds: float,
    deadline_monotonic: float,
) -> OwnerQuery:
    if service_url is None and service_token is None:
        try:
            handoff = resolve_reddog_holoindex_owner_handoff()
        except Exception:
            handoff = None
        if handoff is not None:
            service_url, service_token = handoff
    def query_owner(query: str) -> Mapping[str, Any]:
        remaining = max(0.001, deadline_monotonic - time.monotonic())
        requested = max(0.001, float(timeout_seconds))
        return query_holoindex_owner(
            repo_root=repo_root,
            query=query,
            limit=12,
            service_url=service_url,
            service_token=service_token,
            timeout_seconds=min(requested, remaining),
        )

    return query_owner


def _normalize_repo_target(value: str) -> str:
    normalized = str(value or "").strip("`'\"()[]{}<>").rstrip(".,;:").replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _clean_url(value: str) -> str:
    return str(value or "").rstrip(".,;:!?)\"]}'")


def _dedupe(values: Sequence[str] | Any) -> list[str]:
    return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _reject(
    reasons: Sequence[str],
    *,
    typed: Mapping[str, Any] | None = None,
    receipt: Mapping[str, Any] | None = None,
) -> TransportGroundingResult:
    return TransportGroundingResult(
        schema_version=GROUNDING_RESULT_SCHEMA,
        accepted=False,
        typed_targets=dict(typed or {}),
        grounding_receipt=dict(receipt or {}),
        rejection_reasons=tuple(dict.fromkeys(str(item) for item in reasons if str(item))),
    )


__all__ = [
    "GROUNDING_RESULT_SCHEMA",
    "GroundingServiceReason",
    "TransportGroundingResult",
    "ground_transport_work_focus",
]
