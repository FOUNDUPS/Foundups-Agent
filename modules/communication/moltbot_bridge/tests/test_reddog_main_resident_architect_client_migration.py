"""Security regressions for main.py canonical resident-client migration."""

from __future__ import annotations

import inspect
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import main
from modules.communication.moltbot_bridge.src import (
    reddog_main_resident_architect_cycle_bootstrap as resident_main_bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle import (
    ResidentCycleReason,
    run_reddog_resident_architect_durable_agentdb_cycle,
)
from modules.communication.moltbot_bridge.src.reddog_transport_neutral_grounding_service import (
    TransportGroundingResult,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MAIN_AUTH_ENV = {
    "REDDOG_AUTHENTICATED_PRINCIPAL_ID": "principal-main-test",
    "REDDOG_AUTHORIZED_FOUNDUP_IDS": "foundups_agent",
}


def _model_runtime_bindings() -> tuple[dict[str, str], dict[str, str], str]:
    return (
        {"runtime_surface": "reddog_readonly_audit_worker"},
        {"runtime_surface": "reddog_backend_architect"},
        "",
    )


def _runtime_defaults() -> dict[str, object]:
    return {"requested_operation": "main_resident_architect_cycle"}


def _status_fix_response() -> SimpleNamespace:
    return SimpleNamespace(
        accepted=True,
        operation="status",
        status="DETERMINED",
        intent_id="sha256:existing",
        cycle_id="sha256:cycle",
        snapshot_id="sha256:snapshot",
        swarm_id="sha256:swarm",
        task_ids=("task-1",),
        task_status_counts={"completed": 1},
        openclaw_claim_count=1,
        recovered_existing_cycle=True,
        duplicate_intent_reused=True,
        architect_action="FIX",
        architect_next_slice="REDDOG_NEXT_PHASE1",
        determination_id="sha256:determination",
        queue_candidate_count=1,
        rejection_reasons=(),
        read_only_authority_only=True,
        client_no_shell_command_executed=True,
        client_no_repo_mutation_performed=True,
        client_no_holoindex_reindex_performed=True,
        client_no_hermes_execution_performed=True,
        client_no_worktree_operation_performed=True,
        client_no_pr_created=True,
    )


def test_main_preflight_requires_host_authenticated_scope_before_runtime(
    monkeypatch, capsys
) -> None:
    monkeypatch.setenv("REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE", "1")
    monkeypatch.delenv("REDDOG_AUTHENTICATED_PRINCIPAL_ID", raising=False)
    monkeypatch.delenv("REDDOG_AUTHORIZED_FOUNDUP_IDS", raising=False)

    with (
        patch.object(
            main,
            "_reddog_resident_model_runtime_bindings_from_env",
            return_value=_model_runtime_bindings(),
        ),
        patch.object(main, "_run_reddog_main_resident_client") as runtime,
    ):
        assert (
            main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT)
            is True
        )

    runtime.assert_not_called()
    assert "authenticated_scope_missing_or_mismatched" in capsys.readouterr().out


def test_main_preflight_rejects_principal_cross_check_mismatch(monkeypatch) -> None:
    monkeypatch.setenv("REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE", "1")
    monkeypatch.setenv("REDDOG_AUTHENTICATED_PRINCIPAL_ID", "principal-main-test")
    monkeypatch.setenv("REDDOG_AUTHORIZED_FOUNDUP_IDS", "foundups_agent")
    monkeypatch.setenv("REDDOG_RESIDENT_ARCHITECT_PRINCIPAL_REF", "forged-principal")

    with (
        patch.object(
            main,
            "_reddog_resident_model_runtime_bindings_from_env",
            return_value=_model_runtime_bindings(),
        ),
        patch.object(main, "_run_reddog_main_resident_client") as runtime,
    ):
        assert (
            main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT)
            is True
        )

    runtime.assert_not_called()


