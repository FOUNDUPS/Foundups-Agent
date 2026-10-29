#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Skill boundary policy enforcement tests."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modules.communication.moltbot_bridge.src.openclaw_dae import (  # noqa: E402
    IntentCategory,
    OpenClawDAE,
    OpenClawIntent,
)


MUTATING_CATEGORIES = (
    IntentCategory.COMMAND,
    IntentCategory.SYSTEM,
    IntentCategory.SCHEDULE,
    IntentCategory.SOCIAL,
    IntentCategory.AUTOMATION,
    IntentCategory.FOUNDUP,
    IntentCategory.RESEARCH,
)

NON_MUTATING_CATEGORIES = (
    IntentCategory.QUERY,
    IntentCategory.MONITOR,
    IntentCategory.CONVERSATION,
)


def _make_intent(category: IntentCategory) -> OpenClawIntent:
    return OpenClawIntent(
        raw_message="test message",
        category=category,
        confidence=0.95,
        sender="@UnDaoDu",
        channel="discord",
        session_key="test-session",
        is_authorized_commander=True,
        extracted_task="test task",
        target_domain=OpenClawDAE.DOMAIN_ROUTES.get(category),
        metadata={},
    )


def _run_process_with_intent(dae: OpenClawDAE, intent: OpenClawIntent, observed=None):
    mock_result = SimpleNamespace(
        response_text="ok", success=True, pattern_fidelity=1.0,
        learning_stored=False, wsp_violations=[],
    )
    with (
        patch.object(dae, "classify_intent", return_value=intent),
        patch.object(dae, "_wsp_preflight", return_value=True) as preflight,
        patch.object(dae, "_check_permission_gate", return_value=True) as permission,
        patch.object(dae, "_execute_plan", new=AsyncMock(return_value="ok")) as execute,
        patch.object(dae, "_validate_and_remember", return_value=mock_result) as validate,
    ):
        if observed is not None:
            observed.update(preflight=preflight, permission=permission, execute=execute, validate=validate)
        response = asyncio.run(dae.process(
            message=intent.raw_message, sender=intent.sender,
            channel=intent.channel, session_key=intent.session_key,
        ))
    return response


def test_skill_boundary_policy_doc_exists():
    policy = project_root / "modules/communication/moltbot_bridge/docs/SKILL_BOUNDARY_POLICY.md"
    assert policy.exists(), "Skill boundary policy doc is required"


def test_workspace_skills_are_docs_only():
    skills_root = project_root / "modules/communication/moltbot_bridge/workspace/skills"
    py_files = list(skills_root.rglob("*.py"))
    assert not py_files, f"Workspace skills must not contain Python executors: {py_files}"


@pytest.mark.parametrize("category", MUTATING_CATEGORIES)
def test_mutating_intents_require_skill_safety_gate(category: IntentCategory):
    dae = OpenClawDAE(repo_root=project_root)
    intent = _make_intent(category)

    with patch.object(dae, "_ensure_skill_safety", return_value=(True, "current")) as gate:
        _run_process_with_intent(dae, intent)

    gate.assert_called_once_with(details=True)


@pytest.mark.parametrize("category", NON_MUTATING_CATEGORIES)
def test_non_mutating_intents_skip_skill_safety_gate(category: IntentCategory):
    dae = OpenClawDAE(repo_root=project_root)
    intent = _make_intent(category)

    with patch.object(dae, "_ensure_skill_safety", return_value=(True, "current")) as gate:
        _run_process_with_intent(dae, intent)

    gate.assert_not_called()



@pytest.mark.parametrize("allowed", [False, True])
@pytest.mark.parametrize("pair_kind", ["tuple", "list"])
def test_skill_gate_keeps_own_explanation_across_callbacks(allowed, pair_kind):
    dae = OpenClawDAE(repo_root=project_root)
    actions, warnings, observed = [], [], {}

    def gate(**kwargs):
        dae._skill_scan_message = "other gate"
        return (allowed, "own verdict") if pair_kind == "tuple" else [allowed, "own verdict"]

    def warning(*args, **kwargs):
        warnings.append(args)
        dae._skill_scan_message = "other logger"

    def action(event, **fields):
        if event == "skill_safety_gate":
            actions.append(fields)
            dae._skill_scan_message = "other action"

    with (
        patch.object(dae, "_ensure_skill_safety", side_effect=gate) as called,
        patch.object(dae, "_report_daemon_action", side_effect=action),
        patch("modules.communication.moltbot_bridge.src.openclaw_process_loop.logger.warning", side_effect=warning),
    ):
        response = _run_process_with_intent(dae, _make_intent(IntentCategory.RESEARCH), observed)
    assert len(actions) == 1
    assert actions[0]["result"] == ("passed" if allowed else "blocked")
    assert actions[0]["policy" if allowed else "reason"] == "own verdict"
    called.assert_called_once_with(details=True)
    assert dae._skill_scan_message == "other action"
    if allowed:
        assert response == "ok" and warnings == []
        observed["execute"].assert_awaited_once()
    else:
        assert response == "[SECURITY BLOCK] Execution prevented by Skill Safety Guard: own verdict"
        assert len(warnings) == 1 and warnings[0][-1] == "own verdict"
        for call in observed.values():
            call.assert_not_called()


@pytest.mark.parametrize("result", [
    None, False, True, (), (False,), (True, "own", "extra"), "bad",
    ("false", "own"), (1, "own"), (False, None), (True, 1), "truthy-verdict",
])
def test_malformed_skill_details_reject_before_downstream(result):
    dae = OpenClawDAE(repo_root=project_root)
    observed = {}
    if result == "truthy-verdict":
        result = (SimpleNamespace(), "own")
    with patch.object(dae, "_ensure_skill_safety", return_value=result) as gate:
        with pytest.raises((TypeError, ValueError)):
            _run_process_with_intent(dae, _make_intent(IntentCategory.RESEARCH), observed)
    for call in observed.values():
        call.assert_not_called()
    gate.assert_called_once_with(details=True)
