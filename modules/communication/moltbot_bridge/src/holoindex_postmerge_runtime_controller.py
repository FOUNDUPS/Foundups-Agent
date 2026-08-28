"""Bounded owner for one exact-main HoloIndex post-merge transaction."""

from __future__ import annotations

import re
import subprocess
import time
from contextlib import nullcontext
from dataclasses import asdict, dataclass, replace
from functools import partial
from pathlib import Path
from typing import Any, Callable, ContextManager, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_holoindex_incident_repair_runtime import (
    coordinate_holoindex_incident_repair,
)
from modules.communication.moltbot_bridge.src.reddog_holoindex_owner_result_verification import (
    CURRENT,
    classify_verified_owner_result,
    is_verified_transient_owner_result,
    query_and_classify_owner_result,
)
from modules.communication.moltbot_bridge.src.reddog_holoindex_incident_repair_contract import (
    rehydrate_deferred_receipt,
    rehydrate_owner_ready_receipt,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_acquisition import (
    OWNER_OPERATION_TIMEOUT_SECONDS,
)

from .holoindex_postmerge_supervisor_policy import (
    HOLOINDEX_POSTMERGE_ONLY_MODE,
    HOLOINDEX_POSTMERGE_TASK_PREFIX,
    validate_supervisor_holoindex_postmerge_completion,
)
from .holoindex_postmerge_runtime_liveness import (
    holoindex_postmerge_runtime_inspection,
    preexisting_runtime_topology as _preexisting_runtime_topology,
    run_with_supervisor_binding_release,
    wait_for_supervisor_binding as _wait_for_supervisor_binding,
)


SCHEMA_VERSION = "reddog_holoindex_postmerge_runtime.v1"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_RUNTIME_LEASE_FILENAME = "reddog_holoindex_postmerge_runtime.lock"
_POSTCOMPLETION_OWNER_PROOF_ATTEMPTS = 2
_RUNTIME_STARTUP_TIMEOUT_SECONDS = 60.0
@dataclass(frozen=True)
class HoloIndexPostmergeRuntimeResult:
    accepted: bool
    status: str
    target_repo_head_sha: str = ""
    task_id: str = ""
    generation_id: str = ""
    freshness_receipt_digest: str = ""
    started_runtime_ids: tuple[str, ...] = ()
    stopped_runtime_ids: tuple[str, ...] = ()
    rejection_reasons: tuple[str, ...] = ()
    no_holoindex_reindex_performed_by_controller: bool = True

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["schema_version"] = SCHEMA_VERSION
        for field in (
            "started_runtime_ids",
            "stopped_runtime_ids",
            "rejection_reasons",
        ):
            value[field] = list(value[field])
        return value


GitRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]
def _git_runner(argv: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv), cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60, check=False, shell=False,
    )


def _git_value(
    runner: GitRunner, root: Path, *args: str, allow_empty: bool = False,
) -> tuple[str, str]:
    try:
        completed = runner(("git", *args), root)
    except BaseException:
        return "", "git_command_failed"
    value = str(completed.stdout or "").strip()
    if completed.returncode != 0 or (not value and not allow_empty):
        return "", "git_command_failed"
    return value, ""


def _exact_local_main(root: Path, runner: GitRunner) -> tuple[str, str]:
    dirty, error = _git_value(
        runner, root, "status", "--porcelain=v1", "--untracked-files=all",
        allow_empty=True,
    )
    if error or dirty:
        return "", "workspace_not_clean"
    head, error = _git_value(runner, root, "rev-parse", "HEAD")
    if error or _SHA_RE.fullmatch(head.lower()) is None:
        return "", "workspace_head_unproven"
    origin_main, error = _git_value(
        runner, root, "rev-parse", "refs/remotes/origin/main"
    )
    if error or _SHA_RE.fullmatch(origin_main.lower()) is None:
        return "", "origin_main_unproven"
    if head.lower() != origin_main.lower():
        return "", "workspace_not_exact_origin_main"
    return head.lower(), ""


