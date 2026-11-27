"""Focused and adversarial tests for the WRE worktree registry guard."""

from __future__ import annotations

import ast
import json
import os
from dataclasses import replace
from pathlib import Path

import pytest

from modules.infrastructure.wre_core.src.wre_worktree_registry_guard import (
    CommandResult,
    FAIL_CWD_DEVICE_PREFIX,
    FAIL_CWD_PATH_AMBIGUOUS,
    FAIL_DETACHED_WORKTREE_MUTATION,
    FAIL_GIT_PROOF_UNAVAILABLE,
    FAIL_HEAD_MISMATCH,
    FAIL_INTENDED_WORKTREE_MISMATCH,
    FAIL_MALFORMED_WORKTREE_PORCELAIN,
    FAIL_PROCESS_LIVENESS_UNAVAILABLE,
    FAIL_RECEIPT_INVALID,
    FAIL_SHARED_MAIN_MUTATION,
    STATUS_PASS,
    STATUS_REJECT,
    STATUS_WARN,
    SubprocessWorktreeRegistryCommandRunner,
    WORKTREE_MUTATION_ADMISSION_PASS,
    audit_worktree_registry,
    validate_worktree_mutation_admission,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "infrastructure"
    / "wre_core"
    / "src"
    / "wre_worktree_registry_guard.py"
)
HEAD_MAIN = "a" * 40
HEAD_WORKER = "b" * 40


class FakeRunner:
    def __init__(
        self,
        *,
        common_dir: Path,
        owning_worktree: Path,
        head: str,
        porcelain: str,
        status: str = "",
        fail_command: tuple[str, ...] | None = None,
    ) -> None:
        self.common_dir = common_dir
        self.owning_worktree = owning_worktree
        self.head = head
        self.porcelain = porcelain
        self.status = status
        self.fail_command = fail_command
        self.calls: list[tuple[tuple[str, ...], Path, int]] = []

    def run(self, argv, *, cwd: Path, timeout_s: int) -> CommandResult:
        key = tuple(str(item) for item in argv)
        self.calls.append((key, cwd, timeout_s))
        if key == self.fail_command:
            return CommandResult(1, "", "injected failure")
        outputs = {
            ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"): str(self.common_dir),
            ("git", "rev-parse", "--show-toplevel"): str(self.owning_worktree),
            ("git", "rev-parse", "--verify", "HEAD"): self.head,
            (
                "git",
                "--no-optional-locks",
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
            ): self.status,
            ("git", "worktree", "list", "--porcelain"): self.porcelain,
        }
        if key not in outputs:
            raise AssertionError(f"unexpected argv: {key!r}")
        return CommandResult(0, outputs[key])


def _record(
    path: Path,
    *,
    head: str,
    branch: str | None = None,
    detached: bool = False,
    locked: str | None = None,
    prunable: str | None = None,
) -> str:
    lines = [f"worktree {path}", f"HEAD {head}"]
    if detached:
        lines.append("detached")
    else:
        lines.append(f"branch {branch}")
    if locked is not None:
        lines.append("locked" + (f" {locked}" if locked else ""))
    if prunable is not None:
        lines.append("prunable" + (f" {prunable}" if prunable else ""))
    return "\n".join(lines) + "\n\n"


def _layout(tmp_path: Path) -> tuple[Path, Path, Path]:
    shared = tmp_path / "shared-main"
    worker = tmp_path / "worker"
    common = shared / ".git"
    common.mkdir(parents=True)
    worker.mkdir()
    return shared, worker, common


def _isolated_runner(
    tmp_path: Path,
    *,
    status: str = "",
    extra_records: str = "",
    owner_branch: str | None = "refs/heads/feat/worker",
    owner_detached: bool = False,
    owner_locked: str | None = None,
) -> tuple[Path, Path, FakeRunner]:
    shared, worker, common = _layout(tmp_path)
    porcelain = _record(shared, head=HEAD_MAIN, branch="refs/heads/main")
    porcelain += _record(
        worker,
        head=HEAD_WORKER,
        branch=owner_branch,
        detached=owner_detached,
        locked=owner_locked,
    )
    porcelain += extra_records
    return shared, worker, FakeRunner(
        common_dir=common,
        owning_worktree=worker,
        head=HEAD_WORKER,
        porcelain=porcelain,
        status=status,
    )


