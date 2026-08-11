"""Deterministic static classification for tracked Python test files."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import warnings

from .wre_test_registry_ast import (
    module_effects,
    node_name,
)

SUITE_CLASSES = {"unit", "integration", "manual", "operational"}
_ARCHIVE_PARTS = {"_archive", "archive", "archived", "modules_archive"}
_DANGEROUS_CALLS = {
    "exit", "quit", "sys.exit", "os._exit",
    "subprocess.call", "subprocess.check_call", "subprocess.check_output",
    "subprocess.run", "subprocess.Popen", "uvicorn.run",
    "webdriver.Chrome", "webdriver.Firefox", "webdriver.Edge",
}
_DANGEROUS_PREFIXES = (
    "requests.", "httpx.", "socket.", "urllib.request.",
)
_SLUG = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class TestFileClassification:
    suite_class: str
    owner: str
    capabilities: tuple[str, ...]
    quarantine_reasons: tuple[str, ...]
    collectable: bool
    description: str


def classify_test_file(repo_root: Path, relative_path: str) -> TestFileClassification:
    """Classify one repository-relative, tracked ``test_*.py`` file."""
    path = PurePosixPath(relative_path)
    owner = owner_for_path(path)
    target = repo_root / path
    reasons: set[str] = set()
    capabilities: set[str] = set()
    description = ""
    tree: ast.Module | None = None
    try:
        source = target.read_text(encoding="utf-8", errors="strict")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(source, filename=relative_path)
        description = (ast.get_docstring(tree) or "").strip()[:500]
    except UnicodeError:
        reasons.add("non_utf8_source")
    except SyntaxError:
        reasons.add("syntax_error")
    if any(part.lower() in _ARCHIVE_PARTS for part in path.parts):
        reasons.add("archived_source")
    if tree is not None:
        _apply_effects(tree, reasons, capabilities)
    suite_class = _suite_class(path, tree, reasons)
    return TestFileClassification(
        suite_class=suite_class,
        owner=owner,
        capabilities=tuple(sorted(capabilities)),
        quarantine_reasons=tuple(sorted(reasons)),
        collectable=suite_class in {"unit", "integration"} and not reasons,
        description=description,
    )


def _apply_effects(
    tree: ast.Module, reasons: set[str], capabilities: set[str]
) -> None:
    effects = module_effects(tree)
    if any(
        call in _DANGEROUS_CALLS
        or call.endswith((".Chrome", ".Firefox", ".Edge"))
        or call.startswith(_DANGEROUS_PREFIXES)
        for call in effects.calls
    ):
        reasons.add("module_scope_external_effect")
    for active, reason in (
        (effects.stdout_mutated, "module_scope_process_stream_mutation"),
        (effects.environment_mutated, "module_scope_environment_mutation"),
        (effects.module_raise, "module_scope_raise"),
        (effects.file_write, "module_scope_file_write"),
        (effects.test_function_invoked, "module_scope_test_function_invocation"),
        (effects.local_function_invoked, "module_scope_local_function_invocation"),
    ):
        if active:
            reasons.add(reason)
    if any(call.startswith("sys.path.") for call in effects.calls):
        capabilities.add("import_path_mutation")
    if "logging.basicConfig" in effects.calls:
        capabilities.add("logging_configuration")
    capabilities.update(_capabilities(tree))


def owner_for_path(path: PurePosixPath) -> str:
    parts = path.parts
    if len(parts) >= 3 and parts[0] == "modules":
        return "/".join(parts[:3])
    if len(parts) >= 2 and parts[0] == "extensions":
        return "/".join(parts[:2])
    if parts and parts[0] in {"holo_index", "WSP_agentic", "WSP_framework", "WSP_knowledge"}:
        return parts[0]
    if parts and parts[0] == "tests":
        return "repository"
    return parts[0] if parts else "repository"


def shard_slug(owner: str, suite_class: str) -> str:
    raw = _SLUG.sub("-", f"{owner}-{suite_class}".lower()).strip("-")
    return raw[:96]


def _suite_class(
    path: PurePosixPath, tree: ast.Module | None, reasons: set[str]
) -> str:
    if "archived_source" in reasons:
        return "manual"
    if reasons:
        return "operational"
    lowered = path.as_posix().lower()
    if tree is not None and _has_pytest_mark(tree, {"integration", "e2e", "slow"}):
        return "integration"
    if any(token in lowered for token in ("/integration/", "_integration.py", "_e2e.py")):
        return "integration"
    return "unit"


def _has_pytest_mark(tree: ast.Module, marks: set[str]) -> bool:
    return any(
        isinstance(node, ast.Attribute)
        and node.attr in marks
        and node_name(node.value) == "pytest.mark"
        for node in ast.walk(tree)
    )


def _capabilities(tree: ast.Module) -> set[str]:
    names = {node_name(node) for node in ast.walk(tree)}
    result = set()
    if any(name.startswith(("selenium", "webdriver", "playwright")) for name in names):
        result.add("browser")
    if any(name.startswith(("requests", "httpx", "socket", "urllib")) for name in names):
        result.add("network")
    if any(name.startswith("subprocess") for name in names):
        result.add("process")
    if any(name.startswith(("tkinter", "PyQt", "wx")) for name in names):
        result.add("interactive")
    return result


__all__ = [
    "SUITE_CLASSES", "TestFileClassification", "classify_test_file",
    "owner_for_path", "shard_slug",
]
