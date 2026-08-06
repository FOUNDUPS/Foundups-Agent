"""Profile and publication tests for signer config materialization."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_publication import (
    architect_fix_publication_state_projection,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_records import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply import (
    FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID,
    SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
    SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT,
    run_reddog_signer_socket_service_config_supply,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_socket_service_config_supply import (
    _PRINCIPAL_PUBLIC_KEY,
    _REDDOG_PUBLIC_KEY,
    _authority_profile,
    _kwargs,
    _repo,
)


def _assert_result(result: object, repo: Path) -> None:
    assert result.accepted is True
    assert result.status == SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT
    assert result.profile_count == 2
    assert result.config_supply_receipt_id.startswith("sha256:")
    assert result.config_digest.startswith("sha256:")
    assert result.no_secret_values_written is True
    assert result.no_secret_values_resolved is True
    assert result.no_signer_started is True
    assert result.no_holoindex_reindex_performed is True
    assert not (repo / "signer-service.json").exists()


def _assert_policy_payload(payload: dict, runtime: Path) -> None:
    signer_root = (runtime.parent / f"{runtime.name}-signer-state").resolve()
    assert payload["schema_version"] == SIGNER_SERVICE_CONFIG_SCHEMA_VERSION
    assert payload["runtime_root"] == str(runtime.resolve())
    assert payload["signer_runtime_root"] == str(signer_root)
    assert payload["provider_mode"] == "WSP71_PERMISSIONED"
    assert payload["allow_test_only_key_material"] is False
    assert payload["permission_snapshot_fresh"] is True
    assert payload["socket_path"] == str((runtime / "reddog-signer.sock").resolve())
    assert payload["conversation_scope_anchor_path"] == str(
        signer_root / "conversation_scope_anchor.json"
    )
    assert payload["conversation_scope_signer_policy"] == {
        "issuer_principal_id": "github:mjtrout",
        "issuer_principal_provider": "github",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "signer_public_key": _REDDOG_PUBLIC_KEY,
        "key_epoch": "epoch-1",
        "max_scope_ttl_seconds": 600,
    }


def _assert_authority_and_profiles(payload: dict) -> None:
    control = payload["control_loop_authority_policy"]
    assert control["issuer_principal_id"] == "github:mjtrout"
    assert control["signer_public_key"] == _REDDOG_PUBLIC_KEY
    assert control["authority_profile_source_receipt_id"] == "sha256:" + "3" * 64
    expected = "sha256:" + hashlib.sha256(
        json.dumps(
            _authority_profile(), sort_keys=True,
            separators=(",", ":"), ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    assert control["authority_profile_digest"] == expected
    assert payload["peer_policy"]["uid_to_principal"] == {"1001": "github:mjtrout"}
    profiles = payload["key_provider_profiles"]
    assert [item["signer_profile_id"] for item in profiles] == [
        "principal-identity", "reddog-work-authority",
    ]
    for item, public_key in zip(
        profiles, (_PRINCIPAL_PUBLIC_KEY, _REDDOG_PUBLIC_KEY), strict=True
    ):
        assert item["expected_public_key"] == public_key
        assert item["expected_key_fingerprint"] == public_key_fingerprint(public_key)
    serialized = json.dumps(payload, sort_keys=True)
    assert "ed25519-private-raw-b64-v1" not in serialized
    assert "audit-mac-test-key-b64-v1" not in serialized


def test_config_supply_writes_multi_profile_signer_cli_config(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    result = run_reddog_signer_socket_service_config_supply(**_kwargs(repo, runtime))
    _assert_result(result, repo)
    payload = json.loads((runtime / "signer-service.json").read_text(encoding="utf-8"))
    _assert_policy_payload(payload, runtime)
    _assert_authority_and_profiles(payload)


def _prepared_publication_case(
    include_marker: bool,
) -> tuple[dict[str, object], dict[str, object]]:
    publication_id = "sha256:" + "4" * 64
    queue_item_id = "sha256:" + "5" * 64
    claim_id = "sha256:" + "6" * 64
    attestation_id = "reddog_architect_proposal_attestation_" + "7" * 32
    overrides: dict[str, object] = {
        "proposal_authenticity_attestation_id": attestation_id,
        "operational_context_binding": {
            "queue_item_id": queue_item_id, "claim_id": claim_id,
        },
    }
    if include_marker:
        overrides["promotion_publication_id"] = publication_id
    profile = _authority_profile(**overrides)
    promotion = {
        "publication_id": publication_id, "queue_item_id": queue_item_id,
        "claim_id": claim_id, "authority_profile_digest": canonical_digest(profile),
        "proposal_authenticity_attestation_id": attestation_id,
    }
    state = {
        "schema_version": "reddog_authoritative_work_state.v1",
        "architect_fix_promotions": [promotion],
        "wre_queue_items": [{"queue_item_id": queue_item_id, "claim_id": claim_id}],
        "worker_claims": [{"claim_id": claim_id}],
    }
    projection = architect_fix_publication_state_projection(
        state, publication_id=publication_id
    )
    state["architect_fix_publications"] = [{
        "schema_version": "reddog_architect_fix_promotion_publication.v1",
        "publication_id": publication_id, "state": "STATE_PREPARED",
        "proposal_authenticity_attestation_id": attestation_id,
        "authority_profile_digest": canonical_digest(profile),
        "active_work_state_digest": canonical_digest(projection),
        "base_work_state_digest": "sha256:" + "8" * 64,
    }]
    return profile, state


@pytest.mark.parametrize("include_marker", (True, False))
def test_config_supply_rejects_prepared_architect_publication(
    tmp_path: Path, include_marker: bool,
) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    profile, state = _prepared_publication_case(include_marker)
    runtime.mkdir()
    (runtime / "authoritative_work_state.json").write_text(
        json.dumps(state), encoding="utf-8"
    )
    result = run_reddog_signer_socket_service_config_supply(
        **_kwargs(repo, runtime, authority_profile=profile)
    )
    assert result.accepted is False
    assert FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID in result.rejection_reasons
    assert not (runtime / "signer-service.json").exists()


def _selected_state(profile: dict[str, object]) -> tuple[dict, dict]:
    publication_id = "sha256:" + "4" * 64
    binding = profile["operational_context_binding"]
    queue_item_id, claim_id = binding["queue_item_id"], binding["claim_id"]
    state = {
        "schema_version": "reddog_authoritative_work_state.v1",
        "architect_fix_promotions": [{
            "publication_id": publication_id, "queue_item_id": queue_item_id,
            "claim_id": claim_id, "authority_profile_digest": canonical_digest(profile),
            "proposal_authenticity_attestation_id": profile["proposal_authenticity_attestation_id"],
        }],
        "wre_queue_items": [{"queue_item_id": queue_item_id, "claim_id": claim_id}],
        "worker_claims": [{"claim_id": claim_id}],
    }
    projection = architect_fix_publication_state_projection(
        state, publication_id=publication_id
    )
    publication = {
        "schema_version": "reddog_architect_fix_promotion_publication.v1",
        "publication_id": publication_id, "state": "COMMITTED",
        "proposal_authenticity_attestation_id": profile["proposal_authenticity_attestation_id"],
        "authority_profile_digest": canonical_digest(profile),
        "active_work_state_digest": canonical_digest(projection),
        "base_work_state_digest": None,
    }
    default = {**state, "architect_fix_publications": [publication]}
    selected = {**state, "architect_fix_publications": [{
        **publication, "state": "STATE_PREPARED",
        "base_work_state_digest": "sha256:" + "8" * 64,
    }]}
    return default, selected


def test_config_supply_uses_selected_state_not_stale_default(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    profile = _authority_profile(
        proposal_authenticity_attestation_id=(
            "reddog_architect_proposal_attestation_" + "7" * 32
        ),
        operational_context_binding={
            "queue_item_id": "sha256:" + "5" * 64,
            "claim_id": "sha256:" + "6" * 64,
        },
    )
    default, selected = _selected_state(profile)
    kwargs = _kwargs(repo, runtime, authority_profile=profile)
    (runtime / "authoritative_work_state.json").write_text(
        json.dumps(default), encoding="utf-8"
    )
    selected_path = runtime / "selected_work_state.json"
    selected_path.write_text(json.dumps(selected), encoding="utf-8")
    kwargs["authoritative_work_state_path"] = selected_path
    result = run_reddog_signer_socket_service_config_supply(**kwargs)
    assert result.accepted is False
    assert FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID in result.rejection_reasons
    assert not (runtime / "signer-service.json").exists()
