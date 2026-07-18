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
import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping


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
DEFAULT_OWNER_PROBE_INTERVAL_SECONDS = 0.5


class HoloQueryServiceSupervisorError(RuntimeError):
    """Stable, secret-free lifecycle failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


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
    if response.status not in {200, 409} or len(body) > MAX_HEALTH_RESPONSE_BYTES:
        return None
    payload = json.loads(body.decode("utf-8"))
    return payload if isinstance(payload, Mapping) else None


def _health_contract_ready(
    payload: Mapping[str, object],
    *,
    expected_repo_head_sha: str,
    expected_generation_id: str,
    expected_receipt_digest: str,
) -> bool:
    repo_head_sha = str(payload.get("repo_head_sha") or "")
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
        bool(repo_head_sha and generation_id and receipt_digest),
    )
    binding_checks = (
        not expected_repo_head_sha or repo_head_sha == expected_repo_head_sha,
        not expected_generation_id or generation_id == expected_generation_id,
        not expected_receipt_digest or receipt_digest == expected_receipt_digest,
    )
    return all(contract_checks + binding_checks)


def _authenticated_health_probe(
    *,
    host: str,
    port: int,
    token: str,
    timeout_seconds: float,
    expected_repo_head_sha: str = "",
    expected_generation_id: str = "",
    expected_receipt_digest: str = "",
) -> bool:
    """Return true only for the exact authenticated owner-ready contract."""
    if not _probe_target_is_private(host, token):
        return False
    connection = http.client.HTTPConnection(
        host,
        int(port),
        timeout=max(0.01, float(timeout_seconds)),
    )
    try:
        payload = _read_health_payload(connection, token)
        return bool(
            payload is not None
            and _health_contract_ready(
                payload,
                expected_repo_head_sha=expected_repo_head_sha,
                expected_generation_id=expected_generation_id,
                expected_receipt_digest=expected_receipt_digest,
            )
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return False
    finally:
        connection.close()


def _health_rejection_code(payload: Mapping[str, object] | None) -> str:
    """Expose only authenticated, terminal freshness failures during startup."""
    value = payload if isinstance(payload, Mapping) else {}
    error = str(value.get("error") or "")
    terminal = {
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


def _authenticated_health_rejection(
    *, host: str, port: int, token: str, timeout_seconds: float
) -> str:
    if not _probe_target_is_private(host, token):
        return ""
    connection = http.client.HTTPConnection(
        host, int(port), timeout=max(0.01, float(timeout_seconds))
    )
    try:
        return _health_rejection_code(_read_health_payload(connection, token))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return ""
    finally:
        connection.close()


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


def _owner_environment(token: str, ssd_path: Path | None) -> dict[str, str]:
    environment = dict(os.environ)
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
    return environment


def _owner_command(
    python_executable: str,
    port: int,
) -> list[str]:
    return [
        python_executable,
        "-B",
        "-m",
        OWNER_MODULE,
        "--host",
        OWNER_HOST,
        "--port",
        str(port),
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
        probe_timeout_seconds: float = 1.0,
        probe_interval_seconds: float = DEFAULT_OWNER_PROBE_INTERVAL_SECONDS,
        shutdown_timeout_seconds: float = 3.0,
        python_executable: Path | str | None = None,
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
        self.ssd_path = (
            Path(ssd_path).resolve(strict=False) if ssd_path is not None else None
        )
        self.port = int(port)
        (
            self.startup_timeout_seconds,
            self.probe_timeout_seconds,
            self.probe_interval_seconds,
            self.shutdown_timeout_seconds,
        ) = limits
        self.python_executable = str(python_executable or sys.executable)
        self._process: subprocess.Popen[bytes] | None = None
        self._token = ""
        self._ready = False
        self._atexit_registered = False

    @property
    def service_url(self) -> str:
        """Return the non-secret loopback endpoint."""
        return f"http://{OWNER_HOST}:{self.port}"

    @property
    def is_ready(self) -> bool:
        """Report whether the verified owner process is still alive."""
        return bool(
            self._ready
            and self._process is not None
            and self._process.poll() is None
            and self._token
        )

    def _spawn(self) -> subprocess.Popen[bytes]:
        if not self.repo_root.is_dir():
            raise HoloQueryServiceSupervisorError(
                "HOLOINDEX_QUERY_SERVICE_REPO_ROOT_UNAVAILABLE"
            )
        token = _owner_token()
        owner_environment = _owner_environment(token, self.ssd_path)
        try:
            process = subprocess.Popen(
                _owner_command(self.python_executable, self.port),
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

    def start(self) -> "HoloQueryServiceSupervisor":
        """Start, authenticate, and prove the owner ready or fail closed."""
        if self.is_ready:
            return self
        self.stop()
        self._process = self._spawn()
        deadline = time.monotonic() + self.startup_timeout_seconds
        try:
            while True:
                if self._process.poll() is not None:
                    raise HoloQueryServiceSupervisorError(
                        "HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP"
                    )
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise HoloQueryServiceSupervisorError(
                        "HOLOINDEX_QUERY_SERVICE_STARTUP_TIMEOUT"
                    )
                if _authenticated_health_probe(
                    host=OWNER_HOST,
                    port=self.port,
                    token=self._token,
                    timeout_seconds=min(self.probe_timeout_seconds, remaining),
                ):
                    if self._process.poll() is not None:
                        raise HoloQueryServiceSupervisorError(
                            "HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP"
                        )
                    self._ready = True
                    self._register_cleanup()
                    return self
                rejection = _authenticated_health_rejection(
                    host=OWNER_HOST,
                    port=self.port,
                    token=self._token,
                    timeout_seconds=min(self.probe_timeout_seconds, remaining),
                )
                if rejection:
                    raise HoloQueryServiceSupervisorError(rejection)
                time.sleep(min(self.probe_interval_seconds, remaining))
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
    "DEFAULT_OWNER_PORT",
    "DEFAULT_OWNER_PROBE_INTERVAL_SECONDS",
    "DEFAULT_OWNER_STARTUP_TIMEOUT_SECONDS",
    "HoloQueryServiceSupervisor",
    "HoloQueryServiceSupervisorError",
    "OWNER_HOST",
    "SERVICE_TOKEN_ENV",
    "SERVICE_URL_ENV",
]