def _wait_for(
    predicate: Callable[[], bool], *, deadline: float,
    clock: Callable[[], float], sleeper: Callable[[float], None], interval: float,
) -> bool:
    while clock() < deadline:
        if predicate():
            return True
        sleeper(interval)
    return predicate()


def _runtime_ready(status: Mapping[str, Any]) -> bool:
    return bool(
        status.get("registered") is True
        and status.get("running") is True
        and status.get("thread_alive") is True
        and status.get("state") in {"starting", "running", "degraded"}
        and not status.get("last_error")
    )


def _wait_runtime_ready(
    broker: Any, runtime_id: str, *, deadline: float,
    clock: Callable[[], float], sleeper: Callable[[float], None], interval: float,
) -> bool:
    consecutive = 0

    while clock() < deadline:
        status = broker.get_runtime_status(runtime_id)
        consecutive = consecutive + 1 if _runtime_ready(status) else 0
        if consecutive >= 2:
            return True
        if (
            status.get("last_error")
            or status.get("registered") is not True
            or status.get("state") in {"crashed", "failed"}
        ):
            return False
        sleeper(interval)
    return False


def _start_runtime(
    broker: Any, runtime_id: str, *, deadline: float,
    clock: Callable[[], float], sleeper: Callable[[float], None], interval: float,
    launch_kwargs: Mapping[str, Any] | None = None,
) -> tuple[bool, bool, str]:
    ready_deadline = min(deadline, clock() + _RUNTIME_STARTUP_TIMEOUT_SECONDS)
    status = broker.get_runtime_status(runtime_id)
    if status.get("thread_alive") is True or status.get("running") is True:
        ready = _wait_runtime_ready(
            broker, runtime_id, deadline=ready_deadline, clock=clock,
            sleeper=sleeper, interval=interval,
        )
        reason = "" if ready else f"{runtime_id}_preexisting_not_stable"
        return ready, False, reason
    if launch_kwargs is None:
        started = broker.start_dae(runtime_id, actor_id="0102")
    else:
        started = broker.start_dae(
            runtime_id, actor_id="0102", launch_kwargs=dict(launch_kwargs)
        )
    if started.get("success") is not True:
        return False, False, f"{runtime_id}_start_failed"
    owned = started.get("status") != "already_running"
    ready = _wait_runtime_ready(
        broker, runtime_id, deadline=ready_deadline, clock=clock,
        sleeper=sleeper, interval=interval,
    )
    return ready, owned, "" if ready else f"{runtime_id}_start_timeout"


