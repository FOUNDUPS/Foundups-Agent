"""Adversarial tests for external signer lifecycle admission."""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import pickle
import stat
import types
from dataclasses import replace
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_external_signer_lifecycle_admission import (
    ExternalSignerLifecycleAdmissionError,
    create_external_signer_lifecycle_admission_boundary,
)
from modules.communication.moltbot_bridge.src import (
    reddog_external_signer_lifecycle_admission as lifecycle_module,
)
from modules.communication.moltbot_bridge.src.reddog_external_signer_os_observer import (
    EXTERNAL_SIGNER_OS_OBSERVATION_SCHEMA_VERSION,
    ExternalSignerOsObservationPolicy,
    ExternalSignerOsObservationReceipt,
    VerifiedExternalSignerOsPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    SignerRuntimeGenerationActivation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_healthcheck import (
    SIGNER_SERVICE_HEALTHCHECK_READY,
    SignerServiceHealthcheckResult,
)
from modules.communication.moltbot_bridge.tests.reddog_signer_generation_test_support import (
    create_lifecycle_generation_authority,
)


NOW = 2_000_000_000
SOCKET = "/run/foundups/reddog-signer.sock"
EXECUTABLE = "/usr/bin/python3.12"


def _sha(char: str) -> str:
    return "sha256:" + char * 64


class _SelectionBoundary:
    def __init__(self, values: dict[str, object]) -> None:
        self.values = values
        self.consumed = False

    def consume(self, value: object) -> dict[str, object]:
        if value is not self or self.consumed:
            raise ValueError("selection_unverified")
        self.consumed = True
        return dict(self.values)


class _Anchor:
    def __init__(self, activation: SignerRuntimeGenerationActivation) -> None:
        self.activation = activation

    def load(self) -> SignerRuntimeGenerationActivation:
        return self.activation


class _WriterAnchor(_Anchor):
    def activate(self) -> None:
        raise AssertionError("must not be called")


class _SigningAnchor(_Anchor):
    def sign(self) -> None:
        raise AssertionError("must not be called")


class _ReaderBoundary:
    def __init__(self, reader: _Anchor) -> None:
        self.reader = reader

    def require(self, value: object) -> _Anchor:
        if value is not self:
            raise ValueError("generation_reader_authority_unverified")
        return self.reader


class _Observer:
    def __init__(self, receipt: ExternalSignerOsObservationReceipt) -> None:
        self.receipt = receipt
        self.calls = 0

    def __call__(self, policy, *, observed_at_epoch):
        assert isinstance(policy, ExternalSignerOsObservationPolicy)
        assert observed_at_epoch == NOW
        self.calls += 1
        return self.receipt


class _Healthcheck:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls = 0

    def __call__(self, **kwargs):
        assert kwargs["now_epoch"]() == NOW
        assert kwargs["manifest_id"] == _sha("1")
        assert kwargs["artifact_generation_digest"] == _sha("2")
        self.calls += 1
        return self.result


class _Clocks:
    def __init__(self) -> None:
        self.wall_value: object = NOW
        self.monotonic_value: object = 1000

    def wall(self) -> int:
        return self.wall_value  # type: ignore[return-value]

    def monotonic(self) -> int:
        return self.monotonic_value  # type: ignore[return-value]


class _PolicyBoundary:
    def require(self, value: object) -> VerifiedExternalSignerOsPolicy:
        if value is not self:
            raise ValueError("policy_authority_unverified")
        return VerifiedExternalSignerOsPolicy(
            policy=_policy(),
            authority_receipt_id=_sha("6"),
            authority_source_id="external-supervisor:test",
        )


def _cmdline() -> bytes:
    return b"\x00".join(
        item.encode("ascii") for item in (EXECUTABLE, "-m", "signer")
    ) + b"\x00"


def _runtime(tmp_path: Path) -> tuple[Path, Path, dict[str, object]]:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    runtime.mkdir()
    packet_path = runtime / "signer_service_run_packet.json"
    packet = {
        "run_packet_id": _sha("7"),
        "config_digest": _sha("3"),
        "session_id": "session-unique-1",
        "socket_path": SOCKET,
        "argv": [EXECUTABLE, "-m", "signer"],
    }
    raw = json.dumps(packet, sort_keys=True, separators=(",", ":"))
    packet_path.write_text(raw, encoding="utf-8")
    config_path = runtime / "signer_service_config.json"
    config_raw = '{"profiles":[]}'
    config_path.write_text(config_raw, encoding="utf-8")
    values: dict[str, object] = {
        "manifest_id": _sha("1"),
        "artifact_generation_digest": _sha("2"),
        "config_digest": _sha("3"),
        "config_raw_digest": _text_digest(config_raw),
        "run_packet_digest": _text_digest(raw),
        "repo_root": str(repo.resolve()),
        "runtime_root": str(runtime.resolve()),
        "config_path": str(config_path.resolve()),
        "run_packet_path": str(packet_path.resolve()),
    }
    return repo, packet_path, values


def _activation(values: dict[str, object]) -> SignerRuntimeGenerationActivation:
    return SignerRuntimeGenerationActivation(
        anchor_id="reddog-signer:production",
        generation=1,
        manifest_id=str(values["manifest_id"]),
        artifact_generation_digest=str(values["artifact_generation_digest"]),
        config_digest=str(values["config_digest"]),
        config_raw_digest=str(values["config_raw_digest"]),
        run_packet_digest=str(values["run_packet_digest"]),
        previous_revision=None,
        authenticator_id="signer-mac:v1",
        high_water_store_id="signer-high-water:v1",
        high_water_durability_receipt_id=_sha("8"),
        authentication_tag="mac",
        revision="9" * 64,
    )


def _policy() -> ExternalSignerOsObservationPolicy:
    return ExternalSignerOsObservationPolicy(
        pid=4242,
        expected_signer_uid=1201,
        expected_signer_gid=1202,
        requester_uid=1000,
        requester_gid=1000,
        expected_executable=EXECUTABLE,
        expected_executable_device=8,
        expected_executable_inode=101,
        socket_path=SOCKET,
        expected_socket_uid=1201,
        expected_socket_gid=1202,
        expected_socket_mode=0o600,
        expected_process_start_identity=(
            "11111111-2222-3333-4444-555555555555:987654"
        ),
    )


def _observation(
    *, cmdline: bytes | None = None
) -> ExternalSignerOsObservationReceipt:
    observed_cmdline = _cmdline() if cmdline is None else cmdline
    payload: dict[str, object] = {
        "schema_version": EXTERNAL_SIGNER_OS_OBSERVATION_SCHEMA_VERSION,
        "pid": 4242,
        "process_uid": 1201,
        "process_gid": 1202,
        "process_state": "S",
        "process_start_ticks": 987654,
        "boot_id": "11111111-2222-3333-4444-555555555555",
        "process_start_identity": (
            "11111111-2222-3333-4444-555555555555:987654"
        ),
        "executable_path": EXECUTABLE,
        "executable_device": 8,
        "executable_inode": 101,
        "cmdline_digest": _bytes_digest(observed_cmdline),
        "cmdline_size_bytes": len(observed_cmdline),
        "socket_path": SOCKET,
        "socket_uid": 1201,
        "socket_gid": 1202,
        "socket_mode": stat.S_IMODE(stat.S_IFSOCK | 0o600),
        "socket_device": 9,
        "socket_inode": 202,
        "socket_owned_by_process": True,
        "observed_at_epoch": NOW,
        "kernel_observed": True,
        "raw_cmdline_persisted": False,
        "authority_granted": False,
        "valve_unlocked": False,
    }
    return ExternalSignerOsObservationReceipt(
        **payload, receipt_id=_mapping_digest(payload)
    )


def _health(packet_path: Path) -> SignerServiceHealthcheckResult:
    return SignerServiceHealthcheckResult(
        accepted=True,
        status=SIGNER_SERVICE_HEALTHCHECK_READY,
        run_packet_path=str(packet_path),
        run_packet_id=_sha("7"),
        config_path=str(packet_path.with_name("signer_service_config.json")),
        config_digest=_sha("3"),
        socket_path=SOCKET,
        signer_profile_id="reddog-work-authority",
        signer_public_key="ed25519:public",
        requester_principal_id="github:mjtrout",
        request_digest=_sha("b"),
        response_digest=_sha("c"),
        rejection_reasons=(),
        manifest_id=_sha("1"),
        artifact_generation_digest=_sha("2"),
        peer_handshake_verified=True,
        peer_handshake_expires_at=NOW + 30,
    )


def _boundary(tmp_path: Path, **changes):
    repo, packet_path, values = _runtime(tmp_path)
    selection = _SelectionBoundary(values)
    observer = changes.get("observer", _Observer(_observation()))
    health_result = replace(
        _health(packet_path), **changes.get("health_changes", {})
    )
    healthcheck = changes.get("healthcheck", _Healthcheck(health_result))
    generation_authority, reader_boundary = create_lifecycle_generation_authority(
        repo, values
    )
    clocks = changes.get("clocks", _Clocks())
    policy_boundary = _PolicyBoundary()
    boundary = create_external_signer_lifecycle_admission_boundary(
        repo_root=repo,
        manifest_boundary=selection,
        generation_reader_authority=generation_authority,
        generation_reader_authority_boundary=reader_boundary,
        os_policy_authority=policy_boundary,
        os_policy_authority_boundary=policy_boundary,
        requester_principal_id="github:mjtrout",
        os_observer=observer,
        healthcheck_runner=healthcheck,
        trusted_clock=clocks.wall,
        trusted_monotonic_clock=clocks.monotonic,
    )
    return boundary, selection, observer, healthcheck, values, packet_path, clocks


def _reachable_objects(root: object) -> tuple[object, ...]:
    stack = [root]
    seen: set[int] = set()
    found: list[object] = []
    while stack:
        value = stack.pop()
        if id(value) in seen or isinstance(
            value, (str, bytes, int, float, bool, type(None), Path, type)
        ):
            continue
        seen.add(id(value))
        found.append(value)
        if isinstance(value, dict):
            stack.extend(value.values())
        elif isinstance(value, (list, tuple, set, frozenset)):
            stack.extend(value)
        if isinstance(value, types.FunctionType) and value.__closure__:
            stack.extend(cell.cell_contents for cell in value.__closure__)
        namespace = getattr(value, "__dict__", None)
        if isinstance(namespace, dict):
            stack.extend(namespace.values())
        for cls in type(value).__mro__:
            slots = cls.__dict__.get("__slots__", ())
            for name in (slots,) if isinstance(slots, str) else slots:
                try:
                    stack.append(object.__getattribute__(value, name))
                except (AttributeError, TypeError):
                    pass
    return tuple(found)


def test_exact_generation_os_and_handshake_issue_one_shot_capability(tmp_path) -> None:
    boundary, selection, observer, healthcheck, _, _, clocks = _boundary(tmp_path)
    capability = boundary.admit(selection)
    clocks.wall_value = NOW + 1
    clocks.monotonic_value = 1001

    receipt = boundary.consume(capability)

    assert receipt.manifest_id == _sha("1")
    assert receipt.generation == 1
    assert receipt.pid == 4242
    assert receipt.handshake_request_digest == _sha("b")
    assert receipt.authority_granted is False
    assert receipt.valve_unlocked is False
    assert receipt.effect_capability_issued is False
    assert observer.calls == healthcheck.calls == 1
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        boundary.consume(capability)


def test_lifecycle_boundary_cannot_be_retargeted_after_construction(
    tmp_path,
) -> None:
    boundary, selection, *_ = _boundary(tmp_path)

    for field in ("_admit", "_consume"):
        with pytest.raises(AttributeError):
            setattr(boundary, field, lambda *_args, **_kwargs: object())
        with pytest.raises(AttributeError):
            object.__setattr__(
                boundary, field, lambda *_args, **_kwargs: object()
            )
    assert not hasattr(lifecycle_module, "_issue_boundary")
    assert not hasattr(lifecycle_module, "_lookup_boundary")
    assert boundary.admit(selection) is not None


def test_lifecycle_public_api_rejects_registry_injection(tmp_path) -> None:
    boundary, selection, *_ = _boundary(tmp_path)

    factory_parameters = inspect.signature(
        create_external_signer_lifecycle_admission_boundary
    ).parameters
    assert "_issue" not in factory_parameters
    assert "_lookup" not in inspect.signature(boundary.admit).parameters
    assert "_lookup" not in inspect.signature(boundary.consume).parameters
    with pytest.raises(TypeError):
        boundary.admit(selection, _lookup=lambda _value: (object(), object()))


def test_canonical_lifecycle_graph_has_no_signer_or_writer_capability(
    tmp_path,
) -> None:
    boundary, *_ = _boundary(tmp_path)
    forbidden = {
        "activate",
        "advance",
        "authenticate",
        "commit",
        "commit_prepared",
        "prepare",
        "private_key",
        "sign",
    }

    for value in _reachable_objects(boundary):
        for name in forbidden:
            try:
                inspect.getattr_static(value, name)
            except AttributeError:
                continue
            pytest.fail(
                f"forbidden capability {name} reachable on "
                f"{type(value).__name__}"
            )


def test_capability_cannot_be_copied_pickled_or_forged(tmp_path) -> None:
    boundary, selection, *_ = _boundary(tmp_path)
    capability = boundary.admit(selection)

    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(TypeError):
            operation(capability)
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        boundary.consume(object())


def test_caller_cannot_supply_an_unverified_os_policy(tmp_path) -> None:
    repo, _, values = _runtime(tmp_path)
    policy_boundary = _PolicyBoundary()

    with pytest.raises(ValueError, match="policy_authority_unverified"):
        generation_authority, reader_boundary = create_lifecycle_generation_authority(
            repo, values
        )
        create_external_signer_lifecycle_admission_boundary(
            repo_root=repo,
            manifest_boundary=_SelectionBoundary(values),
            generation_reader_authority=generation_authority,
            generation_reader_authority_boundary=reader_boundary,
            os_policy_authority=object(),
            os_policy_authority_boundary=policy_boundary,
            requester_principal_id="github:mjtrout",
            trusted_clock=_Clocks().wall,
        )


def test_writer_generation_anchor_cannot_be_smuggled_into_lifecycle(tmp_path) -> None:
    repo, _, values = _runtime(tmp_path)
    reader_boundary = _ReaderBoundary(_WriterAnchor(_activation(values)))
    policy_boundary = _PolicyBoundary()

    with pytest.raises(ValueError, match="authority_boundary_invalid"):
        create_external_signer_lifecycle_admission_boundary(
            repo_root=repo,
            manifest_boundary=_SelectionBoundary(values),
            generation_reader_authority=reader_boundary,
            generation_reader_authority_boundary=reader_boundary,
            os_policy_authority=policy_boundary,
            os_policy_authority_boundary=policy_boundary,
            requester_principal_id="github:mjtrout",
            trusted_clock=_Clocks().wall,
        )


def test_signing_reader_cannot_be_smuggled_into_lifecycle(tmp_path) -> None:
    repo, _, values = _runtime(tmp_path)
    reader_boundary = _ReaderBoundary(_SigningAnchor(_activation(values)))
    policy_boundary = _PolicyBoundary()

    with pytest.raises(ValueError, match="authority_boundary_invalid"):
        create_external_signer_lifecycle_admission_boundary(
            repo_root=repo,
            manifest_boundary=_SelectionBoundary(values),
            generation_reader_authority=reader_boundary,
            generation_reader_authority_boundary=reader_boundary,
            os_policy_authority=policy_boundary,
            os_policy_authority_boundary=policy_boundary,
            requester_principal_id="reddog-host",
        )


def test_stale_generation_rejects_before_observation_or_handshake(tmp_path) -> None:
    repo, packet_path, values = _runtime(tmp_path)
    selection = _SelectionBoundary(values)
    observer = _Observer(_observation())
    healthcheck = _Healthcheck(_health(packet_path))
    generation_authority, reader_boundary = create_lifecycle_generation_authority(
        repo,
        values,
        manifest_id=_sha("d"),
    )
    policy_boundary = _PolicyBoundary()
    boundary = create_external_signer_lifecycle_admission_boundary(
        repo_root=repo,
        manifest_boundary=selection,
        generation_reader_authority=generation_authority,
        generation_reader_authority_boundary=reader_boundary,
        os_policy_authority=policy_boundary,
        os_policy_authority_boundary=policy_boundary,
        requester_principal_id="github:mjtrout",
        os_observer=observer,
        healthcheck_runner=healthcheck,
        trusted_clock=_Clocks().wall,
    )

    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        boundary.admit(selection)

    assert observer.calls == healthcheck.calls == 0


def test_packet_tampering_rejects_before_observation(tmp_path) -> None:
    boundary, selection, observer, healthcheck, _, packet_path, _ = _boundary(tmp_path)
    packet_path.write_text('{"attacker":true}', encoding="utf-8")

    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        boundary.admit(selection)

    assert observer.calls == healthcheck.calls == 0


def test_config_tampering_rejects_before_observation(tmp_path) -> None:
    boundary, selection, observer, healthcheck, values, _, _ = _boundary(tmp_path)
    Path(str(values["config_path"])).write_text(
        '{"profiles":["attacker"]}', encoding="utf-8"
    )

    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        boundary.admit(selection)

    assert observer.calls == healthcheck.calls == 0


def test_full_process_argv_must_match_selected_run_packet(tmp_path) -> None:
    attacker = _observation(
        cmdline=_cmdline().replace(b"signer\x00", b"attacker\x00")
    )
    boundary, selection, observer, healthcheck, *_ = _boundary(
        tmp_path, observer=_Observer(attacker)
    )

    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        boundary.admit(selection)

    assert observer.calls == 1
    assert healthcheck.calls == 0


def test_tampered_os_receipt_rejects_before_handshake(tmp_path) -> None:
    observation = replace(_observation(), socket_inode=999)
    healthcheck = _Healthcheck(object())
    boundary, selection, observer, _, _, _, _ = _boundary(
        tmp_path,
        observer=_Observer(observation),
        healthcheck=healthcheck,
    )

    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        boundary.admit(selection)

    assert observer.calls == 1
    assert healthcheck.calls == 0


@pytest.mark.parametrize(
    "change",
    [
        {"accepted": False},
        {"peer_handshake_verified": False},
        {"peer_handshake_expires_at": NOW},
        {"config_digest": _sha("f")},
        {"socket_path": "/run/attacker.sock"},
        {"requester_principal_id": "github:attacker"},
        {"signer_profile_id": "attacker-profile"},
        {"config_path": "/run/attacker-config.json"},
        {"run_packet_path": "/run/attacker-packet.json"},
        {"request_digest": None},
        {"response_digest": None},
        {"manifest_id": _sha("e")},
        {"artifact_generation_digest": _sha("e")},
    ],
)
def test_incomplete_or_mismatched_handshake_rejects(
    tmp_path, change: dict[str, object]
) -> None:
    boundary, selection, *_ = _boundary(
        tmp_path, health_changes=change
    )

    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        boundary.admit(selection)


def test_expired_capability_is_consumed_and_cannot_be_replayed(tmp_path) -> None:
    boundary, selection, *_, clocks = _boundary(tmp_path)
    capability = boundary.admit(selection)
    clocks.wall_value = NOW + 30
    clocks.monotonic_value = 1030

    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        boundary.consume(capability)


@pytest.mark.parametrize(
    ("wall_value", "monotonic_value"),
    [(NOW - 1, 1001), (NOW + 1, 999)],
)
def test_clock_rollback_cannot_revive_lifecycle_admission(
    tmp_path, wall_value: int, monotonic_value: int
) -> None:
    boundary, selection, *_, clocks = _boundary(tmp_path)
    capability = boundary.admit(selection)
    clocks.wall_value = wall_value
    clocks.monotonic_value = monotonic_value

    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        boundary.consume(capability)


@pytest.mark.parametrize("clock_value", [0, -1, True, "2000000000"])
def test_untrusted_or_malformed_clock_fails_closed(
    tmp_path, clock_value: object
) -> None:
    clocks = _Clocks()
    clocks.wall_value = clock_value
    boundary, selection, observer, healthcheck, *_ = _boundary(
        tmp_path, clocks=clocks
    )

    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        boundary.admit(selection)

    assert observer.calls == healthcheck.calls == 0


def _mapping_digest(value: dict[str, object]) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return _text_digest(raw)


def _text_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()
