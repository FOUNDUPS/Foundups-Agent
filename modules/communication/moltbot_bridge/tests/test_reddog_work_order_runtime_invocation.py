"""Tests for RedDog work-order runtime invocation dry-run."""

from __future__ import annotations

import ast
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_openclaw_work_order_policy_gate import (
    POLICY_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_receipt import (
    RedDogWorkOrderReceiptStore,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_runtime_invocation import (
    INVOCATION_ACCEPT_WITH_RETRIEVAL_GAP,
    INVOCATION_REJECT,
    invoke_reddog_work_order_dryrun,
)


def _future_expiry(hours: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).replace(microsecond=0).isoformat()


def _fresh_captured() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _base_order(**overrides):
    payload = {
        "work_order_id": "wo-invoke-001",
        "created_at": _fresh_captured(),
        "red_dog_instance_id": "reddog-ext-0.3.27",
        "authenticated_principal": "principal-012",
        "principal_provider": "github",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "repo_permission_snapshot": {
            "permission_level": "read",
            "captured_at": _fresh_captured(),
            "source": "mock",
            "digest": "sha256:" + ("a" * 64),
        },
        "requested_operation": "audit_only",
        "authority_tier": "advisory",
        "allowed_paths": ["docs/**"],
        "denied_paths": [".env"],
        "branch_name": "docs/invoke-test",
        "base_ref": "main",
        "task_summary": "Runtime invocation dry-run validation",
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
        "nonce": "nonce-invoke-001",
        "evidence_digest": "sha256:" + ("b" * 64),
        "advisory_only_source_packet": {
            "work_focus_digest": "sha256:" + ("c" * 64),
            "wsp_prompt_digest": "sha256:" + ("d" * 64),
            "copy_md_run_trace_digest": "sha256:" + ("e" * 64),
        },
        "holoindex_evidence": {
            "holoindex_query": "RedDog runtime invocation dryrun",
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


class TestInvocationAccept:
    def test_audit_docs_work_order_stores_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            with RedDogWorkOrderReceiptStore(Path(tmp) / "receipts.db") as store:
                result = invoke_reddog_work_order_dryrun(
                    _base_order(nonce="nonce-audit-accept"),
                    permission_snapshot={
                        "permission_level": "read",
                        "captured_at": _fresh_captured(),
                        "source": "mock",
                    },
                    seen_nonces=set(),
                    receipt_store=store,
                )
                assert result.decision == INVOCATION_ACCEPT_WITH_RETRIEVAL_GAP
                assert result.no_execution_performed is True
                assert result.receipt_id
                assert result.receipt_digest
                loaded = store.get_by_policy_digest(result.policy_gate_receipt_digest)
                assert loaded is not None
                assert loaded.receipt_id == result.receipt_id


class TestInvocationReject:
    def test_stale_permission_write_rejects_and_stores_receipt(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=2)).replace(microsecond=0).isoformat()
        order = _base_order(
            nonce="nonce-stale-write",
            requested_operation="feature_slice",
            authority_tier="source",
            branch_name="feat/stale-test",
            allowed_paths=["modules/**"],
            holoindex_evidence={
                "holoindex_query": "stale permission test",
                "holoindex_status": "bundle_json_ok",
                "code_hits": [],
                "wsp_hits": ["WSP_framework/src/WSP_34_Git_Operations_Protocol.md"],
                "skillz_hits": [],
                "direct_read_fallback_used": False,
                "index_gap_detected": False,
                "applicable_wsps": ["WSP_34"],
                "evidence_refs": [
                    "docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md"
                ],
                "retrieval_quality": "HIGH",
                "skillz_gap_detected": False,
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            with RedDogWorkOrderReceiptStore(Path(tmp) / "receipts.db") as store:
                result = invoke_reddog_work_order_dryrun(
                    order,
                    permission_snapshot={
                        "permission_level": "write",
                        "captured_at": past,
                        "source": "mock",
                    },
                    seen_nonces=set(),
                    receipt_store=store,
                    permission_ttl_seconds=300,
                )
                assert result.decision == INVOCATION_REJECT
                assert result.policy_gate_decision == POLICY_REJECT
                assert "stale_permission_snapshot" in result.rejection_reasons
                assert result.receipt_id
                loaded = store.get_by_policy_digest(result.policy_gate_receipt_digest)
                assert loaded is not None

    def test_index_gap_write_rejects_and_stores_receipt(self):
        order = _base_order(
            nonce="nonce-index-gap-write",
            requested_operation="feature_slice",
            authority_tier="source",
            branch_name="feat/index-gap",
            allowed_paths=["modules/**"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            with RedDogWorkOrderReceiptStore(Path(tmp) / "receipts.db") as store:
                result = invoke_reddog_work_order_dryrun(
                    order,
                    permission_snapshot={
                        "permission_level": "write",
                        "captured_at": _fresh_captured(),
                        "source": "mock",
                    },
                    seen_nonces=set(),
                    receipt_store=store,
                )
                assert result.decision == INVOCATION_REJECT
                assert "index_gap_blocks_write_operation" in result.rejection_reasons
                assert result.receipt_id
                loaded = store.get_by_policy_digest(result.policy_gate_receipt_digest)
                assert loaded is not None

    def test_replayed_nonce_fails_closed(self):
        seen = set()
        order = _base_order(nonce="nonce-replay-invoke")
        first = invoke_reddog_work_order_dryrun(
            order,
            permission_snapshot={"permission_level": "read", "captured_at": _fresh_captured()},
            seen_nonces=seen,
        )
        assert first.decision == INVOCATION_ACCEPT_WITH_RETRIEVAL_GAP
        second = invoke_reddog_work_order_dryrun(
            order,
            permission_snapshot={"permission_level": "read", "captured_at": _fresh_captured()},
            seen_nonces=seen,
        )
        assert second.decision == INVOCATION_REJECT
        assert "replayed_nonce" in second.rejection_reasons


class TestInvocationStability:
    def test_receipt_id_and_digest_stable(self):
        fixed = datetime(2026, 6, 28, 16, 0, 0, tzinfo=timezone.utc)
        captured = (fixed - timedelta(seconds=60)).replace(microsecond=0).isoformat()
        order = _base_order(
            nonce="nonce-stable-invoke",
            repo_permission_snapshot={
                "permission_level": "read",
                "captured_at": captured,
                "source": "mock",
                "digest": "sha256:" + ("f" * 64),
            },
        )
        first = invoke_reddog_work_order_dryrun(order, seen_nonces=set(), now=fixed)
        second = invoke_reddog_work_order_dryrun(order, seen_nonces=set(), now=fixed)
        assert first.receipt_id == second.receipt_id
        assert first.receipt_digest == second.receipt_digest
        assert first.no_execution_performed is True

    def test_idempotent_store_replay(self):
        fixed = datetime(2026, 6, 28, 16, 5, 0, tzinfo=timezone.utc)
        order = _base_order(nonce="nonce-idem-invoke")
        with tempfile.TemporaryDirectory() as tmp:
            with RedDogWorkOrderReceiptStore(Path(tmp) / "receipts.db") as store:
                first = invoke_reddog_work_order_dryrun(
                    order, seen_nonces=set(), receipt_store=store, now=fixed
                )
                second = invoke_reddog_work_order_dryrun(
                    order, seen_nonces=set(), receipt_store=store, now=fixed
                )
                assert first.receipt_id == second.receipt_id
                assert second.idempotent_replay is True


class TestNoExecutionBoundary:
    def test_ast_denylist(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "reddog_work_order_runtime_invocation.py"
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
            if any(
                token in name
                for token in ("subprocess", "github_integration", "wre_core", "skillz")
            )
        ]
        assert forbidden == []
        for token in (
            "subprocess",
            "probe_repo_permission",
            "create_branch",
            "merge_pull_request",
            "git ",
            "gh ",
        ):
            assert token not in source
