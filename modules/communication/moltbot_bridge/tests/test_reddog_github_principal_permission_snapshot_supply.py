"""Tests for REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_PHASE1."""

from __future__ import annotations

import ast
import json
from datetime import datetime, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_authority_profile_source_artifact_supply import (
    run_reddog_authority_profile_source_artifact_supply,
)
from modules.communication.moltbot_bridge.src.reddog_github_principal_permission_snapshot_supply import (
    GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_ACCEPT,
    GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_REJECT,
    GitHubPrincipalPermissionSnapshotSupplyReason,
    run_reddog_github_principal_permission_snapshot_supply,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_WORKTREE_CREATE,
)
from modules.platform_integration.github_integration.src.reddog_github_permission_probe import (
    build_probe_backend_from_callable,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_github_principal_permission_snapshot_supply.py"
)
NOW = datetime(2026, 7, 16, 0, 0, 0, tzinfo=timezone.utc)
NOW_EPOCH = int(NOW.timestamp())


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


def _seed(permission_digest: str) -> dict[str, object]:
    return {
        "principal_id": "github:mjtrout",
        "principal_provider": "github",
        "reddog_id": "reddog:architect",
        "reddog_public_key": "pub:reddog",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "foundup_id": "paccess_001",
        "allowed_paths": ["modules/foundups/paccess_001/**"],
        "denied_paths": ["modules/foundups/paccess_001/secrets/**"],
        "requested_operation": "create_foundup",
        "permission_snapshot_digest": permission_digest,
        "identity_nonce": "identity-nonce-0001",
        "work_authority_nonce": "workauth-nonce-0001",
        "issued_at": NOW_EPOCH,
        "identity_expires_at": NOW_EPOCH + 3600,
        "work_authority_expires_at": NOW_EPOCH + 900,
        "valve_state_required": VALVE_OPEN_WORKTREE_CREATE,
        "key_epoch": "epoch-1",
        "required_tests": ["pytest modules/communication/moltbot_bridge/tests"],
        "required_policy_gates": ["signed_work_order_authority", "execution_valve"],
        "consensus_receipt_digest": "sha256:" + "c" * 64,
        "sovereign_authorization_digest": "sha256:" + "d" * 64,
        "holoindex_evidence": {
            "holoindex_query": "RedDog authority profile",
            "holoindex_status": "bundle_json_ok",
            "index_gap_detected": False,
            "retrieval_quality": "HIGH",
            "applicable_wsps": ["WSP_15", "WSP_97"],
            "evidence_refs": [
                "modules/communication/moltbot_bridge/src/reddog_authority_profile_source_artifact_supply.py"
            ],
        },
    }


def test_supplier_materializes_principal_and_permission_inputs_for_authority_source(tmp_path: Path) -> None:
    principal_path = tmp_path / "runtime" / "principal.json"
    permission_path = tmp_path / "runtime" / "permission.json"

    result = run_reddog_github_principal_permission_snapshot_supply(
        repo_root=REPO_ROOT,
        repo_full_name="FOUNDUPS/Foundups-Agent",
        foundup_id="paccess_001",
        principal_public_key="pub:principal",
        principal_authority_record_output_path=principal_path,
        permission_snapshot_output_path=permission_path,
        now=NOW,
        probe_backend=_backend(permission="write"),
    )

    assert result.accepted is True
    assert result.status == GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_ACCEPT
    assert result.receipt_id and result.receipt_id.startswith("sha256:")
    principal = json.loads(principal_path.read_text(encoding="utf-8"))
    permission = json.loads(permission_path.read_text(encoding="utf-8"))
    assert principal["principal_id"] == "github:mjtrout"
    assert principal["principal_public_key"] == "pub:principal"
    assert principal["repo_scope"] == ["FOUNDUPS/Foundups-Agent"]
    assert principal["foundup_scope"] == ["paccess_001"]
    assert principal["verified_subject_digest"].startswith("sha256:")
    assert permission["evidence_digest"] == result.permission_snapshot_digest
    assert permission["can_write"] is True
    assert permission["repo_full_name"] == "FOUNDUPS/Foundups-Agent"

    authority = run_reddog_authority_profile_source_artifact_supply(
        repo_root=REPO_ROOT,
        authority_seed=_seed(str(result.permission_snapshot_digest)),
        principal_authority_record=principal,
        permission_snapshot=permission,
        output_path=tmp_path / "runtime" / "authority_profile_source.json",
        now_epoch=NOW_EPOCH,
    )
    assert authority.accepted is True


