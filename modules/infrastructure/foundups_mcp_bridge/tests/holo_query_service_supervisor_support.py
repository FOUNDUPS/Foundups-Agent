"""Tests for the host-owned HoloIndex query-service lifecycle boundary."""

from __future__ import annotations

import json

import http.client

import math

import os

import socket

import subprocess

import sys

import threading

import time

from collections import UserDict

from collections.abc import Mapping

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pathlib import Path

from types import MappingProxyType

from typing import Any

from unittest.mock import Mock

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    holo_query_owner_health as health_module,
    holo_query_service_supervisor as supervisor_module,
)

from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service_supervisor import (
    DEFAULT_OWNER_PROBE_TIMEOUT_SECONDS,
    DEFAULT_OWNER_STARTUP_PROBE_TIMEOUT_SECONDS,
    HEALTH_SCHEMA_VERSION,
    OWNER_HOST,
    OWNER_MODULE,
    SERVICE_TOKEN_ENV,
    SERVICE_URL_ENV,
    HoloQueryServiceSupervisor,
    HoloQueryServiceSupervisorError,
)

TOKEN = "x" * 64

REPLICA_BINDING = ("descriptor", "generation", "replica", "path")

_RawHoloQueryServiceSupervisor = HoloQueryServiceSupervisor

class _TupleBinding(tuple):
    pass

class _StringField(str):
    pass

class _HostileField:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def __bool__(self) -> bool:
        self.calls.append("__bool__")
        raise AssertionError("hostile bool called")

    def __str__(self) -> str:
        self.calls.append("__str__")
        raise AssertionError("hostile str called")

    def __eq__(self, _other: object) -> bool:
        self.calls.append("__eq__")
        raise AssertionError("hostile equality called")

class _HostileTransport:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def _called(self, name: str) -> Any:
        self.calls.append(name)
        raise AssertionError(f"hostile transport {name} called")

    def __bool__(self) -> bool: return self._called("__bool__")
    def __str__(self) -> str: return self._called("__str__")
    def __int__(self) -> int: return self._called("__int__")
    def __float__(self) -> float: return self._called("__float__")
    def __eq__(self, _other: object) -> bool: return self._called("__eq__")

class _HostileReplicaExpectation:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def _called(self, name: str) -> Any:
        self.calls.append(name)
        raise AssertionError(f"hostile replica expectation {name} called")

    def __len__(self) -> int: return self._called("__len__")
    def __iter__(self) -> Any: return self._called("__iter__")
    def __bool__(self) -> bool: return self._called("__bool__")
    def __str__(self) -> str: return self._called("__str__")
    def __eq__(self, _other: object) -> bool: return self._called("__eq__")

class _TransportString(str):
    def __str__(self) -> str: raise AssertionError("string subclass converted")

class _TransportInt(int):
    def __int__(self) -> int: raise AssertionError("int subclass converted")

class _TransportFloat(float):
    def __float__(self) -> float: raise AssertionError("float subclass converted")

def _invalid_transport_value(kind: str, calls: list[str]) -> object:
    values: dict[str, object] = {
        "hostile": _HostileTransport(calls), "str-subclass": _TransportString("x"),
        "int-subclass": _TransportInt(8127), "float-subclass": _TransportFloat(1.0),
        "bool": True, "bytes": b"x", "none": None, "mapping": {"x": 1},
        "generator": (item for item in (1,)), "empty": "", "whitespace": " ",
        "control": "x\n", "short": "x" * 31, "ipv6": "::1",
        "localhost": "localhost", "spaced-host": " 127.0.0.1 ",
        "control-host": "127.0.0.1\n", "zero": 0, "negative": -1,
        "port-over": 65536, "nan": math.nan, "inf": math.inf,
        "negative-inf": -math.inf, "huge": 301.0,
    }
    return values[kind]

