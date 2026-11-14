"""Production-supplier seven-artifact fixture for resident canary tests."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_digest import (
    canonical_model_runtime_binding_digest,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_resolver_artifact_supply import (
    run_reddog_authority_runtime_resolver_artifact_supply,
)
from modules.communication.moltbot_bridge.src.reddog_execution_valve_environment_supply import (
    run_reddog_execution_valve_environment_supply,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply import (
    run_reddog_signer_socket_service_config_supply,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_run_packet_supply import (
    run_reddog_signer_socket_service_run_packet_supply,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_WORKTREE_CREATE,
)
from modules.communication.moltbot_bridge.src.reddog_progressive_execution_stage_policy import (
    STAGE_BOUNDED_EXECUTION,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_selection_and_runtime_binding_receipts,
)
from modules.communication.moltbot_bridge.tests.test_reddog_resident_queue_serial_loop import (
    _snapshot,
)


PERMISSION_DIGEST = "sha256:" + "a" * 64
CONSENSUS_DIGEST = "sha256:" + "b" * 64
SOVEREIGN_DIGEST = "sha256:" + "c" * 64
PRINCIPAL_PUBLIC_KEY = encode_ed25519_public_key(bytes(range(32)))
REDDOG_PUBLIC_KEY = encode_ed25519_public_key(bytes(range(32, 64)))


def write_live_canary_artifacts(
    *, repo: Path, runtime: Path, queue_item_id: str, now_iso: str,
) -> None:
    """Write canonical fixture artifacts without signer/model/live execution."""

    now_epoch = int(datetime.fromisoformat(now_iso).timestamp())
    selection, runtime_binding = model_selection_and_runtime_binding_receipts(
        runtime_surface="reddog_artifact_generation",
    )
    work, profile = _governed_lineage(queue_item_id, now_epoch, selection, runtime_binding)
    _write(runtime / "authoritative_work_state.json", work)
    _write(runtime / "authority_profile.json", profile)
    permission, principal = _resolver_inputs(now_epoch)
    resolver = run_reddog_authority_runtime_resolver_artifact_supply(
        repo_root=repo, principal_authority_record=principal, permission_snapshot=permission,
        principal_records_output_path=runtime / "principal_authority_records.json",
        permission_snapshots_output_path=runtime / "permission_snapshots.json",
    )
    assert resolver.accepted
    _write_valve(repo, runtime, work, profile, queue_item_id, now_epoch)
    _write_signer(repo, runtime, profile)


def _governed_lineage(
    queue_id: str, now: int, selection: dict, runtime_binding: dict,
) -> tuple[dict, dict]:
    work = _snapshot()
    queue = work["wre_queue_items"][0]
    claim = work["worker_claims"][0]
    queue["queue_item_id"] = queue_id
    determination_id = "sha256:canary-determination"
    selection_digest = _digest(selection)
    runtime_digest = canonical_model_runtime_binding_digest(runtime_binding)
    memex_id, memex_digest = "sha256:canary-memex", _digest({"receipt_id": "sha256:canary-memex"})
    queue.update({
        "source_determination_receipt_id": determination_id,
        "model_selection_receipt_id": selection["receipt_id"],
        "model_selection_digest": selection_digest,
        "model_runtime_binding_receipt_id": runtime_binding["receipt_id"],
        "model_runtime_binding_digest": runtime_digest,
        "memex_supply_receipt_id": memex_id, "memex_supply_digest": memex_digest,
    })
    claim.update({
        "lane_id": "reddog_operational",
        "reconciliation_report_id": determination_id,
        "source_determination_receipt_id": determination_id,
        "model_selection_receipt_id": selection["receipt_id"],
        "model_runtime_binding_receipt_id": runtime_binding["receipt_id"],
        "memex_supply_receipt_id": memex_id,
    })
    queue["evidence_refs"] = list(dict.fromkeys([
        *queue.get("evidence_refs", ()),
        f"architect_determination:{determination_id}",
        f"model_selection:{selection['receipt_id']}",
        f"model_runtime_binding:{runtime_binding['receipt_id']}",
        f"memex_supply:{memex_id}",
    ]))
    allocation = queue["wsp15_allocation_receipt"]
    work_order_id = "wre-queue-" + hashlib.sha256(queue_id.encode("utf-8")).hexdigest()[:16]
    binding = {
        "work_order_id": work_order_id, "queue_item_id": queue_id,
        "claim_id": claim["claim_id"], "determination_id": determination_id,
        "wsp15_allocation_receipt": allocation,
        "model_selection_receipt_id": selection["receipt_id"],
        "model_selection_digest": selection_digest,
        "model_runtime_binding_receipt_id": runtime_binding["receipt_id"],
        "model_runtime_binding_digest": runtime_digest,
        "memex_supply_receipt_id": memex_id, "memex_supply_digest": memex_digest,
    }
    profile = _profile(now, work_order_id, selection, runtime_binding, binding)
    raw = json.dumps(work, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    work["revision"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return work, profile


def _profile(
    now: int, work_order_id: str, selection: dict, runtime_binding: dict, binding: dict,
) -> dict:
    return {
        "principal_id": "github:mjtrout", "principal_provider": "github",
        "principal_public_key": PRINCIPAL_PUBLIC_KEY,
        "reddog_id": "reddog:canary", "reddog_public_key": REDDOG_PUBLIC_KEY,
        "repo_full_name": "FOUNDUPS/Foundups-Agent", "foundup_id": "paccess_001",
        "allowed_paths": ["modules/foundups/paccess_001/**"], "denied_paths": ["modules/foundups/paccess_001/secrets/**"],
        "requested_operation": "feature_slice", "permission_snapshot_digest": PERMISSION_DIGEST,
        "identity_nonce": "identity-canary", "work_authority_nonce": "work-canary",
        "issued_at": now - 30, "identity_expires_at": now + 315360000,
        "work_authority_expires_at": now + 315360000,
        "valve_state_required": VALVE_OPEN_WORKTREE_CREATE, "key_epoch": "epoch-1",
        "required_tests": ["pytest canary"], "required_policy_gates": ["signed_authority"],
        "consensus_receipt_digest": CONSENSUS_DIGEST,
        "sovereign_authorization_digest": SOVEREIGN_DIGEST,
        "authority_profile_source_receipt_id": "sha256:" + "d" * 64,
        "work_order_id": work_order_id,
        "wsp15_allocation_receipt": binding["wsp15_allocation_receipt"],
        "model_catalog_snapshot_id": selection["catalog_snapshot_id"],
        "model_selection_receipt_id": selection["receipt_id"],
        "model_selection_digest": binding["model_selection_digest"],
        "model_selection_receipt": selection,
        "model_runtime_binding_receipt_id": runtime_binding["receipt_id"],
        "model_runtime_binding_digest": binding["model_runtime_binding_digest"],
        "model_runtime_binding_receipt": runtime_binding,
        "memex_supply_receipt_id": binding["memex_supply_receipt_id"],
        "memex_supply_digest": binding["memex_supply_digest"],
        "operational_context_binding": binding,
    }


def _resolver_inputs(now: int) -> tuple[dict, dict]:
    return ({
        "evidence_digest": PERMISSION_DIGEST, "expires_at": now + 315360000,
        "can_write": True, "can_admin": False, "repo_full_name": "FOUNDUPS/Foundups-Agent",
    }, {
        "principal_id": "github:mjtrout", "principal_provider": "github",
        "principal_public_key": PRINCIPAL_PUBLIC_KEY,
        "repo_scope": ["FOUNDUPS/Foundups-Agent"], "foundup_scope": ["paccess_001"],
        "verified_subject_digest": "sha256:verified",
    })


def _write_valve(repo: Path, runtime: Path, work: dict, profile: dict, queue_id: str, now: int) -> None:
    result = run_reddog_execution_valve_environment_supply(
        repo_root=repo, work_state=work, authority_profile=profile,
        permission_snapshots=_read(runtime / "permission_snapshots.json"),
        principal_authority_records=_read(runtime / "principal_authority_records.json"),
        output_path=runtime / "execution_valve_env.json",
        requested_valve_state=VALVE_OPEN_WORKTREE_CREATE, queue_item_id=queue_id, now_epoch=now,
        progressive_execution_stage_ceiling=STAGE_BOUNDED_EXECUTION,
    )
    assert result.accepted, result.rejection_reasons


def _write_signer(repo: Path, runtime: Path, profile: dict) -> None:
    config = run_reddog_signer_socket_service_config_supply(
        repo_root=repo,
        runtime_root=runtime,
        signer_runtime_root=runtime.parent / f"{runtime.name}-signer-state",
        authority_profile=profile,
        authoritative_work_state_path=runtime / "authoritative_work_state.json",
        output_path=runtime / "signer_service_config.json",
        socket_path=runtime / "reddog_signer.sock",
        principal_signing_key_ref="op://vault/principal/private",
        principal_audit_mac_key_ref="op://vault/principal/audit",
        reddog_signing_key_ref="op://vault/reddog/private",
        reddog_audit_mac_key_ref="op://vault/reddog/audit",
        peer_uid_to_principal={1001: "github:mjtrout"}, allowed_gids=(1002,),
    )
    assert config.accepted
    packet = run_reddog_signer_socket_service_run_packet_supply(
        repo_root=repo, config_path=runtime / "signer_service_config.json",
        output_path=runtime / "signer_service_run_packet.json",
        owner_authority_config_path=(
            runtime.parent / "signer-owner" / "owner.json"
        ),
        python_executable="python",
        session_id="canary-test",
    )
    assert packet.accepted


def _digest(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
