"""Tests for REDDOG_SIGNED_WORKER_TASK_OPENCLAW_CLAIM_RUNTIME_PHASE1."""

from __future__ import annotations

from modules.communication.moltbot_bridge.tests.test_reddog_main_resident_queue_serial_loop_bootstrap import (  # noqa: F401
    _FakeWorktreeRunner,
    _draft_pr_publish_request,
    _ed25519_signing_material,
    _outcome_ratchet_request,
    _pilot_allowed_paths,
    _pilot_bounded_worker_plan,
    _pilot_path_overrides,
    _pilot_payloads,
    _pilot_worktree_path,
    _principals,
    _repo,
    _slice_verifier_request,
    _snapshots,
    _valve_environment,
    run_reddog_main_resident_queue_serial_loop_bootstrap,
)
from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (  # noqa: F401
    AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (  # noqa: F401
    resident_queue_runtime_file_path,
)
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from modules.communication.moltbot_bridge.scripts.run_task import execute_task
from modules.communication.moltbot_bridge.src import (
    openclaw_supervisor as supervisor_module,
    reddog_openclaw_hermes_0102_worker_dispatch_runtime as runtime,
)
from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
    OpenClawSupervisor,
    SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT,
    SIGNED_WORKER_OPENCLAW_CLAIM_IDLE,
    SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT,
    SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_IDLE,
    SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_REJECT,
    SIGNED_WORKER_OPENCLAW_CLAIM_REJECT,
    SIGNED_WORKER_OPENCLAW_CLAIM_REQUEUED,
    SignedWorkerOpenClawClaimReason,
    _signed_worker_claim_loop_result,
    claim_reddog_signed_worker_dispatch_task_once,
    claim_reddog_signed_worker_dispatch_tasks_until_idle,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_dispatch_task_executor import (
    SignedWorkerDispatchTaskExecutorReason,
    execute_reddog_signed_worker_dispatch_task,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime import (
    RUNTIME_SURFACE_READONLY_AUDIT,
    RepoAuditModelResult,
)
from modules.communication.moltbot_bridge.src.reddog_bounded_artifact_generation_runtime import (
    RUNTIME_SURFACE_ARTIFACT_GENERATION,
)
from modules.communication.moltbot_bridge.tests.test_reddog_main_resident_queue_serial_loop_bootstrap import (
    NOW as BOOTSTRAP_NOW,
    PILOT_ARTIFACT,
    PILOT_OPERATION,
    REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    _FakeExactShaEvidenceRunner,
    _held_out_gate_request,
    _pattern_memory_admission_request,
    _profile as _bootstrap_profile,
    _snapshot as _bootstrap_snapshot,
    _run_bootstrap_to_held_out_regression_gate,
    _run_bootstrap_to_verified_outcome_ratchet,
    _work_order,
    _write_runtime_json,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    publish_bound_worker_dispatch,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    worker_dispatch_dryrun_result,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    configure_signed_worker_claim_authority_env,
    install_signed_worker_envelope_test_authority,
    publish_agentdb_task_for_intent,
)
from modules.communication.moltbot_bridge.tests.reddog_signed_worker_dispatch_test_support import (
    bounded_allocation as _allocation,
    governed_snapshot as _snapshot,
    openclaw_candidate_allocation as _openclaw_candidate_allocation,
    readonly_allocation as _valid_readonly_allocation,
    signed_stage_binding,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_runtime_binding_test_capability,
    model_selection_and_runtime_binding_receipts,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    canonical_model_runtime_binding_digest,
    verification_receipt_digest,
    verified_runtime_binding_receipt,
)
from modules.communication.moltbot_bridge.tests.test_reddog_readonly_audit_task_executor import (
    _audit_provider_call_evidence_from_binding,
)
from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager

REPO_ROOT = Path(__file__).resolve().parents[4]


def _artifact_runtime_snapshot() -> dict[str, object]:
    selection, runtime_binding = _artifact_model_lineage()
    verification = verified_runtime_binding_receipt(runtime_binding)
    assert verification is not None
    snapshot = _bootstrap_snapshot()
    queue_item = snapshot["wre_queue_items"][0]
    worker_claim = snapshot["worker_claims"][0]
    progressive = _artifact_progressive_binding()
    allocation = progressive["wsp15_allocation_receipt"]
    queue_item.update(progressive)
    queue_item["evidence_refs"] = [
        item
        for item in queue_item["evidence_refs"]
        if not str(item).startswith("wsp15_allocation:")
    ]
    queue_item["evidence_refs"].append(f"wsp15_allocation:{allocation['receipt_id']}")
    queue_item["model_selection_receipt_id"] = selection["receipt_id"]
    queue_item["model_selection_digest"] = _mapping_digest(selection)
    queue_item["model_runtime_binding_receipt_id"] = runtime_binding["receipt_id"]
    queue_item["model_runtime_binding_digest"] = canonical_model_runtime_binding_digest(
        runtime_binding
    )
    queue_item["model_runtime_binding_verification_receipt_id"] = (
        verification.receipt_id
    )
    queue_item["model_runtime_binding_verification_digest"] = (
        verification_receipt_digest(verification)
    )
    worker_claim["model_selection_receipt_id"] = selection["receipt_id"]
    worker_claim["model_runtime_binding_receipt_id"] = runtime_binding["receipt_id"]
    worker_claim["model_runtime_binding_verification_receipt_id"] = (
        verification.receipt_id
    )
    queue_item["evidence_refs"] = [
        item
        for item in queue_item["evidence_refs"]
        if not str(item).startswith(("model_selection:", "model_runtime_binding:"))
    ]
    queue_item["evidence_refs"].extend(
        (
            f"model_selection:{selection['receipt_id']}",
            f"model_runtime_binding:{runtime_binding['receipt_id']}",
            f"model_runtime_binding_verification:{verification.receipt_id}",
        )
    )
    return snapshot


def _artifact_runtime_profile(**overrides: object) -> dict[str, object]:
    selection, runtime_binding = _artifact_model_lineage()
    verification = verified_runtime_binding_receipt(runtime_binding)
    assert verification is not None
    progressive = _artifact_progressive_binding()
    values = {
        "requested_operation": PILOT_OPERATION,
        "allowed_paths": [PILOT_ARTIFACT],
        "denied_paths": [],
        "wsp15_allocation_receipt": progressive["wsp15_allocation_receipt"],
        "model_selection_receipt": selection,
        "model_selection_receipt_id": selection["receipt_id"],
        "model_selection_digest": _mapping_digest(selection),
        "model_runtime_binding_receipt": runtime_binding,
        "model_runtime_binding_receipt_id": runtime_binding["receipt_id"],
        "model_runtime_binding_digest": canonical_model_runtime_binding_digest(
            runtime_binding
        ),
        "model_runtime_binding_verification_receipt_id": verification.receipt_id,
        "model_runtime_binding_verification_digest": verification_receipt_digest(
            verification
        ),
    }
    values.update(overrides)
    values.update(
        requested_operation=PILOT_OPERATION,
        allowed_paths=[PILOT_ARTIFACT],
        denied_paths=[],
        wsp15_allocation_receipt=progressive["wsp15_allocation_receipt"],
    )
    return _bootstrap_profile(**values)


def _artifact_runtime_work_order(**overrides: object) -> dict[str, object]:
    selection, runtime_binding = _artifact_model_lineage()
    verification = verified_runtime_binding_receipt(runtime_binding)
    assert verification is not None
    progressive = _artifact_progressive_binding()
    values = {
        "requested_operation": PILOT_OPERATION,
        "allowed_paths": [PILOT_ARTIFACT],
        "denied_paths": [],
        "wsp15_allocation_receipt": progressive["wsp15_allocation_receipt"],
        "model_selection_receipt": selection,
        "model_selection_receipt_id": selection["receipt_id"],
        "model_selection_digest": _mapping_digest(selection),
        "model_runtime_binding_receipt": runtime_binding,
        "model_runtime_binding_receipt_id": runtime_binding["receipt_id"],
        "model_runtime_binding_digest": canonical_model_runtime_binding_digest(
            runtime_binding
        ),
        "model_runtime_binding_verification_receipt_id": verification.receipt_id,
        "model_runtime_binding_verification_digest": verification_receipt_digest(
            verification
        ),
    }
    values.update(overrides)
    values.update(
        requested_operation=PILOT_OPERATION,
        allowed_paths=[PILOT_ARTIFACT],
        denied_paths=[],
        wsp15_allocation_receipt=progressive["wsp15_allocation_receipt"],
    )
    return _work_order(**values)


def _artifact_progressive_binding() -> dict[str, object]:
    return signed_stage_binding(
        requested_operation=PILOT_OPERATION,
        changed_paths=(PILOT_ARTIFACT,),
    )


def _artifact_model_lineage() -> tuple[dict[str, object], dict[str, object]]:
    with patch(
        "modules.ai_intelligence.ai_gateway.tests."
        "model_signed_evidence_test_helpers.NOW",
        1000,
    ):
        return model_selection_and_runtime_binding_receipts(
            runtime_surface=RUNTIME_SURFACE_ARTIFACT_GENERATION,
            verified_at_epoch=1000,
        )


def _mapping_digest(value: dict[str, object]) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


@pytest.fixture(autouse=True)
def isolated_agent_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    monkeypatch.setenv("OPENCLAW_SIGNED_QUEUE_STAGE_TASKS_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_SIGNED_0102_READONLY_TASKS_ENABLED", "1")
    DatabaseManager.reset_for_tests()
    _patch_assurance_store(monkeypatch)
    install_signed_worker_envelope_test_authority(monkeypatch)
    yield
    DatabaseManager.reset_for_tests()


class _FakeRunner:
    def __init__(
        self,
        *,
        accepted: bool = True,
        unsafe: bool = False,
        requeue_required: bool = False,
        result_overrides: dict | None = None,
    ) -> None:
        self.accepted = accepted
        self.unsafe = unsafe
        self.requeue_required = requeue_required
        self.result_overrides = dict(result_overrides or {})
        self.calls = []

    def run_signed_worker_dispatch_task(
        self,
        *,
        task_id,
        task_context,
        worker_dispatch_intent,
        signed_authority_receipt,
        repo_root,
    ):
        self.calls.append(
            {
                "task_id": task_id,
                "task_context": dict(task_context),
                "worker_dispatch_intent": dict(worker_dispatch_intent),
                "signed_authority_receipt": dict(signed_authority_receipt),
                "repo_root": Path(repo_root),
            }
        )
        result = {
            "accepted": self.accepted,
            "receipt_id": "fake-signed-worker-runner-receipt",
            "rejection_reasons": [] if self.accepted else ["runner_declined"],
            "no_source_repo_mutation_performed": not self.unsafe,
            "no_shell_command_executed": not self.unsafe,
            "no_holoindex_reindex_performed": True,
            "no_hermes_dispatch_performed": True,
            "no_worktree_operation_performed": True,
            "no_pr_created": True,
            "no_live_foundup_enqueue_performed": True,
            "no_pattern_memory_write_performed": True,
            "no_reward_settlement_performed": True,
            "worker_process_spawn_count": 0,
            "shell_command_count": 0,
        }
        if self.requeue_required:
            result["queue_chain_complete"] = False
            result["queue_chain_requeue_required"] = True
        result.update(self.result_overrides)
        return result


class _FakeQueryAdapter:
    def __init__(self, repo_head_sha: str = "abc123") -> None:
        self.repo_head_sha = repo_head_sha

    def query(self, *, query: str, allowed_paths, limit: int):
        path = allowed_paths[0] if allowed_paths else "docs/work_ledger.schema.json"
        return {
            "ok": True,
            "source": "fake",
            "query": query,
            "freshness": "CURRENT",
            "hits": [
                {
                    "path": path,
                    "title": "fake hit",
                    "score": 0.99,
                    "digest": "sha256:index-hit",
                }
            ],
            "error": "",
            "freshness_generation_id": "generation-1",
            "freshness_receipt_digest": "sha256:freshness",
            "freshness_receipt_path": "O:/Foundups-Agent/.holoindex/freshness.json",
            "repo_head_sha": self.repo_head_sha,
        }


class _EchoEvidenceModelRunner:
    def __init__(self) -> None:
        self.calls = []

    def run_repo_code_audit(
        self, *, prompt: str, context: str, binding, timeout_seconds: int
    ):
        self.calls.append(
            {"prompt": prompt, "context": context, "binding": dict(binding)}
        )
        parsed = json.loads(context)
        evidence_ref = parsed["untrusted_repository_evidence"][0]["evidence_ref"]
        output = {
            "summary": "Signed 0102 read-only review used supplied repository evidence.",
            "evidence_refs": [evidence_ref],
            "findings": [
                {
                    "finding_id": "signed-0102-readonly-review-1",
                    "claim": "The signed 0102 review cited the bound repository evidence.",
                    "wsp97_label": "OBSERVED",
                    "recommended_action": "FIX",
                    "wsp15_priority": "P1",
                    "severity": "MAJOR",
                    "evidence_refs": [evidence_ref],
                    "next_slice_name": "REDDOG_NEXT_RUNTIME_SLICE_PHASE1",
                }
            ],
        }
        return RepoAuditModelResult(
            ok=True,
            status="MODEL_OK",
            content=json.dumps(output, sort_keys=True),
            model_receipt_id="model-receipt-1",
            model_result_digest="sha256:model-result-1",
            made_network_call=True,
            provider_call_evidence=_audit_provider_call_evidence_from_binding(binding),
        )


class _FakeEnvDraftPrRunner:
    instances: list["_FakeEnvDraftPrRunner"] = []

    def __init__(self, *, repo_root: Path, timeout_s: int) -> None:
        self.repo_root = Path(repo_root)
        self.timeout_s = timeout_s
        self.calls: list[tuple[str, ...]] = []
        self.__class__.instances.append(self)

    def push_branch(self, *, worktree_path: Path, branch_name: str):
        self.calls.append(("push_branch", str(worktree_path), branch_name))
        return {"ok": True, "branch_name": branch_name}

    def create_draft_pr(
        self, *, branch_name: str, base_branch: str, title: str, body: str
    ):
        self.calls.append(("create_draft_pr", branch_name, base_branch, title, body))
        return "https://github.com/FOUNDUPS/Foundups-Agent/pull/4242"


class _FakeEnvCommitDraftPrRunner(_FakeEnvDraftPrRunner):
    evidence_runner: _FakeExactShaEvidenceRunner | None = None

    def commit_all(self, *, worktree_path: Path, add_paths, message: str):
        self.calls.append(("commit_all", str(worktree_path), tuple(add_paths), message))
        if self.evidence_runner is None:
            return {"ok": False, "returncode": 1, "stdout": "", "stderr": ""}
        self.evidence_runner.head = "a" * 40
        self.evidence_runner.parent = "b" * 40
        self.evidence_runner.dirty = False
        self.evidence_runner.commit_message = message
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}


class _FakeModelRuntimeBindingVerifier:
    trusted_now_epoch = staticmethod(lambda: 1000)

    def verify(self, *, binding, selection):
        capability = model_runtime_binding_test_capability(
            dict(selection), dict(binding)
        )
        assert capability is not None
        return capability


def _patch_exact_sha_commit_runtime(
    monkeypatch: pytest.MonkeyPatch,
    *,
    branch_name: str,
) -> _FakeExactShaEvidenceRunner:
    from modules.communication.moltbot_bridge.src import (
        reddog_main_resident_queue_serial_loop_bootstrap as bootstrap_module,
    )
    from modules.foundups.agent.src import worktree_pr_runner

    evidence_runner = _FakeExactShaEvidenceRunner(branch_name=branch_name)
    _FakeEnvCommitDraftPrRunner.evidence_runner = evidence_runner
    monkeypatch.setattr(
        worktree_pr_runner,
        "RealWorktreeRunner",
        _FakeEnvCommitDraftPrRunner,
    )
    monkeypatch.setattr(
        bootstrap_module,
        "_build_evidence_command_runner",
        lambda *args, **kwargs: (evidence_runner, ()),
    )
    monkeypatch.setattr(
        bootstrap_module,
        "build_model_runtime_verifier",
        lambda **_kwargs: (_FakeModelRuntimeBindingVerifier(), ()),
    )
    monkeypatch.setenv("REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS", "openrouter")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_EPOCH", "1000")
    monkeypatch.setenv("REDDOG_DRAFT_PR_RUNNER_MODE", "real")
    return evidence_runner


class _FakeBinding:
    def __init__(self, runner) -> None:
        self.accepted = True
        self.requested = True
        self.runner = runner
        self.rejection_reasons = ()

    def to_dict(self):
        return {
            "accepted": self.accepted,
            "requested": self.requested,
            "runner": "FakeRunner",
            "rejection_reasons": list(self.rejection_reasons),
        }


class _CollectingWriter:
    def enqueue_signed_worker_dispatch_tasks(self, tasks, receipt):
        return {
            "ok": True,
            "created_task_ids": [task.task_id for task in tasks],
        }

    def activate_signed_worker_dispatch_tasks(self, tasks, receipt):  # noqa: D102,E701
        return self.enqueue_signed_worker_dispatch_tasks(tasks, receipt)


def _digest(value: object) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _dryrun_result(allocation=None, intent=None):
    assert intent is None
    return worker_dispatch_dryrun_result(allocation or _allocation())


def _task_context():
    result = publish_bound_worker_dispatch(
        worker_dispatch_dryrun_result=_dryrun_result(
            allocation=_openclaw_candidate_allocation()
        ),
        work_state_snapshot=_snapshot(_openclaw_candidate_allocation()),
        queue_item_id="queue-1",
        writer=_CollectingWriter(),
    )
    assert result.accepted is True
    return result.tasks[0].context


def _context_with_intent_overrides(context, overrides):
    updated = dict(context)
    intent = {**dict(updated["worker_dispatch_intent"]), **overrides}
    receipt = dict(updated["signed_authority_worker_dispatch_receipt"])
    receipt["dispatch_intents"] = [intent]
    updated.update(
        worker_runtime=intent["worker_runtime"],
        worker_role=intent["role"],
        capability=intent["capability"],
        worker_dispatch_intent=intent,
        signed_authority_worker_dispatch_receipt=receipt,
    )
    return updated


def _task_context_with_model_runtime_binding(
    runtime_binding=None,
    *,
    intent_overrides=None,
):
    if runtime_binding is None:
        _, runtime_binding = model_selection_and_runtime_binding_receipts(
            runtime_surface=RUNTIME_SURFACE_READONLY_AUDIT,
        )
    verification = verified_runtime_binding_receipt(runtime_binding)
    assert verification is not None
    allocation = _valid_readonly_allocation(runtime_binding=runtime_binding)
    allocation.update(
        {
            "model_runtime_binding_verification_receipt_id": (verification.receipt_id),
            "model_runtime_binding_verification_digest": (
                verification_receipt_digest(verification)
            ),
        }
    )
    binding_refs = {
        "model_runtime_binding_receipt_id": runtime_binding["receipt_id"],
        "model_runtime_binding_digest": allocation["model_runtime_binding_digest"],
        "model_runtime_binding_verification_receipt_id": verification.receipt_id,
        "model_runtime_binding_verification_digest": (
            verification_receipt_digest(verification)
        ),
    }
    result = publish_bound_worker_dispatch(
        worker_dispatch_dryrun_result=_dryrun_result(allocation=allocation),
        work_state_snapshot=_snapshot(allocation, **binding_refs),
        queue_item_id="queue-1",
        writer=_CollectingWriter(),
    )
    assert result.accepted is True
    context = _context_with_intent_overrides(
        result.tasks[0].context,
        intent_overrides or {},
    )
    context["model_runtime_binding_receipt"] = runtime_binding
    return context, runtime_binding


def _publish_agentdb_task(**intent_overrides) -> str:
    defaults = {
        "intent_id": "worker_dispatch_intent_openclaw_candidate",
        "role": "openclaw_candidate",
        "worker_runtime": "openclaw",
        "capability": "candidate_queue_review",
    }
    requested = str(intent_overrides.get("intent_id") or defaults["intent_id"])
    return _publish_agentdb_task_with_allocation(
        _openclaw_candidate_allocation(prompt_suffix=requested),
        **{**defaults, **intent_overrides},
    )


def _publish_agentdb_task_with_allocation(allocation, **intent_overrides) -> str:
    return publish_agentdb_task_for_intent(
        allocation=allocation,
        intent_overrides=intent_overrides,
        dryrun_builder=_dryrun_result,
        snapshot_builder=_snapshot,
        context_override_builder=_context_with_intent_overrides,
        digest_builder=_digest,
    )


def _publish_readonly_agentdb_task() -> str:
    return _publish_agentdb_task_with_allocation(
        _valid_readonly_allocation(),
        intent_id="worker_dispatch_intent_fusion_lead",
        role="fusion_lead",
        worker_runtime="0102",
        capability="architect_review",
    )


def _pending_signed_task_id(capability: str) -> str:
    matches = [
        str(task.get("task_id") or "")
        for task in AgentDB().get_autonomous_tasks(status="pending", limit=20)
        if task.get("discovered_by") == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
        and isinstance(task.get("context"), dict)
        and str(task["context"].get("capability") or "") == capability
    ]
    debug_rows = AgentDB().db.execute_query(
        "SELECT task_id, status, assigned_to, context FROM agents_autonomous_tasks"
    )
    assert len(matches) == 1, [
        (
            row["task_id"],
            row["status"],
            row["assigned_to"],
            json.loads(row["context"]).get("capability"),
        )
        for row in debug_rows
    ]
    return matches[0]


def _assurance_store() -> AgentDB:
    trusted_now = datetime.fromisoformat(BOOTSTRAP_NOW)
    return AgentDB(assurance_now_provider=lambda: trusted_now)


def _patch_assurance_store(monkeypatch: pytest.MonkeyPatch) -> None:
    from modules.communication.moltbot_bridge.src import (
        reddog_signed_worker_openclaw_queue_loop_runtime_binding as binding_module,
    )

    monkeypatch.setattr(
        binding_module,
        "_build_assurance_reservation_store",
        lambda env: _assurance_store(),
    )


def _claim_reserved_author_and_verifier(
    *,
    monkeypatch: pytest.MonkeyPatch,
    repo: Path,
    state: Path,
    chain: Path,
    profile: Path,
    work_orders: Path,
    generic_writer: Path,
    governed_shell: Path,
    holoindex: Path,
    verifier: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    """Run the separately owned author and verifier tasks after admission."""

    work_order_payload = json.loads(work_orders.read_text(encoding="utf-8"))
    first_work_order = next(iter(work_order_payload["work_orders"].values()))
    _patch_exact_sha_commit_runtime(
        monkeypatch,
        branch_name=str(first_work_order["branch_name"]),
    )
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(chain.parent))
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(profile))
    monkeypatch.setenv("REDDOG_WORK_ORDERS_PATH", str(work_orders))
    monkeypatch.setenv("REDDOG_GENERIC_WRITER_DRYRUN_RESULT_PATH", str(generic_writer))
    monkeypatch.setenv("REDDOG_GOVERNED_SHELL_DRYRUN_RESULT_PATH", str(governed_shell))
    monkeypatch.setenv("REDDOG_HOLOINDEX_EVIDENCE_PATH", str(holoindex))
    monkeypatch.setenv("REDDOG_SLICE_VERIFIER_REQUEST_PATH", str(verifier))
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING", "1")
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATOR_MODE", "foundups_fusion")
    monkeypatch.setenv("OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED", "1")
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "2")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)
    configure_signed_worker_claim_authority_env(
        monkeypatch,
        chain_path=chain,
        signature_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")

    from modules.communication.moltbot_bridge.src import (
        reddog_bounded_artifact_generation_runtime as artifact_runtime,
    )

    monkeypatch.setattr(
        artifact_runtime,
        "_load_foundups_fusion_runner",
        lambda: (
            lambda _api_key, _user_payload, _messages, _payload: {
                "ok": True,
                "content": json.dumps(
                    {
                        "artifact_contents": {
                            PILOT_ARTIFACT: "# Generated By Independent Author\n"
                        }
                    },
                    sort_keys=True,
                ),
                "review_packet": {"receipt_id": "fusion-artifact-receipt"},
            }
        ),
    )

    author_result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=repo,
        agent_db_factory=_assurance_store,
    )
    assert author_result["accepted"] is True, json.dumps(author_result, sort_keys=True)
    assert author_result["capability"] == "bounded_code_change"

    verifier_result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=repo,
        agent_db_factory=_assurance_store,
    )
    assert verifier_result["accepted"] is True, json.dumps(
        verifier_result, sort_keys=True
    )
    assert verifier_result["capability"] == "independent_slice_verification"
    return author_result, verifier_result


