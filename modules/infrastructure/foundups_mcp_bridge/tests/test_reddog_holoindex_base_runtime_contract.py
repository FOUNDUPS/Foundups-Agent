"""Fail-closed tests for the inert HoloIndex Python base-runtime contract."""

from __future__ import annotations

from copy import deepcopy

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_base_runtime_contract import (
    ADMITTED_PATH_ROOTS,
    DESCRIPTOR_SCHEMA_VERSION,
    EXCLUDED_PATH_ROOTS,
    INVENTORY_NAME,
    INVENTORY_ROLES,
    INVENTORY_SCHEMA_VERSION,
    PAYLOAD_DIRECTORY,
    PLATFORM_TAG,
    REQUIRED_INVENTORY_ROLES,
    BaseRuntimeBinding,
    BaseRuntimeContractError,
    BaseRuntimeLimits,
    base_runtime_file_role,
    base_runtime_tree_digest,
    canonical_json_bytes,
    canonical_relative_path,
    digest_bytes,
    parse_canonical_json,
    validate_descriptor,
    validate_inventory,
)


def _row(path: str, role: str, marker: str) -> dict[str, object]:
    return {
        "path": path,
        "size": 3,
        "sha256": "sha256:" + (marker * 64),
        "role": role,
    }


def _inventory() -> dict[str, object]:
    return {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "platform_tag": PLATFORM_TAG,
        "admitted_path_roots": list(ADMITTED_PATH_ROOTS),
        "excluded_path_roots": list(EXCLUDED_PATH_ROOTS),
        "directories": ["DLLs", "Lib", "Lib/encodings", "tcl", "tcl/tcl8.6"],
        "files": [
            _row("DLLs/_hashlib.pyd", "python_native_extension", "1"),
            _row("Lib/encodings/__init__.py", "python_standard_library", "2"),
            _row("python.exe", "python_executable", "3"),
            _row("python312.dll", "python_runtime_library", "4"),
            _row("pyvenv.cfg", "python_runtime_configuration", "5"),
            _row("tcl/tcl8.6/init.tcl", "python_runtime_data", "6"),
            _row("vcruntime140_1.dll", "python_runtime_library", "7"),
        ],
    }


def _descriptor() -> dict[str, object]:
    inventory = validate_inventory(_inventory())
    inventory_raw = canonical_json_bytes(inventory)
    tree_digest = base_runtime_tree_digest(
        inventory["directories"], inventory["files"]  # type: ignore[arg-type]
    )
    return {
        "schema_version": DESCRIPTOR_SCHEMA_VERSION,
        "status": "INERT",
        "generation_id": tree_digest,
        "inventory_file": INVENTORY_NAME,
        "inventory_digest": digest_bytes(inventory_raw),
        "inventory_bytes": len(inventory_raw),
        "base_runtime_tree_digest": tree_digest,
        "file_count": len(inventory["files"]),  # type: ignore[arg-type]
        "directory_count": len(inventory["directories"]),  # type: ignore[arg-type]
        "total_bytes": sum(row["size"] for row in inventory["files"]),  # type: ignore[index]
        "platform_tag": PLATFORM_TAG,
        "admitted_path_roots": list(ADMITTED_PATH_ROOTS),
        "excluded_path_roots": list(EXCLUDED_PATH_ROOTS),
        "inventory_roles": list(INVENTORY_ROLES),
        "required_inventory_roles": list(REQUIRED_INVENTORY_ROLES),
        "artifact_bytes_verified_at_publication": True,
        "native_loader_closure_verified": False,
        "deterministic_effects_verified": False,
        "signature_verified": False,
        "write_denial_verified": False,
        "activation_eligible": False,
        "exact_runtime_closure_verified": False,
    }


def test_inventory_preserves_runnable_windows_base_prefix_topology() -> None:
    inventory = validate_inventory(_inventory())
    paths = [row["path"] for row in inventory["files"]]

    assert paths == [
        "DLLs/_hashlib.pyd",
        "Lib/encodings/__init__.py",
        "python.exe",
        "python312.dll",
        "pyvenv.cfg",
        "tcl/tcl8.6/init.tcl",
        "vcruntime140_1.dll",
    ]
    assert {row["role"] for row in inventory["files"]} == set(INVENTORY_ROLES)
    assert all(not path.startswith(("executable/", "stdlib/")) for path in paths)
    assert ADMITTED_PATH_ROOTS == (".", "DLLs", "Lib", "tcl")
    assert "Doc" in EXCLUDED_PATH_ROOTS and "share" not in EXCLUDED_PATH_ROOTS
    assert PAYLOAD_DIRECTORY == "python-runtime"


