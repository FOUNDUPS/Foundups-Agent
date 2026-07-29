"""Authenticated control adapter for one read-only resident RedDog cycle."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    observe_repo_state,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_resident_client import (
    StartOperationsResidentArchitectClient,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_control_binding import (
    CONTROL_SCHEMA,
    validated_request,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_control_actions import (
    control_existing,
    submit,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_control_authority import (
    StartOperationsRejected,
    authorized_scope,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_control_receipt import (
    PROGRESS_SCHEMA,
    RESULT_SCHEMA,
    StartOperationsControlResult,
    reject,
    result_json,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_profile import (
    StartOperationsProfile,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_holo_repair import (
    repair_start_operations_holoindex,
)
from modules.communication.moltbot_bridge.src.reddog_transport_neutral_grounding_service import (
    ground_transport_work_focus,
)


CONTROL_ACTIONS = frozenset({"submit", "status", "cancel", "resume"})
ProgressWriter = Callable[[Mapping[str, Any]], None]


def run_start_operations_control(
    *,
    repo_root: Path | str, operations_skill_root: Path | str | None = None,
    request: Mapping[str, Any], environ: Mapping[str, str] | None = None,
    operations_skill_reader: Callable[[Path], str] | None = None,
    client_factory: Callable[..., Any] = StartOperationsResidentArchitectClient,
    grounding_runner: Callable[..., Any] = ground_transport_work_focus,
    holo_repair_runner: Callable[..., Any] = repair_start_operations_holoindex,
    progress_writer: ProgressWriter | None = None,
) -> StartOperationsControlResult:
    env = environ if environ is not None else os.environ
    root = Path(repo_root).resolve()
    skill_root = Path(operations_skill_root or root).resolve()
    if operations_skill_root is not None and not callable(operations_skill_reader):
        return reject(
            "invalid", StartOperationsProfile(), {},
            ("start_operations_skill_reader_missing",),
        )
    profile, action, control_request_id = _initial_request_fields(request)
    intent_id = ""
    try:
        repo_state = observe_repo_state(root)
    except (OSError, RuntimeError, ValueError):
        return reject(
            action, profile, {}, ("start_operations_repository_observation_failed",),
            control_request_id=control_request_id,
        )
    try:
        action, profile, intent_id, control_request_id = validated_request(
            request, CONTROL_ACTIONS
        )
        scope = authorized_scope(env)
    except StartOperationsRejected as exc:
        return reject(
            action, profile, repo_state, exc.reasons, intent_id=intent_id,
            control_request_id=control_request_id,
        )
    return _dispatch(
        root=root, skill_root=skill_root,
        skill_reader=operations_skill_reader,
        action=action, profile=profile,
        intent_id=intent_id, control_request_id=control_request_id,
        scope=scope,
        repo_state=repo_state,
        env=env,
        client_factory=client_factory,
        grounding_runner=grounding_runner,
        holo_repair_runner=holo_repair_runner,
        progress_writer=progress_writer,
    )


def _initial_request_fields(
    request: Mapping[str, Any],
) -> tuple[StartOperationsProfile, str, str]:
    action = str(request.get("action") or "").strip()
    return (
        StartOperationsProfile(),
        action if action in CONTROL_ACTIONS else "invalid",
        str(request.get("control_request_id") or "").strip(),
    )


def _dispatch(
    *,
    root: Path,
    skill_root: Path,
    skill_reader: Callable[[Path], str] | None,
    action: str,
    profile: Any,
    intent_id: str,
    control_request_id: str,
    scope: tuple[str, tuple[str, ...], str],
    repo_state: Mapping[str, Any],
    env: Mapping[str, str],
    client_factory: Callable[..., Any],
    grounding_runner: Callable[..., Any],
    holo_repair_runner: Callable[..., Any],
    progress_writer: ProgressWriter | None,
) -> StartOperationsControlResult:
    if action == "submit":
        return submit(
            root=root,
            skill_root=skill_root,
            skill_reader=skill_reader,
            profile=profile,
            scope=scope,
            repo_state=repo_state,
            env=env,
            client_factory=client_factory,
            grounding_runner=grounding_runner,
            holo_repair_runner=holo_repair_runner,
            progress_writer=progress_writer,
            control_request_id=control_request_id,
        )
    return control_existing(
        root=root,
        skill_root=skill_root,
        skill_reader=skill_reader,
        profile=profile,
        scope=scope,
        repo_state=repo_state,
        env=env,
        action=action,
        intent_id=intent_id,
        client_factory=client_factory,
        control_request_id=control_request_id,
    )

__all__ = [
    "CONTROL_ACTIONS",
    "CONTROL_SCHEMA",
    "PROGRESS_SCHEMA",
    "RESULT_SCHEMA",
    "StartOperationsControlResult",
    "result_json",
    "run_start_operations_control",
]
