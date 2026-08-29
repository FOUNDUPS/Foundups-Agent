"""Adversarial derivation tests for inert runtime ABI attestation evidence."""

from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_runtime_abi_descriptor import (
    RuntimeAbiDescriptorError,
    build_runtime_abi_evidence,
    verify_runtime_abi_generation,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_runtime_abi_contract import (
    BASE_ROLE,
    DEPENDENCY_ROLE,
    DESCRIPTOR_NAME,
    INVENTORY_NAME,
    RuntimeAbiContractError,
    RuntimeAbiLimits,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_runtime_abi_graph import (
    NativeNode,
    derive_declared_abi_rows,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_runtime_abi_materializer import (
    RuntimeAbiMaterializationError,
    _MaterializerDependencies,
    _materialize_runtime_abi_for_test,
    materialize_runtime_abi_attestation,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_windows_pe import (
    parse_pe_image,
)
from modules.infrastructure.foundups_mcp_bridge.tests.reddog_holoindex_runtime_composition_test_support import (
    BASE_LIMITS,
    DEPENDENCY_LIMITS,
    RuntimeCompositionFixture,
    materialize_composition,
    materialized_runtime_components,
    synthetic_pe,
)


def _composition_kwargs(fixture: RuntimeCompositionFixture) -> dict[str, object]:
    composition = materialize_composition(fixture)
    return {
        "composition_store_root": fixture.composition_store,
        "generation_root": composition.binding.generation_root,
        "base_runtime_store_root": fixture.base_store,
        "base_generation_root": fixture.base.binding.generation_root,
        "dependency_runtime_store_root": fixture.dependency_store,
        "dependency_generation_root": fixture.dependency.binding.generation_root,
        "canonical_store": fixture.canonical,
        "repo_roots": (fixture.repo,),
        "base_limits": BASE_LIMITS,
        "dependency_limits": DEPENDENCY_LIMITS,
    }


def _evidence(fixture: RuntimeCompositionFixture):
    return build_runtime_abi_evidence(
        composition_kwargs=_composition_kwargs(fixture)
    )


def _materializer_kwargs(
    fixture: RuntimeCompositionFixture, abi_store: Path,
) -> dict[str, object]:
    return {
        "abi_store_root": abi_store,
        "composition_kwargs": _composition_kwargs(fixture),
    }


def test_exact_composition_derives_inert_static_abi_evidence(tmp_path: Path) -> None:
    fixture = materialized_runtime_components(tmp_path)

    evidence = _evidence(fixture)
    descriptor = evidence.descriptor

    assert descriptor["native_file_count"] == 6
    assert descriptor["distribution_count"] == 1
    assert descriptor["declared_pe_metadata_verified"] is True
    assert descriptor["declared_python_link_abi_verified"] is True
    assert descriptor["native_loader_closure_verified"] is False
    assert descriptor["activation_eligible"] is False
    dependency = [
        row for row in evidence.inventory["native_files"]
        if row["component_role"] == "python_dependency_runtime"
    ]
    assert dependency[0]["distribution"] == "demo-1.0.dist-info"
    assert dependency[0]["compatible_wheel_tag"] == "cp312-cp312-win_amd64"
    assert dependency[0]["direct_python_link_libraries"] == ["python312.dll"]
    assert dependency[0]["reachable_python_libraries"] == ["python312.dll"]


def test_pure_python_distribution_is_accepted_without_native_ownership(
    tmp_path: Path,
) -> None:
    fixture = materialized_runtime_components(
        tmp_path, include_dependency_native=False,
        dependency_wheel_tag="py3-none-any",
    )

    evidence = _evidence(fixture)

    assert evidence.descriptor["distribution_count"] == 1
    assert all(
        row["component_role"] == "python_base_runtime"
        for row in evidence.inventory["native_files"]
    )


def test_stable_abi_extension_requires_and_accepts_python3_link(tmp_path: Path) -> None:
    fixture = materialized_runtime_components(
        tmp_path,
        dependency_native_filename="demo.abi3.pyd",
        dependency_import_library="python3.dll",
        dependency_wheel_tag="cp37-abi3-win_amd64",
    )

    evidence = _evidence(fixture)
    row = next(
        value for value in evidence.inventory["native_files"]
        if value["path"] == "demo/demo.abi3.pyd"
    )

    assert row["direct_python_link_libraries"] == ["python3.dll"]
    assert row["reachable_python_libraries"] == ["python3.dll"]


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"dependency_native_machine": 0xAA64}, "RUNTIME_ABI_PE_MACHINE_INCOMPATIBLE"),
        ({"dependency_wheel_tag": "cp311-cp311-win_amd64"}, "RUNTIME_ABI_WHEEL_TAG_INCOMPATIBLE"),
        ({"include_native_record": False}, "RUNTIME_ABI_RECORD_OWNERSHIP_INVALID"),
        ({"dependency_import_symbol": "PyMissing"}, "RUNTIME_ABI_PYTHON_EXPORT_MISSING"),
    ],
)
def test_machine_wheel_ownership_and_symbol_mismatches_fail_closed(
    tmp_path: Path, kwargs: dict[str, object], code: str,
) -> None:
    fixture = materialized_runtime_components(tmp_path, **kwargs)

    with pytest.raises(RuntimeAbiDescriptorError, match=code):
        _evidence(fixture)