def test_configuration_role_is_optional_for_the_production_base_shape() -> None:
    inventory = _inventory()
    inventory["files"] = [
        row for row in inventory["files"]  # type: ignore[union-attr]
        if row["role"] != "python_runtime_configuration"
    ]
    validated = validate_inventory(inventory)
    assert "python_runtime_configuration" not in {
        row["role"] for row in validated["files"]
    }


@pytest.mark.parametrize(
    ("path", "role"),
    (
        ("python.exe", "python_executable"),
        ("python312.dll", "python_runtime_library"),
        ("vcruntime140.dll", "python_runtime_library"),
        ("vcruntime140_1.dll", "python_runtime_library"),
        ("DLLs/_ssl.pyd", "python_native_extension"),
        ("DLLs/python_lib.cat", "python_runtime_data"),
        ("Lib/lib-dynload/_hashlib.pyd", "python_native_extension"),
        ("Lib/os.py", "python_standard_library"),
        ("tcl/tcl8.6/init.tcl", "python_runtime_data"),
        ("python312._pth", "python_runtime_configuration"),
    ),
)
def test_authoritative_role_classifier_matches_runnable_topology(
    path: str, role: str,
) -> None:
    assert base_runtime_file_role(path) == role


def test_canonical_json_round_trip_and_duplicate_keys_fail_closed() -> None:
    raw = canonical_json_bytes({"unicode": "caf\N{LATIN SMALL LETTER E WITH ACUTE}", "a": 1})
    assert raw == b'{"a":1,"unicode":"caf\\u00e9"}\n'
    assert parse_canonical_json(raw.decode("ascii"))["unicode"] == "caf\N{LATIN SMALL LETTER E WITH ACUTE}"

    with pytest.raises(BaseRuntimeContractError, match="BASE_RUNTIME_JSON_DUPLICATE_KEY"):
        parse_canonical_json('{"a":1,"a":1}\n')
    with pytest.raises(BaseRuntimeContractError, match="BASE_RUNTIME_JSON_INVALID"):
        parse_canonical_json('{"unicode":"\N{LATIN SMALL LETTER E WITH ACUTE}"}\n')


@pytest.mark.parametrize(
    "path",
    (".", "/python.exe", "C:/python.exe", "Lib\\os.py", "Lib/../python.exe", "Lib/e\u0301.py"),
)
def test_noncanonical_inventory_paths_are_rejected(path: str) -> None:
    with pytest.raises(BaseRuntimeContractError, match="BASE_RUNTIME_PATH_INVALID"):
        canonical_relative_path(path)


@pytest.mark.parametrize("field", ("admitted_path_roots", "excluded_path_roots"))
def test_inventory_requires_exact_platform_path_sets(field: str) -> None:
    inventory = _inventory()
    inventory[field] = list(reversed(inventory[field]))  # type: ignore[arg-type]
    with pytest.raises(BaseRuntimeContractError, match="BASE_RUNTIME_ROOT_CONTRACT_INVALID"):
        validate_inventory(inventory)


@pytest.mark.parametrize(
    ("path", "role"),
    (
        ("Lib/site-packages/pkg.py", "python_standard_library"),
        ("Scripts/python.exe", "python_executable"),
        ("Lib/os.py", "python_native_extension"),
        ("DLLs/_hashlib.pyd", "python_standard_library"),
        ("runtime.dll", "python_runtime_library"),
    ),
)
def test_excluded_or_role_incompatible_paths_are_rejected(path: str, role: str) -> None:
    inventory = _inventory()
    inventory["files"][0] = _row(path, role, "a")  # type: ignore[index]
    inventory["files"] = sorted(  # type: ignore[index]
        inventory["files"], key=lambda row: row["path"].casefold()  # type: ignore[index]
    )
    with pytest.raises(BaseRuntimeContractError, match="BASE_RUNTIME_FILE_INVALID"):
        validate_inventory(inventory)


def test_inventory_requires_complete_roles_and_parent_topology() -> None:
    missing_role = _inventory()
    missing_role["files"] = [
        row for row in missing_role["files"]  # type: ignore[union-attr]
        if row["role"] != "python_runtime_data"
    ]
    with pytest.raises(BaseRuntimeContractError, match="BASE_RUNTIME_ROLE_COVERAGE_INVALID"):
        validate_inventory(missing_role)

    missing_parent = _inventory()
    missing_parent["directories"] = ["DLLs", "Lib"]
    with pytest.raises(BaseRuntimeContractError, match="BASE_RUNTIME_TOPOLOGY_INVALID"):
        validate_inventory(missing_parent)


