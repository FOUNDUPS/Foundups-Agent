"""Durable-cycle tests for the live Principal Memex source boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from holo_index.repository_state import RepositoryState
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_digest import (
    canonical_model_runtime_binding_digest,
)
from modules.communication.moltbot_bridge.src.reddog_principal_memex_live_resident_source_supply import (
    consume_principal_memex_live_resident_source,
)
from modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle import (
    AgentDbResidentArchitectCycleStore,
    ResidentCycleReason,
    STATUS_RUNNING,
    run_reddog_resident_architect_durable_agentdb_cycle,
)
import modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime as readonly_worker_runtime
from modules.communication.moltbot_bridge.tests.holoindex_freshness_receipt_test_helpers import (
    build_fresh_holoindex_receipt,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_signing_test_support import (
    NOW as PRINCIPAL_NOW,
)
from modules.communication.moltbot_bridge.tests.test_reddog_principal_memex_live_resident_source_supply import (
    _prepared_live_source,
)
from modules.communication.moltbot_bridge.tests.test_reddog_principal_memex_resident_admission import (
    _prepared as _prepared_principal_memex,
)
from modules.communication.moltbot_bridge.tests.test_reddog_resident_architect_durable_agentdb_cycle import (
    HEAD,
    REPO_ROOT,
    _ArchitectRunner,
    _architect_runtime_binding,
    _intent,
    _runtime_kwargs,
    _seed_cycle_status,
)
from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager


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


def _deferred_source(tmp_path: Path, *, binding, intent, clock):
    grounding = intent["grounding_receipt"]
    return _prepared_live_source(
        tmp_path,
        intent_id=str(intent["intent_id"]),
        grounding_receipt_id=str(grounding["receipt_id"]),
        now_epoch=clock,
        binding=binding,
        consume=False,
    )[1]


def _current_holo_receipt(runtime_now: str):
    return build_fresh_holoindex_receipt(
        generated_at=runtime_now,
        repo_root=REPO_ROOT,
        head_sha=HEAD,
    )


def test_durable_cycle_supplies_principal_memex_only_to_final_architect(
    tmp_path: Path,
) -> None:
    architect_runner = _ArchitectRunner()
    binding = _architect_runtime_binding()
    runtime_now = "2027-01-15T08:00:01+00:00"
    prepared, _ = _prepared_principal_memex(
        tmp_path / "principal-resident.sqlite",
        model_receipt=str(binding["receipt_id"]),
        model_digest=canonical_model_runtime_binding_digest(binding),
    )
    assert prepared.accepted is True

    result = run_reddog_resident_architect_durable_agentdb_cycle(
        **_runtime_kwargs(
            now_iso=runtime_now,
            holoindex_receipt_override=_current_holo_receipt(runtime_now),
            architect_model_runner=architect_runner,
            architect_model_runtime_binding_receipt=binding,
            principal_memex_context=prepared.context,
        )
    )

    assert result.accepted is True
    architect_context = json.loads(architect_runner.calls[0]["context"])
    principal_memex = architect_context["principal_memex_context"]
    assert principal_memex["source_class"] == "principal_memex"
    assert principal_memex["authority_effect"] == "none"
    assert "Audit before implementation." in json.dumps(principal_memex)
    completed = AgentDB().get_autonomous_tasks(status="completed", limit=10)
    assert "principal_memex_context" not in json.dumps(completed, sort_keys=True)


def test_durable_cycle_consumes_deferred_source_at_final_boundary(
    tmp_path: Path,
) -> None:
    architect_runner = _ArchitectRunner()
    binding = _architect_runtime_binding()
    intent = dict(_intent())
    intent["intent_id"] = "sha256:" + "9" * 64
    epochs = iter((PRINCIPAL_NOW, PRINCIPAL_NOW + 1, PRINCIPAL_NOW + 2))
    source = _deferred_source(
        tmp_path, binding=binding, intent=intent, clock=lambda: next(epochs)
    )
    runtime_now = "2027-01-15T08:00:01+00:00"

    result = run_reddog_resident_architect_durable_agentdb_cycle(
        **_runtime_kwargs(
            red_dog_intent=intent,
            now_iso=runtime_now,
            holoindex_receipt_override=_current_holo_receipt(runtime_now),
            architect_model_runner=architect_runner,
            architect_model_runtime_binding_receipt=binding,
            principal_memex_source=source,
        )
    )

    assert result.accepted is True
    context_value = json.loads(architect_runner.calls[0]["context"])
    assert context_value["principal_memex_context"]["source_class"] == "principal_memex"
    assert "Audit before implementation." in json.dumps(context_value)


def test_duplicate_cycle_does_not_consume_deferred_source(tmp_path: Path) -> None:
    intent = dict(_intent())
    intent["intent_id"] = "sha256:" + "8" * 64
    binding = _architect_runtime_binding()
    first = run_reddog_resident_architect_durable_agentdb_cycle(
        **_runtime_kwargs(
            red_dog_intent=intent,
            architect_model_runtime_binding_receipt=binding,
        )
    )
    assert first.accepted is True
    source = _deferred_source(
        tmp_path, binding=binding, intent=intent, clock=lambda: PRINCIPAL_NOW
    )

    duplicate = run_reddog_resident_architect_durable_agentdb_cycle(
        **_runtime_kwargs(
            red_dog_intent=intent,
            architect_model_runtime_binding_receipt=binding,
            principal_memex_source=source,
        )
    )
    admission = consume_principal_memex_live_resident_source(
        source,
        resident_cycle_id=first.cycle_id,
    )

    assert duplicate.accepted is True
    assert duplicate.duplicate_intent_reused is True
    assert admission.accepted is True


@pytest.mark.parametrize("cancel_requested", (False, True))
def test_active_or_cancelled_cycle_does_not_consume_principal_memex_source(
    monkeypatch, cancel_requested: bool,
) -> None:
    calls = []
    store = AgentDbResidentArchitectCycleStore()
    _seed_cycle_status(store, status=STATUS_RUNNING)
    monkeypatch.setattr(
        "modules.communication.moltbot_bridge.src."
        "reddog_resident_architect_durable_agentdb_cycle."
        "admit_principal_memex_cycle_context",
        lambda *_args, **_kwargs: calls.append(True),
    )

    result = run_reddog_resident_architect_durable_agentdb_cycle(
        **_runtime_kwargs(
            cycle_store=store,
            cancel_requested=cancel_requested,
            principal_memex_source=object(),
        )
    )

    assert result.accepted is False
    assert calls == []
    expected = (
        ResidentCycleReason.CANCELLED
        if cancel_requested
        else ResidentCycleReason.ACTIVE_INTENT
    )
    assert expected in result.rejection_reasons


def test_principal_memex_expiry_during_prompt_build_blocks_model_call(
    tmp_path: Path,
) -> None:
    architect_runner = _ArchitectRunner()
    binding = _architect_runtime_binding()
    intent = dict(_intent())
    intent["intent_id"] = "sha256:" + "7" * 64
    epochs = iter((PRINCIPAL_NOW, PRINCIPAL_NOW + 1, PRINCIPAL_NOW + 60))
    source = _deferred_source(
        tmp_path, binding=binding, intent=intent, clock=lambda: next(epochs)
    )
    runtime_now = "2027-01-15T08:00:01+00:00"

    result = run_reddog_resident_architect_durable_agentdb_cycle(
        **_runtime_kwargs(
            red_dog_intent=intent,
            now_iso=runtime_now,
            holoindex_receipt_override=_current_holo_receipt(runtime_now),
            architect_model_runner=architect_runner,
            architect_model_runtime_binding_receipt=binding,
            principal_memex_source=source,
        )
    )

    assert result.accepted is False
    assert architect_runner.calls == []
    assert ResidentCycleReason.FINAL_BOOTSTRAP_REJECTED in result.rejection_reasons
