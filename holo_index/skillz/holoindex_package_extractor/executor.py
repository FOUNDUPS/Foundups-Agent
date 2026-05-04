#!/usr/bin/env python3
"""
HoloIndex Package Extractor

Extracts HoloIndex core into a standalone pip-installable package
for use in external FoundUp repositories.

Usage:
    python executor.py --analyze              # Analyze dependencies
    python executor.py --extract /tmp/holo    # Extract to directory
    python executor.py --pyproject            # Generate pyproject.toml only
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set


# Core files to extract (relative to holo_index/core/)
CORE_FILES = [
    "holo_index.py",
    "search_engine.py",
    "indexing_engine.py",
    "backend_routing.py",
    "search_cache.py",
    "circuit_breaker.py",
]

# Files to EXCLUDE (framework-specific)
EXCLUDED_FILES = [
    "comment_search.py",      # YouTube specific
    "video_search.py",        # YouTube specific
    "intelligent_subroutine_engine.py",  # Framework specific
    "module_scoring_subroutine.py",      # Framework specific
    "mps_m_scorer.py",        # Framework specific
    "introspection_engine.py",  # TypeScript parsing
    "vocabulary_indexer.py",  # Specialized
    "turboquant_backend.py",  # Optional (can add later)
]

# Internal imports to stub
INTERNAL_STUBS = {
    "wsp_summaries": "{}",
    "NAVIGATION": "{'NEED_TO': {}}",
    "qwen_advisor": "# EXCLUDED - not needed for standalone",
}

# External dependencies
REQUIRED_DEPS = [
    "chromadb>=0.4.0",
    "sentence-transformers>=2.2.0",
]

OPTIONAL_DEPS = [
    "onnxruntime>=1.16.0",  # For turboquant
]


@dataclass
class ExtractionResult:
    """Result of package extraction."""
    success: bool
    files_extracted: List[str] = field(default_factory=list)
    files_skipped: List[str] = field(default_factory=list)
    internal_deps_found: List[str] = field(default_factory=list)
    external_deps: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    output_path: Optional[str] = None


@dataclass
class DependencyAnalysis:
    """Analysis of file dependencies."""
    file_path: str
    stdlib_imports: List[str] = field(default_factory=list)
    external_imports: List[str] = field(default_factory=list)
    internal_imports: List[str] = field(default_factory=list)
    relative_imports: List[str] = field(default_factory=list)


def get_repo_root() -> Path:
    """Get repository root."""
    return Path(__file__).resolve().parents[3]


def analyze_imports(file_path: Path) -> DependencyAnalysis:
    """Analyze imports in a Python file."""
    analysis = DependencyAnalysis(file_path=str(file_path))

    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError) as e:
        analysis.internal_imports.append(f"ERROR: {e}")
        return analysis

    stdlib_modules = {
        "os", "sys", "re", "json", "ast", "logging", "pathlib",
        "datetime", "time", "hashlib", "shutil", "subprocess",
        "typing", "dataclasses", "collections", "functools",
        "io", "threading", "contextlib", "tempfile", "uuid",
        "__future__",
    }

    external_known = {
        "chromadb", "sentence_transformers", "numpy", "torch",
        "onnxruntime", "transformers",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".")[0]
                if module in stdlib_modules:
                    analysis.stdlib_imports.append(alias.name)
                elif module in external_known:
                    analysis.external_imports.append(alias.name)
                else:
                    analysis.internal_imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue

            if node.level > 0:
                # Relative import
                analysis.relative_imports.append(node.module or ".")
            else:
                module = node.module.split(".")[0]
                if module in stdlib_modules:
                    analysis.stdlib_imports.append(node.module)
                elif module in external_known:
                    analysis.external_imports.append(node.module)
                else:
                    analysis.internal_imports.append(node.module)

    return analysis


def analyze_all_core_files(repo_root: Path) -> Dict[str, DependencyAnalysis]:
    """Analyze all core files."""
    core_dir = repo_root / "holo_index" / "core"
    results = {}

    for filename in CORE_FILES:
        file_path = core_dir / filename
        if file_path.exists():
            results[filename] = analyze_imports(file_path)
        else:
            results[filename] = DependencyAnalysis(
                file_path=str(file_path),
                internal_imports=[f"ERROR: File not found"]
            )

    return results


def generate_pyproject_toml() -> str:
    """Generate pyproject.toml content."""
    return '''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "holoindex"
version = "0.1.0"
description = "Semantic code retrieval and project memory substrate for the FoundUps ecosystem"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [
    {name = "FoundUps", email = "dev@foundups.com"},
]
keywords = ["semantic-search", "code-retrieval", "chromadb", "embeddings"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
    "chromadb>=0.4.0",
    "sentence-transformers>=2.2.0",
]

[project.optional-dependencies]
turboquant = [
    "onnxruntime>=1.16.0",
]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
]

[project.scripts]
holoindex = "holoindex.cli:main"

[project.urls]
Homepage = "https://github.com/FOUNDUPS/holoindex"
Documentation = "https://github.com/FOUNDUPS/holoindex#readme"
Repository = "https://github.com/FOUNDUPS/holoindex"

[tool.hatch.build.targets.wheel]
packages = ["src/holoindex"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
'''


def generate_readme() -> str:
    """Generate README.md content."""
    return '''# HoloIndex

Semantic code retrieval and project memory substrate for the FoundUps ecosystem.

## Installation

```bash
pip install holoindex
```

## Quick Start

```python
from holoindex import HoloIndex

# Initialize with vector storage path
holo = HoloIndex(vector_path="./vectors")

# Index your codebase
holo.index_documents(roots=["./src"])

# Search
results = holo.search("authentication middleware", limit=5)
for r in results:
    print(f"{r['path']}: {r['similarity']:.2f}")
```

## Features

- **Semantic Search**: Find code by meaning, not just keywords
- **ChromaDB Backend**: Persistent vector storage
- **Sentence Transformers**: State-of-the-art embeddings
- **Hybrid Scoring**: Combines semantic + keyword relevance

## Configuration

```python
# Use custom embedding model
holo = HoloIndex(
    vector_path="./vectors",
    model_name="all-MiniLM-L6-v2",
)

# Configure similarity threshold
results = holo.search("query", min_similarity=0.5)
```

## License

MIT - See LICENSE for details.

## Links

- [FoundUps](https://foundups.com)
- [Documentation](https://github.com/FOUNDUPS/holoindex)
'''


def extract_package(
    repo_root: Path,
    output_path: Path,
    with_tests: bool = False,
) -> ExtractionResult:
    """Extract HoloIndex core to standalone package."""
    result = ExtractionResult(success=False, output_path=str(output_path))

    core_dir = repo_root / "holo_index" / "core"
    src_dir = output_path / "src" / "holoindex"
    tests_dir = output_path / "tests"

    # Create directories
    src_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    # File mapping (source -> dest)
    file_mapping = {
        "holo_index.py": "core.py",
        "search_engine.py": "search.py",
        "indexing_engine.py": "indexing.py",
        "backend_routing.py": "backend.py",
        "search_cache.py": "cache.py",
        "circuit_breaker.py": "resilience.py",
    }

    # Copy and transform core files
    for src_name, dest_name in file_mapping.items():
        src_file = core_dir / src_name
        dest_file = src_dir / dest_name

        if not src_file.exists():
            result.warnings.append(f"Source file not found: {src_name}")
            result.files_skipped.append(src_name)
            continue

        try:
            content = src_file.read_text(encoding="utf-8")

            # Transform relative imports
            content = re.sub(
                r"from \.(\w+) import",
                r"from holoindex.\1 import",
                content,
            )
            content = re.sub(
                r"from \.\.(\w+) import",
                r"from holoindex.\1 import",
                content,
            )

            # Stub internal dependencies
            for internal, stub in INTERNAL_STUBS.items():
                if internal in content:
                    result.internal_deps_found.append(internal)

            dest_file.write_text(content, encoding="utf-8")
            result.files_extracted.append(dest_name)

        except Exception as e:
            result.errors.append(f"Failed to extract {src_name}: {e}")
            result.files_skipped.append(src_name)

    # Generate __init__.py
    init_content = '''"""
