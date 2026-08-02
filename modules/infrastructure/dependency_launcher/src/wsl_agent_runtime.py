"""Opt-in advisory discovery for agents in the canonical WSL runtime."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence


RUNTIME_SCHEMA = "foundups_agent_wsl_runtime_receipt.v1"
AUTHORITY_CLASS = "advisory_unverified_runtime_report"
DEFAULT_DISTRO = "Ubuntu-24.04"
COMPONENT_EXECUTABLES = {
    "openclaw": "/usr/local/bin/openclaw",
    "hermes": "/usr/local/bin/hermes",
}
COMPONENT_VERSION_PATTERNS = {
    "openclaw": re.compile(r"OpenClaw [0-9]{4}\.[0-9]{1,2}\.[0-9]{1,2}(?: \([0-9a-f]{7,40}\))?"),
    "hermes": re.compile(r"Hermes Agent v[0-9]+\.[0-9]+\.[0-9]+ \([0-9]{4}\.[0-9]{1,2}\.[0-9]{1,2}\)"),
}
_DISTRO_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_MAX_OUTPUT_CHARS = 128

@dataclass(frozen=True)
class WslAgentComponentStatus:
    component_id: str
    executable: str
    available: bool
    version: str
    reason: str

@dataclass(frozen=True)
class WslAgentRuntimeReceipt:
    schema_version: str
    authority_class: str
    state: str
    distro: str
    base_path: str
    expected_base_path: str
    components: tuple[WslAgentComponentStatus, ...]
    reasons: tuple[str, ...]
    receipt_id: str


Runner = Callable[[Sequence[str], float], tuple[int, str]]
BasePathResolver = Callable[[str], str]

def run_wsl_agent_runtime_advisory(
    *,
    environment: Mapping[str, str] | None = None,
    runner: Runner | None = None,
    base_path_resolver: BasePathResolver | None = None,
) -> WslAgentRuntimeReceipt:
    """Probe exact WSL executables and emit one non-authoritative status line."""
    receipt = probe_wsl_agent_runtime(
        environment=environment,
        runner=runner,
        base_path_resolver=base_path_resolver,
    )
    versions = ",".join(
        f"{item.component_id}={item.version or item.reason}" for item in receipt.components
    ) or "none"
    reasons = ",".join(receipt.reasons) if receipt.reasons else "none"
    print(
        f"[AGENT-WSL] preflight={receipt.state} distro={receipt.distro or 'none'} "
        f"components={versions} reasons={reasons}"
    )
    return receipt


def probe_wsl_agent_runtime(
    *,
    environment: Mapping[str, str] | None = None,
    runner: Runner | None = None,
    base_path_resolver: BasePathResolver | None = None,
) -> WslAgentRuntimeReceipt:
    """Return non-authoritative availability evidence without lifecycle changes."""
    env = environment if environment is not None else os.environ
    if not _truthy(env.get("FOUNDUPS_AGENT_WSL_RUNTIME_ENABLED", "0")):
        return _receipt("DISABLED", "", "", "", (), ("runtime_probe_disabled",))
    try:
        distro = _validate_distro(env.get("FOUNDUPS_AGENT_WSL_DISTRO", DEFAULT_DISTRO))
    except ValueError:
        return _receipt("NOT_READY", "", "", "", (), ("distro_invalid",))
    expected = str(env.get("FOUNDUPS_AGENT_WSL_EXPECTED_BASE", "")).strip()
    resolver = base_path_resolver or _resolve_windows_wsl_base_path
    try:
        base_path = resolver(distro)
    except Exception:
        return _receipt("NOT_READY", distro, "", expected, (), ("distro_not_registered",))
    if expected and not _same_path(base_path, expected):
        return _receipt(
            "NOT_READY", distro, base_path, expected, (), ("distro_base_path_mismatch",)
        )
    executor = runner or _run_command
    components = tuple(_probe_component(distro, name, executor) for name in COMPONENT_EXECUTABLES)
    reasons = tuple(item.reason for item in components if not item.available)
    state = "PASS" if not reasons else "NOT_READY"
    return _receipt(state, distro, base_path, expected, components, reasons)


def build_wsl_version_command(component_id: str, distro: str) -> tuple[str, ...]:
    """Build the fixed, shell-free version probe for one allowlisted runtime."""
    normalized = _validate_distro(distro)
    executable = COMPONENT_EXECUTABLES.get(component_id)
    if executable is None:
        raise ValueError("wsl_component_not_allowlisted")
    return (
        "wsl.exe",
        "--distribution",
        normalized,
        "--exec",
        executable,
        "--version",
    )


def _probe_component(distro: str, component_id: str, runner: Runner) -> WslAgentComponentStatus:
    executable = COMPONENT_EXECUTABLES[component_id]
    try:
        code, output = runner(build_wsl_version_command(component_id, distro), 10.0)
    except Exception:
        return WslAgentComponentStatus(component_id, executable, False, "", "probe_failed")
    version = _parse_version(component_id, output)
    if code != 0 or not version:
        return WslAgentComponentStatus(component_id, executable, False, "", "runtime_unavailable")
    return WslAgentComponentStatus(component_id, executable, True, version, "")


def _run_command(command: Sequence[str], timeout: float) -> tuple[int, str]:
    executable = _trusted_wsl_path()
    if command[0] != "wsl.exe" or executable is None:
        return 127, ""
    completed = subprocess.run(
        [str(executable), *command[1:]],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        shell=False,
    )
    return completed.returncode, completed.stdout or completed.stderr


def _trusted_wsl_path() -> Path | None:
    if os.name != "nt":
        return None
    import ctypes

    buffer = ctypes.create_unicode_buffer(32768)
    length = ctypes.windll.kernel32.GetSystemDirectoryW(buffer, len(buffer))
    candidate = Path(buffer.value) / "wsl.exe"
    return candidate if 0 < length < len(buffer) and candidate.is_file() else None


def _resolve_windows_wsl_base_path(distro: str) -> str:
    if os.name != "nt":
        return ""
    import winreg

    root = r"Software\Microsoft\Windows\CurrentVersion\Lxss"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, root) as parent:
        for index in range(winreg.QueryInfoKey(parent)[0]):
            try:
                with winreg.OpenKey(parent, winreg.EnumKey(parent, index)) as child:
                    name = str(winreg.QueryValueEx(child, "DistributionName")[0])
                    if name == distro:
                        return str(winreg.QueryValueEx(child, "BasePath")[0])
            except OSError:
                continue
    raise ValueError("distro_not_registered")


def _receipt(
    state: str,
    distro: str,
    base_path: str,
    expected: str,
    components: tuple[WslAgentComponentStatus, ...],
    reasons: tuple[str, ...],
) -> WslAgentRuntimeReceipt:
    payload = {
        "schema_version": RUNTIME_SCHEMA,
        "authority_class": AUTHORITY_CLASS,
        "state": state,
        "distro": distro,
        "base_path": base_path,
        "expected_base_path": expected,
        "components": [asdict(item) for item in components],
        "reasons": list(reasons),
    }
    receipt_id = "sha256:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
    ).hexdigest()
    return WslAgentRuntimeReceipt(
        RUNTIME_SCHEMA, AUTHORITY_CLASS, state, distro, base_path,
        expected, components, reasons, receipt_id,
    )


def _validate_distro(value: object) -> str:
    distro = str(value or "").strip()
    if not _DISTRO_PATTERN.fullmatch(distro):
        raise ValueError("wsl_distro_invalid")
    return distro


def _parse_version(component_id: str, value: object) -> str:
    lines = (line.strip() for line in str(value or "").splitlines())
    text = next((line for line in lines if line), "")[:_MAX_OUTPUT_CHARS]
    normalized = "".join(char for char in text if 32 <= ord(char) <= 126)
    pattern = COMPONENT_VERSION_PATTERNS[component_id]
    return normalized if pattern.fullmatch(normalized) else ""


def _same_path(left: str, right: str) -> bool:
    return Path(left).resolve(strict=False) == Path(right).resolve(strict=False)


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


__all__ = [
    "AUTHORITY_CLASS",
    "COMPONENT_EXECUTABLES",
    "COMPONENT_VERSION_PATTERNS",
    "DEFAULT_DISTRO",
    "WslAgentComponentStatus",
    "WslAgentRuntimeReceipt",
    "build_wsl_version_command",
    "probe_wsl_agent_runtime",
    "run_wsl_agent_runtime_advisory",
]
