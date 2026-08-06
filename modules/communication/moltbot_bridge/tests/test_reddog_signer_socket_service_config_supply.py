"""Tests for REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_publication import (
    architect_fix_publication_state_projection,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_records import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
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
    assert payload["conversation_scope_anchor_path"] == str(
        (
            runtime.parent
            / f"{runtime.name}-signer-state"
            / "conversation_scope_anchor.json"
        ).resolve()
    )
    assert payload["conversation_scope_signer_policy"] == {
        "issuer_principal_id": "github:mjtrout",
        "issuer_principal_provider": "github",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "signer_public_key": _REDDOG_PUBLIC_KEY,
        "key_epoch": "epoch-1",
        "max_scope_ttl_seconds": 600,
    }
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


@pytest.mark.parametrize("include_marker", (True, False))
def test_config_supply_rejects_prepared_architect_publication(
    tmp_path: Path,
    include_marker: bool,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    publication_id = "sha256:" + "4" * 64
    queue_item_id = "sha256:" + "5" * 64
    claim_id = "sha256:" + "6" * 64
    attestation_id = "reddog_architect_proposal_attestation_" + "7" * 32
    profile_overrides = {
        "proposal_authenticity_attestation_id": attestation_id,
        "operational_context_binding": {
            "queue_item_id": queue_item_id,
            "claim_id": claim_id,
        },
    }
    if include_marker:
        profile_overrides["promotion_publication_id"] = publication_id
    profile = _authority_profile(**profile_overrides)
    promotion = {
        "publication_id": publication_id,
        "queue_item_id": queue_item_id,
        "claim_id": claim_id,
        "authority_profile_digest": canonical_digest(profile),
        "proposal_authenticity_attestation_id": attestation_id,
    }
    work_state = {
        "schema_version": "reddog_authoritative_work_state.v1",
        "architect_fix_promotions": [promotion],
        "wre_queue_items": [
            {"queue_item_id": queue_item_id, "claim_id": claim_id}
        ],
        "worker_claims": [{"claim_id": claim_id}],
    }
    projection = architect_fix_publication_state_projection(
        work_state,
        publication_id=publication_id,
    )
    work_state["architect_fix_publications"] = [
        {
            "schema_version": "reddog_architect_fix_promotion_publication.v1",
            "publication_id": publication_id,
            "state": "STATE_PREPARED",
            "proposal_authenticity_attestation_id": attestation_id,
            "authority_profile_digest": canonical_digest(profile),
            "active_work_state_digest": canonical_digest(projection),
            "base_work_state_digest": "sha256:" + "8" * 64,
        }
    ]
    runtime.mkdir()
    (runtime / "authoritative_work_state.json").write_text(
        json.dumps(work_state),
        encoding="utf-8",
    )

    result = run_reddog_signer_socket_service_config_supply(
        **_kwargs(
            repo,
            runtime,
            authority_profile=profile,
        )
    )

    assert result.accepted is False
    assert FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID in (
        result.rejection_reasons
    )
    assert not (runtime / "signer-service.json").exists()


def test_config_supply_uses_selected_state_not_stale_default(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    publication_id = "sha256:" + "4" * 64
    queue_item_id = "sha256:" + "5" * 64
    claim_id = "sha256:" + "6" * 64
    attestation_id = "reddog_architect_proposal_attestation_" + "7" * 32
    profile = _authority_profile(
        proposal_authenticity_attestation_id=attestation_id,
        operational_context_binding={
            "queue_item_id": queue_item_id,
            "claim_id": claim_id,
        },
    )
    state = {
        "schema_version": "reddog_authoritative_work_state.v1",
        "architect_fix_promotions": [{
            "publication_id": publication_id,
            "queue_item_id": queue_item_id,
            "claim_id": claim_id,
            "authority_profile_digest": canonical_digest(profile),
            "proposal_authenticity_attestation_id": attestation_id,
        }],
        "wre_queue_items": [{"queue_item_id": queue_item_id, "claim_id": claim_id}],
        "worker_claims": [{"claim_id": claim_id}],
    }
    projection = architect_fix_publication_state_projection(
        state,
        publication_id=publication_id,
    )
    publication = {
        "schema_version": "reddog_architect_fix_promotion_publication.v1",
        "publication_id": publication_id,
        "state": "COMMITTED",
        "proposal_authenticity_attestation_id": attestation_id,
        "authority_profile_digest": canonical_digest(profile),
        "active_work_state_digest": canonical_digest(projection),
        "base_work_state_digest": None,
    }
    default_state = {**state, "architect_fix_publications": [publication]}
    selected_state = {
        **state,
        "architect_fix_publications": [{
            **publication,
            "state": "STATE_PREPARED",
            "base_work_state_digest": "sha256:" + "8" * 64,
        }],
    }
    kwargs = _kwargs(repo, runtime, authority_profile=profile)
    (runtime / "authoritative_work_state.json").write_text(
        json.dumps(default_state),
        encoding="utf-8",
    )
    selected_path = runtime / "selected_work_state.json"
    selected_path.write_text(json.dumps(selected_state), encoding="utf-8")
    kwargs["authoritative_work_state_path"] = selected_path

    result = run_reddog_signer_socket_service_config_supply(**kwargs)

    assert result.accepted is False
    assert FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID in result.rejection_reasons
    assert not (runtime / "signer-service.json").exists()


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
    assert not (runtime / "signer-service.json").exists()


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
    assert not (runtime / "signer-service.json").exists()


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
    assert not (runtime / "signer-service.json").exists()


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
    assert (runtime / "signer-service.json").exists()


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
