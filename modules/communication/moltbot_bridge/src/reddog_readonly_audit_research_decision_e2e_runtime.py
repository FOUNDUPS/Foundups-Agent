"""End-to-end resident RedDog read-only audit and decision cycle.

Slice: REDDOG_READONLY_AUDIT_RESEARCH_DECISION_E2E_PHASE1

This module composes the existing read-only operational bootstrap, AgentDB
task enqueue seam, read-only 0102 audit executor, report persistence,
report collection, and backend architect determination runtime into one
explicit resident-cycle call.

It does not execute shell commands, mutate repository files, create worktrees,
dispatch Hermes/WRE coding workers, create PRs, promote PatternMemory, or
re-index HoloIndex. It may publish and execute read-only audit task records
when the caller explicitly invokes this runtime.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Protocol, Sequence

from holo_index.freshness_receipt import HoloIndexFreshnessReceipt
from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ArchitectDeterminationStore,
    ArchitectModelRunner,
    BackendArchitectDeterminationResult,
)
from modules.communication.moltbot_bridge.src.reddog_main_readonly_operational_bootstrap import (
    DEFAULT_BOOTSTRAP_CHANGED_PATHS,
    DEFAULT_BOOTSTRAP_READ_TARGETS,
    REDDOG_MAIN_BOOTSTRAP_READY,
    RedDogMainReadonlyBootstrapResult,
    run_reddog_main_readonly_operational_bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
    AgentDbReadOnlyAuditTaskWriter,
    ReadOnlyAuditSwarmEnqueueReceipt,
    ReadOnlyAuditTaskSpec,
    ReadOnlyAuditTaskWriter,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_runtime import (
    DEFAULT_AUDIT_LANES,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime import (
    ExternalResearchRetriever,
    ReadOnlyEvidenceQueryAdapter,
    RepoAuditModelRunner,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_decision_persistence import (
    ReadOnlyAuditDecisionStore,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_report_collection import (
    AgentDbReadOnlyAuditReportStore,
    ReadOnlyAuditReportPersistResult,
    ReadOnlyAuditReportStore,
    persist_reddog_readonly_audit_task_report,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_task_executor import (
    ReadOnlyAuditTaskExecutionResult,
    execute_reddog_readonly_audit_task,
)


READONLY_AUDIT_RESEARCH_DECISION_E2E_ACCEPT = "READONLY_AUDIT_RESEARCH_DECISION_E2E_ACCEPT"
READONLY_AUDIT_RESEARCH_DECISION_E2E_REJECT = "READONLY_AUDIT_RESEARCH_DECISION_E2E_REJECT"


class ReadOnlyAuditResearchDecisionE2EReason:
    BOOTSTRAP_REJECTED = "REJECT_E2E_BOOTSTRAP_REJECTED"
    ENQUEUE_NOT_ACCEPTED = "REJECT_E2E_ENQUEUE_NOT_ACCEPTED"
    NO_CAPTURED_TASKS = "REJECT_E2E_NO_CAPTURED_TASKS"
    TASK_EXECUTION_REJECTED = "REJECT_E2E_TASK_EXECUTION_REJECTED"
    REPORT_PERSIST_REJECTED = "REJECT_E2E_REPORT_PERSIST_REJECTED"
    FINAL_BOOTSTRAP_REJECTED = "REJECT_E2E_FINAL_BOOTSTRAP_REJECTED"
    FINAL_SWARM_MISMATCH = "REJECT_E2E_FINAL_SWARM_MISMATCH"
    ARCHITECT_DETERMINATION_MISSING = "REJECT_E2E_ARCHITECT_DETERMINATION_MISSING"


class ReadOnlyAuditTaskExecutor(Protocol):
    def execute_readonly_audit_task(
        self,
        *,
        task: ReadOnlyAuditTaskSpec,
        repo_root: Path,
        model_runner: RepoAuditModelRunner | None,
        holoindex_adapter: ReadOnlyEvidenceQueryAdapter | None,
        codeindex_adapter: ReadOnlyEvidenceQueryAdapter | None,
        external_research_retriever: ExternalResearchRetriever | None,
        timeout_seconds: int,
    ) -> ReadOnlyAuditTaskExecutionResult: ...


@dataclass(frozen=True)
class DirectReadOnlyAuditTaskExecutor:
    """In-process executor for already planned read-only audit tasks."""

    def execute_readonly_audit_task(
        self,
        *,
        task: ReadOnlyAuditTaskSpec,
        repo_root: Path,
        model_runner: RepoAuditModelRunner | None,
        holoindex_adapter: ReadOnlyEvidenceQueryAdapter | None,
        codeindex_adapter: ReadOnlyEvidenceQueryAdapter | None,
        external_research_retriever: ExternalResearchRetriever | None,
        timeout_seconds: int,
    ) -> ReadOnlyAuditTaskExecutionResult:
        return execute_reddog_readonly_audit_task(
            task_context=task.context,
            repo_root=repo_root,
            task_id=task.task_id,
            model_runner=model_runner,
            holoindex_adapter=holoindex_adapter,
            codeindex_adapter=codeindex_adapter,
            external_research_retriever=external_research_retriever,
            timeout_seconds=timeout_seconds,
        )


@dataclass(frozen=True)
class ReadOnlyAuditTaskRunRecord:
    task_id: str
    assignment_id: str
    lane_id: str
    accepted: bool
    report_digest: Optional[str]
    persist_accepted: bool
    rejection_reasons: tuple[str, ...]
    persist_rejection_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RedDogReadonlyAuditResearchDecisionE2EResult:
    accepted: bool
    status: str
    initial_bootstrap: RedDogMainReadonlyBootstrapResult
    final_bootstrap: Optional[RedDogMainReadonlyBootstrapResult]
    task_runs: tuple[ReadOnlyAuditTaskRunRecord, ...]
    architect_result: Optional[BackendArchitectDeterminationResult]
    rejection_reasons: tuple[str, ...]
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_worktree_operation_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_promotion_performed: bool = True
    no_live_foundup_enqueue_performed: bool = True
    coding_worker_spawned: bool = False
    readonly_audit_tasks_enqueued: bool = False
    readonly_audit_tasks_executed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "initial_bootstrap": self.initial_bootstrap.to_dict(),
            "final_bootstrap": self.final_bootstrap.to_dict() if self.final_bootstrap else None,
            "task_runs": [item.to_dict() for item in self.task_runs],
            "architect_result": self.architect_result.to_dict() if self.architect_result else None,
            "rejection_reasons": list(self.rejection_reasons),
            "no_shell_command_executed": self.no_shell_command_executed,
            "no_repo_mutation_performed": self.no_repo_mutation_performed,
            "no_holoindex_reindex_performed": self.no_holoindex_reindex_performed,
            "no_hermes_dispatch_performed": self.no_hermes_dispatch_performed,
            "no_worktree_operation_performed": self.no_worktree_operation_performed,
            "no_pr_created": self.no_pr_created,
            "no_pattern_memory_promotion_performed": self.no_pattern_memory_promotion_performed,
            "no_live_foundup_enqueue_performed": self.no_live_foundup_enqueue_performed,
            "coding_worker_spawned": self.coding_worker_spawned,
            "readonly_audit_tasks_enqueued": self.readonly_audit_tasks_enqueued,
            "readonly_audit_tasks_executed": self.readonly_audit_tasks_executed,
        }


class _CapturingReadOnlyAuditTaskWriter:
    def __init__(self, delegate: ReadOnlyAuditTaskWriter | None) -> None:
        self.delegate = delegate
        self.tasks: tuple[ReadOnlyAuditTaskSpec, ...] = ()
        self.receipt: ReadOnlyAuditSwarmEnqueueReceipt | None = None

    def enqueue_readonly_audit_tasks(
        self,
        tasks: Sequence[ReadOnlyAuditTaskSpec],
        receipt: ReadOnlyAuditSwarmEnqueueReceipt,
    ) -> Mapping[str, Any]:
        self.tasks = tuple(tasks)
        self.receipt = receipt
        if self.delegate is None:
            return {"ok": True, "created_task_ids": [task.task_id for task in self.tasks]}
        return self.delegate.enqueue_readonly_audit_tasks(self.tasks, receipt)


def run_reddog_readonly_audit_research_decision_e2e(
    *,
    repo_root: Path | str,
    work_state_path: Path | str | None = None,
    holoindex_receipt_path: Path | str | None = None,
    holoindex_ssd_path: Path | str | None = None,
    changed_paths: Sequence[str] = DEFAULT_BOOTSTRAP_CHANGED_PATHS,
    allowed_read_targets: Sequence[str] = DEFAULT_BOOTSTRAP_READ_TARGETS,
    requested_operation: str = "main_startup_readonly_operational_audit",
    prompt_text: str = "main.py read-only RedDog operational bootstrap",
    now_iso: str | None = None,
    repo_state_override: Mapping[str, Any] | None = None,
    work_state_snapshot_override: Mapping[str, Any] | None = None,
    holoindex_receipt_override: HoloIndexFreshnessReceipt | Mapping[str, Any] | None = None,
    audit_lanes: Sequence[str] = DEFAULT_AUDIT_LANES,
    enqueue_writer: ReadOnlyAuditTaskWriter | None = None,
    report_store: ReadOnlyAuditReportStore | None = None,
    decision_store: ReadOnlyAuditDecisionStore | None = None,
    architect_model_runner: ArchitectModelRunner | None = None,
    architect_model_runtime_binding_receipt: Mapping[str, Any] | None = None,
    architect_determination_store: ArchitectDeterminationStore | None = None,
    audit_model_runner: RepoAuditModelRunner | None = None,
    audit_model_runtime_binding_receipt: Mapping[str, Any] | None = None,
    holoindex_adapter: ReadOnlyEvidenceQueryAdapter | None = None,
    codeindex_adapter: ReadOnlyEvidenceQueryAdapter | None = None,
    external_research_retriever: ExternalResearchRetriever | None = None,
    task_executor: ReadOnlyAuditTaskExecutor | None = None,
    timeout_seconds: int = 60,
) -> RedDogReadonlyAuditResearchDecisionE2EResult:
    """Run one explicit read-only audit -> research -> decision cycle."""

    root = Path(repo_root).resolve()
    report_writer = report_store if report_store is not None else AgentDbReadOnlyAuditReportStore()
    delegate_writer = enqueue_writer if enqueue_writer is not None else AgentDbReadOnlyAuditTaskWriter()
    capture_writer = _CapturingReadOnlyAuditTaskWriter(delegate_writer)
    executor = task_executor if task_executor is not None else DirectReadOnlyAuditTaskExecutor()

    initial = run_reddog_main_readonly_operational_bootstrap(
        repo_root=root,
        work_state_path=work_state_path,
        holoindex_receipt_path=holoindex_receipt_path,
        holoindex_ssd_path=holoindex_ssd_path,
        changed_paths=changed_paths,
        allowed_read_targets=allowed_read_targets,
        requested_operation=requested_operation,
        prompt_text=prompt_text,
        now_iso=now_iso,
        repo_state_override=repo_state_override,
        work_state_snapshot_override=work_state_snapshot_override,
        holoindex_receipt_override=holoindex_receipt_override,
        audit_lanes=audit_lanes,
        enqueue_readonly_audit_tasks=True,
        enqueue_writer=capture_writer,
        audit_model_runtime_binding_receipt=audit_model_runtime_binding_receipt,
        require_audit_model_runtime_binding=True,
        architect_model_runtime_binding_receipt_override=(
            architect_model_runtime_binding_receipt
        ),
    )
    if not initial.ready or initial.status != REDDOG_MAIN_BOOTSTRAP_READY:
        return _result(
            accepted=False,
            initial=initial,
            final=None,
            task_runs=(),
            architect_result=None,
            reasons=(ReadOnlyAuditResearchDecisionE2EReason.BOOTSTRAP_REJECTED, *initial.rejection_reasons),
        )
    if initial.enqueue_decision is None or initial.enqueue_rejection_reasons:
        return _result(
            accepted=False,
            initial=initial,
            final=None,
            task_runs=(),
            architect_result=None,
            reasons=(
                ReadOnlyAuditResearchDecisionE2EReason.ENQUEUE_NOT_ACCEPTED,
                *initial.enqueue_rejection_reasons,
            ),
        )
    if not capture_writer.tasks:
        return _result(
            accepted=False,
            initial=initial,
            final=None,
            task_runs=(),
            architect_result=None,
            reasons=(ReadOnlyAuditResearchDecisionE2EReason.NO_CAPTURED_TASKS,),
        )

    task_runs: list[ReadOnlyAuditTaskRunRecord] = []
    for task in capture_writer.tasks:
        run_result = executor.execute_readonly_audit_task(
            task=task,
            repo_root=root,
            model_runner=audit_model_runner,
            holoindex_adapter=holoindex_adapter,
            codeindex_adapter=codeindex_adapter,
            external_research_retriever=external_research_retriever,
            timeout_seconds=timeout_seconds,
        )
        persist_result: ReadOnlyAuditReportPersistResult | None = None
        if run_result.accepted:
            persist_result = persist_reddog_readonly_audit_task_report(
                task_id=task.task_id,
                task_context=task.context,
                task_result={
                    "ok": True,
                    "executor": "reddog:readonly_audit",
                    "structured_result": run_result.to_dict(),
                },
                store=report_writer,
            )
        record = _task_record(task=task, run_result=run_result, persist_result=persist_result)
        task_runs.append(record)
        if not run_result.accepted:
            return _result(
                accepted=False,
                initial=initial,
                final=None,
                task_runs=tuple(task_runs),
                architect_result=None,
                reasons=(
                    ReadOnlyAuditResearchDecisionE2EReason.TASK_EXECUTION_REJECTED,
                    *run_result.rejection_reasons,
                ),
            )
        if persist_result is None or not persist_result.accepted:
            return _result(
                accepted=False,
                initial=initial,
                final=None,
                task_runs=tuple(task_runs),
                architect_result=None,
                reasons=(
                    ReadOnlyAuditResearchDecisionE2EReason.REPORT_PERSIST_REJECTED,
                    *(persist_result.rejection_reasons if persist_result else ()),
                ),
            )

    final = run_reddog_main_readonly_operational_bootstrap(
        repo_root=root,
        work_state_path=work_state_path,
        holoindex_receipt_path=holoindex_receipt_path,
        holoindex_ssd_path=holoindex_ssd_path,
        changed_paths=changed_paths,
        allowed_read_targets=allowed_read_targets,
        requested_operation=requested_operation,
        prompt_text=prompt_text,
        now_iso=now_iso,
        repo_state_override=repo_state_override,
        work_state_snapshot_override=work_state_snapshot_override,
        holoindex_receipt_override=holoindex_receipt_override,
        audit_lanes=audit_lanes,
        audit_model_runtime_binding_receipt=audit_model_runtime_binding_receipt,
        require_audit_model_runtime_binding=True,
        collect_readonly_audit_reports=True,
        report_store=report_writer,
        persist_readonly_audit_decision=True,
        decision_store=decision_store,
        run_backend_architect_determination=True,
        architect_model_runner=architect_model_runner,
        architect_model_runtime_binding_receipt_override=architect_model_runtime_binding_receipt,
        architect_determination_store=architect_determination_store,
    )
    if final.swarm_id != initial.swarm_id:
        return _result(
            accepted=False,
            initial=initial,
            final=final,
            task_runs=tuple(task_runs),
            architect_result=None,
            reasons=(ReadOnlyAuditResearchDecisionE2EReason.FINAL_SWARM_MISMATCH,),
        )
    if not final.ready:
        return _result(
            accepted=False,
            initial=initial,
            final=final,
            task_runs=tuple(task_runs),
            architect_result=None,
            reasons=(ReadOnlyAuditResearchDecisionE2EReason.FINAL_BOOTSTRAP_REJECTED, *final.rejection_reasons),
        )
    if not final.backend_architect_determination_attempted or not final.backend_architect_determination_id:
        return _result(
            accepted=False,
            initial=initial,
            final=final,
            task_runs=tuple(task_runs),
            architect_result=None,
            reasons=(ReadOnlyAuditResearchDecisionE2EReason.ARCHITECT_DETERMINATION_MISSING,),
        )

    architect_result = None
    if final.backend_architect_determination_status:
        # The bootstrap result intentionally exposes only safe summary fields.
        # Preserve a None architect_result here rather than reloading store state.
        architect_result = None

    return _result(
        accepted=True,
        initial=initial,
        final=final,
        task_runs=tuple(task_runs),
        architect_result=architect_result,
        reasons=(),
    )


def _task_record(
    *,
    task: ReadOnlyAuditTaskSpec,
    run_result: ReadOnlyAuditTaskExecutionResult,
    persist_result: ReadOnlyAuditReportPersistResult | None,
) -> ReadOnlyAuditTaskRunRecord:
    assignment = task.context.get("assignment") if isinstance(task.context, Mapping) else {}
    report = run_result.report if isinstance(run_result.report, Mapping) else {}
    return ReadOnlyAuditTaskRunRecord(
        task_id=task.task_id,
        assignment_id=str(assignment.get("assignment_id") or ""),
        lane_id=str(assignment.get("lane_id") or ""),
        accepted=run_result.accepted,
        report_digest=str(report.get("report_digest") or "").strip() or None,
        persist_accepted=bool(persist_result and persist_result.accepted),
        rejection_reasons=run_result.rejection_reasons,
        persist_rejection_reasons=persist_result.rejection_reasons if persist_result else (),
    )


def _result(
    *,
    accepted: bool,
    initial: RedDogMainReadonlyBootstrapResult,
    final: RedDogMainReadonlyBootstrapResult | None,
    task_runs: Sequence[ReadOnlyAuditTaskRunRecord],
    architect_result: BackendArchitectDeterminationResult | None,
    reasons: Sequence[str],
) -> RedDogReadonlyAuditResearchDecisionE2EResult:
    return RedDogReadonlyAuditResearchDecisionE2EResult(
        accepted=accepted,
        status=(
            READONLY_AUDIT_RESEARCH_DECISION_E2E_ACCEPT
            if accepted
            else READONLY_AUDIT_RESEARCH_DECISION_E2E_REJECT
        ),
        initial_bootstrap=initial,
        final_bootstrap=final,
        task_runs=tuple(task_runs),
        architect_result=architect_result,
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons if str(reason).strip())),
        readonly_audit_tasks_enqueued=initial.enqueue_task_count > 0,
        readonly_audit_tasks_executed=bool(task_runs) and all(item.accepted for item in task_runs),
    )


__all__ = [
    "READONLY_AUDIT_RESEARCH_DECISION_E2E_ACCEPT",
    "READONLY_AUDIT_RESEARCH_DECISION_E2E_REJECT",
    "DirectReadOnlyAuditTaskExecutor",
    "ReadOnlyAuditResearchDecisionE2EReason",
    "ReadOnlyAuditTaskExecutor",
    "ReadOnlyAuditTaskRunRecord",
    "RedDogReadonlyAuditResearchDecisionE2EResult",
    "run_reddog_readonly_audit_research_decision_e2e",
]
