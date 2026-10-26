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
from modules.communication.moltbot_bridge.src.reddog_start_operations_holo_repair import (
    repairable_grounding_failure,
)


def submit(
    *,
    root: Path, skill_root: Path,
    skill_reader: Callable[[Path], str] | None,
    profile: Any,
    scope: tuple[str, tuple[str, ...], str],
    repo_state: Mapping[str, Any],
    env: Mapping[str, str],
    client_factory: Callable[..., Any], grounding_runner: Callable[..., Any],
    holo_repair_runner: Callable[..., Any],
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
    prepared, repair, rejection = _prepare_with_holo_repair(
        root=root,
        skill_root=skill_root,
        skill_reader=skill_reader,
        profile=profile,
        scope=scope,
        repo_state=repo_state,
        env=env,
        grounding_runner=grounding_runner,
        holo_repair_runner=holo_repair_runner,
        control_request_id=control_request_id,
    )
    if prepared is None:
        return reject(
            "submit", profile, repo_state, rejection,
            control_request_id=control_request_id, holo_repair=repair,
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
        holo_repair=repair,
    )


def _prepare_with_holo_repair(
    *,
    root: Path,
    skill_root: Path,
    skill_reader: Callable[[Path], str] | None,
    profile: Any,
    scope: tuple[str, tuple[str, ...], str],
    repo_state: Mapping[str, Any],
    env: Mapping[str, str],
    grounding_runner: Callable[..., Any],
    holo_repair_runner: Callable[..., Any],
    control_request_id: str,
) -> tuple[Any | None, Any | None, tuple[str, ...]]:
    try:
        return (
            prepare_submission(
                repo_root=root, profile=profile, scope=scope,
                repo_state=repo_state, env=env,
                operations_skill_root=skill_root,
                operations_skill_reader=skill_reader,
                grounding_runner=grounding_runner,
            ),
            None,
            (),
        )
    except StartOperationsRejected as exc:
        if not repairable_grounding_failure(exc.reasons):
            return None, None, exc.reasons
        repair = holo_repair_runner(
            repo_root=root,
            repo_head_sha=str(repo_state.get("head_sha") or ""),
            control_request_id=control_request_id,
            environ=env,
        )
        if not repair.accepted:
            return None, repair, (*exc.reasons, *repair.rejection_reasons)
    try:
        prepared = prepare_submission(
            repo_root=root, profile=profile, scope=scope,
            repo_state=repo_state, env=env,
            operations_skill_root=skill_root,
            operations_skill_reader=skill_reader,
            grounding_runner=grounding_runner,
        )
    except StartOperationsRejected as exc:
        return None, repair, exc.reasons
    return prepared, repair, ()


def control_existing(
    *,
    root: Path,
    skill_root: Path,
    skill_reader: Callable[[Path], str] | None,
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
            runtime_defaults_for_resume(
                root, skill_root, skill_reader, profile, env
            )
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
