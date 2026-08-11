from __future__ import annotations

from io import BytesIO
from pathlib import Path
import subprocess
import tarfile

import pytest

from modules.infrastructure.wre_core.src import wre_git_commit_archive as archive


def _run_with_members(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    members: list[tarfile.TarInfo],
) -> Path:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    runtime.mkdir()

    def fake_run(command, **kwargs):
        output = Path(next(value for value in command if value.startswith("--output="))[9:])
        with tarfile.open(output, "w") as handle:
            for member in members:
                data = BytesIO(b"x" * member.size) if member.isfile() else None
                handle.addfile(member, data)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(archive.subprocess, "run", fake_run)
    destination = runtime / "source"
    archive.materialize_git_commit(repo, "a" * 40, destination, runtime)
    return destination


def _file(name: str) -> tarfile.TarInfo:
    member = tarfile.TarInfo(name)
    member.size = 1
    return member


def test_regular_file_archive_materializes(tmp_path: Path, monkeypatch) -> None:
    destination = _run_with_members(tmp_path, monkeypatch, [_file("tests/test_ok.py")])
    assert (destination / "tests/test_ok.py").read_bytes() == b"x"


@pytest.mark.parametrize(
    "member",
    [
        _file("../escape.py"), _file("/absolute.py"), _file("CON.py"),
        _file("tests/data:stream.py"),
        tarfile.TarInfo("link.py"), tarfile.TarInfo("hardlink.py"),
        tarfile.TarInfo("device.py"),
    ],
)
def test_unsafe_archive_members_reject_and_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, member: tarfile.TarInfo,
) -> None:
    if member.name == "link.py":
        member.type = tarfile.SYMTYPE
    elif member.name == "hardlink.py":
        member.type = tarfile.LNKTYPE
    elif member.name == "device.py":
        member.type = tarfile.CHRTYPE
    with pytest.raises(ValueError, match="git_archive_member_invalid"):
        _run_with_members(tmp_path, monkeypatch, [member])
    assert not (tmp_path / "runtime/source").exists()
    assert not (tmp_path / "runtime/source.tar").exists()


def test_archive_entry_bound_rejects_and_cleans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(archive, "MAX_ARCHIVE_ENTRIES", 0)
    with pytest.raises(ValueError, match="git_archive_bounds_exceeded"):
        _run_with_members(tmp_path, monkeypatch, [_file("test_ok.py")])
    assert not (tmp_path / "runtime/source").exists()
