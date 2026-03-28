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


def _run_process_with_intent(dae: OpenClawDAE, intent: OpenClawIntent):
    mock_result = SimpleNamespace(
        response_text="ok",
        success=True,
        pattern_fidelity=1.0,
        learning_stored=False,
        wsp_violations=[]
    )
    with patch.object(dae, "classify_intent", return_value=intent):
        with patch.object(dae, "_wsp_preflight", return_value=True):
            with patch.object(dae, "_check_permission_gate", return_value=True):
                with patch.object(dae, "_execute_plan", new=AsyncMock(return_value="ok")):
                    with patch.object(dae, "_validate_and_remember", return_value=mock_result):
                        return asyncio.run(
                            dae.process(
                                message=intent.raw_message,
                                sender=intent.sender,
                                channel=intent.channel,
                                session_key=intent.session_key,
                            )
                        )


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

    with patch.object(dae, "_ensure_skill_safety", return_value=True) as gate:
        _run_process_with_intent(dae, intent)

    gate.assert_called_once_with()


@pytest.mark.parametrize("category", NON_MUTATING_CATEGORIES)
def test_non_mutating_intents_skip_skill_safety_gate(category: IntentCategory):
    dae = OpenClawDAE(repo_root=project_root)
    intent = _make_intent(category)

    with patch.object(dae, "_ensure_skill_safety", return_value=True) as gate:
        _run_process_with_intent(dae, intent)

    gate.assert_not_called()