def _invalid_replica_expectation(kind: str, calls: list[str]) -> object:
    values: dict[str, object] = {
        "string": "abcd", "list": ["a", "b", "c", "d"],
        "tuple-subclass": _TupleBinding(("a", "b", "c", "d")),
        "hostile": _HostileReplicaExpectation(calls),
        "partial": ("a", "b", "c"), "bytes": b"abcd",
        "mapping": {"a": 1, "b": 2, "c": 3, "d": 4},
        "generator": (item for item in ("a", "b", "c", "d")),
        "bool-element": (True, "b", "c", "d"),
        "whitespace": (" ", "b", "c", "d"),
        "empty": ("", "b", "c", "d"),
        "over": ("a", "b", "c", "d", "e"),
    }
    return values[kind]

class _HostileDict(dict[str, object]):
    def __init__(self, calls: list[str]) -> None:
        dict.__init__(self)
        self.calls = calls
        dict.__setitem__(self, "repo_head_sha", _HostileField(calls))

    def _called(self, name: str) -> Any:
        self.calls.append(name)
        raise AssertionError(f"hostile container {name} called")

    def get(self, *_args: Any, **_kwargs: Any) -> Any:
        return self._called("get")

    def items(self) -> Any:
        return self._called("items")

    def keys(self) -> Any:
        return self._called("keys")

    def values(self) -> Any:
        return self._called("values")

    def __iter__(self) -> Any:
        return self._called("__iter__")

    def __contains__(self, _item: object) -> bool:
        return self._called("__contains__")

    def __len__(self) -> int:
        return self._called("__len__")

    def __bool__(self) -> bool:
        return self._called("__bool__")

    def __str__(self) -> str:
        return self._called("__str__")

    def __repr__(self) -> str:
        return self._called("__repr__")

    def __eq__(self, _other: object) -> bool:
        return self._called("__eq__")

class _HostileMapping(Mapping[str, object]):
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def _called(self, name: str) -> Any:
        self.calls.append(name)
        raise AssertionError(f"hostile mapping {name} called")

    def __getitem__(self, _key: str) -> object:
        return self._called("__getitem__")

    def __iter__(self) -> Any:
        return self._called("__iter__")

    def __len__(self) -> int:
        return self._called("__len__")

def _malformed_health_container(kind: str) -> tuple[object, list[str]]:
    calls: list[str] = []
    values: dict[str, object] = {
        "dict-subclass": _HostileDict(calls),
        "mapping": _HostileMapping(calls),
        "user-dict": UserDict({"repo_head_sha": _HostileField(calls)}),
        "mapping-proxy": MappingProxyType({"repo_head_sha": _HostileField(calls)}),
        "list": [_HostileField(calls)],
        "string": "health",
        "object": object(),
    }
    return values[kind], calls

def _ready_health_payload(
    *, replica_binding: tuple[str, str, str, str],
) -> dict[str, object]:
    return {
        "schema_version": HEALTH_SCHEMA_VERSION,
        "ok": True,
        "source": "holoindex",
        "status": "ready",
        "loopback_only": True,
        "freshness": "CURRENT",
        "error": "",
        "stale_reasons": [],
        "index_gap_detected": False,
        "no_holoindex_reindex_performed": True,
        "retrieval_mode": "semantic",
        "repo_head_sha": "a" * 40,
        "repo_root_digest": "sha256:" + ("d" * 64),
        "freshness_generation_id": "sha256:" + ("b" * 64),
        "freshness_receipt_digest": "sha256:" + ("c" * 64),
        "query_replica_descriptor_digest": replica_binding[0],
        "query_replica_generation_id": replica_binding[1],
        "query_replica_id": replica_binding[2],
        "query_replica_path_identity_digest": replica_binding[3],
    }

def _health_json_body_with_prefix(prefix: str) -> bytes:
    payload = json.dumps(
        _ready_health_payload(replica_binding=REPLICA_BINDING),
        separators=(",", ":"),
    )
    return ("{" + prefix + payload[1:]).encode("utf-8")

def _duplicate_health_key_body(key: str) -> bytes:
    payload = _ready_health_payload(replica_binding=REPLICA_BINDING)
    pair = json.dumps(key) + ":" + json.dumps(payload[key]) + ","
    return _health_json_body_with_prefix(pair)

