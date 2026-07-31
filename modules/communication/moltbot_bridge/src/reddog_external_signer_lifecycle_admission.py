"""Opaque admission for one externally supervised RedDog signer instance."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol
from weakref import WeakKeyDictionary

from modules.communication.moltbot_bridge.src.reddog_external_signer_os_observer import (
    ExternalSignerOsObservationPolicy,
    ExternalSignerOsObservationReceipt,
    ExternalSignerOsPolicyAuthorityBoundary,
    observe_external_signer_os_state,
    verify_external_signer_os_observation_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_launch_selection import (
    RuntimeArtifactManifestLaunchSelectionBoundary,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    is_sha256,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    SignerRuntimeGenerationActivation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_reader import (
    SignerRuntimeGenerationReaderAuthorityBoundary,
    require_signer_runtime_generation_reader_authority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_healthcheck import (
    SignerServiceHealthcheckResult,
    run_reddog_signer_socket_service_healthcheck,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_text,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)

_DEFAULT_OS_OBSERVER = observe_external_signer_os_state
_DEFAULT_HEALTHCHECK_RUNNER = run_reddog_signer_socket_service_healthcheck


class ExternalSignerLifecycleAdmissionError(RuntimeError):
    """Fail-closed lifecycle admission failure."""


@dataclass(frozen=True)
class ExternalSignerLifecycleAdmissionReceipt:
    """Audit evidence only; this receipt cannot authorize an effect."""

    manifest_id: str
    artifact_generation_digest: str
    generation: int
    generation_revision: str
    config_digest: str
    config_raw_digest: str
    run_packet_digest: str
    run_packet_id: str
    session_id: str
    os_observation_receipt_id: str
    os_policy_authority_receipt_id: str
    pid: int
    process_start_identity: str
    socket_device: int
    socket_inode: int
    handshake_request_digest: str
    handshake_response_digest: str
    admitted_at_epoch: int
    admitted_monotonic_ns: int
    handshake_expires_at: int
    receipt_id: str
    authority_granted: bool = False
    valve_unlocked: bool = False
    effect_capability_issued: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExternalSignerLifecycleAdmissionBoundary(Protocol):
    def admit(
        self,
        manifest_selection: object,
    ) -> object: ...

    def consume(
        self, value: object
    ) -> ExternalSignerLifecycleAdmissionReceipt: ...


class _Boundary:
    __slots__ = ("_admit", "_consume")

    def __init__(self, admit: Any, consume: Any) -> None:
        self._admit, self._consume = admit, consume

    def admit(self, value: object, **kwargs: Any) -> object:
        return self._admit(value, **kwargs)

    def consume(
        self, value: object, **kwargs: Any
    ) -> ExternalSignerLifecycleAdmissionReceipt:
        return self._consume(value, **kwargs)


def create_external_signer_lifecycle_admission_boundary(
    *,
    repo_root: Path | str,
    manifest_boundary: RuntimeArtifactManifestLaunchSelectionBoundary,
    generation_reader_authority: object,
    generation_reader_authority_boundary: (
        SignerRuntimeGenerationReaderAuthorityBoundary
    ),
    os_policy_authority: object,
    os_policy_authority_boundary: ExternalSignerOsPolicyAuthorityBoundary,
    requester_principal_id: str,
    signer_profile_id: str = "reddog-work-authority",
    os_observer: Callable[..., ExternalSignerOsObservationReceipt] = (
        _DEFAULT_OS_OBSERVER
    ),
    healthcheck_runner: Callable[..., SignerServiceHealthcheckResult] = (
        _DEFAULT_HEALTHCHECK_RUNNER
    ),
    trusted_clock: Callable[[], int] | None = None,
    trusted_monotonic_clock: Callable[[], int] | None = None,
) -> ExternalSignerLifecycleAdmissionBoundary:
    """Create a one-shot boundary pinned to trusted lifecycle dependencies."""
    root = Path(repo_root).resolve()
    verified_policy = _verified_os_policy(
        os_policy_authority, os_policy_authority_boundary
    )
    seal = object()
    issued: WeakKeyDictionary[object, str] = WeakKeyDictionary()
    capability_type = _capability_type(seal)
    generation_reader = require_signer_runtime_generation_reader_authority(
        generation_reader_authority,
        generation_reader_authority_boundary,
    )
    _require_read_only_generation_reader(generation_reader)
    dependencies = {
        "root": root,
        "manifest_boundary": manifest_boundary,
        "generation_anchor": generation_reader,
        "requester": requester_principal_id,
        "profile": signer_profile_id,
        "observer": os_observer,
        "healthcheck": healthcheck_runner,
        "clock": trusted_clock or (lambda: int(time.time())),
        "monotonic_clock": trusted_monotonic_clock or time.monotonic_ns,
        "os_policy": verified_policy.policy,
        "os_policy_authority_receipt_id": verified_policy.authority_receipt_id,
    }
    return _Boundary(
        _make_admit(dependencies, capability_type, issued),
        _make_consume(
            capability_type,
            seal,
            issued,
            dependencies["clock"],
            dependencies["monotonic_clock"],
        ),
    )


def _require_read_only_generation_reader(value: object) -> None:
    forbidden = (
        "activate",
        "advance",
        "authenticate",
        "commit",
        "prepare",
        "recover",
        "sign",
    )
    if (
        not callable(getattr(value, "load", None))
        or any(callable(getattr(value, name, None)) for name in forbidden)
        or hasattr(value, "_signer")
    ):
        raise ValueError("external_signer_generation_reader_invalid")


def _verified_os_policy(
    authority: object,
    boundary: ExternalSignerOsPolicyAuthorityBoundary,
) -> Any:
    verified = boundary.require(authority)
    if (
        not isinstance(verified.policy, ExternalSignerOsObservationPolicy)
        or not is_sha256(verified.authority_receipt_id)
        or not str(verified.authority_source_id)
    ):
        raise ValueError("external_signer_os_policy_authority_invalid")
    return verified


def _make_admit(
    dependencies: Mapping[str, Any],
    capability_type: type,
    issued: WeakKeyDictionary[object, str],
) -> Any:
    def admit(
        selection_capability: object,
    ) -> object:
        try:
            values = _verified_admission_values(
                dependencies, selection_capability
            )
        except Exception as exc:
            raise ExternalSignerLifecycleAdmissionError(
                "external_signer_lifecycle_rejected"
            ) from exc
        capability = capability_type(values)
        issued[capability] = _digest(values)
        return capability

    return admit


def _make_consume(
    capability_type: type,
    seal: object,
    issued: WeakKeyDictionary[object, str],
    clock: Callable[[], int],
    monotonic_clock: Callable[[], int],
) -> Any:
    def consume(value: object) -> ExternalSignerLifecycleAdmissionReceipt:
        if not isinstance(value, capability_type):
            raise ExternalSignerLifecycleAdmissionError(
                "external_signer_lifecycle_unverified"
            )
        expected = issued.pop(value, None)
        values = object.__getattribute__(value, "_values")
        now_epoch = _trusted_now(clock)
        now_monotonic_ns = _trusted_monotonic_now(monotonic_clock)
        valid = (
            object.__getattribute__(value, "_seal") is seal
            and expected == _digest(values)
            and values["admitted_at_epoch"] <= now_epoch
            and now_epoch < values["handshake_expires_at"]
            and values["admitted_monotonic_ns"] <= now_monotonic_ns
        )
        if not valid:
            raise ExternalSignerLifecycleAdmissionError(
                "external_signer_lifecycle_unverified"
            )
        return ExternalSignerLifecycleAdmissionReceipt(
            **dict(values), receipt_id=_digest(values)
        )

    return consume


def _verified_admission_values(
    dependencies: Mapping[str, Any],
    selection_capability: object,
) -> Mapping[str, Any]:
    now_epoch = _trusted_now(dependencies["clock"])
    admitted_monotonic_ns = _trusted_monotonic_now(
        dependencies["monotonic_clock"]
    )
    selected = dependencies["manifest_boundary"].consume(selection_capability)
    os_policy = dependencies["os_policy"]
    activation = dependencies["generation_anchor"].load()
    packet = _selected_artifacts(dependencies["root"], selected)
    _validate_generation(selected, activation)
    _validate_policy_packet(os_policy, packet, selected)
    observation = dependencies["observer"](
        os_policy, observed_at_epoch=now_epoch
    )
    verify_external_signer_os_observation_receipt(observation)
    _validate_observation_packet(observation, packet, now_epoch)
    health = dependencies["healthcheck"](
        repo_root=dependencies["root"],
        run_packet_path=selected["run_packet_path"],
        requester_principal_id=dependencies["requester"],
        signer_profile_id=dependencies["profile"],
        now_epoch=lambda: now_epoch,
        manifest_id=selected["manifest_id"],
        artifact_generation_digest=selected["artifact_generation_digest"],
    )
    return _admission_values(
        selected, packet, activation, observation, health,
        dependencies["requester"], dependencies["profile"], now_epoch,
        dependencies["os_policy_authority_receipt_id"],
        admitted_monotonic_ns,
    )


def _capability_type(seal: object) -> type:
    class Capability:
        __slots__ = ("_values", "_seal", "__weakref__")

        def __init__(self, values: Mapping[str, Any]) -> None:
            object.__setattr__(self, "_values", MappingProxyType(dict(values)))
            object.__setattr__(self, "_seal", seal)

        def __setattr__(self, name: str, value: Any) -> None:
            del name, value
            raise AttributeError("external_signer_lifecycle_immutable")

        def __copy__(self):
            raise TypeError("external_signer_lifecycle_not_copyable")

        def __deepcopy__(self, memo: Any):
            del memo
            raise TypeError("external_signer_lifecycle_not_copyable")

        def __reduce__(self):
            raise TypeError("external_signer_lifecycle_not_serializable")

    return Capability


def _selected_artifacts(
    root: Path, selection: Mapping[str, Any]
) -> Mapping[str, Any]:
    if Path(str(selection.get("repo_root") or "")).resolve() != root:
        raise ValueError("external_signer_repo_root_mismatch")
    runtime = validate_runtime_root_path(selection["runtime_root"], repo_root=root)
    path = validate_runtime_artifact_path(
        selection["run_packet_path"], repo_root=root, allowed_root=runtime
    )
    raw = secure_read_confined_text(path, allowed_root=runtime, max_bytes=256 * 1024)
    if _text_digest(raw) != selection["run_packet_digest"]:
        raise ValueError("external_signer_run_packet_changed")
    packet = json.loads(raw)
    if not isinstance(packet, Mapping):
        raise ValueError("external_signer_run_packet_invalid")
    config_path = validate_runtime_artifact_path(
        selection["config_path"], repo_root=root, allowed_root=runtime
    )
    config_raw = secure_read_confined_text(
        config_path, allowed_root=runtime, max_bytes=256 * 1024
    )
    if _text_digest(config_raw) != selection["config_raw_digest"]:
        raise ValueError("external_signer_config_changed")
    return packet


def _validate_generation(
    selected: Mapping[str, Any],
    activation: SignerRuntimeGenerationActivation | None,
) -> None:
    if activation is None or any(
        getattr(activation, field) != selected[field]
        for field in (
            "manifest_id",
            "artifact_generation_digest",
            "config_digest",
            "config_raw_digest",
            "run_packet_digest",
        )
    ):
        raise ValueError("external_signer_generation_mismatch")


def _validate_policy_packet(
    policy: ExternalSignerOsObservationPolicy,
    packet: Mapping[str, Any],
    selected: Mapping[str, Any],
) -> None:
    argv = packet.get("argv")
    expected_cmdline = _argv_cmdline_bytes(argv)
    if (
        not isinstance(argv, list)
        or not argv
        or policy.socket_path != str(packet.get("socket_path") or "")
        or policy.expected_executable != str(argv[0])
        or not expected_cmdline
        or str(packet.get("config_digest") or "") != selected["config_digest"]
    ):
        raise ValueError("external_signer_process_policy_mismatch")


def _validate_observation_packet(
    observation: ExternalSignerOsObservationReceipt,
    packet: Mapping[str, Any],
    now_epoch: int,
) -> None:
    expected_cmdline = _argv_cmdline_bytes(packet.get("argv"))
    if (
        observation.observed_at_epoch != now_epoch
        or observation.cmdline_digest != _bytes_digest(expected_cmdline)
        or observation.cmdline_size_bytes != len(expected_cmdline)
    ):
        raise ValueError("external_signer_process_observation_mismatch")


def _admission_values(
    selected: Mapping[str, Any],
    packet: Mapping[str, Any],
    activation: SignerRuntimeGenerationActivation,
    observation: ExternalSignerOsObservationReceipt,
    health: SignerServiceHealthcheckResult,
    requester_principal_id: str,
    signer_profile_id: str,
    now_epoch: int,
    os_policy_authority_receipt_id: str,
    admitted_monotonic_ns: int,
) -> Mapping[str, Any]:
    valid = _admission_bindings_valid(
        selected, packet, observation, health,
        requester_principal_id, signer_profile_id, now_epoch,
    )
    if not valid:
        raise ValueError("external_signer_handshake_rejected")
    return _admission_payload(
        selected, packet, activation, observation, health,
        os_policy_authority_receipt_id, now_epoch, admitted_monotonic_ns,
    )


def _admission_bindings_valid(
    selected: Mapping[str, Any],
    packet: Mapping[str, Any],
    observation: ExternalSignerOsObservationReceipt,
    health: SignerServiceHealthcheckResult,
    requester_principal_id: str,
    signer_profile_id: str,
    now_epoch: int,
) -> bool:
    return all(
        (
            type(now_epoch) is int,
            health.accepted is True,
            health.peer_handshake_verified is True,
            type(health.peer_handshake_expires_at) is int
            and health.peer_handshake_expires_at > now_epoch,
            health.manifest_id == selected["manifest_id"],
            health.artifact_generation_digest
            == selected["artifact_generation_digest"],
            health.run_packet_id == packet.get("run_packet_id"),
            health.run_packet_path == selected["run_packet_path"],
            health.config_path == selected["config_path"],
            health.config_digest == selected["config_digest"],
            health.socket_path == observation.socket_path,
            health.requester_principal_id == requester_principal_id,
            health.signer_profile_id == signer_profile_id,
            is_sha256(health.request_digest),
            is_sha256(health.response_digest),
            bool(str(packet.get("session_id") or "")),
        )
    )


def _admission_payload(
    selected: Mapping[str, Any],
    packet: Mapping[str, Any],
    activation: SignerRuntimeGenerationActivation,
    observation: ExternalSignerOsObservationReceipt,
    health: SignerServiceHealthcheckResult,
    os_policy_authority_receipt_id: str,
    admitted_at_epoch: int,
    admitted_monotonic_ns: int,
) -> Mapping[str, Any]:
    return {
        "manifest_id": selected["manifest_id"],
        "artifact_generation_digest": selected["artifact_generation_digest"],
        "generation": activation.generation,
        "generation_revision": activation.revision,
        "config_digest": selected["config_digest"],
        "config_raw_digest": selected["config_raw_digest"],
        "run_packet_digest": selected["run_packet_digest"],
        "run_packet_id": health.run_packet_id,
        "session_id": str(packet["session_id"]),
        "os_observation_receipt_id": observation.receipt_id,
        "os_policy_authority_receipt_id": os_policy_authority_receipt_id,
        "pid": observation.pid,
        "process_start_identity": observation.process_start_identity,
        "socket_device": observation.socket_device,
        "socket_inode": observation.socket_inode,
        "handshake_request_digest": str(health.request_digest),
        "handshake_response_digest": str(health.response_digest),
        "admitted_at_epoch": admitted_at_epoch,
        "admitted_monotonic_ns": admitted_monotonic_ns,
        "handshake_expires_at": health.peer_handshake_expires_at,
    }


def _trusted_now(clock: Callable[[], int]) -> int:
    value = clock()
    if type(value) is not int or value <= 0:
        raise ValueError("external_signer_time_invalid")
    return value


def _trusted_monotonic_now(clock: Callable[[], int]) -> int:
    value = clock()
    if type(value) is not int or value < 0:
        raise ValueError("external_signer_monotonic_time_invalid")
    return value


def _argv_cmdline_bytes(value: object) -> bytes:
    if (
        not isinstance(value, list)
        or not value
        or any(
            not isinstance(item, str)
            or not item
            or "\x00" in item
            or any(ord(char) >= 128 for char in item)
            for item in value
        )
    ):
        return b""
    return b"\x00".join(item.encode("ascii") for item in value) + b"\x00"


def _bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _text_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _digest(value: Mapping[str, Any]) -> str:
    raw = json.dumps(
        dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return _text_digest(raw)


__all__ = [
    "ExternalSignerLifecycleAdmissionBoundary",
    "ExternalSignerLifecycleAdmissionError",
    "ExternalSignerLifecycleAdmissionReceipt",
    "create_external_signer_lifecycle_admission_boundary",
]