def _signed_worker_task_last_result(task_id: str) -> dict[str, object]:
    task = AgentDB().get_autonomous_task_by_id(task_id)
    assert task is not None
    context = task.get("context")
    assert isinstance(context, dict)
    receipt = context.get("signed_worker_task_last_result")
    assert isinstance(receipt, dict)
    history = context.get("signed_worker_task_result_receipts")
    assert isinstance(history, list)
    assert history
    assert history[-1]["receipt_digest"] == receipt["receipt_digest"]
    assert receipt["schema_version"] == "reddog_signed_worker_task_result.v1"
    assert str(receipt["receipt_digest"]).startswith("sha256:")
    return receipt


def _queue_chain_results_through(stage_key: str) -> dict[str, object]:
    values = {
        "authority_request": {"status": "QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT"},
        "authority_runtime": {"decision": "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT"},
        "authority_verification": {
            "decision": "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT"
        },
        "worker_dispatch_dryrun": {
            "decision": "SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT"
        },
        "worker_dispatch_runtime": {
            "decision": "SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT"
        },
        "work_order_invocation": {
            "decision": "QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT"
        },
        "executor_plan": {"decision": "QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT"},
        "execution_valve": {
            "decision": "QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT"
        },
        "worktree_create": {
            "decision": "QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT"
        },
        "assurance_capacity_admission": {
            "decision": "ASSURANCE_CAPACITY_ADMISSION_ACCEPT"
        },
    }
    accepted = {}
    for key, value in values.items():
        accepted[key] = value
        if key == stage_key:
            break
    return {
        "schema_version": "reddog_resident_queue_chain_results.v1",
        "stage_results": accepted,
    }