def _install_health_json_response(
    monkeypatch: pytest.MonkeyPatch, body: bytes, *, status: int = 200,
) -> list[tuple[object, ...]]:
    events: list[tuple[object, ...]] = []

    class Response:
        def read(self, limit: int) -> bytes:
            events.append(("read", limit))
            return body

    class Connection:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            events.append(("connect",))

        def request(self, method: str, path: str, **_kwargs: Any) -> None:
            events.append(("request", method, path))

        def getresponse(self) -> Response:
            events.append(("getresponse",))
            response = Response()
            response.status = status  # type: ignore[attr-defined]
            return response

        def close(self) -> None:
            events.append(("close",))

    monkeypatch.setattr(health_module.http.client, "HTTPConnection", Connection)
    return events

def _install_health_transport_failure(
    monkeypatch: pytest.MonkeyPatch, *, stage: str = "", failure: Exception | None = None,
    close_failure: Exception | None = None,
) -> list[str]:
    events: list[str] = []
    body = json.dumps(
        _ready_health_payload(replica_binding=REPLICA_BINDING)
    ).encode("utf-8")

    class Response:
        status = 200

        def read(self, _limit: int) -> bytes:
            events.append("read")
            if stage == "read" and failure is not None:
                raise failure
            return body

    class Connection:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            events.append("connect")

        def request(self, *_args: Any, **_kwargs: Any) -> None:
            events.append("request")
            if stage == "request" and failure is not None:
                raise failure

        def getresponse(self) -> Response:
            events.append("getresponse")
            if stage == "getresponse" and failure is not None:
                raise failure
            return Response()

        def close(self) -> None:
            events.append("close")
            if close_failure is not None:
                raise close_failure

    monkeypatch.setattr(health_module.http.client, "HTTPConnection", Connection)
    return events

def _exchange_health_json() -> health_module.AuthenticatedOwnerHealthProof:
    return health_module._authenticated_health_exchange(
        host=OWNER_HOST, port=8127, token=TOKEN, timeout_seconds=1.0,
        expected_replica_binding=REPLICA_BINDING,
    )

def _assert_complete_health_exchange(events: list[tuple[object, ...]]) -> None:
    assert [event[0] for event in events] == [
        "connect", "request", "getresponse", "read", "close",
    ]
    assert events[1] == ("request", "GET", health_module.HEALTH_PATH)
    assert events[3] == ("read", health_module.MAX_HEALTH_RESPONSE_BYTES + 1)

def HoloQueryServiceSupervisor(  # type: ignore[misc]
    *, repo_root: Path | str, **kwargs: Any,
) -> _RawHoloQueryServiceSupervisor:
    """Build the explicit full synthetic route used by lifecycle tests."""

    root = Path(repo_root)
    kwargs.setdefault("canonical_ssd_path", root / "canonical")
    kwargs.setdefault("query_replica_root", root / "replica")
    kwargs.setdefault("replica_capability_verifier", lambda: object())
    kwargs.setdefault("expected_replica_binding", REPLICA_BINDING)
    return _RawHoloQueryServiceSupervisor(repo_root=root, **kwargs)

@pytest.fixture(autouse=True)
def _available_owner_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        supervisor_module,
        "_owner_port_available",
        lambda _host, _port: True,
    )

class _FakeProcess:
    def __init__(
        self,
        *,
        returncode: int | None = None,
        wait_timeouts: int = 0,
    ) -> None:
        self.returncode = returncode
        self.wait_timeouts = wait_timeouts
        self.wait_calls = 0
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def wait(self, *, timeout: float) -> int:
        del timeout
        self.wait_calls += 1
        if self.wait_calls <= self.wait_timeouts:
            raise subprocess.TimeoutExpired("owner", 1)
        self.returncode = -9 if self.killed else 0
        return self.returncode