def test_cp311_extension_name_rejects_under_cp312(tmp_path: Path) -> None:
    fixture = materialized_runtime_components(
        tmp_path,
        dependency_native_filename="demo.cp311-win_amd64.pyd",
    )

    with pytest.raises(
        RuntimeAbiDescriptorError, match="RUNTIME_ABI_EXTENSION_TAG_INCOMPATIBLE"
    ):
        _evidence(fixture)


def test_malformed_pe_fails_without_loader_execution(tmp_path: Path) -> None:
    fixture = materialized_runtime_components(
        tmp_path, dependency_native_payload=b"not-a-pe-image",
    )

    with pytest.raises(RuntimeAbiDescriptorError, match="RUNTIME_ABI_PE_INVALID"):
        _evidence(fixture)


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"duplicate_native_record": True}, "RUNTIME_ABI_RECORD_DUPLICATE_PATH"),
        ({"record_traversal": True}, "RUNTIME_ABI_RECORD_INVALID"),
    ],
)
def test_record_ambiguity_and_traversal_fail_closed(
    tmp_path: Path, kwargs: dict[str, object], code: str,
) -> None:
    fixture = materialized_runtime_components(tmp_path, **kwargs)

    with pytest.raises(RuntimeAbiDescriptorError, match=code):
        _evidence(fixture)


def test_forwarded_python_symbol_does_not_earn_abi_proof(tmp_path: Path) -> None:
    import struct

    python312 = bytearray(synthetic_pe(exports=("Py_Main", "PyLong_FromLong")))
    struct.pack_into("<I", python312, 0x244, 0x10E0)
    forwarder = b"other.PyLong_FromLong\0"
    python312[0x2E0:0x2E0 + len(forwarder)] = forwarder
    fixture = materialized_runtime_components(
        tmp_path, python312_payload=bytes(python312),
    )

    with pytest.raises(RuntimeAbiDescriptorError, match="RUNTIME_ABI_PYTHON_EXPORT_MISSING"):
        _evidence(fixture)


def test_forwarded_extension_initializer_does_not_earn_abi_proof(
    tmp_path: Path,
) -> None:
    import struct

    payload = bytearray(synthetic_pe(
        library="python312.dll", import_symbol="PyLong_FromLong",
        exports=("PyInit_demo",),
    ))
    struct.pack_into("<I", payload, 0x240, 0x10E0)
    forwarder = b"other.PyInit_demo\0"
    payload[0x2E0:0x2E0 + len(forwarder)] = forwarder
    fixture = materialized_runtime_components(
        tmp_path, dependency_native_payload=bytes(payload),
    )

    with pytest.raises(RuntimeAbiDescriptorError, match="RUNTIME_ABI_EXTENSION_INIT_MISSING"):
        _evidence(fixture)