def _repo_with_readonly_target(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    target = root / "docs" / "work_ledger.schema.json"
    target.parent.mkdir(parents=True)
    target.write_text('{"schema": "work-ledger", "version": 1}\n', encoding="utf-8")
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "test@example.invalid"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "config", "user.name", "RedDog Test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "add", "."], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(root), "commit", "-m", "test: seed readonly target"],
        check=True,
        capture_output=True,
    )
    return root


def _repo_head(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_signed_worker_executor_rejects_without_runner(tmp_path: Path) -> None:
    result = execute_reddog_signed_worker_dispatch_task(
        task_context=_task_context(),
        task_id="task-1",
        repo_root=tmp_path,
        runner=None,
    )

    assert result.accepted is False
    assert (
        SignedWorkerDispatchTaskExecutorReason.RUNNER_MISSING
        in result.rejection_reasons
    )


def test_signed_worker_executor_rejects_tampered_receipt_and_wsp15(
    tmp_path: Path,
) -> None:
    context = _task_context()
    context["signed_authority_worker_dispatch_receipt"] = dict(
        context["signed_authority_worker_dispatch_receipt"]
    )
    context["signed_authority_worker_dispatch_receipt"]["dispatch_intents"] = []
    context["worker_dispatch_intent"] = dict(context["worker_dispatch_intent"])
    context["worker_dispatch_intent"]["wsp15_allocation_digest"] = "sha256:tampered"

    result = execute_reddog_signed_worker_dispatch_task(
        task_context=context,
        task_id="task-1",
        repo_root=tmp_path,
        runner=_FakeRunner(),
    )

    assert result.accepted is False
    assert (
        SignedWorkerDispatchTaskExecutorReason.INTENT_NOT_IN_RECEIPT
        in result.rejection_reasons
    )
    assert (
        SignedWorkerDispatchTaskExecutorReason.WSP15_MISMATCH
        in result.rejection_reasons
    )
    assert result.worker_execution_performed is False


def test_signed_worker_executor_rejects_unsafe_runner(tmp_path: Path) -> None:
    result = execute_reddog_signed_worker_dispatch_task(
        task_context=_task_context(),
        task_id="task-1",
        repo_root=tmp_path,
        runner=_FakeRunner(unsafe=True),
    )

    assert result.accepted is False
    assert (
        SignedWorkerDispatchTaskExecutorReason.RUNNER_UNSAFE in result.rejection_reasons
    )
    assert result.no_source_repo_mutation_performed is False
    assert result.no_shell_command_executed is False
    assert result.worker_execution_performed is True
    assert result.shell_command_count == 1


def test_signed_worker_executor_counts_rejected_and_raising_runner_execution(
    tmp_path: Path,
) -> None:
    rejected = execute_reddog_signed_worker_dispatch_task(
        task_context=_task_context(),
        task_id="task-rejected",
        repo_root=tmp_path,
        runner=_FakeRunner(accepted=False),
    )

    class RaisingRunner:
        def run_signed_worker_dispatch_task(self, **kwargs):
            raise RuntimeError("runner failed after invocation")

    raised = execute_reddog_signed_worker_dispatch_task(
        task_context=_task_context(),
        task_id="task-raised",
        repo_root=tmp_path,
        runner=RaisingRunner(),
    )

    assert rejected.worker_execution_performed is True
    assert raised.worker_execution_performed is True
    assert raised.effect_evidence_complete is False
    assert raised.no_shell_command_executed is False
    assert raised.no_source_repo_mutation_performed is False
    assert (
        SignedWorkerDispatchTaskExecutorReason.RUNNER_REJECTED
        in rejected.rejection_reasons
    )
    assert (
        SignedWorkerDispatchTaskExecutorReason.RUNNER_REJECTED
        in raised.rejection_reasons
    )


def test_signed_worker_executor_rejects_incomplete_or_inconsistent_effect_evidence(
    tmp_path: Path,
) -> None:
    context = _task_context()
    incomplete = _FakeRunner(result_overrides={"shell_command_count": None})
    inconsistent = _FakeRunner(result_overrides={"shell_command_count": 1})

    incomplete_result = execute_reddog_signed_worker_dispatch_task(
        task_context=context,
        task_id="task-incomplete-effects",
        repo_root=tmp_path,
        runner=incomplete,
    )
    inconsistent_result = execute_reddog_signed_worker_dispatch_task(
        task_context=context,
        task_id="task-inconsistent-effects",
        repo_root=tmp_path,
        runner=inconsistent,
    )

    for result in (incomplete_result, inconsistent_result):
        assert result.accepted is False
        assert result.effect_evidence_complete is False
        assert result.no_shell_command_executed is False
        assert (
            SignedWorkerDispatchTaskExecutorReason.RUNNER_EFFECT_EVIDENCE_INCOMPLETE
            in result.rejection_reasons
        )


def test_run_task_routes_signed_worker_before_wre_fallback(
    tmp_path: Path, monkeypatch
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    row = db.db.execute_query(
        "SELECT status, discovered_by, assigned_to, context, required_skills "
        "FROM agents_autonomous_tasks WHERE task_id = ?",
        (task_id,),
    )

    assert db.assign_signed_worker_task(task_id), row
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)

    result = execute_task(
        task_id, repo_root=tmp_path, signed_worker_runner=_FakeRunner()
    )

    assert result["ok"] is True
    assert result["executor"] == "reddog:signed_worker_dispatch"
    assert result["structured_result"]["accepted"] is True
    assert db.get_autonomous_task_by_id(task_id)["status"] == "completed"


def test_run_task_rejects_signed_worker_without_runner_instead_of_wre_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)

    result = execute_task(task_id, repo_root=tmp_path)

    assert result["ok"] is False
    assert result["executor"] == "reddog:signed_worker_dispatch"
    assert SignedWorkerDispatchTaskExecutorReason.RUNNER_MISSING in result["detail"]
    assert db.get_autonomous_task_by_id(task_id)["status"] == "failed"


