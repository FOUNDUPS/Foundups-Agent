"""Authenticated control adapter for one read-only resident RedDog cycle."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    observe_repo_state,
)
from modules.communication.moltbot_bridge.src.reddog_resident_architect_client import (
    RedDogResidentArchitectClient,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_control_binding import (
    CONTROL_SCHEMA,
    prepare_submission,
    runtime_defaults_for_resume,
    validated_request,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_control_authority import (
    StartOperationsRejected,
    authorized_scope,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_control_receipt import (
    PROGRESS_SCHEMA,
    RESULT_SCHEMA,
    StartOperationsControlResult,
    from_client,
    reject,
    result_json,
    write_progress,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_profile import (
    StartOperationsProfile,
)
from modules.communication.moltbot_bridge.src.reddog_transport_neutral_grounding_service import (
    ground_transport_work_focus,
)


CONTROL_ACTIONS = frozenset({"submit", "status", "cancel", "resume"})
ProgressWriter = Callable[[Mapping[str, Any]], None]


def run_start_operations_control(
    *,
    repo_root: Path | str,
    request: Mapping[str, Any],
    environ: Mapping[str, str] | None = None,
    client_factory: Callable[..., Any] = RedDogResidentArchitectClient,
    grounding_runner: Callable[..., Any] = ground_transport_work_focus,
    progress_writer: ProgressWriter | None = None,
) -> StartOperationsControlResult:
    env = environ if environ is not None else os.environ
    root = Path(repo_root).resolve()
    profile = StartOperationsProfile()
    raw_action = str(request.get("action") or "").strip()
    action = raw_action if raw_action in CONTROL_ACTIONS else "invalid"
    repo_state: Mapping[str, Any] = {}
    try:
        repo_state = observe_repo_state(root)
        action, profile, intent_id = validated_request(request, CONTROL_ACTIONS)
        scope = authorized_scope(env)
    except StartOperationsRejected as exc:
        return reject(action, profile, repo_state, exc.reasons)
    except (OSError, RuntimeError, ValueError):
        return reject(
            action,
            profile,
            repo_state,
            ("start_operations_repository_observation_failed",),
        )
    if action == "submit":
        return _submit(
            root=root,
            profile=profile,
            scope=scope,
            repo_state=repo_state,
            env=env,
            client_factory=client_factory,
            grounding_runner=grounding_runner,
            progress_writer=progress_writer,
        )
    return _control_existing(
        root=root,
        profile=profile,
        scope=scope,
        repo_state=repo_state,
        env=env,
        action=action,
        intent_id=intent_id,
        client_factory=client_factory,
    )


def _submit(
    *,
    root: Path,
    profile: Any,
    scope: tuple[str, tuple[str, ...], str],
    repo_state: Mapping[str, Any],
    env: Mapping[str, str],
    client_factory: Callable[..., Any],
    grounding_runner: Callable[..., Any],
    progress_writer: ProgressWriter | None,
) -> StartOperationsControlResult:
    if tuple(repo_state.get("dirty_paths") or ()):
        return reject("submit", profile, repo_state, ("start_operations_repo_dirty",))
    try:
        prepared = prepare_submission(
            repo_root=root,
            profile=profile,
            scope=scope,
            repo_state=repo_state,
            env=env,
            grounding_runner=grounding_runner,
        )
    except StartOperationsRejected as exc:
        return reject("submit", profile, repo_state, exc.reasons)
    write_progress(progress_writer, prepared.intent, repo_state)
    client = client_factory(
        repo_root=root,
        authenticated_principal_id=scope[0],
        authorized_foundup_ids=scope[1],
        transport="editor",
        runtime_defaults=prepared.runtime_defaults,
    )
    return from_client("submit", profile, repo_state, client.submit(prepared.intent))


def _control_existing(
    *,
    root: Path,
    profile: Any,
    scope: tuple[str, tuple[str, ...], str],
    repo_state: Mapping[str, Any],
    env: Mapping[str, str],
    action: str,
    intent_id: str,
    client_factory: Callable[..., Any],
) -> StartOperationsControlResult:
    try:
        defaults = (
            runtime_defaults_for_resume(root, profile, env)
            if action == "resume"
            else {}
        )
    except StartOperationsRejected as exc:
        return reject(action, profile, repo_state, exc.reasons, intent_id=intent_id)
    client = client_factory(
        repo_root=root,
        authenticated_principal_id=scope[0],
        authorized_foundup_ids=scope[1],
        transport="editor",
        runtime_defaults=defaults,
    )
    return from_client(action, profile, repo_state, getattr(client, action)(intent_id))


__all__ = [
    "CONTROL_ACTIONS",
    "CONTROL_SCHEMA",
    "PROGRESS_SCHEMA",
    "RESULT_SCHEMA",
    "StartOperationsControlResult",
    "result_json",
    "run_start_operations_control",
]