@pytest.mark.parametrize(
    "duplicate_path", ["demo/python312.dll", "other/python312.dll"]
)
def test_ambiguous_or_nonlocal_python_dll_does_not_resolve_to_base(
    duplicate_path: str,
) -> None:
    inventory = {"sha256": "sha256:" + "1" * 64, "size": 2048}
    nodes = [
        NativeNode(
            BASE_ROLE, "python312.dll", inventory,
            parse_pe_image(synthetic_pe(exports=("PyLong_FromLong",))), "", "",
        ),
        NativeNode(
            DEPENDENCY_ROLE, "demo/demo.cp312-win_amd64.pyd", inventory,
            parse_pe_image(synthetic_pe(
                library="python312.dll", import_symbol="PyLong_FromLong",
                exports=("PyInit_demo",),
            )), "demo-1.0.dist-info", "cp312-cp312-win_amd64",
        ),
        NativeNode(
            DEPENDENCY_ROLE, duplicate_path, inventory,
            parse_pe_image(synthetic_pe()),
            "demo-1.0.dist-info", "cp312-cp312-win_amd64",
        ),
    ]

    with pytest.raises(RuntimeAbiContractError, match="RUNTIME_ABI_PYTHON_DLL_MISMATCH"):
        derive_declared_abi_rows(nodes, RuntimeAbiLimits())


def test_multi_image_aggregate_budget_fails_closed(tmp_path: Path) -> None:
    fixture = materialized_runtime_components(tmp_path)

    with pytest.raises(RuntimeAbiDescriptorError, match="RUNTIME_ABI_AGGREGATE_PE_LIMIT_EXCEEDED"):
        build_runtime_abi_evidence(
            composition_kwargs=_composition_kwargs(fixture),
            abi_limits=RuntimeAbiLimits(max_total_import_libraries=5),
        )


def test_zero_export_slots_count_toward_aggregate_budget(tmp_path: Path) -> None:
    import struct

    payload = bytearray(synthetic_pe(exports=("Py_Main", "PyLong_FromLong")))
    struct.pack_into("<I", payload, 0x214, 4)
    fixture = materialized_runtime_components(
        tmp_path, python312_payload=bytes(payload)
    )

    with pytest.raises(
        RuntimeAbiDescriptorError,
        match="RUNTIME_ABI_PE_INVALID:PE_EXPORT_LIMIT_EXCEEDED",
    ):
        build_runtime_abi_evidence(
            composition_kwargs=_composition_kwargs(fixture),
            abi_limits=RuntimeAbiLimits(max_total_exports=5),
        )


def test_windows_publish_collision_uses_stable_generation_error(
    monkeypatch, tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_query_replica_generation as publication,
    )

    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()

    def collision(_source: Path, _target: Path) -> None:
        raise FileExistsError("simulated_collision")

    monkeypatch.setattr(publication.os, "name", "nt")
    monkeypatch.setattr(publication, "rename_windows_path_no_replace", collision)
    with pytest.raises(
        publication.QueryReplicaGenerationError,
        match="QUERY_REPLICA_GENERATION_EXISTS",
    ):
        publication.publish_directory_no_replace(source, target)


def test_os_failure_is_translated_to_path_free_descriptor_code(
    monkeypatch, tmp_path: Path,
) -> None:
    fixture = materialized_runtime_components(tmp_path)
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_runtime_abi_descriptor as module,
    )

    def leaked(**_values):
        raise FileNotFoundError(r"O:\private\SECRET_TOKEN_NAME\artifact.json")

    monkeypatch.setattr(module, "verify_runtime_composition_generation", leaked)
    with pytest.raises(RuntimeAbiDescriptorError) as observed:
        build_runtime_abi_evidence(composition_kwargs=_composition_kwargs(fixture))

    assert str(observed.value) == "RUNTIME_ABI_EVIDENCE_FAILED"


