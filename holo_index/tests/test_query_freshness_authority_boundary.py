"""Dependency-inversion contract for the neutral query freshness authority."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
NEUTRAL_MODULE = PROJECT_ROOT / "holo_index" / "query_freshness_gate.py"
QUERY_ADMISSION = PROJECT_ROOT / "holo_index" / "query_admission.py"
BRIDGE_ADAPTER = (
    PROJECT_ROOT
    / "modules"
    / "infrastructure"
    / "foundups_mcp_bridge"
    / "src"
    / "holo_query_freshness_gate.py"
)
FORBIDDEN_IMPORT_PREFIXES = (
    "modules",
    "fastapi",
    "uvicorn",
    "requests",
    "httpx",
    "chromadb",
    "sentence_transformers",
    "torch",
    "openai",
)


def _absolute_imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.append(node.module)
    return tuple(names)


def test_neutral_authority_exists_and_has_no_forbidden_direct_imports() -> None:
    assert NEUTRAL_MODULE.is_file()
    assert not any(
        name == prefix or name.startswith(f"{prefix}.")
        for name in _absolute_imports(NEUTRAL_MODULE)
        for prefix in FORBIDDEN_IMPORT_PREFIXES
    )


def test_query_admission_depends_only_on_holoindex_freshness_authority() -> None:
    imports = _absolute_imports(QUERY_ADMISSION)
    assert "holo_index.query_freshness_gate" in imports
    assert not any(name.startswith("modules.") for name in imports)


def test_neutral_authority_import_does_not_load_transport_or_provider_modules() -> None:
    script = """
import sys
before = set(sys.modules)
import holo_index.query_freshness_gate  # noqa: F401
loaded = set(sys.modules).difference(before)
forbidden = (
    "modules", "fastapi", "uvicorn", "requests", "httpx", "chromadb",
    "sentence_transformers", "torch", "openai",
)
bad = sorted(
    name for name in loaded
    if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden)
)
raise SystemExit("\\n".join(bad) if bad else 0)
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout or completed.stderr


def test_bridge_adapter_reexports_exact_neutral_public_authority() -> None:
    from holo_index import query_freshness_gate as neutral
    from modules.infrastructure.foundups_mcp_bridge.src import (
        holo_query_freshness_gate as bridge,
    )

    assert tuple(bridge.__all__) == tuple(neutral.__all__)
    for name in neutral.__all__:
        assert getattr(bridge, name) is getattr(neutral, name)


def test_bridge_adapter_contains_no_freshness_decision_implementation() -> None:
    tree = ast.parse(
        BRIDGE_ADAPTER.read_text(encoding="utf-8"),
        filename=str(BRIDGE_ADAPTER),
    )
    assert not any(
        isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        for node in tree.body
    )
