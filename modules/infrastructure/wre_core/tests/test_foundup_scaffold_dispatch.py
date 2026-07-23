#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Malformed-adapter containment tests for create_foundup dispatch."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from modules.infrastructure.wre_core.src.foundup_job_consumer import (
    FoundUpJobConsumer,
)
from modules.infrastructure.wre_core.src.foundup_job_router import (
    RouteEnvelope,
    RouteReasonCode,
    RouteStatus,
    TargetBackend,
)
from modules.infrastructure.wre_core.src.foundup_scaffold_adapter import (
    ScaffoldAdapterResult,
)
from modules.infrastructure.wre_core.src.foundup_scaffold_route_contract import (
    CreateScaffoldRequest,
    digest_scaffold_contract,
)
from modules.infrastructure.wre_core.src import (
    foundup_scaffold_adapter,
    foundup_scaffold_dispatch,
    foundup_scaffold_route_contract,
)


def _request_and_plan() -> tuple[CreateScaffoldRequest, dict]:
    genesis_digest = "sha256:" + ("a" * 64)
    contract = {
        "foundup_id": "alpha_widget",
        "genesis_envelope_digest": genesis_digest,
        "nested": {"evidence": ["A"]},
    }
    request = CreateScaffoldRequest(
        job_id="job-alpha",
        tenant_id="tenant-alpha",
        foundup_id="alpha_widget",
        creation_mode="new_scaffold",
        genesis_envelope_digest=genesis_digest,
        scaffold_contract_digest=digest_scaffold_contract(contract),
        genesis_envelope_json='{"foundup_id":"alpha_widget"}',
        request_digest="sha256:" + ("c" * 64),
    )
    plan = {
        "action": "create_foundup",
        "ok": True,
        "dry_run": True,
        "files_written": [],
        "fam_called": False,
        "hermes_called": False,
        "registry_mutated": False,
        "worktree_created": False,
        "scaffold_contract": contract,
    }
    return request, plan


def _route(request: CreateScaffoldRequest) -> RouteEnvelope:
    return RouteEnvelope(
        job_id=request.job_id,
        tenant_id=request.tenant_id,
        target_backend=TargetBackend.HERMES_SCAFFOLD,
        requested_action="create_foundup",
        route_status=RouteStatus.ROUTED,
        reason_code=RouteReasonCode.OK_ROUTED,
        reason_human="routed",
        foundup_id=request.foundup_id,
        creation_mode=request.creation_mode,
        genesis_envelope_digest=request.genesis_envelope_digest,
        scaffold_contract_digest=request.scaffold_contract_digest,
        scaffold_request=request,
    )


class _ValueAdapter:
    def __init__(self, value: Any) -> None:
        self.value = value

    def plan(self, request: CreateScaffoldRequest) -> Any:
        return self.value


@pytest.mark.parametrize("malformed", [None, {}, object()])
def test_wrong_type_adapter_results_become_stable_blocked_consumer_results(
    malformed: Any,
) -> None:
    request, _ = _request_and_plan()
    consumer = FoundUpJobConsumer(
        scaffold_adapter=_ValueAdapter(malformed),
    )

    result = consumer._dispatch_to_scaffold(_route(request))

    assert result.dispatched is False
    assert result.route_status == RouteStatus.BLOCKED
    assert result.checkpoint_blocker == "FAIL_SCAFFOLD_ADAPTER_RESULT"
    assert result.reason == "scaffold adapter returned an invalid result"
    assert "object at 0x" not in str(result.to_dict())


def test_raising_adapter_is_contained_and_exception_text_is_redacted() -> None:
    request, _ = _request_and_plan()

    class RaisingAdapter:
        def plan(self, request: CreateScaffoldRequest) -> ScaffoldAdapterResult:
            raise RuntimeError("secret-provider-path")

    result = FoundUpJobConsumer(
        scaffold_adapter=RaisingAdapter()
    )._dispatch_to_scaffold(_route(request))

    assert result.route_status == RouteStatus.BLOCKED
    assert result.checkpoint_blocker == "FAIL_SCAFFOLD_ADAPTER_EXCEPTION"
    assert "secret-provider-path" not in str(result.to_dict())


