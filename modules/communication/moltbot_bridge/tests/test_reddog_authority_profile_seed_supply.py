"""Tests for REDDOG_AUTHORITY_PROFILE_SEED_SUPPLY_PHASE1."""

from __future__ import annotations

import ast
import json
from dataclasses import asdict
from pathlib import Path

from modules.communication.moltbot_bridge.src import (
    reddog_architect_fix_signed_wsp15_work_order_promotion as promotion,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_refresh_runtime import (
    InMemoryAuthoritativeWorkStateStore,
)
from modules.communication.moltbot_bridge.src.reddog_authority_profile_seed_supply import (
    AUTHORITY_PROFILE_SEED_SUPPLY_ACCEPT,
    AUTHORITY_PROFILE_SEED_SUPPLY_REJECT,
    AuthorityProfileSeedSupplyReason,
    run_reddog_authority_profile_seed_supply,
)
from modules.communication.moltbot_bridge.src.reddog_authority_profile_source_artifact_supply import (
    run_reddog_authority_profile_source_artifact_supply,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _determination,
    _memex_supply,
    _model_selection,
    _work_state,
)
from modules.communication.moltbot_bridge.tests.test_reddog_authority_profile_source_artifact_supply import (
    _principal,
    _snapshot,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_authority_profile_seed_supply.py"
)
NOW = 1_800_000_000


def _supply(tmp_path: Path, **overrides):
    params = {
        "repo_root": REPO_ROOT,
        "architect_determination": _determination(),
        "model_selection_receipt": _model_selection(),
        "memex_supply_receipt": _memex_supply(),
        "principal_authority_record": _principal(),
        "permission_snapshot": _snapshot(),
        "output_path": tmp_path / "runtime" / "authority_profile_seed.json",
        "reddog_id": "reddog:architect",
        "reddog_public_key": "pub:reddog",
        "now_epoch": NOW,
    }
    params.update(overrides)
    return run_reddog_authority_profile_seed_supply(**params)


def test_seed_supply_writes_seed_consumable_by_source_supplier_and_promotion(tmp_path: Path) -> None:
    seed_result = _supply(
        tmp_path,
        consensus_receipt_digest="sha256:consensus",
        sovereign_authorization_digest="sha256:sovereign",
    )

    assert seed_result.accepted is True
    assert seed_result.status == AUTHORITY_PROFILE_SEED_SUPPLY_ACCEPT
    assert seed_result.seed_supply_receipt_id and seed_result.seed_supply_receipt_id.startswith("sha256:")
    seed = json.loads(Path(seed_result.output_path or "").read_text(encoding="utf-8"))
    assert seed["schema_version"] == "reddog_authority_profile_seed.v1"
    assert seed["principal_id"] == "github:mjtrout"
    assert seed["permission_snapshot_digest"] == "sha256:permission"
    assert seed["holoindex_evidence"]["index_gap_detected"] is False
    assert seed["no_holoindex_reindex_performed"] is True

    source_path = tmp_path / "runtime" / "authority_profile_source.json"
    source = run_reddog_authority_profile_source_artifact_supply(
        repo_root=REPO_ROOT,
        authority_seed=seed,
        principal_authority_record=_principal(),
        permission_snapshot=_snapshot(),
        output_path=source_path,
        now_epoch=NOW,
    )
    assert source.accepted is True

    profile = json.loads(source_path.read_text(encoding="utf-8"))
    promoted = promotion.promote_reddog_architect_fix_to_signed_wsp15_work_order(
        architect_determination=_determination(),
        work_state_store=InMemoryAuthoritativeWorkStateStore(_work_state()),
        authority_profile=profile,
        model_selection_receipt=_model_selection(),
        memex_supply_receipt=_memex_supply(),
        worker_id="reddog-seed-test",
        now_iso="2026-07-16T00:00:00+00:00",
    )
    assert promoted.accepted is True
    assert promoted.authority_profile is not None
    assert promoted.authority_profile["seed_supply_receipt_id"] == seed["seed_supply_receipt_id"]


def test_seed_supply_rejects_missing_reddog_public_key(tmp_path: Path) -> None:
    result = _supply(tmp_path, reddog_public_key="")

    assert result.accepted is False
    assert result.status == AUTHORITY_PROFILE_SEED_SUPPLY_REJECT
    assert AuthorityProfileSeedSupplyReason.MISSING_REDDOG_PUBLIC_KEY in result.rejection_reasons


def test_seed_supply_rejects_principal_reddog_key_reuse(tmp_path: Path) -> None:
    result = _supply(tmp_path, reddog_public_key="pub:principal")

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.PRINCIPAL_REDDOG_KEY_REUSE in result.rejection_reasons


def test_seed_supply_rejects_high_authority_without_cosign(tmp_path: Path) -> None:
    result = _supply(tmp_path, requested_operation="create_foundup")

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.HIGH_AUTHORITY_COSIGN_MISSING in result.rejection_reasons


def test_seed_supply_rejects_worktree_intent_for_low_operation_without_cosign(tmp_path: Path) -> None:
    result = _supply(tmp_path, requested_operation="inspect_repo")

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.HIGH_AUTHORITY_COSIGN_MISSING in result.rejection_reasons


def test_seed_supply_rejects_live_enqueue_intent_without_cosign(tmp_path: Path) -> None:
    result = _supply(
        tmp_path,
        requested_operation="inspect_repo",
        valve_state_required="VALVE_OPEN_LIVE_ENQUEUE",
    )

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.HIGH_AUTHORITY_COSIGN_MISSING in result.rejection_reasons


def test_seed_supply_normalizes_empty_worktree_intent_before_classification(tmp_path: Path) -> None:
    for value in (None, ""):
        result = _supply(
            tmp_path,
            requested_operation="inspect_repo",
            valve_state_required=value,
        )
        assert result.accepted is False
        assert AuthorityProfileSeedSupplyReason.HIGH_AUTHORITY_COSIGN_MISSING in result.rejection_reasons


def test_seed_supply_rejects_consensus_without_sovereign_authorization(tmp_path: Path) -> None:
    result = _supply(tmp_path, consensus_receipt_digest="sha256:consensus")

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.HIGH_AUTHORITY_COSIGN_MISSING in result.rejection_reasons


def test_seed_supply_accepts_high_authority_with_cosign(tmp_path: Path) -> None:
    result = _supply(
        tmp_path,
        requested_operation="create_foundup",
        consensus_receipt_digest="sha256:consensus",
        sovereign_authorization_digest="sha256:sovereign",
    )

    assert result.accepted is True
    seed = json.loads(Path(result.output_path or "").read_text(encoding="utf-8"))
    assert seed["consensus_receipt_digest"] == "sha256:consensus"
    assert seed["sovereign_authorization_digest"] == "sha256:sovereign"


def test_seed_supply_rejects_memex_foundup_mismatch(tmp_path: Path) -> None:
    result = _supply(tmp_path, memex_supply_receipt=_memex_supply(foundup_id="other_foundup"))

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.FOUNDUP_SCOPE_INVALID in result.rejection_reasons


def test_seed_supply_rejects_output_inside_repo(tmp_path: Path) -> None:
    result = _supply(tmp_path, output_path=REPO_ROOT / "authority_profile_seed.json")

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.OUTPUT_PATH_INVALID in result.rejection_reasons
    assert not (REPO_ROOT / "authority_profile_seed.json").exists()


def test_seed_supply_rejects_missing_evidence_refs(tmp_path: Path) -> None:
    determination = _determination()
    determination["queue_candidate"]["evidence_refs"] = []
    result = _supply(tmp_path, architect_determination=determination)

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.HOLOINDEX_EVIDENCE_INVALID in result.rejection_reasons


def test_seed_supply_rejects_allocation_mismatch(tmp_path: Path) -> None:
    determination = _determination()
    determination["wsp15_allocation_receipt_id"] = "sha256:wrong"
    result = _supply(tmp_path, architect_determination=determination)

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.WSP15_ALLOCATION_MISMATCH in result.rejection_reasons


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
