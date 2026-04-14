#!/usr/bin/env python3
"""
MCP Bridge Dependency Tools.

Provides module dependency perception for blast-radius analysis.
Leverages existing code_analyzer for import parsing.

Tools:
- get_module_dependencies: What does module X depend on?
- get_reverse_dependencies: What depends on module X?

WSP References:
- WSP 3: Module Organization (domain/module structure)
- WSP 72: Module Independence (cross-module boundaries)
"""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .response_schema import ok_response, error_response

logger = logging.getLogger(__name__)

# Standard library modules to exclude from dependency analysis
STDLIB_MODULES = {
    "abc", "aifc", "argparse", "array", "ast", "asyncio", "atexit",
    "base64", "binascii", "builtins", "calendar", "collections",
    "concurrent", "contextlib", "copy", "csv", "ctypes", "dataclasses",
    "datetime", "decimal", "difflib", "dis", "email", "encodings",
    "enum", "errno", "faulthandler", "fnmatch", "fractions", "functools",
    "gc", "getopt", "getpass", "glob", "gzip", "hashlib", "heapq", "hmac",
    "html", "http", "importlib", "inspect", "io", "itertools", "json",
    "keyword", "linecache", "locale", "logging", "lzma", "math", "mimetypes",
    "multiprocessing", "numbers", "operator", "os", "pathlib", "pickle",
    "platform", "pprint", "profile", "queue", "random", "re", "reprlib",
    "secrets", "select", "selectors", "shelve", "shlex", "shutil", "signal",
    "socket", "sqlite3", "ssl", "stat", "statistics", "string", "struct",
    "subprocess", "sys", "tarfile", "tempfile", "textwrap", "threading",
    "time", "timeit", "tkinter", "token", "tokenize", "traceback", "types",
    "typing", "typing_extensions", "unicodedata", "unittest", "urllib",
    "uuid", "venv", "warnings", "weakref", "webbrowser", "xml", "zipfile",
    "zlib", "_thread",
}

# Common third-party packages (not tracked as internal deps)
THIRD_PARTY_PACKAGES = {
    "aiohttp", "aiosqlite", "anthropic", "beautifulsoup4", "bs4", "certifi",
    "charset_normalizer", "click", "cryptography", "discord", "dotenv",
    "fastapi", "flask", "google", "googleapiclient", "httpx", "httpcore",
    "idna", "jinja2", "jwt", "llama_cpp", "markdown", "markupsafe",
    "numpy", "oauth2client", "openai", "pandas", "pdfplumber", "PIL",
    "pillow", "psutil", "pydantic", "pyautogui", "pynput", "pyperclip",
    "pytest", "requests", "selenium", "sniffio", "sqlalchemy", "starlette",
    "tiktoken", "toml", "tqdm", "transformers", "undetected_chromedriver",
    "urllib3", "uvicorn", "websockets", "yaml", "pyyaml",
}


def get_module_dependencies(
    repo_root: Path,
    module_name: str,
    include_external: bool = True,
    max_depth: int = 1,
) -> Dict[str, Any]:
    """
    Get dependencies for a FoundUps module.

    Args:
        repo_root: Repository root path
        module_name: Module name (e.g., "ai_overseer", "wre_core")
        include_external: Include external package dependencies
        max_depth: Depth of internal dependency traversal (1=direct only)

    Returns:
        MCPResponse with dependency information
    """
    # Find module directory
    module_path = _find_module_path(repo_root, module_name)
    if not module_path:
        return error_response(
            f"Module not found: {module_name}",
            hint="Use format like 'ai_overseer' or 'wre_core'",
        )

    # Collect all Python files in module
    py_files = list(module_path.rglob("*.py"))
    if not py_files:
        return error_response(f"No Python files found in module: {module_name}")

    # Parse imports from all files
    internal_deps: Dict[str, Set[str]] = {}  # module -> set of files importing it
    external_deps: Dict[str, Set[str]] = {}  # package -> set of files importing it
    file_imports: Dict[str, List[Dict]] = {}  # file -> list of import details

    for py_file in py_files:
        rel_path = str(py_file.relative_to(repo_root))
        imports = _parse_file_imports(py_file)
        file_imports[rel_path] = imports

        for imp in imports:
            imp_name = imp["module"]
            first_part = imp_name.split(".")[0]

            if first_part in STDLIB_MODULES:
                continue  # Skip stdlib

            if first_part in THIRD_PARTY_PACKAGES or first_part.lower() in THIRD_PARTY_PACKAGES:
                if include_external:
                    if imp_name not in external_deps:
                        external_deps[imp_name] = set()
                    external_deps[imp_name].add(rel_path)
                continue

            # Check if it's an internal module import
            if imp_name.startswith("modules."):
                target_module = _extract_module_name(imp_name)
                if target_module and target_module != module_name:
                    if target_module not in internal_deps:
                        internal_deps[target_module] = set()
                    internal_deps[target_module].add(rel_path)

    # Build response
    internal_list = [
        {
            "module": mod,
            "imported_by": sorted(files),
            "import_count": len(files),
            "confidence": "direct_import",
        }
        for mod, files in sorted(internal_deps.items())
    ]

    external_list = [
        {
            "package": pkg,
            "imported_by": sorted(files),
            "import_count": len(files),
            "confidence": "direct_import",
        }
        for pkg, files in sorted(external_deps.items())
    ]

    # Check requirements.txt for declared dependencies
    requirements_file = module_path / "requirements.txt"
    declared_deps = []
    if requirements_file.exists():
        declared_deps = _parse_requirements(requirements_file)

    return ok_response(
        {
            "module": module_name,
            "module_path": str(module_path.relative_to(repo_root)),
            "files_analyzed": len(py_files),
            "internal_dependencies": internal_list,
            "internal_count": len(internal_list),
            "external_dependencies": external_list,
            "external_count": len(external_list),
            "declared_requirements": declared_deps,
            "depth": max_depth,
        },
        source="dependency_analysis",
        tool="get_module_dependencies",
    )