def test_run_task_uses_env_bound_queue_loop_runner_when_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()
    assert db.assign_signed_worker_task(task_id)
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", "signed_0102_bounded_code_fusion"
    )

    from modules.communication.moltbot_bridge.src import (
        reddog_signed_worker_openclaw_queue_loop_runtime_binding as binding_module,
    )

    runner = _FakeRunner()
    monkeypatch.setattr(
        binding_module,
        "build_reddog_signed_worker_queue_loop_runner_from_env",
        lambda *, repo_root, env: _FakeBinding(runner),
    )

    result = execute_task(task_id, repo_root=tmp_path)

    assert result["ok"] is True
    assert result["executor"] == "reddog:signed_worker_dispatch"
    assert result["structured_result"]["accepted"] is True
    assert runner.calls[0]["task_id"] == task_id
    assert db.get_autonomous_task_by_id(task_id)["status"] == "completed"


def test_openclaw_claim_ignores_0102_readonly_task_until_env_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    allocation = _valid_readonly_allocation()
    task_id = _publish_agentdb_task_with_allocation(
        allocation,
        intent_id="worker_dispatch_intent_fusion_lead",
        role="fusion_lead",
        worker_runtime="0102",
        capability="architect_review",
    )
    monkeypatch.delenv("OPENCLAW_SIGNED_0102_READONLY_TASKS_ENABLED", raising=False)

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=tmp_path)

    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_IDLE
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "pending"


