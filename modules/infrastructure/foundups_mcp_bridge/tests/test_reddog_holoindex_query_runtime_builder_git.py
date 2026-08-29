from __future__ import annotations

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_query_runtime_builder_git as builder_git_module,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_process_image import (
    ProcessExecutableCapability,
    ProcessExecutableProof,
    hold_process_executable_for_launch,
    prove_process_executable_path,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_git import (
    QueryRuntimeBuilderGitError,
    _batch_blob_rows,
    _batch_header,
    _git_environment,
    _git_topology_snapshot,
    _tree_blob_ids,
    _validated_inputs,
    _validate_index_flags,
    prove_pinned_git_authority,
)


def _blob_id(payload: bytes) -> str:
    framed = f"blob {len(payload)}\0".encode("ascii") + payload
    return hashlib.sha1(framed).hexdigest()


def _batch(paths: tuple[str, ...], payloads: dict[str, bytes]) -> tuple[bytes, dict[str, str]]:
    object_ids = {path: _blob_id(payloads[path]) for path in paths}
    raw = b"".join(
        object_ids[path].encode("ascii") + f" blob {len(payloads[path])}\n".encode("ascii")
        + payloads[path] + b"\n"
        for path in paths
    )
    return raw, object_ids


def _repo_fixture() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    Path("O:/tmp").mkdir(parents=True, exist_ok=True)
    temp = tempfile.TemporaryDirectory(prefix="reddog-builder-git-", dir="O:/tmp")
    root = Path(temp.name)
    (root / ".git" / "objects").mkdir(parents=True)
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
    return temp, root


def test_tree_and_batch_bind_every_requested_blob() -> None:
    paths = ("a.py", "nested/b.py")
    payloads = {"a.py": b"A = 1\n", "nested/b.py": b"B = 2\n"}
    raw_batch, expected = _batch(paths, payloads)
    raw_tree = b"".join(
        f"100644 blob {expected[path]}\t{path}".encode("utf-8") + b"\0"
        for path in paths
    )
    observed = _tree_blob_ids(raw_tree, paths)
    rows = _batch_blob_rows(raw_batch, paths, observed)
    assert observed == expected
    assert [row[:2] for row in rows] == [(path, len(payloads[path])) for path in paths]


def test_tree_requires_complete_unique_regular_blob_set() -> None:
    object_id = _blob_id(b"A")
    duplicate = (
        f"100644 blob {object_id}\ta.py\0"
        f"100644 blob {object_id}\ta.py\0"
    ).encode("ascii")
    with pytest.raises(QueryRuntimeBuilderGitError, match="TREE_INVALID"):
        _tree_blob_ids(duplicate, ("a.py",))
    with pytest.raises(QueryRuntimeBuilderGitError, match="HEAD_BLOB_MISSING"):
        _tree_blob_ids(b"", ("a.py",))


def test_batch_rejects_payload_or_trailing_byte_substitution() -> None:
    paths, payloads = ("a.py",), {"a.py": b"A = 1\n"}
    raw, object_ids = _batch(paths, payloads)
    changed = raw.replace(b"A = 1", b"A = 2")
    with pytest.raises(QueryRuntimeBuilderGitError, match="BLOB_ID_MISMATCH"):
        _batch_blob_rows(changed, paths, object_ids)
    with pytest.raises(QueryRuntimeBuilderGitError, match="BATCH_INVALID"):
        _batch_blob_rows(raw + b"x", paths, object_ids)


def test_batch_header_enforces_per_file_ceiling() -> None:
    object_id = "a" * 40
    with pytest.raises(QueryRuntimeBuilderGitError, match="SOURCE_LIMIT_EXCEEDED"):
        _batch_header(f"{object_id} blob {64 * 1024 * 1024 + 1}".encode("ascii"), object_id)


def test_inputs_reject_aliases_noncanonical_unicode_and_uppercase_head() -> None:
    temp, root = _repo_fixture()
    try:
        digest = "sha256:" + "a" * 64
        with pytest.raises(QueryRuntimeBuilderGitError, match="EXPECTATION_INVALID"):
            _validated_inputs(root, "a" * 40, digest, ("A.py", "a.py"))
        with pytest.raises(QueryRuntimeBuilderGitError, match="PATH_INVALID"):
            _validated_inputs(root, "a" * 40, digest, ("bad\u200d.py",))
        with pytest.raises(QueryRuntimeBuilderGitError, match="EXPECTATION_INVALID"):
            _validated_inputs(root, "A" * 40, digest, ("a.py",))
    finally:
        temp.cleanup()


def test_git_topology_snapshot_binds_root_and_is_stable() -> None:
    temp, root = _repo_fixture()
    try:
        first = _git_topology_snapshot(root)
        second = _git_topology_snapshot(root)
        assert first == second
        assert first[0][0:2] == ("", "d")
        assert {row[0] for row in first} >= {"", "HEAD", "objects"}
    finally:
        temp.cleanup()


def test_git_topology_rejects_hardlinks() -> None:
    temp, root = _repo_fixture()
    try:
        first, second = root / ".git" / "one", root / ".git" / "two"
        first.write_bytes(b"x")
        try:
            os.link(first, second)
        except OSError as exc:
            pytest.skip(f"hardlinks unavailable on O: test volume: {exc}")
        with pytest.raises(QueryRuntimeBuilderGitError, match="TOPOLOGY_INVALID"):
            _git_topology_snapshot(root)
    finally:
        temp.cleanup()


def test_git_topology_rejects_repository_indirection_markers() -> None:
    temp, root = _repo_fixture()
    try:
        (root / ".git" / "commondir").write_text("..\n", encoding="ascii")
        with pytest.raises(QueryRuntimeBuilderGitError, match="TOPOLOGY_INVALID"):
            _git_topology_snapshot(root)
    finally:
        temp.cleanup()


def test_git_environment_drops_caller_git_authority(monkeypatch) -> None:
    temp, root = _repo_fixture()
    try:
        Path("O:/tmp").mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("GIT_OBJECT_DIRECTORY", "O:/hostile-objects")
        monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
        environment = _git_environment(Path("O:/tools/git/bin/git.exe"), root)
        assert "GIT_OBJECT_DIRECTORY" not in environment
        assert "GIT_CONFIG_COUNT" not in environment
        assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
        assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
        assert environment["GIT_NO_LAZY_FETCH"] == "1"
        assert environment["PATH"] == "O:\\tools\\git\\bin"
    finally:
        temp.cleanup()


@pytest.mark.parametrize("tag", ["h", "S", "s", "M"])
def test_index_flags_reject_hidden_or_nonordinary_tracked_state(tag: str) -> None:
    with pytest.raises(QueryRuntimeBuilderGitError, match="INDEX_FLAGS_INVALID"):
        _validate_index_flags(f"{tag} a.py\0".encode("ascii"), frozenset({"a.py"}))


def test_index_flags_require_exact_tracked_set() -> None:
    _validate_index_flags(b"H a.py\0H b.py\0", frozenset({"a.py", "b.py"}))
    with pytest.raises(QueryRuntimeBuilderGitError, match="INDEX_FLAGS_INVALID"):
        _validate_index_flags(b"H a.py\0", frozenset({"a.py", "b.py"}))


def test_git_image_is_held_and_hashed_around_all_observations(monkeypatch) -> None:
    events = []
    proof = ProcessExecutableProof(Path("O:/tools/git.exe"), (1, 2, 3, 4, 5, 1))
    capability = ProcessExecutableCapability(7, proof.path, ())
    expected = "sha256:" + "a" * 64
    observations = (b"top", b"head", b"tracked", b"flags", ())

    @contextmanager
    def held(value):
        assert value is proof
        events.append("hold-enter")
        yield capability
        events.append("hold-exit")

    def hashed(value, expected_proof):
        assert value is capability and expected_proof is proof
        events.append("hash")
        return expected

    def observed(*args):
        assert args[1:3] == (proof, capability)
        events.append("observe")
        return observations

    monkeypatch.setattr(builder_git_module, "hold_process_executable_for_launch", held)
    monkeypatch.setattr(builder_git_module, "_hash_held_executable", hashed)
    monkeypatch.setattr(builder_git_module, "_run_git_observations", observed)
    result = builder_git_module._held_git_observations(
        Path("O:/repo"), proof, "a" * 40, ("a.py",), expected,
    )
    assert result == (expected, observations)
    assert events == ["hold-enter", "hash", "observe", "hash", "hold-exit"]


def test_git_image_change_during_held_observations_is_rejected(monkeypatch) -> None:
    proof = ProcessExecutableProof(Path("O:/tools/git.exe"), (1, 2, 3, 4, 5, 1))
    capability = ProcessExecutableCapability(7, proof.path, ())
    digests = iter(("sha256:" + "a" * 64, "sha256:" + "b" * 64))

    @contextmanager
    def held(_value):
        yield capability

    monkeypatch.setattr(builder_git_module, "hold_process_executable_for_launch", held)
    monkeypatch.setattr(builder_git_module, "_hash_held_executable", lambda *_args: next(digests))
    monkeypatch.setattr(
        builder_git_module, "_run_git_observations",
        lambda *_args: (b"top", b"head", b"tracked", b"flags", ()),
    )
    with pytest.raises(QueryRuntimeBuilderGitError, match="IMAGE_MUTATED"):
        builder_git_module._held_git_observations(
            Path("O:/repo"), proof, "a" * 40, ("a.py",), "sha256:" + "a" * 64,
        )


def test_held_git_image_can_be_hashed_twice_from_offset_zero() -> None:
    temp, root = _repo_fixture()
    try:
        executable = root / "git.exe"
        payload = b"pinned-git-image"
        executable.write_bytes(payload)
        proof = prove_process_executable_path(executable)
        with hold_process_executable_for_launch(proof) as capability:
            first = builder_git_module._hash_held_executable(capability, proof)
            second = builder_git_module._hash_held_executable(capability, proof)
        assert first == second == "sha256:" + hashlib.sha256(payload).hexdigest()
    finally:
        temp.cleanup()


def test_held_git_image_rejects_non_oe_volume() -> None:
    proof = ProcessExecutableProof(Path("F:/tools/git.exe"), (1, 2, 3, 4, 5, 1))
    capability = ProcessExecutableCapability(7, proof.path, ())
    with pytest.raises(QueryRuntimeBuilderGitError, match="VOLUME_INVALID"):
        builder_git_module._hash_held_executable(capability, proof)


def _run_live_git(executable: Path, root: Path, *arguments: str) -> bytes:
    environment = builder_git_module._git_environment(executable, root)
    environment.update({
        "GIT_AUTHOR_NAME": "RedDog Test", "GIT_AUTHOR_EMAIL": "reddog@example.invalid",
        "GIT_COMMITTER_NAME": "RedDog Test", "GIT_COMMITTER_EMAIL": "reddog@example.invalid",
        "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
        "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
    })
    result = subprocess.run(
        [str(executable), "-C", str(root), *arguments],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=True, timeout=30, env=environment,
    )
    return result.stdout


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(64 * 1024):
            hasher.update(chunk)
    return "sha256:" + hasher.hexdigest()


def test_live_oe_pinned_git_authority_when_provisioned() -> None:
    raw = os.environ.get("REDDOG_PINNED_GIT_EXE", "")
    executable = Path(raw) if raw else Path()
    if (
        not raw or not executable.is_absolute()
        or executable.drive.rstrip(":").upper() not in {"O", "E"}
        or not executable.is_file()
    ):
        pytest.skip("no provisioned O:/E: pinned Git image")
    Path("O:/tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reddog-builder-live-git-", dir="O:/tmp") as name:
        root = Path(name)
        _run_live_git(executable, root, "init")
        (root / "bound.py").write_bytes(b"BOUND = True\n")
        _run_live_git(executable, root, "add", "--", "bound.py")
        _run_live_git(executable, root, "commit", "-m", "fixture")
        head = _run_live_git(executable, root, "rev-parse", "HEAD").decode("ascii").strip()
        authority = prove_pinned_git_authority(
            root=root, expected_head=head, executable=executable,
            expected_digest=_sha256_file(executable), bound_paths=("bound.py",),
        )
        assert authority.repo_head_sha == head
        assert authority.committed_files[0][0:2] == ("bound.py", len(b"BOUND = True\n"))
        (root / "bound.py").write_bytes(b"BOUND = False\n")
        with pytest.raises(QueryRuntimeBuilderGitError, match="REPOSITORY_STATE_INVALID"):
            prove_pinned_git_authority(
                root=root, expected_head=head, executable=executable,
                expected_digest=_sha256_file(executable), bound_paths=("bound.py",),
            )


def test_stream_validation_errors_map_to_stable_git_errors(monkeypatch) -> None:
    temp, root = _repo_fixture()
    try:
        monkeypatch.setattr(
            builder_git_module, "require_unnamed_data_stream_only",
            lambda _path: (_ for _ in ()).throw(ValueError("host path")),
        )
        with pytest.raises(QueryRuntimeBuilderGitError, match="EXPECTATION_INVALID"):
            _validated_inputs(
                root, "a" * 40, "sha256:" + "b" * 64, ("bound.py",),
            )
        with pytest.raises(QueryRuntimeBuilderGitError, match="TOPOLOGY_INVALID"):
            _git_topology_snapshot(root)
    finally:
        temp.cleanup()


def test_git_observations_never_enter_worktree_filter_surface(monkeypatch) -> None:
    Path("O:/tmp").mkdir(parents=True, exist_ok=True)
    payload = b"BOUND = True\n"
    object_id = _blob_id(payload)
    calls: list[tuple[str, ...]] = []

    def observed_git(
        _prefix, _root, _environment, *arguments,
        limit, stdin_bytes=None,
    ):
        del limit, stdin_bytes
        calls.append(tuple(arguments))
        command = arguments[0]
        if command == "status":
            raise AssertionError("worktree status may launch repository-configured filters")
        if arguments == ("rev-parse", "--show-toplevel"):
            return b"O:/repo\n"
        if command == "rev-parse":
            return ("a" * 40 + "\n").encode("ascii")
        if arguments[:2] == ("ls-files", "-z"):
            return b"bound.py\0"
        if arguments[:2] == ("ls-files", "-v"):
            return b"H bound.py\0"
        if command == "ls-tree":
            return f"100644 blob {object_id}\tbound.py\0".encode("ascii")
        if command == "cat-file":
            return (
                f"{object_id} blob {len(payload)}\n".encode("ascii")
                + payload + b"\n"
            )
        raise AssertionError(arguments)

    monkeypatch.setattr(builder_git_module, "_git", observed_git)
    proof = ProcessExecutableProof(Path("O:/tools/git.exe"), (1, 2, 3, 4, 5, 1))
    capability = ProcessExecutableCapability(7, proof.path, ())
    result = builder_git_module._run_git_observations(
        Path("O:/repo"), proof, capability, "a" * 40, ("bound.py",),
    )
    assert result[-1][0][0:2] == ("bound.py", len(payload))
    assert all(call[0] != "status" for call in calls)
