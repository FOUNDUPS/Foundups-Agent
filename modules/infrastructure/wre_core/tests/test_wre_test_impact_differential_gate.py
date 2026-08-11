from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path

import pytest

from modules.infrastructure.wre_core.src import wre_test_impact_differential_gate as gate


BASE_SHA = "a" * 40
CANDIDATE_SHA = "b" * 40
DIGESTS = ["sha256:" + str(index) * 64 for index in range(1, 10)]


def plan(**updates):
    values = {
        "base_sha": BASE_SHA, "candidate_sha": CANDIDATE_SHA,
        "changed_paths_digest": DIGESTS[0], "impact_class": "MODULAR",
        "suite_scope_digest": DIGESTS[1], "runner_digest": DIGESTS[2],
        "environment_digest": DIGESTS[3], "dependency_lock_digest": DIGESTS[4],
        "selection_policy_digest": DIGESTS[5], "selection_args_digest": DIGESTS[6],
        "base_lineage_receipt_digest": DIGESTS[7],
        "wsp15_allocation_receipt_id": "wsp15-allocation-1",
        "wsp15_allocation_receipt_digest": DIGESTS[8],
        "omitted_scope_rationale": "full suite deferred to promotion",
    }
    values.update(updates)
    return gate.make_test_impact_plan(**values)


def snapshot(sha: str, **updates):
    values = {
        "head_sha": sha, "suite_kind": "MODULE_CLOSURE",
        "suite_scope_digest": DIGESTS[1], "runner_digest": DIGESTS[2],
        "environment_digest": DIGESTS[3], "dependency_lock_digest": DIGESTS[4],
        "selection_policy_digest": DIGESTS[5], "selection_args_digest": DIGESTS[6],
        "base_lineage_receipt_digest": DIGESTS[7],
        "evidence_receipt_id": f"evidence-{sha[:1]}",
        "evidence_receipt_digest": DIGESTS[7] if sha == BASE_SHA else DIGESTS[8],
        "evidence_author_id": "independent-verifier-0102", "independent": True,
        "passed_ids": ["tests/test_a.py::test_a"],
        "failed_ids": ["tests/test_known.py::test_known"],
    }
    values.update(updates)
    return gate.make_test_run_snapshot(**values)


def evaluate(impact_plan, base, candidate):
    return gate.evaluate_test_differential(impact_plan, base, candidate)


def test_same_failures_and_added_passing_tests_are_clean_analysis_only() -> None:
    base = snapshot(BASE_SHA)
    candidate = snapshot(CANDIDATE_SHA, passed_ids=[
        "tests/test_a.py::test_a", "tests/test_new.py::test_new"
    ])
    receipt = evaluate(plan(), base, candidate)
    assert receipt.differential_clean is True
    assert receipt.authority_verified is False
    assert receipt.promotion_authorized is False
    assert receipt.added_passing_tests == ("tests/test_new.py::test_new",)


def test_sha256_object_ids_are_valid_plan_and_snapshot_bindings() -> None:
    base_sha, candidate_sha = "a" * 64, "b" * 64
    impact_plan = plan(base_sha=base_sha, candidate_sha=candidate_sha)
    assert gate.validate_test_impact_plan(impact_plan) == []
    assert snapshot(base_sha)["head_sha"] == base_sha
    assert snapshot(candidate_sha)["head_sha"] == candidate_sha


def test_reported_4618_vs_4589_same_40_failures_is_exactly_proven() -> None:
    passed = [f"tests/test_base.py::test_{index:04d}" for index in range(4589)]
    failed = [f"tests/test_known.py::test_{index:02d}" for index in range(40)]
    added = [f"tests/test_added.py::test_{index:02d}" for index in range(29)]
    receipt = evaluate(
        plan(), snapshot(BASE_SHA, passed_ids=passed, failed_ids=failed),
        snapshot(CANDIDATE_SHA, passed_ids=passed + added, failed_ids=failed),
    )
    assert receipt.differential_clean is True
    assert len(receipt.unchanged_failures) == 40
    assert len(receipt.added_passing_tests) == 29


