"""Tests for GitHub principal/permission snapshot bootstrap."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_github_principal_permission_snapshot_supply_bootstrap import (
    GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_BOOTSTRAP_APPLIED,
    run_reddog_github_principal_permission_snapshot_supply_bootstrap,
)
from modules.platform_integration.github_integration.src.reddog_github_permission_probe import (
    build_probe_backend_from_callable,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
NOW = datetime(2026, 7, 16, 0, 0, 0, tzinfo=timezone.utc)


def _backend(**overrides):
    payload = {
        "authenticated": True,
        "login": "mjtrout",
        "permission": "write",
        "default_branch": "main",
        "scopes": ["repo"],
        "branch_protection_observed": "true",
        "source": "mock",
    }
    payload.update(overrides)
    return build_probe_backend_from_callable(lambda _repo: payload)


def test_bootstrap_materializes_both_runtime_files(tmp_path: Path) -> None:
    principal_path = tmp_path / "runtime" / "principal.json"
    permission_path = tmp_path / "runtime" / "permission.json"

    result = run_reddog_github_principal_permission_snapshot_supply_bootstrap(
        repo_root=REPO_ROOT,
        repo_full_name="FOUNDUPS/Foundups-Agent",
        foundup_id="paccess_001",
        principal_public_key="pub:principal",
        principal_authority_record_output_path=principal_path,
        permission_snapshot_output_path=permission_path,
        now_iso=NOW.isoformat(),
        probe_backend=_backend(permission="write"),
    )

    assert result.accepted is True
    assert result.status == GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_BOOTSTRAP_APPLIED
    assert result.principal_authority_record_path == str(principal_path.resolve())
    assert result.permission_snapshot_path == str(permission_path.resolve())
    assert result.principal_id == "github:mjtrout"
    assert json.loads(principal_path.read_text(encoding="utf-8"))["principal_id"] == "github:mjtrout"
    assert json.loads(permission_path.read_text(encoding="utf-8"))["can_write"] is True


def test_bootstrap_fails_closed_on_read_only_permission(tmp_path: Path) -> None:
    result = run_reddog_github_principal_permission_snapshot_supply_bootstrap(
        repo_root=REPO_ROOT,
        repo_full_name="FOUNDUPS/Foundups-Agent",
        foundup_id="paccess_001",
        principal_public_key="pub:principal",
        principal_authority_record_output_path=tmp_path / "principal.json",
        permission_snapshot_output_path=tmp_path / "permission.json",
        now_iso=NOW.isoformat(),
        probe_backend=_backend(permission="read"),
    )

    assert result.accepted is False
    assert "github_permission_not_write_capable" in result.rejection_reasons
