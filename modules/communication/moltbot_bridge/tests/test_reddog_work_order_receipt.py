"""Tests for RedDog Hermes-compatible work-order receipt layer."""

from __future__ import annotations

import ast
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_openclaw_work_order_policy_gate import (
    evaluate_work_order_policy_gate,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_receipt import (
    RECEIPT_SOURCE,
    RedDogWorkOrderReceiptStore,
    ReceiptStoreStatus,
    build_reddog_work_order_receipt,
    emit_work_order_receipt,
)


def _future_expiry(hours: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).replace(microsecond=0).isoformat()


def _fresh_captured() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _accept_policy_order(**overrides):
    payload = {
        "work_order_id": "wo-receipt-001",
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
        "requested_operation": "audit_only",
        "authority_tier": "advisory",
        "allowed_paths": ["docs/**"],
        "denied_paths": [".env"],
        "branch_name": "docs/receipt-test",
        "base_ref": "main",
        "task_summary": "Receipt layer validation",
        "wsp_applicability": ["WSP_34", "WSP_50"],
        "holoindex_evidence_refs": [
            "docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md"
        ],
        "skillz_candidates": [],
        "required_tests": [],
        "required_policy_gates": ["openclaw_policy_gate"],
        "required_reviewers": [],
        "sentinel_checks": [],
        "rollback_plan": "No execution performed.",
        "expiry": _future_expiry(),
        "nonce": "nonce-receipt-001",
        "evidence_digest": "sha256:" + ("b" * 64),
        "advisory_only_source_packet": {
            "work_focus_digest": "sha256:" + ("c" * 64),
            "wsp_prompt_digest": "sha256:" + ("d" * 64),
            "copy_md_run_trace_digest": "sha256:" + ("e" * 64),
        },
        "holoindex_evidence": {
            "holoindex_query": "RedDog work order receipt",
            "holoindex_status": "bundle_json_ok",
            "code_hits": [],
            "wsp_hits": ["WSP_framework/src/WSP_34_Git_Operations_Protocol.md"],
            "skillz_hits": [],
            "direct_read_fallback_used": False,
            "index_gap_detected": True,
            "applicable_wsps": ["WSP_34"],
            "evidence_refs": [
                "docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md"
            ],
            "retrieval_quality": "INDEX_GAP",
            "skillz_gap_detected": True,
        },
    }
    payload.update(overrides)
    return payload


class TestReceiptSchema:
    def test_build_from_policy_gate_receipt(self):
        policy = evaluate_work_order_policy_gate(_accept_policy_order(), seen_nonces=set())
        receipt = build_reddog_work_order_receipt(policy)
        assert receipt.work_order_id == "wo-receipt-001"
        assert receipt.policy_gate_decision == policy.decision
        assert receipt.policy_gate_receipt_digest == policy.receipt_digest
        assert receipt.dry_run_receipt_digest == policy.dry_run_receipt_digest
        assert receipt.permission_snapshot_digest == policy.permission_snapshot_digest
        assert receipt.holoindex_evidence_digest == policy.holoindex_evidence_digest
        assert receipt.permission_truth_label == policy.permission_truth_label
        assert receipt.source == RECEIPT_SOURCE

    def test_no_execution_performed_invariant(self):
        policy = evaluate_work_order_policy_gate(
            _accept_policy_order(nonce="nonce-noexec"), seen_nonces=set()
        )
        receipt = build_reddog_work_order_receipt(policy)
        assert receipt.no_execution_performed is True

    def test_receipt_digest_stable(self):
        fixed = datetime(2026, 6, 28, 15, 0, 0, tzinfo=timezone.utc)
        captured = (fixed - timedelta(seconds=60)).replace(microsecond=0).isoformat()
        order = _accept_policy_order(
            nonce="nonce-stable-receipt",
            repo_permission_snapshot={
                "permission_level": "write",
                "captured_at": captured,
                "source": "mock",
                "digest": "sha256:" + ("f" * 64),
            },
        )
        policy = evaluate_work_order_policy_gate(order, seen_nonces=set(), now=fixed)
        first = build_reddog_work_order_receipt(policy, now=fixed)
        second = build_reddog_work_order_receipt(policy, now=fixed)
        assert first.to_dict() == second.to_dict()
        assert first.receipt_digest == second.receipt_digest

    def test_json_serializable(self):
        policy = evaluate_work_order_policy_gate(
            _accept_policy_order(nonce="nonce-json"), seen_nonces=set()
        )
        receipt = build_reddog_work_order_receipt(policy)
        parsed = json.loads(receipt.to_json())
        assert parsed["source"] == RECEIPT_SOURCE
        assert parsed["no_execution_performed"] is True


class TestSecretSafety:
    def test_redaction_on_store_payload(self):
        policy = evaluate_work_order_policy_gate(
            _accept_policy_order(nonce="nonce-redact"), seen_nonces=set()
        )
        receipt = build_reddog_work_order_receipt(policy)
        poisoned = receipt.to_dict()
        poisoned["work_order_id"] = "ghp_abcdefghijklmnopqrstuvwxyz1234567890"
        from modules.communication.moltbot_bridge.src.reddog_work_order_receipt import _sanitize_dict

        cleaned = _sanitize_dict(poisoned)
        assert "ghp_" not in cleaned["work_order_id"]
        assert "[REDACTED]" in cleaned["work_order_id"]

    def test_receipt_json_has_no_token_patterns(self):
        policy = evaluate_work_order_policy_gate(
            _accept_policy_order(nonce="nonce-token-scan"), seen_nonces=set()
        )
        receipt = build_reddog_work_order_receipt(policy)
        blob = receipt.to_json()
        assert "ghp_" not in blob
        assert "sk-" not in blob


class TestIdempotency:
    def test_same_policy_receipt_same_receipt_id(self):
        policy = evaluate_work_order_policy_gate(
            _accept_policy_order(nonce="nonce-idem"), seen_nonces=set()
        )
        a = build_reddog_work_order_receipt(policy)
        b = build_reddog_work_order_receipt(policy)
        assert a.receipt_id == b.receipt_id
        assert a.receipt_digest == b.receipt_digest

    def test_store_replay_is_idempotent(self):
        policy = evaluate_work_order_policy_gate(
            _accept_policy_order(nonce="nonce-store-idem"), seen_nonces=set()
        )
        with tempfile.TemporaryDirectory() as tmp:
            with RedDogWorkOrderReceiptStore(Path(tmp) / "receipts.db") as store:
                first = emit_work_order_receipt(policy, store=store)
                second = emit_work_order_receipt(policy, store=store)
                assert first.success is True
                assert second.success is True
                assert second.idempotent_replay is True
                assert first.receipt.receipt_id == second.receipt.receipt_id
                assert second.store_status == ReceiptStoreStatus.ALREADY_EXISTS

    def test_different_policy_digest_different_receipt_id(self):
        policy_a = evaluate_work_order_policy_gate(
            _accept_policy_order(nonce="nonce-a"), seen_nonces=set()
        )
        policy_b = evaluate_work_order_policy_gate(
            _accept_policy_order(nonce="nonce-b"), seen_nonces=set()
        )
        receipt_a = build_reddog_work_order_receipt(policy_a)
        receipt_b = build_reddog_work_order_receipt(policy_b)
        assert receipt_a.receipt_id != receipt_b.receipt_id


class TestEmission:
    def test_emit_without_store(self):
        policy = evaluate_work_order_policy_gate(
            _accept_policy_order(nonce="nonce-emit-memory"), seen_nonces=set()
        )
        result = emit_work_order_receipt(policy)
        assert result.success is True
        assert result.persisted is False
        assert result.receipt is not None

    def test_emit_with_store_persists(self):
        policy = evaluate_work_order_policy_gate(
            _accept_policy_order(nonce="nonce-emit-store"), seen_nonces=set()
        )
        with tempfile.TemporaryDirectory() as tmp:
            with RedDogWorkOrderReceiptStore(Path(tmp) / "receipts.db") as store:
                result = emit_work_order_receipt(policy, store=store)
                assert result.success is True
                assert result.persisted is True
                loaded = store.get_by_policy_digest(policy.receipt_digest)
                assert loaded is not None
                assert loaded.receipt_id == result.receipt.receipt_id


class TestNoExecutionBoundary:
    def test_module_has_no_mutation_imports(self):
        module_path = (
            Path(__file__).resolve().parents[1] / "src" / "reddog_work_order_receipt.py"
        )
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        forbidden = [
            name
            for name in imported
            if any(token in name for token in ("subprocess", "github_integration", "wre_core"))
        ]
        assert forbidden == []
        assert "probe_repo_permission" not in source

    def test_rejects_policy_receipt_without_no_execution_flag(self):
        policy = evaluate_work_order_policy_gate(
            _accept_policy_order(nonce="nonce-bad-flag"), seen_nonces=set()
        )
        policy.no_execution_performed = False
        with pytest.raises(ValueError, match="no_execution_performed"):
            build_reddog_work_order_receipt(policy)
