"""Use-time integration tests for current signer generation evidence."""

from __future__ import annotations

import json

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_execution_valve_use_time_authority as use_time_module,
)
from modules.communication.moltbot_bridge.src import (
    reddog_signer_current_generation_use_time_gate as gate_module,
)
from modules.communication.moltbot_bridge.src.reddog_execution_valve_use_time_authority import (
    AUTHENTICATED_RUNTIME_ARTIFACT_MANIFEST_SELECTION_MISSING,
    CURRENT_RUNTIME_ARTIFACT_GENERATION_VERIFIER_MISSING,
    DURABLE_RUNTIME_ARTIFACT_MANIFEST_REPLAY_STATE_MISSING,
    GovernedValveUseTimeAuthorityResolver,
    _digest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    InMemoryResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_runtime_binding import (
    SignerCurrentGenerationRuntimeBinding,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    VerificationResult,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_live_canary_test_support import (
    QUEUE_ID,
    _roots,
)


NOW_EPOCH = 1_784_006_400
SLICE = "REDDOG_TEST_SLICE_PHASE1"


def _authority_state(work_order_id: str, work_order: dict[str, object]):
    work_authority = {
        "work_order_id": work_order_id,
        "work_order_digest": canonical_full_work_order_digest(work_order),
        "base_ref": "main",
        "nonce": "nonce-use-time-generation",
        "expires_at": NOW_EPOCH + 300,
    }
    stages = {
        "authority_runtime": {
            "decision": "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT",
            "authority_result": {
                "accepted": True,
                "receipt": {
                    "status": "DELEGATED_AUTHORITY_ISSUED",
                    "work_authority_digest": _digest(work_authority),
                },
                "identity": {"principal_id": "github:mjtrout"},
                "work_authority": work_authority,
            },
        },
        "authority_verification": {
            "decision": "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT",
            "verification_result": {
                "accepted": True,
                "work_order_id": work_order_id,
            },
        },
    }
    store = InMemoryResidentQueueChainResultsStore()
    store.commit(
        {
            "schema_version": "reddog_resident_queue_chain_results.v1",
            "queue_item_id": QUEUE_ID,
            "selected_slice": SLICE,
            "stage_results": stages,
            "receipts": [{"store_revision": None}],
        },
        expected_revision=None,
    )
    return store


def _resolver(repo, runtime) -> GovernedValveUseTimeAuthorityResolver:
    return GovernedValveUseTimeAuthorityResolver(
        repo_root=repo,
        work_state_path=runtime / "authoritative_work_state.json",
        authority_profile_path=runtime / "authority_profile.json",
        permission_snapshots_path=runtime / "permission_snapshots.json",
        principal_authority_records_path=runtime / "principal_authority_records.json",
        valve_environment_path=runtime / "execution_valve_env.json",
        runtime_allowed_root=runtime,
        signature_verifier=object(),
        principal_key_resolver=object(),
        nonce_store=object(),
        snapshot_resolver=object(),
        revocation_oracle=object(),
        now_epoch=NOW_EPOCH,
        required_valve_state="VALVE_OPEN_WORKTREE_CREATE",
        trusted_now_epoch=lambda: NOW_EPOCH,
    )


def test_resolver_removes_only_three_verified_generation_blockers(
    tmp_path, monkeypatch,
) -> None:
    repo, runtime = _roots(tmp_path, canonical_artifacts=True)
    valve = json.loads((runtime / "execution_valve_env.json").read_text("utf-8"))
    work_order = {"work_order_id": valve["work_order_id"], "base_ref": "main"}
    store = _authority_state(valve["work_order_id"], work_order)
    monkeypatch.setattr(
        use_time_module,
        "verify_delegated_work_authority",
        lambda **_: VerificationResult(
            accepted=True, work_order_id=valve["work_order_id"]
        ),
    )
    receipt_id = "sha256:" + "a" * 64

    class AcceptedEvidence:
        def __init__(self):
            self.receipt_id = receipt_id

        def remaining_reasons(self, all_reasons, bound_reasons):
            bound = frozenset(bound_reasons)
            return tuple(reason for reason in all_reasons if reason not in bound)

    monkeypatch.setattr(
        use_time_module,
        "collect_signer_current_generation_use_time_evidence",
        lambda *_: AcceptedEvidence(),
    )

    result = _resolver(repo, runtime).resolve(
        chain_state=store.load(),
        work_order=work_order,
        queue_item_id=QUEUE_ID,
        selected_slice=SLICE,
    )

    assert AUTHENTICATED_RUNTIME_ARTIFACT_MANIFEST_SELECTION_MISSING not in result.rejection_reasons
    assert DURABLE_RUNTIME_ARTIFACT_MANIFEST_REPLAY_STATE_MISSING not in result.rejection_reasons
    assert CURRENT_RUNTIME_ARTIFACT_GENERATION_VERIFIER_MISSING not in result.rejection_reasons
    assert "canonical_signer_client_peer_handshake_verifier_missing" in result.rejection_reasons
    assert result.authoritative_use_lease is None
    assert result.signer_generation_binding_receipt_id == receipt_id


@pytest.mark.parametrize(
    "proof",
    (
        {"accepted": True, "receipt_id": "sha256:" + "a" * 64},
        SignerCurrentGenerationRuntimeBinding(
            accepted=False,
            rejection_reasons=("rejected",),
            receipt_id="sha256:" + "a" * 64,
        ),
    ),
)
def test_binding_requires_typed_accepted_digest(tmp_path, monkeypatch, proof) -> None:
    monkeypatch.setattr(
        gate_module,
        "verify_signer_current_generation_runtime_binding",
        lambda **_: proof,
    )
    result = gate_module.collect_signer_current_generation_use_time_evidence(
        enabled=True,
        repo_root=tmp_path / "repo",
        runtime_root=tmp_path / "runtime",
        trusted_now_epoch=lambda: 100,
    )
    assert result.receipt_id is None


def test_binding_dependency_failure_is_fail_closed(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        gate_module,
        "verify_signer_current_generation_runtime_binding",
        lambda **_: (_ for _ in ()).throw(RuntimeError("dependency failed")),
    )
    result = gate_module.collect_signer_current_generation_use_time_evidence(
        enabled=True,
        repo_root=tmp_path / "repo",
        runtime_root=tmp_path / "runtime",
        trusted_now_epoch=lambda: 100,
    )
    assert result.receipt_id is None
