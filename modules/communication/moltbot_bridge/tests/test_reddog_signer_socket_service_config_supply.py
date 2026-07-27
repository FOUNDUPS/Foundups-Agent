"""Tests for REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply import (
    FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID,
    FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID,
    FAIL_SIGNER_CONFIG_LIMITS_INVALID,
    FAIL_SIGNER_CONFIG_OP_REF_INVALID,
    FAIL_SIGNER_CONFIG_OP_REF_REUSED,
    FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID,
    FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID,
    FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID,
    FAIL_SIGNER_CONFIG_WRITE_FAILED,
    SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
    SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT,
    run_reddog_signer_socket_service_config_supply,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_signer_socket_service_config_supply.py"
)
_PRINCIPAL_PUBLIC_KEY = encode_ed25519_public_key(bytes(range(32)))
_REDDOG_PUBLIC_KEY = encode_ed25519_public_key(bytes(range(32, 64)))


def _repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    return path


def _authority_profile(**overrides: object) -> dict[str, object]:
    profile: dict[str, object] = {
        "principal_id": "github:mjtrout",
        "principal_provider": "github",
        "principal_public_key": _PRINCIPAL_PUBLIC_KEY,
        "reddog_id": "reddog:foundups-agent",
        "reddog_public_key": _REDDOG_PUBLIC_KEY,
        "permission_snapshot_digest": "sha256:" + "1" * 64,
        "key_epoch": "epoch-1",
        "consensus_receipt_digest": "sha256:" + "2" * 64,
        "authority_profile_source_receipt_id": "sha256:" + "3" * 64,
        "identity_ttl_seconds": 600,
        "work_authority_ttl_seconds": 300,
    }
    profile.update(overrides)
    return profile


def _kwargs(repo: Path, runtime: Path, **overrides: object) -> dict[str, object]:
    signer_runtime = runtime.parent / f"{runtime.name}-signer-state"
    values: dict[str, object] = {
        "repo_root": repo,
        "runtime_root": runtime,
        "signer_runtime_root": signer_runtime,
        "authority_profile": _authority_profile(),
        "output_path": runtime / "signer-service.json",
        "socket_path": runtime / "reddog-signer.sock",
        "principal_signing_key_ref": "op://prod-vault/principal/private",
        "principal_audit_mac_key_ref": "op://prod-vault/principal/audit",
        "reddog_signing_key_ref": "op://prod-vault/reddog/private",
        "reddog_audit_mac_key_ref": "op://prod-vault/reddog/audit",
        "peer_uid_to_principal": {1001: "github:mjtrout"},
        "allowed_gids": (1002,),
        "max_requests": 2,
    }
    values.update(overrides)
    return values


def test_config_supply_writes_multi_profile_signer_cli_config(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    result = run_reddog_signer_socket_service_config_supply(**_kwargs(repo, runtime))

    assert result.accepted is True
    assert result.status == SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT
    assert result.profile_count == 2
    assert result.config_supply_receipt_id and result.config_supply_receipt_id.startswith("sha256:")
    assert result.config_digest and result.config_digest.startswith("sha256:")
    assert result.no_secret_values_written is True
    assert result.no_secret_values_resolved is True
    assert result.no_signer_started is True
    assert result.no_holoindex_reindex_performed is True
    assert not (repo / "signer-service.json").exists()

    payload = json.loads((runtime / "signer-service.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == SIGNER_SERVICE_CONFIG_SCHEMA_VERSION
    assert payload["runtime_root"] == str(runtime.resolve())
    assert payload["signer_runtime_root"] == str(
        (runtime.parent / f"{runtime.name}-signer-state").resolve()
    )
    assert payload["provider_mode"] == "WSP71_PERMISSIONED"
    assert payload["allow_test_only_key_material"] is False
    assert payload["permission_snapshot_fresh"] is True
    assert payload["socket_path"] == str((runtime / "reddog-signer.sock").resolve())
    control_policy = payload["control_loop_authority_policy"]
    assert control_policy == {
        "issuer_principal_id": "github:mjtrout",
        "signer_public_key": _REDDOG_PUBLIC_KEY,
        "key_epoch": "epoch-1",
        "consensus_receipt_digest": "sha256:" + "2" * 64,
        "authority_profile_digest": control_policy["authority_profile_digest"],
        "authority_profile_source_receipt_id": "sha256:" + "3" * 64,
    }
    expected_profile_digest = "sha256:" + hashlib.sha256(
        json.dumps(
            _authority_profile(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    assert control_policy["authority_profile_digest"] == expected_profile_digest
    assert payload["peer_policy"] == {
        "uid_to_principal": {"1001": "github:mjtrout"},
        "allowed_gids": [1002],
        "transport": "unix_socket",
        "credential_source_prefix": "kernel_peer_credential",
    }
    profiles = payload["key_provider_profiles"]
    assert [item["signer_profile_id"] for item in profiles] == [
        "principal-identity",
        "reddog-work-authority",
    ]
    assert profiles[0]["expected_public_key"] == _PRINCIPAL_PUBLIC_KEY
    assert profiles[0]["expected_key_fingerprint"] == public_key_fingerprint(
        _PRINCIPAL_PUBLIC_KEY
    )
    assert profiles[1]["expected_public_key"] == _REDDOG_PUBLIC_KEY
    assert profiles[1]["expected_key_fingerprint"] == public_key_fingerprint(
        _REDDOG_PUBLIC_KEY
    )
    serialized = json.dumps(payload, sort_keys=True)
    assert "ed25519-private-raw-b64-v1" not in serialized
    assert "audit-mac-test-key-b64-v1" not in serialized


def test_config_supply_rejects_invalid_authority_profile_and_key_reuse(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"

    missing = run_reddog_signer_socket_service_config_supply(
        **_kwargs(repo, runtime, authority_profile=_authority_profile(principal_public_key=""))
    )
    reused = run_reddog_signer_socket_service_config_supply(
        **_kwargs(
            repo,
            runtime,
            authority_profile=_authority_profile(
                reddog_public_key=_PRINCIPAL_PUBLIC_KEY
            ),
        )
    )

    assert missing.accepted is False
    assert any(
        reason.startswith(FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID)
        for reason in missing.rejection_reasons
    )
    assert reused.accepted is False
    assert FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID + ":key_reuse" in reused.rejection_reasons


def test_config_supply_rejects_malformed_public_key_before_write(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"

    result = run_reddog_signer_socket_service_config_supply(
        **_kwargs(
            repo,
            runtime,
            authority_profile=_authority_profile(
                reddog_public_key="ed25519-pub-v1:not-a-key"
            ),
        )
    )

    assert result.accepted is False
    assert (
        FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID + ":runtime_config"
        in result.rejection_reasons
    )
    assert not (runtime / "signer-service.json").exists()


def test_config_supply_rejects_inside_repo_or_existing_socket_paths(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    existing_socket = runtime / "reddog-signer.sock"
    existing_socket.write_text("", encoding="utf-8")

    inside_output = run_reddog_signer_socket_service_config_supply(
        **_kwargs(repo, runtime, output_path=repo / "signer-service.json")
    )
    inside_socket = run_reddog_signer_socket_service_config_supply(
        **_kwargs(repo, runtime, socket_path=repo / "reddog-signer.sock")
    )
    existing = run_reddog_signer_socket_service_config_supply(
        **_kwargs(repo, runtime, socket_path=existing_socket)
    )

    assert FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID in inside_output.rejection_reasons
    assert FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID in inside_socket.rejection_reasons
    assert FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID in existing.rejection_reasons


def test_config_supply_rejects_paths_outside_bound_runtime_root(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    outside = tmp_path / "outside"

    output = run_reddog_signer_socket_service_config_supply(
        **_kwargs(repo, runtime, output_path=outside / "signer-service.json")
    )
    anchor = run_reddog_signer_socket_service_config_supply(
        **_kwargs(
            repo,
            runtime,
            control_loop_anchor_path=outside / "anchor.json",
        )
    )

    assert FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID in output.rejection_reasons
    assert FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID in anchor.rejection_reasons


def test_config_supply_rejects_nested_config_output_path(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"

    result = run_reddog_signer_socket_service_config_supply(
        **_kwargs(
            repo,
            runtime,
            output_path=runtime / "nested" / "signer-service.json",
        )
    )

    assert not result.accepted
    assert FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID in result.rejection_reasons


def test_config_supply_rejects_nested_socket_or_anchor_path(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    signer_runtime = tmp_path / "runtime-signer-state"

    socket = run_reddog_signer_socket_service_config_supply(
        **_kwargs(
            repo,
            runtime,
            socket_path=runtime / "nested" / "reddog-signer.sock",
        )
    )
    anchor = run_reddog_signer_socket_service_config_supply(
        **_kwargs(
            repo,
            runtime,
            control_loop_anchor_path=signer_runtime / "nested" / "anchor.json",
        )
    )

    assert FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID in socket.rejection_reasons
    assert (
        FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID
        in anchor.rejection_reasons
    )


def test_config_supply_rejects_shared_resident_and_signer_runtime_root(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    state = tmp_path / "state"
    runtime = state / "resident"

    for signer_root in (runtime, runtime / "signer", state):
        result = run_reddog_signer_socket_service_config_supply(
            **_kwargs(repo, runtime, signer_runtime_root=signer_root)
        )
        assert not result.accepted
        assert (
            FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID
            in result.rejection_reasons
        )


def test_config_supply_rejects_hard_linked_output_without_mutating_source(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text('{"sentinel":true}\n', encoding="utf-8")
    output = runtime / "signer-service.json"
    try:
        os.link(outside, output)
    except OSError as exc:
        pytest.skip(f"hard-link creation unavailable: {exc}")

    result = run_reddog_signer_socket_service_config_supply(
        **_kwargs(repo, runtime, output_path=output)
    )

    assert not result.accepted
    assert result.rejection_reasons == (FAIL_SIGNER_CONFIG_WRITE_FAILED,)
    assert outside.read_text(encoding="utf-8") == '{"sentinel":true}\n'


def test_config_supply_rejects_bad_or_reused_op_refs(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"

    bad = run_reddog_signer_socket_service_config_supply(
        **_kwargs(repo, runtime, principal_signing_key_ref="not-op")
    )
    reused = run_reddog_signer_socket_service_config_supply(
        **_kwargs(
            repo,
            runtime,
            reddog_audit_mac_key_ref="op://prod-vault/reddog/private",
        )
    )

    assert FAIL_SIGNER_CONFIG_OP_REF_INVALID in bad.rejection_reasons
    assert FAIL_SIGNER_CONFIG_OP_REF_REUSED in reused.rejection_reasons


def test_config_supply_rejects_peer_policy_and_limit_errors(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"

    bad_peer = run_reddog_signer_socket_service_config_supply(
        **_kwargs(repo, runtime, peer_uid_to_principal={})
    )
    bad_limit = run_reddog_signer_socket_service_config_supply(
        **_kwargs(repo, runtime, max_requests=1)
    )

    assert FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID in bad_peer.rejection_reasons
    assert FAIL_SIGNER_CONFIG_LIMITS_INVALID in bad_limit.rejection_reasons


def test_config_supply_module_has_no_secret_resolution_spawn_or_runtime_authority_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "http",
        "git",
        "holo_index",
    }
    banned_name_calls = {"eval", "exec", "compile", "__import__", "open"}
    banned_attrs = {
        "getenv",
        "environ",
        "system",
        "popen",
        "run",
        "Popen",
        "check_call",
        "check_output",
        "spawn",
    }
    banned_name_fragments = ("openclaw", "hermes", "holoindex")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
            assert not any(fragment in node.module.lower() for fragment in banned_name_fragments)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_name_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs
