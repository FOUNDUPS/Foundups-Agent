"""Explicit, bounded LM Studio server startup; never load or unload models."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
    lm_studio_node_lock_identity,
)
from modules.infrastructure.shared_utilities.lm_studio_native_transport import (
    LMStudioResidencyState,
    inspect_lm_studio_model,
    normalize_lm_studio_base_url,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)

_SERVER_PROBE_KEY = "__foundups_server_reachability_probe__"
_COMMAND_TIMEOUT = 30
_WAIT_SECONDS = 30
_LOCK_WAIT_SECONDS = 2.0


def resolve_lms_cli_path() -> str | None:
    """Resolve an explicit CLI or the existing PATH/per-user installation."""
    explicit = os.getenv("LMS_CLI_PATH")
    candidates = [explicit] if explicit else [
        shutil.which("lms"),
        shutil.which("lms.exe"),
        str(Path.home() / ".lmstudio" / "bin" / "lms.exe"),
    ]
    return next((str(Path(p)) for p in candidates if p and Path(p).is_file()), None)


def observe_processes() -> tuple[bool | None, bool | None]:
    """Return (GUI, llmster); incomplete observation is explicitly unknown."""
    gui = daemon = False
    try:
        import psutil

        for process in psutil.process_iter(["name"]):
            name = process.info.get("name")
            if not isinstance(name, str) or not name.strip():
                return None, None
            name = name.casefold()
            gui |= name in {"lm studio", "lm studio.exe"}
            daemon |= name in {"llmster", "llmster.exe"}
    except Exception:
        return None, None
    return gui, daemon


def _observe(root: str, model_key: str | None, timeout: float = 1.0):
    return inspect_lm_studio_model(
        model_key if model_key is not None else _SERVER_PROBE_KEY,
        base_url=root,
        timeout=timeout,
    )


def _readiness(state, model_key: str | None) -> tuple[bool, str]:
    if model_key is None:
        return True, "LM Studio native server reachable (model readiness not requested)"
    if state.model_key != model_key:
        return False, "LM Studio selected model identity mismatch"
    if state.state is LMStudioResidencyState.RESIDENT:
        if len(state.loaded_instances) == 1:
            return True, "LM Studio native server and exact selected model ready"
        return False, "LM Studio selected model has ambiguous resident instances"
    return False, "LM Studio server reachable; selected model not resident; load it explicitly"


def is_server_reachable(port: int) -> bool:
    """Observe native HTTP only; no process discovery or lifecycle action."""
    try:
        root = _server_root(port)
        return _observe(root, None).state is not LMStudioResidencyState.SERVER_UNREACHABLE
    except Exception:
        return False


def _server_root(port: int) -> str:
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("lm_studio_port_invalid")
    return normalize_lm_studio_base_url(f"http://127.0.0.1:{port}")


def launch_model_server(
    *, port: int, model_key: str | None, lms_cli: str | None,
    gui_path: str | None, prefer_headless: bool = True,
) -> tuple[bool, str]:
    """Serialize participating startup/model owners; borrow existing residency.

    External GUI launches do not participate in this lock. Fresh observations
    reduce races but do not establish exclusion against unrelated operators.
    """
    try:
        root = _server_root(port)
        if model_key is not None and (
            not isinstance(model_key, str) or not model_key.strip()
        ):
            raise ValueError("lm_studio_model_key_invalid")
        with runtime_operation_lock(
            lm_studio_node_lock_identity(root), timeout_seconds=_LOCK_WAIT_SECONDS
        ):
            state = _observe(root, model_key)
            if state.state is not LMStudioResidencyState.SERVER_UNREACHABLE:
                return _readiness(state, model_key)
            return _start_unreachable(root, port, model_key, lms_cli, gui_path, prefer_headless)
    except TimeoutError:
        return False, "LM Studio startup/model operation busy or timed out; no alternate launch"
    except Exception as exc:
        return False, f"LM Studio startup not ready ({type(exc).__name__}); inspect local configuration"


def _start_unreachable(root, port, model_key, cli, gui_path, prefer_headless):
    from .dae_dependencies import is_port_open

    if is_port_open(port):
        return False, "LM Studio port occupied without valid native HTTP; no launch"
    processes = observe_processes()
    if None in processes or processes == (True, True):
        return False, "LM Studio process state unknown or conflicting; no launch"
    if not cli:
        return False, "lms CLI required for explicit loopback server startup; start manually"
    if processes != (False, False):
        return _start_http(root, port, model_key, cli, processes)
    if observe_processes() != (False, False):
        return False, "LM Studio process state changed before launch; retry observation"
    if prefer_headless or not gui_path:
        if not _run_cli(cli, ["daemon", "up"]):
            return False, "llmster daemon command failed; no GUI fallback"
        return _start_http(root, port, model_key, cli, (False, True))
    return False, "Cold GUI launch is not qualified for loopback binding; start manually then retry"


def _run_cli(cli: str, arguments: list[str]) -> bool:
    completed = subprocess.run(
        [cli, *arguments], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=_COMMAND_TIMEOUT, check=False, shell=False,
    )
    return completed.returncode == 0


def _start_http(root, port, model_key, cli, expected):
    if observe_processes() != expected:
        return False, "LM Studio process state changed before server command; no alternate launch"
    if not _run_cli(cli, ["server", "start", "--bind", "127.0.0.1", "--port", str(port)]):
        return False, "LM Studio server command failed; no alternate launch"
    deadline = time.monotonic() + _WAIT_SECONDS
    for _ in range(_WAIT_SECONDS):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        state = _observe(root, model_key, timeout=min(1.0, remaining))
        if state.state is not LMStudioResidencyState.SERVER_UNREACHABLE:
            return _readiness(state, model_key)
        time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
    return False, "LM Studio server command completed but native API not ready"
