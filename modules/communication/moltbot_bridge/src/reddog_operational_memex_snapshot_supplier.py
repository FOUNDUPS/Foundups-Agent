"""Operational Memex snapshot supplier for resident RedDog audit tasks.

Slice: REDDOG_OPERATIONAL_MEMEX_SNAPSHOT_SUPPLIER_PHASE1

This module enriches already planned read-only audit task packets with an
assignment-bound FoundUp Memex view. It does not project into HoloIndex, query
HoloIndex, write Memex, write Brain/Breadcrumbs, re-index, execute shell, spawn
workers, or mutate repository state. The worker runtime owns projection,
integrity rehydration, query receipt creation, and citation policy.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_runtime_authority import (
    VerifiedOutcomeRuntimeAuthority,
    VerifiedOutcomeRuntimeReference,
)

from modules.communication.moltbot_bridge.src.foundup_memex_current_state import (
    assemble_foundup_memex_current_state,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
    ReadOnlyAuditSwarmEnqueueReceipt,
    ReadOnlyAuditTaskSpec,
    ReadOnlyAuditTaskWriter,
)
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    OperationalContextSnapshot,
)


OPERATIONAL_MEMEX_SUPPLY_ACCEPT = "OPERATIONAL_MEMEX_SUPPLY_ACCEPT"
OPERATIONAL_MEMEX_SUPPLY_REJECT = "OPERATIONAL_MEMEX_SUPPLY_REJECT"


@dataclass(frozen=True)
class OperationalMemexSnapshotSupplyConfig:
    """Typed operator-approved Memex supply config for one resident cycle."""

    foundup_id: str
    principal_id: str
    identity: Mapping[str, Any] = field(default_factory=dict)
    roadmap_state: Mapping[str, Any] = field(default_factory=dict)
    verified_outcome_references: tuple[VerifiedOutcomeRuntimeReference, ...] = ()
    untrusted_verified_outcomes_supplied: bool = False
    policy_issued_at: str = ""
    policy_expires_at: str = ""
    holoindex_generation_id: str = ""
    source_revision: str = ""
    max_records: int = 32

    def to_dict(self) -> dict[str, Any]:
        return {
            "foundup_id": self.foundup_id,
            "principal_id": self.principal_id,
            "identity": dict(self.identity),
            "roadmap_state": dict(self.roadmap_state),
            "verified_outcome_references": [
                reference.to_dict() for reference in self.verified_outcome_references
            ],
            "policy_issued_at": self.policy_issued_at,
            "policy_expires_at": self.policy_expires_at,
            "holoindex_generation_id": self.holoindex_generation_id,
            "source_revision": self.source_revision,
            "max_records": self.max_records,
        }


@dataclass(frozen=True)
class OperationalMemexTaskEnrichmentResult:
    """Result from adding operational Memex bindings to task contexts."""

    accepted: bool
    status: str
    tasks: tuple[ReadOnlyAuditTaskSpec, ...]
    memex_view_id: str | None
    rejection_reasons: tuple[str, ...]
    supply_receipt: Mapping[str, Any] | None = None
    no_memex_write_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_shell_command_executed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "tasks": [task.to_dict() for task in self.tasks],
            "memex_view_id": self.memex_view_id,
            "supply_receipt": dict(self.supply_receipt or {}),
            "rejection_reasons": list(self.rejection_reasons),
            "no_memex_write_performed": self.no_memex_write_performed,
            "no_holoindex_reindex_performed": self.no_holoindex_reindex_performed,
            "no_repo_mutation_performed": self.no_repo_mutation_performed,
            "no_worker_spawn_performed": self.no_worker_spawn_performed,
            "no_shell_command_executed": self.no_shell_command_executed,
        }


class OperationalMemexReadOnlyAuditTaskWriter:
    """Read-only writer wrapper that supplies Memex context before enqueue."""

    def __init__(
        self,
        *,
        delegate: ReadOnlyAuditTaskWriter,
        snapshot: OperationalContextSnapshot,
        config: OperationalMemexSnapshotSupplyConfig | Mapping[str, Any],
        verified_outcome_runtime_authority: VerifiedOutcomeRuntimeAuthority | None = None,
        now_iso: str | None = None,
    ) -> None:
        self.delegate = delegate
        self.snapshot = snapshot
        self.config = normalize_operational_memex_supply_config(config)
        self.verified_outcome_runtime_authority = verified_outcome_runtime_authority
        self.now_iso = now_iso
        self.last_result: OperationalMemexTaskEnrichmentResult | None = None

    def enqueue_readonly_audit_tasks(
        self,
        tasks: Sequence[ReadOnlyAuditTaskSpec],
        receipt: ReadOnlyAuditSwarmEnqueueReceipt,
    ) -> Mapping[str, Any]:
        result = enrich_readonly_audit_tasks_with_operational_memex(
            tasks=tasks,
            snapshot=self.snapshot,
            config=self.config,
            verified_outcome_runtime_authority=self.verified_outcome_runtime_authority,
            now_iso=self.now_iso,
        )
        self.last_result = result
        if not result.accepted:
            return {
                "ok": False,
                "reason": "operational_memex_supply_rejected",
                "rejection_reasons": list(result.rejection_reasons),
                "created_task_ids": [],
            }
        return self.delegate.enqueue_readonly_audit_tasks(result.tasks, receipt)


def normalize_operational_memex_supply_config(
    config: OperationalMemexSnapshotSupplyConfig | Mapping[str, Any],
) -> OperationalMemexSnapshotSupplyConfig:
    """Normalize a mapping into a typed supply config without guessing scope."""

    if isinstance(config, OperationalMemexSnapshotSupplyConfig):
        return config
    data = dict(config or {})
    references = data.get("verified_outcome_references") or ()
    if isinstance(references, Mapping):
        references = (references,)
    return OperationalMemexSnapshotSupplyConfig(
        foundup_id=_clean(data.get("foundup_id")),
        principal_id=_clean(data.get("principal_id")),
        identity=dict(data.get("identity") or {}),
        roadmap_state=dict(data.get("roadmap_state") or {}),
        verified_outcome_references=tuple(
            VerifiedOutcomeRuntimeReference.from_mapping(value)
            for value in references
        ),
        untrusted_verified_outcomes_supplied=bool(data.get("verified_outcomes")),
        policy_issued_at=_clean(data.get("policy_issued_at")),
        policy_expires_at=_clean(data.get("policy_expires_at")),
        holoindex_generation_id=_clean(data.get("holoindex_generation_id")),
        source_revision=_clean(data.get("source_revision")),
        max_records=_positive_int(data.get("max_records"), default=32),
    )


def enrich_readonly_audit_tasks_with_operational_memex(
    *,
    tasks: Sequence[ReadOnlyAuditTaskSpec],
    snapshot: OperationalContextSnapshot,
    config: OperationalMemexSnapshotSupplyConfig | Mapping[str, Any],
    verified_outcome_runtime_authority: VerifiedOutcomeRuntimeAuthority | None = None,
    now_iso: str | None = None,
) -> OperationalMemexTaskEnrichmentResult:
    """Attach a snapshot-bound Memex view and assignment bindings to tasks."""

    try:
        cfg = normalize_operational_memex_supply_config(config)
    except (TypeError, ValueError):
        return _reject("verified_outcome_runtime_reference_invalid")
    reasons = _validate_config(cfg)
    if not isinstance(snapshot, OperationalContextSnapshot):
        reasons.append("missing_operational_snapshot")
    if not tasks:
        reasons.append("missing_readonly_audit_tasks")
    if isinstance(snapshot, OperationalContextSnapshot):
        reasons.extend(_validate_snapshot_memory_sources(snapshot))
    if reasons:
        return _reject(reasons)

    assert isinstance(snapshot, OperationalContextSnapshot)
    issued_at = cfg.policy_issued_at or now_iso or snapshot.created_at
    expires_at = cfg.policy_expires_at or snapshot.valid_until
    generation_id = cfg.holoindex_generation_id or _clean(snapshot.holoindex_state.get("generation_id"))
    source_revision = cfg.source_revision or _clean(snapshot.work_state.get("revision")) or snapshot.snapshot_content_digest
    missing_runtime = [
        name
        for name, value in (
            ("memex_policy_issued_at", issued_at),
            ("memex_policy_expires_at", expires_at),
            ("memex_holoindex_generation_id", generation_id),
            ("memex_source_revision", source_revision),
        )
        if not value
    ]
    if missing_runtime:
        return _reject(missing_runtime)

    capabilities: list[Any] = []
    consumption_now_iso = now_iso or issued_at
    if cfg.verified_outcome_references:
        if verified_outcome_runtime_authority is None:
            return _reject("verified_outcome_runtime_authority_required")
        try:
            capabilities = [
                verified_outcome_runtime_authority.issue(reference)
                for reference in cfg.verified_outcome_references
            ]
        except (RuntimeError, TypeError, ValueError) as exc:
            return _reject(f"verified_outcome_runtime_authority_rejected:{exc}")
        try:
            consumption_now_iso = _trusted_runtime_now_iso(
                verified_outcome_runtime_authority
            )
        except (OSError, OverflowError, TypeError, ValueError) as exc:
            return _reject(f"verified_outcome_trusted_clock_rejected:{exc}")

    assembly = assemble_foundup_memex_current_state(
        foundup_id=cfg.foundup_id,
        snapshot=snapshot,
        identity=cfg.identity,
        roadmap_state=cfg.roadmap_state,
        verified_outcomes=tuple(capabilities),
        now_iso=consumption_now_iso,
        resident_mode=True,
        legacy_single_foundup_compatibility=False,
        policy_foundup_scope=(cfg.foundup_id,),
    )
    if not assembly.accepted or assembly.view is None:
        return _reject("memex_view_assembly_failed:" + ",".join(assembly.rejection_reasons))

    memex_view = assembly.view.to_dict()
    view_id = _clean(memex_view.get("foundup_brain_view_id"))
    enriched: list[ReadOnlyAuditTaskSpec] = []
    assignment_receipts: list[Mapping[str, Any]] = []
    for task in tasks:
        context = dict(task.context)
        assignment = dict(context.get("assignment") or {})
        lane_id = _clean(assignment.get("lane_id")) or "unknown_lane"
        assignment_id = _clean(assignment.get("assignment_id")) or task.task_id
        binding = {
            "foundup_id": cfg.foundup_id,
            "principal_id": cfg.principal_id,
            "work_order_id": assignment_id,
            "memex_now_iso": consumption_now_iso,
            "memex_policy_issued_at": issued_at,
            "memex_policy_expires_at": expires_at,
            "memex_source_scope": f"foundup:{cfg.foundup_id}:lane:{lane_id}",
            "memex_source_revision": source_revision,
            "memex_holoindex_generation_id": generation_id,
        }
        assignment.update(binding)
        context.update(binding)
        context["assignment"] = assignment
        context["memex_view"] = memex_view
        assignment_receipt = {
            "schema_version": "reddog_operational_memex_snapshot_supply_receipt.v1",
            "foundup_id": cfg.foundup_id,
            "principal_id": cfg.principal_id,
            "snapshot_receipt_id": snapshot.snapshot_receipt_id,
            "snapshot_content_digest": snapshot.snapshot_content_digest,
            "memex_view_id": view_id,
            "holoindex_generation_id": generation_id,
            "source_revision": source_revision,
            "policy_issued_at": issued_at,
            "policy_expires_at": expires_at,
            "assignment_id": assignment_id,
            "lane_id": lane_id,
            "receipt_id": _digest(
                {
                    "snapshot_receipt_id": snapshot.snapshot_receipt_id,
                    "snapshot_content_digest": snapshot.snapshot_content_digest,
                    "memex_view_id": view_id,
                    "assignment_id": assignment_id,
                    "lane_id": lane_id,
                    "principal_id": cfg.principal_id,
                    "foundup_id": cfg.foundup_id,
                }
            ),
            "no_memex_write_performed": True,
            "no_holoindex_reindex_performed": True,
            "no_repo_mutation_performed": True,
        }
        context["memex_snapshot_supply_receipt"] = assignment_receipt
        assignment_receipts.append(assignment_receipt)
        enriched.append(replace(task, context=context))

    supply_receipt = _cycle_supply_receipt(
        config=cfg,
        snapshot=snapshot,
        memex_view_id=view_id,
        generation_id=generation_id,
        source_revision=source_revision,
        issued_at=issued_at,
        expires_at=expires_at,
        tasks=enriched,
        assignment_receipts=assignment_receipts,
    )

    return OperationalMemexTaskEnrichmentResult(
        accepted=True,
        status=OPERATIONAL_MEMEX_SUPPLY_ACCEPT,
        tasks=tuple(enriched),
        memex_view_id=view_id,
        supply_receipt=supply_receipt,
        rejection_reasons=(),
    )


def _validate_config(config: OperationalMemexSnapshotSupplyConfig) -> list[str]:
    reasons: list[str] = []
    if not config.foundup_id:
        reasons.append("missing_foundup_id")
    if not config.principal_id:
        reasons.append("missing_principal_id")
    if not isinstance(config.identity, Mapping) or not config.identity:
        reasons.append("missing_memex_identity")
    if not isinstance(config.roadmap_state, Mapping) or not config.roadmap_state:
        reasons.append("missing_memex_roadmap_state")
    if config.max_records <= 0:
        reasons.append("invalid_max_records")
    if config.untrusted_verified_outcomes_supplied:
        reasons.append("untrusted_verified_outcomes_forbidden")
    if len(config.verified_outcome_references) > config.max_records:
        reasons.append("verified_outcome_reference_limit_exceeded")
    return reasons


def _validate_snapshot_memory_sources(snapshot: OperationalContextSnapshot) -> list[str]:
    reasons: list[str] = []
    if snapshot.brain_state.get("available") is not True:
        reasons.append("brain_source_not_available")
    if int(snapshot.brain_state.get("record_count") or 0) <= 0:
        reasons.append("brain_source_empty")
    if int(snapshot.breadcrumbs_state.get("record_count") or 0) <= 0:
        reasons.append("breadcrumbs_source_empty")
    return reasons


def _cycle_supply_receipt(
    *,
    config: OperationalMemexSnapshotSupplyConfig,
    snapshot: OperationalContextSnapshot,
    memex_view_id: str,
    generation_id: str,
    source_revision: str,
    issued_at: str,
    expires_at: str,
    tasks: Sequence[ReadOnlyAuditTaskSpec],
    assignment_receipts: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Return one cycle-level receipt for all assignment-bound Memex supplies."""

    assignment_ids: list[str] = []
    lane_ids: list[str] = []
    task_ids: list[str] = []
    assignment_receipt_ids: list[str] = []
    for task, receipt in zip(tasks, assignment_receipts):
        assignment = task.context.get("assignment") if isinstance(task.context, Mapping) else {}
        assignment_ids.append(_clean(assignment.get("assignment_id")) or task.task_id)
        lane_ids.append(_clean(assignment.get("lane_id")) or "unknown_lane")
        task_ids.append(task.task_id)
        assignment_receipt_ids.append(_clean(receipt.get("receipt_id")))

    body = {
        "schema_version": "reddog_operational_memex_snapshot_supply_receipt.v1",
        "foundup_id": config.foundup_id,
        "principal_id": config.principal_id,
        "snapshot_receipt_id": snapshot.snapshot_receipt_id,
        "snapshot_content_digest": snapshot.snapshot_content_digest,
        "memex_view_id": memex_view_id,
        "holoindex_generation_id": generation_id,
        "source_revision": source_revision,
        "policy_issued_at": issued_at,
        "policy_expires_at": expires_at,
        "assignment_count": len(assignment_ids),
        "assignment_ids": tuple(assignment_ids),
        "lane_ids": tuple(lane_ids),
        "task_ids": tuple(task_ids),
        "assignment_receipt_ids": tuple(assignment_receipt_ids),
        "max_records": config.max_records,
        "no_memex_write_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_repo_mutation_performed": True,
    }
    return {**body, "receipt_id": _digest(body)}


