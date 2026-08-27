"""Secret-free runtime identity for reproducible HoloIndex retrieval evidence."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import stat
import struct
import sys
import sysconfig
from importlib import metadata
from pathlib import Path
from typing import Any, Iterable, Mapping

from holo_index.query_receipt import digest_json
from holo_index.retrieval_runtime_binding import is_retrieval_runtime_digest

from .reddog_holoindex_process_image import (
    ProcessExecutableProofError,
    hold_process_executable_for_launch,
    prove_process_executable_path,
)


RUNTIME_ENVIRONMENT_SCHEMA = "holoindex_retrieval_runtime_environment.v1"
BACKEND_MANIFEST_RELATIVE_PATH = "scripts/reddog_backend_manifest.json"
QUERY_RUNTIME_FORCED_ENVIRONMENT = {
    "ANONYMIZED_TELEMETRY": "false",
    "HF_DATASETS_OFFLINE": "1",
    "HF_HUB_OFFLINE": "1",
    "HOLOINDEX_QUERY_READONLY": "1",
    "HOLO_ALLOW_PIP_INSTALL": "0",
    "HOLO_DISABLE_PIP_INSTALL": "1",
    "HOLO_OFFLINE": "1",
    "HOLO_SILENT": "1",
    "HOLO_USE_TURBOQUANT": "0",
    "TRANSFORMERS_OFFLINE": "1",
}
OWNER_STARTUP_FORCED_ENVIRONMENT = {
    "CUDA_VISIBLE_DEVICES": "",
    "MKL_NUM_THREADS": "1",
    "NVIDIA_VISIBLE_DEVICES": "none",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "PYTHONHASHSEED": "0",
    "TOKENIZERS_PARALLELISM": "false",
    "TORCH_DEVICE": "cpu",
}
_RUNTIME_KNOB_DEFAULTS = {
    "CUDA_VISIBLE_DEVICES": "",
    "HOLO_CACHE_SIZE": "100",
    "HOLO_CACHE_TTL": "300",
    "HOLO_EMIT_CONFIDENCE": "0",
    "HOLO_ENCODE_TIMEOUT": "3",
    "HOLO_FORCE_SYMBOL_SCAN": "0",
    "HOLO_LEXICAL_BATCH": "500",
    "HOLO_LEXICAL_MAX_DOCS": "",
    "HOLO_MIN_SIMILARITY": "0.35",
    "HOLO_MODEL_IMPORT_TIMEOUT": "120",
    "HOLO_MODEL_LOAD_TIMEOUT": "120",
    "HOLO_SEARCH_TIMEOUT": "15",
    "HOLO_SKIP_MODEL": "0",
    "MKL_NUM_THREADS": "",
    "NVIDIA_VISIBLE_DEVICES": "",
    "OMP_NUM_THREADS": "",
    "OPENBLAS_NUM_THREADS": "",
    "PYTHONHASHSEED": "",
    "TOKENIZERS_PARALLELISM": "",
    "TORCH_DEVICE": "",
}
_DISTRIBUTION_FILES = ("METADATA", "WHEEL", "RECORD", "direct_url.json")
_REQUIRED_DISTRIBUTION_FILES = frozenset({"METADATA", "WHEEL", "RECORD"})
_REPLICA_FIELDS = (
    "query_replica_descriptor_digest",
    "query_replica_generation_id",
    "query_replica_id",
    "query_replica_path_identity_digest",
)
_NORMALIZED_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_METADATA_FILE_BYTES = 2 * 1024 * 1024
_MAX_METADATA_TOTAL_BYTES = 32 * 1024 * 1024
_MAX_DISTRIBUTIONS = 2_048
_MAX_EXECUTABLE_BYTES = 512 * 1024 * 1024
_MAX_RUNTIME_SOURCE_BYTES = 512 * 1024 * 1024
_MAX_RUNTIME_SOURCE_FILE_BYTES = 64 * 1024 * 1024
_MAX_RUNTIME_SOURCE_FILES = 10_000


class RuntimeEnvironmentBindingError(RuntimeError):
    """The exact retrieval runtime could not be represented safely."""


def _fail(code: str) -> None:
    raise RuntimeEnvironmentBindingError(code)


def _sha256(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _file_identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        int(value.st_dev), int(value.st_ino), int(value.st_size),
        int(value.st_mtime_ns), int(stat.S_IFMT(value.st_mode)),
    )


def _read_stable_regular_file(path: Path, *, maximum: int, error: str) -> bytes:
    descriptor = -1
    try:
        before = os.lstat(path)
        attributes = int(getattr(before, "st_file_attributes", 0))
        if (
            not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode)
            or attributes & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
            or getattr(path, "is_junction", lambda: False)()
            or before.st_size < 0 or before.st_size > maximum
        ):
            _fail(error)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOINHERIT", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        if os.name == "nt":
            from .reddog_holoindex_acceptance_windows import (
                validate_windows_file_descriptor_exact_path,
            )
            validate_windows_file_descriptor_exact_path(descriptor, path)
        if _file_identity(os.fstat(descriptor)) != _file_identity(before):
            _fail(error)
        chunks: list[bytes] = []
        remaining = int(before.st_size)
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                _fail(error)
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.lstat(path)
        if (
            _file_identity(os.fstat(descriptor)) != _file_identity(before)
            or _file_identity(after) != _file_identity(before)
        ):
            _fail(error)
        return b"".join(chunks)
    except (OSError, TypeError, ValueError):
        _fail(error)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _safe_text(value: Any, *, maximum: int = 256) -> str:
    text = value if type(value) is str else ""
    if (
        len(text) > maximum
        or any(ord(character) < 0x20 or ord(character) > 0x7E for character in text)
    ):
        _fail("RUNTIME_ENVIRONMENT_VALUE_INVALID")
    return text


def _distribution_name(value: Any) -> str:
    normalized = re.sub(r"[-_.]+", "-", _safe_text(value).strip()).lower()
    if not _NORMALIZED_NAME.fullmatch(normalized):
        _fail("RUNTIME_DISTRIBUTION_NAME_INVALID")
    return normalized


def _distribution_text(distribution: Any, filename: str) -> str:
    try:
        value = distribution.read_text(filename)
    except Exception:
        _fail("RUNTIME_DISTRIBUTION_METADATA_UNREADABLE")
    if value is None:
        if filename in _REQUIRED_DISTRIBUTION_FILES:
            _fail("RUNTIME_DISTRIBUTION_METADATA_INCOMPLETE")
        return ""
    if type(value) is not str or len(value.encode("utf-8")) > _MAX_METADATA_FILE_BYTES:
        _fail("RUNTIME_DISTRIBUTION_METADATA_INVALID")
    return value


def distribution_environment_manifest(
    distributions: Iterable[Any],
) -> tuple[Mapping[str, Any], ...]:
    """Return sorted build identities without publishing paths or metadata."""

    rows: list[Mapping[str, Any]] = []
    total_bytes = 0
    for distribution in distributions:
        if len(rows) >= _MAX_DISTRIBUTIONS:
            _fail("RUNTIME_DISTRIBUTION_LIMIT_EXCEEDED")
        try:
            name = _distribution_name(distribution.metadata.get("Name"))
            version = _safe_text(distribution.version).strip()
        except (AttributeError, TypeError):
            _fail("RUNTIME_DISTRIBUTION_METADATA_INVALID")
        if not version:
            _fail("RUNTIME_DISTRIBUTION_VERSION_INVALID")
        files = {
            filename: _distribution_text(distribution, filename)
            for filename in _DISTRIBUTION_FILES
        }
        total_bytes += sum(len(value.encode("utf-8")) for value in files.values())
        if total_bytes > _MAX_METADATA_TOTAL_BYTES:
            _fail("RUNTIME_DISTRIBUTION_METADATA_LIMIT_EXCEEDED")
        rows.append({
            "name": name,
            "version": version,
            "metadata_digest": _sha256(files["METADATA"].encode("utf-8")),
            "wheel_digest": _sha256(files["WHEEL"].encode("utf-8")),
            "record_digest": _sha256(files["RECORD"].encode("utf-8")),
            "direct_url_digest": (
                _sha256(files["direct_url.json"].encode("utf-8"))
                if files["direct_url.json"] else ""
            ),
        })
    rows.sort(key=lambda row: str(row["name"]))
    names = [str(row["name"]) for row in rows]
    if not rows or len(names) != len(set(names)):
        _fail("RUNTIME_DISTRIBUTION_SET_INVALID")
    return tuple(rows)


def _site_packages_path(entries: Iterable[str]) -> Path:
    candidates: dict[str, Path] = {}
    for value in entries:
        candidate = Path(str(value or ""))
        if candidate.name.lower() not in {"site-packages", "dist-packages"}:
            continue
        try:
            if not candidate.is_absolute() or any(
                part in {".", ".."} for part in candidate.parts
            ):
                _fail("RUNTIME_SITE_PACKAGES_INVALID")
            current = Path(candidate.anchor)
            for part in candidate.parts[1:]:
                current /= part
                observed = os.lstat(current)
                attributes = int(getattr(observed, "st_file_attributes", 0))
                if (
                    stat.S_ISLNK(observed.st_mode)
                    or attributes
                    & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
                    or getattr(current, "is_junction", lambda: False)()
                ):
                    _fail("RUNTIME_SITE_PACKAGES_INVALID")
            resolved = candidate.resolve(strict=True)
        except OSError:
            _fail("RUNTIME_SITE_PACKAGES_UNAVAILABLE")
        if (
            os.path.normcase(str(resolved)) != os.path.normcase(str(candidate))
            or not resolved.is_dir()
        ):
            _fail("RUNTIME_SITE_PACKAGES_INVALID")
        candidates[os.path.normcase(str(resolved))] = resolved
    if len(candidates) != 1:
        _fail("RUNTIME_SITE_PACKAGES_AMBIGUOUS")
    return next(iter(candidates.values()))


def _executable_manifest(executable_path: Path | str | None) -> Mapping[str, Any]:
    raw = executable_path or getattr(sys, "_base_executable", sys.executable)
    try:
        candidate = Path(raw)
        proof = prove_process_executable_path(candidate)
        size = int(proof.identity[2])
        if size <= 0 or size > _MAX_EXECUTABLE_BYTES:
            _fail("RUNTIME_EXECUTABLE_SIZE_INVALID")
        hasher = hashlib.sha256()
        with hold_process_executable_for_launch(proof) as capability:
            os.lseek(capability.descriptor, 0, os.SEEK_SET)
            remaining = size
            while remaining:
                chunk = os.read(capability.descriptor, min(1024 * 1024, remaining))
                if not chunk:
                    _fail("RUNTIME_EXECUTABLE_READ_INCOMPLETE")
                hasher.update(chunk)
                remaining -= len(chunk)
            if os.fstat(capability.descriptor).st_size != size:
                _fail("RUNTIME_EXECUTABLE_CHANGED")
    except (OSError, TypeError, ValueError, ProcessExecutableProofError):
        _fail("RUNTIME_EXECUTABLE_UNPROVEN")
    return {"content_digest": "sha256:" + hasher.hexdigest(), "size": size}


def _platform_manifest() -> Mapping[str, Any]:
    values = {
        "implementation": sys.implementation.name,
        "implementation_version": list(sys.implementation.version[:3]),
        "python_version": list(sys.version_info[:3]),
        "cache_tag": sys.implementation.cache_tag or "",
        "abi_flags": getattr(sys, "abiflags", ""),
        "soabi": sysconfig.get_config_var("SOABI") or "",
        "platform_tag": sysconfig.get_platform(),
        "system": platform.system(),
        "system_release": platform.release(),
        "machine": platform.machine(),
        "byteorder": sys.byteorder,
        "pointer_bits": struct.calcsize("P") * 8,
    }
    for value in values.values():
        if isinstance(value, str):
            _safe_text(value)
    return values


def _declared_source_closure(raw: bytes) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        _fail("RUNTIME_SOURCE_MANIFEST_UNAVAILABLE")
    declared = value.get("required_runtime_sha256") if isinstance(value, Mapping) else None
    if (
        not isinstance(value, Mapping)
        or value.get("schema_version") != "reddog_backend_manifest.v3"
        or not isinstance(declared, Mapping)
        or not declared
        or len(declared) > _MAX_RUNTIME_SOURCE_FILES
    ):
        _fail("RUNTIME_SOURCE_MANIFEST_INVALID")
    return value, declared


def _verified_source_row(
    root: Path, relative: Any, expected: Any,
) -> Mapping[str, Any]:
    if (
        type(relative) is not str or not relative or len(relative) > 512
        or "\\" in relative or ":" in relative
        or any(part in {"", ".", ".."} for part in relative.split("/"))
        or type(expected) is not str
        or re.fullmatch(r"[0-9a-f]{64}", expected) is None
    ):
        _fail("RUNTIME_SOURCE_MANIFEST_INVALID")
    raw = _read_stable_regular_file(
        root.joinpath(*relative.split("/")),
        maximum=_MAX_RUNTIME_SOURCE_FILE_BYTES,
        error="RUNTIME_SOURCE_FILE_UNAVAILABLE",
    )
    actual = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    if actual != expected:
        _fail("RUNTIME_SOURCE_DIGEST_MISMATCH")
    return {"relative_path": relative, "size": len(raw), "digest": actual}


def _backend_manifest(source_root: Path | str) -> Mapping[str, Any]:
    root = Path(source_root).resolve(strict=True)
    raw = _read_stable_regular_file(
        root / BACKEND_MANIFEST_RELATIVE_PATH,
        maximum=4 * 1024 * 1024,
        error="RUNTIME_SOURCE_MANIFEST_UNAVAILABLE",
    )
    value, declared = _declared_source_closure(raw)
    rows: list[Mapping[str, Any]] = []
    total_bytes = 0
    for relative, expected in sorted(declared.items()):
        row = _verified_source_row(root, relative, expected)
        rows.append(row)
        total_bytes += int(row["size"])
        if total_bytes > _MAX_RUNTIME_SOURCE_BYTES:
            _fail("RUNTIME_SOURCE_CLOSURE_LIMIT_EXCEEDED")
    return {
        "schema_version": str(value["schema_version"]),
        "manifest_digest": _sha256(_canonical_bytes(value)),
        "runtime_file_count": len(rows),
        "runtime_file_bytes": total_bytes,
        "verified_runtime_closure_digest": digest_json(rows),
        "runtime_source_bytes_verified": True,
    }


def retrieval_runtime_knobs(
    environment: Mapping[str, str] | None = None,
) -> Mapping[str, Mapping[str, Any]]:
    """Project only allowlisted behavior controls exactly as observed."""

    source = os.environ if environment is None else environment
    defaults = {
        **{name: value for name, value in QUERY_RUNTIME_FORCED_ENVIRONMENT.items()},
        **{name: value for name, value in OWNER_STARTUP_FORCED_ENVIRONMENT.items()},
        **_RUNTIME_KNOB_DEFAULTS,
    }
    values: dict[str, Mapping[str, Any]] = {
        name: {
            "present": name in source,
            "value": _safe_text(source.get(name, default), maximum=128),
        }
        for name, default in defaults.items()
    }
    return dict(sorted(values.items()))


def _verify_required_environment(
    source: Mapping[str, str], required: Mapping[str, str] | None,
) -> bool:
    if required is None:
        return False
    for name, expected in required.items():
        if source.get(name) != expected:
            _fail("RUNTIME_REQUIRED_ENVIRONMENT_MISMATCH")
    return True


def _model_artifact_closure(
    artifacts: Iterable[Any] | None,
    *,
    required: bool,
) -> Mapping[str, Any]:
    rows: list[Mapping[str, Any]] = []
    for artifact in artifacts or ():
        if isinstance(artifact, Mapping):
            relative = str(artifact.get("relative_path") or "")
            size = artifact.get("size")
            digest = str(artifact.get("digest") or "")
        else:
            relative = str(getattr(artifact, "relative_path", "") or "")
            size = getattr(artifact, "size", None)
            digest = str(getattr(artifact, "digest", "") or "")
        if not relative.startswith("models/"):
            continue
        if (
            "\\" in relative or ".." in relative.split("/")
            or type(size) is not int or size < 0
            or not is_retrieval_runtime_digest(digest)
        ):
            _fail("RUNTIME_MODEL_ARTIFACT_INVALID")
        rows.append({"relative_path": relative, "size": size, "digest": digest})
    rows.sort(key=lambda row: str(row["relative_path"]))
    if required and not rows:
        _fail("RUNTIME_MODEL_ARTIFACT_CLOSURE_INCOMPLETE")
    return {
        "artifact_count": len(rows),
        "artifact_bytes": sum(int(row["size"]) for row in rows),
        "artifact_manifest_digest": digest_json(rows) if rows else "",
        "complete": bool(rows),
    }


def _replica_deployment_manifest(
    replica_binding: Mapping[str, Any], *, required: bool,
) -> tuple[Mapping[str, str], bool]:
    replica = {field: str(replica_binding.get(field) or "") for field in _REPLICA_FIELDS}
    if any(value and not is_retrieval_runtime_digest(value) for value in replica.values()):
        _fail("RUNTIME_REPLICA_BINDING_INVALID")
    complete = all(replica.values())
    if required and not complete:
        _fail("RUNTIME_REPLICA_BINDING_INCOMPLETE")
    return replica, complete


def _installed_distribution_manifest(
    entries: Iterable[str], distributions: Iterable[Any] | None,
) -> tuple[Mapping[str, Any], ...]:
    site_packages = _site_packages_path(entries)
    installed = (
        metadata.distributions(path=[str(site_packages)])
        if distributions is None else distributions
    )
    return distribution_environment_manifest(installed)


def runtime_environment_manifest(
    *,
    source_root: Path | str,
    ranker_digest: str,
    replica_binding: Mapping[str, Any],
    environment: Mapping[str, str] | None = None,
    executable_path: Path | str | None = None,
    sys_path_entries: Iterable[str] | None = None,
    distributions: Iterable[Any] | None = None,
    require_complete_replica_binding: bool = True,
    replica_artifacts: Iterable[Any] | None = None,
    required_environment: Mapping[str, str] | None = None,
) -> Mapping[str, Any]:
    """Build the complete private manifest whose digest crosses trust boundaries."""

    if not is_retrieval_runtime_digest(ranker_digest):
        _fail("RUNTIME_RANKER_DIGEST_INVALID")
    replica, replica_complete = _replica_deployment_manifest(
        replica_binding, required=require_complete_replica_binding,
    )
    entries = tuple(sys.path if sys_path_entries is None else sys_path_entries)
    distribution_manifest = _installed_distribution_manifest(entries, distributions)
    runtime_environment = os.environ if environment is None else environment
    return {
        "schema_version": RUNTIME_ENVIRONMENT_SCHEMA,
        "source_closure": _backend_manifest(source_root),
        "ranker_digest": ranker_digest,
        "executable": _executable_manifest(executable_path),
        "platform_abi": _platform_manifest(),
        "distribution_count": len(distribution_manifest),
        "distribution_build_record_digest": digest_json(distribution_manifest),
        "installed_distribution_bytes_verified": False,
        "replica_deployment_binding": replica,
        "replica_deployment_binding_complete": replica_complete,
        "model_artifact_closure": _model_artifact_closure(
            replica_artifacts, required=require_complete_replica_binding,
        ),
        "declared_runtime_knobs": retrieval_runtime_knobs(runtime_environment),
        "required_environment_verified": _verify_required_environment(
            runtime_environment, required_environment,
        ),
        "python_hash_seed_effect_verified": False,
        "contains_paths": False,
        "contains_environment_secrets": False,
    }


def runtime_environment_digest(**kwargs: Any) -> str:
    """Return the only secret-free projection exposed by the query owner."""

    return digest_json(runtime_environment_manifest(**kwargs))


def exact_runtime_closure_verified(manifest: Mapping[str, Any]) -> bool:
    """Require every byte closure needed for production A-grade evidence."""

    source = manifest.get("source_closure")
    model = manifest.get("model_artifact_closure")
    return bool(
        isinstance(source, Mapping)
        and source.get("runtime_source_bytes_verified") is True
        and manifest.get("installed_distribution_bytes_verified") is True
        and manifest.get("replica_deployment_binding_complete") is True
        and isinstance(model, Mapping) and model.get("complete") is True
        and manifest.get("required_environment_verified") is True
    )


__all__ = [
    "BACKEND_MANIFEST_RELATIVE_PATH",
    "QUERY_RUNTIME_FORCED_ENVIRONMENT",
    "OWNER_STARTUP_FORCED_ENVIRONMENT",
    "RUNTIME_ENVIRONMENT_SCHEMA",
    "RuntimeEnvironmentBindingError",
    "distribution_environment_manifest",
    "exact_runtime_closure_verified",
    "retrieval_runtime_knobs",
    "runtime_environment_digest",
    "runtime_environment_manifest",
]
