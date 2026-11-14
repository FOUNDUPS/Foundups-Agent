"""Validate local from-import members in the grant service archive."""

from __future__ import annotations

import ast
from typing import Mapping

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
)


def verify_local_from_members(
    module: str,
    tree: ast.AST,
    modules: Mapping[str, ast.AST],
    packages: frozenset[str],
) -> None:
    """Reject missing or star-imported members from archive-local modules."""

    package = module if module in packages else module.rsplit(".", 1)[0]
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        base = resolve_relative_import(package, node.module or "", node.level)
        if base == "__invalid_relative_import__":
            raise RuntimeArtifactManifestError(
                "grant_service_archive_dependency_missing"
            )
        if base not in modules:
            continue
        exported = _top_level_names(modules[base])
        for item in node.names:
            child = f"{base}.{item.name}"
            if item.name == "*" or (
                child not in modules and item.name not in exported
            ):
                raise RuntimeArtifactManifestError(
                    "grant_service_archive_dependency_missing"
                )


def resolve_relative_import(package: str, name: str, level: int) -> str:
    if level == 0:
        return name
    parts = package.split(".") if package else []
    if level > len(parts):
        return "__invalid_relative_import__"
    prefix = parts[: len(parts) - level + 1]
    return ".".join((*prefix, name) if name else prefix)


def _top_level_names(tree: ast.AST) -> frozenset[str]:
    names: set[str] = set()
    for node in getattr(tree, "body", ()):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update(
                item.asname or item.name.split(".", 1)[0]
                for item in node.names
            )
        elif isinstance(node, ast.Assign) or (
            isinstance(node, ast.AnnAssign) and node.value is not None
        ):
            names.update(
                item.id
                for item in ast.walk(node)
                if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Store)
            )
        elif isinstance(node, ast.Delete):
            names.difference_update(
                item.id for item in ast.walk(node) if isinstance(item, ast.Name)
            )
    return frozenset(names)


__all__ = ["resolve_relative_import", "verify_local_from_members"]
