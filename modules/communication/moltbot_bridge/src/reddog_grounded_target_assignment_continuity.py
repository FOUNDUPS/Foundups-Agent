"""Validate integrity-only RedDog grounding receipts across assignments."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from holo_index.cli.repo_audit_discovery import (
    canonicalize_entity, detect_repo_audit_intent, repo_audit_category,
    repo_audit_path_supports_entity,
)
from modules.communication.moltbot_bridge.src.reddog_repo_audit_fallback_grounding import (
    NO_ACTION_FIELDS,
    REPO_AUDIT_POLICY,
)
from modules.communication.moltbot_bridge.src.reddog_bounded_iterative_retrieval import (
    MAX_TOTAL_GROUNDING_SECONDS,
    MAX_TOTAL_OWNER_QUERIES,
    canonical_digest as retrieval_digest,
    validate_bounded_retrieval_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_grounding_evidence_rehydration import (
    RehydratedSemanticEvidenceRecord, VerifiedGroundedSemanticEvidence,
    rehydrate_semantic_receipt_evidence,
)

SCHEMA_VERSION = "reddog_grounded_target_receipt.v1"
BOUNDED_SCHEMA_VERSION = "reddog_grounded_target_receipt.v2"
SOURCE_SURFACES = frozenset(
    {"editor_thin_client", "hermes_thin_client", "api_thin_client", "main_resident_host"}
)
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_OBJECT_ID_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
REGULAR_GIT_MODES = frozenset({"100644", "100755"})
REPO_AUDIT_PRUNED_SEGMENTS = frozenset({
    ".agent", ".agents", ".cache", ".chroma", ".claude", ".codex", ".cursor",
    ".git", ".idea", ".m2m", ".memory", ".venv", ".vscode", ".windsurf",
    ".worktrees", "__pycache__", "archive", "archives", "build", "cache", "chroma",
    "dist", "generated", "log", "logs", "memory", "node_modules", "temp", "tmp",
    "vector", "vectors", "vendor", "venv",
})
REPO_AUDIT_SECRET_MARKERS = ("secret", "credential", "token", "private_key", "apikey", "api_key")
REPO_AUDIT_SECRET_NAMES = frozenset({".env", "id_rsa", "id_ed25519"})
REPO_AUDIT_SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".keystore", ".vsix")
REPO_AUDIT_ALLOWED_SUFFIXES = frozenset({
    ".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".rst", ".txt", ".json",
    ".yaml", ".yml", ".toml", ".html", ".css", ".sol", ".go", ".rs", ".java",
    ".c", ".h",
})


class GroundingReason:
    MISSING = "grounding_receipt_missing"
    SCHEMA = "grounding_receipt_schema_invalid"
    RECEIPT_ID = "grounding_receipt_id_invalid"
    SOURCE = "grounding_source_surface_invalid"
    WORK_FOCUS = "grounding_work_focus_mismatch"
    TARGET_DIGEST = "grounding_typed_targets_digest_invalid"
    PREFLIGHT = "grounding_preflight_not_passed"
    TARGET_UNIVERSE = "grounding_target_universe_empty"
    SEMANTIC_COVERAGE = "grounding_semantic_coverage_invalid"
    SEMANTIC_GENERATION = "grounding_semantic_generation_invalid"
    SEMANTIC_TRACE = "grounding_semantic_retrieval_trace_invalid"
    REHYDRATION_SCHEMA = "grounding_semantic_rehydration_schema_invalid"
    REHYDRATION_ROOT = "grounding_semantic_rehydration_root_mismatch"
    REHYDRATION_HEAD = "grounding_semantic_rehydration_head_mismatch"
    REHYDRATION_EVIDENCE = "grounding_semantic_rehydration_evidence_mismatch"
    REPO_STATE = "grounding_repository_state_binding_invalid"
    REPO_RECALL = "grounding_repo_recall_invalid"
    REPO_AUDIT = "grounding_repo_audit_receipt_invalid"
    COUNTS = "grounding_target_counts_invalid"


@dataclass(frozen=True)
class VerifiedGroundedTargetReceipt:
    receipt: Mapping[str, Any]
    receipt_id: str
    work_focus_digest: str
    typed_targets_digest: str
    repo_file_targets: tuple[str, ...]
    semantic_targets: tuple[str, ...]
    external_research_targets: tuple[str, ...]
    allowed_read_targets: tuple[str, ...]
    holoindex_generation_id: str
    holoindex_query_receipt_id: str

    def to_dict(self) -> dict[str, Any]:
        return dict(self.receipt)


@dataclass(frozen=True)
class GroundedTargetReceiptValidation:
    accepted: bool
    verified: VerifiedGroundedTargetReceipt | None
    rejection_reasons: tuple[str, ...]


def canonical_digest(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def validate_grounded_target_receipt(receipt: Mapping[str, Any] | None, *, work_focus: str, expected_source_surface: str | None = None) -> GroundedTargetReceiptValidation:
    reasons: list[str] = []
    if not isinstance(receipt, Mapping):
        return _rejected(GroundingReason.MISSING)
    data = dict(receipt)
    schema = str(data.get("schema_version") or "")
    if schema not in {SCHEMA_VERSION, BOUNDED_SCHEMA_VERSION}:
        reasons.append(GroundingReason.SCHEMA)
    receipt_id, expected_focus_digest = _validate_receipt_identity(
        data, work_focus, expected_source_surface, reasons
    )
    typed = data.get("typed_targets")
    typed_mapping = dict(typed) if isinstance(typed, Mapping) else {}
    typed_digest = str(data.get("typed_targets_digest") or "")
    if not typed_mapping or typed_digest != canonical_digest(typed_mapping):
        reasons.append(GroundingReason.TARGET_DIGEST)
    targets = _targets(typed_mapping)
    _validate_counts(data, typed_mapping, reasons)
    if data.get("grounding_preflight_applied") is not True or data.get("grounding_preflight_passed") is not True:
        reasons.append(GroundingReason.PREFLIGHT)
    if _strings(data.get("grounding_preflight_rejection_reasons")):
        reasons.append(GroundingReason.PREFLIGHT)
    if data.get("grounding_target_universe_required") is True and not any(targets):
        reasons.append(GroundingReason.TARGET_UNIVERSE)
    if schema == BOUNDED_SCHEMA_VERSION:
        if any(targets[:2]) and not _valid_repository_state_binding(data):
            reasons.append(GroundingReason.REPO_STATE)
        _validate_semantic_v2(data, targets[1], reasons)
        _validate_retrieval_traces(data, targets[1], reasons)
    elif schema == SCHEMA_VERSION:
        _validate_semantic_v1(data, targets[1], reasons)
    _validate_repo(data, targets[0], str(work_focus or ""), reasons)
    reasons = list(dict.fromkeys(reasons))
    if reasons:
        return GroundedTargetReceiptValidation(False, None, tuple(reasons))
    verified = VerifiedGroundedTargetReceipt(
        receipt=data,
        receipt_id=receipt_id,
        work_focus_digest=expected_focus_digest,
        typed_targets_digest=typed_digest,
        repo_file_targets=targets[0],
        semantic_targets=targets[1],
        external_research_targets=targets[2],
        allowed_read_targets=tuple(dict.fromkeys(
            (*targets[0], *_strings(data.get("semantic_direct_read_paths")))
        )),
        holoindex_generation_id=str(data.get("holoindex_generation_id") or ""),
        holoindex_query_receipt_id=str(data.get("holoindex_query_receipt_id") or ""),
    )
    return GroundedTargetReceiptValidation(True, verified, ())


def resolve_grounding_read_targets(
    receipt: Mapping[str, Any] | None, *, work_focus: str
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return only read targets carried by a validated grounding receipt."""

    if receipt is None:
        return (), ()
    validation = validate_grounded_target_receipt(receipt, work_focus=work_focus)
    if not validation.accepted or validation.verified is None:
        return (), validation.rejection_reasons
    return validation.verified.allowed_read_targets, ()