def get_reverse_dependencies(
    repo_root: Path,
    module_name: str,
    search_scope: str = "modules",
) -> Dict[str, Any]:
    """
    Find modules that depend on the specified module.

    Args:
        repo_root: Repository root path
        module_name: Module name to find dependents of
        search_scope: Scope to search ("modules", "all")

    Returns:
        MCPResponse with reverse dependency information
    """
    # Verify target module exists
    module_path = _find_module_path(repo_root, module_name)
    if not module_path:
        return error_response(
            f"Module not found: {module_name}",
            hint="Use format like 'ai_overseer' or 'wre_core'",
        )

    # Define search scope
    if search_scope == "modules":
        search_root = repo_root / "modules"
    else:
        search_root = repo_root

    if not search_root.exists():
        return error_response(f"Search scope not found: {search_scope}")

    # Build import patterns to search for
    import_patterns = [
        f"modules.{_get_module_domain(module_path, repo_root)}.{module_name}",
        f"from modules.{_get_module_domain(module_path, repo_root)}.{module_name}",
    ]

    # Search all Python files for imports
    dependents: Dict[str, List[Dict]] = {}  # module -> list of import details

    for py_file in search_root.rglob("*.py"):
        # Skip the target module itself
        try:
            if module_path in py_file.parents or py_file.parent == module_path:
                continue
        except (ValueError, TypeError):
            pass

        # Skip test files optionally
        rel_path = str(py_file.relative_to(repo_root))

        imports = _parse_file_imports(py_file)
        for imp in imports:
            imp_module = imp["module"]

            # Check if this import references our target module
            if module_name in imp_module and "modules." in imp_module:
                # Extract the importing module's name
                importing_module = _extract_module_name_from_path(py_file, repo_root)
                if importing_module and importing_module != module_name:
                    if importing_module not in dependents:
                        dependents[importing_module] = []
                    dependents[importing_module].append({
                        "file": rel_path,
                        "import_statement": imp["full_statement"],
                        "line": imp.get("line", 0),
                    })

    # Build response
    dependent_list = [
        {
            "module": mod,
            "import_details": details,
            "import_count": len(details),
            "confidence": "direct_import" if len(details) > 0 else "inferred",
        }
        for mod, details in sorted(dependents.items())
    ]

    return ok_response(
        {
            "module": module_name,
            "module_path": str(module_path.relative_to(repo_root)),
            "search_scope": search_scope,
            "dependents": dependent_list,
            "dependent_count": len(dependent_list),
            "total_imports": sum(d["import_count"] for d in dependent_list),
            "blast_radius": _classify_blast_radius(len(dependent_list)),
        },
        source="reverse_dependency_analysis",
        tool="get_reverse_dependencies",
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _find_module_path(repo_root: Path, module_name: str) -> Optional[Path]:
    """Find module directory by name, searching all domains."""
    modules_dir = repo_root / "modules"
    if not modules_dir.exists():
        return None

    # Search in each domain
    for domain in modules_dir.iterdir():
        if domain.is_dir() and not domain.name.startswith("."):
            candidate = domain / module_name
            if candidate.exists() and candidate.is_dir():
                return candidate

    return None


def _get_module_domain(module_path: Path, repo_root: Path) -> str:
    """Extract domain from module path."""
    try:
        rel = module_path.relative_to(repo_root / "modules")
        parts = rel.parts
        if parts:
            return parts[0]
    except ValueError:
        pass
    return "unknown"


def _extract_module_name(import_path: str) -> Optional[str]:
    """Extract module name from import path like 'modules.domain.module_name.src.file'."""
    if not import_path.startswith("modules."):
        return None
    parts = import_path.split(".")
    if len(parts) >= 3:
        return parts[2]  # modules.domain.MODULE_NAME
    return None


def _extract_module_name_from_path(file_path: Path, repo_root: Path) -> Optional[str]:
    """Extract module name from file path."""
    try:
        rel = file_path.relative_to(repo_root / "modules")
        parts = rel.parts
        if len(parts) >= 2:
            return parts[1]  # domain/MODULE_NAME/...
    except ValueError:
        pass
    return None


def _parse_file_imports(file_path: Path) -> List[Dict]:
    """Parse imports from a Python file using AST."""
    imports = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        tree = ast.parse(content, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "module": alias.name,
                    "type": "import",
                    "full_statement": f"import {alias.name}",
                    "line": node.lineno,
                })
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names = [a.name for a in node.names]
                imports.append({
                    "module": node.module,
                    "type": "from_import",
                    "names": names,
                    "full_statement": f"from {node.module} import {', '.join(names[:3])}{'...' if len(names) > 3 else ''}",
                    "line": node.lineno,
                })

    return imports


def _parse_requirements(req_file: Path) -> List[str]:
    """Parse requirements.txt file."""
    deps = []
    try:
        with open(req_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Extract package name (before any version specifier)
                    match = re.match(r"^([a-zA-Z0-9_-]+)", line)
                    if match:
                        deps.append(match.group(1))
    except OSError:
        pass
    return deps


def _classify_blast_radius(dependent_count: int) -> str:
    """Classify blast radius based on dependent count."""
    if dependent_count == 0:
        return "isolated"
    elif dependent_count <= 2:
        return "low"
    elif dependent_count <= 5:
        return "medium"
    elif dependent_count <= 10:
        return "high"
    else:
        return "critical"
