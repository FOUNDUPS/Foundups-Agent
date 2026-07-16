"""Independent evidence producer for bounded RedDog/WRE coding slices.

Slice: WRE_INDEPENDENT_EVIDENCE_PRODUCER_RUNTIME_PHASE1

This module produces machine-derived evidence for the existing autonomous slice
verifier. It inspects an already-created isolated worktree, computes the real
Git diff between an exact base/head pair, runs caller-declared allowlisted
checks, and emits a verifier-compatible evidence packet.

It does not edit files, create worktrees, call GitHub, publish PRs, merge,
write PatternMemory, settle rewards, or re-index HoloIndex.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence

EVIDENCE_PRODUCER_ACCEPT = "INDEPENDENT_EVIDENCE_PRODUCER_ACCEPT"
EVIDENCE_PRODUCER_REJECT = "INDEPENDENT_EVIDENCE_PRODUCER_REJECT"

FAIL_EXPLICIT_REQUEST = "FAIL_EXPLICIT_EVIDENCE_PRODUCTION_REQUEST_MISSING"
FAIL_REPO_ROOT = "FAIL_REPO_ROOT_INVALID"
FAIL_WORKTREE = "FAIL_WORKTREE_INVALID"
FAIL_WORKTREE_INSIDE_REPO = "FAIL_WORKTREE_INSIDE_REPO"
FAIL_OPERATION_CWD = "FAIL_OPERATION_CWD_INVALID"
FAIL_SHA = "FAIL_SHA_INVALID"
FAIL_HEAD_MISMATCH = "FAIL_HEAD_SHA_MISMATCH"
FAIL_DIFF_EVIDENCE = "FAIL_DIFF_EVIDENCE"
FAIL_SCOPE_VIOLATION = "FAIL_SCOPE_VIOLATION"
FAIL_PROTECTED_SURFACE = "FAIL_PROTECTED_SURFACE"
FAIL_SECRET_IN_DIFF = "FAIL_SECRET_IN_DIFF"
FAIL_REQUIRED_CHECKS = "FAIL_REQUIRED_CHECKS"
FAIL_CHECK_COMMAND_REJECTED = "FAIL_CHECK_COMMAND_REJECTED"
FAIL_CHECK_FAILED = "FAIL_CHECK_FAILED"
FAIL_HOLOINDEX_EVIDENCE = "FAIL_HOLOINDEX_EVIDENCE"
FAIL_RUNNER_EXCEPTION = "FAIL_RUNNER_EXCEPTION"

HEAD_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

MAX_DIFF_SAMPLE_BYTES = 64 * 1024
MAX_COMMAND_OUTPUT_BYTES = 32 * 1024
MAX_CHECKS = 8
MAX_ARGV = 24
DEFAULT_TIMEOUT_S = 60

PROTECTED_PATH_PREFIXES = (
    ".github/workflows/",
    "WSP_framework/",
    "holo_index/",
    "modules/infrastructure/wre_core/src/wre_autonomous_slice_verifier_runtime.py",
    "modules/infrastructure/wre_core/src/wre_independent_evidence_producer_runtime.py",
    "modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py",
    "modules/communication/moltbot_bridge/src/reddog_work_order_signature_verifier.py",
    "modules/communication/moltbot_bridge/src/reddog_signed_receipt_chain.py",
)

DENIED_PATH_FRAGMENTS = (
    "/secrets/",
    "/wallet/",
    "/private_key",
    "/nonce/",
    "/permission/",
)

SECRET_MARKERS = (
    "authorization:",
    "bearer ",
    "api_key",
    "apikey",
    "private_key",
    "begin private key",
    "secret=",
    "token=",
    "password=",
)


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    timed_out: bool = False
    stdout_truncated: bool = False
    stderr_truncated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EvidenceCommandRunner(Protocol):
    def run(self, argv: Sequence[str], *, cwd: Path, timeout_s: int) -> CommandResult:
        ...


class SubprocessEvidenceCommandRunner:
    """Read-only command runner. Uses argv lists only; shell is never enabled."""

    def run(self, argv: Sequence[str], *, cwd: Path, timeout_s: int) -> CommandResult:
        start = time.perf_counter()
        try:
            completed = subprocess.run(
                list(argv),
                cwd=str(cwd),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_s,
                shell=False,
                check=False,
            )
            stdout, stdout_truncated = _truncate_with_flag(completed.stdout, MAX_COMMAND_OUTPUT_BYTES)
            stderr, stderr_truncated = _truncate_with_flag(completed.stderr, MAX_COMMAND_OUTPUT_BYTES)
            return CommandResult(
                returncode=int(completed.returncode),
                stdout=stdout,
                stderr=stderr,
                duration_ms=int((time.perf_counter() - start) * 1000),
                stdout_truncated=stdout_truncated,
                stderr_truncated=stderr_truncated,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            stdout, stdout_truncated = _truncate_with_flag(stdout, MAX_COMMAND_OUTPUT_BYTES)
            stderr, stderr_truncated = _truncate_with_flag(stderr, MAX_COMMAND_OUTPUT_BYTES)
            return CommandResult(
                returncode=124,
                stdout=stdout,
                stderr=stderr,
                duration_ms=int((time.perf_counter() - start) * 1000),
                timed_out=True,
                stdout_truncated=stdout_truncated,
                stderr_truncated=stderr_truncated,
            )


@dataclass(frozen=True)
class EvidenceProducerReceipt:
    receipt_id: str
    work_order_id: str
    slice_name: str
    worker_id: str
    verifier_id: str
    base_sha: str
    head_sha: str
    changed_paths: List[str]
    diff_digest: str
    test_evidence_digest: str
    check_count: int
    rejection_reasons: List[str]
    accepted: bool
    no_file_edit_performed: bool = True
    no_worktree_created: bool = True
    no_github_call_performed: bool = True
    no_pr_publish_performed: bool = True
    no_merge_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IndependentEvidenceProducerResult:
    decision: str
    accepted: bool
    rejection_reasons: List[str]
    diff_evidence: Dict[str, Any]
    test_evidence: Dict[str, Any]
    receipt: EvidenceProducerReceipt
    command_results: List[Dict[str, Any]] = field(default_factory=list)
    no_file_edit_performed: bool = True
    no_worktree_created: bool = True
    no_github_call_performed: bool = True
    no_pr_publish_performed: bool = True
    no_merge_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["receipt"] = self.receipt.to_dict()
        return payload


def produce_independent_slice_evidence(
    request: Mapping[str, Any],
    *,
    runner: Optional[EvidenceCommandRunner] = None,
) -> IndependentEvidenceProducerResult:
    """Produce machine-derived evidence for one bounded worktree slice."""

    req = request if isinstance(request, Mapping) else {}
    reasons: List[str] = []
    if req.get("explicit_evidence_production_requested") is not True:
        reasons.append(FAIL_EXPLICIT_REQUEST)

    repo_root = _resolve_path(req.get("repo_root"))
    worktree_path = _resolve_path(req.get("worktree_path"))
    operation_cwd = _resolve_path(req.get("operation_cwd") or req.get("worktree_path"))
    if repo_root is None or not repo_root.exists() or not repo_root.is_dir():
        reasons.append(FAIL_REPO_ROOT)
    if worktree_path is None or not worktree_path.exists() or not worktree_path.is_dir():
        reasons.append(FAIL_WORKTREE)
    if repo_root and worktree_path and _is_inside(worktree_path, repo_root):
        reasons.append(FAIL_WORKTREE_INSIDE_REPO)
    if worktree_path and operation_cwd and not _is_inside(operation_cwd, worktree_path):
        reasons.append(FAIL_OPERATION_CWD)

    work_order_id = str(req.get("work_order_id") or "")
    slice_name = str(req.get("slice_name") or "")
    worker_id = str(req.get("worker_id") or "")
    verifier_id = str(req.get("verifier_id") or "")
    base_sha = str(req.get("base_sha") or "")
    head_sha = str(req.get("head_sha") or "")
    if not all([work_order_id, slice_name, worker_id, verifier_id]):
        reasons.append(FAIL_DIFF_EVIDENCE)
    if not _is_head_sha(base_sha) or not _is_head_sha(head_sha) or base_sha == head_sha:
        reasons.append(FAIL_SHA)

    holo = _mapping(req.get("holoindex_evidence"))
    if holo.get("index_gap_detected") is True or str(holo.get("retrieval_quality") or "").upper() == "INDEX_GAP":
        reasons.append(FAIL_HOLOINDEX_EVIDENCE)

    command_runner = runner or SubprocessEvidenceCommandRunner()
    command_results: List[Dict[str, Any]] = []
    changed_paths: List[str] = []
    diff_text = ""
    added_lines: List[str] = []

    if not reasons:
        try:
            assert worktree_path is not None
            head = command_runner.run(("git", "rev-parse", "HEAD"), cwd=worktree_path, timeout_s=DEFAULT_TIMEOUT_S)
            command_results.append(_command_record("git_rev_parse_head", ("git", "rev-parse", "HEAD"), head))
            if head.returncode != 0 or head.stdout.strip() != head_sha:
                reasons.append(FAIL_HEAD_MISMATCH)

            if not reasons:
                names = command_runner.run(
                    ("git", "diff", "--name-only", base_sha, head_sha, "--"),
                    cwd=worktree_path,
                    timeout_s=DEFAULT_TIMEOUT_S,
                )
                command_results.append(
                    _command_record("git_diff_name_only", ("git", "diff", "--name-only", base_sha, head_sha, "--"), names)
                )
                if names.returncode != 0:
                    reasons.append(FAIL_DIFF_EVIDENCE)
                changed_paths = _normalize_changed_paths(names.stdout)
                if not changed_paths:
                    reasons.append(FAIL_DIFF_EVIDENCE)

            if changed_paths and not reasons:
                diff = command_runner.run(
                    ("git", "diff", "--unified=0", base_sha, head_sha, "--", *changed_paths),
                    cwd=worktree_path,
                    timeout_s=DEFAULT_TIMEOUT_S,
                )
                command_results.append(
                    _command_record("git_diff_unified", ("git", "diff", "--unified=0", base_sha, head_sha, "--", *changed_paths), diff)
                )
                if diff.returncode != 0 or diff.stdout_truncated:
                    reasons.append(FAIL_DIFF_EVIDENCE)
                diff_text = diff.stdout
                added_lines = _added_lines(diff_text)
        except Exception:
            reasons.append(FAIL_RUNNER_EXCEPTION)

    if changed_paths:
        path_reasons = _path_reasons(changed_paths, req)
        reasons.extend(path_reasons)
        if _diff_contains_secret(diff_text):
            reasons.append(FAIL_SECRET_IN_DIFF)

    checks = _list(req.get("required_checks"))
    test_records: List[Dict[str, Any]] = []
    if not checks:
        reasons.append(FAIL_REQUIRED_CHECKS)
    elif len(checks) > MAX_CHECKS:
        reasons.append(FAIL_REQUIRED_CHECKS)
    elif _terminal_reasons(reasons):
        # Unsafe diff/path state: do not proceed to caller commands.
        pass
    else:
        assert operation_cwd is not None
        for check in checks:
            check_map = _mapping(check)
            name = str(check_map.get("name") or "")
            argv = check_map.get("argv")
            timeout_s = _bounded_timeout(check_map.get("timeout_s"))
            if not _allowed_check_argv(argv):
                reasons.append(FAIL_CHECK_COMMAND_REJECTED)
                continue
            argv_tuple = tuple(str(item) for item in argv)
            try:
                result = command_runner.run(argv_tuple, cwd=operation_cwd, timeout_s=timeout_s)
            except Exception:
                reasons.append(FAIL_RUNNER_EXCEPTION)
                continue
            command_results.append(_command_record(name or "required_check", argv_tuple, result))
            conclusion = "success" if result.returncode == 0 and result.timed_out is False else "failure"
            record = {
                "name": name or argv_tuple[0],
                "head_sha": head_sha,
                "conclusion": conclusion,
                "returncode": result.returncode,
                "timed_out": result.timed_out,
                "argv_digest": _digest(list(argv_tuple)),
                "stdout_digest": _digest(result.stdout),
                "stderr_digest": _digest(result.stderr),
                "duration_ms": result.duration_ms,
            }
            test_records.append(record)
            if conclusion != "success":
                reasons.append(FAIL_CHECK_FAILED)

    diff_digest = _digest(diff_text)
    diff_evidence = {
        "source": "machine_derived",
        "red_dog_prose_source": False,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "diff_digest": diff_digest,
        "changed_paths": changed_paths,
        "added_lines": added_lines[:50],
        "diff_text_sample": _truncate(diff_text, MAX_DIFF_SAMPLE_BYTES),
    }
    test_evidence_digest = _digest(test_records)
    test_evidence = {
        "head_sha": head_sha,
        "test_evidence_digest": test_evidence_digest,
        "required_checks": test_records,
    }

    deduped = _dedupe(reasons)
    accepted = not deduped
    receipt_seed = {
        "work_order_id": work_order_id,
        "slice_name": slice_name,
        "worker_id": worker_id,
        "verifier_id": verifier_id,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "changed_paths": changed_paths,
        "diff_digest": diff_digest,
        "test_evidence_digest": test_evidence_digest,
        "rejection_reasons": deduped,
    }
    receipt = EvidenceProducerReceipt(
        receipt_id="wre_evidence_" + _digest(receipt_seed).removeprefix("sha256:")[:16],
        work_order_id=work_order_id,
        slice_name=slice_name,
        worker_id=worker_id,
        verifier_id=verifier_id,
        base_sha=base_sha,
        head_sha=head_sha,
        changed_paths=changed_paths,
        diff_digest=diff_digest,
        test_evidence_digest=test_evidence_digest,
        check_count=len(test_records),
        rejection_reasons=deduped,
        accepted=accepted,
    )
    return IndependentEvidenceProducerResult(
        decision=EVIDENCE_PRODUCER_ACCEPT if accepted else EVIDENCE_PRODUCER_REJECT,
        accepted=accepted,
        rejection_reasons=deduped,
        diff_evidence=diff_evidence,
        test_evidence=test_evidence,
        receipt=receipt,
        command_results=command_results,
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _resolve_path(value: Any) -> Optional[Path]:
    if not isinstance(value, (str, Path)) or not str(value):
        return None
    return Path(value).resolve()


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _is_head_sha(value: str) -> bool:
    return bool(HEAD_SHA_RE.fullmatch(str(value or "")))


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _dedupe(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def _truncate(value: str, max_bytes: int) -> str:
    return _truncate_with_flag(value, max_bytes)[0]


def _truncate_with_flag(value: str, max_bytes: int) -> tuple[str, bool]:
    data = str(value or "").encode("utf-8", errors="replace")
    if len(data) <= max_bytes:
        return str(value or ""), False
    return data[:max_bytes].decode("utf-8", errors="replace"), True


def _normalize_changed_paths(stdout: str) -> List[str]:
    paths: List[str] = []
    for raw in str(stdout or "").splitlines():
        path = raw.replace("\\", "/").strip().strip("/")
        if path and _safe_repo_path(path):
            paths.append(path)
    return _dedupe(paths)


def _safe_repo_path(path: str) -> bool:
    if not path or path.startswith("/") or ":" in path or "\x00" in path:
        return False
    parts = [part for part in path.split("/") if part]
    return bool(parts) and ".." not in parts and all(part.strip(" .\t") for part in parts)


def _matches_any(path: str, patterns: Sequence[str]) -> bool:
    lowered = path.lower()
    for pattern in patterns:
        pat = str(pattern or "").replace("\\", "/").strip().lower()
        if pat and fnmatch.fnmatch(lowered, pat):
            return True
    return False


def _protected_path(path: str) -> bool:
    lowered = path.lower()
    basename = lowered.rsplit("/", 1)[-1]
    if basename.startswith(".env"):
        return True
    if any(fragment in lowered for fragment in DENIED_PATH_FRAGMENTS):
        return True
    return any(lowered.startswith(prefix.lower()) for prefix in PROTECTED_PATH_PREFIXES)


def _path_reasons(paths: Sequence[str], req: Mapping[str, Any]) -> List[str]:
    reasons: List[str] = []
    allowed = [str(item) for item in _list(req.get("allowed_path_patterns"))]
    forbidden = [str(item) for item in _list(req.get("forbidden_path_patterns"))]
    expected = {_normalize_expected_path(item) for item in _list(req.get("expected_changed_paths"))}
    expected.discard("")
    if expected and set(paths) != expected:
        reasons.append(FAIL_SCOPE_VIOLATION)
    for path in paths:
        if not _safe_repo_path(path):
            reasons.append(FAIL_SCOPE_VIOLATION)
        if allowed and not _matches_any(path, allowed):
            reasons.append(FAIL_SCOPE_VIOLATION)
        if forbidden and _matches_any(path, forbidden):
            reasons.append(FAIL_SCOPE_VIOLATION)
        if _protected_path(path) and not (
            _is_digest(req.get("protected_surface_authorization_digest"))
            and _is_digest(req.get("consensus_receipt_digest"))
        ):
            reasons.append(FAIL_PROTECTED_SURFACE)
    return reasons


def _normalize_expected_path(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip().strip("/")


def _diff_contains_secret(diff_text: str) -> bool:
    lower = str(diff_text or "").lower()
    return any(marker in lower for marker in SECRET_MARKERS)


def _added_lines(diff_text: str) -> List[str]:
    lines: List[str] = []
    for line in str(diff_text or "").splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            lines.append(line[1:])
    return lines


def _terminal_reasons(reasons: Sequence[str]) -> bool:
    blocked = {
        FAIL_EXPLICIT_REQUEST,
        FAIL_REPO_ROOT,
        FAIL_WORKTREE,
        FAIL_WORKTREE_INSIDE_REPO,
        FAIL_OPERATION_CWD,
        FAIL_SHA,
        FAIL_HEAD_MISMATCH,
        FAIL_DIFF_EVIDENCE,
        FAIL_SCOPE_VIOLATION,
        FAIL_PROTECTED_SURFACE,
        FAIL_SECRET_IN_DIFF,
        FAIL_HOLOINDEX_EVIDENCE,
        FAIL_RUNNER_EXCEPTION,
    }
    return any(reason in blocked for reason in reasons)


def _bounded_timeout(value: Any) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = DEFAULT_TIMEOUT_S
    return max(1, min(parsed, 300))


def _allowed_check_argv(value: Any) -> bool:
    if not isinstance(value, list) or not value or len(value) > MAX_ARGV:
        return False
    argv = [str(item) for item in value]
    if any((not item or "\x00" in item or "\n" in item or "\r" in item) for item in argv):
        return False
    first = argv[0].lower()
    if first in {"python", "python3", "py"}:
        return len(argv) >= 3 and argv[1] == "-m" and argv[2] in {"pytest", "ruff", "mypy"}
    if first in {"pytest", "ruff", "mypy"}:
        return True
    return False


def _command_record(name: str, argv: Sequence[str], result: CommandResult) -> Dict[str, Any]:
    return {
        "name": str(name or ""),
        "argv_digest": _digest(list(argv)),
        "returncode": result.returncode,
        "stdout_digest": _digest(result.stdout),
        "stderr_digest": _digest(result.stderr),
        "duration_ms": result.duration_ms,
        "timed_out": result.timed_out,
        "stdout_truncated": result.stdout_truncated,
        "stderr_truncated": result.stderr_truncated,
    }


__all__ = [
    "CommandResult",
    "EVIDENCE_PRODUCER_ACCEPT",
    "EVIDENCE_PRODUCER_REJECT",
    "EvidenceCommandRunner",
    "IndependentEvidenceProducerResult",
    "SubprocessEvidenceCommandRunner",
    "produce_independent_slice_evidence",
]