@pytest.mark.parametrize(
    ("cancel_requested", "retry_requested", "explicit_intent_id", "reason"),
    (
        (True, True, "sha256:existing", "resident_architect_cancel_retry_conflict"),
        (True, False, "", "resident_architect_control_intent_missing"),
        (False, True, "", "resident_architect_control_intent_missing"),
    ),
)
def test_control_operations_fail_before_client(
    cancel_requested: bool,
    retry_requested: bool,
    explicit_intent_id: str,
    reason: str,
) -> None:
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_client."
        "RedDogResidentArchitectClient"
    ) as client:
        with pytest.raises(ValueError, match=reason):
            main._run_reddog_main_resident_client(
                repo_root=REPO_ROOT,
                authenticated_principal="principal-main-test",
                authorized_foundups=("foundups_agent",),
                foundup_id="foundups_agent",
                work_focus="Audit main resident RedDog.",
                client_request_id="request-1",
                explicit_intent_id=explicit_intent_id,
                runtime_defaults=_runtime_defaults(),
                cancel_requested=cancel_requested,
                retry_requested=retry_requested,
            )
    client.assert_not_called()


def test_exported_helper_rejects_unauthorized_foundup_before_runtime() -> None:
    with (
        patch(
            "modules.communication.moltbot_bridge.src.reddog_resident_architect_client."
            "RedDogResidentArchitectClient"
        ) as client,
        patch(
            "modules.communication.moltbot_bridge.src.reddog_transport_neutral_grounding_service."
            "ground_transport_work_focus"
        ) as grounding,
    ):
        with pytest.raises(
            ValueError,
            match="resident_architect_authenticated_scope_missing_or_mismatched",
        ):
            resident_main_bootstrap.run_main_resident_client(
                repo_root=REPO_ROOT,
                authenticated_principal="principal-main-test",
                authorized_foundups=("foundup-a",),
                foundup_id="foundup-b",
                work_focus="Audit main resident RedDog.",
                client_request_id="request-1",
                explicit_intent_id="",
                runtime_defaults=_runtime_defaults(),
                cancel_requested=False,
                retry_requested=False,
            )

    client.assert_not_called()
    grounding.assert_not_called()


def test_grounding_failure_never_constructs_client() -> None:
    rejected = TransportGroundingResult(
        schema_version="reddog_transport_grounding_result.v1",
        accepted=False,
        rejection_reasons=("grounding_failed",),
    )
    with (
        patch(
            "modules.communication.moltbot_bridge.src.reddog_transport_neutral_grounding_service."
            "ground_transport_work_focus",
            return_value=rejected,
        ),
        patch(
            "modules.communication.moltbot_bridge.src.reddog_resident_architect_client."
            "RedDogResidentArchitectClient"
        ) as client,
    ):
        with pytest.raises(RuntimeError, match="grounding_rejected:grounding_failed"):
            main._run_reddog_main_resident_client(
                repo_root=REPO_ROOT,
                authenticated_principal="principal-main-test",
                authorized_foundups=("foundups_agent",),
                foundup_id="foundups_agent",
                work_focus="Audit missing evidence.",
                client_request_id="request-1",
                explicit_intent_id="",
                runtime_defaults=_runtime_defaults(),
                cancel_requested=False,
                retry_requested=False,
            )
    client.assert_not_called()


def test_explicit_intent_routes_status_without_grounding() -> None:
    expected = SimpleNamespace(accepted=True, intent_id="sha256:existing")
    client_instance = Mock()
    client_instance.status.return_value = expected
    with (
        patch(
            "modules.communication.moltbot_bridge.src.reddog_resident_architect_client."
            "RedDogResidentArchitectClient",
            return_value=client_instance,
        ) as client_class,
        patch(
            "modules.communication.moltbot_bridge.src.reddog_transport_neutral_grounding_service."
            "ground_transport_work_focus"
        ) as grounding,
    ):
        result = main._run_reddog_main_resident_client(
            repo_root=REPO_ROOT,
            authenticated_principal="principal-main-test",
            authorized_foundups=("foundups_agent", "second_foundup"),
            foundup_id="foundups_agent",
            work_focus="Audit main resident RedDog.",
            client_request_id="request-1",
            explicit_intent_id="sha256:existing",
            runtime_defaults=_runtime_defaults(),
            cancel_requested=False,
            retry_requested=False,
        )

    assert result is expected
    client_class.assert_called_once_with(
        repo_root=REPO_ROOT,
        authenticated_principal_id="principal-main-test",
        authorized_foundup_ids=("foundups_agent",),
        transport="main",
        runtime_defaults=_runtime_defaults(),
    )
    client_instance.status.assert_called_once_with("sha256:existing")
    grounding.assert_not_called()


