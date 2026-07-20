"""Backend RedDog architect determination runtime.

Slice: REDDOG_BACKEND_ARCHITECT_DETERMINATION_RUNTIME_PHASE1

This module consumes an accepted operational snapshot plus collected read-only
audit reports, calls a redaction-gated RedDog/Fusion model runner, validates a
bounded architect determination, persists that determination, and emits at most
one candidate WRE queue item for a FIX decision.

It does not spawn workers, execute shell commands, mutate repository files,
create worktrees, enqueue OpenClaw, dispatch Hermes, publish PRs, admit
PatternMemory, settle rewards, or re-index HoloIndex.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Protocol, Sequence

from modules.communication.moltbot_bridge.src.reddog_context_snapshot_fusion_assignment_gate import (
    FUSION_ASSIGNMENT_GATE_PASSED,
    FusionAssignmentGateDecision,
)
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    ContextView,
    EvidenceBundle,
    OperationalContextSnapshot,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_report_collection import (
    ReadOnlyAuditReportCollectionResult,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    validate_reddog_wsp15_allocation_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import (
    SelectionDecision,
    SelectionPurpose,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding import ModelRuntimeBindingDecision
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    rehydrate_model_runtime_binding_receipt,
    rehydrate_model_selection_receipt,
)


ARCHITECT_DETERMINATION_ACCEPT = "ARCHITECT_DETERMINATION_ACCEPT"
ARCHITECT_DETERMINATION_REJECT = "ARCHITECT_DETERMINATION_REJECT"
ARCHITECT_DETERMINATION_SCHEMA_VERSION = "reddog_architect_determination_receipt.v1"
ARCHITECT_QUEUE_CANDIDATE_SCHEMA_VERSION = "reddog_architect_queue_candidate.v1"

ACTION_FIX = "FIX"
ACTION_RESEARCH_MORE = "RESEARCH_MORE"
ACTION_REVISE = "REVISE"
ACTION_STOP = "STOP"
ALLOWED_ACTIONS = (ACTION_FIX, ACTION_RESEARCH_MORE, ACTION_REVISE, ACTION_STOP)

ENV_ARCHITECT_RUNTIME_MODE = "REDDOG_BACKEND_ARCHITECT_RUNTIME_MODE"
RUNTIME_MODE_FOUNDUPS_FUSION = "foundups_fusion"
DEFAULT_MAX_PROMPT_CHARS = 24_000
RUNTIME_SURFACE_BACKEND_ARCHITECT = "reddog_backend_architect"


class ArchitectDeterminationReason:
    MISSING_SNAPSHOT = "REJECT_ARCHITECT_DETERMINATION_MISSING_SNAPSHOT"
    SNAPSHOT_REJECTED = "REJECT_ARCHITECT_DETERMINATION_SNAPSHOT_REJECTED"
    SNAPSHOT_EXPIRED = "REJECT_ARCHITECT_DETERMINATION_SNAPSHOT_EXPIRED"
    SNAPSHOT_HAS_CONFLICTS = "REJECT_ARCHITECT_DETERMINATION_SNAPSHOT_HAS_CONFLICTS"
    MISSING_CONTEXT_VIEW = "REJECT_ARCHITECT_DETERMINATION_MISSING_CONTEXT_VIEW"
    MISSING_EVIDENCE_BUNDLE = "REJECT_ARCHITECT_DETERMINATION_MISSING_EVIDENCE_BUNDLE"
    FUSION_GATE_NOT_PASSED = "REJECT_ARCHITECT_DETERMINATION_FUSION_GATE_NOT_PASSED"
    MISSING_DETERMINATION_BINDING = "REJECT_ARCHITECT_DETERMINATION_MISSING_BINDING"
    REPORT_COLLECTION_NOT_ACCEPTED = "REJECT_ARCHITECT_DETERMINATION_REPORT_COLLECTION_NOT_ACCEPTED"
    MISSING_AUDIT_REPORTS = "REJECT_ARCHITECT_DETERMINATION_MISSING_AUDIT_REPORTS"
    REPORT_COUNT_MISMATCH = "REJECT_ARCHITECT_DETERMINATION_REPORT_COUNT_MISMATCH"
    REPORT_MISSING_RECEIPT = "REJECT_ARCHITECT_DETERMINATION_REPORT_MISSING_RECEIPT"
    REPORT_MISSING_EVIDENCE = "REJECT_ARCHITECT_DETERMINATION_REPORT_MISSING_EVIDENCE"
    REPORT_CLAIMS_SIDE_EFFECT = "REJECT_ARCHITECT_DETERMINATION_REPORT_CLAIMS_SIDE_EFFECT"
    MISSING_WSP15_ALLOCATION = "REJECT_ARCHITECT_DETERMINATION_MISSING_WSP15_ALLOCATION"
    MALFORMED_WSP15_ALLOCATION = "REJECT_ARCHITECT_DETERMINATION_MALFORMED_WSP15_ALLOCATION"
    DUPLICATE_CYCLE = "REJECT_ARCHITECT_DETERMINATION_DUPLICATE_CYCLE"
    MODEL_FAILURE = "REJECT_ARCHITECT_DETERMINATION_MODEL_FAILURE"
    MODEL_TIMEOUT = "REJECT_ARCHITECT_DETERMINATION_MODEL_TIMEOUT"
    FUSION_QUORUM_NOT_PASSED = "REJECT_ARCHITECT_DETERMINATION_FUSION_QUORUM_NOT_PASSED"
    INVALID_MODEL_OUTPUT = "REJECT_ARCHITECT_DETERMINATION_INVALID_MODEL_OUTPUT"
    WSP15_RECEIPT_MISMATCH = "REJECT_ARCHITECT_DETERMINATION_WSP15_RECEIPT_MISMATCH"
    STORE_REJECTED = "REJECT_ARCHITECT_DETERMINATION_STORE_REJECTED"
    PROMPT_BUDGET_EXCEEDED = "REJECT_ARCHITECT_DETERMINATION_PROMPT_BUDGET_EXCEEDED"
    MODEL_SELECTION_RECEIPT = "REJECT_ARCHITECT_DETERMINATION_MODEL_SELECTION_RECEIPT"
    MODEL_RUNTIME_BINDING_RECEIPT = "REJECT_ARCHITECT_DETERMINATION_MODEL_RUNTIME_BINDING_RECEIPT"


@dataclass(frozen=True)
class ArchitectModelResult:
    """Result returned by a configured backend architect model runner."""

    ok: bool
    status: str
    content: str
    model_receipt_id: Optional[str]
    model_result_digest: str
    review_packet: Mapping[str, Any]
    made_network_call: bool
    rejection_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ArchitectModelRunner(Protocol):
    """Runtime model runner interface for backend architect determination."""

    def run_architect_determination(
        self,
        *,
        prompt: str,
        context: str,
        binding: Mapping[str, Any],
        timeout_seconds: int,
    ) -> ArchitectModelResult: ...


@dataclass(frozen=True)
class FoundupsFusionArchitectModelRunner:
    """Production runner for the existing redaction-gated FoundUps Fusion bridge.

    The runner is concrete, not a SPECIFIED_NOT_IMPLEMENTED placeholder. It is
    explicit-mode only: callers must set REDDOG_BACKEND_ARCHITECT_RUNTIME_MODE
    to ``foundups_fusion`` and provide OPENROUTER_API_KEY. Tests should inject a
    fake runner instead of reaching the network.
    """

    lead_model: str = ""
    panel_models: tuple[str, ...] = ()
    max_tokens: int = 1200
    temperature: float = 0.0

    def run_architect_determination(
        self,
        *,
        prompt: str,
        context: str,
        binding: Mapping[str, Any],
        timeout_seconds: int,
    ) -> ArchitectModelResult:
        if os.getenv(ENV_ARCHITECT_RUNTIME_MODE, "").strip() != RUNTIME_MODE_FOUNDUPS_FUSION:
            return _model_result_reject("runtime_mode_not_enabled")
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return _model_result_reject("missing_openrouter_api_key")
        try:
            from modules.communication.moltbot_bridge.src.fusion_redaction_gate import (
                REDACTION_GATE_PASSED,
                evaluate_redaction_gate,
            )
            run_foundups_fusion = _load_foundups_fusion_runner()
        except Exception:
            return _model_result_reject("fusion_bridge_unavailable")

        gate = evaluate_redaction_gate(prompt, context, audit_mode=True)
        if gate.status != REDACTION_GATE_PASSED or not gate.redacted_prompt:
            return _model_result_reject("redaction_blocked")
        model_topology = _runtime_model_topology(
            binding,
            default_lead=self.lead_model,
            default_panel=self.panel_models,
        )
        if (
            not model_topology["model_runtime_binding_receipt_id"]
            or not model_topology["lead_model"]
        ):
            return _model_result_reject(ArchitectDeterminationReason.MODEL_RUNTIME_BINDING_RECEIPT)
        redacted_user = gate.redacted_prompt
        if gate.redacted_context:
            redacted_user = gate.redacted_prompt + "\n\n" + gate.redacted_context
        payload = {
            "mode": "foundups_fusion",
            "lead_model": model_topology["lead_model"],
            "panel_models": list(model_topology["panel_models"]),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout": timeout_seconds,
            "_redacted_evidence_context": gate.redacted_context or "",
            "bridge_meta": {
                "architect_binding": dict(binding),
                "model_selection_receipt_id": model_topology["model_selection_receipt_id"],
                "model_runtime_binding_receipt_id": model_topology["model_runtime_binding_receipt_id"],
            },
        }
        try:
            result = run_foundups_fusion(api_key, redacted_user, [], payload)
        except TimeoutError:
            return _model_result_reject(ArchitectDeterminationReason.MODEL_TIMEOUT)
        except Exception:
            return _model_result_reject("fusion_bridge_call_failed")
        if not isinstance(result, Mapping) or result.get("ok") is not True:
            return _model_result_reject(str(result.get("reason") if isinstance(result, Mapping) else "model_failed"))
        content = str(result.get("content") or "")
        review_packet = result.get("review_packet") if isinstance(result.get("review_packet"), Mapping) else {}
        model_receipt_id = str(review_packet.get("receipt_id") or "").strip() or None
        return ArchitectModelResult(
            ok=True,
            status="MODEL_OK",
            content=content,
            model_receipt_id=model_receipt_id,
            model_result_digest=_digest({"content": content, "review_packet": review_packet}),
            review_packet=dict(review_packet),
            made_network_call=True,
            rejection_reasons=(),
        )


@dataclass(frozen=True)
class ArchitectQueueCandidate:
    """Queue candidate emitted by a FIX determination."""

    schema_version: str
    queue_candidate_id: str
    source_determination_receipt_id: str
    slice_id: str
    status: str
    evidence_refs: tuple[str, ...]
    wsp15_allocation_receipt: Mapping[str, Any]
    no_queue_mutation_performed: bool = True
    no_execution_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArchitectDeterminationReceipt:
    """Validated backend architect determination receipt."""

    schema_version: str
    determination_receipt_id: str
    cycle_id: str
    accepted: bool
    status: str
    action: str
    next_slice_name: Optional[str]
    summary: str
    snapshot_receipt_id: Optional[str]
    snapshot_content_digest: Optional[str]
    context_view_id: Optional[str]
    evidence_bundle_id: Optional[str]
    report_bundle_id: Optional[str]
    report_count: int
    audit_report_digests: tuple[str, ...]
    model_result_digest: Optional[str]
    model_receipt_id: Optional[str]
    model_selection_receipt_id: Optional[str]
    model_selection_digest: Optional[str]
    model_runtime_binding_receipt_id: Optional[str]
    model_runtime_binding_digest: Optional[str]
    fusion_quorum_passed: bool
    wsp15_allocation_receipt_id: Optional[str]
    wsp15_allocation_digest: Optional[str]
    queue_candidate: Optional[ArchitectQueueCandidate]
    decision_reasons: tuple[str, ...]
    rejection_reasons: tuple[str, ...]
    no_coding_worker_spawned: bool = True
    no_shell_command_executed: bool = True
    no_worktree_operation_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_promotion_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["queue_candidate"] = self.queue_candidate.to_dict() if self.queue_candidate else None
        return data


@dataclass(frozen=True)
class ArchitectDeterminationPersistResult:
    """Persistence result for a backend architect determination."""

    accepted: bool
    status: str
    determination_receipt_id: Optional[str]
    cycle_id: Optional[str]
    stored: bool
    idempotent: bool
    rejection_reasons: tuple[str, ...]
    no_queue_mutation_performed: bool = True
    no_execution_performed: bool = True
    no_repo_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BackendArchitectDeterminationResult:
    """Top-level runtime result."""

    accepted: bool
    status: str
    receipt: ArchitectDeterminationReceipt
    persist_result: ArchitectDeterminationPersistResult
    queue_candidate_count: int
    rejection_reasons: tuple[str, ...]
    no_coding_worker_spawned: bool = True
    no_shell_command_executed: bool = True
    no_worktree_operation_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_promotion_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "receipt": self.receipt.to_dict(),
            "persist_result": self.persist_result.to_dict(),
            "queue_candidate_count": self.queue_candidate_count,
            "rejection_reasons": list(self.rejection_reasons),
            "no_coding_worker_spawned": self.no_coding_worker_spawned,
            "no_shell_command_executed": self.no_shell_command_executed,
            "no_worktree_operation_performed": self.no_worktree_operation_performed,
            "no_repo_mutation_performed": self.no_repo_mutation_performed,
            "no_openclaw_enqueue_performed": self.no_openclaw_enqueue_performed,
            "no_hermes_dispatch_performed": self.no_hermes_dispatch_performed,
            "no_pr_created": self.no_pr_created,
            "no_pattern_memory_promotion_performed": self.no_pattern_memory_promotion_performed,
            "no_holoindex_reindex_performed": self.no_holoindex_reindex_performed,
        }


@dataclass(frozen=True)
class ArchitectDeterminationRecord:
    determination_receipt_id: str
    cycle_id: str
    action: str
    next_slice_name: Optional[str]
    determination: Mapping[str, Any]
    stored_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ArchitectDeterminationStore(Protocol):
    def load_architect_determination_by_cycle(self, cycle_id: str) -> Optional[Mapping[str, Any]]: ...

    def store_architect_determination(self, record: ArchitectDeterminationRecord) -> Mapping[str, Any]: ...


class InMemoryArchitectDeterminationStore:
    """Test/runtime helper with duplicate-cycle protection."""

    def __init__(self, initial: Sequence[Mapping[str, Any]] = (), *, reject: bool = False) -> None:
        self.reject = reject
        self.records: list[ArchitectDeterminationRecord] = []
        self._by_cycle: dict[str, Mapping[str, Any]] = {}
        for item in initial:
            cycle_id = str(item.get("cycle_id") or "")
            if cycle_id:
                self._by_cycle[cycle_id] = dict(item)

    def load_architect_determination_by_cycle(self, cycle_id: str) -> Optional[Mapping[str, Any]]:
        return self._by_cycle.get(cycle_id)

    def store_architect_determination(self, record: ArchitectDeterminationRecord) -> Mapping[str, Any]:
        if self.reject:
            return {"ok": False, "reason": "store_rejected"}
        existing = self._by_cycle.get(record.cycle_id)
        payload = record.to_dict()
        if existing is not None:
            if _canonical_json(existing) == _canonical_json(payload):
                return {"ok": True, "stored": False, "idempotent": True}
            return {"ok": False, "reason": "duplicate_cycle"}
        self.records.append(record)
        self._by_cycle[record.cycle_id] = payload
        return {"ok": True, "stored": True, "idempotent": False}


class AgentDbArchitectDeterminationStore:
    """AgentDB-backed store for backend architect determination receipts."""

    def __init__(self, agent_db_factory: Optional[Any] = None) -> None:
        self._agent_db_factory = agent_db_factory

    def load_architect_determination_by_cycle(self, cycle_id: str) -> Optional[Mapping[str, Any]]:
        db = self._agent_db()
        self._ensure_table(db)
        rows = db.db.execute_query(
            """
            SELECT determination_json FROM reddog_architect_determinations
            WHERE cycle_id = ?
            """,
            (cycle_id,),
        )
        if not rows:
            return None
        value = rows[0]["determination_json"] if isinstance(rows[0], Mapping) else rows[0][0]
        return json.loads(value)

    def store_architect_determination(self, record: ArchitectDeterminationRecord) -> Mapping[str, Any]:
        db = self._agent_db()
        self._ensure_table(db)
        determination_json = _canonical_json(record.determination)
        with db.db.get_connection() as conn:
            existing = conn.execute(
                """
                SELECT determination_json FROM reddog_architect_determinations
                WHERE cycle_id = ?
                """,
                (record.cycle_id,),
            ).fetchone()
            if existing:
                existing_json = existing["determination_json"] if hasattr(existing, "keys") else existing[0]
                if existing_json == determination_json:
                    return {"ok": True, "stored": False, "idempotent": True}
                return {"ok": False, "reason": "duplicate_cycle"}
            conn.execute(
                """
                INSERT INTO reddog_architect_determinations
                (determination_receipt_id, cycle_id, action, next_slice_name, determination_json, stored_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.determination_receipt_id,
                    record.cycle_id,
                    record.action,
                    record.next_slice_name,
                    determination_json,
                    record.stored_at,
                ),
            )
        return {"ok": True, "stored": True, "idempotent": False}

    def _agent_db(self) -> Any:
        factory = self._agent_db_factory
        if factory is None:
            from modules.infrastructure.database.src.agent_db import AgentDB

            factory = AgentDB
        return factory()

    @staticmethod
    def _ensure_table(db: Any) -> None:
        with db.db.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reddog_architect_determinations (
                    determination_receipt_id TEXT PRIMARY KEY,
                    cycle_id TEXT NOT NULL UNIQUE,
                    action TEXT NOT NULL,
                    next_slice_name TEXT,
                    determination_json TEXT NOT NULL,
                    stored_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_reddog_architect_determinations_action
                ON reddog_architect_determinations(action)
                """
            )


def run_reddog_backend_architect_determination_runtime(
    *,
    snapshot: OperationalContextSnapshot | None,
    context_view: ContextView | None,
    evidence_bundle: EvidenceBundle | None,
    fusion_gate: FusionAssignmentGateDecision | None,
    report_collection: ReadOnlyAuditReportCollectionResult | None,
    reports: Sequence[Mapping[str, Any]],
    wsp15_allocation_receipt: Mapping[str, Any],
    store: ArchitectDeterminationStore | None = None,
    model_runner: ArchitectModelRunner | None = None,
    model_selection_receipt: Mapping[str, Any] | None = None,
    model_runtime_binding_receipt: Mapping[str, Any] | None = None,
    now_iso: str | None = None,
    timeout_seconds: int = 60,
) -> BackendArchitectDeterminationResult:
    """Produce, persist, and queue-candidate one backend architect determination."""

    observed_at = now_iso or datetime.now(timezone.utc).isoformat()
    reasons: list[str] = []
    model_result: ArchitectModelResult | None = None

    _validate_static_inputs(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        fusion_gate=fusion_gate,
        report_collection=report_collection,
        reports=reports,
        wsp15_allocation_receipt=wsp15_allocation_receipt,
        now_iso=observed_at,
        reasons=reasons,
    )
    report_bundle_id = _report_bundle_id(report_collection)
    report_digests = _report_digests(reports)
    allocation_receipt_id = str(wsp15_allocation_receipt.get("receipt_id") or "").strip() or None
    allocation_digest = _digest(wsp15_allocation_receipt) if isinstance(wsp15_allocation_receipt, Mapping) else None
    model_selection = _model_runtime_binding(
        model_runtime_binding_receipt,
        reasons,
        expected_surface=RUNTIME_SURFACE_BACKEND_ARCHITECT,
    )
    production_runner = model_runner is None or isinstance(model_runner, FoundupsFusionArchitectModelRunner)
    if not model_selection and production_runner:
        if ArchitectDeterminationReason.MODEL_RUNTIME_BINDING_RECEIPT not in reasons:
            reasons.append(ArchitectDeterminationReason.MODEL_RUNTIME_BINDING_RECEIPT)
    elif not model_selection:
        model_selection = _model_selection_binding(model_selection_receipt, reasons)
    model_selection_receipt_id = str(model_selection.get("receipt_id") or "").strip() or None
    model_selection_digest = str(model_selection.get("digest") or "").strip() or None
    model_runtime_binding_receipt_id = (
        str(model_selection.get("model_runtime_binding_receipt_id") or "").strip() or None
    )
    model_runtime_binding_digest = (
        str(model_selection.get("model_runtime_binding_digest") or "").strip() or None
    )
    cycle_id = _cycle_id(
        snapshot=snapshot,
        report_bundle_id=report_bundle_id,
        report_digests=report_digests,
        wsp15_allocation_digest=allocation_digest,
        model_selection_digest=model_selection_digest,
    )
    writer = store if store is not None else AgentDbArchitectDeterminationStore()
    if cycle_id and not reasons:
        try:
            if writer.load_architect_determination_by_cycle(cycle_id) is not None:
                reasons.append(ArchitectDeterminationReason.DUPLICATE_CYCLE)
        except Exception:
            reasons.append(ArchitectDeterminationReason.STORE_REJECTED)

    if reasons:
        receipt = _receipt(
            accepted=False,
            action=ACTION_STOP,
            next_slice_name=None,
            summary="Backend architect determination rejected before model call.",
            snapshot=snapshot,
            context_view=context_view,
            evidence_bundle=evidence_bundle,
            report_bundle_id=report_bundle_id,
            report_count=_report_count(report_collection),
            report_digests=report_digests,
            model_result=None,
            allocation_receipt_id=allocation_receipt_id,
            allocation_digest=allocation_digest,
            cycle_id=cycle_id or "sha256:" + "0" * 64,
            decision_reasons=(),
            rejection_reasons=_dedupe(reasons),
            model_selection_receipt_id=model_selection_receipt_id,
            model_selection_digest=model_selection_digest,
            model_runtime_binding_receipt_id=model_runtime_binding_receipt_id,
            model_runtime_binding_digest=model_runtime_binding_digest,
        )
        persist_result = _persist_rejected(receipt)
        return _result(receipt=receipt, persist_result=persist_result)

    assert snapshot is not None
    assert context_view is not None
    assert evidence_bundle is not None
    assert fusion_gate is not None
    assert report_collection is not None
    assert cycle_id is not None
    runner = model_runner if model_runner is not None else FoundupsFusionArchitectModelRunner()
    try:
        prompt = _build_architect_prompt(
            snapshot=snapshot,
            report_collection=report_collection,
            reports=reports,
            wsp15_allocation_receipt=wsp15_allocation_receipt,
        )
        context = _build_architect_context(
            context_view=context_view,
            evidence_bundle=evidence_bundle,
            reports=reports,
        )
    except ValueError:
        receipt = _receipt(
            accepted=False,
            action=ACTION_STOP,
            next_slice_name=None,
            summary="Backend architect prompt/context exceeded deterministic budget.",
            snapshot=snapshot,
            context_view=context_view,
            evidence_bundle=evidence_bundle,
            report_bundle_id=report_bundle_id,
            report_count=_report_count(report_collection),
            report_digests=report_digests,
            model_result=None,
            allocation_receipt_id=allocation_receipt_id,
            allocation_digest=allocation_digest,
            cycle_id=cycle_id,
            decision_reasons=(),
            rejection_reasons=(ArchitectDeterminationReason.PROMPT_BUDGET_EXCEEDED,),
            model_selection_receipt_id=model_selection_receipt_id,
            model_selection_digest=model_selection_digest,
            model_runtime_binding_receipt_id=model_runtime_binding_receipt_id,
            model_runtime_binding_digest=model_runtime_binding_digest,
        )
        return _result(receipt=receipt, persist_result=_persist_rejected(receipt))
    binding = fusion_gate.determination_binding.to_dict() if fusion_gate.determination_binding else {}
    if model_selection:
        binding = {**binding, "model_selection": dict(model_selection)}
    try:
        model_result = runner.run_architect_determination(
            prompt=prompt,
            context=context,
            binding=binding,
            timeout_seconds=timeout_seconds,
        )
    except TimeoutError:
        reasons.append(ArchitectDeterminationReason.MODEL_TIMEOUT)
        model_result = None
    except Exception:
        reasons.append(ArchitectDeterminationReason.MODEL_FAILURE)
        model_result = None

    if model_result is None:
        receipt = _receipt(
            accepted=False,
            action=ACTION_STOP,
            next_slice_name=None,
            summary="Backend architect model call failed.",
            snapshot=snapshot,
            context_view=context_view,
            evidence_bundle=evidence_bundle,
            report_bundle_id=report_bundle_id,
            report_count=_report_count(report_collection),
            report_digests=report_digests,
            model_result=None,
            allocation_receipt_id=allocation_receipt_id,
            allocation_digest=allocation_digest,
            cycle_id=cycle_id,
            decision_reasons=(),
            rejection_reasons=_dedupe(reasons),
            model_selection_receipt_id=model_selection_receipt_id,
            model_selection_digest=model_selection_digest,
            model_runtime_binding_receipt_id=model_runtime_binding_receipt_id,
            model_runtime_binding_digest=model_runtime_binding_digest,
        )
        persist_result = _persist_rejected(receipt)
        return _result(receipt=receipt, persist_result=persist_result)

    if not model_result.ok:
        reasons.append(ArchitectDeterminationReason.MODEL_FAILURE)
        reasons.extend(model_result.rejection_reasons)
    if not _fusion_quorum_passed(model_result.review_packet):
        reasons.append(ArchitectDeterminationReason.FUSION_QUORUM_NOT_PASSED)

    parsed = _parse_model_output(model_result.content)
    output_reasons: list[str] = []
    _validate_model_output(
        parsed,
        reports=reports,
        wsp15_allocation_receipt_id=allocation_receipt_id,
        output_reasons=output_reasons,
    )
    reasons.extend(output_reasons)
    if reasons:
        receipt = _receipt(
            accepted=False,
            action=ACTION_STOP,
            next_slice_name=None,
            summary="Backend architect determination rejected after model validation.",
            snapshot=snapshot,
            context_view=context_view,
            evidence_bundle=evidence_bundle,
            report_bundle_id=report_bundle_id,
            report_count=_report_count(report_collection),
            report_digests=report_digests,
            model_result=model_result,
            allocation_receipt_id=allocation_receipt_id,
            allocation_digest=allocation_digest,
            cycle_id=cycle_id,
            decision_reasons=(),
            rejection_reasons=_dedupe(reasons),
            model_selection_receipt_id=model_selection_receipt_id,
            model_selection_digest=model_selection_digest,
            model_runtime_binding_receipt_id=model_runtime_binding_receipt_id,
            model_runtime_binding_digest=model_runtime_binding_digest,
        )
        persist_result = _persist_rejected(receipt)
        return _result(receipt=receipt, persist_result=persist_result)

    action = str(parsed["action"]).upper()
    next_slice_name = str(parsed.get("next_slice_name") or "").strip() or None
    summary = str(parsed.get("summary") or "").strip()
    decision_reasons = _normalize_text_list(parsed.get("decision_reasons"))
    queue_candidate = None
    receipt_stub_id = _digest(
        {
            "cycle_id": cycle_id,
            "action": action,
            "next_slice_name": next_slice_name,
            "model_result_digest": model_result.model_result_digest,
            "model_selection_digest": model_selection_digest,
        }
    )
    if action == ACTION_FIX:
        assert next_slice_name is not None
        queue_candidate = _queue_candidate(
            source_determination_receipt_id=receipt_stub_id,
            next_slice_name=next_slice_name,
            snapshot=snapshot,
            report_bundle_id=report_bundle_id,
            wsp15_allocation_receipt=wsp15_allocation_receipt,
        )
    receipt = _receipt(
        accepted=True,
        action=action,
        next_slice_name=next_slice_name,
        summary=summary,
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=evidence_bundle,
        report_bundle_id=report_bundle_id,
        report_count=_report_count(report_collection),
        report_digests=report_digests,
        model_result=model_result,
        allocation_receipt_id=allocation_receipt_id,
        allocation_digest=allocation_digest,
        cycle_id=cycle_id,
        decision_reasons=decision_reasons,
        rejection_reasons=(),
        model_selection_receipt_id=model_selection_receipt_id,
        model_selection_digest=model_selection_digest,
        model_runtime_binding_receipt_id=model_runtime_binding_receipt_id,
        model_runtime_binding_digest=model_runtime_binding_digest,
        queue_candidate=queue_candidate,
        determination_receipt_id=receipt_stub_id,
    )
    persist_result = _persist_receipt(receipt, writer=writer, now_iso=observed_at)
    if not persist_result.accepted:
        failed = _receipt(
            accepted=False,
            action=ACTION_STOP,
            next_slice_name=None,
            summary="Backend architect determination persistence rejected.",
            snapshot=snapshot,
            context_view=context_view,
            evidence_bundle=evidence_bundle,
            report_bundle_id=report_bundle_id,
            report_count=_report_count(report_collection),
            report_digests=report_digests,
            model_result=model_result,
            allocation_receipt_id=allocation_receipt_id,
            allocation_digest=allocation_digest,
            cycle_id=cycle_id,
            decision_reasons=decision_reasons,
            rejection_reasons=(ArchitectDeterminationReason.STORE_REJECTED, *persist_result.rejection_reasons),
            model_selection_receipt_id=model_selection_receipt_id,
            model_selection_digest=model_selection_digest,
            model_runtime_binding_receipt_id=model_runtime_binding_receipt_id,
            model_runtime_binding_digest=model_runtime_binding_digest,
        )
        return _result(receipt=failed, persist_result=persist_result)
    return _result(receipt=receipt, persist_result=persist_result)


def _validate_static_inputs(
    *,
    snapshot: OperationalContextSnapshot | None,
    context_view: ContextView | None,
    evidence_bundle: EvidenceBundle | None,
    fusion_gate: FusionAssignmentGateDecision | None,
    report_collection: ReadOnlyAuditReportCollectionResult | None,
    reports: Sequence[Mapping[str, Any]],
    wsp15_allocation_receipt: Mapping[str, Any],
    now_iso: str,
    reasons: list[str],
) -> None:
    if snapshot is None:
        reasons.append(ArchitectDeterminationReason.MISSING_SNAPSHOT)
    else:
        if snapshot.rejection_reasons:
            reasons.append(ArchitectDeterminationReason.SNAPSHOT_REJECTED)
        if snapshot.conflicts:
            reasons.append(ArchitectDeterminationReason.SNAPSHOT_HAS_CONFLICTS)
        if _snapshot_expired(snapshot.valid_until, now_iso):
            reasons.append(ArchitectDeterminationReason.SNAPSHOT_EXPIRED)
        if not snapshot.snapshot_receipt_id or not snapshot.snapshot_content_digest:
            reasons.append(ArchitectDeterminationReason.MISSING_SNAPSHOT)
    if context_view is None:
        reasons.append(ArchitectDeterminationReason.MISSING_CONTEXT_VIEW)
    if evidence_bundle is None:
        reasons.append(ArchitectDeterminationReason.MISSING_EVIDENCE_BUNDLE)
    if fusion_gate is None or not fusion_gate.accepted or fusion_gate.status != FUSION_ASSIGNMENT_GATE_PASSED:
        reasons.append(ArchitectDeterminationReason.FUSION_GATE_NOT_PASSED)
    elif fusion_gate.determination_binding is None:
        reasons.append(ArchitectDeterminationReason.MISSING_DETERMINATION_BINDING)
    if report_collection is None or not report_collection.accepted:
        reasons.append(ArchitectDeterminationReason.REPORT_COLLECTION_NOT_ACCEPTED)
    else:
        if not report_collection.validation or not report_collection.validation.bundle:
            reasons.append(ArchitectDeterminationReason.REPORT_COLLECTION_NOT_ACCEPTED)
        if report_collection.report_count != len(reports):
            reasons.append(ArchitectDeterminationReason.REPORT_COUNT_MISMATCH)
    if not reports:
        reasons.append(ArchitectDeterminationReason.MISSING_AUDIT_REPORTS)
    for index, report in enumerate(reports):
        if not isinstance(report, Mapping):
            reasons.append(f"{ArchitectDeterminationReason.REPORT_MISSING_RECEIPT}:{index}")
            continue
        if not str(report.get("report_digest") or "").strip() or not str(report.get("assignment_id") or "").strip():
            reasons.append(f"{ArchitectDeterminationReason.REPORT_MISSING_RECEIPT}:{index}")
        evidence_refs = _normalize_text_list(report.get("evidence_refs"))
        if not evidence_refs:
            reasons.append(f"{ArchitectDeterminationReason.REPORT_MISSING_EVIDENCE}:{index}")
        if (
            report.get("repo_mutation_performed") is True
            or report.get("execution_performed") is True
            or report.get("openclaw_enqueue_performed") is True
        ):
            reasons.append(f"{ArchitectDeterminationReason.REPORT_CLAIMS_SIDE_EFFECT}:{index}")
    _validate_wsp15_allocation(wsp15_allocation_receipt, reasons)


def _validate_wsp15_allocation(allocation: Mapping[str, Any], reasons: list[str]) -> None:
    validation = validate_reddog_wsp15_allocation_receipt(allocation)
    if validation.accepted:
        return
    if validation.rejection_reasons == ("missing_wsp15_allocation",):
        reasons.append(ArchitectDeterminationReason.MISSING_WSP15_ALLOCATION)
    else:
        reasons.append(ArchitectDeterminationReason.MALFORMED_WSP15_ALLOCATION)


def _model_selection_binding(value: Any, reasons: list[str]) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        reasons.append(ArchitectDeterminationReason.MODEL_SELECTION_RECEIPT)
        return {}
    selection = _json_compatible_mapping(value)
    if not selection:
        reasons.append(ArchitectDeterminationReason.MODEL_SELECTION_RECEIPT)
        return {}
    try:
        receipt = rehydrate_model_selection_receipt(selection)
    except Exception:
        reasons.append(ArchitectDeterminationReason.MODEL_SELECTION_RECEIPT)
        return {}
    if (
        receipt.decision != SelectionDecision.SELECTED
        or not receipt.selected_model_ids
        or receipt.requirements.purpose != SelectionPurpose.PRODUCTION
    ):
        reasons.append(ArchitectDeterminationReason.MODEL_SELECTION_RECEIPT)
        return {}
    lead_model = ""
    panel_models: list[str] = []
    assignments = [asdict(item) for item in receipt.role_assignments]
    for assignment in assignments:
        role = str(assignment.get("role") or "")
        model_id = str(assignment.get("canonical_model_id") or "")
        if role == "principal" and model_id:
            lead_model = model_id
        elif role != "verifier" and model_id:
            panel_models.append(model_id)
    if not lead_model:
        lead_model = str(receipt.selected_model_ids[0])
        panel_models = [str(item) for item in receipt.selected_model_ids[1:]]
    return {
        "receipt_id": receipt.receipt_id,
        "digest": _digest(selection),
        "catalog_snapshot_id": receipt.catalog_snapshot_id,
        "task_family": receipt.requirements.task_family,
        "selection_mode": receipt.requirements.selection_mode.value,
        "purpose": receipt.requirements.purpose.value,
        "selected_model_ids": [str(item) for item in receipt.selected_model_ids],
        "role_assignments": assignments,
        "panel_topology_digest": receipt.panel_topology_digest,
        "lead_model": lead_model,
        "panel_models": panel_models,
    }


def _model_runtime_binding(
    value: Any,
    reasons: list[str],
    *,
    expected_surface: str,
) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        reasons.append(ArchitectDeterminationReason.MODEL_RUNTIME_BINDING_RECEIPT)
        return {}
    binding = _json_compatible_mapping(value)
    if not binding:
        reasons.append(ArchitectDeterminationReason.MODEL_RUNTIME_BINDING_RECEIPT)
        return {}
    try:
        receipt = rehydrate_model_runtime_binding_receipt(binding)
    except Exception:
        reasons.append(ArchitectDeterminationReason.MODEL_RUNTIME_BINDING_RECEIPT)
        return {}
    if (
        receipt.decision != ModelRuntimeBindingDecision.BOUND
        or not receipt.principal_model
        or receipt.runtime_surface != expected_surface
    ):
        reasons.append(ArchitectDeterminationReason.MODEL_RUNTIME_BINDING_RECEIPT)
        return {}
    payload = receipt.to_reddog_bridge_payload()
    return {
        "receipt_id": receipt.selection_receipt_id,
        "digest": _digest(binding),
        "catalog_snapshot_id": receipt.catalog_snapshot_id,
        "task_family": receipt.task_family,
        "purpose": SelectionPurpose.PRODUCTION.value,
        "selected_model_ids": [receipt.principal_model, *receipt.panel_models],
        "role_assignments": list(payload.get("model_role_bindings") or ()),
        "panel_topology_digest": "",
        "lead_model": str(payload.get("lead_model") or ""),
        "panel_models": [str(item) for item in payload.get("panel_models") or ()],
        "model_runtime_binding_receipt_id": receipt.receipt_id,
        "model_runtime_binding_digest": _digest(binding),
        "runtime_surface": receipt.runtime_surface,
    }


def _json_compatible_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    try:
        normalized = json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    except (TypeError, ValueError):
        return {}
    return normalized if isinstance(normalized, Mapping) else {}


def _runtime_model_topology(
    binding: Mapping[str, Any],
    *,
    default_lead: str,
    default_panel: Sequence[str],
) -> Mapping[str, Any]:
    selection = binding.get("model_selection")
    selection = selection if isinstance(selection, Mapping) else {}
    lead = str(selection.get("lead_model") or default_lead)
    raw_panel = selection.get("panel_models")
    panel = [str(item) for item in raw_panel] if isinstance(raw_panel, list) else list(default_panel)
    return {
        "lead_model": lead,
        "panel_models": tuple(item for item in panel if item),
        "model_selection_receipt_id": str(selection.get("receipt_id") or ""),
        "model_runtime_binding_receipt_id": str(selection.get("model_runtime_binding_receipt_id") or ""),
    }


def _parse_model_output(content: str) -> Mapping[str, Any]:
    text = str(content or "").strip()
    if not text:
        return {}
    candidates = [text]
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            cleaned = part.strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
            if cleaned.startswith("{") and cleaned.endswith("}"):
                candidates.insert(0, cleaned)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, Mapping):
            return parsed
    return {}


def _validate_model_output(
    output: Mapping[str, Any],
    *,
    reports: Sequence[Mapping[str, Any]],
    wsp15_allocation_receipt_id: Optional[str],
    output_reasons: list[str],
) -> None:
    if not output:
        output_reasons.append(ArchitectDeterminationReason.INVALID_MODEL_OUTPUT)
        return
    action = str(output.get("action") or "").strip().upper()
    next_slice = str(output.get("next_slice_name") or "").strip()
    summary = str(output.get("summary") or "").strip()
    evidence_refs = _normalize_text_list(output.get("evidence_refs"))
    model_allocation_id = str(output.get("wsp15_allocation_receipt_id") or "").strip()
    if action not in ALLOWED_ACTIONS:
        output_reasons.append(ArchitectDeterminationReason.INVALID_MODEL_OUTPUT)
    if action in {ACTION_FIX, ACTION_RESEARCH_MORE, ACTION_REVISE} and not _valid_slice_name(next_slice):
        output_reasons.append(ArchitectDeterminationReason.INVALID_MODEL_OUTPUT)
    if action == ACTION_STOP and next_slice:
        output_reasons.append(ArchitectDeterminationReason.INVALID_MODEL_OUTPUT)
    if not summary:
        output_reasons.append(ArchitectDeterminationReason.INVALID_MODEL_OUTPUT)
    if not evidence_refs:
        output_reasons.append(ArchitectDeterminationReason.INVALID_MODEL_OUTPUT)
    report_refs = set(_all_report_evidence_refs(reports))
    if evidence_refs and not set(evidence_refs).issubset(report_refs):
        output_reasons.append(ArchitectDeterminationReason.INVALID_MODEL_OUTPUT)
    if not model_allocation_id or model_allocation_id != wsp15_allocation_receipt_id:
        output_reasons.append(ArchitectDeterminationReason.WSP15_RECEIPT_MISMATCH)


def _fusion_quorum_passed(review_packet: Mapping[str, Any]) -> bool:
    quorum = review_packet.get("fusion_panel_quorum")
    return isinstance(quorum, Mapping) and quorum.get("passed") is True


def _build_architect_prompt(
    *,
    snapshot: OperationalContextSnapshot,
    report_collection: ReadOnlyAuditReportCollectionResult,
    reports: Sequence[Mapping[str, Any]],
    wsp15_allocation_receipt: Mapping[str, Any],
) -> str:
    payload = {
        "task": "Return one backend RedDog architect determination as strict JSON only.",
        "allowed_actions": list(ALLOWED_ACTIONS),
        "required_json_fields": [
            "action",
            "next_slice_name",
            "summary",
            "decision_reasons",
            "evidence_refs",
            "wsp15_allocation_receipt_id",
        ],
        "rules": [
            "Use FIX only when exactly one next implementation slice should be queued.",
            "Use RESEARCH_MORE when evidence is insufficient.",
            "Use REVISE when prior work should be corrected before new implementation.",
            "Use STOP when no next work should be queued.",
            "Use only evidence_refs present in the supplied audit reports.",
            "Echo the supplied WSP15 allocation receipt id exactly.",
        ],
        "snapshot_receipt_id": snapshot.snapshot_receipt_id,
        "snapshot_content_digest": snapshot.snapshot_content_digest,
        "report_collection": {
            "status": report_collection.status,
            "report_count": report_collection.report_count,
            "bundle_id": _report_bundle_id(report_collection),
        },
        "wsp15_allocation_receipt_id": wsp15_allocation_receipt.get("receipt_id"),
        "reports": [_report_prompt_view(report) for report in reports],
    }
    return _budgeted_canonical_json(payload, max_chars=DEFAULT_MAX_PROMPT_CHARS)


def _build_architect_context(
    *,
    context_view: ContextView,
    evidence_bundle: EvidenceBundle,
    reports: Sequence[Mapping[str, Any]],
) -> str:
    payload = {
        "context_view_id": context_view.context_view_id,
        "snapshot_receipt_id": context_view.snapshot_receipt_id,
        "evidence_bundle_id": evidence_bundle.evidence_bundle_id,
        "context_view_text": _bound_text(context_view.text, 6000),
        "audit_reports": [_report_prompt_view(report) for report in reports],
    }
    return _budgeted_canonical_json(payload, max_chars=DEFAULT_MAX_PROMPT_CHARS)


def _report_prompt_view(report: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        "assignment_id": report.get("assignment_id"),
        "lane_id": report.get("lane_id"),
        "summary": _bound_text(report.get("summary"), 1000),
        "report_digest": report.get("report_digest"),
        "evidence_refs": list(_normalize_text_list(report.get("evidence_refs")))[:32],
        "findings": _bounded_findings(report.get("findings")),
    }


def _queue_candidate(
    *,
    source_determination_receipt_id: str,
    next_slice_name: str,
    snapshot: OperationalContextSnapshot,
    report_bundle_id: Optional[str],
    wsp15_allocation_receipt: Mapping[str, Any],
) -> ArchitectQueueCandidate:
    payload = {
        "source_determination_receipt_id": source_determination_receipt_id,
        "slice_id": next_slice_name,
        "snapshot_receipt_id": snapshot.snapshot_receipt_id,
        "report_bundle_id": report_bundle_id,
        "wsp15_allocation_receipt_id": wsp15_allocation_receipt.get("receipt_id"),
    }
    return ArchitectQueueCandidate(
        schema_version=ARCHITECT_QUEUE_CANDIDATE_SCHEMA_VERSION,
        queue_candidate_id=_digest(payload),
        source_determination_receipt_id=source_determination_receipt_id,
        slice_id=next_slice_name,
        status="CANDIDATE",
        evidence_refs=(
            f"architect_determination:{source_determination_receipt_id}",
            f"snapshot:{snapshot.snapshot_receipt_id}",
            f"report_bundle:{report_bundle_id}",
            f"wsp15_allocation:{wsp15_allocation_receipt.get('receipt_id')}",
        ),
        wsp15_allocation_receipt=dict(wsp15_allocation_receipt),
    )


def _receipt(
    *,
    accepted: bool,
    action: str,
    next_slice_name: Optional[str],
    summary: str,
    snapshot: OperationalContextSnapshot | None,
    context_view: ContextView | None,
    evidence_bundle: EvidenceBundle | None,
    report_bundle_id: Optional[str],
    report_count: int,
    report_digests: Sequence[str],
    model_result: ArchitectModelResult | None,
    allocation_receipt_id: Optional[str],
    allocation_digest: Optional[str],
    cycle_id: str,
    decision_reasons: Sequence[str],
    rejection_reasons: Sequence[str],
    model_selection_receipt_id: Optional[str] = None,
    model_selection_digest: Optional[str] = None,
    model_runtime_binding_receipt_id: Optional[str] = None,
    model_runtime_binding_digest: Optional[str] = None,
    queue_candidate: ArchitectQueueCandidate | None = None,
    determination_receipt_id: Optional[str] = None,
) -> ArchitectDeterminationReceipt:
    payload = {
        "schema_version": ARCHITECT_DETERMINATION_SCHEMA_VERSION,
        "accepted": accepted,
        "action": action,
        "next_slice_name": next_slice_name,
        "summary": summary,
        "cycle_id": cycle_id,
        "snapshot_receipt_id": snapshot.snapshot_receipt_id if snapshot else None,
        "context_view_id": context_view.context_view_id if context_view else None,
        "evidence_bundle_id": evidence_bundle.evidence_bundle_id if evidence_bundle else None,
        "report_bundle_id": report_bundle_id,
        "report_count": report_count,
        "audit_report_digests": tuple(report_digests),
        "model_result_digest": model_result.model_result_digest if model_result else None,
        "model_receipt_id": model_result.model_receipt_id if model_result else None,
        "model_selection_receipt_id": model_selection_receipt_id,
        "model_selection_digest": model_selection_digest,
        "model_runtime_binding_receipt_id": model_runtime_binding_receipt_id,
        "model_runtime_binding_digest": model_runtime_binding_digest,
        "fusion_quorum_passed": _fusion_quorum_passed(model_result.review_packet) if model_result else False,
        "wsp15_allocation_receipt_id": allocation_receipt_id,
        "wsp15_allocation_digest": allocation_digest,
        "queue_candidate_id": queue_candidate.queue_candidate_id if queue_candidate else None,
        "decision_reasons": tuple(decision_reasons),
        "rejection_reasons": tuple(rejection_reasons),
    }
    receipt_id = determination_receipt_id or _digest(payload)
    return ArchitectDeterminationReceipt(
        schema_version=ARCHITECT_DETERMINATION_SCHEMA_VERSION,
        determination_receipt_id=receipt_id,
        cycle_id=cycle_id,
        accepted=accepted,
        status=ARCHITECT_DETERMINATION_ACCEPT if accepted else ARCHITECT_DETERMINATION_REJECT,
        action=action,
        next_slice_name=next_slice_name,
        summary=summary,
        snapshot_receipt_id=snapshot.snapshot_receipt_id if snapshot else None,
        snapshot_content_digest=snapshot.snapshot_content_digest if snapshot else None,
        context_view_id=context_view.context_view_id if context_view else None,
        evidence_bundle_id=evidence_bundle.evidence_bundle_id if evidence_bundle else None,
        report_bundle_id=report_bundle_id,
        report_count=report_count,
        audit_report_digests=tuple(report_digests),
        model_result_digest=model_result.model_result_digest if model_result else None,
        model_receipt_id=model_result.model_receipt_id if model_result else None,
        model_selection_receipt_id=model_selection_receipt_id,
        model_selection_digest=model_selection_digest,
        model_runtime_binding_receipt_id=model_runtime_binding_receipt_id,
        model_runtime_binding_digest=model_runtime_binding_digest,
        fusion_quorum_passed=_fusion_quorum_passed(model_result.review_packet) if model_result else False,
        wsp15_allocation_receipt_id=allocation_receipt_id,
        wsp15_allocation_digest=allocation_digest,
        queue_candidate=queue_candidate,
        decision_reasons=tuple(decision_reasons),
        rejection_reasons=tuple(rejection_reasons),
    )


def _persist_receipt(
    receipt: ArchitectDeterminationReceipt,
    *,
    writer: ArchitectDeterminationStore,
    now_iso: str,
) -> ArchitectDeterminationPersistResult:
    if not receipt.accepted:
        return _persist_rejected(receipt)
    record = ArchitectDeterminationRecord(
        determination_receipt_id=receipt.determination_receipt_id,
        cycle_id=receipt.cycle_id,
        action=receipt.action,
        next_slice_name=receipt.next_slice_name,
        determination=receipt.to_dict(),
        stored_at=now_iso,
    )
    try:
        write = writer.store_architect_determination(record)
    except Exception:
        write = {"ok": False, "reason": "store_exception"}
    if not isinstance(write, Mapping) or write.get("ok") is not True:
        return ArchitectDeterminationPersistResult(
            accepted=False,
            status=ARCHITECT_DETERMINATION_REJECT,
            determination_receipt_id=receipt.determination_receipt_id,
            cycle_id=receipt.cycle_id,
            stored=False,
            idempotent=False,
            rejection_reasons=(ArchitectDeterminationReason.STORE_REJECTED,),
        )
    return ArchitectDeterminationPersistResult(
        accepted=True,
        status=ARCHITECT_DETERMINATION_ACCEPT,
        determination_receipt_id=receipt.determination_receipt_id,
        cycle_id=receipt.cycle_id,
        stored=bool(write.get("stored")),
        idempotent=bool(write.get("idempotent")),
        rejection_reasons=(),
    )


def _persist_rejected(receipt: ArchitectDeterminationReceipt) -> ArchitectDeterminationPersistResult:
    return ArchitectDeterminationPersistResult(
        accepted=False,
        status=ARCHITECT_DETERMINATION_REJECT,
        determination_receipt_id=receipt.determination_receipt_id,
        cycle_id=receipt.cycle_id,
        stored=False,
        idempotent=False,
        rejection_reasons=receipt.rejection_reasons,
    )


def _result(
    *,
    receipt: ArchitectDeterminationReceipt,
    persist_result: ArchitectDeterminationPersistResult,
) -> BackendArchitectDeterminationResult:
    accepted = receipt.accepted and persist_result.accepted
    reasons = receipt.rejection_reasons or persist_result.rejection_reasons
    return BackendArchitectDeterminationResult(
        accepted=accepted,
        status=ARCHITECT_DETERMINATION_ACCEPT if accepted else ARCHITECT_DETERMINATION_REJECT,
        receipt=receipt,
        persist_result=persist_result,
        queue_candidate_count=1 if receipt.queue_candidate else 0,
        rejection_reasons=tuple(reasons),
    )


def _model_result_reject(reason: str) -> ArchitectModelResult:
    normalized = str(reason or ArchitectDeterminationReason.MODEL_FAILURE)
    return ArchitectModelResult(
        ok=False,
        status="MODEL_REJECT",
        content="",
        model_receipt_id=None,
        model_result_digest=_digest({"ok": False, "reason": normalized}),
        review_packet={},
        made_network_call=False,
        rejection_reasons=(normalized,),
    )


def _load_foundups_fusion_runner():
    try:
        from scripts.advisory_model_once import _run_foundups_fusion

        return _run_foundups_fusion
    except Exception:
        bridge_path = Path(__file__).resolve().parents[4] / "scripts" / "advisory_model_once.py"
        spec = importlib.util.spec_from_file_location("reddog_advisory_model_once_backend", bridge_path)
        if spec is None or spec.loader is None:
            raise ImportError("advisory_model_once_unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        runner = getattr(module, "_run_foundups_fusion", None)
        if not callable(runner):
            raise ImportError("foundups_fusion_runner_unavailable")
        return runner


def _cycle_id(
    *,
    snapshot: OperationalContextSnapshot | None,
    report_bundle_id: Optional[str],
    report_digests: Sequence[str],
    wsp15_allocation_digest: Optional[str],
    model_selection_digest: Optional[str],
) -> Optional[str]:
    if snapshot is None or not report_bundle_id or not wsp15_allocation_digest:
        return None
    return _digest(
        {
            "snapshot_receipt_id": snapshot.snapshot_receipt_id,
            "snapshot_content_digest": snapshot.snapshot_content_digest,
            "report_bundle_id": report_bundle_id,
            "report_digests": tuple(report_digests),
            "wsp15_allocation_digest": wsp15_allocation_digest,
            "model_selection_digest": model_selection_digest,
        }
    )


def _report_bundle_id(collection: ReadOnlyAuditReportCollectionResult | None) -> Optional[str]:
    if not collection or not collection.validation or not collection.validation.bundle:
        return None
    return collection.validation.bundle.bundle_id


def _report_count(collection: ReadOnlyAuditReportCollectionResult | None) -> int:
    return int(collection.report_count) if collection else 0


def _report_digests(reports: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    digests = []
    for report in reports:
        if isinstance(report, Mapping):
            digest = str(report.get("report_digest") or "").strip()
            digests.append(digest or _digest(report))
    return tuple(sorted(digests))


def _all_report_evidence_refs(reports: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    refs: list[str] = []
    for report in reports:
        if isinstance(report, Mapping):
            refs.extend(_normalize_text_list(report.get("evidence_refs")))
    return tuple(dict.fromkeys(refs))


def _normalize_text_list(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return ()
    return tuple(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value).strip()))


def _valid_slice_name(value: str) -> bool:
    text = str(value or "").strip()
    return bool(text) and text == text.upper() and all(ch.isalnum() or ch == "_" for ch in text)


def _snapshot_expired(valid_until: str, now_iso: str) -> bool:
    try:
        valid = datetime.fromisoformat(str(valid_until))
        now = datetime.fromisoformat(str(now_iso))
    except ValueError:
        return True
    if valid.tzinfo is None:
        valid = valid.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return valid <= now


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _budgeted_canonical_json(value: Mapping[str, Any], *, max_chars: int) -> str:
    encoded = _canonical_json(value)
    if len(encoded) > max_chars:
        raise ValueError("canonical_json_budget_exceeded")
    return encoded


def _bound_text(value: Any, max_chars: int) -> str:
    text = str(value or "")
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _bounded_findings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    bounded: list[Mapping[str, Any]] = []
    for item in value[:12]:
        if not isinstance(item, Mapping):
            continue
        bounded.append(
            {
                "finding_id": _bound_text(item.get("finding_id"), 160),
                "claim": _bound_text(item.get("claim"), 800),
                "wsp97_label": _bound_text(item.get("wsp97_label"), 64),
                "recommended_action": _bound_text(item.get("recommended_action"), 64),
                "wsp15_priority": _bound_text(item.get("wsp15_priority"), 16),
                "severity": _bound_text(item.get("severity"), 32),
                "next_slice_name": _bound_text(item.get("next_slice_name"), 160),
                "evidence_refs": list(_normalize_text_list(item.get("evidence_refs")))[:16],
            }
        )
    return bounded


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


__all__ = [
    "ACTION_FIX",
    "ACTION_RESEARCH_MORE",
    "ACTION_REVISE",
    "ACTION_STOP",
    "ALLOWED_ACTIONS",
    "ARCHITECT_DETERMINATION_ACCEPT",
    "ARCHITECT_DETERMINATION_REJECT",
    "ARCHITECT_DETERMINATION_SCHEMA_VERSION",
    "ArchitectDeterminationPersistResult",
    "ArchitectDeterminationReason",
    "ArchitectDeterminationReceipt",
    "ArchitectDeterminationStore",
    "ArchitectModelResult",
    "ArchitectModelRunner",
    "ArchitectQueueCandidate",
    "AgentDbArchitectDeterminationStore",
    "BackendArchitectDeterminationResult",
    "ENV_ARCHITECT_RUNTIME_MODE",
    "FoundupsFusionArchitectModelRunner",
    "InMemoryArchitectDeterminationStore",
    "RUNTIME_MODE_FOUNDUPS_FUSION",
    "run_reddog_backend_architect_determination_runtime",
]
