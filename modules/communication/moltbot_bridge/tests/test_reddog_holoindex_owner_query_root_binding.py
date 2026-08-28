"""Workspace/authority root separation for verified Holo owner requery."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from holo_index.authority_worktree import HoloIndexAuthoritySelection
from modules.communication.moltbot_bridge.src import (
    holoindex_postmerge_runtime_controller as controller,
)
from modules.communication.moltbot_bridge.src import (
    reddog_holoindex_blocked_request_recovery as blocked_recovery,
)
from modules.communication.moltbot_bridge.src import (
    reddog_holoindex_incident_repair_runtime as incident_repair,
)
from modules.communication.moltbot_bridge.src import (
    reddog_holoindex_owner_result_verification as verification,
)


HEAD = "a" * 40
ROOT_DIGEST = "sha256:" + ("b" * 64)
GENERATION = "sha256:" + ("c" * 64)
FRESHNESS = "sha256:" + ("d" * 64)
QUERY = "workspace authority separation"


def _selection(workspace: Path, authority: Path) -> HoloIndexAuthoritySelection:
    return HoloIndexAuthoritySelection(
        True, authority, HEAD, HEAD, ROOT_DIGEST, False, "configured"
    )


def test_classifier_queries_original_workspace_not_selected_authority(
    monkeypatch, tmp_path: Path,
) -> None:
    workspace = tmp_path / "control"
    authority = tmp_path / "authority"
    workspace.mkdir()
    authority.mkdir()
    observed: list[Path] = []
    monkeypatch.setattr(
        verification, "classify_verified_owner_result",
        lambda *_args, **_kwargs: verification.CURRENT,
    )

    def query_runner(_payload: Mapping[str, Any], *, repo_root: Path):
        observed.append(repo_root)
        return {"ok": True}

    status, _ = verification.query_and_classify_owner_result(
        query=QUERY,
        selection=_selection(workspace, authority),
        workspace_repo_root=workspace,
        query_runner=query_runner,
    )

    assert status == verification.CURRENT
    assert observed == [workspace.resolve(strict=False)]
    assert observed[0] != authority.resolve(strict=False)


def test_postcompletion_proof_passes_control_root_to_classifier(
    monkeypatch, tmp_path: Path,
) -> None:
    workspace = tmp_path / "control"
    authority = tmp_path / "authority"
    workspace.mkdir()
    authority.mkdir()
    observed: list[Path] = []

    def classify(*, workspace_repo_root: Path, query_runner, **_kwargs):
        observed.append(workspace_repo_root)
        cycle = query_runner.keywords["acquisition_cycle"]
        return controller.CURRENT, {
            "freshness_generation_id": GENERATION,
            "freshness_receipt_digest": FRESHNESS,
            "owner_acquisition_cycle": cycle,
        }

    monkeypatch.setattr(controller, "query_and_classify_owner_result", classify)
    owner, reason = controller._prove_completion_owner(
        query=QUERY,
        root=workspace,
        completion={
            "generation_id": GENERATION,
            "freshness_receipt_digest": FRESHNESS,
        },
        deadline=10.0,
        clock=lambda: 0.0,
        query_runner=lambda *_args, **_kwargs: {},
        select_authority=lambda _root: _selection(workspace, authority),
    )

    assert reason == ""
    assert owner is not None
    assert observed == [workspace]


def _current_classifier(observed: list[Path]):
    def classify(*, workspace_repo_root: Path, **_kwargs):
        observed.append(workspace_repo_root)
        return verification.CURRENT, {
            "freshness_generation_id": GENERATION,
            "freshness_receipt_digest": FRESHNESS,
        }

    return classify


def test_blocked_recovery_proof_passes_workspace_root(
    monkeypatch, tmp_path: Path,
) -> None:
    workspace, authority = tmp_path / "control", tmp_path / "authority"
    observed: list[Path] = []
    monkeypatch.setattr(
        blocked_recovery, "query_and_classify_owner_result",
        _current_classifier(observed),
    )

    matched, _owner = blocked_recovery._owner_matches_completion(
        query=QUERY, workspace_repo_root=workspace,
        selection=_selection(workspace, authority),
        completion={"generation_id": GENERATION,
                    "freshness_receipt_digest": FRESHNESS},
        query_runner=lambda *_args, **_kwargs: {},
    )

    assert matched is True
    assert observed == [workspace]


def test_incident_recheck_passes_workspace_root(
    monkeypatch, tmp_path: Path,
) -> None:
    workspace, authority = tmp_path / "control", tmp_path / "authority"
    observed: list[Path] = []
    monkeypatch.setattr(
        incident_repair, "query_and_classify_owner_result",
        _current_classifier(observed),
    )

    receipt = incident_repair._incident_recheck(
        query=QUERY, workspace_repo_root=workspace,
        selection=_selection(workspace, authority),
        query_runner=lambda *_args, **_kwargs: {}, incident_id=ROOT_DIGEST,
    )

    assert receipt is not None and receipt.status == "OWNER_READY"
    assert observed == [workspace]


def test_current_coordination_proof_passes_workspace_root(
    monkeypatch, tmp_path: Path,
) -> None:
    workspace, authority = tmp_path / "control", tmp_path / "authority"
    observed: list[Path] = []
    monkeypatch.setattr(
        incident_repair, "query_and_classify_owner_result",
        _current_classifier(observed),
    )
    coordinated = {
        "accepted": True, "status": "CURRENT", "task_id": "",
        "target_repo_head_sha": HEAD, "authority_root_digest": ROOT_DIGEST,
        "rejection_reasons": (),
    }

    receipt = incident_repair._coordination_receipt(
        coordinated=coordinated, incident_id=ROOT_DIGEST, query=QUERY,
        workspace_repo_root=workspace,
        selection=_selection(workspace, authority), expected_target_head=HEAD,
        binding={}, query_runner=lambda *_args, **_kwargs: {},
    )

    assert receipt.accepted is True and receipt.status == "OWNER_READY"
    assert observed == [workspace]
