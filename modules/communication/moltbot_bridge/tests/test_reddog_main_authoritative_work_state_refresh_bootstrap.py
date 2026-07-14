"""Tests for REDDOG_MAIN_AUTHORITATIVE_WORK_STATE_REFRESH_BOOTSTRAP_PHASE1."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from unittest.mock import patch

from modules.communication.moltbot_bridge.src.reddog_main_authoritative_work_state_refresh_bootstrap import (
    REDDOG_WORK_STATE_BOOTSTRAP_APPLIED,
    REDDOG_WORK_STATE_BOOTSTRAP_NOT_READY,
    run_reddog_main_authoritative_work_state_refresh_bootstrap,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_main_authoritative_work_state_refresh_bootstrap.py"
)
NOW = "2026-07-14T00:00:00+00:00"
SLICE_ID = "REDDOG_MAIN_AUTHORITATIVE_WORK_STATE_REFRESH_BOOTSTRAP_PHASE1"


def _active_ledger(updated: str = NOW) -> str:
    return f"""# Active Slice Ledger

**Updated**: {updated}

## Open Slices

| Slice | Priority | Blocked By | Notes |
|-------|----------|------------|-------|
| `{SLICE_ID}` | P0 | - | refresh bootstrap |

## Next Priority Order

1. **{SLICE_ID}** - refresh bootstrap
"""


def _work_ledger(updated: str = NOW) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "last_updated": updated,
        "slices": [
            {
                "slice_id": SLICE_ID,
                "title": "Refresh bootstrap",
                "status": "IN_PROGRESS",
                "priority": "P0",
                "source": "audit",
                "lane": "A",
                "created_at": updated,
                "wsp15_score": {"total": 18},
            }
        ],
    }


def _github_records() -> list[dict[str, object]]:
    return [
        {
            "slice_id": SLICE_ID,
            "status": "PR_OPEN",
            "priority": "P0",
            "lane": "A",
            "pr_number": 1013,
            "head_commit": "cfe916b5acbf1dfe606b3b5b5fc55a6f6f92c095",
            "wsp15_score": {"total": 18},
        }
    ]


def _w10_records() -> list[dict[str, object]]:
    return [
        {
            "slice_id": SLICE_ID,
            "status": "STAGED_FOR_W10",
            "priority": "P0",
            "lane": "A",
            "evidence_refs": ["w10:local-fixture"],
            "wsp15_score": {"total": 18},
        }
    ]


def _write_sources(tmp_path: Path, *, stale: bool = False) -> dict[str, Path]:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    active = repo_root / "ACTIVE_SLICE_LEDGER.md"
    ledger = repo_root / "work_ledger.json"
    github = repo_root / "github_records.json"
    w10 = repo_root / "w10_records.json"
    updated = "2026-05-01T00:00:00+00:00" if stale else NOW
    active.write_text(_active_ledger(updated), encoding="utf-8")
    ledger.write_text(json.dumps(_work_ledger(updated), sort_keys=True), encoding="utf-8")
    github.write_text(json.dumps(_github_records(), sort_keys=True), encoding="utf-8")
    w10.write_text(json.dumps(_w10_records(), sort_keys=True), encoding="utf-8")
    return {
        "repo": repo_root,
        "active": active,
        "ledger": ledger,
        "github": github,
        "w10": w10,
        "output": tmp_path / "runtime" / "authoritative_work_state.json",
    }


def test_refresh_bootstrap_commits_work_state_outside_repo_from_existing_sources(tmp_path: Path) -> None:
    paths = _write_sources(tmp_path)

    result = run_reddog_main_authoritative_work_state_refresh_bootstrap(
        repo_root=paths["repo"],
        active_slice_ledger_path=paths["active"],
        work_ledger_json_path=paths["ledger"],
        github_pr_records_path=paths["github"],
        w10_report_records_path=paths["w10"],
        work_state_output_path=paths["output"],
        worker_id="reddog-test",
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.status == REDDOG_WORK_STATE_BOOTSTRAP_APPLIED
    assert result.work_state_path == str(paths["output"].resolve())
    assert result.refresh_id and re.fullmatch(r"[a-f0-9]{64}", result.refresh_id)
    assert result.committed_revision and re.fullmatch(r"[a-f0-9]{64}", result.committed_revision)
    assert result.selected_slice == SLICE_ID
    assert result.queue_item_count == 1
    assert paths["output"].exists()
    data = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert data["schema_version"] == "reddog_authoritative_work_state.v1"
    assert data["worker_claims"][0]["worker_id"] == "reddog-test"
    assert data["no_execution_performed"] is True


def test_refresh_bootstrap_rejects_missing_github_and_w10_sources_without_write(tmp_path: Path) -> None:
    paths = _write_sources(tmp_path)
    paths["github"].unlink()
    paths["w10"].unlink()

    result = run_reddog_main_authoritative_work_state_refresh_bootstrap(
        repo_root=paths["repo"],
        active_slice_ledger_path=paths["active"],
        work_ledger_json_path=paths["ledger"],
        github_pr_records_path=paths["github"],
        w10_report_records_path=paths["w10"],
        work_state_output_path=paths["output"],
        now_iso=NOW,
    )

    assert result.accepted is False
    assert result.status == REDDOG_WORK_STATE_BOOTSTRAP_NOT_READY
    assert "missing_github_pr_records" in result.rejection_reasons
    assert "missing_w10_report_records" in result.rejection_reasons
    assert not paths["output"].exists()


def test_refresh_bootstrap_rejects_stale_embedded_ledgers_before_commit(tmp_path: Path) -> None:
    paths = _write_sources(tmp_path, stale=True)

    result = run_reddog_main_authoritative_work_state_refresh_bootstrap(
        repo_root=paths["repo"],
        active_slice_ledger_path=paths["active"],
        work_ledger_json_path=paths["ledger"],
        github_pr_records_path=paths["github"],
        w10_report_records_path=paths["w10"],
        work_state_output_path=paths["output"],
        now_iso=NOW,
    )

    assert result.accepted is False
    assert any(reason.startswith("stale_ledger_source:") for reason in result.rejection_reasons)
    assert not paths["output"].exists()


def test_refresh_bootstrap_rejects_output_inside_repo(tmp_path: Path) -> None:
    paths = _write_sources(tmp_path)
    in_repo_output = paths["repo"] / "runtime" / "authoritative_work_state.json"

    result = run_reddog_main_authoritative_work_state_refresh_bootstrap(
        repo_root=paths["repo"],
        active_slice_ledger_path=paths["active"],
        work_ledger_json_path=paths["ledger"],
        github_pr_records_path=paths["github"],
        w10_report_records_path=paths["w10"],
        work_state_output_path=in_repo_output,
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "work_state_output_inside_repo" in result.rejection_reasons
    assert not in_repo_output.exists()


def test_main_preflight_is_nonblocking_when_refresh_not_ready() -> None:
    import main

    with patch.dict(
        "os.environ",
        {
            "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH": "1",
            "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_ENFORCED": "0",
            "REDDOG_GITHUB_PR_RECORDS_PATH": "",
            "REDDOG_W10_REPORT_RECORDS_PATH": "",
            "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": "",
        },
        clear=False,
    ):
        assert main.run_reddog_authoritative_work_state_refresh_preflight(REPO_ROOT) is True


def test_main_preflight_blocks_when_enforced_and_refresh_not_ready() -> None:
    import main

    with patch.dict(
        "os.environ",
        {
            "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH": "1",
            "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_ENFORCED": "1",
            "REDDOG_GITHUB_PR_RECORDS_PATH": "",
            "REDDOG_W10_REPORT_RECORDS_PATH": "",
            "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": "",
        },
        clear=False,
    ):
        assert main.run_reddog_authoritative_work_state_refresh_preflight(REPO_ROOT) is False


def test_main_preflight_sets_work_state_path_after_success(tmp_path: Path) -> None:
    import main

    paths = _write_sources(tmp_path)
    with patch.dict(
        "os.environ",
        {
            "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH": "1",
            "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_ENFORCED": "0",
            "REDDOG_ACTIVE_SLICE_LEDGER_PATH": str(paths["active"]),
            "REDDOG_WORK_LEDGER_JSON_PATH": str(paths["ledger"]),
            "REDDOG_GITHUB_PR_RECORDS_PATH": str(paths["github"]),
            "REDDOG_W10_REPORT_RECORDS_PATH": str(paths["w10"]),
            "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(paths["output"]),
        },
        clear=False,
    ):
        assert main.run_reddog_authoritative_work_state_refresh_preflight(paths["repo"]) is True
        import os

        assert os.environ["REDDOG_AUTHORITATIVE_WORK_STATE_PATH"] == str(paths["output"].resolve())


def test_refresh_bootstrap_module_has_no_fetch_execution_or_holoindex_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "requests",
        "httpx",
        "urllib",
        "socket",
        "holo_index",
        "openclaw_supervisor",
        "hermes_job_executor",
    }
    banned_calls = {
        "eval",
        "exec",
        "__import__",
        "system",
        "popen",
        "run",
        "call",
        "check_call",
        "check_output",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in banned_import_roots
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
            assert name not in banned_calls
