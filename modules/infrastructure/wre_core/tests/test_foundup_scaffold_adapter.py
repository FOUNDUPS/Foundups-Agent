#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused contract tests for the create_foundup scaffold consumer route."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    FoundUpJob,
    PolicyFlags,
)
from modules.foundups.agent.src.create_foundup_dryrun import (
    plan_create_foundup_dry_run,
)
from modules.infrastructure.wre_core.src.foundup_job_consumer import (
    FoundUpJobConsumer,
)
from modules.infrastructure.wre_core.src.foundup_job_router import (
    RouteStatus,
    TargetBackend,
)
from modules.infrastructure.wre_core.src.foundup_scaffold_adapter import (
    CreateFoundUpDryRunScaffoldAdapter,
    ScaffoldAdapterResult,
    digest_scaffold_contract,
)


def _valid_envelope(foundup_id: str = "routing_widget") -> dict:
    return {
        "foundup_id": foundup_id,
        "name": "Routing Widget",
        "tagline": "A dry-run routing fixture",
        "description": "Valid genesis input for the scaffold routing contract.",
        "category": "tools",
        "lifecycle_stage": "idea",
        "binding_state": "unbound",
        "external_repo_requested": False,
        "created_at": 1_700_000_000.0,
        "acceptance_criteria": [
            {
                "observable": "route is simulated",
                "method": "pytest",
                "oracle": "typed plan",
                "pass_condition": "dry_run is true",
            }
        ],
        "truth_state_map": [
            {
                "feature": foundup_id,
                "marker": "IDEA_ONLY",
                "evidence": "",
            }
        ],
    }


def _empty_registry(tmp_path: Path) -> Path:
    path = tmp_path / "foundup_registry.json"
    path.write_text(json.dumps({"entities": []}), encoding="utf-8")
    return path


def _bound_job(tmp_path: Path) -> tuple[FoundUpJob, Path]:
    registry_path = _empty_registry(tmp_path)
    genesis_envelope = _valid_envelope()
    plan = plan_create_foundup_dry_run(
        genesis_envelope,
        registry_path=registry_path,
    )
    assert plan.ok is True, plan.rejection_reason
    contract = plan.scaffold_contract
    assert contract is not None
    job = FoundUpJob(
        job_id="job_create_routing_widget",
        tenant_id="tenant_creator",
        requested_action="create_foundup",
        foundup_id="routing_widget",
        policy_flags=PolicyFlags(dry_run_mode=True),
        payload={"genesis_envelope": genesis_envelope},
        creation_mode="new_scaffold",
        genesis_envelope_digest=contract["genesis_envelope_digest"],
        scaffold_contract_digest=digest_scaffold_contract(contract),
    )
    return job, registry_path


def test_default_adapter_returns_verified_side_effect_free_plan(tmp_path: Path):
    job, registry_path = _bound_job(tmp_path)
    before = registry_path.read_bytes()
    adapter = CreateFoundUpDryRunScaffoldAdapter(registry_path=registry_path)

    result = adapter.plan(job)

    assert result.ok is True
    assert result.reason_code == "OK_SCAFFOLD_PLAN"
    assert result.plan["dry_run"] is True
    assert result.plan["files_written"] == []
    assert result.plan["fam_called"] is False
    assert result.plan["hermes_called"] is False
    assert result.plan["registry_mutated"] is False
    assert result.plan["worktree_created"] is False
    assert registry_path.read_bytes() == before


def test_default_adapter_rejects_scaffold_digest_mismatch(tmp_path: Path):
    job, registry_path = _bound_job(tmp_path)
    job.scaffold_contract_digest = "sha256:" + ("f" * 64)
    adapter = CreateFoundUpDryRunScaffoldAdapter(registry_path=registry_path)

    result = adapter.plan(job)

    assert result.ok is False
    assert result.reason_code == "FAIL_SCAFFOLD_LINEAGE_MISMATCH"
    assert result.plan is None


def test_default_adapter_rejects_wrong_action_and_missing_genesis(tmp_path: Path):
    job, registry_path = _bound_job(tmp_path)
    adapter = CreateFoundUpDryRunScaffoldAdapter(registry_path=registry_path)

    job.requested_action = "build_foundup"
    wrong_action = adapter.plan(job)
    job.requested_action = "create_foundup"
    job.payload = {}
    missing_genesis = adapter.plan(job)

    assert wrong_action.reason_code == "FAIL_WRONG_SCAFFOLD_ACTION"
    assert missing_genesis.reason_code == "FAIL_MISSING_GENESIS_ENVELOPE"


