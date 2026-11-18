"""Tests for REDDOG_AUTHORITATIVE_WORK_STATE_SOURCE_RECORD_SUPPLY_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_source_record_supply import (
    SOURCE_RECORD_SUPPLY_APPLIED,
    SOURCE_RECORD_SUPPLY_NOT_READY,
    WorkLedgerProjectionW10ReportProvider,
    supply_authoritative_work_state_source_records,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_source_record_supply_bootstrap import (
    run_reddog_authoritative_work_state_source_record_supply_bootstrap,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_authoritative_work_state_source_record_supply.py"
)
NOW = "2026-07-16T00:00:00+00:00"
SLICE_ID = "REDDOG_AUTHORITATIVE_WORK_STATE_SOURCE_RECORD_SUPPLY_PHASE1"


class _GitHubProvider:
    def __init__(self, records):
        self.records = records
        self.called = False

    def collect_pull_request_records(self, *, now_iso: str):
        self.called = True
        return self.records


class _W10Provider:
    def __init__(self, records):
        self.records = records
        self.called = False

    def collect_w10_report_records(self, *, now_iso: str):
        self.called = True
        return self.records


def _github_records() -> list[dict[str, object]]:
    return [
        {
            "slice_id": SLICE_ID,
            "status": "PR_OPEN",
            "priority": "P0",
            "lane": "A",
            "pr_number": 1179,
            "head_commit": "a" * 40,
            "evidence_refs": ["github:pr:1179"],
            "wsp15_score": {"total": 18},
        }
    ]


def _w10_records() -> list[dict[str, object]]:
    return [
        {
            "slice_id": SLICE_ID,
            "status": "PR_OPEN",
            "priority": "P0",
            "lane": "A",
            "evidence_refs": ["w10:fixture"],
            "wsp15_score": {"total": 18},
        }
    ]


def _work_ledger(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "last_updated": NOW,
                "slices": [
                    {
                        "slice_id": SLICE_ID,
                        "status": "PR_OPEN",
                        "priority": "P0",
                        "lane": "A",
                        "branch": "feat/reddog-authoritative-work-state-source-record-supply-phase1",
                        "pr_number": 1179,
                        "head_commit": "a" * 40,
                        "evidence_docs": ["docs/audits/example.md"],
                        "wsp15_score": {"total": 18},
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def test_supply_writes_github_and_w10_source_records_outside_repo(tmp_path: Path) -> None:
    github_path = tmp_path / "runtime" / "github_pr_records.json"
    w10_path = tmp_path / "runtime" / "w10_report_records.json"

    result = supply_authoritative_work_state_source_records(
        repo_root=REPO_ROOT,
        github_pr_records_output_path=github_path,
        w10_report_records_output_path=w10_path,
        github_provider=_GitHubProvider(_github_records()),
        w10_provider=_W10Provider(_w10_records()),
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.status == SOURCE_RECORD_SUPPLY_APPLIED
    assert result.receipt.github_record_count == 1
    assert result.receipt.w10_record_count == 1
    assert json.loads(github_path.read_text(encoding="utf-8"))[0]["slice_id"] == SLICE_ID
    assert json.loads(w10_path.read_text(encoding="utf-8"))[0]["slice_id"] == SLICE_ID
    assert result.receipt.no_repo_mutation_performed is True
    assert result.receipt.no_holoindex_reindex_performed is True
    assert result.receipt.no_execution_performed is True


def test_supply_rejects_outputs_inside_repo(tmp_path: Path) -> None:
    result = supply_authoritative_work_state_source_records(
        repo_root=REPO_ROOT,
        github_pr_records_output_path=REPO_ROOT / "github_records.json",
        w10_report_records_output_path=tmp_path / "w10_records.json",
        github_provider=_GitHubProvider(_github_records()),
        w10_provider=_W10Provider(_w10_records()),
        now_iso=NOW,
    )

    assert result.accepted is False
    assert result.status == SOURCE_RECORD_SUPPLY_NOT_READY
    assert "github_pr_records_output_inside_repo" in result.receipt.rejection_reasons
    assert not (REPO_ROOT / "github_records.json").exists()


def test_supply_rejects_empty_sources_without_writing(tmp_path: Path) -> None:
    github_path = tmp_path / "runtime" / "github_pr_records.json"
    w10_path = tmp_path / "runtime" / "w10_report_records.json"

    result = supply_authoritative_work_state_source_records(
        repo_root=REPO_ROOT,
        github_pr_records_output_path=github_path,
        w10_report_records_output_path=w10_path,
        github_provider=_GitHubProvider([]),
        w10_provider=_W10Provider(_w10_records()),
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "no_github_pr_records" in result.receipt.rejection_reasons
    assert not github_path.exists()
    assert not w10_path.exists()


def test_work_ledger_projection_w10_provider_marks_projection_evidence(tmp_path: Path) -> None:
    ledger = tmp_path / "work_ledger.json"
    _work_ledger(ledger)

    provider = WorkLedgerProjectionW10ReportProvider(work_ledger_json_path=ledger)
    records = list(provider.collect_w10_report_records(now_iso=NOW))

    assert len(records) == 1
    assert records[0]["slice_id"] == SLICE_ID
    assert records[0]["status"] == "PR_OPEN"
    assert any(str(ref).startswith("w10:ledger_projection:") for ref in records[0]["evidence_refs"])


def test_bootstrap_uses_injected_providers_and_returns_paths(tmp_path: Path) -> None:
    ledger = tmp_path / "repo" / "work_ledger.json"
    ledger.parent.mkdir()
    _work_ledger(ledger)
    github_path = tmp_path / "runtime" / "github_pr_records.json"
    w10_path = tmp_path / "runtime" / "w10_report_records.json"

    result = run_reddog_authoritative_work_state_source_record_supply_bootstrap(
        repo_root=ledger.parent,
        github_pr_records_output_path=github_path,
        w10_report_records_output_path=w10_path,
        work_ledger_json_path=ledger,
        github_provider=_GitHubProvider(_github_records()),
        w10_provider=_W10Provider(_w10_records()),
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.github_pr_records_path == str(github_path.resolve())
    assert result.w10_report_records_path == str(w10_path.resolve())
    assert result.github_record_count == 1
    assert result.w10_record_count == 1


def test_module_has_no_shell_execution_or_holoindex_mutation_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {"subprocess", "socket", "holo_index"}
    banned_calls = {"eval", "exec", "compile", "__import__"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned_import_roots
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in banned_import_roots
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                assert func.id not in banned_calls
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                assert func.value.id not in banned_import_roots
