"""Tests for REDDOG_READONLY_AUDIT_TASK_REPORT_EXECUTOR_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.scripts.run_task import execute_task
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
    READONLY_AUDIT_TASK_SKILL,
    READONLY_AUDIT_TASK_SOURCE,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime import (
    MODEL_WORKER_MODE,
    REPO_CODE_AUDIT_LANE,
    FoundupsFusionRepoAuditModelRunner,
    CodeIndexReadOnlyQueryAdapter,
    HoloIndexReadOnlyQueryAdapter,
    RepoAuditModelResult,
)
import modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime as readonly_worker_runtime
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_task_executor import (
    AUTHORITATIVE_WORK_STATE_REFRESH_SLICE,
    READONLY_AUDIT_LANE_ANALYZER_SLICE,
    READONLY_AUDIT_TASK_REPORT_ACCEPT,
    READONLY_AUDIT_TASK_REPORT_REJECT,
    ReadOnlyAuditTaskRejectReason,
    execute_reddog_readonly_audit_task,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
    canonical_reddog_wsp15_allocation_digest,
)
from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_readonly_audit_task_executor.py"
)
MODEL_WORKER_MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_readonly_0102_audit_worker_runtime.py"
)


@pytest.fixture(autouse=True)
def isolated_agent_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    DatabaseManager.reset_for_tests()
    yield
    DatabaseManager.reset_for_tests()


class _FakeQueryAdapter:
    def __init__(self, *, ok: bool = True, error: str = "", freshness: str = "FRESH") -> None:
        self.ok = ok
        self.error = error
        self.freshness = freshness
        self.calls = []

    def query(self, *, query: str, allowed_paths, limit: int):
        self.calls.append({"query": query, "allowed_paths": tuple(allowed_paths), "limit": limit})
        path = allowed_paths[0] if allowed_paths else "modules/communication/moltbot_bridge/src/sample.py"
        return {
            "ok": self.ok,
            "source": "fake",
            "query": query,
            "freshness": self.freshness,
            "hits": [
                {
                    "path": path,
                    "title": "fake hit",
                    "score": 0.99,
                    "digest": "sha256:index-hit",
                }
            ]
            if self.ok
            else [],
            "error": self.error,
        }


def _patch_default_query_adapters(monkeypatch) -> None:
    def fake_holo_query(self, *, query: str, allowed_paths, limit: int):
        return _FakeQueryAdapter().query(query=query, allowed_paths=allowed_paths, limit=limit)

    def fake_code_query(self, *, query: str, allowed_paths, limit: int):
        return _FakeQueryAdapter().query(query=query, allowed_paths=allowed_paths, limit=limit)

    monkeypatch.setattr(HoloIndexReadOnlyQueryAdapter, "query", fake_holo_query)
    monkeypatch.setattr(CodeIndexReadOnlyQueryAdapter, "query", fake_code_query)


class _EchoEvidenceModelRunner:
    def __init__(self, *, unknown_ref: bool = False) -> None:
        self.unknown_ref = unknown_ref
        self.calls = []

    def run_repo_code_audit(self, *, prompt: str, context: str, binding, timeout_seconds: int):
        self.calls.append({"prompt": prompt, "context": context, "binding": dict(binding)})
        parsed = json.loads(context)
        evidence_ref = parsed["untrusted_repository_evidence"][0]["evidence_ref"]
        if self.unknown_ref:
            evidence_ref = "file:missing.py:sha256:missing:lines:1"
        output = {
            "summary": "Model-backed repo audit verified supplied evidence.",
            "evidence_refs": [evidence_ref],
            "findings": [
                {
                    "finding_id": "repo-code-audit-finding-1",
                    "claim": "The worker used supplied repository evidence only.",
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
        )


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    target = root / "docs" / "work_ledger.schema.json"
    target.parent.mkdir(parents=True)
    target.write_text('{"schema": "work-ledger", "version": 1}\n', encoding="utf-8")
    other = root / "modules" / "communication" / "moltbot_bridge" / "src" / "sample.py"
    other.parent.mkdir(parents=True)
    other.write_text("VALUE = 1\n", encoding="utf-8")
    return root


def _repo_with_ledgers(tmp_path: Path) -> Path:
    root = tmp_path / "repo-ledgers"
    active = root / "docs" / "0102_session_briefings" / "ACTIVE_SLICE_LEDGER.md"
    active.parent.mkdir(parents=True)
    active.write_text(
        """# Active Slice Ledger