def _validate_receipt_identity(
    data: Mapping[str, Any],
    work_focus: str,
    expected_source_surface: str | None,
    reasons: list[str],
) -> tuple[str, str]:
    source = str(data.get("source_surface") or "").strip()
    if source not in SOURCE_SURFACES or (expected_source_surface and source != expected_source_surface):
        reasons.append(GroundingReason.SOURCE)
    receipt_id = str(data.get("receipt_id") or "")
    payload = dict(data)
    payload.pop("receipt_id", None)
    if not SHA256_RE.fullmatch(receipt_id) or receipt_id != canonical_digest(payload):
        reasons.append(GroundingReason.RECEIPT_ID)
    focus_digest = canonical_digest({"work_focus": str(work_focus or "")})
    if data.get("work_focus_digest") != focus_digest:
        reasons.append(GroundingReason.WORK_FOCUS)
    return receipt_id, focus_digest


def rehydrate_grounded_semantic_evidence(
    receipt: Mapping[str, Any],
    *,
    work_focus: str,
    repo_root: Path | str,
) -> VerifiedGroundedSemanticEvidence:
    """Re-read v2 semantic evidence from exact HEAD before consumption."""

    validation = validate_grounded_target_receipt(receipt, work_focus=work_focus)
    if not validation.accepted or validation.verified is None:
        raise ValueError(GroundingReason.REHYDRATION_EVIDENCE)
    verified = validation.verified
    data = dict(receipt)
    if data.get("schema_version") != BOUNDED_SCHEMA_VERSION:
        raise ValueError(GroundingReason.REHYDRATION_SCHEMA)
    try:
        return rehydrate_semantic_receipt_evidence(
            data,
            repo_root=repo_root,
            receipt_id=verified.receipt_id,
            work_focus=work_focus,
        )
    except ValueError as exc:
        message = str(exc)
        if message == GroundingReason.REHYDRATION_ROOT:
            raise ValueError(GroundingReason.REHYDRATION_ROOT) from exc
        if message == GroundingReason.REHYDRATION_HEAD:
            raise ValueError(GroundingReason.REHYDRATION_HEAD) from exc
        raise ValueError(GroundingReason.REHYDRATION_EVIDENCE) from exc

