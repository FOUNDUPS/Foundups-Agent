"""Filesystem bootstrap for canonical execution-valve environment supply."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)

from modules.communication.moltbot_bridge.src.reddog_execution_valve_environment_supply import (
    ExecutionValveEnvironmentSupplyResult,
    run_reddog_execution_valve_environment_supply,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)
from modules.communication.moltbot_bridge.src.reddog_progressive_execution_stage_policy import (
    STAGE_AUDIT,
)


def run_reddog_execution_valve_environment_supply_bootstrap(
    *,
    repo_root: Path | str,
    runtime_allowed_root: Path | str,
    work_state_path: Path | str,
    authority_profile_path: Path | str,
    permission_snapshots_path: Path | str,
    principal_authority_records_path: Path | str,
    output_path: Path | str,
    requested_valve_state: str,
    queue_item_id: str = "",
    now_epoch: int | None = None,
    permission_ttl_seconds: int = 300,
    progressive_execution_stage_ceiling: str = STAGE_AUDIT,
) -> ExecutionValveEnvironmentSupplyResult:
    """Read four independent governed inputs and invoke the pure supplier."""
    root = Path(repo_root).resolve()
    runtime_root = Path(os.path.abspath(Path(runtime_allowed_root).expanduser()))
    try:
        validate_runtime_root_path(runtime_root, repo_root=root)
    except ValueError:
        return _reject(["invalid_runtime_artifact_root"])
    paths = {
        "work_state": Path(work_state_path),
        "authority_profile": Path(authority_profile_path),
        "permission_snapshots": Path(permission_snapshots_path),
        "principal_authority_records": Path(principal_authority_records_path),
        "output": Path(output_path),
    }
    reasons = _validate_paths(paths, root, runtime_root)
    if reasons:
        return _reject(reasons)
    inputs: dict[str, Mapping[str, Any]] = {}
    for name in ("work_state", "authority_profile", "permission_snapshots", "principal_authority_records"):
        payload = _read_mapping(paths[name], runtime_root)
        if not payload:
            reasons.append(f"{name}_missing_or_malformed")
        inputs[name] = payload
    if reasons:
        return _reject(reasons)
    return run_reddog_execution_valve_environment_supply(
        repo_root=root,
        work_state=inputs["work_state"],
        authority_profile=inputs["authority_profile"],
        permission_snapshots=inputs["permission_snapshots"],
        principal_authority_records=inputs["principal_authority_records"],
        output_path=paths["output"],
        requested_valve_state=requested_valve_state,
        queue_item_id=queue_item_id,
        now_epoch=now_epoch,
        permission_ttl_seconds=permission_ttl_seconds,
        progressive_execution_stage_ceiling=progressive_execution_stage_ceiling,
    )


def _validate_paths(
    paths: Mapping[str, Path], repo_root: Path, allowed_root: Path
) -> list[str]:
    reasons: list[str] = []
    resolved: dict[str, Path] = {}
    for name, path in paths.items():
        if not path.is_absolute():
            reasons.append(f"{name}_path_not_absolute")
            continue
        try:
            candidate = validate_runtime_artifact_path(
                path, repo_root=repo_root, allowed_root=allowed_root
            )
        except ValueError:
            reasons.append(f"{name}_path_outside_runtime_root_or_linked")
            continue
        resolved[name] = candidate
        if candidate == repo_root or repo_root in candidate.parents:
            reasons.append(f"{name}_path_inside_repo")
    if len(set(resolved.values())) != len(resolved):
        reasons.append("execution_valve_environment_path_collision")
    for name in ("work_state", "authority_profile", "permission_snapshots", "principal_authority_records"):
        path = resolved.get(name)
        if path is not None and not path.is_file():
            reasons.append(f"{name}_path_missing")
    output = resolved.get("output")
    if output is not None and output.exists() and not output.is_file():
        reasons.append("output_path_invalid")
    return list(dict.fromkeys(reasons))


def _read_mapping(path: Path, allowed_root: Path) -> Mapping[str, Any]:
    try:
        payload = read_reddog_runtime_json_mapping(path, allowed_root=allowed_root)
    except (OSError, ValueError, UnicodeError):
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _reject(reasons: list[str]) -> ExecutionValveEnvironmentSupplyResult:
    return ExecutionValveEnvironmentSupplyResult(
        accepted=False,
        status="EXECUTION_VALVE_ENVIRONMENT_SUPPLY_REJECT",
        output_path=None,
        environment_digest=None,
        supply_receipt_id=None,
        rejection_reasons=tuple(dict.fromkeys(reasons)),
    )


__all__ = ["run_reddog_execution_valve_environment_supply_bootstrap"]
