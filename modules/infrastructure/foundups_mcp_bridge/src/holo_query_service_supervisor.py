"""Host lifecycle boundary for the private HoloIndex query owner.

The supervisor is intentionally separate from RedDog. A trusted host bootstrap
starts the owner, verifies its authenticated loopback health contract, and
retains its URL/token in a process-private handoff resolved by the adapter.
"""

from __future__ import annotations

import atexit
import http.client
import ipaddress
import json
import math
import os
import secrets
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .holo_query_service import DEFAULT_STARTUP_WARMUP_TIMEOUT_SECONDS
from .holo_query_owner_startup import OwnerStartupSettings, await_owner_startup
from .reddog_sealed_holo_runtime import (
    scrub_holo_child_environment,
    sealed_holo_command,
    sealed_runtime_required,
    trusted_holo_site_packages,
)

OWNER_MODULE = (
    "modules.infrastructure.foundups_mcp_bridge.src.holo_query_service"
)
OWNER_HOST = "127.0.0.1"
DEFAULT_OWNER_PORT = 8127
HEALTH_PATH = "/holoindex/v1/health"
SERVICE_URL_ENV = "HOLOINDEX_QUERY_SERVICE_URL"
SERVICE_TOKEN_ENV = "HOLOINDEX_QUERY_SERVICE_TOKEN"
SSD_PATH_ENV = "HOLOINDEX_SSD_PATH"
HEALTH_SCHEMA_VERSION = "holoindex_query_service.v1"
MAX_HEALTH_RESPONSE_BYTES = 65_536
TOKEN_ENTROPY_BYTES = 48
DEFAULT_OWNER_STARTUP_TIMEOUT_SECONDS = 300.0
DEFAULT_OWNER_PROBE_TIMEOUT_SECONDS = 30.0
DEFAULT_OWNER_STARTUP_PROBE_TIMEOUT_SECONDS = (
    DEFAULT_STARTUP_WARMUP_TIMEOUT_SECONDS
)
DEFAULT_OWNER_PROBE_INTERVAL_SECONDS = 0.5
PORT_IN_USE_ERROR = "HOLOINDEX_QUERY_SERVICE_PORT_IN_USE"
BINDING_MISMATCH_ERROR = "HOLOINDEX_QUERY_SERVICE_BINDING_MISMATCH"
SEALED_RUNTIME_INVALID_ERROR = "HOLOINDEX_QUERY_SERVICE_SEALED_RUNTIME_INVALID"


