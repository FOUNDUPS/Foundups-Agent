"""Tests for CI main HoloIndex freshness gate wrapper."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from holo_index.ci_freshness_gate import STATUS_FAIL, STATUS_NOT_CONFIGURED, STATUS_PASS
from holo_index.ci_main_freshness_gate import (
    discover_changed_paths,
    main,
    run_ci_main_freshness_gate,
)
from holo_index.freshness_receipt import (
    CollectionFreshness,
    HoloIndexFreshnessReceipt,
    freshness_receipt_path,
    write_freshness_receipt,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE = REPO_ROOT / "holo_index" / "ci_main_freshness_gate.py"
HEAD = "9c31512a8b4d6e1f0a2b3c4d5e6f708192a3b4c5"
BASE = "7994990bcf1e2d3c4b5a69788776655443322110"


def _write_receipt(tmp_path: Path, *, head: str = HEAD) -> Path:
    receipt = HoloIndexFreshnessReceipt(
        schema_version="holoindex_freshness_receipt.v1",
        generated_at="2026-07-14T00:00:00+00:00",
        repo_root=str(REPO_ROOT),
        repo_head_sha=head,
        ssd_path=str(tmp_path),
        source="ci_targeted_reindex",
        collections=[
            CollectionFreshness(
                name="navigation_work_ledger",
                count=2,
                status="indexed",
                source="ci_targeted_reindex",
                repo_head_sha=head,
                last_indexed_at="2026-07-14T00:00:00+00:00",
            )
        ],
    )
    path = freshness_receipt_path(tmp_path)
    write_freshness_receipt(receipt, path)
    return path


def test_run_ci_main_freshness_gate_passes_with_fresh_receipt(tmp_path: Path) -> None:
    receipt_path = _write_receipt(tmp_path)

    result = run_ci_main_freshness_gate(
        receipt_path=receipt_path,
        changed_paths=["docs/0102_session_briefings/work_ledger.schema.json"],
        expected_repo_head_sha=HEAD,
        enforce_configured=True,
    )

    assert result.ok is True
    assert result.status == STATUS_PASS
    assert result.no_reindex_performed is True
    assert result.no_holoindex_mutation_performed is True


def test_missing_receipt_is_nonblocking_when_not_configured() -> None:
    result = run_ci_main_freshness_gate(
        receipt_path=None,
        ssd_path="",
        changed_paths=["docs/0102_session_briefings/work_ledger.schema.json"],
        expected_repo_head_sha=HEAD,
        enforce_configured=False,
    )

    assert result.ok is True
    assert result.status == STATUS_NOT_CONFIGURED
    assert result.configured is False


def test_unconfigured_env_does_not_use_local_default_holoindex() -> None:
    with patch.dict("os.environ", {"HOLOINDEX_FRESHNESS_RECEIPT": "", "HOLOINDEX_SSD_PATH": ""}, clear=False):
        result = run_ci_main_freshness_gate(
            receipt_path=None,
            ssd_path=None,
            changed_paths=["docs/0102_session_briefings/work_ledger.schema.json"],
            expected_repo_head_sha=HEAD,
            enforce_configured=False,
        )

    assert result.ok is True
    assert result.status == STATUS_NOT_CONFIGURED
    assert result.configured is False
    assert result.receipt_path is None


def test_missing_receipt_fails_when_enforced() -> None:
    result = run_ci_main_freshness_gate(
        receipt_path=None,
        ssd_path="",
        changed_paths=["docs/0102_session_briefings/work_ledger.schema.json"],
        expected_repo_head_sha=HEAD,
        enforce_configured=True,
    )

    assert result.ok is False
    assert result.status == STATUS_FAIL
    assert "missing_freshness_receipt_path" in result.reasons


def test_stale_receipt_fails_when_head_changes(tmp_path: Path) -> None:
    receipt_path = _write_receipt(tmp_path, head="0" * 40)

    result = run_ci_main_freshness_gate(
        receipt_path=receipt_path,
        changed_paths=["docs/0102_session_briefings/work_ledger.schema.json"],
        expected_repo_head_sha=HEAD,
        enforce_configured=True,
    )

    assert result.ok is False
    assert "stale_repo_head_sha" in result.reasons


def test_discover_changed_paths_uses_readonly_git_diff() -> None:
    fake = type("Completed", (), {"returncode": 0, "stdout": "a.py\n./a.py\ndocs/x.md\n"})()
    with patch("holo_index.ci_main_freshness_gate.subprocess.run", return_value=fake) as mock_run:
        paths = discover_changed_paths(repo_root=REPO_ROOT, base_sha=BASE, head_sha=HEAD)

    assert paths == ["a.py", "docs/x.md"]
    args = mock_run.call_args.args[0]
    assert args[:3] == ("git", "-C", str(REPO_ROOT))
    assert "diff" in args
    assert "--name-only" in args


def test_discover_changed_paths_rejects_non_sha_input() -> None:
    with pytest.raises(ValueError, match="invalid_git_sha"):
        discover_changed_paths(repo_root=REPO_ROOT, base_sha="main;rm -rf", head_sha=HEAD)


def test_cli_outputs_json_and_exit_code(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    receipt_path = _write_receipt(tmp_path)

    code = main(
        [
            "--receipt",
            str(receipt_path),
            "--head-sha",
            HEAD,
            "--changed-path",
            "docs/0102_session_briefings/work_ledger.schema.json",
            "--enforce-configured",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == STATUS_PASS


def test_module_does_not_reindex_or_mutate_holoindex() -> None:
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_tokens = (
        "--index",
        "write_freshness_receipt",
        "build_freshness_receipt",
        "_reset_collection",
        "index_code_entries",
        "index_wsp_entries",
        "index_all",
    )
    for token in forbidden_tokens:
        assert token not in source
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"write_text", "mkdir"}
            if isinstance(node.func.value, ast.Name) and node.func.value.id in {
                "collection",
                "collections",
                "index",
                "store",
            }:
                assert node.func.attr not in {"add", "append", "extend", "insert", "pop", "remove", "clear"}
