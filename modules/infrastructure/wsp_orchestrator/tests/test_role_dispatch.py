#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for role-based worker dispatch in WSPOrchestrator.

Validates that the runtime dispatch uses role constants (``role:triage``,
``role:code``, ``role:0102``) instead of model-name strings, and that
``_0102_improve_plan`` assigns roles correctly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

import modules.infrastructure.wsp_orchestrator.src.wsp_orchestrator as mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_orchestrator(monkeypatch) -> mod.WSPOrchestrator:
    """Build an orchestrator with workers/MCP disabled."""
    monkeypatch.setattr(mod, "WORKERS_AVAILABLE", False)
    monkeypatch.setattr(mod, "MCP_DIRECT_AVAILABLE", False)
    return mod.WSPOrchestrator(repo_root=Path("."))


def _make_task(worker_assignment: str, description: str = "test") -> mod.WSPTask:
    return mod.WSPTask(
        task_type="test",
        description=description,
        wsp_references=[],
        mps_score=mod.MPSScore(3, 3, 3, 3),
        worker_assignment=worker_assignment,
    )


# ---------------------------------------------------------------------------
# Role constants exist and are role-prefixed
# ---------------------------------------------------------------------------

def test_role_constants_are_prefixed():
    assert mod.ROLE_TRIAGE.startswith("role:")
    assert mod.ROLE_CODE.startswith("role:")
    assert mod.ROLE_GENERAL.startswith("role:")
    assert mod.ROLE_0102.startswith("role:")


def test_role_constants_are_distinct():
    roles = {mod.ROLE_TRIAGE, mod.ROLE_CODE, mod.ROLE_GENERAL, mod.ROLE_0102}
    assert len(roles) == 4


# ---------------------------------------------------------------------------
# WorkerPlan replaced QwenPlan
# ---------------------------------------------------------------------------

def test_worker_plan_exists():
    plan = mod.WorkerPlan(tasks=["a"], reasoning="r", estimated_time_ms=100, confidence=0.9)
    assert plan.tasks == ["a"]
    assert plan.confidence == 0.9


def test_qwen_plan_no_longer_exists():
    assert not hasattr(mod, "QwenPlan"), "QwenPlan should be renamed to WorkerPlan"


# ---------------------------------------------------------------------------
# _0102_improve_plan assigns role-based workers, not model names
# ---------------------------------------------------------------------------

def test_improve_plan_assigns_role_triage_for_pattern_tasks(monkeypatch):
    orch = _build_orchestrator(monkeypatch)
    plan = mod.WorkerPlan(
        tasks=["pattern match existing code"],
        reasoning="test",
        estimated_time_ms=100,
        confidence=0.8,
    )
    mps = {"mps": mod.MPSScore(3, 3, 3, 3)}
    result = orch._0102_improve_plan(plan, mps)

    worker_suggested = [t for t in result if t.task_type == "worker_suggested"]
    assert len(worker_suggested) == 1
    assert worker_suggested[0].worker_assignment == mod.ROLE_TRIAGE


def test_improve_plan_assigns_role_code_for_planning_tasks(monkeypatch):
    orch = _build_orchestrator(monkeypatch)
    plan = mod.WorkerPlan(
        tasks=["design the new architecture"],
        reasoning="test",
        estimated_time_ms=100,
        confidence=0.8,
    )
    mps = {"mps": mod.MPSScore(3, 3, 3, 3)}
    result = orch._0102_improve_plan(plan, mps)

    worker_suggested = [t for t in result if t.task_type == "worker_suggested"]
    assert len(worker_suggested) == 1
    assert worker_suggested[0].worker_assignment == mod.ROLE_CODE


def test_improve_plan_assigns_role_0102_for_generic_tasks(monkeypatch):
    orch = _build_orchestrator(monkeypatch)
    plan = mod.WorkerPlan(
        tasks=["refactor the module"],
        reasoning="test",
        estimated_time_ms=100,
        confidence=0.8,
    )
    mps = {"mps": mod.MPSScore(3, 3, 3, 3)}
    result = orch._0102_improve_plan(plan, mps)

    worker_suggested = [t for t in result if t.task_type == "worker_suggested"]
    assert len(worker_suggested) == 1
    assert worker_suggested[0].worker_assignment == mod.ROLE_0102


