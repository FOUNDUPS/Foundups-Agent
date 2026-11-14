"""Launch/runtime scripts for the OpenClaw bridge module."""

from pathlib import Path


if __name__ == "scripts":
    _root_scripts = Path(__file__).resolve().parents[4] / "scripts"
    if _root_scripts.is_dir():
        __path__.append(str(_root_scripts))
