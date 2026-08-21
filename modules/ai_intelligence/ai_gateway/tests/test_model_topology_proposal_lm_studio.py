"""Tests for the bounded local Nemotron shadow-proposal caller."""

from __future__ import annotations

import json

import pytest

from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import (
    SelectionPurpose,
)
from modules.ai_intelligence.ai_gateway.src.model_topology_proposal_lm_studio import (
    propose_lm_studio_shadow_topologies,
    rehydrate_lm_studio_topology_proposal_call_receipt,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_topology_proposal_admission import (
    _proposal,
    _requirements,
    _snapshot,
)


class _FakeLMStudioBackend:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls = []

    def create_native_chat(self, **controls):
        self.calls.append(controls)
        return {"output": [{"type": "message", "content": self.content}]}


def test_local_proposer_requests_strict_schema_and_binds_call_evidence():
    snapshot = _snapshot()
    requirements = _requirements()
    proposal = _proposal(snapshot, requirements)
    proposal["candidates"] = proposal["candidates"][:2]
    choices = {
        "topologies": [
            [item["model_id"] for item in candidate["role_assignments"]]
            for candidate in proposal["candidates"]
        ]
    }
    backend = _FakeLMStudioBackend(json.dumps(choices))
    requested_models = []

    def factory(model_id):
        requested_models.append(model_id)
        return backend

    result = propose_lm_studio_shadow_topologies(
        catalog_snapshot=snapshot,
        requirements=requirements,
        proposer_model_id="nvidia/nemotron-3.5-lightning",
        backend_factory=factory,
    )

    assert requested_models == ["nvidia/nemotron-3.5-lightning"]
    assert result.call_receipt.provider == "lm_studio_local"
    assert result.call_receipt.structured_output_requested is False
    assert result.call_receipt.json_schema_prompted is True
    assert result.call_receipt.native_reasoning_control == "off"
    assert result.call_receipt.no_provider_fallback_performed is True
    assert result.call_receipt.no_server_launch_performed is True
    assert result.admission_receipt.accepted is True
    assert (
        result.admission_receipt.proposer_call_receipt_id
        == result.call_receipt.receipt_id
    )
    assert (
        result.admission_receipt.proposer_output_digest
        == result.call_receipt.output_digest
    )
    controls = backend.calls[0]
    assert controls["temperature"] == 1.0
    assert controls["top_p"] == 0.95
    assert controls["reasoning"] == "off"
    assert "required_json_schema" in controls["input_text"]
    assert '"required_candidate_count":2' in controls["input_text"]
    assert '"required_models_per_candidate":4' in controls["input_text"]
    assert (
        rehydrate_lm_studio_topology_proposal_call_receipt(
            result.call_receipt.to_dict()
        )
        == result.call_receipt
    )


def test_local_proposer_call_receipt_rejects_tamper():
    snapshot = _snapshot()
    requirements = _requirements()
    proposal = _proposal(snapshot, requirements)
    choices = {
        "topologies": [
            [item["model_id"] for item in candidate["role_assignments"]]
            for candidate in proposal["candidates"][:2]
        ]
    }
    backend = _FakeLMStudioBackend(json.dumps(choices))
    result = propose_lm_studio_shadow_topologies(
        catalog_snapshot=snapshot,
        requirements=requirements,
        proposer_model_id="nvidia/nemotron-3.5-lightning",
        backend_factory=lambda _model_id: backend,
    )
    payload = result.call_receipt.to_dict()
    payload["output_bytes"] += 1

    with pytest.raises(ValueError, match="receipt_id_invalid"):
        rehydrate_lm_studio_topology_proposal_call_receipt(payload)


def test_local_proposer_rejects_non_json_output_before_admission():
    backend = _FakeLMStudioBackend("not-json")

    with pytest.raises(ValueError, match="output_json_invalid"):
        propose_lm_studio_shadow_topologies(
            catalog_snapshot=_snapshot(),
            requirements=_requirements(),
            proposer_model_id="nvidia/nemotron-3.5-lightning",
            backend_factory=lambda _model_id: backend,
        )


def test_local_proposer_rejects_production_requirements_without_call():
    backend = _FakeLMStudioBackend("{}")

    with pytest.raises(ValueError, match="evaluation_only"):
        propose_lm_studio_shadow_topologies(
            catalog_snapshot=_snapshot(),
            requirements=_requirements(purpose=SelectionPurpose.PRODUCTION),
            proposer_model_id="nvidia/nemotron-3.5-lightning",
            backend_factory=lambda _model_id: backend,
        )

    assert backend.calls == []
