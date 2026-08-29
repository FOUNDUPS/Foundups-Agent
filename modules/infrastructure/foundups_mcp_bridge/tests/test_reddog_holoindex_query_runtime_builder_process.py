from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_query_runtime_builder_process as builder_process_module,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_base_runtime_contract import (
    BaseRuntimeBinding,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_contract import (
    DependencyRuntimeBinding,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_process_image import (
    prove_process_executable_path,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_process import (
    BuilderProcessObservation,
    QueryRuntimeBuilderProcessError,
    _prove_builder_process_authority_for_test,
    prove_builder_process_authority,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_runtime_composition_contract import (
    RuntimeCompositionBinding,
)


def _d(char: str) -> str:
    return "sha256:" + char * 64


def _fixture():
    Path("O:/tmp").mkdir(parents=True, exist_ok=True)
    temp = tempfile.TemporaryDirectory(prefix="reddog-builder-process-", dir="O:/tmp")
    root = Path(temp.name)
    base_root = root / "base"
    dependency_root = root / "dependency"
    site = dependency_root / "site-packages"
    repo = root / "repo"
    composition_root = root / "composition"
    for directory in (base_root / "DLLs", base_root / "Lib", site, repo, composition_root):
        directory.mkdir(parents=True, exist_ok=True)
    image = base_root / "python.exe"
    payload = b"sealed-python-image"
    image.write_bytes(payload)
    base = BaseRuntimeBinding(
        base_root, base_root, base_root / "holoindex_base_runtime_descriptor.json",
        _d("1"), _d("2"), _d("3"), _d("4"), 1, 2, len(payload), True,
        False, False, False, False, False, False,
    )
    dependency = DependencyRuntimeBinding(
        dependency_root, site,
        dependency_root / "holoindex_dependency_payload_descriptor.json",
        _d("5"), _d("6"), _d("7"), _d("8"), 1, 1, 1, True, False, False,
    )
    image_digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    composition = RuntimeCompositionBinding(
        composition_root,
        composition_root / "holoindex_runtime_composition_descriptor.json",
        _d("9"), _d("a"), base, dependency, image, image_digest, len(payload), site,
        True, False, False, False, False, False, False, False, False,
    )
    observation = BuilderProcessObservation(
        executable=image,
        isolated=1,
        no_site=1,
        dont_write_bytecode=1,
        ignore_environment=1,
        no_user_site=1,
        sys_prefix=base_root,
        sys_base_prefix=base_root,
        sys_exec_prefix=base_root,
        sys_base_exec_prefix=base_root,
        sys_path=(
            base_root / "python312.zip", base_root / "DLLs", base_root / "Lib",
            base_root, site, repo,
        ),
        stdlib_zip_name="python312.zip",
    )
    return temp, composition, repo, observation, prove_process_executable_path(image)


def test_actual_image_and_isolated_path_roles_are_bound() -> None:
    temp, composition, repo, observation, proof = _fixture()
    try:
        authority = _prove_builder_process_authority_for_test(
            composition=composition,
            repo_root=repo,
            observation=observation,
            executable_proof=proof,
        ).public_binding
        assert authority["process_image_content_digest"] == composition.interpreter_content_digest
        assert authority["dependency_runtime_inventory_digest"] == composition.dependency_runtime.inventory_digest
        assert authority["actual_process_image_verified"] is True
        assert authority["isolation_verified"] is True
        assert authority["native_loaded_image_closure_verified"] is False
    finally:
        temp.cleanup()


def test_missing_isolation_flag_is_rejected() -> None:
    temp, composition, repo, observation, proof = _fixture()
    try:
        with pytest.raises(QueryRuntimeBuilderProcessError, match="ISOLATION_INVALID"):
            _prove_builder_process_authority_for_test(
                composition=composition,
                repo_root=repo,
                observation=replace(observation, no_site=0),
                executable_proof=proof,
            )
    finally:
        temp.cleanup()


def test_ambient_sys_path_is_rejected() -> None:
    temp, composition, repo, observation, proof = _fixture()
    try:
        ambient = Path(temp.name) / "ambient"
        ambient.mkdir()
        with pytest.raises(QueryRuntimeBuilderProcessError, match="SYS_PATH_INVALID"):
            _prove_builder_process_authority_for_test(
                composition=composition,
                repo_root=repo,
                observation=replace(observation, sys_path=(*observation.sys_path, ambient)),
                executable_proof=proof,
            )
    finally:
        temp.cleanup()


def test_descendant_source_and_dependency_entries_are_rejected() -> None:
    temp, composition, repo, observation, proof = _fixture()
    try:
        nested_repo = repo / "nested"
        nested_dependency = composition.site_packages_root / "nested"
        nested_repo.mkdir()
        nested_dependency.mkdir()
        changed_paths = (
            *observation.sys_path[:4], nested_dependency, nested_repo,
        )
        with pytest.raises(QueryRuntimeBuilderProcessError, match="SYS_PATH_INVALID"):
            _prove_builder_process_authority_for_test(
                composition=composition,
                repo_root=repo,
                observation=replace(observation, sys_path=changed_paths),
                executable_proof=proof,
            )
    finally:
        temp.cleanup()


def test_image_content_mismatch_is_rejected() -> None:
    temp, composition, repo, observation, proof = _fixture()
    try:
        changed = replace(composition, interpreter_content_digest=_d("f"))
        with pytest.raises(QueryRuntimeBuilderProcessError, match="IMAGE_MISMATCH"):
            _prove_builder_process_authority_for_test(
                composition=changed,
                repo_root=repo,
                observation=observation,
                executable_proof=proof,
            )
    finally:
        temp.cleanup()


def test_builder_source_root_must_be_a_directory() -> None:
    temp, composition, repo, observation, proof = _fixture()
    try:
        source_file = repo.parent / "repo-file"
        source_file.write_bytes(b"not-a-directory")
        with pytest.raises(QueryRuntimeBuilderProcessError, match="VOLUME_INVALID"):
            _prove_builder_process_authority_for_test(
                composition=composition,
                repo_root=source_file,
                observation=replace(
                    observation,
                    sys_path=(*observation.sys_path[:-1], source_file),
                ),
                executable_proof=proof,
            )
    finally:
        temp.cleanup()


def test_builder_roots_must_be_disjoint() -> None:
    temp, composition, _repo, observation, proof = _fixture()
    try:
        nested = composition.site_packages_root / "builder"
        nested.mkdir()
        with pytest.raises(QueryRuntimeBuilderProcessError, match="TOPOLOGY_INVALID"):
            _prove_builder_process_authority_for_test(
                composition=composition,
                repo_root=nested,
                observation=replace(
                    observation,
                    sys_path=(*observation.sys_path[:-1], nested),
                ),
                executable_proof=proof,
            )
    finally:
        temp.cleanup()


def test_dependency_and_builder_path_order_is_exact() -> None:
    temp, composition, repo, observation, proof = _fixture()
    try:
        changed = (
            *observation.sys_path[:4], observation.sys_path[-1], observation.sys_path[-2],
        )
        with pytest.raises(QueryRuntimeBuilderProcessError, match="SYS_PATH_INVALID"):
            _prove_builder_process_authority_for_test(
                composition=composition,
                repo_root=repo,
                observation=replace(observation, sys_path=changed),
                executable_proof=proof,
            )
    finally:
        temp.cleanup()


def test_prefix_descendant_is_rejected() -> None:
    temp, composition, repo, observation, proof = _fixture()
    try:
        with pytest.raises(QueryRuntimeBuilderProcessError, match="PREFIX_INVALID"):
            _prove_builder_process_authority_for_test(
                composition=composition,
                repo_root=repo,
                observation=replace(observation, sys_prefix=observation.sys_prefix / "Lib"),
                executable_proof=proof,
            )
    finally:
        temp.cleanup()


def test_public_process_wrapper_uses_actual_observation_and_reproves(monkeypatch) -> None:
    temp, composition, repo, observation, proof = _fixture()
    try:
        calls = []

        def verify(**_kwargs):
            calls.append("verify")
            return composition

        monkeypatch.setattr(builder_process_module, "verify_runtime_composition_generation", verify)
        monkeypatch.setattr(builder_process_module, "current_process_image_path", lambda: observation.executable)
        monkeypatch.setattr(builder_process_module, "prove_process_executable_path", lambda _path: proof)
        monkeypatch.setattr(builder_process_module, "_actual_process_observation", lambda _path: observation)
        authority = prove_builder_process_authority(
            composition_verification_kwargs={}, repo_root=repo,
        )
        assert authority.public_binding["actual_process_image_verified"] is True
        assert calls == ["verify", "verify"]
    finally:
        temp.cleanup()


def test_public_process_wrapper_rejects_composition_mutation(monkeypatch) -> None:
    temp, composition, repo, observation, proof = _fixture()
    try:
        values = iter((composition, replace(composition, generation_id=_d("f"))))
        monkeypatch.setattr(
            builder_process_module, "verify_runtime_composition_generation",
            lambda **_kwargs: next(values),
        )
        monkeypatch.setattr(builder_process_module, "current_process_image_path", lambda: observation.executable)
        monkeypatch.setattr(builder_process_module, "prove_process_executable_path", lambda _path: proof)
        monkeypatch.setattr(builder_process_module, "_actual_process_observation", lambda _path: observation)
        with pytest.raises(QueryRuntimeBuilderProcessError, match="COMPOSITION_MUTATED"):
            prove_builder_process_authority(
                composition_verification_kwargs={}, repo_root=repo,
            )
    finally:
        temp.cleanup()