@pytest.mark.parametrize(
    ("cancel_requested", "retry_requested", "method_name"),
    (
        (True, False, "cancel"),
        (False, True, "resume"),
    ),
)
def test_control_reconnects_bind_to_selected_foundup_only(
    cancel_requested: bool,
    retry_requested: bool,
    method_name: str,
) -> None:
    expected = SimpleNamespace(accepted=True, intent_id="sha256:existing")
    client_instance = Mock()
    getattr(client_instance, method_name).return_value = expected
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_architect_client."
        "RedDogResidentArchitectClient",
        return_value=client_instance,
    ) as client_class:
        result = main._run_reddog_main_resident_client(
            repo_root=REPO_ROOT,
            authenticated_principal="principal-main-test",
            authorized_foundups=("foundups_agent", "second_foundup"),
            foundup_id="foundups_agent",
            work_focus="Audit main resident RedDog.",
            client_request_id="request-1",
            explicit_intent_id="sha256:existing",
            runtime_defaults=_runtime_defaults(),
            cancel_requested=cancel_requested,
            retry_requested=retry_requested,
        )

    assert result is expected
    client_class.assert_called_once_with(
        repo_root=REPO_ROOT,
        authenticated_principal_id="principal-main-test",
        authorized_foundup_ids=("foundups_agent",),
        transport="main",
        runtime_defaults=_runtime_defaults(),
    )
    getattr(client_instance, method_name).assert_called_once_with("sha256:existing")


def test_status_reconnect_cannot_rearm_fix_handoff(monkeypatch) -> None:
    monkeypatch.setenv("REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE", "1")
    monkeypatch.setenv("REDDOG_AUTHENTICATED_PRINCIPAL_ID", "principal-main-test")
    monkeypatch.setenv("REDDOG_AUTHORIZED_FOUNDUP_IDS", "foundups_agent")
    monkeypatch.setenv("REDDOG_RESIDENT_ARCHITECT_INTENT_ID", "sha256:existing")
    monkeypatch.delenv("REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF", raising=False)
    monkeypatch.delenv("REDDOG_RESIDENT_QUEUE_BINDING_PROFILE", raising=False)

    with (
        patch.object(
            main,
            "_reddog_resident_model_runtime_bindings_from_env",
            return_value=_model_runtime_bindings(),
        ),
        patch.object(
            main,
            "_run_reddog_main_resident_client",
            return_value=_status_fix_response(),
        ),
    ):
        assert (
            main.run_reddog_resident_architect_durable_cycle_preflight(REPO_ROOT)
            is True
        )

    assert "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF" not in os.environ
    assert "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE" not in os.environ


def test_new_legacy_main_v1_submission_is_rejected() -> None:
    result = run_reddog_resident_architect_durable_agentdb_cycle(
        repo_root=REPO_ROOT,
        red_dog_intent={
            "schema_version": "reddog_intent.v1",
            "intent_id": "sha256:new-legacy-main-intent",
            "origin": "main.py",
            "principal_ref": "principal-main-test",
            "foundup_id": "foundups_agent",
            "work_focus": "Legacy main submission must not be accepted.",
            "requested_authority": "read_only_audit",
            "submits_executable_authority": False,
        },
    )

    assert result.accepted is False
    assert ResidentCycleReason.INTENT_INVALID in result.rejection_reasons


def test_main_preflight_source_has_no_direct_cycle_runner_reference() -> None:
    source = inspect.getsource(
        main.run_reddog_resident_architect_durable_cycle_preflight
    )
    source += inspect.getsource(main._run_reddog_main_resident_client)
    source += inspect.getsource(resident_main_bootstrap.run_main_resident_client)
    source += inspect.getsource(resident_main_bootstrap._resident_client)
    assert "run_reddog_resident_architect_durable_agentdb_cycle" not in source
    assert "RedDogResidentArchitectClient" in source
    assert "ground_transport_work_focus" in source


def test_main_preflight_is_thin_and_bootstrap_functions_are_decomposed() -> None:
    assert len(
        inspect.getsource(
            main.run_reddog_resident_architect_durable_cycle_preflight
        ).splitlines()
    ) <= 40
    for name in (
        "run_main_resident_architect_cycle_preflight",
        "run_main_resident_client",
        "_resident_request_from_env",
        "_report_result",
    ):
        assert len(inspect.getsource(getattr(resident_main_bootstrap, name)).splitlines()) <= 75
