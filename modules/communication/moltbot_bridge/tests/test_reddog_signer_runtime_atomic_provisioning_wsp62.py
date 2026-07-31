"""Exact WSP 62 gate for the signer atomic-provisioning slice."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
FILES = (
    "modules/communication/moltbot_bridge/src/"
    "reddog_atomic_signer_runtime_generation_high_water.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_atomic_signer_runtime_generation_high_water_reader.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_authority_runtime_store.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_authority_runtime_store_windows.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_runtime_artifact_activation_lease.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_runtime_artifact_manifest_authority.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_runtime_artifact_manifest_io.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_signed_runtime_artifact_manifest.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_signer_runtime_atomic_provisioning.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_signer_runtime_atomic_provisioning_contract.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_signer_runtime_generation_anchor.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_signer_runtime_generation_anchor_codec.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_signer_runtime_generation_commit_guard.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_signer_runtime_generation_contract.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_signer_runtime_generation_pending_codec.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_signer_runtime_generation_reader.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_signer_runtime_generation_witness_binding.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_sqlite_monotonic_authority_store.py",
    "modules/communication/moltbot_bridge/tests/"
    "reddog_signer_generation_anchor_test_support.py",
    "modules/communication/moltbot_bridge/tests/"
    "reddog_signer_generation_test_support.py",
    "modules/communication/moltbot_bridge/tests/"
    "reddog_signer_runtime_provisioning_process_test_support.py",
    "modules/communication/moltbot_bridge/tests/"
    "test_reddog_atomic_signer_runtime_generation_high_water.py",
    "modules/communication/moltbot_bridge/tests/"
    "test_reddog_runtime_artifact_activation_lease.py",
    "modules/communication/moltbot_bridge/tests/"
    "test_reddog_runtime_artifact_manifest_authority_freshness.py",
    "modules/communication/moltbot_bridge/tests/"
    "test_reddog_signer_runtime_atomic_provisioning.py",
    "modules/communication/moltbot_bridge/tests/"
    "test_reddog_signer_runtime_atomic_provisioning_recovery.py",
    "modules/communication/moltbot_bridge/tests/"
    "test_reddog_signer_runtime_atomic_provisioning_wsp62.py",
    "modules/communication/moltbot_bridge/tests/"
    "test_reddog_signer_runtime_generation_anchor.py",
    "modules/communication/moltbot_bridge/tests/"
    "test_reddog_signer_runtime_generation_commit_guard.py",
    "modules/communication/moltbot_bridge/tests/"
    "test_reddog_signer_runtime_generation_reader.py",
    "modules/communication/moltbot_bridge/tests/"
    "test_reddog_signer_runtime_generation_witness_isolation.py",
    "modules/communication/moltbot_bridge/tests/"
    "test_reddog_sqlite_monotonic_authority_store.py",
    "modules/infrastructure/shared_utilities/"
    "reddog_runtime_artifact_generation.py",
)


def test_slice_python_files_remain_below_675_lines() -> None:
    for relative in FILES:
        path = ROOT / relative
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 675, path


def test_slice_functions_and_classes_remain_bounded() -> None:
    for relative in FILES:
        path = ROOT / relative
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
