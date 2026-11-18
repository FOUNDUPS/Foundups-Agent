"""Adversaries for bounded no-follow RedDog runtime JSON reads."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    MAX_REDDOG_RUNTIME_JSON_BYTES,
    read_reddog_runtime_json_mapping,
)


def _symlink(link: Path, target: Path, *, target_is_directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=target_is_directory)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")


def test_reads_exact_regular_mapping_inside_allowed_root(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps({"schema_version": "test.v1"}), encoding="utf-8")

    assert read_reddog_runtime_json_mapping(path, allowed_root=tmp_path) == {
        "schema_version": "test.v1"
    }


def test_rejects_final_component_symlink_even_when_target_is_inside_root(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    link = tmp_path / "artifact.json"
    _symlink(link, target)

    with pytest.raises(ValueError, match="runtime_json_symlink_forbidden"):
        read_reddog_runtime_json_mapping(link, allowed_root=tmp_path)


def test_rejects_symlinked_parent_component(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / "artifact.json").write_text("{}", encoding="utf-8")
    link = tmp_path / "linked"
    _symlink(link, target, target_is_directory=True)

    with pytest.raises((OSError, ValueError)):
        read_reddog_runtime_json_mapping(
            link / "artifact.json", allowed_root=tmp_path
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows junction adversary")
def test_rejects_junction_parent_component(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / "artifact.json").write_text("{}", encoding="utf-8")
    junction = tmp_path / "junction"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"junction creation unavailable: {result.stderr}")

    with pytest.raises(ValueError, match="confined_read_path_link_rejected"):
        read_reddog_runtime_json_mapping(
            junction / "artifact.json", allowed_root=tmp_path
        )


def test_rejects_oversized_json_before_parsing(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    path.write_bytes(b"{" + (b" " * MAX_REDDOG_RUNTIME_JSON_BYTES) + b"}")

    with pytest.raises((OSError, ValueError)):
        read_reddog_runtime_json_mapping(path, allowed_root=tmp_path)
