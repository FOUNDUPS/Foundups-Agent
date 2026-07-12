"""Tests for HOLOINDEX_CI_FRESHNESS_GATE_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from holo_index.ci_freshness_gate import (
    EXIT_OK,
    EXIT_STALE,
    STATUS_FAIL,
    STATUS_NOT_CONFIGURED,
    STATUS_NO_RELEVANT_CHANGES,
    STATUS_PASS,
    check_ci_freshness,
    main,
)
from holo_index.freshness_receipt import (
    build_freshness_receipt,
    freshness_receipt_path,
    write_freshness_receipt,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE = REPO_ROOT / "holo_index" / "ci_freshness_gate.py"


class CountCollection:
    def __init__(self, count: int = 3):
        self._count = count

    def count(self) -> int:
        return self._count


def _holo(**counts: int):
    attr_map = {
        "navigation_code": "code_collection",
        "navigation_wsp": "wsp_collection",
        "navigation_tests": "test_collection",
        "navigation_skills": "skill_collection",
        "navigation_symbols": "symbol_collection",
        "navigation_docs": "docs_collection",
        "navigation_knowledge": "knowledge_collection",
        "navigation_work_ledger": "work_ledger_collection",
        "navigation_vocabulary": "vocabulary_collection",
    }
    values = {}
    for collection_name, attr_name in attr_map.items():
        values[attr_name] = CountCollection(counts.get(collection_name, 3))
    return SimpleNamespace(**values)


def _write_receipt(tmp_path: Path, *, sha: str = "abc123", **counts: int) -> Path:
    receipt = build_freshness_receipt(
        _holo(**counts),
        ssd_path=tmp_path,
        repo_root=REPO_ROOT,
        source="ci_test",
        generated_at="2026-07-12T00:00:00+00:00",
        repo_head_sha=sha,
    )
    path = freshness_receipt_path(tmp_path)
    write_freshness_receipt(receipt, path)
    return path


def test_ci_gate_passes_when_receipt_covers_changed_collections(tmp_path: Path) -> None:
    receipt = _write_receipt(tmp_path)

    result = check_ci_freshness(
        receipt_path=receipt,
        changed_paths=[
            "modules/foundups/agent/src/create_foundup_dryrun.py",
            "docs/0102_session_briefings/work_ledger.schema.json",
        ],
        expected_repo_head_sha="abc123",
    )

    assert result.ok is True
    assert result.status == STATUS_PASS
    assert result.configured is True
    assert result.required_collections == ["navigation_symbols", "navigation_work_ledger"]
    assert result.stale_collections == []
    assert result.no_reindex_performed is True
    assert result.no_runtime_reindex_performed is True
    assert result.no_holoindex_mutation_performed is True


def test_ci_gate_fails_closed_when_receipt_path_missing() -> None:
    result = check_ci_freshness(
        receipt_path=None,
        changed_paths=["modules/foundups/agent/src/create_foundup_dryrun.py"],
        expected_repo_head_sha="abc123",
    )

    assert result.ok is False
    assert result.status == STATUS_FAIL
    assert result.configured is False
    assert result.stale_collections == ["navigation_symbols"]
    assert result.reasons == ["missing_freshness_receipt_path"]


def test_ci_gate_can_report_not_configured_without_claiming_freshness() -> None:
    result = check_ci_freshness(
        receipt_path="E:/HoloIndex/indexes/holoindex_freshness_receipt.json",
        changed_paths=["modules/foundups/agent/src/create_foundup_dryrun.py"],
        expected_repo_head_sha="abc123",
        allow_not_configured=True,
    )

    assert result.ok is True
    assert result.status == STATUS_NOT_CONFIGURED
    assert result.configured is False
    assert result.required_collections == ["navigation_symbols"]
    assert result.stale_collections == []
    assert result.reasons == ["missing_freshness_receipt_file"]


def test_ci_gate_fails_on_stale_repo_sha(tmp_path: Path) -> None:
    receipt = _write_receipt(tmp_path, sha="old")

    result = check_ci_freshness(
        receipt_path=receipt,
        changed_paths=[
            "WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md",
            "docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md",
        ],
        expected_repo_head_sha="new",
    )

    assert result.ok is False
    assert result.status == STATUS_FAIL
    assert result.stale_collections == ["navigation_work_ledger", "navigation_wsp"]
    assert "stale_repo_head_sha" in result.reasons


def test_ci_gate_fails_on_empty_required_collection(tmp_path: Path) -> None:
    receipt = _write_receipt(tmp_path, navigation_docs=0)

    result = check_ci_freshness(
        receipt_path=receipt,
        changed_paths=["docs/audits/infrastructure/HOLOINDEX_FRESHNESS_AND_SCALING_GOVERNANCE_PHASE1.md"],
        expected_repo_head_sha="abc123",
    )

    assert result.ok is False
    assert result.status == STATUS_FAIL
    assert result.stale_collections == ["navigation_docs"]
    assert "collection_not_indexed:navigation_docs" in result.reasons


def test_ci_gate_dedupes_and_normalizes_changed_paths(tmp_path: Path) -> None:
    receipt = _write_receipt(tmp_path)

    result = check_ci_freshness(
        receipt_path=receipt,
        changed_paths=[
            ".\\modules\\foundups\\agent\\src\\create_foundup_dryrun.py",
            "modules/foundups/agent/src/create_foundup_dryrun.py",
            "",
            "# comment",
        ],
        expected_repo_head_sha="abc123",
    )

    assert result.ok is True
    assert result.changed_paths == ["modules/foundups/agent/src/create_foundup_dryrun.py"]
    assert result.required_collections == ["navigation_symbols"]


def test_ci_gate_allows_no_relevant_changes(tmp_path: Path) -> None:
    receipt = _write_receipt(tmp_path)

    result = check_ci_freshness(
        receipt_path=receipt,
        changed_paths=[".gitignore"],
        expected_repo_head_sha="abc123",
    )

    assert result.ok is True
    assert result.status == STATUS_NO_RELEVANT_CHANGES
    assert result.required_collections == []


def test_ci_gate_allows_no_relevant_changes_without_receipt() -> None:
    result = check_ci_freshness(
        receipt_path=None,
        changed_paths=[".gitignore"],
        expected_repo_head_sha="abc123",
    )

    assert result.ok is True
    assert result.status == STATUS_NO_RELEVANT_CHANGES
    assert result.configured is False
    assert result.required_collections == []
    assert result.reasons == []


def test_cli_returns_zero_and_json_for_fresh_receipt(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    receipt = _write_receipt(tmp_path)

    code = main([
        "--receipt",
        str(receipt),
        "--changed-path",
        "modules/foundups/agent/src/create_foundup_dryrun.py",
        "--expected-repo-head-sha",
        "abc123",
    ])

    assert code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == STATUS_PASS
    assert payload["required_collections"] == ["navigation_symbols"]
    assert payload["no_reindex_performed"] is True


def test_cli_changed_paths_file_and_failure_exit(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    receipt = _write_receipt(tmp_path, sha="old")
    paths = tmp_path / "changed.txt"
    paths.write_text("docs/0102_session_briefings/work_ledger.schema.json\n", encoding="utf-8")

    code = main([
        "--receipt",
        str(receipt),
        "--changed-paths-file",
        str(paths),
        "--expected-repo-head-sha",
        "new",
    ])

    assert code == EXIT_STALE
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == STATUS_FAIL
    assert payload["stale_collections"] == ["navigation_work_ledger"]


def test_module_has_no_git_reindex_or_execution_imports() -> None:
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned_imports = {"subprocess", "requests", "git", "holo_index.core.holo_index"}
    banned_calls = {
        "system",
        "popen",
        "run",
        "check_call",
        "check_output",
        "index_code_entries",
        "index_wsp_entries",
        "write_freshness_receipt",
    }
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
