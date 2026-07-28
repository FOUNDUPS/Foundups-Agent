"""Pure admission helpers for signed AgentDB worker claims."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence


def verify_signed_worker_agentdb_context(
    *,
    repo_root: Path | str,
    task_id: str,
    context: Mapping[str, Any],
    authority_verification_context: Any | None,
    env: Mapping[str, str],
) -> Any:
    """Return the sealed result of canonical signed-envelope verification."""

    from modules.communication.moltbot_bridge.src.reddog_signed_worker_agentdb_envelope import (
        build_worker_dispatch_authority_context_from_env,
        verify_reddog_signed_worker_agentdb_envelope,
    )

    authority = authority_verification_context
    if authority is None:
        authority = build_worker_dispatch_authority_context_from_env(
            repo_root=Path(repo_root),
            env=env,
        )
    return verify_reddog_signed_worker_agentdb_envelope(
        envelope=context.get("signed_worker_agentdb_envelope", {}),
        task_id=task_id,
        authority_context=authority,
    )


def rehydrate_signed_worker_agentdb_context(
    *,
    repo_root: Path | str,
    task_id: str,
    context: Mapping[str, Any],
    authority_verification_context: Any | None,
    env: Mapping[str, str],
) -> Mapping[str, Any]:
    """Authenticate one AgentDB envelope without performing a durable effect."""

    verified = verify_signed_worker_agentdb_context(
        repo_root=repo_root,
        task_id=task_id,
        context=context,
        authority_verification_context=authority_verification_context,
        env=env,
    )
    return verified.canonical_context


def try_rehydrate_signed_worker_agentdb_context(
    *,
    repo_root: Path | str,
    task_id: str,
    context: Mapping[str, Any],
    authority_verification_context: Any | None,
    env: Mapping[str, str],
) -> tuple[Mapping[str, Any] | None, str]:
    """Return canonical context or one bounded fail-closed reason."""

    try:
        verified = rehydrate_signed_worker_agentdb_context(
            repo_root=repo_root,
            task_id=task_id,
            context=context,
            authority_verification_context=authority_verification_context,
            env=env,
        )
    except (TypeError, ValueError) as exc:
        return None, str(exc)[:160]
    return verified, ""


def quarantine_unverified_signed_worker_assignment(
    *,
    db: Any,
    task_id: str,
    reason: str,
) -> str:
    """Atomically isolate an assigned task rejected by canonical verification."""

    from modules.infrastructure.database.src.signed_worker_execution_quarantine import (
        quarantine_signed_worker_execution_in_transaction,
    )

    try:
        with db.db.get_connection() as connection:
            row = connection.execute(
                "SELECT status, context FROM agents_autonomous_tasks "
                "WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if row is None or dict(row).get("status") != "assigned":
                return "REJECTED"
            return quarantine_signed_worker_execution_in_transaction(
                connection,
                task_id=task_id,
                raw_context=dict(row).get("context"),
                expected_status="assigned",
                reason=reason,
                now_iso=datetime.now(timezone.utc).isoformat(),
            )
    except Exception:
        return "REJECTED"


def exclude_signed_worker_origin(
    tasks: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """Keep signed-origin rows out of every generic executor path."""

    from modules.communication.moltbot_bridge.src.reddog_signed_worker_agentdb_envelope import (
        SIGNED_WORKER_DISPATCH_TASK_SOURCE,
    )

    return [
        task
        for task in tasks
        if str(task.get("discovered_by") or "")
        != SIGNED_WORKER_DISPATCH_TASK_SOURCE
    ]


def renew_expired_verified_assurance(
    *,
    db: Any,
    source: str,
    env: Mapping[str, str],
    repo_root: Path | str | None,
    authority_verification_context: Any | None,
    rehydrate: Callable[..., Mapping[str, Any]],
    is_verifier_context: Callable[[Mapping[str, Any]], bool],
    is_stage_ready: Callable[[Mapping[str, Any], Mapping[str, str], Any], bool],
) -> None:
    """Renew one lease only after authenticating its signed AgentDB envelope."""

    rows = _expired_signed_rows(db, source)
    trusted_now = _trusted_now(env)
    if trusted_now is None:
        return
    for task_id, context in rows:
        try:
            verified_context = rehydrate(
                repo_root=repo_root or Path.cwd(),
                task_id=task_id,
                context=context,
                authority_verification_context=authority_verification_context,
            )
        except (TypeError, ValueError):
            continue
        if not is_verifier_context(verified_context) or not is_stage_ready(
            verified_context,
            env,
            repo_root=repo_root,
        ):
            continue
        reservation = _expired_reservation(db, task_id)
        if reservation is None:
            continue
        from modules.communication.moltbot_bridge.src.reddog_openclaw_assurance_capacity import (
            build_assurance_renewal_request,
        )

        renewal = db.renew_independent_assurance(
            build_assurance_renewal_request(reservation, now=trusted_now)
        )
        if renewal.get("accepted") is True:
            return


def _expired_signed_rows(
    db: Any,
    source: str,
) -> list[tuple[str, Mapping[str, Any]]]:
    with db.db.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT task_id, context
            FROM agents_autonomous_tasks
            WHERE status = 'expired' AND discovered_by = ?
            ORDER BY priority_score DESC, discovered_at ASC
            LIMIT 50
            """,
            (source,),
        ).fetchall()
    parsed: list[tuple[str, Mapping[str, Any]]] = []
    for row in rows:
        task_id = str(row["task_id"] if hasattr(row, "keys") else row[0])
        raw = row["context"] if hasattr(row, "keys") else row[1]
        try:
            context = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            continue
        if isinstance(context, Mapping):
            parsed.append((task_id, context))
    return parsed


def _expired_reservation(
    db: Any,
    task_id: str,
) -> Optional[Mapping[str, Any]]:
    durable = db.get_independent_assurance_reservation_for_task(
        task_id,
        task_kind="verifier",
    )
    reservation = (
        durable.get("reservation")
        if isinstance(durable, Mapping)
        else None
    )
    if (
        not isinstance(reservation, Mapping)
        or str(reservation.get("status") or "") != "EXPIRED"
    ):
        return None
    return reservation


def _trusted_now(env: Mapping[str, str]) -> Optional[datetime]:
    raw = str(env.get("REDDOG_RESIDENT_QUEUE_NOW_ISO") or "").strip()
    try:
        now = (
            datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if raw
            else datetime.now(timezone.utc)
        )
    except ValueError:
        return None
    return now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)


__all__ = [
    "exclude_signed_worker_origin",
    "quarantine_unverified_signed_worker_assignment",
    "rehydrate_signed_worker_agentdb_context",
    "renew_expired_verified_assurance",
    "try_rehydrate_signed_worker_agentdb_context",
    "verify_signed_worker_agentdb_context",
]
