from __future__ import annotations

import base64
import csv
from dataclasses import replace
import hashlib
import importlib.machinery
import io
from pathlib import Path
import tempfile
from types import ModuleType

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_contract import (
    DependencyRuntimeBinding,
    canonical_json_bytes,
    dependency_tree_digest,
    digest_bytes,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_packaging import (
    QueryRuntimeBuilderPackagingError,
    _parse_record,
    _prove_builder_packaging_authority_for_test,
    _validate_metadata,
    prove_builder_packaging_authority,
)
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_query_runtime_builder_packaging as packaging_authority_module,
)


_MODULE_PATHS = {
    "packaging": "packaging/__init__.py",
    "packaging.markers": "packaging/markers.py",
    "packaging.requirements": "packaging/requirements.py",
    "packaging.specifiers": "packaging/specifiers.py",
    "packaging.utils": "packaging/utils.py",
    "packaging.version": "packaging/version.py",
}


def _digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _record_hash(data: bytes) -> str:
    value = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode("ascii")
    return "sha256=" + value.rstrip("=")


def _package_files(*, cache: bool, dist_info: str, package_root: str) -> dict[str, bytes]:
    files: dict[str, bytes] = {
        **{
            path.replace("packaging/", f"{package_root}/", 1): f"# {name}\n".encode("utf-8")
            for name, path in _MODULE_PATHS.items()
        },
        f"{dist_info}/METADATA": b"Name: packaging\nVersion: 26.0\n",
        f"{dist_info}/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\n",
    }
    if cache:
        files[f"{package_root}/__pycache__/version.cpython-314.pyc"] = b"cache"
    return files


def _write_files(site: Path, files: dict[str, bytes]) -> None:
    for relative, payload in files.items():
        target = site.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)


def _record_bytes(
    files: dict[str, bytes], record_path: str, *, blank_member: str,
    record_alias: tuple[str, str] | None, malformed_hash_member: str,
) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    for relative in sorted((*files, record_path), key=str.casefold):
        if relative == record_path or relative == blank_member:
            writer.writerow((relative, "", ""))
        else:
            payload = files[relative]
            written_path = record_alias[1] if record_alias and relative == record_alias[0] else relative
            digest = _record_hash(payload) + ("=" if relative == malformed_hash_member else "")
            writer.writerow((written_path, digest, len(payload)))
    return buffer.getvalue().encode("utf-8")


def _inventory(site: Path, paths: tuple[str, ...]) -> dict[str, object]:
    rows = []
    for path in sorted(paths, key=str.casefold):
        payload = (site / Path(path)).read_bytes()
        rows.append({
            "path": path, "size": len(payload), "sha256": _digest(payload),
            "role": "dependency_payload",
        })
    directories = sorted(
        {parent.as_posix() for path in rows for parent in Path(path["path"]).parents if str(parent) != "."},
        key=str.casefold,
    )
    return {
        "schema_version": "holoindex_dependency_payload_inventory.v1",
        "directories": directories,
        "files": rows,
    }


def _binding(generation: Path, site: Path, inventory: dict[str, object]) -> DependencyRuntimeBinding:
    rows = inventory["files"]
    directories = inventory["directories"]
    binding = DependencyRuntimeBinding(
        generation_root=generation,
        site_packages_root=site,
        descriptor_path=generation / "holoindex_dependency_payload_descriptor.json",
        descriptor_digest="sha256:" + "1" * 64,
        generation_id="sha256:" + "2" * 64,
        inventory_digest=digest_bytes(canonical_json_bytes(inventory)),
        dependency_tree_digest=dependency_tree_digest(directories, rows),
        file_count=len(rows),  # type: ignore[arg-type]
        directory_count=len(directories),  # type: ignore[arg-type]
        total_bytes=sum(row["size"] for row in rows),  # type: ignore[index,union-attr]
        artifact_bytes_verified_at_publication=True,
        write_denial_verified=False,
        activation_eligible=False,
    )
    return binding


