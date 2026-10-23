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
    - Commander dispatch: declared metadata -> detached gated queue; no live execution
"""

from __future__ import annotations

import ast
from copy import deepcopy
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

def _make_intent(raw_message: str, envelope: dict | None, *, authorized=True):
    from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawIntent, IntentCategory
    return OpenClawIntent(
        raw_message=raw_message, category=IntentCategory.FOUNDUP, confidence=1.0,
        sender="012", session_key="sess_test", channel="test",
        is_authorized_commander=authorized,
        metadata={"genesis_envelope": envelope} if envelope is not None else {},
    )


@pytest.fixture
def isolated_dispatch(monkeypatch):
    from modules.communication.moltbot_bridge.src import openclaw_foundup_orchestrator as dispatch
    monkeypatch.setattr(dispatch, "_FOUNDUP_JOB_QUEUE", [])
    monkeypatch.setattr(dispatch, "_orchestrator", None)
    return dispatch


def test_openclaw_dispatch_simulation(isolated_dispatch) -> None:
    """Declared intent and explicit fixture authority must reach a real queued job."""
    from modules.communication.moltbot_bridge.src.foundup_job_contract import FoundUpJob
    dispatch = isolated_dispatch
    built = build_intake_packet_dry_run(VALID_IDEA)
    assert built.gate_passed is True
    intent = _make_intent("onboard foundup widget_demo [dry-run]", built.envelope)
    response = dispatch.dispatch_foundup(None, intent)
    assert "FoundUpJob created" in response, response
    assert len(dispatch.get_job_queue()) == 1
    job = dispatch.get_job_queue()[0]
    assert job.tenant_id == "012" and job.intent_id == "sess_test"
    assert job.foundup_id == built.envelope["foundup_id"] == "widget_demo"
    assert job.requested_action == "build_foundup" and job.status.value == "queued"
    assert job.payload["genesis_envelope"] == built.envelope
    assert job.policy_flags.dry_run_mode is True
    assert job.creation_mode is None and job.scaffold_contract_digest is None
    assert job.evidence_refs == []
    assert FoundUpJob.from_dict(job.to_dict()).payload == job.payload
    without_env = dispatch.dispatch_foundup(None, _make_intent("onboard foundup widget_demo", None))
    assert "NOT_READY" in without_env
    assert len(dispatch.get_job_queue()) == 1


@pytest.mark.parametrize("message", ("onboard foundup widget_demo", "build foundup widget_demo"))
@pytest.mark.parametrize("authorized", (False, None, 1, "true"))
def test_envelope_never_grants_commander_authority(isolated_dispatch, monkeypatch, message, authorized):
    intent = _make_intent(message, build_intake_packet_dry_run(VALID_IDEA).envelope, authorized=authorized)
    intent.metadata.update(is_authorized_commander=True, authenticated=True, owner_principal_id="012")
    monkeypatch.setattr(isolated_dispatch, "_extract_envelope_data",
                        lambda *_: pytest.fail("Untrusted request reached intake"))
    response = isolated_dispatch.dispatch_foundup(None, intent)
    assert "mutation denied" in response
    assert isolated_dispatch.get_job_queue() == []


@pytest.mark.parametrize("case", ("null", "empty", "list", "invalid", "nan", "cycle", "non_json",
                                 "tuple", "integer_key", "depth", "nested_subclass"))
def test_declared_invalid_envelope_never_falls_back_to_bare_build(isolated_dispatch, case):
    envelope = build_intake_packet_dry_run(VALID_IDEA).envelope
    if case in {"null", "empty", "list"}:
        envelope = {"null": None, "empty": {}, "list": []}[case]
    elif case == "invalid":
        envelope["foundup_id"] = "Bad-ID"
    elif case == "cycle":
        envelope["notes"] = envelope
    elif case == "tuple":
        envelope["notes"] = ("coerced",)
    elif case == "integer_key":
        envelope["notes"] = {1: "coerced"}
    elif case == "depth":
        nested = []
        for _ in range(1200):
            nested = [nested]
        envelope["notes"] = nested
    elif case == "nested_subclass":
        class HostileDict(dict):
            def items(self):
                pytest.fail("Untrusted mapping hook invoked")
        envelope["notes"] = HostileDict(secret="unused")
    else:
        envelope["notes"] = float("nan") if case == "nan" else object()
    intent = _make_intent("build foundup widget_demo", None)
    intent.metadata["genesis_envelope"] = envelope
    response = isolated_dispatch.dispatch_foundup(None, intent)
    assert "NOT_READY" in response
    assert isolated_dispatch.get_job_queue() == []


@pytest.mark.parametrize("field", ("metadata", "payload"))
@pytest.mark.parametrize("case", ("absent", "none", "empty", "list", "string", "subclass"))
def test_intent_context_root_contract(isolated_dispatch, field, case):
    intent = _make_intent("build foundup widget_demo", None)
    # A legacy intent may lack metadata; a declared intent must supply its dict.
    intent = types.SimpleNamespace(**vars(intent))
    class HostileDict(dict):
        def __contains__(self, _key):
            pytest.fail("Untrusted root hook invoked")
    if case == "absent":
        vars(intent).pop(field, None)
    else:
        setattr(intent, field, {"none": None, "empty": {}, "list": [],
                               "string": "{}", "subclass": HostileDict()}[case])
    response = isolated_dispatch.dispatch_foundup(None, intent)
    accepted = case in {"absent", "empty"} or (field == "payload" and case == "none")
    assert ("FoundUpJob created" in response) is accepted
    assert len(isolated_dispatch.get_job_queue()) == int(accepted)
    if not accepted:
        assert "NOT_READY" in response


@pytest.mark.parametrize("case", ("legacy", "equal", "conflict", "invalid_canonical"))
def test_metadata_and_legacy_payload_have_one_unambiguous_envelope(isolated_dispatch, case):
    envelope = build_intake_packet_dry_run(VALID_IDEA).envelope
    intent = _make_intent("onboard foundup widget_demo", deepcopy(envelope))
    intent.payload = {"genesis_envelope": deepcopy(envelope)}
    if case == "legacy":
        intent = types.SimpleNamespace(**{k:v for k,v in vars(intent).items() if k != "metadata"})
    elif case == "conflict":
        intent.payload["genesis_envelope"]["name"] = "Different request"
    elif case == "invalid_canonical":
        intent.metadata["genesis_envelope"] = None
    response = isolated_dispatch.dispatch_foundup(None, intent)
    if case in {"legacy", "equal"}:
        assert "FoundUpJob created" in response
        assert isolated_dispatch.get_job_queue()[0].payload["genesis_envelope"] == envelope
    else:
        assert "NOT_READY" in response
        assert isolated_dispatch.get_job_queue() == []


def test_structured_foundup_conflict_is_rejected(isolated_dispatch):
    envelope = build_intake_packet_dry_run(VALID_IDEA).envelope
    response = isolated_dispatch.dispatch_foundup(None, _make_intent("build foundup other_demo", envelope))
    assert "NOT_READY" in response
    assert isolated_dispatch.get_job_queue() == []


def test_json_type_conflict_is_not_python_equality(isolated_dispatch):
    envelope = build_intake_packet_dry_run(VALID_IDEA).envelope
    envelope["extra"] = True
    intent = _make_intent("build foundup widget_demo", envelope)
    intent.payload = {"genesis_envelope": deepcopy(envelope)}
    intent.payload["genesis_envelope"]["extra"] = 1
    assert "NOT_READY" in isolated_dispatch.dispatch_foundup(None, intent)
    assert isolated_dispatch.get_job_queue() == []


def test_direct_build_helper_cannot_skip_declared_envelope_gate(isolated_dispatch):
    envelope = build_intake_packet_dry_run(VALID_IDEA).envelope
    envelope["foundup_id"] = "Bad-ID"
    assert "NOT_READY" in isolated_dispatch._handle_build_intent(
        _make_intent("build foundup widget_demo", envelope))
    assert isolated_dispatch.get_job_queue() == []


def test_validated_envelope_and_actor_are_detached_before_gate_callbacks(isolated_dispatch, monkeypatch):
    dispatch = isolated_dispatch
    envelope = build_intake_packet_dry_run(VALID_IDEA).envelope
    expected = deepcopy(envelope)
    intent = _make_intent("onboard foundup widget_demo", envelope)
    gate = dispatch.get_orchestrator()
    validate = gate.validate_genesis_envelope

    def mutate_after_validation(data, actor_id="openclaw", **kwargs):
        result = validate(data, actor_id=actor_id, **kwargs)
        envelope["name"] = "late source mutation"
        data["foundup_id"] = "late_validator_mutation"
        intent.sender = "late_sender"
        intent.session_key = "late_session"
        intent.raw_message = "build foundup other_demo"
        return result

    monkeypatch.setattr(gate, "validate_genesis_envelope", mutate_after_validation)
    response = dispatch.dispatch_foundup(None, intent)
    assert "FoundUpJob created" in response
    job = dispatch.get_job_queue()[0]
    assert job.payload["genesis_envelope"] == expected
    assert job.foundup_id == "widget_demo"
    assert job.tenant_id == "012" and job.intent_id == "sess_test"
    assert job.payload["raw_message"] == "onboard foundup widget_demo"


def test_envelope_affects_idempotency_without_importing_metadata_authority(isolated_dispatch):
    envelope = build_intake_packet_dry_run(VALID_IDEA).envelope
    first = _make_intent("build foundup widget_demo", deepcopy(envelope))
    first.metadata.update(authenticated=True, creation_mode="new_scaffold", unexpected="ignored")
    second = _make_intent(first.raw_message, deepcopy(envelope))
    second.metadata["genesis_envelope"]["description"] += " Revised idea."
    for intent in (first, second):
        assert "FoundUpJob created" in isolated_dispatch.dispatch_foundup(None, intent)
    a, b = isolated_dispatch.get_job_queue()
    assert a.idempotency_key != b.idempotency_key
    assert set(a.payload) == {"raw_message", "channel", "source", "genesis_envelope"}
    assert a.creation_mode is None and a.scaffold_contract_digest is None


def test_bare_build_preserves_legacy_queue_contract(isolated_dispatch):
    response = isolated_dispatch.dispatch_foundup(None, _make_intent("build foundup widget_demo", None))
    assert "FoundUpJob created" in response
    job = isolated_dispatch.get_job_queue()[0]
    assert job.foundup_id == "widget_demo" and job.requested_action == "build_foundup"
    assert "genesis_envelope" not in job.payload
    assert job.genesis_envelope_digest is None
    assert job.policy_flags.dry_run_mode is True


@pytest.mark.parametrize("structured", (False, True))
@pytest.mark.parametrize("foundup_id", ("onboard_demo", "demo_onboard", "onboarding"))
def test_build_precedence_and_command_words_inside_identity(isolated_dispatch, foundup_id, structured):
    envelope = build_intake_packet_dry_run(VALID_IDEA).envelope if structured else None
    if envelope:
        envelope["foundup_id"] = foundup_id
    response = isolated_dispatch.dispatch_foundup(
        None, _make_intent(f"build foundup {foundup_id}", envelope))
    assert "FoundUpJob created" in response
    assert isolated_dispatch.get_job_queue()[0].foundup_id == foundup_id


@pytest.mark.parametrize("field,value", (("foundup_id", 1), ("foundup_id", []),
                                        ("foundup_id", {}), ("category", 1),
                                        ("category", ["tools"])))
def test_malformed_json_field_types_return_handoff(isolated_dispatch, field, value):
    envelope = build_intake_packet_dry_run(VALID_IDEA).envelope
    envelope[field] = value
    response = isolated_dispatch.dispatch_foundup(None, _make_intent("build foundup widget_demo", envelope))
    assert "NOT_READY" in response
    assert isolated_dispatch.get_job_queue() == []


@pytest.mark.parametrize("field", ("metadata", "payload"))
def test_context_keys_reject_subclass_hooks(isolated_dispatch, field):
    class HostileKey(str):
        __hash__ = str.__hash__
        def __eq__(self, other):
            pytest.fail("Supplied key hook invoked")
    intent = _make_intent("build foundup widget_demo", None)
    setattr(intent, field, {HostileKey("genesis_envelope"):
                           build_intake_packet_dry_run(VALID_IDEA).envelope})
    assert "NOT_READY" in isolated_dispatch.dispatch_foundup(None, intent)
    assert isolated_dispatch.get_job_queue() == []