def _successful_health_proof(
    launch: dict[str, Any], kwargs: dict[str, Any],
) -> supervisor_module.AuthenticatedOwnerHealthProof:
    launch.setdefault("probe_timeouts", []).append(kwargs["timeout_seconds"])
    launch.setdefault("probe_bindings", []).append(
        (
            kwargs["expected_repo_head_sha"],
            kwargs["expected_repo_root_digest"],
            kwargs["expected_generation_id"],
            kwargs["expected_receipt_digest"],
        )
    )
    return supervisor_module.AuthenticatedOwnerHealthProof(
        ready=kwargs["token"] == TOKEN,
        rejection="",
        binding=(
            kwargs["expected_repo_head_sha"] or ("a" * 40),
            kwargs["expected_repo_root_digest"] or ("sha256:" + ("d" * 64)),
            kwargs["expected_generation_id"] or ("sha256:" + ("b" * 64)),
            kwargs["expected_receipt_digest"] or ("sha256:" + ("c" * 64)),
        ),
        replica_binding=kwargs.get("expected_replica_binding", ("", "", "", "")),
    )


def _install_successful_start(
    monkeypatch: pytest.MonkeyPatch, process: _FakeProcess,
) -> dict[str, Any]:
    launch: dict[str, Any] = {}

    def fake_popen(command: list[str], **kwargs: Any) -> _FakeProcess:
        launch["command"] = list(command)
        launch["kwargs"] = {**kwargs, "env": dict(kwargs["env"])}
        return process

    monkeypatch.setattr(supervisor_module.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        supervisor_module,
        "_owner_port_available",
        lambda _host, _port: True,
    )

    monkeypatch.setattr(
        supervisor_module,
        "_authenticated_health_exchange",
        lambda **kwargs: _successful_health_proof(launch, kwargs),
    )
    monkeypatch.setattr(
        supervisor_module.secrets,
        "token_urlsafe",
        lambda _bytes: TOKEN,
    )
    return launch

_INVALID_TRANSPORT_CASES = [
    *(("host", kind) for kind in (
        "hostile", "str-subclass", "bool", "bytes", "none", "mapping",
        "generator", "empty", "ipv6", "localhost", "spaced-host", "control-host",
    )),
    *(("token", kind) for kind in (
        "hostile", "str-subclass", "bool", "bytes", "none", "mapping",
        "generator", "empty", "whitespace", "control", "short",
    )),
    *(("port", kind) for kind in (
        "hostile", "int-subclass", "bool", "bytes", "none", "mapping",
        "generator", "zero", "negative", "port-over", "nan", "inf",
    )),
    *(("timeout_seconds", kind) for kind in (
        "hostile", "int-subclass", "float-subclass", "bool", "bytes", "none",
        "mapping", "generator", "zero", "negative", "nan", "inf",
        "negative-inf", "huge",
    )),
]

def _binding_health_handler(
    observed_authorization: list[str] | None = None,
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if observed_authorization is not None:
                observed_authorization.append(self.headers.get("Authorization", ""))
            payload = json.dumps(
                {
                    "schema_version": HEALTH_SCHEMA_VERSION,
                    "ok": True,
                    "source": "holoindex",
                    "status": "ready",
                    "loopback_only": True,
                    "freshness": "CURRENT",
                    "error": "",
                    "stale_reasons": [],
                    "index_gap_detected": False,
                    "no_holoindex_reindex_performed": True,
                    "retrieval_mode": "semantic",
                    "repo_head_sha": "a" * 40,
                    "repo_root_digest": "sha256:" + ("d" * 64),
                    "freshness_generation_id": "sha256:generation",
                    "freshness_receipt_digest": "sha256:receipt",
                    "query_replica_descriptor_digest": REPLICA_BINDING[0],
                    "query_replica_generation_id": REPLICA_BINDING[1],
                    "query_replica_id": REPLICA_BINDING[2],
                    "query_replica_path_identity_digest": REPLICA_BINDING[3],
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_args: object) -> None:
            return

    return Handler


def _slow_semantic_health_handler() -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802
            time.sleep(1.1)
            body = json.dumps(
                _ready_health_payload(replica_binding=REPLICA_BINDING)
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler

__all__ = [name for name in globals() if not name.startswith("__")]
