"""RedDog operational context snapshot runtime.

This module builds the read-only context boundary RedDog must bind before
Fusion, worker assignment, or execution authority. It consumes authoritative
work state, repo HEAD evidence, HoloIndex freshness receipts, breadcrumbs,
Brain artifacts, and workspace memory metadata without mutating any source.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from holo_index.freshness_receipt import (
    FreshnessCheck,
    HoloIndexFreshnessReceipt,
    evaluate_freshness_for_paths,
    load_freshness_receipt,
)


SNAPSHOT_SCHEMA_VERSION = "reddog_operational_context_snapshot.v1"
CONTEXT_POLICY_VERSION = "reddog_context_view_policy.v1"
REPO_STATE_RECEIPT_SCHEMA = "reddog_governed_git_repo_state.v2"
GIT_READINESS_SCHEMA = "reddog_governed_git_readiness.v2"
GIT_EXECUTABLE_SCHEMA = "reddog_governed_git_executable.v1"
MAX_EXECUTABLE_BYTES = 256 * 1024 * 1024
MAX_LINK_COUNT = 2**32 - 1
WINDOWS_VERIFIER_RELATIVE_DIGEST = "sha256:" + hashlib.sha256(
    b"System32/WindowsPowerShell/v1.0/powershell.exe"
).hexdigest()

SOURCE_REPO = "repo"
SOURCE_WORK_STATE = "work_state"
SOURCE_HOLOINDEX = "holoindex"
SOURCE_BREADCRUMBS = "breadcrumbs"
SOURCE_BRAIN = "brain"
SOURCE_WORKSPACE_MEMORY = "workspace_memory"
SOURCE_BOOTSTRAP_PROJECTION = "bootstrap_projection"

AUTHORITY_AUTHORITATIVE = "AUTHORITATIVE"
AUTHORITY_VERIFIED = "VERIFIED"
AUTHORITY_OBSERVATIONAL = "OBSERVATIONAL"
AUTHORITY_HISTORICAL = "HISTORICAL"

FRESH = "FRESH"
STALE = "STALE"
UNKNOWN = "UNKNOWN"
MISSING = "MISSING"

SNAPSHOT_ACCEPTED = "SNAPSHOT_ACCEPTED"
SNAPSHOT_REJECTED = "SNAPSHOT_REJECTED"
ASSIGNMENT_CONTEXT_VALID = "ASSIGNMENT_CONTEXT_VALID"
ASSIGNMENT_CONTEXT_STALE = "ASSIGNMENT_CONTEXT_STALE"

_ABSOLUTE_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/][^\s,\]\)}]+|[\\/][A-Za-z0-9_.-]+(?:[\\/][^\s,\]\)}]+)+)")
_SECRET_RE = re.compile(r"(?i)(api[_-]?key|secret|token|password|private[_-]?key|sk-[A-Za-z0-9_-]+)")


@dataclass(frozen=True)
class SourceReceipt:
    """Evidence receipt for one context source."""

    source: str
    authority_class: str
    required: bool
    observed_at: str
    source_version: str
    content_digest: str
    freshness: str
    rejection_reasons: tuple[str, ...] = ()
    record_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OperationalContextSnapshot:
    """Canonical RedDog runtime context snapshot."""

    schema_version: str
    policy_version: str
    snapshot_receipt_id: str
    snapshot_content_digest: str
    created_at: str
    valid_until: str
    repo_state: dict[str, Any]
    work_state: dict[str, Any]
    holoindex_state: dict[str, Any]
    breadcrumbs_state: dict[str, Any]
    brain_state: dict[str, Any]
    workspace_memory_state: dict[str, Any]
    source_receipts: tuple[SourceReceipt, ...]
    conflicts: tuple[str, ...] = ()
    rejection_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_receipts"] = [receipt.to_dict() for receipt in self.source_receipts]
        return data


@dataclass(frozen=True)
class ContextView:
    """Filtered model-visible view derived from an exact snapshot."""

    context_view_id: str
    snapshot_receipt_id: str
    snapshot_content_digest: str
    policy_version: str
    text: str
    included_sources: tuple[str, ...]
    omitted_sources: tuple[str, ...]
    redaction_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceBundle:
    """Derived evidence bundle that augments, but never mutates, a snapshot."""

    evidence_bundle_id: str
    snapshot_receipt_id: str
    context_view_id: str
    report_digests: tuple[str, ...]
    external_research_receipts: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SnapshotBuildResult:
    """Result returned by snapshot construction."""

    accepted: bool
    status: str
    snapshot: Optional[OperationalContextSnapshot]
    context_view: Optional[ContextView]
    source_receipts: tuple[SourceReceipt, ...]
    rejection_reasons: tuple[str, ...]
    conflicts: tuple[str, ...]
    no_repo_mutation_performed: bool = True
    no_holoindex_mutation_performed: bool = True
    no_queue_mutation_performed: bool = True
    no_worker_spawn_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "snapshot": self.snapshot.to_dict() if self.snapshot else None,
            "context_view": self.context_view.to_dict() if self.context_view else None,
            "source_receipts": [receipt.to_dict() for receipt in self.source_receipts],
            "rejection_reasons": list(self.rejection_reasons),
            "conflicts": list(self.conflicts),
            "no_repo_mutation_performed": self.no_repo_mutation_performed,
            "no_holoindex_mutation_performed": self.no_holoindex_mutation_performed,
            "no_queue_mutation_performed": self.no_queue_mutation_performed,
            "no_worker_spawn_performed": self.no_worker_spawn_performed,
        }


@dataclass(frozen=True)
class AssignmentContextCheck:
    """Gate result before assignment/work-order promotion."""

    accepted: bool
    status: str
    snapshot_receipt_id: str
    context_view_id: str
    evidence_bundle_id: Optional[str]
    rejection_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def observe_repo_state(
    repo_root: Path | str,
    governed_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Consume the extension's already-verified governed Git state receipt."""

    receipt = _validated_repo_state_receipt(Path(repo_root).resolve(), governed_receipt)
    return {
        "repo_root_digest": str(receipt["repo_root_digest"]),
        "head_sha": str(receipt["head_sha"]),
        "dirty_paths": tuple(str(value) for value in receipt["dirty_paths"]),
        "dirty_digest": str(receipt["dirty_digest"]),
        "worktree_digest": str(receipt["worktree_digest"]),
        "governed_git_readiness": dict(receipt["governed_git_readiness"]),
    }