def _stop_owned(
    broker: Any, owned: Sequence[str], *, deadline: float,
    clock: Callable[[], float], sleeper: Callable[[float], None], interval: float,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    stopped: list[str] = []
    errors: list[str] = []
    for runtime_id in reversed(tuple(owned)):
        try:
            requested = broker.stop_dae(runtime_id, actor_id="0102")
            if requested.get("success") is not True:
                errors.append(f"{runtime_id}_stop_failed")
                continue
            dead = _wait_for(
                lambda: broker.get_runtime_status(runtime_id).get("thread_alive") is False,
                deadline=deadline, clock=clock, sleeper=sleeper, interval=interval,
            )
            if dead:
                stopped.append(runtime_id)
            else:
                errors.append(f"{runtime_id}_stop_timeout")
        except BaseException:
            errors.append(f"{runtime_id}_stop_exception")
    return tuple(stopped), tuple(errors)


def _owner_matches_completion(
    owner: Mapping[str, Any], completion: Mapping[str, Any],
) -> bool:
    return all(
        owner.get(owner_key) == completion.get(completion_key)
        for owner_key, completion_key in (
            ("freshness_generation_id", "generation_id"),
            ("freshness_receipt_digest", "freshness_receipt_digest"),
        )
    )


def _prove_completion_owner(
    *, query: str, root: Path, completion: Mapping[str, Any], deadline: float,
    clock: Callable[[], float], query_runner: Callable[..., Mapping[str, Any]],
    select_authority: Callable[[Path], Any],
) -> tuple[Mapping[str, Any] | None, str]:
    proof_deadline = min(deadline, clock() + OWNER_OPERATION_TIMEOUT_SECONDS)
    for attempt in range(1, _POSTCOMPLETION_OWNER_PROOF_ATTEMPTS + 1):
        acquisition_cycle = attempt - 1
        remaining = proof_deadline - clock()
        if remaining <= 0:
            return None, "owner_proof_timeout_after_completion"
        selection = select_authority(root)
        if not getattr(selection, "accepted", False):
            return None, "owner_not_current_after_completion"
        remaining = proof_deadline - clock()
        if remaining <= 0:
            return None, "owner_proof_timeout_after_completion"
        status, owner = query_and_classify_owner_result(
            query=query, selection=selection,
            query_runner=partial(query_runner, acquisition_cycle=acquisition_cycle),
            operation_timeout_seconds=remaining,
        )
        if clock() >= proof_deadline:
            return None, "owner_proof_timeout_after_completion"
        verified_transient = is_verified_transient_owner_result(
            owner, query=query, selection=selection,
        )
        if status == CURRENT or verified_transient:
            if owner.get("owner_acquisition_cycle") != acquisition_cycle:
                return None, "owner_acquisition_cycle_mismatch_after_completion"
        if status == CURRENT:
            if not _owner_matches_completion(owner, completion):
                return None, "owner_completion_binding_mismatch"
            return owner, ""
        if verified_transient:
            if attempt < _POSTCOMPLETION_OWNER_PROOF_ATTEMPTS:
                continue
            return None, "owner_transient_exhausted_after_completion"
        return None, "owner_result_invalid_after_completion"
    return None, "owner_transient_exhausted_after_completion"


def _query_initial_owner(
    *, root: Path, head: str, query: str,
    query_runner: Callable[..., Mapping[str, Any]],
    select_authority: Callable[[Path], Any],
) -> tuple[Mapping[str, Any] | None, HoloIndexPostmergeRuntimeResult | None]:
    try:
        initial = query_runner({"query": query, "limit": 5}, repo_root=root)
    except BaseException:
        return None, HoloIndexPostmergeRuntimeResult(
            False, "REJECTED", head, rejection_reasons=("owner_query_failed",),
        )
    if not isinstance(initial, Mapping):
        return None, HoloIndexPostmergeRuntimeResult(
            False, "REJECTED", head, rejection_reasons=("owner_query_invalid",),
        )
    try:
        selection = select_authority(root)
        current = bool(
            getattr(selection, "accepted", False)
            and classify_verified_owner_result(
                initial, query=query, selection=selection
            ) == CURRENT
        )
    except BaseException:
        current = False
    if current:
        return None, HoloIndexPostmergeRuntimeResult(
            True, "OWNER_READY", head,
            generation_id=str(initial.get("freshness_generation_id") or ""),
            freshness_receipt_digest=str(initial.get("freshness_receipt_digest") or ""),
        )
    return initial, None


def _coordinate_repair(
    *, root: Path, head: str, query: str, initial: Mapping[str, Any],
    coordinator: Callable[..., Any],
) -> tuple[str, str, HoloIndexPostmergeRuntimeResult | None]:
    try:
        repair_value = coordinator(
            repo_root=root, query=query, owner_failure=initial
        ).to_dict()
    except BaseException:
        return "", "", HoloIndexPostmergeRuntimeResult(
            False, "REJECTED", head,
            rejection_reasons=("repair_coordination_failed",),
        )
    if not isinstance(repair_value, Mapping) or repair_value.get("accepted") is not True:
        return "", "", HoloIndexPostmergeRuntimeResult(
            False, "REJECTED", head, rejection_reasons=("repair_rejected",),
        )
    if repair_value.get("status") == "OWNER_READY":
        ready = rehydrate_owner_ready_receipt(repair_value)
        if ready is None or ready.target_repo_head_sha != head:
            return "", "", HoloIndexPostmergeRuntimeResult(
                False, "REJECTED", head,
                rejection_reasons=("owner_ready_receipt_not_exact_head",),
            )
        return "", "", HoloIndexPostmergeRuntimeResult(
            True, "OWNER_READY", head,
            generation_id=ready.generation_id,
            freshness_receipt_digest=ready.freshness_receipt_digest,
        )
    deferred = rehydrate_deferred_receipt(repair_value)
    task_id = deferred.task_id if deferred else ""
    if deferred is None or task_id != HOLOINDEX_POSTMERGE_TASK_PREFIX + head:
        return task_id, "", HoloIndexPostmergeRuntimeResult(
            False, "REJECTED", head, task_id,
            rejection_reasons=("repair_task_not_exact_head",),
        )
    return task_id, deferred.authority_root_digest, None


def _admit_or_coordinate(
    *, root: Path, query: str, git_runner: GitRunner,
    query_runner: Callable[..., Mapping[str, Any]],
    select_authority: Callable[[Path], Any], coordinator: Callable[..., Any],
    runtime_preflight: Callable[[], bool],
) -> tuple[str, str, str, HoloIndexPostmergeRuntimeResult | None]:
    head, error = _exact_local_main(root, git_runner)
    if error:
        return "", "", "", HoloIndexPostmergeRuntimeResult(
            False, "REJECTED", rejection_reasons=(error,)
        )
    initial, terminal = _query_initial_owner(
        root=root, head=head, query=query, query_runner=query_runner,
        select_authority=select_authority,
    )
    if terminal is not None or initial is None:
        return head, "", "", terminal
    try:
        dependencies_ready = runtime_preflight()
    except BaseException:
        dependencies_ready = False
    if dependencies_ready is not True:
        return head, "", "", HoloIndexPostmergeRuntimeResult(
            False, "REJECTED", head,
            rejection_reasons=("runtime_dependencies_unavailable",),
        )
    task_id, authority_root_digest, terminal = _coordinate_repair(
        root=root, head=head, query=query, initial=initial, coordinator=coordinator,
    )
    return head, task_id, authority_root_digest, terminal


def _start_required_runtimes(
    broker: Any, *, deadline: float, clock: Callable[[], float],
    sleeper: Callable[[float], None], interval: float,
    task_id: str,
    owned: list[str] | None = None,
) -> tuple[list[str], int, str]:
    owned = [] if owned is None else owned
    preexisting = 0
    for runtime_id in ("openclaw", "openclaw_supervisor"):
        launch_kwargs = (
            {
                "runtime_mode": HOLOINDEX_POSTMERGE_ONLY_MODE,
                "postmerge_task_id": task_id,
            }
            if runtime_id == "openclaw_supervisor"
            else None
        )
        ready, started, reason = _start_runtime(
            broker, runtime_id, deadline=deadline, clock=clock,
            sleeper=sleeper, interval=interval, launch_kwargs=launch_kwargs,
        )
        if started:
            owned.append(runtime_id)
        else:
            preexisting += 1
        if not ready:
            return owned, preexisting, reason
    return owned, preexisting, ""


def _wait_for_completion(
    *, database: Any, task_id: str, query: str, root: Path, deadline: float,
    clock: Callable[[], float], sleeper: Callable[[float], None], interval: float,
    query_runner: Callable[..., Mapping[str, Any]],
    select_authority: Callable[[Path], Any], git_runner: GitRunner,
    expected_head: str, expected_authority_root_digest: str,
    broker: Any,
) -> tuple[Mapping[str, Any] | None, str]:
    completion: Mapping[str, Any] | None = None
    progress_marker = ""
    progress_deadline = deadline
    while clock() < deadline:
        completion = validate_supervisor_holoindex_postmerge_completion(database, task_id)
        if completion is not None:
            break
        rejection, marker, phase_timeout = holoindex_postmerge_runtime_inspection(
            broker, database, task_id=task_id, expected_head=expected_head,
            expected_authority_root_digest=expected_authority_root_digest,
        )
        if rejection:
            return None, rejection
        if marker != progress_marker:
            progress_marker = marker
            progress_deadline = min(deadline, clock() + phase_timeout)
        elif clock() >= progress_deadline:
            return None, "postmerge_task_progress_timeout"
        sleeper(interval)
    if completion is None:
        completion = validate_supervisor_holoindex_postmerge_completion(database, task_id)
    if completion is None:
        return None, "postmerge_completion_timeout"
    owner, reason = _prove_completion_owner(
        query=query, root=root, completion=completion, deadline=deadline,
        clock=clock, query_runner=query_runner,
        select_authority=select_authority,
    )
    if reason or owner is None:
        return None, reason or "owner_not_current_after_completion"
    current_head, error = _exact_local_main(root, git_runner)
    if error or current_head != expected_head:
        return None, "workspace_changed_during_transaction"
    return owner, ""


def _perform_runtime_transaction(
    *, root: Path, head: str, task_id: str, authority_root_digest: str,
    query: str, timeout_seconds: float,
    poll_interval_seconds: float, query_runner: Callable[..., Mapping[str, Any]],
    select_authority: Callable[[Path], Any], broker: Any,
    database_provider: Callable[[], Any], clock: Callable[[], float],
    sleeper: Callable[[float], None], git_runner: GitRunner,
    owned: list[str], preexisting_allowed: bool,
    task_binder: Callable[[str, Path], str],
    task_releaser: Callable[[str, Path], str],
) -> tuple[HoloIndexPostmergeRuntimeResult, list[str]]:
    deadline = clock() + timeout_seconds
    outcome = HoloIndexPostmergeRuntimeResult(False, "REJECTED", head, task_id)
    owned, preexisting, reason = _start_required_runtimes(
        broker, deadline=deadline, clock=clock, sleeper=sleeper,
        interval=poll_interval_seconds, task_id=task_id, owned=owned,
    )
    if reason:
        return replace(outcome, rejection_reasons=(reason,)), owned
    if preexisting and not preexisting_allowed:
        return replace(
            outcome, rejection_reasons=("runtime_ownership_race",)
        ), owned
    database = database_provider()
    reason = _wait_for_supervisor_binding(
        task_binder, task_id, root, broker=broker, database=database,
        expected_head=head, expected_authority_root_digest=authority_root_digest,
        deadline=deadline, clock=clock, sleeper=sleeper,
        interval=poll_interval_seconds,
    )
    if reason:
        return replace(outcome, rejection_reasons=(reason,)), owned
    operation = partial(
        _wait_for_completion, database=database, task_id=task_id, query=query,
        root=root, deadline=deadline, clock=clock, sleeper=sleeper,
        interval=poll_interval_seconds, query_runner=query_runner,
        select_authority=select_authority, git_runner=git_runner,
        expected_head=head, expected_authority_root_digest=authority_root_digest,
        broker=broker,
    )
    owner, reason = (
        operation()
        if "openclaw_supervisor" in owned
        else run_with_supervisor_binding_release(
            operation, task_releaser, task_id, root,
        )
    )
    if reason:
        return replace(outcome, rejection_reasons=(reason,)), owned
    return HoloIndexPostmergeRuntimeResult(
        True, "COMPLETED", head, task_id,
        generation_id=str(owner.get("freshness_generation_id") or ""),
        freshness_receipt_digest=str(owner.get("freshness_receipt_digest") or ""),
    ), owned


def _finalize_runtime_outcome(
    *, outcome: HoloIndexPostmergeRuntimeResult, owned: Sequence[str],
    stopped: Sequence[str], stop_errors: Sequence[str], root: Path,
    head: str, git_runner: GitRunner,
) -> HoloIndexPostmergeRuntimeResult:
    outcome = replace(
        outcome, started_runtime_ids=tuple(owned),
        stopped_runtime_ids=tuple(stopped),
    )
    if stop_errors:
        return replace(
            outcome, accepted=False, status="REJECTED",
            rejection_reasons=outcome.rejection_reasons + tuple(stop_errors),
        )
    if not outcome.accepted:
        return outcome
    final_head, final_error = _exact_local_main(root, git_runner)
    if final_error or final_head != head:
        return replace(
            outcome, accepted=False, status="REJECTED",
            rejection_reasons=("workspace_changed_before_return",),
        )
    return outcome


def _execute_runtime_transaction(
    *, root: Path, head: str, task_id: str, authority_root_digest: str,
    query: str, timeout_seconds: float,
    poll_interval_seconds: float, query_runner: Callable[..., Mapping[str, Any]],
    select_authority: Callable[[Path], Any], bootstrap: Callable[[], None],
    broker_provider: Callable[[], Any], database_provider: Callable[[], Any],
    clock: Callable[[], float], sleeper: Callable[[float], None],
    git_runner: GitRunner,
    task_binder: Callable[[str, Path], str] = lambda _task_id, _root: "bound",
    task_releaser: Callable[[str, Path], str] = lambda _task_id, _root: "released",
) -> HoloIndexPostmergeRuntimeResult:
    outcome = HoloIndexPostmergeRuntimeResult(False, "REJECTED", head, task_id)
    broker: Any | None = None
    owned: list[str] = []
    stopped: tuple[str, ...] = ()
    stop_errors: tuple[str, ...] = ()
    try:
        bootstrap()
        broker = broker_provider()
        topology = _preexisting_runtime_topology(broker)
        if topology == "partial":
            outcome = replace(
                outcome, rejection_reasons=("preexisting_runtime_topology_partial",)
            )
        else:
            outcome, owned = _perform_runtime_transaction(
                root=root, head=head, task_id=task_id,
                authority_root_digest=authority_root_digest, query=query,
                timeout_seconds=timeout_seconds,
                poll_interval_seconds=poll_interval_seconds,
                query_runner=query_runner, select_authority=select_authority,
                broker=broker, database_provider=database_provider, clock=clock,
                sleeper=sleeper, git_runner=git_runner, owned=owned,
                preexisting_allowed=topology == "all",
                task_binder=task_binder,
                task_releaser=task_releaser,
            )
    except BaseException:
        outcome = replace(outcome, rejection_reasons=("runtime_exception",))
    finally:
        if broker is not None and owned:
            stopped, stop_errors = _stop_owned(
                broker, owned, deadline=clock() + min(timeout_seconds, 60.0),
                clock=clock, sleeper=sleeper, interval=poll_interval_seconds,
            )
    return _finalize_runtime_outcome(
        outcome=outcome, owned=owned, stopped=stopped, stop_errors=stop_errors,
        root=root, head=head, git_runner=git_runner,
    )


def _run_holoindex_postmerge_runtime_for_test(
    *, repo_root: Path, query: str, timeout_seconds: float, poll_interval_seconds: float,
    git_runner: GitRunner, query_runner: Callable[..., Mapping[str, Any]],
    select_authority: Callable[[Path], Any], coordinator: Callable[..., Any],
    bootstrap: Callable[[], None], broker_provider: Callable[[], Any],
    database_provider: Callable[[], Any], clock: Callable[[], float],
    sleeper: Callable[[float], None],
    lease_factory: Callable[[], ContextManager[Any]] = nullcontext,
    runtime_preflight: Callable[[], bool] = lambda: True,
    task_binder: Callable[[str, Path], str] = lambda _task_id, _root: "bound",
    task_releaser: Callable[[str, Path], str] = lambda _task_id, _root: "released",
) -> HoloIndexPostmergeRuntimeResult:
    root = repo_root.resolve(strict=False)
    try:
        with lease_factory():
            head, task_id, authority_root_digest, terminal = _admit_or_coordinate(
                root=root, query=query, git_runner=git_runner,
                query_runner=query_runner, select_authority=select_authority,
                coordinator=coordinator, runtime_preflight=runtime_preflight,
            )
            if terminal is not None:
                return _finalize_runtime_outcome(
                    outcome=terminal, owned=(), stopped=(), stop_errors=(),
                    root=root, head=head, git_runner=git_runner,
                )
            return _execute_runtime_transaction(
                root=root, head=head, task_id=task_id,
                authority_root_digest=authority_root_digest, query=query,
                timeout_seconds=timeout_seconds,
                poll_interval_seconds=poll_interval_seconds,
                query_runner=query_runner, select_authority=select_authority,
                bootstrap=bootstrap, broker_provider=broker_provider,
                database_provider=database_provider, clock=clock, sleeper=sleeper,
                git_runner=git_runner, task_binder=task_binder,
                task_releaser=task_releaser,
            )
    except BaseException:
        return HoloIndexPostmergeRuntimeResult(
            False, "REJECTED", rejection_reasons=("runtime_controller_unavailable",)
        )


def _production_runtime_lease() -> ContextManager[Any]:
    from holo_index.maintenance_lock import acquire_maintenance_lease
    from holo_index.storage_contract import resolve_holoindex_ssd_path

    path = (
        resolve_holoindex_ssd_path() / "indexes" / _RUNTIME_LEASE_FILENAME
    )
    return acquire_maintenance_lease(path)


def run_holoindex_postmerge_runtime_once(
    *, repo_root: Path | str, query: str, timeout_seconds: float = 14_400.0,
    poll_interval_seconds: float = 1.0,
) -> HoloIndexPostmergeRuntimeResult:
    """Run or reconcile one exact-main transaction and release owned runtimes."""

    if not isinstance(query, str) or not query.strip() or len(query) > 16_000:
        return HoloIndexPostmergeRuntimeResult(
            False, "REJECTED", rejection_reasons=("query_invalid",)
        )
    if not (30.0 <= timeout_seconds <= 21_600.0) or not (
        0.05 <= poll_interval_seconds <= 10.0
    ):
        return HoloIndexPostmergeRuntimeResult(
            False, "REJECTED", rejection_reasons=("runtime_limits_invalid",)
        )
    from holo_index.authority_worktree import resolve_holoindex_authority_root
    from modules.communication.moltbot_bridge.scripts.launch import (
        _ensure_broker_bootstrap,
        openclaw_postmerge_runtime_dependencies_ready,
        register_openclaw_supervisor_postmerge_task,
        release_openclaw_supervisor_postmerge_task,
    )
    from modules.infrastructure.dae_daemon.src.dae_launch_broker import get_dae_launch_broker
    from modules.infrastructure.database.src.agent_db import AgentDB
    from scripts.reddog_holoindex_owner_query_once import query_once

    return _run_holoindex_postmerge_runtime_for_test(
        repo_root=Path(repo_root), query=query.strip(), timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds, git_runner=_git_runner,
        query_runner=query_once, select_authority=resolve_holoindex_authority_root,
        coordinator=coordinate_holoindex_incident_repair,
        bootstrap=_ensure_broker_bootstrap, broker_provider=get_dae_launch_broker,
        database_provider=AgentDB, clock=time.monotonic, sleeper=time.sleep,
        lease_factory=_production_runtime_lease,
        runtime_preflight=openclaw_postmerge_runtime_dependencies_ready,
        task_binder=register_openclaw_supervisor_postmerge_task,
        task_releaser=release_openclaw_supervisor_postmerge_task,
    )


__all__ = [
    "HoloIndexPostmergeRuntimeResult",
    "run_holoindex_postmerge_runtime_once",
]