def test_openclaw_signed_worker_healthcheck_blocks_before_agentdb_claim(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_id = _publish_readonly_agentdb_task()
    monkeypatch.setenv("OPENCLAW_SIGNED_WORKER_SIGNER_HEALTHCHECK", "1")
    from modules.communication.moltbot_bridge.src import (
        reddog_signer_socket_service_healthcheck as healthcheck_module,
    )

    monkeypatch.setattr(
        healthcheck_module,
        "run_reddog_signer_socket_service_healthcheck",
        lambda **_: SimpleNamespace(
            to_dict=lambda: {
                "accepted": False,
                "status": "SIGNER_SERVICE_HEALTHCHECK_REJECT",
                "rejection_reasons": ("signer_healthcheck_client_rejected",),
            }
        ),
    )
    runner = _FakeRunner()

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
    )

    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REJECT
    assert (
        SignedWorkerOpenClawClaimReason.SIGNER_HEALTHCHECK_REJECTED
        in result["rejection_reasons"]
    )
    assert "signer_healthcheck_client_rejected" in result["rejection_reasons"]
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "pending"
    assert runner.calls == []


def test_openclaw_signed_worker_healthcheck_accept_allows_claim(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_id = _publish_readonly_agentdb_task()
    monkeypatch.setenv("OPENCLAW_SIGNED_WORKER_SIGNER_HEALTHCHECK", "1")
    from modules.communication.moltbot_bridge.src import (
        reddog_signer_socket_service_healthcheck as healthcheck_module,
    )

    monkeypatch.setattr(
        healthcheck_module,
        "run_reddog_signer_socket_service_healthcheck",
        lambda **_: SimpleNamespace(
            to_dict=lambda: {
                "accepted": True,
                "status": "SIGNER_SERVICE_HEALTHCHECK_READY",
                "rejection_reasons": (),
            }
        ),
    )
    runner = _FakeRunner()

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=runner,
    )

    assert result["accepted"] is True, json.dumps(result, sort_keys=True, default=str)
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert result["task_id"] == task_id
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "completed"
    assert runner.calls[0]["task_id"] == task_id
    receipt = _signed_worker_task_last_result(task_id)
    assert receipt["claim_status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert receipt["accepted"] is True
    assert receipt["receipt_id"] == result["receipt_id"]
    assert receipt["worker_runtime"] == "0102"
    assert receipt["capability"] == "architect_review"
    assert str(receipt["run_result_digest"]).startswith("sha256:")
    assert str(receipt["runner_result_digest"]).startswith("sha256:")


def test_openclaw_signed_worker_claim_persists_failure_result_receipt(
    tmp_path: Path,
) -> None:
    task_id = _publish_readonly_agentdb_task()

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=tmp_path)

    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REJECT
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "failed"
    receipt = _signed_worker_task_last_result(task_id)
    assert receipt["claim_status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REJECT
    assert receipt["accepted"] is False
    assert (
        SignedWorkerOpenClawClaimReason.TASK_EXECUTION_REJECTED
        in receipt["rejection_reasons"]
    )
    assert (
        SignedWorkerDispatchTaskExecutorReason.RUNNER_REJECTED
        in receipt["rejection_reasons"]
    )


def test_openclaw_signed_worker_claim_fails_terminally_on_binding_exception(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_id = _publish_readonly_agentdb_task()

    def _raise_binding_error(**_kwargs):
        raise RuntimeError("binding failed")

    monkeypatch.setattr(
        supervisor_module,
        "_signed_worker_effective_runner",
        _raise_binding_error,
    )
    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=tmp_path)

    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REJECT
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "failed"
    receipt = _signed_worker_task_last_result(task_id)
    assert receipt["claim_status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REJECT
    assert str(receipt["runner_result_digest"]).startswith("sha256:")


def test_openclaw_signed_worker_claim_persists_requeue_result_receipt(
    tmp_path: Path,
) -> None:
    task_id = _publish_readonly_agentdb_task()

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(requeue_required=True),
    )

    assert result["accepted"] is True
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REQUEUED
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "pending"
    receipt = _signed_worker_task_last_result(task_id)
    assert receipt["claim_status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REQUEUED
    assert receipt["accepted"] is True
    summary = receipt["runner_result_summary"]
    assert isinstance(summary, dict)
    assert summary["queue_chain_requeue_required"] is True


def test_openclaw_signed_worker_claim_rejects_when_result_persistence_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_id = _publish_readonly_agentdb_task()
    from modules.communication.moltbot_bridge.src import openclaw_supervisor

    monkeypatch.setattr(
        openclaw_supervisor,
        "_persist_reddog_signed_worker_dispatch_task_result",
        lambda *_, **__: False,
    )

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
    )

    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REJECT
    assert (
        SignedWorkerOpenClawClaimReason.RESULT_PERSISTENCE_REJECTED
        in result["rejection_reasons"]
    )
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "executing"


@pytest.mark.parametrize(
    "requeue_required",
    (False, True),
)
def test_openclaw_signed_worker_claim_rejects_when_task_transition_fails(
    tmp_path: Path,
    monkeypatch,
    requeue_required: bool,
) -> None:
    _publish_readonly_agentdb_task()
    from modules.communication.moltbot_bridge.src import openclaw_supervisor

    monkeypatch.setattr(
        openclaw_supervisor,
        "_commit_signed_worker_task_result",
        lambda *_, **__: False,
    )

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(requeue_required=requeue_required),
    )

    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REJECT
    assert (
        SignedWorkerOpenClawClaimReason.TASK_STATE_TRANSITION_REJECTED
        in result["rejection_reasons"]
    )


