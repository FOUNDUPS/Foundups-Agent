"""Tests for REDDOG_MAIN_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Mapping
from unittest.mock import patch

from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_serial_loop_bootstrap import (
    REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED,
    REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY,
    _operational_context_binding,
    run_reddog_main_resident_queue_serial_loop_bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_runtime_dependency_bundle import (
    REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
    REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY,
)
from modules.communication.moltbot_bridge.src.reddog_generic_agent_worktree_writer_dryrun import (
    GENERIC_WRITER_DRYRUN_ACCEPT,
    GenericAgentWorktreeDomainProfile,
    plan_generic_agent_worktree_writer_dry_run,
)
from modules.communication.moltbot_bridge.src.reddog_wre_executor_dryrun import (
    _proposed_worktree_path,
)
from modules.communication.moltbot_bridge.src.reddog_wre_governed_shell_runner_dryrun import (
    GOVERNED_SHELL_DRYRUN_ACCEPT,
    plan_governed_shell_runner_dry_run,
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
from modules.communication.moltbot_bridge.src.reddog_bounded_artifact_generation_runtime import (
    ArtifactGenerationModelResult,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_bounded_worker_pilot_invoke import (
    _receipt_chain as _pilot_receipt_chain,
    _selection_receipt as _pilot_selection_receipt,
    _shell_profile as _pilot_shell_profile,
    _signed_authority as _pilot_signed_authority,
    _valve as _pilot_valve,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_verified_draft_pr_publish_invoke import (
    FakeDraftPrRunner,
)
from modules.infrastructure.wre_core.src import reddog_verified_outcome_ratchet as ratchet
from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (
    AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
    verify_autonomous_slice_runtime,
)
from modules.infrastructure.wre_core.src.wre_independent_evidence_producer_runtime import (
    CommandResult,
    EVIDENCE_PRODUCER_ACCEPT,
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
PILOT_OPERATION = "queue_bounded_pilot_docs_patch"
PILOT_DOMAIN_ID = FOUNDUP_ID
PILOT_ARTIFACT = f"modules/foundups/{PILOT_DOMAIN_ID}/README.md"


def _queue_wsp15_allocation_receipt() -> dict[str, object]:
    return {
        "schema_version": "reddog_wsp15_allocation_receipt.v1",
        "receipt_id": "sha256:wsp15-allocation-queue",
        "complexity": 5,
        "importance": 5,
        "deferability": 5,
        "impact": 5,
        "mps_total": 20,
        "priority": "P0",
        "reasoning_tier": "ULTRA",
        "worker_plan": {
            "schema_version": "reddog_wsp15_worker_plan.v1",
            "fusion_required": True,
            "reasoning_tier": "ULTRA",
            "critic_count": 2,
            "coding_worker_count": 2,
            "independent_verifier_required": True,
            "openclaw_candidate": True,
            "queue_mutation_allowed": False,
            "hermes_execution_allowed": False,
            "mode_selection_source": "reddog_wsp15_allocation_receipt.v1",
        },
    }


def _snapshot() -> dict[str, object]:
    allocation = _queue_wsp15_allocation_receipt()
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
                "evidence_refs": [
                    "claim:claim-1",
                    "freshness:fresh-1",
                    f"wsp15_allocation:{allocation['receipt_id']}",
                ],
                "wsp15_allocation_receipt": allocation,
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
        "snapshot_receipt_id": "sha256:snapshot-1",
        "context_view_id": "sha256:context-view-1",
        "evidence_bundle_id": "sha256:evidence-bundle-1",
        "readonly_audit_decision_id": "sha256:decision-1",
        "wsp15_allocation_receipt": _queue_wsp15_allocation_receipt(),
        "holoindex_evidence": {
            "holoindex_query": "RedDog resident queue materialized work order",
            "holoindex_status": "bundle_json_ok",
            "code_hits": [
                "modules/communication/moltbot_bridge/src/reddog_main_resident_queue_serial_loop_bootstrap.py"
            ],
            "wsp_hits": ["WSP_framework/src/WSP_34_Git_Operations_Protocol.md"],
            "skillz_hits": [],
            "direct_read_fallback_used": True,
            "index_gap_detected": False,
            "applicable_wsps": ["WSP_34", "WSP_50", "WSP_97"],
            "evidence_refs": [
                "modules/communication/moltbot_bridge/src/reddog_main_resident_queue_serial_loop_bootstrap.py"
            ],
            "retrieval_quality": "HIGH",
            "skillz_gap_detected": False,
            "holoindex_freshness_receipt_digest": "sha256:holo-fresh",
        },
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


def _pilot_allowed_paths() -> list[str]:
    return [f"modules/foundups/{PILOT_DOMAIN_ID}/**"]


def _pilot_domain_profile() -> GenericAgentWorktreeDomainProfile:
    return GenericAgentWorktreeDomainProfile(
        profile_id="resident_queue_paccess_docs_patch",
        operation=PILOT_OPERATION,
        artifact_contract_type="text_patch",
        domain_id_pattern=r"[a-z][a-z0-9_]{2,49}",
        canonical_root_template="modules/foundups/{domain_id}",
        allowed_path_patterns=["modules/foundups/{domain_id}/**"],
        denied_path_patterns=["**/.env", "**/secrets/**"],
        required_tests=[
            "python -m pytest "
            "modules/communication/moltbot_bridge/tests/"
            "test_reddog_main_resident_queue_serial_loop_bootstrap.py -q"
        ],
        branch_prefix="feat/",
        draft_pr_only=True,
        consensus_required=False,
    )


def _pilot_path_overrides() -> dict[str, object]:
    return {
        "requested_operation": PILOT_OPERATION,
        "allowed_paths": _pilot_allowed_paths(),
        "denied_paths": [f"modules/foundups/{PILOT_DOMAIN_ID}/secrets/**"],
        "required_tests": [
            "python -m pytest "
            "modules/communication/moltbot_bridge/tests/"
            "test_reddog_main_resident_queue_serial_loop_bootstrap.py -q"
        ],
        "task_summary": "Resident queue startup materializes one declared fixture in an isolated worktree.",
        "rollback_plan": "Remove isolated worktree and branch; no repo checkout write is permitted.",
    }


def _pilot_worktree_path(repo: Path, work_order: Mapping[str, object]) -> Path:
    return Path(
        _proposed_worktree_path(
            str(repo),
            str(work_order["work_order_id"]),
            str(work_order["nonce"]),
        )
    )


def _pilot_signed_authority_for_bootstrap() -> dict[str, object]:
    authority = dict(_pilot_signed_authority(WORK_ORDER_ID))
    authority["permission_snapshot_digest"] = "sha256:snap-1"
    return authority


def _pilot_payloads(repo: Path, worktree: Path, work_order: Mapping[str, object]) -> dict[str, object]:
    writer = plan_generic_agent_worktree_writer_dry_run(
        {
            "work_order_id": WORK_ORDER_ID,
            "operation": PILOT_OPERATION,
            "domain_id": PILOT_DOMAIN_ID,
            "domain_profile": _pilot_domain_profile(),
            "planned_artifacts": [PILOT_ARTIFACT],
            "requested_allowed_paths": _pilot_allowed_paths(),
            "target_branch": str(work_order["branch_name"]),
            "repo_root": str(repo),
            "worktree_path": str(worktree),
            "operation_cwd": str(worktree),
            "selection_receipt": _pilot_selection_receipt(),
            "signed_authority": _pilot_signed_authority_for_bootstrap(),
            "signed_receipt_chain": _pilot_receipt_chain(),
            "execution_valve_decision": _pilot_valve(),
            "permission_snapshot_digest": "sha256:snap-1",
            "holoindex_evidence": {"index_gap_detected": False},
        }
    )
    assert writer.decision == GENERIC_WRITER_DRYRUN_ACCEPT

    shell = plan_governed_shell_runner_dry_run(
        {
            "work_order_id": WORK_ORDER_ID,
            "profile": _pilot_shell_profile(),
            "argv": [
                "python",
                "-m",
                "pytest",
                "modules/communication/moltbot_bridge/tests/"
                "test_reddog_main_resident_queue_serial_loop_bootstrap.py",
                "-q",
            ],
            "operation_cwd": str(worktree),
            "worktree_path": str(worktree),
            "repo_root": str(repo),
            "selection_receipt": _pilot_selection_receipt(),
            "signed_authority": _pilot_signed_authority_for_bootstrap(),
            "signed_receipt_chain": _pilot_receipt_chain(),
            "execution_valve_decision": _pilot_valve(),
            "generic_writer_dryrun_receipt": writer.receipt.to_dict(),
            "permission_snapshot_digest": "sha256:snap-1",
            "stdin_policy": "none",
            "env_policy": {"scrubbed": True},
            "holoindex_evidence": {
                "index_gap_detected": False,
                "holoindex_freshness_receipt_digest": "sha256:holo-fresh",
            },
        }
    )
    assert shell.decision == GOVERNED_SHELL_DRYRUN_ACCEPT
    return {
        "generic_writer_dryrun_result": writer.to_dict(),
        "governed_shell_dryrun_result": shell.to_dict(),
        "artifact_contents": {
            PILOT_ARTIFACT: (
                "# Resident Queue Pilot\n\n"
                "This artifact is materialized only inside the isolated worktree.\n"
            )
        },
        "holoindex_evidence": {
            "index_gap_detected": False,
            "retrieval_quality": "HIGH",
            "holoindex_freshness_receipt_digest": "sha256:holo-fresh",
        },
    }


def _pilot_bounded_worker_plan() -> dict[str, object]:
    return {
        "operation": PILOT_OPERATION,
        "domain_id": PILOT_DOMAIN_ID,
        "domain_profile": _pilot_domain_profile().to_dict(),
        "planned_artifacts": [PILOT_ARTIFACT],
        "requested_allowed_paths": _pilot_allowed_paths(),
        "shell_profile": _pilot_shell_profile().to_dict(),
        "shell_argv": [
            "python",
            "-m",
            "pytest",
            "modules/communication/moltbot_bridge/tests/"
            "test_reddog_main_resident_queue_serial_loop_bootstrap.py",
            "-q",
        ],
        "selection_receipt": _pilot_selection_receipt(),
        "signed_receipt_chain": _pilot_receipt_chain(),
        "stdin_policy": "none",
        "env_policy": {"scrubbed": True},
    }


def _digest(ch: str) -> str:
    return "sha256:" + ch * 64


def _slice_verifier_request() -> dict[str, object]:
    base_sha = "b" * 40
    head_sha = "a" * 40
    return {
        "work_order_id": WORK_ORDER_ID,
        "slice_name": "REDDOG_MAIN_RESIDENT_QUEUE_SLICE_VERIFIER_BOOTSTRAP_PHASE1",
        "worker_id": "worker:author",
        "verifier_id": "worker:verifier",
        "base_sha": base_sha,
        "head_sha": head_sha,
        "allowed_path_patterns": _pilot_allowed_paths(),
        "expected_changed_paths": [PILOT_ARTIFACT],
        "forbidden_path_patterns": ["**/.env", "**/secrets/**"],
        "diff_evidence": {
            "source": "machine_derived",
            "red_dog_prose_source": False,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "diff_digest": _digest("7"),
            "changed_paths": [PILOT_ARTIFACT],
            "added_lines": ["resident queue pilot fixture update"],
        },
        "test_evidence": {
            "head_sha": head_sha,
            "test_evidence_digest": _digest("8"),
            "required_checks": [
                {"name": "pytest", "head_sha": head_sha, "conclusion": "success"},
                {"name": "security", "head_sha": head_sha, "conclusion": "pass"},
            ],
        },
        "signed_authority": {
            "accepted": True,
            "signature_gate_digest": _digest("9"),
        },
        "signed_receipt_chain": {
            "accepted": True,
            "terminal_receipt_hash": _digest("a"),
        },
        "holoindex_evidence": {
            "index_gap_detected": False,
            "holoindex_freshness_receipt_digest": _digest("b"),
        },
        "pattern_memory_write_performed": False,
        "draft_pr_published": False,
        "merge_performed": False,
    }


def _slice_verifier_plan() -> dict[str, object]:
    return {
        "slice_name": "REDDOG_MAIN_RESIDENT_QUEUE_SLICE_VERIFIER_BOOTSTRAP_PHASE1",
        "worker_id": "worker:author",
        "verifier_id": "worker:verifier",
        "base_sha": "b" * 40,
        "head_sha": "a" * 40,
        "allowed_path_patterns": _pilot_allowed_paths(),
        "expected_changed_paths": [PILOT_ARTIFACT],
        "forbidden_path_patterns": ["**/.env", "**/secrets/**"],
        "required_checks": [
            {
                "name": "pytest",
                "argv": [
                    "python",
                    "-m",
                    "pytest",
                    "modules/communication/moltbot_bridge/tests/"
                    "test_reddog_main_resident_queue_serial_loop_bootstrap.py",
                    "-q",
                ],
                "timeout_s": 30,
            }
        ],
        "signed_receipt_chain": {
            "accepted": True,
            "terminal_receipt_hash": _digest("a"),
        },
    }


def _evidence_producer_request(repo: Path, worktree: Path) -> dict[str, object]:
    return {
        **_slice_verifier_request(),
        "explicit_evidence_production_requested": True,
        "repo_root": str(repo),
        "worktree_path": str(worktree),
        "operation_cwd": str(worktree),
        "required_checks": [
            {
                "name": "pytest",
                "argv": [
                    "python",
                    "-m",
                    "pytest",
                    "modules/communication/moltbot_bridge/tests/"
                    "test_reddog_main_resident_queue_serial_loop_bootstrap.py",
                    "-q",
                ],
                "timeout_s": 30,
            }
        ],
    }


def _artifact_generation_request(worktree: Path) -> dict[str, object]:
    return {
        "explicit_artifact_generation_requested": True,
        "work_order_id": WORK_ORDER_ID,
        "slice_name": "REDDOG_TEST_SLICE_PHASE1",
        "task_summary": "Generate one bounded pilot README artifact.",
        "planned_artifacts": [PILOT_ARTIFACT],
        "evidence_context": "The resident queue pilot is allowed to create only the README fixture.",
        "worktree_path": str(worktree),
        "holoindex_evidence": {
            "index_gap_detected": False,
            "retrieval_quality": "HIGH",
            "holoindex_freshness_receipt_digest": _digest("b"),
        },
        "signed_authority": {
            "accepted": True,
            "signature_gate_digest": _digest("9"),
        },
        "signed_receipt_chain": {
            "accepted": True,
            "terminal_receipt_hash": _digest("a"),
        },
        "timeout_seconds": 30,
    }


def _draft_pr_publish_request(worktree_path: Path) -> dict[str, object]:
    return {
        "work_order_id": WORK_ORDER_ID,
        "pre_publish_branch_head_sha": "a" * 40,
        "branch_name": "feat/reddog-resident-queue-paccess-pilot",
        "base_branch": "main",
        "pr_title": "feat(reddog): resident queue paccess pilot",
        "pr_body": "Verified by WRE autonomous slice verifier.",
        "worktree_path": str(worktree_path),
        "draft_pr_only": True,
        "mark_ready": False,
        "merge": False,
    }


def _draft_pr_publish_plan() -> dict[str, object]:
    return {
        "branch_name": "feat/reddog-resident-queue-paccess-pilot",
        "base_branch": "main",
        "pr_title": "feat(reddog): resident queue paccess pilot",
        "pr_body": "Verified by WRE autonomous slice verifier.",
        "draft_pr_only": True,
        "mark_ready": False,
        "merge": False,
    }


def _outcome_ratchet_request(
    verification_result: Mapping[str, object] | None = None,
) -> dict[str, object]:
    verifier_result = dict(
        verification_result or verify_autonomous_slice_runtime(_slice_verifier_request()).to_dict()
    )
    verifier_receipt = verifier_result["receipt"]
    return {
        "work_order_id": WORK_ORDER_ID,
        "slice_name": verifier_receipt["slice_name"],
        "outcome_status": "accepted",
        "request_receipt": {
            "request_id": "resident-queue-request-1",
            "principal_id": "012",
            "work_focus_digest": _digest("c"),
        },
        "execution_receipts": [
            {"step": "worktree_created", "receipt_id": _digest("d")},
            {"step": "bounded_worker_pilot", "receipt_id": _digest("e")},
            {"step": "draft_pr_published", "receipt_id": "pending-publish-receipt"},
        ],
        "verification_result": verifier_result,
        "publish_result": {
            "accepted": False,
            "decision": "VERIFIED_DRAFT_PR_PUBLISH_REJECT",
            "receipt": {},
        },
        "cost_receipt": {
            "total_tokens": 1234,
            "estimated_cost_usd": 0.12,
        },
        "latency_receipt": {
            "wall_time_ms": 1000,
            "queue_time_ms": 10,
        },
        "acceptance_receipt": {
            "accepted": True,
            "reason": "queue verifier and draft PR publish accepted",
        },
        "failure_receipt": None,
        "holoindex_evidence": {
            "index_gap_detected": False,
            "holoindex_freshness_receipt_digest": _digest("f"),
        },
        "enable_pattern_memory_write": False,
    }


def _held_out_gate_request(
    verification_result: Mapping[str, object] | None = None,
) -> dict[str, object]:
    verifier_result = dict(
        verification_result or verify_autonomous_slice_runtime(_slice_verifier_request()).to_dict()
    )
    verifier_receipt = verifier_result["receipt"]
    head_sha = str(verifier_receipt["head_sha"])
    return {
        "work_order_id": WORK_ORDER_ID,
        "slice_name": verifier_receipt["slice_name"],
        "worker_id": verifier_receipt["worker_id"],
        "enable_pattern_memory_admission": True,
        "improvement_job": {
            "job_id": "imp_resident_queue_heldout_1234",
            "finding_id": "resident-heldout-1",
            "improvement_type": "resident_queue_bootstrap",
            "status": "pending",
            "dry_run": True,
        },
        "verification_result": verifier_result,
        "held_out_regression": {
            "suite_id": "heldout-resident-queue-001",
            "is_held_out": True,
            "independent": True,
            "generated_by_author": False,
            "evidence_author_id": verifier_receipt["verifier_id"],
            "passed": True,
            "test_count": 12,
            "failure_count": 0,
            "suite_digest": _digest("1"),
            "baseline_digest": _digest("2"),
            "candidate_digest": _digest("3"),
            "candidate_head_sha": head_sha,
        },
        "holoindex_evidence": {
            "index_gap_detected": False,
            "holoindex_freshness_receipt_digest": _digest("4"),
        },
    }


def _pattern_memory_admission_request() -> dict[str, object]:
    return {
        "work_order_id": WORK_ORDER_ID,
        "admission_metadata": {
            "source": "resident_queue_bootstrap",
            "retention_policy": "verified_recursive_improvement_only",
        },
    }


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


class _FakeWorktreeRunner:
    def __init__(self, *, ok: bool = True) -> None:
        self.ok = ok
        self.calls: list[tuple[str, str, str | None, str | None]] = []

    def create_worktree(self, *, worktree_path: Path, branch_name: str, base_ref: str):
        self.calls.append(("create_worktree", str(worktree_path), branch_name, base_ref))
        if self.ok:
            Path(worktree_path).mkdir(parents=True, exist_ok=True)
        return {"ok": self.ok, "returncode": 0 if self.ok else 1, "stdout": "", "stderr": ""}

    def cleanup_worktree(self, *, worktree_path: Path):
        self.calls.append(("cleanup_worktree", str(worktree_path), None, None))
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}


class _FakeEvidenceRunner:
    def __init__(self, *, head: str = "a" * 40) -> None:
        self.head = head
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv, *, cwd: Path, timeout_s: int) -> CommandResult:
        _ = (cwd, timeout_s)
        argv_tuple = tuple(argv)
        self.calls.append(argv_tuple)
        if argv_tuple == ("git", "rev-parse", "HEAD"):
            return CommandResult(returncode=0, stdout=self.head + "\n")
        if argv_tuple[:3] == ("git", "diff", "--name-only"):
            return CommandResult(returncode=0, stdout=PILOT_ARTIFACT + "\n")
        if argv_tuple[:3] == ("git", "diff", "--unified=0"):
            return CommandResult(
                returncode=0,
                stdout=(
                    f"diff --git a/{PILOT_ARTIFACT} b/{PILOT_ARTIFACT}\n"
                    f"+++ b/{PILOT_ARTIFACT}\n"
                    "+resident queue produced independent evidence\n"
                ),
            )
        return CommandResult(returncode=0, stdout="ok\n")


class _FakeArtifactGenerator:
    def __init__(self, *, content: str = "# generated by resident queue\n") -> None:
        self.content = content
        self.calls: list[dict[str, object]] = []

    def generate_artifacts(
        self,
        *,
        prompt: str,
        context: str,
        binding: Mapping[str, object],
        timeout_seconds: int,
    ) -> ArtifactGenerationModelResult:
        self.calls.append(
            {
                "prompt": prompt,
                "context": context,
                "binding": dict(binding),
                "timeout_seconds": timeout_seconds,
            }
        )
        return ArtifactGenerationModelResult(
            ok=True,
            status="MODEL_OK",
            artifact_contents={PILOT_ARTIFACT: self.content},
            model_receipt_id="artifact-model-receipt-1",
            model_result_digest=_digest("e"),
            made_network_call=False,
            rejection_reasons=(),
        )


class _FakePatternMemoryAdmissionSink:
    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []

    def store_verified_outcome(self, record: Mapping[str, object]) -> str:
        self.records.append(dict(record))
        return "pattern-memory-record-1"


class _FakeWorkerDispatchTaskWriter:
    def __init__(self, *, accepted: bool = True) -> None:
        self.accepted = accepted
        self.calls: list[dict[str, object]] = []

    def enqueue_signed_worker_dispatch_tasks(self, tasks, receipt):
        task_ids = [task.task_id for task in tasks]
        self.calls.append(
            {
                "task_ids": task_ids,
                "receipt_id": receipt.receipt_id,
            }
        )
        return {
            "ok": self.accepted,
            "created_task_ids": task_ids,
            "receipt_id": receipt.receipt_id,
        }


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


def _run_bootstrap_to_verified_outcome_ratchet(tmp_path: Path) -> dict[str, object]:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(**pilot_overrides)
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {WORK_ORDER_ID: work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    worktree_runner = _FakeWorktreeRunner()
    worktree = _pilot_worktree_path(repo, work_order)
    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        pilot_payloads["artifact_contents"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )
    verifier = _write_runtime_json(
        tmp_path,
        "verifier_request.json",
        _slice_verifier_request(),
    )
    publish_request = _write_runtime_json(
        tmp_path,
        "publish_request.json",
        _draft_pr_publish_request(worktree),
    )
    outcome_store = tmp_path / "runtime" / "outcomes" / "ratchet.jsonl"
    draft_pr_runner = FakeDraftPrRunner()

    verifier_run = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        generic_writer_dryrun_result_path=generic_writer,
        governed_shell_dryrun_result_path=governed_shell,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        verifier_request_path=verifier,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=worktree_runner,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=11,
    )
    assert verifier_run.accepted is True
    verifier_stage = json.loads(chain.read_text(encoding="utf-8"))["stage_results"]["slice_verifier"]
    ratchet_request = _write_runtime_json(
        tmp_path,
        "ratchet_request.json",
        _outcome_ratchet_request(verifier_stage["verifier_result"]),
    )

    ratchet_run = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        generic_writer_dryrun_result_path=generic_writer,
        governed_shell_dryrun_result_path=governed_shell,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        verifier_request_path=verifier,
        publish_request_path=publish_request,
        ratchet_request_path=ratchet_request,
        outcome_ratchet_store_path=outcome_store,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=worktree_runner,
        draft_pr_runner=draft_pr_runner,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=2,
    )
    assert ratchet_run.accepted is True
    stored = json.loads(chain.read_text(encoding="utf-8"))
    assert stored["stage_results"]["verified_outcome_ratchet"]["decision"] == (
        "QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT"
    )

    return {
        "repo": repo,
        "state": state,
        "profile": profile,
        "chain": chain,
        "verifier_stage": verifier_stage,
    }


def _run_bootstrap_to_held_out_regression_gate(tmp_path: Path) -> dict[str, object]:
    ctx = _run_bootstrap_to_verified_outcome_ratchet(tmp_path)
    verifier_stage = ctx["verifier_stage"]
    held_out_request = _write_runtime_json(
        tmp_path,
        "held_out_gate_request.json",
        _held_out_gate_request(verifier_stage["verifier_result"]),
    )
    gate_run = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=ctx["repo"],
        work_state_path=ctx["state"],
        chain_results_path=ctx["chain"],
        authority_profile_path=ctx["profile"],
        held_out_gate_request_path=held_out_request,
        now_iso=NOW,
        requested_queue_item_id="queue-1",
        max_steps=1,
    )
    assert gate_run.accepted is True
    stored = json.loads(Path(ctx["chain"]).read_text(encoding="utf-8"))
    assert stored["stage_results"]["held_out_regression_gate"]["decision"] == (
        "QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT"
    )
    return ctx


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
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
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
    assert result.next_action == "RUN_QUEUE_SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN"
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
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=8,
    )

    assert result.accepted is True
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED
    assert result.steps_run == 8
    assert result.dispatched_stages == (
        "authority_request",
        "authority_runtime",
        "authority_verification",
        "worker_dispatch_dryrun",
            "worker_dispatch_runtime",
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


def test_bootstrap_serial_loop_materializes_work_order_from_authority_profile(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            required_tests=["pytest modules/communication/moltbot_bridge/tests"],
        ),
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
        work_order_materializer_mode="authority_profile",
        valve_environment_path=valve_env,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=8,
    )

    assert result.accepted is True
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED
    assert result.steps_run == 8
    assert result.dispatched_stages == (
        "authority_request",
        "authority_runtime",
        "authority_verification",
        "worker_dispatch_dryrun",
            "worker_dispatch_runtime",
            "work_order_invocation",
        "executor_plan",
        "execution_valve",
    )
    assert result.next_action == "RUN_QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE"

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage_results = stored["stage_results"]
    assert stage_results["work_order_invocation"]["decision"] == "QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT"
    invocation = stage_results["work_order_invocation"]["invocation_result"]
    assert invocation["work_order_id"] == WORK_ORDER_ID
    assert invocation["receipt_digest"]
    assert invocation["policy_gate_receipt_digest"]
    assert invocation["no_execution_performed"] is True
    assert stage_results["executor_plan"]["decision"] == "QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT"
    assert stage_results["execution_valve"]["decision"] == "QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT"
    assert "work_orders.json" not in json.dumps(stored, sort_keys=True)


def test_bootstrap_serial_loop_creates_worktree_only_with_explicit_runner(
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
    runner = _FakeWorktreeRunner()

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
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=runner,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=9,
    )

    assert result.accepted is True
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED
    assert result.steps_run == 9
    assert result.dispatched_stages == (
        "authority_request",
        "authority_runtime",
        "authority_verification",
        "worker_dispatch_dryrun",
            "worker_dispatch_runtime",
            "work_order_invocation",
        "executor_plan",
        "execution_valve",
        "worktree_create",
    )
    assert result.next_action == "RUN_QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE"
    assert result.no_worktree_created is False
    assert result.no_repo_mutation_performed is False
    assert result.no_worker_spawn_performed is True
    assert result.no_shell_command_executed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_pr_created is True
    assert [call[0] for call in runner.calls] == ["create_worktree"]

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["worktree_create"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT"
    assert stage["worktree_create_result"]["decision"] == "WORKTREE_CREATE_ACCEPT"
    assert stage["worktree_create_result"]["no_task_execution_performed"] is True
    assert stage["worktree_create_result"]["no_file_edit_performed"] is True
    assert stage["no_openclaw_enqueue_performed"] is True
    assert stage["no_hermes_dispatch_performed"] is True
    assert Path(stage["worktree_create_result"]["worktree_path"]).exists()
    assert "012-sovereign-worktree-token" not in json.dumps(stored, sort_keys=True)


def test_bootstrap_serial_loop_reaches_bounded_worker_pilot_with_explicit_artifacts(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(**pilot_overrides)
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {WORK_ORDER_ID: work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    runner = _FakeWorktreeRunner()
    worktree = _pilot_worktree_path(repo, work_order)
    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        pilot_payloads["artifact_contents"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        generic_writer_dryrun_result_path=generic_writer,
        governed_shell_dryrun_result_path=governed_shell,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=runner,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=10,
    )

    assert result.accepted is True
    assert result.steps_run == 10
    assert result.dispatched_stages == (
        "authority_request",
        "authority_runtime",
        "authority_verification",
        "worker_dispatch_dryrun",
            "worker_dispatch_runtime",
            "work_order_invocation",
        "executor_plan",
        "execution_valve",
        "worktree_create",
        "bounded_worker_pilot",
    )
    assert result.next_action == "RUN_QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE"
    assert result.no_worktree_created is False
    assert result.no_bounded_task_execution_performed is False
    assert result.no_bounded_file_edit_performed is False
    assert result.no_shell_command_executed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_pr_created is True
    assert result.no_holoindex_reindex_performed is True

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["bounded_worker_pilot"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT"
    assert stage["bounded_task_execution_performed"] is True
    assert stage["bounded_file_edit_performed"] is True
    assert stage["shell_command_executed"] is False
    assert stage["openclaw_enqueue_performed"] is False
    assert stage["hermes_dispatch_performed"] is False
    assert stage["holoindex_reindex_performed"] is False
    assert (worktree / PILOT_ARTIFACT).read_text(encoding="utf-8").startswith(
        "# Resident Queue Pilot"
    )
    assert not (repo / PILOT_ARTIFACT).exists()
    assert "012-sovereign-worktree-token" not in json.dumps(stored, sort_keys=True)


def test_bootstrap_serial_loop_binds_pilot_dryruns_from_resident_queue_state(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(
        **{
            **pilot_overrides,
            "bounded_worker_plan": _pilot_bounded_worker_plan(),
        }
    )
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {WORK_ORDER_ID: work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    runner = _FakeWorktreeRunner()
    worktree = _pilot_worktree_path(repo, work_order)
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        {
            PILOT_ARTIFACT: (
                "# Resident Queue Pilot\n\n"
                "The dry-run planner receipts were bound from resident queue state.\n"
            )
        },
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        {
            "index_gap_detected": False,
            "retrieval_quality": "HIGH",
            "holoindex_freshness_receipt_digest": "sha256:holo-fresh",
        },
    )

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        pilot_dryrun_binding_enabled=True,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=runner,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=10,
    )

    assert result.accepted is True
    assert result.steps_run == 10
    assert result.dispatched_stages == (
        "authority_request",
        "authority_runtime",
        "authority_verification",
        "worker_dispatch_dryrun",
            "worker_dispatch_runtime",
            "work_order_invocation",
        "executor_plan",
        "execution_valve",
        "worktree_create",
        "bounded_worker_pilot",
    )
    assert result.next_action == "RUN_QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE"
    assert result.no_worktree_created is False
    assert result.no_bounded_task_execution_performed is False
    assert result.no_bounded_file_edit_performed is False
    assert result.no_shell_command_executed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_pr_created is True
    assert result.no_holoindex_reindex_performed is True

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["bounded_worker_pilot"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT"
    binding = stage["pilot_dryrun_binding_result"]
    assert binding["accepted"] is True
    assert binding["generic_writer_dryrun_result"]["accepted"] is True
    assert binding["governed_shell_dryrun_result"]["accepted"] is True
    assert stage["shell_command_executed"] is False
    assert (worktree / PILOT_ARTIFACT).read_text(encoding="utf-8").startswith(
        "# Resident Queue Pilot"
    )
    assert not (repo / PILOT_ARTIFACT).exists()
    assert "012-sovereign-worktree-token" not in json.dumps(stored, sort_keys=True)


def test_bootstrap_serial_loop_binds_slice_verifier_request_from_queue_state(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(
        **{
            **pilot_overrides,
            "bounded_worker_plan": _pilot_bounded_worker_plan(),
            "slice_verifier_plan": _slice_verifier_plan(),
        }
    )
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {WORK_ORDER_ID: work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    runner = _FakeWorktreeRunner()
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        {
            PILOT_ARTIFACT: (
                "# Resident Queue Pilot\n\n"
                "The verifier request was bound from resident queue state.\n"
            )
        },
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        {
            "index_gap_detected": False,
            "retrieval_quality": "HIGH",
            "holoindex_freshness_receipt_digest": _digest("b"),
        },
    )
    evidence_runner = _FakeEvidenceRunner()

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        pilot_dryrun_binding_enabled=True,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=runner,
        evidence_command_runner=evidence_runner,
        slice_verifier_request_binding_enabled=True,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=11,
    )

    assert result.accepted is True
    assert result.steps_run == 11
    assert result.dispatched_stages == (
        "authority_request",
        "authority_runtime",
        "authority_verification",
        "worker_dispatch_dryrun",
            "worker_dispatch_runtime",
            "work_order_invocation",
        "executor_plan",
        "execution_valve",
        "worktree_create",
        "bounded_worker_pilot",
        "slice_verifier",
    )
    assert result.next_action == "RUN_QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE"
    assert result.no_worktree_created is False
    assert result.no_bounded_task_execution_performed is False
    assert result.no_bounded_file_edit_performed is False
    assert result.no_shell_command_executed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_pr_created is True
    assert result.no_holoindex_reindex_performed is True

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["slice_verifier"]
    binding = stage["slice_verifier_request_binding_result"]
    assert binding["accepted"] is True
    assert binding["evidence_producer_request"]["expected_changed_paths"] == [PILOT_ARTIFACT]
    assert binding["evidence_producer_request"]["worktree_receipt"]["receipt_id"]
    assert stage["evidence_producer_result"]["decision"] == EVIDENCE_PRODUCER_ACCEPT
    assert stage["verifier_result"]["decision"] == AUTONOMOUS_SLICE_VERIFIER_ACCEPT
    assert ("git", "rev-parse", "HEAD") in evidence_runner.calls
    assert "012-sovereign-worktree-token" not in json.dumps(stored, sort_keys=True)


def test_bootstrap_serial_loop_reaches_slice_verifier_with_explicit_request(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(**pilot_overrides)
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {WORK_ORDER_ID: work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    runner = _FakeWorktreeRunner()
    worktree = _pilot_worktree_path(repo, work_order)
    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        pilot_payloads["artifact_contents"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )
    verifier = _write_runtime_json(
        tmp_path,
        "verifier_request.json",
        _slice_verifier_request(),
    )

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        generic_writer_dryrun_result_path=generic_writer,
        governed_shell_dryrun_result_path=governed_shell,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        verifier_request_path=verifier,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=runner,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=11,
    )

    assert result.accepted is True
    assert result.steps_run == 11
    assert result.dispatched_stages == (
        "authority_request",
        "authority_runtime",
        "authority_verification",
        "worker_dispatch_dryrun",
            "worker_dispatch_runtime",
            "work_order_invocation",
        "executor_plan",
        "execution_valve",
        "worktree_create",
        "bounded_worker_pilot",
        "slice_verifier",
    )
    assert result.next_action == "RUN_QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE"
    assert result.no_slice_verification_performed is False
    assert result.no_shell_command_executed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_pr_created is True
    assert result.no_holoindex_reindex_performed is True

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["slice_verifier"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT"
    assert stage["verifier_result"]["decision"] == AUTONOMOUS_SLICE_VERIFIER_ACCEPT
    assert stage["verifier_result"]["receipt"]["changed_paths"] == [PILOT_ARTIFACT]
    assert stage["no_command_execution_performed"] is True
    assert stage["no_github_call_performed"] is True
    assert stage["no_pr_publish_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_pattern_memory_write_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True
    assert (worktree / PILOT_ARTIFACT).exists()
    assert not (repo / PILOT_ARTIFACT).exists()
    assert "012-sovereign-worktree-token" not in json.dumps(stored, sort_keys=True)


def test_bootstrap_serial_loop_generates_artifacts_before_bounded_worker_pilot(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(
        **pilot_overrides,
        bounded_worker_plan=_pilot_bounded_worker_plan(),
    )
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {WORK_ORDER_ID: work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    runner = _FakeWorktreeRunner()
    artifact_generator = _FakeArtifactGenerator(content="# generated by bootstrap\n")
    worktree = _pilot_worktree_path(repo, work_order)
    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        generic_writer_dryrun_result_path=generic_writer,
        governed_shell_dryrun_result_path=governed_shell,
        artifact_generation_request_binding_enabled=True,
        holoindex_evidence_path=holoindex,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=runner,
        artifact_generator=artifact_generator,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=10,
    )

    assert result.accepted is True, result.rejection_reasons
    assert result.dispatched_stages[-1] == "bounded_worker_pilot"
    assert artifact_generator.calls
    assert artifact_generator.calls[0]["binding"]["work_order_id"] == WORK_ORDER_ID
    context = json.loads(str(artifact_generator.calls[0]["context"]))
    assert context["holoindex_evidence"]["retrieval_quality"] == "HIGH"
    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["bounded_worker_pilot"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT"
    assert stage["artifact_generation_result"]["accepted"] is True
    assert (worktree / PILOT_ARTIFACT).read_text(encoding="utf-8") == "# generated by bootstrap\n"
    assert not (repo / PILOT_ARTIFACT).exists()


def test_bootstrap_serial_loop_produces_independent_evidence_for_slice_verifier(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(**pilot_overrides)
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {WORK_ORDER_ID: work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    worktree_runner = _FakeWorktreeRunner()
    evidence_runner = _FakeEvidenceRunner()
    worktree = _pilot_worktree_path(repo, work_order)
    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        pilot_payloads["artifact_contents"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )
    evidence_request = _write_runtime_json(
        tmp_path,
        "evidence_producer_request.json",
        _evidence_producer_request(repo, worktree),
    )

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        generic_writer_dryrun_result_path=generic_writer,
        governed_shell_dryrun_result_path=governed_shell,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        evidence_producer_request_path=evidence_request,
        evidence_command_runner=evidence_runner,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=worktree_runner,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=11,
    )

    assert result.accepted is True
    assert result.steps_run == 11
    assert result.dispatched_stages[-1] == "slice_verifier"
    assert result.no_slice_verification_performed is False
    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["slice_verifier"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT"
    assert stage["evidence_producer_result"]["decision"] == EVIDENCE_PRODUCER_ACCEPT
    assert stage["verifier_result"]["decision"] == AUTONOMOUS_SLICE_VERIFIER_ACCEPT
    assert stage["verifier_result"]["receipt"]["changed_paths"] == [PILOT_ARTIFACT]
    assert stage["bounded_evidence_command_execution_performed"] is True
    assert stage["no_command_execution_performed"] is False
    assert stage["no_shell_command_executed"] is True
    assert stage["no_github_call_performed"] is True
    assert stage["no_pr_publish_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True
    assert ("git", "rev-parse", "HEAD") in evidence_runner.calls
    assert (worktree / PILOT_ARTIFACT).exists()
    assert not (repo / PILOT_ARTIFACT).exists()
    assert "012-sovereign-worktree-token" not in json.dumps(stored, sort_keys=True)


def test_bootstrap_serial_loop_reaches_verified_draft_pr_publish_with_injected_runner(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(**pilot_overrides)
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {WORK_ORDER_ID: work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    worktree_runner = _FakeWorktreeRunner()
    worktree = _pilot_worktree_path(repo, work_order)
    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        pilot_payloads["artifact_contents"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )
    verifier = _write_runtime_json(
        tmp_path,
        "verifier_request.json",
        _slice_verifier_request(),
    )
    publish_request = _write_runtime_json(
        tmp_path,
        "publish_request.json",
        _draft_pr_publish_request(worktree),
    )
    draft_pr_runner = FakeDraftPrRunner()

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        generic_writer_dryrun_result_path=generic_writer,
        governed_shell_dryrun_result_path=governed_shell,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        verifier_request_path=verifier,
        publish_request_path=publish_request,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=worktree_runner,
        draft_pr_runner=draft_pr_runner,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=12,
    )

    assert result.accepted is True
    assert result.steps_run == 12
    assert result.dispatched_stages == (
        "authority_request",
        "authority_runtime",
        "authority_verification",
        "worker_dispatch_dryrun",
            "worker_dispatch_runtime",
            "work_order_invocation",
        "executor_plan",
        "execution_valve",
        "worktree_create",
        "bounded_worker_pilot",
        "slice_verifier",
        "verified_draft_pr_publish",
    )
    assert result.next_action == "RUN_QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE"
    assert result.no_slice_verification_performed is False
    assert result.no_verified_draft_pr_publish_performed is False
    assert result.no_pr_created is False
    assert result.no_shell_command_executed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_holoindex_reindex_performed is True

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["verified_draft_pr_publish"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT"
    assert stage["publish_result"]["decision"] == "VERIFIED_DRAFT_PR_PUBLISH_ACCEPT"
    assert stage["publish_result"]["receipt"]["draft_pr_url"].endswith("/pull/2000")
    assert stage["no_ready_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_pattern_memory_write_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True
    assert [call[0] for call in draft_pr_runner.calls] == ["push_branch", "create_draft_pr"]
    assert (worktree / PILOT_ARTIFACT).exists()
    assert not (repo / PILOT_ARTIFACT).exists()
    assert "012-sovereign-worktree-token" not in json.dumps(stored, sort_keys=True)


def test_bootstrap_serial_loop_binds_draft_pr_publish_request_from_queue_state(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(
        **{
            **pilot_overrides,
            "bounded_worker_plan": _pilot_bounded_worker_plan(),
            "slice_verifier_plan": _slice_verifier_plan(),
            "draft_pr_publish_plan": _draft_pr_publish_plan(),
        }
    )
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {WORK_ORDER_ID: work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    worktree_runner = _FakeWorktreeRunner()
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        {
            PILOT_ARTIFACT: (
                "# Resident Queue Pilot\n\n"
                "The draft PR request was bound from resident queue state.\n"
            )
        },
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        {
            "index_gap_detected": False,
            "retrieval_quality": "HIGH",
            "holoindex_freshness_receipt_digest": _digest("b"),
        },
    )
    evidence_runner = _FakeEvidenceRunner()
    draft_pr_runner = FakeDraftPrRunner()

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        pilot_dryrun_binding_enabled=True,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=worktree_runner,
        evidence_command_runner=evidence_runner,
        slice_verifier_request_binding_enabled=True,
        draft_pr_runner=draft_pr_runner,
        draft_pr_publish_request_binding_enabled=True,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=12,
    )

    assert result.accepted is True
    assert result.steps_run == 12
    assert result.dispatched_stages == (
        "authority_request",
        "authority_runtime",
        "authority_verification",
        "worker_dispatch_dryrun",
            "worker_dispatch_runtime",
            "work_order_invocation",
        "executor_plan",
        "execution_valve",
        "worktree_create",
        "bounded_worker_pilot",
        "slice_verifier",
        "verified_draft_pr_publish",
    )
    assert result.next_action == "RUN_QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE"
    assert result.no_slice_verification_performed is False
    assert result.no_verified_draft_pr_publish_performed is False
    assert result.no_pr_created is False
    assert result.no_shell_command_executed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_holoindex_reindex_performed is True

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["verified_draft_pr_publish"]
    binding = stage["draft_pr_publish_request_binding_result"]
    assert binding["accepted"] is True
    assert binding["publish_request"]["branch_name"] == "feat/reddog-resident-queue-paccess-pilot"
    assert binding["publish_request"]["draft_pr_only"] is True
    assert binding["publish_request"]["mark_ready"] is False
    assert binding["publish_request"]["merge"] is False
    assert stage["decision"] == "QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_ACCEPT"
    assert stage["publish_result"]["decision"] == "VERIFIED_DRAFT_PR_PUBLISH_ACCEPT"
    assert stage["no_ready_performed"] is True
    assert stage["no_merge_performed"] is True
    assert [call[0] for call in draft_pr_runner.calls] == ["push_branch", "create_draft_pr"]
    assert ("git", "rev-parse", "HEAD") in evidence_runner.calls
    assert "012-sovereign-worktree-token" not in json.dumps(stored, sort_keys=True)


def test_bootstrap_serial_loop_reaches_verified_outcome_ratchet_with_jsonl_store(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(**pilot_overrides)
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {WORK_ORDER_ID: work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    worktree_runner = _FakeWorktreeRunner()
    worktree = _pilot_worktree_path(repo, work_order)
    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        pilot_payloads["artifact_contents"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )
    verifier = _write_runtime_json(
        tmp_path,
        "verifier_request.json",
        _slice_verifier_request(),
    )
    publish_request = _write_runtime_json(
        tmp_path,
        "publish_request.json",
        _draft_pr_publish_request(worktree),
    )
    outcome_store = tmp_path / "runtime" / "outcomes" / "ratchet.jsonl"
    draft_pr_runner = FakeDraftPrRunner()

    verifier_run = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        generic_writer_dryrun_result_path=generic_writer,
        governed_shell_dryrun_result_path=governed_shell,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        verifier_request_path=verifier,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=worktree_runner,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=11,
    )
    assert verifier_run.accepted is True
    verifier_stage = json.loads(chain.read_text(encoding="utf-8"))["stage_results"]["slice_verifier"]
    ratchet_request = _write_runtime_json(
        tmp_path,
        "ratchet_request.json",
        _outcome_ratchet_request(verifier_stage["verifier_result"]),
    )

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        generic_writer_dryrun_result_path=generic_writer,
        governed_shell_dryrun_result_path=governed_shell,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        verifier_request_path=verifier,
        publish_request_path=publish_request,
        ratchet_request_path=ratchet_request,
        outcome_ratchet_store_path=outcome_store,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=worktree_runner,
        draft_pr_runner=draft_pr_runner,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=2,
    )

    assert result.accepted is True
    assert result.steps_run == 2
    assert result.dispatched_stages == (
        "verified_draft_pr_publish",
        "verified_outcome_ratchet",
    )
    assert result.next_action == "RUN_QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE"
    assert result.no_verified_draft_pr_publish_performed is False
    assert result.no_verified_outcome_ratchet_performed is False
    assert result.no_pr_created is False
    assert result.no_pattern_memory_client_created is True
    assert result.no_reward_settlement_performed is True
    assert result.no_holoindex_reindex_performed is True

    stored = json.loads(chain.read_text(encoding="utf-8"))
    stage = stored["stage_results"]["verified_outcome_ratchet"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_ACCEPT"
    assert stage["ratchet_result"]["decision"] == ratchet.OUTCOME_RATCHET_RECORDED
    receipt = stage["ratchet_result"]["receipt"]
    assert receipt["pattern_memory_eligible"] is True
    assert receipt["pattern_memory_write_performed"] is False
    assert stage["no_command_execution_performed"] is True
    assert stage["no_pr_publish_performed"] is True
    assert stage["no_ready_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True

    records = [
        json.loads(line)
        for line in outcome_store.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 1
    assert records[0]["ratchet_receipt"]["work_order_id"] == WORK_ORDER_ID
    assert records[0]["publish_result"]["decision"] == "VERIFIED_DRAFT_PR_PUBLISH_ACCEPT"
    assert not (repo / "runtime" / "outcomes" / "ratchet.jsonl").exists()


def test_bootstrap_serial_loop_reaches_held_out_regression_gate_with_request(
    tmp_path: Path,
) -> None:
    ctx = _run_bootstrap_to_verified_outcome_ratchet(tmp_path)
    verifier_stage = ctx["verifier_stage"]
    held_out_request = _write_runtime_json(
        tmp_path,
        "held_out_gate_request.json",
        _held_out_gate_request(verifier_stage["verifier_result"]),
    )

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=ctx["repo"],
        work_state_path=ctx["state"],
        chain_results_path=ctx["chain"],
        authority_profile_path=ctx["profile"],
        held_out_gate_request_path=held_out_request,
        now_iso=NOW,
        requested_queue_item_id="queue-1",
        max_steps=1,
    )

    assert result.accepted is True
    assert result.steps_run == 1
    assert result.dispatched_stages == ("held_out_regression_gate",)
    assert result.next_action == "RUN_QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE"
    assert result.no_held_out_regression_gate_performed is False
    assert result.no_verified_outcome_ratchet_performed is True
    assert result.no_pattern_memory_client_created is True
    assert result.no_reward_settlement_performed is True
    assert result.no_holoindex_reindex_performed is True

    stored = json.loads(Path(ctx["chain"]).read_text(encoding="utf-8"))
    stage = stored["stage_results"]["held_out_regression_gate"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_ACCEPT"
    assert (
        stage["gate_result"]["decision"]
        == "HELD_OUT_RECURSIVE_IMPROVEMENT_REGRESSION_GATE_ACCEPT"
    )
    assert stage["gate_result"]["receipt"]["no_pattern_memory_write_performed"] is True
    assert stage["no_command_execution_performed"] is True
    assert stage["no_test_execution_performed"] is True
    assert stage["no_pattern_memory_write_performed"] is True
    assert stage["no_pr_publish_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True


def test_bootstrap_serial_loop_fails_closed_at_held_out_without_gate_request(
    tmp_path: Path,
) -> None:
    ctx = _run_bootstrap_to_verified_outcome_ratchet(tmp_path)

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=ctx["repo"],
        work_state_path=ctx["state"],
        chain_results_path=ctx["chain"],
        authority_profile_path=ctx["profile"],
        now_iso=NOW,
        requested_queue_item_id="queue-1",
        max_steps=1,
    )

    assert result.accepted is False
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY
    assert result.steps_run == 0
    assert result.dispatched_stages == ()
    assert "FAIL_HANDLER_MISSING" in result.rejection_reasons
    assert "stage:held_out_regression_gate" in result.rejection_reasons
    assert result.no_held_out_regression_gate_performed is True
    assert result.no_pattern_memory_client_created is True


def test_bootstrap_serial_loop_reaches_pattern_memory_admission_with_injected_sink(
    tmp_path: Path,
) -> None:
    ctx = _run_bootstrap_to_held_out_regression_gate(tmp_path)
    admission_request = _write_runtime_json(
        tmp_path,
        "pattern_memory_admission_request.json",
        _pattern_memory_admission_request(),
    )
    sink = _FakePatternMemoryAdmissionSink()

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=ctx["repo"],
        work_state_path=ctx["state"],
        chain_results_path=ctx["chain"],
        authority_profile_path=ctx["profile"],
        admission_request_path=admission_request,
        pattern_memory_admission_sink=sink,
        now_iso=NOW,
        requested_queue_item_id="queue-1",
        max_steps=1,
    )

    assert result.accepted is True
    assert result.steps_run == 1
    assert result.dispatched_stages == ("pattern_memory_admission",)
    assert result.next_action == "STOP_QUEUE_CHAIN_COMPLETE"
    assert result.no_pattern_memory_admission_performed is False
    assert result.no_pattern_memory_write_performed is False
    assert result.no_pattern_memory_client_created is True
    assert result.no_reward_settlement_performed is True
    assert result.no_holoindex_reindex_performed is True

    stored = json.loads(Path(ctx["chain"]).read_text(encoding="utf-8"))
    stage = stored["stage_results"]["pattern_memory_admission"]
    assert stage["decision"] == "QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_ACCEPT"
    assert stage["pattern_memory_write_performed"] is True
    assert stage["receipt"]["pattern_memory_record_id"] == "pattern-memory-record-1"
    assert stage["no_command_execution_performed"] is True
    assert stage["no_pr_publish_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True
    assert len(sink.records) == 1
    assert sink.records[0]["record_type"] == "reddog_verified_recursive_improvement_outcome"
    assert sink.records[0]["work_order_id"] == WORK_ORDER_ID


def test_bootstrap_serial_loop_fails_closed_at_pattern_memory_without_injected_sink(
    tmp_path: Path,
) -> None:
    ctx = _run_bootstrap_to_held_out_regression_gate(tmp_path)
    admission_request = _write_runtime_json(
        tmp_path,
        "pattern_memory_admission_request.json",
        _pattern_memory_admission_request(),
    )

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=ctx["repo"],
        work_state_path=ctx["state"],
        chain_results_path=ctx["chain"],
        authority_profile_path=ctx["profile"],
        admission_request_path=admission_request,
        now_iso=NOW,
        requested_queue_item_id="queue-1",
        max_steps=1,
    )

    assert result.accepted is False
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY
    assert result.steps_run == 0
    assert result.dispatched_stages == ()
    assert "FAIL_HANDLER_MISSING" in result.rejection_reasons
    assert "stage:pattern_memory_admission" in result.rejection_reasons
    assert result.no_pattern_memory_admission_performed is True
    assert result.no_pattern_memory_write_performed is True
    assert result.no_pattern_memory_client_created is True


def test_bootstrap_serial_loop_fails_closed_at_bounded_worker_without_pilot_artifacts(
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
    runner = _FakeWorktreeRunner()

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
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=runner,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=10,
    )

    assert result.accepted is False
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY
    assert result.steps_run == 9
    assert "FAIL_HANDLER_MISSING" in result.rejection_reasons
    assert "stage:bounded_worker_pilot" in result.rejection_reasons
    assert result.no_worktree_created is False
    assert result.no_bounded_task_execution_performed is True
    assert result.no_bounded_file_edit_performed is True


def test_bootstrap_serial_loop_fails_closed_at_slice_verifier_without_request(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(**pilot_overrides)
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {WORK_ORDER_ID: work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    runner = _FakeWorktreeRunner()
    worktree = _pilot_worktree_path(repo, work_order)
    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        pilot_payloads["artifact_contents"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        generic_writer_dryrun_result_path=generic_writer,
        governed_shell_dryrun_result_path=governed_shell,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=runner,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=11,
    )

    assert result.accepted is False
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY
    assert result.steps_run == 10
    assert "FAIL_HANDLER_MISSING" in result.rejection_reasons
    assert "stage:slice_verifier" in result.rejection_reasons
    assert result.no_slice_verification_performed is True
    assert result.no_pr_created is True


def test_bootstrap_serial_loop_fails_closed_at_verified_draft_pr_publish_without_runner(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(**pilot_overrides)
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {WORK_ORDER_ID: work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    runner = _FakeWorktreeRunner()
    worktree = _pilot_worktree_path(repo, work_order)
    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        pilot_payloads["artifact_contents"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )
    verifier = _write_runtime_json(
        tmp_path,
        "verifier_request.json",
        _slice_verifier_request(),
    )
    publish_request = _write_runtime_json(
        tmp_path,
        "publish_request.json",
        _draft_pr_publish_request(worktree),
    )

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        generic_writer_dryrun_result_path=generic_writer,
        governed_shell_dryrun_result_path=governed_shell,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        verifier_request_path=verifier,
        publish_request_path=publish_request,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=runner,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=12,
    )

    assert result.accepted is False
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY
    assert result.steps_run == 11
    assert "FAIL_HANDLER_MISSING" in result.rejection_reasons
    assert "stage:verified_draft_pr_publish" in result.rejection_reasons
    assert result.no_slice_verification_performed is False
    assert result.no_verified_draft_pr_publish_performed is True
    assert result.no_pr_created is True


def test_bootstrap_serial_loop_fails_closed_at_verified_outcome_ratchet_without_store(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    principal_public, reddog_public, connector = _ed25519_signing_material()
    pilot_overrides = _pilot_path_overrides()
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(
        tmp_path,
        "profile.json",
        _profile(
            principal_public_key=principal_public,
            reddog_public_key=reddog_public,
            requested_operation=PILOT_OPERATION,
            allowed_paths=_pilot_allowed_paths(),
            denied_paths=pilot_overrides["denied_paths"],
        ),
    )
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals(principal_public))
    work_order = _work_order(**pilot_overrides)
    work_orders = _write_runtime_json(
        tmp_path,
        "work_orders.json",
        {"work_orders": {WORK_ORDER_ID: work_order}},
    )
    valve_env = _write_runtime_json(tmp_path, "valve_env.json", _valve_environment())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"
    socket_path = tmp_path / "runtime" / "signer.sock"
    worktree_runner = _FakeWorktreeRunner()
    worktree = _pilot_worktree_path(repo, work_order)
    pilot_payloads = _pilot_payloads(repo, worktree, work_order)
    generic_writer = _write_runtime_json(
        tmp_path,
        "generic_writer.json",
        pilot_payloads["generic_writer_dryrun_result"],
    )
    governed_shell = _write_runtime_json(
        tmp_path,
        "governed_shell.json",
        pilot_payloads["governed_shell_dryrun_result"],
    )
    artifacts = _write_runtime_json(
        tmp_path,
        "artifact_contents.json",
        pilot_payloads["artifact_contents"],
    )
    holoindex = _write_runtime_json(
        tmp_path,
        "holoindex_evidence.json",
        pilot_payloads["holoindex_evidence"],
    )
    verifier = _write_runtime_json(
        tmp_path,
        "verifier_request.json",
        _slice_verifier_request(),
    )
    publish_request = _write_runtime_json(
        tmp_path,
        "publish_request.json",
        _draft_pr_publish_request(worktree),
    )
    draft_pr_runner = FakeDraftPrRunner()

    verifier_run = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        generic_writer_dryrun_result_path=generic_writer,
        governed_shell_dryrun_result_path=governed_shell,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        verifier_request_path=verifier,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=worktree_runner,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=11,
    )
    assert verifier_run.accepted is True
    verifier_stage = json.loads(chain.read_text(encoding="utf-8"))["stage_results"]["slice_verifier"]
    ratchet_request = _write_runtime_json(
        tmp_path,
        "ratchet_request.json",
        _outcome_ratchet_request(verifier_stage["verifier_result"]),
    )

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        work_orders_path=work_orders,
        valve_environment_path=valve_env,
        generic_writer_dryrun_result_path=generic_writer,
        governed_shell_dryrun_result_path=governed_shell,
        artifact_contents_path=artifacts,
        holoindex_evidence_path=holoindex,
        verifier_request_path=verifier,
        publish_request_path=publish_request,
        ratchet_request_path=ratchet_request,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        worktree_runner=worktree_runner,
        draft_pr_runner=draft_pr_runner,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=2,
    )

    assert result.accepted is False
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY
    assert result.steps_run == 1
    assert "FAIL_HANDLER_MISSING" in result.rejection_reasons
    assert "stage:verified_outcome_ratchet" in result.rejection_reasons
    assert result.no_verified_draft_pr_publish_performed is False
    assert result.no_verified_outcome_ratchet_performed is True
    assert result.no_pr_created is False
    assert result.no_pattern_memory_client_created is True


def test_bootstrap_serial_loop_fails_closed_at_worktree_without_runner(
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
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=9,
    )

    assert result.accepted is False
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY
    assert result.steps_run == 8
    assert result.dispatched_stages == (
        "authority_request",
        "authority_runtime",
        "authority_verification",
        "worker_dispatch_dryrun",
            "worker_dispatch_runtime",
            "work_order_invocation",
        "executor_plan",
        "execution_valve",
    )
    assert "FAIL_HANDLER_MISSING" in result.rejection_reasons
    assert "stage:worktree_create" in result.rejection_reasons
    assert result.no_worktree_created is True


def test_bootstrap_rejects_unsupported_worktree_runner_mode(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(tmp_path, "profile.json", _profile())

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=tmp_path / "runtime" / "chain_results.json",
        authority_profile_path=profile,
        worktree_runner_mode="shell",
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "unsupported_worktree_runner_mode" in result.rejection_reasons


def test_bootstrap_rejects_unsupported_evidence_command_runner_mode(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(tmp_path, "profile.json", _profile())

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=tmp_path / "runtime" / "chain_results.json",
        authority_profile_path=profile,
        evidence_command_runner_mode="shell",
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "unsupported_evidence_command_runner_mode" in result.rejection_reasons


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
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=6,
    )

    assert result.accepted is False
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY
    assert result.steps_run == 5
    assert result.dispatched_stages == (
        "authority_request",
        "authority_runtime",
        "authority_verification",
        "worker_dispatch_dryrun",
            "worker_dispatch_runtime",
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


def test_bootstrap_rejects_unsupported_work_order_materializer_mode(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(tmp_path, "profile.json", _profile())

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=tmp_path / "runtime" / "chain_results.json",
        authority_profile_path=profile,
        work_order_materializer_mode="unsafe",
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "unsupported_work_order_materializer_mode" in result.rejection_reasons


def test_bootstrap_rejects_work_order_materializer_with_explicit_work_orders_path(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(tmp_path, "profile.json", _profile())
    work_orders = _write_runtime_json(tmp_path, "work_orders.json", _work_orders())

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=tmp_path / "runtime" / "chain_results.json",
        authority_profile_path=profile,
        work_orders_path=work_orders,
        work_order_materializer_mode="authority_profile",
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "work_order_materializer_conflicts_with_work_orders_path" in result.rejection_reasons


def test_bootstrap_rejects_work_order_materializer_without_holoindex_evidence(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(tmp_path, "profile.json", _profile(holoindex_evidence=None))

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=tmp_path / "runtime" / "chain_results.json",
        authority_profile_path=profile,
        work_order_materializer_mode="authority_profile",
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "work_order_materializer_missing_holoindex_evidence" in result.rejection_reasons


def test_bootstrap_rejects_work_order_materializer_without_context_binding(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _profile()
    profile.pop("snapshot_receipt_id")
    profile.pop("wsp15_allocation_receipt")
    profile = _write_runtime_json(tmp_path, "profile.json", profile)

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=tmp_path / "runtime" / "chain_results.json",
        authority_profile_path=profile,
        work_order_materializer_mode="authority_profile",
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "work_order_materializer_missing_context_binding:snapshot_receipt_id" in result.rejection_reasons


def test_bootstrap_materializer_uses_queue_wsp15_allocation_when_profile_omits_it(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile_payload = _profile()
    profile_payload.pop("wsp15_allocation_receipt")
    principal_public, reddog_public, connector = _ed25519_signing_material()
    profile_payload["principal_public_key"] = principal_public
    profile_payload["reddog_public_key"] = reddog_public
    profile = _write_runtime_json(tmp_path, "profile.json", profile_payload)
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
        work_order_materializer_mode="authority_profile",
        valve_environment_path=valve_env,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        signer_socket_path=socket_path,
        signer_socket_connector=connector,
        signature_verifier_backend=REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
            worker_dispatch_writer=_FakeWorkerDispatchTaskWriter(),
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=7,
    )

    assert result.accepted is True


def test_materializer_context_binding_uses_queue_wsp15_allocation_as_authority() -> None:
    profile = _profile()
    profile.pop("wsp15_allocation_receipt")
    allocation = _queue_wsp15_allocation_receipt()

    binding, reasons = _operational_context_binding(
        authority_profile=profile,
        snapshot={},
        queue_wsp15_allocation=allocation,
        queue_wsp15_allocation_receipt_id=str(allocation["receipt_id"]),
    )

    assert reasons == ()
    assert binding["wsp15_allocation_receipt"] == allocation


def test_materializer_context_binding_rejects_conflicting_profile_wsp15_allocation() -> None:
    allocation = _queue_wsp15_allocation_receipt()
    conflicting = dict(allocation)
    conflicting["priority"] = "P4"

    _, reasons = _operational_context_binding(
        authority_profile=_profile(wsp15_allocation_receipt=conflicting),
        snapshot={},
        queue_wsp15_allocation=allocation,
        queue_wsp15_allocation_receipt_id=str(allocation["receipt_id"]),
    )

    assert (
        "work_order_materializer_conflicting_wsp15_allocation_receipt:"
        "authority_profile.wsp15_allocation_receipt"
    ) in reasons


def test_materializer_context_binding_rejects_conflicting_snapshot_wsp15_allocation() -> None:
    allocation = _queue_wsp15_allocation_receipt()
    conflicting = dict(allocation)
    conflicting["mps_total"] = 19

    _, reasons = _operational_context_binding(
        authority_profile=_profile(),
        snapshot={"wsp15_allocation_receipt": conflicting},
        queue_wsp15_allocation=allocation,
        queue_wsp15_allocation_receipt_id=str(allocation["receipt_id"]),
    )

    assert (
        "work_order_materializer_conflicting_wsp15_allocation_receipt:"
        "snapshot.wsp15_allocation_receipt"
    ) in reasons


def test_materializer_context_binding_rejects_queue_receipt_id_mismatch() -> None:
    allocation = _queue_wsp15_allocation_receipt()

    _, reasons = _operational_context_binding(
        authority_profile=_profile(),
        snapshot={},
        queue_wsp15_allocation=allocation,
        queue_wsp15_allocation_receipt_id="sha256:other-allocation",
    )

    assert "work_order_materializer_wsp15_allocation_receipt_id_mismatch" in reasons


def test_materializer_context_binding_rejects_missing_queue_allocation_receipt_id() -> None:
    profile = _profile()
    profile.pop("wsp15_allocation_receipt")
    allocation = _queue_wsp15_allocation_receipt()
    allocation.pop("receipt_id")

    _, reasons = _operational_context_binding(
        authority_profile=profile,
        snapshot={},
        queue_wsp15_allocation=allocation,
        queue_wsp15_allocation_receipt_id="",
    )

    assert "work_order_materializer_missing_queue_wsp15_allocation_receipt_id" in reasons
    assert "work_order_materializer_malformed_wsp15_allocation_receipt:receipt_id" in reasons


def test_materializer_context_binding_rejects_malformed_mps_priority_relationship() -> None:
    profile = _profile()
    profile.pop("wsp15_allocation_receipt")
    allocation = _queue_wsp15_allocation_receipt()
    allocation["priority"] = "P4"

    _, reasons = _operational_context_binding(
        authority_profile=profile,
        snapshot={},
        queue_wsp15_allocation=allocation,
        queue_wsp15_allocation_receipt_id=str(allocation["receipt_id"]),
    )

    assert "work_order_materializer_malformed_wsp15_allocation_receipt:priority" in reasons


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


def test_bootstrap_rejects_unsupported_artifact_generator_mode(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(tmp_path, "profile.json", _profile())

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=tmp_path / "runtime" / "chain_results.json",
        authority_profile_path=profile,
        artifact_generator_mode="unsafe",
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "unsupported_artifact_generator_mode" in result.rejection_reasons


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
                "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_MAX_STEPS": "1",
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(tmp_path / "state.json"),
                "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH": str(tmp_path / "chain.json"),
                "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH": str(tmp_path / "profile.json"),
                "REDDOG_WORK_ORDERS_PATH": str(tmp_path / "work_orders.json"),
                "REDDOG_WORK_ORDER_MATERIALIZER_MODE": "",
                "REDDOG_EXECUTION_VALVE_ENV_PATH": str(tmp_path / "valve_env.json"),
                "REDDOG_GENERIC_WRITER_DRYRUN_RESULT_PATH": str(tmp_path / "generic_writer.json"),
                "REDDOG_GOVERNED_SHELL_DRYRUN_RESULT_PATH": str(tmp_path / "governed_shell.json"),
                "REDDOG_ARTIFACT_CONTENTS_PATH": str(tmp_path / "artifact_contents.json"),
                "REDDOG_ARTIFACT_GENERATION_REQUEST_PATH": str(
                    tmp_path / "artifact_generation_request.json"
                ),
                "REDDOG_ARTIFACT_GENERATOR_MODE": "foundups_fusion",
                "REDDOG_HOLOINDEX_EVIDENCE_PATH": str(tmp_path / "holoindex_evidence.json"),
                "REDDOG_SLICE_VERIFIER_REQUEST_PATH": str(tmp_path / "verifier_request.json"),
                "REDDOG_EVIDENCE_PRODUCER_REQUEST_PATH": str(
                    tmp_path / "evidence_producer_request.json"
                ),
                "REDDOG_EVIDENCE_COMMAND_RUNNER_MODE": "real",
                "REDDOG_DRAFT_PR_PUBLISH_REQUEST_PATH": str(tmp_path / "publish_request.json"),
                "REDDOG_OUTCOME_RATCHET_REQUEST_PATH": str(tmp_path / "ratchet_request.json"),
                "REDDOG_OUTCOME_RATCHET_STORE_PATH": str(tmp_path / "ratchet.jsonl"),
                "REDDOG_HELD_OUT_GATE_REQUEST_PATH": str(tmp_path / "held_out_gate_request.json"),
                "REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_PATH": str(
                    tmp_path / "pattern_memory_admission_request.json"
                ),
                "REDDOG_PATTERN_MEMORY_ADMISSION_DB_PATH": str(
                    tmp_path / "pattern_memory.db"
                ),
                "REDDOG_AUTHORITY_RUNTIME_STATE_PATH": str(tmp_path / "authority_state.json"),
                "REDDOG_PERMISSION_SNAPSHOTS_PATH": str(tmp_path / "snapshots.json"),
                "REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH": str(tmp_path / "principals.json"),
                "REDDOG_SIGNER_SOCKET_PATH": str(tmp_path / "signer.sock"),
                "REDDOG_SIGNER_SOCKET_TIMEOUT_S": "2.5",
                "REDDOG_SIGNER_SOCKET_MAX_RESPONSE_BYTES": "8192",
                "REDDOG_SIGNATURE_VERIFIER_BACKEND": REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519,
                "REDDOG_RESIDENT_QUEUE_WORKTREE_RUNNER_MODE": "real",
                "REDDOG_RESIDENT_QUEUE_WORKTREE_RUNNER_TIMEOUT_S": "77",
                "REDDOG_DRAFT_PR_RUNNER_MODE": "real",
                "REDDOG_DRAFT_PR_RUNNER_TIMEOUT_S": "88",
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
    assert mocked.call_args.kwargs["work_order_materializer_mode"] == "authority_profile"
    assert mocked.call_args.kwargs["valve_environment_path"] == str(tmp_path / "valve_env.json")
    assert mocked.call_args.kwargs["pilot_dryrun_binding_enabled"] is True
    assert mocked.call_args.kwargs["generic_writer_dryrun_result_path"] == str(
        tmp_path / "generic_writer.json"
    )
    assert mocked.call_args.kwargs["governed_shell_dryrun_result_path"] == str(
        tmp_path / "governed_shell.json"
    )
    assert mocked.call_args.kwargs["artifact_contents_path"] == str(
        tmp_path / "artifact_contents.json"
    )
    assert mocked.call_args.kwargs["artifact_generation_request_path"] == str(
        tmp_path / "artifact_generation_request.json"
    )
    assert mocked.call_args.kwargs["artifact_generation_request_binding_enabled"] is True
    assert mocked.call_args.kwargs["artifact_generator_mode"] == "foundups_fusion"
    assert mocked.call_args.kwargs["holoindex_evidence_path"] == str(
        tmp_path / "holoindex_evidence.json"
    )
    assert mocked.call_args.kwargs["verifier_request_path"] == str(
        tmp_path / "verifier_request.json"
    )
    assert mocked.call_args.kwargs["evidence_producer_request_path"] == str(
        tmp_path / "evidence_producer_request.json"
    )
    assert mocked.call_args.kwargs["slice_verifier_request_binding_enabled"] is True
    assert mocked.call_args.kwargs["evidence_command_runner_mode"] == "real"
    assert mocked.call_args.kwargs["publish_request_path"] == str(
        tmp_path / "publish_request.json"
    )
    assert mocked.call_args.kwargs["draft_pr_publish_request_binding_enabled"] is True
    assert mocked.call_args.kwargs["ratchet_request_path"] == str(
        tmp_path / "ratchet_request.json"
    )
    assert mocked.call_args.kwargs["outcome_ratchet_store_path"] == str(
        tmp_path / "ratchet.jsonl"
    )
    assert mocked.call_args.kwargs["outcome_ratchet_request_binding_enabled"] is True
    assert mocked.call_args.kwargs["held_out_gate_request_path"] == str(
        tmp_path / "held_out_gate_request.json"
    )
    assert mocked.call_args.kwargs["held_out_gate_request_binding_enabled"] is True
    assert mocked.call_args.kwargs["admission_request_path"] == str(
        tmp_path / "pattern_memory_admission_request.json"
    )
    assert mocked.call_args.kwargs["pattern_memory_admission_request_binding_enabled"] is True
    assert mocked.call_args.kwargs["pattern_memory_admission_sink"] is not None
    assert str(mocked.call_args.kwargs["pattern_memory_admission_sink"].db_path) == str(
        tmp_path / "pattern_memory.db"
    )
    assert mocked.call_args.kwargs["authority_state_path"] == str(tmp_path / "authority_state.json")
    assert mocked.call_args.kwargs["permission_snapshots_path"] == str(tmp_path / "snapshots.json")
    assert mocked.call_args.kwargs["principal_authority_records_path"] == str(tmp_path / "principals.json")
    assert mocked.call_args.kwargs["signer_socket_path"] == str(tmp_path / "signer.sock")
    assert mocked.call_args.kwargs["signer_socket_timeout_s"] == 2.5
    assert mocked.call_args.kwargs["signer_socket_max_response_bytes"] == 8192
    assert mocked.call_args.kwargs["signature_verifier_backend"] == REDDOG_SIGNATURE_VERIFIER_BACKEND_ED25519
    assert mocked.call_args.kwargs["worktree_runner_mode"] == "real"
    assert mocked.call_args.kwargs["worktree_runner_timeout_s"] == 77
    assert mocked.call_args.kwargs["draft_pr_runner"].__class__.__name__ == "RealWorktreeRunner"
    assert mocked.call_args.kwargs["draft_pr_runner"].timeout_s == 88
    assert mocked.call_args.kwargs["requested_queue_item_id"] == "queue-1"
    assert mocked.call_args.kwargs["now_epoch"] == 1000
    assert mocked.call_args.kwargs["max_steps"] == 1


def test_main_serial_loop_preflight_worktree_profile_derives_model_and_worktree_modes(
    tmp_path: Path,
) -> None:
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
                "dispatched_stages": ("bounded_worker_pilot",),
                "next_action": "STOP_QUEUE_CHAIN_COMPLETE",
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
                "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code_fusion_worktree",
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(tmp_path / "state.json"),
                "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH": str(tmp_path / "chain.json"),
                "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH": str(tmp_path / "profile.json"),
            },
            clear=True,
        ):
            assert main.run_reddog_resident_queue_serial_loop_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["work_order_materializer_mode"] == "authority_profile"
    assert mocked.call_args.kwargs["artifact_generation_request_binding_enabled"] is True
    assert mocked.call_args.kwargs["artifact_generator_mode"] == "foundups_fusion"
    assert mocked.call_args.kwargs["worktree_runner_mode"] == "real"
    assert mocked.call_args.kwargs["evidence_command_runner_mode"] is None
    assert mocked.call_args.kwargs["outcome_ratchet_store_path"] is None


def test_main_serial_loop_preflight_draft_pr_profile_derives_draft_runner(
    tmp_path: Path,
) -> None:
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
                "dispatched_stages": ("verified_draft_pr_publish",),
                "next_action": "STOP_QUEUE_CHAIN_COMPLETE",
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
                "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code_fusion_worktree_draft_pr",
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(tmp_path / "state.json"),
                "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH": str(tmp_path / "chain.json"),
                "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH": str(tmp_path / "profile.json"),
                "REDDOG_DRAFT_PR_RUNNER_TIMEOUT_S": "91",
            },
            clear=True,
        ):
            assert main.run_reddog_resident_queue_serial_loop_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["artifact_generator_mode"] == "foundups_fusion"
    assert mocked.call_args.kwargs["worktree_runner_mode"] == "real"
    assert mocked.call_args.kwargs["evidence_command_runner_mode"] == "real"
    assert mocked.call_args.kwargs["outcome_ratchet_store_path"] == str(
        REPO_ROOT.resolve().parent
        / ".reddog"
        / "outcome_ratchet"
        / REPO_ROOT.resolve().name
        / "verified_outcomes.jsonl"
    )
    assert mocked.call_args.kwargs["pattern_memory_admission_sink"] is None
    assert mocked.call_args.kwargs["draft_pr_runner"].__class__.__name__ == "RealWorktreeRunner"
    assert mocked.call_args.kwargs["draft_pr_runner"].timeout_s == 91


def test_main_serial_loop_preflight_pattern_memory_profile_derives_sink(
    tmp_path: Path,
) -> None:
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
                "dispatched_stages": ("pattern_memory_admission",),
                "next_action": "STOP_QUEUE_CHAIN_COMPLETE",
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
                "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": (
                    "signed_0102_bounded_code_fusion_worktree_draft_pr_pattern_memory"
                ),
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(tmp_path / "state.json"),
                "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH": str(tmp_path / "chain.json"),
                "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH": str(tmp_path / "profile.json"),
                "REDDOG_DRAFT_PR_RUNNER_TIMEOUT_S": "92",
            },
            clear=True,
        ):
            assert main.run_reddog_resident_queue_serial_loop_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["artifact_generator_mode"] == "foundups_fusion"
    assert mocked.call_args.kwargs["worktree_runner_mode"] == "real"
    assert mocked.call_args.kwargs["evidence_command_runner_mode"] == "real"
    assert mocked.call_args.kwargs["outcome_ratchet_store_path"] == str(
        REPO_ROOT.resolve().parent
        / ".reddog"
        / "outcome_ratchet"
        / REPO_ROOT.resolve().name
        / "verified_outcomes.jsonl"
    )
    sink = mocked.call_args.kwargs["pattern_memory_admission_sink"]
    assert sink is not None
    assert sink.__class__.__name__ == "RedDogVerifiedPatternMemorySink"
    assert str(sink.db_path) == str(
        REPO_ROOT.resolve().parent
        / ".reddog"
        / "pattern_memory"
        / REPO_ROOT.resolve().name
        / "pattern_memory.db"
    )
    assert mocked.call_args.kwargs["draft_pr_runner"].__class__.__name__ == "RealWorktreeRunner"
    assert mocked.call_args.kwargs["draft_pr_runner"].timeout_s == 92


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


def test_main_serial_loop_preflight_rejects_unsupported_draft_pr_runner_mode_when_enforced() -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_resident_queue_serial_loop_bootstrap.run_reddog_main_resident_queue_serial_loop_bootstrap",
        side_effect=AssertionError("bootstrap must not run for unsupported draft PR runner mode"),
    ):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP": "1",
                "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_ENFORCED": "1",
                "REDDOG_DRAFT_PR_RUNNER_MODE": "unsafe",
            },
            clear=True,
        ):
            assert main.run_reddog_resident_queue_serial_loop_preflight(REPO_ROOT) is False


def test_module_has_no_shell_network_holoindex_or_worker_stage_imports() -> None:
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
