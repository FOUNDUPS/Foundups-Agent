"""Tests for REDDOG_MERGE_AUTHORITY_DRYRUN_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_merge_authority_dryrun import (
    FAIL_CI_STATUS,
    FAIL_CONSENSUS_REQUIRED,
    FAIL_DIFF_SUMMARY,
    FAIL_EXPIRY,
    FAIL_HEAD_SHA,
    FAIL_HOLOINDEX_FRESHNESS_RECEIPT,
    FAIL_HOLOINDEX_INDEX_GAP,
    FAIL_MERGE_METHOD,
    FAIL_NONCE,
    FAIL_PERMISSION_SNAPSHOT,
    FAIL_POLICY_TIER,
    FAIL_PR_IDENTITY,
    FAIL_PROTECTED_SURFACE,
    FAIL_RECEIPT_CHAIN,
    FAIL_REQUIRED_FIELD,
    FAIL_REVIEW_OPINIONS,
    FAIL_SECRET_IN_REQUEST,
    FAIL_SELF_PROMOTION,
    FAIL_SHELL_RECEIPTS,
    FAIL_SIGNED_AUTHORITY,
    FAIL_SIGNING_KEY_REUSE,
    FAIL_WORKTREE_RECEIPT,
    MERGE_AUTHORITY_ACCEPT,
    MERGE_AUTHORITY_REJECT,
    plan_reddog_merge_authority_dry_run,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_merge_authority_dryrun.py"
)

_HEAD = "a" * 40
_DIGEST = "sha256:" + "1" * 64


def valid_request() -> dict:
    return {
        "merge_request_id": "merge-1",
        "work_order_id": "wo-1",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "pr_number": 960,
        "base_ref": "main",
        "head_ref": "feat/example",
        "head_sha": _HEAD,
        "author_principal_id": "github:author",
        "author_reddog_id": "reddog:author",
        "promoter_principal_id": "github:promoter",
        "promoter_reddog_id": "reddog:promoter",
        "signed_work_authority_digest": _DIGEST,
        "signed_receipt_chain_terminal_hash": "sha256:" + "2" * 64,
        "worktree_write_receipt_digest": "sha256:" + "3" * 64,
        "shell_run_receipt_digests": ["sha256:" + "4" * 64],
        "ci_status": {
            "head_sha": _HEAD,
            "status": "success",
            "ci_status_digest": "sha256:" + "5" * 64,
            "required_checks": [
                {"name": "test (3.12)", "head_sha": _HEAD, "conclusion": "success"},
                {"name": "security", "head_sha": _HEAD, "conclusion": "success"},
                {"name": "redteam observation", "head_sha": _HEAD, "conclusion": "skipped_report_only"},
            ],
        },
        "diff_summary": {
            "source": "machine_derived",
            "red_dog_prose_source": False,
            "diff_summary_digest": "sha256:" + "6" * 64,
            "changed_paths": ["modules/communication/moltbot_bridge/src/example.py"],
        },
        "review_opinions": [
            {
                "accepted": True,
                "review_opinion_digest": "sha256:" + "7" * 64,
                "reviewer_principal_id": "github:reviewer",
                "reviewer_reddog_id": "reddog:reviewer",
                "reviewer_key_fingerprint": "key-reviewer",
                "lane_id": "sentinel",
            }
        ],
        "consensus_receipt_digest": "sha256:" + "8" * 64,
        "holoindex_evidence": {
            "index_gap_detected": False,
            "holoindex_freshness_receipt_digest": "sha256:" + "9" * 64,
        },
        "permission_snapshot_digest": "sha256:" + "a" * 64,
        "policy_tier": "f0_sovereign",
        "requested_merge_method": "squash",
        "expiry": "2099-01-01T00:00:00Z",
        "nonce": "merge-nonce-1",
        "author_lane_id": "author",
        "promoter_signature_digest": "sha256:" + "b" * 64,
        "author_key_fingerprint": "key-author",
        "promoter_key_fingerprint": "key-promoter",
        "now": "2026-07-12T00:00:00Z",
    }


def assert_reject(req: dict, code: str) -> None:
    result = plan_reddog_merge_authority_dry_run(req)
    assert result.accepted is False
    assert result.decision.decision == MERGE_AUTHORITY_REJECT
    assert code in result.decision.rejection_reasons
    assert result.no_execution_performed is True
    assert result.no_github_call_performed is True
    assert result.no_merge_performed is True
    assert result.decision.no_merge_performed is True


def test_merge_authority_dryrun_accepts_complete_f0_packet() -> None:
    result = plan_reddog_merge_authority_dry_run(valid_request())

    assert result.accepted is True
    assert result.decision.decision == MERGE_AUTHORITY_ACCEPT
    assert result.decision.rejection_reasons == []
    assert result.decision.expected_head_sha == _HEAD
    assert result.decision.merge_method == "squash"
    assert result.decision.ci_status_digest == "sha256:" + "5" * 64
    assert result.decision.machine_diff_summary_digest == "sha256:" + "6" * 64
    assert result.decision.holoindex_freshness_receipt_digest == "sha256:" + "9" * 64
    assert result.decision.no_reward_settlement_performed is True
    assert result.decision.no_holoindex_reindex_performed is True


def test_docs_only_non_protected_can_skip_consensus() -> None:
    req = valid_request()
    req["policy_tier"] = "docs_only"
    req["consensus_receipt_digest"] = None
    req["diff_summary"]["changed_paths"] = ["docs/audits/example.md"]

    result = plan_reddog_merge_authority_dry_run(req)

    assert result.accepted is True
    assert result.decision.consensus_receipt_digest is None


def test_rejects_missing_required_field() -> None:
    req = valid_request()
    req["repo_full_name"] = ""
    assert_reject(req, FAIL_REQUIRED_FIELD)


def test_rejects_invalid_pr_or_same_head_base() -> None:
    req = valid_request()
    req["pr_number"] = 0
    assert_reject(req, FAIL_PR_IDENTITY)

    req = valid_request()
    req["head_ref"] = "main"
    assert_reject(req, FAIL_PR_IDENTITY)


def test_rejects_invalid_head_sha() -> None:
    req = valid_request()
    req["head_sha"] = "not-sha"
    assert_reject(req, FAIL_HEAD_SHA)


def test_rejects_invalid_merge_method_and_policy_tier() -> None:
    req = valid_request()
    req["requested_merge_method"] = "octopus"
    assert_reject(req, FAIL_MERGE_METHOD)

    req = valid_request()
    req["policy_tier"] = "admin_everything"
    assert_reject(req, FAIL_POLICY_TIER)


def test_rejects_self_promotion_for_f0() -> None:
    req = valid_request()
    req["promoter_principal_id"] = req["author_principal_id"]
    assert_reject(req, FAIL_SELF_PROMOTION)

    req = valid_request()
    req["promoter_reddog_id"] = req["author_reddog_id"]
    assert_reject(req, FAIL_SELF_PROMOTION)


def test_rejects_signing_key_reuse() -> None:
    req = valid_request()
    req["promoter_key_fingerprint"] = req["author_key_fingerprint"]
    assert_reject(req, FAIL_SIGNING_KEY_REUSE)


def test_rejects_bad_authority_and_receipt_digests() -> None:
    req = valid_request()
    req["signed_work_authority_digest"] = "bad"
    req["promoter_signature_digest"] = "bad"
    result = plan_reddog_merge_authority_dry_run(req)
    assert FAIL_SIGNED_AUTHORITY in result.decision.rejection_reasons

    req = valid_request()
    req["signed_receipt_chain_terminal_hash"] = "bad"
    assert_reject(req, FAIL_RECEIPT_CHAIN)

    req = valid_request()
    req["worktree_write_receipt_digest"] = "bad"
    assert_reject(req, FAIL_WORKTREE_RECEIPT)


def test_rejects_missing_shell_receipts_and_permission_snapshot() -> None:
    req = valid_request()
    req["shell_run_receipt_digests"] = []
    assert_reject(req, FAIL_SHELL_RECEIPTS)

    req = valid_request()
    req["permission_snapshot_digest"] = ""
    assert_reject(req, FAIL_PERMISSION_SNAPSHOT)


def test_rejects_ci_head_mismatch_failure_or_missing_checks() -> None:
    req = valid_request()
    req["ci_status"]["head_sha"] = "b" * 40
    assert_reject(req, FAIL_CI_STATUS)

    req = valid_request()
    req["ci_status"]["required_checks"][0]["conclusion"] = "failure"
    assert_reject(req, FAIL_CI_STATUS)

    req = valid_request()
    req["ci_status"]["required_checks"] = []
    assert_reject(req, FAIL_CI_STATUS)


def test_rejects_diff_summary_from_reddog_prose_or_missing_paths() -> None:
    req = valid_request()
    req["diff_summary"]["source"] = "reddog_prose"
    assert_reject(req, FAIL_DIFF_SUMMARY)

    req = valid_request()
    req["diff_summary"]["changed_paths"] = []
    assert_reject(req, FAIL_DIFF_SUMMARY)


def test_rejects_missing_or_self_review_opinion() -> None:
    req = valid_request()
    req["review_opinions"] = []
    assert_reject(req, FAIL_REVIEW_OPINIONS)

    req = valid_request()
    req["review_opinions"][0]["reviewer_reddog_id"] = req["author_reddog_id"]
    assert_reject(req, FAIL_REVIEW_OPINIONS)

    req = valid_request()
    req["review_opinions"][0]["lane_id"] = req["author_lane_id"]
    assert_reject(req, FAIL_REVIEW_OPINIONS)


def test_rejects_missing_consensus_for_high_authority_or_protected_surface() -> None:
    req = valid_request()
    req["consensus_receipt_digest"] = None
    assert_reject(req, FAIL_CONSENSUS_REQUIRED)

    req = valid_request()
    req["policy_tier"] = "docs_only"
    req["consensus_receipt_digest"] = None
    req["diff_summary"]["changed_paths"] = ["WSP_framework/src/WSP_97.md"]
    result = plan_reddog_merge_authority_dry_run(req)
    assert FAIL_CONSENSUS_REQUIRED in result.decision.rejection_reasons
    assert FAIL_PROTECTED_SURFACE in result.decision.rejection_reasons


def test_rejects_holoindex_gap_or_missing_freshness() -> None:
    req = valid_request()
    req["holoindex_evidence"] = {"index_gap_detected": True}
    result = plan_reddog_merge_authority_dry_run(req)
    assert FAIL_HOLOINDEX_INDEX_GAP in result.decision.rejection_reasons
    assert FAIL_HOLOINDEX_FRESHNESS_RECEIPT in result.decision.rejection_reasons


def test_rejects_expired_or_missing_nonce() -> None:
    req = valid_request()
    req["expiry"] = "2020-01-01T00:00:00Z"
    assert_reject(req, FAIL_EXPIRY)

    req = valid_request()
    req["nonce"] = ""
    assert_reject(req, FAIL_NONCE)


def test_rejects_secret_like_content() -> None:
    req = valid_request()
    req["diff_summary"]["changed_paths"] = ["docs/token=abc.md"]
    assert_reject(req, FAIL_SECRET_IN_REQUEST)


def test_result_is_json_serializable() -> None:
    result = plan_reddog_merge_authority_dry_run(valid_request())
    payload = result.to_dict()

    json.dumps(payload, sort_keys=True)
    assert payload["accepted"] is True
    assert payload["decision"]["no_merge_performed"] is True


def test_merge_authority_dryrun_module_ast_forbids_runtime_merge_surfaces() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_imports = {"subprocess", "os", "shutil", "requests", "github"}
    banned_calls = {
        "open",
        "exec",
        "eval",
        "mkdir",
        "write_text",
        "write_bytes",
        "run",
        "Popen",
        "call",
        "check_call",
        "check_output",
        "create_pull_request",
        "merge_pull_request",
        "enable_auto_merge",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported = {alias.name.split(".")[0] for alias in node.names}
            assert imported.isdisjoint(banned_imports)
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in banned_imports
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_calls


def test_merge_authority_dryrun_module_ascii_only() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    assert [hex(ord(ch)) for ch in text if ord(ch) > 127] == []