class HoloQueryServiceSupervisorError(RuntimeError):
    """Stable, secret-free lifecycle failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class AuthenticatedOwnerHealthProof:
    """One authenticated health exchange and its actual owner binding."""

    ready: bool
    rejection: str
    binding: tuple[str, str, str, str]


def _probe_target_is_private(host: str, token: str) -> bool:
    try:
        address = ipaddress.ip_address(str(host or ""))
    except ValueError:
        return False
    return str(address) == OWNER_HOST and bool(token)


def _read_health_payload(
    connection: http.client.HTTPConnection,
    token: str,
) -> Mapping[str, object] | None:
    connection.request(
        "GET",
        HEALTH_PATH,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Connection": "close",
        },
    )
    response = connection.getresponse()
    body = response.read(MAX_HEALTH_RESPONSE_BYTES + 1)
    if response.status not in {200, 400, 409, 503, 504} or len(body) > MAX_HEALTH_RESPONSE_BYTES:
        return None
    payload = json.loads(body.decode("utf-8"))
    return payload if isinstance(payload, Mapping) else None


def _health_contract_ready(
    payload: Mapping[str, object],
    *,
    expected_repo_head_sha: str,
    expected_repo_root_digest: str,
    expected_generation_id: str,
    expected_receipt_digest: str,
) -> bool:
    repo_head_sha = str(payload.get("repo_head_sha") or "")
    repo_root_digest = str(payload.get("repo_root_digest") or "")
    generation_id = str(payload.get("freshness_generation_id") or "")
    receipt_digest = str(payload.get("freshness_receipt_digest") or "")
    contract_checks = (
        payload.get("schema_version") == HEALTH_SCHEMA_VERSION,
        payload.get("ok") is True,
        payload.get("source") == "holoindex",
        payload.get("status") == "ready",
        payload.get("loopback_only") is True,
        payload.get("freshness") == "CURRENT",
        not payload.get("error"),
        payload.get("stale_reasons") == [],
        payload.get("index_gap_detected") is False,
        payload.get("no_holoindex_reindex_performed") is True,
        payload.get("retrieval_mode") == "semantic",
        bool(repo_head_sha and repo_root_digest and generation_id and receipt_digest),
    )
    binding_checks = (
        not expected_repo_head_sha or repo_head_sha == expected_repo_head_sha,
        not expected_repo_root_digest
        or repo_root_digest == expected_repo_root_digest,
        not expected_generation_id or generation_id == expected_generation_id,
        not expected_receipt_digest or receipt_digest == expected_receipt_digest,
    )
    return all(contract_checks + binding_checks)


def _health_binding(payload: Mapping[str, object] | None) -> tuple[str, str, str, str]:
    value = payload if isinstance(payload, Mapping) else {}
    return (
        str(value.get("repo_head_sha") or ""),
        str(value.get("repo_root_digest") or ""),
        str(value.get("freshness_generation_id") or ""),
        str(value.get("freshness_receipt_digest") or ""),
    )


def _authenticated_health_exchange(
    *,
    host: str,
    port: int,
    token: str,
    timeout_seconds: float,
    expected_repo_head_sha: str = "",
    expected_repo_root_digest: str = "",
    expected_generation_id: str = "",
    expected_receipt_digest: str = "",
) -> AuthenticatedOwnerHealthProof:
    """Return one authenticated ready/rejection decision with actual binding."""
    unavailable = AuthenticatedOwnerHealthProof(False, "", ("", "", "", ""))
    if not _probe_target_is_private(host, token):
        return unavailable
    connection = http.client.HTTPConnection(
        host,
        int(port),
        timeout=max(0.01, float(timeout_seconds)),
    )
    try:
        payload = _read_health_payload(connection, token)
        binding = _health_binding(payload)
        if payload is not None and _health_contract_ready(
            payload,
            expected_repo_head_sha=expected_repo_head_sha,
            expected_repo_root_digest=expected_repo_root_digest,
            expected_generation_id=expected_generation_id,
            expected_receipt_digest=expected_receipt_digest,
        ):
            return AuthenticatedOwnerHealthProof(True, "", binding)
        rejection = _health_rejection_code(payload) or _health_binding_rejection_code(
            payload,
            expected_repo_head_sha=expected_repo_head_sha,
            expected_repo_root_digest=expected_repo_root_digest,
            expected_generation_id=expected_generation_id,
            expected_receipt_digest=expected_receipt_digest,
        )
        return AuthenticatedOwnerHealthProof(False, rejection, binding)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return unavailable
    finally:
        connection.close()


def _authenticated_health_probe(
    *,
    host: str,
    port: int,
    token: str,
    timeout_seconds: float,
    expected_repo_head_sha: str = "",
    expected_repo_root_digest: str = "",
    expected_generation_id: str = "",
    expected_receipt_digest: str = "",
) -> bool:
    """Compatibility wrapper for one exact authenticated owner-ready proof."""
    return _authenticated_health_exchange(
        host=host,
        port=port,
        token=token,
        timeout_seconds=timeout_seconds,
        expected_repo_head_sha=expected_repo_head_sha,
        expected_repo_root_digest=expected_repo_root_digest,
        expected_generation_id=expected_generation_id,
        expected_receipt_digest=expected_receipt_digest,
    ).ready


def _health_rejection_code(payload: Mapping[str, object] | None) -> str:
    """Expose only authenticated, terminal freshness failures during startup."""
    value = payload if isinstance(payload, Mapping) else {}
    error = str(value.get("error") or "")
    terminal = {
        "QUERY_OWNER_POISONED",
        "QUERY_TIMEOUT",
        "SEMANTIC_BACKEND_UNAVAILABLE",
        "SEMANTIC_CANARY_EMPTY",
        "MISSING_GENERATION_BINDING",
        "REPO_HEAD_MISMATCH",
        "STALE_INDEX",
        "GENERATION_CHANGED_DURING_QUERY",
    }
    valid = (
        value.get("schema_version") == HEALTH_SCHEMA_VERSION
        and value.get("ok") is False
        and value.get("source") == "holoindex"
        and value.get("loopback_only") is True
        and value.get("no_holoindex_reindex_performed") is True
    )
    return error if valid and error in terminal else ""


def _health_binding_rejection_code(
    payload: Mapping[str, object] | None,
    *,
    expected_repo_head_sha: str,
    expected_repo_root_digest: str,
    expected_generation_id: str,
    expected_receipt_digest: str,
) -> str:
    """Reject an authenticated ready owner that proves a different binding."""
    value = payload if isinstance(payload, Mapping) else {}
    if not _health_contract_ready(
        value,
        expected_repo_head_sha="",
        expected_repo_root_digest="",
        expected_generation_id="",
        expected_receipt_digest="",
    ):
        return ""
    actual = _health_binding(value)
    expected = (
        expected_repo_head_sha,
        expected_repo_root_digest,
        expected_generation_id,
        expected_receipt_digest,
    )
    return (
        BINDING_MISMATCH_ERROR
        if any(
            wanted and wanted != observed
            for wanted, observed in zip(expected, actual)
        )
        else ""
    )


def _authenticated_health_rejection(
    *,
    host: str,
    port: int,
    token: str,
    timeout_seconds: float,
    expected_repo_head_sha: str = "",
    expected_repo_root_digest: str = "",
    expected_generation_id: str = "",
    expected_receipt_digest: str = "",
) -> str:
    return _authenticated_health_exchange(
        host=host,
        port=port,
        token=token,
        timeout_seconds=timeout_seconds,
        expected_repo_head_sha=expected_repo_head_sha,
        expected_repo_root_digest=expected_repo_root_digest,
        expected_generation_id=expected_generation_id,
        expected_receipt_digest=expected_receipt_digest,
    ).rejection


def _hidden_process_options() -> dict[str, object]:
    """Build Windows no-window options without weakening other platforms."""
    if os.name != "nt":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return {
        "creationflags": subprocess.CREATE_NO_WINDOW,
        "startupinfo": startupinfo,
    }


def _owner_port_available(host: str, port: int) -> bool:
    """Prove the fixed loopback endpoint is free before expensive startup."""

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            probe.bind((host, int(port)))
    except OSError:
        return False
    return True


def _terminate_process(
    process: subprocess.Popen[bytes],
    *,
    timeout_seconds: float,
) -> None:
    """Bound termination without retaining any lifecycle secret state."""
    if process.poll() is not None:
        return
    try:
        process.terminate()
    except OSError:
        return
    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except OSError:
            return
        try:
            process.wait(timeout=timeout_seconds)
        except (OSError, subprocess.TimeoutExpired):
            return
    except OSError:
        return


def _owner_token() -> str:
    try:
        token = secrets.token_urlsafe(TOKEN_ENTROPY_BYTES)
    except Exception:
        raise HoloQueryServiceSupervisorError(
            "HOLOINDEX_QUERY_SERVICE_TOKEN_GENERATION_FAILED"
        ) from None
    if len(token) < 64:
        raise HoloQueryServiceSupervisorError(
            "HOLOINDEX_QUERY_SERVICE_TOKEN_GENERATION_FAILED"
        )
    return token


def _owner_python_runtime(
    python_executable: str,
    *,
    platform_name: str | None = None,
    current_executable: str | None = None,
    base_executable: str | None = None,
    current_prefix: str | None = None,
    base_prefix: str | None = None,
    site_packages_path: str | None = None,
) -> tuple[str, tuple[str, ...]]:
    """Avoid the transient Windows venv launcher in the parent watchdog chain."""

    platform = platform_name or os.name
    current = current_executable or sys.executable
    base = base_executable or str(getattr(sys, "_base_executable", "") or "")
    prefix = current_prefix or sys.prefix
    root_prefix = base_prefix or sys.base_prefix
    requested = os.path.normcase(os.path.abspath(python_executable))
    running = os.path.normcase(os.path.abspath(current))
    if (
        platform != "nt"
        or requested != running
        or os.path.normcase(prefix) == os.path.normcase(root_prefix)
        or not base
    ):
        return python_executable, ()
    prefix_path = Path(prefix).resolve(strict=False)
    site_path = Path(
        site_packages_path or (prefix_path / "Lib" / "site-packages")
    ).resolve(strict=False)
    if (
        not Path(base).is_file()
        or not site_path.is_dir()
        or not site_path.is_relative_to(prefix_path)
    ):
        return python_executable, ()
    return str(Path(base).resolve(strict=True)), (str(site_path),)


def _owner_environment(
    token: str,
    ssd_path: Path | None,
    pythonpath_entries: tuple[str, ...] = (),
) -> dict[str, str]:
    environment = scrub_holo_child_environment(os.environ)
    environment.update(
        {
            SERVICE_TOKEN_ENV: token,
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
        }
    )
    if ssd_path is not None:
        environment[SSD_PATH_ENV] = str(ssd_path)
    if pythonpath_entries:
        environment["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    return environment


def _resolved_owner_runtime(
    python_executable: str, runtime_root: Path
) -> tuple[str, tuple[str, ...]]:
    executable, entries = _owner_python_runtime(python_executable)
    if sealed_runtime_required(os.environ) or os.name != "nt":
        return executable, entries
    return executable, trusted_holo_site_packages(runtime_root, base_executable=executable)
def _owner_command(
    python_executable: str,
    port: int,
    parent_pid: int,
    *,
    repo_root: Path | str | None = None,
    environ: Mapping[str, str] | None = None,
) -> list[str]:
    env = os.environ if environ is None else environ
    if repo_root is not None:
        sealed = sealed_holo_command(
            environ=env,
            trusted_module_path=Path(__file__),
            target_repo_root=repo_root,
            entry_relative_path="scripts/reddog_holoindex_owner_service_once.py",
            script_args=(
                "--host", OWNER_HOST, "--port", str(port),
                "--parent-pid", str(parent_pid),
            ),
            python_executable=python_executable,
        )
        if sealed_runtime_required(env):
            return list(sealed or ())
    return [
        python_executable,
        *(("-S",) if os.name == "nt" else ()),
        "-B",
        "-m",
        OWNER_MODULE,
        "--host",
        OWNER_HOST,
        "--port",
        str(port),
        "--parent-pid",
        str(parent_pid),
    ]


class HoloQueryServiceSupervisor:
    """Own one authenticated loopback HoloIndex query-service process."""

    def __init__(
        self,
        *,
        repo_root: Path | str,
        ssd_path: Path | str | None = None,
        port: int = DEFAULT_OWNER_PORT,
        startup_timeout_seconds: float = DEFAULT_OWNER_STARTUP_TIMEOUT_SECONDS,
        probe_timeout_seconds: float = DEFAULT_OWNER_PROBE_TIMEOUT_SECONDS,
        probe_interval_seconds: float = DEFAULT_OWNER_PROBE_INTERVAL_SECONDS,
        shutdown_timeout_seconds: float = 3.0,
        python_executable: Path | str | None = None,
        runtime_root: Path | str | None = None,
    ) -> None:
        if not 1 <= int(port) <= 65_535:
            raise ValueError("port must be between 1 and 65535")
        limits = (
            float(startup_timeout_seconds),
            float(probe_timeout_seconds),
            float(probe_interval_seconds),
            float(shutdown_timeout_seconds),
        )
        if any(not math.isfinite(value) or value <= 0 for value in limits):
            raise ValueError("lifecycle timeouts must be positive")
        self.repo_root = Path(repo_root).resolve(strict=False)
        self.runtime_root = Path(runtime_root or repo_root).resolve(strict=False)
        self.ssd_path = (
            Path(ssd_path).resolve(strict=False) if ssd_path is not None else None
        )
        self.port = int(port)
        (
            self.startup_timeout_seconds, self.probe_timeout_seconds,
            self.probe_interval_seconds, self.shutdown_timeout_seconds,
        ) = limits
        requested_python = str(python_executable or sys.executable)
        self.python_executable, self._pythonpath_entries = _resolved_owner_runtime(
            requested_python, self.runtime_root
        )
        self._process: subprocess.Popen[bytes] | None = None
        self._token, self._ready = "", False
        self._verified_binding: tuple[str, str, str, str] = ("", "", "", "")
        self._atexit_registered = False

    @property
    def service_url(self) -> str:
        return f"http://{OWNER_HOST}:{self.port}"

    @property
    def is_ready(self) -> bool:
        return bool(
            self._ready and self._process is not None
            and self._process.poll() is None and self._token
        )

    @property
    def verified_binding(self) -> tuple[str, str, str, str]:
        return self._verified_binding

    def _spawn(self) -> subprocess.Popen[bytes]:
        if not self.repo_root.is_dir():
            raise HoloQueryServiceSupervisorError(
                "HOLOINDEX_QUERY_SERVICE_REPO_ROOT_UNAVAILABLE"
            )
        if not _owner_port_available(OWNER_HOST, self.port):
            raise HoloQueryServiceSupervisorError(PORT_IN_USE_ERROR)
        token = _owner_token()
        owner_environment = _owner_environment(
            token,
            self.ssd_path,
            self._pythonpath_entries,
        )
        try:
            command = _owner_command(
                self.python_executable,
                self.port,
                os.getpid(),
                repo_root=self.repo_root,
                environ=os.environ,
            )
            if not command:
                raise HoloQueryServiceSupervisorError(
                    SEALED_RUNTIME_INVALID_ERROR
                )
            process = subprocess.Popen(
                command,
                cwd=str(self.repo_root),
                env=owner_environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
                close_fds=True,
                **_hidden_process_options(),
            )
        except (OSError, ValueError):
            raise HoloQueryServiceSupervisorError(
                "HOLOINDEX_QUERY_SERVICE_SPAWN_FAILED"
            ) from None
        finally:
            owner_environment.pop(SERVICE_TOKEN_ENV, None)
        self._token = token
        return process

    def start(
        self,
        *,
        expected_repo_head_sha: str = "",
        expected_repo_root_digest: str = "",
        expected_generation_id: str = "",
        expected_receipt_digest: str = "",
    ) -> "HoloQueryServiceSupervisor":
        requested_binding = (
            expected_repo_head_sha, expected_repo_root_digest, expected_generation_id,
            expected_receipt_digest,
        )
        if self.is_ready and all(
            not requested or requested == verified
            for requested, verified in zip(
                requested_binding,
                self._verified_binding,
            )
        ):
            return self
        self.stop()
        self._process = self._spawn()
        try:
            result = await_owner_startup(
                process=self._process,
                settings=OwnerStartupSettings.from_binding(
                    host=OWNER_HOST,
                    port=self.port,
                    token=self._token,
                    timeouts=(
                        self.startup_timeout_seconds,
                        self.probe_timeout_seconds,
                        DEFAULT_OWNER_STARTUP_PROBE_TIMEOUT_SECONDS,
                        self.probe_interval_seconds,
                    ),
                    binding=requested_binding,
                ),
                health_exchange=_authenticated_health_exchange,
                clock=time.monotonic,
                sleeper=time.sleep,
            )
            if result.error:
                raise HoloQueryServiceSupervisorError(result.error)
            self._ready = True
            self._verified_binding = result.binding
            self._register_cleanup()
            return self
        except BaseException:
            self.stop()
            raise

    def environment_for_child(
        self,
        base_environment: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        """Return a copy containing the verified RedDog service handoff."""
        if not self.is_ready:
            self.stop()
            raise HoloQueryServiceSupervisorError(
                "HOLOINDEX_QUERY_SERVICE_NOT_READY"
            )
        child_environment = dict(
            os.environ if base_environment is None else base_environment
        )
        child_environment[SERVICE_URL_ENV] = self.service_url
        child_environment[SERVICE_TOKEN_ENV] = self._token
        return child_environment

    def _register_cleanup(self) -> None:
        if not self._atexit_registered:
            atexit.register(self.stop)
            self._atexit_registered = True

    def stop(self) -> None:
        """Invalidate handoff state and terminate the owned process."""
        process, self._process = self._process, None
        self._ready = False
        self._token = ""
        self._verified_binding = ("", "", "", "")
        if self._atexit_registered:
            atexit.unregister(self.stop)
            self._atexit_registered = False
        if process is not None:
            _terminate_process(
                process,
                timeout_seconds=self.shutdown_timeout_seconds,
            )

    close = stop

    def __enter__(self) -> "HoloQueryServiceSupervisor":
        return self.start()

    def __exit__(self, *_exc: object) -> None:
        self.stop()


__all__ = [
    "AuthenticatedOwnerHealthProof",
    "BINDING_MISMATCH_ERROR",
    "DEFAULT_OWNER_PORT",
    "DEFAULT_OWNER_PROBE_INTERVAL_SECONDS",
    "DEFAULT_OWNER_STARTUP_PROBE_TIMEOUT_SECONDS",
    "DEFAULT_OWNER_STARTUP_TIMEOUT_SECONDS",
    "HoloQueryServiceSupervisor",
    "HoloQueryServiceSupervisorError",
    "DEFAULT_OWNER_PROBE_TIMEOUT_SECONDS",
    "OWNER_HOST",
    "PORT_IN_USE_ERROR",
    "SERVICE_TOKEN_ENV",
    "SERVICE_URL_ENV",
]
