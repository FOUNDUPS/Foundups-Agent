"""Host-capability helpers shared by RedDog Holo filesystem falsifiers."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


def create_directory_alias_or_skip(alias: Path, target: Path) -> None:
    """Create a symlink or Windows junction using the proven test fallback."""

    try:
        os.symlink(target, alias, target_is_directory=True)
        return
    except OSError:
        pass
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/d", "/c", "mklink", "/J", str(alias), str(target)],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return
    pytest.skip("directory link/junction unavailable on this host")


__all__ = ["create_directory_alias_or_skip"]
