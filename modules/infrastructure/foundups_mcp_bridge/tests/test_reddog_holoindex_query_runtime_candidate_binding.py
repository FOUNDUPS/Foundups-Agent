"""End-to-end binding tests for the inert query-runtime candidate."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import tempfile

import pytest
from holo_index.repository_state import RepositoryState
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_query_runtime_candidate_binding as binding_module,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_base_runtime_contract import (
    BaseRuntimeBinding,
    PAYLOAD_DIRECTORY,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_contract import (
    DependencyRuntimeBinding,
    INVENTORY_SCHEMA_VERSION,
    canonical_json_bytes,
    dependency_tree_digest,
    digest_bytes,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_candidate_binding import (
    CandidateBindingError,
    CandidateBindingLimits,
    _CandidateBindingDependencies,
    _build_bound_candidate_for_test,
    _reprove_bound_candidate_for_test,
    build_bound_candidate,
    reprove_bound_candidate,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_distribution_graph import (
    DistributionGraphLimits,
    DistributionProjection,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_candidate_contract import (
    CandidateLimits,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_candidate_source import (
    CandidateSourceAuthority,
    CandidateSourceAuthorityError,
    _verify_candidate_source_authority_for_test,
    verify_candidate_source_authority,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_runtime_composition_contract import (
    RuntimeCompositionBinding,
)
from modules.infrastructure.foundups_mcp_bridge.tests.test_reddog_holoindex_query_distribution_graph import (
    TARGET,
    _fixture,
)


DIGESTS = tuple(f"sha256:{index:064x}" for index in range(100, 130))


@pytest.fixture
def approved_tmp_path() -> Path:
    root = Path("O:/.reddog_test_tmp")
    if os.name != "nt" or not root.anchor.upper().startswith("O:"):
        pytest.skip("approved O:-local Windows test volume unavailable")
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="query-candidate-", dir=root) as value:
        yield Path(value)


def _dependency_binding(root: Path) -> tuple[DependencyRuntimeBinding, dict[str, object]]:
    rows, payloads, _stems = _fixture()
    dependency_root = root / "dependency"
    site_packages = dependency_root / "site-packages"
    for path, payload in payloads.items():
        target = site_packages / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    directories = sorted({
        str(parent.relative_to(site_packages)).replace("\\", "/")
        for path in payloads for parent in (site_packages / path).parents
        if parent != site_packages and site_packages in parent.parents
    }, key=str.casefold)
    inventory = {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "directories": directories, "files": rows,
    }
    return DependencyRuntimeBinding(
        generation_root=dependency_root, site_packages_root=site_packages,
        descriptor_path=dependency_root / "holoindex_dependency_payload_descriptor.json",
        descriptor_digest=DIGESTS[0], generation_id=DIGESTS[1],
        inventory_digest=digest_bytes(canonical_json_bytes(inventory)),
        dependency_tree_digest=dependency_tree_digest(directories, rows),
        file_count=len(rows), directory_count=len(directories),
        total_bytes=sum(row["size"] for row in rows),
        artifact_bytes_verified_at_publication=True,
        write_denial_verified=False, activation_eligible=False,
    ), inventory


def _base_binding(root: Path) -> BaseRuntimeBinding:
    generation_root = root / "base"
    base_root = generation_root / PAYLOAD_DIRECTORY
    return BaseRuntimeBinding(
        generation_root=generation_root, base_prefix_root=base_root,
        descriptor_path=generation_root / "holoindex_base_runtime_descriptor.json",
        descriptor_digest=DIGESTS[2], generation_id=DIGESTS[3],
        inventory_digest=DIGESTS[4], base_runtime_tree_digest=DIGESTS[5],
        file_count=1, directory_count=0, total_bytes=1,
        artifact_bytes_verified_at_publication=True,
        native_loader_closure_verified=False, deterministic_effects_verified=False,
        signature_verified=False, write_denial_verified=False,
        activation_eligible=False, exact_runtime_closure_verified=False,
    )


def _composition(root: Path) -> tuple[RuntimeCompositionBinding, dict[str, object]]:
    dependency, inventory = _dependency_binding(root)
    base = _base_binding(root)
    composition_root = root / "composition"
    return RuntimeCompositionBinding(
        generation_root=composition_root,
        descriptor_path=composition_root / "holoindex_runtime_composition_descriptor.json",
        descriptor_digest=DIGESTS[6], generation_id=DIGESTS[7],
        base_runtime=base, dependency_runtime=dependency,
        interpreter_path=base.base_prefix_root / "python.exe",
        interpreter_content_digest=DIGESTS[8], interpreter_size=1,
        site_packages_root=dependency.site_packages_root,
        artifact_bytes_independently_reverified=True,
        abi_compatibility_verified=False, native_loader_closure_verified=False,
        deterministic_effects_verified=False, preimport_bootstrap_verified=False,
        signature_verified=False, write_denial_verified=False,
        activation_eligible=False, exact_runtime_closure_verified=False,
    ), inventory


def _source(root: Path) -> CandidateSourceAuthority:
    source_root = root / "source"
    source_root.mkdir()
    return CandidateSourceAuthority(
        repo_root=source_root, repo_head_sha="a" * 40,
        repo_root_digest=DIGESTS[9], repository_state_digest=DIGESTS[10],
        backend_manifest_digest=DIGESTS[11],
        verified_runtime_closure_digest=DIGESTS[12],
        runtime_file_count=10, runtime_file_bytes=100,
        runtime_source_bytes_verified=True,
        phase2a_module_set_digest=DIGESTS[13],
        phase2a_module_count=8, phase2a_module_bytes=80,
        phase2a_module_set_verified=True,
    )


def _composition_kwargs(root: Path) -> dict[str, object]:
    return {
        "composition_store_root": root / "composition-store",
        "generation_root": root / "composition-generation",
        "base_runtime_store_root": root / "base-store",
        "base_generation_root": root / "base-generation",
        "dependency_runtime_store_root": root / "dependency-store",
        "dependency_generation_root": root / "dependency-generation",
        "canonical_store": root / "canonical", "repo_roots": (root / "source",),
    }


def _inputs(root: Path) -> tuple[dict[str, object], _CandidateBindingDependencies]:
    composition, inventory = _composition(root)
    source = _source(root)
    dependencies = _CandidateBindingDependencies(
        verify_composition=lambda **_kwargs: composition,
        verify_source=lambda **_kwargs: source,
    )
    inputs = {
        "composition_kwargs": _composition_kwargs(root),
        "source_authority_kwargs": {
            "source_root": source.repo_root,
            "expected_repo_head_sha": source.repo_head_sha,
        },
        "dependency_inventory": inventory,
        "root_requirements": [{"name": "demo", "version": "1.0", "extras": []}],
        "module_origins": ["demo/__init__.py", "dep/native.cp312-win_amd64.pyd"],
        "marker_environment": TARGET,
        "dynamic_surfaces": [{
            "kind": "import_module", "owner": "demo", "target": "dep",
        }],
        "observed_import_trace": {
            "trace_digest": DIGESTS[13], "module_count": 2,
            "native_extension_count": 1, "completeness_claimed": False,
        },
        "temporary_runtime_volume": "O",
    }
    return inputs, dependencies


def _build(
    inputs: dict[str, object], dependencies: _CandidateBindingDependencies,
):
    return _build_bound_candidate_for_test(**inputs, dependencies=dependencies)


def _source_fixture(root: Path) -> tuple[Path, str, RepositoryState]:
    source = root / "source-fixture"
    (source / "scripts").mkdir(parents=True)
    files = {
        "candidate-only.py": b"CANDIDATE = 1\n",
        "main.py": b"print('marker')\n",
        "runtime.py": b"VALUE = 1\n",
        "scripts/tool.py": b"print('tool')\n",
    }
    for relative, payload in files.items():
        target = source.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    runtime = ["runtime.py", "scripts/tool.py"]
    digests = {
        relative: hashlib.sha256(files[relative]).hexdigest() for relative in runtime
    }
    manifest = {
        "schema_version": "reddog_backend_manifest.v3",
        "product": "foundups-agent-reddog-backend", "backend_api_version": 2,
        "runtime_dependency_graph_version": 2,
        "required_executable_files": ["scripts/tool.py"],
        "required_bridge_files": ["scripts/tool.py"],
        "required_bridge_sha256": {"scripts/tool.py": digests["scripts/tool.py"]},
        "required_runtime_files": runtime,
        "required_runtime_sha256": digests,
        "required_repository_markers": ["main.py"],
    }
    (source / "scripts/reddog_backend_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8",
    )
    head = "b" * 40
    state = RepositoryState(head, True, DIGESTS[20])
    return source, head, state


def test_bound_candidate_brackets_exact_authorities(approved_tmp_path: Path) -> None:
    inputs, dependencies = _inputs(approved_tmp_path)
    result = _build(inputs, dependencies)

    assert result.descriptor["candidate_identity_validated"] is True
    assert result.inventory["source_authority"]["repo_head_sha"] == "a" * 40
    assert _reprove_bound_candidate_for_test(
        expected_inventory=result.inventory, expected_descriptor=result.descriptor,
        build_inputs=inputs, dependencies=dependencies,
    ) == result


def test_same_inputs_produce_exact_same_projection_and_candidate(
    approved_tmp_path: Path,
) -> None:
    inputs, dependencies = _inputs(approved_tmp_path)
    first = _build(inputs, dependencies)
    second = _build(inputs, dependencies)
    assert second == first
    assert second.inventory["projection_digest"] == first.inventory["projection_digest"]


def test_binding_rejects_inventory_substitution_and_unbounded_inputs(
    approved_tmp_path: Path,
) -> None:
    inputs, dependencies = _inputs(approved_tmp_path)
    tampered = dict(inputs["dependency_inventory"])
    tampered["files"] = [dict(row) for row in tampered["files"]]
    tampered["files"][0]["sha256"] = DIGESTS[14]
    with pytest.raises(CandidateBindingError, match="DEPENDENCY_BINDING_MISMATCH"):
        _build({**inputs, "dependency_inventory": tampered}, dependencies)

    oversized = [dict(inputs["dynamic_surfaces"][0]) for _ in range(4_097)]
    with pytest.raises(CandidateBindingError, match="DECLARATION_INVALID"):
        _build({**inputs, "dynamic_surfaces": oversized}, dependencies)
    with pytest.raises(CandidateBindingError, match="VOLUME_INVALID"):
        _build({**inputs, "temporary_runtime_volume": object()}, dependencies)


def test_nested_input_strings_reject_before_authority_calls(
    approved_tmp_path: Path,
) -> None:
    inputs, dependencies = _inputs(approved_tmp_path)

    def unexpected(**_kwargs):
        raise AssertionError("authority verifier must not run")

    guarded = replace(
        dependencies, verify_source=unexpected, verify_composition=unexpected,
    )
    cases = (
        {"root_requirements": [{"name": "x" * 257, "version": "1", "extras": []}]},
        {"root_requirements": [{"name": "demo", "version": "1", "extras": ["x" * 257]}]},
        {"dynamic_surfaces": [{"kind": "import_module", "owner": "demo", "target": "x" * 1025}]},
        {"module_origins": ["x" * 513]},
    )
    for update in cases:
        with pytest.raises(CandidateBindingError):
            _build({**inputs, **update}, guarded)


def test_relaxed_public_limits_above_ceiling_reject(
    approved_tmp_path: Path,
) -> None:
    inputs, dependencies = _inputs(approved_tmp_path)
    cases = (
        {"candidate_limits": CandidateLimits(max_files=100_001)},
        {"graph_limits": DistributionGraphLimits(max_files=100_001)},
        {"binding_limits": CandidateBindingLimits(max_binding_arguments=17)},
    )
    for update in cases:
        with pytest.raises(CandidateBindingError, match="LIMIT_INVALID"):
            _build({**inputs, **update}, dependencies)


def test_binding_rejects_ambient_and_drive_relative_composition_paths(
    approved_tmp_path: Path,
) -> None:
    inputs, dependencies = _inputs(approved_tmp_path)
    composition = dependencies.verify_composition()
    for external in (
        replace(composition, generation_root=Path("O:relative")),
        replace(composition, interpreter_path=Path("C:/ambient/python.exe")),
        replace(
            composition,
            dependency_runtime=replace(
                composition.dependency_runtime,
                site_packages_root=Path("C:/ambient/site-packages"),
            ),
            site_packages_root=Path("C:/ambient/site-packages"),
        ),
    ):
        hostile = replace(dependencies, verify_composition=lambda **_kwargs: external)
        with pytest.raises(CandidateBindingError, match="VOLUME_INVALID"):
            _build(inputs, hostile)


def test_composition_requires_only_the_exact_source_repo_root(
    approved_tmp_path: Path,
) -> None:
    inputs, dependencies = _inputs(approved_tmp_path)
    missing = dict(inputs["composition_kwargs"])
    missing["repo_roots"] = (approved_tmp_path / "other",)
    with pytest.raises(CandidateBindingError, match="SOURCE_REPO_ROOT_UNBOUND"):
        _build({**inputs, "composition_kwargs": missing}, dependencies)

    extra = dict(inputs["composition_kwargs"])
    extra["repo_roots"] = (*extra["repo_roots"], approved_tmp_path / "other")
    with pytest.raises(CandidateBindingError, match="SOURCE_REPO_ROOT_UNBOUND"):
        _build({**inputs, "composition_kwargs": extra}, dependencies)


def test_cross_pass_source_or_composition_mutation_rejects(approved_tmp_path: Path) -> None:
    inputs, dependencies = _inputs(approved_tmp_path)
    source = dependencies.verify_source()
    calls = iter((source, replace(source, runtime_file_bytes=101)))
    changed = replace(dependencies, verify_source=lambda **_kwargs: next(calls))
    with pytest.raises(CandidateBindingError, match="AUTHORITY_MUTATED_DURING_BUILD"):
        _build(inputs, changed)


def test_upstream_verifier_errors_are_path_free(approved_tmp_path: Path) -> None:
    inputs, dependencies = _inputs(approved_tmp_path)

    def leaking_verifier(**_kwargs):
        raise RuntimeError("C:/private")

    hostile = replace(dependencies, verify_source=leaking_verifier)
    with pytest.raises(CandidateBindingError) as captured:
        _build(inputs, hostile)
    assert str(captured.value) == "QUERY_RUNTIME_CANDIDATE_SOURCE_VERIFICATION_FAILED"


def test_public_build_and_reproof_fail_until_builder_runtime_is_bound(
    approved_tmp_path: Path,
) -> None:
    inputs, dependencies = _inputs(approved_tmp_path)
    with pytest.raises(TypeError):
        build_bound_candidate(**inputs, _dependencies=dependencies)
    with pytest.raises(CandidateBindingError, match="BUILDER_RUNTIME_UNBOUND"):
        build_bound_candidate(**inputs)
    with pytest.raises(CandidateBindingError, match="BUILDER_RUNTIME_UNBOUND"):
        reprove_bound_candidate(
            expected_inventory={}, expected_descriptor={}, **inputs,
        )

    source, head, state = _source_fixture(approved_tmp_path)
    with pytest.raises(TypeError):
        verify_candidate_source_authority(
            source_root=source, expected_repo_head_sha=head,
            state_reader=lambda _root: state,
        )


def test_transitive_http_server_distribution_conflicts_with_stdlib_transport(
    approved_tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, dependencies = _inputs(approved_tmp_path)
    projection = DistributionProjection(
        [{"name": "fastapi"}], [], [], [], TARGET, DIGESTS[18], DIGESTS[19],
    )
    monkeypatch.setattr(
        binding_module, "_derive_projection", lambda *_args, **_kwargs: projection,
    )
    with pytest.raises(CandidateBindingError, match="STDLIB_TRANSPORT_CONFLICT"):
        _build(inputs, dependencies)


def test_source_authority_verifies_complete_manifest_and_bytes(
    approved_tmp_path: Path,
) -> None:
    source, head, state = _source_fixture(approved_tmp_path)
    result = _verify_candidate_source_authority_for_test(
        source_root=source, expected_repo_head_sha=head,
        state_reader=lambda _root: state,
    )
    manifest = json.loads((source / "scripts/reddog_backend_manifest.json").read_text())
    canonical = json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")
    assert result.backend_manifest_digest == f"sha256:{hashlib.sha256(canonical).hexdigest()}"
    assert result.runtime_file_count == 2
    assert result.runtime_source_bytes_verified is True


def test_source_authority_binds_exact_phase2a_module_set_and_loaded_origins(
    approved_tmp_path: Path,
) -> None:
    source, head, state = _source_fixture(approved_tmp_path)
    files = ("candidate-only.py", "runtime.py")
    paths = {relative: source / relative for relative in files}
    result = _verify_candidate_source_authority_for_test(
        source_root=source, expected_repo_head_sha=head,
        state_reader=lambda _root: state, candidate_source_files=files,
        executing_source_paths=paths,
    )
    assert result.phase2a_module_count == 2
    assert result.phase2a_module_bytes == sum((source / item).stat().st_size for item in files)
    assert result.phase2a_module_set_verified is True

    (source / "candidate-only.py").unlink()
    with pytest.raises(CandidateSourceAuthorityError, match="EXECUTING_SOURCE_INVALID"):
        _verify_candidate_source_authority_for_test(
            source_root=source, expected_repo_head_sha=head,
            state_reader=lambda _root: state, candidate_source_files=files,
            executing_source_paths=paths,
        )


def test_source_authority_rejects_executing_module_substitution(
    approved_tmp_path: Path,
) -> None:
    source, head, state = _source_fixture(approved_tmp_path)
    with pytest.raises(CandidateSourceAuthorityError, match="EXECUTING_SOURCE_INVALID"):
        _verify_candidate_source_authority_for_test(
            source_root=source, expected_repo_head_sha=head,
            state_reader=lambda _root: state,
            executing_source_paths={"runtime.py": source / "candidate-only.py"},
        )


def test_source_authority_rejects_linked_root_when_capability_exists(
    approved_tmp_path: Path,
) -> None:
    source, head, state = _source_fixture(approved_tmp_path)
    alias = approved_tmp_path / "source-link"
    try:
        os.symlink(source, alias, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink capability unavailable: {exc.winerror}")
    with pytest.raises(CandidateSourceAuthorityError, match="SOURCE_ROOT_INVALID"):
        _verify_candidate_source_authority_for_test(
            source_root=alias, expected_repo_head_sha=head,
            state_reader=lambda _root: state,
        )


def test_candidate_requirements_are_exact_and_disjoint_from_launcher() -> None:
    module_root = Path(__file__).parents[1]
    launcher = [
        row for row in
        (module_root / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if row and not row.startswith("#")
    ]
    candidate = [
        row for row in (
        module_root / "requirements-query-candidate.txt"
        ).read_text(encoding="utf-8").splitlines()
        if row and not row.startswith("#")
    ]
    assert launcher == [
        "fastmcp==2.13.0.2", "mcp==1.20.0", "pydantic==2.12.3", "uvicorn==0.38.0",
    ]
    assert candidate == ["packaging==26.0"]
    launcher_names = {row.partition("==")[0].casefold() for row in launcher}
    candidate_names = {row.partition("==")[0].casefold() for row in candidate}
    assert launcher_names.isdisjoint(candidate_names)


def test_source_authority_rejects_wrong_head_and_manifest_substitution(
    approved_tmp_path: Path,
) -> None:
    source, head, state = _source_fixture(approved_tmp_path)
    with pytest.raises(CandidateSourceAuthorityError, match="SOURCE_STATE_INVALID"):
        _verify_candidate_source_authority_for_test(
            source_root=source, expected_repo_head_sha="c" * 40,
            state_reader=lambda _root: state,
        )
    (source / "runtime.py").write_bytes(b"changed\n")
    with pytest.raises(CandidateSourceAuthorityError, match="SOURCE_DIGEST_MISMATCH"):
        _verify_candidate_source_authority_for_test(
            source_root=source, expected_repo_head_sha=head,
            state_reader=lambda _root: state,
        )


def test_source_authority_rejects_cross_pass_state_and_hardlinks(
    approved_tmp_path: Path,
) -> None:
    source, head, state = _source_fixture(approved_tmp_path)
    changed_state = replace(state, state_digest=DIGESTS[21])
    states = iter((state, changed_state))
    with pytest.raises(CandidateSourceAuthorityError, match="MUTATED_DURING_SCAN"):
        _verify_candidate_source_authority_for_test(
            source_root=source, expected_repo_head_sha=head,
            state_reader=lambda _root: next(states),
        )

    _source, _head, clean_state = _source_fixture(approved_tmp_path / "hardlink")
    os.link(_source / "runtime.py", _source / "runtime-link.py")
    with pytest.raises(CandidateSourceAuthorityError, match="SOURCE_FILE_INVALID"):
        _verify_candidate_source_authority_for_test(
            source_root=_source, expected_repo_head_sha=_head,
            state_reader=lambda _root: clean_state,
        )
