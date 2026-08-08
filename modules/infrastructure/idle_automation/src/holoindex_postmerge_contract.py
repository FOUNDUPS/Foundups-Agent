"""Immutable contract and trusted helpers for post-merge HoloIndex work."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from holo_index.repository_state import (
    read_repository_state,
    repository_root_digest,
)
from holo_index.maintenance_lock import (
    AUTHORITY_BLOCK_MARKER_FILENAME,
    authority_block_marker_valid,
)


SCHEMA_VERSION = "holoindex_postmerge_coordination_v1"
TASK_PREFIX = "holoindex_postmerge_refresh:"
REQUEST_EVENT_PREFIX = "holoindex_postmerge_requested:"
COMPLETION_EVENT_PREFIX = "holoindex_postmerge_completed:"
SOURCE = "holoindex_postmerge_coordinator"
CLAIM_AGENT_ID = "openclaw_supervisor"
AUTHORITY_REPO_ROOT_ENV = "REDDOG_HOLOINDEX_AUTHORITY_REPO_ROOT"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 300
ASSIGNMENT_LEASE_SECONDS = 7500

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class AgentDbPort(Protocol):
    def get_autonomous_task_by_id(self, task_id: str) -> dict[str, Any] | None: ...

    def create_holoindex_postmerge_task_if_absent(
        self,
        task_id: str,
        description: str,
        required_skills: list[str],
        estimated_complexity: float,
        priority_score: float,
        context: dict[str, Any] | None = None,
        origin_continuity_id: str | None = None,
    ) -> bool: ...

    def create_coordination_event(
        self,
        event_id: str,
        event_type: str,
        initiator_agent: str,
        target_agents: list[str],
        payload: dict[str, Any],
    ) -> bool: ...

    def get_coordination_event_by_id(self, event_id: str) -> dict[str, Any] | None: ...

    def schedule_holoindex_postmerge_task_retry(
        self,
        task_id: str,
        *,
        context: dict[str, Any],
        retry_not_before: str,
    ) -> bool: ...

    def requeue_holoindex_postmerge_task(
        self,
        task_id: str,
        *,
        expected_status: str,
    ) -> bool: ...

    def claim_holoindex_postmerge_task(
        self,
        task_id: str,
        agent_id: str,
        *,
        expected_source: str,
        expected_schema_version: str,
        expected_target_repo_head_sha: str,
        expected_authority_root_digest: str,
        lease_seconds: int = 900,
    ) -> str: ...

    def start_holoindex_postmerge_execution(
        self,
        task_id: str,
        agent_id: str,
        *,
        claim_id: str,
        claim_binding_digest: str,
    ) -> bool: ...

    def fail_holoindex_postmerge_task(
        self,
        task_id: str,
        agent_id: str,
        *,
        claim_id: str,
        claim_binding_digest: str,
        status: str = "failed",
    ) -> bool: ...

    def reclaim_expired_holoindex_postmerge_task(
        self,
        task_id: str,
        agent_id: str,
        *,
        expected_assigned_at: str,
    ) -> bool: ...

    def commit_holoindex_postmerge_completion(
        self,
        *,
        task_id: str,
        agent_id: str,
        request_event_id: str,
        request_payload_digest: str,
        completion_event_id: str,
        completion_payload: dict[str, Any],
        claim_id: str,
        claim_binding_digest: str,
    ) -> bool: ...


GitRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class HoloIndexPostMergeCoordinationResult:
    accepted: bool
    status: str
    target_repo_head_sha: str = ""
    task_id: str = ""
    authority_root_digest: str = ""
    generation_id: str = ""
    freshness_receipt_digest: str = ""
    rejection_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["rejection_reasons"] = list(self.rejection_reasons)
        return value


def _canonical_digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _default_git_runner(
    argv: Sequence[str], cwd: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
        shell=False,
    )


def _git_output(
    runner: GitRunner,
    cwd: Path,
    *args: str,
) -> tuple[str, str]:
    try:
        completed = runner(("git", *args), cwd)
    except (OSError, subprocess.SubprocessError, ValueError):
        return "", "git_command_failed"
    output = str(completed.stdout or "").strip()
    if completed.returncode != 0 or not output:
        return "", "git_command_failed"
    return output, ""


def _fetch_origin_main(runner: GitRunner, repo_root: Path) -> tuple[str, str]:
    try:
        fetched = runner(("git", "fetch", "--quiet", "origin", "main"), repo_root)
    except (OSError, subprocess.SubprocessError, ValueError):
        return "", "origin_main_fetch_failed"
    if fetched.returncode != 0:
        return "", "origin_main_fetch_failed"
    head, error = _git_output(runner, repo_root, "rev-parse", "FETCH_HEAD")
    normalized = head.lower()
    if error or _SHA_RE.fullmatch(normalized) is None:
        return "", "origin_main_sha_unproven"
    return normalized, ""


def _authority_root(
    workspace_root: Path,
    environment: Mapping[str, str],
) -> tuple[Path | None, str]:
    configured = str(environment.get(AUTHORITY_REPO_ROOT_ENV, "") or "").strip()
    if configured:
        candidate = Path(configured)
        if not candidate.is_absolute():
            return None, "authority_root_not_absolute"
        return candidate.resolve(strict=False), ""
    return (
        workspace_root.parent / f"{workspace_root.name}-holo-authority"
    ).resolve(strict=False), ""


def _common_git_dir(
    runner: GitRunner,
    repo_root: Path,
) -> tuple[Path | None, str]:
    value, error = _git_output(
        runner,
        repo_root,
        "rev-parse",
        "--path-format=absolute",
        "--git-common-dir",
    )
    if error:
        return None, "git_common_dir_unproven"
    path = Path(value)
    return (
        path if path.is_absolute() else repo_root / path
    ).resolve(strict=False), ""


def _validate_authority_root(
    workspace_root: Path,
    authority_root: Path,
    runner: GitRunner,
) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    if (
        authority_root == workspace_root
        or not authority_root.is_dir()
        or not (authority_root / ".git").exists()
    ):
        reasons.append("authority_root_invalid")
    workspace_common, workspace_error = _common_git_dir(runner, workspace_root)
    authority_common, authority_error = _common_git_dir(runner, authority_root)
    if workspace_error or authority_error:
        reasons.append("authority_git_identity_unproven")
    elif os.path.normcase(str(workspace_common)) != os.path.normcase(
        str(authority_common)
    ):
        reasons.append("authority_root_unrelated")
    authority_state = read_repository_state(authority_root)
    marker_recovery = bool(
        authority_block_marker_valid(authority_root)
        and _marker_is_only_dirty_path(runner, authority_root)
    )
    if not authority_state.proven_clean and not marker_recovery:
        reasons.append("authority_root_dirty")
    digest = repository_root_digest(authority_root) if not reasons else ""
    return digest, tuple(dict.fromkeys(reasons))


def _marker_is_only_dirty_path(
    runner: GitRunner,
    authority_root: Path,
) -> bool:
    value, error = _git_output(
        runner,
        authority_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    if error:
        return False
    entries = [line.strip() for line in value.splitlines() if line.strip()]
    return entries == [f"?? {AUTHORITY_BLOCK_MARKER_FILENAME}"]


def _event_payload(
    *,
    target_repo_head_sha: str,
    authority_root_digest: str,
    status: str,
    generation_id: str = "",
    freshness_receipt_digest: str = "",
) -> dict[str, Any]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "target_repo_head_sha": target_repo_head_sha,
        "authority_root_digest": authority_root_digest,
        "status": status,
        "generation_id": generation_id,
        "freshness_receipt_digest": freshness_receipt_digest,
    }
    payload["payload_digest"] = _canonical_digest(payload)
    return payload


def _event_payload_valid(
    event: Mapping[str, Any] | None,
    *,
    target_repo_head_sha: str,
    authority_root_digest: str,
    expected_status: str,
) -> bool:
    if not isinstance(event, Mapping):
        return False
    payload = event.get("payload")
    if not isinstance(payload, Mapping):
        return False
    unsigned = dict(payload)
    claimed = str(unsigned.pop("payload_digest", "") or "")
    base_valid = bool(
        claimed
        and claimed == _canonical_digest(unsigned)
        and unsigned.get("schema_version") == SCHEMA_VERSION
        and unsigned.get("target_repo_head_sha") == target_repo_head_sha
        and unsigned.get("authority_root_digest") == authority_root_digest
        and unsigned.get("status") == expected_status
    )
    if not base_valid:
        return False
    if expected_status == "COMPLETED":
        return all(
            isinstance(unsigned.get(field), str)
            and re.fullmatch(r"sha256:[0-9a-f]{64}", unsigned[field]) is not None
            for field in ("generation_id", "freshness_receipt_digest")
        )
    return True


def _load_db(db: AgentDbPort | None) -> AgentDbPort:
    if db is not None:
        return db
    from modules.infrastructure.database.src.agent_db import AgentDB

    return AgentDB()


def _completed_task_valid(
    task: Mapping[str, Any] | None,
    *,
    target_repo_head_sha: str,
    authority_root_digest: str,
) -> bool:
    if not isinstance(task, Mapping) or task.get("status") != "completed":
        return False
    context = task.get("context")
    return bool(
        isinstance(context, Mapping)
        and context.get("schema_version") == SCHEMA_VERSION
        and context.get("source") == SOURCE
        and context.get("target_repo_head_sha") == target_repo_head_sha
        and context.get("authority_root_digest") == authority_root_digest
        and context.get("request_event_id")
        == REQUEST_EVENT_PREFIX + target_repo_head_sha
        and task.get("assigned_to") == CLAIM_AGENT_ID
    )


def validate_holoindex_postmerge_completion(
    database: AgentDbPort,
    *,
    task_id: str,
    target_repo_head_sha: str,
    authority_root_digest: str,
) -> Mapping[str, Any] | None:
    """Read one completion proven by the existing atomic task/event transaction."""

    if task_id != TASK_PREFIX + target_repo_head_sha or not _completed_task_valid(
        database.get_autonomous_task_by_id(task_id),
        target_repo_head_sha=target_repo_head_sha,
        authority_root_digest=authority_root_digest,
    ):
        return None
    requested = database.get_coordination_event_by_id(REQUEST_EVENT_PREFIX + target_repo_head_sha)
    completed = database.get_coordination_event_by_id(COMPLETION_EVENT_PREFIX + target_repo_head_sha)
    if not _event_payload_valid(
        requested,
        target_repo_head_sha=target_repo_head_sha,
        authority_root_digest=authority_root_digest,
        expected_status="REQUESTED",
    ) or not _event_payload_valid(
        completed,
        target_repo_head_sha=target_repo_head_sha,
        authority_root_digest=authority_root_digest,
        expected_status="COMPLETED",
    ):
        return None
    return dict(completed["payload"])


__all__ = [
    "AUTHORITY_REPO_ROOT_ENV",
    "CLAIM_AGENT_ID",
    "COMPLETION_EVENT_PREFIX",
    "HoloIndexPostMergeCoordinationResult",
    "MAX_RETRIES",
    "REQUEST_EVENT_PREFIX",
    "RETRY_DELAY_SECONDS",
    "SCHEMA_VERSION",
    "SOURCE",
    "TASK_PREFIX",
    "validate_holoindex_postmerge_completion",
]