def _validated_repo_state_receipt(
    root: Path,
    value: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("governed_repo_state_receipt_missing")
    _require_exact_mapping(
        value,
        {
            "schema_version", "repo_root_digest", "head_sha", "dirty_paths",
            "dirty_digest", "worktree_digest", "governed_git_readiness",
            "content_digest",
        },
        "governed_repo_state_receipt_schema_invalid",
    )
    body = {str(key): value[key] for key in value if key != "content_digest"}
    if value.get("schema_version") != REPO_STATE_RECEIPT_SCHEMA:
        raise ValueError("governed_repo_state_receipt_schema_invalid")
    if value.get("content_digest") != _digest(body):
        raise ValueError("governed_repo_state_receipt_digest_invalid")
    if value.get("repo_root_digest") != _digest({"repo_root": str(root)}):
        raise ValueError("governed_repo_state_receipt_root_invalid")
    _validate_repo_state_fields(value)
    _validate_governed_git_readiness(value.get("governed_git_readiness"))
    return value


def _validate_repo_state_fields(value: Mapping[str, Any]) -> None:
    if not _is_string_match(value.get("head_sha"), r"[a-f0-9]{40}|[a-f0-9]{64}"):
        raise ValueError("governed_repo_state_head_invalid")
    dirty_paths = value.get("dirty_paths")
    if not isinstance(dirty_paths, list) or len(dirty_paths) > 5000:
        raise ValueError("governed_repo_state_paths_invalid")
    for item in dirty_paths:
        if not isinstance(item, str) or not 0 < len(item) <= 4096:
            raise ValueError("governed_repo_state_paths_invalid")
        parts = item.split("/")
        if Path(item).is_absolute() or ".." in parts or re.search(r"[\\\0\r\n]", item):
            raise ValueError("governed_repo_state_paths_invalid")
    if dirty_paths != sorted(set(dirty_paths)):
        raise ValueError("governed_repo_state_paths_invalid")
    for key in ("dirty_digest", "worktree_digest"):
        if not _is_prefixed_digest(value.get(key)):
            raise ValueError("governed_repo_state_digest_invalid")


def _validate_governed_git_readiness(value: Any) -> None:
    keys = {
        "schema_version", "ready", "canonical_root_validated",
        "git_metadata_validated", "ownership_mismatch_observed",
        "safe_directory_override_applied", "safe_directory_scope",
        "safe_directory_wildcard", "config_write_performed",
        "git_executable_binding", "reason",
    }
    _require_exact_mapping(value, keys, "governed_git_readiness_invalid")
    if value.get("schema_version") != GIT_READINESS_SCHEMA or value.get("ready") is not True:
        raise ValueError("governed_git_readiness_invalid")
    bool_keys = keys - {"schema_version", "safe_directory_scope", "reason",
                        "git_executable_binding"}
    if any(type(value.get(key)) is not bool for key in bool_keys):
        raise ValueError("governed_git_readiness_invalid")
    override = value.get("safe_directory_override_applied")
    if value.get("canonical_root_validated") is not True or value.get("git_metadata_validated") is not True:
        raise ValueError("governed_git_readiness_invalid")
    if value.get("safe_directory_wildcard") or value.get("config_write_performed"):
        raise ValueError("governed_git_readiness_invalid")
    if override is not value.get("ownership_mismatch_observed"):
        raise ValueError("governed_git_readiness_invalid")
    if value.get("safe_directory_scope") != ("command" if override else "none"):
        raise ValueError("governed_git_readiness_invalid")
    if value.get("reason") != ("ownership_override_required" if override else "ready"):
        raise ValueError("governed_git_readiness_invalid")
    binding = value.get("git_executable_binding")
    _validate_executable_binding(binding)


def _validate_executable_binding(binding: Mapping[str, Any]) -> None:
    keys = {"schema_version", "canonical_path_digest", "sha256", "size",
            "start_identity", "final_identity", "signature"}
    _require_exact_mapping(binding, keys, "governed_git_executable_binding_invalid")
    if binding.get("schema_version") != GIT_EXECUTABLE_SCHEMA:
        raise ValueError("governed_git_executable_binding_invalid")
    if not _is_prefixed_digest(binding.get("canonical_path_digest")):
        raise ValueError("governed_git_executable_binding_invalid")
    if not _is_raw_digest(binding.get("sha256")):
        raise ValueError("governed_git_executable_binding_invalid")
    if not _is_bounded_int(binding.get("size"), 1, MAX_EXECUTABLE_BYTES):
        raise ValueError("governed_git_executable_binding_invalid")
    _validate_identity(binding.get("start_identity"))
    _validate_identity(binding.get("final_identity"))
    if binding.get("start_identity") != binding.get("final_identity"):
        raise ValueError("governed_git_executable_binding_invalid")
    _validate_executable_signature(binding.get("signature"))


def _validate_identity(value: Any) -> None:
    keys = {"portable", "native", "nlink"}
    _require_exact_mapping(value, keys, "governed_git_executable_binding_invalid")
    if not _is_prefixed_digest(value.get("portable")):
        raise ValueError("governed_git_executable_binding_invalid")
    native_keys = {"dev", "ino", "mode", "nlink", "birthtime_ns", "ctime_ns", "mtime_ns"}
    native = _require_exact_mapping(
        value.get("native"), native_keys, "governed_git_executable_binding_invalid"
    )
    if not _is_bounded_int(value.get("nlink"), 1, MAX_LINK_COUNT):
        raise ValueError("governed_git_executable_binding_invalid")
    if not _is_bounded_int(native.get("nlink"), 1, MAX_LINK_COUNT):
        raise ValueError("governed_git_executable_binding_invalid")
    if value.get("nlink") != native.get("nlink"):
        raise ValueError("governed_git_executable_binding_invalid")
    for key in native_keys - {"nlink"}:
        if not _is_string_match(native.get(key), r"0|[1-9][0-9]{0,31}"):
            raise ValueError("governed_git_executable_binding_invalid")


def _validate_executable_signature(value: Any) -> None:
    if _platform_name() != "nt":
        _require_exact_mapping(
            value, {"status"}, "governed_git_executable_binding_invalid"
        )
        if value.get("status") != "not_applicable":
            raise ValueError("governed_git_executable_binding_invalid")
        return
    keys = {"status", "subject_digest", "thumbprint_digest", "verifier"}
    _require_exact_mapping(value, keys, "governed_git_executable_binding_invalid")
    if value.get("status") != "valid":
        raise ValueError("governed_git_executable_binding_invalid")
    if not _is_prefixed_digest(value.get("subject_digest")):
        raise ValueError("governed_git_executable_binding_invalid")
    if not _is_prefixed_digest(value.get("thumbprint_digest")):
        raise ValueError("governed_git_executable_binding_invalid")
    _validate_signature_verifier(value.get("verifier"))


def _validate_signature_verifier(value: Any) -> None:
    keys = {"canonical_path_digest", "sha256", "size", "start_identity",
            "final_identity", "system_root_digest", "fixed_relative_path_digest",
            "system_root_containment_proof"}
    _require_exact_mapping(value, keys, "governed_git_executable_binding_invalid")
    for key in ("canonical_path_digest", "system_root_digest",
                "fixed_relative_path_digest", "system_root_containment_proof"):
        if not _is_prefixed_digest(value.get(key)):
            raise ValueError("governed_git_executable_binding_invalid")
    if not _is_raw_digest(value.get("sha256")):
        raise ValueError("governed_git_executable_binding_invalid")
    if not _is_bounded_int(value.get("size"), 1, MAX_EXECUTABLE_BYTES):
        raise ValueError("governed_git_executable_binding_invalid")
    _validate_identity(value.get("start_identity"))
    _validate_identity(value.get("final_identity"))
    if value.get("start_identity") != value.get("final_identity"):
        raise ValueError("governed_git_executable_binding_invalid")
    if value.get("fixed_relative_path_digest") != WINDOWS_VERIFIER_RELATIVE_DIGEST:
        raise ValueError("governed_git_executable_binding_invalid")
    parts = (value["system_root_digest"], value["canonical_path_digest"],
             value["fixed_relative_path_digest"])
    if value.get("system_root_containment_proof") != _raw_digest("\0".join(parts)):
        raise ValueError("governed_git_executable_binding_invalid")


def _require_exact_mapping(value: Any, keys: set[str], reason: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(reason)
    return value


def _is_string_match(value: Any, pattern: str) -> bool:
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def _is_prefixed_digest(value: Any) -> bool:
    return _is_string_match(value, r"sha256:[a-f0-9]{64}")


def _is_raw_digest(value: Any) -> bool:
    return _is_string_match(value, r"[a-f0-9]{64}")


def _is_bounded_int(value: Any, minimum: int, maximum: int) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _raw_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _platform_name() -> str:
    return os.name


def load_authoritative_work_state(path: Path | str) -> dict[str, Any]:
    """Load an already-materialized authoritative work-state snapshot."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_existing_holoindex_receipt(path: Path | str) -> HoloIndexFreshnessReceipt:
    """Load a HoloIndex freshness receipt; this never writes or refreshes the index."""

    return load_freshness_receipt(path)


def build_operational_context_snapshot(
    *,
    repo_state: Mapping[str, Any],
    work_state_snapshot: Mapping[str, Any],
    holoindex_receipt: HoloIndexFreshnessReceipt | Mapping[str, Any] | None,
    changed_paths: Sequence[str],
    now_iso: str | None = None,
    ttl_seconds: int = 600,
    breadcrumbs: Sequence[Mapping[str, Any]] = (),
    breadcrumb_scope: str | None = None,
    brain_state: Mapping[str, Any] | None = None,
    workspace_memory_notes: Sequence[Mapping[str, Any]] = (),
    bootstrap_projection: Mapping[str, Any] | None = None,
    required_sources: Sequence[str] = (SOURCE_REPO, SOURCE_WORK_STATE, SOURCE_HOLOINDEX),
    context_view_max_chars: int = 12000,
) -> SnapshotBuildResult:
    """Build an operational snapshot and its exact model-visible view."""

    observed_at = now_iso or utc_now_iso()
    valid_until = (datetime.fromisoformat(observed_at) + timedelta(seconds=ttl_seconds)).isoformat()
    required = set(required_sources)
    repo_clean = _normalize_repo_state(repo_state)
    work_clean = _normalize_work_state(work_state_snapshot)
    scoped_breadcrumbs = tuple(_filter_breadcrumbs(breadcrumbs, breadcrumb_scope))
    brain_clean = _normalize_brain_state(brain_state)
    workspace_clean = _normalize_workspace_memory(workspace_memory_notes)
    holo_state = _normalize_holoindex_state(
        holoindex_receipt,
        repo_head_sha=str(repo_clean.get("head_sha", "unknown")),
        changed_paths=changed_paths,
    )

    receipts = (
        _source_receipt(
            source=SOURCE_REPO,
            authority_class=AUTHORITY_AUTHORITATIVE,
            required=SOURCE_REPO in required,
            observed_at=observed_at,
            source_version=str(repo_clean.get("head_sha", "unknown")),
            payload=repo_clean,
            freshness=FRESH if repo_clean.get("head_sha") and repo_clean.get("head_sha") != "unknown" else UNKNOWN,
        ),
        _source_receipt(
            source=SOURCE_WORK_STATE,
            authority_class=AUTHORITY_AUTHORITATIVE,
            required=SOURCE_WORK_STATE in required,
            observed_at=observed_at,
            source_version=str(work_clean.get("revision", "")),
            payload=work_clean,
            freshness=FRESH if work_clean.get("revision") else MISSING,
            rejection_reasons=() if work_clean.get("revision") else ("missing_work_state_revision",),
            record_count=len(work_clean.get("worker_claims", ())) + len(work_clean.get("wre_queue_items", ())),
        ),
        _source_receipt(
            source=SOURCE_HOLOINDEX,
            authority_class=AUTHORITY_VERIFIED,
            required=SOURCE_HOLOINDEX in required,
            observed_at=observed_at,
            source_version=str(holo_state.get("repo_head_sha", "")),
            payload=holo_state,
            freshness=FRESH if holo_state.get("freshness_ok") else (MISSING if holoindex_receipt is None else STALE),
            rejection_reasons=tuple(holo_state.get("rejection_reasons", ())),
            record_count=int(holo_state.get("required_collection_count", 0)),
        ),
        _source_receipt(
            source=SOURCE_BREADCRUMBS,
            authority_class=AUTHORITY_OBSERVATIONAL,
            required=SOURCE_BREADCRUMBS in required,
            observed_at=observed_at,
            source_version=str(breadcrumb_scope or "unscoped"),
            payload=scoped_breadcrumbs,
            freshness=FRESH if scoped_breadcrumbs or SOURCE_BREADCRUMBS not in required else MISSING,
            record_count=len(scoped_breadcrumbs),
        ),
        _source_receipt(
            source=SOURCE_BRAIN,
            authority_class=AUTHORITY_HISTORICAL,
            required=SOURCE_BRAIN in required,
            observed_at=observed_at,
            source_version=str(brain_clean.get("signature_digest", "")),
            payload=brain_clean,
            freshness=FRESH if brain_clean.get("available") else MISSING,
            rejection_reasons=() if brain_clean.get("available") or SOURCE_BRAIN not in required else ("missing_brain_artifacts",),
        ),
        _source_receipt(
            source=SOURCE_WORKSPACE_MEMORY,
            authority_class=AUTHORITY_HISTORICAL,
            required=SOURCE_WORKSPACE_MEMORY in required,
            observed_at=observed_at,
            source_version=str(workspace_clean.get("memory_digest", "")),
            payload=workspace_clean,
            freshness=FRESH if workspace_clean.get("record_count", 0) else UNKNOWN,
            record_count=int(workspace_clean.get("record_count", 0)),
        ),
    )

    conflicts = tuple(_derive_conflicts(repo_clean, work_clean, brain_clean, bootstrap_projection))
    rejection_reasons = tuple(_mandatory_source_rejections(receipts))
    content = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "policy_version": CONTEXT_POLICY_VERSION,
        "repo_state": repo_clean,
        "work_state": work_clean,
        "holoindex_state": holo_state,
        "breadcrumbs_state": _breadcrumb_state(scoped_breadcrumbs, breadcrumb_scope),
        "brain_state": brain_clean,
        "workspace_memory_state": workspace_clean,
        "source_receipts": [receipt.to_dict() for receipt in receipts],
        "conflicts": conflicts,
        "rejection_reasons": rejection_reasons,
    }
    content_digest = _digest(content)
    receipt_id = _digest(
        {
            "snapshot_content_digest": content_digest,
            "created_at": observed_at,
            "valid_until": valid_until,
            "source_receipt_ids": [receipt.content_digest for receipt in receipts],
        }
    )

    if rejection_reasons:
        return SnapshotBuildResult(
            accepted=False,
            status=SNAPSHOT_REJECTED,
            snapshot=None,
            context_view=None,
            source_receipts=receipts,
            rejection_reasons=rejection_reasons,
            conflicts=conflicts,
        )

    snapshot = OperationalContextSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        policy_version=CONTEXT_POLICY_VERSION,
        snapshot_receipt_id=receipt_id,
        snapshot_content_digest=content_digest,
        created_at=observed_at,
        valid_until=valid_until,
        repo_state=repo_clean,
        work_state=work_clean,
        holoindex_state=holo_state,
        breadcrumbs_state=_breadcrumb_state(scoped_breadcrumbs, breadcrumb_scope),
        brain_state=brain_clean,
        workspace_memory_state=workspace_clean,
        source_receipts=receipts,
        conflicts=conflicts,
        rejection_reasons=rejection_reasons,
    )
    context_view = build_context_view(snapshot, max_chars=context_view_max_chars)
    return SnapshotBuildResult(
        accepted=True,
        status=SNAPSHOT_ACCEPTED,
        snapshot=snapshot,
        context_view=context_view,
        source_receipts=receipts,
        rejection_reasons=(),
        conflicts=conflicts,
    )


def build_context_view(snapshot: OperationalContextSnapshot, *, max_chars: int = 12000) -> ContextView:
    """Build the exact sanitized model-visible context view for a snapshot."""

    lines = [
        "REDDOG_OPERATIONAL_CONTEXT_VIEW",
        f"schema_version: {snapshot.schema_version}",
        f"policy_version: {snapshot.policy_version}",
        f"snapshot_receipt_id: {snapshot.snapshot_receipt_id}",
        f"snapshot_content_digest: {snapshot.snapshot_content_digest}",
        f"repo_head_sha: {snapshot.repo_state.get('head_sha', 'unknown')}",
        f"work_state_revision: {snapshot.work_state.get('revision', '')}",
        f"holoindex_freshness: {snapshot.holoindex_state.get('freshness_ok', False)}",
        f"breadcrumb_scope: {snapshot.breadcrumbs_state.get('scope', 'none')}",
        f"brain_available: {snapshot.brain_state.get('available', False)}",
        f"conflicts: {','.join(snapshot.conflicts) if snapshot.conflicts else '(none)'}",
        "source_receipts:",
    ]
    for receipt in snapshot.source_receipts:
        lines.append(
            "- "
            + json.dumps(
                {
                    "source": receipt.source,
                    "authority_class": receipt.authority_class,
                    "required": receipt.required,
                    "freshness": receipt.freshness,
                    "content_digest": receipt.content_digest,
                    "rejection_reasons": receipt.rejection_reasons,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    text = _sanitize_context_text("\n".join(lines))
    if len(text) > max_chars:
        text = text[:max_chars] + "\n[TRUNCATED_CONTEXT_VIEW]"
    view_id = _digest(
        {
            "snapshot_receipt_id": snapshot.snapshot_receipt_id,
            "snapshot_content_digest": snapshot.snapshot_content_digest,
            "policy_version": snapshot.policy_version,
            "text": text,
        }
    )
    return ContextView(
        context_view_id=view_id,
        snapshot_receipt_id=snapshot.snapshot_receipt_id,
        snapshot_content_digest=snapshot.snapshot_content_digest,
        policy_version=snapshot.policy_version,
        text=text,
        included_sources=tuple(receipt.source for receipt in snapshot.source_receipts),
        omitted_sources=("raw_brain", "raw_breadcrumbs", "raw_workspace_memory"),
        redaction_reasons=("no_raw_historical_memory", "absolute_paths", "secret_like_values"),
    )


def build_evidence_bundle(
    *,
    snapshot: OperationalContextSnapshot,
    context_view: ContextView,
    report_digests: Sequence[str],
    external_research_receipts: Sequence[str] = (),
) -> EvidenceBundle:
    """Bind reports/research to a snapshot without changing the snapshot."""

    bundle_id = _digest(
        {
            "snapshot_receipt_id": snapshot.snapshot_receipt_id,
            "context_view_id": context_view.context_view_id,
            "report_digests": sorted(report_digests),
            "external_research_receipts": sorted(external_research_receipts),
        }
    )
    return EvidenceBundle(
        evidence_bundle_id=bundle_id,
        snapshot_receipt_id=snapshot.snapshot_receipt_id,
        context_view_id=context_view.context_view_id,
        report_digests=tuple(sorted(report_digests)),
        external_research_receipts=tuple(sorted(external_research_receipts)),
    )


def validate_context_before_assignment(
    *,
    snapshot: OperationalContextSnapshot,
    context_view: ContextView,
    current_repo_head_sha: str,
    current_work_state_revision: str,
    current_breadcrumb_high_watermark: str | None = None,
    evidence_bundle: EvidenceBundle | None = None,
    now_iso: str | None = None,
) -> AssignmentContextCheck:
    """Fail closed when the assignment-time world no longer matches the snapshot."""

    reasons: list[str] = []
    now = datetime.fromisoformat(now_iso or utc_now_iso())
    if now > datetime.fromisoformat(snapshot.valid_until):
        reasons.append("snapshot_expired")
    if context_view.snapshot_receipt_id != snapshot.snapshot_receipt_id:
        reasons.append("context_view_snapshot_mismatch")
    if context_view.snapshot_content_digest != snapshot.snapshot_content_digest:
        reasons.append("context_view_content_mismatch")
    if current_repo_head_sha != snapshot.repo_state.get("head_sha"):
        reasons.append("repo_head_changed")
    if current_work_state_revision != snapshot.work_state.get("revision"):
        reasons.append("work_state_revision_changed")
    expected_high_watermark = snapshot.breadcrumbs_state.get("high_watermark")
    if current_breadcrumb_high_watermark and expected_high_watermark:
        if current_breadcrumb_high_watermark != expected_high_watermark:
            reasons.append("breadcrumb_high_watermark_changed")
    if evidence_bundle and evidence_bundle.context_view_id != context_view.context_view_id:
        reasons.append("evidence_bundle_context_view_mismatch")

    return AssignmentContextCheck(
        accepted=not reasons,
        status=ASSIGNMENT_CONTEXT_VALID if not reasons else ASSIGNMENT_CONTEXT_STALE,
        snapshot_receipt_id=snapshot.snapshot_receipt_id,
        context_view_id=context_view.context_view_id,
        evidence_bundle_id=evidence_bundle.evidence_bundle_id if evidence_bundle else None,
        rejection_reasons=tuple(reasons),
    )


def _normalize_repo_state(repo_state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "head_sha": str(repo_state.get("head_sha", "unknown")),
        "dirty_paths": tuple(sorted(str(path).replace("\\", "/") for path in repo_state.get("dirty_paths", ()))),
        "dirty_digest": str(repo_state.get("dirty_digest", _digest(tuple(repo_state.get("dirty_paths", ()))))),
        "worktree_digest": str(repo_state.get("worktree_digest", "")),
    }


def _normalize_work_state(work_state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": str(work_state.get("schema_version", "")),
        "revision": str(work_state.get("revision", "")),
        "selected_slice": str(work_state.get("selected_slice", "")),
        "worker_claims": tuple(_stable_mapping(entry) for entry in work_state.get("worker_claims", ())),
        "wre_queue_items": tuple(_stable_mapping(entry) for entry in work_state.get("wre_queue_items", ())),
        "refresh_receipt_id": str(work_state.get("refresh_receipt_id", "")),
    }


def _normalize_holoindex_state(
    receipt: HoloIndexFreshnessReceipt | Mapping[str, Any] | None,
    *,
    repo_head_sha: str,
    changed_paths: Sequence[str],
) -> dict[str, Any]:
    check: FreshnessCheck = evaluate_freshness_for_paths(
        receipt,
        changed_paths,
        expected_repo_head_sha=repo_head_sha if repo_head_sha != "unknown" else None,
    )
    receipt_digest = _digest(receipt.to_dict() if hasattr(receipt, "to_dict") else receipt or {})
    receipt_head = ""
    generation_id = ""
    if isinstance(receipt, HoloIndexFreshnessReceipt):
        receipt_head = receipt.repo_head_sha
        generation_id = receipt.generation_id
    elif isinstance(receipt, Mapping):
        receipt_head = str(receipt.get("repo_head_sha", ""))
        generation_id = str(receipt.get("generation_id", ""))
    return {
        "receipt_digest": receipt_digest,
        "generation_id": generation_id,
        "repo_head_sha": receipt_head,
        "freshness_ok": check.ok,
        "required_collections": tuple(check.required_collections),
        "required_collection_count": len(check.required_collections),
        "stale_collections": tuple(check.stale_collections),
        "rejection_reasons": tuple(check.reasons),
        "changed_paths": tuple(sorted(path.replace("\\", "/") for path in changed_paths)),
    }


def _normalize_brain_state(brain_state: Mapping[str, Any] | None) -> dict[str, Any]:
    if not brain_state:
        return {"available": False, "signature_digest": "", "summary_digest": "", "record_count": 0}
    sanitized = {
        "available": bool(brain_state.get("available", True)),
        "signature_digest": str(brain_state.get("signature_digest", brain_state.get("signature", ""))),
        "summary_digest": str(brain_state.get("summary_digest", _digest(brain_state.get("summary", "")))),
        "record_count": int(brain_state.get("record_count", brain_state.get("conversation_count", 0) or 0)),
        "reported_repo_head_sha": str(brain_state.get("repo_head_sha", "")),
        "reported_work_state_revision": str(brain_state.get("work_state_revision", "")),
    }
    return sanitized


def _normalize_workspace_memory(notes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    metadata = []
    for entry in notes:
        metadata.append(
            {
                "note_id": str(entry.get("note_id", entry.get("id", ""))),
                "topic": _safe_short_text(str(entry.get("topic", ""))),
                "digest": _digest(entry),
            }
        )
    return {
        "record_count": len(metadata),
        "memory_digest": _digest(metadata),
        "records": tuple(metadata),
    }


def _filter_breadcrumbs(
    breadcrumbs: Sequence[Mapping[str, Any]],
    scope: str | None,
) -> Iterable[dict[str, Any]]:
    for entry in breadcrumbs:
        continuity = str(entry.get("continuity_id", entry.get("root_continuity_id", "")))
        task_id = str(entry.get("task_id", ""))
        if scope and scope not in {continuity, task_id}:
            continue
        yield {
            "breadcrumb_id": str(entry.get("breadcrumb_id", entry.get("id", ""))),
            "continuity_id": continuity,
            "task_id": task_id,
            "observed_at": str(entry.get("timestamp", entry.get("created_at", ""))),
            "digest": _digest(entry),
        }


def _breadcrumb_state(records: Sequence[Mapping[str, Any]], scope: str | None) -> dict[str, Any]:
    high_watermark = ""
    if records:
        high_watermark = _digest(tuple(record.get("digest", "") for record in records))
    return {
        "scope": scope or "none",
        "record_count": len(records),
        "high_watermark": high_watermark,
        "records": tuple(_stable_mapping(record) for record in records),
    }


def _derive_conflicts(
    repo_state: Mapping[str, Any],
    work_state: Mapping[str, Any],
    brain_state: Mapping[str, Any],
    bootstrap_projection: Mapping[str, Any] | None,
) -> Iterable[str]:
    if bootstrap_projection:
        bootstrap_head = str(bootstrap_projection.get("repo_head_sha", ""))
        if bootstrap_head and bootstrap_head != repo_state.get("head_sha"):
            yield "bootstrap_head_stale"
        bootstrap_revision = str(bootstrap_projection.get("work_state_revision", ""))
        if bootstrap_revision and bootstrap_revision != work_state.get("revision"):
            yield "bootstrap_work_state_stale"
    brain_head = str(brain_state.get("reported_repo_head_sha", ""))
    if brain_head and brain_head != repo_state.get("head_sha"):
        yield "brain_head_historical_conflict"
    brain_revision = str(brain_state.get("reported_work_state_revision", ""))
    if brain_revision and brain_revision != work_state.get("revision"):
        yield "brain_work_state_historical_conflict"


def _mandatory_source_rejections(receipts: Sequence[SourceReceipt]) -> Iterable[str]:
    for receipt in receipts:
        if not receipt.required:
            continue
        if receipt.freshness in {MISSING, STALE, UNKNOWN}:
            yield f"mandatory_source_not_fresh:{receipt.source}"
        for reason in receipt.rejection_reasons:
            yield f"{receipt.source}:{reason}"


def _source_receipt(
    *,
    source: str,
    authority_class: str,
    required: bool,
    observed_at: str,
    source_version: str,
    payload: Any,
    freshness: str,
    rejection_reasons: Sequence[str] = (),
    record_count: int = 0,
) -> SourceReceipt:
    return SourceReceipt(
        source=source,
        authority_class=authority_class,
        required=required,
        observed_at=observed_at,
        source_version=source_version,
        content_digest=_digest(payload),
        freshness=freshness,
        rejection_reasons=tuple(rejection_reasons),
        record_count=record_count,
    )


def _sanitize_context_text(text: str) -> str:
    text = _ABSOLUTE_PATH_RE.sub("[ABS_PATH_REDACTED]", text)
    text = _SECRET_RE.sub("[SENSITIVE_VALUE_REDACTED]", text)
    return text


def _safe_short_text(text: str) -> str:
    return _sanitize_context_text(text.replace("\n", " ").strip())[:120]


def _stable_mapping(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): entry[key] for key in sorted(entry)}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


__all__ = [
    "ASSIGNMENT_CONTEXT_STALE",
    "ASSIGNMENT_CONTEXT_VALID",
    "AUTHORITY_AUTHORITATIVE",
    "AUTHORITY_HISTORICAL",
    "AUTHORITY_OBSERVATIONAL",
    "AUTHORITY_VERIFIED",
    "CONTEXT_POLICY_VERSION",
    "FRESH",
    "MISSING",
    "SNAPSHOT_ACCEPTED",
    "SNAPSHOT_REJECTED",
    "SNAPSHOT_SCHEMA_VERSION",
    "REPO_STATE_RECEIPT_SCHEMA",
    "STALE",
    "UNKNOWN",
    "AssignmentContextCheck",
    "ContextView",
    "EvidenceBundle",
    "OperationalContextSnapshot",
    "SnapshotBuildResult",
    "SourceReceipt",
    "build_context_view",
    "build_evidence_bundle",
    "build_operational_context_snapshot",
    "load_authoritative_work_state",
    "load_existing_holoindex_receipt",
    "observe_repo_state",
    "validate_context_before_assignment",
]