**Updated**: 2026-07-14

## Open Slices

| Slice | Priority | Blocked By | Notes |
|-------|----------|------------|-------|
| `REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1` | P0 | - | next |
""",
        encoding="utf-8",
    )
    ledger = root / "docs" / "0102_session_briefings" / "work_ledger.schema.json"
    ledger.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "last_updated": "2026-07-14T00:00:00Z",
                "slices": [
                    {
                        "slice_id": "REDDOG_JSON_SECONDARY_PHASE1",
                        "status": "PROPOSED",
                        "priority": "P1",
                        "wsp15_score": {"total": 16},
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return root


def _context() -> dict:
    return {
        "source": READONLY_AUDIT_TASK_SOURCE,
        "swarm_receipt": {
            "swarm_id": "swarm-1",
            "snapshot_receipt_id": "snapshot-1",
            "determination_id": "det-1",
        },
        "assignment": {
            "assignment_id": "assignment-1",
            "lane_id": "repo_code_audit",
            "snapshot_receipt_id": "snapshot-1",
            "allowed_read_targets": [
                "docs/work_ledger.schema.json",
                "modules/communication/moltbot_bridge/src/sample.py",
            ],
        },
        "forbidden_actions": [
            "repo_write",
            "shell_execute",
            "git_push",
            "openclaw_enqueue",
            "holoindex_reindex",
        ],
    }


def _model_context(
    *,
    allowed_read_targets: tuple[str, ...] | None = None,
    requested_operation: str = "repo_code_audit",
    prompt_text: str = "Run model-backed RedDog repo code audit.",
) -> dict:
    context = _context()
    if allowed_read_targets is not None:
        context["assignment"] = dict(context["assignment"])
        context["assignment"]["allowed_read_targets"] = list(allowed_read_targets)
    allocation = allocate_reddog_wsp15_receipt(
        requested_operation=requested_operation,
        prompt_text=prompt_text,
        allowed_read_targets=context["assignment"]["allowed_read_targets"],
    ).to_dict()
    context["worker_mode"] = MODEL_WORKER_MODE
    context["wsp15_allocation_receipt"] = allocation
    context["wsp15_allocation_receipt_id"] = allocation["receipt_id"]
    context["wsp15_allocation_digest"] = canonical_reddog_wsp15_allocation_digest(allocation)
    context["assignment"] = dict(context["assignment"])
    context["assignment"]["lane_id"] = REPO_CODE_AUDIT_LANE
    context["assignment"]["snapshot_content_digest"] = "sha256:snapshot-content"
    context["assignment"]["context_view_id"] = "sha256:context-view"
    context["assignment"]["evidence_bundle_id"] = "sha256:evidence-bundle"
    context["assignment"]["determination_id"] = "sha256:determination"
    context["assignment"]["wsp15_allocation_receipt_id"] = allocation["receipt_id"]
    context["assignment"]["wsp15_allocation_digest"] = context["wsp15_allocation_digest"]
    return context


def _ledger_context() -> dict:
    context = _context()
    context["assignment"] = dict(context["assignment"])
    context["assignment"]["allowed_read_targets"] = [
        "docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md",
        "docs/0102_session_briefings/work_ledger.schema.json",
    ]
    return context


def test_readonly_audit_executor_reads_only_allowlisted_targets(tmp_path: Path) -> None:
    root = _repo(tmp_path)

    result = execute_reddog_readonly_audit_task(task_context=_context(), repo_root=root)

    assert result.accepted is True
    assert result.decision == READONLY_AUDIT_TASK_REPORT_ACCEPT
    assert result.no_repo_mutation_performed is True
    assert result.no_shell_command_executed is True
    assert result.no_holoindex_reindex_performed is True
    assert result.report is not None
    assert result.report["repo_mutation_performed"] is False
    assert result.report["execution_performed"] is False
    assert result.report["openclaw_enqueue_performed"] is False
    assert len(result.report["evidence_refs"]) == 2
    assert all(ref.startswith("file:") for ref in result.report["evidence_refs"])
    assert len(result.report["findings"]) == 1
    finding = result.report["findings"][0]
    assert finding["finding_id"] == "repo_code_audit:lane_analyzer_missing"
    assert finding["wsp97_label"] == "SPECIFIED_NOT_IMPLEMENTED"
    assert finding["recommended_action"] == "FIX"
    assert finding["next_slice_name"] == READONLY_AUDIT_LANE_ANALYZER_SLICE
    assert set(finding["evidence_refs"]) == set(result.report["evidence_refs"])


def test_model_backed_repo_code_audit_accepts_strict_evidence_bound_report(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runner = _EchoEvidenceModelRunner()
    holo = _FakeQueryAdapter()
    code = _FakeQueryAdapter()

    result = execute_reddog_readonly_audit_task(
        task_context=_model_context(),
        repo_root=root,
        task_id="task-1",
        model_runner=runner,
        holoindex_adapter=holo,
        codeindex_adapter=code,
    )

    assert result.accepted is True
    assert result.decision == READONLY_AUDIT_TASK_REPORT_ACCEPT
    assert result.no_model_call_performed is False
    assert result.no_repo_mutation_performed is True
    assert result.no_holoindex_reindex_performed is True
    assert runner.calls
    assert holo.calls and code.calls
    assert result.report is not None
    assert result.report["model_backed_0102_worker_performed"] is True
    assert result.report["worker_receipt"]["schema_version"] == "readonly_0102_audit_worker_receipt.v1"
    assert result.report["worker_receipt"]["model_receipt_id"] == "model-receipt-1"
    assert result.report["worker_receipt"]["model_route_receipt_id"].startswith("sha256:")
    assert result.report["findings"][0]["evidence_refs"][0] in result.report["evidence_refs"]


def test_model_backed_discovers_index_candidate_before_direct_read(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runner = _EchoEvidenceModelRunner()
    context = _model_context(allowed_read_targets=("docs/work_ledger.schema.json",))

    result = execute_reddog_readonly_audit_task(
        task_context=context,
        repo_root=root,
        task_id="task-1",
        model_runner=runner,
        holoindex_adapter=_FakeQueryAdapter(),
        codeindex_adapter=_FakeQueryAdapter(),
    )

    assert result.accepted is True
    assert result.report is not None
    evidence_paths = {item["path"] for item in result.report["target_evidence"]}
    assert "docs/work_ledger.schema.json" in evidence_paths
    assert "modules/communication/moltbot_bridge/src/sample.py" in evidence_paths
    assert runner.calls
    context_payload = json.loads(runner.calls[0]["context"])
    assert len(context_payload["untrusted_repository_evidence"]) == 2


def test_model_backed_repo_code_audit_rejects_unknown_evidence_ref(tmp_path: Path) -> None:
    root = _repo(tmp_path)

    result = execute_reddog_readonly_audit_task(
        task_context=_model_context(),
        repo_root=root,
        task_id="task-1",
        model_runner=_EchoEvidenceModelRunner(unknown_ref=True),
        holoindex_adapter=_FakeQueryAdapter(),
        codeindex_adapter=_FakeQueryAdapter(),
    )

    assert result.accepted is False
    assert any(ReadOnlyAuditTaskRejectReason.UNKNOWN_EVIDENCE_REF in reason for reason in result.rejection_reasons)


def test_model_backed_rejects_stale_holoindex_receipt_before_model_call(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runner = _EchoEvidenceModelRunner()

    result = execute_reddog_readonly_audit_task(
        task_context=_model_context(),
        repo_root=root,
        task_id="task-1",
        model_runner=runner,
        holoindex_adapter=_FakeQueryAdapter(freshness="STALE"),
        codeindex_adapter=_FakeQueryAdapter(),
    )

    assert result.accepted is False
    assert ReadOnlyAuditTaskRejectReason.INDEX_QUERY_STALE in result.rejection_reasons
    assert not runner.calls


def test_model_backed_rejects_holoindex_error_before_model_call(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runner = _EchoEvidenceModelRunner()

    result = execute_reddog_readonly_audit_task(
        task_context=_model_context(),
        repo_root=root,
        task_id="task-1",
        model_runner=runner,
        holoindex_adapter=_FakeQueryAdapter(ok=False, error="holoindex_unavailable"),
        codeindex_adapter=_FakeQueryAdapter(),
    )

    assert result.accepted is False
    assert ReadOnlyAuditTaskRejectReason.INDEX_QUERY_FAILED in result.rejection_reasons
    assert not runner.calls


def test_model_backed_rejects_wsp15_binding_digest_mismatch(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    context = _model_context()
    context["assignment"] = dict(context["assignment"])
    context["assignment"]["wsp15_allocation_digest"] = "sha256:tampered"

    result = execute_reddog_readonly_audit_task(
        task_context=context,
        repo_root=root,
        task_id="task-1",
        model_runner=_EchoEvidenceModelRunner(),
        holoindex_adapter=_FakeQueryAdapter(),
        codeindex_adapter=_FakeQueryAdapter(),
    )

    assert result.accepted is False
    assert ReadOnlyAuditTaskRejectReason.WSP15_BINDING_MISMATCH in result.rejection_reasons


def test_model_backed_rejects_regular_allocation_without_fusion_requirement(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    context = _model_context()
    allocation = allocate_reddog_wsp15_receipt(
        requested_operation="answer_simple_question",
        prompt_text="Say hello.",
    ).to_dict()
    context["wsp15_allocation_receipt"] = allocation
    context["wsp15_allocation_receipt_id"] = allocation["receipt_id"]
    context["wsp15_allocation_digest"] = canonical_reddog_wsp15_allocation_digest(allocation)
    context["assignment"] = dict(context["assignment"])
    context["assignment"]["wsp15_allocation_receipt_id"] = allocation["receipt_id"]
    context["assignment"]["wsp15_allocation_digest"] = context["wsp15_allocation_digest"]

    result = execute_reddog_readonly_audit_task(
        task_context=context,
        repo_root=root,
        task_id="task-1",
        model_runner=_EchoEvidenceModelRunner(),
        holoindex_adapter=_FakeQueryAdapter(),
        codeindex_adapter=_FakeQueryAdapter(),
    )

    assert result.accepted is False
    assert ReadOnlyAuditTaskRejectReason.WSP15_FUSION_REQUIRED in result.rejection_reasons


def test_model_backed_rejects_invalid_recommended_action_enum(tmp_path: Path) -> None:
    root = _repo(tmp_path)

    class BadActionRunner(_EchoEvidenceModelRunner):
        def run_repo_code_audit(self, *, prompt: str, context: str, binding, timeout_seconds: int):
            result = super().run_repo_code_audit(
                prompt=prompt,
                context=context,
                binding=binding,
                timeout_seconds=timeout_seconds,
            )
            payload = json.loads(result.content)
            payload["findings"][0]["recommended_action"] = "DO_ANYTHING"
            return RepoAuditModelResult(
                ok=True,
                status="MODEL_OK",
                content=json.dumps(payload, sort_keys=True),
                model_receipt_id="model-receipt-1",
                model_result_digest="sha256:model-result-1",
                made_network_call=True,
            )

    result = execute_reddog_readonly_audit_task(
        task_context=_model_context(),
        repo_root=root,
        task_id="task-1",
        model_runner=BadActionRunner(),
        holoindex_adapter=_FakeQueryAdapter(),
        codeindex_adapter=_FakeQueryAdapter(),
    )

    assert result.accepted is False
    assert any("recommended_action" in reason for reason in result.rejection_reasons)


def test_model_backed_rejects_stop_with_next_slice(tmp_path: Path) -> None:
    root = _repo(tmp_path)

    class StopWithSliceRunner(_EchoEvidenceModelRunner):
        def run_repo_code_audit(self, *, prompt: str, context: str, binding, timeout_seconds: int):
            result = super().run_repo_code_audit(
                prompt=prompt,
                context=context,
                binding=binding,
                timeout_seconds=timeout_seconds,
            )
            payload = json.loads(result.content)
            payload["findings"][0]["recommended_action"] = "STOP"
            payload["findings"][0]["next_slice_name"] = "SHOULD_NOT_EXIST_PHASE1"
            return RepoAuditModelResult(
                ok=True,
                status="MODEL_OK",
                content=json.dumps(payload, sort_keys=True),
                model_receipt_id="model-receipt-1",
                model_result_digest="sha256:model-result-1",
                made_network_call=True,
            )

    result = execute_reddog_readonly_audit_task(
        task_context=_model_context(),
        repo_root=root,
        task_id="task-1",
        model_runner=StopWithSliceRunner(),
        holoindex_adapter=_FakeQueryAdapter(),
        codeindex_adapter=_FakeQueryAdapter(),
    )

    assert result.accepted is False
    assert any("stop_next_slice" in reason for reason in result.rejection_reasons)


def test_production_runner_uses_fusion_synthesis_excerpt_for_json(tmp_path: Path, monkeypatch) -> None:
    root = _repo(tmp_path)
    monkeypatch.setenv("REDDOG_READONLY_AUDIT_RUNTIME_MODE", "foundups_fusion")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def fake_fusion(api_key, redacted_prompt, history, payload):  # noqa: ANN001, ARG001
        import re

        match = re.search(r"file:[^\"\\]+:lines:\d+", str(redacted_prompt))
        evidence_ref = match.group(0) if match else ""
        return {
            "ok": True,
            "content": "## Lead\nnot json\n## Synthesis\nnot json",
            "review_packet": {
                "receipt_id": "fusion-receipt-1",
                "synthesis_excerpt": json.dumps(
                    {
                        "summary": "Synthesis JSON accepted.",
                        "evidence_refs": [evidence_ref],
                        "findings": [
                            {
                                "finding_id": "synthesis-json-1",
                                "claim": "The worker parsed the Fusion synthesis excerpt.",
                                "wsp97_label": "OBSERVED",
                                "recommended_action": "FIX",
                                "wsp15_priority": "P1",
                                "severity": "MAJOR",
                                "evidence_refs": [evidence_ref],
                                "next_slice_name": "REDDOG_NEXT_RUNTIME_SLICE_PHASE1",
                            }
                        ],
                    },
                    sort_keys=True,
                ),
            },
        }

    monkeypatch.setattr(readonly_worker_runtime, "_load_foundups_fusion_runner", lambda: fake_fusion)

    result = execute_reddog_readonly_audit_task(
        task_context=_model_context(),
        repo_root=root,
        task_id="task-1",
        model_runner=FoundupsFusionRepoAuditModelRunner(),
        holoindex_adapter=_FakeQueryAdapter(),
        codeindex_adapter=_FakeQueryAdapter(),
    )

    assert result.accepted is True
    assert result.report is not None
    assert result.report["summary"] == "Synthesis JSON accepted."
    assert result.report["worker_receipt"]["model_route_receipt"]["made_network_call"] is True


def test_model_backed_requires_valid_wsp15_receipt(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    context = _model_context()
    context["wsp15_allocation_receipt"] = dict(context["wsp15_allocation_receipt"])
    context["wsp15_allocation_receipt"]["complexity"] = False

    result = execute_reddog_readonly_audit_task(
        task_context=context,
        repo_root=root,
        task_id="task-1",
        model_runner=_EchoEvidenceModelRunner(),
    )

    assert result.accepted is False
    assert ReadOnlyAuditTaskRejectReason.MALFORMED_WSP15_ALLOCATION in result.rejection_reasons


def test_readonly_audit_executor_uses_lane_reconciler_when_ledgers_are_available(tmp_path: Path) -> None:
    root = _repo_with_ledgers(tmp_path)

    result = execute_reddog_readonly_audit_task(task_context=_ledger_context(), repo_root=root)

    assert result.accepted is True
    assert result.report is not None
    assert len(result.report["findings"]) == 1
    finding = result.report["findings"][0]
    assert finding["wsp97_label"] == "OBSERVED"
    assert finding["recommended_action"] == "FIX"
    assert finding["next_slice_name"] == "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1"
    assert finding["reconciliation_report_id"]
    assert finding["next_wsp15_queue"][0] == "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1"
    assert set(finding["evidence_refs"]) == set(result.report["evidence_refs"])


def test_readonly_audit_executor_routes_conflicted_ledgers_to_refresh_runtime(tmp_path: Path) -> None:
    root = _repo_with_ledgers(tmp_path)
    active = root / "docs" / "0102_session_briefings" / "ACTIVE_SLICE_LEDGER.md"
    active.write_text(
        """# Active Slice Ledger

