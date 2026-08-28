"""Adversarial tests for inert HoloIndex runtime-composition generations."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_runtime_composition_contract import (
    DESCRIPTOR_NAME,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_runtime_composition_descriptor import (
    RuntimeCompositionDescriptorError,
    _VerifierDependencies,
    verify_runtime_composition_components,
    verify_runtime_composition_generation,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_runtime_composition_materializer import (
    RuntimeCompositionMaterializationError,
    _MaterializerDependencies,
    _materialize_runtime_composition_for_test,
    materialize_runtime_composition,
)
from modules.infrastructure.foundups_mcp_bridge.tests.reddog_holoindex_runtime_composition_test_support import (
    BASE_LIMITS,
    DEPENDENCY_LIMITS,
    RuntimeCompositionFixture,
    materialize_composition,
    materialized_runtime_components,
)


def _verification_kwargs(fixture: RuntimeCompositionFixture, generation: Path):
    return {
        "composition_store_root": fixture.composition_store,
        "generation_root": generation,
        "base_runtime_store_root": fixture.base_store,
        "base_generation_root": fixture.base.binding.generation_root,
        "dependency_runtime_store_root": fixture.dependency_store,
        "dependency_generation_root": fixture.dependency.binding.generation_root,
        "canonical_store": fixture.canonical,
        "repo_roots": (fixture.repo,),
        "base_limits": BASE_LIMITS,
        "dependency_limits": DEPENDENCY_LIMITS,
    }


def _materializer_kwargs(fixture: RuntimeCompositionFixture):
    values = _verification_kwargs(fixture, fixture.composition_store / "unused")
    values.pop("generation_root")
    return values


def _tree_digest(root: Path) -> str:
    hasher = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda value: value.as_posix().casefold()):
        relative = path.relative_to(root).as_posix()
        hasher.update(relative.encode("utf-8"))
        if path.is_file():
            hasher.update(path.read_bytes())
    return hasher.hexdigest()


def test_composition_is_exact_inert_path_free_and_payload_free(tmp_path: Path) -> None:
    fixture = materialized_runtime_components(tmp_path)
    base_before = _tree_digest(fixture.base.binding.generation_root)
    dependency_before = _tree_digest(fixture.dependency.binding.generation_root)
    result = materialize_composition(fixture)
    binding = result.binding

    assert result.reused_existing_generation is False
    assert binding.generation_root.name == binding.generation_id[7:]
    assert binding.interpreter_path == fixture.base.binding.base_prefix_root / "python.exe"
    assert binding.site_packages_root == fixture.dependency.binding.site_packages_root
    assert binding.artifact_bytes_independently_reverified is True
    assert all(
        getattr(binding, name) is False
        for name in (
            "abi_compatibility_verified",
            "native_loader_closure_verified",
            "deterministic_effects_verified",
            "preimport_bootstrap_verified",
            "signature_verified",
            "write_denial_verified",
            "activation_eligible",
            "exact_runtime_closure_verified",
        )
    )
    assert {path.name for path in binding.generation_root.iterdir()} == {
        DESCRIPTOR_NAME,
        ".runtime-composition-publication-orphans",
    }
    assert _tree_digest(fixture.base.binding.generation_root) == base_before
    assert _tree_digest(fixture.dependency.binding.generation_root) == dependency_before
    encoded = json.dumps(binding.public_binding)
    assert str(tmp_path) not in encoded
    assert "python-runtime" not in encoded
    assert "site-packages" not in encoded
    assert verify_runtime_composition_generation(
        **_verification_kwargs(fixture, binding.generation_root)
    ) == binding


def test_exact_reuse_never_publishes_or_copies_payload(tmp_path: Path) -> None:
    fixture = materialized_runtime_components(tmp_path)
    first = materialize_composition(fixture)

    def forbidden_publish(*_args, **_kwargs):
        raise AssertionError("exact reuse must not publish")

    second = _materialize_runtime_composition_for_test(
        **_materializer_kwargs(fixture),
        dependencies=_MaterializerDependencies(
            publish_directory=forbidden_publish
        ),
    )

    assert second.reused_existing_generation is True
    assert second.binding == first.binding


def test_component_payload_or_descriptor_tampering_fails(tmp_path: Path) -> None:
    fixture = materialized_runtime_components(tmp_path)
    composition = materialize_composition(fixture)
    dependency_file = fixture.dependency.binding.site_packages_root / "alpha.py"
    dependency_file.write_text("VALUE = 2\n", encoding="utf-8")

    with pytest.raises(RuntimeCompositionDescriptorError):
        verify_runtime_composition_generation(
            **_verification_kwargs(fixture, composition.binding.generation_root)
        )


def test_dependency_verification_cannot_stale_the_base_reproof(
    tmp_path: Path,
) -> None:
    fixture = materialized_runtime_components(tmp_path)
    trusted = _VerifierDependencies()
    calls = 0

    def mutate_verified_base(**kwargs):
        nonlocal calls
        dependency = trusted.verify_dependency(**kwargs)
        calls += 1
        if calls == 1:
            target = fixture.base.binding.base_prefix_root / "python312.dll"
            target.write_bytes(b"mutated-after-first-base-proof")
        return dependency

    with pytest.raises(
        RuntimeCompositionDescriptorError,
        match="RUNTIME_COMPOSITION_COMPONENT_MUTATED_DURING_VERIFICATION",
    ):
        verify_runtime_composition_components(
            base_runtime_store_root=fixture.base_store,
            base_generation_root=fixture.base.binding.generation_root,
            dependency_runtime_store_root=fixture.dependency_store,
            dependency_generation_root=fixture.dependency.binding.generation_root,
            canonical_store=fixture.canonical,
            repo_roots=(fixture.repo,),
            base_limits=BASE_LIMITS,
            dependency_limits=DEPENDENCY_LIMITS,
            dependencies=_VerifierDependencies(
                verify_dependency=mutate_verified_base
            ),
        )


def test_reverse_dependency_reproof_detects_one_shot_mutation(
    tmp_path: Path,
) -> None:
    fixture = materialized_runtime_components(tmp_path)
    trusted = _VerifierDependencies()
    calls = 0

    def mutate_verified_dependency(**kwargs):
        nonlocal calls
        dependency = trusted.verify_dependency(**kwargs)
        calls += 1
        if calls == 1:
            target = fixture.dependency.binding.site_packages_root / "alpha.py"
            target.write_text("VALUE = 9\n", encoding="utf-8")
        return dependency

    with pytest.raises(
        RuntimeCompositionDescriptorError,
        match="RUNTIME_COMPOSITION_COMPONENT_MUTATED_DURING_VERIFICATION",
    ):
        verify_runtime_composition_components(
            base_runtime_store_root=fixture.base_store,
            base_generation_root=fixture.base.binding.generation_root,
            dependency_runtime_store_root=fixture.dependency_store,
            dependency_generation_root=fixture.dependency.binding.generation_root,
            canonical_store=fixture.canonical,
            repo_roots=(fixture.repo,),
            base_limits=BASE_LIMITS,
            dependency_limits=DEPENDENCY_LIMITS,
            dependencies=_VerifierDependencies(
                verify_dependency=mutate_verified_dependency
            ),
        )


def test_composition_descriptor_tampering_fails(tmp_path: Path) -> None:
    fixture = materialized_runtime_components(tmp_path)
    composition = materialize_composition(fixture)
    path = composition.binding.descriptor_path
    value = json.loads(path.read_text("ascii"))
    value["activation_eligible"] = True
    path.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="ascii",
    )

    with pytest.raises(RuntimeCompositionDescriptorError):
        verify_runtime_composition_generation(
            **_verification_kwargs(fixture, composition.binding.generation_root)
        )


def test_component_generation_substitution_fails(tmp_path: Path) -> None:
    fixture = materialized_runtime_components(tmp_path)
    composition = materialize_composition(fixture)
    source = fixture.repo / ".venv" / "Lib" / "site-packages" / "alpha.py"
    source.write_text("VALUE = 3\n", encoding="utf-8")
    replacement = materialize_runtime_components_dependency(fixture, source.parent)
    kwargs = _verification_kwargs(fixture, composition.binding.generation_root)
    kwargs["dependency_generation_root"] = replacement.binding.generation_root

    with pytest.raises(
        RuntimeCompositionDescriptorError,
        match="RUNTIME_COMPOSITION_COMPONENT_BINDING_MISMATCH",
    ):
        verify_runtime_composition_generation(**kwargs)


def materialize_runtime_components_dependency(
    fixture: RuntimeCompositionFixture, source: Path,
):
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_materializer import (
        materialize_dependency_runtime,
    )

    return materialize_dependency_runtime(
        source_site_packages=source,
        runtime_store_root=fixture.dependency_store,
        canonical_store=fixture.canonical,
        repo_roots=(fixture.repo,),
        limits=DEPENDENCY_LIMITS,
    )


def test_unlisted_composition_topology_fails(tmp_path: Path) -> None:
    fixture = materialized_runtime_components(tmp_path)
    composition = materialize_composition(fixture)
    (composition.binding.generation_root / "ambient.txt").write_text(
        "ambient", encoding="utf-8"
    )

    with pytest.raises(
        RuntimeCompositionDescriptorError,
        match="RUNTIME_COMPOSITION_GENERATION_TOPOLOGY_INVALID",
    ):
        verify_runtime_composition_generation(
            **_verification_kwargs(fixture, composition.binding.generation_root)
        )


def test_component_mutation_after_descriptor_quarantines_composition(
    tmp_path: Path,
) -> None:
    fixture = materialized_runtime_components(tmp_path)

    def mutate_component(_staging: Path) -> None:
        target = fixture.dependency.binding.site_packages_root / "alpha.py"
        target.write_text("VALUE = 4\n", encoding="utf-8")

    with pytest.raises(RuntimeCompositionMaterializationError):
        _materialize_runtime_composition_for_test(
            **_materializer_kwargs(fixture),
            dependencies=_MaterializerDependencies(
                after_descriptor=mutate_component
            ),
        )

    assert not any(
        entry.is_dir() and not entry.name.startswith(".")
        for entry in fixture.composition_store.iterdir()
    )
    assert len(tuple((fixture.composition_store / ".runtime-composition-orphans").iterdir())) == 1


def test_overlapping_store_rejects_before_mutation(tmp_path: Path) -> None:
    fixture = materialized_runtime_components(tmp_path)
    existing = set(fixture.base_store.iterdir())

    with pytest.raises(
        RuntimeCompositionMaterializationError,
        match="RUNTIME_COMPOSITION_STORE_OVERLAP",
    ):
        materialize_runtime_composition(
            composition_store_root=fixture.base_store / "compositions",
            base_runtime_store_root=fixture.base_store,
            base_generation_root=fixture.base.binding.generation_root,
            dependency_runtime_store_root=fixture.dependency_store,
            dependency_generation_root=fixture.dependency.binding.generation_root,
            canonical_store=fixture.canonical,
            repo_roots=(fixture.repo,),
            base_limits=BASE_LIMITS,
            dependency_limits=DEPENDENCY_LIMITS,
        )

    assert set(fixture.base_store.iterdir()) == existing
    assert not (fixture.base_store / "compositions").exists()


@pytest.mark.parametrize("defect", ["symlink", "hardlink"])
def test_composition_descriptor_alias_rejects(
    tmp_path: Path, defect: str,
) -> None:
    fixture = materialized_runtime_components(tmp_path)
    composition = materialize_composition(fixture)
    path = composition.binding.descriptor_path
    payload = path.read_bytes()
    alternate = tmp_path / "external-composition-descriptor.json"
    path.unlink()
    try:
        alternate.write_bytes(payload)
        if defect == "symlink":
            path.symlink_to(alternate)
        else:
            os.link(alternate, path)
    except OSError:
        pytest.skip(f"{defect} unavailable")

    with pytest.raises(RuntimeCompositionDescriptorError):
        verify_runtime_composition_generation(
            **_verification_kwargs(fixture, composition.binding.generation_root)
        )
