"""Pure contract tests for inert HoloIndex runtime compositions."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_base_runtime_contract import (
    BaseRuntimeBinding,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_contract import (
    DependencyRuntimeBinding,
    canonical_json_bytes,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_runtime_composition_contract import (
    RuntimeCompositionContractError,
    runtime_composition_descriptor,
    validate_runtime_composition_descriptor,
)


DIGESTS = tuple(f"sha256:{index:064x}" for index in range(1, 16))


def _base() -> BaseRuntimeBinding:
    return BaseRuntimeBinding(
        generation_root=Path("O:/private/base-generation"),
        base_prefix_root=Path("O:/private/base-generation/python-runtime"),
        descriptor_path=Path("O:/private/base-generation/base.json"),
        descriptor_digest=DIGESTS[0],
        generation_id=DIGESTS[1],
        inventory_digest=DIGESTS[2],
        base_runtime_tree_digest=DIGESTS[3],
        file_count=100,
        directory_count=20,
        total_bytes=1000,
        artifact_bytes_verified_at_publication=True,
        native_loader_closure_verified=False,
        deterministic_effects_verified=False,
        signature_verified=False,
        write_denial_verified=False,
        activation_eligible=False,
        exact_runtime_closure_verified=False,
    )


def _dependency() -> DependencyRuntimeBinding:
    return DependencyRuntimeBinding(
        generation_root=Path("O:/private/dependency-generation"),
        site_packages_root=Path(
            "O:/private/dependency-generation/site-packages"
        ),
        descriptor_path=Path("O:/private/dependency-generation/dependency.json"),
        descriptor_digest=DIGESTS[4],
        generation_id=DIGESTS[5],
        inventory_digest=DIGESTS[6],
        dependency_tree_digest=DIGESTS[7],
        file_count=200,
        directory_count=40,
        total_bytes=2000,
        artifact_bytes_verified_at_publication=True,
        write_denial_verified=False,
        activation_eligible=False,
    )


def _descriptor() -> dict[str, object]:
    return runtime_composition_descriptor(
        base_runtime=_base(),
        dependency_runtime=_dependency(),
        interpreter_content_digest=DIGESTS[8],
        interpreter_size=512,
    )


def test_descriptor_is_canonical_path_free_and_domain_separated() -> None:
    descriptor = _descriptor()

    assert validate_runtime_composition_descriptor(descriptor) == descriptor
    assert descriptor["status"] == "INERT"
    assert descriptor["generation_id"].startswith("sha256:")
    encoded = canonical_json_bytes(descriptor).decode("ascii")
    assert "O:/" not in encoded
    assert "private" not in encoded
    assert "secret" not in encoded.lower()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("artifact_bytes_independently_reverified", False),
        ("abi_compatibility_verified", True),
        ("native_loader_closure_verified", True),
        ("deterministic_effects_verified", True),
        ("preimport_bootstrap_verified", True),
        ("signature_verified", True),
        ("write_denial_verified", True),
        ("activation_eligible", True),
        ("exact_runtime_closure_verified", True),
    ],
)
def test_unearned_truth_claims_are_rejected(field: str, value: bool) -> None:
    descriptor = _descriptor()
    descriptor[field] = value

    with pytest.raises(
        RuntimeCompositionContractError,
        match="RUNTIME_COMPOSITION_DESCRIPTOR_TRUTH_INVALID",
    ):
        validate_runtime_composition_descriptor(descriptor)


def test_component_order_or_generation_substitution_rejects() -> None:
    descriptor = _descriptor()
    descriptor["base_runtime"], descriptor["dependency_runtime"] = (
        descriptor["dependency_runtime"],
        descriptor["base_runtime"],
    )

    with pytest.raises(RuntimeCompositionContractError):
        validate_runtime_composition_descriptor(descriptor)

    descriptor = _descriptor()
    descriptor["base_runtime"] = dict(
        descriptor["base_runtime"], generation_id=DIGESTS[10]
    )
    with pytest.raises(
        RuntimeCompositionContractError,
        match="RUNTIME_COMPOSITION_GENERATION_ID_INVALID",
    ):
        validate_runtime_composition_descriptor(descriptor)


def test_counts_reject_bool_and_empty_payloads() -> None:
    for field, value in (("file_count", True), ("total_bytes", 0)):
        descriptor = _descriptor()
        descriptor["base_runtime"] = dict(
            descriptor["base_runtime"], **{field: value}
        )
        with pytest.raises(RuntimeCompositionContractError):
            validate_runtime_composition_descriptor(descriptor)


def test_generation_changes_for_either_component_or_interpreter() -> None:
    original = _descriptor()["generation_id"]
    changed_base = runtime_composition_descriptor(
        base_runtime=replace(_base(), generation_id=DIGESTS[11]),
        dependency_runtime=_dependency(),
        interpreter_content_digest=DIGESTS[8],
        interpreter_size=512,
    )["generation_id"]
    changed_dependency = runtime_composition_descriptor(
        base_runtime=_base(),
        dependency_runtime=replace(_dependency(), generation_id=DIGESTS[12]),
        interpreter_content_digest=DIGESTS[8],
        interpreter_size=512,
    )["generation_id"]
    changed_interpreter = runtime_composition_descriptor(
        base_runtime=_base(),
        dependency_runtime=_dependency(),
        interpreter_content_digest=DIGESTS[13],
        interpreter_size=512,
    )["generation_id"]

    assert len({original, changed_base, changed_dependency, changed_interpreter}) == 4
