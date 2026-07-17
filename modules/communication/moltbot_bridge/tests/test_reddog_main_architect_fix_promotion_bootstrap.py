"""Tests for REDDOG_ARCHITECT_FIX_PROMOTION_MAIN_PREFLIGHT_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import patch

from modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap import (
    REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED,
    REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_NOT_READY,
    run_reddog_main_architect_fix_promotion_bootstrap,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _authority_profile,
    _determination,
    _memex_supply,
    _model_selection,
    _runtime_binding,
    _work_state,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_main_architect_fix_promotion_bootstrap.py"
)
NOW = "2026-07-16T00:00:00+00:00"


def _repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    return path


def _write_json(tmp_path: Path, name: str, payload: object) -> Path:
    path = tmp_path / "runtime" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _runtime_files(tmp_path: Path) -> dict[str, Path]:
    model_selection = _model_selection()
    return {
        "work_state": _write_json(tmp_path, "authoritative_work_state.json", _work_state()),
        "determination": _write_json(tmp_path, "architect_determination.json", _determination()),
        "model_selection": _write_json(tmp_path, "model_selection.json", model_selection),
        "model_runtime_binding": _write_json(
            tmp_path,
            "model_runtime_binding.json",
            _runtime_binding(model_selection),
        ),
        "memex_supply": _write_json(tmp_path, "memex_supply.json", _memex_supply()),
        "authority_profile_source": _write_json(
            tmp_path,
            "authority_profile_source.json",
            _authority_profile(),
        ),
        "authority_profile_output": tmp_path / "runtime" / "authority_profile.json",
    }


def test_bootstrap_promotes_fix_and_writes_authority_profile(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    files = _runtime_files(tmp_path)

    result = run_reddog_main_architect_fix_promotion_bootstrap(
        repo_root=repo,
        work_state_path=files["work_state"],
        architect_determination_path=files["determination"],
        model_selection_receipt_path=files["model_selection"],
        memex_supply_receipt_path=files["memex_supply"],
        authority_profile_source_path=files["authority_profile_source"],
        authority_profile_output_path=files["authority_profile_output"],
        worker_id="reddog-main-test",
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.status == REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED
    assert result.queue_item_id
    assert result.claim_id
    assert result.selected_slice == "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1"
    assert result.authority_profile_path == str(files["authority_profile_output"].resolve())
    assert result.no_signing_performed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_holoindex_reindex_performed is True

    promoted_profile = json.loads(files["authority_profile_output"].read_text(encoding="utf-8"))
    assert promoted_profile["operational_context_binding"]["queue_item_id"] == result.queue_item_id
    assert promoted_profile["operational_context_binding"]["claim_id"] == result.claim_id

    work_state = json.loads(files["work_state"].read_text(encoding="utf-8"))
    assert work_state["wre_queue_items"][0]["queue_item_id"] == result.queue_item_id
    assert work_state["worker_claims"][0]["claim_id"] == result.claim_id
    assert not (repo / ".reddog").exists()


def test_bootstrap_forwards_runtime_binding_receipt_into_promotion(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    files = _runtime_files(tmp_path)

    result = run_reddog_main_architect_fix_promotion_bootstrap(
        repo_root=repo,
        work_state_path=files["work_state"],
        architect_determination_path=files["determination"],
        model_selection_receipt_path=files["model_selection"],
        model_runtime_binding_receipt_path=files["model_runtime_binding"],
        memex_supply_receipt_path=files["memex_supply"],
        authority_profile_source_path=files["authority_profile_source"],
        authority_profile_output_path=files["authority_profile_output"],
        worker_id="reddog-main-test",
        now_iso=NOW,
    )

    assert result.accepted is True
    promoted_profile = json.loads(files["authority_profile_output"].read_text(encoding="utf-8"))
    runtime_binding = json.loads(files["model_runtime_binding"].read_text(encoding="utf-8"))
    assert promoted_profile["model_runtime_binding_receipt_id"] == runtime_binding["receipt_id"]
    assert promoted_profile["operational_context_binding"]["model_runtime_binding_receipt_id"] == (
        runtime_binding["receipt_id"]
    )


def test_bootstrap_rejects_authority_profile_output_inside_repo(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    files = _runtime_files(tmp_path)

    result = run_reddog_main_architect_fix_promotion_bootstrap(
        repo_root=repo,
        work_state_path=files["work_state"],
        architect_determination_path=files["determination"],
        model_selection_receipt_path=files["model_selection"],
        memex_supply_receipt_path=files["memex_supply"],
        authority_profile_source_path=files["authority_profile_source"],
        authority_profile_output_path=repo / "authority_profile.json",
        worker_id="reddog-main-test",
        now_iso=NOW,
    )

    assert result.accepted is False
    assert result.status == REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_NOT_READY
    assert "authority_profile_output_path_inside_repo" in result.rejection_reasons


def test_main_preflight_auto_runs_when_all_artifacts_are_present(tmp_path: Path) -> None:
    import main

    repo = _repo(tmp_path)
    files = _runtime_files(tmp_path)
    runtime_root = tmp_path / "runtime"

    with patch.dict(
        "os.environ",
        {
            "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(files["work_state"]),
            "REDDOG_ARCHITECT_FIX_DETERMINATION_PATH": str(files["determination"]),
            "REDDOG_MODEL_SELECTION_RECEIPT_PATH": str(files["model_selection"]),
            "REDDOG_MEMEX_SUPPLY_RECEIPT_PATH": str(files["memex_supply"]),
            "REDDOG_AUTHORITY_PROFILE_SOURCE_PATH": str(files["authority_profile_source"]),
            "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
            "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
            "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF": "0",
            "REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY": "0",
            "REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY": "0",
            "REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY": "0",
        },
        clear=True,
    ):
        assert main.run_reddog_architect_fix_promotion_preflight(repo) is True
        assert main.os.environ["REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH"] == str(
            runtime_root / "authority_profile.json"
        )

    assert (runtime_root / "authority_profile.json").exists()


def test_main_preflight_handoff_materializes_resident_cycle_artifacts_before_promotion(tmp_path: Path) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    work_state = _write_json(tmp_path, "authoritative_work_state.json", _work_state())
    model_selection = _write_json(tmp_path, "model_selection_receipt.json", _model_selection())
    authority_source = _write_json(tmp_path, "authority_profile_source.json", _authority_profile())
    handoff_result = type(
        "HandoffResult",
        (),
        {
            "accepted": True,
            "status": "RESIDENT_FIX_HANDOFF_APPLIED",
            "architect_determination_id": "sha256:architect-determination-1",
            "architect_determination_path": str(runtime_root / "architect_determination.json"),
            "memex_supply_receipt_path": str(runtime_root / "memex_supply_receipt.json"),
            "rejection_reasons": (),
        },
    )()
    promotion_result = type(
        "PromotionResult",
        (),
        {
            "accepted": True,
            "status": REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED,
            "promotion_receipt_id": "sha256:promotion",
            "queue_item_id": "queue-1",
            "claim_id": "claim-1",
            "selected_slice": "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
            "authority_profile_path": str(runtime_root / "authority_profile.json"),
            "committed_revision": "sha256:revision",
            "rejection_reasons": (),
        },
    )()

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_fix_promotion_artifact_handoff.run_reddog_resident_fix_promotion_artifact_handoff",
        return_value=handoff_result,
    ) as handoff:
        with patch(
            "modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap.run_reddog_main_architect_fix_promotion_bootstrap",
            return_value=promotion_result,
        ) as promote:
            with patch.dict(
                "os.environ",
                {
                    "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF": "1",
                    "REDDOG_RESIDENT_ARCHITECT_INTENT_ID": "sha256:intent-handoff",
                    "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(work_state),
                    "REDDOG_MODEL_SELECTION_RECEIPT_PATH": str(model_selection),
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_PATH": str(authority_source),
                    "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                    "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
                    "REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY": "0",
                    "REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY": "0",
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY": "0",
                },
                clear=True,
            ):
                assert main.run_reddog_architect_fix_promotion_preflight(repo) is True

    handoff.assert_called_once()
    handoff_kwargs = handoff.call_args.kwargs
    assert handoff_kwargs["intent_id"] == "sha256:intent-handoff"
    assert handoff_kwargs["architect_determination_output_path"] == str(
        runtime_root / "architect_determination.json"
    )
    assert handoff_kwargs["memex_supply_receipt_output_path"] == str(runtime_root / "memex_supply_receipt.json")
    promote.assert_called_once()
    promote_kwargs = promote.call_args.kwargs
    assert promote_kwargs["architect_determination_path"] == str(runtime_root / "architect_determination.json")
    assert promote_kwargs["memex_supply_receipt_path"] == str(runtime_root / "memex_supply_receipt.json")
    assert promote_kwargs["model_selection_receipt_path"] == str(model_selection)
    assert promote_kwargs["authority_profile_source_path"] == str(authority_source)
    assert promote_kwargs["authority_profile_output_path"] == str(runtime_root / "authority_profile.json")


def test_main_preflight_model_selection_supply_runs_before_promotion(tmp_path: Path) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    work_state = _write_json(tmp_path, "authoritative_work_state.json", _work_state())
    determination = _write_json(tmp_path, "architect_determination.json", _determination())
    memex = _write_json(tmp_path, "memex_supply_receipt.json", _memex_supply())
    authority_source = _write_json(tmp_path, "authority_profile_source.json", _authority_profile())
    model_supply_result = type(
        "ModelSupplyResult",
        (),
        {
            "accepted": True,
            "status": "MODEL_SELECTION_ARTIFACT_BOOTSTRAP_APPLIED",
            "model_selection_receipt_id": "model_selection_receipt:runtime",
            "output_path": str(runtime_root / "model_selection_receipt.json"),
            "rejection_reasons": (),
        },
    )()
    promotion_result = type(
        "PromotionResult",
        (),
        {
            "accepted": True,
            "status": REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED,
            "promotion_receipt_id": "sha256:promotion",
            "queue_item_id": "queue-1",
            "claim_id": "claim-1",
            "selected_slice": "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
            "authority_profile_path": str(runtime_root / "authority_profile.json"),
            "committed_revision": "sha256:revision",
            "rejection_reasons": (),
        },
    )()

    with patch(
        "modules.ai_intelligence.ai_gateway.src.model_selection_artifact_supply_bootstrap.run_reddog_model_selection_artifact_supply_bootstrap",
        return_value=model_supply_result,
    ) as model_supply:
        with patch(
            "modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap.run_reddog_main_architect_fix_promotion_bootstrap",
            return_value=promotion_result,
        ) as promote:
            with patch.dict(
                "os.environ",
                {
                    "REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY": "1",
                    "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(work_state),
                    "REDDOG_ARCHITECT_FIX_DETERMINATION_PATH": str(determination),
                    "REDDOG_MEMEX_SUPPLY_RECEIPT_PATH": str(memex),
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_PATH": str(authority_source),
                    "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                    "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
                    "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF": "0",
                    "REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY": "0",
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_CATALOG_SNAPSHOT_PATH": str(tmp_path / "catalog.json"),
                    "REDDOG_MODEL_PRODUCTION_EVIDENCE_BUNDLE_PATH": str(tmp_path / "evidence.json"),
                    "REDDOG_MODEL_SELECTION_REQUIREMENTS_PATH": str(tmp_path / "requirements.json"),
                    "REDDOG_MODEL_EVIDENCE_TRUSTED_KEYS_PATH": str(tmp_path / "keys.json"),
                    "REDDOG_MODEL_SELECTION_EVIDENCE_NOW_EPOCH": "1800000000",
                },
                clear=True,
            ):
                assert main.run_reddog_architect_fix_promotion_preflight(repo) is True
                assert main.os.environ["REDDOG_MODEL_SELECTION_RECEIPT_PATH"] == str(
                    runtime_root / "model_selection_receipt.json"
                )

    model_supply.assert_called_once()
    model_kwargs = model_supply.call_args.kwargs
    assert model_kwargs["output_path"] == str(runtime_root / "model_selection_receipt.json")
    assert model_kwargs["now_epoch"] == 1_800_000_000
    promote.assert_called_once()
    promote_kwargs = promote.call_args.kwargs
    assert promote_kwargs["model_selection_receipt_path"] == str(runtime_root / "model_selection_receipt.json")
    assert promote_kwargs["model_runtime_binding_receipt_path"] is None


def test_main_preflight_model_runtime_binding_supply_runs_after_model_selection(
    tmp_path: Path,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    work_state = _write_json(tmp_path, "authoritative_work_state.json", _work_state())
    determination = _write_json(tmp_path, "architect_determination.json", _determination())
    memex = _write_json(tmp_path, "memex_supply_receipt.json", _memex_supply())
    authority_source = _write_json(tmp_path, "authority_profile_source.json", _authority_profile())
    model_supply_result = type(
        "ModelSupplyResult",
        (),
        {
            "accepted": True,
            "status": "MODEL_SELECTION_ARTIFACT_BOOTSTRAP_APPLIED",
            "model_selection_receipt_id": "model_selection_receipt:runtime",
            "output_path": str(runtime_root / "model_selection_receipt.json"),
            "rejection_reasons": (),
        },
    )()
    runtime_binding_supply_result = type(
        "RuntimeBindingSupplyResult",
        (),
        {
            "accepted": True,
            "status": "MODEL_RUNTIME_BINDING_ARTIFACT_BOOTSTRAP_APPLIED",
            "runtime_binding_receipt_id": "reddog_model_runtime_binding:runtime",
            "output_path": str(runtime_root / "model_runtime_binding_receipt.json"),
            "rejection_reasons": (),
        },
    )()
    promotion_result = type(
        "PromotionResult",
        (),
        {
            "accepted": True,
            "status": REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED,
            "promotion_receipt_id": "sha256:promotion",
            "queue_item_id": "queue-1",
            "claim_id": "claim-1",
            "selected_slice": "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
            "authority_profile_path": str(runtime_root / "authority_profile.json"),
            "committed_revision": "sha256:revision",
            "rejection_reasons": (),
        },
    )()

    with patch(
        "modules.ai_intelligence.ai_gateway.src.model_selection_artifact_supply_bootstrap.run_reddog_model_selection_artifact_supply_bootstrap",
        return_value=model_supply_result,
    ) as model_supply:
        with patch(
            "modules.ai_intelligence.ai_gateway.src.model_runtime_binding_artifact_supply_bootstrap.run_reddog_model_runtime_binding_artifact_supply_bootstrap",
            return_value=runtime_binding_supply_result,
        ) as runtime_binding_supply:
            with patch(
                "modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap.run_reddog_main_architect_fix_promotion_bootstrap",
                return_value=promotion_result,
            ) as promote:
                with patch.dict(
                    "os.environ",
                    {
                        "REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY": "1",
                        "REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY": "1",
                        "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(work_state),
                        "REDDOG_ARCHITECT_FIX_DETERMINATION_PATH": str(determination),
                        "REDDOG_MEMEX_SUPPLY_RECEIPT_PATH": str(memex),
                        "REDDOG_AUTHORITY_PROFILE_SOURCE_PATH": str(authority_source),
                        "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                        "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
                        "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF": "0",
                        "REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY": "0",
                        "REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY": "0",
                        "REDDOG_MODEL_CATALOG_SNAPSHOT_PATH": str(tmp_path / "catalog.json"),
                        "REDDOG_MODEL_PRODUCTION_EVIDENCE_BUNDLE_PATH": str(tmp_path / "evidence.json"),
                        "REDDOG_MODEL_SELECTION_REQUIREMENTS_PATH": str(tmp_path / "requirements.json"),
                        "REDDOG_MODEL_EVIDENCE_TRUSTED_KEYS_PATH": str(tmp_path / "keys.json"),
                        "REDDOG_MODEL_BENCHMARK_EVIDENCE_RECEIPTS_PATH": str(tmp_path / "benchmarks.json"),
                        "REDDOG_MODEL_PROMOTION_EVIDENCE_RECEIPTS_PATH": str(tmp_path / "promotions.json"),
                        "REDDOG_MODEL_RUNTIME_BINDING_POLICY_PATH": str(tmp_path / "policy.json"),
                        "REDDOG_MODEL_RUNTIME_BINDING_EVIDENCE_NOW_EPOCH": "1800000001",
                    },
                    clear=True,
                ):
                    assert main.run_reddog_architect_fix_promotion_preflight(repo) is True
                    assert main.os.environ["REDDOG_MODEL_SELECTION_RECEIPT_PATH"] == str(
                        runtime_root / "model_selection_receipt.json"
                    )
                    assert main.os.environ["REDDOG_MODEL_RUNTIME_BINDING_RECEIPT_PATH"] == str(
                        runtime_root / "model_runtime_binding_receipt.json"
                    )

    model_supply.assert_called_once()
    runtime_binding_supply.assert_called_once()
    runtime_kwargs = runtime_binding_supply.call_args.kwargs
    assert runtime_kwargs["model_selection_receipt_path"] == str(runtime_root / "model_selection_receipt.json")
    assert runtime_kwargs["output_path"] == str(runtime_root / "model_runtime_binding_receipt.json")
    assert runtime_kwargs["now_epoch"] == 1_800_000_001
    promote.assert_called_once()
    promote_kwargs = promote.call_args.kwargs
    assert promote_kwargs["model_selection_receipt_path"] == str(runtime_root / "model_selection_receipt.json")
    assert promote_kwargs["model_runtime_binding_receipt_path"] == str(
        runtime_root / "model_runtime_binding_receipt.json"
    )


def test_main_preflight_model_autoresearch_plan_supply_runs_before_promotion(
    tmp_path: Path,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    work_state = _write_json(tmp_path, "authoritative_work_state.json", _work_state())
    determination = _write_json(tmp_path, "architect_determination.json", _determination())
    memex = _write_json(tmp_path, "memex_supply_receipt.json", _memex_supply())
    authority_source = _write_json(tmp_path, "authority_profile_source.json", _authority_profile())
    autoresearch_supply_result = type(
        "AutoResearchSupplyResult",
        (),
        {
            "accepted": True,
            "status": "MODEL_AUTORESEARCH_PLAN_ARTIFACT_BOOTSTRAP_APPLIED",
            "plan_receipt_id": "model_autoresearch_plan:runtime",
            "output_path": str(runtime_root / "model_autoresearch_plan_receipt.json"),
            "source_gate_receipt_ids": ("model_promotion_gate:1",),
            "source_feedback_record_ids": ("model_feedback_runtime",),
            "campaign_item_count": 1,
            "rejection_reasons": (),
        },
    )()
    promotion_result = type(
        "PromotionResult",
        (),
        {
            "accepted": True,
            "status": REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED,
            "promotion_receipt_id": "sha256:promotion",
            "queue_item_id": "queue-1",
            "claim_id": "claim-1",
            "selected_slice": "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
            "authority_profile_path": str(runtime_root / "authority_profile.json"),
            "committed_revision": "sha256:revision",
            "rejection_reasons": (),
        },
    )()

    with patch(
        "modules.ai_intelligence.ai_gateway.src.model_autoresearch_plan_artifact_supply_bootstrap.run_reddog_model_autoresearch_plan_artifact_supply_bootstrap",
        return_value=autoresearch_supply_result,
    ) as autoresearch_supply:
        with patch(
            "modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap.run_reddog_main_architect_fix_promotion_bootstrap",
            return_value=promotion_result,
        ) as promote:
            with patch.dict(
                "os.environ",
                {
                    "REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY": "1",
                    "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(work_state),
                    "REDDOG_ARCHITECT_FIX_DETERMINATION_PATH": str(determination),
                    "REDDOG_MEMEX_SUPPLY_RECEIPT_PATH": str(memex),
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_PATH": str(authority_source),
                    "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                    "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
                    "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF": "0",
                    "REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY": "0",
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_PROMOTION_GATE_RECEIPTS_PATH": str(
                        tmp_path / "promotion_gates.json"
                    ),
                    "REDDOG_MODEL_AUTORESEARCH_CANDIDATE_POOL_PATH": str(tmp_path / "candidates.json"),
                    "REDDOG_MODEL_AUTORESEARCH_POLICY_PATH": str(tmp_path / "autoresearch_policy.json"),
                    "REDDOG_MODEL_AUTORESEARCH_FEEDBACK_RECORDS_PATH": str(tmp_path / "feedback.jsonl"),
                },
                clear=True,
            ):
                assert main.run_reddog_architect_fix_promotion_preflight(repo) is True
                assert main.os.environ["REDDOG_MODEL_AUTORESEARCH_PLAN_RECEIPT_PATH"] == str(
                    runtime_root / "model_autoresearch_plan_receipt.json"
                )

    autoresearch_supply.assert_called_once()
    autoresearch_kwargs = autoresearch_supply.call_args.kwargs
    assert autoresearch_kwargs["promotion_gate_receipts_path"] == str(tmp_path / "promotion_gates.json")
    assert autoresearch_kwargs["candidate_pool_path"] == str(tmp_path / "candidates.json")
    assert autoresearch_kwargs["policy_path"] == str(tmp_path / "autoresearch_policy.json")
    assert autoresearch_kwargs["feedback_records_path"] == str(tmp_path / "feedback.jsonl")
    assert autoresearch_kwargs["output_path"] == str(runtime_root / "model_autoresearch_plan_receipt.json")
    promote.assert_called_once()


def test_main_preflight_enforced_model_autoresearch_plan_supply_blocks_startup(
    tmp_path: Path,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    autoresearch_supply_result = type(
        "AutoResearchSupplyResult",
        (),
        {
            "accepted": False,
            "status": "MODEL_AUTORESEARCH_PLAN_ARTIFACT_BOOTSTRAP_NOT_READY",
            "plan_receipt_id": None,
            "output_path": None,
            "source_gate_receipt_ids": (),
            "source_feedback_record_ids": (),
            "campaign_item_count": 0,
            "rejection_reasons": ("missing_model_autoresearch_policy_path",),
        },
    )()

    with patch(
        "modules.ai_intelligence.ai_gateway.src.model_autoresearch_plan_artifact_supply_bootstrap.run_reddog_model_autoresearch_plan_artifact_supply_bootstrap",
        return_value=autoresearch_supply_result,
    ):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY": "1",
                "REDDOG_MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY_ENFORCED": "1",
                "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
            },
            clear=True,
        ):
            assert main.run_reddog_architect_fix_promotion_preflight(repo) is False


def test_main_preflight_model_autoresearch_campaign_execution_supply_runs_before_promotion(
    tmp_path: Path,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    work_state = _write_json(tmp_path, "authoritative_work_state.json", _work_state())
    determination = _write_json(tmp_path, "architect_determination.json", _determination())
    memex = _write_json(tmp_path, "memex_supply_receipt.json", _memex_supply())
    authority_source = _write_json(tmp_path, "authority_profile_source.json", _authority_profile())
    campaign_result = type(
        "AutoResearchCampaignResult",
        (),
        {
            "accepted": True,
            "status": "MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_APPLIED",
            "execution_receipt_id": "model_autoresearch_campaign_execution:runtime",
            "source_plan_receipt_id": "model_autoresearch_plan:runtime",
            "benchmark_run_receipt_id": "model_benchmark_run:runtime",
            "output_path": str(runtime_root / "model_autoresearch_campaign_execution_receipt.json"),
            "executed_candidate_ids": ("provider/new",),
            "task_count": 2,
            "rejection_reasons": (),
        },
    )()
    promotion_result = type(
        "PromotionResult",
        (),
        {
            "accepted": True,
            "status": REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED,
            "promotion_receipt_id": "sha256:promotion",
            "queue_item_id": "queue-1",
            "claim_id": "claim-1",
            "selected_slice": "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
            "authority_profile_path": str(runtime_root / "authority_profile.json"),
            "committed_revision": "sha256:revision",
            "rejection_reasons": (),
        },
    )()

    with patch(
        "modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution_artifact_supply_bootstrap.run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap",
        return_value=campaign_result,
    ) as campaign_supply:
        with patch(
            "modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap.run_reddog_main_architect_fix_promotion_bootstrap",
            return_value=promotion_result,
        ) as promote:
            with patch.dict(
                "os.environ",
                {
                    "REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ARTIFACT_SUPPLY": "1",
                    "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(work_state),
                    "REDDOG_ARCHITECT_FIX_DETERMINATION_PATH": str(determination),
                    "REDDOG_MEMEX_SUPPLY_RECEIPT_PATH": str(memex),
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_PATH": str(authority_source),
                    "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                    "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
                    "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF": "0",
                    "REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY": "0",
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_CANDIDATE_POOL_PATH": str(tmp_path / "candidates.json"),
                    "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_TASKS_PATH": str(tmp_path / "tasks.json"),
                    "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_VERIFIER_DIGEST": "sha256:verifier",
                    "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_HELD_OUT_SPLIT_ID": "heldout-v1",
                },
                clear=True,
            ):
                assert main.run_reddog_architect_fix_promotion_preflight(repo) is True
                assert main.os.environ[
                    "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_RECEIPT_PATH"
                ] == str(runtime_root / "model_autoresearch_campaign_execution_receipt.json")

    campaign_supply.assert_called_once()
    campaign_kwargs = campaign_supply.call_args.kwargs
    assert campaign_kwargs["plan_receipt_path"] == str(runtime_root / "model_autoresearch_plan_receipt.json")
    assert campaign_kwargs["candidate_pool_path"] == str(tmp_path / "candidates.json")
    assert campaign_kwargs["tasks_path"] == str(tmp_path / "tasks.json")
    assert campaign_kwargs["output_path"] == str(runtime_root / "model_autoresearch_campaign_execution_receipt.json")
    assert campaign_kwargs["verifier_digest"] == "sha256:verifier"
    assert campaign_kwargs["held_out_split_id"] == "heldout-v1"
    promote.assert_called_once()


def test_main_preflight_enforced_model_autoresearch_campaign_execution_blocks_startup(
    tmp_path: Path,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    campaign_result = type(
        "AutoResearchCampaignResult",
        (),
        {
            "accepted": False,
            "status": "MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_BOOTSTRAP_NOT_READY",
            "execution_receipt_id": None,
            "source_plan_receipt_id": None,
            "benchmark_run_receipt_id": None,
            "output_path": None,
            "executed_candidate_ids": (),
            "task_count": 0,
            "rejection_reasons": ("missing_model_autoresearch_campaign_tasks_path",),
        },
    )()

    with patch(
        "modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_execution_artifact_supply_bootstrap.run_reddog_model_autoresearch_campaign_execution_artifact_supply_bootstrap",
        return_value=campaign_result,
    ):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ARTIFACT_SUPPLY": "1",
                "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ARTIFACT_SUPPLY_ENFORCED": "1",
                "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
            },
            clear=True,
        ):
            assert main.run_reddog_architect_fix_promotion_preflight(repo) is False


def test_main_preflight_model_autoresearch_campaign_gate_supply_runs_before_promotion(
    tmp_path: Path,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    work_state = _write_json(tmp_path, "authoritative_work_state.json", _work_state())
    determination = _write_json(tmp_path, "architect_determination.json", _determination())
    memex = _write_json(tmp_path, "memex_supply_receipt.json", _memex_supply())
    authority_source = _write_json(tmp_path, "authority_profile_source.json", _authority_profile())
    gate_result = type(
        "AutoResearchCampaignGateResult",
        (),
        {
            "accepted": True,
            "status": "MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_BOOTSTRAP_APPLIED",
            "supply_receipt_id": "model_autoresearch_campaign_promotion_gate_supply:runtime",
            "source_execution_receipt_id": "model_autoresearch_campaign_execution:runtime",
            "output_path": str(runtime_root / "model_autoresearch_promotion_gate_receipts.json"),
            "promotion_gate_receipt_ids": ("model_promotion_gate:1",),
            "rejection_reasons": (),
        },
    )()
    promotion_result = type(
        "PromotionResult",
        (),
        {
            "accepted": True,
            "status": REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED,
            "promotion_receipt_id": "sha256:promotion",
            "queue_item_id": "queue-1",
            "claim_id": "claim-1",
            "selected_slice": "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
            "authority_profile_path": str(runtime_root / "authority_profile.json"),
            "committed_revision": "sha256:revision",
            "rejection_reasons": (),
        },
    )()

    with patch(
        "modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_promotion_gate_supply_bootstrap.run_reddog_model_autoresearch_campaign_promotion_gate_supply_bootstrap",
        return_value=gate_result,
    ) as gate_supply:
        with patch(
            "modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap.run_reddog_main_architect_fix_promotion_bootstrap",
            return_value=promotion_result,
        ) as promote:
            with patch.dict(
                "os.environ",
                {
                    "REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY": "1",
                    "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(work_state),
                    "REDDOG_ARCHITECT_FIX_DETERMINATION_PATH": str(determination),
                    "REDDOG_MEMEX_SUPPLY_RECEIPT_PATH": str(memex),
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_PATH": str(authority_source),
                    "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                    "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
                    "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF": "0",
                    "REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY": "0",
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_PROMOTION_AUTHORITY_RECEIPT_ID": "authority:1",
                    "REDDOG_MODEL_AUTORESEARCH_SIGNED_PROMOTION_RECEIPT_ID": "signed:1",
                },
                clear=True,
            ):
                assert main.run_reddog_architect_fix_promotion_preflight(repo) is True
                assert main.os.environ["REDDOG_MODEL_AUTORESEARCH_PROMOTION_GATE_RECEIPTS_PATH"] == str(
                    runtime_root / "model_autoresearch_promotion_gate_receipts.json"
                )

    gate_supply.assert_called_once()
    gate_kwargs = gate_supply.call_args.kwargs
    assert gate_kwargs["campaign_execution_receipt_path"] == str(
        runtime_root / "model_autoresearch_campaign_execution_receipt.json"
    )
    assert gate_kwargs["promotion_policies_path"] == str(
        runtime_root / "model_autoresearch_campaign_promotion_policies.json"
    )
    assert gate_kwargs["output_path"] == str(runtime_root / "model_autoresearch_promotion_gate_receipts.json")
    assert gate_kwargs["promotion_authority_receipt_id"] == "authority:1"
    assert gate_kwargs["signed_promotion_receipt_id"] == "signed:1"
    promote.assert_called_once()


def test_main_preflight_enforced_model_autoresearch_campaign_gate_supply_blocks_startup(
    tmp_path: Path,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    gate_result = type(
        "AutoResearchCampaignGateResult",
        (),
        {
            "accepted": False,
            "status": "MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_BOOTSTRAP_NOT_READY",
            "supply_receipt_id": None,
            "source_execution_receipt_id": None,
            "output_path": None,
            "promotion_gate_receipt_ids": (),
            "rejection_reasons": ("missing_model_autoresearch_campaign_promotion_policies_path",),
        },
    )()

    with patch(
        "modules.ai_intelligence.ai_gateway.src.model_autoresearch_campaign_promotion_gate_supply_bootstrap.run_reddog_model_autoresearch_campaign_promotion_gate_supply_bootstrap",
        return_value=gate_result,
    ):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY": "1",
                "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_ENFORCED": "1",
                "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
            },
            clear=True,
        ):
            assert main.run_reddog_architect_fix_promotion_preflight(repo) is False


def test_main_preflight_model_autoresearch_cycle_receipt_supply_runs_before_promotion(
    tmp_path: Path,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    work_state = _write_json(tmp_path, "authoritative_work_state.json", _work_state())
    determination = _write_json(tmp_path, "architect_determination.json", _determination())
    memex = _write_json(tmp_path, "memex_supply_receipt.json", _memex_supply())
    authority_source = _write_json(tmp_path, "authority_profile_source.json", _authority_profile())
    cycle_result = type(
        "AutoResearchCycleResult",
        (),
        {
            "accepted": True,
            "status": "MODEL_AUTORESEARCH_CYCLE_RECEIPT_BOOTSTRAP_APPLIED",
            "cycle_receipt_id": "model_autoresearch_cycle:runtime",
            "output_path": str(runtime_root / "model_autoresearch_cycle_receipt.json"),
            "source_plan_receipt_id": "model_autoresearch_plan:runtime",
            "campaign_execution_receipt_id": "model_autoresearch_campaign_execution:runtime",
            "promotion_gate_supply_receipt_id": "model_autoresearch_campaign_promotion_gate_supply:runtime",
            "rejection_reasons": (),
        },
    )()
    promotion_result = type(
        "PromotionResult",
        (),
        {
            "accepted": True,
            "status": REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED,
            "promotion_receipt_id": "sha256:promotion",
            "queue_item_id": "queue-1",
            "claim_id": "claim-1",
            "selected_slice": "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
            "authority_profile_path": str(runtime_root / "authority_profile.json"),
            "committed_revision": "sha256:revision",
            "rejection_reasons": (),
        },
    )()

    with patch(
        "modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_receipt_supply_bootstrap.run_reddog_model_autoresearch_cycle_receipt_supply_bootstrap",
        return_value=cycle_result,
    ) as cycle_supply:
        with patch(
            "modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap.run_reddog_main_architect_fix_promotion_bootstrap",
            return_value=promotion_result,
        ) as promote:
            with patch.dict(
                "os.environ",
                {
                    "REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_SUPPLY": "1",
                    "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(work_state),
                    "REDDOG_ARCHITECT_FIX_DETERMINATION_PATH": str(determination),
                    "REDDOG_MEMEX_SUPPLY_RECEIPT_PATH": str(memex),
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_PATH": str(authority_source),
                    "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                    "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
                    "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF": "0",
                    "REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY": "0",
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY": "0",
                },
                clear=True,
            ):
                assert main.run_reddog_architect_fix_promotion_preflight(repo) is True
                assert main.os.environ["REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_PATH"] == str(
                    runtime_root / "model_autoresearch_cycle_receipt.json"
                )

    cycle_supply.assert_called_once()
    cycle_kwargs = cycle_supply.call_args.kwargs
    assert cycle_kwargs["plan_receipt_path"] == str(runtime_root / "model_autoresearch_plan_receipt.json")
    assert cycle_kwargs["campaign_execution_receipt_path"] == str(
        runtime_root / "model_autoresearch_campaign_execution_receipt.json"
    )
    assert cycle_kwargs["promotion_gate_supply_receipt_path"] == str(
        runtime_root / "model_autoresearch_promotion_gate_receipts.json"
    )
    assert cycle_kwargs["output_path"] == str(runtime_root / "model_autoresearch_cycle_receipt.json")
    promote.assert_called_once()


def test_main_preflight_enforced_model_autoresearch_cycle_receipt_supply_blocks_startup(
    tmp_path: Path,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    cycle_result = type(
        "AutoResearchCycleResult",
        (),
        {
            "accepted": False,
            "status": "MODEL_AUTORESEARCH_CYCLE_RECEIPT_BOOTSTRAP_NOT_READY",
            "cycle_receipt_id": None,
            "output_path": None,
            "source_plan_receipt_id": None,
            "campaign_execution_receipt_id": None,
            "promotion_gate_supply_receipt_id": None,
            "rejection_reasons": ("missing_model_autoresearch_cycle_gate_supply_receipt_path",),
        },
    )()

    with patch(
        "modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_receipt_supply_bootstrap.run_reddog_model_autoresearch_cycle_receipt_supply_bootstrap",
        return_value=cycle_result,
    ):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_SUPPLY": "1",
                "REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_SUPPLY_ENFORCED": "1",
                "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
            },
            clear=True,
        ):
            assert main.run_reddog_architect_fix_promotion_preflight(repo) is False


def test_main_preflight_model_autoresearch_cycle_feedback_admission_runs_before_promotion(
    tmp_path: Path,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    work_state = _write_json(tmp_path, "authoritative_work_state.json", _work_state())
    determination = _write_json(tmp_path, "architect_determination.json", _determination())
    memex = _write_json(tmp_path, "memex_supply_receipt.json", _memex_supply())
    authority_source = _write_json(tmp_path, "authority_profile_source.json", _authority_profile())
    cycle_feedback_result = type(
        "AutoResearchCycleFeedbackResult",
        (),
        {
            "accepted": True,
            "status": "MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_BOOTSTRAP_APPLIED",
            "admission_id": "model_autoresearch_cycle_feedback_admission:runtime",
            "cycle_receipt_id": "model_autoresearch_cycle:runtime",
            "feedback_record_id": "model_autoresearch_cycle_feedback:runtime",
            "output_path": str(runtime_root / "model_autoresearch_cycle_feedback.jsonl"),
            "rejection_reasons": (),
        },
    )()
    promotion_result = type(
        "PromotionResult",
        (),
        {
            "accepted": True,
            "status": REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED,
            "promotion_receipt_id": "sha256:promotion",
            "queue_item_id": "queue-1",
            "claim_id": "claim-1",
            "selected_slice": "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
            "authority_profile_path": str(runtime_root / "authority_profile.json"),
            "committed_revision": "sha256:revision",
            "rejection_reasons": (),
        },
    )()

    with patch(
        "modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_feedback_ledger_admission_bootstrap.run_reddog_model_autoresearch_cycle_feedback_ledger_admission_bootstrap",
        return_value=cycle_feedback_result,
    ) as cycle_feedback:
        with patch(
            "modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap.run_reddog_main_architect_fix_promotion_bootstrap",
            return_value=promotion_result,
        ) as promote:
            with patch.dict(
                "os.environ",
                {
                    "REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_PLAN_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_SUPPLY": "0",
                    "REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION": "1",
                    "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(work_state),
                    "REDDOG_ARCHITECT_FIX_DETERMINATION_PATH": str(determination),
                    "REDDOG_MEMEX_SUPPLY_RECEIPT_PATH": str(memex),
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_PATH": str(authority_source),
                    "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                    "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
                    "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF": "0",
                    "REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY": "0",
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY": "0",
                },
                clear=True,
            ):
                assert main.run_reddog_architect_fix_promotion_preflight(repo) is True
                assert main.os.environ["REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_PATH"] == str(
                    runtime_root / "model_autoresearch_cycle_feedback.jsonl"
                )

    cycle_feedback.assert_called_once()
    cycle_feedback_kwargs = cycle_feedback.call_args.kwargs
    assert cycle_feedback_kwargs["plan_receipt_path"] == str(runtime_root / "model_autoresearch_plan_receipt.json")
    assert cycle_feedback_kwargs["cycle_receipt_path"] == str(
        runtime_root / "model_autoresearch_cycle_receipt.json"
    )
    assert cycle_feedback_kwargs["output_path"] == str(
        runtime_root / "model_autoresearch_cycle_feedback.jsonl"
    )
    promote.assert_called_once()


def test_main_preflight_enforced_model_autoresearch_cycle_feedback_admission_blocks_startup(
    tmp_path: Path,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    cycle_feedback_result = type(
        "AutoResearchCycleFeedbackResult",
        (),
        {
            "accepted": False,
            "status": "MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_BOOTSTRAP_NOT_READY",
            "admission_id": None,
            "cycle_receipt_id": None,
            "feedback_record_id": None,
            "output_path": None,
            "rejection_reasons": ("missing_model_autoresearch_cycle_receipt_path",),
        },
    )()

    with patch(
        "modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_feedback_ledger_admission_bootstrap.run_reddog_model_autoresearch_cycle_feedback_ledger_admission_bootstrap",
        return_value=cycle_feedback_result,
    ):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION": "1",
                "REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_ENFORCED": "1",
                "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
            },
            clear=True,
        ):
            assert main.run_reddog_architect_fix_promotion_preflight(repo) is False


def test_main_preflight_enforced_model_runtime_binding_supply_blocks_promotion(
    tmp_path: Path,
) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    work_state = _write_json(tmp_path, "authoritative_work_state.json", _work_state())
    determination = _write_json(tmp_path, "architect_determination.json", _determination())
    model_selection = _write_json(tmp_path, "model_selection_receipt.json", _model_selection())
    memex = _write_json(tmp_path, "memex_supply_receipt.json", _memex_supply())
    authority_source = _write_json(tmp_path, "authority_profile_source.json", _authority_profile())
    runtime_binding_supply_result = type(
        "RuntimeBindingSupplyResult",
        (),
        {
            "accepted": False,
            "status": "MODEL_RUNTIME_BINDING_ARTIFACT_BOOTSTRAP_NOT_READY",
            "runtime_binding_receipt_id": None,
            "output_path": None,
            "rejection_reasons": ("missing_model_runtime_binding_policy_path",),
        },
    )()

    with patch(
        "modules.ai_intelligence.ai_gateway.src.model_runtime_binding_artifact_supply_bootstrap.run_reddog_model_runtime_binding_artifact_supply_bootstrap",
        return_value=runtime_binding_supply_result,
    ) as runtime_binding_supply:
        with patch(
            "modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap.run_reddog_main_architect_fix_promotion_bootstrap",
        ) as promote:
            with patch.dict(
                "os.environ",
                {
                    "REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY": "1",
                    "REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_ENFORCED": "1",
                    "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(work_state),
                    "REDDOG_ARCHITECT_FIX_DETERMINATION_PATH": str(determination),
                    "REDDOG_MODEL_SELECTION_RECEIPT_PATH": str(model_selection),
                    "REDDOG_MEMEX_SUPPLY_RECEIPT_PATH": str(memex),
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_PATH": str(authority_source),
                    "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                    "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
                    "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF": "0",
                    "REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY": "0",
                    "REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY": "0",
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY": "0",
                    "REDDOG_MODEL_CATALOG_SNAPSHOT_PATH": str(tmp_path / "catalog.json"),
                    "REDDOG_MODEL_PRODUCTION_EVIDENCE_BUNDLE_PATH": str(tmp_path / "evidence.json"),
                    "REDDOG_MODEL_EVIDENCE_TRUSTED_KEYS_PATH": str(tmp_path / "keys.json"),
                    "REDDOG_MODEL_BENCHMARK_EVIDENCE_RECEIPTS_PATH": str(tmp_path / "benchmarks.json"),
                    "REDDOG_MODEL_PROMOTION_EVIDENCE_RECEIPTS_PATH": str(tmp_path / "promotions.json"),
                },
                clear=True,
            ):
                assert main.run_reddog_architect_fix_promotion_preflight(repo) is False

    runtime_binding_supply.assert_called_once()
    promote.assert_not_called()


def test_main_preflight_authority_source_supply_runs_before_promotion(tmp_path: Path) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    work_state = _write_json(tmp_path, "authoritative_work_state.json", _work_state())
    determination = _write_json(tmp_path, "architect_determination.json", _determination())
    model_selection = _write_json(tmp_path, "model_selection_receipt.json", _model_selection())
    memex = _write_json(tmp_path, "memex_supply_receipt.json", _memex_supply())
    authority_supply_result = type(
        "AuthoritySupplyResult",
        (),
        {
            "accepted": True,
            "status": "AUTHORITY_PROFILE_SOURCE_BOOTSTRAP_APPLIED",
            "authority_profile_source_receipt_id": "sha256:authority-source",
            "output_path": str(runtime_root / "authority_profile_source.json"),
            "rejection_reasons": (),
        },
    )()
    promotion_result = type(
        "PromotionResult",
        (),
        {
            "accepted": True,
            "status": REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED,
            "promotion_receipt_id": "sha256:promotion",
            "queue_item_id": "queue-1",
            "claim_id": "claim-1",
            "selected_slice": "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
            "authority_profile_path": str(runtime_root / "authority_profile.json"),
            "committed_revision": "sha256:revision",
            "rejection_reasons": (),
        },
    )()

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_authority_profile_source_artifact_supply_bootstrap.run_reddog_authority_profile_source_artifact_supply_bootstrap",
        return_value=authority_supply_result,
    ) as authority_supply:
        with patch(
            "modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap.run_reddog_main_architect_fix_promotion_bootstrap",
            return_value=promotion_result,
        ) as promote:
            with patch.dict(
                "os.environ",
                {
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY": "1",
                    "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(work_state),
                    "REDDOG_ARCHITECT_FIX_DETERMINATION_PATH": str(determination),
                    "REDDOG_MODEL_SELECTION_RECEIPT_PATH": str(model_selection),
                    "REDDOG_MEMEX_SUPPLY_RECEIPT_PATH": str(memex),
                    "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                    "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
                    "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF": "0",
                    "REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY": "0",
                    "REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY": "0",
                    "REDDOG_AUTHORITY_PROFILE_SEED_PATH": str(tmp_path / "seed.json"),
                    "REDDOG_PRINCIPAL_AUTHORITY_RECORD_PATH": str(tmp_path / "principal.json"),
                    "REDDOG_PERMISSION_SNAPSHOT_PATH": str(tmp_path / "permission.json"),
                    "REDDOG_AUTHORITY_PROFILE_SOURCE_NOW_EPOCH": "1800000000",
                },
                clear=True,
            ):
                assert main.run_reddog_architect_fix_promotion_preflight(repo) is True
                assert main.os.environ["REDDOG_AUTHORITY_PROFILE_SOURCE_PATH"] == str(
                    runtime_root / "authority_profile_source.json"
                )

    authority_supply.assert_called_once()
    authority_kwargs = authority_supply.call_args.kwargs
    assert authority_kwargs["output_path"] == str(runtime_root / "authority_profile_source.json")
    assert authority_kwargs["now_epoch"] == 1_800_000_000
    promote.assert_called_once()
    promote_kwargs = promote.call_args.kwargs
    assert promote_kwargs["authority_profile_source_path"] == str(runtime_root / "authority_profile_source.json")


def test_main_preflight_profile_runs_artifact_supply_chain_before_promotion(tmp_path: Path) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    work_state = runtime_root / "authoritative_work_state.json"
    handoff_result = type(
        "HandoffResult",
        (),
        {
            "accepted": True,
            "status": "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF_APPLIED",
            "architect_determination_id": "architect_determination:profile",
            "architect_determination_path": str(runtime_root / "architect_determination.json"),
            "memex_supply_receipt_path": str(runtime_root / "memex_supply_receipt.json"),
            "rejection_reasons": (),
        },
    )()
    model_supply_result = type(
        "ModelSupplyResult",
        (),
        {
            "accepted": True,
            "status": "MODEL_SELECTION_BOOTSTRAP_APPLIED",
            "model_selection_receipt_id": "model_selection_receipt:profile",
            "output_path": str(runtime_root / "model_selection_receipt.json"),
            "rejection_reasons": (),
        },
    )()
    principal_snapshot_result = type(
        "PrincipalSnapshotResult",
        (),
        {
            "accepted": True,
            "status": "GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_BOOTSTRAP_APPLIED",
            "receipt_id": "sha256:principal-snapshot-profile",
            "principal_authority_record_path": str(runtime_root / "principal_authority_record.json"),
            "permission_snapshot_path": str(runtime_root / "permission_snapshot.json"),
            "principal_id": "github:mjtrout",
            "permission_snapshot_digest": "sha256:permission",
            "rejection_reasons": (),
        },
    )()
    seed_supply_result = type(
        "SeedSupplyResult",
        (),
        {
            "accepted": True,
            "status": "AUTHORITY_PROFILE_SEED_BOOTSTRAP_APPLIED",
            "seed_supply_receipt_id": "sha256:authority-seed-profile",
            "output_path": str(runtime_root / "authority_profile_seed.json"),
            "rejection_reasons": (),
        },
    )()
    authority_supply_result = type(
        "AuthoritySupplyResult",
        (),
        {
            "accepted": True,
            "status": "AUTHORITY_PROFILE_SOURCE_BOOTSTRAP_APPLIED",
            "authority_profile_source_receipt_id": "sha256:authority-source-profile",
            "output_path": str(runtime_root / "authority_profile_source.json"),
            "rejection_reasons": (),
        },
    )()
    promotion_result = type(
        "PromotionResult",
        (),
        {
            "accepted": True,
            "status": REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_APPLIED,
            "promotion_receipt_id": "sha256:promotion",
            "queue_item_id": "queue-1",
            "claim_id": "claim-1",
            "selected_slice": "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
            "authority_profile_path": str(runtime_root / "authority_profile.json"),
            "committed_revision": "sha256:revision",
            "rejection_reasons": (),
        },
    )()

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_fix_promotion_artifact_handoff.run_reddog_resident_fix_promotion_artifact_handoff",
        return_value=handoff_result,
    ) as handoff:
        with patch(
            "modules.ai_intelligence.ai_gateway.src.model_selection_artifact_supply_bootstrap.run_reddog_model_selection_artifact_supply_bootstrap",
            return_value=model_supply_result,
        ) as model_supply:
            with patch(
                "modules.communication.moltbot_bridge.src.reddog_github_principal_permission_snapshot_supply_bootstrap.run_reddog_github_principal_permission_snapshot_supply_bootstrap",
                return_value=principal_snapshot_result,
            ) as principal_snapshot_supply:
                with patch(
                    "modules.communication.moltbot_bridge.src.reddog_authority_profile_seed_supply_bootstrap.run_reddog_authority_profile_seed_supply_bootstrap",
                    return_value=seed_supply_result,
                ) as seed_supply:
                    with patch(
                        "modules.communication.moltbot_bridge.src.reddog_authority_profile_source_artifact_supply_bootstrap.run_reddog_authority_profile_source_artifact_supply_bootstrap",
                        return_value=authority_supply_result,
                    ) as authority_supply:
                        with patch(
                            "modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap.run_reddog_main_architect_fix_promotion_bootstrap",
                            return_value=promotion_result,
                        ) as promote:
                            with patch.dict(
                                "os.environ",
                                {
                                    "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                                    "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
                                    "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(work_state),
                                    "REDDOG_RESIDENT_ARCHITECT_INTENT_ID": "intent-profile",
                                    "REDDOG_MODEL_CATALOG_SNAPSHOT_PATH": str(tmp_path / "catalog.json"),
                                    "REDDOG_MODEL_PRODUCTION_EVIDENCE_BUNDLE_PATH": str(tmp_path / "evidence.json"),
                                    "REDDOG_MODEL_SELECTION_REQUIREMENTS_PATH": str(tmp_path / "requirements.json"),
                                    "REDDOG_MODEL_EVIDENCE_TRUSTED_KEYS_PATH": str(tmp_path / "keys.json"),
                                    "REDDOG_GITHUB_REPO_FULL_NAME": "FOUNDUPS/Foundups-Agent",
                                    "REDDOG_AUTHORITY_FOUNDUP_ID": "paccess_001",
                                    "REDDOG_PRINCIPAL_PUBLIC_KEY": "pub:principal",
                                    "REDDOG_REDDOG_PUBLIC_KEY": "pub:reddog",
                                },
                                clear=True,
                            ):
                                assert main.run_reddog_architect_fix_promotion_preflight(repo) is True

    handoff.assert_called_once()
    handoff_kwargs = handoff.call_args.kwargs
    assert handoff_kwargs["architect_determination_output_path"] == str(
        runtime_root / "architect_determination.json"
    )
    assert handoff_kwargs["memex_supply_receipt_output_path"] == str(
        runtime_root / "memex_supply_receipt.json"
    )
    model_supply.assert_called_once()
    assert model_supply.call_args.kwargs["output_path"] == str(runtime_root / "model_selection_receipt.json")
    principal_snapshot_supply.assert_called_once()
    assert principal_snapshot_supply.call_args.kwargs["principal_authority_record_output_path"] == str(
        runtime_root / "principal_authority_record.json"
    )
    assert principal_snapshot_supply.call_args.kwargs["permission_snapshot_output_path"] == str(
        runtime_root / "permission_snapshot.json"
    )
    seed_supply.assert_called_once()
    assert seed_supply.call_args.kwargs["output_path"] == str(runtime_root / "authority_profile_seed.json")
    assert seed_supply.call_args.kwargs["architect_determination_path"] == str(
        runtime_root / "architect_determination.json"
    )
    assert seed_supply.call_args.kwargs["model_selection_receipt_path"] == str(
        runtime_root / "model_selection_receipt.json"
    )
    assert seed_supply.call_args.kwargs["memex_supply_receipt_path"] == str(
        runtime_root / "memex_supply_receipt.json"
    )
    assert seed_supply.call_args.kwargs["principal_authority_record_path"] == str(
        runtime_root / "principal_authority_record.json"
    )
    assert seed_supply.call_args.kwargs["permission_snapshot_path"] == str(
        runtime_root / "permission_snapshot.json"
    )
    assert seed_supply.call_args.kwargs["reddog_public_key"] == "pub:reddog"
    authority_supply.assert_called_once()
    assert authority_supply.call_args.kwargs["authority_seed_path"] == str(runtime_root / "authority_profile_seed.json")
    assert authority_supply.call_args.kwargs["output_path"] == str(runtime_root / "authority_profile_source.json")
    assert authority_supply.call_args.kwargs["principal_authority_record_path"] == str(
        runtime_root / "principal_authority_record.json"
    )
    assert authority_supply.call_args.kwargs["permission_snapshot_path"] == str(
        runtime_root / "permission_snapshot.json"
    )
    promote.assert_called_once()
    promote_kwargs = promote.call_args.kwargs
    assert promote_kwargs["architect_determination_path"] == str(runtime_root / "architect_determination.json")
    assert promote_kwargs["model_selection_receipt_path"] == str(runtime_root / "model_selection_receipt.json")
    assert promote_kwargs["memex_supply_receipt_path"] == str(runtime_root / "memex_supply_receipt.json")
    assert promote_kwargs["authority_profile_source_path"] == str(runtime_root / "authority_profile_source.json")


def test_main_preflight_explicit_zero_overrides_profile_artifact_supply(tmp_path: Path) -> None:
    import main

    repo = _repo(tmp_path)
    with patch(
        "modules.communication.moltbot_bridge.src.reddog_resident_fix_promotion_artifact_handoff.run_reddog_resident_fix_promotion_artifact_handoff",
        side_effect=AssertionError("handoff supply must not run"),
    ):
        with patch(
            "modules.ai_intelligence.ai_gateway.src.model_selection_artifact_supply_bootstrap.run_reddog_model_selection_artifact_supply_bootstrap",
            side_effect=AssertionError("model supply must not run"),
        ):
            with patch(
                "modules.communication.moltbot_bridge.src.reddog_github_principal_permission_snapshot_supply_bootstrap.run_reddog_github_principal_permission_snapshot_supply_bootstrap",
                side_effect=AssertionError("principal snapshot supply must not run"),
            ):
                with patch(
                    "modules.communication.moltbot_bridge.src.reddog_authority_profile_seed_supply_bootstrap.run_reddog_authority_profile_seed_supply_bootstrap",
                    side_effect=AssertionError("authority seed supply must not run"),
                ):
                    with patch(
                        "modules.communication.moltbot_bridge.src.reddog_authority_profile_source_artifact_supply_bootstrap.run_reddog_authority_profile_source_artifact_supply_bootstrap",
                        side_effect=AssertionError("authority supply must not run"),
                    ):
                        with patch.dict(
                            "os.environ",
                            {
                                "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code",
                                "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF": "0",
                                "REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY": "0",
                                "REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY": "0",
                                "REDDOG_AUTHORITY_PROFILE_SEED_SUPPLY": "0",
                                "REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY": "0",
                            },
                            clear=True,
                        ):
                            assert main.run_reddog_architect_fix_promotion_preflight(repo) is True


def test_main_preflight_enforced_blocks_principal_snapshot_rejection(tmp_path: Path) -> None:
    import main

    repo = _repo(tmp_path)
    runtime_root = tmp_path / "runtime"
    rejected = type(
        "PrincipalSnapshotResult",
        (),
        {
            "accepted": False,
            "status": "GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_BOOTSTRAP_NOT_READY",
            "receipt_id": None,
            "principal_authority_record_path": None,
            "permission_snapshot_path": None,
            "principal_id": None,
            "permission_snapshot_digest": None,
            "rejection_reasons": ("missing_principal_public_key",),
        },
    )()

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_github_principal_permission_snapshot_supply_bootstrap.run_reddog_github_principal_permission_snapshot_supply_bootstrap",
        return_value=rejected,
    ):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY": "1",
                "REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_ENFORCED": "1",
                "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
                "REDDOG_GITHUB_REPO_FULL_NAME": "FOUNDUPS/Foundups-Agent",
                "REDDOG_AUTHORITY_FOUNDUP_ID": "paccess_001",
            },
            clear=True,
        ):
            assert main.run_reddog_architect_fix_promotion_preflight(repo) is False


def test_main_preflight_disabled_without_requested_or_complete_inputs() -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap.run_reddog_main_architect_fix_promotion_bootstrap",
    ) as mocked:
        with patch.dict("os.environ", {}, clear=True):
            assert main.run_reddog_architect_fix_promotion_preflight(REPO_ROOT) is True

    assert mocked.called is False


def test_main_preflight_enforced_blocks_rejection() -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap.run_reddog_main_architect_fix_promotion_bootstrap",
        return_value=type(
            "Result",
            (),
            {
                "accepted": False,
                "status": REDDOG_ARCHITECT_FIX_PROMOTION_BOOTSTRAP_NOT_READY,
                "promotion_receipt_id": None,
                "queue_item_id": None,
                "claim_id": None,
                "selected_slice": None,
                "authority_profile_path": None,
                "committed_revision": None,
                "rejection_reasons": ("missing_architect_determination_path",),
            },
        )(),
    ):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_ARCHITECT_FIX_PROMOTION_RUNTIME": "1",
                "REDDOG_ARCHITECT_FIX_PROMOTION_ENFORCED": "1",
            },
            clear=True,
        ):
            assert main.run_reddog_architect_fix_promotion_preflight(REPO_ROOT) is False


def test_module_has_no_execution_network_or_reindex_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "holo_index",
        "git",
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}
    banned_attrs = {
        "system",
        "popen",
        "spawn",
        "run",
        "Popen",
        "check_call",
        "check_output",
        "replace",
        "unlink",
        "remove",
        "rmdir",
        "rename",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in banned_import_roots
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    assert not (
                        node.func.value.id in banned_import_roots
                        and node.func.attr in banned_attrs
                    )