def _targets(typed: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    return (
        _strings(typed.get("repo_file_targets")),
        _strings(typed.get("semantic_targets")),
        _strings(typed.get("external_research_targets")),
    )

def _validate_counts(data: Mapping[str, Any], typed: Mapping[str, Any], reasons: list[str]) -> None:
    expected = {
        "repo_file_targets_count": len(_strings(typed.get("repo_file_targets"))),
        "semantic_targets_count": len(_strings(typed.get("semantic_targets"))),
        "external_research_targets_count": len(_strings(typed.get("external_research_targets"))),
        "quoted_reference_blocks_count": int(typed.get("quoted_reference_blocks_count") or 0),
    }
    if any(_integer(data.get(key)) != value for key, value in expected.items()):
        reasons.append(GroundingReason.COUNTS)

def _validate_semantic_v1(
    data: Mapping[str, Any], targets: Sequence[str], reasons: list[str]
) -> None:
    coverage = data.get("semantic_target_coverage")
    records = tuple(item for item in coverage if isinstance(item, Mapping)) if _sequence(coverage) else ()
    digest = str(data.get("semantic_target_coverage_digest") or "")
    if digest != canonical_digest({"semantic_target_coverage": list(records)}):
        reasons.append(GroundingReason.SEMANTIC_COVERAGE)
    covered = tuple(str(item.get("target") or "") for item in records)
    if tuple(targets) != covered or any(item.get("verdict") != "SUFFICIENT" for item in records):
        reasons.append(GroundingReason.SEMANTIC_COVERAGE)
    if targets and not _valid_semantic_generation_v1(data):
        reasons.append(GroundingReason.SEMANTIC_GENERATION)

def _valid_semantic_generation_v1(data: Mapping[str, Any]) -> bool:
    return _valid_semantic_generation(data, bounded=False)

def _valid_semantic_generation(data: Mapping[str, Any], *, bounded: bool) -> bool:
    common = all((
        data.get("holoindex_owner_query_ok") is True,
        data.get("holoindex_freshness") == "CURRENT",
        data.get("holoindex_index_gap_detected") is False,
        data.get("no_holoindex_reindex_performed") is True,
        SHA256_RE.fullmatch(str(data.get("holoindex_generation_id") or "")) is not None,
        SHA256_RE.fullmatch(str(data.get("holoindex_query_receipt_id") or "")) is not None,
        SHA256_RE.fullmatch(str(data.get("holoindex_freshness_receipt_digest") or "")) is not None,
        bool(str(data.get("holoindex_repo_head_sha") or "").strip()),
    ))
    return common and (not bounded or all((
        SHA256_RE.fullmatch(str(data.get("holoindex_repo_root_digest") or "")) is not None,
        data.get("repo_state_head_sha") == data.get("holoindex_repo_head_sha"),
        data.get("repo_state_root_digest") == data.get("holoindex_repo_root_digest"),
    )))

def _validate_semantic_v2(
    data: Mapping[str, Any], targets: Sequence[str], reasons: list[str]
) -> None:
    coverage = data.get("semantic_target_coverage")
    records = tuple(item for item in coverage if isinstance(item, Mapping)) if _sequence(coverage) else ()
    digest = str(data.get("semantic_target_coverage_digest") or "")
    if digest != canonical_digest({"semantic_target_coverage": list(records)}):
        reasons.append(GroundingReason.SEMANTIC_COVERAGE)
    covered = tuple(str(item.get("target") or "") for item in records)
    evidence_paths = tuple(
        str(record.get("path") or "")
        for item in records
        for record in item.get("evidence_records", ())
        if isinstance(record, Mapping)
    )
    if (
        tuple(targets) != covered
        or any(not _valid_semantic_coverage_record(item) for item in records)
        or tuple(_strings(data.get("semantic_direct_read_paths")))
        != tuple(dict.fromkeys(evidence_paths))
    ):
        reasons.append(GroundingReason.SEMANTIC_COVERAGE)
    if not targets:
        return
    if not _valid_semantic_generation(data, bounded=True):
        reasons.append(GroundingReason.SEMANTIC_GENERATION)

def _valid_repository_state_binding(data: Mapping[str, Any]) -> bool:
    return bool(
        GIT_OBJECT_ID_RE.fullmatch(str(data.get("repo_state_head_sha") or ""))
        and SHA256_RE.fullmatch(str(data.get("repo_state_root_digest") or ""))
    )

def _validate_retrieval_traces(
    data: Mapping[str, Any], targets: Sequence[str], reasons: list[str]
) -> None:
    raw = data.get("semantic_retrieval_traces")
    traces = list(raw) if _sequence(raw) else []
    attempt_count = sum(
        len(trace.get("attempts") or ())
        for trace in traces
        if isinstance(trace, Mapping)
    )
    if data.get("semantic_retrieval_traces_digest") != retrieval_digest(
        {"semantic_retrieval_traces": traces}
    ):
        reasons.append(GroundingReason.SEMANTIC_TRACE)
        return
    if not (
        data.get("semantic_owner_query_attempts_total") == attempt_count
        and data.get("semantic_owner_query_budget") == MAX_TOTAL_OWNER_QUERIES
        and data.get("semantic_grounding_deadline_seconds")
        == MAX_TOTAL_GROUNDING_SECONDS
        and attempt_count <= MAX_TOTAL_OWNER_QUERIES
    ):
        reasons.append(GroundingReason.SEMANTIC_TRACE)
        return
    fallback_used = data.get("repo_audit_fallback_used") is True
    if targets:
        coverage = data.get("semantic_target_coverage")
        coverage_records = list(coverage) if _sequence(coverage) else []
        valid = len(traces) == len(targets) == len(coverage_records) and all(
            _valid_selected_trace(trace, target, item)
            for trace, target, item in zip(traces, targets, coverage_records)
        )
    elif fallback_used:
        valid = len(traces) == 1 and _valid_fallback_trace(traces[0])
    else:
        valid = not traces
    if not valid:
        reasons.append(GroundingReason.SEMANTIC_TRACE)

def _valid_fallback_trace(trace: Any) -> bool:
    if not isinstance(trace, Mapping):
        return False
    variants = trace.get("query_variants")
    target = str(variants[0] or "") if _sequence(variants) and variants else ""
    return bool(
        target
        and trace.get("accepted") is False
        and validate_bounded_retrieval_receipt(trace, target=target)
    )

def _valid_selected_trace(trace: Any, target: str, coverage: Any) -> bool:
    if not isinstance(trace, Mapping) or not isinstance(coverage, Mapping):
        return False
    attempts = trace.get("attempts")
    records = list(attempts) if _sequence(attempts) else []
    selected = trace.get("selected_round")
    selected_attempt = next(
        (item for item in records if isinstance(item, Mapping) and item.get("round") == selected),
        None,
    )
    return bool(
        trace.get("accepted") is True
        and validate_bounded_retrieval_receipt(trace, target=target)
        and isinstance(selected_attempt, Mapping)
        and selected_attempt.get("coverage_digest") == retrieval_digest(dict(coverage))
        and _strings(selected_attempt.get("evidence_refs"))
        == _strings(coverage.get("evidence_refs"))
    )

def _valid_semantic_coverage_record(value: Mapping[str, Any]) -> bool:
    evidence = value.get("evidence_records")
    records = list(evidence) if _sequence(evidence) else []
    categories = {str(item.get("category") or "") for item in records if isinstance(item, Mapping)}
    refs = _strings(value.get("evidence_refs"))
    quality = value.get("evidence_quality")
    broad = bool(isinstance(quality, Mapping) and quality.get("required") is True)
    implementation = "implementation" in categories
    corroborated = bool({"verification", "authoritative"}.intersection(categories))
    return bool(
        value.get("verdict") == "SUFFICIENT"
        and isinstance(quality, Mapping)
        and quality.get("passed") is True
        and quality.get("repository_state_bound") is True
        and records
        and refs == tuple(str(item.get("path") or "") for item in records)
        and value.get("evidence_records_digest")
        == canonical_digest({"evidence_records": records})
        and all(_valid_semantic_record(item) for item in records)
        and (not broad or (implementation and corroborated))
    )

def _valid_semantic_record(record: Any) -> bool:
    if not isinstance(record, Mapping):
        return False
    path = str(record.get("path") or "").replace("\\", "/")
    category = str(record.get("category") or "")
    return bool(
        _valid_repo_file_record(record)
        and _valid_git_object_binding(record)
        and category in {"authoritative", "verification", "implementation", "supporting"}
        and (
            (category == "authoritative" and path.lower().startswith("wsp_framework/"))
            or (category == "implementation" and Path(path).suffix.lower() in {
                ".py", ".js", ".ts", ".rs", ".go", ".java"
            })
            or category in {"verification", "supporting"}
        )
        and re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", str(record.get("repo_head_sha") or ""))
    )

def _valid_git_object_binding(record: Mapping[str, Any]) -> bool:
    return bool(
        str(record.get("git_mode") or "") in REGULAR_GIT_MODES
        and GIT_OBJECT_ID_RE.fullmatch(str(record.get("blob_oid") or ""))
    )

def _validate_repo(
    data: Mapping[str, Any], targets: Sequence[str], work_focus: str, reasons: list[str]
) -> None:
    if not targets:
        return
    if data.get("target_recall_ok") is not True or _strings(data.get("required_targets_missing")):
        reasons.append(GroundingReason.REPO_RECALL)
    if data.get("repo_audit_fallback_used") is not True:
        return
    if tuple(targets) != _strings(data.get("direct_read_paths")):
        reasons.append(GroundingReason.REPO_RECALL)
    fallback = data.get("repo_audit_fallback")
    if not isinstance(fallback, Mapping):
        reasons.append(GroundingReason.REPO_AUDIT)
        return
    if not _valid_repo_audit_fallback(data, fallback, targets, work_focus):
        reasons.append(GroundingReason.REPO_AUDIT)

def _valid_repo_audit_fallback(
    data: Mapping[str, Any],
    fallback: Mapping[str, Any],
    targets: Sequence[str],
    work_focus: str,
) -> bool:
    audit = fallback.get("repo_audit_grounding")
    audit_mapping = dict(audit) if isinstance(audit, Mapping) else {}
    selected = audit_mapping.get("selected")
    records = (
        [dict(item) for item in selected if isinstance(item, Mapping)]
        if _sequence(selected)
        else []
    )
    intent = detect_repo_audit_intent(work_focus)
    expected_entity = str(intent.get("entity") or "")
    categories = {repo_audit_category(str(item.get("path") or "")) for item in records}
    paths = tuple(str(item.get("path") or "") for item in records)
    coverage = (
        audit_mapping.get("coverage")
        if isinstance(audit_mapping.get("coverage"), Mapping)
        else {}
    )
    state = {
        "repo_head_sha": str(fallback.get("repo_head_sha") or ""),
        "evidence_digest": str(fallback.get("selected_evidence_digest") or ""),
        "expected_entity": expected_entity,
        "search_mode": str(audit_mapping.get("search_mode") or ""),
        "work_focus_digest": canonical_digest({"work_focus": work_focus}),
        "policy_digest": canonical_digest(REPO_AUDIT_POLICY),
    }
    aliases = _strings(audit_mapping.get("aliases"))
    expected_search_mode = (
        "holo_evidence_only"
        if audit_mapping.get("holo_evidence_sufficient") is True
        else "holo_then_deterministic"
    )
    deterministic = audit_mapping.get("deterministic_candidates")
    deterministic_records = list(deterministic) if _sequence(deterministic) else []
    total_bytes = sum(_integer(item.get("bytes")) for item in records)
    return all((
        _valid_fallback_metadata(
            fallback, audit_mapping, intent, aliases, expected_entity, expected_search_mode
        ),
        _valid_fallback_evidence(
            records, categories, coverage, deterministic_records, total_bytes, expected_entity
        ),
        _valid_fallback_bindings(data, fallback, audit_mapping, records, paths, targets, state),
    ))

def _valid_fallback_metadata(
    fallback: Mapping[str, Any],
    audit: Mapping[str, Any],
    intent: Mapping[str, Any],
    aliases: Sequence[str],
    expected_entity: str,
    expected_search_mode: str,
) -> bool:
    fallback_true = ("applied", "accepted", "holo_owner_attempted_first")
    audit_true = ("applied", "audit_intent", "holo_first")
    return all((
        fallback.get("schema_version") == "reddog_repo_audit_fallback.v1",
        all(fallback.get(key) is True for key in fallback_true),
        fallback.get("holo_owner_evidence_usable") is False,
        fallback.get("expected_entity") == expected_entity,
        fallback.get("fixed_policy") == REPO_AUDIT_POLICY
        and fallback.get("fixed_policy_digest") == canonical_digest(REPO_AUDIT_POLICY),
        all(fallback.get(field_name) is True for field_name in NO_ACTION_FIELDS),
        not _strings(fallback.get("rejection_reasons")),
        audit.get("schema_version") == "repo_audit_grounding.v1",
        all(audit.get(key) is True for key in audit_true),
        intent.get("audit_intent") is True,
        audit.get("entity") == expected_entity and audit.get("search_mode") == expected_search_mode,
        bool(aliases) and all(canonicalize_entity(alias) == expected_entity for alias in aliases),
    ))

def _valid_fallback_evidence(
    records: Sequence[Mapping[str, Any]],
    categories: set[str],
    coverage: Mapping[str, Any],
    deterministic_records: Sequence[Any],
    total_bytes: int,
    expected_entity: str,
) -> bool:
    return all((
        len(deterministic_records) <= int(REPO_AUDIT_POLICY["max_selected_paths"]) * 3,
        coverage.get("verdict") == "PASS" and not _strings(coverage.get("reasons")),
        "implementation_source" in categories and bool(categories.intersection({"test", "contract"})),
        0 < len(records) <= int(REPO_AUDIT_POLICY["max_selected_paths"]),
        len({str(item.get("path") or "").casefold() for item in records}) == len(records),
        0 < total_bytes <= int(REPO_AUDIT_POLICY["total_read_budget_bytes"]),
        all(_valid_repo_audit_record(item, expected_entity) for item in records),
    ))


def _valid_fallback_bindings(
    data: Mapping[str, Any],
    fallback: Mapping[str, Any],
    audit: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    paths: Sequence[str],
    targets: Sequence[str],
    state: Mapping[str, Any],
) -> bool:
    return all((
        fallback.get("work_focus_digest") == state["work_focus_digest"] and tuple(targets) == paths,
        data.get("repo_audit_fallback_digest") == canonical_digest(fallback),
        fallback.get("repo_audit_grounding_digest") == canonical_digest(audit),
        fallback.get("selected_evidence_digest") == canonical_digest({"selected": records}),
        fallback.get("repository_state_digest") == canonical_digest(state),
        data.get("repo_state_head_sha") == fallback.get("repo_head_sha"),
        re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", state["repo_head_sha"]) is not None,
    ))


def _valid_repo_audit_record(record: Mapping[str, Any], expected_entity: str) -> bool:
    path = str(record.get("path") or "").replace("\\", "/")
    return bool(
        _valid_repo_file_record(record)
        and repo_audit_path_supports_entity(path, expected_entity)
        and record.get("category") == repo_audit_category(path)
    )


def _valid_repo_file_record(record: Mapping[str, Any]) -> bool:
    path = str(record.get("path") or "").replace("\\", "/")
    parts = path.split("/")
    lowered = [part.casefold() for part in parts]
    try:
        size = int(record.get("bytes"))
    except (TypeError, ValueError):
        return False
    return (
        bool(path)
        and not path.startswith("/")
        and not (len(path) > 1 and path[1] == ":")
        and all(part not in ("", ".", "..") for part in parts)
        and not any(part in REPO_AUDIT_PRUNED_SEGMENTS for part in lowered)
        and not any(part in REPO_AUDIT_SECRET_NAMES for part in lowered)
        and not any(marker in part for part in lowered for marker in REPO_AUDIT_SECRET_MARKERS)
        and not lowered[-1].endswith(REPO_AUDIT_SECRET_SUFFIXES)
        and Path(lowered[-1]).suffix in REPO_AUDIT_ALLOWED_SUFFIXES
        and SHA256_RE.fullmatch(str(record.get("digest") or "")) is not None
        and 0 < size <= int(REPO_AUDIT_POLICY["per_file_read_bytes"])
        and isinstance(record.get("truncated"), bool)
    )


def _strings(value: Any) -> tuple[str, ...]:
    if not _sequence(value):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _integer(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def _rejected(reason: str) -> GroundedTargetReceiptValidation:
    return GroundedTargetReceiptValidation(False, None, (reason,))


__all__ = [
    "BOUNDED_SCHEMA_VERSION",
    "GroundedTargetReceiptValidation",
    "GroundingReason",
    "RehydratedSemanticEvidenceRecord",
    "SCHEMA_VERSION",
    "VerifiedGroundedTargetReceipt",
    "VerifiedGroundedSemanticEvidence",
    "canonical_digest",
    "rehydrate_grounded_semantic_evidence",
    "resolve_grounding_read_targets",
    "validate_grounded_target_receipt",
]
