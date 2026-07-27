"""Tests for REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_authority_profile_source_artifact_supply import (
    AUTHORITY_PROFILE_SOURCE_SUPPLY_ACCEPT,
    AUTHORITY_PROFILE_SOURCE_SUPPLY_REJECT,
    AuthorityProfileSourceSupplyReason,
    run_reddog_authority_profile_source_artifact_supply,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    PrincipalAuthorityRecord,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PermissionSnapshot,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_WORKTREE_CREATE,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _promote,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_authority_profile_source_artifact_supply.py"
)
NOW = 1_800_000_000


def _principal() -> PrincipalAuthorityRecord:
    return PrincipalAuthorityRecord(
        principal_id="github:mjtrout",
        principal_provider="github",
        principal_public_key="pub:principal",
        repo_scope=("FOUNDUPS/Foundups-Agent",),
        foundup_scope=("paccess_001",),
        verified_subject_digest="sha256:verified-subject",
        reward_account="reward:paccess",
        owner_dae="dae:paccess",
    )


def _snapshot(**overrides) -> PermissionSnapshot:
    payload = {
        "evidence_digest": "sha256:permission",
        "expires_at": NOW + 3600,
        "can_write": True,
        "can_admin": False,
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
    }
    payload.update(overrides)
    return PermissionSnapshot(**payload)


def _seed(**overrides):
    payload = {
        "principal_id": "github:mjtrout",
        "principal_provider": "github",
        "reddog_id": "reddog:architect",
        "reddog_public_key": "pub:reddog",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "foundup_id": "paccess_001",
        "allowed_paths": ["modules/foundups/paccess_001/**"],
        "denied_paths": ["modules/foundups/paccess_001/secrets/**"],
        "requested_operation": "create_foundup",
        "permission_snapshot_digest": "sha256:permission",
        "identity_nonce": "identity-nonce-0001",
        "work_authority_nonce": "workauth-nonce-0001",
        "issued_at": NOW,
        "identity_expires_at": NOW + 3600,
        "work_authority_expires_at": NOW + 900,
        "valve_state_required": VALVE_OPEN_WORKTREE_CREATE,
        "key_epoch": "epoch-1",
        "required_tests": ["pytest modules/communication/moltbot_bridge/tests"],
        "required_policy_gates": ["signed_work_order_authority", "execution_valve"],
        "consensus_receipt_digest": "sha256:consensus",
        "sovereign_authorization_digest": "sha256:012-token",
        "holoindex_evidence": {
            "holoindex_query": "RedDog architect FIX promotion",
            "holoindex_status": "bundle_json_ok",
            "index_gap_detected": False,
            "retrieval_quality": "HIGH",
            "applicable_wsps": ["WSP_15", "WSP_97"],
            "evidence_refs": [
                "modules/communication/moltbot_bridge/src/reddog_backend_architect_determination_runtime.py"
            ],
        },
    }
    payload.update(overrides)
    return payload


def test_supplier_writes_profile_source_consumable_by_fix_promotion(tmp_path: Path) -> None:
    output = tmp_path / "runtime" / "authority_profile_source.json"

    result = run_reddog_authority_profile_source_artifact_supply(
        repo_root=REPO_ROOT,
        authority_seed=_seed(),
        principal_authority_record=_principal(),
        permission_snapshot=_snapshot(),
        output_path=output,
        now_epoch=NOW,
    )

    assert result.accepted is True
    assert result.status == AUTHORITY_PROFILE_SOURCE_SUPPLY_ACCEPT
    assert result.authority_profile_source_receipt_id and result.authority_profile_source_receipt_id.startswith(
        "sha256:"
    )
    profile = json.loads(output.read_text(encoding="utf-8"))
    assert profile["principal_public_key"] == "pub:principal"
    assert profile["no_signing_performed"] is True
    assert profile["no_holoindex_reindex_performed"] is True
    assert profile["source_authority_basis"]["permission_snapshot_can_write"] is True

    promoted, _ = _promote(authority_profile=profile)
    assert promoted.accepted is True
    assert promoted.authority_profile is not None
    assert promoted.authority_profile["authority_profile_source_receipt_id"] == profile[
        "authority_profile_source_receipt_id"
    ]


def test_supplier_rejects_output_inside_repo(tmp_path: Path) -> None:
    result = run_reddog_authority_profile_source_artifact_supply(
        repo_root=REPO_ROOT,
        authority_seed=_seed(),
        principal_authority_record=_principal(),
        permission_snapshot=_snapshot(),
        output_path=REPO_ROOT / "authority_profile_source.json",
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert result.status == AUTHORITY_PROFILE_SOURCE_SUPPLY_REJECT
    assert AuthorityProfileSourceSupplyReason.OUTPUT_PATH_INVALID in result.rejection_reasons
    assert not (REPO_ROOT / "authority_profile_source.json").exists()


def test_supplier_rejects_stale_permission_snapshot(tmp_path: Path) -> None:
    result = run_reddog_authority_profile_source_artifact_supply(
        repo_root=REPO_ROOT,
        authority_seed=_seed(),
        principal_authority_record=_principal(),
        permission_snapshot=_snapshot(expires_at=NOW - 100),
        output_path=tmp_path / "runtime" / "authority_profile_source.json",
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert AuthorityProfileSourceSupplyReason.PERMISSION_SNAPSHOT_STALE in result.rejection_reasons


def test_supplier_rejects_path_outside_foundup_scope(tmp_path: Path) -> None:
    result = run_reddog_authority_profile_source_artifact_supply(
        repo_root=REPO_ROOT,
        authority_seed=_seed(allowed_paths=["modules/communication/moltbot_bridge/**"]),
        principal_authority_record=_principal(),
        permission_snapshot=_snapshot(),
        output_path=tmp_path / "runtime" / "authority_profile_source.json",
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert AuthorityProfileSourceSupplyReason.PATH_SCOPE in result.rejection_reasons


def test_supplier_rejects_high_authority_without_cosign(tmp_path: Path) -> None:
    seed = _seed()
    seed.pop("consensus_receipt_digest")
    seed.pop("sovereign_authorization_digest")

    result = run_reddog_authority_profile_source_artifact_supply(
        repo_root=REPO_ROOT,
        authority_seed=seed,
        principal_authority_record=_principal(),
        permission_snapshot=_snapshot(),
        output_path=tmp_path / "runtime" / "authority_profile_source.json",
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert AuthorityProfileSourceSupplyReason.HIGH_AUTHORITY_COSIGN in result.rejection_reasons


def test_supplier_rejects_worktree_intent_for_low_operation_without_cosign(tmp_path: Path) -> None:
    seed = _seed(requested_operation="inspect_repo")
    seed.pop("consensus_receipt_digest")
    seed.pop("sovereign_authorization_digest")

    result = run_reddog_authority_profile_source_artifact_supply(
        repo_root=REPO_ROOT,
        authority_seed=seed,
        principal_authority_record=_principal(),
        permission_snapshot=_snapshot(),
        output_path=tmp_path / "runtime" / "authority_profile_source.json",
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert AuthorityProfileSourceSupplyReason.HIGH_AUTHORITY_COSIGN in result.rejection_reasons


def test_supplier_rejects_live_enqueue_intent_without_cosign(tmp_path: Path) -> None:
    seed = _seed(
        requested_operation="inspect_repo",
        valve_state_required="VALVE_OPEN_LIVE_ENQUEUE",
    )
    seed.pop("consensus_receipt_digest")
    seed.pop("sovereign_authorization_digest")

    result = run_reddog_authority_profile_source_artifact_supply(
        repo_root=REPO_ROOT,
        authority_seed=seed,
        principal_authority_record=_principal(),
        permission_snapshot=_snapshot(),
        output_path=tmp_path / "runtime" / "authority_profile_source.json",
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert AuthorityProfileSourceSupplyReason.HIGH_AUTHORITY_COSIGN in result.rejection_reasons


def test_supplier_rejects_consensus_without_sovereign_authorization(tmp_path: Path) -> None:
    seed = _seed()
    seed.pop("sovereign_authorization_digest")

    result = run_reddog_authority_profile_source_artifact_supply(
        repo_root=REPO_ROOT,
        authority_seed=seed,
        principal_authority_record=_principal(),
        permission_snapshot=_snapshot(),
        output_path=tmp_path / "runtime" / "authority_profile_source.json",
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert AuthorityProfileSourceSupplyReason.HIGH_AUTHORITY_COSIGN in result.rejection_reasons


def test_supplier_rejects_holoindex_gap_authority(tmp_path: Path) -> None:
    evidence = dict(_seed()["holoindex_evidence"])
    evidence["index_gap_detected"] = True

    result = run_reddog_authority_profile_source_artifact_supply(
        repo_root=REPO_ROOT,
        authority_seed=_seed(holoindex_evidence=evidence),
        principal_authority_record=_principal(),
        permission_snapshot=_snapshot(),
        output_path=tmp_path / "runtime" / "authority_profile_source.json",
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert AuthorityProfileSourceSupplyReason.HOLOINDEX_EVIDENCE_INVALID in result.rejection_reasons


def test_supplier_rejects_principal_foundup_scope_mismatch(tmp_path: Path) -> None:
    principal = PrincipalAuthorityRecord(
        principal_id="github:mjtrout",
        principal_provider="github",
        principal_public_key="pub:principal",
        repo_scope=("FOUNDUPS/Foundups-Agent",),
        foundup_scope=("other_foundup",),
        verified_subject_digest="sha256:verified-subject",
    )

    result = run_reddog_authority_profile_source_artifact_supply(
        repo_root=REPO_ROOT,
        authority_seed=_seed(),
        principal_authority_record=principal,
        permission_snapshot=_snapshot(),
        output_path=tmp_path / "runtime" / "authority_profile_source.json",
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert AuthorityProfileSourceSupplyReason.FOUNDUP_OUT_OF_SCOPE in result.rejection_reasons


def test_module_has_no_execution_network_signing_or_reindex_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "git",
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
