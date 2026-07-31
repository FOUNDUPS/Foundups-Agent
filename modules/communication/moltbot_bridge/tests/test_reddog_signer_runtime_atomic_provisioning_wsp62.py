"""Exact WSP 62 gate for the signer atomic-provisioning slice."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
FILES = (
    "src/reddog_atomic_signer_runtime_generation_high_water.py",
    "src/reddog_atomic_signer_runtime_generation_high_water_reader.py",
    "src/reddog_runtime_artifact_activation_lease.py",
    "src/reddog_signer_runtime_atomic_provisioning.py",
    "src/reddog_signer_runtime_generation_anchor.py",
    "src/reddog_signer_runtime_generation_anchor_codec.py",
    "src/reddog_signer_runtime_generation_commit_guard.py",
    "src/reddog_signer_runtime_generation_pending_codec.py",
    "src/reddog_signer_runtime_generation_witness_binding.py",
    "src/reddog_sqlite_monotonic_authority_store.py",
    "tests/reddog_signer_generation_anchor_test_support.py",
    "tests/reddog_signer_runtime_provisioning_process_test_support.py",
    "tests/test_reddog_atomic_signer_runtime_generation_high_water.py",
    "tests/test_reddog_runtime_artifact_activation_lease.py",
    "tests/test_reddog_signer_runtime_atomic_provisioning.py",
    "tests/test_reddog_signer_runtime_generation_anchor.py",
    "tests/test_reddog_signer_runtime_generation_commit_guard.py",
    "tests/test_reddog_sqlite_monotonic_authority_store.py",
)


def _module_root() -> Path:
    return ROOT / "modules" / "communication" / "moltbot_bridge"


def test_slice_python_files_remain_below_675_lines() -> None:
    for relative in FILES:
        path = _module_root() / relative
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 675, path


def test_slice_functions_and_classes_remain_bounded() -> None:
    for relative in FILES:
        path = _module_root() / relative
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno - node.lineno + 1 <= 60, (
                    path,
                    node.name,
                )
            elif isinstance(node, ast.ClassDef):
                assert node.end_lineno - node.lineno + 1 <= 200, (
                    path,
                    node.name,
                )
