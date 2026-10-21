from __future__ import annotations

import ast
from pathlib import Path
import subprocess

import pytest

from modules.infrastructure.wre_core.src import wre_git_commit_archive as archive
from modules.infrastructure.wre_core.src import wre_git_bounded_io as bounded
from modules.infrastructure.wre_core.src import wre_git_blob_batch_reader as batch
from modules.infrastructure.wre_core.src import wre_git_process_io as process_io
from modules.infrastructure.wre_core.src import wre_git_tree_manifest as tree


def _git(repo: Path, *args: str, text: bool = True):
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, check=True,
        text=text, timeout=30,
    ).stdout


def _repository(tmp_path: Path, files: dict[str, bytes]) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "WRE Tests")
    for relative, payload in files.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "fixture")
    return repo, _git(repo, "rev-parse", "HEAD").strip()


def _materialize(repo: Path, sha: str, root: Path) -> Path:
    runtime = root / "runtime"
    runtime.mkdir()
    destination = runtime / "source"
    archive.materialize_git_commit(repo, sha, destination, runtime)
    return destination


def test_regular_files_materialize_as_exact_blob_bytes(tmp_path: Path) -> None:
    repo, sha = _repository(tmp_path, {"tests/test_ok.py": b"assert True\n"})
    destination = _materialize(repo, sha, tmp_path)
    expected = _git(repo, "show", f"{sha}:tests/test_ok.py", text=False)
    assert (destination / "tests/test_ok.py").read_bytes() == expected


def test_selected_blobs_read_in_one_bounded_batch(tmp_path: Path) -> None:
    repo, sha = _repository(tmp_path, {"a.py": b"a = 1\n", "b.py": b"b = 2\n"})
    manifest = tree.exact_git_tree_manifest(repo, sha)
    values = batch.read_exact_git_blobs(
        repo, manifest.blobs, object_format=manifest.object_format,
        max_blob_bytes=64, max_total_bytes=128,
    )

    assert dict(values) == {"a.py": b"a = 1\n", "b.py": b"b = 2\n"}


def test_batch_aggregate_bound_fails_before_return(tmp_path: Path) -> None:
    repo, sha = _repository(tmp_path, {"a.py": b"a" * 32, "b.py": b"b" * 32})
    manifest = tree.exact_git_tree_manifest(repo, sha)

    with pytest.raises(ValueError, match="bounds_exceeded"):
        batch.read_exact_git_blobs(
            repo, manifest.blobs, object_format=manifest.object_format,
            max_blob_bytes=32, max_total_bytes=40,
        )


def test_git_read_environment_removes_authority_overrides() -> None:
    result = bounded.git_read_environment({
        "PATH": "safe", "GIT_DIR": "attacker", "git_work_tree": "attacker",
    })

    assert result["PATH"] == "safe"
    assert "GIT_DIR" not in result
    assert "git_work_tree" not in result
    assert result["GIT_CONFIG_NOSYSTEM"] == "1"


def test_git_provenance_io_modules_remain_bounded() -> None:
    root = Path(__file__).parents[1] / "src"
    for name in ("wre_git_bounded_io.py", "wre_git_blob_batch_reader.py"):
        source = (root / name).read_text(encoding="ascii")
        assert len(source.splitlines()) <= 200
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno is not None
                assert node.end_lineno - node.lineno + 1 <= 50


def test_materialization_ignores_export_attributes(tmp_path: Path) -> None:
    files = {
        ".gitattributes": b"hidden.py export-ignore\nsubst.py export-subst\n",
        "hidden.py": b"HIDDEN\n",
        "subst.py": b"$Format:%H$\n",
    }
    repo, sha = _repository(tmp_path, files)
    destination = _materialize(repo, sha, tmp_path)
    assert (destination / "hidden.py").read_bytes() == b"HIDDEN\n"
    assert (destination / "subst.py").read_bytes() == b"$Format:%H$\n"


def test_entry_and_expanded_byte_bounds_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, sha = _repository(tmp_path, {"test_ok.py": b"x"})
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    monkeypatch.setattr(archive, "MAX_ARCHIVE_ENTRIES", 0)
    with pytest.raises(ValueError, match="git_archive_bounds_exceeded"):
        archive.materialize_git_commit(repo, sha, runtime / "entries", runtime)
    monkeypatch.setattr(archive, "MAX_ARCHIVE_ENTRIES", 10)
    monkeypatch.setattr(archive, "MAX_ARCHIVE_BYTES", 0)
    with pytest.raises(ValueError, match="git_archive_bounds_exceeded"):
        archive.materialize_git_commit(repo, sha, runtime / "bytes", runtime)
    assert not (runtime / "entries").exists()
    assert not (runtime / "bytes").exists()


