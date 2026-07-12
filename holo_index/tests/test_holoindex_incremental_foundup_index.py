"""Tests for HOLOINDEX_INCREMENTAL_PER_FOUNDUP_INDEX_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from holo_index.incremental_foundup_index import (
    DECISION_NO_INDEXABLE_CHANGES,
    DECISION_PLANNED,
    DECISION_REJECTED,
    OP_DELETE_PATH_ID,
    OP_UPSERT_PATH,
    delete_filter_for_foundup,
    foundup_root_for_id,
    path_is_under_foundup,
    plan_incremental_foundup_index,
    stable_index_id,
    validate_foundup_id,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE = REPO_ROOT / "holo_index" / "incremental_foundup_index.py"


def test_foundup_id_validation_is_strict() -> None:
    assert validate_foundup_id("paccess_001") is True
    assert validate_foundup_id("gotjunk") is True
    assert validate_foundup_id("Bad") is False
    assert validate_foundup_id("../escape") is False
    assert validate_foundup_id("") is False


def test_foundup_root_is_deterministic() -> None:
    assert foundup_root_for_id("paccess_001") == "modules/foundups/paccess_001"
    with pytest.raises(ValueError):
        foundup_root_for_id("../escape")


def test_path_scope_requires_modules_foundups_id() -> None:
    assert path_is_under_foundup(
        "modules/foundups/paccess_001/src/main.py",
        "paccess_001",
    )
    assert not path_is_under_foundup(
        "modules/foundups/other/src/main.py",
        "paccess_001",
    )
    with pytest.raises(ValueError):
        path_is_under_foundup("../modules/foundups/paccess_001/src/main.py", "paccess_001")


def test_stable_id_is_non_positional_and_deterministic() -> None:
    first = stable_index_id(
        "navigation_symbols",
        "modules/foundups/paccess_001/src/main.py",
        foundup_id="paccess_001",
    )
    second = stable_index_id(
        "navigation_symbols",
        "./modules\\foundups\\paccess_001\\src\\main.py",
        foundup_id="paccess_001",
    )

    assert first == second
    assert first.startswith("hidx_nav_symbols_")
    assert "sym_" not in first
    assert "doc_" not in first


def test_stable_id_changes_by_collection_and_symbol() -> None:
    base = stable_index_id(
        "navigation_symbols",
        "modules/foundups/paccess_001/src/main.py",
        foundup_id="paccess_001",
        symbol="create_foundup",
    )
    other_symbol = stable_index_id(
        "navigation_symbols",
        "modules/foundups/paccess_001/src/main.py",
        foundup_id="paccess_001",
        symbol="validate_foundup",
    )
    docs = stable_index_id(
        "navigation_docs",
        "modules/foundups/paccess_001/src/main.py",
        foundup_id="paccess_001",
        symbol="create_foundup",
    )

    assert base != other_symbol
    assert base != docs


def test_delete_filter_is_foundup_scoped_only() -> None:
    assert delete_filter_for_foundup("paccess_001") == {"foundup_id": "paccess_001"}
    with pytest.raises(ValueError):
        delete_filter_for_foundup("bad/id")


def test_plan_maps_changed_foundup_paths_to_collections() -> None:
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=[
            "modules/foundups/paccess_001/src/main.py",
            "modules/foundups/paccess_001/README.md",
            "modules/foundups/paccess_001/tests/test_main.py",
            "modules/foundups/paccess_001/SKILLz.md",
        ],
    )

    assert plan.decision == DECISION_PLANNED
    assert plan.target_collections == [
        "navigation_docs",
        "navigation_skills",
        "navigation_symbols",
        "navigation_tests",
    ]
    assert {operation.operation for operation in plan.operations} == {OP_UPSERT_PATH}
    assert all(operation.delete_where == {"foundup_id": "paccess_001"} for operation in plan.operations)
    assert all(operation.stable_id.startswith("hidx_") for operation in plan.operations)
    assert plan.no_reindex_performed is True
    assert plan.no_collection_mutation_performed is True


def test_plan_dedupes_changed_paths() -> None:
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=[
            "./modules/foundups/paccess_001/src/main.py",
            "modules\\foundups\\paccess_001\\src\\main.py",
        ],
    )

    assert plan.decision == DECISION_PLANNED
    assert plan.changed_paths == ["modules/foundups/paccess_001/src/main.py"]
    assert len(plan.operations) == 1


def test_plan_rejects_out_of_scope_paths() -> None:
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/other/src/main.py"],
    )

    assert plan.decision == DECISION_REJECTED
    assert plan.operations == []
    assert plan.rejection_reasons == [
        "path_outside_foundup_scope:modules/foundups/other/src/main.py"
    ]


def test_plan_rejects_traversal_and_absolute_paths() -> None:
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=[
            "../modules/foundups/paccess_001/src/main.py",
            "C:/repo/modules/foundups/paccess_001/src/main.py",
        ],
    )

    assert plan.decision == DECISION_REJECTED
    assert "path_traversal:../modules/foundups/paccess_001/src/main.py" in plan.rejection_reasons
    assert "absolute_path:C:/repo/modules/foundups/paccess_001/src/main.py" in plan.rejection_reasons


def test_plan_handles_removed_paths_as_delete_id_operations() -> None:
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        removed_paths=[
            "modules/foundups/paccess_001/src/main.py",
            "modules/foundups/paccess_001/README.md",
        ],
    )

    assert plan.decision == DECISION_PLANNED
    assert {operation.operation for operation in plan.operations} == {OP_DELETE_PATH_ID}
    assert plan.target_collections == ["navigation_docs", "navigation_symbols"]


def test_no_indexable_changes_is_explicit_not_successful_reindex() -> None:
    plan = plan_incremental_foundup_index(
        foundup_id="paccess_001",
        changed_paths=["modules/foundups/paccess_001/.gitkeep"],
    )

    assert plan.decision == DECISION_NO_INDEXABLE_CHANGES
    assert plan.operations == []
    assert plan.target_collections == []
    assert plan.no_reindex_performed is True


def test_invalid_foundup_id_rejects_without_normalizing_scope() -> None:
    plan = plan_incremental_foundup_index(
        foundup_id="../paccess_001",
        changed_paths=["modules/foundups/paccess_001/src/main.py"],
    )

    assert plan.decision == DECISION_REJECTED
    assert plan.foundup_root == ""
    assert plan.rejection_reasons == ["invalid_foundup_id"]


def test_module_has_no_live_index_or_subprocess_imports() -> None:
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned_imports = {"subprocess", "requests", "holo_index.core.holo_index"}
    banned_calls = {
        "delete",
        "delete_collection",
        "get_collection",
        "index_code_entries",
        "index_docs_entries",
        "index_symbol_entries",
        "run",
        "system",
    }
    assert ".collection.add(" not in source
    assert "_reset_collection(" not in source
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in banned_imports
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "") not in banned_imports
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in banned_calls
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls
