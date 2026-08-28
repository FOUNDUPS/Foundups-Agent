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
import importlib.util
import json
import subprocess
import warnings
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "scripts" / "reddog_backend_manifest.json"
SCHEMA_VERSION = "reddog_backend_manifest.v3"
BACKEND_API_VERSION = 2
GRAPH_VERSION = 2
BRIDGE_FILES = (
    "scripts/advisory_model_once.py",
    "scripts/reddog_authoritative_work_state_query_once.py",
    "scripts/reddog_extension_live_enqueue_invoke_once.py",
    "scripts/reddog_extension_wre_spine_invoke_once.py",
    "scripts/reddog_github_permission_probe_once.py",
    "scripts/reddog_holoindex_incident_repair_once.py",
    "scripts/reddog_holoindex_blocked_request_recovery_once.py",
    "scripts/reddog_holoindex_candidate_acceptance.py",
    "scripts/reddog_holoindex_owner_query_once.py",
    "scripts/reddog_holoindex_postmerge_runtime_once.py",
    "scripts/reddog_judgment_verifier_once.py",
    "scripts/reddog_model_freshness_query_once.py",
    "scripts/reddog_model_runtime_binding_query_once.py",
    "scripts/reddog_operator_wardrobe_selection_once.py",
    "scripts/reddog_repair_guard_once.py",
    "scripts/reddog_resident_architect_session_once.py",
    "scripts/reddog_start_operations_control_once.py",
)
EXECUTABLE_FILES = (*BRIDGE_FILES, "holo_index.py")
STATIC_RUNTIME_FILES = (
    "holo_index/docs/HOLO_INDEX_MACHINE_LANGUAGE_SPEC_0102.json",
    "holo_index/query_result_contract_schema.py",
    "extensions/reddog/start_operations_python_bootstrap.py",
    "scripts/reddog_holoindex_owner_service_once.py",
    "modules/infrastructure/wre_core/src/wre_pytest_exact_id_collector.py",
    "modules/infrastructure/wre_core/src/"
    "wre_test_registry_differential_plan_runtime.py",
    "modules/communication/moltbot_bridge/src/"
    "reddog_signer_system_service_entrypoint.py",
    "modules/communication/moltbot_bridge/src/"
    "foundup_verified_outcome_root_authority_service_entrypoint.py",
    "modules/communication/moltbot_bridge/src/"
    "foundup_verified_outcome_root_authority_provision_entrypoint.py",
    "modules/communication/moltbot_bridge/skillz/reddog_operations/SKILLz.md",
    "modules/infrastructure/wre_core/skillz/skills_registry_v2.json",
    "modules/infrastructure/wre_core/skillz/"
    "auto_test_registry_audit/SKILLz.md",
    "modules/ai_intelligence/ai_overseer/skillz/"
    "m2m_holo_retrieval_benchmark/retrieval_corpus_v1.json",
)
REPOSITORY_MARKERS = (
    "main.py",
    "holo_index.py",
    "WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md",
)
DYNAMIC_IMPORT_NAMES = frozenset({"__import__", "import_module"})
DYNAMIC_FILE_LOAD_NAMES = frozenset({"spec_from_file_location", "SourceFileLoader", "run_path"})
DYNAMIC_IMPORT_GLOBS = {
    "holo_index/qwen_advisor/holodae_coordinator.py": ("modules/**/*_gate.py",),
    "modules/infrastructure/wre_core/wre_master_orchestrator/src/wre_master_orchestrator.py": (
        "modules/**/executor.py",
    ),
}
DYNAMIC_IMPORT_MODULES = {
    "modules/communication/moltbot_bridge/src/reddog_backend_architect_determination_runtime.py": (
        "scripts.advisory_model_once",
    ),
    "modules/communication/moltbot_bridge/src/reddog_bounded_artifact_generation_runtime.py": (
        "scripts.advisory_model_once",
    ),
    "modules/communication/moltbot_bridge/src/reddog_foundups_fusion_artifact_provider.py": (
        "scripts.advisory_model_once",
    ),
    "modules/communication/moltbot_bridge/src/reddog_readonly_0102_audit_worker_runtime.py": (
        "scripts.advisory_model_once",
    ),
    "modules/infrastructure/foundups_mcp_bridge/src/holo_tools.py": (
        "modules.foundups.src.foundup_registry_loader",
    ),
    "modules/foundups/agent/src/__init__.py": (
        "modules.foundups.agent.src.hermes_adapter",
        "modules.foundups.agent.src.hermes_model_router",
    ),
}
_TRACKED_FILE_CACHE: tuple[str, ...] | None = None
_TRACKED_FILE_SET_CACHE: frozenset[str] | None = None


def _normalized_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def _digest(path: Path) -> str:
    return hashlib.sha256(_normalized_bytes(path)).hexdigest()


def _resolve_local_module(module_name: str) -> Path | None:
    candidate = REPO_ROOT.joinpath(*module_name.split("."))
    tracked_by_casefold = {
        relative.casefold(): relative for relative in _tracked_files()
    }
    for path in (candidate.with_suffix(".py"), candidate / "__init__.py"):
        if path.is_file():
            relative = path.relative_to(REPO_ROOT).as_posix()
            canonical = tracked_by_casefold.get(relative.casefold())
            return REPO_ROOT / canonical if canonical is not None else path
    return None


def _package_parts(path: Path) -> list[str]:
    relative = path.relative_to(REPO_ROOT)
    parts = list(relative.with_suffix("").parts)
    return parts[:-1]


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
    global _TRACKED_FILE_CACHE
    if _TRACKED_FILE_CACHE is not None:
        return _TRACKED_FILE_CACHE
    output = subprocess.check_output(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
    )
    _TRACKED_FILE_CACHE = tuple(
        line.strip().replace("\\", "/")
        for line in output.splitlines()
        if line.strip()
    )
    return _TRACKED_FILE_CACHE


def _tracked_file_set() -> frozenset[str]:
    global _TRACKED_FILE_SET_CACHE
    if _TRACKED_FILE_SET_CACHE is None:
        _TRACKED_FILE_SET_CACHE = frozenset(_tracked_files())
    return _TRACKED_FILE_SET_CACHE


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


def _dynamic_module_name(
    value: str, node: ast.Call, package: list[str], relative: str
) -> str:
    if not value.startswith("."):
        return value
    package_name = ".".join(package)
    if len(node.args) > 1:
        package_arg = node.args[1]
        if isinstance(package_arg, ast.Constant) and isinstance(package_arg.value, str):
            package_name = package_arg.value
        elif not isinstance(package_arg, ast.Name) or package_arg.id != "__name__":
            raise ValueError(
                f"undeclared_dynamic_relative_package:{relative}:{node.lineno}"
            )
    try:
        return importlib.util.resolve_name(value, package_name)
    except (ImportError, ValueError) as exc:
        raise ValueError(
            f"invalid_dynamic_relative_import:{relative}:{node.lineno}"
        ) from exc


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
        elif isinstance(node, ast.Call):
            called = _called_name(node)
            if called in DYNAMIC_FILE_LOAD_NAMES:
                dynamic_paths.extend(_declared_dynamic_paths(relative))
            elif called in DYNAMIC_IMPORT_NAMES:
                if not node.args or not isinstance(node.args[0], ast.Constant):
                    dynamic_paths.extend(_declared_dynamic_paths(relative))
                    continue
                value = node.args[0].value
                if not isinstance(value, str):
                    raise ValueError(f"nonstring_dynamic_import:{relative}:{node.lineno}")
                names.append(_dynamic_module_name(value, node, package, relative))
    return names, dynamic_paths


def _parse_source(path: Path, relative: str) -> ast.AST:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        return ast.parse(path.read_text(encoding="utf-8-sig"), filename=relative)


def _dependency_closure() -> tuple[str, ...]:
    queue = [
        REPO_ROOT / relative
        for relative in (*EXECUTABLE_FILES, *STATIC_RUNTIME_FILES)
        if relative.endswith(".py")
    ]
    observed: set[str] = set()
    tracked = _tracked_file_set()
    while queue:
        path = queue.pop()
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative in observed:
            continue
        if not path.is_file():
            raise FileNotFoundError(relative)
        if relative not in tracked:
            raise ValueError(f"untracked_runtime_dependency:{relative}")
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
    runtime_files = tuple(
        sorted({*_dependency_closure(), *STATIC_RUNTIME_FILES})
    )
    missing_static = [
        relative
        for relative in STATIC_RUNTIME_FILES
        if relative not in _tracked_file_set()
        or not (REPO_ROOT / relative).is_file()
    ]
    if missing_static:
        raise FileNotFoundError(",".join(missing_static))
    runtime_digests = {
        relative: _digest(REPO_ROOT / relative)
        for relative in runtime_files
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "product": "foundups-agent-reddog-backend",
        "backend_api_version": BACKEND_API_VERSION,
        "runtime_dependency_graph_version": GRAPH_VERSION,
        "required_executable_files": list(EXECUTABLE_FILES),
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
