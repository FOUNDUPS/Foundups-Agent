#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the WSP 109 intake packet builder (dry-run only).

Slice: WSP109_INTAKE_PACKET_BUILDER_PHASE1
WSP:   50, 97, 109

Proves:
    - Valid structured idea -> populated envelope -> GATE_PASSED
    - Empty idea -> NO_ENVELOPE / NOT_READY
    - Invalid foundup_id -> gate rejects (not GATE_PASSED)
    - Builder module imports no FAM/Hermes writer (AST guard)
    - Result is dry-run only; no filesystem side effect
    - OpenClaw dispatch: envelope in payload -> gate passes; without -> NOT_READY
"""

from __future__ import annotations

import ast
import types
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_overseer.src.foundup_genesis import intake_packet_builder
from modules.ai_intelligence.ai_overseer.src.foundup_genesis.intake_packet_builder import (
    IntakePacketBuilderResult,
    build_intake_packet_dry_run,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

VALID_IDEA = """
name: Widget Demo
tagline: A tiny demo widget
description: A demonstration FoundUp used to prove the WSP 109 intake packet builder reaches the genesis gate.
category: tools
foundup_id: widget_demo
lifecycle_stage: idea
binding_state: unbound
acceptance: widget renders | pytest | returns HTML 200 | response.status == 200
""".strip()

INVALID_ID_IDEA = """
name: Bad Id Demo
tagline: has an invalid id
description: This idea deliberately supplies a foundup_id that violates WSP 104 so the validator rejects it.
category: tools
foundup_id: Bad-ID
acceptance: renders | pytest | returns HTML | status == 200
""".strip()


# --------------------------------------------------------------------------- #
# Gate outcomes
# --------------------------------------------------------------------------- #

def test_empty_idea_returns_no_envelope_not_ready() -> None:
    result = build_intake_packet_dry_run("")
    assert isinstance(result, IntakePacketBuilderResult)
    assert result.envelope is None
    assert result.gate_passed is False
    assert result.gate_reason == "NO_ENVELOPE"
    assert result.dry_run is True


def test_whitespace_only_idea_is_no_envelope() -> None:
    result = build_intake_packet_dry_run("   \n\t  \n")
    assert result.envelope is None
    assert result.gate_reason == "NO_ENVELOPE"
    assert result.gate_passed is False


def test_minimal_valid_fixture_gate_passed() -> None:
    result = build_intake_packet_dry_run(VALID_IDEA)
    assert result.gate_passed is True, result.gate_result
    assert result.gate_reason == "GATE_PASSED"
    assert result.envelope is not None
    assert result.envelope["foundup_id"] == "widget_demo"
    assert len(result.envelope["acceptance_criteria"]) == 1


def test_invalid_foundup_id_rejected() -> None:
    result = build_intake_packet_dry_run(INVALID_ID_IDEA)
    assert result.gate_passed is False
    assert result.gate_reason != "GATE_PASSED"
    # Envelope was built (structured input), but the gate blocked it.
    assert result.envelope is not None
    errors = " ".join(result.gate_result.get("errors", [])).lower()
    assert "foundup_id" in errors


def test_unparseable_prose_is_no_envelope() -> None:
    # Free-form prose with no structured headers -> nothing to validate.
    result = build_intake_packet_dry_run(
        "I want to build a really cool marketplace for trading rare houseplants"
    )
    assert result.envelope is None
    assert result.gate_reason == "NO_ENVELOPE"


# --------------------------------------------------------------------------- #
# Hard prohibitions (fail closed)
# --------------------------------------------------------------------------- #

_FORBIDDEN_IMPORT_TOKENS = (
    "hermes_adapter",
    "HermesFoundUpBuilder",
    "fam_adapter",
    "launch_foundup",
    "FoundUpJobConsumer",
)


def test_no_fam_hermes_imports() -> None:
    """AST guard: the builder module must not import any FAM/Hermes writer or
    the job consumer -- anywhere (module level or inside functions)."""
    source = Path(intake_packet_builder.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
            imported.extend(alias.name for alias in node.names)

    blob = " ".join(imported)
    offenders = [tok for tok in _FORBIDDEN_IMPORT_TOKENS if tok in blob]
    assert offenders == [], f"builder imports forbidden writer(s): {offenders}"


def test_result_is_dry_run_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No filesystem side effect; dry-run telemetry all safe."""
    monkeypatch.chdir(tmp_path)
    result = build_intake_packet_dry_run(VALID_IDEA)
    assert result.dry_run is True
    assert result.fam_called is False
    assert result.hermes_called is False
    assert result.registry_mutated is False
    # The builder wrote nothing to the working directory.
    assert list(tmp_path.iterdir()) == []


# --------------------------------------------------------------------------- #
# OpenClaw dispatch simulation
# --------------------------------------------------------------------------- #

def _make_intent(raw_message: str, envelope: dict | None):
    payload = {"genesis_envelope": envelope} if envelope is not None else {}
    return types.SimpleNamespace(
        raw_message=raw_message,
        sender="012",
        session_key="sess_test",
        channel="test",
        payload=payload,
    )


def test_openclaw_dispatch_simulation() -> None:
    """envelope in intent.payload['genesis_envelope'] -> gate passes (not
    NOT_READY); without envelope -> NOT_READY handoff."""
    from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
        clear_job_queue,
        dispatch_foundup,
    )

    built = build_intake_packet_dry_run(VALID_IDEA)
    assert built.gate_passed is True

    clear_job_queue()

    # With a valid envelope populated: onboarding intent passes the genesis gate.
    with_env = dispatch_foundup(None, _make_intent("onboard foundup widget_demo", built.envelope))
    assert "NOT_READY" not in with_env

    # Without an envelope: the gate blocks and returns a NOT_READY handoff.
    without_env = dispatch_foundup(None, _make_intent("onboard foundup widget_demo", None))
    assert "NOT_READY" in without_env

    clear_job_queue()
