"""Tests for REDDOG_RESIDENT_ARCHITECT_DURABLE_AGENTDB_CYCLE_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from holo_index.freshness_receipt import HoloIndexFreshnessReceipt
from holo_index.repository_state import RepositoryState
from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ArchitectModelResult,
    InMemoryArchitectDeterminationStore,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
    READONLY_AUDIT_TASK_SOURCE,
)
from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    SCHEMA_VERSION as GROUNDING_SCHEMA_VERSION,
    canonical_digest as grounding_digest,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime import (
    RepoAuditModelResult,
)
import modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime as readonly_worker_runtime
from modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle import (
    REDDOG_RESIDENT_CYCLE_ACCEPT,
    STATUS_DETERMINED,
    STATUS_TIMED_OUT,
    NoopExternalResearchRetriever,
    ResidentCycleReason,
    run_reddog_resident_architect_durable_agentdb_cycle,
)
from modules.communication.moltbot_bridge.tests.holoindex_freshness_receipt_test_helpers import (
    build_fresh_holoindex_receipt,
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
    / "reddog_resident_architect_durable_agentdb_cycle.py"
)
NOW = "2026-07-16T00:00:00+00:00"
HEAD = "f9ac824d8"
REVISION = "sha256:resident-work-state"
WORK_FOCUS = "resident RedDog architect audit"


def _grounding_receipt() -> dict[str, object]:
    typed = {
        "repo_file_targets": [
            "modules/communication/moltbot_bridge/src/reddog_operational_context_snapshot.py"
        ],
        "semantic_targets": [],
        "external_research_targets": [],
        "quoted_reference_blocks_count": 0,
        "quoted_reference_blocks_digest": grounding_digest([]),
    }
    value = {
        "schema_version": GROUNDING_SCHEMA_VERSION,
        "source_surface": "editor_thin_client",
        "work_focus_digest": grounding_digest({"work_focus": WORK_FOCUS}),
        "typed_targets": typed,
        "typed_targets_digest": grounding_digest(typed),
        "grounding_preflight_applied": True,
        "grounding_preflight_passed": True,
        "grounding_preflight_rejection_reasons": [],
        "grounding_target_universe_required": True,
        "repo_file_targets_count": 1,
        "semantic_targets_count": 0,
        "external_research_targets_count": 0,
        "quoted_reference_blocks_count": 0,
        "semantic_target_coverage": [],
        "semantic_target_coverage_digest": grounding_digest({"semantic_target_coverage": []}),
        "target_recall_ok": True,
        "required_targets_missing": [],
        "direct_read_paths": [],
        "holoindex_owner_query_ok": False,
        "holoindex_freshness": "UNKNOWN",
        "holoindex_generation_id": "",
        "holoindex_freshness_receipt_digest": "",
        "holoindex_repo_head_sha": "",
        "holoindex_query_receipt_id": "",
        "holoindex_index_gap_detected": False,
        "no_holoindex_reindex_performed": True,
    }
    value["receipt_id"] = grounding_digest(value)
    return value


@pytest.fixture(autouse=True)
def isolated_agent_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    monkeypatch.setattr(
        readonly_worker_runtime,
        "read_repository_state",
        lambda *args, **kwargs: RepositoryState(
            head_sha=HEAD,
            clean=True,
            state_digest="sha256:resident-clean",
        ),
    )
    DatabaseManager.reset_for_tests()
    yield
    DatabaseManager.reset_for_tests()


def _intent() -> dict[str, object]:
    return {
        "schema_version": "reddog_intent.v2",
        "intent_id": "sha256:intent-resident-cycle",
        "origin": "extension",
        "principal_ref": "012",
        "work_focus": WORK_FOCUS,
        "grounding_receipt": _grounding_receipt(),
        "submits_executable_authority": False,
    }


def _repo_state() -> dict[str, object]:
    return {
        "head_sha": HEAD,
        "dirty_paths": (),
        "dirty_digest": "sha256:clean",
        "worktree_digest": "sha256:worktrees",
    }


def _work_state() -> dict[str, object]:
    return {
        "schema_version": "reddog_authoritative_work_state.v1",
        "revision": REVISION,
        "selected_slice": "REDDOG_RESIDENT_ARCHITECT_DURABLE_AGENTDB_CYCLE_PHASE1",
        "refresh_receipt_id": "sha256:refresh-resident",
        "worker_claims": [
            {
                "claim_id": "claim-resident",
                "slice_id": "REDDOG_RESIDENT_ARCHITECT_DURABLE_AGENTDB_CYCLE_PHASE1",
            }
        ],
        "wre_queue_items": [{"queue_item_id": "queue-resident", "claim_id": "claim-resident"}],
    }


def _foundup_work_state() -> dict[str, object]:
    state = dict(_work_state())
    state["worker_claims"] = [
        {
            "claim_id": "claim-resident",
            "slice_id": "REDDOG_RESIDENT_ARCHITECT_DURABLE_AGENTDB_CYCLE_PHASE1",
            "foundup_id": "foundups_agent",
        }
    ]
    state["wre_queue_items"] = [
        {"queue_item_id": "queue-resident", "claim_id": "claim-resident", "foundup_id": "foundups_agent"}
    ]
    return state


def _fresh_holo_receipt() -> HoloIndexFreshnessReceipt:
    return build_fresh_holoindex_receipt(
        generated_at=NOW,
        repo_root=REPO_ROOT,
        head_sha=HEAD,
    )


class _FakeQueryAdapter:
    def __init__(self) -> None:
        self.calls = []

    def query(self, *, query: str, allowed_paths, limit: int):
        self.calls.append({"query": query, "allowed_paths": tuple(allowed_paths), "limit": limit})
        path = allowed_paths[0] if allowed_paths else "docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md"
        return {
            "ok": True,
            "source": "fake",
            "query": query,
            "freshness": "FRESH",
            "hits": [{"path": path, "title": "fake hit", "score": 0.99, "digest": "sha256:index-hit"}],
            "error": "",
            "freshness_generation_id": "sha256:holo-generation-resident",
            "freshness_receipt_digest": "sha256:holo-receipt-resident",
            "freshness_receipt_path": "E:/HoloIndex/indexes/holoindex_freshness_receipt.json",
            "repo_head_sha": HEAD,
        }


class _FakeExternalResearchRetriever:
    def __init__(self) -> None:
        self.calls = []

    def fetch(self, target):
        self.calls.append(dict(target))
        return {
            "source_url": str(target.get("url") or "https://github.com/FOUNDUPS/Foundups-Agent"),
            "source_type": "github",
            "fetched_at": 1000,
            "content_sha256": "a" * 64,
            "provenance_refs": ["github:FOUNDUPS/Foundups-Agent@main"],
            "freshness_receipt_digest": "sha256:" + "b" * 64,
            "finding_status": "candidate",
            "content_text": "Repository metadata snapshot.",
        }


class _AuditModelRunner:
    def __init__(self) -> None:
        self.calls = []

    def run_repo_code_audit(self, *, prompt: str, context: str, binding, timeout_seconds: int):
        self.calls.append({"prompt": prompt, "context": context, "binding": dict(binding)})
        parsed_context = json.loads(context)
        parsed_prompt = json.loads(prompt)
        evidence_ref = parsed_context["untrusted_repository_evidence"][0]["evidence_ref"]
        lane_id = parsed_prompt["assignment"]["lane_id"]
        output = {
            "summary": f"{lane_id} verified read-only resident-cycle evidence.",
            "evidence_refs": [evidence_ref],
            "findings": [
                {
                    "finding_id": f"{lane_id}:resident-cycle",
                    "claim": f"{lane_id} supports continuing the resident AgentDB cycle.",
                    "wsp97_label": "OBSERVED",
                    "recommended_action": "FIX",
                    "wsp15_priority": "P1",
                    "severity": "MAJOR",
                    "evidence_refs": [evidence_ref],
                    "next_slice_name": "REDDOG_RESIDENT_RUNTIME_NEXT_PHASE1",
                }
            ],
        }
        return RepoAuditModelResult(
            ok=True,
            status="MODEL_OK",
            content=json.dumps(output, sort_keys=True),
            model_receipt_id=f"model-receipt-{lane_id}",
            model_result_digest=f"sha256:model-result-{lane_id}",
            made_network_call=True,
        )


class _ArchitectRunner:
    def __init__(self) -> None:
        self.calls = []

    def run_architect_determination(self, *, prompt: str, context: str, binding, timeout_seconds: int):
        self.calls.append({"prompt": prompt, "context": context, "binding": dict(binding)})
        parsed = json.loads(prompt)
        evidence_ref = parsed["reports"][0]["evidence_refs"][0]
        content = {
            "action": "FIX",
            "next_slice_name": "REDDOG_RESIDENT_RUNTIME_NEXT_PHASE1",
            "summary": "Read-only OpenClaw audit reports support one next resident runtime slice.",
            "decision_reasons": ["selected highest-priority verified report"],
            "evidence_refs": [evidence_ref],
            "wsp15_allocation_receipt_id": parsed["wsp15_allocation_receipt_id"],
        }
        return ArchitectModelResult(
            ok=True,
            status="MODEL_OK",
            content=json.dumps(content, sort_keys=True),
            model_receipt_id="architect-model-receipt-resident",
            model_result_digest="sha256:architect-model-result-resident",
            review_packet={"fusion_panel_quorum": {"passed": True}},
            made_network_call=True,
            rejection_reasons=(),
        )


def _runtime_kwargs(**overrides):
    kwargs = {
        "repo_root": REPO_ROOT,
        "red_dog_intent": _intent(),
        "repo_state_override": _repo_state(),
        "work_state_snapshot_override": _work_state(),
        "holoindex_receipt_override": _fresh_holo_receipt(),
        "now_iso": NOW,
        "architect_determination_store": InMemoryArchitectDeterminationStore(),
        "audit_model_runner": _AuditModelRunner(),
        "architect_model_runner": _ArchitectRunner(),
        "holoindex_adapter": _FakeQueryAdapter(),
        "codeindex_adapter": _FakeQueryAdapter(),
        "external_research_retriever": _FakeExternalResearchRetriever(),
    }
    kwargs.update(overrides)
    return kwargs


def test_durable_cycle_submits_agentdb_tasks_openclaw_claims_reports_and_determines() -> None:
    result = run_reddog_resident_architect_durable_agentdb_cycle(**_runtime_kwargs())

    assert result.accepted is True
    assert result.decision == REDDOG_RESIDENT_CYCLE_ACCEPT
    assert result.status == STATUS_DETERMINED
    assert result.snapshot_id
    assert result.determination_id
    assert len(result.task_ids) == 5
    assert result.task_status_counts == {"completed": 5}
    assert len(result.openclaw_claims) == 5
    assert all(claim["accepted"] is True for claim in result.openclaw_claims)
    assert result.architect_determination_id
    assert result.architect_action == "FIX"
    assert result.queue_candidate_count == 1
    assert result.read_only_authority_only is True
    assert result.no_repo_mutation_performed is True
    assert result.no_holoindex_reindex_performed is True

    tasks = AgentDB().get_autonomous_tasks(status="completed", limit=10)
    assert len([task for task in tasks if task["discovered_by"] == READONLY_AUDIT_TASK_SOURCE]) == 5


def test_durable_cycle_supplies_operational_memex_to_openclaw_workers() -> None:
    audit_runner = _AuditModelRunner()
    intent = dict(_intent())
    intent["principal_ref"] = "principal-012"

    result = run_reddog_resident_architect_durable_agentdb_cycle(
        **_runtime_kwargs(
            red_dog_intent=intent,
            work_state_snapshot_override=_foundup_work_state(),
            breadcrumbs=[
                {
                    "breadcrumb_id": "crumb-resident",
                    "continuity_id": "REDDOG_RESIDENT_ARCHITECT_DURABLE_AGENTDB_CYCLE_PHASE1",
                    "task_id": "task-resident",
                    "created_at": NOW,
                }
            ],
            brain_state={
                "available": True,
                "signature_digest": "sha256:brain-resident",
                "summary_digest": "sha256:brain-summary-resident",
                "record_count": 9,
            },
            memex_snapshot_supply_config={
                "foundup_id": "foundups_agent",
                "identity": {"foundup_id": "foundups_agent", "name": "Foundups Agent"},
                "roadmap_state": {
                    "foundup_id": "foundups_agent",
                    "roadmap_id": "resident-roadmap",
                    "version": "1",
                    "content_digest": "sha256:resident-roadmap",
                },
            },
            audit_model_runner=audit_runner,
        )
    )

    assert result.accepted is True
    assert result.status == STATUS_DETERMINED
    assert result.final_bootstrap is not None
    assert result.final_bootstrap.memex_snapshot_supply_attempted is False
    assert len(audit_runner.calls) == 5
    contexts = [json.loads(call["context"]) for call in audit_runner.calls]
    assert all(context["memex_query_receipt"]["source_class"] == "memex" for context in contexts)
    assert all(
        context["memex_query_receipt"]["freshness_generation_id"]
        == _fresh_holo_receipt().generation_id
        for context in contexts
    )
    assert all(context["memex_evidence_bundle"]["records"] for context in contexts)
    completed = AgentDB().get_autonomous_tasks(status="completed", limit=10)
    readonly_contexts = [
        task["context"] if isinstance(task["context"], dict) else json.loads(task["context"])
        for task in completed
        if task["discovered_by"] == READONLY_AUDIT_TASK_SOURCE
    ]
    assert readonly_contexts
    assert all(context["assignment"]["principal_id"] == "principal-012" for context in readonly_contexts)
    assert all(
        context["assignment"]["memex_holoindex_generation_id"]
        == _fresh_holo_receipt().generation_id
        for context in readonly_contexts
    )


def test_duplicate_intent_reconnects_to_persisted_cycle_without_new_claims() -> None:
    first = run_reddog_resident_architect_durable_agentdb_cycle(**_runtime_kwargs())
    assert first.accepted is True

    second = run_reddog_resident_architect_durable_agentdb_cycle(**_runtime_kwargs())

    assert second.accepted is True
    assert second.status == STATUS_DETERMINED
    assert second.cycle_id == first.cycle_id
    assert second.duplicate_intent_reused is True
    assert len(second.openclaw_claims) == len(first.openclaw_claims) == 5
    assert tuple(claim["task_id"] for claim in second.openclaw_claims) == tuple(
        claim["task_id"] for claim in first.openclaw_claims
    )
    assert AgentDB().get_autonomous_tasks(status="completed", limit=20)


def test_missing_external_research_retriever_uses_noop_receipt_instead_of_blocking_cycle() -> None:
    audit_runner = _AuditModelRunner()
    result = run_reddog_resident_architect_durable_agentdb_cycle(
        **_runtime_kwargs(
            audit_model_runner=audit_runner,
            external_research_retriever=None,
        )
    )

    assert result.accepted is True
    assert result.decision == REDDOG_RESIDENT_CYCLE_ACCEPT
    assert result.status == STATUS_DETERMINED
    assert result.task_status_counts == {"completed": 5}
    assert ResidentCycleReason.EXTERNAL_RESEARCH_RETRIEVER_MISSING not in result.rejection_reasons
    external_contexts = [
        json.loads(call["context"])
        for call in audit_runner.calls
        if json.loads(call["prompt"])["assignment"]["lane_id"] == "external_research_audit"
    ]
    assert len(external_contexts) == 1
    assert "external_research_query_receipt" not in external_contexts[0]
    assert "untrusted_external_research_evidence" not in external_contexts[0]
    assert AgentDB().get_autonomous_tasks(status="pending", limit=10) == []


def test_noop_external_research_retriever_returns_no_content_bearing_evidence() -> None:
    payload = NoopExternalResearchRetriever().fetch(
        {"url": "https://github.com/FOUNDUPS/Foundups-Agent"}
    )

    assert payload["source_type"] == "unconfigured"
    assert payload["finding_status"] == "missing"
    assert payload.get("content_text") in (None, "")
    assert payload.get("content_sha256") in (None, "")
    assert "approved_external_research_retriever_not_configured" in payload["rejection_reasons"]


def test_timeout_when_openclaw_does_not_claim_tasks() -> None:
    result = run_reddog_resident_architect_durable_agentdb_cycle(
        **_runtime_kwargs(max_claims=0)
    )

    assert result.accepted is False
    assert result.status == STATUS_TIMED_OUT
    assert ResidentCycleReason.TIMEOUT in result.rejection_reasons
    assert result.task_status_counts == {"pending": 5}
    assert result.architect_determination_id is None


def test_cancel_unknown_intent_returns_cancelled_without_side_effects() -> None:
    result = run_reddog_resident_architect_durable_agentdb_cycle(
        **_runtime_kwargs(cancel_requested=True)
    )

    assert result.accepted is False
    assert ResidentCycleReason.CANCELLED in result.rejection_reasons
    assert AgentDB().get_autonomous_tasks(status="pending", limit=10) == []


def test_runtime_module_has_no_shell_worktree_repo_mutation_or_reindex_imports() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "subprocess" not in imports
    forbidden_text = (
        "git push",
        "gh pr",
        "holo_index.py --index",
        "hermes_job_executor",
        "worktree add",
        "PatternMemory.promote",
    )
    for text in forbidden_text:
        assert text not in source
