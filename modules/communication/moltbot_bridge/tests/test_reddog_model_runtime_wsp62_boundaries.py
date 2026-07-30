"""WSP 62 boundaries for RedDog model-runtime authority adapters."""

from __future__ import annotations

import ast
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
BOUNDED_MODULES = (
    "reddog_artifact_generation_admission_capability.py",
    "reddog_artifact_generation_authority_lineage.py",
    "reddog_artifact_generation_authority_capability.py",
    "reddog_artifact_generation_model_binding.py",
    "reddog_artifact_generation_model_capability.py",
    "reddog_artifact_generation_provider_contract.py",
    "reddog_artifact_generation_result.py",
    "reddog_foundups_fusion_artifact_provider.py",
    "reddog_model_runtime_verifier_bootstrap.py",
    "reddog_queue_model_runtime_authority.py",
    "reddog_runtime_json_read.py",
)
TOUCHED_FUNCTIONS = {
    "reddog_bounded_artifact_generation_runtime.py": (
        "_model_runtime_binding",
        "_run_bounded_artifact_model",
        "_validate_generation_request",
    ),
}


def test_reddog_model_runtime_adapters_are_wsp62_bounded() -> None:
    for name in BOUNDED_MODULES:
        source = (SRC_ROOT / name).read_text(encoding="utf-8")
        assert len(source.splitlines()) <= 200, name
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno - node.lineno + 1 <= 50, (
                    name,
                    node.name,
                )
            if isinstance(node, ast.ClassDef):
                assert node.end_lineno - node.lineno + 1 <= 200, (
                    name,
                    node.name,
                )


def test_touched_existing_bridge_functions_remain_bounded() -> None:
    for name, functions in TOUCHED_FUNCTIONS.items():
        tree = ast.parse((SRC_ROOT / name).read_text(encoding="utf-8"))
        sizes = {
            node.name: node.end_lineno - node.lineno + 1
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert all(sizes[function] <= 60 for function in functions)


def test_model_runtime_integration_tests_remain_bounded() -> None:
    path = Path(__file__).with_name(
        "test_reddog_resident_queue_model_runtime_artifact_integration.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    sizes = [
        node.end_lineno - node.lineno + 1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert max(sizes) <= 60