HoloIndex - Semantic code retrieval for FoundUps.

Usage:
    from holoindex import HoloIndex

    holo = HoloIndex(vector_path="./vectors")
    holo.index_documents(roots=["./src"])
    results = holo.search("query", limit=5)
"""

from holoindex.core import HoloIndex

__version__ = "0.1.0"
__all__ = ["HoloIndex"]
'''
    (src_dir / "__init__.py").write_text(init_content)
    result.files_extracted.append("__init__.py")

    # Generate pyproject.toml
    (output_path / "pyproject.toml").write_text(generate_pyproject_toml())
    result.files_extracted.append("pyproject.toml")

    # Generate README.md
    (output_path / "README.md").write_text(generate_readme())
    result.files_extracted.append("README.md")

    # Generate LICENSE
    license_content = f'''MIT License

Copyright (c) {datetime.now().year} FoundUps

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''
    (output_path / "LICENSE").write_text(license_content)
    result.files_extracted.append("LICENSE")

    # Generate basic tests if requested
    if with_tests:
        test_content = '''"""Basic tests for HoloIndex standalone package."""

import pytest
from pathlib import Path


def test_import():
    """Test that holoindex can be imported."""
    from holoindex import HoloIndex
    assert HoloIndex is not None


def test_version():
    """Test version is defined."""
    import holoindex
    assert hasattr(holoindex, "__version__")
    assert holoindex.__version__ == "0.1.0"


@pytest.mark.skip(reason="Requires ChromaDB setup")
def test_basic_indexing(tmp_path):
    """Test basic indexing functionality."""
    from holoindex import HoloIndex

    vector_path = tmp_path / "vectors"
    holo = HoloIndex(vector_path=str(vector_path))

    # Create a test file
    test_file = tmp_path / "test.py"
    test_file.write_text("def hello(): return 'world'")

    # Index it
    holo.index_documents(roots=[str(tmp_path)])

    # Search
    results = holo.search("hello function")
    assert len(results) > 0
'''
        (tests_dir / "test_core.py").write_text(test_content)
        (tests_dir / "__init__.py").write_text("")
        result.files_extracted.extend(["tests/test_core.py", "tests/__init__.py"])

    result.external_deps = REQUIRED_DEPS
    result.success = len(result.errors) == 0

    return result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract HoloIndex core into standalone package"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze dependencies only (no extraction)",
    )
    parser.add_argument(
        "--extract",
        type=str,
        metavar="PATH",
        help="Extract package to specified directory",
    )
    parser.add_argument(
        "--pyproject",
        action="store_true",
        help="Generate pyproject.toml only",
    )
    parser.add_argument(
        "--with-tests",
        action="store_true",
        help="Include test templates",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()
    repo_root = get_repo_root()

    if args.analyze:
        # Analyze dependencies
        analyses = analyze_all_core_files(repo_root)

        if args.json:
            output = {
                "timestamp": datetime.now().isoformat(),
                "repo_root": str(repo_root),
                "core_files": len(CORE_FILES),
                "excluded_files": len(EXCLUDED_FILES),
                "analyses": {
                    name: {
                        "stdlib": analysis.stdlib_imports,
                        "external": analysis.external_imports,
                        "internal": analysis.internal_imports,
                        "relative": analysis.relative_imports,
                    }
                    for name, analysis in analyses.items()
                },
                "required_deps": REQUIRED_DEPS,
                "optional_deps": OPTIONAL_DEPS,
            }
            print(json.dumps(output, indent=2))
        else:
            print("=" * 60)
            print("HoloIndex Package Extractor - Dependency Analysis")
            print("=" * 60)
            print(f"\nRepository: {repo_root}")
            print(f"Core files: {len(CORE_FILES)}")
            print(f"Excluded: {len(EXCLUDED_FILES)}")
            print()

            for name, analysis in analyses.items():
                print(f"\n{name}:")
                print(f"  Stdlib: {len(analysis.stdlib_imports)}")
                print(f"  External: {analysis.external_imports or 'none'}")
                print(f"  Internal: {analysis.internal_imports or 'none'}")
                print(f"  Relative: {analysis.relative_imports or 'none'}")

            print("\n" + "=" * 60)
            print("Required Dependencies:")
            for dep in REQUIRED_DEPS:
                print(f"  - {dep}")
            print("\nOptional Dependencies:")
            for dep in OPTIONAL_DEPS:
                print(f"  - {dep}")

    elif args.pyproject:
        print(generate_pyproject_toml())

    elif args.extract:
        output_path = Path(args.extract).resolve()
        result = extract_package(
            repo_root=repo_root,
            output_path=output_path,
            with_tests=args.with_tests,
        )

        if args.json:
            output = {
                "timestamp": datetime.now().isoformat(),
                "success": result.success,
                "output_path": result.output_path,
                "files_extracted": result.files_extracted,
                "files_skipped": result.files_skipped,
                "internal_deps_found": result.internal_deps_found,
                "external_deps": result.external_deps,
                "warnings": result.warnings,
                "errors": result.errors,
            }
            print(json.dumps(output, indent=2))
        else:
            print("=" * 60)
            print("HoloIndex Package Extraction")
            print("=" * 60)
            print(f"\nOutput: {result.output_path}")
            print(f"Success: {result.success}")
            print(f"\nFiles extracted: {len(result.files_extracted)}")
            for f in result.files_extracted:
                print(f"  + {f}")

            if result.files_skipped:
                print(f"\nFiles skipped: {len(result.files_skipped)}")
                for f in result.files_skipped:
                    print(f"  - {f}")

            if result.internal_deps_found:
                print(f"\nInternal deps (need stubbing): {result.internal_deps_found}")

            if result.warnings:
                print(f"\nWarnings:")
                for w in result.warnings:
                    print(f"  ! {w}")

            if result.errors:
                print(f"\nErrors:")
                for e in result.errors:
                    print(f"  X {e}")

    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
