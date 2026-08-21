"""Host lifecycle boundary for the private HoloIndex query owner."""
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
from typing import Callable, Mapping, Self
from .holo_query_service import DEFAULT_STARTUP_WARMUP_TIMEOUT_SECONDS
from .holo_query_owner_startup import (
    OwnerStartupResult, OwnerStartupSettings, await_owner_startup,
)
from .holo_query_owner_health import (
    AuthenticatedOwnerHealthProof,
    BINDING_MISMATCH_ERROR,
    _authenticated_health_exchange,
    _authenticated_health_probe,
    _authenticated_health_rejection,
    _health_binding_rejection_code,
    _health_contract_ready,
    _health_rejection_code,
)
from .holo_query_binding import parse_exact_binding
from .holo_query_replica_binding import parse_replica_binding
from .reddog_sealed_holo_runtime import (
    scrub_holo_child_environment,
    sealed_holo_command,
    sealed_runtime_required,
    trusted_holo_site_packages,
)
OWNER_MODULE = "modules.infrastructure.foundups_mcp_bridge.src.holo_query_service"
OWNER_HOST = "127.0.0.1"
DEFAULT_OWNER_PORT = 8127
HEALTH_PATH = "/holoindex/v1/health"
SERVICE_URL_ENV = "HOLOINDEX_QUERY_SERVICE_URL"
SERVICE_TOKEN_ENV = "HOLOINDEX_QUERY_SERVICE_TOKEN"
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
SEALED_RUNTIME_INVALID_ERROR = "HOLOINDEX_QUERY_SERVICE_SEALED_RUNTIME_INVALID"
class HoloQueryServiceSupervisorError(RuntimeError):
    """Stable, secret-free lifecycle failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
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
    pythonpath_entries: tuple[str, ...] = (),
) -> dict[str, str]:
    environment = scrub_holo_child_environment(os.environ)
    environment.pop("HOLOINDEX_SSD_PATH", None)
    environment.update(
        {
            SERVICE_TOKEN_ENV: token,
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
        }
    )
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


def _binding_matches(
    requested: tuple[str, str, str, str], verified: tuple[str, str, str, str]
) -> bool:
    wanted = parse_exact_binding(requested, allow_empty_fields=True)
    found = parse_exact_binding(verified, allow_empty_fields=True)
    return bool(wanted is not None and found is not None and all(
        not item or item == observed for item, observed in zip(wanted, found)
    ))


def _required_canonical_start_binding(
    value: object,
) -> tuple[str, str, str, str]:
    binding = parse_exact_binding(value, allow_empty_fields=True)
    if binding is None:
        raise HoloQueryServiceSupervisorError(BINDING_MISMATCH_ERROR)
    return binding


def _required_replica_start_binding(
    *, requested: tuple[str, str, str, str] | None,
    configured: tuple[str, str, str, str], canonical_ssd_path: Path | None,
    query_replica_root: Path | None, verifier: Callable[[], object] | None,
) -> tuple[str, str, str, str]:
    binding = configured if requested is None else requested
    parsed = parse_replica_binding(binding)
    if (
        parsed is None or canonical_ssd_path is None or query_replica_root is None
        or verifier is None
    ):
        raise HoloQueryServiceSupervisorError("HOLOINDEX_QUERY_REPLICA_REQUIRED")
    return parsed


def _owner_command(
    python_executable: str,
    port: int,
    parent_pid: int,
    *,
    repo_root: Path | str | None = None,
    canonical_ssd_path: Path | str | None = None,
    query_replica_root: Path | str | None = None,
    environ: Mapping[str, str] | None = None,
) -> list[str]:
    env = os.environ if environ is None else environ
    storage_args = (
        (
            "--canonical-ssd-path", str(canonical_ssd_path),
            "--query-replica-root", str(query_replica_root),
        )
        if canonical_ssd_path is not None and query_replica_root is not None else ()
    )
    if repo_root is not None:
        sealed = sealed_holo_command(
            environ=env,
            trusted_module_path=Path(__file__),
            target_repo_root=repo_root,
            entry_relative_path="scripts/reddog_holoindex_owner_service_once.py",
            script_args=(
                "--host", OWNER_HOST, "--port", str(port),
                "--parent-pid", str(parent_pid),
                *storage_args,
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
        *storage_args,
    ]


class _SupervisorLifecycle:
    """Own shutdown and context-manager behavior for one supervisor instance."""

    _process: subprocess.Popen[bytes] | None
    _ready: bool
    _token: str
    _verified_binding: tuple[str, str, str, str]
    _verified_replica_binding: tuple[str, str, str, str]
    _atexit_registered: bool
    shutdown_timeout_seconds: float

    def start(self: Self) -> Self:
        raise NotImplementedError

    def stop(self) -> None:
        """Invalidate handoff state and terminate the owned process."""
        process, self._process = self._process, None
        self._ready = False
        self._token = ""
        self._verified_binding = ("", "", "", "")
        self._verified_replica_binding = ("", "", "", "")
        if self._atexit_registered:
            atexit.unregister(self.stop)
            self._atexit_registered = False
        if process is not None:
            _terminate_process(process, timeout_seconds=self.shutdown_timeout_seconds)

    close = stop

    def __enter__(self: Self) -> Self:
        return self.start()

    def __exit__(self, *_exc: object) -> None:
        self.stop()


class HoloQueryServiceSupervisor(_SupervisorLifecycle):
    """Own one authenticated loopback HoloIndex query-service process."""
    def __init__(
        self, *, repo_root: Path | str,
        ssd_path: Path | str | None = None,
        canonical_ssd_path: Path | str | None = None,
        query_replica_root: Path | str | None = None,
        port: int = DEFAULT_OWNER_PORT,
        startup_timeout_seconds: float = DEFAULT_OWNER_STARTUP_TIMEOUT_SECONDS,
        probe_timeout_seconds: float = DEFAULT_OWNER_PROBE_TIMEOUT_SECONDS,
        probe_interval_seconds: float = DEFAULT_OWNER_PROBE_INTERVAL_SECONDS,
        shutdown_timeout_seconds: float = 3.0,
        python_executable: Path | str | None = None,
        runtime_root: Path | str | None = None,
        replica_capability_verifier: Callable[[], object] | None = None,
        expected_replica_binding: tuple[str, str, str, str] = ("", "", "", ""),
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
        canonical_input = canonical_ssd_path if canonical_ssd_path is not None else ssd_path
        self.canonical_ssd_path = (
            Path(canonical_input).resolve(strict=False) if canonical_input else None
        )
        self.ssd_path = self.canonical_ssd_path  # compatibility
        self.query_replica_root = (
            Path(query_replica_root).resolve(strict=False) if query_replica_root else None
        )
        self._replica_capability_verifier = replica_capability_verifier
        self._expected_replica_binding = expected_replica_binding
        self.port = int(port)
        (
            self.startup_timeout_seconds, self.probe_timeout_seconds,
            self.probe_interval_seconds, self.shutdown_timeout_seconds,
        ) = limits
        runtime = str(python_executable or sys.executable)
        resolved_runtime = _resolved_owner_runtime(runtime, self.runtime_root)
        self.python_executable, self._pythonpath_entries = resolved_runtime
        self._process: subprocess.Popen[bytes] | None = None
        self._token, self._ready = "", False
        self._verified_binding: tuple[str, str, str, str] = ("", "", "", "")
        self._verified_replica_binding: tuple[str, str, str, str] = ("", "", "", "")
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
    @property
    def verified_replica_binding(self) -> tuple[str, str, str, str]:
        return self._verified_replica_binding
    def _spawn(self) -> subprocess.Popen[bytes]:
        if not self.repo_root.is_dir():
            raise HoloQueryServiceSupervisorError("HOLOINDEX_QUERY_SERVICE_REPO_ROOT_UNAVAILABLE")
        if not _owner_port_available(OWNER_HOST, self.port):
            raise HoloQueryServiceSupervisorError(PORT_IN_USE_ERROR)
        token = _owner_token()
        owner_environment = _owner_environment(token, self._pythonpath_entries)
        try:
            command = _owner_command(
                self.python_executable,
                self.port,
                os.getpid(),
                repo_root=self.repo_root,
                canonical_ssd_path=self.canonical_ssd_path,
                query_replica_root=self.query_replica_root,
                environ=os.environ,
            )
            if not command:
                raise HoloQueryServiceSupervisorError(SEALED_RUNTIME_INVALID_ERROR)
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
            raise HoloQueryServiceSupervisorError("HOLOINDEX_QUERY_SERVICE_SPAWN_FAILED") from None
        finally:
            owner_environment.pop(SERVICE_TOKEN_ENV, None)
        self._token = token
        return process
    def _await_startup(
        self, requested_binding: tuple[str, str, str, str],
        replica_binding: tuple[str, str, str, str],
    ) -> OwnerStartupResult:
        return await_owner_startup(
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
                replica_binding=replica_binding,
            ),
            health_exchange=_authenticated_health_exchange,
            clock=time.monotonic,
            sleeper=time.sleep,
        )
    def start(
        self, *, expected_repo_head_sha: str = "",
        expected_repo_root_digest: str = "", expected_generation_id: str = "",
        expected_receipt_digest: str = "",
        expected_replica_binding: tuple[str, str, str, str] | None = None,
    ) -> Self:
        requested_binding = _required_canonical_start_binding((
            expected_repo_head_sha, expected_repo_root_digest,
            expected_generation_id, expected_receipt_digest,
        ))
        replica_binding = _required_replica_start_binding(
            requested=expected_replica_binding,
            configured=self._expected_replica_binding,
            canonical_ssd_path=self.canonical_ssd_path,
            query_replica_root=self.query_replica_root,
            verifier=self._replica_capability_verifier,
        )
        reusable = _binding_matches(
            requested_binding, self._verified_binding
        ) and _binding_matches(replica_binding, self._verified_replica_binding)
        if self.is_ready and reusable:
            return self
        if self._replica_capability_verifier is not None:
            self._replica_capability_verifier()
        self.stop()
        self._process = self._spawn()
        try:
            if self._replica_capability_verifier is not None:
                self._replica_capability_verifier()
            result = self._await_startup(requested_binding, replica_binding)
            if result.error:
                raise HoloQueryServiceSupervisorError(result.error)
            self._ready = True
            self._verified_binding = result.binding
            self._verified_replica_binding = result.replica_binding
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
