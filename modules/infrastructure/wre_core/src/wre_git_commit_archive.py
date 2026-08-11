"""Safe materialization of one exact Git commit into an external directory."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile

MAX_ARCHIVE_ENTRIES = 100_000
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024
_SHA = re.compile(r"[0-9a-f]{40}")
_WINDOWS_DEVICES = {
    "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
    "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3",
    "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def materialize_git_commit(
    repo: Path, sha: str, destination: Path, runtime_root: Path
) -> None:
    """Extract one bounded, regular-file-only Git archive."""
    if _SHA.fullmatch(sha) is None:
        raise ValueError("git_commit_sha_invalid")
    root = runtime_root.resolve(strict=True)
    target = destination.resolve(strict=False)
    if target == root or root not in target.parents or target.exists():
        raise ValueError("git_archive_destination_invalid")
    archive = root / f"{destination.name}.tar"
    try:
        subprocess.run(
            ["git", "-C", str(repo), "archive", "--format=tar", f"--output={archive}", sha],
            capture_output=True, timeout=300, shell=False, check=True,
        )
        target.mkdir()
        try:
            with tarfile.open(archive, "r:") as handle:
                members = handle.getmembers()
                if (
                    len(members) > MAX_ARCHIVE_ENTRIES
                    or sum(item.size for item in members) > MAX_ARCHIVE_BYTES
                ):
                    raise ValueError("git_archive_bounds_exceeded")
                for member in members:
                    member_target = (target / PurePosixPath(member.name)).resolve()
                    if not _portable_member_name(member.name) or (
                        target not in member_target.parents
                    ) or not (
                        member.isfile() or member.isdir()
                    ):
                        raise ValueError("git_archive_member_invalid")
                handle.extractall(target, members=members, filter="data")
        except tarfile.TarError as exc:
            raise ValueError("git_archive_invalid") from exc
    except Exception:
        if target.exists():
            shutil.rmtree(target)
        raise
    finally:
        archive.unlink(missing_ok=True)


def _portable_member_name(value: str) -> bool:
    if not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return False
    for part in path.parts:
        stem = part.split(".", 1)[0].upper()
        if ":" in part or part.endswith((" ", ".")) or stem in _WINDOWS_DEVICES:
            return False
    return True


__all__ = ["materialize_git_commit"]