def test_os_failure_is_translated_to_path_free_materializer_code(
    monkeypatch, tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_runtime_abi_materializer as module,
    )

    def leaked(*_args, **_values):
        raise FileNotFoundError(r"O:\private\SECRET_TOKEN_NAME\artifact.json")

    monkeypatch.setattr(module, "_prepare_request", leaked)
    with pytest.raises(RuntimeAbiMaterializationError) as observed:
        module._materialize_runtime_abi_for_test(
            abi_store_root=tmp_path / "abi", composition_kwargs={},
        )

    assert str(observed.value) == "RUNTIME_ABI_MATERIALIZATION_FAILED"


def test_changed_second_composition_proof_rejects(monkeypatch, tmp_path: Path) -> None:
    fixture = materialized_runtime_components(tmp_path)
    kwargs = _composition_kwargs(fixture)
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_runtime_abi_descriptor as module,
    )

    trusted = module.verify_runtime_composition_generation
    calls = 0

    def changed(**values):
        nonlocal calls
        binding = trusted(**values)
        calls += 1
        return binding if calls == 1 else replace(
            binding, interpreter_size=binding.interpreter_size + 1
        )

    monkeypatch.setattr(module, "verify_runtime_composition_generation", changed)
    with pytest.raises(
        RuntimeAbiDescriptorError,
        match="RUNTIME_ABI_COMPOSITION_MUTATED_DURING_SCAN",
    ):
        build_runtime_abi_evidence(composition_kwargs=kwargs)


def test_materializes_reuses_and_independently_verifies_exact_evidence(
    tmp_path: Path,
) -> None:
    fixture = materialized_runtime_components(tmp_path)
    abi_store = tmp_path / "runtime-abi-attestations"
    kwargs = _materializer_kwargs(fixture, abi_store)

    first = materialize_runtime_abi_attestation(**kwargs)
    second = _materialize_runtime_abi_for_test(**kwargs)
    verified = verify_runtime_abi_generation(
        abi_store_root=abi_store,
        generation_root=first.binding.generation_root,
        composition_kwargs=kwargs["composition_kwargs"],
    )

    assert first.reused_existing_generation is False
    assert second.reused_existing_generation is True
    assert verified == first.binding == second.binding
    assert {path.name for path in first.binding.generation_root.iterdir()} == {
        INVENTORY_NAME, DESCRIPTOR_NAME, ".runtime-abi-publication-orphans"
    }
    assert first.binding.declared_python_link_abi_verified is True
    assert first.binding.native_loader_closure_verified is False
    assert first.binding.activation_eligible is False


def test_exact_reuse_does_not_publish(tmp_path: Path) -> None:
    fixture = materialized_runtime_components(tmp_path)
    abi_store = tmp_path / "runtime-abi-attestations"
    kwargs = _materializer_kwargs(fixture, abi_store)
    materialize_runtime_abi_attestation(**kwargs)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("exact reuse must not publish")

    reused = _materialize_runtime_abi_for_test(
        **kwargs,
        dependencies=_MaterializerDependencies(
            publish_json=forbidden, publish_directory=forbidden,
        ),
    )

    assert reused.reused_existing_generation is True


@pytest.mark.parametrize("filename", [INVENTORY_NAME, DESCRIPTOR_NAME])
def test_published_evidence_tampering_fails(tmp_path: Path, filename: str) -> None:
    fixture = materialized_runtime_components(tmp_path)
    abi_store = tmp_path / "runtime-abi-attestations"
    kwargs = _materializer_kwargs(fixture, abi_store)
    result = materialize_runtime_abi_attestation(**kwargs)
    path = result.binding.generation_root / filename
    value = json.loads(path.read_text("ascii"))
    value["status" if filename == DESCRIPTOR_NAME else "schema_version"] = "tampered"
    path.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="ascii",
    )

    with pytest.raises(RuntimeAbiDescriptorError):
        verify_runtime_abi_generation(
            abi_store_root=abi_store,
            generation_root=result.binding.generation_root,
            composition_kwargs=kwargs["composition_kwargs"],
        )


