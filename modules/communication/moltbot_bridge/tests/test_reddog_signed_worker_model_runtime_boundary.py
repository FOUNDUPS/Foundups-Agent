"""Focused signed-worker model-runtime boundary regressions."""

from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    canonical_model_runtime_binding_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_dispatch_task_executor import (
    SIGNED_WORKER_DISPATCH_TASK_EXECUTOR_ACCEPT,
    SignedWorkerDispatchTaskExecutorReason,
    execute_reddog_signed_worker_dispatch_task,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_0102_readonly_review_binding import (
    SIGNED_0102_READONLY_REVIEW_BINDING_ACCEPT,
    Signed0102ReadOnlyReviewBindingReason,
    Signed0102ReadOnlyReviewRunner,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    publish_bound_worker_dispatch,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_worker_dispatch_task_executor import (
    _CollectingWriter,
    _EchoEvidenceModelRunner,
    _FakeQueryAdapter,
    _FakeRunner,
    _allocation,
    _dryrun_result,
    _repo_head,
    _repo_with_readonly_target,
    _snapshot,
    _task_context,
    _task_context_with_model_runtime_binding,
)


def test_signed_worker_accepts_valid_task_with_injected_runner(
    tmp_path: Path,
) -> None:
    runner = _FakeRunner()
    result = execute_reddog_signed_worker_dispatch_task(
        task_context=_task_context(),
        task_id="task-1",
        repo_root=tmp_path,
        runner=runner,
    )
    assert result.accepted is True
    assert result.decision == SIGNED_WORKER_DISPATCH_TASK_EXECUTOR_ACCEPT
    assert result.worker_runtime == "openclaw"
    assert result.capability == "candidate_queue_review"
    assert result.no_shell_command_executed is True
    assert result.no_source_repo_mutation_performed is True
    assert result.worker_execution_performed is True
    assert result.worker_process_spawn_count == 0
    assert result.shell_command_count == 0
    assert runner.calls[0]["worker_dispatch_intent"]["intent_id"] == (
        "worker_dispatch_intent_openclaw_candidate"
    )


def test_signed_worker_preserves_model_runtime_metadata(tmp_path: Path) -> None:
    context, binding = _task_context_with_model_runtime_binding()
    runner = _FakeRunner()
    result = execute_reddog_signed_worker_dispatch_task(
        task_context=context,
        task_id="task-1",
        repo_root=tmp_path,
        runner=runner,
    )
    assert result.accepted is True
    task_context = runner.calls[0]["task_context"]
    assert task_context["model_runtime_binding_receipt_id"] == binding["receipt_id"]
    assert task_context["model_runtime_binding_digest"] == (
        canonical_model_runtime_binding_digest(binding)
    )
    assert task_context["worker_dispatch_intent"][
        "model_runtime_binding_receipt_id"
    ] == binding["receipt_id"]
    assert task_context["signed_authority_worker_dispatch_receipt"][
        "model_runtime_binding_receipt_id"
    ] == binding["receipt_id"]


def test_signed_worker_rejects_tampered_model_runtime_context(
    tmp_path: Path,
) -> None:
    context, _ = _task_context_with_model_runtime_binding()
    context["model_runtime_binding_digest"] = "sha256:tampered"
    result = execute_reddog_signed_worker_dispatch_task(
        task_context=context,
        task_id="task-1",
        repo_root=tmp_path,
        runner=_FakeRunner(),
    )
    assert result.accepted is False
    assert (
        SignedWorkerDispatchTaskExecutorReason.MODEL_RUNTIME_BINDING_MISMATCH
        in result.rejection_reasons
    )


def test_signed_0102_readonly_runner_executes_bound_review(
    tmp_path: Path,
) -> None:
    repo = _repo_with_readonly_target(tmp_path)
    context, _ = _architect_review_context()
    allocation = context["wsp15_allocation_receipt"]
    model_runner = _EchoEvidenceModelRunner()
    runner = Signed0102ReadOnlyReviewRunner(
        model_runner=model_runner,
        holoindex_adapter=_FakeQueryAdapter(_repo_head(repo)),
        codeindex_adapter=_FakeQueryAdapter(_repo_head(repo)),
    )
    result = execute_reddog_signed_worker_dispatch_task(
        task_context=context,
        task_id="task-0102-1",
        repo_root=repo,
        runner=runner,
    )
    assert result.accepted is True, result.rejection_reasons
    assert result.decision == SIGNED_WORKER_DISPATCH_TASK_EXECUTOR_ACCEPT
    assert result.runner_result["decision"] == SIGNED_0102_READONLY_REVIEW_BINDING_ACCEPT
    readonly = result.runner_result["readonly_result"]
    assert readonly["report"]["model_backed_0102_worker_performed"] is True
    assert readonly["report"]["target_evidence"][0]["path"] == (
        "docs/work_ledger.schema.json"
    )
    assert model_runner.calls[0]["binding"]["wsp15_allocation_receipt_id"] == (
        allocation["receipt_id"]
    )


def test_signed_0102_runner_receives_model_runtime_binding(
    tmp_path: Path,
) -> None:
    repo = _repo_with_readonly_target(tmp_path)
    context, binding = _architect_review_context()
    model_runner = _EchoEvidenceModelRunner()
    result = execute_reddog_signed_worker_dispatch_task(
        task_context=context,
        task_id="task-0102-runtime-binding",
        repo_root=repo,
        runner=Signed0102ReadOnlyReviewRunner(
            model_runner=model_runner,
            holoindex_adapter=_FakeQueryAdapter(_repo_head(repo)),
            codeindex_adapter=_FakeQueryAdapter(_repo_head(repo)),
        ),
    )
    assert result.accepted is True, result.rejection_reasons
    selected = model_runner.calls[0]["binding"]["model_selection"]
    assert selected["model_runtime_binding_receipt_id"] == binding["receipt_id"]
    worker = result.runner_result["readonly_result"]["report"]["worker_receipt"]
    assert worker["model_runtime_binding_receipt_id"] == binding["receipt_id"]


def test_signed_0102_readonly_runner_rejects_code_change(
    tmp_path: Path,
) -> None:
    repo = _repo_with_readonly_target(tmp_path)
    allocation = _allocation()
    context = publish_bound_worker_dispatch(
        worker_dispatch_dryrun_result=_dryrun_result(allocation=allocation),
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=_CollectingWriter(),
    ).tasks[0].context
    result = execute_reddog_signed_worker_dispatch_task(
        task_context=context,
        task_id="task-0102-code",
        repo_root=repo,
        runner=Signed0102ReadOnlyReviewRunner(
            model_runner=_EchoEvidenceModelRunner()
        ),
    )
    assert result.accepted is False
    assert Signed0102ReadOnlyReviewBindingReason.UNSUPPORTED_CONTEXT in (
        result.rejection_reasons
    )
    assert result.no_source_repo_mutation_performed is True
    assert result.no_shell_command_executed is True


def _architect_review_context():
    return _task_context_with_model_runtime_binding(
        intent_overrides={
            "intent_id": "worker_dispatch_intent_fusion_lead",
            "role": "fusion_lead",
            "worker_runtime": "0102",
            "capability": "architect_review",
        }
    )
