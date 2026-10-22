"""Contracts for the generic scheduled resident FoundUp reconciliation path."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.infrastructure.idle_automation.src.schedule_claim_state import (
    ScheduleClaim,
    build_execution_id,
)
from modules.communication.moltbot_bridge.src import (
    reddog_scheduled_resident_reconcile as scheduled,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
FOCUS = "Audit current YUMORI project blockers and select the next evidence-first action."


def _claim(
    *,
    routine: str = "resident_reconcile",
    cadence: str = "daily",
) -> ScheduleClaim:
    start = "2026-10-23T00:00:00+00:00"
    end = "2026-10-24T00:00:00+00:00"
    schedule_id = "scheduled-yumori"
    return ScheduleClaim(
        schedule_id=schedule_id,
        routine=routine,
        cadence=cadence,
        window_start=start,
        window_end=end,
        execution_id=build_execution_id(
            schedule_id, routine, cadence, start, end
        ),
        token="opaque-scheduled-resident-token",
        claimant_id="idle-dae",
        lease_expires_at="2026-10-23T01:00:00+00:00",
        attempt=1,
    )


class _Grounded:
    accepted = True
    rejection_reasons = ()
    intent = {
        "schema_version": "reddog_intent.v2",
        "intent_id": "sha256:scheduled-resident-intent",
    }


class _SafeResponse:
    accepted = True
    read_only_authority_only = True
    client_no_shell_command_executed = True
    client_no_repo_mutation_performed = True
    client_no_holoindex_reindex_performed = True
    client_no_hermes_execution_performed = True
    client_no_worktree_operation_performed = True
    client_no_pr_created = True
    client_no_merge_performed = True
    rejection_reasons = ()

    def to_dict(self):
        return {
            "accepted": True,
            "intent_id": "sha256:scheduled-resident-intent",
            "cycle_id": "sha256:scheduled-resident-cycle",
            "status": "DETERMINED",
            "read_only_authority_only": True,
        }


class _FakeClient:
    calls = []

    def __init__(self, **kwargs):
        type(self).calls.append(dict(kwargs))

    def submit(self, intent):
        type(self).calls[-1]["intent"] = dict(intent)
        return _SafeResponse()


def _env():
    return {
        "REDDOG_AUTHENTICATED_PRINCIPAL_ID": "012",
        "REDDOG_AUTHORIZED_FOUNDUP_IDS": "esingularity_001",
        "REDDOG_SCHEDULED_RESIDENT_FOUNDUP_ID": "esingularity_001",
        "REDDOG_SCHEDULED_RESIDENT_WORK_FOCUS": FOCUS,
        "REDDOG_RESIDENT_MEMORY_MAX_RECORDS": "20",
    }


def test_scheduled_resident_reconcile_composes_existing_memory_and_client(monkeypatch):
    _FakeClient.calls.clear()
    monkeypatch.setattr(
        scheduled,
        "load_resident_model_runtime_bindings",
        lambda *_args, **_kwargs: (
            {"receipt_id": "audit-binding"},
            {"receipt_id": "architect-binding"},
            "",
        ),
    )
    monkeypatch.setattr(
        scheduled,
        "resident_brain_state_from_artifacts",
        lambda _env: {"available": True, "record_count": 4},
    )
    monkeypatch.setattr(
        scheduled,
        "resident_breadcrumbs_from_runtime",
        lambda **_kwargs: ({"breadcrumb_id": "crumb-1"}, {"breadcrumb_id": "crumb-2"}),
    )
    monkeypatch.setattr(
        scheduled,
        "resident_workspace_memory_notes_from_env",
        lambda _env: ({"note_id": "workspace-1"},),
    )
    memex_config = object()
    monkeypatch.setattr(
        scheduled,
        "build_resident_foundup_memex_supply_config",
        lambda **_kwargs: memex_config,
    )

    first = scheduled.run_scheduled_resident_reconcile(
        _claim(),
        repo_root=REPO_ROOT,
        environ=_env(),
        client_factory=_FakeClient,
        grounding_service=lambda **_kwargs: _Grounded(),
    )
    second = scheduled.run_scheduled_resident_reconcile(
        _claim(),
        repo_root=REPO_ROOT,
        environ=_env(),
        client_factory=_FakeClient,
        grounding_service=lambda **_kwargs: _Grounded(),
    )

    assert first["success"] is True
    assert first["foundup_id"] == "esingularity_001"
    assert first["brain_record_count"] == 4
    assert first["breadcrumb_count"] == 2
    assert first["workspace_note_count"] == 1
    assert first["foundup_memex_configured"] is True
    assert first["request_id"] == second["request_id"]
    assert first["no_gmail_mutation_performed"] is True
    assert first["no_linkedin_mutation_performed"] is True
    assert first["no_repo_mutation_performed"] is True
    defaults = _FakeClient.calls[0]["runtime_defaults"]
    assert defaults["memex_snapshot_supply_config"] is memex_config
    assert defaults["audit_model_runtime_binding_receipt"]["receipt_id"] == "audit-binding"
    assert defaults["architect_model_runtime_binding_receipt"]["receipt_id"] == "architect-binding"
    assert defaults["breadcrumbs"][0]["breadcrumb_id"] == "crumb-1"
    assert _FakeClient.calls[0]["transport"] == "api"
    assert _FakeClient.calls[0]["authorized_foundup_ids"] == ("esingularity_001",)


@pytest.mark.parametrize(
    "env_patch,expected",
    [
        ({"REDDOG_AUTHENTICATED_PRINCIPAL_ID": ""}, "authenticated_principal_missing"),
        ({"REDDOG_AUTHORIZED_FOUNDUP_IDS": "a,b"}, "scheduled_resident_requires_exactly_one_foundup"),
        ({"REDDOG_SCHEDULED_RESIDENT_FOUNDUP_ID": "other"}, "scheduled_resident_foundup_scope_mismatch"),
        ({"REDDOG_SCHEDULED_RESIDENT_WORK_FOCUS": ""}, "scheduled_resident_work_focus_missing"),
    ],
)
def test_scheduled_resident_reconcile_fails_before_memory_on_bad_scope(
    monkeypatch, env_patch, expected
):
    called = []
    monkeypatch.setattr(
        scheduled,
        "load_resident_model_runtime_bindings",
        lambda *_args, **_kwargs: called.append(True),
    )
    env = _env()
    env.update(env_patch)

    result = scheduled.run_scheduled_resident_reconcile(
        _claim(),
        repo_root=REPO_ROOT,
        environ=env,
        client_factory=_FakeClient,
        grounding_service=lambda **_kwargs: _Grounded(),
    )

    assert result["success"] is False
    assert expected in result["rejection_reasons"]
    assert called == []


def test_scheduled_resident_reconcile_fails_closed_without_memory(monkeypatch):
    monkeypatch.setattr(
        scheduled,
        "load_resident_model_runtime_bindings",
        lambda *_args, **_kwargs: (
            {"receipt_id": "audit-binding"},
            {"receipt_id": "architect-binding"},
            "",
        ),
    )
    monkeypatch.setattr(
        scheduled,
        "resident_brain_state_from_artifacts",
        lambda _env: {"available": True, "record_count": 2},
    )
    monkeypatch.setattr(
        scheduled,
        "resident_breadcrumbs_from_runtime",
        lambda **_kwargs: (),
    )

    result = scheduled.run_scheduled_resident_reconcile(
        _claim(),
        repo_root=REPO_ROOT,
        environ=_env(),
        client_factory=_FakeClient,
        grounding_service=lambda **_kwargs: _Grounded(),
    )

    assert result["success"] is False
    assert result["rejection_reasons"] == [
        "resident_breadcrumbs_context_unavailable"
    ]


@pytest.mark.asyncio
async def test_idle_resident_reconcile_is_default_off(monkeypatch, tmp_path):
    from modules.infrastructure.idle_automation.src.idle_automation_dae import (
        IdleAutomationDAE,
    )

    monkeypatch.delenv("AUTO_REDDOG_RESIDENT_RECONCILE", raising=False)
    with patch.object(IdleAutomationDAE, "__init__", lambda self: None):
        dae = IdleAutomationDAE()
        dae.module_path = tmp_path / "modules" / "infrastructure" / "idle_automation"
        with patch(
            "modules.communication.moltbot_bridge.src.reddog_scheduled_resident_reconcile."
            "run_scheduled_resident_reconcile"
        ) as runner:
            result = await dae._dispatch_resident_reconcile_claim(_claim())

    assert result["success"] is False
    assert result["rejection_reasons"] == [
        "scheduled_resident_reconcile_disabled"
    ]
    runner.assert_not_called()


@pytest.mark.asyncio
async def test_idle_resident_reconcile_enabled_dispatches_exact_claim(monkeypatch, tmp_path):
    from modules.infrastructure.idle_automation.src.idle_automation_dae import (
        IdleAutomationDAE,
    )

    monkeypatch.setenv("AUTO_REDDOG_RESIDENT_RECONCILE", "true")
    claim = _claim()
    expected = {
        "success": True,
        "receipt_id": "sha256:resident-reconcile",
        "resident_response": {"intent_id": "sha256:resident-intent"},
        "rejection_reasons": [],
    }
    with patch.object(IdleAutomationDAE, "__init__", lambda self: None):
        dae = IdleAutomationDAE()
        dae.module_path = tmp_path / "repo" / "modules" / "infrastructure" / "idle_automation"
        with patch(
            "modules.communication.moltbot_bridge.src.reddog_scheduled_resident_reconcile."
            "run_scheduled_resident_reconcile",
            return_value=expected,
        ) as runner:
            result = await dae._dispatch_resident_reconcile_claim(claim)

    assert result == expected
    runner.assert_called_once()
    assert runner.call_args.args == (claim,)
    assert runner.call_args.kwargs["repo_root"] == tmp_path / "repo"


@pytest.mark.asyncio
async def test_claim_dispatch_projects_resident_receipts_into_existing_history():
    from modules.infrastructure.idle_automation.src.idle_automation_dae import (
        IdleAutomationDAE,
    )

    claim = _claim()
    with patch.object(IdleAutomationDAE, "__init__", lambda self: None):
        dae = IdleAutomationDAE()
        dae._dispatch_resident_reconcile_claim = AsyncMock(
            return_value={
                "success": True,
                "receipt_id": "sha256:resident-reconcile",
                "resident_response": {"intent_id": "sha256:resident-intent"},
                "rejection_reasons": [],
            }
        )
        dispatch = await dae._dispatch_claimed_routine(claim)

    assert dispatch["success"] is True
    assert dispatch["receipt_id"] == "sha256:resident-reconcile"
    assert dispatch["resident_intent_id"] == "sha256:resident-intent"
