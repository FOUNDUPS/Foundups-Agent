"""Small synthetic component generations for runtime-composition tests."""

from __future__ import annotations

import base64
import hashlib
import stat
import struct
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


def _put_ascii(data: bytearray, offset: int, value: str) -> None:
    encoded = value.encode("ascii") + b"\0"
    data[offset:offset + len(encoded)] = encoded


def synthetic_pe(
    *, library: str = "kernel32.dll", import_symbol: str = "GetProcAddress",
    exports: tuple[str, ...] = (), dll: bool = True, machine: int = 0x8664,
) -> bytes:
    """Return one small PE32+ image with deterministic imports and exports."""

    if len(exports) > 4:
        raise ValueError("synthetic_pe_export_limit")
    data = bytearray(0x800)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    characteristics = 0x2022 if dll else 0x0022
    struct.pack_into(
        "<HHIIIHH", data, 0x84, machine, 1, 0, 0, 0, 0xF0, characteristics
    )
    optional = 0x98
    struct.pack_into("<H", data, optional, 0x20B)
    struct.pack_into("<I", data, optional + 60, 0x200)
    struct.pack_into("<I", data, optional + 108, 16)
    if exports:
        struct.pack_into("<II", data, optional + 112, 0x1000, 0x100)
    struct.pack_into("<II", data, optional + 120, 0x1200, 0x80)
    section = optional + 0xF0
    data[section:section + 8] = b".rdata\0\0"
    struct.pack_into("<IIII", data, section + 8, 0x600, 0x1000, 0x600, 0x200)
    _write_synthetic_exports(data, exports)
    struct.pack_into("<IIIII", data, 0x400, 0x1260, 0, 0, 0x1240, 0x1260)
    _put_ascii(data, 0x440, library)
    struct.pack_into("<QQ", data, 0x460, 0x1280, 0)
    struct.pack_into("<H", data, 0x480, 0)
    _put_ascii(data, 0x482, import_symbol)
    return bytes(data)


def _write_synthetic_exports(data: bytearray, exports: tuple[str, ...]) -> None:
    if not exports:
        return
    count = len(exports)
    struct.pack_into(
        "<7I", data, 0x20C, 0x1070, 1, count, count, 0x1040, 0x1050, 0x1060
    )
    for index, name in enumerate(exports):
        struct.pack_into("<I", data, 0x240 + index * 4, 0x1300 + index * 0x10)
        struct.pack_into("<I", data, 0x250 + index * 4, 0x1080 + index * 0x20)
        struct.pack_into("<H", data, 0x260 + index * 2, index)
        _put_ascii(data, 0x280 + index * 0x20, name)
    _put_ascii(data, 0x270, "synthetic.dll")


def _record_digest(payload: bytes) -> str:
    value = base64.urlsafe_b64encode(hashlib.sha256(payload).digest())
    return value.rstrip(b"=").decode("ascii")


def materialized_runtime_components(
    tmp_path: Path, *, dependency_native_machine: int = 0x8664,
    dependency_native_filename: str = "demo.cp312-win_amd64.pyd",
    dependency_import_library: str = "python312.dll",
    dependency_import_symbol: str = "PyLong_FromLong",
    dependency_wheel_tag: str = "cp312-cp312-win_amd64",
    include_dependency_native: bool = True, include_native_record: bool = True,
    dependency_native_payload: bytes | None = None,
    duplicate_native_record: bool = False, record_traversal: bool = False,
    python312_payload: bytes | None = None,
) -> RuntimeCompositionFixture:
    paths = _runtime_fixture_paths(tmp_path)
    repo, canonical, base_source, dependency_source = paths[:4]
    base_store, dependency_store, composition_store = paths[4:]
    (repo / ".git").mkdir(parents=True)
    canonical.mkdir()
    _write_base_source(base_source, python312_payload)
    _write_dependency_source(
        dependency_source, dependency_native_machine, dependency_native_filename,
        dependency_import_library, dependency_import_symbol,
        dependency_wheel_tag, include_dependency_native, include_native_record,
        dependency_native_payload, duplicate_native_record, record_traversal,
    )
    base = materialize_base_runtime(
        source_base_prefix=base_source, runtime_store_root=base_store,
        canonical_store=canonical, repo_roots=(repo,), limits=BASE_LIMITS,
    )
    dependency = materialize_dependency_runtime(
        source_site_packages=dependency_source, runtime_store_root=dependency_store,
        canonical_store=canonical, repo_roots=(repo,), limits=DEPENDENCY_LIMITS,
    )
    return RuntimeCompositionFixture(
        repo, canonical, base_store, dependency_store, composition_store,
        base, dependency,
    )


