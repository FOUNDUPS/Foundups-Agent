from __future__ import annotations

import pytest

from modules.infrastructure.wre_core.src.wre_test_scope_coverage import (
    FAIL_CHANGED_PATHS,
    FAIL_COVERAGE,
    FAIL_POLICY_DOWNGRADE,
    FAIL_SELECTION,
    resolve_test_scope_coverage,
)


def resolve(paths, impact, selection):
    return resolve_test_scope_coverage(paths, impact, selection)


def test_one_module_test_file_is_isolated() -> None:
    result = resolve(
        ["modules/communication/demo/tests/test_api.py"],
        "ISOLATED",
        ["modules/communication/demo/tests/test_api.py", "-q"],
    )
    assert result.accepted is True
    assert result.minimum_impact == "ISOLATED"
    assert result.required_suite_kind == "FOCUSED"


@pytest.mark.parametrize(
    "changed,root",
    [
        (["modules/communication/demo/src/api.py"], "modules/communication/demo"),
        (["extensions/reddog/extension.js"], "extensions/reddog"),
        ([
            "modules/communication/demo/tests/test_a.py",
            "modules/communication/demo/tests/test_b.py",
        ], "modules/communication/demo"),
    ],
)
def test_module_changes_require_whole_module_tests(changed, root) -> None:
    result = resolve(changed, "MODULAR", [f"{root}/tests", "--tb=short"])
    assert result.accepted is True
    assert result.minimum_impact == "MODULAR"
    assert result.required_suite_kind == "MODULE_CLOSURE"
    assert result.module_root == root


@pytest.mark.parametrize(
    "changed",
    [
        ["main.py"],
        ["WSP_framework/src/WSP_5_Test_Coverage_Enforcement_Protocol.md"],
        ["holo_index/holo_index.py"],
        ["modules/infrastructure/shared_utilities/runtime_artifact_safety.py"],
        ["modules/infrastructure/wre_core/src/pattern_memory.py"],
        [
            "modules/communication/demo/src/api.py",
            "modules/infrastructure/database/src/agent_db.py",
        ],
    ],
)
def test_shared_protected_top_level_and_multiple_roots_are_systemic(changed) -> None:
    result = resolve(changed, "SYSTEMIC", [".", "-q"])
    assert result.accepted is True
    assert result.minimum_impact == "SYSTEMIC"
    assert result.required_suite_kind == "FULL_REPOSITORY"


def test_policy_can_escalate_but_never_downgrade() -> None:
    changed = ["modules/communication/demo/tests/test_api.py"]
    escalated = resolve(changed, "MODULAR", ["modules/communication/demo/tests"])
    assert escalated.accepted is True
    downgraded = resolve(
        ["modules/communication/demo/src/api.py"],
        "ISOLATED",
        ["modules/communication/demo/tests/test_api.py"],
    )
    assert downgraded.accepted is False
    assert downgraded.effective_impact == "SYSTEMIC"
    assert FAIL_POLICY_DOWNGRADE in downgraded.rejection_reasons


def test_noncovering_module_and_systemic_selection_fail_full() -> None:
    modular = resolve(
        ["modules/communication/demo/src/api.py"],
        "MODULAR",
        ["modules/communication/demo/tests/test_api.py"],
    )
    systemic = resolve(["main.py"], "SYSTEMIC", ["tests"])
    for result in (modular, systemic):
        assert result.accepted is False
        assert result.required_suite_kind == "FULL_REPOSITORY"
        assert FAIL_COVERAGE in result.rejection_reasons


@pytest.mark.parametrize(
    "selection",
    [
        ["C:/repo/tests"], ["/repo/tests"], ["../tests"], ["tests/../other"],
        ["tests", "--rootdir=repo"], ["tests", "--pyargs"],
        ["tests", "-k", "fast"], ["tests", "-m", "unit"],
        ["tests", "--ignore=slow"], ["tests", "--deselect=x"],
        ["tests", "--lf"], ["tests", "--ff"],
        ["tests", "--maxfail=1"], ["tests", "-x"],
        ["tests", "--unknown"], ["tests", "--tb=unknown"],
        ["tests/test_api.py::test_one"], ["@selection.txt"], ["tests/test_*.py"],
    ],
)
def test_unsafe_filters_and_unknown_args_reject(selection) -> None:
    result = resolve(["main.py"], "SYSTEMIC", selection)
    assert result.accepted is False
    assert result.required_suite_kind == "FULL_REPOSITORY"
    assert FAIL_SELECTION in result.rejection_reasons


@pytest.mark.parametrize(
    "changed",
    [
        [], {"main.py": True}, {"main.py"}, ["../module/test.py"],
        ["C:/repo/test.py"], ["module/file.py"], ["main.py", "main.py"],
    ],
)
def test_missing_ambiguous_or_invalid_changed_paths_fail_full(changed) -> None:
    result = resolve(changed, "SYSTEMIC", ["."])
    assert result.accepted is False
    assert result.required_suite_kind == "FULL_REPOSITORY"
    assert FAIL_CHANGED_PATHS in result.rejection_reasons


def test_unordered_or_mapping_selection_fails_closed() -> None:
    for selection in ({".": True}, {"."}):
        result = resolve(["main.py"], "SYSTEMIC", selection)
        assert result.accepted is False
        assert FAIL_SELECTION in result.rejection_reasons


def test_result_is_deterministic_and_detached() -> None:
    changed = ["modules/communication/demo/src/b.py", "modules/communication/demo/src/a.py"]
    selection = ["modules/communication/demo/tests", "-q"]
    first = resolve(changed, "MODULAR", selection)
    changed.reverse()
    selection.reverse()
    assert first == resolve(changed, "MODULAR", selection)
    assert first.to_dict()["selection_paths"] == ("modules/communication/demo/tests",)
