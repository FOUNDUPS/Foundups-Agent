"""Focused static trust-boundary checks extracted from integration matrices."""

from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
BRIDGE_SRC = REPO_ROOT / "modules/communication/moltbot_bridge/src"


def test_resident_serial_loop_has_no_effectful_stage_imports() -> None:
    tree = ast.parse(
        (BRIDGE_SRC / "reddog_main_resident_queue_serial_loop_bootstrap.py").read_text(
            encoding="utf-8"
        )
    )
    banned_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "holo_index",
        "git",
        "hmac",
        "secrets",
    }
    banned_fragments = {
        "reddog_signer_delegated_authority_runtime",
        "reddog_wre_queue_authority_runtime_invoke",
        "reddog_wre_queue_authority_verification_invoke",
        "reddog_wre_queue_authorized",
        "reddog_wre_queue_verified_authority_work_order_invoke",
        "worktree_pr_runner",
        "pattern_memory",
        "openclaw_supervisor",
        "hermes_job_executor",
    }
    _assert_static_boundary(tree, banned_roots, banned_fragments)


def test_signed_worker_executor_has_no_shell_network_or_runtime_mutation() -> None:
    source = (BRIDGE_SRC / "reddog_signed_worker_dispatch_task_executor.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    for token in (
        "subprocess",
        "requests",
        "socket",
        "holo_index.py --index",
        "create_autonomous_task",
        "complete_autonomous_task",
        "git push",
        "gh pr",
    ):
        assert token not in source
    _assert_static_boundary(tree, {"subprocess", "requests"}, set())


def _assert_static_boundary(
    tree, banned_roots: set[str], banned_fragments: set[str]
) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_roots
                assert all(part not in alias.name for part in banned_fragments)
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_roots
            assert all(part not in node.module for part in banned_fragments)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in {"eval", "exec", "compile", "__import__"}
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {
                    "system",
                    "popen",
                    "spawn",
                    "run",
                    "Popen",
                    "check_call",
                    "check_output",
                    "unlink",
                    "remove",
                    "rmdir",
                    "rename",
                }
