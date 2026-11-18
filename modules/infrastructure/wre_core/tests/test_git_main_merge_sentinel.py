"""Tests for the legacy startup interface to Git lifecycle reconciliation."""

from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import Mock

import pytest

from modules.infrastructure.wre_core.src import git_main_merge_sentinel as sentinel


_LIFECYCLE = "modules.infrastructure.wre_core.src.git_lifecycle"


@pytest.fixture(autouse=True)
def isolate_sentinel(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("GIT_MAIN_MERGE_SENTINEL", "GIT_MAIN_MERGE_SENTINEL_ENFORCED"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def reconcile(monkeypatch: pytest.MonkeyPatch) -> Mock:
    lifecycle = ModuleType(_LIFECYCLE)
    lifecycle.reconcile_git_lifecycle = Mock(
        return_value={"coverage": "complete", "reason": None},
    )
    monkeypatch.setitem(sys.modules, _LIFECYCLE, lifecycle)
    return lifecycle.reconcile_git_lifecycle


def test_disabled_skips_without_loading_lifecycle(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setitem(sys.modules, _LIFECYCLE, None)
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL_ENFORCED", "1")

    assert sentinel.run_main_merge_sentinel(tmp_path) == {
        "passed": True,
        "merged": False,
        "branch": None,
        "actions": ["skip (disabled)"],
        "error": None,
    }


@pytest.mark.parametrize("force", [False, True], ids=["enabled", "forced"])
def test_delegates_without_synchronizing_or_merging(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, reconcile: Mock, force: bool,
):
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL", "0" if force else "1")
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL_ENFORCED", "1")
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL_DELETE_BRANCH", "1")

    assert sentinel.run_main_merge_sentinel(tmp_path, force=force) == {
        "passed": True,
        "merged": False,
        "branch": None,
        "actions": ["checked git lifecycle (complete)"],
        "error": None,
    }
    reconcile.assert_called_once_with(tmp_path, synchronize_pc=False)


@pytest.mark.parametrize("enforced", [False, True], ids=["advisory", "enforced"])
@pytest.mark.parametrize(
    ("receipt", "reason"),
    [
        ({"coverage": "partial", "reason": "github_page_limit"}, "github_page_limit"),
        ({"coverage": "unavailable"}, "git_lifecycle_coverage_unavailable"),
        ({}, "git_lifecycle_coverage_unavailable"),
    ],
    ids=["partial", "unavailable", "missing_coverage"],
)
def test_coverage_failures_respect_enforcement(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, reconcile: Mock,
    enforced: bool, receipt: dict, reason: str,
):
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL_ENFORCED", str(int(enforced)))
    reconcile.return_value = receipt

    result = sentinel.run_main_merge_sentinel(tmp_path, force=True)

    assert result["passed"] is (not enforced)
    assert result["merged"] is False
    assert result["error"] == reason
    reconcile.assert_called_once_with(tmp_path, synchronize_pc=False)


def test_reconciliation_exception_returns_stable_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, reconcile: Mock,
):
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL_ENFORCED", "1")
    reconcile.side_effect = RuntimeError("unfiltered provider response")

    result = sentinel.run_main_merge_sentinel(tmp_path, force=True)

    assert result["passed"] is False
    assert result["merged"] is False
    assert result["error"] == "git_lifecycle_reconciliation_failed"
