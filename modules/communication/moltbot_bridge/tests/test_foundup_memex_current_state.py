"""Tests for FOUNDUP_MEMEX_CURRENT_STATE_ASSEMBLY_PHASE1 adapter."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch

from modules.communication.moltbot_bridge.src import foundup_memex_current_state as memex
from modules.communication.moltbot_bridge.src.foundup_brain_current_state import (
    FOUNDUP_BRAIN_VIEW_ACCEPTED,
    FOUNDUP_BRAIN_VIEW_REJECTED,
    FOUNDUP_BRAIN_VIEW_SCHEMA_VERSION,
    FoundUpBrainAssemblyResult,
    FoundUpBrainView,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "foundup_memex_current_state.py"
)


def test_memex_aliases_preserve_existing_brain_contract() -> None:
    assert memex.FOUNDUP_MEMEX_VIEW_SCHEMA_VERSION == FOUNDUP_BRAIN_VIEW_SCHEMA_VERSION
    assert memex.FOUNDUP_MEMEX_VIEW_ACCEPTED == FOUNDUP_BRAIN_VIEW_ACCEPTED
    assert memex.FOUNDUP_MEMEX_VIEW_REJECTED == FOUNDUP_BRAIN_VIEW_REJECTED
    assert memex.FoundUpMemexView is FoundUpBrainView
    assert memex.FoundUpMemexAssemblyResult is FoundUpBrainAssemblyResult


def test_memex_adapter_delegates_exact_inputs_without_new_authority() -> None:
    sentinel = object()
    snapshot = object()
    identity = {"foundup_id": "foundups-agent", "name": "Foundups Agent"}
    roadmap = {"foundup_id": "foundups-agent", "roadmap_id": "r1"}
    outcomes = ({"foundup_id": "foundups-agent", "outcome_id": "o1"},)

    with patch.object(memex, "assemble_foundup_brain_current_state", return_value=sentinel) as delegate:
        result = memex.assemble_foundup_memex_current_state(
            foundup_id="foundups-agent",
            snapshot=snapshot,
            identity=identity,
            roadmap_state=roadmap,
            verified_outcomes=outcomes,
            now_iso="2026-07-14T00:00:00+00:00",
            resident_mode=True,
            legacy_single_foundup_compatibility=False,
            policy_foundup_scope=("foundups-agent",),
        )

    assert result is sentinel
    delegate.assert_called_once_with(
        foundup_id="foundups-agent",
        snapshot=snapshot,
        identity=identity,
        roadmap_state=roadmap,
        verified_outcomes=outcomes,
        now_iso="2026-07-14T00:00:00+00:00",
        resident_mode=True,
        legacy_single_foundup_compatibility=False,
        policy_foundup_scope=("foundups-agent",),
    )


def test_memex_adapter_has_no_execution_or_governance_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    forbidden = {
        "subprocess",
        "os",
        "requests",
        "httpx",
        "sqlite3",
        "modules.infrastructure.wre_core",
        "modules.infrastructure.instance_lock",
    }
    assert imported.isdisjoint(forbidden)

    source = MODULE_PATH.read_text(encoding="utf-8").lower()
    assert "cabr" in source
    assert "no cabr" in source
    assert "delegate" in source
    assert "authority is inferred" in source