def test_default_adapter_propagates_planner_rejection(tmp_path: Path):
    job, registry_path = _bound_job(tmp_path)
    job.payload["genesis_envelope"]["acceptance_criteria"] = []
    adapter = CreateFoundUpDryRunScaffoldAdapter(registry_path=registry_path)

    result = adapter.plan(job)

    assert result.ok is False
    assert result.reason_code == "FAIL_ENVELOPE_NOT_GATE_PASSED"


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("side_effect", "FAIL_SCAFFOLD_PLAN_SIDE_EFFECT"),
        ("missing_contract", "FAIL_MISSING_SCAFFOLD_CONTRACT"),
        ("foundup_mismatch", "FAIL_SCAFFOLD_FOUNDUP_MISMATCH"),
        ("genesis_mismatch", "FAIL_GENESIS_LINEAGE_MISMATCH"),
    ],
)
def test_default_adapter_rejects_untrusted_planner_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    expected_code: str,
):
    from modules.foundups.agent.src import create_foundup_dryrun

    job, registry_path = _bound_job(tmp_path)
    planner_result = plan_create_foundup_dry_run(
        job.payload["genesis_envelope"],
        registry_path=registry_path,
    )
    assert planner_result.ok is True
    if mutation == "side_effect":
        planner_result.files_written = ["unexpected.py"]
    elif mutation == "missing_contract":
        planner_result.scaffold_contract = None
    elif mutation == "foundup_mismatch":
        planner_result.scaffold_contract["foundup_id"] = "other_foundup"
    else:
        planner_result.scaffold_contract["genesis_envelope_digest"] = (
            "sha256:" + ("0" * 64)
        )
    monkeypatch.setattr(
        create_foundup_dryrun,
        "plan_create_foundup_dry_run",
        lambda *args, **kwargs: planner_result,
    )
    adapter = CreateFoundUpDryRunScaffoldAdapter(registry_path=registry_path)

    result = adapter.plan(job)

    assert result.ok is False
    assert result.reason_code == expected_code


def test_default_adapter_fails_closed_on_internal_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from modules.foundups.agent.src import create_foundup_dryrun

    job, registry_path = _bound_job(tmp_path)

    def _raise(*args, **kwargs):
        raise RuntimeError("planner unavailable")

    monkeypatch.setattr(
        create_foundup_dryrun,
        "plan_create_foundup_dry_run",
        _raise,
    )
    adapter = CreateFoundUpDryRunScaffoldAdapter(registry_path=registry_path)

    result = adapter.plan(job)

    assert result.ok is False
    assert result.reason_code == "FAIL_SCAFFOLD_ADAPTER_INTERNAL"
    assert "failed closed" in result.reason_human


def test_consumer_uses_injected_scaffold_adapter_not_generic_hermes(
    tmp_path: Path,
):
    job, _ = _bound_job(tmp_path)
    injected_adapter = Mock()
    injected_adapter.plan.return_value = ScaffoldAdapterResult(
        ok=True,
        reason_code="OK_SCAFFOLD_PLAN",
        reason_human="injected scaffold plan verified",
        plan={"dry_run": True, "files_written": []},
    )
    consumer = FoundUpJobConsumer(
        dry_run=True,
        scaffold_adapter=injected_adapter,
    )
    consumer._dispatch_to_hermes = Mock(
        side_effect=AssertionError("generic Hermes executor must not be called")
    )

    result = consumer.consume_one(job)

    injected_adapter.plan.assert_called_once_with(job)
    consumer._dispatch_to_hermes.assert_not_called()
    assert result.dispatched is True
    assert result.route_status == RouteStatus.ROUTED
    assert result.target_backend == TargetBackend.HERMES_SCAFFOLD
    assert result.hermes_result is None
    assert result.scaffold_result["ok"] is True
    assert result.checkpoint_state == "SIMULATED"
    assert result.real_execution_performed is False
    assert result.is_terminal is True
    assert result.retention_reason == "dry_run_evidence_only"


def test_consumer_global_live_mode_blocks_before_scaffold_adapter(tmp_path: Path):
    job, _ = _bound_job(tmp_path)
    injected_adapter = Mock()
    consumer = FoundUpJobConsumer(
        dry_run=False,
        scaffold_adapter=injected_adapter,
    )

    result = consumer.consume_one(job)

    injected_adapter.plan.assert_not_called()
    assert result.dispatched is False
    assert result.route_status == RouteStatus.BLOCKED
    assert result.target_backend == TargetBackend.HERMES_SCAFFOLD
    assert result.checkpoint_state == "BLOCKED"
    assert result.real_execution_performed is False
