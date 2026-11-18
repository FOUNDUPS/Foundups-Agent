"""Bounded exact-object Git blob batch reader."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import threading
from types import MappingProxyType
from typing import Mapping

from .wre_git_bounded_io import git_read_environment

_CHUNK_BYTES = 64 * 1024


def read_exact_git_blobs(
    repo: Path, objects: Mapping[str, str], *, object_format: str,
    max_blob_bytes: int, max_total_bytes: int,
) -> Mapping[str, bytes]:
    """Read selected objects in one bounded, replacement-disabled Git process."""
    requested = dict(objects) if isinstance(objects, Mapping) else {}
    _validate_request(requested, object_format, max_blob_bytes, max_total_bytes)
    process = subprocess.Popen(
        ["git", "--no-replace-objects", "-C", str(repo), "cat-file", "--batch"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        shell=False, env=git_read_environment(),
    )
    state: dict[str, object] = {"values": {}}
    worker = threading.Thread(
        target=_read_objects,
        args=(process, requested, object_format, max_blob_bytes,
              max_total_bytes, state), daemon=True,
    )
    worker.start()
    worker.join(timeout=120)
    _finish_process(process, worker, state)
    values = state["values"]
    assert isinstance(values, dict)
    return MappingProxyType(dict(values))


def _read_objects(
    process: subprocess.Popen[bytes], objects: Mapping[str, str],
    object_format: str, max_blob: int, max_total: int,
    state: dict[str, object],
) -> None:
    total = 0
    try:
        assert process.stdin is not None and process.stdout is not None
        values = state["values"]
        assert isinstance(values, dict)
        for name, object_id in objects.items():
            process.stdin.write(object_id.encode("ascii") + b"\n")
            process.stdin.flush()
            size = _header(process.stdout, object_id)
            total += size
            if size > max_blob or total > max_total:
                raise ValueError("git_blob_batch_bounds_exceeded")
            values[name] = _body(
                process.stdout, object_id, object_format, size
            )
            if process.stdout.read(1) != b"\n":
                raise ValueError("git_blob_batch_protocol_invalid")
    except BaseException as exc:
        state["error"] = exc
        process.kill()


def _header(stream: object, expected_id: str) -> int:
    raw = stream.readline(256)  # type: ignore[attr-defined]
    if not raw.endswith(b"\n") or len(raw) >= 256:
        raise ValueError("git_blob_batch_header_invalid")
    try:
        object_id, kind, raw_size = raw[:-1].decode("ascii").split(" ")
        size = int(raw_size)
    except (UnicodeError, ValueError) as exc:
        raise ValueError("git_blob_batch_header_invalid") from exc
    if object_id != expected_id or kind != "blob" or size < 0:
        raise ValueError("git_blob_batch_header_invalid")
    return size


def _body(stream: object, object_id: str, object_format: str, size: int) -> bytes:
    digest = hashlib.new(object_format)
    digest.update(f"blob {size}\0".encode("ascii"))
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = stream.read(min(_CHUNK_BYTES, remaining))  # type: ignore[attr-defined]
        if not chunk:
            raise ValueError("git_blob_batch_truncated")
        chunks.append(chunk)
        digest.update(chunk)
        remaining -= len(chunk)
    if digest.hexdigest() != object_id:
        raise ValueError("git_blob_digest_mismatch")
    return b"".join(chunks)


def _finish_process(
    process: subprocess.Popen[bytes], worker: threading.Thread,
    state: Mapping[str, object],
) -> None:
    if worker.is_alive():
        process.kill()
        worker.join(timeout=5)
        raise subprocess.TimeoutExpired(process.args, 120)
    if process.stdin is not None:
        try:
            process.stdin.close()
        except BrokenPipeError:
            pass
    returncode = process.wait(timeout=30)
    error = state.get("error")
    if isinstance(error, BaseException):
        raise error
    if returncode != 0:
        raise subprocess.CalledProcessError(returncode, process.args)


def _validate_request(
    objects: Mapping[str, str], object_format: str,
    max_blob: int, max_total: int,
) -> None:
    length = 40 if object_format == "sha1" else 64
    if (
        object_format not in {"sha1", "sha256"} or not objects
        or max_blob < 1 or max_total < 1 or max_blob > max_total
        or any(
            not isinstance(name, str) or not name
            or not isinstance(value, str) or len(value) != length
            or any(char not in "0123456789abcdef" for char in value)
            for name, value in objects.items()
        )
    ):
        raise ValueError("git_blob_batch_request_invalid")


__all__ = ["read_exact_git_blobs"]
