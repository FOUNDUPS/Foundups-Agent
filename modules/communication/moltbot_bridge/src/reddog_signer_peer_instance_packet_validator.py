"""Strict run-packet validation for one manifest-bound signer instance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_socket_schema import (
    SIGNER_SERVICE_RUN_PACKET_SCHEMA_VERSION,
)


_FIXED_FIELDS = {
    "run_mode": "signer_owned_system_service_entrypoint",
    "process_owner_requirement": "distinct_signer_os_principal",
    "redDog_must_not_spawn": True,
    "main_py_must_not_spawn": True,
    "shell_required": False,
    "shell_command": None,
    "no_secret_values_in_packet": True,
}
_FIELDS = frozenset(
    {
        "schema_version", "run_mode", "repo_root", "working_directory",
        "python_module", "argv", "config_path", "config_digest",
        "owner_authority_config_path", "socket_path",
        "profile_count", "provider_mode", "op_executable", "op_timeout_s",
        "ttl_seconds", "session_id", "process_owner_requirement",
        "redDog_must_not_spawn", "main_py_must_not_spawn", "shell_required",
        "shell_command", "no_secret_values_in_packet", "run_packet_id",
    }
)
_CLI_MODULE = (
    "modules.communication.moltbot_bridge.src."
    "reddog_signer_system_service_entrypoint"
)
_SELECTION_FIELDS = frozenset(
    {
        "manifest_id", "artifact_generation_digest", "config_digest",
        "config_raw_digest", "run_packet_digest", "repo_root", "runtime_root",
        "config_path", "run_packet_path",
    }
)
_GENERATION_SELECTION_FIELDS = frozenset(
    {
        "generation", "generation_revision", "selection_issued_at",
        "selection_expires_at", "owner_config_id",
    }
)


def signer_run_packet_selection_valid(
    selection: object,
    packet: object,
    *,
    root: Path,
    config_path: Path,
    run_packet_path: Path,
    config_digest: str,
    run_packet_raw: str,
) -> bool:
    return _selection_valid(
        selection,
        root=root,
        config_path=config_path,
        run_packet_path=run_packet_path,
        config_digest=config_digest,
        run_packet_raw=run_packet_raw,
    ) and _packet_shape_valid(packet)


def signer_run_packet_bindings_valid(
    packet: Mapping[str, Any],
    *,
    root: Path,
    config_path: Path,
    config_digest: str,
    session_id: str,
    run_packet_path: Path,
    socket_path: Path,
    python_executable: Path,
    owner_authority_config_path: Path | str | None = None,
) -> bool:
    return signer_run_packet_static_valid(packet, root=root) and all(
        (
            Path(str(packet.get("repo_root") or "")).resolve() == root,
            Path(str(packet.get("working_directory") or "")).resolve() == root,
            Path(str(packet.get("config_path") or "")).resolve() == config_path,
            packet.get("config_digest") == config_digest,
            packet.get("session_id") == session_id,
            Path(str(packet.get("socket_path") or "")).resolve() == socket_path,
            packet.get("python_module") == _CLI_MODULE,
            _absolute_outside_repo(socket_path, root),
            _absolute_outside_repo(
                packet.get("owner_authority_config_path"), root
            ),
            bool(owner_authority_config_path),
            Path(
                str(packet.get("owner_authority_config_path") or "")
            ).resolve()
            == Path(str(owner_authority_config_path)).resolve(),
            _argv_valid(
                packet.get("argv"),
                root=root,
                owner_authority_config_path=Path(
                    str(owner_authority_config_path)
                ).resolve(),
                python_executable=python_executable,
            ),
        )
    )


def signer_profile_bindings_valid(
    profiles: tuple[Any, ...],
    profile_count: object,
) -> bool:
    if not profiles or profile_count != len(profiles):
        return False
    ids = [item.signer_profile_id for item in profiles]
    return len(ids) == len(set(ids)) and all(
        _ascii_text(item.signer_profile_id)
        and _ascii_text(item.signer_public_key)
        and _ascii_text(item.key_epoch)
        for item in profiles
    )


def signer_run_packet_static_valid(
    packet: object,
    *,
    root: Path,
) -> bool:
    """Validate the signed packet's self-contained stable launch contract."""

    if not isinstance(packet, Mapping) or not _packet_shape_valid(packet):
        return False
    argv = packet.get("argv")
    if not isinstance(argv, list) or not argv:
        return False
    python_executable = Path(str(argv[0])).resolve()
    owner_path = Path(
        str(packet.get("owner_authority_config_path") or "")
    )
    return all(
        (
            Path(str(packet.get("repo_root") or "")).resolve() == root,
            Path(str(packet.get("working_directory") or "")).resolve()
            == root,
            packet.get("python_module") == _CLI_MODULE,
            _absolute_outside_repo(owner_path, root),
            _absolute_outside_repo(packet.get("config_path"), root),
            _absolute_outside_repo(packet.get("socket_path"), root),
            _argv_valid(
                argv,
                root=root,
                owner_authority_config_path=owner_path.resolve(),
                python_executable=python_executable,
            ),
        )
    )


