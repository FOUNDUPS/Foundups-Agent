"""Content binding for the HoloIndex retrieval modules a query owner loads."""

from __future__ import annotations

import hashlib
import importlib
import os
import stat
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Mapping

from holo_index.query_receipt import digest_json


MAX_RANKER_MODULE_BYTES = 4 * 1024 * 1024
RANKER_RUNTIME_MODULES = (
    ("holo_index.core.holo_index", "holo_index/core/holo_index.py"),
    ("holo_index.core.search_engine", "holo_index/core/search_engine.py"),
    ("holo_index.core.collection_search", "holo_index/core/collection_search.py"),
    ("holo_index.core.backend_routing", "holo_index/core/backend_routing.py"),
    (
        "holo_index.core.collection_injections",
        "holo_index/core/collection_injections.py",
    ),
    ("holo_index.tier0_retrieval", "holo_index/tier0_retrieval.py"),
    (
        "holo_index.module_intent_snapshot",
        "holo_index/module_intent_snapshot.py",
    ),
    ("holo_index.document_truth", "holo_index/document_truth.py"),
    (
        "modules.infrastructure.foundups_mcp_bridge.src.holo_query_service_response",
        "modules/infrastructure/foundups_mcp_bridge/src/holo_query_service_response.py",
    ),
    (
        "modules.infrastructure.foundups_mcp_bridge.src.holo_query_path_projection",
        "modules/infrastructure/foundups_mcp_bridge/src/holo_query_path_projection.py",
    ),
    (
        "modules.infrastructure.foundups_mcp_bridge.src.holo_query_service_replica",
        "modules/infrastructure/foundups_mcp_bridge/src/holo_query_service_replica.py",
    ),
    (
        "modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_adapter",
        "modules/infrastructure/foundups_mcp_bridge/src/holo_query_snapshot_adapter.py",
    ),
)
_WINDOWS_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _link_or_reparse(path: Path) -> bool:
    metadata = os.lstat(path)
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    return path.is_symlink() or bool(attributes & _WINDOWS_REPARSE_POINT)


def _exact_runtime_file(root: Path, relative_path: str) -> Path:
    resolved_root = root.resolve(strict=True)
    if not resolved_root.is_dir() or _link_or_reparse(root):
        raise ValueError("retrieval_runtime_root_invalid")
    candidate = resolved_root
    for part in relative_path.split("/"):
        candidate /= part
        if _link_or_reparse(candidate):
            raise ValueError("retrieval_runtime_path_invalid")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_file() or not resolved.is_relative_to(resolved_root):
        raise ValueError("retrieval_runtime_path_invalid")
    metadata = os.stat(resolved, follow_symlinks=False)
    if metadata.st_nlink != 1 or metadata.st_size > MAX_RANKER_MODULE_BYTES:
        raise ValueError("retrieval_runtime_file_invalid")
    return resolved


def _content_digest(path: Path) -> str:
    before = os.stat(path, follow_symlinks=False)
    payload = path.read_bytes()
    after = os.stat(path, follow_symlinks=False)
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    if identity(before) != identity(after) or len(payload) != before.st_size:
        raise ValueError("retrieval_runtime_file_changed")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def retrieval_ranker_digest_for_root(repo_root: Path | str) -> str:
    """Hash the exact retrieval policy source closure under one repository root."""

    root = Path(repo_root)
    manifest = {
        relative: _content_digest(_exact_runtime_file(root, relative))
        for _module, relative in RANKER_RUNTIME_MODULES
    }
    return digest_json(manifest)


def _loaded_runtime_root(
    module_loader: Callable[[str], ModuleType],
) -> Path:
    root: Path | None = None
    for module_name, relative in RANKER_RUNTIME_MODULES:
        module = module_loader(module_name)
        origin = Path(str(getattr(module, "__file__", "") or ""))
        parts = relative.split("/")
        if not origin.is_absolute() or len(origin.parents) < len(parts):
            raise ValueError("retrieval_runtime_module_origin_invalid")
        candidate_root = origin.resolve(strict=True).parents[len(parts) - 1]
        root = candidate_root if root is None else root
        expected = _exact_runtime_file(root, relative)
        if origin.resolve(strict=True) != expected or candidate_root != root:
            raise ValueError("retrieval_runtime_module_origin_mismatch")
    if root is None:
        raise ValueError("retrieval_runtime_modules_missing")
    return root


def loaded_retrieval_ranker_digest(
    module_loader: Callable[[str], ModuleType] = importlib.import_module,
) -> str:
    """Hash the source closure actually imported by this owner process."""

    return retrieval_ranker_digest_for_root(_loaded_runtime_root(module_loader))


def loaded_retrieval_runtime_root(
    module_loader: Callable[[str], ModuleType] = importlib.import_module,
) -> Path:
    """Return the common verified source root of the loaded ranker closure."""

    return _loaded_runtime_root(module_loader)


def is_retrieval_ranker_digest(value: Any) -> bool:
    text = value if type(value) is str else ""
    return (
        len(text) == 71
        and text.startswith("sha256:")
        and all(character in "0123456789abcdef" for character in text[7:])
    )


def retrieval_ranker_binding(value: Any) -> dict[str, str]:
    return {"retrieval_runtime_ranker_digest": str(value or "")}


def retrieval_ranker_digest_from(value: Mapping[str, Any]) -> str:
    return str(value.get("retrieval_runtime_ranker_digest") or "")


def is_retrieval_runtime_digest(value: Any) -> bool:
    """Validate any canonical SHA-256 retrieval-runtime identity."""

    return is_retrieval_ranker_digest(value)


def runtime_environment_binding(value: Any) -> dict[str, str]:
    return {"runtime_environment_digest": str(value or "")}


def runtime_environment_digest_from(value: Mapping[str, Any]) -> str:
    return str(value.get("runtime_environment_digest") or "")


def retrieval_runtime_binding(
    ranker_digest: Any, environment_digest: Any, exact_closure_verified: bool,
) -> dict[str, Any]:
    """Project the complete public retrieval-runtime identity."""

    return {
        **retrieval_ranker_binding(ranker_digest),
        **runtime_environment_binding(environment_digest),
        "runtime_environment_exact_closure_verified": exact_closure_verified is True,
    }


def retrieval_runtime_binding_from(value: Mapping[str, Any]) -> dict[str, Any]:
    return retrieval_runtime_binding(
        retrieval_ranker_digest_from(value), runtime_environment_digest_from(value),
        value.get("runtime_environment_exact_closure_verified") is True,
    )


__all__ = [
    "MAX_RANKER_MODULE_BYTES",
    "RANKER_RUNTIME_MODULES",
    "is_retrieval_ranker_digest",
    "is_retrieval_runtime_digest",
    "loaded_retrieval_ranker_digest",
    "loaded_retrieval_runtime_root",
    "retrieval_ranker_binding",
    "retrieval_runtime_binding",
    "retrieval_runtime_binding_from",
    "retrieval_ranker_digest_from",
    "retrieval_ranker_digest_for_root",
    "runtime_environment_binding",
    "runtime_environment_digest_from",
]