def test_clean_isolated_worktree_audit_and_mutation_admission_pass(tmp_path: Path) -> None:
    _, worker, runner = _isolated_runner(tmp_path)

    receipt = audit_worktree_registry(cwd=worker, runner=runner, now=lambda: 1000)
    decision = validate_worktree_mutation_admission(
        receipt=receipt,
        intended_worktree_path=worker,
        now=lambda: 1001,
    )

    assert receipt.accepted is True
    assert receipt.status == STATUS_PASS
    assert receipt.registered_count == 2
    assert receipt.shared_main_indicator is False
    assert receipt.dirty is False
    assert receipt.dirty_state_digest.startswith("sha256:")
    assert decision.accepted is True
    assert decision.reason == WORKTREE_MUTATION_ADMISSION_PASS


def test_repeated_cwd_hazard_rejects_mutation_from_shared_main(tmp_path: Path) -> None:
    shared, worker, common = _layout(tmp_path)
    porcelain = _record(shared, head=HEAD_MAIN, branch="refs/heads/main")
    porcelain += _record(worker, head=HEAD_WORKER, branch="refs/heads/feat/worker")
    runner = FakeRunner(
        common_dir=common,
        owning_worktree=shared,
        head=HEAD_MAIN,
        porcelain=porcelain,
    )

    receipt = audit_worktree_registry(cwd=shared, runner=runner, now=lambda: 1000)
    decision = validate_worktree_mutation_admission(
        receipt=receipt,
        intended_worktree_path=worker,
        now=lambda: 1000,
    )

    assert receipt.accepted is True
    assert receipt.shared_main_indicator is True
    assert decision.accepted is False
    assert decision.reason == FAIL_SHARED_MAIN_MUTATION


def test_primary_shared_checkout_is_rejected_even_on_feature_branch(tmp_path: Path) -> None:
    shared, worker, common = _layout(tmp_path)
    porcelain = _record(shared, head=HEAD_MAIN, branch="refs/heads/feat/shared-root")
    porcelain += _record(worker, head=HEAD_WORKER, branch="refs/heads/feat/worker")
    runner = FakeRunner(
        common_dir=common,
        owning_worktree=shared,
        head=HEAD_MAIN,
        porcelain=porcelain,
    )

    receipt = audit_worktree_registry(cwd=shared, runner=runner, now=lambda: 1000)
    decision = validate_worktree_mutation_admission(
        receipt=receipt,
        intended_worktree_path=shared,
        now=lambda: 1000,
    )

    assert receipt.shared_main_indicator is True
    assert decision.reason == FAIL_SHARED_MAIN_MUTATION


def test_dirty_shared_main_rejects_without_exposing_dirty_paths(tmp_path: Path) -> None:
    shared, _, common = _layout(tmp_path)
    porcelain = _record(shared, head=HEAD_MAIN, branch="refs/heads/main")
    dirty_status = " M modules/private/secret.py\x00?? credentials.txt\x00"
    runner = FakeRunner(
        common_dir=common,
        owning_worktree=shared,
        head=HEAD_MAIN,
        porcelain=porcelain,
        status=dirty_status,
    )

    receipt = audit_worktree_registry(cwd=shared, runner=runner, now=lambda: 1000)
    serialized = json.dumps(receipt.to_dict(), sort_keys=True)
    decision = validate_worktree_mutation_admission(
        receipt=receipt,
        intended_worktree_path=shared,
        now=lambda: 1000,
    )

    assert receipt.dirty is True
    assert "secret.py" not in serialized
    assert "credentials.txt" not in serialized
    assert decision.reason == FAIL_SHARED_MAIN_MUTATION


def test_dead_pid_lock_is_a_stale_remediation_candidate(tmp_path: Path) -> None:
    stale = tmp_path / "stale-worker"
    stale.mkdir()
    extra = _record(
        stale,
        head="c" * 40,
        branch="refs/heads/feat/stale",
        locked="worker claim (pid 4242)",
    )
    _, worker, runner = _isolated_runner(tmp_path, extra_records=extra)

    receipt = audit_worktree_registry(
        cwd=worker,
        runner=runner,
        process_is_alive=lambda pid: False,
        now=lambda: 1000,
    )

    assert receipt.accepted is True
    assert receipt.status == STATUS_WARN
    assert receipt.locked_count == 1
    assert receipt.stale_count == 1
    assert len(receipt.stale_lock_candidates) == 1
    assert receipt.stale_lock_candidates[0].pid == 4242
    assert receipt.stale_lock_candidates[0].classification == "dead_pid"
    assert receipt.no_cleanup_performed is True


def test_live_lock_is_retained_and_not_classified_stale(tmp_path: Path) -> None:
    live = tmp_path / "live-worker"
    live.mkdir()
    extra = _record(
        live,
        head="c" * 40,
        branch="refs/heads/feat/live",
        locked="worker claim (pid 101)",
    )
    _, worker, runner = _isolated_runner(tmp_path, extra_records=extra)

    receipt = audit_worktree_registry(
        cwd=worker,
        runner=runner,
        process_is_alive=lambda pid: True,
        now=lambda: 1000,
    )

    assert receipt.locked_count == 1
    assert receipt.stale_count == 0
    assert receipt.stale_lock_candidates == ()


