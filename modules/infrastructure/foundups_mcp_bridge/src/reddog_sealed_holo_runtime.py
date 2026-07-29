"""Manifest-authenticated process boundary for RedDog-owned Holo workers."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Mapping, Sequence


SEALED_REQUIRED_ENV = "REDDOG_SEALED_RUNTIME_REQUIRED"
SEALED_ROOT_ENV = "REDDOG_SEALED_RUNTIME_ROOT"
SEALED_MANIFEST_ENV = "REDDOG_SEALED_RUNTIME_MANIFEST_PATH"
SEALED_MANIFEST_DIGEST_ENV = "REDDOG_SEALED_RUNTIME_MANIFEST_DIGEST"
SEALED_BOOTSTRAP_ENV = "REDDOG_SEALED_RUNTIME_BOOTSTRAP_PATH"
SEALED_SITE_PACKAGES_ENV = "REDDOG_SEALED_RUNTIME_SITE_PACKAGES"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SECRET_SUFFIXES = (
    "_API_KEY",
    "_ACCESS_KEY",
    "_PRIVATE_KEY",
    "_PASSWORD",
    "_SECRET",
    "_TOKEN",
    "_CREDENTIAL",
    "_CREDENTIALS",
    "_COOKIE",
)
_PYTHON_OVERRIDE_NAMES = frozenset(
    {"PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "PYTHONUSERBASE"}
)


def sealed_runtime_required(environ: Mapping[str, str]) -> bool:
    return str(environ.get(SEALED_REQUIRED_ENV, "")).strip() == "1"


def scrub_holo_child_environment(
    environ: Mapping[str, str],
) -> dict[str, str]:
    """Remove provider credentials and Python import overrides."""

    child: dict[str, str] = {}
    for name, value in environ.items():
        normalized = str(name).upper()
        secret = normalized.endswith(_SECRET_SUFFIXES)
        reddog_private = normalized.startswith("REDDOG_") and not normalized.startswith(
            "REDDOG_SEALED_RUNTIME_"
        )
        if secret or reddog_private or normalized in _PYTHON_OVERRIDE_NAMES:
            continue
        child[str(name)] = str(value)
    child["PYTHONDONTWRITEBYTECODE"] = "1"
    child["PYTHONNOUSERSITE"] = "1"
    child["PYTHONUTF8"] = "1"
    return child


def sealed_holo_command(
    *,
    environ: Mapping[str, str],
    trusted_module_path: Path | str,
    target_repo_root: Path | str,
    entry_relative_path: str,
    script_args: Sequence[str],
    python_executable: str,
) -> tuple[str, ...] | None:
    """Return a sealed command, None when optional, or empty when invalid."""

    if not sealed_runtime_required(environ):
        return None
    values = _runtime_values(
        environ, trusted_module_path, entry_relative_path)
    if values is None:
        return ()
    source, manifest, bootstrap, site_packages, entry, digest = values
    return (
        python_executable, "-I", "-S", "-B", str(bootstrap), str(entry),
        str(source), str(Path(target_repo_root).resolve(strict=False)),
        str(site_packages), str(manifest), digest,
        *tuple(str(value) for value in script_args),
    )


def _runtime_values(
    environ: Mapping[str, str],
    trusted_module_path: Path | str,
    entry_relative_path: str,
) -> tuple[Path, Path, Path, Path, Path, str] | None:
    source = Path(str(environ.get(SEALED_ROOT_ENV) or "")).resolve(strict=False)
    expected_source = Path(trusted_module_path).resolve(strict=False).parents[4]
    manifest = Path(
        str(environ.get(SEALED_MANIFEST_ENV) or "")
    ).resolve(strict=False)
    bootstrap = Path(
        str(environ.get(SEALED_BOOTSTRAP_ENV) or "")
    ).resolve(strict=False)
    site_packages = Path(
        str(environ.get(SEALED_SITE_PACKAGES_ENV) or "")
    ).resolve(strict=False)
    digest = str(environ.get(SEALED_MANIFEST_DIGEST_ENV) or "").strip()
    expected_bootstrap = (
        source / "extensions" / "reddog" / "start_operations_python_bootstrap.py"
    )
    entry = source / Path(entry_relative_path)
    if (
        source != expected_source
        or not source.is_dir()
        or not manifest.is_file()
        or manifest.parent != source
        or bootstrap != expected_bootstrap
        or not bootstrap.is_file()
        or not _bootstrap_authenticated(source, manifest, bootstrap, digest)
        or not entry.is_file()
        or not site_packages.is_dir()
        or _SHA256_RE.fullmatch(digest) is None
    ):
        return None
    return source, manifest, bootstrap, site_packages, entry, digest


def _bootstrap_authenticated(
    source: Path,
    manifest: Path,
    bootstrap: Path,
    expected_manifest_digest: str,
) -> bool:
    try:
        value = json.loads(manifest.read_text(encoding="utf-8"))
        canonical = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        if hashlib.sha256(canonical).hexdigest() != expected_manifest_digest:
            return False
        relative = bootstrap.relative_to(source).as_posix()
        expected = value["required_runtime_sha256"][relative]
        observed = hashlib.sha256(
            bootstrap.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        return observed == expected
    except (KeyError, OSError, TypeError, ValueError):
        return False


__all__ = [
    "SEALED_REQUIRED_ENV",
    "scrub_holo_child_environment",
    "sealed_holo_command",
    "sealed_runtime_required",
]