def test_openclaw_signed_worker_rejection_surfaces_failed_failure_transition(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _publish_readonly_agentdb_task()
    from modules.communication.moltbot_bridge.src import openclaw_supervisor

    monkeypatch.setattr(
        openclaw_supervisor,
        "_persist_reddog_signed_worker_dispatch_task_result",
        lambda *_, **__: False,
    )

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=None,
    )

    assert result["accepted"] is False
    assert result["worker_execution_performed"] is True
    assert result["effect_evidence_complete"] is True
    assert (
        SignedWorkerOpenClawClaimReason.TASK_STATE_TRANSITION_REJECTED
        in result["rejection_reasons"]
    )


def test_openclaw_claim_executes_0102_readonly_task_when_env_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    allocation = _valid_readonly_allocation()
    task_id = _publish_agentdb_task_with_allocation(
        allocation,
        intent_id="worker_dispatch_intent_fusion_lead",
        role="fusion_lead",
        worker_runtime="0102",
        capability="architect_review",
    )
    runner = _FakeRunner()
    monkeypatch.setenv("OPENCLAW_SIGNED_0102_READONLY_TASKS_ENABLED", "1")
    from modules.communication.moltbot_bridge.src import (
        reddog_signed_worker_0102_readonly_review_binding as review_binding,
    )

    monkeypatch.setattr(
        review_binding, "Signed0102ReadOnlyReviewRunner", lambda: runner
    )

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=tmp_path)

    assert result["accepted"] is True, json.dumps(result, sort_keys=True)
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert result["task_id"] == task_id
    assert result["worker_runtime"] == "0102"
    assert result["capability"] == "architect_review"
    assert runner.calls[0]["task_id"] == task_id
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "completed"


def test_openclaw_claim_does_not_claim_0102_bounded_code_change_even_when_readonly_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    allocation = _valid_readonly_allocation()
    task_id = _publish_agentdb_task_with_allocation(
        allocation,
        intent_id="worker_dispatch_intent_coding_worker_1",
        role="coding_worker_1",
        worker_runtime="0102",
        capability="bounded_code_change",
    )
    monkeypatch.setenv("OPENCLAW_SIGNED_0102_READONLY_TASKS_ENABLED", "1")

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=tmp_path)

    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_IDLE
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "pending"


def test_openclaw_claim_0102_bounded_code_waits_for_bounded_stage(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_id = _publish_agentdb_task_with_allocation(
        _allocation(),
        intent_id="worker_dispatch_intent_coding_worker_1",
        role="coding_worker_1",
        worker_runtime="0102",
        capability="bounded_code_change",
    )
    runtime_root = tmp_path.parent / f"{tmp_path.name}-runtime"
    state = _write_runtime_json(runtime_root, "work_state.json", _bootstrap_snapshot())
    chain = _write_runtime_json(
        runtime_root,
        "chain_results.json",
        _queue_chain_results_through("execution_valve"),
    )
    monkeypatch.setenv("OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED", "1")
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH",
        str(runtime_root / "profile.json"),
    )
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING", "1")
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATOR_MODE", "foundups_fusion")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=tmp_path)

    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_IDLE
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "pending"


def test_openclaw_claim_0102_bounded_code_requires_artifact_request_source(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_id = _publish_agentdb_task_with_allocation(
        _allocation(),
        intent_id="worker_dispatch_intent_coding_worker_1",
        role="coding_worker_1",
        worker_runtime="0102",
        capability="bounded_code_change",
    )
    runtime_root = tmp_path.parent / f"{tmp_path.name}-runtime"
    state = _write_runtime_json(runtime_root, "work_state.json", _bootstrap_snapshot())
    chain = _write_runtime_json(
        runtime_root,
        "chain_results.json",
        _queue_chain_results_through("assurance_capacity_admission"),
    )
    monkeypatch.setenv("OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED", "1")
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH",
        str(runtime_root / "profile.json"),
    )
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATOR_MODE", "foundups_fusion")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=tmp_path)

    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_IDLE
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "pending"


def test_openclaw_claim_executes_0102_bounded_code_when_bounded_stage_ready(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_id = _publish_agentdb_task_with_allocation(
        _allocation(),
        intent_id="worker_dispatch_intent_coding_worker_1",
        role="coding_worker_1",
        worker_runtime="0102",
        capability="bounded_code_change",
    )
    runtime_root = tmp_path.parent / f"{tmp_path.name}-runtime"
    state = _write_runtime_json(runtime_root, "work_state.json", _bootstrap_snapshot())
    chain = _write_runtime_json(
        runtime_root,
        "chain_results.json",
        _queue_chain_results_through("assurance_capacity_admission"),
    )
    runner = _FakeRunner()
    monkeypatch.setenv("OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED", "1")
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", "signed_0102_bounded_code"
    )
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH",
        str(runtime_root / "profile.json"),
    )
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATOR_MODE", "foundups_fusion")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)
    from modules.communication.moltbot_bridge.src import (
        reddog_signed_worker_openclaw_queue_loop_runtime_binding as binding_module,
    )

    monkeypatch.setattr(
        binding_module,
        "build_reddog_signed_worker_queue_loop_runner_from_env",
        lambda *, repo_root, env: _FakeBinding(runner),
    )

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=tmp_path)

    assert result["accepted"] is True, json.dumps(result, sort_keys=True)
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert result["task_id"] == task_id
    assert result["worker_runtime"] == "0102"
    assert result["capability"] == "bounded_code_change"
    assert runner.calls[0]["task_id"] == task_id
    assert not (tmp_path / "artifact_generation_request.json").exists()
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "completed"


def test_openclaw_claim_profile_enables_0102_bounded_code_when_stage_ready(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_id = _publish_agentdb_task_with_allocation(
        _allocation(),
        intent_id="worker_dispatch_intent_coding_worker_1",
        role="coding_worker_1",
        worker_runtime="0102",
        capability="bounded_code_change",
    )
    state = _write_runtime_json(tmp_path, "work_state.json", _bootstrap_snapshot())
    chain = _write_runtime_json(
        tmp_path,
        "chain_results.json",
        _queue_chain_results_through("assurance_capacity_admission"),
    )
    runner = _FakeRunner()
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", "signed_0102_bounded_code"
    )
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(tmp_path / "profile.json")
    )
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATOR_MODE", "foundups_fusion")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)
    from modules.communication.moltbot_bridge.src import (
        reddog_signed_worker_openclaw_queue_loop_runtime_binding as binding_module,
    )

    monkeypatch.setattr(
        binding_module,
        "build_reddog_signed_worker_queue_loop_runner_from_env",
        lambda *, repo_root, env: _FakeBinding(runner),
    )

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=tmp_path)

    assert result["accepted"] is True, json.dumps(result, sort_keys=True)
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert result["task_id"] == task_id
    assert result["worker_runtime"] == "0102"
    assert result["capability"] == "bounded_code_change"
    assert runner.calls[0]["task_id"] == task_id