def test_supplier_rejects_read_only_permission_for_fix_promotion(tmp_path: Path) -> None:
    result = run_reddog_github_principal_permission_snapshot_supply(
        repo_root=REPO_ROOT,
        repo_full_name="FOUNDUPS/Foundups-Agent",
        foundup_id="paccess_001",
        principal_public_key="pub:principal",
        principal_authority_record_output_path=tmp_path / "principal.json",
        permission_snapshot_output_path=tmp_path / "permission.json",
        now=NOW,
        probe_backend=_backend(permission="read"),
    )

    assert result.accepted is False
    assert result.status == GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_REJECT
    assert GitHubPrincipalPermissionSnapshotSupplyReason.PERMISSION_NOT_WRITE_CAPABLE in result.rejection_reasons


def test_supplier_rejects_unauthenticated_probe(tmp_path: Path) -> None:
    result = run_reddog_github_principal_permission_snapshot_supply(
        repo_root=REPO_ROOT,
        repo_full_name="FOUNDUPS/Foundups-Agent",
        foundup_id="paccess_001",
        principal_public_key="pub:principal",
        principal_authority_record_output_path=tmp_path / "principal.json",
        permission_snapshot_output_path=tmp_path / "permission.json",
        now=NOW,
        probe_backend=_backend(authenticated=False, permission="write", login="unknown"),
    )

    assert result.accepted is False
    assert GitHubPrincipalPermissionSnapshotSupplyReason.PROBE_NOT_AUTHENTICATED in result.rejection_reasons


def test_supplier_rejects_missing_public_key_instead_of_minting_identity(tmp_path: Path) -> None:
    result = run_reddog_github_principal_permission_snapshot_supply(
        repo_root=REPO_ROOT,
        repo_full_name="FOUNDUPS/Foundups-Agent",
        foundup_id="paccess_001",
        principal_public_key="",
        principal_authority_record_output_path=tmp_path / "principal.json",
        permission_snapshot_output_path=tmp_path / "permission.json",
        now=NOW,
        probe_backend=_backend(permission="write"),
    )

    assert result.accepted is False
    assert GitHubPrincipalPermissionSnapshotSupplyReason.MISSING_PRINCIPAL_PUBLIC_KEY in result.rejection_reasons


def test_supplier_rejects_output_inside_repo(tmp_path: Path) -> None:
    result = run_reddog_github_principal_permission_snapshot_supply(
        repo_root=REPO_ROOT,
        repo_full_name="FOUNDUPS/Foundups-Agent",
        foundup_id="paccess_001",
        principal_public_key="pub:principal",
        principal_authority_record_output_path=REPO_ROOT / "principal.json",
        permission_snapshot_output_path=tmp_path / "permission.json",
        now=NOW,
        probe_backend=_backend(permission="write"),
    )

    assert result.accepted is False
    assert GitHubPrincipalPermissionSnapshotSupplyReason.OUTPUT_PATH_INVALID in result.rejection_reasons
    assert not (REPO_ROOT / "principal.json").exists()


def test_supplier_rejects_invalid_foundup_scope(tmp_path: Path) -> None:
    result = run_reddog_github_principal_permission_snapshot_supply(
        repo_root=REPO_ROOT,
        repo_full_name="FOUNDUPS/Foundups-Agent",
        foundup_id="repo",
        principal_public_key="pub:principal",
        principal_authority_record_output_path=tmp_path / "principal.json",
        permission_snapshot_output_path=tmp_path / "permission.json",
        now=NOW,
        probe_backend=_backend(permission="write"),
    )

    assert result.accepted is False
    assert GitHubPrincipalPermissionSnapshotSupplyReason.INVALID_FOUNDUP_ID in result.rejection_reasons


def test_module_has_no_direct_execution_signing_or_holoindex_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "holo_index",
        "hmac",
        "secrets",
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls
