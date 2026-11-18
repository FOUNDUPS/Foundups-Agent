"""Configuration and binding-adversarial RedDog owner-bootstrap tests."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from .reddog_holoindex_owner_bootstrap_support import (
    REPLICA_BINDING,
    SAFE_TOKEN,
    SAFE_URL,
    REAL_CONFIGURED_HEALTH,
    REAL_ENSURE_OWNER,
    REAL_VERIFY_OWNER,
    _FakeReplicaRoute,
    _FakeSupervisor,
    _clean_owner_state,
    _full_route,
    bootstrap,
    configured,
    HoloQueryServiceSupervisorError,
    SERVICE_TOKEN_ENV,
    SERVICE_URL_ENV,
)


def test_not_requested_has_no_process_or_environment_side_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bootstrap,
        "HoloQueryServiceSupervisor",
        Mock(side_effect=AssertionError("must not start")),
    )

    result = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=False,
    )

    assert result.status == bootstrap.OWNER_NOT_REQUESTED
    assert result.ready is False
    assert SERVICE_URL_ENV not in os.environ
    assert SERVICE_TOKEN_ENV not in os.environ


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8127",
        "http://127.0.0.1",
        "http://127.0.0.1:8127/holoindex/v1/query",
        "http://127.0.0.1:8127/holoindex/v1/query/",
    ],
)
def test_explicit_loopback_service_bypasses_auto_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    url: str,
) -> None:
    monkeypatch.setenv(SERVICE_URL_ENV, url)
    monkeypatch.setenv(SERVICE_TOKEN_ENV, SAFE_TOKEN)
    constructor = Mock(side_effect=AssertionError("configured service must win"))
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", constructor)

    result = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
    )

    assert result.ready is True
    assert result.status == bootstrap.OWNER_CONFIGURED
    assert bootstrap.resolve_reddog_holoindex_owner_handoff() is None
    constructor.assert_not_called()


def test_configured_owner_without_replica_route_fails_before_health_or_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(SERVICE_URL_ENV, SAFE_URL)
    monkeypatch.setenv(SERVICE_TOKEN_ENV, SAFE_TOKEN)
    health = Mock(side_effect=AssertionError("missing route must fail before health"))
    constructor = Mock(side_effect=AssertionError("missing route must fail before start"))
    monkeypatch.setattr(bootstrap, "_configured_owner_health_ready", health)
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", constructor)

    result = REAL_ENSURE_OWNER(
        repo_root=tmp_path,
        requested=True,
    )

    assert result.ready is False
    assert result.status == bootstrap.OWNER_FAILED
    assert result.error == "HOLOINDEX_QUERY_REPLICA_REQUIRED"
    health.assert_not_called()
    constructor.assert_not_called()


def test_malformed_and_partial_replica_routes_fail_closed_before_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructor = Mock(side_effect=AssertionError("invalid route must not start"))
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", constructor)

    class MalformedRoute:
        def revalidate(self) -> object:
            return object()

    for route in (
        MalformedRoute(),
        _FakeReplicaRoute(
            tmp_path, ("descriptor", "", "replica", "path")
        ),
        _FakeReplicaRoute(
            tmp_path, ["descriptor", "generation", "replica", "path"]
        ),
    ):
        result = REAL_ENSURE_OWNER(
            repo_root=tmp_path,
            requested=True,
            query_replica_route=route,  # type: ignore[arg-type]
        )
        assert result.ready is False
        assert result.error == bootstrap.QUERY_REPLICA_INVALID_ERROR

    constructor.assert_not_called()


def test_verify_without_replica_route_fails_before_configured_health(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    health = Mock(side_effect=AssertionError("missing route must not probe"))
    monkeypatch.setattr(bootstrap, "_configured_owner_health_ready", health)

    assert not REAL_VERIFY_OWNER(
        repo_root=tmp_path,
        expected_repo_head_sha="a" * 40,
        expected_generation_id="sha256:" + ("b" * 64),
        expected_receipt_digest="sha256:" + ("c" * 64),
    )
    health.assert_not_called()


def test_verify_binding_uses_configured_owner_health_without_starting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(SERVICE_URL_ENV, SAFE_URL)
    monkeypatch.setenv(SERVICE_TOKEN_ENV, SAFE_TOKEN)
    health = Mock(return_value=True)
    monkeypatch.setattr(bootstrap, "_configured_owner_health_ready", health)

    assert bootstrap.verify_reddog_holoindex_owner_binding(
        repo_root=tmp_path,
        expected_repo_head_sha="a" * 40,
        expected_generation_id="sha256:" + ("b" * 64),
        expected_receipt_digest="sha256:" + ("c" * 64),
    )

    health.assert_called_once_with(
        service_url=SAFE_URL,
        token=SAFE_TOKEN,
        expected_repo_head_sha="a" * 40,
        expected_repo_root_digest=bootstrap.repository_root_digest(tmp_path),
        expected_generation_id="sha256:" + ("b" * 64),
        expected_receipt_digest="sha256:" + ("c" * 64),
        expected_replica_binding=REPLICA_BINDING,
    )


def test_verify_binding_rejects_owned_owner_serving_another_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "HoloQueryServiceSupervisor", _FakeSupervisor)
    started = bootstrap.ensure_reddog_holoindex_owner(
        repo_root=tmp_path,
        requested=True,
        expected_repo_head_sha="a" * 40,
        expected_generation_id="sha256:" + ("b" * 64),
        expected_receipt_digest="sha256:" + ("c" * 64),
    )
    assert started.ready is True

    assert not bootstrap.verify_reddog_holoindex_owner_binding(
        repo_root=tmp_path,
        expected_repo_head_sha="a" * 40,
        expected_generation_id="sha256:" + ("d" * 64),
        expected_receipt_digest="sha256:" + ("c" * 64),
    )


def test_configured_health_wrapper_uses_authenticated_loopback_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = Mock(return_value=True)
    monkeypatch.setattr(bootstrap, "_authenticated_health_probe", probe)

    assert REAL_CONFIGURED_HEALTH(
        service_url="http://127.0.0.1:9127/holoindex/v1/query",
        token=SAFE_TOKEN,
        expected_replica_binding=REPLICA_BINDING,
    )

    probe.assert_called_once_with(
        host="127.0.0.1",
        port=9127,
        token=SAFE_TOKEN,
        timeout_seconds=bootstrap.CONFIGURED_HEALTH_TIMEOUT_SECONDS,
        expected_replica_binding=REPLICA_BINDING,
    )


def test_final_binding_probe_allows_bounded_semantic_canary_latency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[float] = []

    def probe(**kwargs) -> bool:
        observed.append(float(kwargs["timeout_seconds"]))
        return kwargs["timeout_seconds"] >= 1.1

    monkeypatch.setattr(bootstrap, "_authenticated_health_probe", probe)

    assert REAL_CONFIGURED_HEALTH(
        service_url=SAFE_URL,
        token=SAFE_TOKEN,
        expected_repo_head_sha="a" * 40,
        expected_generation_id="sha256:" + ("b" * 64),
        expected_receipt_digest="sha256:" + ("c" * 64),
        expected_replica_binding=REPLICA_BINDING,
    )
    assert observed == [bootstrap.CONFIGURED_HEALTH_TIMEOUT_SECONDS]
    assert observed[0] == bootstrap.DEFAULT_OWNER_PROBE_TIMEOUT_SECONDS


def test_private_handoff_uses_binding_proven_during_supervisor_startup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    health = Mock(side_effect=AssertionError("handoff must not rerun semantic health"))
    monkeypatch.setattr(bootstrap, "_configured_owner_health_ready", health)
    supervisor = _FakeSupervisor(repo_root=tmp_path, ssd_path=tmp_path)
    supervisor.start(
        expected_repo_head_sha="a" * 40,
        expected_repo_root_digest="sha256:" + ("d" * 64),
        expected_generation_id="sha256:" + ("b" * 64),
        expected_receipt_digest="sha256:" + ("c" * 64),
        expected_replica_binding=REPLICA_BINDING,
    )

    handoff = bootstrap._validated_owner_handoff(
        supervisor,
        expected_repo_head_sha="a" * 40,
        expected_repo_root_digest="sha256:" + ("d" * 64),
        expected_generation_id="sha256:" + ("b" * 64),
        expected_receipt_digest="sha256:" + ("c" * 64),
        expected_replica_binding=REPLICA_BINDING,
    )

    assert handoff == (SAFE_URL, SAFE_TOKEN)
    health.assert_not_called()


def test_private_handoff_fails_closed_when_supervisor_proved_another_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    health = Mock(side_effect=AssertionError("handoff must not rerun semantic health"))
    monkeypatch.setattr(bootstrap, "_configured_owner_health_ready", health)
    supervisor = _FakeSupervisor(repo_root=tmp_path, ssd_path=tmp_path)
    supervisor.start(
        expected_repo_head_sha="d" * 40,
        expected_repo_root_digest="sha256:" + ("a" * 64),
        expected_generation_id="sha256:" + ("e" * 64),
        expected_receipt_digest="sha256:" + ("f" * 64),
        expected_replica_binding=REPLICA_BINDING,
    )

    with pytest.raises(HoloQueryServiceSupervisorError) as exc_info:
        bootstrap._validated_owner_handoff(
            supervisor,
            expected_repo_head_sha="a" * 40,
            expected_repo_root_digest="sha256:" + ("d" * 64),
            expected_generation_id="sha256:" + ("b" * 64),
            expected_receipt_digest="sha256:" + ("c" * 64),
            expected_replica_binding=REPLICA_BINDING,
        )

    assert exc_info.value.code == bootstrap.CONFIGURED_UNREADY_ERROR
    health.assert_not_called()


def test_private_handoff_rejects_partial_expected_replica_binding(
    tmp_path: Path,
) -> None:
    supervisor = _FakeSupervisor(repo_root=tmp_path, ssd_path=tmp_path)
    supervisor.start(expected_replica_binding=REPLICA_BINDING)

    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        bootstrap._validated_owner_handoff(
            supervisor,
            expected_replica_binding=("descriptor", "", "replica", "path"),
        )

    assert error.value.code == "HOLOINDEX_QUERY_REPLICA_REQUIRED"


def test_private_handoff_rejects_malformed_binding_before_reading_handoff(
    tmp_path: Path,
) -> None:
    supervisor = _FakeSupervisor(repo_root=tmp_path, ssd_path=tmp_path)
    supervisor.environment_for_child = Mock(
        side_effect=AssertionError("malformed binding must fail before handoff")
    )

    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        bootstrap._validated_owner_handoff(
            supervisor,
            expected_replica_binding=[
                "descriptor", "generation", "replica", "path",
            ],  # type: ignore[arg-type]
        )

    assert error.value.code == "HOLOINDEX_QUERY_REPLICA_REQUIRED"
    supervisor.environment_for_child.assert_not_called()


def test_private_handoff_rejects_hostile_expected_canonical_before_read(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    class Hostile:
        def __bool__(self) -> bool:
            calls.append("__bool__")
            raise AssertionError("hostile bool called")

        def __str__(self) -> str:
            calls.append("__str__")
            raise AssertionError("hostile str called")

        def __eq__(self, _other: object) -> bool:
            calls.append("__eq__")
            raise AssertionError("hostile equality called")

    supervisor = _FakeSupervisor(repo_root=tmp_path, ssd_path=tmp_path)
    supervisor.environment_for_child = Mock(
        side_effect=AssertionError("invalid expected binding read handoff")
    )

    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        bootstrap._validated_owner_handoff(
            supervisor,
            expected_repo_head_sha=Hostile(),  # type: ignore[arg-type]
            expected_replica_binding=REPLICA_BINDING,
        )

    assert error.value.code == bootstrap.BINDING_MISMATCH_ERROR
    assert calls == []
    supervisor.environment_for_child.assert_not_called()


def test_private_handoff_rejects_hostile_verified_canonical_before_read(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    class Hostile:
        def __bool__(self) -> bool:
            calls.append("__bool__")
            raise AssertionError("hostile bool called")

        def __str__(self) -> str:
            calls.append("__str__")
            raise AssertionError("hostile str called")

        def __eq__(self, _other: object) -> bool:
            calls.append("__eq__")
            raise AssertionError("hostile equality called")

    supervisor = _FakeSupervisor(repo_root=tmp_path, ssd_path=tmp_path)
    supervisor.started = True
    supervisor.verified_binding = (Hostile(), "root", "generation", "receipt")  # type: ignore[assignment]
    supervisor.verified_replica_binding = REPLICA_BINDING
    supervisor.environment_for_child = Mock(
        side_effect=AssertionError("invalid verified binding read handoff")
    )

    with pytest.raises(HoloQueryServiceSupervisorError) as error:
        bootstrap._validated_owner_handoff(
            supervisor,
            expected_replica_binding=REPLICA_BINDING,
        )

    assert error.value.code == bootstrap.CONFIGURED_UNREADY_ERROR
    assert calls == []
    supervisor.environment_for_child.assert_not_called()


def test_configured_owner_rejects_malformed_binding_before_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    health = Mock(side_effect=AssertionError("malformed binding must not probe"))
    monkeypatch.setattr(bootstrap, "_authenticated_health_probe", health)

    assert not REAL_CONFIGURED_HEALTH(
        service_url=SAFE_URL,
        token=SAFE_TOKEN,
        expected_replica_binding="abcd",  # type: ignore[arg-type]
    )
    health.assert_not_called()


def test_configured_owner_rejects_hostile_canonical_before_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class Hostile:
        def __bool__(self) -> bool:
            calls.append("__bool__")
            raise AssertionError("hostile bool called")

        def __str__(self) -> str:
            calls.append("__str__")
            raise AssertionError("hostile str called")

        def __eq__(self, _other: object) -> bool:
            calls.append("__eq__")
            raise AssertionError("hostile equality called")

    health = Mock(side_effect=AssertionError("invalid canonical must not probe"))
    monkeypatch.setattr(bootstrap, "_authenticated_health_probe", health)

    assert not REAL_CONFIGURED_HEALTH(
        service_url=SAFE_URL,
        token=SAFE_TOKEN,
        expected_repo_head_sha=Hostile(),  # type: ignore[arg-type]
        expected_replica_binding=REPLICA_BINDING,
    )
    assert calls == []
    health.assert_not_called()


def test_requested_binding_rejects_hostile_before_repository_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class Hostile:
        def __bool__(self) -> bool:
            calls.append("__bool__")
            raise AssertionError("hostile bool called")

        def __str__(self) -> str:
            calls.append("__str__")
            raise AssertionError("hostile str called")

        def __eq__(self, _other: object) -> bool:
            calls.append("__eq__")
            raise AssertionError("hostile equality called")

    digest = Mock(side_effect=AssertionError("invalid binding hashed repository"))
    monkeypatch.setattr(configured, "repository_root_digest", digest)

    with pytest.raises(ValueError, match=bootstrap.BINDING_MISMATCH_ERROR):
        configured.requested_owner_binding(
            tmp_path, Hostile(), "generation", "receipt",  # type: ignore[arg-type]
        )

    assert calls == []
    digest.assert_not_called()


def test_route_start_kwargs_reject_hostile_canonical_without_methods() -> None:
    calls: list[str] = []

    class Hostile:
        def __bool__(self) -> bool:
            calls.append("__bool__")
            raise AssertionError("hostile bool called")

        def __str__(self) -> str:
            calls.append("__str__")
            raise AssertionError("hostile str called")

        def __eq__(self, _other: object) -> bool:
            calls.append("__eq__")
            raise AssertionError("hostile equality called")

    with pytest.raises(ValueError, match=bootstrap.BINDING_MISMATCH_ERROR):
        bootstrap.owner_start_binding_kwargs(
            (Hostile(), "root", "generation", "receipt"),  # type: ignore[arg-type]
            REPLICA_BINDING,
        )

    assert calls == []


def test_verify_and_ensure_reject_hostile_canonical_before_route(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    class Hostile:
        def __bool__(self) -> bool:
            calls.append("__bool__")
            raise AssertionError("hostile bool called")

        def __str__(self) -> str:
            calls.append("__str__")
            raise AssertionError("hostile str called")

        def __eq__(self, _other: object) -> bool:
            calls.append("__eq__")
            raise AssertionError("hostile equality called")

    route = _full_route(tmp_path)
    assert not REAL_VERIFY_OWNER(
        repo_root=tmp_path,
        expected_repo_head_sha=Hostile(),  # type: ignore[arg-type]
        expected_generation_id="generation",
        expected_receipt_digest="receipt",
        query_replica_route=route,  # type: ignore[arg-type]
    )
    result = REAL_ENSURE_OWNER(
        repo_root=tmp_path,
        requested=True,
        expected_repo_head_sha=Hostile(),  # type: ignore[arg-type]
        query_replica_route=route,  # type: ignore[arg-type]
    )

    assert result.ready is False
    assert result.error == bootstrap.BINDING_MISMATCH_ERROR
    assert route.revalidations == 0
    assert calls == []
