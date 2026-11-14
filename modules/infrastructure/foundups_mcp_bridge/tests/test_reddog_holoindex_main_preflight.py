"""Main-preflight integration tests for RedDog's private HoloIndex owner."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_owner_bootstrap as bootstrap,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service_supervisor import (
    SERVICE_TOKEN_ENV,
    SERVICE_URL_ENV,
)


SAFE_TOKEN = "s" * 64
SAFE_URL = "http://127.0.0.1:8127"
OWNER_ONLY_ENV = {"REDDOG_HOLOINDEX_AUTO_MAINTENANCE": "0"}


@pytest.fixture(autouse=True)
def _clean_main_owner_state(monkeypatch: pytest.MonkeyPatch):
    bootstrap.cleanup_reddog_holoindex_owner(restore_environment=True)
    monkeypatch.setattr(
        bootstrap,
        "_configured_owner_health_ready",
        lambda **_kwargs: True,
    )
    for name in (
        bootstrap.AUTO_START_ENV,
        SERVICE_TOKEN_ENV,
        SERVICE_URL_ENV,
    ):
        monkeypatch.delenv(name, raising=False)
    yield
    bootstrap.cleanup_reddog_holoindex_owner(restore_environment=True)
    os.environ.pop(SERVICE_URL_ENV, None)
    os.environ.pop(SERVICE_TOKEN_ENV, None)

def _ready_runtime_result() -> SimpleNamespace:
    return SimpleNamespace(
        ready=True,
        status="READY",
        assignment_count=0,
        report_collection_attempted=False,
        report_collection_status=None,
        report_collection_report_count=0,
        readonly_audit_decision_attempted=False,
        readonly_audit_decision_action=None,
        readonly_audit_decision_next_slice=None,
        readonly_audit_decision_persist_attempted=False,
        readonly_audit_decision_persist_status=None,
        enqueue_attempted=False,
        enqueue_decision=None,
        enqueue_task_count=0,
        rejection_reasons=(),
        snapshot_receipt_id="sha256:test-snapshot",
        swarm_id="sha256:test-swarm",
    )


def _owner_log_lines(
    capsys: pytest.CaptureFixture[str],
) -> list[str]:
    return [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("[REDDOG-HOLO-OWNER]")
    ]


def test_main_menu_only_preflight_never_requests_owner(
    tmp_path: Path,
) -> None:
    import main

    with patch(
        "modules.infrastructure.foundups_mcp_bridge.src."
        "reddog_holoindex_main_preflight.ensure_reddog_holoindex_operational"
    ) as ensure_operational, patch(
        "modules.communication.moltbot_bridge.src."
        "reddog_main_readonly_operational_bootstrap."
        "run_reddog_main_readonly_operational_bootstrap",
        return_value=_ready_runtime_result(),
    ):
        with patch.dict(
            os.environ,
            {"REDDOG_READONLY_OPERATIONAL_BOOTSTRAP": "1"},
            clear=True,
        ):
            assert (
                main.run_reddog_readonly_operational_bootstrap_preflight(
                    tmp_path
                )
                is True
            )
    ensure_operational.assert_not_called()


@pytest.mark.parametrize(
    "work_environment",
    [
        {"REDDOG_READONLY_AUDIT_RESEARCH_DECISION_E2E_ENABLED": "1"},
        {"REDDOG_READONLY_AUDIT_REPORT_COLLECTION_ENABLED": "1"},
        {"REDDOG_READONLY_AUDIT_SWARM_ENQUEUE_ENABLED": "1"},
        {"OPENCLAW_AUTO_TASKS_ENABLED": "1"},
    ],
)
def test_main_holo_work_requests_owner_and_enforces_startup_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    work_environment: dict[str, str],
) -> None:
    import main

    failure = bootstrap.RedDogHoloIndexOwnerBootstrapResult(
        ready=False,
        status=bootstrap.OWNER_FAILED,
        error="HOLOINDEX_QUERY_SERVICE_STARTUP_TIMEOUT",
    )
    environment = {
        "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP": "1",
        "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP_ENFORCED": "1",
        **OWNER_ONLY_ENV,
        **work_environment,
    }
    with patch(
        "modules.infrastructure.foundups_mcp_bridge.src."
        "reddog_holoindex_main_preflight.ensure_reddog_holoindex_operational",
        return_value=failure,
    ) as ensure_operational:
        with patch.dict(os.environ, environment, clear=True):
            assert (
                main.run_reddog_readonly_operational_bootstrap_preflight(
                    tmp_path
                )
                is False
            )

    ensure_operational.assert_called_once_with(
        repo_root=tmp_path,
        requested=True,
        auto_maintenance=False,
    )
    output = capsys.readouterr().out
    assert "[REDDOG-HOLO-OWNER] preflight=FAIL" in output
    assert "HOLOINDEX_QUERY_SERVICE_STARTUP_TIMEOUT" in output
    assert SAFE_TOKEN not in output


def test_main_owner_failure_warns_without_logging_secrets_when_not_enforced(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import main

    failure = bootstrap.RedDogHoloIndexOwnerBootstrapResult(
        ready=False,
        status=bootstrap.OWNER_FAILED,
        error="HOLOINDEX_QUERY_SERVICE_STARTUP_TIMEOUT",
    )
    with patch(
        "modules.infrastructure.foundups_mcp_bridge.src."
        "reddog_holoindex_main_preflight.ensure_reddog_holoindex_operational",
        return_value=failure,
    ), patch(
        "modules.communication.moltbot_bridge.src."
        "reddog_main_readonly_operational_bootstrap."
        "run_reddog_main_readonly_operational_bootstrap",
        return_value=_ready_runtime_result(),
    ):
        with patch.dict(
            os.environ,
            {
                "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP": "1",
                "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP_ENFORCED": "0",
                "REDDOG_READONLY_AUDIT_REPORT_COLLECTION_ENABLED": "1",
                "UNRELATED_PRIVATE_VALUE": SAFE_TOKEN,
                **OWNER_ONLY_ENV,
            },
            clear=True,
        ):
            assert (
                main.run_reddog_readonly_operational_bootstrap_preflight(
                    tmp_path
                )
                is True
            )

    output = capsys.readouterr().out
    assert "[REDDOG-HOLO-OWNER] preflight=WARN" in output
    assert "HOLOINDEX_QUERY_SERVICE_STARTUP_TIMEOUT" in output
    assert SAFE_TOKEN not in output


def test_main_configured_but_unready_owner_never_logs_pass(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import main

    failure = bootstrap.RedDogHoloIndexOwnerBootstrapResult(
        ready=False,
        status=bootstrap.OWNER_FAILED,
        error=bootstrap.CONFIGURED_UNREADY_ERROR,
    )
    with patch(
        "modules.infrastructure.foundups_mcp_bridge.src."
        "reddog_holoindex_main_preflight.ensure_reddog_holoindex_operational",
        return_value=failure,
    ), patch(
        "modules.communication.moltbot_bridge.src."
        "reddog_main_readonly_operational_bootstrap."
        "run_reddog_main_readonly_operational_bootstrap",
        return_value=_ready_runtime_result(),
    ):
        with patch.dict(
            os.environ,
            {
                "REDDOG_READONLY_OPERATIONAL_BOOTSTRAP": "1",
                "REDDOG_READONLY_AUDIT_REPORT_COLLECTION_ENABLED": "1",
                SERVICE_URL_ENV: SAFE_URL,
                SERVICE_TOKEN_ENV: SAFE_TOKEN,
                **OWNER_ONLY_ENV,
            },
            clear=True,
        ):
            assert (
                main.run_reddog_readonly_operational_bootstrap_preflight(
                    tmp_path
                )
                is True
            )
            assert os.environ[SERVICE_URL_ENV] == SAFE_URL
            assert os.environ[SERVICE_TOKEN_ENV] == SAFE_TOKEN

    owner_lines = _owner_log_lines(capsys)
    assert owner_lines
    assert all("preflight=PASS" not in line for line in owner_lines)
    assert "preflight=WARN" in owner_lines[0]
    assert bootstrap.CONFIGURED_UNREADY_ERROR in owner_lines[0]
    assert SAFE_TOKEN not in owner_lines[0]