def test_component_mutation_after_publication_quarantines_generation(
    tmp_path: Path,
) -> None:
    fixture = materialized_runtime_components(tmp_path)
    abi_store = tmp_path / "runtime-abi-attestations"
    kwargs = _materializer_kwargs(fixture, abi_store)

    def mutate(_staging: Path) -> None:
        target = fixture.dependency.binding.site_packages_root / "alpha.py"
        target.write_text("VALUE = 9\n", encoding="utf-8")

    with pytest.raises(RuntimeAbiMaterializationError):
        _materialize_runtime_abi_for_test(
            **kwargs,
            dependencies=_MaterializerDependencies(after_evidence=mutate),
        )

    assert not any(
        entry.is_dir() and not entry.name.startswith(".")
        for entry in abi_store.iterdir()
    )
    assert len(tuple((abi_store / ".runtime-abi-orphans").iterdir())) == 1


@pytest.mark.skipif(os.name != "nt", reason="Windows extended-path contract")
def test_long_store_postpublication_failure_quarantines_canonical_name(
    monkeypatch, tmp_path: Path,
) -> None:
    fixture = materialized_runtime_components(tmp_path)
    abi_store = tmp_path / ("a" * 48) / "runtime-abi-attestations"
    abi_store.parent.mkdir()
    kwargs = _materializer_kwargs(fixture, abi_store)

    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_runtime_abi_materializer as module,
    )

    def reject_published(**_values):
        raise RuntimeAbiDescriptorError("RUNTIME_ABI_INJECTED_FINAL_REJECTION")

    monkeypatch.setattr(module, "verify_runtime_abi_generation", reject_published)

    with pytest.raises(RuntimeAbiMaterializationError):
        module._materialize_runtime_abi_for_test(**kwargs)

    assert not any(path.is_dir() and not path.name.startswith(".") for path in abi_store.iterdir())
    assert len(tuple((abi_store / ".runtime-abi-orphans").iterdir())) == 1


def test_overlapping_store_rejects_before_mutation(tmp_path: Path) -> None:
    fixture = materialized_runtime_components(tmp_path)
    composition_kwargs = _composition_kwargs(fixture)
    existing = set(fixture.composition_store.iterdir())

    with pytest.raises(RuntimeAbiMaterializationError, match="RUNTIME_ABI_STORE_OVERLAP"):
        materialize_runtime_abi_attestation(
            abi_store_root=fixture.composition_store / "abi",
            composition_kwargs=composition_kwargs,
        )

    assert set(fixture.composition_store.iterdir()) == existing
    assert not (fixture.composition_store / "abi").exists()


@pytest.mark.parametrize("defect", ["symlink", "hardlink"])
def test_evidence_aliases_fail_closed(tmp_path: Path, defect: str) -> None:
    fixture = materialized_runtime_components(tmp_path)
    abi_store = tmp_path / "runtime-abi-attestations"
    kwargs = _materializer_kwargs(fixture, abi_store)
    result = materialize_runtime_abi_attestation(**kwargs)
    path = result.binding.inventory_path
    payload = path.read_bytes()
    alternate = tmp_path / "external-abi-inventory.json"
    path.unlink()
    try:
        alternate.write_bytes(payload)
        if defect == "symlink":
            path.symlink_to(alternate)
        else:
            os.link(alternate, path)
    except OSError:
        pytest.skip(f"{defect} unavailable")

    with pytest.raises(RuntimeAbiDescriptorError):
        verify_runtime_abi_generation(
            abi_store_root=abi_store,
            generation_root=result.binding.generation_root,
            composition_kwargs=kwargs["composition_kwargs"],
        )