def test_openclaw_claim_fusion_profile_supplies_artifact_generator_mode(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_id = _publish_agentdb_task_with_allocation(
        _allocation(),
        intent_id="worker_dispatch_intent_coding_worker_1",
        role="coding_worker_1",
        worker_runtime="0102",
        capability="bounded_code_change",
    )
    state = _write_runtime_json(
        tmp_path, "work_state.json", _artifact_runtime_snapshot()
    )
    chain = _write_runtime_json(
        tmp_path,
        "chain_results.json",
        _queue_chain_results_through("assurance_capacity_admission"),
    )
    runner = _FakeRunner()
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", "signed_0102_bounded_code_fusion"
    )
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(tmp_path / "profile.json")
    )
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)
    from modules.communication.moltbot_bridge.src import (
        reddog_signed_worker_openclaw_queue_loop_runtime_binding as binding_module,
    )

    monkeypatch.setattr(
        binding_module,
        "build_reddog_signed_worker_queue_loop_runner_from_env",
        lambda *, repo_root, env: _FakeBinding(runner),
    )

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=tmp_path)

    assert result["accepted"] is True, json.dumps(result, sort_keys=True)
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert result["task_id"] == task_id
    assert result["worker_runtime"] == "0102"
    assert result["capability"] == "bounded_code_change"
    assert runner.calls[0]["task_id"] == task_id


def test_openclaw_claim_explicit_zero_disables_profile_0102_bounded_code(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_id = _publish_agentdb_task_with_allocation(
        _allocation(),
        intent_id="worker_dispatch_intent_coding_worker_1",
        role="coding_worker_1",
        worker_runtime="0102",
        capability="bounded_code_change",
    )
    state = _write_runtime_json(tmp_path, "work_state.json", _bootstrap_snapshot())
    chain = _write_runtime_json(
        tmp_path,
        "chain_results.json",
        _queue_chain_results_through("worktree_create"),
    )
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", "signed_0102_bounded_code"
    )
    monkeypatch.setenv("OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED", "0")
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(state))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(chain))
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(tmp_path / "profile.json")
    )
    monkeypatch.setenv("REDDOG_ARTIFACT_GENERATOR_MODE", "foundups_fusion")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=tmp_path)

    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_IDLE
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "pending"


def test_openclaw_claim_env_bound_queue_loop_runner_reaches_held_out_regression_gate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    ctx = _run_bootstrap_to_verified_outcome_ratchet(tmp_path, monkeypatch)
    verifier_stage = ctx["verifier_stage"]
    held_out_request = _write_runtime_json(
        tmp_path,
        "held_out_gate_request.json",
        _held_out_gate_request(verifier_stage["verifier_result"]),
    )
    task_id = _pending_signed_task_id("queue_stage_progress")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(ctx["state"]))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(ctx["chain"]))
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(ctx["profile"])
    )
    monkeypatch.setenv("REDDOG_HELD_OUT_GATE_REQUEST_PATH", str(held_out_request))
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)

    result = claim_reddog_signed_worker_dispatch_tasks_until_idle(
        repo_root=ctx["repo"],
        max_claims=2,
    )

    assert result["accepted"] is True, json.dumps(result, sort_keys=True)
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT, json.dumps(
        result, sort_keys=True
    )
    assert result["claimed_count"] == 2
    assert result["requeued_task_ids"] == (task_id, task_id)
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "pending"

    stored = json.loads(Path(ctx["chain"]).read_text(encoding="utf-8"))
    stage = stored["stage_results"]["held_out_regression_gate"]
    assert (
        stage["decision"] == "QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT"
    )
    assert (
        stage["gate_result"]["decision"]
        == "HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT"
    )
    assert stage["gate_result"]["receipt"]["no_pattern_memory_write_performed"] is True
    assert stage["no_command_execution_performed"] is True
    assert stage["no_test_execution_performed"] is True
    assert stage["no_pattern_memory_write_performed"] is True
    assert stage["no_pr_publish_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True
    assert "pattern_memory_admission" not in stored["stage_results"]


def test_openclaw_claim_env_bound_queue_loop_rejects_without_outcome_authority(
    tmp_path: Path,
    monkeypatch,
) -> None:
    ctx = _run_bootstrap_to_held_out_regression_gate(tmp_path, monkeypatch)
    admission_request = _write_runtime_json(
        tmp_path,
        "pattern_memory_admission_request.json",
        _pattern_memory_admission_request(),
    )
    pattern_memory_db = tmp_path / "runtime" / "pattern_memory.db"
    task_id = _pending_signed_task_id("queue_stage_progress")
    monkeypatch.setenv("WRE_MOCK_SKILLS", runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL)
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", str(ctx["state"]))
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH", str(ctx["chain"]))
    monkeypatch.setenv(
        "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH", str(ctx["profile"])
    )
    monkeypatch.setenv(
        "REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_PATH", str(admission_request)
    )
    monkeypatch.setenv(
        "REDDOG_PATTERN_MEMORY_ADMISSION_DB_PATH", str(pattern_memory_db)
    )
    monkeypatch.setenv("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS", "1")
    monkeypatch.setenv("REDDOG_RESIDENT_QUEUE_NOW_ISO", BOOTSTRAP_NOW)

    result = claim_reddog_signed_worker_dispatch_task_once(repo_root=ctx["repo"])

    assert result["accepted"] is False, json.dumps(result, sort_keys=True)
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REJECT
    assert result["task_id"] == task_id
    assert "FAIL_VERIFIED_OUTCOME_EVIDENCE_PUBLICATION" in result["rejection_reasons"]
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "failed"

    stored = json.loads(Path(ctx["chain"]).read_text(encoding="utf-8"))
    assert "pattern_memory_admission" not in stored["stage_results"]
    assert not pattern_memory_db.exists()
    assert not (ctx["repo"] / "runtime" / "pattern_memory.db").exists()


def test_openclaw_claims_signed_worker_task_once_and_completes_it(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
    )

    assert result["accepted"] is True
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert result["task_id"] == task_id
    assert result["worker_runtime"] == "openclaw"
    assert result["receipt_id"]
    assert db.get_autonomous_task_by_id(task_id)["status"] == "completed"


def test_openclaw_claim_requeues_incomplete_queue_chain_task(tmp_path: Path) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(requeue_required=True),
    )

    assert result["accepted"] is True
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REQUEUED
    assert result["task_id"] == task_id
    assert result["worker_runtime"] == "openclaw"
    assert result["receipt_id"]
    stored = db.get_autonomous_task_by_id(task_id)
    assert stored["status"] == "pending"
    assert stored["assigned_to"] is None
    assert stored["assigned_at"] is None


def test_openclaw_claim_ignores_non_openclaw_signed_worker_task(tmp_path: Path) -> None:
    task_id = _publish_agentdb_task(
        intent_id="worker_dispatch_intent_hermes_candidate",
        role="hermes_candidate",
        worker_runtime="hermes",
        capability="bounded_code_change",
    )
    db = AgentDB()

    result = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
    )

    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_IDLE
    assert (
        SignedWorkerOpenClawClaimReason.NO_PENDING_TASK in result["rejection_reasons"]
    )
    assert db.get_autonomous_task_by_id(task_id)["status"] == "pending"


def test_openclaw_supervisor_instance_claims_signed_worker_task(tmp_path: Path) -> None:
    task_id = _publish_agentdb_task()
    supervisor = OpenClawSupervisor(repo_root=tmp_path)

    result = supervisor.claim_reddog_signed_worker_dispatch_task_once(
        signed_worker_runner=_FakeRunner(),
    )

    assert result["accepted"] is True
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT
    assert result["task_id"] == task_id
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "completed"


