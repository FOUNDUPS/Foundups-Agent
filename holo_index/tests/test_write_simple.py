"""Regression coverage for sandboxed filesystem write probes."""

from __future__ import annotations

import ast
from pathlib import Path, PureWindowsPath


def test_write_probe_uses_pytest_sandbox(tmp_path: Path) -> None:
    target = tmp_path / "test_write.txt"

    target.write_text("WRITE SUCCESS", encoding="ascii")

    assert target.read_text(encoding="ascii") == "WRITE SUCCESS"
    assert target.parent == tmp_path


def test_write_probe_has_no_import_time_effect_or_checkout_path() -> None:
    source_path = Path(__file__)
    source = source_path.read_text(encoding="utf-8")
    module = ast.parse(source)
    imports = [node for node in module.body if isinstance(node, ast.Import)]
    import_from = [node for node in module.body if isinstance(node, ast.ImportFrom)]
    functions = [node for node in module.body if isinstance(node, ast.FunctionDef)]
    docstrings = [
        node
        for node in module.body
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    ]
    allowed_nodes = [*imports, *import_from, *functions, *docstrings]

    assert len(allowed_nodes) == len(module.body)
    assert [[alias.name for alias in node.names] for node in imports] == [["ast"]]
    assert [(node.module, [alias.name for alias in node.names]) for node in import_from] == [
        ("__future__", ["annotations"]),
        ("pathlib", ["Path", "PureWindowsPath"]),
    ]
    for function in functions:
        assert function.decorator_list == []
        assert function.args.defaults == []
        assert all(value is None for value in function.args.kw_defaults)
        assert not any(isinstance(node, ast.Call) for node in ast.walk(function.returns))
    path_literals = [
        node.value
        for node in ast.walk(module)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    assert not any(PureWindowsPath(value).is_absolute() for value in path_literals)
