"""Adversarial tests for bounded RedDog maintenance child diagnostics."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from holo_index.repository_state import RepositoryState
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_maintenance_handshake as handshake,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_process_image import (
    prove_current_process_executable,
)


def _state() -> RepositoryState:
    return RepositoryState(
        head_sha="a" * 40,
        clean=True,
        state_digest="sha256:state",
        error="",
    )


def _runtime_executable() -> str:
    return str(prove_current_process_executable().path)


def _trusted_runtime_root(tmp_path: Path) -> Path:
    """Create the minimal exact virtualenv proof required by the handshake."""

    root = tmp_path / "runtime"
    site_packages = root / ".venv" / "Lib" / "site-packages"
    site_packages.mkdir(parents=True)
    base = Path(getattr(sys, "_base_executable", sys.executable)).resolve()
    (root / ".venv" / "pyvenv.cfg").write_text(
        "\n".join(
            (
                f"home = {base.parent}",
                "include-system-site-packages = false",
                f"version = {sys.version.split()[0]}",
                f"executable = {base}",
            )
        ),
        encoding="utf-8",
    )
    return root


def _failed_refresh(tmp_path: Path, monkeypatch, runner):
    monkeypatch.setattr(handshake, "read_repository_state", lambda _root: _state())
    monkeypatch.setattr(
        handshake.owner_bootstrap, "cleanup_reddog_holoindex_owner", lambda: None
    )
    return handshake.ensure_reddog_holoindex_operational(
        repo_root=tmp_path,
        owner_runtime_root=_trusted_runtime_root(tmp_path),
        requested=True,
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        runner=runner,
    )


def _process_exists(pid: int) -> bool:
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, shell=False, timeout=1, check=False,
        )
        return f'"{pid}"' in result.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _wait_process_absent(pid: int) -> bool:
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        if not _process_exists(pid):
            return True
        time.sleep(0.02)
    return not _process_exists(pid)


def _refresh_reader_alive() -> bool:
    return any(
        thread.name == "reddog-holo-refresh-output" and thread.is_alive()
        for thread in threading.enumerate()
    )


def _wait_reader_absent() -> bool:
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if not _refresh_reader_alive():
            return True
        time.sleep(0.02)
    return not _refresh_reader_alive()


def _kill_exact_pid(pid: int, *, windows_runner=subprocess.run) -> None:
    if not _process_exists(pid):
        return
    if os.name == "nt":
        windows_runner(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            timeout=2,
            check=False,
        )
        return
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _run_descendant_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    escaped_session: bool = False,
):
    pid_file = tmp_path / "refresh-pids.txt"
    session_option = ",start_new_session=True" if escaped_session else ""
    child = (
        "import os,subprocess,sys,time; from pathlib import Path; "
        "desc=subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(15)']"
        f"{session_option}); "
        f"Path({str(pid_file)!r}).write_text(f'{{os.getpid()}},{{desc.pid}}'); "
        "time.sleep(15)"
    )
    real_popen = subprocess.Popen
    opened = []

    def recording_popen(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        opened.append(process)
        return process

    monkeypatch.setattr(subprocess, "Popen", recording_popen)
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        handshake._bounded_refresh_runner(
            [_runtime_executable(), "-B", "-c", child],
            cwd=str(tmp_path),
            env=os.environ.copy(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=False,
            timeout=0.75,
            check=False,
        )
    elapsed = time.monotonic() - started
    readiness_deadline = time.monotonic() + 2.0
    while not pid_file.exists() and time.monotonic() < readiness_deadline:
        time.sleep(0.01)
    assert pid_file.exists(), "refresh fixture did not publish process identities"
    direct_pid, descendant_pid = map(int, pid_file.read_text().split(","))
    return elapsed, opened[0], direct_pid, descendant_pid


def test_nonzero_refresh_propagates_only_allowlisted_final_child_error(
    tmp_path: Path, monkeypatch
) -> None:
    secret = "should-never-cross-parent-boundary"
    child_stdout = (
        f"arbitrary log containing {secret}\n"
        f'{{"detail":"path and {secret}",'
        '"error":"HOLOINDEX_REPOSITORY_DIRTY","ok":false}\n'
    ).encode()

    result = _failed_refresh(
        tmp_path,
        monkeypatch,
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=4,
            stdout=child_stdout,
        ),
    )

    assert result.ready is False
    assert result.error == "HOLOINDEX_REPOSITORY_DIRTY"
    assert secret not in repr(result)


@pytest.mark.parametrize(
    "completed",
    [
        SimpleNamespace(returncode=4, stdout=b"free text only\n"),
        SimpleNamespace(returncode=4, stdout=b"{malformed-json}\n"),
        SimpleNamespace(
            returncode=4,
            stdout=b'{"error":"HOLOINDEX_FORGED_ERROR","ok":false}\n',
        ),
        SimpleNamespace(
            returncode=4,
            stdout=b'{"error":"HOLOINDEX_REPOSITORY_DIRTY","extra":1,"ok":false}\n',
        ),
        SimpleNamespace(
            returncode=4,
            stdout=(
                b'{"error":"HOLOINDEX_FORGED_ERROR",'
                b'"error":"HOLOINDEX_REPOSITORY_DIRTY","ok":false}\n'
            ),
        ),
        SimpleNamespace(
            returncode=4,
            stdout=b'{"error":"HOLOINDEX_REPOSITORY_DIRTY","ok":false}\n',
            output_oversized=True,
        ),
    ],
    ids=(
        "free-text",
        "malformed",
        "forged",
        "extra-schema",
        "duplicate-key",
        "oversized",
    ),
)
def test_untrusted_refresh_diagnostics_fall_back_to_generic(
    tmp_path: Path, monkeypatch, completed
) -> None:
    result = _failed_refresh(
        tmp_path,
        monkeypatch,
        lambda *_args, **_kwargs: completed,
    )

    assert result.ready is False
    assert result.error == handshake.REFRESH_FAILED_ERROR


def test_refresh_timeout_remains_stable_and_secret_free(tmp_path: Path, monkeypatch) -> None:
    def timeout_runner(command, **_kwargs):
        raise subprocess.TimeoutExpired(command, timeout=1, output=b"secret")

    result = _failed_refresh(tmp_path, monkeypatch, timeout_runner)

    assert result.error == handshake.REFRESH_TIMEOUT_ERROR
    assert "secret" not in repr(result)


def test_default_refresh_runner_bounds_retained_stdout(tmp_path: Path) -> None:
    completed = handshake._bounded_refresh_runner(
        [
            _runtime_executable(), "-B",
            "-c",
            f"import sys; sys.stdout.buffer.write(b'x' * "
            f"{handshake._REFRESH_STDOUT_MAX_BYTES + 1})",
        ],
        cwd=str(tmp_path),
        env=os.environ.copy(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        shell=False,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.output_oversized is True
    assert len(completed.stdout) == handshake._REFRESH_STDOUT_MAX_BYTES


def test_timeout_kills_descendant_and_releases_reader_pipe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid_file = tmp_path / "refresh-pids.txt"
    child = (
        "import os,subprocess,sys,time; from pathlib import Path; "
        "desc=subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(5)']); "
        f"Path({str(pid_file)!r}).write_text(f'{{os.getpid()}},{{desc.pid}}'); "
        "time.sleep(5)"
    )
    real_popen = subprocess.Popen
    opened = []

    def recording_popen(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        opened.append(process)
        return process

    monkeypatch.setattr(subprocess, "Popen", recording_popen)
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        handshake._bounded_refresh_runner(
            [_runtime_executable(), "-B", "-c", child],
            cwd=str(tmp_path),
            env=os.environ.copy(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=False,
            timeout=0.5,
            check=False,
        )
    elapsed = time.monotonic() - started
    script_pid, descendant_pid = map(int, pid_file.read_text().split(","))
    refresh_process = opened[0]

    assert elapsed < 2.0
    assert refresh_process.poll() is not None
    assert refresh_process.stdout is not None and refresh_process.stdout.closed
    assert _wait_process_absent(refresh_process.pid)
    assert _wait_process_absent(script_pid)
    assert _wait_process_absent(descendant_pid)
    assert not _refresh_reader_alive()


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object contract")
def test_windows_job_bounds_tree_without_external_taskkill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_run = subprocess.run

    def intercepted_run(command, **kwargs):
        if command and command[0] == "taskkill":
            raise AssertionError("bounded cleanup must not resolve ambient taskkill")
        return real_run(command, **kwargs)

    assert not _refresh_reader_alive()
    monkeypatch.setattr(subprocess, "run", intercepted_run)
    elapsed, refresh_process, script_pid, descendant_pid = _run_descendant_timeout(
        tmp_path, monkeypatch
    )
    try:
        assert elapsed < 3.5
        assert refresh_process.poll() is not None
        assert _wait_process_absent(refresh_process.pid)
        assert _wait_process_absent(script_pid)
        assert _wait_process_absent(descendant_pid)
        assert _wait_reader_absent()
        assert refresh_process.stdout is not None and refresh_process.stdout.closed
    finally:
        monkeypatch.setattr(subprocess, "run", real_run)
        _kill_exact_pid(descendant_pid, windows_runner=real_run)
        _kill_exact_pid(script_pid, windows_runner=real_run)
        _kill_exact_pid(refresh_process.pid, windows_runner=real_run)

    assert _wait_process_absent(script_pid)
    assert _wait_process_absent(descendant_pid)
    assert _wait_reader_absent()
    assert refresh_process.stdout.closed


@pytest.mark.skipif(os.name == "nt", reason="POSIX new-session escape contract")
def test_posix_new_session_descendant_outlives_group_kill_until_exact_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert not _refresh_reader_alive()
    elapsed, refresh_process, direct_pid, descendant_pid = _run_descendant_timeout(
        tmp_path, monkeypatch, escaped_session=True
    )
    try:
        assert elapsed < 2.0
        assert refresh_process.poll() is not None
        assert _wait_process_absent(direct_pid)
        assert _process_exists(descendant_pid)
        assert refresh_process.stdout is not None
        assert not refresh_process.stdout.closed
        assert _refresh_reader_alive()
    finally:
        _kill_exact_pid(descendant_pid)
        _kill_exact_pid(direct_pid)

    assert _wait_process_absent(descendant_pid)
    assert _wait_reader_absent()
    assert refresh_process.stdout.closed
