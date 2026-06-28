"""Tests for RedDog governed repo work-order dry-run validator."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from modules.communication.moltbot_bridge.src.reddog_governed_work_order_dryrun import (
    DECISION_ACCEPT,
    DECISION_ACCEPT_WITH_GAP,
    DECISION_REJECT,
    validate_work_order_dryrun,
)


def _future_expiry(hours: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).replace(microsecond=0).isoformat()


def _base_order(**overrides):
    payload = {
        "work_order_id": "wo-test-001",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "red_dog_instance_id": "reddog-ext-0.3.27",
        "authenticated_principal": "principal-012",
        "principal_provider": "gh_cli_session",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "repo_permission_snapshot": {
            "permission_level": "write",
            "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "source": "github_api",
            "digest": "sha256:" + ("a" * 64),
        },
        "requested_operation": "feature_slice",
        "authority_tier": "source",
        "allowed_paths": ["extensions/foundups_advisory_workers/**"],
        "denied_paths": [".env"],
        "branch_name": "feat/reddog-dryrun-test",
        "base_ref": "main",
        "task_summary": "Add governed work-order dry-run validator",
        "wsp_applicability": ["WSP_34", "WSP_50", "WSP_97"],
        "holoindex_evidence_refs": ["docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md"],
        "skillz_candidates": ["qwen_wsp_enhancement"],
        "required_tests": [
            "modules/communication/moltbot_bridge/tests/test_reddog_governed_work_order_dryrun.py"
        ],
        "required_policy_gates": ["openclaw_source_check", "github_permission_fresh"],
        "required_reviewers": ["sentinel_wsp_compliance"],
        "sentinel_checks": ["wsp_compliance", "regression"],
        "rollback_plan": "Revert branch if dry-run receipt fails downstream gates.",
        "expiry": _future_expiry(),
        "nonce": "nonce-001",
        "evidence_digest": "sha256:" + ("b" * 64),
        "advisory_only_source_packet": {
            "work_focus_digest": "sha256:" + ("c" * 64),
            "wsp_prompt_digest": "sha256:" + ("d" * 64),
            "copy_md_run_trace_digest": "sha256:" + ("e" * 64),
        },
        "holoindex_evidence": {
            "holoindex_query": "RedDog governed repo work order",
            "holoindex_status": "bundle_json_ok",
            "code_hits": ["modules/communication/moltbot_bridge/src/openclaw_permission_policy.py"],
            "wsp_hits": ["WSP_framework/src/WSP_34_Git_Operations_Protocol.md"],
            "skillz_hits": ["qwen_wsp_enhancement"],
            "direct_read_fallback_used": False,
            "index_gap_detected": False,
            "applicable_wsps": ["WSP_34", "WSP_50", "WSP_97"],
            "evidence_refs": ["docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md"],
            "retrieval_quality": "HIGH",
            "skillz_gap_detected": False,
        },
    }
    payload.update(overrides)
    if "holoindex_evidence" in overrides and overrides["holoindex_evidence"] is None:
        payload.pop("holoindex_evidence", None)
    return payload


class TestDryRunAccept:
    def test_valid_work_order_with_holoindex_would_accept(self):
        seen = set()
        receipt = validate_work_order_dryrun(_base_order(), seen_nonces=seen)
        assert receipt.decision == DECISION_ACCEPT
        assert receipt.rejection_reasons == []
        assert receipt.no_mutation_performed is True
        assert len(receipt.receipt_digest) == 64
        assert "holoindex_evidence" in receipt.gates_checked

    def test_index_gap_docs_only_would_accept_with_retrieval_gap(self):
        order = _base_order(
            requested_operation="audit_only",
            authority_tier="advisory",
            branch_name="docs/reddog-audit",
            allowed_paths=["docs/**"],
        )
        order["holoindex_evidence"]["retrieval_quality"] = "INDEX_GAP"
        order["holoindex_evidence"]["index_gap_detected"] = True
        receipt = validate_work_order_dryrun(order, seen_nonces=set())
        assert receipt.decision == DECISION_ACCEPT_WITH_GAP
        assert receipt.rejection_reasons == []


class TestDryRunReject:
    def test_missing_holoindex_evidence(self):
        receipt = validate_work_order_dryrun(_base_order(holoindex_evidence=None), seen_nonces=set())
        assert receipt.decision == DECISION_REJECT
        assert "missing_holoindex_evidence" in receipt.rejection_reasons

    def test_index_gap_on_write_operation(self):
        order = _base_order()
        order["holoindex_evidence"]["retrieval_quality"] = "INDEX_GAP"
        order["holoindex_evidence"]["index_gap_detected"] = True
        receipt = validate_work_order_dryrun(order, seen_nonces=set())
        assert receipt.decision == DECISION_REJECT
        assert "index_gap_blocks_write_operation" in receipt.rejection_reasons

    def test_skillz_handoff_missing_evidence(self):
        order = _base_order(
            skillz_candidates=[],
            task_summary="Route via Skillz/Wardrobe handoff to WRE",
        )
        order["holoindex_evidence"]["skillz_hits"] = []
        order["holoindex_evidence"]["skillz_gap_detected"] = False
        receipt = validate_work_order_dryrun(order, seen_nonces=set())
        assert receipt.decision == DECISION_REJECT
        assert "skillz_handoff_missing_evidence" in receipt.rejection_reasons

    def test_expired_work_order(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(microsecond=0).isoformat()
        receipt = validate_work_order_dryrun(_base_order(expiry=past), seen_nonces=set())
        assert receipt.decision == DECISION_REJECT
        assert "expired_work_order" in receipt.rejection_reasons

    def test_replayed_nonce(self):
        seen = set()
        first = validate_work_order_dryrun(_base_order(nonce="nonce-replay"), seen_nonces=seen)
        assert first.decision == DECISION_ACCEPT
        second = validate_work_order_dryrun(_base_order(nonce="nonce-replay"), seen_nonces=seen)
        assert second.decision == DECISION_REJECT
        assert "replayed_nonce" in second.rejection_reasons

    def test_direct_main_branch_mutation(self):
        receipt = validate_work_order_dryrun(_base_order(branch_name="main"), seen_nonces=set())
        assert receipt.decision == DECISION_REJECT
        assert "direct_main_branch_mutation" in receipt.rejection_reasons

    def test_forbidden_admin_operation(self):
        receipt = validate_work_order_dryrun(
            _base_order(requested_operation="grant_permission_admin"),
            seen_nonces=set(),
        )
        assert receipt.decision == DECISION_REJECT
        assert "forbidden_requested_operation" in receipt.rejection_reasons

    def test_forbidden_env_path_in_allowed_scope(self):
        receipt = validate_work_order_dryrun(
            _base_order(allowed_paths=[".env", "extensions/**"]),
            seen_nonces=set(),
        )
        assert receipt.decision == DECISION_REJECT
        assert "forbidden_paths_in_allowed_scope" in receipt.rejection_reasons

    def test_denied_path_also_allowed(self):
        receipt = validate_work_order_dryrun(
            _base_order(
                allowed_paths=["extensions/**", ".env"],
                denied_paths=[".env"],
            ),
            seen_nonces=set(),
        )
        assert receipt.decision == DECISION_REJECT
        assert "denied_path_also_allowed" in receipt.rejection_reasons

    def test_weak_wsp_recall_requires_direct_read_fallback(self):
        order = _base_order()
        order["holoindex_evidence"]["retrieval_quality"] = "LOW"
        order["holoindex_evidence"]["direct_read_fallback_used"] = False
        order["holoindex_evidence"]["wsp_hits"] = []
        order["holoindex_evidence"]["applicable_wsps"] = []
        receipt = validate_work_order_dryrun(order, seen_nonces=set())
        assert receipt.decision == DECISION_REJECT
        assert "missing_applicable_wsp_evidence" in receipt.rejection_reasons

    def test_missing_required_field(self):
        order = _base_order(work_order_id="")
        receipt = validate_work_order_dryrun(order, seen_nonces=set())
        assert receipt.decision == DECISION_REJECT
        assert "missing_required_field:work_order_id" in receipt.rejection_reasons
