"""Tests for REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY_PHASE1."""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_records import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply import (
    FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID,
    FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID,
    FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID,
    FAIL_SIGNER_CONFIG_LIMITS_INVALID,
    FAIL_SIGNER_CONFIG_OP_REF_INVALID,
    FAIL_SIGNER_CONFIG_OP_REF_REUSED,
    FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID,
    FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID,
    FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID,
    FAIL_SIGNER_CONFIG_WRITE_FAILED,
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
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
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
    runtime.mkdir(parents=True, exist_ok=True)
    state_path = runtime / "authoritative_work_state.json"
    if not state_path.exists():
        state_path.write_text(
            json.dumps(
                {
                    "schema_version": "reddog_authoritative_work_state.v1",
                    "architect_fix_promotions": [],
                    "architect_fix_publications": [],
                }
            ),
            encoding="utf-8",
        )
    signer_runtime = runtime.parent / f"{runtime.name}-signer-state"
    values: dict[str, object] = {
        "repo_root": repo,
        "runtime_root": runtime,
        "signer_runtime_root": signer_runtime,
        "authority_profile": _authority_profile(),
        "authoritative_work_state_path": state_path,
        "output_path": runtime / "signer_service_config.json",
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



def test_config_supply_rejects_architect_profile_with_marker_and_binding_stripped(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    publication_id = "sha256:" + "4" * 64
    queue_item_id = "sha256:" + "5" * 64
    claim_id = "sha256:" + "6" * 64
    attestation_id = "reddog_architect_proposal_attestation_" + "7" * 32
    original = _authority_profile(
        promotion_publication_id=publication_id,
        proposal_authenticity_attestation_id=attestation_id,
        operational_context_binding={
            "queue_item_id": queue_item_id,
            "claim_id": claim_id,
        },
    )
    attacker_profile = dict(original)
    attacker_profile.pop("promotion_publication_id")
    attacker_profile.pop("operational_context_binding")
    state = {
        "schema_version": "reddog_authoritative_work_state.v1",
        "architect_fix_promotions": [{
            "publication_id": publication_id,
            "queue_item_id": queue_item_id,
            "claim_id": claim_id,
            "authority_profile_digest": canonical_digest(original),
            "proposal_authenticity_attestation_id": attestation_id,
        }],
        "architect_fix_publications": [],
    }
    kwargs = _kwargs(repo, runtime, authority_profile=attacker_profile)
    (runtime / "authoritative_work_state.json").write_text(
        json.dumps(state),
        encoding="utf-8",
    )

    result = run_reddog_signer_socket_service_config_supply(**kwargs)

    assert result.accepted is False
    assert FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID in result.rejection_reasons
    assert not (runtime / "signer_service_config.json").exists()


def test_config_supply_rejects_missing_durable_authoritative_state(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    kwargs = _kwargs(repo, runtime)
    (runtime / "authoritative_work_state.json").unlink()

    result = run_reddog_signer_socket_service_config_supply(**kwargs)

    assert result.accepted is False
    assert FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID in (
        result.rejection_reasons
    )
    assert not (runtime / "signer_service_config.json").exists()


def test_config_supply_rejects_injected_state_that_differs_from_durable_state(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    kwargs = _kwargs(
        repo,
        runtime,
        authoritative_work_state={
            "schema_version": "reddog_authoritative_work_state.v1",
            "architect_fix_promotions": [],
            "architect_fix_publications": [],
            "work_state_revision": 1,
        },
    )

    result = run_reddog_signer_socket_service_config_supply(**kwargs)

    assert result.accepted is False
    assert FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID in (
        result.rejection_reasons
    )
    assert not (runtime / "signer_service_config.json").exists()


def test_config_supply_accepts_injected_state_that_matches_durable_state(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    durable_state = {
        "schema_version": "reddog_authoritative_work_state.v1",
        "architect_fix_promotions": [],
        "architect_fix_publications": [],
    }
    result = run_reddog_signer_socket_service_config_supply(
        **_kwargs(
            repo,
            runtime,
            authoritative_work_state=durable_state,
        )
    )

    assert result.accepted is True


@pytest.mark.parametrize("value", (16384, 163840))
def test_config_supply_preserves_explicit_request_budget(
    tmp_path: Path,
    value: int,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    kwargs = _kwargs(repo, runtime)
    if value != 16384:
        kwargs["max_request_bytes"] = value

    result = run_reddog_signer_socket_service_config_supply(**kwargs)

    assert result.accepted, result.rejection_reasons
    config = json.loads(
        (runtime / "signer_service_config.json").read_text(encoding="utf-8")
    )
    assert config["max_request_bytes"] == value
    assert (config.get("conversation_scope_signer_policy") is not None) == (
        value == 163840
    )
    assert (runtime / "signer_service_config.json").exists()


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
    assert not (runtime / "signer_service_config.json").exists()


def test_config_supply_rejects_inside_repo_or_existing_socket_paths(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    existing_socket = runtime / "reddog-signer.sock"
    existing_socket.write_text("", encoding="utf-8")

    inside_output = run_reddog_signer_socket_service_config_supply(
        **_kwargs(repo, runtime, output_path=repo / "signer_service_config.json")
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
        **_kwargs(repo, runtime, output_path=outside / "signer_service_config.json")
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
            output_path=runtime / "nested" / "signer_service_config.json",
        )
    )

    assert not result.accepted
    assert FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID in result.rejection_reasons


def test_config_supply_rejects_noncanonical_output_without_overwriting_state(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    state_path = runtime / "authoritative_work_state.json"
    original = b'{"schema_version":"reddog_authoritative_work_state.v1"}\n'
    state_path.write_bytes(original)

    result = run_reddog_signer_socket_service_config_supply(
        **_kwargs(
            repo,
            runtime,
            authoritative_work_state_path=state_path,
            output_path=state_path,
        )
    )

    assert not result.accepted
    assert FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID in result.rejection_reasons
    assert state_path.read_bytes() == original
    assert not (runtime / "signer_service_config.json").exists()


def test_config_supply_rejects_canonical_output_used_as_work_state(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    target = runtime / "signer_service_config.json"
    original = b'{"schema_version":"reddog_authoritative_work_state.v1"}\n'
    target.write_bytes(original)

    result = run_reddog_signer_socket_service_config_supply(
        **_kwargs(
            repo,
            runtime,
            authoritative_work_state_path=target,
            output_path=target,
        )
    )

    assert not result.accepted
    assert FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID in result.rejection_reasons
    assert target.read_bytes() == original


@pytest.mark.parametrize(
    "reserved_name",
    (
        "authority_profile.json",
        "runtime_artifact_manifest.json",
        "reddog_signer.sock",
        "architect_proposal_nonce_store.json",
        "signer_control_loop_anchor.json",
        "conversation_scope_anchor.json",
    ),
)
def test_config_supply_rejects_runtime_artifact_name_collisions(
    tmp_path: Path,
    reserved_name: str,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    target = runtime / reserved_name
    original = b'{"sentinel":true}\n'
    target.write_bytes(original)

    result = run_reddog_signer_socket_service_config_supply(
        **_kwargs(repo, runtime, output_path=target)
    )

    assert not result.accepted
    assert FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID in result.rejection_reasons
    assert target.read_bytes() == original


@pytest.mark.parametrize(
    "field,value",
    (
        ("harmless_extra", "attacker-selected"),
        ("runtime_api_secret", "must-not-persist"),
    ),
)
def test_config_supply_rejects_unknown_or_secret_profile_fields(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"

    result = run_reddog_signer_socket_service_config_supply(
        **_kwargs(
            repo,
            runtime,
            authority_profile=_authority_profile(**{field: value}),
        )
    )

    assert not result.accepted
    assert any(
        reason.startswith(FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID)
        for reason in result.rejection_reasons
    )
    assert not (runtime / "signer_service_config.json").exists()


def test_config_supply_rejects_nested_unknown_profile_field(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    profile = _authority_profile(
        holoindex_evidence={
            "holoindex_status": "CURRENT",
            "harmless_extra": "attacker-selected",
        }
    )

    result = run_reddog_signer_socket_service_config_supply(
        **_kwargs(repo, runtime, authority_profile=profile)
    )

    assert not result.accepted
    assert (
        FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID
        + ":holoindex_evidence.harmless_extra"
        in result.rejection_reasons
    )
    assert not (runtime / "signer_service_config.json").exists()


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
    output = runtime / "signer_service_config.json"
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
