"""Tests for WRE_AUTONOMOUS_SLICE_VERIFIER_RUNTIME_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_work_authority_digest import (
    canonical_work_authority_digest,
)
from modules.infrastructure.wre_core.src import (
    wre_autonomous_slice_verifier_runtime as verifier,
)

BASE_SHA = "b" * 40
HEAD_SHA = "a" * 40
PATH = "modules/communication/moltbot_bridge/tests/fixtures/reddog_pilot/README.md"


def _digest(ch: str) -> str:
    return "sha256:" + ch * 64


def _resign_authority(req: dict) -> dict:
    authority = req["signed_authority"]
    work_authority = {
        key: value
        for key, value in authority.items()
        if key
        not in {
            "accepted",
            "signature_gate_digest",
            "signed_work_authority_digest",
        }
    }
    authority["signature_gate_digest"] = canonical_work_authority_digest(
        work_authority
    )
    return req


def valid_request() -> dict:
    request = {
        "work_order_id": "wo-autonomous-verify-1",
        "slice_name": "WRE_AUTONOMOUS_SLICE_VERIFIER_RUNTIME_PHASE1",
        "worker_id": "worker:author-1",
        "verifier_id": "worker:verifier-1",
        "assurance_reservation_id": "assurance-reservation-" + "1" * 20,
        "assurance_reservation_digest": _digest("0"),
        "verifier_task_id": "reddog-worker-dispatch-" + "2" * 16,
        "base_sha": BASE_SHA,
        "head_sha": HEAD_SHA,
        "allowed_path_patterns": [
            "modules/communication/moltbot_bridge/tests/fixtures/reddog_pilot/**"
        ],
        "expected_changed_paths": [PATH],
        "forbidden_path_patterns": ["**/.env", "**/secrets/**"],
        "diff_evidence": {
            "source": "machine_derived",
            "red_dog_prose_source": False,
            "base_sha": BASE_SHA,
            "head_sha": HEAD_SHA,
            "diff_digest": _digest("1"),
            "changed_paths": [PATH],
            "added_lines": ["bounded pilot fixture update"],
        },
        "test_evidence": {
            "head_sha": HEAD_SHA,
            "test_evidence_digest": _digest("2"),
            "required_checks": [
                {
                    "name": "pytest",
                    "head_sha": HEAD_SHA,
                    "conclusion": "success",
                },
                {
                    "name": "security",
                    "head_sha": HEAD_SHA,
                    "conclusion": "pass",
                },
            ],
        },
        "signed_authority": {
            "accepted": True,
            "authority_id": "authority-1",
            "work_order_id": "wo-autonomous-verify-1",
        },
        "signed_receipt_chain": {
            "accepted": True,
            "terminal_receipt_hash": _digest("4"),
        },
        "worktree_receipt": {
            "accepted": True,
            "receipt_digest": _digest("5"),
        },
        "bounded_worker_pilot_receipt": {
            "accepted": True,
            "receipt_id": "bounded_wt_pilot_1234",
        },
        "holoindex_evidence": {
            "index_gap_detected": False,
            "holoindex_freshness_receipt_digest": _digest("6"),
        },
        "pattern_memory_write_performed": False,
        "draft_pr_published": False,
        "merge_performed": False,
    }
    return _resign_authority(request)


def assert_reject(req: dict, code: str) -> None:
    result = verifier.verify_autonomous_slice_runtime(req)
    assert result.accepted is False
    assert result.decision == verifier.AUTONOMOUS_SLICE_VERIFIER_REJECT
    assert code in result.rejection_reasons
    assert code in result.receipt.rejection_reasons
    assert result.no_execution_performed is True
    assert result.no_command_execution_performed is True
    assert result.no_github_call_performed is True
    assert result.no_pr_publish_performed is True
    assert result.no_merge_performed is True
    assert result.no_pattern_memory_write_performed is True


def test_accepts_complete_machine_derived_slice_packet() -> None:
    result = verifier.verify_autonomous_slice_runtime(valid_request())

    assert result.accepted is True
    assert result.decision == verifier.AUTONOMOUS_SLICE_VERIFIER_ACCEPT
    assert result.rejection_reasons == []
    assert result.receipt.changed_paths == [PATH]
    assert result.receipt.diff_digest == _digest("1")
    assert result.receipt.test_evidence_digest == _digest("2")
    assert result.receipt.signed_authority_digest == (
        valid_request()["signed_authority"]["signature_gate_digest"]
    )
    assert result.receipt.receipt_chain_terminal_hash == _digest("4")
    assert result.receipt.worktree_receipt_digest == _digest("5")
    assert result.receipt.holoindex_freshness_receipt_digest == _digest("6")
    assert result.receipt.model_runtime_binding_receipt_id is None
    assert result.receipt.model_runtime_binding_digest == ""
    assert result.receipt.memex_supply_receipt_id is None
    assert result.receipt.memex_supply_digest == ""
    assert result.receipt.no_command_execution_performed is True
    assert result.receipt.no_pr_publish_performed is True
    assert result.receipt.no_pattern_memory_write_performed is True


def test_carries_model_runtime_binding_from_signed_authority() -> None:
    req = valid_request()
    req["signed_authority"]["model_runtime_binding_receipt_id"] = (
        "reddog_model_runtime_binding:test"
    )
    req["signed_authority"]["model_runtime_binding_digest"] = _digest("7")
    _resign_authority(req)

    result = verifier.verify_autonomous_slice_runtime(req)

    assert result.accepted is True
    assert (
        result.receipt.model_runtime_binding_receipt_id
        == "reddog_model_runtime_binding:test"
    )
    assert result.receipt.model_runtime_binding_digest == _digest("7")


def test_rejects_conflicting_or_one_sided_model_runtime_binding() -> None:
    req = valid_request()
    req["signed_authority"]["model_runtime_binding_receipt_id"] = (
        "reddog_model_runtime_binding:test"
    )
    _resign_authority(req)
    assert_reject(req, verifier.FAIL_MODEL_RUNTIME_BINDING)

    req = valid_request()
    req["signed_authority"]["model_runtime_binding_receipt_id"] = (
        "reddog_model_runtime_binding:test"
    )
    req["signed_authority"]["model_runtime_binding_digest"] = _digest("7")
    _resign_authority(req)
    req["artifact_generation_receipt"] = {
        "model_runtime_binding_receipt_id": "reddog_model_runtime_binding:test",
        "model_runtime_binding_digest": _digest("8"),
    }
    assert_reject(req, verifier.FAIL_MODEL_RUNTIME_BINDING)


def test_carries_memex_binding_and_binds_it_into_verifier_receipt() -> None:
    req = valid_request()
    req["signed_authority"]["memex_supply_receipt_id"] = "memex-supply-receipt-1"
    req["signed_authority"]["memex_supply_digest"] = _digest("7")
    _resign_authority(req)

    result = verifier.verify_autonomous_slice_runtime(req)
    without_memex = verifier.verify_autonomous_slice_runtime(valid_request())

    assert result.accepted is True
    assert result.receipt.memex_supply_receipt_id == "memex-supply-receipt-1"
    assert result.receipt.memex_supply_digest == _digest("7")
    assert result.receipt.receipt_id != without_memex.receipt.receipt_id


def test_rejects_malformed_half_or_conflicting_memex_binding() -> None:
    req = valid_request()
    req["signed_authority"]["memex_supply_receipt_id"] = "memex-supply-receipt-1"
    _resign_authority(req)
    assert_reject(req, verifier.FAIL_MEMEX_SUPPLY_BINDING)

    req = valid_request()
    req["signed_authority"]["memex_supply_receipt_id"] = "memex-supply-receipt-1"
    req["signed_authority"]["memex_supply_digest"] = "sha256:not-a-digest"
    _resign_authority(req)
    assert_reject(req, verifier.FAIL_MEMEX_SUPPLY_BINDING)

    req = valid_request()
    req["signed_authority"]["memex_supply_receipt_id"] = "memex-supply-receipt-1"
    req["signed_authority"]["memex_supply_digest"] = _digest("7")
    _resign_authority(req)
    req["artifact_generation_receipt"] = {
        "memex_supply_receipt_id": "memex-supply-receipt-1",
        "memex_supply_digest": _digest("8"),
    }
    assert_reject(req, verifier.FAIL_MEMEX_SUPPLY_BINDING)


def test_rejects_post_signing_memex_substitution() -> None:
    req = valid_request()
    req["signed_authority"]["memex_supply_receipt_id"] = "memex-supply-attacker"
    req["signed_authority"]["memex_supply_digest"] = _digest("7")

    assert_reject(req, verifier.FAIL_SIGNED_AUTHORITY)


def test_rejects_falsy_non_string_memex_bindings() -> None:
    for receipt_id, digest in (
        (False, _digest("7")),
        (0, _digest("7")),
        ([], _digest("7")),
        ("memex-supply-receipt-1", False),
        ("memex-supply-receipt-1", 0),
        ("memex-supply-receipt-1", []),
    ):
        req = valid_request()
        req["signed_authority"]["memex_supply_receipt_id"] = receipt_id
        req["signed_authority"]["memex_supply_digest"] = digest
        _resign_authority(req)
        assert_reject(req, verifier.FAIL_MEMEX_SUPPLY_BINDING)


def test_rejects_missing_identity_and_self_verification() -> None:
    req = valid_request()
    req["slice_name"] = ""
    assert_reject(req, verifier.FAIL_REQUIRED_FIELD)

    req = valid_request()
    req["verifier_id"] = req["worker_id"]
    assert_reject(req, verifier.FAIL_SELF_VERIFICATION)


def test_rejects_invalid_or_equal_head_base_sha() -> None:
    req = valid_request()
    req["head_sha"] = "not-a-sha"
    assert_reject(req, verifier.FAIL_HEAD_SHA)

    req = valid_request()
    req["base_sha"] = req["head_sha"]
    assert_reject(req, verifier.FAIL_HEAD_SHA)


def test_rejects_reddog_prose_or_stale_diff_evidence() -> None:
    req = valid_request()
    req["diff_evidence"]["source"] = "reddog_summary"
    assert_reject(req, verifier.FAIL_DIFF_EVIDENCE)

    req = valid_request()
    req["diff_evidence"]["red_dog_prose_source"] = True
    assert_reject(req, verifier.FAIL_DIFF_EVIDENCE)

    req = valid_request()
    req["diff_evidence"]["head_sha"] = "c" * 40
    assert_reject(req, verifier.FAIL_DIFF_EVIDENCE)


def test_rejects_scope_mismatch_and_forbidden_paths() -> None:
    req = valid_request()
    req["diff_evidence"]["changed_paths"] = ["modules/other/outside.py"]
    assert_reject(req, verifier.FAIL_SCOPE_VIOLATION)

    req = valid_request()
    req["diff_evidence"]["changed_paths"] = [PATH, "modules/other/outside.py"]
    assert_reject(req, verifier.FAIL_SCOPE_VIOLATION)

    req = valid_request()
    req["diff_evidence"]["changed_paths"] = [
        "modules/communication/moltbot_bridge/tests/fixtures/reddog_pilot/.env"
    ]
    req["expected_changed_paths"] = req["diff_evidence"]["changed_paths"]
    assert_reject(req, verifier.FAIL_SCOPE_VIOLATION)


def test_rejects_protected_surface_without_consensus_and_accepts_with_escalation() -> None:
    req = valid_request()
    protected = "holo_index/docs/command_rolodex.json"
    req["diff_evidence"]["changed_paths"] = [protected]
    req["expected_changed_paths"] = [protected]
    req["allowed_path_patterns"] = ["holo_index/docs/**"]
    assert_reject(req, verifier.FAIL_PROTECTED_SURFACE)

    req["protected_surface_authorization_digest"] = _digest("7")
    req["consensus_receipt_digest"] = _digest("8")
    result = verifier.verify_autonomous_slice_runtime(req)
    assert result.accepted is True


def test_rejects_secret_bearing_diff_content() -> None:
    req = valid_request()
    req["diff_evidence"]["added_lines"] = ["api_key = 'leak'"]
    assert_reject(req, verifier.FAIL_SECRET_IN_DIFF)


def test_rejects_missing_failing_or_stale_test_evidence() -> None:
    req = valid_request()
    req["test_evidence"]["required_checks"] = []
    assert_reject(req, verifier.FAIL_TEST_EVIDENCE)

    req = valid_request()
    req["test_evidence"]["required_checks"][0]["conclusion"] = "failure"
    assert_reject(req, verifier.FAIL_TEST_EVIDENCE)

    req = valid_request()
    req["test_evidence"]["head_sha"] = "c" * 40
    assert_reject(req, verifier.FAIL_TEST_EVIDENCE)


def test_rejects_unsigned_authority_or_receipt_chain() -> None:
    req = valid_request()
    req["signed_authority"]["accepted"] = False
    assert_reject(req, verifier.FAIL_SIGNED_AUTHORITY)

    req = valid_request()
    req["signed_authority"]["signature_gate_digest"] = "bad"
    assert_reject(req, verifier.FAIL_SIGNED_AUTHORITY)

    req = valid_request()
    req["signed_authority"]["signed_work_authority_digest"] = _digest("f")
    assert_reject(req, verifier.FAIL_SIGNED_AUTHORITY)

    req = valid_request()
    req["signed_receipt_chain"]["accepted"] = False
    assert_reject(req, verifier.FAIL_RECEIPT_CHAIN)

    req = valid_request()
    req["signed_receipt_chain"]["terminal_receipt_hash"] = "bad"
    assert_reject(req, verifier.FAIL_RECEIPT_CHAIN)


def test_rejects_worktree_or_bounded_pilot_receipt_failure() -> None:
    req = valid_request()
    req["worktree_receipt"]["accepted"] = False
    assert_reject(req, verifier.FAIL_WORKTREE_RECEIPT)

    req = valid_request()
    req["worktree_receipt"]["receipt_digest"] = ""
    assert_reject(req, verifier.FAIL_WORKTREE_RECEIPT)

    req = valid_request()
    req["bounded_worker_pilot_receipt"]["accepted"] = False
    assert_reject(req, verifier.FAIL_WORKTREE_RECEIPT)


def test_rejects_holoindex_gap_or_missing_freshness_receipt() -> None:
    req = valid_request()
    req["holoindex_evidence"]["index_gap_detected"] = True
    assert_reject(req, verifier.FAIL_HOLOINDEX_EVIDENCE)

    req = valid_request()
    req["holoindex_evidence"]["retrieval_quality"] = "INDEX_GAP"
    assert_reject(req, verifier.FAIL_HOLOINDEX_EVIDENCE)

    req = valid_request()
    req["holoindex_evidence"]["holoindex_freshness_receipt_digest"] = ""
    assert_reject(req, verifier.FAIL_HOLOINDEX_EVIDENCE)


def test_rejects_pattern_memory_write_or_pr_publish_before_acceptance() -> None:
    req = valid_request()
    req["pattern_memory_write_performed"] = True
    assert_reject(req, verifier.FAIL_PATTERN_MEMORY_WRITE)

    req = valid_request()
    req["draft_pr_published"] = True
    assert_reject(req, verifier.FAIL_PR_OR_MERGE_ALREADY_PERFORMED)

    req = valid_request()
    req["merge_performed"] = True
    assert_reject(req, verifier.FAIL_PR_OR_MERGE_ALREADY_PERFORMED)


def test_receipt_is_deterministic_and_json_serializable() -> None:
    first = verifier.verify_autonomous_slice_runtime(valid_request())
    second = verifier.verify_autonomous_slice_runtime(valid_request())

    assert first.receipt.receipt_id == second.receipt.receipt_id
    dumped = json.dumps(first.to_dict(), sort_keys=True)
    assert "wre_slice_verify_" in dumped


def test_ast_boundary_no_execution_publish_or_memory_write_surface() -> None:
    path = Path("modules/infrastructure/wre_core/src/wre_autonomous_slice_verifier_runtime.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = set()
    calls = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    forbidden_imports = {
        "os",
        "subprocess",
        "socket",
        "requests",
        "sqlite3",
        "modules.infrastructure.wre_core.src.pattern_memory",
    }
    forbidden_calls = {
        "open",
        "eval",
        "exec",
        "system",
        "popen",
        "run",
        "check_call",
        "check_output",
        "store_outcome",
        "gh",
    }

    assert imports.isdisjoint(forbidden_imports)
    assert calls.isdisjoint(forbidden_calls)