def test_resolved_failure_means_passed_not_changed_to_error() -> None:
    passed = snapshot(CANDIDATE_SHA, failed_ids=[], passed_ids=[
        "tests/test_a.py::test_a", "tests/test_known.py::test_known"
    ])
    receipt = evaluate(plan(), snapshot(BASE_SHA), passed)
    assert receipt.resolved_failures == ("tests/test_known.py::test_known",)
    error = snapshot(CANDIDATE_SHA, failed_ids=[], error_ids=[
        "tests/test_known.py::test_known"
    ])
    receipt = evaluate(plan(), snapshot(BASE_SHA), error)
    assert receipt.resolved_failures == ()
    assert gate.FAIL_NEW_ERROR in receipt.rejection_reasons


@pytest.mark.parametrize(("field", "reason"), [
    ("failed_ids", gate.FAIL_NEW_FAILURE), ("error_ids", gate.FAIL_NEW_ERROR),
    ("skipped_ids", gate.FAIL_NEW_SKIP), ("xfailed_ids", gate.FAIL_NEW_XFAIL),
    ("xpassed_ids", gate.FAIL_NEW_XPASS), ("deselected_ids", gate.FAIL_NEW_DESELECTION),
])
def test_new_nonpassing_or_unexecuted_state_rejects(field: str, reason: str) -> None:
    receipt = evaluate(
        plan(), snapshot(BASE_SHA),
        snapshot(CANDIDATE_SHA, **{field: [f"tests/test_new.py::{field}"]}),
    )
    assert receipt.differential_clean is False
    assert reason in receipt.rejection_reasons


def test_removed_test_rejects() -> None:
    base = snapshot(BASE_SHA, passed_ids=["tests/test_a.py::test_a", "tests/test_b.py::test_b"])
    candidate = snapshot(CANDIDATE_SHA, passed_ids=["tests/test_a.py::test_a"], failed_ids=[])
    receipt = evaluate(plan(), base, candidate)
    assert gate.FAIL_REMOVED_TEST in receipt.rejection_reasons


@pytest.mark.parametrize("binding", [
    "suite_scope_digest", "runner_digest", "environment_digest",
    "dependency_lock_digest", "selection_policy_digest", "selection_args_digest",
    "base_lineage_receipt_digest",
])
def test_cached_parent_rejects_binding_drift(binding: str) -> None:
    receipt = evaluate(plan(), snapshot(BASE_SHA), snapshot(CANDIDATE_SHA, **{binding: DIGESTS[0]}))
    assert gate.FAIL_BINDING in receipt.rejection_reasons


def test_systemic_and_stale_dependency_plans_derive_full_suite() -> None:
    assert plan(impact_class="SYSTEMIC")["required_suite_kind"] == "FULL_REPOSITORY"
    assert plan(dependency_evidence_stale=True)["required_suite_kind"] == "FULL_REPOSITORY"
    receipt = evaluate(plan(impact_class="SYSTEMIC"), snapshot(BASE_SHA), snapshot(CANDIDATE_SHA))
    assert gate.FAIL_SUITE_SCOPE in receipt.rejection_reasons


def test_full_suite_requires_exact_collection_and_optional_closures() -> None:
    impact_plan = plan(
        impact_class="SYSTEMIC", security_closure_required=True,
        held_out_closure_required=True,
    )
    base = snapshot(BASE_SHA, suite_kind="FULL_REPOSITORY")
    candidate = snapshot(CANDIDATE_SHA, suite_kind="FULL_REPOSITORY")
    receipt = evaluate(impact_plan, base, candidate)
    assert gate.FAIL_SECURITY_CLOSURE in receipt.rejection_reasons
    assert gate.FAIL_HELD_OUT_CLOSURE in receipt.rejection_reasons
    candidate = snapshot(
        CANDIDATE_SHA, suite_kind="FULL_REPOSITORY",
        security_closure_passed=True, held_out_closure_passed=True,
    )
    assert evaluate(impact_plan, base, candidate).differential_clean is True


def test_collection_manifest_and_full_ids_are_integrity_bound() -> None:
    candidate = snapshot(CANDIDATE_SHA)
    candidate["collected_ids"].append("tests/test_attack.py::test_attack")
    receipt = evaluate(plan(), snapshot(BASE_SHA), candidate)
    assert gate.FAIL_SNAPSHOT in receipt.rejection_reasons
    assert len(candidate["snapshot_id"].removeprefix("wre_test_run_")) == 64


