"""Exact callable-entrypoint validation for the grant-authority zipapp."""

from __future__ import annotations

import ast

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
)


def validate_grant_service_entrypoint(tree: ast.AST) -> None:
    """Require one undecorated synchronous main callable with the shim ABI."""

    body = tuple(getattr(tree, "body", ()))
    candidates = tuple(
        node
        for node in body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    if len(candidates) != 1 or not _valid_signature(candidates[0]):
        raise RuntimeArtifactManifestError("grant_service_archive_entrypoint_invalid")
    if any(_rebinds_main(node, candidates[0]) for node in body):
        raise RuntimeArtifactManifestError("grant_service_archive_entrypoint_invalid")


def _valid_signature(node: ast.FunctionDef) -> bool:
    args = node.args
    positional = tuple(args.posonlyargs) + tuple(args.args)
    no_arguments = not positional and not args.defaults
    optional_argv = (
        not args.posonlyargs
        and len(args.args) == 1
        and args.args[0].arg == "argv"
        and len(args.defaults) == 1
        and isinstance(args.defaults[0], ast.Constant)
        and args.defaults[0].value is None
    )
    return bool(
        not node.decorator_list
        and node.returns is None
        and all(item.annotation is None for item in positional)
        and not args.vararg
        and not args.kwarg
        and not args.kwonlyargs
        and not args.kw_defaults
        and not _contains_yield(node)
        and (no_arguments or optional_argv)
    )


def _contains_yield(node: ast.FunctionDef) -> bool:
    pending = list(node.body)
    while pending:
        item = pending.pop()
        if isinstance(item, (ast.Yield, ast.YieldFrom)):
            return True
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        pending.extend(ast.iter_child_nodes(item))
    return False


def _rebinds_main(node: ast.AST, accepted: ast.FunctionDef) -> bool:
    if node is accepted:
        return False
    for item in ast.walk(node):
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if item.name == "main":
                return True
        if isinstance(item, ast.Name) and item.id == "main" and isinstance(
            item.ctx, (ast.Store, ast.Del)
        ):
            return True
        if isinstance(item, ast.alias):
            local = item.asname or item.name.split(".", 1)[0]
            if local == "main":
                return True
    return False


__all__ = ["validate_grant_service_entrypoint"]
