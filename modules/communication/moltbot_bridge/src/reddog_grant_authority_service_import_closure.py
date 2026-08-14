"""Static import-reference defense in depth; this is not a Python sandbox."""

from __future__ import annotations

import ast
import sys
from typing import Mapping

from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_entrypoint_validation import (
    validate_grant_service_entrypoint,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_import_member_validation import (
    resolve_relative_import,
    verify_local_from_members,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
)


def validate_grant_service_static_imports(entries: Mapping[str, bytes]) -> None:
    """Validate direct imports and reject common dynamic-loader spellings."""

    modules, packages = _archive_modules(entries)
    service = modules.get("reddog_grant_authority_service")
    if service is None:
        raise RuntimeArtifactManifestError("grant_service_archive_entrypoint_invalid")
    validate_grant_service_entrypoint(service)
    _require_packages(modules, packages)
    _reject_stdlib_shadowing(modules)
    for name, tree in modules.items():
        _reject_common_dynamic_loading(tree)
        _reject_unverifiable_stdlib_imports(tree)
        for imported in _imports(name, tree, name in packages):
            if imported.split(".", 1)[0] in sys.stdlib_module_names:
                continue
            if not _module_present(imported, modules):
                raise RuntimeArtifactManifestError(
                    "grant_service_archive_dependency_missing"
                )
        verify_local_from_members(name, tree, modules, packages)


def _reject_unverifiable_stdlib_imports(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(
                "." in item.name
                and item.name.split(".", 1)[0] in sys.stdlib_module_names
                for item in node.names
            ):
                raise RuntimeArtifactManifestError(
                    "grant_service_archive_stdlib_member_unverifiable"
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "__future__" and all(
                item.name == "annotations" for item in node.names
            ):
                continue
            if module.split(".", 1)[0] in sys.stdlib_module_names:
                raise RuntimeArtifactManifestError(
                    "grant_service_archive_stdlib_member_unverifiable"
                )


def _archive_modules(
    entries: Mapping[str, bytes],
) -> tuple[dict[str, ast.AST], frozenset[str]]:
    modules: dict[str, ast.AST] = {}
    packages: set[str] = set()
    for path, body in entries.items():
        if path.endswith(".json"):
            continue
        if not path.endswith(".py"):
            raise RuntimeArtifactManifestError("grant_service_archive_member_invalid")
        name = path[:-3].replace("/", ".")
        if name.endswith(".__init__"):
            name = name[:-9]
            packages.add(name)
        try:
            tree = ast.parse(body.decode("ascii"), filename=path)
        except (UnicodeDecodeError, SyntaxError) as exc:
            raise RuntimeArtifactManifestError("grant_service_archive_python_invalid") from exc
        modules[name] = tree
    return modules, frozenset(packages)


def _require_packages(
    modules: Mapping[str, ast.AST], packages: frozenset[str]
) -> None:
    for name in modules:
        parts = name.split(".")
        for index in range(1, len(parts)):
            if ".".join(parts[:index]) not in packages:
                raise RuntimeArtifactManifestError(
                    "grant_service_archive_package_missing"
                )


def _reject_stdlib_shadowing(modules: Mapping[str, ast.AST]) -> None:
    if any(
        name not in {"__main__"}
        and name.split(".", 1)[0] in sys.stdlib_module_names
        for name in modules
    ):
        raise RuntimeArtifactManifestError("grant_service_archive_stdlib_shadowed")


def _imports(module: str, tree: ast.AST, is_package: bool) -> tuple[str, ...]:
    found: set[str] = set()
    package = module if is_package else module.rsplit(".", 1)[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = resolve_relative_import(package, node.module or "", node.level)
            if base:
                found.add(base)
            if node.level and not node.module:
                found.update(f"{base}.{alias.name}" for alias in node.names)
    return tuple(sorted(found))


def _module_present(name: str, modules: Mapping[str, ast.AST]) -> bool:
    return name in modules or any(item.startswith(name + ".") for item in modules)


def _reject_common_dynamic_loading(tree: ast.AST) -> None:
    aliases = _import_aliases(tree)
    forbidden = {
        "__import__", "__builtins__", "__path__", "compile", "delattr", "eval",
        "exec", "getattr", "globals", "locals", "setattr", "vars",
        "importlib", "pkgutil", "runpy", "zipimport",
        "ctypes", "builtins", "sys.meta_path", "sys.modules", "sys.path",
        "sys.path_hooks",
    }
    for node in ast.walk(tree):
        name = _resolved_name(node, aliases)
        if any(name == item or name.startswith(item + ".") for item in forbidden):
            raise RuntimeArtifactManifestError(
                "grant_service_archive_dynamic_load_forbidden"
            )
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            if any(
                _resolved_name(target, aliases) == "sys.path"
                for target in _targets(node)
            ):
                raise RuntimeArtifactManifestError(
                    "grant_service_archive_dynamic_load_forbidden"
                )


def _import_aliases(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                local = item.asname or item.name.split(".", 1)[0]
                aliases[local] = item.name if item.asname else local
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for item in node.names:
                aliases[item.asname or item.name] = f"{node.module}.{item.name}"
    for _ in range(len(aliases) + 1):
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            value = _resolved_name(node.value, aliases)
            if isinstance(target, ast.Name) and value and aliases.get(target.id) != value:
                aliases[target.id] = value
                changed = True
        if not changed:
            break
    return aliases


def _targets(node: ast.AST) -> tuple[ast.AST, ...]:
    value = getattr(node, "targets", None)
    if isinstance(value, list):
        return tuple(value)
    target = getattr(node, "target", None)
    return (target,) if isinstance(target, ast.AST) else ()


def _resolved_name(value: ast.AST, aliases: Mapping[str, str]) -> str:
    if isinstance(value, ast.Name):
        return aliases.get(value.id, value.id)
    if isinstance(value, ast.Attribute):
        prefix = _resolved_name(value.value, aliases)
        return f"{prefix}.{value.attr}" if prefix else value.attr
    if isinstance(value, ast.Subscript):
        return _resolved_name(value.value, aliases)
    return ""


__all__ = ["validate_grant_service_static_imports"]
