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
    return {
        "work_state": _write_json(tmp_path, "authoritative_work_state.json", _work_state()),
        "determination": _write_json(tmp_path, "architect_determination.json", _determination()),
        "model_selection": _write_json(tmp_path, "model_selection.json", _model_selection()),
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
                                "REDDOG_AUTHORITY_PROFILE_SEED_PATH": str(tmp_path / "seed.json"),
                                "REDDOG_GITHUB_REPO_FULL_NAME": "FOUNDUPS/Foundups-Agent",
                                "REDDOG_AUTHORITY_FOUNDUP_ID": "paccess_001",
                                "REDDOG_PRINCIPAL_PUBLIC_KEY": "pub:principal",
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
    authority_supply.assert_called_once()
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