def test_openclaw_claim_rejects_without_runner_and_idle_when_empty(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task()
    db = AgentDB()

    rejected = claim_reddog_signed_worker_dispatch_task_once(repo_root=tmp_path)
    idle = claim_reddog_signed_worker_dispatch_task_once(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
    )

    assert rejected["accepted"] is False
    assert rejected["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_REJECT
    assert (
        SignedWorkerOpenClawClaimReason.TASK_EXECUTION_REJECTED
        in rejected["rejection_reasons"]
    )
    assert (
        SignedWorkerDispatchTaskExecutorReason.RUNNER_MISSING
        in rejected["rejection_reasons"]
    )
    assert db.get_autonomous_task_by_id(task_id)["status"] == "failed"
    assert idle["accepted"] is False
    assert idle["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_IDLE


def test_openclaw_claim_loop_claims_until_idle(tmp_path: Path) -> None:
    task_id_1 = _publish_agentdb_task(
        intent_id="worker_dispatch_intent_openclaw_candidate_1"
    )
    task_id_2 = _publish_agentdb_task(
        intent_id="worker_dispatch_intent_openclaw_candidate_2"
    )
    db = AgentDB()

    result = claim_reddog_signed_worker_dispatch_tasks_until_idle(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
        max_claims=5,
    )

    assert result["accepted"] is True
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT
    assert result["claimed_count"] == 2
    assert set(result["completed_task_ids"]) == {task_id_1, task_id_2}
    assert result["failed_task_ids"] == ()
    assert result["idle"] is True
    assert result["max_claims_reached"] is False
    assert len(result["claim_results"]) == 3
    assert result["claim_results"][-1]["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_IDLE
    assert db.get_autonomous_task_by_id(task_id_1)["status"] == "completed"
    assert db.get_autonomous_task_by_id(task_id_2)["status"] == "completed"
    assert result["no_shell_command_executed"] is True
    assert result["no_repo_mutation_performed"] is True
    assert result["no_holoindex_reindex_performed"] is True
    assert result["no_hermes_dispatch_performed"] is True


def test_openclaw_claim_loop_respects_max_claims(tmp_path: Path) -> None:
    task_id_1 = _publish_agentdb_task(
        intent_id="worker_dispatch_intent_openclaw_candidate_1"
    )
    task_id_2 = _publish_agentdb_task(
        intent_id="worker_dispatch_intent_openclaw_candidate_2"
    )
    db = AgentDB()

    result = claim_reddog_signed_worker_dispatch_tasks_until_idle(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
        max_claims=1,
    )

    assert result["accepted"] is True
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT
    assert result["claimed_count"] == 1
    assert result["completed_task_ids"] == (task_id_1,)
    assert result["max_claims_reached"] is True
    assert result["idle"] is False
    assert len(result["child_execution_evidence_digests"]) == 1
    assert db.get_autonomous_task_by_id(task_id_1)["status"] == "completed"
    assert db.get_autonomous_task_by_id(task_id_2)["status"] == "pending"


def test_openclaw_claim_loop_counts_requeued_claims(tmp_path: Path) -> None:
    task_id = _publish_agentdb_task(
        intent_id="worker_dispatch_intent_openclaw_candidate_1"
    )
    db = AgentDB()

    result = claim_reddog_signed_worker_dispatch_tasks_until_idle(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(requeue_required=True),
        max_claims=2,
    )

    assert result["accepted"] is True
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT
    assert result["claimed_count"] == 2
    assert result["completed_task_ids"] == ()
    assert result["requeued_task_ids"] == (task_id, task_id)
    assert result["failed_task_ids"] == ()
    assert result["idle"] is False
    assert result["max_claims_reached"] is True
    assert db.get_autonomous_task_by_id(task_id)["status"] == "pending"


def test_openclaw_claim_loop_skips_task_before_retry_window(tmp_path: Path) -> None:
    task_id = _publish_agentdb_task(intent_id="worker_dispatch_intent_retry_future")
    db = AgentDB()
    assert (
        db.db.execute_write(
            "UPDATE agents_autonomous_tasks SET retry_not_before = ? WHERE task_id = ?",
            ("2999-01-01T00:00:00+00:00", task_id),
        )
        == 1
    )

    result = claim_reddog_signed_worker_dispatch_tasks_until_idle(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
        max_claims=1,
    )

    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_IDLE
    assert result["claimed_count"] == 0
    assert db.get_autonomous_task_by_id(task_id)["status"] == "pending"


def test_openclaw_claim_loop_claims_task_after_retry_window(tmp_path: Path) -> None:
    task_id = _publish_agentdb_task(intent_id="worker_dispatch_intent_retry_due")
    db = AgentDB()
    assert (
        db.db.execute_write(
            "UPDATE agents_autonomous_tasks SET retry_not_before = ? WHERE task_id = ?",
            ("2000-01-01T00:00:00+00:00", task_id),
        )
        == 1
    )

    result = claim_reddog_signed_worker_dispatch_tasks_until_idle(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
        max_claims=1,
    )

    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT
    assert result["completed_task_ids"] == (task_id,)
    assert db.get_autonomous_task_by_id(task_id)["status"] == "completed"


def test_openclaw_claim_loop_reports_idle_without_work(tmp_path: Path) -> None:
    result = claim_reddog_signed_worker_dispatch_tasks_until_idle(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
        max_claims=3,
    )

    assert result["accepted"] is True
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_IDLE
    assert result["claimed_count"] == 0
    assert result["idle"] is True
    assert (
        SignedWorkerOpenClawClaimReason.NO_PENDING_TASK in result["rejection_reasons"]
    )


def test_openclaw_claim_loop_ignores_non_openclaw_tasks(tmp_path: Path) -> None:
    task_id = _publish_agentdb_task(
        intent_id="worker_dispatch_intent_hermes_candidate",
        role="hermes_candidate",
        worker_runtime="hermes",
        capability="bounded_code_change",
    )
    db = AgentDB()

    result = claim_reddog_signed_worker_dispatch_tasks_until_idle(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
        max_claims=3,
    )

    assert result["accepted"] is True
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_IDLE
    assert result["claimed_count"] == 0
    assert db.get_autonomous_task_by_id(task_id)["status"] == "pending"


def test_openclaw_claim_loop_stops_after_first_rejected_claim(tmp_path: Path) -> None:
    task_id_1 = _publish_agentdb_task(
        intent_id="worker_dispatch_intent_openclaw_candidate_1"
    )
    task_id_2 = _publish_agentdb_task(
        intent_id="worker_dispatch_intent_openclaw_candidate_2"
    )
    db = AgentDB()

    result = claim_reddog_signed_worker_dispatch_tasks_until_idle(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(accepted=False),
        max_claims=5,
    )

    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_REJECT
    assert result["claimed_count"] == 1
    assert len(result["failed_task_ids"]) == 1
    assert SignedWorkerOpenClawClaimReason.CLAIM_REJECTED in result["rejection_reasons"]
    statuses = {
        task_id_1: db.get_autonomous_task_by_id(task_id_1)["status"],
        task_id_2: db.get_autonomous_task_by_id(task_id_2)["status"],
    }
    assert sorted(statuses.values()) == ["failed", "pending"]


def test_claim_loop_no_effect_attestations_are_strict_booleans() -> None:
    result = _signed_worker_claim_loop_result(
        accepted=True,
        status=SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT,
        max_claims=1,
        claim_results=(
            {
                "no_shell_command_executed": "false",
                "no_repo_mutation_performed": True,
                "no_holoindex_reindex_performed": True,
                "no_hermes_dispatch_performed": True,
                "no_worktree_operation_performed": True,
                "no_pr_created": True,
                "no_live_foundup_enqueue_performed": True,
                "no_pattern_memory_write_performed": True,
                "no_reward_settlement_performed": True,
            },
        ),
        completed_task_ids=("task-1",),
    )

    assert result["no_shell_command_executed"] is False
    assert result["no_repo_mutation_performed"] is True


def test_openclaw_claim_loop_rejects_invalid_max_claims(tmp_path: Path) -> None:
    result = claim_reddog_signed_worker_dispatch_tasks_until_idle(
        repo_root=tmp_path,
        signed_worker_runner=_FakeRunner(),
        max_claims=0,
    )

    assert result["accepted"] is False
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_REJECT
    assert (
        SignedWorkerOpenClawClaimReason.MAX_CLAIMS_INVALID
        in result["rejection_reasons"]
    )
