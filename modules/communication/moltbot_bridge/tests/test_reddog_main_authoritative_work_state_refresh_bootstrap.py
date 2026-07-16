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
DECISION_SLICE_ID = "REDDOG_DECISION_SELECTED_PHASE1"


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


def _active_ledger_with_decision_slice(updated: str = NOW) -> str:
    return f"""# Active Slice Ledger

**Updated**: {updated}

## Open Slices

| Slice | Priority | Blocked By | Notes |
|-------|----------|------------|-------|
| `{SLICE_ID}` | P0 | - | refresh bootstrap |
| `{DECISION_SLICE_ID}` | P1 | - | selected by persisted decision |

## Next Priority Order

1. **{SLICE_ID}** - refresh bootstrap
2. **{DECISION_SLICE_ID}** - selected by persisted decision
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


def _work_ledger_with_decision_slice(updated: str = NOW) -> dict[str, object]:
    payload = _work_ledger(updated)
    payload["slices"] = [
        *payload["slices"],  # type: ignore[index]
        {
            "slice_id": DECISION_SLICE_ID,
            "title": "Decision selected slice",
            "status": "PROPOSED",
            "priority": "P1",
            "source": "audit",
            "lane": "B",
            "created_at": updated,
            "wsp15_score": {"total": 15},
        },
    ]
    return payload


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


def _github_records_with_decision_slice() -> list[dict[str, object]]:
    return [
        *_github_records(),
        {
            "slice_id": DECISION_SLICE_ID,
            "status": "PROPOSED",
            "priority": "P1",
            "lane": "B",
            "head_commit": "d" * 40,
            "wsp15_score": {"total": 15},
        },
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


def _w10_records_with_decision_slice() -> list[dict[str, object]]:
    return [
        *_w10_records(),
        {
            "slice_id": DECISION_SLICE_ID,
            "status": "PROPOSED",
            "priority": "P1",
            "lane": "B",
            "evidence_refs": ["w10:decision-fixture"],
            "wsp15_score": {"total": 15},
        },
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


def _write_sources_with_decision_slice(tmp_path: Path) -> dict[str, Path]:
    paths = _write_sources(tmp_path)
    paths["active"].write_text(_active_ledger_with_decision_slice(), encoding="utf-8")
    paths["ledger"].write_text(json.dumps(_work_ledger_with_decision_slice(), sort_keys=True), encoding="utf-8")
    paths["github"].write_text(json.dumps(_github_records_with_decision_slice(), sort_keys=True), encoding="utf-8")
    paths["w10"].write_text(json.dumps(_w10_records_with_decision_slice(), sort_keys=True), encoding="utf-8")
    return paths


class _FakeDecisionStore:
    def __init__(self, decision: dict[str, object] | None) -> None:
        self.decision = decision

    def load_latest_readonly_audit_decision(self):
        return self.decision

    def load_readonly_audit_decision(self, decision_id: str):
        return self.decision if self.decision and self.decision.get("decision_id") == decision_id else None

    def store_readonly_audit_decision(self, record):
        return {"ok": False, "reason": "not_used"}


def _persisted_decision(next_slice: str = DECISION_SLICE_ID) -> dict[str, object]:
    return {
        "accepted": True,
        "decision_id": "sha256:persisted-decision-1",
        "action": "FIX",
        "swarm_id": "sha256:swarm-1",
        "report_bundle_id": "sha256:bundle-1",
        "next_slice_name": next_slice,
        "wsp15_priority": "P1",
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


def test_refresh_bootstrap_uses_persisted_decision_after_claim_gate_accepts(tmp_path: Path) -> None:
    paths = _write_sources_with_decision_slice(tmp_path)

    result = run_reddog_main_authoritative_work_state_refresh_bootstrap(
        repo_root=paths["repo"],
        active_slice_ledger_path=paths["active"],
        work_ledger_json_path=paths["ledger"],
        github_pr_records_path=paths["github"],
        w10_report_records_path=paths["w10"],
        work_state_output_path=paths["output"],
        worker_id="reddog-test",
        now_iso=NOW,
        use_latest_readonly_audit_decision=True,
        decision_store=_FakeDecisionStore(_persisted_decision()),
    )

    assert result.accepted is True
    assert result.status == REDDOG_WORK_STATE_BOOTSTRAP_APPLIED
    assert result.selected_slice == DECISION_SLICE_ID
    assert result.latest_decision_attempted is True
    assert result.latest_decision_id == "sha256:persisted-decision-1"
    assert result.latest_decision_next_slice == DECISION_SLICE_ID
    assert result.latest_decision_claim_gate_decision == "CLAIM_READY_DRYRUN"
    data = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert data["worker_claims"][0]["slice_id"] == DECISION_SLICE_ID


def test_refresh_bootstrap_rejects_persisted_decision_for_non_open_slice(tmp_path: Path) -> None:
    paths = _write_sources_with_decision_slice(tmp_path)

    result = run_reddog_main_authoritative_work_state_refresh_bootstrap(
        repo_root=paths["repo"],
        active_slice_ledger_path=paths["active"],
        work_ledger_json_path=paths["ledger"],
        github_pr_records_path=paths["github"],
        w10_report_records_path=paths["w10"],
        work_state_output_path=paths["output"],
        worker_id="reddog-test",
        now_iso=NOW,
        use_latest_readonly_audit_decision=True,
        decision_store=_FakeDecisionStore(_persisted_decision("REDDOG_MISSING_PHASE1")),
    )

    assert result.accepted is False
    assert "persisted_decision_claim_gate_rejected" in result.rejection_reasons
    assert "persisted_decision_claim_gate:requested_slice_not_in_open_queue" in result.rejection_reasons
    assert result.latest_decision_attempted is True
    assert result.latest_decision_claim_gate_decision == "CLAIM_REJECTED"
    assert not paths["output"].exists()


def test_refresh_bootstrap_rejects_missing_latest_decision_when_enabled(tmp_path: Path) -> None:
    paths = _write_sources_with_decision_slice(tmp_path)

    result = run_reddog_main_authoritative_work_state_refresh_bootstrap(
        repo_root=paths["repo"],
        active_slice_ledger_path=paths["active"],
        work_ledger_json_path=paths["ledger"],
        github_pr_records_path=paths["github"],
        w10_report_records_path=paths["w10"],
        work_state_output_path=paths["output"],
        worker_id="reddog-test",
        now_iso=NOW,
        use_latest_readonly_audit_decision=True,
        decision_store=_FakeDecisionStore(None),
    )

    assert result.accepted is False
    assert "latest_readonly_audit_decision_missing" in result.rejection_reasons
    assert result.latest_decision_attempted is True
    assert result.latest_decision_rejection_reasons == ("latest_readonly_audit_decision_missing",)
    assert not paths["output"].exists()


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


def test_main_preflight_profile_derives_work_state_output_path(tmp_path: Path) -> None:
    import main

    paths = _write_sources(tmp_path)
    runtime_root = tmp_path / "resident-runtime"
    expected_output = runtime_root / "authoritative_work_state.json"
    with patch.dict(
        "os.environ",
        {
            "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH": "1",
            "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_ENFORCED": "0",
            "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
            "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
            "REDDOG_ACTIVE_SLICE_LEDGER_PATH": str(paths["active"]),
            "REDDOG_WORK_LEDGER_JSON_PATH": str(paths["ledger"]),
            "REDDOG_GITHUB_PR_RECORDS_PATH": str(paths["github"]),
            "REDDOG_W10_REPORT_RECORDS_PATH": str(paths["w10"]),
        },
        clear=True,
    ):
        assert main.run_reddog_authoritative_work_state_refresh_preflight(paths["repo"]) is True
        import os

        assert os.environ["REDDOG_AUTHORITATIVE_WORK_STATE_PATH"] == str(
            expected_output.resolve()
        )

    assert expected_output.exists()
    assert not (paths["repo"] / ".reddog").exists()


def test_main_preflight_profile_runs_source_record_supply_before_refresh(tmp_path: Path) -> None:
    import main

    paths = _write_sources(tmp_path)
    runtime_root = tmp_path / "resident-runtime"
    github_path = runtime_root / "github_pr_records.json"
    w10_path = runtime_root / "w10_report_records.json"

    source_result = type(
        "SourceResult",
        (),
        {
            "accepted": True,
            "status": "SOURCE_RECORD_SUPPLY_APPLIED",
            "github_pr_records_path": str(github_path),
            "w10_report_records_path": str(w10_path),
            "receipt_id": "sha256:source-records",
            "github_record_count": 1,
            "w10_record_count": 1,
            "rejection_reasons": (),
        },
    )()
    refresh_result = type(
        "RefreshResult",
        (),
        {
            "accepted": True,
            "status": REDDOG_WORK_STATE_BOOTSTRAP_APPLIED,
            "work_state_path": str(runtime_root / "authoritative_work_state.json"),
            "refresh_id": "refresh",
            "committed_revision": "revision",
            "selected_slice": SLICE_ID,
            "queue_item_count": 1,
            "rejection_reasons": (),
            "latest_decision_attempted": False,
            "latest_decision_next_slice": None,
        },
    )()

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_source_record_supply_bootstrap.run_reddog_authoritative_work_state_source_record_supply_bootstrap",
        return_value=source_result,
    ) as supply_mock:
        with patch(
            "modules.communication.moltbot_bridge.src.reddog_main_authoritative_work_state_refresh_bootstrap.run_reddog_main_authoritative_work_state_refresh_bootstrap",
            return_value=refresh_result,
        ) as refresh_mock:
            with patch.dict(
                "os.environ",
                {
                    "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH": "1",
                    "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                    "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
                    "REDDOG_ACTIVE_SLICE_LEDGER_PATH": str(paths["active"]),
                    "REDDOG_WORK_LEDGER_JSON_PATH": str(paths["ledger"]),
                },
                clear=True,
            ):
                assert main.run_reddog_authoritative_work_state_refresh_preflight(paths["repo"]) is True

    assert supply_mock.called is True
    assert supply_mock.call_args.kwargs["github_pr_records_output_path"] == str(github_path)
    assert supply_mock.call_args.kwargs["w10_report_records_output_path"] == str(w10_path)
    assert refresh_mock.call_args.kwargs["github_pr_records_path"] == str(github_path)
    assert refresh_mock.call_args.kwargs["w10_report_records_path"] == str(w10_path)


def test_main_preflight_profile_runs_projection_after_source_supply_before_refresh(tmp_path: Path) -> None:
    import main

    paths = _write_sources(tmp_path)
    runtime_root = tmp_path / "resident-runtime"
    github_path = runtime_root / "github_pr_records.json"
    w10_path = runtime_root / "w10_report_records.json"
    active_path = runtime_root / "ACTIVE_SLICE_LEDGER.runtime.md"
    work_path = runtime_root / "work_ledger.runtime.json"
    call_order: list[str] = []

    source_result = type(
        "SourceResult",
        (),
        {
            "accepted": True,
            "status": "SOURCE_RECORD_SUPPLY_APPLIED",
            "github_pr_records_path": str(github_path),
            "w10_report_records_path": str(w10_path),
            "receipt_id": "sha256:source-records",
            "github_record_count": 1,
            "w10_record_count": 1,
            "rejection_reasons": (),
        },
    )()
    projection_result = type(
        "ProjectionResult",
        (),
        {
            "accepted": True,
            "status": "WORK_LEDGER_PROJECTION_APPLIED",
            "active_slice_ledger_path": str(active_path),
            "work_ledger_json_path": str(work_path),
            "receipt_id": "sha256:projection",
            "source_record_count": 2,
            "projected_slice_count": 1,
            "open_slice_count": 1,
            "closed_slice_count": 0,
            "rejection_reasons": (),
        },
    )()
    refresh_result = type(
        "RefreshResult",
        (),
        {
            "accepted": True,
            "status": REDDOG_WORK_STATE_BOOTSTRAP_APPLIED,
            "work_state_path": str(runtime_root / "authoritative_work_state.json"),
            "refresh_id": "refresh",
            "committed_revision": "revision",
            "selected_slice": SLICE_ID,
            "queue_item_count": 1,
            "rejection_reasons": (),
            "latest_decision_attempted": False,
            "latest_decision_next_slice": None,
        },
    )()

    def _source_side_effect(**kwargs):
        call_order.append("source")
        return source_result

    def _projection_side_effect(**kwargs):
        call_order.append("projection")
        assert kwargs["github_pr_records_path"] == str(github_path)
        assert kwargs["w10_report_records_path"] == str(w10_path)
        return projection_result

    def _refresh_side_effect(**kwargs):
        call_order.append("refresh")
        assert kwargs["active_slice_ledger_path"] == str(active_path)
        assert kwargs["work_ledger_json_path"] == str(work_path)
        return refresh_result

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_source_record_supply_bootstrap.run_reddog_authoritative_work_state_source_record_supply_bootstrap",
        side_effect=_source_side_effect,
    ):
        with patch(
            "modules.communication.moltbot_bridge.src.reddog_work_ledger_source_projection_supply_bootstrap.run_reddog_work_ledger_source_projection_supply_bootstrap",
            side_effect=_projection_side_effect,
        ):
            with patch(
                "modules.communication.moltbot_bridge.src.reddog_main_authoritative_work_state_refresh_bootstrap.run_reddog_main_authoritative_work_state_refresh_bootstrap",
                side_effect=_refresh_side_effect,
            ):
                with patch.dict(
                    "os.environ",
                    {
                        "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH": "1",
                        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                        "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
                        "REDDOG_ACTIVE_SLICE_LEDGER_PATH": "",
                        "REDDOG_WORK_LEDGER_JSON_PATH": "",
                    },
                    clear=True,
                ):
                    assert main.run_reddog_authoritative_work_state_refresh_preflight(paths["repo"]) is True

    assert call_order == ["source", "projection", "refresh"]


def test_main_preflight_explicit_zero_disables_profile_source_supply(tmp_path: Path) -> None:
    import main

    paths = _write_sources(tmp_path)
    runtime_root = tmp_path / "resident-runtime"
    refresh_result = type(
        "RefreshResult",
        (),
        {
            "accepted": True,
            "status": REDDOG_WORK_STATE_BOOTSTRAP_APPLIED,
            "work_state_path": str(runtime_root / "authoritative_work_state.json"),
            "refresh_id": "refresh",
            "committed_revision": "revision",
            "selected_slice": SLICE_ID,
            "queue_item_count": 1,
            "rejection_reasons": (),
            "latest_decision_attempted": False,
            "latest_decision_next_slice": None,
        },
    )()

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_source_record_supply_bootstrap.run_reddog_authoritative_work_state_source_record_supply_bootstrap",
        side_effect=AssertionError("source supply should not run"),
    ):
        with patch(
            "modules.communication.moltbot_bridge.src.reddog_main_authoritative_work_state_refresh_bootstrap.run_reddog_main_authoritative_work_state_refresh_bootstrap",
            return_value=refresh_result,
        ) as refresh_mock:
            with patch.dict(
                "os.environ",
                {
                    "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH": "1",
                    "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                    "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
                    "REDDOG_WORK_STATE_SOURCE_RECORD_SUPPLY": "0",
                    "REDDOG_ACTIVE_SLICE_LEDGER_PATH": str(paths["active"]),
                    "REDDOG_WORK_LEDGER_JSON_PATH": str(paths["ledger"]),
                    "REDDOG_GITHUB_PR_RECORDS_PATH": str(paths["github"]),
                    "REDDOG_W10_REPORT_RECORDS_PATH": str(paths["w10"]),
                },
                clear=True,
            ):
                assert main.run_reddog_authoritative_work_state_refresh_preflight(paths["repo"]) is True

    assert refresh_mock.call_args.kwargs["github_pr_records_path"] == str(paths["github"])
    assert refresh_mock.call_args.kwargs["w10_report_records_path"] == str(paths["w10"])


def test_main_preflight_explicit_zero_disables_profile_projection_supply(tmp_path: Path) -> None:
    import main

    paths = _write_sources(tmp_path)
    runtime_root = tmp_path / "resident-runtime"
    refresh_result = type(
        "RefreshResult",
        (),
        {
            "accepted": True,
            "status": REDDOG_WORK_STATE_BOOTSTRAP_APPLIED,
            "work_state_path": str(runtime_root / "authoritative_work_state.json"),
            "refresh_id": "refresh",
            "committed_revision": "revision",
            "selected_slice": SLICE_ID,
            "queue_item_count": 1,
            "rejection_reasons": (),
            "latest_decision_attempted": False,
            "latest_decision_next_slice": None,
        },
    )()

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_work_ledger_source_projection_supply_bootstrap.run_reddog_work_ledger_source_projection_supply_bootstrap",
        side_effect=AssertionError("projection supply should not run"),
    ):
        with patch(
            "modules.communication.moltbot_bridge.src.reddog_main_authoritative_work_state_refresh_bootstrap.run_reddog_main_authoritative_work_state_refresh_bootstrap",
            return_value=refresh_result,
        ) as refresh_mock:
            with patch.dict(
                "os.environ",
                {
                    "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH": "1",
                    "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                    "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
                    "REDDOG_WORK_STATE_SOURCE_RECORD_SUPPLY": "0",
                    "REDDOG_WORK_LEDGER_SOURCE_PROJECTION_SUPPLY": "0",
                    "REDDOG_ACTIVE_SLICE_LEDGER_PATH": str(paths["active"]),
                    "REDDOG_WORK_LEDGER_JSON_PATH": str(paths["ledger"]),
                    "REDDOG_GITHUB_PR_RECORDS_PATH": str(paths["github"]),
                    "REDDOG_W10_REPORT_RECORDS_PATH": str(paths["w10"]),
                },
                clear=True,
            ):
                assert main.run_reddog_authoritative_work_state_refresh_preflight(paths["repo"]) is True

    assert refresh_mock.call_args.kwargs["active_slice_ledger_path"] == str(paths["active"])
    assert refresh_mock.call_args.kwargs["work_ledger_json_path"] == str(paths["ledger"])


def test_main_preflight_enables_latest_decision_bridge_with_openclaw_auto_tasks(tmp_path: Path) -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_authoritative_work_state_refresh_bootstrap.run_reddog_main_authoritative_work_state_refresh_bootstrap",
        return_value=type(
            "Result",
            (),
            {
                "accepted": True,
                "status": REDDOG_WORK_STATE_BOOTSTRAP_APPLIED,
                "work_state_path": str(tmp_path / "state.json"),
                "refresh_id": "refresh",
                "committed_revision": "revision",
                "selected_slice": SLICE_ID,
                "queue_item_count": 1,
                "rejection_reasons": (),
                "latest_decision_attempted": True,
                "latest_decision_next_slice": SLICE_ID,
            },
        )(),
    ) as mocked:
        with patch.dict(
            "os.environ",
            {
                "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH": "1",
                "OPENCLAW_AUTO_TASKS_ENABLED": "1",
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(tmp_path / "state.json"),
            },
            clear=True,
        ):
            assert main.run_reddog_authoritative_work_state_refresh_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["use_latest_readonly_audit_decision"] is True


def test_main_preflight_explicit_latest_decision_disable_overrides_openclaw_auto_tasks(tmp_path: Path) -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_authoritative_work_state_refresh_bootstrap.run_reddog_main_authoritative_work_state_refresh_bootstrap",
        return_value=type(
            "Result",
            (),
            {
                "accepted": True,
                "status": REDDOG_WORK_STATE_BOOTSTRAP_APPLIED,
                "work_state_path": str(tmp_path / "state.json"),
                "refresh_id": "refresh",
                "committed_revision": "revision",
                "selected_slice": SLICE_ID,
                "queue_item_count": 1,
                "rejection_reasons": (),
                "latest_decision_attempted": False,
                "latest_decision_next_slice": None,
            },
        )(),
    ) as mocked:
        with patch.dict(
            "os.environ",
            {
                "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH": "1",
                "OPENCLAW_AUTO_TASKS_ENABLED": "1",
                "REDDOG_WORK_STATE_USE_LATEST_READONLY_AUDIT_DECISION": "0",
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(tmp_path / "state.json"),
            },
            clear=True,
        ):
            assert main.run_reddog_authoritative_work_state_refresh_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["use_latest_readonly_audit_decision"] is False


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
