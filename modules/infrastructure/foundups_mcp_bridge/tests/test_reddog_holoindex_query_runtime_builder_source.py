from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
import tempfile
from types import ModuleType

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_query_runtime_builder_source as builder_source_module,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_git import (
    PinnedGitAuthority,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_source import (
    QueryRuntimeBuilderSourceError,
    _prove_builder_source_authority_for_test,
    prove_builder_source_authority,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fixture():
    Path("O:/tmp").mkdir(parents=True, exist_ok=True)
    temp = tempfile.TemporaryDirectory(prefix="reddog-builder-source-", dir="O:/tmp")
    root = Path(temp.name)
    source = root / "runtime.py"
    payload = b"VALUE = 1\n"
    source.write_bytes(payload)
    manifest = {
        "schema_version": "reddog_backend_manifest.v3",
        "product": "foundups-agent-reddog-backend",
        "backend_api_version": 2,
        "runtime_dependency_graph_version": 2,
        "required_runtime_files": ["runtime.py"],
        "required_runtime_sha256": {"runtime.py": _sha256(payload)},
    }
    target = root / "scripts" / "reddog_backend_manifest.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    module = ModuleType("runtime")
    module.__file__ = str(source)
    module.__cached__ = str(root / "__pycache__" / "runtime.pyc")
    git = PinnedGitAuthority(
        repo_root=root,
        repo_head_sha="a" * 40,
        git_executable_content_digest="sha256:" + "b" * 64,
        repository_state_digest="sha256:" + "c" * 64,
        tracked_files=frozenset({"runtime.py", "scripts/reddog_backend_manifest.json"}),
        committed_files=(
            ("runtime.py", len(payload), "sha256:" + _sha256(payload)),
            (
                "scripts/reddog_backend_manifest.json", target.stat().st_size,
                "sha256:" + _sha256(target.read_bytes()),
            ),
        ),
    )
    return temp, root, module, git


def test_manifest_bound_loaded_source_authority_is_path_free() -> None:
    temp, root, module, git = _fixture()
    try:
        authority = _prove_builder_source_authority_for_test(
            repo_root=root,
            git_authority=git,
            modules={"runtime": module},
            required_builder_files=("runtime.py",),
        ).public_binding
        assert authority["repo_head_sha"] == "a" * 40
        assert authority["loaded_source_count"] == 1
        assert authority["loaded_source_bytes"] == len(b"VALUE = 1\n")
        assert authority["pinned_git_executable_verified"] is True
        assert str(root) not in json.dumps(authority)
    finally:
        temp.cleanup()


def test_loaded_source_outside_manifest_is_rejected() -> None:
    temp, root, module, git = _fixture()
    try:
        extra = root / "extra.py"
        extra.write_bytes(b"EXTRA = 1\n")
        extra_module = ModuleType("extra")
        extra_module.__file__ = str(extra)
        extra_module.__cached__ = None
        with pytest.raises(QueryRuntimeBuilderSourceError, match="LOADED_ORIGIN_UNBOUND"):
            _prove_builder_source_authority_for_test(
                repo_root=root,
                git_authority=git,
                modules={"runtime": module, "extra": extra_module},
                required_builder_files=("runtime.py",),
            )
    finally:
        temp.cleanup()


def test_physical_source_bytecode_cache_is_rejected() -> None:
    temp, root, module, git = _fixture()
    try:
        cache = Path(str(module.__cached__))
        cache.parent.mkdir()
        cache.write_bytes(b"cache")
        with pytest.raises(QueryRuntimeBuilderSourceError, match="BYTECODE_CACHE_PRESENT"):
            _prove_builder_source_authority_for_test(
                repo_root=root,
                git_authority=git,
                modules={"runtime": module},
                required_builder_files=("runtime.py",),
            )
    finally:
        temp.cleanup()


def test_manifest_digest_mismatch_is_rejected() -> None:
    temp, root, module, git = _fixture()
    try:
        (root / "runtime.py").write_bytes(b"VALUE = 2\n")
        with pytest.raises(QueryRuntimeBuilderSourceError, match="MANIFEST_DIGEST_MISMATCH"):
            _prove_builder_source_authority_for_test(
                repo_root=root,
                git_authority=git,
                modules={"runtime": module},
                required_builder_files=("runtime.py",),
            )
    finally:
        temp.cleanup()


def test_committed_head_blob_mismatch_is_rejected() -> None:
    temp, root, module, git = _fixture()
    try:
        changed_rows = tuple(
            (path, size, "sha256:" + "f" * 64) if path == "runtime.py" else row
            for row in git.committed_files
            for path, size, _digest in (row,)
        )
        changed = replace(git, committed_files=changed_rows)
        with pytest.raises(QueryRuntimeBuilderSourceError, match="HEAD_BLOB_MISMATCH"):
            _prove_builder_source_authority_for_test(
                repo_root=root,
                git_authority=changed,
                modules={"runtime": module},
                required_builder_files=("runtime.py",),
            )
    finally:
        temp.cleanup()


def test_two_module_names_cannot_alias_one_source_file() -> None:
    temp, root, module, git = _fixture()
    try:
        alias = ModuleType("runtime_alias")
        alias.__file__ = module.__file__
        alias.__cached__ = None
        with pytest.raises(QueryRuntimeBuilderSourceError, match="LOADED_ORIGIN_INVALID"):
            _prove_builder_source_authority_for_test(
                repo_root=root,
                git_authority=git,
                modules={"runtime": module, "runtime_alias": alias},
                required_builder_files=("runtime.py",),
            )
    finally:
        temp.cleanup()


def test_public_source_wrapper_reproves_origins_and_git(monkeypatch) -> None:
    temp, root, module, git = _fixture()
    try:
        expected = _prove_builder_source_authority_for_test(
            repo_root=root, git_authority=git, modules={"runtime": module},
            required_builder_files=("runtime.py",),
        ).public_binding
        origin_calls, git_calls = [], []

        def origins(_root, _modules):
            origin_calls.append("origins")
            return {"runtime.py": "runtime"}

        def pinned(**_kwargs):
            git_calls.append("git")
            return git

        monkeypatch.setattr(builder_source_module, "_module_origins", origins)
        monkeypatch.setattr(builder_source_module, "prove_pinned_git_authority", pinned)
        source_calls = []

        def source_binding(**_kwargs):
            source_calls.append("source")
            return expected

        monkeypatch.setattr(builder_source_module, "_source_binding", source_binding)
        observed = prove_builder_source_authority(
            repo_root=root, expected_repo_head_sha="a" * 40,
            git_executable=Path("O:/tools/git.exe"),
            expected_git_executable_digest="sha256:" + "b" * 64,
        )
        assert observed.public_binding == expected
        assert origin_calls == ["origins", "origins"]
        assert git_calls == ["git", "git"]
        assert source_calls == ["source", "source"]
    finally:
        temp.cleanup()


def test_public_source_wrapper_rejects_git_reproof_mutation(monkeypatch) -> None:
    temp, root, module, git = _fixture()
    try:
        expected = _prove_builder_source_authority_for_test(
            repo_root=root, git_authority=git, modules={"runtime": module},
            required_builder_files=("runtime.py",),
        ).public_binding
        values = iter((git, replace(git, repository_state_digest="sha256:" + "f" * 64)))
        monkeypatch.setattr(
            builder_source_module, "_module_origins",
            lambda _root, _modules: {"runtime.py": "runtime"},
        )
        monkeypatch.setattr(
            builder_source_module, "prove_pinned_git_authority",
            lambda **_kwargs: next(values),
        )
        monkeypatch.setattr(builder_source_module, "_source_binding", lambda **_kwargs: expected)
        with pytest.raises(QueryRuntimeBuilderSourceError, match="MUTATED_DURING_PROOF"):
            prove_builder_source_authority(
                repo_root=root, expected_repo_head_sha="a" * 40,
                git_executable=Path("O:/tools/git.exe"),
                expected_git_executable_digest="sha256:" + "b" * 64,
            )
    finally:
        temp.cleanup()


def test_public_source_wrapper_rejects_second_pass_source_mutation(monkeypatch) -> None:
    temp, root, module, git = _fixture()
    try:
        origin_calls = []

        def origins(_root, _modules):
            origin_calls.append("origins")
            if len(origin_calls) == 2:
                (root / "runtime.py").write_bytes(b"VALUE = 2\n")
            return {"runtime.py": "runtime"}

        monkeypatch.setattr(builder_source_module, "_module_origins", origins)
        monkeypatch.setattr(
            builder_source_module, "prove_pinned_git_authority",
            lambda **_kwargs: git,
        )
        monkeypatch.setattr(builder_source_module, "_REQUIRED_BUILDER_FILES", ("runtime.py",))
        with pytest.raises(QueryRuntimeBuilderSourceError, match="MANIFEST_DIGEST_MISMATCH"):
            prove_builder_source_authority(
                repo_root=root, expected_repo_head_sha="a" * 40,
                git_executable=Path("O:/tools/git.exe"),
                expected_git_executable_digest="sha256:" + "b" * 64,
            )
        assert origin_calls == ["origins", "origins"]
    finally:
        temp.cleanup()
