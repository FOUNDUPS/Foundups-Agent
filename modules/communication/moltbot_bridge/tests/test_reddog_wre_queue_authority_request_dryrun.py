"""Tests for REDDOG_WRE_QUEUE_AUTHORITY_REQUEST_DRYRUN_PHASE1."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from modules.communication.moltbot_bridge.src import (
    reddog_wre_queue_authority_request_dryrun as planner,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_WORKTREE_CREATE,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_consumer_dryrun import (
    NEXT_GATE_SIGNED_AUTHORITY_REQUIRED,
    WRE_QUEUE_CONSUMER_DRYRUN_READY,
)
from modules.communication.moltbot_bridge.tests.reddog_signed_worker_dispatch_test_support import (
    signed_stage_binding,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MEMEX_SUPPLY_RECEIPT_ID = "sha256:memex-supply"
MEMEX_SUPPLY_DIGEST = "sha256:" + ("d" * 64)
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_wre_queue_authority_request_dryrun.py"
)


def _queue_result(**overrides):
    receipt = {
        "receipt_id": "wre_queue_consumer_1234",
        "queue_item_id": "queue-1",
        "slice_id": "FOUNDUP_SCOPED_SAMPLE_PHASE1",
        "claim_id": "claim-1",
        "worker_id": "reddog-main-bootstrap",
        "freshness_receipt_id": "fresh-1",
        "wsp15_allocation_receipt_id": "sha256:wsp15-allocation",
        "wsp15_allocation_digest": "sha256:wsp15-allocation-digest",
        "wsp15_priority": "P0",
        "wsp15_mps_total": 18,
        "reasoning_tier": "ULTRA",
        **signed_stage_binding(requested_operation="create_foundup"),
        "model_selection_receipt_id": "sha256:model-selection",
        "model_selection_digest": "sha256:model-selection-digest",
        "model_runtime_binding_receipt_id": "reddog_model_runtime_binding:abc123",
        "model_runtime_binding_digest": "sha256:model-runtime-binding",
        "model_runtime_binding_verification_receipt_id": (
            "model_runtime_binding_verification:abc123"
        ),
        "model_runtime_binding_verification_digest": (
            "sha256:model-runtime-binding-verification"
        ),
        "memex_supply_receipt_id": MEMEX_SUPPLY_RECEIPT_ID,
        "memex_supply_digest": MEMEX_SUPPLY_DIGEST,
        "next_required_gate": NEXT_GATE_SIGNED_AUTHORITY_REQUIRED,
        "execution_ready": False,
        "no_queue_mutation_performed": True,
    }
    result = {
        "accepted": True,
        "status": WRE_QUEUE_CONSUMER_DRYRUN_READY,
        "rejection_reasons": [],
        "receipt": receipt,
        "selected_queue_item_id": "queue-1",
        "selected_slice": "FOUNDUP_SCOPED_SAMPLE_PHASE1",
        "next_required_gate": NEXT_GATE_SIGNED_AUTHORITY_REQUIRED,
        "execution_ready": False,
    }
    result.update(overrides)
    return result


def _profile(**overrides):
    profile = {
        "principal_id": "github:mjtrout",
        "principal_provider": "github",
        "principal_public_key": "pub:principal",
        "reddog_id": "reddog:abc123",
        "reddog_public_key": "pub:reddog",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "foundup_id": "paccess_001",
        "base_ref": "main",
        "allowed_paths": ["modules/foundups/paccess_001/**"],
        "denied_paths": ["modules/foundups/paccess_001/secrets/**"],
        "requested_operation": "create_foundup",
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
        "wsp15_allocation_receipt": {
            "receipt_id": "sha256:wsp15-allocation",
            "priority": "P0",
            "mps_total": 18,
            "reasoning_tier": "ULTRA",
            "worker_plan": {"fusion_required": True},
        },
        "model_runtime_binding_receipt_id": "reddog_model_runtime_binding:abc123",
        "model_runtime_binding_digest": "sha256:model-runtime-binding",
        "model_runtime_binding_verification_receipt_id": (
            "model_runtime_binding_verification:abc123"
        ),
        "model_runtime_binding_verification_digest": (
            "sha256:model-runtime-binding-verification"
        ),
    }
    profile.update(overrides)
    return profile


def _work_order(**overrides):
    work_order = {
        "work_order_id": "wre-queue-" + hashlib.sha256(b"queue-1").hexdigest()[:16],
        "base_ref": "main",
        "branch_name": "feat/reddog-bound-work-order",
        "requested_operation": "create_foundup",
    }
    work_order.update(overrides)
    return work_order


def test_builds_delegated_authority_runtime_request_without_signing() -> None:
    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=_queue_result(),
        authority_profile=_profile(),
        work_order=_work_order(),
    )

    assert result.accepted is True
    assert result.status == planner.QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT
    assert result.execution_ready is False
    assert result.signer_invoked is False
    assert result.no_signing_performed is True
    assert result.no_signer_state_mutation_performed is True
    assert result.no_worker_spawn_performed is True
    assert result.no_worktree_created is True
    assert result.no_shell_command_executed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_repo_mutation_performed is True
    assert result.no_holoindex_reindex_performed is True
    assert result.no_pr_created is True
    assert result.no_reward_settlement_performed is True
    assert result.receipt is not None
    request = result.delegated_authority_request
    assert request is not None
    assert request["work_order_id"].startswith("wre-queue-")
    assert request["base_ref"] == "main"
    assert request["work_order_digest"] == canonical_full_work_order_digest(_work_order())
    assert request["foundup_id"] == "paccess_001"
    assert request["allowed_paths"] == (
        "modules/foundups/paccess_001/src/worker.py",
    )
    assert request["requested_operation"] == "create_foundup"
    assert request["valve_state_required"] == VALVE_OPEN_WORKTREE_CREATE
    assert request["wsp15_allocation_receipt_id"] == "sha256:wsp15-allocation"
    assert request["wsp15_allocation_digest"] == "sha256:wsp15-allocation-digest"
    assert request["wsp15_priority"] == "P0"
    assert request["wsp15_mps_total"] == 18
    assert request["wsp15_reasoning_tier"] == "ULTRA"
    expected_stage = _queue_result()["receipt"]
    assert request["progressive_policy_stage_receipt_id"] == expected_stage[
        "progressive_policy_stage_receipt_id"
    ]
    assert request["progressive_policy_stage_digest"] == expected_stage[
        "progressive_policy_stage_digest"
    ]
    assert request["progressive_policy_stage_receipt"] == expected_stage[
        "progressive_policy_stage_receipt"
    ]
    assert request["model_selection_receipt_id"] == "sha256:model-selection"
    assert request["model_selection_digest"] == "sha256:model-selection-digest"
    assert request["model_runtime_binding_receipt_id"] == "reddog_model_runtime_binding:abc123"
    assert request["model_runtime_binding_digest"] == "sha256:model-runtime-binding"
    assert request["memex_supply_receipt_id"] == MEMEX_SUPPLY_RECEIPT_ID
    assert request["memex_supply_digest"] == MEMEX_SUPPLY_DIGEST
    assert result.receipt.wsp15_allocation_receipt_id == "sha256:wsp15-allocation"
    assert result.receipt.wsp15_allocation_digest == "sha256:wsp15-allocation-digest"
    assert result.receipt.wsp15_priority == "P0"
    assert result.receipt.wsp15_mps_total == 18
    assert result.receipt.reasoning_tier == "ULTRA"
    assert result.receipt.model_selection_receipt_id == "sha256:model-selection"
    assert result.receipt.model_selection_digest == "sha256:model-selection-digest"
    assert result.receipt.model_runtime_binding_receipt_id == "reddog_model_runtime_binding:abc123"
    assert result.receipt.model_runtime_binding_digest == "sha256:model-runtime-binding"
    assert result.receipt.memex_supply_receipt_id == MEMEX_SUPPLY_RECEIPT_ID
    assert result.receipt.memex_supply_digest == MEMEX_SUPPLY_DIGEST
    assert result.receipt.delegated_authority_request_digest.startswith("sha256:")


def test_rejects_unaccepted_queue_consumer_result() -> None:
    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=_queue_result(accepted=False),
        authority_profile=_profile(),
    )

    assert result.accepted is False
    assert planner.FAIL_QUEUE_CONSUMER_NOT_READY in result.rejection_reasons
    assert result.delegated_authority_request is None


def test_rejects_missing_profile() -> None:
    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=_queue_result(),
        authority_profile=None,
    )

    assert result.accepted is False
    assert planner.FAIL_PROFILE_MISSING in result.rejection_reasons


def test_rejects_queue_consumer_without_wsp15_allocation_binding() -> None:
    queue = _queue_result()
    queue["receipt"].pop("wsp15_allocation_receipt_id")

    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=queue,
        authority_profile=_profile(),
    )

    assert result.accepted is False
    assert planner.FAIL_WSP15_ALLOCATION_BINDING in result.rejection_reasons


def test_rejects_profile_wsp15_binding_that_conflicts_with_queue() -> None:
    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=_queue_result(),
        authority_profile=_profile(
            wsp15_allocation_receipt={
                "receipt_id": "sha256:other",
                "priority": "P0",
                "mps_total": 18,
                "reasoning_tier": "ULTRA",
            }
        ),
    )

    assert result.accepted is False
    assert planner.FAIL_WSP15_ALLOCATION_BINDING in result.rejection_reasons


def test_rejects_model_runtime_binding_that_conflicts_with_queue() -> None:
    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=_queue_result(),
        authority_profile=_profile(model_runtime_binding_digest="sha256:other"),
    )

    assert result.accepted is False
    assert planner.FAIL_MODEL_RUNTIME_BINDING in result.rejection_reasons


def test_allows_legacy_queue_without_model_runtime_binding() -> None:
    queue = _queue_result()
    queue["receipt"].pop("model_runtime_binding_receipt_id")
    queue["receipt"].pop("model_runtime_binding_digest")
    queue["receipt"].pop("model_runtime_binding_verification_receipt_id")
    queue["receipt"].pop("model_runtime_binding_verification_digest")
    profile = _profile()
    profile.pop("model_runtime_binding_receipt_id")
    profile.pop("model_runtime_binding_digest")
    profile.pop("model_runtime_binding_verification_receipt_id")
    profile.pop("model_runtime_binding_verification_digest")

    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=queue,
        authority_profile=profile,
        work_order=_work_order(),
    )

    assert result.accepted is True
    assert result.delegated_authority_request is not None
    assert result.delegated_authority_request["model_runtime_binding_receipt_id"] is None
    assert result.delegated_authority_request["model_runtime_binding_digest"] is None


def test_accepts_mixed_absent_memex_encodings_without_exception() -> None:
    queue = _queue_result()
    queue["receipt"]["memex_supply_receipt_id"] = None
    queue["receipt"]["memex_supply_digest"] = None

    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=queue,
        authority_profile=_profile(),
        work_order=_work_order(
            memex_supply_receipt_id="",
            memex_supply_digest="",
        ),
    )

    assert result.accepted is True
    assert result.delegated_authority_request is not None
    assert result.delegated_authority_request["memex_supply_receipt_id"] is None
    assert result.delegated_authority_request["memex_supply_digest"] is None


def test_rejects_base_ref_spliced_between_profile_and_full_work_order() -> None:
    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=_queue_result(),
        authority_profile=_profile(base_ref="release"),
        work_order=_work_order(base_ref="main"),
    )

    assert result.accepted is False
    assert planner.FAIL_WORK_ORDER_BINDING in result.rejection_reasons


def test_rejects_profile_memex_binding_conflicting_with_queue_authority() -> None:
    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=_queue_result(),
        authority_profile=_profile(
            memex_supply_receipt_id="sha256:attacker-memex",
            memex_supply_digest="sha256:" + ("e" * 64),
        ),
        work_order=_work_order(),
    )

    assert result.accepted is False
    assert planner.FAIL_MEMEX_SUPPLY_BINDING in result.rejection_reasons
    assert result.delegated_authority_request is None


def test_rejects_work_order_memex_binding_conflicting_with_queue_authority() -> None:
    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=_queue_result(),
        authority_profile=_profile(),
        work_order=_work_order(
            memex_supply_receipt_id="sha256:attacker-memex",
            memex_supply_digest="sha256:" + ("e" * 64),
        ),
    )

    assert result.accepted is False
    assert planner.FAIL_MEMEX_SUPPLY_BINDING in result.rejection_reasons
    assert result.delegated_authority_request is None


def test_rejects_malformed_queue_memex_authority_before_signing() -> None:
    queue = _queue_result()
    queue["receipt"]["memex_supply_digest"] = "sha256:not-canonical"

    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=queue,
        authority_profile=_profile(),
        work_order=_work_order(),
    )

    assert result.accepted is False
    assert planner.FAIL_MEMEX_SUPPLY_BINDING in result.rejection_reasons
    assert result.delegated_authority_request is None


def test_rejects_missing_required_profile_field() -> None:
    profile = _profile()
    del profile["principal_public_key"]

    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=_queue_result(),
        authority_profile=profile,
    )

    assert result.accepted is False
    assert f"{planner.FAIL_REQUIRED_FIELD}:principal_public_key" in result.rejection_reasons


def test_rejects_non_ascii_profile() -> None:
    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=_queue_result(),
        authority_profile=_profile(principal_id="github:mjtrout-\u03c0"),
    )

    assert result.accepted is False
    assert planner.FAIL_PROFILE_NON_ASCII in result.rejection_reasons


def test_rejects_allowed_path_outside_foundup_scope() -> None:
    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=_queue_result(),
        authority_profile=_profile(allowed_paths=["modules/communication/moltbot_bridge/src/main.py"]),
    )

    assert result.accepted is False
    assert planner.FAIL_ALLOWED_PATH_SCOPE in result.rejection_reasons


def test_rejects_denied_path_outside_foundup_scope() -> None:
    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=_queue_result(),
        authority_profile=_profile(denied_paths=[".github/workflows/**"]),
    )

    assert result.accepted is False
    assert planner.FAIL_DENIED_PATH_SCOPE in result.rejection_reasons


def test_rejects_repo_wide_authority_until_generic_contract_exists() -> None:
    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=_queue_result(),
        authority_profile=_profile(foundup_id="repo", allowed_paths=["modules/foundups/repo/**"]),
    )

    assert result.accepted is False
    assert planner.FAIL_UNSUPPORTED_REPO_WIDE_AUTHORITY in result.rejection_reasons


def test_rejects_high_authority_without_consensus_and_sovereign_digest() -> None:
    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=_queue_result(),
        authority_profile=_profile(consensus_receipt_digest=None, sovereign_authorization_digest=None),
    )

    assert result.accepted is False
    assert planner.FAIL_HIGH_AUTHORITY_COSIGN in result.rejection_reasons


def test_low_authority_does_not_require_cosign() -> None:
    result = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=_queue_result(),
        authority_profile=_profile(
            requested_operation="inspect_repo",
            consensus_receipt_digest=None,
            sovereign_authorization_digest=None,
        ),
        work_order=_work_order(requested_operation="inspect_repo"),
    )

    assert result.accepted is True
    assert result.delegated_authority_request is not None
    assert result.delegated_authority_request["requested_operation"] == "inspect_repo"


def test_module_has_no_shell_network_signing_state_or_runtime_invocation_imports() -> None:
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
    banned_calls = {"eval", "exec", "compile", "__import__"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls
