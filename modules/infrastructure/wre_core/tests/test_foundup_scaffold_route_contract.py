#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adversarial tests for immutable create-scaffold route snapshots."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest

from modules.infrastructure.wre_core.src.foundup_job_router import (
    RouteStatus,
    route_foundup_job,
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
        ("tenant_id", "..\\tenant"),
        ("tenant_id", "tenant\nname"),
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
