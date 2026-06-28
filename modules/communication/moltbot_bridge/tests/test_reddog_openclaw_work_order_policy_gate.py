"""Tests for OpenClaw RedDog work-order policy gate (no execution, mocked permissions)."""

from __future__ import annotations

import ast
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_openclaw_work_order_policy_gate import (
    POLICY_ACCEPT,
    POLICY_ACCEPT_WITH_RETRIEVAL_GAP,
    POLICY_REJECT,
    TRUTH_NEEDS_VERIFICATION,
    TRUTH_OBSERVED,
    evaluate_work_order_policy_gate,
    permission_truth_label,
)
from modules.communication.moltbot_bridge.src.reddog_governed_work_order_dryrun import (
    validate_work_order_dryrun,
)


def _future_expiry(hours: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).replace(microsecond=0).isoformat()


def _fresh_captured() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _base_order(**overrides):
    payload = {
        "work_order_id": "wo-policy-001",
        "created_at": _fresh_captured(),
        "red_dog_instance_id": "reddog-ext-0.3.27",
        "authenticated_principal": "principal-012",
        "principal_provider": "github",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "repo_permission_snapshot": {
            "permission_level": "write",
            "captured_at": _fresh_captured(),
            "source": "mock",
            "digest": "sha256:" + ("a" * 64),
        },
        "requested_operation": "feature_slice",
        "authority_tier": "source",
        "allowed_paths": ["modules/communication/moltbot_bridge/**"],
        "denied_paths": [".env"],
        "branch_name": "feat/policy-gate-test",
        "base_ref": "main",
        "task_summary": "Policy gate validation slice",
        "wsp_applicability": ["WSP_34", "WSP_50", "WSP_97"],
        "holoindex_evidence_refs": [
            "docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md"
        ],
        "skillz_candidates": ["qwen_wsp_enhancement"],
        "required_tests": [
            "modules/communication/moltbot_bridge/tests/test_reddog_openclaw_work_order_policy_gate.py"
        ],
        "required_policy_gates": ["openclaw_policy_gate", "github_permission_fresh"],
        "required_reviewers": [],
        "sentinel_checks": [],
        "rollback_plan": "No execution performed.",
        "expiry": _future_expiry(),
        "nonce": "nonce-policy-001",
        "evidence_digest": "sha256:" + ("b" * 64),
        "advisory_only_source_packet": {
            "work_focus_digest": "sha256:" + ("c" * 64),
            "wsp_prompt_digest": "sha256:" + ("d" * 64),
            "copy_md_run_trace_digest": "sha256:" + ("e" * 64),
        },
        "holoindex_evidence": {
            "holoindex_query": "RedDog OpenClaw policy gate",
            "holoindex_status": "bundle_json_ok",
            "code_hits": [
                "modules/communication/moltbot_bridge/src/reddog_openclaw_work_order_policy_gate.py"
            ],
            "wsp_hits": ["WSP_framework/src/WSP_34_Git_Operations_Protocol.md"],
            "skillz_hits": ["qwen_wsp_enhancement"],
            "direct_read_fallback_used": False,
            "index_gap_detected": False,
            "applicable_wsps": ["WSP_34", "WSP_50", "WSP_97"],
            "evidence_refs": [
                "docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md"
            ],
            "retrieval_quality": "HIGH",
            "skillz_gap_detected": False,
        },
    }
    snap_override = overrides.pop("repo_permission_snapshot", None)
    payload.update(overrides)
    if snap_override:
        payload["repo_permission_snapshot"] = {
            **payload["repo_permission_snapshot"],
            **snap_override,
        }
    if "holoindex_evidence" in overrides and overrides["holoindex_evidence"] is None:
        payload.pop("holoindex_evidence", None)
    return payload


class TestPolicyAccept:
    def test_write_operation_with_fresh_write_snapshot(self):
        receipt = evaluate_work_order_policy_gate(_base_order(), seen_nonces=set())
        assert receipt.decision == POLICY_ACCEPT
        assert receipt.rejection_reasons == []
        assert receipt.no_execution_performed is True
        assert receipt.permission_truth_label == TRUTH_OBSERVED

    def test_audit_only_with_read_permission(self):
        order = _base_order(
            requested_operation="audit_only",
            authority_tier="advisory",
            branch_name="docs/policy-audit",
            allowed_paths=["docs/**"],
            repo_permission_snapshot={
                "permission_level": "read",
                "captured_at": _fresh_captured(),
                "source": "mock",
            },
        )
        receipt = evaluate_work_order_policy_gate(order, seen_nonces=set())
        assert receipt.decision == POLICY_ACCEPT
        assert receipt.no_execution_performed is True


