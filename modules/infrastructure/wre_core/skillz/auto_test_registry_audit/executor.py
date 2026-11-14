"""Named registry-scope telemetry; never execute tests or model proposals."""
from pathlib import Path


def execute(task: dict) -> dict:
    """Project once using the existing exact-commit owner in our own checkout."""
    required = {"operation", "request", "skill_name", "agent"}
    if (
        type(task) is not dict or not required <= set(task)
        or set(task) - required - {"parent_continuity_context"}
        or task["operation"] != "project_scope"
        or task["skill_name"] != "auto_test_registry_audit"
        or type(task["agent"]) is not str or not task["agent"]
        or type(task["request"]) is not dict
        or set(task["request"]) != {
            "base_sha", "head_sha", "expected_changed_paths", "projection_input",
        }
    ):
        return _reject("FAIL_REGISTRY_TELEMETRY_INPUT")
    executor = Path(__file__).resolve()
    if executor.parts[-6:] != (
        "modules", "infrastructure", "wre_core", "skillz",
        "auto_test_registry_audit", "executor.py",
    ):
        return _reject("FAIL_REGISTRY_TELEMETRY_LAYOUT")
    from modules.infrastructure.wre_core.src.wre_test_registry_differential_plan_runtime import (
        produce_registry_scope_projection,
    )
    root = executor.parents[5]
    return produce_registry_scope_projection(
        task["request"], worktree_path=root, repo_root=root,
    ).to_dict()


def _reject(reason: str) -> dict:
    return {"projected": False, "rejection_reasons": [reason], "evidence": {}}