def test_stale_lock_candidates_are_bounded_without_losing_total(tmp_path: Path) -> None:
    records = []
    for index in range(40):
        stale = tmp_path / f"stale-{index:02d}"
        stale.mkdir()
        records.append(
            _record(
                stale,
                head=f"{index + 1:040x}",
                branch=f"refs/heads/feat/stale-{index:02d}",
                locked=f"worker claim (pid {5000 + index})",
            )
        )
    _, worker, runner = _isolated_runner(tmp_path / "layout", extra_records="".join(records))

    receipt = audit_worktree_registry(
        cwd=worker,
        runner=runner,
        process_is_alive=lambda pid: False,
        now=lambda: 1000,
    )

    assert receipt.stale_count == 40
    assert len(receipt.stale_lock_candidates) == 32
    assert receipt.stale_lock_candidates_truncated is True


def test_process_liveness_failure_rejects_stale_lock_claim(tmp_path: Path) -> None:
    locked = tmp_path / "locked-worker"
    locked.mkdir()
    extra = _record(
        locked,
        head="c" * 40,
        branch="refs/heads/feat/locked",
        locked="worker claim (pid 8080)",
    )
    _, worker, runner = _isolated_runner(tmp_path / "layout", extra_records=extra)

    def unavailable(pid: int) -> bool:
        raise OSError(f"cannot inspect {pid}")

    receipt = audit_worktree_registry(
        cwd=worker,
        runner=runner,
        process_is_alive=unavailable,
        now=lambda: 1000,
    )

    assert receipt.accepted is False
    assert receipt.reasons == (FAIL_PROCESS_LIVENESS_UNAVAILABLE,)


def test_detached_worktree_is_counted_and_owner_mutation_fails_closed(tmp_path: Path) -> None:
    _, worker, runner = _isolated_runner(
        tmp_path,
        owner_branch=None,
        owner_detached=True,
    )

    receipt = audit_worktree_registry(cwd=worker, runner=runner, now=lambda: 1000)
    decision = validate_worktree_mutation_admission(
        receipt=receipt,
        intended_worktree_path=worker,
        now=lambda: 1000,
    )

    assert receipt.detached_count == 1
    assert receipt.status == STATUS_WARN
    assert decision.accepted is False
    assert decision.reason == FAIL_DETACHED_WORKTREE_MUTATION


def test_intended_worktree_must_equal_git_owned_worktree(tmp_path: Path) -> None:
    _, worker, runner = _isolated_runner(tmp_path)
    other = tmp_path / "other-worker"
    other.mkdir()
    receipt = audit_worktree_registry(cwd=worker, runner=runner, now=lambda: 1000)

    decision = validate_worktree_mutation_admission(
        receipt=receipt,
        intended_worktree_path=other,
        now=lambda: 1000,
    )

    assert decision.accepted is False
    assert decision.reason == FAIL_INTENDED_WORKTREE_MISMATCH


@pytest.mark.parametrize(
    "malformed",
    [
        "HEAD " + HEAD_MAIN + "\nbranch refs/heads/main\n\n",
        "worktree relative/path\nHEAD " + HEAD_MAIN + "\nbranch refs/heads/main\n\n",
        "worktree C:/repo\nHEAD not-a-head\nbranch refs/heads/main\n\n",
        "worktree C:/repo\nHEAD " + HEAD_MAIN + "\nunknown field\n\n",
    ],
)
def test_malformed_porcelain_fails_closed(tmp_path: Path, malformed: str) -> None:
    _, worker, common = _layout(tmp_path)
    runner = FakeRunner(
        common_dir=common,
        owning_worktree=worker,
        head=HEAD_WORKER,
        porcelain=malformed,
    )

    receipt = audit_worktree_registry(cwd=worker, runner=runner, now=lambda: 1000)

    assert receipt.accepted is False
    assert receipt.status == STATUS_REJECT
    assert receipt.reasons == (FAIL_MALFORMED_WORKTREE_PORCELAIN,)


def test_head_mismatch_fails_closed(tmp_path: Path) -> None:
    _, worker, runner = _isolated_runner(tmp_path)
    runner.head = "d" * 40

    receipt = audit_worktree_registry(cwd=worker, runner=runner, now=lambda: 1000)

    assert receipt.accepted is False
    assert receipt.reasons == (FAIL_HEAD_MISMATCH,)


