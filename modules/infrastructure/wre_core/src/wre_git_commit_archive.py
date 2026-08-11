"""Safe materialization of exact Git blobs into an external directory."""

from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import threading

from .wre_git_tree_manifest import ExactGitTreeManifest, exact_git_tree_manifest

MAX_ARCHIVE_ENTRIES = 100_000
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024
_CHUNK_BYTES = 64 * 1024


def materialize_git_commit(
    repo: Path, sha: str, destination: Path, runtime_root: Path,
) -> None:
    """Materialize bounded regular blobs without checkout or archive filters."""
    root = runtime_root.resolve(strict=True)
    target = destination.resolve(strict=False)
    if target == root or root not in target.parents or target.exists():
        raise ValueError("git_archive_destination_invalid")
    manifest = exact_git_tree_manifest(repo, sha)
    if len(manifest.blobs) > MAX_ARCHIVE_ENTRIES:
        raise ValueError("git_archive_bounds_exceeded")
    target.mkdir()
    try:
        _materialize_manifest(repo, target, manifest)
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise


def _materialize_manifest(
    repo: Path, target: Path, manifest: ExactGitTreeManifest,
) -> None:
    process = subprocess.Popen(
        ["git", "-C", str(repo), "cat-file", "--batch"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, shell=False,
    )
    state: dict[str, BaseException] = {}
    worker = threading.Thread(
        target=_copy_manifest, args=(process, target, manifest, state), daemon=True,
    )
    worker.start()
    worker.join(timeout=300)
    if worker.is_alive():
        _kill_and_reap(process, worker)
        raise subprocess.TimeoutExpired(process.args, 300)
    if process.stdin is not None:
        try:
            process.stdin.close()
        except BrokenPipeError:
            pass
    try:
        returncode = process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise
    if "error" in state:
        raise state["error"]
    if returncode != 0:
        raise subprocess.CalledProcessError(returncode, process.args)


def _kill_and_reap(
    process: subprocess.Popen[bytes], worker: threading.Thread,
) -> None:
    if process.poll() is None:
        process.kill()
    process.wait(timeout=30)
    for stream in (process.stdin, process.stdout):
        if stream is not None:
            try:
                stream.close()
            except (BrokenPipeError, OSError):
                pass
    worker.join(timeout=5)
    if worker.is_alive():
        raise RuntimeError("git_blob_reader_stalled")


def _copy_manifest(
    process: subprocess.Popen[bytes], target: Path,
    manifest: ExactGitTreeManifest, state: dict[str, BaseException],
) -> None:
    total = 0
    try:
        assert process.stdin is not None and process.stdout is not None
        for path, object_id in manifest.blobs.items():
            process.stdin.write(object_id.encode("ascii") + b"\n")
            process.stdin.flush()
            size = _batch_header(process.stdout, object_id)
            total += size
            if total > MAX_ARCHIVE_BYTES:
                raise ValueError("git_archive_bounds_exceeded")
            _copy_blob(process.stdout, target / path, object_id, size,
                       manifest.object_format)
            if process.stdout.read(1) != b"\n":
                raise ValueError("git_blob_protocol_invalid")
    except BaseException as exc:
        state["error"] = exc
        process.kill()


def _batch_header(stream, expected_id: str) -> int:
    header = stream.readline(256)
    if not header.endswith(b"\n") or len(header) >= 256:
        raise ValueError("git_blob_header_invalid")
    try:
        object_id, kind, raw_size = header[:-1].decode("ascii").split(" ")
        size = int(raw_size)
    except (UnicodeError, ValueError) as exc:
        raise ValueError("git_blob_header_invalid") from exc
    if object_id != expected_id or kind != "blob" or size < 0:
        raise ValueError("git_blob_header_invalid")
    return size


def _copy_blob(
    stream, target: Path, object_id: str, size: int, object_format: str,
) -> None:
    digest = hashlib.new(object_format)
    digest.update(f"blob {size}\0".encode("ascii"))
    remaining = size
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as output:
        while remaining:
            chunk = stream.read(min(_CHUNK_BYTES, remaining))
            if not chunk:
                raise ValueError("git_blob_truncated")
            digest.update(chunk)
            output.write(chunk)
            remaining -= len(chunk)
    if digest.hexdigest() != object_id:
        raise ValueError("git_blob_digest_mismatch")


__all__ = ["materialize_git_commit"]
