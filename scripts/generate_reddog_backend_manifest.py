"""Generate the RedDog backend runtime dependency manifest.

The generator parses local Python imports without importing repository code.
Every executable bridge, resolved local dependency, and package initializer is
content-bound. Nonliteral dynamic imports fail generation because they cannot
be represented by a deterministic dependency closure.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import subprocess
import warnings
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "scripts" / "reddog_backend_manifest.json"
SCHEMA_VERSION = "reddog_backend_manifest.v2"
BACKEND_API_VERSION = 2
GRAPH_VERSION = 1
BRIDGE_FILES = (
    "scripts/advisory_model_once.py",
    "scripts/reddog_extension_live_enqueue_invoke_once.py",
    "scripts/reddog_extension_wre_spine_invoke_once.py",
    "scripts/reddog_github_permission_probe_once.py",
    "scripts/reddog_holoindex_owner_query_once.py",
    "scripts/reddog_judgment_verifier_once.py",
    "scripts/reddog_operator_wardrobe_selection_once.py",
    "scripts/reddog_repair_guard_once.py",
    "scripts/reddog_resident_architect_session_once.py",
)
REPOSITORY_MARKERS = (
    "main.py",
    "holo_index.py",
    "WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md",
)
DYNAMIC_IMPORT_NAMES = frozenset({"__import__", "import_module"})
DYNAMIC_IMPORT_GLOBS = {
    "holo_index/qwen_advisor/holodae_coordinator.py": ("modules/**/*_gate.py",),
}
DYNAMIC_IMPORT_MODULES = {
    "modules/foundups/agent/src/__init__.py": (
        "modules.foundups.agent.src.hermes_adapter",
        "modules.foundups.agent.src.hermes_model_router",
    ),
}


def _normalized_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def _digest(path: Path) -> str:
    return hashlib.sha256(_normalized_bytes(path)).hexdigest()


def _resolve_local_module(module_name: str) -> Path | None:
    candidate = REPO_ROOT.joinpath(*module_name.split("."))
    for path in (candidate.with_suffix(".py"), candidate / "__init__.py"):
        if path.is_file():
            return path
    return None


def _package_parts(path: Path) -> list[str]:
    relative = path.relative_to(REPO_ROOT)
    parts = list(relative.with_suffix("").parts)
    return parts if path.name == "__init__.py" else parts[:-1]


def _parent_initializers(path: Path) -> Iterable[Path]:
    current = path.parent
    while current != REPO_ROOT and REPO_ROOT in current.parents:
        initializer = current / "__init__.py"
        if initializer.is_file():
            yield initializer
        current = current.parent


def _called_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _tracked_files() -> tuple[str, ...]:
    output = subprocess.check_output(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
    )
    return tuple(line.strip() for line in output.splitlines() if line.strip())


def _declared_dynamic_paths(relative: str) -> tuple[Path, ...]:
    patterns = DYNAMIC_IMPORT_GLOBS.get(relative, ())
    module_names = DYNAMIC_IMPORT_MODULES.get(relative, ())
    if not patterns and not module_names:
        raise ValueError(f"undeclared_dynamic_import:{relative}")
    matches = [
        REPO_ROOT / tracked
        for tracked in _tracked_files()
        if any(fnmatch.fnmatchcase(tracked, pattern) for pattern in patterns)
    ]
    matches.extend(
        resolved
        for module_name in module_names
        if (resolved := _resolve_local_module(module_name)) is not None
    )
    if len(matches) < len(module_names) or not matches:
        raise ValueError(f"empty_dynamic_import_scope:{relative}")
    return tuple(dict.fromkeys(matches))


def _from_import_names(node: ast.ImportFrom, package: list[str]) -> list[str]:
    base = [] if node.level == 0 else package[: max(0, len(package) - node.level + 1)]
    if node.module:
        base.extend(node.module.split("."))
    names = [".".join(base)] if base else []
    names.extend(
        ".".join([*base, alias.name])
        for alias in node.names
        if alias.name != "*"
    )
    return names


def _imports(tree: ast.AST, path: Path) -> tuple[list[str], list[Path]]:
    package = _package_parts(path)
    names: list[str] = []
    dynamic_paths: list[Path] = []
    relative = path.relative_to(REPO_ROOT).as_posix()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.extend(_from_import_names(node, package))
        elif isinstance(node, ast.Call) and _called_name(node) in DYNAMIC_IMPORT_NAMES:
            if not node.args or not isinstance(node.args[0], ast.Constant):
                dynamic_paths.extend(_declared_dynamic_paths(relative))
                continue
            value = node.args[0].value
            if not isinstance(value, str):
                raise ValueError(f"nonstring_dynamic_import:{relative}:{node.lineno}")
            names.append(value)
    return names, dynamic_paths


def _parse_source(path: Path, relative: str) -> ast.AST:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        return ast.parse(path.read_text(encoding="utf-8-sig"), filename=relative)


def _dependency_closure() -> tuple[str, ...]:
    queue = [REPO_ROOT / relative for relative in BRIDGE_FILES]
    observed: set[str] = set()
    while queue:
        path = queue.pop()
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative in observed:
            continue
        if not path.is_file():
            raise FileNotFoundError(relative)
        observed.add(relative)
        tree = _parse_source(path, relative)
        queue.extend(_parent_initializers(path))
        import_names, dynamic_paths = _imports(tree, path)
        queue.extend(dynamic_paths)
        for module_name in import_names:
            resolved = _resolve_local_module(module_name)
            if resolved is not None:
                queue.append(resolved)
    return tuple(sorted(observed))


def build_manifest() -> dict[str, object]:
    runtime_files = _dependency_closure()
    runtime_digests = {
        relative: _digest(REPO_ROOT / relative)
        for relative in runtime_files
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "product": "foundups-agent-reddog-backend",
        "backend_api_version": BACKEND_API_VERSION,
        "runtime_dependency_graph_version": GRAPH_VERSION,
        "required_bridge_files": list(BRIDGE_FILES),
        "required_bridge_sha256": {
            relative: runtime_digests[relative]
            for relative in BRIDGE_FILES
        },
        "required_runtime_files": list(runtime_files),
        "required_runtime_sha256": runtime_digests,
        "required_repository_markers": list(REPOSITORY_MARKERS),
    }


def canonical_manifest_digest(manifest: dict[str, object]) -> str:
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest = build_manifest()
    if args.check:
        current = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if current != manifest:
            raise SystemExit("RedDog backend manifest is stale")
    if args.write:
        MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(canonical_manifest_digest(manifest))
    print(f"runtime_files={len(manifest['required_runtime_files'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
