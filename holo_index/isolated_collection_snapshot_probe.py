"""Isolated persisted-state verification for HoloIndex maintenance receipts."""

from __future__ import annotations

import argparse
import json
import math
import os
import stat
import subprocess  # nosec B404  # Fixed interpreter/module, never a worker command.
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence

from holo_index.freshness_receipt import (
    BASELINE_QUERY_COLLECTIONS,
    COLLECTION_ATTRS,
    CollectionFreshness,
    HoloIndexFreshnessReceipt,
    collection_snapshot_matches_entry,
    freshness_receipt_integrity_ok,
)
from holo_index.storage_contract import storage_path_identity
from holo_index.persisted_vector_segment_probe import unqueryable_vector_segments
from holo_index.vector_segment_durability import non_durable_vector_segments
from modules.infrastructure.foundups_mcp_bridge.src.reddog_sealed_holo_runtime import (
    scrub_holo_child_environment,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_process_image import (
    ProcessExecutableProofError,
    hold_process_executable_for_launch,
)


SCHEMA_VERSION = "holoindex_isolated_snapshot_probe.v1"
MAX_RECEIPT_BYTES = 2_000_000
MAX_PROCESS_OUTPUT_BYTES = 16_384
DEFAULT_TIMEOUT_SECONDS = 180.0
SUPPORTED_CHROMADB_VERSIONS = frozenset({"1.5.5"})
STABLE_RUNTIME_ERRORS = frozenset({
    "CANDIDATE_SOURCE_ORIGIN_INVALID",
    "RUNTIME_DEPENDENCY_UNAVAILABLE",
    "UNSUPPORTED_CHROMADB_VERSION",
})
_PROBE_ERRORS = STABLE_RUNTIME_ERRORS | {
    "", "BASELINE_COLLECTIONS_INCOMPLETE", "COLLECTION_SNAPSHOT_MISMATCH",
    "INVALID_RECEIPT_INTEGRITY", "INVALID_REQUEST", "PERSISTED_STORE_UNAVAILABLE",
    "SSD_PATH_MISMATCH", "VECTOR_SEGMENT_UNAVAILABLE",
}


class IsolatedSnapshotProbeError(RuntimeError):
    """Stable fail-closed error raised by the parent maintenance process."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _RuntimeDependencyError(ValueError):
    pass


@dataclass(frozen=True)
class IsolatedSnapshotProbeResult:
    """Secret-free persisted collection verification result."""

    ok: bool
    generation_id: str
    mismatched_collections: tuple[str, ...]
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": self.ok,
            "generation_id": self.generation_id,
            "mismatched_collections": list(self.mismatched_collections),
            "error": self.error,
        }


def _receipt_from_mapping(value: Mapping[str, Any]) -> HoloIndexFreshnessReceipt:
    collections = value.get("collections")
    if not isinstance(collections, list):
        raise ValueError("collections_required")
    return HoloIndexFreshnessReceipt(
        schema_version=str(value.get("schema_version") or ""),
        generated_at=str(value.get("generated_at") or ""),
        repo_root=str(value.get("repo_root") or ""),
        repo_head_sha=str(value.get("repo_head_sha") or ""),
        ssd_path=str(value.get("ssd_path") or ""),
        source=str(value.get("source") or ""),
        generation_id=str(value.get("generation_id") or ""),
        base_generation_id=str(value.get("base_generation_id") or ""),
        collections=[
            CollectionFreshness(**entry)
            for entry in collections
            if isinstance(entry, Mapping)
        ],
    )


def _default_client_factory(
    ssd_path: Path, runtime_site_packages: Path | None = None,
) -> Any:
    os.environ.update(
        {
            "ANONYMIZED_TELEMETRY": "false",
            "HOLOINDEX_QUERY_READONLY": "1",
            "HOLO_OFFLINE": "1",
            "HOLO_DISABLE_PIP_INSTALL": "1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
        }
    )
    try:
        import chromadb
        from chromadb.config import Settings
    except (ImportError, OSError):
        raise _RuntimeDependencyError("RUNTIME_DEPENDENCY_UNAVAILABLE") from None

    if str(getattr(chromadb, "__version__", "")) not in SUPPORTED_CHROMADB_VERSIONS:
        raise _RuntimeDependencyError("UNSUPPORTED_CHROMADB_VERSION")
    if runtime_site_packages is not None:
        origin = Path(str(getattr(chromadb, "__file__", ""))).resolve(strict=False)
        if not origin.is_file() or not origin.is_relative_to(runtime_site_packages):
            raise _RuntimeDependencyError("RUNTIME_DEPENDENCY_UNAVAILABLE")

    return chromadb.PersistentClient(
        path=str(ssd_path / "vectors"),
        settings=Settings(anonymized_telemetry=False, migrations="validate"),
    )


def finalize_chroma_client(client: Any) -> None:
    """Stop one pinned Chroma client and clear its process-local cache."""

    system = getattr(client, "_system", None)
    stop = getattr(system, "stop", None)
    clear_cache = getattr(type(client), "clear_system_cache", None)
    if not callable(stop) or not callable(clear_cache):
        raise ValueError("probe_client_lifecycle_unavailable")
    try:
        stop()
    finally:
        clear_cache()


def open_persisted_collection_view(
    ssd_path: Path | str,
    *,
    client_factory: Callable[[Path], Any] | None = None,
) -> Any:
    """Open collection handles from persisted state without loading an encoder."""

    ssd = Path(ssd_path).resolve(strict=False)
    client = (client_factory or _default_client_factory)(ssd)
    attributes: dict[str, Any] = {}
    for name, attr_name in COLLECTION_ATTRS.items():
        try:
            attributes[attr_name] = client.get_collection(
                name,
                embedding_function=None,
            )
        except Exception:
            attributes[attr_name] = None
    metadata = getattr(attributes.get("code_collection"), "metadata", None)
    embedding = metadata if isinstance(metadata, Mapping) else {}
    return SimpleNamespace(
        client=client,
        **attributes,
        index_embedding_backend=str(embedding.get("embedding_backend") or ""),
        index_embedding_model_id=str(embedding.get("embedding_model") or ""),
        index_embedding_space_fingerprint=str(
            embedding.get("embedding_space_fingerprint") or ""
        ),
    )


def probe_collection_snapshots(
    receipt: HoloIndexFreshnessReceipt,
    *,
    ssd_path: Path | str,
    client_factory: Callable[[Path], Any] | None = None,
) -> IsolatedSnapshotProbeResult:
    """Reopen the persisted store and verify every canonical collection once."""

    ssd = Path(ssd_path).resolve(strict=False)
    if not freshness_receipt_integrity_ok(receipt):
        return IsolatedSnapshotProbeResult(
            False, receipt.generation_id, (), "INVALID_RECEIPT_INTEGRITY"
        )
    if storage_path_identity(receipt.ssd_path) != storage_path_identity(ssd):
        return IsolatedSnapshotProbeResult(
            False, receipt.generation_id, (), "SSD_PATH_MISMATCH"
        )
    entries = {
        entry.name: entry
        for entry in receipt.collections
        if entry.name in BASELINE_QUERY_COLLECTIONS
    }
    if set(entries) != set(BASELINE_QUERY_COLLECTIONS):
        return IsolatedSnapshotProbeResult(
            False, receipt.generation_id, (), "BASELINE_COLLECTIONS_INCOMPLETE"
        )
    non_durable = non_durable_vector_segments(
        ssd,
        collection_names=BASELINE_QUERY_COLLECTIONS,
    )
    if non_durable:
        return IsolatedSnapshotProbeResult(
            False,
            receipt.generation_id,
            non_durable,
            "VECTOR_SEGMENT_UNAVAILABLE",
        )
    try:
        client = (client_factory or _default_client_factory)(ssd)
        mismatches = _snapshot_mismatches(client, entries)
    except Exception:
        return IsolatedSnapshotProbeResult(
            False, receipt.generation_id, (), "PERSISTED_STORE_UNAVAILABLE"
        )
    if mismatches:
        return IsolatedSnapshotProbeResult(
            False,
            receipt.generation_id,
            mismatches,
            "COLLECTION_SNAPSHOT_MISMATCH",
        )
    unqueryable = unqueryable_vector_segments(
        client,
        entries,
        ssd_path=ssd,
        collection_names=BASELINE_QUERY_COLLECTIONS,
    )
    return IsolatedSnapshotProbeResult(
        not unqueryable, receipt.generation_id,
        unqueryable,
        "" if not unqueryable else "VECTOR_SEGMENT_UNAVAILABLE",
    )


def _snapshot_mismatches(
    client: Any,
    entries: Mapping[str, CollectionFreshness],
) -> tuple[str, ...]:
    holo = SimpleNamespace(client=client)
    return tuple(
        name
        for name in sorted(BASELINE_QUERY_COLLECTIONS)
        if not collection_snapshot_matches_entry(holo, name, entries[name])
    )


def _probe_environment(runtime_site_packages: Path | None = None) -> dict[str, str]:
    environment = scrub_holo_child_environment(os.environ)
    environment.update(
        {
            "ANONYMIZED_TELEMETRY": "false",
            "HOLOINDEX_QUERY_READONLY": "1",
            "HOLO_OFFLINE": "1",
            "HOLO_DISABLE_PIP_INSTALL": "1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
        }
    )
    if runtime_site_packages is not None:
        environment["PYTHONPATH"] = str(runtime_site_packages)
    return environment


def _is_link_or_reparse(path: Path) -> bool:
    metadata = os.lstat(path)
    return bool(
        stat.S_ISLNK(metadata.st_mode)
        or getattr(metadata, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        or getattr(path, "is_junction", lambda: False)()
    )


def _validated_runtime_site_packages(values: Sequence[str]) -> Path:
    if len(values) != 1:
        raise IsolatedSnapshotProbeError("RUNTIME_DEPENDENCY_UNAVAILABLE")
    raw = Path(values[0])
    try:
        resolved = raw.resolve(strict=True)
        if (
            not raw.is_absolute()
            or os.path.normcase(str(raw)) != os.path.normcase(str(resolved))
            or not resolved.is_dir()
            or resolved.name.lower() != "site-packages"
            or resolved.parent.name.lower() != "lib"
            or resolved.parent.parent.name.lower() != ".venv"
        ):
            raise ValueError
        current = Path(resolved.anchor)
        for component in resolved.parts[1:]:
            current /= component
            if _is_link_or_reparse(current):
                raise ValueError
    except (OSError, ValueError):
        raise IsolatedSnapshotProbeError("RUNTIME_DEPENDENCY_UNAVAILABLE") from None
    return resolved


def _runtime_executable(runtime: Path | None, proof: object) -> Path:
    if runtime is None:
        return Path(sys.executable)
    try:
        path = Path(proof.path)
    except (AttributeError, TypeError, ValueError):
        raise IsolatedSnapshotProbeError("RUNTIME_DEPENDENCY_UNAVAILABLE") from None
    return path


def _bounded_process_stdout(
    completed: Any,
    stdout_file: Any,
    stderr_file: Any,
) -> str:
    injected_stdout = getattr(completed, "stdout", None)
    if isinstance(injected_stdout, str):
        stdout = injected_stdout
        stdout_size = len(stdout.encode("utf-8"))
    else:
        stdout_file.seek(0, os.SEEK_END)
        stdout_size = stdout_file.tell()
        stdout_file.seek(0)
        stdout = stdout_file.read(MAX_PROCESS_OUTPUT_BYTES + 1).decode(
            "utf-8", errors="strict"
        )
    injected_stderr = getattr(completed, "stderr", None)
    stderr_size = (
        len(injected_stderr.encode("utf-8"))
        if isinstance(injected_stderr, str)
        else stderr_file.tell()
    )
    if stdout_size > MAX_PROCESS_OUTPUT_BYTES or stderr_size > (
        MAX_PROCESS_OUTPUT_BYTES
    ):
        raise IsolatedSnapshotProbeError("ISOLATED_PROBE_OUTPUT_LIMIT")
    return stdout


def _run_isolated_probe(
    receipt: HoloIndexFreshnessReceipt,
    ssd_path: Path | str,
    repo_root: Path | str,
    timeout_seconds: float,
    runtime_site_packages: Sequence[str] | None = None,
    base_executable_proof: object = None,
    runner: Callable[..., Any] | None = None,
) -> str:
    runtime = (
        _validated_runtime_site_packages(runtime_site_packages)
        if runtime_site_packages is not None else None
    )
    executable = _runtime_executable(runtime, base_executable_proof)
    command = _probe_command(executable, ssd_path, repo_root, runtime)
    process_runner = runner if runner is not None else subprocess.run
    try:
        with (
            tempfile.TemporaryFile() as stdout_file,
            tempfile.TemporaryFile() as stderr_file,
        ):
            runner_kwargs = {
                "cwd": str(Path(repo_root).resolve(strict=False)),
                "env": _probe_environment(runtime),
                "input": receipt.to_json().encode("utf-8"),
                "stdout": stdout_file,
                "stderr": stderr_file,
                "timeout": float(timeout_seconds),
                "check": False,
                "shell": False,
            }
            if runtime is None:
                completed = process_runner(command, **runner_kwargs)
            else:
                try:
                    with hold_process_executable_for_launch(
                        base_executable_proof
                    ) as capability:
                        command[0] = str(capability.launch_path)
                        if capability.pass_fds:
                            runner_kwargs["pass_fds"] = capability.pass_fds
                        completed = process_runner(  # nosec B603
                            command, **runner_kwargs
                        )
                except ProcessExecutableProofError:
                    raise IsolatedSnapshotProbeError(
                        "RUNTIME_DEPENDENCY_UNAVAILABLE"
                    ) from None
            stdout = _bounded_process_stdout(completed, stdout_file, stderr_file)
    except (OSError, subprocess.SubprocessError, ValueError):
        raise IsolatedSnapshotProbeError("ISOLATED_PROBE_PROCESS_FAILED") from None
    if (
        not isinstance(completed.returncode, int)
        or isinstance(completed.returncode, bool)
        or completed.returncode != 0
    ):
        raise IsolatedSnapshotProbeError("ISOLATED_PROBE_PROCESS_FAILED")
    return stdout


def _probe_command(
    executable: Path, ssd_path: Path | str, repo_root: Path | str,
    runtime: Path | None,
) -> list[str]:
    command = [str(executable), *(["-S"] if runtime else []), "-B", "-m",
               "holo_index.isolated_collection_snapshot_probe", "--ssd",
               str(Path(ssd_path).resolve(strict=False))]
    if runtime:
        command.extend(["--runtime-site-packages", str(runtime), "--repo-root",
                        str(Path(repo_root).resolve(strict=False))])
    return command


def _validated_probe_response(
    stdout: str,
    generation_id: str,
) -> Mapping[str, Any]:
    try:
        response = json.loads(stdout)
    except (TypeError, ValueError, json.JSONDecodeError):
        raise IsolatedSnapshotProbeError("ISOLATED_PROBE_RESPONSE_INVALID") from None
    if not isinstance(response, Mapping):
        raise IsolatedSnapshotProbeError("ISOLATED_PROBE_RESPONSE_INVALID")
    mismatches = response.get("mismatched_collections")
    valid_mismatches = bool(
        isinstance(mismatches, list)
        and all(
            isinstance(name, str) and name in BASELINE_QUERY_COLLECTIONS
            for name in mismatches
        )
        and len(mismatches) == len(set(mismatches))
    )
    expected_keys = {
        "schema_version", "ok", "generation_id", "mismatched_collections", "error"
    }
    if (
        set(response) != expected_keys
        or response.get("schema_version") != SCHEMA_VERSION
        or not isinstance(response.get("ok"), bool)
        or not isinstance(response.get("error"), str)
        or response.get("error") not in _PROBE_ERRORS
        or response.get("generation_id") != generation_id
        or not valid_mismatches
    ):
        raise IsolatedSnapshotProbeError("ISOLATED_PROBE_RESPONSE_INVALID")
    return response


def verify_collection_snapshots_isolated(
    receipt: HoloIndexFreshnessReceipt,
    *,
    ssd_path: Path | str,
    repo_root: Path | str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    runtime_site_packages: Sequence[str] | None = None,
    base_executable_proof: object = None,
) -> list[str]:
    """Run the persisted proof in a fresh Python process or fail closed."""

    deadline = _probe_deadline(timeout_seconds)
    response = _run_validated_probe(
        receipt, ssd_path, repo_root, _remaining_timeout(deadline),
        runtime_site_packages, base_executable_proof,
    )
    mismatches = response["mismatched_collections"]
    if _probe_succeeded(response):
        return []
    if response.get("error") == "COLLECTION_SNAPSHOT_MISMATCH" and mismatches:
        return sorted(mismatches)
    if response.get("error") == "VECTOR_SEGMENT_UNAVAILABLE" and mismatches:
        raise IsolatedSnapshotProbeError("VECTOR_SEGMENT_UNAVAILABLE")
    raise IsolatedSnapshotProbeError(
        str(response.get("error") or "ISOLATED_PROBE_FAILED")
    )


def _run_validated_probe(
    receipt: HoloIndexFreshnessReceipt,
    ssd_path: Path | str,
    repo_root: Path | str,
    timeout_seconds: float,
    runtime_site_packages: Sequence[str] | None = None,
    base_executable_proof: object = None,
) -> Mapping[str, Any]:
    stdout = _run_isolated_probe(
        receipt, ssd_path, repo_root, timeout_seconds, runtime_site_packages,
        base_executable_proof,
    )
    return _validated_probe_response(stdout, receipt.generation_id)


def _probe_succeeded(response: Mapping[str, Any]) -> bool:
    return bool(
        response.get("ok") is True
        and not response.get("mismatched_collections")
        and not response.get("error")
    )


def _probe_deadline(timeout_seconds: float) -> float:
    try:
        timeout = float(timeout_seconds)
    except (TypeError, ValueError):
        raise IsolatedSnapshotProbeError("ISOLATED_PROBE_TIMEOUT_INVALID") from None
    if not math.isfinite(timeout) or timeout <= 0:
        raise IsolatedSnapshotProbeError("ISOLATED_PROBE_TIMEOUT_INVALID")
    return time.monotonic() + timeout


def _remaining_timeout(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise IsolatedSnapshotProbeError("ISOLATED_PROBE_TIMEOUT")
    return remaining


def _read_receipt() -> HoloIndexFreshnessReceipt:
    raw = sys.stdin.buffer.read(MAX_RECEIPT_BYTES + 1)
    if len(raw) > MAX_RECEIPT_BYTES:
        raise ValueError("receipt_too_large")
    value = json.loads(raw.decode("utf-8", errors="strict"))
    if not isinstance(value, Mapping):
        raise ValueError("receipt_not_object")
    return _receipt_from_mapping(value)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ssd", required=True)
    parser.add_argument("--runtime-site-packages")
    parser.add_argument("--repo-root")
    args = parser.parse_args(argv)
    generation_id = ""
    try:
        receipt = _read_receipt()
        generation_id = receipt.generation_id
        original_ssd = Path(args.ssd).resolve(strict=False)
        runtime = None
        if args.runtime_site_packages:
            runtime = _validated_runtime_site_packages((args.runtime_site_packages,))
            if (
                not args.repo_root
                or Path(args.repo_root).resolve(strict=False)
                != Path(__file__).resolve().parents[1]
            ):
                raise _RuntimeDependencyError("CANDIDATE_SOURCE_ORIGIN_INVALID")
        client = _default_client_factory(original_ssd, runtime)
        try:
            result = probe_collection_snapshots(
                receipt,
                ssd_path=original_ssd,
                client_factory=lambda _path: client,
            )
        finally:
            finalize_chroma_client(client)
    except _RuntimeDependencyError as exc:
        result = IsolatedSnapshotProbeResult(False, generation_id, (), str(exc))
    except IsolatedSnapshotProbeError as exc:
        result = IsolatedSnapshotProbeResult(False, generation_id, (), exc.code)
    except Exception:
        result = IsolatedSnapshotProbeResult(False, generation_id, (), "INVALID_REQUEST")
    sys.stdout.write(json.dumps(result.to_dict(), sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "IsolatedSnapshotProbeError",
    "IsolatedSnapshotProbeResult",
    "STABLE_RUNTIME_ERRORS",
    "finalize_chroma_client",
    "open_persisted_collection_view",
    "probe_collection_snapshots",
    "verify_collection_snapshots_isolated",
]
