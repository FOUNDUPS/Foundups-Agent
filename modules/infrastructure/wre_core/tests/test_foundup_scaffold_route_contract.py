#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adversarial tests for immutable create-scaffold route snapshots."""

from __future__ import annotations

import ast
import logging
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.infrastructure.wre_core.src.foundup_job_router import (
    RouteReasonCode,
    RouteStatus,
    route_foundup_job,
)
from modules.infrastructure.wre_core.src import (
    foundup_job_route_decision,
    foundup_job_router,
    foundup_scaffold_route_contract,
)
from modules.infrastructure.wre_core.src.foundup_scaffold_route_contract import (
    CreateScaffoldRequest,
)


def _job() -> SimpleNamespace:
    return SimpleNamespace(
        job_id="job_create_alpha",
        tenant_id="tenant@example",
        requested_action="create_foundup",
        status="queued",
        foundup_id="alpha_widget",
        creation_mode="new_scaffold",
        genesis_envelope_digest="sha256:" + ("a" * 64),
        scaffold_contract_digest="sha256:" + ("b" * 64),
        policy_flags={"dry_run_mode": True},
        payload={
            "genesis_envelope": {
                "foundup_id": "alpha_widget",
                "nested": {"criteria": ["A"]},
            }
        },
    )


def test_route_freezes_canonical_request_and_detaches_nested_state() -> None:
    job = _job()

    route = route_foundup_job(job)
    request = route.scaffold_request
    assert route.route_status == RouteStatus.ROUTED
    assert isinstance(request, CreateScaffoldRequest)

    job.foundup_id = "beta_widget"
    job.genesis_envelope_digest = "sha256:" + ("c" * 64)
    job.payload["genesis_envelope"]["foundup_id"] = "beta_widget"
    job.payload["genesis_envelope"]["nested"]["criteria"].append("B")

    assert request.foundup_id == "alpha_widget"
    assert request.genesis_envelope_digest == "sha256:" + ("a" * 64)
    assert request.genesis_envelope["nested"]["criteria"] == ["A"]
    assert route.foundup_id == "alpha_widget"

    first = route.to_dict()
    first["scaffold_request"]["genesis_envelope"]["nested"]["criteria"].append(
        "receipt mutation"
    )
    assert route.to_dict()["scaffold_request"]["genesis_envelope"]["nested"][
        "criteria"
    ] == ["A"]

    with pytest.raises(FrozenInstanceError):
        route.foundup_id = "mutated"


@pytest.mark.parametrize(
    ("field_name", "unsafe_value"),
    [
        ("job_id", "../job"),
        ("job_id", "job/name"),
        ("job_id", "job\x00name"),
        ("job_id", "job\u0085name"),
        ("job_id", "job\u202ename"),
        ("tenant_id", "..\\tenant"),
        ("tenant_id", "tenant\nname"),
        ("tenant_id", "tenant\u2066name"),
        ("tenant_id", "tenant\u200fname"),
        ("foundup_id", "../alpha"),
        ("foundup_id", "alpha/name"),
        ("foundup_id", "alpha\x7fname"),
    ],
)
def test_create_route_rejects_traversal_and_control_identifiers(
    field_name: str,
    unsafe_value: str,
) -> None:
    job = _job()
    setattr(job, field_name, unsafe_value)
    if field_name == "foundup_id":
        job.payload["genesis_envelope"]["foundup_id"] = unsafe_value

    route = route_foundup_job(job)

    assert route.route_status == RouteStatus.BLOCKED
    assert route.scaffold_request is None
    assert ".." not in route.reason_human
    assert "\x00" not in route.reason_human


def test_nonserializable_genesis_fails_closed_without_raw_value() -> None:
    job = _job()
    job.payload["genesis_envelope"]["secret"] = object()

    route = route_foundup_job(job)

    assert route.route_status == RouteStatus.BLOCKED
    assert route.reason_human == "create_foundup request could not be canonicalized"
    assert route.scaffold_request is None


def test_router_internal_failure_redacts_exception_and_logs_only_stable_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class ExplodingJob:
        @property
        def job_id(self) -> str:
            raise RuntimeError("secret-path-and-token")

    with caplog.at_level(logging.ERROR, logger="wre_foundup_job_router"):
        route = route_foundup_job(ExplodingJob())

    assert route.route_status == RouteStatus.FAILED
    assert route.reason_code == RouteReasonCode.FAIL_INTERNAL
    assert route.reason_human == "Internal routing error"
    assert "secret-path-and-token" not in caplog.text
    assert "secret-path-and-token" not in str(route.to_dict())


def _function_span(module: object, function_name: str) -> int:
    path = Path(module.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    )
    return function.end_lineno - function.lineno + 1


def test_freeze_entrypoint_stays_below_wsp62_function_limit() -> None:
    assert _function_span(
        foundup_scaffold_route_contract,
        "freeze_create_scaffold_request",
    ) <= 75


def test_public_router_and_extracted_decision_functions_are_bounded() -> None:
    assert _function_span(foundup_job_router, "route_foundup_job") <= 75
    path = Path(foundup_job_route_decision.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    spans = {
        node.name: node.end_lineno - node.lineno + 1
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    assert spans
    assert max(spans.values()) <= 75