def test_improve_plan_modlog_uses_role_code(monkeypatch):
    orch = _build_orchestrator(monkeypatch)
    mps = {"mps": mod.MPSScore(3, 3, 3, 3)}
    result = orch._0102_improve_plan(None, mps)

    modlog_tasks = [t for t in result if t.task_type == "update_modlog"]
    assert len(modlog_tasks) == 1
    assert modlog_tasks[0].worker_assignment == mod.ROLE_CODE


def test_improve_plan_never_emits_role_general(monkeypatch):
    """ROLE_GENERAL is reserved/dispatchable but the planner does not assign it yet."""
    orch = _build_orchestrator(monkeypatch)
    plan = mod.WorkerPlan(
        tasks=[
            "find patterns in the codebase",
            "design integration architecture",
            "implement the changes",
            "summarize the results",
        ],
        reasoning="test",
        estimated_time_ms=400,
        confidence=0.8,
    )
    mps = {"mps": mod.MPSScore(3, 3, 3, 3)}
    result = orch._0102_improve_plan(plan, mps)

    for task in result:
        assert task.worker_assignment != mod.ROLE_GENERAL, (
            f"Planner emitted ROLE_GENERAL for '{task.description}' — "
            "general is reserved but not yet planner-assigned"
        )


def test_improve_plan_no_model_name_strings(monkeypatch):
    """No worker assignment should contain Gemma or Qwen as a string."""
    orch = _build_orchestrator(monkeypatch)
    plan = mod.WorkerPlan(
        tasks=[
            "find patterns in the codebase",
            "design integration architecture",
            "implement the changes",
            "validate matching criteria",
        ],
        reasoning="test",
        estimated_time_ms=400,
        confidence=0.8,
    )
    mps = {"mps": mod.MPSScore(3, 3, 3, 3)}
    result = orch._0102_improve_plan(plan, mps)

    for task in result:
        w = (task.worker_assignment or "").lower()
        assert "gemma" not in w, f"Model name 'gemma' found in worker: {task.worker_assignment}"
        assert "qwen" not in w, f"Model name 'qwen' found in worker: {task.worker_assignment}"


# ---------------------------------------------------------------------------
# _execute_worker dispatch routes on role prefix
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dispatch_triage_routes_correctly(monkeypatch):
    orch = _build_orchestrator(monkeypatch)
    task = _make_task(mod.ROLE_TRIAGE, description="pattern test")
    result = await orch._execute_worker(task)
    assert "TRIAGE" in result


@pytest.mark.asyncio
async def test_dispatch_code_routes_correctly(monkeypatch):
    orch = _build_orchestrator(monkeypatch)
    task = _make_task(mod.ROLE_CODE, description="plan something")
    result = await orch._execute_worker(task)
    assert "CODE" in result


@pytest.mark.asyncio
async def test_dispatch_0102_routes_correctly(monkeypatch):
    orch = _build_orchestrator(monkeypatch)
    task = _make_task(mod.ROLE_0102, description="direct action")
    result = await orch._execute_worker(task)
    assert "0102" in result


@pytest.mark.asyncio
async def test_dispatch_general_routes_correctly(monkeypatch):
    orch = _build_orchestrator(monkeypatch)
    task = _make_task(mod.ROLE_GENERAL, description="synthesize results")
    result = await orch._execute_worker(task)
    # general currently falls through to code executor
    assert "CODE" in result or "0102" in result


@pytest.mark.asyncio
async def test_dispatch_mcp_routes_correctly(monkeypatch):
    orch = _build_orchestrator(monkeypatch)
    task = _make_task("MCP:HoloIndex", description="search code")
    result = await orch._execute_worker(task)
    assert "MCP" in result


@pytest.mark.asyncio
async def test_dispatch_unknown_falls_to_0102(monkeypatch):
    orch = _build_orchestrator(monkeypatch)
    task = _make_task("unknown:label", description="do something")
    result = await orch._execute_worker(task)
    assert "0102" in result