@pytest.mark.parametrize(
    "path", [
        "../escape.py", "/absolute.py", "CON.py", "data:stream.py",
        'bad*name.py', 'bad?name.py', 'bad\"name.py', "bad<name.py",
        "bad>name.py", "bad|name.py", "decomposed/e\u0301.py",
        "COM\u00b9.py", "COM\u00b2", "COM\u00b3.log",
        "LPT\u00b9.py", "LPT\u00b2", "LPT\u00b3.log",
    ],
)
def test_portable_tree_path_rejects_unsafe_names(path: str) -> None:
    assert tree.portable_git_path(path) is False


@pytest.mark.parametrize(
    "paths", [
        ("Dir/a.py", "dir/b.py"),
        ("Foo", "foo/bar.py"),
    ],
)
def test_tree_path_claim_rejects_component_collisions(
    paths: tuple[str, str],
) -> None:
    spellings: dict[tuple[str, ...], dict[str, str]] = {}
    leaves: set[tuple[str, ...]] = set()
    branches: set[tuple[str, ...]] = set()
    tree._claim_portable_path(paths[0], spellings, leaves, branches)
    with pytest.raises(ValueError, match="git_tree_path_collision"):
        tree._claim_portable_path(paths[1], spellings, leaves, branches)


def test_tree_manifest_rejects_casefold_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    object_id = b"a" * 40
    records = (
        b"100644 blob " + object_id + b"\tDemo/test.py\0"
        b"100644 blob " + object_id + b"\tdemo/test.py\0"
    )
    monkeypatch.setattr(tree, "resolve_exact_commit", lambda repo, sha: sha)
    monkeypatch.setattr(
        tree, "run_bounded_stdout",
        lambda argv, **kwargs: b"sha1\n" if "--show-object-format" in argv else records,
    )
    with pytest.raises(ValueError, match="git_tree_path_collision"):
        tree.exact_git_tree_manifest(repo, "a" * 40)


def test_tree_manifest_rejects_symlink() -> None:
    mode, kind = b"120000", b"blob"
    record = mode + b" " + kind + b" " + b"a" * 40 + b"\tunsafe"
    with pytest.raises(ValueError, match="git_tree_record_invalid"):
        tree._tree_record(record, "sha1")


def test_tree_manifest_validates_but_does_not_materialize_gitlink() -> None:
    record = b"160000 commit " + b"a" * 40 + b"\tvendor/dependency"
    assert tree._tree_record(record, "sha1") == (
        "vendor/dependency", "a" * 40, False,
    )


def test_tree_manifest_normalizes_non_ascii_mode_failure() -> None:
    record = b"\xff blob " + b"a" * 40 + b"\tunsafe"
    with pytest.raises(ValueError, match="git_tree_record_invalid"):
        tree._tree_record(record, "sha1")


def test_kill_and_reap_closes_process_and_worker() -> None:
    events: list[str] = []

    class Stream:
        def close(self) -> None:
            events.append("close")

    class Process:
        stdin = Stream()
        stdout = Stream()

        def poll(self):
            return None

        def kill(self) -> None:
            events.append("kill")

        def wait(self, timeout: int) -> int:
            events.append(f"wait:{timeout}")
            return 0

    class Worker:
        def join(self, timeout: int) -> None:
            events.append(f"join:{timeout}")

        def is_alive(self) -> bool:
            return False

    archive._kill_and_reap(Process(), Worker())  # type: ignore[arg-type]
    assert events == ["kill", "wait:30", "close", "close", "join:5"]


def test_bounded_process_timeout_reaps_closes_and_joins(monkeypatch, tmp_path: Path) -> None:
    events: list[str] = []

    class Stream:
        def __init__(self, label: str) -> None:
            self.closed = False
            self.label = label

        def close(self) -> None:
            self.closed = True
            events.append(f"close:{self.label}")

    class Process:
        stdin = Stream("stdin")
        stdout = Stream("stdout")

        def poll(self):
            return None

        def kill(self) -> None:
            events.append("kill")

        def wait(self, timeout: int) -> int:
            events.append(f"wait:{timeout}")
            if timeout == 1:
                raise subprocess.TimeoutExpired("git", timeout)
            return 0

    class Worker:
        def start(self) -> None:
            events.append("start")

        def join(self, timeout: int) -> None:
            events.append(f"join:{timeout}")

        def is_alive(self) -> bool:
            return False

    monkeypatch.setattr(process_io.subprocess, "Popen", lambda *_a, **_k: Process())
    monkeypatch.setattr(process_io.threading, "Thread", lambda **_k: Worker())
    with pytest.raises(subprocess.TimeoutExpired):
        process_io.run_bounded_process(
            ["git"], cwd=tmp_path, max_bytes=1, timeout_s=1,
            chunks=[], output_path=None, environment=None, stdin_bytes=None,
        )
    assert events == [
        "start", "wait:1", "kill", "wait:30",
        "close:stdin", "close:stdout", "join:5",
    ]
