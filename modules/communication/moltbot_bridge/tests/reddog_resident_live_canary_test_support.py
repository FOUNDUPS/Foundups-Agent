"""Canonical local integration support for resident live-canary tests."""

from __future__ import annotations

import json
import hashlib
import subprocess
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_receipt_store import (
    ControlLoopReceiptSigningContext,
    build_resident_control_loop_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_head_store import (
    build_control_receipt_head,
    commit_control_receipt_head,
    load_control_receipt_head,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    ControlLoopAuthorityPolicy,
    Ed25519SignerBackend,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_control_loop_anchor import (
    AtomicSignerControlLoopAnchorStore,
    ControlLoopAnchorPreparation,
)
from modules.communication.moltbot_bridge.src.reddog_resident_live_canary import (
    LIVE_CANARY_CONFIRMATION,
    REQUIRED_JSON_ARTIFACTS,
    run_reddog_resident_live_canary,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    CHAIN_RESULTS_SCHEMA_VERSION,
    AtomicJsonResidentQueueChainResultsStore,
    record_resident_queue_stage_result,
    resident_queue_chain_receipt_id,
    resident_queue_chain_snapshot_is_canonical,
    resident_queue_chain_snapshot_revision,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_CHAIN_COMPLETE,
    _CHAIN,
    plan_reddog_resident_queue_orchestration,
)
from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
    build_reddog_verified_pattern_memory_sink,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_held_out_regression_gate_invoke import (
    invoke_reddog_wre_queue_authorized_held_out_regression_gate,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_pattern_memory_admission_invoke import (
    QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT,
    invoke_reddog_wre_queue_authorized_pattern_memory_admission,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_draft_pr_publish_invoke import (
    invoke_reddog_wre_queue_authorized_verified_draft_pr_publish,
)
from modules.communication.moltbot_bridge.src.reddog_wre_worktree_create import WORKTREE_CREATE_ACCEPT
from modules.communication.moltbot_bridge.tests.reddog_live_canary_artifact_test_support import (
    write_live_canary_artifacts,
)
from modules.communication.moltbot_bridge.tests.test_reddog_resident_queue_serial_loop import _snapshot


SLICE_NAME = "REDDOG_TEST_SLICE_PHASE1"
WORK_ORDER_ID = "work-order-1"
NOW = "2026-07-14T00:00:00+00:00"
QUEUE_ID = "queue-1"


def _test_private_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    return Ed25519PrivateKey.generate()


def _test_public_key(private_key) -> str:
    from cryptography.hazmat.primitives import serialization

    return encode_ed25519_public_key(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )


class _AuditMacBuilder:
    def build(self, request: SigningRequest, signature: str, peer: SignerPeerAttestation) -> str:
        return "audit:" + request.nonce + ":" + peer.peer_principal_id


class _LocalSignerClient:
    def __init__(self, backend: Ed25519SignerBackend) -> None:
        self.backend = backend

    def sign(self, request: SigningRequest):
        return self.backend.sign(
            request,
            SignerPeerAttestation(
                peer_principal_id="github:mjtrout",
                transport="test_in_process",
                credential_source="test_fixture",
                boundary_attested=True,
            ),
        )


_PRIVATE_KEY = _test_private_key()
_PUBLIC_KEY = _test_public_key(_PRIVATE_KEY)
_AUTHORITY_PROFILE_SOURCE = {
    "schema_version": "reddog_authority_profile_source.v1",
    "principal_id": "github:mjtrout",
    "principal_provider": "github",
    "principal_public_key": encode_ed25519_public_key(b"B" * 32),
    "reddog_id": "reddog:architect",
    "reddog_public_key": _PUBLIC_KEY,
    "repo_full_name": "FOUNDUPS/Foundups-Agent",
    "foundup_id": "paccess_001",
    "allowed_paths": ["modules/foundups/paccess_001/src/**"],
    "denied_paths": ["modules/foundups/paccess_001/secrets/**"],
    "requested_operation": "worktree_create",
    "permission_snapshot_digest": "sha256:" + "1" * 64,
    "identity_nonce": "canary-identity-nonce",
    "work_authority_nonce": "canary-work-nonce",
    "issued_at": 1_700_000_000,
    "identity_expires_at": 1_800_000_000,
    "work_authority_expires_at": 1_800_000_000,
    "valve_state_required": "VALVE_OPEN_WORKTREE_CREATE",
    "key_epoch": "epoch-canary-1",
    "required_tests": ["pytest live-canary"],
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
_AUTHORITY_PROFILE_SOURCE["authority_profile_source_receipt_id"] = (
    "sha256:"
    + hashlib.sha256(
        json.dumps(
            _AUTHORITY_PROFILE_SOURCE,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
)
_AUTHORITY_PROFILE = {
    **_AUTHORITY_PROFILE_SOURCE,
    "operational_context_binding": {
        "queue_item_id": QUEUE_ID,
        "claim_id": "claim-live-canary",
        "architect_determination_receipt_id": "determination-live-canary",
        "wsp15_allocation_receipt": {
            "receipt_id": "sha256:" + "3" * 64
        },
    },
}
class _StatelessTestControlLoopAnchorStore:
    """Test-only anchor used where persistence is not under test."""

    def prepare(self, payload):
        return ControlLoopAnchorPreparation(expected_revision=None)

    def commit(self, payload, response, *, expected_revision):
        return None
_AUTHORITY_PROFILE_DIGEST = "sha256:" + hashlib.sha256(
    json.dumps(
        _AUTHORITY_PROFILE,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
).hexdigest()
_SIGNING_CONTEXT = ControlLoopReceiptSigningContext(
    signer=_LocalSignerClient(
        Ed25519SignerBackend(
            private_key=_PRIVATE_KEY,
            public_key=_PUBLIC_KEY,
            key_epoch="epoch-canary-1",
            audit_mac_builder=_AuditMacBuilder(),
            control_loop_anchor_store=_StatelessTestControlLoopAnchorStore(),
            control_loop_authority_policy=ControlLoopAuthorityPolicy(
                issuer_principal_id="github:mjtrout",
                signer_public_key=_PUBLIC_KEY,
                key_epoch="epoch-canary-1",
                consensus_receipt_digest="sha256:" + "c" * 64,
                authority_profile_digest=_AUTHORITY_PROFILE_DIGEST,
                authority_profile_source_receipt_id=str(
                    _AUTHORITY_PROFILE["authority_profile_source_receipt_id"]
                ),
            ),
        )
    ),
    signature_verifier=Ed25519SignatureVerifier(),
    issuer_principal_id="github:mjtrout",
    signer_public_key=_PUBLIC_KEY,
    key_epoch="epoch-canary-1",
    authority_tier="HIGH",
    consensus_receipt_digest="sha256:" + "c" * 64,
    authority_profile_digest=_AUTHORITY_PROFILE_DIGEST,
    authority_profile_source_receipt_id=str(
        _AUTHORITY_PROFILE["authority_profile_source_receipt_id"]
    ),
)


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _roots(
    tmp_path: Path,
    *,
    canonical_artifacts: bool = False,
) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "reddog-canary@example.invalid")
    _git(repo, "config", "user.name", "RedDog Canary Test")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-m", "test: seed live canary repo")
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    write_live_canary_artifacts(
        repo=repo,
        runtime=runtime,
        queue_item_id=QUEUE_ID,
        now_iso=NOW,
    )
    if canonical_artifacts:
        return repo, runtime
    for filename in REQUIRED_JSON_ARTIFACTS:
        payload = {"kind": filename}
        if filename == "authority_profile.json":
            payload = dict(_AUTHORITY_PROFILE)
        (runtime / filename).write_text(json.dumps(payload), encoding="utf-8")
    signer_runtime = runtime.parent / f"{runtime.name}-signer-state"
    anchor_path = signer_runtime / "signer_control_loop_anchor.json"
    (runtime / "signer_service_config.json").write_text(
        json.dumps(
            {
                "control_loop_anchor_path": str(anchor_path),
                "runtime_root": str(runtime),
                "signer_runtime_root": str(signer_runtime),
            }
        ),
        encoding="utf-8",
    )
    (runtime / "authority_profile_source.json").write_text(
        json.dumps(_AUTHORITY_PROFILE_SOURCE), encoding="utf-8"
    )
    return repo, runtime


def _kwargs(repo: Path, runtime: Path) -> dict[str, object]:
    return {
        "repo_root": repo,
        "runtime_root": runtime,
        "environ": {
            "OPENROUTER_API_KEY": "must-never-be-serialized",
            "REDDOG_AUTHORITY_PROFILE_SOURCE_RECEIPT_ID": str(
                _AUTHORITY_PROFILE["authority_profile_source_receipt_id"]
            ),
        },
        "platform_name": "linux",
        "command_resolver": lambda command: f"/usr/bin/{command}",
        "command_probe": lambda argv, cwd: True,
        "socket_probe": lambda path: path.name == "reddog_signer.sock",
    }


class _DraftRunner:
    def push_branch(self, *, worktree_path: Path, branch_name: str):
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}

    def create_draft_pr(self, **_: object) -> str:
        return "https://github.com/FOUNDUPS/Foundups-Agent/pull/9999"


def _create_registered_worktree(repo: Path, runtime: Path) -> tuple[Path, str]:
    isolated = runtime.parent / "isolated-worker"
    _git(repo, "worktree", "add", "--detach", str(isolated), "HEAD")
    return isolated.resolve(), _git(isolated, "rev-parse", "HEAD")


def _draft_stage(isolated: Path, head: str) -> dict[str, object]:
    verifier = {
        "decision": "QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT",
        "verifier_result": {
            "decision": "AUTONOMOUS_SLICE_VERIFIER_ACCEPT",
            "accepted": True,
            "receipt": {
                "receipt_id": "wre_slice_verify_canary",
                "work_order_id": WORK_ORDER_ID,
                "slice_name": SLICE_NAME,
                "head_sha": head,
                "changed_paths": ["seed.txt"],
            },
        },
    }
    request = {
        "work_order_id": WORK_ORDER_ID,
        "pre_publish_branch_head_sha": head,
        "branch_name": "feat/reddog-live-canary-test",
        "base_branch": "main",
        "pr_title": "test: resident live canary evidence",
        "pr_body": "Canonical test-only draft receipt.",
        "worktree_path": str(isolated),
        "draft_pr_only": True,
        "mark_ready": False,
        "merge": False,
    }
    return invoke_reddog_wre_queue_authorized_verified_draft_pr_publish(
        explicit_queue_authorized_verified_draft_pr_publish_requested=True,
        queue_slice_verifier_result=verifier,
        publish_request=request,
        runner=_DraftRunner(),
    ).to_dict()


def _held_out_stage(head: str) -> dict[str, object]:
    ratchet = {
        "decision": "QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT",
        "ratchet_result": {
            "decision": "OUTCOME_RATCHET_RECORDED",
            "accepted": True,
            "receipt": {
                "ratchet_id": "outcome_ratchet_canary",
                "work_order_id": WORK_ORDER_ID,
                "slice_name": SLICE_NAME,
                "verifier_receipt_id": "wre_slice_verify_canary",
                "pattern_memory_eligible": True,
            },
        },
    }
    request = {
        "work_order_id": WORK_ORDER_ID,
        "slice_name": SLICE_NAME,
        "worker_id": "reddog-0102",
        "enable_pattern_memory_admission": True,
        "improvement_job": {"job_id": "imp_live_canary", "status": "pending", "dry_run": True},
        "verification_result": {
            "accepted": True,
            "decision": "AUTONOMOUS_SLICE_VERIFIER_ACCEPT",
            "receipt": {
                "receipt_id": "wre_slice_verify_canary",
                "work_order_id": WORK_ORDER_ID,
                "slice_name": SLICE_NAME,
                "head_sha": head,
            },
        },
        "held_out_regression": {
            "suite_id": "heldout-live-canary",
            "is_held_out": True,
            "independent": True,
            "generated_by_author": False,
            "evidence_author_id": "verifier-0102",
            "passed": True,
            "test_count": 1,
            "failure_count": 0,
            "suite_digest": "sha256:" + "1" * 64,
            "baseline_digest": "sha256:" + "2" * 64,
            "candidate_digest": "sha256:" + "3" * 64,
            "candidate_head_sha": head,
        },
        "holoindex_evidence": {
            "index_gap_detected": False,
            "holoindex_freshness_receipt_digest": "sha256:" + "4" * 64,
        },
    }
    return invoke_reddog_wre_queue_authorized_held_out_regression_gate(
        explicit_queue_authorized_held_out_regression_gate_requested=True,
        queue_verified_outcome_ratchet_result=ratchet,
        held_out_gate_request=request,
    ).to_dict()


def _stage_results(repo: Path, runtime: Path) -> dict[str, dict[str, object]]:
    isolated, head = _create_registered_worktree(repo, runtime)
    stages = {stage.key: {stage.status_field: stage.accepted_value} for stage in _CHAIN}
    stages["worktree_create"].update(
        worktree_create_result={"decision": WORKTREE_CREATE_ACCEPT, "worktree_path": str(isolated)}
    )
    stages["verified_draft_pr_publish"] = _draft_stage(isolated, head)
    stages["held_out_regression_gate"] = _held_out_stage(head)
    stages.pop("pattern_memory_admission")
    return stages


def _write_pre_state(repo: Path, runtime: Path) -> dict[str, object]:
    store = AtomicJsonResidentQueueChainResultsStore(
        runtime / "resident_queue_chain_results.json",
        allowed_root=runtime,
    )
    for stage_key, stage_result in _stage_results(repo, runtime).items():
        result = record_resident_queue_stage_result(
            work_state_snapshot=_snapshot(), store=store, stage_key=stage_key,
            stage_result=stage_result, now_iso=NOW, requested_queue_item_id=QUEUE_ID,
        )
        assert result.accepted is True
    state = dict(store.load())
    assert resident_queue_chain_snapshot_is_canonical(state) is True
    return state


def _control_receipt(repo: Path, **changes: object) -> dict[str, object]:
    receipt = build_resident_control_loop_receipt(
        result={
            "accepted": True, "status": "PASS", "rounds": 1, "serial_progress": 1,
            "claim_progress": 0, "control_lock_acquired": True,
            "receipt_ids": ("serial-receipt-1",), "rejection_reasons": (),
        },
        repo_root=repo,
        created_at="2026-07-14T00:00:00Z",
        cycle_id="canary-cycle-1",
        nonce="canary-nonce-1",
        signing_context=_SIGNING_CONTEXT,
    ).to_dict()
    receipt.update(changes)
    return receipt


def _write_control_receipt_and_head(
    repo: Path,
    runtime: Path,
    control: dict[str, object],
) -> None:
    (runtime / "resident_queue_control_loop_receipts.jsonl").write_text(
        json.dumps(control) + "\n", encoding="utf-8"
    )
    store, state, _ = load_control_receipt_head(
        runtime / "authority_runtime_state.json",
        runtime_root=runtime,
        repo_root=repo,
    )
    head = build_control_receipt_head(
        receipt=control,
        receipt_ids=(str(control["receipt_id"]),),
        consumed_child_receipt_ids=tuple(
            str(item) for item in control["child_execution_receipt_ids"]
        ),
        consumed_child_evidence_digests=tuple(
            str(item) for item in control["child_execution_evidence_digests"]
        ),
    )
    commit_control_receipt_head(store=store, state=state, head=head)
    config = json.loads(
        (runtime / "signer_service_config.json").read_text(encoding="utf-8")
    )
    anchor = AtomicSignerControlLoopAnchorStore(
        config["control_loop_anchor_path"],
        runtime_root=config["signer_runtime_root"],
        repo_root=repo,
    )
    unsigned = {
        key: value
        for key, value in control.items()
        if key
        not in {
            "signature",
            "signer_audit_mac",
            "signer_audit_attestation_signature",
        }
    }
    response = {
        "signature": control["signature"],
        "audit_mac": control["signer_audit_mac"],
        "audit_attestation_signature": control[
            "signer_audit_attestation_signature"
        ],
    }
    anchor.commit(unsigned, response, expected_revision=None)


def _canonicalize_terminal_receipt(chain: dict[str, object]) -> None:
    stages = dict(chain["stage_results"])
    final_plan = plan_reddog_resident_queue_orchestration(
        _snapshot(), chain_results=stages, requested_queue_item_id=QUEUE_ID, now_iso=NOW
    )
    previous_stages = dict(stages)
    previous_stages.pop("pattern_memory_admission")
    previous_plan = plan_reddog_resident_queue_orchestration(
        _snapshot(), chain_results=previous_stages,
        requested_queue_item_id=QUEUE_ID, now_iso=NOW,
    )
    receipt = chain["receipts"][-1]
    receipt.update(
        recorded_stage="pattern_memory_admission",
        previous_plan_id=previous_plan.plan_id,
        next_plan_id=final_plan.plan_id,
        next_action=NEXT_QUEUE_CHAIN_COMPLETE,
        receipt_id=resident_queue_chain_receipt_id(
            queue_item_id=QUEUE_ID,
            selected_slice=SLICE_NAME,
            recorded_stage="pattern_memory_admission",
            previous_plan_id=previous_plan.plan_id,
            next_plan_id=final_plan.plan_id,
        ),
    )


def _runner(
    repo: Path,
    runtime: Path,
    *,
    chain_mutator=None,
    receipt_changes: dict[str, object] | None = None,
    result_receipt_id: str | None = None,
    rebind_after_mutation: bool = True,
    pattern_db_mutator=None,
):
    def run(_: Path) -> dict[str, object]:
        store = AtomicJsonResidentQueueChainResultsStore(
            runtime / "resident_queue_chain_results.json",
            allowed_root=runtime,
        )
        chain = dict(store.load())
        held = chain["stage_results"]["held_out_regression_gate"]
        sink = build_reddog_verified_pattern_memory_sink(repo_root=repo, db_path=runtime / "pattern_memory.db")
        pattern = invoke_reddog_wre_queue_authorized_pattern_memory_admission(
            explicit_queue_authorized_pattern_memory_admission_requested=True,
            queue_held_out_gate_result=held,
            admission_request={"work_order_id": WORK_ORDER_ID},
            sink=sink,
        )
        assert pattern.decision == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT
        recorded = record_resident_queue_stage_result(
            work_state_snapshot=_snapshot(), store=store, stage_key="pattern_memory_admission",
            stage_result=pattern.to_dict(), now_iso=NOW, requested_queue_item_id=QUEUE_ID,
        )
        assert recorded.accepted is True
        if pattern_db_mutator:
            pattern_db_mutator(runtime / "pattern_memory.db", pattern.receipt.pattern_memory_record_id)
        chain = dict(store.load())
        if chain_mutator:
            chain_mutator(chain)
            if rebind_after_mutation and chain.get("schema_version") == CHAIN_RESULTS_SCHEMA_VERSION:
                revision = resident_queue_chain_snapshot_revision(chain)
                chain["revision"] = revision
                if chain.get("receipts"):
                    chain["receipts"][-1]["store_revision"] = revision
        (runtime / "resident_queue_chain_results.json").write_text(json.dumps(chain), encoding="utf-8")
        control = _control_receipt(repo, **(receipt_changes or {}))
        _write_control_receipt_and_head(repo, runtime, control)
        return {"accepted": True, "status": "PASS", "receipt_id": result_receipt_id or control["receipt_id"]}

    return run


def _execute(repo: Path, runtime: Path, **runner_kwargs: object):
    _write_pre_state(repo, runtime)
    return run_reddog_resident_live_canary(
        **_kwargs(repo, runtime), execute=True, confirmation=LIVE_CANARY_CONFIRMATION,
        queue_item_id=QUEUE_ID, control_loop_runner=_runner(repo, runtime, **runner_kwargs),
        now=lambda: __import__("datetime").datetime.fromisoformat(NOW),
    )
