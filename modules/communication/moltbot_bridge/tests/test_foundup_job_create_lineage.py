#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused FoundUpJob serialization contract for create_foundup lineage."""

from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    FoundUpJob,
    create_job,
)


def test_create_foundup_lineage_factory_and_round_trip():
    """Typed scaffold lineage survives the canonical job boundary."""
    genesis_digest = "sha256:" + ("a" * 64)
    scaffold_digest = "sha256:" + ("b" * 64)
    job = create_job(
        tenant_id="tenant_012",
        requested_action="create_foundup",
        foundup_id="widget_demo",
        payload={"genesis_envelope": {"foundup_id": "widget_demo"}},
        creation_mode="new_scaffold",
        genesis_envelope_digest=genesis_digest,
        scaffold_contract_digest=scaffold_digest,
    )

    restored = FoundUpJob.from_dict(job.to_dict())

    assert restored.creation_mode == "new_scaffold"
    assert restored.genesis_envelope_digest == genesis_digest
    assert restored.scaffold_contract_digest == scaffold_digest
    assert restored.to_dict()["creation_mode"] == "new_scaffold"


def test_legacy_serialized_job_without_create_lineage_still_round_trips():
    """Older receipts remain readable and gain only nullable lineage fields."""
    legacy = {
        "job_id": "legacy-job",
        "tenant_id": "legacy-tenant",
        "requested_action": "build_foundup",
        "status": "queued",
        "payload": {"nested": {"value": 1}},
    }

    restored = FoundUpJob.from_dict(legacy)
    serialized = restored.to_dict()

    assert restored.creation_mode is None
    assert restored.genesis_envelope_digest is None
    assert restored.scaffold_contract_digest is None
    assert serialized["payload"] == legacy["payload"]
    assert serialized["creation_mode"] is None
    assert serialized["genesis_envelope_digest"] is None
    assert serialized["scaffold_contract_digest"] is None
