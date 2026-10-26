"""Governed runtime-state reads for the signed-worker queue runner."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    plan_reddog_resident_queue_orchestration,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)


def read_current_queue_plan(
    *,
    work_state_path: Path | str,
    chain_results_path: Path | str,
    allowed_root: Path | str,
    queue_item_id: str,
    now_iso: str | None,
) -> Mapping[str, Any]:
    """Read current state and return its deterministic queue plan."""

    try:
        work_state = _read_mapping(
            Path(work_state_path), allowed_root=allowed_root
        )
        chain = _read_mapping(
            Path(chain_results_path), allowed_root=allowed_root
        )
        if not work_state:
            return {}
        plan = plan_reddog_resident_queue_orchestration(
            work_state,
            chain_results=_stage_results(chain),
            requested_queue_item_id=queue_item_id,
            now_iso=now_iso,
        )
    except Exception:
        return {}
    return plan.to_dict()


def read_assurance_completion_request(
    *,
    chain_results_path: Path | str,
    allowed_root: Path | str,
) -> Mapping[str, Any]:
    """Read the verifier request that the DB finalizer will reauthenticate."""

    try:
        chain = _read_mapping(
            Path(chain_results_path), allowed_root=allowed_root
        )
    except Exception:
        return {}
    verifier = _stage_results(chain).get("slice_verifier")
    verifier = dict(verifier) if isinstance(verifier, Mapping) else {}
    request = verifier.get("assurance_completion_request")
    return dict(request) if isinstance(request, Mapping) else {}


def _read_mapping(
    path: Path,
    *,
    allowed_root: Path | str,
) -> Mapping[str, Any]:
    with runtime_operation_lock(str(path) + ".operation"):
        return read_reddog_runtime_json_mapping(path, allowed_root=allowed_root)


def _stage_results(
    state: Mapping[str, Any],
) -> Mapping[str, Mapping[str, Any]]:
    raw = (
        state.get("stage_results")
        if state.get("schema_version")
        == "reddog_resident_queue_chain_results.v1"
        else state
    )
    if not isinstance(raw, Mapping):
        return {}
    return {
        str(key): value
        for key, value in raw.items()
        if isinstance(value, Mapping)
    }


__all__ = [
    "read_assurance_completion_request",
    "read_current_queue_plan",
]
