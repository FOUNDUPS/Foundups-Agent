"""Tests for runtime control-loop signer context resolution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_signing_context import (
    build_control_loop_receipt_signing_context,
)


def _source_profile(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "reddog_authority_profile_source.v1",
        "principal_id": "github:mjtrout",
        "principal_provider": "github",
        "principal_public_key": "ed25519-pub-v1:" + "B" * 43,
        "reddog_id": "reddog:architect",
        "reddog_public_key": "ed25519-pub-v1:" + "A" * 43,
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "foundup_id": "paccess_001",
        "allowed_paths": ["modules/foundups/paccess_001/src/**"],
        "denied_paths": ["modules/foundups/paccess_001/secrets/**"],
        "requested_operation": "worktree_create",
        "permission_snapshot_digest": "sha256:" + "1" * 64,
        "identity_nonce": "identity-nonce-1",
        "work_authority_nonce": "work-nonce-1",
        "issued_at": 1_700_000_000,
        "identity_expires_at": 1_800_000_000,
        "work_authority_expires_at": 1_800_000_000,
        "valve_state_required": "VALVE_OPEN_WORKTREE_CREATE",
        "key_epoch": "epoch-1",
        "required_tests": ["pytest focused"],
        "required_policy_gates": ["WSP_97"],
        "consensus_receipt_digest": "sha256:" + "c" * 64,
        "sovereign_authorization_digest": "sha256:" + "5" * 64,
        "source_authority_basis": {
            "principal_verified_subject_digest": "sha256:" + "2" * 64,
            "principal_repo_scope": ["FOUNDUPS/Foundups-Agent"],
            "principal_foundup_scope": ["paccess_001"],
            "permission_snapshot_digest": "sha256:" + "1" * 64,
            "permission_snapshot_expires_at": 1_800_000_000,
            "permission_snapshot_can_write": True,
            "permission_snapshot_can_admin": False,
        },
    }
    value.update(overrides)
    value["authority_profile_source_receipt_id"] = "sha256:" + hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    ).hexdigest()
    return value


def _write_profiles(
    runtime: Path,
    *,
    source_path: Path | None = None,
    profile_path: Path | None = None,
    source_overrides: dict[str, object] | None = None,
    profile_overrides: dict[str, object] | None = None,
) -> tuple[Path, Path]:
    source = _source_profile(**(source_overrides or {}))
    profile = {
        **source,
        "operational_context_binding": {
            "queue_item_id": "queue-1",
            "claim_id": "claim-1",
            "architect_determination_receipt_id": "determination-1",
            "wsp15_allocation_receipt": {
                "receipt_id": "sha256:" + "3" * 64
            },
        },
    }
    profile.update(profile_overrides or {})
    source_file = source_path or runtime / "authority_profile_source.json"
    profile_file = profile_path or runtime / "authority_profile.json"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    profile_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text(json.dumps(source), encoding="utf-8")
    profile_file.write_text(json.dumps(profile), encoding="utf-8")
    return source_file, profile_file


def _source_receipt(path: Path) -> str:
    return str(
        json.loads(path.read_text(encoding="utf-8"))[
            "authority_profile_source_receipt_id"
        ]
    )


def _build(
    repo: Path,
    source: Path,
    profile: Path,
    *,
    expected_receipt: str | None = None,
    signer_socket_connector: object = None,
):
    return build_control_loop_receipt_signing_context(
        repo_root=repo,
        authority_profile_path=profile,
        authority_profile_source_path=source,
        signer_socket_path=source.parent / "reddog.sock",
        expected_authority_profile_source_receipt_id=(
            expected_receipt or _source_receipt(source)
        ),
        signer_socket_connector=signer_socket_connector,
    )


def test_context_binds_promoted_profile_source_and_existing_signer(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source, profile = _write_profiles(tmp_path / "runtime")

    context = _build(
        repo,
        source,
        profile,
        signer_socket_connector=lambda *_args: b"{}",
    )

    assert context.issuer_principal_id == "github:mjtrout"
    assert context.key_epoch == "epoch-1"
    assert context.authority_tier == "HIGH"
    assert context.consensus_receipt_digest == "sha256:" + "c" * 64
    assert context.authority_profile_digest.startswith("sha256:")


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"principal_id": ""}, "principal_id_invalid"),
        ({"key_epoch": ""}, "key_epoch_invalid"),
        ({"consensus_receipt_digest": ""}, "consensus_receipt_digest_invalid"),
        ({"consensus_receipt_digest": "sha256:bad"}, "consensus_receipt_digest_invalid"),
        (
            {
                "requested_operation": "feature_slice",
                "valve_state_required": "VALVE_CLOSED",
            },
            "authority_tier_invalid",
        ),
        ({"reddog_public_key": "not-a-key"}, "public_key_invalid"),
        ({"schema_version": "untrusted.v1"}, "profile_schema_invalid"),
        (
            {"sovereign_authorization_digest": "sha256:bad"},
            "sovereign_authorization_digest_invalid",
        ),
    ],
)
def test_context_rejects_missing_authority_bindings(
    tmp_path: Path,
    overrides: dict[str, object],
    reason: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source, profile = _write_profiles(
        tmp_path / "runtime", source_overrides=overrides
    )

    with pytest.raises(ValueError, match=reason):
        _build(
            repo,
            source,
            profile,
            signer_socket_connector=lambda *_args: b"{}",
        )


def test_context_rejects_mismatched_profile_source_receipt(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source, profile = _write_profiles(tmp_path / "runtime")

    with pytest.raises(ValueError, match="profile_source_receipt_invalid"):
        _build(
            repo,
            source,
            profile,
            expected_receipt="sha256:" + "f" * 64,
            signer_socket_connector=lambda *_args: b"{}",
        )


def test_context_rejects_profile_inside_repo_or_unavailable_signer(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source, inside = _write_profiles(
        tmp_path / "runtime", profile_path=repo / "authority_profile.json"
    )
    with pytest.raises(ValueError, match="inside_repo"):
        _build(
            repo,
            source,
            inside,
            signer_socket_connector=lambda *_args: b"{}",
        )

    source, outside = _write_profiles(tmp_path / "runtime")
    with pytest.raises(ValueError, match="signer_client_unavailable"):
        _build(repo, source, outside)


def test_context_rejects_promoted_profile_that_rewrites_its_source(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source, profile = _write_profiles(
        tmp_path / "runtime",
        profile_overrides={"principal_id": "github:forged"},
    )

    with pytest.raises(ValueError, match="profile_source_binding_invalid"):
        _build(
            repo,
            source,
            profile,
            signer_socket_connector=lambda *_args: b"{}",
        )


def test_context_rejects_profile_without_promotion_binding(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source, profile = _write_profiles(
        tmp_path / "runtime", profile_overrides={"operational_context_binding": None}
    )

    with pytest.raises(ValueError, match="profile_promotion_binding_invalid"):
        _build(
            repo,
            source,
            profile,
            signer_socket_connector=lambda *_args: b"{}",
        )


def test_context_rejects_self_hashed_source_without_verified_authority_basis(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source, profile = _write_profiles(
        tmp_path / "runtime",
        source_overrides={"source_authority_basis": {"untrusted": True}},
    )

    with pytest.raises(ValueError, match="profile_source_basis_invalid"):
        _build(
            repo,
            source,
            profile,
            signer_socket_connector=lambda *_args: b"{}",
        )