class TestPolicyReject:
    def test_admin_operation_rejected_even_with_admin_snapshot(self):
        order = _base_order(
            requested_operation="grant_permission_admin",
            repo_permission_snapshot={
                "permission_level": "admin",
                "captured_at": _fresh_captured(),
                "source": "mock",
            },
        )
        receipt = evaluate_work_order_policy_gate(order, seen_nonces=set())
        assert receipt.decision == POLICY_REJECT
        assert "forbidden_requested_operation" in receipt.rejection_reasons

    def test_stale_permission_snapshot_rejected(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=2)).replace(microsecond=0).isoformat()
        order = _base_order(
            repo_permission_snapshot={
                "permission_level": "write",
                "captured_at": past,
                "source": "mock",
            },
        )
        receipt = evaluate_work_order_policy_gate(order, seen_nonces=set(), permission_ttl_seconds=300)
        assert receipt.decision == POLICY_REJECT
        assert "stale_permission_snapshot" in receipt.rejection_reasons

    def test_replayed_nonce_rejected(self):
        seen = set()
        first = evaluate_work_order_policy_gate(
            _base_order(nonce="nonce-replay-policy"), seen_nonces=seen
        )
        assert first.decision == POLICY_ACCEPT
        second = evaluate_work_order_policy_gate(
            _base_order(nonce="nonce-replay-policy"), seen_nonces=seen
        )
        assert second.decision == POLICY_REJECT
        assert "replayed_nonce" in second.rejection_reasons

    def test_forbidden_path_in_allowed_scope(self):
        order = _base_order(allowed_paths=[".env", "docs/**"])
        receipt = evaluate_work_order_policy_gate(order, seen_nonces=set())
        assert receipt.decision == POLICY_REJECT
        assert "forbidden_paths_in_allowed_scope" in receipt.rejection_reasons

    def test_insufficient_permission_for_write(self):
        order = _base_order(
            repo_permission_snapshot={
                "permission_level": "read",
                "captured_at": _fresh_captured(),
                "source": "mock",
            },
        )
        receipt = evaluate_work_order_policy_gate(order, seen_nonces=set())
        assert receipt.decision == POLICY_REJECT
        assert "insufficient_permission_for_operation" in receipt.rejection_reasons

    def test_unknown_permission_blocks_write_with_needs_verification(self):
        order = _base_order(
            repo_permission_snapshot={
                "permission_level": "unknown",
                "captured_at": _fresh_captured(),
                "source": "gh_cli",
            },
        )
        receipt = evaluate_work_order_policy_gate(order, seen_nonces=set())
        assert receipt.decision == POLICY_REJECT
        assert receipt.permission_truth_label == TRUTH_NEEDS_VERIFICATION
        assert "permission_needs_verification" in receipt.rejection_reasons


class TestHoloIndexPolicy:
    def test_missing_holoindex_evidence_rejected(self):
        receipt = evaluate_work_order_policy_gate(
            _base_order(holoindex_evidence=None), seen_nonces=set()
        )
        assert receipt.decision == POLICY_REJECT
        assert "missing_holoindex_evidence" in receipt.rejection_reasons

    def test_index_gap_write_operation_rejected(self):
        order = _base_order()
        order["holoindex_evidence"]["retrieval_quality"] = "INDEX_GAP"
        order["holoindex_evidence"]["index_gap_detected"] = True
        receipt = evaluate_work_order_policy_gate(order, seen_nonces=set())
        assert receipt.decision == POLICY_REJECT
        assert "index_gap_blocks_write_operation" in receipt.rejection_reasons

    def test_index_gap_audit_only_accept_with_retrieval_gap(self):
        order = _base_order(
            requested_operation="audit_only",
            authority_tier="advisory",
            branch_name="docs/audit-gap",
            allowed_paths=["docs/**"],
        )
        order["holoindex_evidence"]["retrieval_quality"] = "INDEX_GAP"
        order["holoindex_evidence"]["index_gap_detected"] = True
        order["holoindex_evidence"]["evidence_refs"] = []
        receipt = evaluate_work_order_policy_gate(order, seen_nonces=set())
        assert receipt.decision == POLICY_ACCEPT_WITH_RETRIEVAL_GAP
        assert receipt.rejection_reasons == []

    def test_weak_wsp_recall_without_fallback_rejected(self):
        order = _base_order()
        order["holoindex_evidence"]["retrieval_quality"] = "LOW"
        order["holoindex_evidence"]["direct_read_fallback_used"] = False
        receipt = evaluate_work_order_policy_gate(order, seen_nonces=set())
        assert receipt.decision == POLICY_REJECT
        assert "weak_wsp_recall_requires_direct_read_fallback" in receipt.rejection_reasons

    def test_weak_wsp_recall_with_fallback_and_refs_accepts(self):
        order = _base_order()
        order["holoindex_evidence"]["retrieval_quality"] = "LOW"
        order["holoindex_evidence"]["direct_read_fallback_used"] = True
        order["holoindex_evidence"]["evidence_refs"] = [
            "docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md"
        ]
        receipt = evaluate_work_order_policy_gate(order, seen_nonces=set())
        assert receipt.decision == POLICY_ACCEPT

    def test_weak_wsp_recall_with_fallback_missing_refs_rejected(self):
        order = _base_order()
        order["holoindex_evidence"]["retrieval_quality"] = "LOW"
        order["holoindex_evidence"]["direct_read_fallback_used"] = True
        order["holoindex_evidence"]["evidence_refs"] = []
        receipt = evaluate_work_order_policy_gate(order, seen_nonces=set())
        assert receipt.decision == POLICY_REJECT
        assert "weak_wsp_recall_missing_direct_read_ref" in receipt.rejection_reasons


