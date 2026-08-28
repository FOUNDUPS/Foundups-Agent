"""Small synthetic component generations for runtime-composition tests."""

from __future__ import annotations

import stat
from dataclasses import dataclass
from pathlib import Path

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_base_runtime_contract import (
    BaseRuntimeLimits,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_base_runtime_materializer import (
    materialize_base_runtime,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_contract import (
    DependencyRuntimeLimits,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_materializer import (
    materialize_dependency_runtime,
)


BASE_LIMITS = BaseRuntimeLimits(
    max_files=50,
    max_directories=50,
    max_directory_depth=8,
    max_path_bytes=256,
    max_total_path_bytes=4096,
    max_file_bytes=1024 * 1024,
    max_total_bytes=8 * 1024 * 1024,
    max_inventory_bytes=64 * 1024,
    max_descriptor_bytes=16 * 1024,
)
DEPENDENCY_LIMITS = DependencyRuntimeLimits(
    max_files=20,
    max_directories=20,
    max_directory_depth=8,
    max_path_bytes=256,
    max_total_path_bytes=2048,
    max_file_bytes=1024 * 1024,
    max_total_bytes=4 * 1024 * 1024,
    max_inventory_bytes=64 * 1024,
    max_descriptor_bytes=16 * 1024,
)


@dataclass(frozen=True)
class RuntimeCompositionFixture:
    repo: Path
    canonical: Path
    base_store: Path
    dependency_store: Path
    composition_store: Path
    base: object
    dependency: object


def materialized_runtime_components(tmp_path: Path) -> RuntimeCompositionFixture:
    repo = tmp_path / "repo"
    canonical = tmp_path / "canonical"
    base_source = repo / "Python312"
    dependency_source = repo / ".venv" / "Lib" / "site-packages"
    base_store = tmp_path / "base-runtimes"
    dependency_store = tmp_path / "dependency-runtimes"
    composition_store = tmp_path / "runtime-compositions"
    (repo / ".git").mkdir(parents=True)
    canonical.mkdir()
    (base_source / "DLLs").mkdir(parents=True)
    (base_source / "Lib" / "encodings").mkdir(parents=True)
    (base_source / "Lib" / "site-packages").mkdir()
    (base_source / "tcl" / "tcl8.6").mkdir(parents=True)
    interpreter = base_source / "python.exe"
    interpreter.write_bytes(b"python-executable")
    interpreter.chmod(interpreter.stat().st_mode | stat.S_IXUSR)
    (base_source / "python312.dll").write_bytes(b"python-runtime-library")
    (base_source / "vcruntime140.dll").write_bytes(b"loader-runtime")
    (base_source / "DLLs" / "_hashlib.pyd").write_bytes(b"native-extension")
    (base_source / "Lib" / "encodings" / "__init__.py").write_bytes(b"stdlib")
    (base_source / "tcl" / "tcl8.6" / "init.tcl").write_bytes(b"runtime-data")
    dependency_source.mkdir(parents=True)
    (dependency_source / "alpha.py").write_text("VALUE = 1\n", encoding="utf-8")
    base = materialize_base_runtime(
        source_base_prefix=base_source,
        runtime_store_root=base_store,
        canonical_store=canonical,
        repo_roots=(repo,),
        limits=BASE_LIMITS,
    )
    dependency = materialize_dependency_runtime(
        source_site_packages=dependency_source,
        runtime_store_root=dependency_store,
        canonical_store=canonical,
        repo_roots=(repo,),
        limits=DEPENDENCY_LIMITS,
    )
    return RuntimeCompositionFixture(
        repo,
        canonical,
        base_store,
        dependency_store,
        composition_store,
        base,
        dependency,
    )


def materialize_composition(fixture: RuntimeCompositionFixture):
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_runtime_composition_materializer import (
        materialize_runtime_composition,
    )

    return materialize_runtime_composition(
        composition_store_root=fixture.composition_store,
        base_runtime_store_root=fixture.base_store,
        base_generation_root=fixture.base.binding.generation_root,
        dependency_runtime_store_root=fixture.dependency_store,
        dependency_generation_root=fixture.dependency.binding.generation_root,
        canonical_store=fixture.canonical,
        repo_roots=(fixture.repo,),
        base_limits=BASE_LIMITS,
        dependency_limits=DEPENDENCY_LIMITS,
    )


__all__ = [
    "BASE_LIMITS",
    "DEPENDENCY_LIMITS",
    "RuntimeCompositionFixture",
    "materialize_composition",
    "materialized_runtime_components",
]
