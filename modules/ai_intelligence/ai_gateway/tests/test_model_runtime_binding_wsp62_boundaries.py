"""WSP 62 boundaries for the model runtime authority modules."""

from __future__ import annotations

import ast
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
BOUNDED_MODULES = (
    "model_evidence_authority_validation.py",
    "model_runtime_binding_capability.py",
    "model_runtime_binding_digest.py",
    "model_runtime_binding_evidence_dispatch.py",
    "model_runtime_binding_evidence_verifier.py",
    "model_runtime_binding_input_rehydration.py",
    "model_runtime_binding_panel_rehydration.py",
    "model_runtime_binding_use_time_verifier.py",
    "model_runtime_binding_verification_builder.py",
    "model_runtime_binding_verification_receipt.py",
    "model_runtime_binding_verified_admission.py",
)
TOUCHED_FUNCTIONS = {
    "model_panel_signed_evidence.py": ("_verify_model_panel_evidence_inputs",),
}


def test_model_runtime_authority_modules_are_wsp62_bounded() -> None:
    for name in BOUNDED_MODULES:
        path = SRC_ROOT / name
        source = path.read_text(encoding="utf-8")
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


def test_touched_existing_ai_gateway_functions_remain_bounded() -> None:
    for name, functions in TOUCHED_FUNCTIONS.items():
        tree = ast.parse((SRC_ROOT / name).read_text(encoding="utf-8"))
        sizes = {
            node.name: node.end_lineno - node.lineno + 1
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert all(sizes[function] <= 50 for function in functions)
