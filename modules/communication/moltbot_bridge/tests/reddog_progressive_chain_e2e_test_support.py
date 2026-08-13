"""Test-only worktree runner for progressive resident-chain coverage."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Any

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VerifiedOutcomeSignerPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_authority_profile_rehydration import (
    rehydrate_authority_profile_runtime,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    ControlLoopAuthorityPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_control_loop_anchor import (
    InMemorySignerControlLoopAnchorStore,
)
from modules.communication.moltbot_bridge.src.reddog_authority_profile_source_artifact_supply import (
    run_reddog_authority_profile_source_artifact_supply,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    PrincipalAuthorityRecord,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PermissionSnapshot,
)


class FakeProfileWorktreeRunner:
    """Record bounded worktree and draft-PR effects without touching Git."""

    instances: list["FakeProfileWorktreeRunner"] = []

    def __init__(self, *, repo_root: Path, timeout_s: int) -> None:
        self.repo_root = Path(repo_root)
        self.timeout_s = timeout_s
        self.calls: list[tuple[str, str, str | None, str | None]] = []
        self.__class__.instances.append(self)

    def create_worktree(self, *, worktree_path: Path, branch_name: str, base_ref: str):
        self.calls.append(("create_worktree", str(worktree_path), branch_name, base_ref))
        Path(worktree_path).mkdir(parents=True, exist_ok=True)
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}

    def cleanup_worktree(self, *, worktree_path: Path):
        self.calls.append(("cleanup_worktree", str(worktree_path), None, None))
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}

    def push_branch(self, *, worktree_path: Path, branch_name: str):
        self.calls.append(("push_branch", str(worktree_path), branch_name, None))
        return {"ok": True, "branch_name": branch_name}

    def create_draft_pr(self, *, branch_name: str, base_branch: str, title: str, body: str):
        self.calls.append(("create_draft_pr", branch_name, base_branch, title))
        _ = body
        return "https://github.com/FOUNDUPS/Foundups-Agent/pull/4242"


class OneUseOutcomeAuthority:
    """Test-only signer authority proving reserve/commit one-use behavior."""

    def __init__(self) -> None:
        self.reserved: set[str] = set()
        self.committed: set[str] = set()

    def reserve(self, **values: object) -> object | None:
        receipt_id = str(values.get("receipt_id") or "")
        if not receipt_id or receipt_id in self.reserved or receipt_id in self.committed:
            return None
        self.reserved.add(receipt_id)
        return receipt_id

    def reserve_proof_input(self, **values: object) -> str:
        return "test-reserve-proof:" + str(values.get("receipt_id") or "")

    def commit(
        self, reservation: object, signature_digest: str,
        signer_instance_signature: str,
    ) -> None:
        receipt_id = str(reservation)
        if (
            receipt_id not in self.reserved
            or not signature_digest.startswith("sha256:")
            or not signer_instance_signature.startswith("ed25519-sig-v1:")
        ):
            raise ValueError("outcome_test_authority_commit_rejected")
        self.reserved.remove(receipt_id)
        self.committed.add(receipt_id)

    def commit_proof_input(self, reservation: object, signature_digest: str) -> str:
        return f"test-commit-proof:{reservation}:{signature_digest}"

    def rollback(self, reservation: object) -> None:
        self.reserved.discard(str(reservation))


def configure_outcome_signing_backend(
    switching_backend: Any,
    *,
    signer_public_key: str,
    principal_id: str,
    reddog_id: str,
    key_epoch: str,
    consensus_receipt_digest: str,
    now_epoch: int,
) -> OneUseOutcomeAuthority:
    """Attach canonical outcome policy and one-use authority to a test backend."""

    authority = OneUseOutcomeAuthority()
    backend = switching_backend._backends[signer_public_key]
    switching_backend._backends[signer_public_key] = replace(
        backend,
        verified_outcome_signer_policy=VerifiedOutcomeSignerPolicy(
            issuer_principal_id=principal_id,
            reddog_id=reddog_id,
            signer_public_key=signer_public_key,
            key_epoch=key_epoch,
            authority_tier="HIGH",
            consensus_receipt_digest=consensus_receipt_digest,
        ),
        verified_outcome_signing_authority=authority,
        proposal_clock=lambda: now_epoch,
    )
    return authority


def configure_control_receipt_signing_backend(
    switching_backend: Any,
    *,
    signer_public_key: str,
    runtime_profile: dict[str, Any],
) -> None:
    """Bind control signing to the final promoted authority profile."""

    profile = rehydrate_authority_profile_runtime(runtime_profile)
    encoded = json.dumps(
        profile, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    backend = switching_backend._backends[signer_public_key]
    switching_backend._backends[signer_public_key] = replace(
        backend,
        control_loop_anchor_store=InMemorySignerControlLoopAnchorStore(),
        control_loop_authority_policy=ControlLoopAuthorityPolicy(
            issuer_principal_id=str(profile["principal_id"]),
            signer_public_key=signer_public_key,
            key_epoch=str(profile["key_epoch"]),
            consensus_receipt_digest=str(profile["consensus_receipt_digest"]),
            authority_profile_digest="sha256:" + hashlib.sha256(encoded).hexdigest(),
            authority_profile_source_receipt_id=str(
                profile["authority_profile_source_receipt_id"]
            ),
        ),
    )


def supply_runtime_authority_source(
    *, repo_root: Path, runtime_root: Path, runtime_profile: dict[str, Any], now_epoch: int
) -> tuple[dict[str, Any], Path, str]:
    """Materialize the canonical source artifact underlying a runtime profile."""

    seed_fields = (
        "principal_id", "principal_provider", "reddog_id", "reddog_public_key",
        "repo_full_name", "foundup_id", "allowed_paths", "denied_paths",
        "requested_operation", "permission_snapshot_digest", "identity_nonce",
        "work_authority_nonce", "issued_at", "identity_expires_at",
        "work_authority_expires_at", "valve_state_required", "key_epoch",
        "consensus_receipt_digest", "sovereign_authorization_digest",
        "holoindex_evidence", "base_ref",
    )
    runtime_profile["consensus_receipt_digest"] = "sha256:" + "c" * 64
    runtime_profile["sovereign_authorization_digest"] = "sha256:" + "d" * 64
    runtime_profile["denied_paths"] = [
        "modules/foundups/paccess_001/secrets/**",
    ]
    runtime_profile["holoindex_evidence"] = {
        "holoindex_query": "RedDog progressive policy chain",
        "holoindex_status": "bundle_json_ok",
        "holoindex_freshness_receipt_digest": "sha256:" + "e" * 64,
        "index_gap_detected": False,
        "retrieval_quality": "HIGH",
        "applicable_wsps": ["WSP_00", "WSP_15", "WSP_97"],
        "evidence_refs": [
            "modules/communication/moltbot_bridge/src/"
            "reddog_main_resident_queue_serial_loop_bootstrap.py",
        ],
    }
    seed = {name: runtime_profile[name] for name in seed_fields if name in runtime_profile}
    seed["required_tests"] = ["pytest progressive-policy-chain"]
    seed["required_policy_gates"] = [
        "signed_work_order_authority", "execution_valve",
    ]
    source_path = runtime_root / "authority_profile_source.json"
    supplied = run_reddog_authority_profile_source_artifact_supply(
        repo_root=repo_root,
        authority_seed=seed,
        principal_authority_record=PrincipalAuthorityRecord(
            principal_id=str(runtime_profile["principal_id"]),
            principal_provider=str(runtime_profile["principal_provider"]),
            principal_public_key=str(runtime_profile["principal_public_key"]),
            repo_scope=(str(runtime_profile["repo_full_name"]),),
            foundup_scope=(str(runtime_profile["foundup_id"]),),
            verified_subject_digest="sha256:" + "7" * 64,
            reward_account="reward:012",
            owner_dae="dae:012",
        ),
        permission_snapshot=PermissionSnapshot(
            evidence_digest=str(runtime_profile["permission_snapshot_digest"]),
            expires_at=int(runtime_profile["identity_expires_at"]),
            can_write=True,
            can_admin=False,
            repo_full_name=str(runtime_profile["repo_full_name"]),
        ),
        output_path=source_path,
        now_epoch=now_epoch,
    )
    if not supplied.accepted or not supplied.authority_profile_source_receipt_id:
        raise AssertionError(supplied.rejection_reasons)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    runtime_profile.update(source)
    return runtime_profile, source_path, supplied.authority_profile_source_receipt_id


def assert_progressive_control_receipt(
    receipt: dict[str, Any], last_result: dict[str, Any]
) -> None:
    """Verify only effects directly observed by the signed parent receipt."""

    assert receipt["receipt_id"] == last_result["receipt_id"]
    assert receipt["receipt_ids"][0].startswith("signed_worker_task_execution_")
    assert receipt["child_execution_receipt_ids"] == receipt["receipt_ids"]
    assert receipt["child_execution_evidence_count"] == sum(
        receipt[name]
        for name in (
            "worker_completion_count",
            "worker_requeue_count",
            "worker_failure_count",
        )
    )
    assert receipt["control_lock_acquired"] is True
    assert "authority_runtime" in receipt["dispatched_stages"]
    assert "bounded_worker_pilot" not in receipt["dispatched_stages"]
    assert receipt["authority_issued"] is True
    assert receipt["worker_claim_performed"] is True
    assert receipt["worker_execution_performed"] is True
    assert receipt["worktree_creation_observed"] is True
    for field in (
        "bounded_file_edit_observed",
        "slice_verification_observed",
        "draft_pr_publish_observed",
        "pattern_memory_admission_observed",
        "shell_command_execution_observed",
        "worker_process_spawn_observed",
    ):
        assert receipt[field] is False
    assert receipt["shell_command_count"] == 0
    assert receipt["worker_process_spawn_count"] == 0
    assert receipt["authentication_status"] == "AUTHENTICATED"
    assert receipt["signature"].startswith("ed25519-sig-v1:")
    assert receipt["signer_audit_attestation_signature"].startswith(
        "ed25519-sig-v1:"
    )


def assert_progressive_chain_state(stored: dict[str, Any]) -> None:
    """Verify downstream stages from the authoritative queue-chain artifact."""

    for stage_name in (
        "worker_dispatch_runtime", "worktree_create", "bounded_worker_pilot",
        "slice_verifier", "verified_draft_pr_publish", "verified_outcome_ratchet",
        "model_feedback_admission", "held_out_regression_gate",
        "pattern_memory_admission",
    ):
        assert stage_name in stored["stage_results"]
    generation = stored["stage_results"]["bounded_worker_pilot"][
        "artifact_generation_result"
    ]
    assert generation["accepted"] is True
    assert generation["receipt"]["model_receipt_id"] == "fusion-artifact-receipt-1"
    assert stored["receipts"][-1]["next_action"] == "STOP_QUEUE_CHAIN_COMPLETE"


def assert_progressive_effects(
    *,
    worktree_instances: list[Any],
    draft_runner_instances: list[Any],
    repo_root: Path,
    artifact_path: str,
    outcome_store: Path,
    pattern_memory_records: list[Any],
) -> None:
    """Verify isolated edit, draft publication, and learning-sink effects."""

    worktree_calls = [
        call for instance in worktree_instances for call in instance.calls
        if call[0] == "create_worktree"
    ]
    assert len(worktree_calls) == 1
    worktree = Path(worktree_calls[0][1])
    assert (worktree / artifact_path).read_text(encoding="utf-8").startswith(
        "# Generated By Fusion"
    )
    assert not (repo_root / artifact_path).exists()
    draft_calls = [
        call[0] for instance in draft_runner_instances for call in instance.calls
        if call[0] in {"push_branch", "create_draft_pr"}
    ]
    assert draft_calls == ["push_branch", "create_draft_pr"]
    assert outcome_store.exists()
    assert len(pattern_memory_records) == 1
    assert not (repo_root / "runtime" / "pattern_memory.db").exists()
