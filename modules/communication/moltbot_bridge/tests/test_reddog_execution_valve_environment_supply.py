"""Tests for canonical RedDog execution-valve environment supply."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_execution_valve_environment_supply import (
    SCHEMA_VERSION,
    run_reddog_execution_valve_environment_supply,
)
from modules.communication.moltbot_bridge.src.reddog_execution_valve_environment_supply_bootstrap import (
    run_reddog_execution_valve_environment_supply_bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_execution_valve_environment_supply_cli import (
    main as supply_cli_main,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    CANONICAL_BINDING_FIELDS,
    GovernedExecutionValveEnvironment,
    VALVE_CLOSED,
    VALVE_OPEN_WORKTREE_CREATE,
    evaluate_reddog_execution_valve_canonical,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _authority_profile,
    _promote,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_execution_valve import (
    _base_order,
    _full_spine_bundle,
    _request_from_spine,
)


NOW = 1_800_000_000
PERMISSION_DIGEST = "sha256:" + "a" * 64
CONSENSUS_DIGEST = "sha256:" + "b" * 64
SOVEREIGN_DIGEST = "sha256:" + "c" * 64


def _inputs() -> tuple[dict, dict, dict, dict]:
    profile = _authority_profile(
        permission_snapshot_digest=PERMISSION_DIGEST,
        consensus_receipt_digest=CONSENSUS_DIGEST,
        sovereign_authorization_digest=SOVEREIGN_DIGEST,
    )
    result, store = _promote(authority_profile=profile)
    assert result.accepted and result.authority_profile
    work_state = store.load()
    promoted = dict(result.authority_profile)
    permission = {
        "evidence_digest": PERMISSION_DIGEST,
        "expires_at": NOW + 600,
        "can_write": True,
        "can_admin": False,
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
    }
    principal = {
        "principal_id": "github:mjtrout",
        "principal_provider": "github",
        "principal_public_key": "pub:principal",
        "repo_scope": ["FOUNDUPS/Foundups-Agent"],
        "foundup_scope": ["paccess_001"],
        "verified_subject_digest": "sha256:verified",
    }
    receipt_id = "sha256:resolver"
    permissions = {
        "schema_version": "reddog_authority_runtime_resolver_supply.v1",
        "snapshots": {permission["evidence_digest"]: permission},
        "snapshot_count": 1,
        "resolver_supply_receipt_id": receipt_id,
    }
    principals = {
        "schema_version": "reddog_authority_runtime_resolver_supply.v1",
        "principals": {"github|github:mjtrout": principal},
        "principal_count": 1,
        "resolver_supply_receipt_id": receipt_id,
    }
    return work_state, promoted, permissions, principals


def _supply(tmp_path: Path, **overrides):
    work_state, profile, permissions, principals = _inputs()
    params = {
        "repo_root": Path(__file__).resolve().parents[4],
        "work_state": work_state,
        "authority_profile": profile,
        "permission_snapshots": permissions,
        "principal_authority_records": principals,
        "output_path": (tmp_path / "runtime" / "execution_valve_env.json").resolve(),
        "requested_valve_state": VALVE_OPEN_WORKTREE_CREATE,
        "queue_item_id": work_state["wre_queue_items"][0]["queue_item_id"],
        "now_epoch": NOW,
    }
    params.update(overrides)
    return run_reddog_execution_valve_environment_supply(**params)


def test_supply_writes_allowlisted_token_free_governed_environment(tmp_path: Path) -> None:
    result = _supply(tmp_path)

    assert result.accepted is True, result.rejection_reasons
    payload = json.loads(Path(result.output_path or "").read_text(encoding="utf-8"))
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["requested_valve_state"] == VALVE_OPEN_WORKTREE_CREATE
    assert payload["authorization_binding_digest"].startswith("sha256:")
    assert payload["supply_provenance"]["environment_digest"] == result.environment_digest
    assert not any("token" in key.lower() for key in payload)
    assert "permission_ttl_seconds" not in payload
    assert "permission_expires_at" not in payload
    assert GovernedExecutionValveEnvironment.from_mapping(payload).to_dict() == payload


def test_supply_defaults_fail_closed_without_explicit_open_request(tmp_path: Path) -> None:
    result = _supply(tmp_path, requested_valve_state="VALVE_CLOSED")

    assert result.accepted is True
    payload = json.loads(Path(result.output_path or "").read_text(encoding="utf-8"))
    assert payload["valve_dryrun_enabled"] is False
    assert payload["valve_worktree_create_enabled"] is False


def test_supply_rejects_authority_splicing(tmp_path: Path) -> None:
    work_state, profile, permissions, principals = _inputs()
    profile["model_selection_digest"] = "sha256:forged"

    result = _supply(tmp_path, authority_profile=profile)

    assert result.accepted is False


def test_supply_rejects_inside_repo_and_symlink_output(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[4]
    inside = _supply(tmp_path, output_path=repo / "execution_valve_env.json")
    assert inside.accepted is False
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    link = tmp_path / "link.json"
    try:
        link.symlink_to(target)
    except OSError:
        return
    linked = _supply(tmp_path, output_path=link)
    assert linked.accepted is False


def test_governed_environment_rejects_legacy_token_key(tmp_path: Path) -> None:
    result = _supply(tmp_path)
    payload = json.loads(Path(result.output_path or "").read_text(encoding="utf-8"))
    payload["sovereign_worktree_token"] = None

    try:
        GovernedExecutionValveEnvironment.from_mapping(payload)
    except ValueError as exc:
        assert "field_set" in str(exc) or "token_key" in str(exc)
    else:
        raise AssertionError("legacy token key accepted")


def _canonical_request(payload: dict, work_state: dict):
    allocation = work_state["wre_queue_items"][0]["wsp15_allocation_receipt"]
    order = _base_order(
        work_order_id=payload["work_order_id"],
        requested_operation=payload["requested_operation"],
        repo_full_name=payload["repo_full_name"],
        foundup_id=payload["foundup_id"],
        wsp15_allocation_receipt=allocation,
        repo_permission_snapshot={
            "permission_level": "write",
            "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "source": "github_api",
            "digest": payload["permission_snapshot_digest"],
        },
    )
    bundle = _full_spine_bundle(order=order)
    return _request_from_spine(*bundle)


def test_canonical_evaluator_binds_authority_and_uses_trusted_freshness(tmp_path: Path) -> None:
    work_state, _, _, _ = _inputs()
    result = _supply(tmp_path)
    payload = json.loads(Path(result.output_path or "").read_text(encoding="utf-8"))
    expected = {field: payload[field] for field in CANONICAL_BINDING_FIELDS}
    decision = evaluate_reddog_execution_valve_canonical(
        _canonical_request(payload, work_state),
        GovernedExecutionValveEnvironment.from_mapping(payload),
        expected_bindings=expected,
        permission_ttl_seconds=300,
        permission_expires_at=(datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
    )

    assert decision.valve_state == VALVE_OPEN_WORKTREE_CREATE, decision.rejection_reasons
    assert decision.authorization_mode == "signed_work_authority_consensus"
    assert decision.authorization_binding_digest == payload["authorization_binding_digest"]


def test_canonical_evaluator_rejects_independent_binding_mismatch(tmp_path: Path) -> None:
    work_state, _, _, _ = _inputs()
    result = _supply(tmp_path)
    payload = json.loads(Path(result.output_path or "").read_text(encoding="utf-8"))
    expected = {field: payload[field] for field in CANONICAL_BINDING_FIELDS}
    expected["sovereign_authorization_digest"] = "sha256:independent-mismatch"
    decision = evaluate_reddog_execution_valve_canonical(
        _canonical_request(payload, work_state),
        GovernedExecutionValveEnvironment.from_mapping(payload),
        expected_bindings=expected,
        permission_ttl_seconds=300,
        permission_expires_at=(datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
    )

    assert decision.valve_state == VALVE_CLOSED
    assert any("sovereign_authorization_digest" in reason for reason in decision.rejection_reasons)


def _bootstrap_paths(tmp_path: Path) -> dict[str, Path]:
    work_state, profile, permissions, principals = _inputs()
    runtime = (tmp_path / "runtime").resolve()
    runtime.mkdir()
    payloads = {
        "work_state": work_state,
        "authority_profile": profile,
        "permission_snapshots": permissions,
        "principal_authority_records": principals,
    }
    paths: dict[str, Path] = {}
    for name, payload in payloads.items():
        path = runtime / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[name] = path
    paths["output"] = runtime / "execution_valve_env.json"
    return paths


def test_bootstrap_reads_distinct_outside_repo_inputs(tmp_path: Path) -> None:
    paths = _bootstrap_paths(tmp_path)
    work_state = json.loads(paths["work_state"].read_text(encoding="utf-8"))
    result = run_reddog_execution_valve_environment_supply_bootstrap(
        repo_root=Path(__file__).resolve().parents[4],
        work_state_path=paths["work_state"],
        authority_profile_path=paths["authority_profile"],
        permission_snapshots_path=paths["permission_snapshots"],
        principal_authority_records_path=paths["principal_authority_records"],
        output_path=paths["output"],
        requested_valve_state=VALVE_OPEN_WORKTREE_CREATE,
        queue_item_id=work_state["wre_queue_items"][0]["queue_item_id"],
        now_epoch=NOW,
    )

    assert result.accepted is True, result.rejection_reasons
    assert paths["output"].is_file()


def test_bootstrap_rejects_input_output_collision(tmp_path: Path) -> None:
    paths = _bootstrap_paths(tmp_path)
    result = run_reddog_execution_valve_environment_supply_bootstrap(
        repo_root=Path(__file__).resolve().parents[4],
        work_state_path=paths["work_state"],
        authority_profile_path=paths["authority_profile"],
        permission_snapshots_path=paths["permission_snapshots"],
        principal_authority_records_path=paths["principal_authority_records"],
        output_path=paths["authority_profile"],
        requested_valve_state=VALVE_OPEN_WORKTREE_CREATE,
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert "execution_valve_environment_path_collision" in result.rejection_reasons


def test_cli_supplies_canonical_environment(tmp_path: Path, capsys) -> None:
    paths = _bootstrap_paths(tmp_path)
    work_state = json.loads(paths["work_state"].read_text(encoding="utf-8"))

    exit_code = supply_cli_main([
        "--repo-root", str(Path(__file__).resolve().parents[4]),
        "--work-state", str(paths["work_state"]),
        "--authority-profile", str(paths["authority_profile"]),
        "--permission-snapshots", str(paths["permission_snapshots"]),
        "--principal-authority-records", str(paths["principal_authority_records"]),
        "--output", str(paths["output"]),
        "--requested-valve-state", VALVE_OPEN_WORKTREE_CREATE,
        "--queue-item-id", work_state["wre_queue_items"][0]["queue_item_id"],
        "--now-epoch", str(NOW),
    ])

    response = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert response["accepted"] is True
    assert paths["output"].is_file()