**Updated**: 2026-07-14

## Closed Slices

| Slice | Commit | Evidence |
|-------|--------|----------|
| `REDDOG_DONE_PHASE1` | `abc1234` | done |
""",
        encoding="utf-8",
    )
    ledger = root / "docs" / "0102_session_briefings" / "work_ledger.schema.json"
    ledger.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "last_updated": "2026-07-14T00:00:00Z",
                "slices": [{"slice_id": "REDDOG_DONE_PHASE1", "status": "IN_PROGRESS"}],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    result = execute_reddog_readonly_audit_task(task_context=_ledger_context(), repo_root=root)

    assert result.accepted is True
    assert result.report is not None
    finding = result.report["findings"][0]
    assert finding["recommended_action"] == "REVISE"
    assert finding["wsp15_priority"] == "P0"
    assert finding["severity"] == "BLOCKER"
    assert finding["next_slice_name"] == AUTHORITATIVE_WORK_STATE_REFRESH_SLICE
    assert finding["conflict_count"] == 1


def test_readonly_audit_executor_rejects_wrong_source_or_missing_assignment(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    wrong = dict(_context())
    wrong["source"] = "other"
    missing = dict(_context())
    missing.pop("assignment")

    wrong_result = execute_reddog_readonly_audit_task(task_context=wrong, repo_root=root)
    missing_result = execute_reddog_readonly_audit_task(task_context=missing, repo_root=root)

    assert wrong_result.accepted is False
    assert wrong_result.decision == READONLY_AUDIT_TASK_REPORT_REJECT
    assert ReadOnlyAuditTaskRejectReason.WRONG_SOURCE in wrong_result.rejection_reasons
    assert missing_result.accepted is False
    assert ReadOnlyAuditTaskRejectReason.MISSING_ASSIGNMENT in missing_result.rejection_reasons


def test_readonly_audit_executor_rejects_traversal_secret_and_missing_targets(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    traversal = _context()
    traversal["assignment"] = dict(traversal["assignment"])
    traversal["assignment"]["allowed_read_targets"] = ["../secret.txt"]
    secret = _context()
    secret["assignment"] = dict(secret["assignment"])
    secret["assignment"]["allowed_read_targets"] = [".env"]
    missing = _context()
    missing["assignment"] = dict(missing["assignment"])
    missing["assignment"]["allowed_read_targets"] = ["docs/missing.md"]

    assert ReadOnlyAuditTaskRejectReason.UNSAFE_TARGET in execute_reddog_readonly_audit_task(
        task_context=traversal,
        repo_root=root,
    ).rejection_reasons
    assert ReadOnlyAuditTaskRejectReason.UNSAFE_TARGET in execute_reddog_readonly_audit_task(
        task_context=secret,
        repo_root=root,
    ).rejection_reasons
    assert ReadOnlyAuditTaskRejectReason.UNSAFE_TARGET in execute_reddog_readonly_audit_task(
        task_context=missing,
        repo_root=root,
    ).rejection_reasons


def test_run_task_executes_reddog_readonly_audit_before_wre(tmp_path: Path, monkeypatch) -> None:
    root = _repo(tmp_path)
    monkeypatch.setenv("WRE_MOCK_SKILLS", READONLY_AUDIT_TASK_SKILL)
    db = AgentDB()
    task_id = "readonly-audit-task-1"
    assert db.create_autonomous_task(
        task_id=task_id,
        description="RedDog read-only audit lane: repo_code_audit",
        required_skills=[READONLY_AUDIT_TASK_SKILL],
        estimated_complexity=0.35,
        priority_score=0.85,
        context=_context(),
        origin_continuity_id="det-1",
    )
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")

    result = execute_task(task_id, repo_root=root)

    assert result["ok"] is True
    assert result["executor"] == "reddog:readonly_audit"
    assert result["structured_result"]["accepted"] is True
    assert db.get_autonomous_task_by_id(task_id)["status"] == "completed"


def test_run_task_model_backed_task_fails_closed_without_runtime_mode(tmp_path: Path, monkeypatch) -> None:
    root = _repo(tmp_path)
    monkeypatch.setenv("WRE_MOCK_SKILLS", READONLY_AUDIT_TASK_SKILL)
    monkeypatch.delenv("REDDOG_READONLY_AUDIT_RUNTIME_MODE", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    _patch_default_query_adapters(monkeypatch)
    db = AgentDB()
    task_id = "readonly-audit-model-task-1"
    assert db.create_autonomous_task(
        task_id=task_id,
        description="RedDog read-only audit lane: repo_code_audit",
        required_skills=[READONLY_AUDIT_TASK_SKILL],
        estimated_complexity=0.35,
        priority_score=0.85,
        context=_model_context(),
        origin_continuity_id="det-1",
    )
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")

    result = execute_task(task_id, repo_root=root)

    assert result["ok"] is False
    assert result["executor"] == "reddog:readonly_audit"
    assert ReadOnlyAuditTaskRejectReason.MODEL_FAILURE in result["detail"]
    assert "runtime_mode_not_enabled" in result["detail"]
    assert db.get_autonomous_task_by_id(task_id)["status"] == "failed"


def test_agentdb_openclaw_claim_run_task_model_worker_persists_report(tmp_path: Path, monkeypatch) -> None:
    root = _repo(tmp_path)
    monkeypatch.setenv("WRE_MOCK_SKILLS", READONLY_AUDIT_TASK_SKILL)
    _patch_default_query_adapters(monkeypatch)

    def fake_run(self, *, prompt: str, context: str, binding, timeout_seconds: int):
        parsed = json.loads(context)
        evidence_ref = parsed["untrusted_repository_evidence"][0]["evidence_ref"]
        output = {
            "summary": "Injected production runner method accepted evidence.",
            "evidence_refs": [evidence_ref],
            "findings": [
                {
                    "finding_id": "repo-code-audit-run-task-finding",
                    "claim": "run_task dispatched the model-backed read-only worker and persisted its report.",
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
            model_receipt_id="model-receipt-run-task",
            model_result_digest="sha256:model-result-run-task",
            made_network_call=False,
        )

    monkeypatch.setattr(FoundupsFusionRepoAuditModelRunner, "run_repo_code_audit", fake_run)
    db = AgentDB()
    task_id = "readonly-audit-model-task-2"
    assert db.create_autonomous_task(
        task_id=task_id,
        description="RedDog read-only audit lane: repo_code_audit",
        required_skills=[READONLY_AUDIT_TASK_SKILL],
        estimated_complexity=0.35,
        priority_score=0.85,
        context=_model_context(),
        origin_continuity_id="det-1",
    )
    assert db.assign_autonomous_task(task_id, "openclaw_supervisor")

    result = execute_task(task_id, repo_root=root)

    assert result["ok"] is True
    assert result["executor"] == "reddog:readonly_audit"
    assert result["structured_result"]["accepted"] is True
    assert result["readonly_audit_report_persist"]["accepted"] is True
    stored = db.db.execute_query("SELECT report_json FROM reddog_readonly_audit_reports")
    assert len(stored) == 1
    assert db.get_autonomous_task_by_id(task_id)["status"] == "completed"


def test_executor_module_ast_has_no_mutation_network_or_runtime_wiring() -> None:
    sources = [
        MODULE_PATH.read_text(encoding="utf-8"),
        MODEL_WORKER_MODULE_PATH.read_text(encoding="utf-8"),
    ]
    source = "\n".join(sources)
    trees = [ast.parse(item) for item in sources]
    forbidden_text = (
        "subprocess",
        "requests",
        "socket",
        "openclaw_supervisor",
        "hermes_job_executor",
        "execute_skill",
        "holo_index.py --index",
        "create_autonomous_task",
        "write_text",
        "mkdir",
        "git push",
        "gh pr",
    )
    for token in forbidden_text:
        assert token not in source

    imported = set()
    calls = set()
    attrs = set()
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
            elif isinstance(node, ast.Attribute):
                attrs.add(node.attr)

    assert not (imported & {"subprocess", "requests", "socket", "urllib", "shutil"})
    assert not (calls & {"eval", "exec", "compile", "system", "popen", "run", "Popen"})
    assert not (attrs & {"write_text", "mkdir", "unlink", "rmdir"})
