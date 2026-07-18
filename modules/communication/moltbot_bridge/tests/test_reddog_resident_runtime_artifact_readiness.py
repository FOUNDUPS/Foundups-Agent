"""Adversarial tests for seven-artifact resident semantic readiness."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_resident_runtime_artifact_readiness import (
    validate_reddog_resident_runtime_artifacts,
)
from modules.communication.moltbot_bridge.src.reddog_execution_valve_use_time_authority import (
    SIGNED_RUNTIME_ARTIFACT_MANIFEST_PRODUCER_MISSING,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_live_canary_test_support import (
    NOW, QUEUE_ID, _roots,
)


def _validate(repo: Path, runtime: Path):
    return validate_reddog_resident_runtime_artifacts(
        repo_root=repo, runtime_root=runtime, queue_item_id=QUEUE_ID,
        now_epoch=int(datetime.fromisoformat(NOW).timestamp()),
    )


def _mutate(runtime: Path, filename: str, mutation: str) -> None:
    path = runtime / filename
    payload = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "work_revision":
        payload["revision"] = "forged"
    elif mutation == "profile_model":
        payload["model_selection_digest"] = "sha256:forged"
    elif mutation == "valve_token":
        payload["sovereign_worktree_token"] = None
    elif mutation == "permission_expiry":
        snapshot = next(iter(payload["snapshots"].values()))
        snapshot["expires_at"] = 1
    elif mutation == "principal_key":
        principal = next(iter(payload["principals"].values()))
        principal["principal_public_key"] = "ed25519-pub-v1:forged"
    elif mutation == "signer_key":
        payload["key_provider_profiles"][0]["expected_public_key"] = "ed25519-pub-v1:forged"
    elif mutation == "packet_digest":
        payload["config_digest"] = "sha256:forged"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def test_unsigned_seven_artifact_pack_is_not_execution_authority(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)

    result = _validate(repo, runtime)

    assert result.accepted is False
    assert len(result.checks) == 7
    valve = next(item for item in result.checks if item.filename == "execution_valve_env.json")
    signer = next(item for item in result.checks if item.filename == "signer_service_config.json")
    assert SIGNED_RUNTIME_ARTIFACT_MANIFEST_PRODUCER_MISSING in valve.rejection_reasons
    assert "signer_client_peer_handshake_verifier_missing" in signer.rejection_reasons
    assert result.authorization_mode == "signed_work_authority_consensus"
    assert result.authorization_binding_digest and result.authorization_binding_digest.startswith("sha256:")


def test_linked_runtime_root_cannot_supply_artifacts(tmp_path: Path) -> None:
    repo, runtime = _roots(tmp_path)
    linked = tmp_path / "linked-runtime"
    try:
        linked.symlink_to(runtime, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    result = _validate(repo, linked)

    assert result.accepted is False
    assert all(check.accepted is False for check in result.checks)


@pytest.mark.parametrize(
    ("filename", "mutation"),
    [
        ("authoritative_work_state.json", "work_revision"),
        ("authority_profile.json", "profile_model"),
        ("execution_valve_env.json", "valve_token"),
        ("permission_snapshots.json", "permission_expiry"),
        ("principal_authority_records.json", "principal_key"),
        ("signer_service_config.json", "signer_key"),
        ("signer_service_run_packet.json", "packet_digest"),
    ],
)
def test_each_artifact_fails_closed_when_semantically_spliced(
    tmp_path: Path, filename: str, mutation: str,
) -> None:
    repo, runtime = _roots(tmp_path)
    _mutate(runtime, filename, mutation)

    result = _validate(repo, runtime)

    assert result.accepted is False
    check = next(item for item in result.checks if item.filename == filename)
    assert check.accepted is False
    assert check.rejection_reasons


@pytest.mark.parametrize(
    ("filename", "field"),
    [
        ("signer_service_config.json", "private_key"),
        ("signer_service_run_packet.json", "access_token"),
    ],
)
def test_signer_artifacts_reject_forbidden_keys_even_when_null(
    tmp_path: Path, filename: str, field: str,
) -> None:
    repo, runtime = _roots(tmp_path)
    path = runtime / filename
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload[field] = None
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    result = _validate(repo, runtime)

    check = next(item for item in result.checks if item.filename == filename)
    assert check.accepted is False
    assert any("forbidden_key_present" in reason for reason in check.rejection_reasons)
    assert any("field_set_invalid" in reason for reason in check.rejection_reasons)