def test_failed_git_proof_command_fails_closed(tmp_path: Path) -> None:
    _, worker, runner = _isolated_runner(tmp_path)
    runner.fail_command = ("git", "rev-parse", "--show-toplevel")

    receipt = audit_worktree_registry(cwd=worker, runner=runner, now=lambda: 1000)

    assert receipt.accepted is False
    assert receipt.reasons == (FAIL_GIT_PROOF_UNAVAILABLE,)


def test_injected_probe_failure_cannot_escape_guard(tmp_path: Path) -> None:
    _, worker, runner = _isolated_runner(tmp_path)

    def broken_exists(path: Path) -> bool:
        raise OSError(f"cannot inspect {path}")

    receipt = audit_worktree_registry(
        cwd=worker,
        runner=runner,
        path_exists=broken_exists,
        now=lambda: 1000,
    )

    assert receipt.accepted is False
    assert receipt.reasons == (FAIL_GIT_PROOF_UNAVAILABLE,)


def test_device_prefix_fails_before_git() -> None:
    receipt = audit_worktree_registry(cwd=r"\\?\C:\repo", runner=None, now=lambda: 1000)
    assert receipt.accepted is False
    assert receipt.reasons == (FAIL_CWD_DEVICE_PREFIX,)


def test_symlink_alias_fails_before_git(tmp_path: Path) -> None:
    target = tmp_path / "target"
    alias = tmp_path / "alias"
    target.mkdir()
    try:
        alias.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks unavailable")
    _, _, runner = _isolated_runner(tmp_path / "layout")
    receipt = audit_worktree_registry(cwd=alias, runner=runner, now=lambda: 1000)
    assert receipt.accepted is False
    assert receipt.reasons == (FAIL_CWD_PATH_AMBIGUOUS,)
    assert runner.calls == []


def test_tampered_or_expired_receipt_is_rejected(tmp_path: Path) -> None:
    _, worker, runner = _isolated_runner(tmp_path)
    receipt = audit_worktree_registry(cwd=worker, runner=runner, now=lambda: 1000)

    tampered = replace(receipt, branch="refs/heads/main")
    tampered_decision = validate_worktree_mutation_admission(
        receipt=tampered,
        intended_worktree_path=worker,
        now=lambda: 1000,
    )
    expired_decision = validate_worktree_mutation_admission(
        receipt=receipt,
        intended_worktree_path=worker,
        now=lambda: 1031,
    )

    assert tampered_decision.reason == FAIL_RECEIPT_INVALID
    assert expired_decision.accepted is False


@pytest.mark.skipif(os.name != "nt", reason="Windows case-folding behavior")
def test_windows_path_case_does_not_break_exact_owner_binding(tmp_path: Path) -> None:
    _, worker, runner = _isolated_runner(tmp_path)
    receipt = audit_worktree_registry(cwd=worker, runner=runner, now=lambda: 1000)

    decision = validate_worktree_mutation_admission(
        receipt=receipt,
        intended_worktree_path=Path(str(worker).upper()),
        now=lambda: 1000,
    )

    assert decision.accepted is True


def test_runner_receives_only_bounded_readonly_git_argv(tmp_path: Path) -> None:
    _, worker, runner = _isolated_runner(tmp_path)

    receipt = audit_worktree_registry(cwd=worker, runner=runner, now=lambda: 1000)

    assert receipt.accepted is True
    commands = [call[0] for call in runner.calls]
    assert commands == [
        ("git", "rev-parse", "--path-format=absolute", "--git-common-dir"),
        ("git", "rev-parse", "--show-toplevel"),
        ("git", "rev-parse", "--verify", "HEAD"),
        (
            "git",
            "--no-optional-locks",
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        ),
        ("git", "worktree", "list", "--porcelain"),
    ]
    destructive = {"add", "commit", "push", "prune", "remove", "unlock", "move", "reset", "checkout"}
    assert not any(token.lower() in destructive for command in commands for token in command)


def test_production_runner_rejects_destructive_argv_before_subprocess(tmp_path: Path) -> None:
    runner = SubprocessWorktreeRegistryCommandRunner()

    with pytest.raises(ValueError, match="read-only allowlist"):
        runner.run(("git", "worktree", "prune"), cwd=tmp_path, timeout_s=1)


def test_source_has_no_shell_true_or_cleanup_primitives() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {"shutil"}
    banned_path_calls = {"unlink", "rmdir", "rename", "replace", "write_text", "write_bytes", "open"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in banned_path_calls:
                raise AssertionError(f"cleanup/write primitive present: {node.func.attr}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
            raise AssertionError("file open is forbidden")

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "run":
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                shell_keywords = [kw for kw in node.keywords if kw.arg == "shell"]
                assert len(shell_keywords) == 1
                assert isinstance(shell_keywords[0].value, ast.Constant)
                assert shell_keywords[0].value.value is False
