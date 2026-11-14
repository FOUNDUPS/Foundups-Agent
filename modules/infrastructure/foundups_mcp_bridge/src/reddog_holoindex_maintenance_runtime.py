"""Explicit runtime capability for governed HoloIndex maintenance probes."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .reddog_holoindex_process_image import (
    ProcessExecutableProof,
    ProcessExecutableProofError,
    prove_current_process_executable,
)
from .reddog_sealed_holo_runtime import (
    SEALED_SITE_PACKAGES_ENV,
    scrub_holo_child_environment,
    sealed_runtime_required,
    trusted_holo_site_packages,
)


MAINTENANCE_JSON_ONLY_ENV = "HOLOINDEX_MAINTENANCE_JSON_ONLY"
PROBE_SITE_PACKAGES_ENV = "HOLOINDEX_MAINTENANCE_PROBE_SITE_PACKAGES"
_RUNTIME_ERROR = "RUNTIME_DEPENDENCY_UNAVAILABLE"
_ENV_EXACT_DENY = frozenset(
    {
        "HOLO_FAST_SEARCH",
        "HOLO_INDEX_SYMBOLS",
        "HOLO_INDEX_WEB",
        "HOLO_SKIP_MODEL",
        MAINTENANCE_JSON_ONLY_ENV,
        PROBE_SITE_PACKAGES_ENV,
        "HOLOINDEX_QUERY_READONLY",
        "HOLOINDEX_QUERY_SERVICE_TOKEN",
        "HOLOINDEX_QUERY_SERVICE_URL",
        "WSP_PATH",
        "WSP_PATHS",
    }
)
_ENV_PREFIX_DENY = (
    "HOLO_SYMBOL_",
    "HOLO_WEB_",
    "HOLO_WSP_",
    "HOLOINDEX_WSP_",
)


class MaintenanceProbeRuntimeError(RuntimeError):
    """The maintenance process cannot prove its isolated-probe runtime."""


@dataclass(frozen=True)
class MaintenanceProbeRuntimeProof:
    """Process-local capability passed unchanged to the isolated verifier."""

    runtime_site_packages: tuple[str, ...] = ()
    base_executable_proof: ProcessExecutableProof | None = None

    def verifier_kwargs(self) -> dict[str, object]:
        present = bool(self.runtime_site_packages)
        if present != (self.base_executable_proof is not None):
            raise MaintenanceProbeRuntimeError(_RUNTIME_ERROR)
        if not present:
            return {}
        return {
            "runtime_site_packages": self.runtime_site_packages,
            "base_executable_proof": self.base_executable_proof,
        }


@dataclass(frozen=True)
class MaintenanceLaunchRuntime:
    """Secret-free environment plus exact interpreter launch capability."""

    environment: dict[str, str]
    executable_proof: ProcessExecutableProof | None = None


def _is_link_or_reparse(path: Path) -> bool:
    metadata = os.lstat(path)
    return bool(
        stat.S_ISLNK(metadata.st_mode)
        or int(getattr(metadata, "st_file_attributes", 0))
        & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        or getattr(path, "is_junction", lambda: False)()
    )


def _validated_site_packages(value: Path | str) -> Path:
    raw = Path(value)
    try:
        resolved = raw.resolve(strict=True)
        if (
            not raw.is_absolute()
            or os.path.normcase(str(raw)) != os.path.normcase(str(resolved))
            or not resolved.is_dir()
            or resolved.name.lower() != "site-packages"
            or resolved.parent.name.lower() != "lib"
            or resolved.parent.parent.name.lower() != ".venv"
        ):
            raise ValueError
        current = Path(resolved.anchor)
        for component in resolved.parts[1:]:
            current /= component
            if _is_link_or_reparse(current):
                raise ValueError
    except (OSError, ValueError):
        raise MaintenanceProbeRuntimeError(_RUNTIME_ERROR) from None
    return resolved


def _trusted_runtime_entries(
    environ: Mapping[str, str],
    runtime_root: Path | str | None,
    *,
    base_executable: Path | str | None = None,
) -> tuple[str, ...]:
    expected: Path | None = None
    if sealed_runtime_required(environ):
        raw = str(environ.get(SEALED_SITE_PACKAGES_ENV) or "").strip()
        if not raw:
            return ()
        try:
            candidate = _validated_site_packages(raw)
        except MaintenanceProbeRuntimeError:
            return ()
        expected = candidate
        root = candidate.parents[2]
        entries = trusted_holo_site_packages(
            root, base_executable=base_executable,
        )
    elif runtime_root is not None:
        entries = trusted_holo_site_packages(
            runtime_root, base_executable=base_executable,
        )
    else:
        entries = ()
    if len(entries) != 1:
        return ()
    try:
        candidate = _validated_site_packages(entries[0])
    except MaintenanceProbeRuntimeError:
        return ()
    if expected is not None and os.path.normcase(str(candidate)) != os.path.normcase(
        str(expected)
    ):
        return ()
    return (str(candidate),)


def prepare_maintenance_launch(
    *, environ: Mapping[str, str], ssd_path: Path,
    runtime_root: Path | str | None,
) -> MaintenanceLaunchRuntime:
    """Bind one governed refresh to its environment and exact process image."""

    child = scrub_holo_child_environment(environ)
    for name in tuple(child):
        normalized = name.upper()
        if normalized in _ENV_EXACT_DENY or normalized.startswith(
            _ENV_PREFIX_DENY
        ):
            child.pop(name, None)
    child["HOLOINDEX_SSD_PATH"] = str(ssd_path)
    child["HOLO_USE_TURBOQUANT"] = "0"
    child[MAINTENANCE_JSON_ONLY_ENV] = "1"
    child["PYTHONDONTWRITEBYTECODE"] = "1"
    governed = runtime_root is not None or sealed_runtime_required(environ)
    executable_proof: ProcessExecutableProof | None = None
    if governed:
        try:
            executable_proof = prove_current_process_executable()
        except ProcessExecutableProofError:
            raise MaintenanceProbeRuntimeError(_RUNTIME_ERROR) from None
    entries = _trusted_runtime_entries(
        environ,
        runtime_root,
        base_executable=(
            executable_proof.path if executable_proof is not None else None
        ),
    )
    if not entries and governed:
        raise MaintenanceProbeRuntimeError(_RUNTIME_ERROR)
    if entries:
        child[PROBE_SITE_PACKAGES_ENV] = entries[0]
        if not sealed_runtime_required(environ):
            child["PYTHONPATH"] = os.pathsep.join(entries)
    return MaintenanceLaunchRuntime(child, executable_proof)


def build_maintenance_environment(
    *, environ: Mapping[str, str], ssd_path: Path,
    runtime_root: Path | str | None,
) -> dict[str, str]:
    """Compatibility projection of the proven maintenance launch environment."""

    return prepare_maintenance_launch(
        environ=environ, ssd_path=ssd_path, runtime_root=runtime_root,
    ).environment


def resolve_maintenance_probe_runtime(
    environ: Mapping[str, str] | None = None,
) -> MaintenanceProbeRuntimeProof:
    """Revalidate the explicit path and bind it to this process image."""

    source = os.environ if environ is None else environ
    raw = str(source.get(PROBE_SITE_PACKAGES_ENV) or "").strip()
    if not raw:
        return MaintenanceProbeRuntimeProof()
    runtime = _validated_site_packages(raw)
    try:
        executable = prove_current_process_executable()
    except ProcessExecutableProofError:
        raise MaintenanceProbeRuntimeError(_RUNTIME_ERROR) from None
    trusted = trusted_holo_site_packages(
        runtime.parents[2], base_executable=executable.path,
    )
    if len(trusted) != 1 or os.path.normcase(trusted[0]) != os.path.normcase(
        str(runtime)
    ):
        raise MaintenanceProbeRuntimeError(_RUNTIME_ERROR)
    return MaintenanceProbeRuntimeProof((str(runtime),), executable)


__all__ = [
    "MAINTENANCE_JSON_ONLY_ENV",
    "PROBE_SITE_PACKAGES_ENV",
    "MaintenanceProbeRuntimeError",
    "MaintenanceProbeRuntimeProof",
    "MaintenanceLaunchRuntime",
    "build_maintenance_environment",
    "prepare_maintenance_launch",
    "resolve_maintenance_probe_runtime",
]