def _fixture(
    *, cache: bool = False, blank_member: str = "",
    record_alias: tuple[str, str] | None = None, malformed_hash_member: str = "",
    dist_info: str = "packaging-26.0.dist-info",
    package_root: str = "packaging",
):
    Path("O:/tmp").mkdir(parents=True, exist_ok=True)
    temp = tempfile.TemporaryDirectory(prefix="reddog-builder-packaging-", dir="O:/tmp")
    generation, record_path = Path(temp.name), f"{dist_info}/RECORD"
    site = generation / "site-packages"
    files = _package_files(cache=cache, dist_info=dist_info, package_root=package_root)
    _write_files(site, files)
    record = _record_bytes(
        files, record_path, blank_member=blank_member,
        record_alias=record_alias, malformed_hash_member=malformed_hash_member,
    )
    target = site.joinpath(*record_path.split("/"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(record)
    inventory = _inventory(site, (*files, record_path))
    binding = _binding(generation, site, inventory)
    return temp, site, inventory, binding


def _modules(site: Path):
    result = {}
    for name, relative in _MODULE_PATHS.items():
        module = ModuleType(name)
        module.__file__ = str(site.joinpath(*relative.split("/")))
        module.__cached__ = str(site / "absent-cache" / f"{name}.pyc")
        module.__loader__ = importlib.machinery.SourceFileLoader(name, module.__file__)
        result[name] = module
    return result


def test_source_only_record_and_loaded_origins_are_bound() -> None:
    temp, site, inventory, binding = _fixture()
    try:
        authority = _prove_builder_packaging_authority_for_test(
            dependency_runtime=binding, dependency_inventory=inventory,
            modules=_modules(site),
        ).public_binding
        assert authority["distribution_version"] == "26.0"
        assert authority["owned_file_count"] == len(inventory["files"])
        assert authority["loaded_module_count"] == 6
        assert authority["bytecode_cache_absent"] is True
    finally:
        temp.cleanup()


def test_physical_bytecode_cache_is_rejected() -> None:
    temp, _site, inventory, binding = _fixture(cache=True)
    try:
        with pytest.raises(QueryRuntimeBuilderPackagingError, match="SOURCE_ONLY_REQUIRED"):
            _prove_builder_packaging_authority_for_test(
                dependency_runtime=binding, dependency_inventory=inventory,
                modules=_modules(Path(binding.site_packages_root)),
            )
    finally:
        temp.cleanup()


def test_only_record_itself_may_have_blank_record_hash() -> None:
    temp, _site, inventory, binding = _fixture(
        blank_member="packaging-26.0.dist-info/METADATA",
    )
    try:
        with pytest.raises(QueryRuntimeBuilderPackagingError, match="UNHASHED_MEMBER"):
            _prove_builder_packaging_authority_for_test(
                dependency_runtime=binding, dependency_inventory=inventory,
                modules=_modules(Path(binding.site_packages_root)),
            )
    finally:
        temp.cleanup()


def test_physical_loaded_cache_is_rejected_after_ownership() -> None:
    temp, site, inventory, binding = _fixture()
    try:
        modules = _modules(site)
        cache = Path(str(modules["packaging.version"].__cached__))
        cache.parent.mkdir(parents=True)
        cache.write_bytes(b"cache")
        with pytest.raises(QueryRuntimeBuilderPackagingError, match="TREE_INVALID"):
            _prove_builder_packaging_authority_for_test(
                dependency_runtime=binding, dependency_inventory=inventory,
                modules=modules,
            )
    finally:
        temp.cleanup()


def test_every_loaded_packaging_module_must_be_record_owned() -> None:
    temp, site, inventory, binding = _fixture()
    try:
        modules = _modules(site)
        rogue = ModuleType("packaging.rogue")
        rogue.__file__ = "O:/unbound/rogue.py"
        rogue.__cached__ = None
        rogue.__loader__ = importlib.machinery.SourceFileLoader(
            "packaging.rogue", rogue.__file__,
        )
        modules["packaging.rogue"] = rogue
        with pytest.raises(QueryRuntimeBuilderPackagingError, match="MODULE_ORIGIN_INVALID"):
            _prove_builder_packaging_authority_for_test(
                dependency_runtime=binding, dependency_inventory=inventory,
                modules=modules,
            )
    finally:
        temp.cleanup()


def test_record_paths_are_exact_case_identities() -> None:
    temp, _site, inventory, binding = _fixture(
        record_alias=("packaging/version.py", "Packaging/version.py"),
    )
    try:
        with pytest.raises(QueryRuntimeBuilderPackagingError, match="RECORD_OWNERSHIP_INVALID"):
            _prove_builder_packaging_authority_for_test(
                dependency_runtime=binding, dependency_inventory=inventory,
                modules=_modules(Path(binding.site_packages_root)),
            )
    finally:
        temp.cleanup()


def test_noncanonical_record_base64url_is_rejected() -> None:
    temp, _site, inventory, binding = _fixture(
        malformed_hash_member="packaging/version.py",
    )
    try:
        with pytest.raises(QueryRuntimeBuilderPackagingError, match="RECORD_INVALID"):
            _prove_builder_packaging_authority_for_test(
                dependency_runtime=binding, dependency_inventory=inventory,
                modules=_modules(Path(binding.site_packages_root)),
            )
    finally:
        temp.cleanup()


def test_loader_name_must_match_loaded_module() -> None:
    temp, site, inventory, binding = _fixture()
    try:
        modules = _modules(site)
        module = modules["packaging.version"]
        module.__loader__ = importlib.machinery.SourceFileLoader(
            "packaging.wrong", str(module.__file__),
        )
        with pytest.raises(QueryRuntimeBuilderPackagingError, match="LOADER_INVALID"):
            _prove_builder_packaging_authority_for_test(
                dependency_runtime=binding, dependency_inventory=inventory,
                modules=modules,
            )
    finally:
        temp.cleanup()


def test_unlisted_physical_member_is_rejected() -> None:
    temp, site, inventory, binding = _fixture()
    try:
        (site / "packaging" / "unlisted.py").write_bytes(b"UNLISTED = True\n")
        with pytest.raises(QueryRuntimeBuilderPackagingError, match="TREE_INVALID"):
            _prove_builder_packaging_authority_for_test(
                dependency_runtime=binding, dependency_inventory=inventory,
                modules=_modules(site),
            )
    finally:
        temp.cleanup()


def test_final_record_member_mutation_is_rejected(monkeypatch) -> None:
    temp, site, inventory, binding = _fixture()
    target = site / "packaging" / "version.py"
    original = packaging_authority_module._read_owned
    mutated = False

    def mutate_before_read(root: Path, row: tuple[str, int, str]) -> bytes:
        nonlocal mutated
        if row[0] == "packaging/version.py" and not mutated:
            mutated = True
            target.write_bytes(target.read_bytes().replace(b"version", b"versioN"))
        return original(root, row)

    try:
        monkeypatch.setattr(packaging_authority_module, "_read_owned", mutate_before_read)
        with pytest.raises(QueryRuntimeBuilderPackagingError, match="MEMBER_MUTATED"):
            _prove_builder_packaging_authority_for_test(
                dependency_runtime=binding, dependency_inventory=inventory,
                modules=_modules(site),
            )
    finally:
        temp.cleanup()


def test_dist_info_directory_identity_is_exact() -> None:
    temp, site, inventory, binding = _fixture(dist_info="evil-1.dist-info")
    try:
        with pytest.raises(QueryRuntimeBuilderPackagingError, match="DISTRIBUTION_SET_INVALID"):
            _prove_builder_packaging_authority_for_test(
                dependency_runtime=binding, dependency_inventory=inventory,
                modules=_modules(site),
            )
    finally:
        temp.cleanup()


@pytest.mark.parametrize("size", ["01", "\u0661"])
def test_record_sizes_require_canonical_ascii_decimal(size: str) -> None:
    record_path = "packaging-26.0.dist-info/RECORD"
    digest = _record_hash(b"x")
    raw = (
        f"packaging/version.py,{digest},{size}\n{record_path},,\n"
    ).encode("utf-8")
    with pytest.raises(QueryRuntimeBuilderPackagingError, match="UNHASHED_MEMBER"):
        _parse_record(raw, record_path)


def test_physical_package_root_identity_is_exact_case() -> None:
    temp, site, inventory, binding = _fixture(package_root="Packaging")
    try:
        with pytest.raises(QueryRuntimeBuilderPackagingError, match="DISTRIBUTION_SET_INVALID"):
            _prove_builder_packaging_authority_for_test(
                dependency_runtime=binding, dependency_inventory=inventory,
                modules=_modules(site),
            )
    finally:
        temp.cleanup()


@pytest.mark.parametrize(
    "metadata",
    [
        b"Name: packaging\nName: evil\nVersion: 26.0\n",
        b"Name: packaging\nVersion: 26.0\nVersion: 999\n",
    ],
)
def test_metadata_requires_one_exact_name_and_version(metadata: bytes) -> None:
    with pytest.raises(QueryRuntimeBuilderPackagingError, match="VERSION_INVALID"):
        _validate_metadata(metadata)


def test_public_packaging_wrapper_reproves_same_runtime(monkeypatch) -> None:
    temp, site, inventory, binding = _fixture()
    try:
        expected = _prove_builder_packaging_authority_for_test(
            dependency_runtime=binding, dependency_inventory=inventory,
            modules=_modules(site),
        )
        calls = []

        def verify(**_kwargs):
            calls.append("verify")
            return binding

        monkeypatch.setattr(packaging_authority_module, "verify_dependency_runtime_generation", verify)
        monkeypatch.setattr(
            packaging_authority_module, "_prove_builder_packaging_authority",
            lambda **_kwargs: expected,
        )
        observed = prove_builder_packaging_authority(
            dependency_verification_kwargs={}, dependency_inventory=inventory,
        )
        assert observed.public_binding == expected.public_binding
        assert calls == ["verify", "verify"]
    finally:
        temp.cleanup()


def test_public_packaging_wrapper_rejects_reproof_mutation(monkeypatch) -> None:
    temp, site, inventory, binding = _fixture()
    try:
        expected = _prove_builder_packaging_authority_for_test(
            dependency_runtime=binding, dependency_inventory=inventory,
            modules=_modules(site),
        )
        values = iter((binding, replace(binding, generation_id=_digest(b"changed"))))
        monkeypatch.setattr(
            packaging_authority_module, "verify_dependency_runtime_generation",
            lambda **_kwargs: next(values),
        )
        monkeypatch.setattr(
            packaging_authority_module, "_prove_builder_packaging_authority",
            lambda **_kwargs: expected,
        )
        with pytest.raises(QueryRuntimeBuilderPackagingError, match="RUNTIME_MUTATED"):
            prove_builder_packaging_authority(
                dependency_verification_kwargs={}, dependency_inventory=inventory,
            )
    finally:
        temp.cleanup()


def test_public_packaging_wrapper_maps_unexpected_errors(monkeypatch) -> None:
    monkeypatch.setattr(
        packaging_authority_module, "verify_dependency_runtime_generation",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("host path")),
    )
    with pytest.raises(QueryRuntimeBuilderPackagingError, match="AUTHORITY_UNAVAILABLE"):
        prove_builder_packaging_authority(
            dependency_verification_kwargs={}, dependency_inventory={},
        )
