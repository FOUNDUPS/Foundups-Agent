"""Bounded submit and existing-cycle actions for start operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_start_operations_control_binding import (
    prepare_submission,
    runtime_defaults_for_resume,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_control_authority import (
    StartOperationsRejected,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_control_receipt import (
    StartOperationsControlResult,
    from_client,
    reject,
    write_progress,
)


def submit(
    *,
    root: Path,
    profile: Any,
    scope: tuple[str, tuple[str, ...], str],
    repo_state: Mapping[str, Any],
    env: Mapping[str, str],
    client_factory: Callable[..., Any],
    grounding_runner: Callable[..., Any],
    progress_writer: Callable[[Mapping[str, Any]], None] | None,
    control_request_id: str,
) -> StartOperationsControlResult:
    if tuple(repo_state.get("dirty_paths") or ()):
        return reject(
            "submit",
            profile,
            repo_state,
            ("start_operations_repo_dirty",),
            control_request_id=control_request_id,
        )
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
        return reject(
            "submit",
            profile,
            repo_state,
            exc.reasons,
            control_request_id=control_request_id,
        )
    write_progress(
        progress_writer, prepared.intent, repo_state, "submit", control_request_id
    )
    client = _client(root, scope, client_factory, prepared.runtime_defaults)
    return from_client(
        "submit",
        profile,
        repo_state,
        client.submit(prepared.intent),
        control_request_id,
    )


def control_existing(
    *,
    root: Path,
    profile: Any,
    scope: tuple[str, tuple[str, ...], str],
    repo_state: Mapping[str, Any],
    env: Mapping[str, str],
    action: str,
    intent_id: str,
    client_factory: Callable[..., Any],
    control_request_id: str,
) -> StartOperationsControlResult:
    try:
        defaults = (
            runtime_defaults_for_resume(root, profile, env)
            if action == "resume"
            else {}
        )
    except StartOperationsRejected as exc:
        return reject(
            action,
            profile,
            repo_state,
            exc.reasons,
            intent_id=intent_id,
            control_request_id=control_request_id,
        )
    client = _client(root, scope, client_factory, defaults)
    return from_client(
        action,
        profile,
        repo_state,
        getattr(client, action)(intent_id),
        control_request_id,
    )


def _client(
    root: Path,
    scope: tuple[str, tuple[str, ...], str],
    client_factory: Callable[..., Any],
    runtime_defaults: Mapping[str, Any],
) -> Any:
    return client_factory(
        repo_root=root,
        authenticated_principal_id=scope[0],
        authorized_foundup_ids=scope[1],
        transport="editor",
        runtime_defaults=runtime_defaults,
    )


__all__ = ["control_existing", "submit"]