class TestReceiptCompatibility:
    def test_receipt_digest_stable_for_same_input(self):
        fixed = datetime(2026, 6, 28, 14, 0, 0, tzinfo=timezone.utc)
        captured = (fixed - timedelta(seconds=60)).replace(microsecond=0).isoformat()
        order = _base_order(
            nonce="nonce-stable-digest",
            repo_permission_snapshot={
                "permission_level": "write",
                "captured_at": captured,
                "source": "mock",
            },
        )
        kwargs = {"seen_nonces": set(), "now": fixed}

        first = evaluate_work_order_policy_gate(order, **kwargs)
        second = evaluate_work_order_policy_gate(order, seen_nonces=set(), now=fixed)

        assert first.to_dict() == second.to_dict()
        assert first.receipt_digest == second.receipt_digest

    def test_receipt_json_serializable_no_secrets(self):
        receipt = evaluate_work_order_policy_gate(_base_order(nonce="nonce-json"), seen_nonces=set())
        blob = json.dumps(receipt.to_dict())
        assert "ghp_" not in blob
        assert "sk-" not in blob
        parsed = json.loads(blob)
        assert parsed["no_execution_performed"] is True
        assert "receipt_digest" in parsed
        assert "holoindex_evidence_digest" in parsed
        assert "dry_run_receipt_digest" in parsed
        assert "permission_snapshot_digest" in parsed
        assert "next_required_check_at" in parsed

    def test_required_receipt_fields_present(self):
        receipt = evaluate_work_order_policy_gate(_base_order(nonce="nonce-fields"), seen_nonces=set())
        data = receipt.to_dict()
        for key in (
            "receipt_id",
            "work_order_id",
            "decision",
            "rejection_reasons",
            "gates_checked",
            "dry_run_receipt_digest",
            "permission_snapshot_digest",
            "permission_truth_label",
            "holoindex_evidence_digest",
            "no_execution_performed",
            "checked_at",
            "expires_at",
            "next_required_check_at",
            "receipt_digest",
        ):
            assert key in data


class TestNoWaeRuntimeOrLiveGithub:
    def test_policy_gate_does_not_import_wae_runtime(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "reddog_openclaw_work_order_policy_gate.py"
        )
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        wae_hits = [name for name in imported if "wae" in name.lower()]
        assert wae_hits == []

    def test_policy_gate_module_has_no_live_github_probe(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "reddog_openclaw_work_order_policy_gate.py"
        ).read_text(encoding="utf-8")
        assert "import subprocess" not in source
        assert "from modules.platform_integration.github_integration" in source
        assert "permission_to_capabilities" in source


class TestPermissionTruthLabel:
    def test_observed_for_proven_permission(self):
        assert permission_truth_label("write", "gh_cli") == TRUTH_OBSERVED

    def test_needs_verification_for_unknown(self):
        assert permission_truth_label("unknown", "gh_cli") == TRUTH_NEEDS_VERIFICATION


class TestDryRunDelegation:
    def test_dry_run_still_independent(self):
        order = _base_order(nonce="nonce-dryrun-only")
        dry = validate_work_order_dryrun(order, seen_nonces=set())
        assert dry.no_mutation_performed is True