def test_nonserializable_adapter_evidence_is_contained() -> None:
    request, plan = _request_and_plan()
    adapter_result = ScaffoldAdapterResult(
        ok=True,
        reason_code="OK_SCAFFOLD_PLAN",
        reason_human="ok",
        plan=plan,
    )
    object.__setattr__(adapter_result, "plan", {"secret": object()})

    result = FoundUpJobConsumer(
        scaffold_adapter=_ValueAdapter(adapter_result)
    )._dispatch_to_scaffold(_route(request))

    assert result.route_status == RouteStatus.BLOCKED
    assert result.checkpoint_blocker == "FAIL_SCAFFOLD_ADAPTER_RESULT"
    assert result.scaffold_result is None


def test_raising_result_serializer_is_contained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, plan = _request_and_plan()
    adapter_result = ScaffoldAdapterResult(
        ok=True,
        reason_code="OK_SCAFFOLD_PLAN",
        reason_human="ok",
        plan=plan,
    )

    def _raise(_self: ScaffoldAdapterResult) -> dict:
        raise RuntimeError("secret-serializer-path")

    monkeypatch.setattr(ScaffoldAdapterResult, "to_dict", _raise)
    result = FoundUpJobConsumer(
        scaffold_adapter=_ValueAdapter(adapter_result)
    )._dispatch_to_scaffold(_route(request))

    assert result.route_status == RouteStatus.BLOCKED
    assert result.checkpoint_blocker == "FAIL_SCAFFOLD_ADAPTER_RESULT"
    assert "secret-serializer-path" not in str(result.to_dict())


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("identity", "FAIL_SCAFFOLD_FOUNDUP_MISMATCH"),
        ("genesis", "FAIL_GENESIS_LINEAGE_MISMATCH"),
        ("scaffold", "FAIL_SCAFFOLD_LINEAGE_MISMATCH"),
    ],
)
def test_returned_plan_must_match_frozen_request_identity_and_digests(
    mutation: str,
    expected_code: str,
) -> None:
    request, plan = _request_and_plan()
    if mutation == "identity":
        plan["scaffold_contract"]["foundup_id"] = "beta_widget"
    elif mutation == "genesis":
        plan["scaffold_contract"]["genesis_envelope_digest"] = (
            "sha256:" + ("f" * 64)
        )
    else:
        plan["scaffold_contract"]["nested"]["evidence"].append("tamper")
    adapter_result = ScaffoldAdapterResult(
        ok=True,
        reason_code="OK_SCAFFOLD_PLAN",
        reason_human="forged",
        plan=plan,
    )

    result = FoundUpJobConsumer(
        scaffold_adapter=_ValueAdapter(adapter_result)
    )._dispatch_to_scaffold(_route(request))

    assert result.route_status == RouteStatus.BLOCKED
    assert result.checkpoint_blocker == expected_code
    assert result.scaffold_result is None


def test_consumer_serialized_scaffold_receipts_are_detached() -> None:
    request, plan = _request_and_plan()
    result = FoundUpJobConsumer(
        scaffold_adapter=_ValueAdapter(
            ScaffoldAdapterResult(
                ok=True,
                reason_code="OK_SCAFFOLD_PLAN",
                reason_human="ok",
                plan=plan,
            )
        )
    )._dispatch_to_scaffold(_route(request))
    assert result.dispatched is True

    first = result.to_dict()
    first["scaffold_result"]["plan"]["scaffold_contract"]["nested"][
        "evidence"
    ].append("tamper")

    assert result.to_dict()["scaffold_result"]["plan"]["scaffold_contract"][
        "nested"
    ]["evidence"] == ["A"]


def test_create_boundary_imports_no_hermes_provider_fam_or_writer() -> None:
    imported: list[str] = []
    for module in (
        foundup_scaffold_adapter,
        foundup_scaffold_dispatch,
        foundup_scaffold_route_contract,
    ):
        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
                imported.extend(alias.name for alias in node.names)
    import_blob = " ".join(imported).lower()

    assert "hermes" not in import_blob
    assert "provider" not in import_blob
    assert "fam" not in import_blob
    assert "writer" not in import_blob
