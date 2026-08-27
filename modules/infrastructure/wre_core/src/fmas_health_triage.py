"""Deterministic FMAS health triage for bounded WRE improvement proposals.

The public entry point runs the canonical WSP 62 producer. It does not invoke a
model, persist a queue, dispatch a worker, mutate source, or promote an artifact.
It turns that producer-bound finding set into dry-run ImprovementJobs only.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .fmas_improvement_bridge import (
    FMASFinding,
    FMASFindingType,
    FMASSeverity,
    _create_job_from_fmas_finding,
    parse_fmas_string,
)
from .improvement_job_contract import ImprovementJob
from .fmas_wsp62_contract import parse_wsp62_finding_text
from .skill_path_security import absolute_unresolved, has_link_or_reparse_component
from tools.modular_audit import modular_audit as canonical_fmas


_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


class HealthFindingDisposition(str, Enum):
    """Evidence class assigned before any model or worker sees a finding."""

    CANDIDATE_CHANGE = "candidate_change"
    HEALTH_DEBT = "health_debt"
    INHERITED_DEBT = "inherited_debt"
    ADVISORY = "advisory"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class HealthAuditBinding:
    """Immutable identity emitted after local authority verification."""

    authority_repo_head_sha: str
    audit_tool_id: str
    audit_tool_digest: str
    baseline_repo_head_sha: Optional[str] = None

    def __post_init__(self) -> None:
        if not _SHA_RE.fullmatch(self.authority_repo_head_sha):
            raise ValueError("authority_repo_head_sha_invalid")
        if self.baseline_repo_head_sha is not None and not _SHA_RE.fullmatch(
            self.baseline_repo_head_sha
        ):
            raise ValueError("baseline_repo_head_sha_invalid")
        if not self.audit_tool_id.strip():
            raise ValueError("audit_tool_id_missing")
        if not _DIGEST_RE.fullmatch(self.audit_tool_digest):
            raise ValueError("audit_tool_digest_invalid")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "authority_repo_head_sha": self.authority_repo_head_sha,
            "baseline_repo_head_sha": self.baseline_repo_head_sha,
            "audit_tool_id": self.audit_tool_id,
            "audit_tool_digest": self.audit_tool_digest,
        }


@dataclass(frozen=True, slots=True)
class TriagedHealthFinding:
    finding: FMASFinding
    disposition: HealthFindingDisposition
    reason_code: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding": self.finding.to_dict(),
            "disposition": self.disposition.value,
            "reason_code": self.reason_code,
        }

    def canonical_evidence_dict(self) -> Dict[str, Any]:
        """Return stable evidence fields; parser wall-clock time is not authority."""
        finding = self.finding.to_dict()
        finding.pop("detected_at", None)
        return {
            "finding": finding,
            "disposition": self.disposition.value,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True, slots=True)
class HealthAuditTriageReceipt:
    receipt_id: str
    audit_id: str
    binding: HealthAuditBinding
    raw_finding_count: int
    unique_finding_count: int
    duplicate_finding_count: int
    disposition_counts: Mapping[str, int]
    candidate_count: int
    emitted_job_count: int
    candidate_overflow_count: int
    finding_set_digest: str
    proposed_finding_ids: Tuple[str, ...]
    proposed_job_set_digest: str
    producer_observation_count: int
    producer_observation_digest: str
    excluded_non_authoritative_observation_count: int
    exclusion_reason_counts: Mapping[str, int]
    no_model_invocation_performed: bool = True
    no_worker_dispatch_performed: bool = True
    no_queue_mutation_performed: bool = True
    no_source_mutation_performed: bool = True

    def __post_init__(self) -> None:
        """Detach nested receipt fields so the frozen boundary is deep."""
        object.__setattr__(
            self,
            "disposition_counts",
            MappingProxyType(dict(self.disposition_counts)),
        )
        object.__setattr__(
            self,
            "exclusion_reason_counts",
            MappingProxyType(dict(self.exclusion_reason_counts)),
        )
        object.__setattr__(
            self,
            "proposed_finding_ids",
            tuple(self.proposed_finding_ids),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "wre_health_audit_triage_receipt.v1",
            "receipt_id": self.receipt_id,
            "audit_id": self.audit_id,
            "binding": self.binding.to_dict(),
            "raw_finding_count": self.raw_finding_count,
            "unique_finding_count": self.unique_finding_count,
            "duplicate_finding_count": self.duplicate_finding_count,
            "disposition_counts": dict(self.disposition_counts),
            "candidate_count": self.candidate_count,
            "emitted_job_count": self.emitted_job_count,
            "candidate_overflow_count": self.candidate_overflow_count,
            "finding_set_digest": self.finding_set_digest,
            "proposed_finding_ids": list(self.proposed_finding_ids),
            "proposed_job_set_digest": self.proposed_job_set_digest,
            "producer_observation_count": self.producer_observation_count,
            "producer_observation_digest": self.producer_observation_digest,
            "excluded_non_authoritative_observation_count": (
                self.excluded_non_authoritative_observation_count
            ),
            "exclusion_reason_counts": dict(self.exclusion_reason_counts),
            "no_model_invocation_performed": self.no_model_invocation_performed,
            "no_worker_dispatch_performed": self.no_worker_dispatch_performed,
            "no_queue_mutation_performed": self.no_queue_mutation_performed,
            "no_source_mutation_performed": self.no_source_mutation_performed,
        }


@dataclass(frozen=True, slots=True)
class HealthAuditTriageResult:
    receipt: HealthAuditTriageReceipt
    findings: Tuple[TriagedHealthFinding, ...]
    jobs: Tuple[ImprovementJob, ...]
    producer_observation_count: int
    excluded_non_authoritative_observation_count: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "findings", tuple(self.findings))
        object.__setattr__(self, "jobs", tuple(self.jobs))


def _wsp62_level(raw_finding: str) -> str:
    parsed = parse_wsp62_finding_text(raw_finding)
    return parsed.level if parsed else ""


def _git_value(repo_root: Path, *args: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _bind_health_audit(
    candidate_repo_root: Path,
    baseline_repo_root: Optional[Path],
) -> HealthAuditBinding:
    """Prove clean Git identity and exact in-repository scanner bytes."""
    candidate_root = Path(candidate_repo_root).resolve()
    candidate_head = _clean_candidate_head(candidate_root)
    tool_id, tool_digest = _canonical_tool_identity(candidate_root)
    baseline_head = _authoritative_baseline_head(candidate_root, baseline_repo_root)
    return HealthAuditBinding(
        authority_repo_head_sha=candidate_head,
        baseline_repo_head_sha=baseline_head,
        audit_tool_id=tool_id,
        audit_tool_digest=tool_digest,
    )


def _clean_candidate_head(candidate_root: Path) -> str:
    """Return clean candidate HEAD or fail closed."""
    if not candidate_root.is_dir() or not (candidate_root / "modules").is_dir():
        raise ValueError("candidate_repo_root_invalid")
    candidate_head = _git_value(candidate_root, "rev-parse", "HEAD")
    candidate_status = _git_value(
        candidate_root,
        "status",
        "--porcelain",
        "--untracked-files=all",
    )
    if candidate_head is None or candidate_status is None:
        raise ValueError("candidate_git_authority_unavailable")
    if candidate_status:
        raise ValueError("candidate_repo_not_clean")
    return candidate_head


def _canonical_tool_identity(candidate_root: Path) -> tuple[str, str]:
    """Bind the imported canonical scanner to confined in-repository bytes."""
    unresolved_tool = Path(canonical_fmas.__file__)
    unresolved_tool = absolute_unresolved(unresolved_tool)
    try:
        unresolved_tool.relative_to(candidate_root)
    except ValueError as exc:
        raise ValueError("audit_tool_outside_candidate_repo") from exc
    if has_link_or_reparse_component(candidate_root, unresolved_tool):
        raise ValueError("audit_tool_link_or_reparse_rejected")
    tool = unresolved_tool.resolve()
    try:
        relative_tool = tool.relative_to(candidate_root)
    except ValueError as exc:
        raise ValueError("audit_tool_outside_candidate_repo") from exc
    if not tool.is_file():
        raise ValueError("audit_tool_not_regular_file")
    tool_id = f"{relative_tool.as_posix()}:audit_file_sizes"
    tool_digest = f"sha256:{hashlib.sha256(tool.read_bytes()).hexdigest()}"
    return tool_id, tool_digest


def _authoritative_baseline_head(
    candidate_root: Path,
    baseline_repo_root: Optional[Path],
) -> Optional[str]:
    """Return the validated exact-base HEAD when Mode 2 is requested."""
    if baseline_repo_root is None:
        return None
    baseline_root = Path(baseline_repo_root).resolve()
    accepted, reason = canonical_fmas.validate_authoritative_baseline(
        candidate_root,
        baseline_root,
    )
    if not accepted:
        raise ValueError(f"baseline_authority_rejected:{reason}")
    baseline_head = _git_value(baseline_root, "rev-parse", "HEAD")
    if baseline_head is None:
        raise ValueError("baseline_git_authority_unavailable")
    return baseline_head


def _exact_head_tracked_paths(repo_root: Path) -> frozenset[str]:
    raw = _git_value(
        repo_root,
        "ls-tree",
        "-r",
        "--name-only",
        "-z",
        "HEAD",
        "--",
        "modules",
    )
    if raw is None:
        raise ValueError("candidate_tracked_inventory_unavailable")
    paths = [item for item in raw.split("\x00") if item]
    if len(paths) != len(set(paths)):
        raise ValueError("candidate_tracked_inventory_duplicate")
    return frozenset(paths)


def _finding_scope_is_confined(
    finding: FMASFinding,
    repo_root: Path,
    tracked_paths: frozenset[str],
) -> bool:
    if not finding.file_path or not finding.module_path:
        return False
    if finding.file_path not in tracked_paths:
        return False
    candidate = repo_root / finding.file_path
    if has_link_or_reparse_component(repo_root, candidate):
        return False
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(repo_root)
    except (OSError, ValueError):
        return False
    if not resolved.is_file():
        return False
    return True


def _classify(
    finding: FMASFinding,
    *,
    baseline_attributed: bool,
    repo_root: Path,
    tracked_paths: frozenset[str],
) -> tuple[HealthFindingDisposition, str]:
    level = _wsp62_level(finding.raw_finding)
    if level:
        if not _finding_scope_is_confined(finding, repo_root, tracked_paths):
            return HealthFindingDisposition.BLOCKED, "wsp62_scope_invalid_or_missing"
        if level == "ERROR" and baseline_attributed:
            return HealthFindingDisposition.CANDIDATE_CHANGE, "wsp62_baseline_error"
        if level in {"INHERITED", "INHERITED_METADATA"}:
            return HealthFindingDisposition.INHERITED_DEBT, f"wsp62_{level.lower()}"
        if level in {"CRITICAL", "ERROR"}:
            return HealthFindingDisposition.HEALTH_DEBT, "wsp62_unattributed_debt"
        if level in {
            "WARNING",
            "APPROACHING",
            "WATCH",
            "ADVISORY_ARCHIVE",
            "EXEMPTION_EXPIRED",
        }:
            return HealthFindingDisposition.ADVISORY, f"wsp62_{level.lower()}"
        return HealthFindingDisposition.BLOCKED, "wsp62_level_unknown"

    if finding.finding_type == FMASFindingType.UNKNOWN:
        return HealthFindingDisposition.BLOCKED, "finding_type_unknown"
    if finding.severity in {
        FMASSeverity.CRITICAL,
        FMASSeverity.HIGH,
        FMASSeverity.MEDIUM,
    }:
        return HealthFindingDisposition.HEALTH_DEBT, "non_wsp62_health_debt"
    return HealthFindingDisposition.ADVISORY, "non_wsp62_advisory"


def _authoritative_wsp62_findings(
    raw_findings: Sequence[str],
    tracked_paths: frozenset[str],
) -> tuple[List[str], Dict[str, int]]:
    """Keep only canonical producer rows scoped to exact-HEAD tracked files."""
    authoritative: List[str] = []
    reasons = {
        "non_string": 0,
        "non_wsp62_or_unparseable": 0,
        "not_exact_head_tracked": 0,
    }
    for raw in raw_findings:
        if not isinstance(raw, str):
            reasons["non_string"] += 1
            continue
        parsed = parse_fmas_string(raw)
        if parsed is None or not _wsp62_level(parsed.raw_finding):
            reasons["non_wsp62_or_unparseable"] += 1
            continue
        if parsed.file_path not in tracked_paths:
            reasons["not_exact_head_tracked"] += 1
            continue
        authoritative.append(raw)
    return authoritative, reasons


def _validate_triage_inputs(
    raw_findings: Sequence[str],
    candidate_repo_root: Path,
    tracked_paths: frozenset[str],
    candidate_job_limit: int,
) -> Path:
    if not 0 <= candidate_job_limit <= 100:
        raise ValueError("candidate_job_limit_out_of_range")
    if isinstance(raw_findings, (str, bytes)):
        raise TypeError("raw_findings_must_be_sequence")
    for raw in raw_findings:
        if not isinstance(raw, str):
            raise TypeError("raw_finding_must_be_string")
        if not raw.strip():
            raise ValueError("raw_finding_empty")
    if not isinstance(tracked_paths, frozenset):
        raise TypeError("tracked_paths_must_be_frozenset")
    return Path(candidate_repo_root).resolve()


def _unique_parsed_findings(raw_findings: Sequence[str]) -> List[FMASFinding]:
    """Parse and deterministically deduplicate authoritative finding strings."""
    unique: Dict[str, FMASFinding] = {}
    for raw in raw_findings:
        parsed = parse_fmas_string(raw)
        if parsed is None:  # pragma: no cover - non-empty strings parse UNKNOWN
            raise ValueError("raw_finding_unparseable")
        evidence_id = _finding_evidence_id(parsed)
        if evidence_id in unique:
            continue
        unique[evidence_id] = parsed
    return [unique[key] for key in sorted(unique)]


def _finding_evidence_id(finding: FMASFinding) -> str:
    """Return collision-resistant identity for one normalized observation."""
    evidence = finding.to_dict()
    evidence.pop("detected_at", None)
    return _canonical_digest(evidence)


def _triage_findings(
    findings: Sequence[FMASFinding],
    *,
    baseline_attributed: bool,
    candidate_root: Path,
    tracked_paths: frozenset[str],
) -> List[TriagedHealthFinding]:
    """Apply deterministic disposition rules to parsed findings."""
    triaged: List[TriagedHealthFinding] = []
    for finding in findings:
        disposition, reason = _classify(
            finding,
            baseline_attributed=baseline_attributed,
            repo_root=candidate_root,
            tracked_paths=tracked_paths,
        )
        triaged.append(TriagedHealthFinding(finding, disposition, reason))
    return triaged


def _build_candidate_jobs(
    selected: Sequence[TriagedHealthFinding],
    *,
    binding: HealthAuditBinding,
    audit_id: str,
    requested_by: str,
) -> List[ImprovementJob]:
    """Build deterministic dry-run jobs for admitted candidate changes only."""
    jobs: List[ImprovementJob] = []
    for item in selected:
        idempotency_key = (
            f"{binding.authority_repo_head_sha}:"
            f"{binding.baseline_repo_head_sha}:{_finding_evidence_id(item.finding)}"
        )
        job = _create_job_from_fmas_finding(
            item.finding,
            idempotency_key=idempotency_key,
            requested_by=requested_by,
        )
        job.evidence_refs.extend(
            [
                f"HEALTH_AUDIT:{audit_id}",
                f"AUDIT_TOOL:{binding.audit_tool_digest}",
                f"BASELINE:{binding.baseline_repo_head_sha}",
            ]
        )
        job.payload["health_triage"] = {
            "audit_id": audit_id,
            "disposition": item.disposition.value,
            "reason_code": item.reason_code,
        }
        jobs.append(job)
    return jobs


def _count_dispositions(
    triaged: Sequence[TriagedHealthFinding],
) -> Dict[str, int]:
    disposition_counts = {item.value: 0 for item in HealthFindingDisposition}
    for item in triaged:
        disposition_counts[item.disposition.value] += 1
    return disposition_counts


def _canonical_job_evidence_dict(job: ImprovementJob) -> Dict[str, Any]:
    """Project stable proposal fields for receipt binding."""
    value = deepcopy(job.to_dict())
    for field in (
        "created_at",
        "approved_at",
        "completed_at",
        "assigned_worker",
        "validation_refs",
        "_transition_history",
    ):
        value.pop(field, None)
    finding_payload = value.get("payload", {}).get("fmas_finding", {})
    if isinstance(finding_payload, dict):
        finding_payload.pop("detected_at", None)
    return value


def _receipt_payload(
    *,
    audit_id: str,
    binding: HealthAuditBinding,
    fields: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "schema_version": "wre_health_audit_triage_receipt.v1",
        "audit_id": audit_id,
        "binding": binding.to_dict(),
        **fields,
        "no_model_invocation_performed": True,
        "no_worker_dispatch_performed": True,
        "no_queue_mutation_performed": True,
        "no_source_mutation_performed": True,
    }


def _new_triage_receipt(
    *,
    audit_id: str,
    binding: HealthAuditBinding,
    fields: Dict[str, Any],
) -> HealthAuditTriageReceipt:
    payload = _receipt_payload(audit_id=audit_id, binding=binding, fields=fields)
    receipt = HealthAuditTriageReceipt(
        receipt_id=_canonical_digest(payload),
        audit_id=audit_id,
        binding=binding,
        **fields,
    )
    return receipt


def _normalize_producer_evidence(
    raw_findings: Sequence[str],
    producer_observation_count: Optional[int],
    producer_observation_digest: Optional[str],
    excluded_count: int,
    exclusion_reason_counts: Optional[Dict[str, int]],
) -> tuple[int, str, Dict[str, int]]:
    producer_count = (
        len(raw_findings)
        if producer_observation_count is None
        else producer_observation_count
    )
    producer_digest = producer_observation_digest or _canonical_digest(list(raw_findings))
    reason_counts = dict(exclusion_reason_counts or {})
    if sum(reason_counts.values()) != excluded_count:
        raise ValueError("health_audit_exclusion_count_mismatch")
    if producer_count != len(raw_findings) + excluded_count:
        raise ValueError("health_audit_producer_count_mismatch")
    if not _DIGEST_RE.fullmatch(producer_digest):
        raise ValueError("health_audit_producer_digest_invalid")
    return producer_count, producer_digest, reason_counts


def _health_audit_id(
    binding: HealthAuditBinding,
    producer_count: int,
    producer_digest: str,
    reason_counts: Dict[str, int],
    finding_digest: str,
) -> str:
    return _canonical_digest({
        "binding": binding.to_dict(), "producer_digest": producer_digest,
        "producer_count": producer_count, "exclusion_reason_counts": reason_counts,
        "finding_set_digest": finding_digest,
    })


def _triage_receipt_fields(
    raw_findings: Sequence[str],
    triaged: Sequence[TriagedHealthFinding],
    candidates: Sequence[TriagedHealthFinding],
    selected: Sequence[TriagedHealthFinding],
    jobs: Sequence[ImprovementJob],
    finding_digest: str,
    producer_count: int,
    producer_digest: str,
    excluded_count: int,
    reason_counts: Dict[str, int],
) -> Dict[str, Any]:
    return {
        "raw_finding_count": len(raw_findings), "unique_finding_count": len(triaged),
        "duplicate_finding_count": len(raw_findings) - len(triaged),
        "disposition_counts": _count_dispositions(triaged),
        "candidate_count": len(candidates), "emitted_job_count": len(jobs),
        "candidate_overflow_count": len(candidates) - len(jobs),
        "finding_set_digest": finding_digest,
        "proposed_finding_ids": [
            _finding_evidence_id(item.finding) for item in selected
        ],
        "proposed_job_set_digest": _canonical_digest(
            [_canonical_job_evidence_dict(job) for job in jobs]
        ),
        "producer_observation_count": producer_count,
        "producer_observation_digest": producer_digest,
        "excluded_non_authoritative_observation_count": excluded_count,
        "exclusion_reason_counts": reason_counts,
    }


def _triage_verified_health_audit(
    raw_findings: Sequence[str],
    *,
    binding: HealthAuditBinding,
    candidate_repo_root: Path,
    tracked_paths: frozenset[str],
    candidate_job_limit: int = 50,
    requested_by: str = "fmas_health_triage",
    producer_observation_count: Optional[int] = None,
    producer_observation_digest: Optional[str] = None,
    excluded_non_authoritative_observation_count: int = 0,
    exclusion_reason_counts: Optional[Dict[str, int]] = None,
) -> HealthAuditTriageResult:
    """Classify producer-bound findings. Internal pure seam for tests."""
    candidate_root = _validate_triage_inputs(
        raw_findings, candidate_repo_root, tracked_paths, candidate_job_limit
    )
    producer_count, producer_digest, reason_counts = _normalize_producer_evidence(
        raw_findings, producer_observation_count, producer_observation_digest,
        excluded_non_authoritative_observation_count, exclusion_reason_counts,
    )
    parsed = _unique_parsed_findings(raw_findings)
    triaged = _triage_findings(
        parsed,
        baseline_attributed=binding.baseline_repo_head_sha is not None,
        candidate_root=candidate_root,
        tracked_paths=tracked_paths,
    )
    finding_digest = _canonical_digest([item.canonical_evidence_dict() for item in triaged])
    audit_id = _health_audit_id(
        binding, producer_count, producer_digest, reason_counts, finding_digest
    )
    candidates = [item for item in triaged if item.disposition == HealthFindingDisposition.CANDIDATE_CHANGE]
    selected = candidates[:candidate_job_limit]
    jobs = _build_candidate_jobs(
        selected, binding=binding, audit_id=audit_id, requested_by=requested_by
    )
    fields = _triage_receipt_fields(
        raw_findings, triaged, candidates, selected, jobs, finding_digest,
        producer_count, producer_digest,
        excluded_non_authoritative_observation_count, reason_counts,
    )
    receipt = _new_triage_receipt(audit_id=audit_id, binding=binding, fields=fields)
    return HealthAuditTriageResult(
        receipt=receipt,
        findings=tuple(triaged),
        jobs=tuple(jobs),
        producer_observation_count=producer_count,
        excluded_non_authoritative_observation_count=excluded_non_authoritative_observation_count,
    )


def validate_health_audit_result(result: HealthAuditTriageResult) -> bool:
    """Recompute immutable receipt and mutable proposal evidence identities."""
    receipt = result.receipt
    receipt_payload = receipt.to_dict()
    claimed_receipt_id = receipt_payload.pop("receipt_id", None)
    if claimed_receipt_id != _canonical_digest(receipt_payload):
        return False
    finding_digest = _canonical_digest(
        [item.canonical_evidence_dict() for item in result.findings]
    )
    if finding_digest != receipt.finding_set_digest:
        return False
    audit_id = _health_audit_id(
        receipt.binding,
        receipt.producer_observation_count,
        receipt.producer_observation_digest,
        dict(receipt.exclusion_reason_counts),
        finding_digest,
    )
    if audit_id != receipt.audit_id:
        return False
    if receipt.proposed_job_set_digest != _canonical_digest(
        [_canonical_job_evidence_dict(job) for job in result.jobs]
    ):
        return False
    candidates = [
        item
        for item in result.findings
        if item.disposition == HealthFindingDisposition.CANDIDATE_CHANGE
    ]
    selected = candidates[: receipt.emitted_job_count]
    if tuple(_finding_evidence_id(item.finding) for item in selected) != tuple(
        receipt.proposed_finding_ids
    ):
        return False
    return (
        receipt.unique_finding_count == len(result.findings)
        and receipt.candidate_count == len(candidates)
        and receipt.emitted_job_count == len(result.jobs)
        and receipt.candidate_overflow_count == len(candidates) - len(result.jobs)
        and dict(receipt.disposition_counts) == _count_dispositions(result.findings)
        and receipt.producer_observation_count == result.producer_observation_count
        and receipt.excluded_non_authoritative_observation_count
        == result.excluded_non_authoritative_observation_count
        and all(job.dry_run for job in result.jobs)
    )


def run_wsp62_health_audit(
    candidate_repo_root: Path,
    *,
    baseline_repo_root: Optional[Path] = None,
    candidate_job_limit: int = 50,
    requested_by: str = "fmas_health_triage",
) -> HealthAuditTriageResult:
    """Run the canonical WSP 62 producer and triage only its bound output."""
    candidate_root = Path(candidate_repo_root).resolve()
    baseline_root = (
        Path(baseline_repo_root).resolve()
        if baseline_repo_root is not None
        else None
    )
    binding = _bind_health_audit(candidate_root, baseline_root)
    tracked_paths = _exact_head_tracked_paths(candidate_root)
    raw_findings = canonical_fmas.audit_file_sizes(
        candidate_root,
        enable_wsp_62=True,
        baseline_root=baseline_root,
        tracked_paths=tracked_paths,
    )
    post_binding = _bind_health_audit(candidate_root, baseline_root)
    if post_binding != binding:
        raise ValueError("health_audit_authority_changed_during_scan")
    if _exact_head_tracked_paths(candidate_root) != tracked_paths:
        raise ValueError("health_audit_tracked_inventory_changed_during_scan")
    authoritative_findings, exclusion_reasons = _authoritative_wsp62_findings(
        raw_findings,
        tracked_paths,
    )
    excluded_count = sum(exclusion_reasons.values())
    return _triage_verified_health_audit(
        authoritative_findings,
        binding=binding,
        candidate_repo_root=candidate_root,
        tracked_paths=tracked_paths,
        candidate_job_limit=candidate_job_limit,
        requested_by=requested_by,
        producer_observation_count=len(raw_findings),
        producer_observation_digest=_canonical_digest(list(raw_findings)),
        excluded_non_authoritative_observation_count=excluded_count,
        exclusion_reason_counts=exclusion_reasons,
    )