def test_inventory_rejects_order_case_collision_unknown_keys_and_bounds() -> None:
    reordered = _inventory()
    reordered["files"] = list(reversed(reordered["files"]))  # type: ignore[arg-type]
    with pytest.raises(BaseRuntimeContractError, match="BASE_RUNTIME_INVENTORY_ORDER_INVALID"):
        validate_inventory(reordered)

    unknown = _inventory()
    unknown["absolute_base_prefix"] = "forbidden"
    with pytest.raises(BaseRuntimeContractError, match="BASE_RUNTIME_INVENTORY_INVALID"):
        validate_inventory(unknown)

    with pytest.raises(BaseRuntimeContractError, match="BASE_RUNTIME_INVENTORY_BOUND_INVALID"):
        validate_inventory(_inventory(), BaseRuntimeLimits(max_files=4))


def test_tree_digest_binds_roles_bytes_topology_and_platform_path_sets() -> None:
    inventory = validate_inventory(_inventory())
    first = base_runtime_tree_digest(
        inventory["directories"], inventory["files"]  # type: ignore[arg-type]
    )
    changed = deepcopy(inventory["files"])
    changed[0]["sha256"] = "sha256:" + ("f" * 64)  # type: ignore[index]
    assert first != base_runtime_tree_digest(inventory["directories"], changed)  # type: ignore[arg-type]


def test_descriptor_is_strict_inert_and_explicitly_non_exact() -> None:
    descriptor = validate_descriptor(_descriptor())
    assert descriptor["artifact_bytes_verified_at_publication"] is True
    assert descriptor["native_loader_closure_verified"] is False
    assert descriptor["deterministic_effects_verified"] is False
    assert descriptor["signature_verified"] is False
    assert descriptor["write_denial_verified"] is False
    assert descriptor["activation_eligible"] is False
    assert descriptor["exact_runtime_closure_verified"] is False


@pytest.mark.parametrize(
    "field",
    (
        "native_loader_closure_verified",
        "deterministic_effects_verified",
        "signature_verified",
        "write_denial_verified",
        "activation_eligible",
        "exact_runtime_closure_verified",
    ),
)
def test_descriptor_rejects_optimistic_truth_flags(field: str) -> None:
    descriptor = _descriptor()
    descriptor[field] = True
    with pytest.raises(BaseRuntimeContractError, match="BASE_RUNTIME_DESCRIPTOR_TRUTH_INVALID"):
        validate_descriptor(descriptor)


def test_descriptor_rejects_binding_count_root_and_shape_substitution() -> None:
    binding = _descriptor()
    binding["generation_id"] = "sha256:" + ("0" * 64)
    with pytest.raises(BaseRuntimeContractError, match="BASE_RUNTIME_DESCRIPTOR_BINDING_INVALID"):
        validate_descriptor(binding)

    count = _descriptor()
    count["file_count"] = True
    with pytest.raises(BaseRuntimeContractError, match="BASE_RUNTIME_DESCRIPTOR_COUNT_INVALID"):
        validate_descriptor(count)

    roots = _descriptor()
    roots["excluded_path_roots"] = list(reversed(EXCLUDED_PATH_ROOTS))
    with pytest.raises(
        BaseRuntimeContractError, match="BASE_RUNTIME_DESCRIPTOR_ROOT_CONTRACT_INVALID"
    ):
        validate_descriptor(roots)

    unknown = _descriptor()
    unknown["owner_executable"] = "forbidden"
    with pytest.raises(BaseRuntimeContractError, match="BASE_RUNTIME_DESCRIPTOR_INVALID"):
        validate_descriptor(unknown)


def test_limits_reject_bool_zero_and_negative_values() -> None:
    for limits in (
        BaseRuntimeLimits(max_files=True),
        BaseRuntimeLimits(max_directories=0),
        BaseRuntimeLimits(max_total_bytes=-1),
    ):
        with pytest.raises(BaseRuntimeContractError, match="BASE_RUNTIME_LIMIT_INVALID"):
            limits.validate()


def test_binding_public_projection_is_path_free_and_preserves_non_claims(tmp_path) -> None:
    binding = BaseRuntimeBinding(
        generation_root=tmp_path / "generation",
        base_prefix_root=tmp_path / "generation" / PAYLOAD_DIRECTORY,
        descriptor_path=tmp_path / "generation" / "descriptor.json",
        descriptor_digest="sha256:" + ("1" * 64),
        generation_id="sha256:" + ("2" * 64),
        inventory_digest="sha256:" + ("3" * 64),
        base_runtime_tree_digest="sha256:" + ("2" * 64),
        file_count=7,
        directory_count=5,
        total_bytes=21,
        artifact_bytes_verified_at_publication=True,
        native_loader_closure_verified=False,
        deterministic_effects_verified=False,
        signature_verified=False,
        write_denial_verified=False,
        activation_eligible=False,
        exact_runtime_closure_verified=False,
    )
    public = binding.public_binding
    assert all("root" not in key and "path" not in key for key in public)
    assert public["base_runtime_artifact_bytes_verified"] is True
    assert public["base_runtime_activation_eligible"] is False
    assert public["base_runtime_exact_closure_verified"] is False
