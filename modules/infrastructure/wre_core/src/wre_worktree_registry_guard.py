"""Read-only Git worktree registry audit and mutation admission guard.

The audit path runs only bounded, read-only Git commands through an injected
argv runner. It emits remediation candidates but never removes, prunes,
unlocks, moves, or edits a worktree. Mutation callers must separately pass the
fresh receipt to ``validate_worktree_mutation_admission``.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import subprocess
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Protocol, Sequence, Tuple


WORKTREE_REGISTRY_RECEIPT_SCHEMA = "wre.worktree_registry_hygiene.v1"
WORKTREE_MUTATION_ADMISSION_SCHEMA = "wre.worktree_mutation_admission.v1"

STATUS_PASS = "PASS"
STATUS_WARN = "WARN"
STATUS_REJECT = "REJECT"

FAIL_CWD_NOT_ABSOLUTE = "FAIL_CWD_NOT_ABSOLUTE"
FAIL_CWD_DEVICE_PREFIX = "FAIL_CWD_DEVICE_PREFIX"
FAIL_CWD_PATH_AMBIGUOUS = "FAIL_CWD_PATH_AMBIGUOUS"
FAIL_GIT_PROOF_UNAVAILABLE = "FAIL_GIT_PROOF_UNAVAILABLE"
FAIL_GIT_OUTPUT_TOO_LARGE = "FAIL_GIT_OUTPUT_TOO_LARGE"
FAIL_MALFORMED_WORKTREE_PORCELAIN = "FAIL_MALFORMED_WORKTREE_PORCELAIN"
FAIL_OWNER_NOT_REGISTERED = "FAIL_OWNER_NOT_REGISTERED"
FAIL_OWNER_AMBIGUOUS = "FAIL_OWNER_AMBIGUOUS"
FAIL_HEAD_MISMATCH = "FAIL_HEAD_MISMATCH"
FAIL_PROCESS_LIVENESS_UNAVAILABLE = "FAIL_PROCESS_LIVENESS_UNAVAILABLE"

FAIL_RECEIPT_INVALID = "FAIL_RECEIPT_INVALID"
FAIL_RECEIPT_EXPIRED = "FAIL_RECEIPT_EXPIRED"
FAIL_SHARED_MAIN_MUTATION = "FAIL_SHARED_MAIN_MUTATION"
FAIL_DETACHED_WORKTREE_MUTATION = "FAIL_DETACHED_WORKTREE_MUTATION"
FAIL_LOCKED_WORKTREE_MUTATION = "FAIL_LOCKED_WORKTREE_MUTATION"
FAIL_STALE_WORKTREE_MUTATION = "FAIL_STALE_WORKTREE_MUTATION"
FAIL_INTENDED_WORKTREE_PATH_INVALID = "FAIL_INTENDED_WORKTREE_PATH_INVALID"
FAIL_INTENDED_WORKTREE_MISMATCH = "FAIL_INTENDED_WORKTREE_MISMATCH"
FAIL_CWD_OUTSIDE_OWNING_WORKTREE = "FAIL_CWD_OUTSIDE_OWNING_WORKTREE"
WORKTREE_MUTATION_ADMISSION_PASS = "WORKTREE_MUTATION_ADMISSION_PASS"

_DEVICE_PREFIXES = ("\\\\?\\", "\\\\.\\", "//?/", "//./")
_HEAD_RE = re.compile(r"^[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?$")
_LOCK_PID_RE = re.compile(r"(?:^|[ (])pid[ =:]+([1-9][0-9]{0,9})(?:[ )]|$)", re.IGNORECASE)
_MAX_GIT_OUTPUT_CHARS = 1_000_000
_MAX_WORKTREES = 512
_MAX_STALE_LOCK_CANDIDATES = 32
_MAX_PATH_CHARS = 4096
_DEFAULT_TIMEOUT_S = 10
_DEFAULT_RECEIPT_MAX_AGE_S = 30

_CMD_COMMON_DIR = ("git", "rev-parse", "--path-format=absolute", "--git-common-dir")
_CMD_TOPLEVEL = ("git", "rev-parse", "--show-toplevel")
_CMD_HEAD = ("git", "rev-parse", "--verify", "HEAD")
_CMD_STATUS = (
    "git",
    "--no-optional-locks",
    "status",
    "--porcelain=v1",
    "-z",
    "--untracked-files=all",
)
_CMD_WORKTREES = ("git", "worktree", "list", "--porcelain")
_READ_ONLY_COMMANDS = (
    _CMD_COMMON_DIR,
    _CMD_TOPLEVEL,
    _CMD_HEAD,
    _CMD_STATUS,
    _CMD_WORKTREES,
)


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str = ""


class WorktreeRegistryCommandRunner(Protocol):
    def run(self, argv: Sequence[str], *, cwd: Path, timeout_s: int) -> CommandResult:
        """Run a read-only argv command with no shell."""


class SubprocessWorktreeRegistryCommandRunner:
    """Production read-only runner; all command authority stays in this module."""

    def run(self, argv: Sequence[str], *, cwd: Path, timeout_s: int) -> CommandResult:
        if tuple(str(item) for item in argv) not in _READ_ONLY_COMMANDS:
            raise ValueError("command is outside the worktree-audit read-only allowlist")
        completed = subprocess.run(
            list(argv),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
            shell=False,
        )
        return CommandResult(
            returncode=int(completed.returncode),
            stdout=str(completed.stdout or ""),
            stderr=str(completed.stderr or ""),
        )


@dataclass(frozen=True)
class StaleLockCandidate:
    worktree_path: str
    classification: str
    pid: Optional[int]
    lock_reason_digest: str


@dataclass(frozen=True)
class WorktreeRegistryReceipt:
    schema_version: str
    receipt_id: str
    observed_at_unix: int
    current_cwd: str
    git_common_dir: str
    owning_worktree: str
    branch: Optional[str]
    head: Optional[str]
    shared_main_indicator: bool
    owning_worktree_locked: bool
    owning_worktree_stale: bool
    registered_count: int
    locked_count: int
    detached_count: int
    stale_count: int
    stale_lock_candidates: Tuple[StaleLockCandidate, ...]
    stale_lock_candidates_truncated: bool
    dirty: bool
    dirty_state_digest: str
    accepted: bool
    status: str
    reasons: Tuple[str, ...]
    no_cleanup_performed: bool = True
    no_registry_mutation_performed: bool = True
    no_repo_mutation_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorktreeMutationAdmission:
    schema_version: str
    receipt_id: str
    accepted: bool
    status: str
    reason: str
    registry_receipt_id: str
    current_cwd: str
    owning_worktree: str
    intended_worktree: str
    no_mutation_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _WorktreeEntry:
    path: str
    head: Optional[str]
    branch: Optional[str]
    detached: bool
    bare: bool
    locked_reason: Optional[str]
    prunable_reason: Optional[str]


class _PathProofError(ValueError):
    pass


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _raw_has_device_prefix(value: Path | str) -> bool:
    raw = str(value)
    return any(raw.startswith(prefix) for prefix in _DEVICE_PREFIXES)


def _path_identity(value: Path | str) -> str:
    return os.path.normcase(os.path.normpath(str(value)))


def _prove_existing_unambiguous_path(value: Path | str, *, label: str) -> Path:
    if not str(value) or len(str(value)) > _MAX_PATH_CHARS:
        raise _PathProofError(f"{label}:invalid_length")
    if _raw_has_device_prefix(value):
        raise _PathProofError(f"{label}:device_prefix")
    path = value if isinstance(value, Path) else Path(str(value))
    if not path.is_absolute():
        raise _PathProofError(f"{label}:not_absolute")
    try:
        lexical = Path(os.path.abspath(os.path.normpath(str(path))))
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise _PathProofError(f"{label}:unresolvable") from exc
    if _path_identity(lexical) != _path_identity(resolved):
        raise _PathProofError(f"{label}:symlink_or_path_ambiguity")
    return resolved


def _lexical_absolute_path(value: str, *, label: str) -> Path:
    if not value or len(value) > _MAX_PATH_CHARS or _raw_has_device_prefix(value):
        raise _PathProofError(f"{label}:invalid")
    path = Path(value)
    if not path.is_absolute():
        raise _PathProofError(f"{label}:not_absolute")
    return Path(os.path.abspath(os.path.normpath(str(path))))


def _is_inside(child: Path | str, parent: Path | str) -> bool:
    try:
        common = os.path.commonpath((str(child), str(parent)))
    except ValueError:
        return False
    return _path_identity(common) == _path_identity(parent)


def _default_process_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _parse_worktree_porcelain(text: str) -> Tuple[_WorktreeEntry, ...]:
    if "\x00" in text or len(text) > _MAX_GIT_OUTPUT_CHARS:
        raise ValueError("invalid porcelain size or NUL")

    records = []
    current: Dict[str, Any] = {}

    def finish_record() -> None:
        nonlocal current
        if not current:
            return
        path = current.get("worktree")
        head = current.get("HEAD")
        branch = current.get("branch")
        detached = bool(current.get("detached"))
        bare = bool(current.get("bare"))
        if not path or (not bare and not head):
            raise ValueError("worktree record missing path or HEAD")
        if head is not None and not _HEAD_RE.fullmatch(str(head)):
            raise ValueError("invalid HEAD")
        if sum((bool(branch), detached, bare)) != 1:
            raise ValueError("worktree state must be exactly branch, detached, or bare")
        records.append(
            _WorktreeEntry(
                path=str(path),
                head=str(head).lower() if head is not None else None,
                branch=str(branch) if branch else None,
                detached=detached,
                bare=bare,
                locked_reason=current.get("locked"),
                prunable_reason=current.get("prunable"),
            )
        )
        current = {}

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        if not line:
            finish_record()
            if len(records) > _MAX_WORKTREES:
                raise ValueError("too many worktrees")
            continue
        if not current and not line.startswith("worktree "):
            raise ValueError("record must start with worktree")
        if line.startswith("worktree "):
            if current:
                raise ValueError("missing record delimiter")
            current["worktree"] = line[len("worktree ") :]
            continue
        if line in {"detached", "bare"}:
            if line in current:
                raise ValueError("duplicate flag")
            current[line] = True
            continue
        key, separator, value = line.partition(" ")
        if key not in {"HEAD", "branch", "locked", "prunable"}:
            raise ValueError("unknown porcelain field")
        if key in current:
            raise ValueError("duplicate porcelain field")
        current[key] = value if separator else ""

    finish_record()
    if not records or len(records) > _MAX_WORKTREES:
        raise ValueError("worktree registry empty or too large")

    identities = set()
    for entry in records:
        path = _lexical_absolute_path(entry.path, label="registry_worktree")
        identity = _path_identity(path)
        if identity in identities:
            raise ValueError("duplicate worktree path")
        identities.add(identity)
    return tuple(records)


def _receipt_payload(receipt: WorktreeRegistryReceipt) -> Dict[str, Any]:
    payload = receipt.to_dict()
    payload.pop("receipt_id", None)
    return payload


def _seal_receipt(receipt: WorktreeRegistryReceipt) -> WorktreeRegistryReceipt:
    return replace(receipt, receipt_id=_digest(_receipt_payload(receipt)))


def _receipt_is_valid(receipt: WorktreeRegistryReceipt) -> bool:
    return (
        receipt.schema_version == WORKTREE_REGISTRY_RECEIPT_SCHEMA
        and bool(receipt.receipt_id)
        and receipt.receipt_id == _digest(_receipt_payload(receipt))
    )


def _rejected_receipt(*, cwd: Path | str, observed_at_unix: int, reason: str) -> WorktreeRegistryReceipt:
    receipt = WorktreeRegistryReceipt(
        schema_version=WORKTREE_REGISTRY_RECEIPT_SCHEMA,
        receipt_id="",
        observed_at_unix=observed_at_unix,
        current_cwd=str(cwd),
        git_common_dir="",
        owning_worktree="",
        branch=None,
        head=None,
        shared_main_indicator=False,
        owning_worktree_locked=False,
        owning_worktree_stale=False,
        registered_count=0,
        locked_count=0,
        detached_count=0,
        stale_count=0,
        stale_lock_candidates=(),
        stale_lock_candidates_truncated=False,
        dirty=False,
        dirty_state_digest=_digest(""),
        accepted=False,
        status=STATUS_REJECT,
        reasons=(reason,),
    )
    return _seal_receipt(receipt)


def audit_worktree_registry(
    *,
    cwd: Path | str,
    runner: Optional[WorktreeRegistryCommandRunner] = None,
    process_is_alive: Optional[Callable[[int], bool]] = None,
    path_exists: Optional[Callable[[Path], bool]] = None,
    now: Optional[Callable[[], float]] = None,
    timeout_s: int = _DEFAULT_TIMEOUT_S,
) -> WorktreeRegistryReceipt:
    """Inspect Git ownership and registry state without mutating either."""

    clock = now or time.time
    observed_at = int(clock())
    try:
        cwd_path = _prove_existing_unambiguous_path(cwd, label="cwd")
    except _PathProofError as exc:
        detail = str(exc)
        if detail.endswith("not_absolute"):
            reason = FAIL_CWD_NOT_ABSOLUTE
        elif detail.endswith("device_prefix"):
            reason = FAIL_CWD_DEVICE_PREFIX
        else:
            reason = FAIL_CWD_PATH_AMBIGUOUS
        return _rejected_receipt(cwd=cwd, observed_at_unix=observed_at, reason=reason)

    command_runner = runner or SubprocessWorktreeRegistryCommandRunner()
    outputs: Dict[Tuple[str, ...], str] = {}
    try:
        for argv in _READ_ONLY_COMMANDS:
            result = command_runner.run(argv, cwd=cwd_path, timeout_s=timeout_s)
            if result.returncode != 0:
                return _rejected_receipt(
                    cwd=cwd_path,
                    observed_at_unix=observed_at,
                    reason=FAIL_GIT_PROOF_UNAVAILABLE,
                )
            if len(result.stdout) > _MAX_GIT_OUTPUT_CHARS:
                return _rejected_receipt(
                    cwd=cwd_path,
                    observed_at_unix=observed_at,
                    reason=FAIL_GIT_OUTPUT_TOO_LARGE,
                )
            outputs[argv] = result.stdout
    except Exception:
        return _rejected_receipt(
            cwd=cwd_path,
            observed_at_unix=observed_at,
            reason=FAIL_GIT_PROOF_UNAVAILABLE,
        )

    try:
        common_dir = _prove_existing_unambiguous_path(
            outputs[_CMD_COMMON_DIR].strip(), label="git_common_dir"
        )
        owning_worktree = _prove_existing_unambiguous_path(
            outputs[_CMD_TOPLEVEL].strip(), label="owning_worktree"
        )
        entries = _parse_worktree_porcelain(outputs[_CMD_WORKTREES])
    except (_PathProofError, ValueError):
        return _rejected_receipt(
            cwd=cwd_path,
            observed_at_unix=observed_at,
            reason=FAIL_MALFORMED_WORKTREE_PORCELAIN,
        )

    if not _is_inside(cwd_path, owning_worktree):
        return _rejected_receipt(
            cwd=cwd_path,
            observed_at_unix=observed_at,
            reason=FAIL_OWNER_AMBIGUOUS,
        )

    owner_matches = [
        entry
        for entry in entries
        if _path_identity(_lexical_absolute_path(entry.path, label="registry_worktree"))
        == _path_identity(owning_worktree)
    ]
    if not owner_matches:
        return _rejected_receipt(
            cwd=cwd_path,
            observed_at_unix=observed_at,
            reason=FAIL_OWNER_NOT_REGISTERED,
        )
    if len(owner_matches) != 1:
        return _rejected_receipt(
            cwd=cwd_path,
            observed_at_unix=observed_at,
            reason=FAIL_OWNER_AMBIGUOUS,
        )
    owner = owner_matches[0]
    observed_head = outputs[_CMD_HEAD].strip().lower()
    if not _HEAD_RE.fullmatch(observed_head) or owner.head != observed_head:
        return _rejected_receipt(
            cwd=cwd_path,
            observed_at_unix=observed_at,
            reason=FAIL_HEAD_MISMATCH,
        )

    alive_probe = process_is_alive or _default_process_is_alive
    exists_probe = path_exists or (lambda path: path.exists())
    stale_entry_ids = set()
    candidates = []
    for entry in entries:
        entry_path = _lexical_absolute_path(entry.path, label="registry_worktree")
        try:
            path_missing = not bool(exists_probe(entry_path))
        except Exception:
            return _rejected_receipt(
                cwd=cwd_path,
                observed_at_unix=observed_at,
                reason=FAIL_GIT_PROOF_UNAVAILABLE,
            )
        if entry.prunable_reason is not None or path_missing:
            stale_entry_ids.add(_path_identity(entry_path))
        if entry.locked_reason is None:
            continue
        match = _LOCK_PID_RE.search(entry.locked_reason)
        pid = int(match.group(1)) if match else None
        dead_pid = False
        if pid is not None:
            try:
                dead_pid = not bool(alive_probe(pid))
            except Exception:
                return _rejected_receipt(
                    cwd=cwd_path,
                    observed_at_unix=observed_at,
                    reason=FAIL_PROCESS_LIVENESS_UNAVAILABLE,
                )
        if dead_pid or path_missing:
            stale_entry_ids.add(_path_identity(entry_path))
            candidates.append(
                StaleLockCandidate(
                    worktree_path=str(entry_path),
                    classification="dead_pid" if dead_pid else "missing_worktree",
                    pid=pid,
                    lock_reason_digest=_digest(entry.locked_reason),
                )
            )

    candidates.sort(key=lambda item: (_path_identity(item.worktree_path), item.classification, item.pid or 0))
    candidates_truncated = len(candidates) > _MAX_STALE_LOCK_CANDIDATES
    bounded_candidates = tuple(candidates[:_MAX_STALE_LOCK_CANDIDATES])
    owner_identity = _path_identity(owning_worktree)
    owner_stale = owner_identity in stale_entry_ids
    primary_checkout = common_dir.parent if common_dir.name.lower() == ".git" else None
    is_primary_checkout = (
        primary_checkout is not None
        and owner_identity == _path_identity(primary_checkout)
    )

    reasons = []
    if stale_entry_ids:
        reasons.append("STALE_WORKTREES_OBSERVED")
    if candidates_truncated:
        reasons.append("STALE_LOCK_CANDIDATES_TRUNCATED")
    if any(entry.detached for entry in entries):
        reasons.append("DETACHED_WORKTREES_OBSERVED")
    status = STATUS_WARN if reasons else STATUS_PASS
    receipt = WorktreeRegistryReceipt(
        schema_version=WORKTREE_REGISTRY_RECEIPT_SCHEMA,
        receipt_id="",
        observed_at_unix=observed_at,
        current_cwd=str(cwd_path),
        git_common_dir=str(common_dir),
        owning_worktree=str(owning_worktree),
        branch=owner.branch,
        head=owner.head,
        shared_main_indicator=is_primary_checkout or owner.branch == "refs/heads/main",
        owning_worktree_locked=owner.locked_reason is not None,
        owning_worktree_stale=owner_stale,
        registered_count=len(entries),
        locked_count=sum(1 for entry in entries if entry.locked_reason is not None),
        detached_count=sum(1 for entry in entries if entry.detached),
        stale_count=len(stale_entry_ids),
        stale_lock_candidates=bounded_candidates,
        stale_lock_candidates_truncated=candidates_truncated,
        dirty=bool(outputs[_CMD_STATUS]),
        dirty_state_digest=_digest(outputs[_CMD_STATUS]),
        accepted=True,
        status=status,
        reasons=tuple(reasons),
    )
    return _seal_receipt(receipt)


def _admission_result(
    *,
    accepted: bool,
    status: str,
    reason: str,
    receipt: WorktreeRegistryReceipt,
    intended_worktree: Path | str,
) -> WorktreeMutationAdmission:
    payload = {
        "schema_version": WORKTREE_MUTATION_ADMISSION_SCHEMA,
        "accepted": accepted,
        "status": status,
        "reason": reason,
        "registry_receipt_id": receipt.receipt_id,
        "current_cwd": receipt.current_cwd,
        "owning_worktree": receipt.owning_worktree,
        "intended_worktree": str(intended_worktree),
        "no_mutation_performed": True,
    }
    return WorktreeMutationAdmission(receipt_id=_digest(payload), **payload)


def validate_worktree_mutation_admission(
    *,
    receipt: WorktreeRegistryReceipt,
    intended_worktree_path: Path | str,
    now: Optional[Callable[[], float]] = None,
    max_receipt_age_s: int = _DEFAULT_RECEIPT_MAX_AGE_S,
) -> WorktreeMutationAdmission:
    """Fail closed unless a fresh registry receipt proves isolated ownership."""

    if not _receipt_is_valid(receipt) or not receipt.accepted or receipt.status == STATUS_REJECT:
        return _admission_result(
            accepted=False,
            status=STATUS_REJECT,
            reason=FAIL_RECEIPT_INVALID,
            receipt=receipt,
            intended_worktree=intended_worktree_path,
        )
    clock = now or time.time
    age = int(clock()) - int(receipt.observed_at_unix)
    if max_receipt_age_s < 0 or age < 0 or age > max_receipt_age_s:
        return _admission_result(
            accepted=False,
            status=STATUS_REJECT,
            reason=FAIL_RECEIPT_EXPIRED,
            receipt=receipt,
            intended_worktree=intended_worktree_path,
        )
    if receipt.shared_main_indicator:
        return _admission_result(
            accepted=False,
            status=STATUS_REJECT,
            reason=FAIL_SHARED_MAIN_MUTATION,
            receipt=receipt,
            intended_worktree=intended_worktree_path,
        )
    if receipt.branch is None:
        return _admission_result(
            accepted=False,
            status=STATUS_REJECT,
            reason=FAIL_DETACHED_WORKTREE_MUTATION,
            receipt=receipt,
            intended_worktree=intended_worktree_path,
        )
    if receipt.owning_worktree_locked:
        return _admission_result(
            accepted=False,
            status=STATUS_REJECT,
            reason=FAIL_LOCKED_WORKTREE_MUTATION,
            receipt=receipt,
            intended_worktree=intended_worktree_path,
        )
    if receipt.owning_worktree_stale:
        return _admission_result(
            accepted=False,
            status=STATUS_REJECT,
            reason=FAIL_STALE_WORKTREE_MUTATION,
            receipt=receipt,
            intended_worktree=intended_worktree_path,
        )
    try:
        intended = _prove_existing_unambiguous_path(intended_worktree_path, label="intended_worktree")
        owner = _prove_existing_unambiguous_path(receipt.owning_worktree, label="owning_worktree")
        current_cwd = _prove_existing_unambiguous_path(receipt.current_cwd, label="current_cwd")
    except _PathProofError:
        return _admission_result(
            accepted=False,
            status=STATUS_REJECT,
            reason=FAIL_INTENDED_WORKTREE_PATH_INVALID,
            receipt=receipt,
            intended_worktree=intended_worktree_path,
        )
    if _path_identity(intended) != _path_identity(owner):
        return _admission_result(
            accepted=False,
            status=STATUS_REJECT,
            reason=FAIL_INTENDED_WORKTREE_MISMATCH,
            receipt=receipt,
            intended_worktree=intended,
        )
    if not _is_inside(current_cwd, owner):
        return _admission_result(
            accepted=False,
            status=STATUS_REJECT,
            reason=FAIL_CWD_OUTSIDE_OWNING_WORKTREE,
            receipt=receipt,
            intended_worktree=intended,
        )
    return _admission_result(
        accepted=True,
        status=STATUS_PASS,
        reason=WORKTREE_MUTATION_ADMISSION_PASS,
        receipt=receipt,
        intended_worktree=intended,
    )


__all__ = [
    "CommandResult",
    "FAIL_CWD_DEVICE_PREFIX",
    "FAIL_CWD_NOT_ABSOLUTE",
    "FAIL_CWD_PATH_AMBIGUOUS",
    "FAIL_DETACHED_WORKTREE_MUTATION",
    "FAIL_GIT_OUTPUT_TOO_LARGE",
    "FAIL_GIT_PROOF_UNAVAILABLE",
    "FAIL_HEAD_MISMATCH",
    "FAIL_INTENDED_WORKTREE_MISMATCH",
    "FAIL_INTENDED_WORKTREE_PATH_INVALID",
    "FAIL_LOCKED_WORKTREE_MUTATION",
    "FAIL_MALFORMED_WORKTREE_PORCELAIN",
    "FAIL_OWNER_AMBIGUOUS",
    "FAIL_OWNER_NOT_REGISTERED",
    "FAIL_PROCESS_LIVENESS_UNAVAILABLE",
    "FAIL_RECEIPT_EXPIRED",
    "FAIL_RECEIPT_INVALID",
    "FAIL_SHARED_MAIN_MUTATION",
    "FAIL_STALE_WORKTREE_MUTATION",
    "STATUS_PASS",
    "STATUS_REJECT",
    "STATUS_WARN",
    "StaleLockCandidate",
    "SubprocessWorktreeRegistryCommandRunner",
    "WORKTREE_MUTATION_ADMISSION_PASS",
    "WORKTREE_MUTATION_ADMISSION_SCHEMA",
    "WORKTREE_REGISTRY_RECEIPT_SCHEMA",
    "WorktreeMutationAdmission",
    "WorktreeRegistryCommandRunner",
    "WorktreeRegistryReceipt",
    "audit_worktree_registry",
    "validate_worktree_mutation_admission",
]
