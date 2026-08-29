"""Pure contract tests for inert composition-bound runtime ABI evidence."""

from __future__ import annotations

import copy
import json

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_contract import (
    canonical_json_bytes,
    digest_bytes,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_runtime_abi_contract import (
    BASE_ROLE,
    DEPENDENCY_ROLE,
    RuntimeAbiContractError,
    runtime_abi_descriptor,
    runtime_abi_inventory,
    validate_runtime_abi_descriptor,
    validate_runtime_abi_inventory,
)


DIGESTS = tuple(f"sha256:{value:064x}" for value in range(1, 20))


def _import(library: str) -> dict[str, object]:
    return {
        "library": library,
        "names_digest": DIGESTS[0],
        "name_count": 1,
        "ordinals_digest": DIGESTS[1],
        "ordinal_count": 0,
    }


def _native(
    role: str, path: str, *, distribution: str = "", wheel_tag: str = "",
) -> dict[str, object]:
    return {
        "component_role": role,
        "path": path,
        "sha256": DIGESTS[2],
        "size": 512,
        "machine": 0x8664,
        "optional_magic": 0x20B,
        "image_kind": "dll" if path.endswith((".dll", ".pyd")) else "executable",
        "normal_imports": [_import("python312.dll")],
        "delay_imports": [],
        "internal_imports": ["python312.dll"],
        "external_imports": [],
        "export_names_digest": DIGESTS[3],
        "export_name_count": 1,
        "export_ordinals_digest": DIGESTS[4],
        "export_ordinal_count": 1,
        "forwarded_export_names_digest": DIGESTS[10],
        "forwarded_export_name_count": 0,
        "forwarded_export_ordinals_digest": DIGESTS[11],
        "forwarded_export_ordinal_count": 0,
        "direct_python_link_libraries": ["python312.dll"],
        "reachable_python_libraries": ["python312.dll"],
        "python_abi_reachable": True,
        "distribution": distribution,
        "compatible_wheel_tag": wheel_tag,
    }


def _distribution() -> dict[str, object]:
    paths = ["demo/demo.cp312-win_amd64.pyd"]
    return {
        "dist_info": "demo-1.0.dist-info",
        "wheel_digest": DIGESTS[5],
        "record_digest": DIGESTS[6],
        "tags": ["cp312-cp312-win_amd64"],
        "compatible_tags": ["cp312-cp312-win_amd64"],
        "native_file_count": 1,
        "native_paths_digest": digest_bytes(canonical_json_bytes(paths)),
    }


def _inventory() -> dict[str, object]:
    return runtime_abi_inventory(
        composition_generation_id=DIGESTS[8],
        distributions=[_distribution()],
        native_files=[
            _native(BASE_ROLE, "python.exe"),
            _native(
                DEPENDENCY_ROLE, "demo/demo.cp312-win_amd64.pyd",
                distribution="demo-1.0.dist-info",
                wheel_tag="cp312-cp312-win_amd64",
            ),
        ],
    )


def _descriptor() -> dict[str, object]:
    return runtime_abi_descriptor(
        composition_generation_id=DIGESTS[8],
        composition_descriptor_digest=DIGESTS[9],
        inventory=_inventory(),
    )


def test_inventory_and_descriptor_are_canonical_root_path_free_and_inert() -> None:
    inventory = _inventory()
    descriptor = _descriptor()

    assert validate_runtime_abi_inventory(inventory) == inventory
    assert validate_runtime_abi_descriptor(descriptor) == descriptor
    assert descriptor["declared_python_link_abi_verified"] is True
    assert descriptor["native_loader_closure_verified"] is False
    assert descriptor["activation_eligible"] is False
    encoded = json.dumps({"inventory": inventory, "descriptor": descriptor})
    assert "O:/" not in encoded and "secret" not in encoded.lower()


@pytest.mark.parametrize(
    "field",
    [
        "native_loader_closure_verified",
        "deterministic_effects_verified",
        "preimport_bootstrap_verified",
        "signature_verified",
        "write_denial_verified",
        "activation_eligible",
        "exact_runtime_closure_verified",
    ],
)
def test_unearned_activation_grade_claims_reject(field: str) -> None:
    descriptor = _descriptor()
    descriptor[field] = True

    with pytest.raises(RuntimeAbiContractError, match="RUNTIME_ABI_DESCRIPTOR_TRUTH_INVALID"):
        validate_runtime_abi_descriptor(descriptor)


def test_wrong_machine_bool_size_and_unknown_keys_reject() -> None:
    for field, value in (("machine", 0x14C), ("size", True)):
        inventory = copy.deepcopy(_inventory())
        inventory["native_files"][0][field] = value
        with pytest.raises(RuntimeAbiContractError):
            validate_runtime_abi_inventory(inventory)

    inventory = copy.deepcopy(_inventory())
    inventory["unknown"] = "field"
    with pytest.raises(RuntimeAbiContractError, match="RUNTIME_ABI_INVENTORY_INVALID"):
        validate_runtime_abi_inventory(inventory)


def test_distribution_substitution_and_order_fail_closed() -> None:
    inventory = copy.deepcopy(_inventory())
    inventory["native_files"][1]["distribution"] = "other-1.0.dist-info"
    with pytest.raises(RuntimeAbiContractError, match="RUNTIME_ABI_DISTRIBUTION_BINDING_INVALID"):
        validate_runtime_abi_inventory(inventory)

    inventory = copy.deepcopy(_inventory())
    inventory["native_files"].reverse()
    with pytest.raises(RuntimeAbiContractError, match="RUNTIME_ABI_NATIVE_ORDER_INVALID"):
        validate_runtime_abi_inventory(inventory)


def test_component_or_inventory_substitution_changes_generation() -> None:
    original = _descriptor()["generation_id"]
    changed_composition = runtime_abi_descriptor(
        composition_generation_id=DIGESTS[10],
        composition_descriptor_digest=DIGESTS[9],
        inventory=runtime_abi_inventory(
            composition_generation_id=DIGESTS[10],
            distributions=[_distribution()],
            native_files=_inventory()["native_files"],
        ),
    )["generation_id"]
    inventory = copy.deepcopy(_inventory())
    inventory["native_files"][0]["sha256"] = DIGESTS[11]
    changed_inventory = runtime_abi_descriptor(
        composition_generation_id=DIGESTS[8],
        composition_descriptor_digest=DIGESTS[9],
        inventory=inventory,
    )["generation_id"]

    assert len({original, changed_composition, changed_inventory}) == 3