def _reject(*reasons: Any) -> OperationalMemexTaskEnrichmentResult:
    flattened: list[str] = []
    for reason in reasons:
        if isinstance(reason, (list, tuple)):
            flattened.extend(str(item) for item in reason)
        else:
            flattened.append(str(reason))
    return OperationalMemexTaskEnrichmentResult(
        accepted=False,
        status=OPERATIONAL_MEMEX_SUPPLY_REJECT,
        tasks=(),
        memex_view_id=None,
        rejection_reasons=tuple(dict.fromkeys(item for item in flattened if item)),
    )


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _trusted_runtime_now_iso(authority: VerifiedOutcomeRuntimeAuthority) -> str:
    now_epoch = authority.trusted_now_epoch()
    if type(now_epoch) is not int or now_epoch <= 0:
        raise ValueError("trusted_now_epoch_invalid")
    return datetime.fromtimestamp(now_epoch, timezone.utc).isoformat()


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "OPERATIONAL_MEMEX_SUPPLY_ACCEPT",
    "OPERATIONAL_MEMEX_SUPPLY_REJECT",
    "OperationalMemexReadOnlyAuditTaskWriter",
    "OperationalMemexSnapshotSupplyConfig",
    "OperationalMemexTaskEnrichmentResult",
    "enrich_readonly_audit_tasks_with_operational_memex",
    "normalize_operational_memex_supply_config",
]
