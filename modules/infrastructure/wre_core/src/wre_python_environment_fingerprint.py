"""Content-free Python environment identity for local WRE diagnostics."""

from __future__ import annotations

import hashlib
from importlib.metadata import distributions
import json
from pathlib import Path
import platform
import sys
from typing import Any


def python_environment_fingerprint() -> dict[str, Any]:
    """Bind interpreter bytes, version, and installed package versions."""
    packages = sorted({
        (str(item.metadata.get("Name", "")).lower(), str(item.version))
        for item in distributions()
        if item.metadata.get("Name")
    })
    payload = {
        "executable_digest": _file_digest(Path(sys.executable)),
        "implementation": platform.python_implementation(),
        "packages": packages,
        "python_version": platform.python_version(),
    }
    return {
        "digest": _digest(payload), "package_count": len(packages),
        "python_version": payload["python_version"],
    }


def _file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


__all__ = ["python_environment_fingerprint"]