def signer_generation_bound_selection_valid(value: object) -> bool:
    """Require the exact current-generation launch selection shape."""

    return bool(
        isinstance(value, Mapping)
        and set(value)
        == _SELECTION_FIELDS | _GENERATION_SELECTION_FIELDS
        and _generation_selection_valid(value)
    )


def _packet_shape_valid(packet: object) -> bool:
    if not isinstance(packet, Mapping) or not _ascii_deep(packet):
        return False
    if set(packet) != _FIELDS:
        return False
    if packet.get("schema_version") != SIGNER_SERVICE_RUN_PACKET_SCHEMA_VERSION:
        return False
    packet_id = packet.get("run_packet_id")
    without_id = {
        key: value for key, value in packet.items() if key != "run_packet_id"
    }
    return all(
        (
            _sha256_digest(packet_id),
            packet_id == _digest(without_id),
            all(packet.get(key) == value for key, value in _FIXED_FIELDS.items()),
        )
    )


def _argv_valid(value: object, **bindings: Any) -> bool:
    python_executable = bindings.pop("python_executable")
    if (
        not isinstance(value, list)
        or len(value) != 7
        or not all(_ascii_text(item) for item in value)
        or value[1:3] != ["-m", _CLI_MODULE]
        or Path(value[0]).resolve() != python_executable
    ):
        return False
    pairs = _argv_pairs(value)
    required = _required_argv_pairs(bindings)
    return pairs is not None and pairs == required


def _argv_pairs(value: list[str]) -> dict[str, str] | None:
    pairs: dict[str, str] = {}
    for index, item in enumerate(value[:-1]):
        if item.startswith("--"):
            if item in pairs:
                return None
            pairs[item] = str(value[index + 1])
    return pairs


def _required_argv_pairs(bindings: Mapping[str, Any]) -> dict[str, str]:
    return {
        "--repo-root": str(bindings["root"]),
        "--owner-authority-config": str(
            bindings["owner_authority_config_path"]
        ),
    }


def _selection_valid(value: object, **bindings: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    fields = set(value)
    if fields not in (
        _SELECTION_FIELDS,
        _SELECTION_FIELDS | _GENERATION_SELECTION_FIELDS,
    ):
        return False
    if (
        fields != _SELECTION_FIELDS
        and not signer_generation_bound_selection_valid(value)
    ):
        return False
    return all(
        (
            all(
                _sha256_digest(value.get(key))
                for key in _SELECTION_FIELDS
                if key.endswith("digest") or key == "manifest_id"
            ),
            value.get("config_digest") == bindings["config_digest"],
            value.get("run_packet_digest")
            == _text_digest(bindings["run_packet_raw"]),
            Path(str(value.get("repo_root") or "")).resolve()
            == bindings["root"],
            Path(str(value.get("config_path") or "")).resolve()
            == bindings["config_path"],
            Path(str(value.get("run_packet_path") or "")).resolve()
            == bindings["run_packet_path"],
        )
    )


def _generation_selection_valid(value: Mapping[str, Any]) -> bool:
    generation = value.get("generation")
    revision = str(value.get("generation_revision") or "")
    issued = value.get("selection_issued_at")
    expires = value.get("selection_expires_at")
    return all(
        (
            type(generation) is int and generation > 0,
            len(revision) == 64
            and all(char in "0123456789abcdef" for char in revision),
            type(issued) is int,
            type(expires) is int,
            expires - issued == 30,
            _sha256_digest(value.get("owner_config_id")),
        )
    )


def _absolute_outside_repo(value: object, root: Path) -> bool:
    text = str(value)
    if "\x00" in text or text.startswith(("\\\\?\\", "//?/")):
        return False
    try:
        path = Path(text)
        resolved = path.resolve()
    except Exception:
        return False
    return path.is_absolute() and resolved != root and root not in resolved.parents


def _number_text(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return str(int(number)) if number.is_integer() else str(number)


def _canonical(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _digest(payload: Mapping[str, Any]) -> str:
    return _text_digest(_canonical(payload))


def _text_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _ascii_text(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and all(ord(char) < 128 for char in value)
    )


def _ascii_deep(value: object) -> bool:
    if isinstance(value, str):
        return all(ord(char) < 128 for char in value)
    if isinstance(value, Mapping):
        return all(
            isinstance(key, str)
            and all(ord(char) < 128 for char in key)
            and _ascii_deep(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return all(_ascii_deep(item) for item in value)
    return value is None or isinstance(value, (bool, int, float))


def _sha256_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 71
        and value.startswith("sha256:")
        and all(char in "0123456789abcdef" for char in value[7:])
        and value[7:] != "0" * 64
    )


__all__ = [
    "signer_generation_bound_selection_valid",
    "signer_profile_bindings_valid",
    "signer_run_packet_bindings_valid",
    "signer_run_packet_static_valid",
    "signer_run_packet_selection_valid",
]
