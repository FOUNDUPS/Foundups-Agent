"""Tests for REDDOG_MAIN_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import patch

from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_serial_loop_bootstrap import (
    REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED,
    REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY,
    run_reddog_main_resident_queue_serial_loop_bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_runtime_dependency_bundle import (
    REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    Ed25519SignerBackend,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    RuntimeRejectCode,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_WORKTREE_CREATE,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_main_resident_queue_serial_loop_bootstrap.py"
)
NOW = "2026-07-14T00:00:00+00:00"
EXPIRES = "2026-07-14T01:00:00+00:00"
WORK_ORDER_ID = "resident-queue-work-order-001"
FOUNDUP_ID = "paccess_001"


def _snapshot() -> dict[str, object]:
    return {
        "schema_version": "reddog_authoritative_work_state.v1",
        "freshness_receipts": [{"receipt_id": "fresh-1", "fresh": True}],
        "worker_claims": [
            {
                "claim_id": "claim-1",
                "slice_id": "REDDOG_TEST_SLICE_PHASE1",
                "worker_id": "reddog-0102",
                "status": "ACTIVE",
                "expires_at": EXPIRES,
                "freshness_receipt_id": "fresh-1",
            }
        ],
        "wre_queue_items": [
            {
                "queue_item_id": "queue-1",
                "slice_id": "REDDOG_TEST_SLICE_PHASE1",
                "claim_id": "claim-1",
                "worker_id": "reddog-0102",
                "status": "QUEUED",
                "evidence_refs": ["claim:claim-1", "freshness:fresh-1"],
                "no_execution_performed": True,
            }
        ],
    }


def _profile(**overrides: object) -> dict[str, object]:
    profile = {
        "work_order_id": WORK_ORDER_ID,
        "principal_id": "github:mjtrout",
        "principal_provider": "github",
        "principal_public_key": "pub:principal",
        "reddog_id": "reddog:abc123",
        "reddog_public_key": "pub:reddog",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "foundup_id": FOUNDUP_ID,
        "allowed_paths": [f"modules/foundups/{FOUNDUP_ID}/**"],
        "denied_paths": [f"modules/foundups/{FOUNDUP_ID}/secrets/**"],
        "requested_operation": "feature_slice",
        "permission_snapshot_digest": "sha256:snap-1",
        "identity_nonce": "identity-nonce-0001",
        "work_authority_nonce": "workauth-nonce-0001",
        "issued_at": 1000,
        "identity_expires_at": 4600,
        "work_authority_expires_at": 1300,
        "valve_state_required": VALVE_OPEN_WORKTREE_CREATE,
        "key_epoch": "epoch-1",
        "consensus_receipt_digest": "sha256:consensus",
        "sovereign_authorization_digest": "sha256:012-token",
    }
    profile.update(overrides)
    return profile


def _work_order(**overrides: object) -> dict[str, object]:
    payload = {
        "work_order_id": WORK_ORDER_ID,
        "created_at": "2026-07-13T23:59:30+00:00",
        "red_dog_instance_id": "reddog-main-bootstrap",
        "authenticated_principal": "github:mjtrout",
        "principal_provider": "github",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "repo_permission_snapshot": {
            "permission_level": "write",
            "captured_at": "2026-07-13T23:59:30+00:00",
            "source": "test",
            "digest": "sha256:snap-1",
        },
        "requested_operation": "feature_slice",
        "authority_tier": "source",
        "allowed_paths": [f"modules/foundups/{FOUNDUP_ID}/**"],
        "denied_paths": [f"modules/foundups/{FOUNDUP_ID}/secrets/**"],
        "branch_name": "feat/paccess-001-resident-queue",
        "base_ref": "main",
        "task_summary": "Resident queue startup reaches the execution valve only.",
        "wsp_applicability": ["WSP_34", "WSP_50", "WSP_97"],
        "holoindex_evidence_refs": [
            "modules/communication/moltbot_bridge/src/reddog_main_resident_queue_serial_loop_bootstrap.py"
        ],
        "skillz_candidates": [],
        "required_tests": ["pytest modules/communication/moltbot_bridge/tests"],
        "required_policy_gates": ["openclaw_policy_gate", "signed_work_order_authority"],
        "required_reviewers": [],
        "sentinel_checks": [],
        "rollback_plan": "No live worktree created by this bootstrap slice.",
        "expiry": EXPIRES,
        "nonce": "resident-queue-work-order-nonce-001",
        "evidence_digest": "sha256:" + ("a" * 64),
        "advisory_only_source_packet": {
            "work_focus_digest": "sha256:" + ("b" * 64),
            "wsp_prompt_digest": "sha256:" + ("c" * 64),
            "copy_md_run_trace_digest": "sha256:" + ("d" * 64),
        },
        "holoindex_evidence": {
            "holoindex_query": "RedDog resident queue execution valve bootstrap",
            "holoindex_status": "bundle_json_ok",
            "code_hits": [
                "modules/communication/moltbot_bridge/src/reddog_resident_queue_execution_valve_handler.py"
            ],
            "wsp_hits": ["WSP_framework/src/WSP_34_Git_Operations_Protocol.md"],
            "skillz_hits": [],
            "direct_read_fallback_used": True,
            "index_gap_detected": False,
            "applicable_wsps": ["WSP_34", "WSP_97"],
            "evidence_refs": [
                "modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py"
            ],
            "retrieval_quality": "HIGH",
            "skillz_gap_detected": False,
        },
    }
    payload.update(overrides)
    return payload


def _work_orders(**overrides: object) -> dict[str, object]:
    order = _work_order(**overrides)
    return {"work_orders": {WORK_ORDER_ID: order}}


def _valve_environment(**overrides: object) -> dict[str, object]:
    env = {
        "valve_worktree_create_enabled": True,
        "sovereign_worktree_token": "012-sovereign-worktree-token",
        "permission_expires_at": EXPIRES,
    }
    env.update(overrides)
    return env


def _snapshots() -> dict[str, object]:
    return {
        "snapshots": {
            "sha256:snap-1": {
                "evidence_digest": "sha256:snap-1",
                "expires_at": 1600,
                "can_write": True,
                "repo_full_name": "FOUNDUPS/Foundups-Agent",
            }
        }
    }


def _principals(principal_public_key: str = "pub:principal") -> dict[str, object]:
    return {
        "principals": {
            "github:mjtrout": {
                "principal_id": "github:mjtrout",
                "principal_provider": "github",
                "principal_public_key": principal_public_key,
                "repo_scope": ["FOUNDUPS/Foundups-Agent"],
                "foundup_scope": ["paccess_001"],
                "verified_subject_digest": "sha256:verified-subject",
                "reward_account": "reward:012",
                "owner_dae": "dae:012",
            }
        }
    }


def _write_runtime_json(tmp_path: Path, name: str, payload: object) -> Path:
    path = tmp_path / "runtime" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _accepted_socket_signer(
    socket_path: Path,
    request_bytes: bytes,
    timeout_s: float,
    max_response_bytes: int,
) -> bytes:
    assert socket_path.is_absolute()
    assert timeout_s > 0
    assert max_response_bytes >= 1024
    decoded = json.loads(request_bytes.decode("utf-8").strip())
    request = decoded["request"]
    public_key = str(request["signer_public_key"])
    response = {
        "accepted": True,
        "signature": "sig:" + str(request["nonce"]),
        "signer_public_key": public_key,
        "key_fingerprint": public_key_fingerprint(public_key),
        "key_epoch": str(request["key_epoch"]),
        "audit_mac": "audit:" + str(request["payload_digest"]),
        "boundary_attested": True,
        "requester_identity_attested": True,
        "signer_loads_no_untrusted_code": True,
        "no_secret_material_returned": True,
    }
    return json.dumps(response, sort_keys=True).encode("utf-8")


class _AuditMacBuilder:
    def build(self, request: SigningRequest, signature: str, peer: SignerPeerAttestation) -> str:
        return "audit:" + request.payload_digest


def _ed25519_signing_material():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    principal_key = Ed25519PrivateKey.generate()
    reddog_key = Ed25519PrivateKey.generate()
    principal_public = encode_ed25519_public_key(
        principal_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )
    reddog_public = encode_ed25519_public_key(
        reddog_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )
    peer = SignerPeerAttestation(
        peer_principal_id="github:mjtrout",
        transport="test_connector",
        credential_source="test_peer_attestation",
        boundary_attested=True,
    )
    backends = {
        principal_public: Ed25519SignerBackend(
            private_key=principal_key,
            public_key=principal_public,
            key_epoch="epoch-1",
            audit_mac_builder=_AuditMacBuilder(),
        ),
        reddog_public: Ed25519SignerBackend(
            private_key=reddog_key,
            public_key=reddog_public,
            key_epoch="epoch-1",
            audit_mac_builder=_AuditMacBuilder(),
        ),
    }

    def connector(socket_path: Path, request_bytes: bytes, timeout_s: float, max_response_bytes: int) -> bytes:
        assert socket_path.is_absolute()
        assert timeout_s > 0
        assert max_response_bytes >= 1024
        decoded = json.loads(request_bytes.decode("utf-8").strip())
        request = SigningRequest(**decoded["request"])
        response = backends[request.signer_public_key].sign(request, peer)
        return json.dumps(response.to_dict(), sort_keys=True).encode("utf-8")

    return principal_public, reddog_public, connector


def _repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    return path


def test_bootstrap_serial_loop_applies_one_stage_with_existing_dependencies(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(tmp_path, "profile.json", _profile())
    chain = tmp_path / "runtime" / "chain_results.json"

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        now_iso=NOW,
        requested_queue_item_id="queue-1",
        max_steps=1,
    )

    assert result.accepted is True
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED
    assert result.queue_item_id == "queue-1"
    assert result.selected_slice == "REDDOG_TEST_SLICE_PHASE1"
    assert result.steps_run == 1
    assert result.dispatched_stages == ("authority_request",)
    assert result.next_action == "RUN_QUEUE_AUTHORITY_RUNTIME_INVOKE"
    assert result.store_revision is not None
    assert result.no_repo_mutation_performed is True
    assert result.no_holoindex_reindex_performed is True
    stored = json.loads(chain.read_text(encoding="utf-8"))
    assert stored["stage_results"]["authority_request"]["status"] == "QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT"


def test_bootstrap_serial_loop_fails_closed_when_later_dependency_missing(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(tmp_path, "profile.json", _profile())
    chain = tmp_path / "runtime" / "chain_results.json"

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        now_iso=NOW,
        requested_queue_item_id="queue-1",
        max_steps=2,
    )

    assert result.accepted is False
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY
    assert result.steps_run == 1
    assert result.dispatched_stages == ("authority_request",)
    assert "FAIL_DISPATCH_REJECTED" in result.rejection_reasons
    assert "FAIL_HANDLER_MISSING" in result.rejection_reasons
    assert "stage:authority_runtime" in result.rejection_reasons


def test_bootstrap_serial_loop_invokes_fail_closed_authority_runtime_bundle(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(tmp_path, "profile.json", _profile())
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=2,
    )

    assert result.accepted is False
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY
    assert result.runtime_dependency_bundle_status == REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY
    assert result.runtime_dependency_bundle_requested is True
    assert result.steps_run == 1
    assert result.dispatched_stages == ("authority_request",)
    assert "FAIL_DISPATCH_REJECTED" in result.rejection_reasons
    assert "FAIL_RECORD_REJECTED" in result.rejection_reasons
    assert "FAIL_STAGE_REJECTED:authority_runtime" in result.rejection_reasons
    assert "REJECT_DELEGATED_AUTHORITY_RUNTIME_REJECTED" in result.rejection_reasons
    assert RuntimeRejectCode.SIGNER_NOT_CONFIGURED in result.rejection_reasons
    stored = json.loads(chain.read_text(encoding="utf-8"))
    assert "authority_runtime" not in stored["stage_results"]
    assert stored["stage_results"]["authority_request"]["status"] == "QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT"


def test_bootstrap_serial_loop_uses_socket_signer_for_authority_runtime(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(tmp_path, "profile.json", _profile())
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=_accepted_socket_signer,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=2,
    )

    assert result.accepted is True
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED
    assert result.runtime_dependency_bundle_status == REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY
    assert result.runtime_dependency_bundle_requested is True
    assert result.steps_run == 2
    assert result.dispatched_stages == ("authority_request", "authority_runtime")
    assert result.next_action == "RUN_QUEUE_AUTHORITY_VERIFICATION_INVOKE"
    assert result.no_shell_command_executed is True
    assert result.no_openclaw_enqueue_performed is True

    stored = json.loads(chain.read_text(encoding="utf-8"))
    assert stored["stage_results"]["authority_runtime"]["decision"] == "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT"
    authority = json.loads(authority_state.read_text(encoding="utf-8"))
    issued = authority["issued_authorities"]
    assert len(issued) == 1
    assert next(iter(issued.values()))["status"] == "DELEGATED_AUTHORITY_ISSUED"


def test_bootstrap_serial_loop_verifies_ed25519_authority_when_configured(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _profile(principal_public_key=principal_public, reddog_public_key=reddog_public),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=3,
    )

    assert result.accepted is True
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED
    assert result.runtime_dependency_bundle_status == REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY
    assert result.steps_run == 3
    assert result.dispatched_stages == (
        "authority_request",
        "authority_runtime",
        "authority_verification",
    )
    assert result.next_action == "RUN_QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE"
    assert result.no_signature_verification_performed is False
    assert result.no_worktree_created is True
    assert result.no_shell_command_executed is True
    assert result.no_openclaw_enqueue_performed is True

    stored = json.loads(chain.read_text(encoding="utf-8"))
    verification = stored["stage_results"]["authority_verification"]
    assert verification["decision"] == "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT"
    assert verification["verification_result"]["accepted"] is True
    authority = json.loads(authority_state.read_text(encoding="utf-8"))
    assert authority["verified_work_authority_nonces"] == ["workauth-nonce-0001"]


def test_bootstrap_serial_loop_reaches_execution_valve_with_explicit_work_order_inputs(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _profile(principal_public_key=principal_public, reddog_public_key=reddog_public),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_orders = _write_runtime_json(tmp_path, "work_orders.json", _work_orders())
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=6,
    )

    assert result.accepted is True
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED
    assert result.steps_run == 6
    assert result.dispatched_stages == (
        "authority_request",
        "authority_runtime",
        "authority_verification",
        "work_order_invocation",
        "executor_plan",
        "execution_valve",
    )
    assert result.next_action == "RUN_QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE"
    assert result.no_signature_verification_performed is False
    assert result.no_worker_spawn_performed is True
    assert result.no_worktree_created is True
    assert result.no_shell_command_executed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_repo_mutation_performed is True
    assert result.no_holoindex_reindex_performed is True
    assert result.no_pr_created is True

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage_results = stored["stage_results"]
    assert stage_results["work_order_invocation"]["decision"] == "QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT"
    assert stage_results["executor_plan"]["decision"] == "QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT"
    valve = stage_results["execution_valve"]
    assert valve["decision"] == "QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT"
    assert valve["valve_decision"]["valve_state"] == VALVE_OPEN_WORKTREE_CREATE
    assert "012-sovereign-worktree-token" not in json.dumps(stored, sort_keys=True)


def test_bootstrap_serial_loop_fails_closed_before_work_order_without_resolver(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _profile(principal_public_key=principal_public, reddog_public_key=reddog_public),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        valve_environment_path=valve_env,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=4,
    )

    assert result.accepted is False
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY
    assert result.steps_run == 3
    assert result.dispatched_stages == (
        "authority_request",
        "authority_runtime",
        "authority_verification",
    )
    assert "FAIL_HANDLER_MISSING" in result.rejection_reasons
    assert "stage:work_order_invocation" in result.rejection_reasons
    assert result.no_worktree_created is True
    assert result.no_shell_command_executed is True


def test_bootstrap_rejects_malformed_work_orders(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(tmp_path, "profile.json", _profile())
    work_orders = _write_runtime_json(tmp_path, "work_orders.json", {"work_orders": {"bad": {}}})

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=tmp_path / "runtime" / "chain_results.json",
        authority_profile_path=profile,
        work_orders_path=work_orders,
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "malformed_work_orders" in result.rejection_reasons


def test_bootstrap_rejects_valve_environment_inside_repo(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(tmp_path, "profile.json", _profile())
    valve_env = repo / "valve_env.json"
    valve_env.write_text(json.dumps(_valve_environment(), sort_keys=True), encoding="utf-8")

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=tmp_path / "runtime" / "chain_results.json",
        authority_profile_path=profile,
        valve_environment_path=valve_env,
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "valve_environment_path_inside_repo" in result.rejection_reasons


def test_bootstrap_rejects_missing_authority_profile(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=tmp_path / "runtime" / "chain_results.json",
        authority_profile_path=None,
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "missing_authority_profile_path" in result.rejection_reasons


def test_bootstrap_rejects_inputs_inside_repo(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    inside_state = repo / "work_state.json"
    inside_state.write_text(json.dumps(_snapshot()), encoding="utf-8")

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=inside_state,
        chain_results_path=tmp_path / "runtime" / "chain_results.json",
        authority_profile_path=tmp_path / "runtime" / "profile.json",
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "work_state_path_inside_repo" in result.rejection_reasons


def test_main_serial_loop_preflight_is_disabled_by_default() -> None:
    import main

    with patch.dict("os.environ", {}, clear=True):
        assert main.run_reddog_resident_queue_serial_loop_preflight(REPO_ROOT) is True


def test_main_serial_loop_preflight_passes_when_bootstrap_applies(tmp_path: Path) -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_resident_queue_serial_loop_bootstrap.run_reddog_main_resident_queue_serial_loop_bootstrap",
        return_value=type(
            "Result",
            (),
            {
                "accepted": True,
                "status": REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED,
                "queue_item_id": "queue-1",
                "selected_slice": "REDDOG_TEST_SLICE_PHASE1",
                "steps_run": 1,
                "dispatched_stages": ("authority_request",),
                "next_action": "RUN_QUEUE_AUTHORITY_RUNTIME_INVOKE",
                "chain_results_path": str(tmp_path / "chain.json"),
                "store_revision": "sha256:revision",
                "rejection_reasons": (),
            },
        )(),
    ) as mocked:
        with patch.dict(
            "os.environ",
            {
                "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP": "1",
                "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_MAX_STEPS": "1",
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(tmp_path / "state.json"),
                "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH": str(tmp_path / "chain.json"),
                "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH": str(tmp_path / "profile.json"),
                "REDDOG_WORK_ORDERS_PATH": str(tmp_path / "work_orders.json"),
                "REDDOG_EXECUTION_VALVE_ENV_PATH": str(tmp_path / "valve_env.json"),
                "REDDOG_AUTHORITY_RUNTIME_STATE_PATH": str(tmp_path / "authority_state.json"),
                "REDDOG_PERMISSION_SNAPSHOTS_PATH": str(tmp_path / "snapshots.json"),
                "REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH": str(tmp_path / "principals.json"),
                "REDDOG_SIGNER_SOCKET_PATH": str(tmp_path / "signer.sock"),
                "REDDOG_SIGNER_SOCKET_TIMEOUT_S": "2.5",
                "REDDOG_SIGNER_SOCKET_MAX_RESPONSE_BYTES": "8192",
                "REDDOG_SIGNATURE_VERIFIER_BACKEND": REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
                "REDDOG_RESIDENT_QUEUE_NOW_EPOCH": "1000",
                "REDDOG_WRE_QUEUE_ITEM_ID": "queue-1",
            },
            clear=True,
        ):
            assert main.run_reddog_resident_queue_serial_loop_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["work_state_path"] == str(tmp_path / "state.json")
    assert mocked.call_args.kwargs["chain_results_path"] == str(tmp_path / "chain.json")
    assert mocked.call_args.kwargs["authority_profile_path"] == str(tmp_path / "profile.json")
    assert mocked.call_args.kwargs["work_orders_path"] == str(tmp_path / "work_orders.json")
    assert mocked.call_args.kwargs["valve_environment_path"] == str(tmp_path / "valve_env.json")
    assert mocked.call_args.kwargs["authority_state_path"] == str(tmp_path / "authority_state.json")
    assert mocked.call_args.kwargs["permission_snapshots_path"] == str(tmp_path / "snapshots.json")
    assert mocked.call_args.kwargs["principal_authority_records_path"] == str(tmp_path / "principals.json")
    assert mocked.call_args.kwargs["signer_socket_path"] == str(tmp_path / "signer.sock")
    assert mocked.call_args.kwargs["signer_socket_timeout_s"] == 2.5
    assert mocked.call_args.kwargs["signer_socket_max_response_bytes"] == 8192
    assert mocked.call_args.kwargs["signature_verifier_backend"] == REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519
    assert mocked.call_args.kwargs["requested_queue_item_id"] == "queue-1"
    assert mocked.call_args.kwargs["now_epoch"] == 1000
    assert mocked.call_args.kwargs["max_steps"] == 1


def test_main_serial_loop_preflight_blocks_when_enforced() -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_resident_queue_serial_loop_bootstrap.run_reddog_main_resident_queue_serial_loop_bootstrap",
        return_value=type(
            "Result",
            (),
            {
                "accepted": False,
                "status": REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY,
                "queue_item_id": None,
                "selected_slice": None,
                "steps_run": 0,
                "dispatched_stages": (),
                "next_action": None,
                "chain_results_path": None,
                "store_revision": None,
                "rejection_reasons": ("missing_authority_profile_path",),
            },
        )(),
    ):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP": "1",
                "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_ENFORCED": "1",
            },
            clear=True,
        ):
            assert main.run_reddog_resident_queue_serial_loop_preflight(REPO_ROOT) is False


def test_module_has_no_shell_network_holoindex_or_later_stage_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "holo_index",
        "git",
        "hmac",
        "secrets",
    }
    banned_import_fragments = {
        "reddog_signer_delegated_authority_runtime",
        "reddog_wre_queue_authority_runtime_invoke",
        "reddog_wre_queue_authority_verification_invoke",
        "reddog_wre_queue_authorized",
        "reddog_wre_queue_verified_authority_work_order_invoke",
        "reddog_wre_worktree_runner",
        "worktree_pr_runner",
        "pattern_memory",
        "openclaw_supervisor",
        "hermes_job_executor",
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}
    banned_attrs = {
        "system",
        "popen",
        "spawn",
        "run",
        "Popen",
        "check_call",
        "check_output",
        "unlink",
        "remove",
        "rmdir",
        "rename",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
                assert all(fragment not in alias.name for fragment in banned_import_fragments)
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
            assert all(fragment not in node.module for fragment in banned_import_fragments)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs
