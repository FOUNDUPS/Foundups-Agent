"""Adversarial tests for inert Holo dependency-runtime generations."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from modules.infrastructure.foundups_mcp_bridge.tests.reddog_holoindex_test_fs_support import (
    create_directory_alias_or_skip,
)

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_contract import (
    DESCRIPTOR_NAME,
    INVENTORY_NAME,
    DependencyRuntimeLimits,
    canonical_json_bytes,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_descriptor import (
    DependencyRuntimeDescriptorError,
    verify_dependency_runtime_generation,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_copy import (
    copy_dependency_runtime_snapshot,
    plan_dependency_runtime_snapshot,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_materializer import (
    DependencyRuntimeMaterializationError,
    _MaterializerDependencies,
    _materialize_dependency_runtime_for_test,
    materialize_dependency_runtime,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica_generation import (
    publish_directory_no_replace,
)


LIMITS = DependencyRuntimeLimits(
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


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    repo = tmp_path / "repo"
    canonical = tmp_path / "canonical"
    source = repo / ".venv" / "Lib" / "site-packages"
    runtime = tmp_path / "query-runtimes"
    (repo / ".git").mkdir(parents=True)
    canonical.mkdir()
    (source / "alpha").mkdir(parents=True)
    (source / "alpha.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "alpha" / "data.bin").write_bytes(b"payload")
    return repo, canonical, source, runtime


def _materialize(tmp_path: Path):
    repo, canonical, source, runtime = _fixture(tmp_path)
    result = materialize_dependency_runtime(
        source_site_packages=source,
        runtime_store_root=runtime,
        canonical_store=canonical,
        repo_roots=(repo,),
        limits=LIMITS,
    )
    return repo, canonical, source, runtime, result


def _verify(repo: Path, canonical: Path, runtime: Path, generation: Path):
    return verify_dependency_runtime_generation(
        runtime_store_root=runtime,
        generation_root=generation,
        canonical_store=canonical,
        repo_roots=(repo,),
        limits=LIMITS,
    )


def test_materialization_is_content_addressed_inert_and_path_free(
    tmp_path: Path,
) -> None:
    repo, canonical, _source, runtime, result = _materialize(tmp_path)
    binding = result.binding

    assert result.reused_existing_generation is False
    assert binding.generation_root.name == binding.generation_id.removeprefix("sha256:")
    assert binding.file_count == 2
    assert binding.artifact_bytes_verified_at_publication is True
    assert binding.write_denial_verified is False
    assert binding.activation_eligible is False
    assert _verify(repo, canonical, runtime, binding.generation_root) == binding

    descriptor = json.loads((binding.generation_root / DESCRIPTOR_NAME).read_text("ascii"))
    inventory = json.loads((binding.generation_root / INVENTORY_NAME).read_text("ascii"))
    serialized = json.dumps({"descriptor": descriptor, "inventory": inventory})
    assert str(repo) not in serialized
    assert str(runtime) not in serialized
    assert descriptor["activation_eligible"] is False
    assert descriptor["write_denial_verified"] is False


def test_second_identical_materialization_reuses_without_overwrite(
    tmp_path: Path,
) -> None:
    repo, canonical, source, runtime, first = _materialize(tmp_path)
    descriptor_before = (first.binding.generation_root / DESCRIPTOR_NAME).read_bytes()

    second = materialize_dependency_runtime(
        source_site_packages=source,
        runtime_store_root=runtime,
        canonical_store=canonical,
        repo_roots=(repo,),
        limits=LIMITS,
    )

    assert second.reused_existing_generation is True
    assert second.binding == first.binding
    assert (first.binding.generation_root / DESCRIPTOR_NAME).read_bytes() == descriptor_before
    assert not (runtime / ".dependency-runtime-orphans").exists()


def test_source_change_after_publication_cannot_mutate_old_generation(
    tmp_path: Path,
) -> None:
    repo, canonical, source, runtime, first = _materialize(tmp_path)
    original_payload = first.binding.site_packages_root / "alpha.py"
    original_bytes = original_payload.read_bytes()
    (source / "alpha.py").write_text("VALUE = 2\n", encoding="utf-8")

    assert _verify(
        repo, canonical, runtime, first.binding.generation_root
    ) == first.binding
    second = materialize_dependency_runtime(
        source_site_packages=source,
        runtime_store_root=runtime,
        canonical_store=canonical,
        repo_roots=(repo,),
        limits=LIMITS,
    )

    assert second.binding.generation_id != first.binding.generation_id
    assert original_payload.read_bytes() == original_bytes
    assert _verify(
        repo, canonical, runtime, first.binding.generation_root
    ) == first.binding


def test_published_payload_mutation_fails_full_reverification(tmp_path: Path) -> None:
    repo, canonical, _source, runtime, result = _materialize(tmp_path)
    target = result.binding.site_packages_root / "alpha.py"
    target.write_text("VALUE = 2\n", encoding="utf-8")

    with pytest.raises(
        DependencyRuntimeDescriptorError,
        match="DEPENDENCY_RUNTIME_PAYLOAD_DIGEST_MISMATCH",
    ):
        _verify(repo, canonical, runtime, result.binding.generation_root)


def test_unlisted_payload_fails_full_reverification(tmp_path: Path) -> None:
    repo, canonical, _source, runtime, result = _materialize(tmp_path)
    (result.binding.site_packages_root / "ambient.py").write_text(
        "AMBIENT = True\n", encoding="utf-8"
    )

    with pytest.raises(
        DependencyRuntimeDescriptorError,
        match="DEPENDENCY_RUNTIME_INVENTORY_MISMATCH",
    ):
        _verify(repo, canonical, runtime, result.binding.generation_root)


def test_unlisted_empty_namespace_directory_fails_reverification(tmp_path: Path) -> None:
    repo, canonical, _source, runtime, result = _materialize(tmp_path)
    (result.binding.site_packages_root / "ambient_namespace").mkdir()

    with pytest.raises(
        DependencyRuntimeDescriptorError,
        match="DEPENDENCY_RUNTIME_INVENTORY_MISMATCH",
    ):
        _verify(repo, canonical, runtime, result.binding.generation_root)


def test_empty_source_directory_is_copied_and_identity_bound(tmp_path: Path) -> None:
    repo, canonical, source, runtime = _fixture(tmp_path)
    (source / "empty_namespace").mkdir()
    result = materialize_dependency_runtime(
        source_site_packages=source, runtime_store_root=runtime,
        canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
    )

    assert (result.binding.site_packages_root / "empty_namespace").is_dir()
    assert result.binding.directory_count == 2


def test_existing_generation_reuse_never_invokes_copy(tmp_path: Path) -> None:
    repo, canonical, source, runtime, first = _materialize(tmp_path)

    def forbidden_copy(*_args, **_kwargs):
        raise AssertionError("copy must not run for exact reuse")

    second = _materialize_dependency_runtime_for_test(
        source_site_packages=source, runtime_store_root=runtime,
        canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
        dependencies=_MaterializerDependencies(copy_tree=forbidden_copy),
    )

    assert second.reused_existing_generation is True
    assert second.binding == first.binding
    assert not (runtime / ".dependency-runtime-orphans").exists()


def test_corrupt_existing_generation_fails_before_copy(tmp_path: Path) -> None:
    repo, canonical, source, runtime, first = _materialize(tmp_path)
    (first.binding.site_packages_root / "alpha.py").write_text(
        "VALUE = 9\n", encoding="utf-8"
    )

    def forbidden_copy(*_args, **_kwargs):
        raise AssertionError("copy must not replace an existing digest root")

    with pytest.raises(
        DependencyRuntimeMaterializationError,
        match="DEPENDENCY_RUNTIME_PAYLOAD_DIGEST_MISMATCH",
    ):
        _materialize_dependency_runtime_for_test(
            source_site_packages=source, runtime_store_root=runtime,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
            dependencies=_MaterializerDependencies(copy_tree=forbidden_copy),
        )


def test_unpublished_staging_is_verified_before_generation_publish(
    tmp_path: Path,
) -> None:
    repo, canonical, source, runtime = _fixture(tmp_path)
    published = False

    def corrupt(staging: Path) -> None:
        (staging / "site-packages" / "alpha.py").write_text(
            "VALUE = 7\n", encoding="utf-8"
        )

    def forbidden_publish(_source: Path, _target: Path) -> None:
        nonlocal published
        published = True

    with pytest.raises(
        DependencyRuntimeMaterializationError,
        match="DEPENDENCY_RUNTIME_PAYLOAD_DIGEST_MISMATCH",
    ):
        _materialize_dependency_runtime_for_test(
            source_site_packages=source, runtime_store_root=runtime,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
            dependencies=_MaterializerDependencies(
                after_contracts=corrupt, publish_directory=forbidden_publish
            ),
        )

    assert published is False
    assert not any(
        entry.is_dir() and not entry.name.startswith(".")
        for entry in runtime.iterdir()
    )


def test_postpublication_mutation_quarantines_owned_generation(tmp_path: Path) -> None:
    repo, canonical, source, runtime = _fixture(tmp_path)

    def publish_then_corrupt(staging: Path, target: Path) -> None:
        publish_directory_no_replace(staging, target)
        (target / "site-packages" / "alpha.py").write_text(
            "VALUE = 8\n", encoding="utf-8"
        )

    with pytest.raises(
        DependencyRuntimeMaterializationError,
        match="DEPENDENCY_RUNTIME_PAYLOAD_DIGEST_MISMATCH",
    ):
        _materialize_dependency_runtime_for_test(
            source_site_packages=source, runtime_store_root=runtime,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
            dependencies=_MaterializerDependencies(
                publish_directory=publish_then_corrupt
            ),
        )

    assert not any(
        entry.is_dir() and not entry.name.startswith(".")
        for entry in runtime.iterdir()
    )
    assert len(tuple((runtime / ".dependency-runtime-orphans").iterdir())) == 1


def test_descriptor_cannot_claim_activation_or_write_denial(tmp_path: Path) -> None:
    repo, canonical, _source, runtime, result = _materialize(tmp_path)
    descriptor_path = result.binding.generation_root / DESCRIPTOR_NAME
    value = json.loads(descriptor_path.read_text("ascii"))
    value["activation_eligible"] = True
    descriptor_path.write_bytes(canonical_json_bytes(value))

    with pytest.raises(
        DependencyRuntimeDescriptorError,
        match="DEPENDENCY_RUNTIME_DESCRIPTOR_TRUTH_INVALID",
    ):
        _verify(repo, canonical, runtime, result.binding.generation_root)


def test_casefold_alias_is_not_materialized_as_valid_generation(
    tmp_path: Path,
) -> None:
    repo, canonical, source, runtime = _fixture(tmp_path)
    upper = source / "Alias.py"
    lower = source / "alias.py"
    upper.write_text("UPPER = True\n", encoding="utf-8")
    try:
        lower.write_text("LOWER = True\n", encoding="utf-8")
    except OSError:
        pytest.skip("case-distinct filenames unavailable")
    if len([entry for entry in source.iterdir() if entry.name.casefold() == "alias.py"]) < 2:
        pytest.skip("case-distinct filenames unavailable")

    with pytest.raises(
        (DependencyRuntimeMaterializationError, DependencyRuntimeDescriptorError),
        match="DEPENDENCY_RUNTIME_INVENTORY_ORDER_INVALID",
    ):
        materialize_dependency_runtime(
            source_site_packages=source,
            runtime_store_root=runtime,
            canonical_store=canonical,
            repo_roots=(repo,),
            limits=LIMITS,
        )


def test_source_link_is_rejected_before_valid_generation(tmp_path: Path) -> None:
    repo, canonical, source, runtime = _fixture(tmp_path)
    link = source / "linked.py"
    try:
        link.symlink_to(source / "alpha.py")
    except OSError:
        pytest.skip("file symlink unavailable")

    with pytest.raises(
        DependencyRuntimeMaterializationError,
        match="MODEL_LINK_OR_REPARSE_REJECTED",
    ):
        materialize_dependency_runtime(
            source_site_packages=source,
            runtime_store_root=runtime,
            canonical_store=canonical,
            repo_roots=(repo,),
            limits=LIMITS,
        )


def test_runtime_store_inside_repo_is_rejected(tmp_path: Path) -> None:
    repo, canonical, source, _runtime = _fixture(tmp_path)
    with pytest.raises(DependencyRuntimeMaterializationError):
        materialize_dependency_runtime(
            source_site_packages=source,
            runtime_store_root=repo / "runtime",
            canonical_store=canonical,
            repo_roots=(repo,),
            limits=LIMITS,
        )


def test_copy_failure_is_preserved_without_generation_activation(
    tmp_path: Path,
) -> None:
    repo, canonical, source, runtime = _fixture(tmp_path)

    def fail_copy(*_args, **_kwargs):
        raise OSError("synthetic-copy-failure")

    with pytest.raises(
        DependencyRuntimeMaterializationError,
        match="synthetic-copy-failure",
    ):
        _materialize_dependency_runtime_for_test(
            source_site_packages=source,
            runtime_store_root=runtime,
            canonical_store=canonical,
            repo_roots=(repo,),
            limits=LIMITS,
            dependencies=_MaterializerDependencies(copy_tree=fail_copy),
        )

    orphans = runtime / ".dependency-runtime-orphans"
    assert orphans.is_dir()
    assert len(tuple(orphans.iterdir())) == 1
    assert not any(
        entry.is_dir() and not entry.name.startswith(".")
        for entry in runtime.iterdir()
    )


def test_hardlinked_source_payload_is_rejected(tmp_path: Path) -> None:
    repo, canonical, source, runtime = _fixture(tmp_path)
    try:
        os.link(source / "alpha.py", source / "alpha-hardlink.py")
    except OSError:
        pytest.skip("hardlink creation unavailable")

    with pytest.raises(
        DependencyRuntimeMaterializationError,
        match="MODEL_SPECIAL_FILE_REJECTED",
    ):
        materialize_dependency_runtime(
            source_site_packages=source,
            runtime_store_root=runtime,
            canonical_store=canonical,
            repo_roots=(repo,),
            limits=LIMITS,
        )


def test_source_root_link_is_not_resolved_away(tmp_path: Path) -> None:
    repo, canonical, source, runtime = _fixture(tmp_path)
    alias = repo / "site-packages-alias"
    create_directory_alias_or_skip(alias, source)

    with pytest.raises(
        DependencyRuntimeMaterializationError,
        match="PATH_LINK_OR_REPARSE_REJECTED",
    ):
        materialize_dependency_runtime(
            source_site_packages=alias, runtime_store_root=runtime,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
        )


def test_source_mutation_after_plan_fails_copy_against_ephemeral_plan(
    tmp_path: Path,
) -> None:
    repo, canonical, source, runtime = _fixture(tmp_path)

    def mutate_then_copy(source_root: Path, destination: Path, **kwargs):
        (source_root / "alpha.py").write_text("VALUE = 3\n", encoding="utf-8")
        return copy_dependency_runtime_snapshot(source_root, destination, **kwargs)

    with pytest.raises(
        DependencyRuntimeMaterializationError,
        match="MODEL_EXPECTED_DIGEST_MISMATCH",
    ):
        _materialize_dependency_runtime_for_test(
            source_site_packages=source, runtime_store_root=runtime,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
            dependencies=_MaterializerDependencies(copy_tree=mutate_then_copy),
        )


def test_directory_count_bound_fails_before_copy(tmp_path: Path) -> None:
    repo, canonical, source, runtime = _fixture(tmp_path)
    (source / "extra-empty").mkdir()
    bounded = DependencyRuntimeLimits(
        max_files=20, max_directories=2, max_directory_depth=8,
        max_path_bytes=256, max_total_path_bytes=2048,
        max_file_bytes=1024 * 1024, max_total_bytes=4 * 1024 * 1024,
        max_inventory_bytes=64 * 1024, max_descriptor_bytes=16 * 1024,
    )

    with pytest.raises(
        DependencyRuntimeMaterializationError,
        match="DEPENDENCY_RUNTIME_SOURCE_DIRECTORY_BOUND",
    ):
        materialize_dependency_runtime(
            source_site_packages=source, runtime_store_root=runtime,
            canonical_store=canonical, repo_roots=(repo,), limits=bounded,
        )