def _runtime_fixture_paths(tmp_path: Path) -> tuple[Path, ...]:
    repo = tmp_path / "repo"
    canonical = tmp_path / "canonical"
    base_source = repo / "Python312"
    dependency_source = repo / ".venv" / "Lib" / "site-packages"
    base_store = tmp_path / "base-runtimes"
    dependency_store = tmp_path / "dependency-runtimes"
    composition_store = tmp_path / "runtime-compositions"
    return (
        repo, canonical, base_source, dependency_source, base_store,
        dependency_store, composition_store,
    )


def _write_base_source(base_source: Path, python312_payload: bytes | None) -> None:
    (base_source / "DLLs").mkdir(parents=True)
    (base_source / "Lib" / "encodings").mkdir(parents=True)
    (base_source / "Lib" / "site-packages").mkdir()
    (base_source / "tcl" / "tcl8.6").mkdir(parents=True)
    interpreter = base_source / "python.exe"
    interpreter.write_bytes(synthetic_pe(
        library="python312.dll", import_symbol="Py_Main", dll=False,
    ))
    interpreter.chmod(interpreter.stat().st_mode | stat.S_IXUSR)
    (base_source / "python312.dll").write_bytes(
        python312_payload or synthetic_pe(exports=("Py_Main", "PyLong_FromLong"))
    )
    (base_source / "python3.dll").write_bytes(synthetic_pe(
        exports=("PyLong_FromLong",),
    ))
    (base_source / "vcruntime140.dll").write_bytes(synthetic_pe())
    (base_source / "DLLs" / "_hashlib.pyd").write_bytes(synthetic_pe(
        library="python312.dll", import_symbol="PyLong_FromLong",
        exports=("PyInit__hashlib",),
    ))
    (base_source / "Lib" / "encodings" / "__init__.py").write_bytes(b"stdlib")
    (base_source / "tcl" / "tcl8.6" / "init.tcl").write_bytes(b"runtime-data")


def _write_dependency_source(
    dependency_source: Path, dependency_native_machine: int,
    dependency_native_filename: str, dependency_import_library: str,
    dependency_import_symbol: str, dependency_wheel_tag: str,
    include_dependency_native: bool, include_native_record: bool,
    dependency_native_payload: bytes | None, duplicate_native_record: bool,
    record_traversal: bool,
) -> None:
    dependency_source.mkdir(parents=True)
    (dependency_source / "alpha.py").write_text("VALUE = 1\n", encoding="utf-8")
    native = dependency_source / "demo" / dependency_native_filename
    native_payload = dependency_native_payload or synthetic_pe(
        library=dependency_import_library, import_symbol=dependency_import_symbol,
        exports=("PyInit_demo",), machine=dependency_native_machine,
    )
    if include_dependency_native:
        native.parent.mkdir()
        native.write_bytes(native_payload)
    dist = dependency_source / "demo-1.0.dist-info"
    dist.mkdir()
    (dist / "WHEEL").write_text(
        f"Wheel-Version: 1.0\nTag: {dependency_wheel_tag}\n", encoding="utf-8"
    )
    native_record = (
        f"demo/{dependency_native_filename},sha256={_record_digest(native_payload)},"
        f"{len(native_payload)}\n"
        if include_dependency_native and include_native_record else ""
    )
    extra = native_record if duplicate_native_record else ""
    extra += "../escape.py,,\n" if record_traversal else ""
    (dist / "RECORD").write_text(
        native_record + extra
        + "demo-1.0.dist-info/WHEEL,,\n"
        "demo-1.0.dist-info/RECORD,,\n",
        encoding="utf-8",
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
    "synthetic_pe",
]
