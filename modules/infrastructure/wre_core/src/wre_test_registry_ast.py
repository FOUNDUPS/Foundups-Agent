"""Small AST helpers shared by canonical test-registry classification."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any

_WRITE_METHODS = {
    "mkdir", "rename", "replace", "rmdir", "touch", "unlink",
    "write_bytes", "write_text",
}


@dataclass(frozen=True)
class ModuleEffects:
    calls: frozenset[str]
    stdout_mutated: bool
    environment_mutated: bool
    module_raise: bool
    file_write: bool
    test_function_invoked: bool
    local_function_invoked: bool


class _Visitor(ast.NodeVisitor):
    def __init__(self, aliases: dict[str, str]) -> None:
        self.aliases = aliases
        self.calls: set[str] = set()
        self.stdout_mutated = False
        self.environment_mutated = False
        self.module_raise = False
        self.file_write = False
        self.test_functions: set[str] = set()
        self.local_functions: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.local_functions.add(node.name)
        if node.name.startswith("test_"):
            self.test_functions.add(node.name)
        for value in (*node.decorator_list, *node.args.defaults):
            self.visit(value)
        for value in node.args.kw_defaults:
            if value is not None:
                self.visit(value)
        annotations = [node.returns, *(
            arg.annotation for arg in (
                *node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs,
            )
        )]
        annotations.extend(
            arg.annotation for arg in (node.args.vararg, node.args.kwarg) if arg
        )
        for value in annotations:
            if value is not None:
                self.visit(value)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for value in (*node.decorator_list, *node.bases):
            self.visit(value)
        for keyword in node.keywords:
            self.visit(keyword.value)
        for statement in node.body:
            self.visit(statement)

    def visit_If(self, node: ast.If) -> None:
        if not is_main_guard(node.test):
            self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            name = node_name(target, self.aliases)
            self.stdout_mutated |= name in {"sys.stdout", "sys.stderr"}
            self.environment_mutated |= name.startswith("os.environ")
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.stdout_mutated |= node_name(node.target, self.aliases) in {
            "sys.stdout", "sys.stderr",
        }
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        called = node_name(node.func, self.aliases)
        if called:
            self.calls.add(called)
        method = called.rsplit(".", 1)[-1]
        self.file_write |= method in _WRITE_METHODS
        self.file_write |= called == "open" and open_call_writes(node)
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        self.module_raise = True
        self.generic_visit(node)


def module_effects(tree: ast.Module) -> ModuleEffects:
    visitor = _Visitor(import_aliases(tree))
    visitor.visit(tree)
    return ModuleEffects(
        calls=frozenset(visitor.calls),
        stdout_mutated=visitor.stdout_mutated,
        environment_mutated=visitor.environment_mutated,
        module_raise=visitor.module_raise,
        file_write=visitor.file_write,
        test_function_invoked=bool(visitor.calls & visitor.test_functions),
        local_function_invoked=bool(visitor.calls & visitor.local_functions),
    )


def node_name(node: Any, aliases: dict[str, str] | None = None) -> str:
    if isinstance(node, ast.Name):
        return (aliases or {}).get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parent = node_name(node.value, aliases)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Subscript):
        return node_name(node.value, aliases)
    return ""


def import_aliases(tree: ast.Module) -> dict[str, str]:
    result: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                result[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                result[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return result


def open_call_writes(node: ast.Call) -> bool:
    mode: Any = node.args[1] if len(node.args) > 1 else None
    for keyword in node.keywords:
        if keyword.arg == "mode":
            mode = keyword.value
    return bool(
        isinstance(mode, ast.Constant) and isinstance(mode.value, str)
        and any(flag in mode.value for flag in "wax+")
    )


def is_main_guard(node: ast.expr) -> bool:
    if not isinstance(node, ast.Compare) or len(node.ops) != 1:
        return False
    if not isinstance(node.ops[0], ast.Eq) or len(node.comparators) != 1:
        return False
    return {_literal(node.left), _literal(node.comparators[0])} == {
        "__name__", "__main__",
    }


def _literal(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


__all__ = ["ModuleEffects", "module_effects", "node_name"]