@pytest.mark.parametrize("malformed", [None, [], "text", 42])
def test_malformed_top_level_inputs_fail_closed(malformed) -> None:
    receipt = gate.evaluate_test_differential(malformed, malformed, malformed)
    assert receipt.differential_clean is False
    assert gate.FAIL_PLAN in receipt.rejection_reasons
    assert gate.FAIL_SNAPSHOT in receipt.rejection_reasons


def test_tampered_plan_or_snapshot_rejects() -> None:
    impact_plan = plan()
    impact_plan["impact_class"] = "ISOLATED"
    assert gate.FAIL_PLAN in evaluate(
        impact_plan, snapshot(BASE_SHA), snapshot(CANDIDATE_SHA)
    ).rejection_reasons
    candidate = snapshot(CANDIDATE_SHA)
    candidate["failed_ids"].append("tests/test_attack.py::test_attack")
    assert gate.FAIL_SNAPSHOT in evaluate(
        plan(), snapshot(BASE_SHA), candidate
    ).rejection_reasons


def test_unknown_schema_fields_reject_even_when_rehashed() -> None:
    impact_plan = plan()
    impact_plan["caller_extension"] = "ignored"
    impact_plan["plan_id"] = "wre_test_plan_" + gate._digest_hex({
        key: value for key, value in impact_plan.items() if key != "plan_id"
    })
    candidate = snapshot(CANDIDATE_SHA)
    candidate["caller_extension"] = "ignored"
    candidate["snapshot_id"] = "wre_test_run_" + gate._digest_hex({
        key: value for key, value in candidate.items() if key != "snapshot_id"
    })
    receipt = evaluate(impact_plan, snapshot(BASE_SHA), candidate)
    assert gate.FAIL_PLAN in receipt.rejection_reasons
    assert gate.FAIL_SNAPSHOT in receipt.rejection_reasons


def test_receipt_is_deterministic_side_effect_free_and_full_digest() -> None:
    base, candidate = snapshot(BASE_SHA), snapshot(CANDIDATE_SHA)
    first = evaluate(plan(), base, candidate)
    second = evaluate(plan(), deepcopy(base), deepcopy(candidate))
    assert first == second
    assert len(first.receipt_id.removeprefix("wre_test_diff_")) == 64
    assert first.no_test_execution_performed is True
    assert first.no_repository_mutation_performed is True


def test_protocols_bind_wsp15_economics_and_truth_boundary() -> None:
    root = Path(__file__).resolve().parents[4]
    wsp6 = (root / "WSP_framework/src/WSP_6_Test_Audit_Coverage_Verification.md").read_text(encoding="utf-8")
    wsp97 = (root / "WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md").read_text(encoding="utf-8")
    contract = json.loads((root / "WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.json").read_text(encoding="utf-8"))["wsp_97"]
    for phrase in ("Focused inner loop", "Dependency closure", "Parent baseline receipt reuse", "identifiers, not aggregate counts"):
        assert phrase in wsp6
    for phrase in ("Do I need it?", "Can I afford it?", "Can I live without it now?", "SPECIFIED_NOT_IMPLEMENTED"):
        assert phrase in wsp97
    assert contract["version"] == "1.8"


def test_framework_and_knowledge_protocol_mirrors_match() -> None:
    root = Path(__file__).resolve().parents[4]
    for name in (
        "WSP_6_Test_Audit_Coverage_Verification.md",
        "WSP_97_System_Execution_Prompting_Protocol.md",
        "WSP_97_System_Execution_Prompting_Protocol.json",
    ):
        assert (root / "WSP_framework/src" / name).read_bytes() == (root / "WSP_knowledge/src" / name).read_bytes()


def test_analysis_has_no_execution_storage_network_or_mutation_surface() -> None:
    tree = ast.parse(Path(gate.__file__).read_text(encoding="utf-8"))
    banned = {"os", "pathlib", "shutil", "socket", "subprocess", "tempfile"}
    imported = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imported.isdisjoint(banned)
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert calls.isdisjoint({"eval", "exec", "open", "compile", "__import__"})


def test_analysis_respects_wsp62_function_and_class_limits() -> None:
    tree = ast.parse(Path(gate.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            assert node.end_lineno is not None
            assert node.end_lineno - node.lineno + 1 <= 50, node.name
