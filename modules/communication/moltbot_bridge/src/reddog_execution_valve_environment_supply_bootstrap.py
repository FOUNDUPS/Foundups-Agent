"""Filesystem bootstrap for canonical execution-valve environment supply."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_execution_valve_environment_supply import (
    ExecutionValveEnvironmentSupplyResult,
    run_reddog_execution_valve_environment_supply,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)


def run_reddog_execution_valve_environment_supply_bootstrap(
    *,
    repo_root: Path | str,
    work_state_path: Path | str,
    authority_profile_path: Path | str,
    permission_snapshots_path: Path | str,
    principal_authority_records_path: Path | str,
    output_path: Path | str,
    requested_valve_state: str,
    queue_item_id: str = "",
    now_epoch: int | None = None,
    permission_ttl_seconds: int = 300,
) -> ExecutionValveEnvironmentSupplyResult:
    """Read four independent governed inputs and invoke the pure supplier."""
    root = Path(repo_root).resolve()
    paths = {
        "work_state": Path(work_state_path),
        "authority_profile": Path(authority_profile_path),
        "permission_snapshots": Path(permission_snapshots_path),
        "principal_authority_records": Path(principal_authority_records_path),
        "output": Path(output_path),
    }
    reasons = _validate_paths(paths, root)
    if reasons:
        return _reject(reasons)
    inputs: dict[str, Mapping[str, Any]] = {}
    for name in ("work_state", "authority_profile", "permission_snapshots", "principal_authority_records"):
        payload = _read_mapping(paths[name])
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
    )


def _validate_paths(paths: Mapping[str, Path], repo_root: Path) -> list[str]:
    reasons: list[str] = []
    resolved: dict[str, Path] = {}
    for name, path in paths.items():
        if not path.is_absolute():
            reasons.append(f"{name}_path_not_absolute")
            continue
        if path.is_symlink():
            reasons.append(f"{name}_path_symlink")
            continue
        candidate = path.resolve()
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


def _read_mapping(path: Path) -> Mapping[str, Any]:
    try:
        if path.stat().st_size > 8 * 1024 * 1024:
            return {}
        payload = read_reddog_runtime_json_mapping(path, allowed_root=path.parent)
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
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
