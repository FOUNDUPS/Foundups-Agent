"""Bounded local-LM-Studio proposer for shadow RedDog topology evaluation.

This is not model-selection, promotion, runtime-binding, or execution authority.
It acquires one exact local model transaction for JSON-schema-constrained
candidate topologies, records content-free call and lifecycle evidence, and
submits the decoded proposal to the deterministic AI Gateway admission gate.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping

from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
    LMStudioModelLease,
    LMStudioModelLifecycleReceipt,
    execute_lm_studio_model_transaction,
    rehydrate_lm_studio_model_lifecycle_receipt,
)
from modules.infrastructure.shared_utilities.local_llm_backends import (
    LMStudioBackend,
)

from .model_intelligence_catalog import ModelCatalogSnapshot
from .model_intelligence_selection import (
    ModelTaskRequirements,
    SelectionMode,
    SelectionPurpose,
    select_models_for_task,
)
from .model_topology_proposal_admission import (
    MAX_PROPOSAL_BYTES,
    PROPOSAL_SCHEMA_VERSION,
    ModelTopologyProposalAdmissionReceipt,
    admit_model_topology_proposal,
    model_task_requirements_digest,
)


CALL_SCHEMA_VERSION = "lm_studio_model_topology_proposal_call.v2"
MAX_PROMPT_BYTES = 65_536
MAX_COMPLETION_TOKENS = 8_192
MAX_ELIGIBLE_MODELS = 20
PROPOSER_REQUEST_TIMEOUT_SECONDS = 300.0
PROPOSER_CANDIDATE_COUNT = 2
PROPOSER_LOAD_CONFIG = {
    "context_length": 32_768,
    "flash_attention": True,
    "offload_kv_cache_to_gpu": True,
}
DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$")


def _require_proposer_backend(model_id: str) -> Any:
    return _ManagedLMStudioProposerBackend(model_id)


class _ManagedLMStudioProposerBackend:
    """One exact load/call/unload transaction; never starts the server."""

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        self.lifecycle_receipt: LMStudioModelLifecycleReceipt | None = None

    def create_native_chat(self, **controls: Any) -> Mapping[str, Any]:
        api_token = os.environ.get("LM_API_TOKEN") or None
        result = execute_lm_studio_model_transaction(
            model_key=self.model_id,
            operation=lambda lease: _call_native_on_lease(
                lease, controls, api_token=api_token
            ),
            api_token=api_token,
            load_config=PROPOSER_LOAD_CONFIG,
            timeout=PROPOSER_REQUEST_TIMEOUT_SECONDS,
        )
        self.lifecycle_receipt = result.lifecycle_receipt
        return result.value


def _call_native_on_lease(
    lease: LMStudioModelLease,
    controls: Mapping[str, Any],
    *,
    api_token: str | None,
) -> Mapping[str, Any]:
    backend = LMStudioBackend(
        model_id=lease.model_key,
        base_url=lease.base_url,
        request_timeout=PROPOSER_REQUEST_TIMEOUT_SECONDS,
        expected_instance_id=lease.instance_id,
        api_token=api_token,
    )
    if not backend.initialize():
        raise RuntimeError("lm_studio_topology_proposer_lease_not_resident")
    return backend.create_native_chat(**dict(controls))


@dataclass(frozen=True)
class LMStudioTopologyProposalCallReceipt:
    """Content-free, digest-bound evidence of one local shadow proposal call."""

    receipt_id: str
    proposer_model_id: str
    provider: str
    catalog_snapshot_id: str
    requirements_digest: str
    output_digest: str
    output_bytes: int
    structured_output_requested: bool
    json_schema_prompted: bool
    native_reasoning_control: str
    no_provider_fallback_performed: bool
    no_server_launch_performed: bool
    lifecycle_receipt_id: str
    lifecycle_receipt_digest: str
    lifecycle_instance_id: str
    lifecycle_residency_origin: str
    lifecycle_observed_config_digest: str
    lifecycle_load_confirmed: bool
    lifecycle_unload_confirmed: bool
    shadow_only: bool
    schema_version: str = CALL_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LMStudioTopologyProposalResult:
    call_receipt: LMStudioTopologyProposalCallReceipt
    admission_receipt: ModelTopologyProposalAdmissionReceipt
    lifecycle_receipt: LMStudioModelLifecycleReceipt


@dataclass(frozen=True)
class _ProposalRequest:
    requirements: ModelTaskRequirements
    model_id: str
    completion_cap: int
    roles: tuple[str, ...]
    eligible_providers: Mapping[str, str]
    catalog_snapshot_id: str
    requirements_digest: str
    prompt: str


def rehydrate_lm_studio_topology_proposal_call_receipt(
    payload: Mapping[str, Any],
) -> LMStudioTopologyProposalCallReceipt:
    """Rehydrate content-free call evidence and verify its deterministic ID."""

    if payload.get("schema_version") != CALL_SCHEMA_VERSION:
        raise ValueError("lm_studio_topology_proposer_call_schema_invalid")
    output_bytes = payload.get("output_bytes")
    if type(output_bytes) is not int or not 1 <= output_bytes <= MAX_PROPOSAL_BYTES:
        raise ValueError("lm_studio_topology_proposer_call_output_bytes_invalid")
    output_digest = str(payload.get("output_digest") or "")
    if not DIGEST_RE.fullmatch(output_digest):
        raise ValueError("lm_studio_topology_proposer_call_output_digest_invalid")
    expected_flags = {
        "structured_output_requested": False,
        "json_schema_prompted": True,
        "no_provider_fallback_performed": True,
        "no_server_launch_performed": True,
        "shadow_only": True,
    }
    if any(payload.get(name) is not value for name, value in expected_flags.items()):
        raise ValueError("lm_studio_topology_proposer_call_flags_invalid")
    body = _call_receipt_body(payload, output_digest, output_bytes, expected_flags)
    if body["provider"] != "lm_studio_local" or body["native_reasoning_control"] != "off":
        raise ValueError("lm_studio_topology_proposer_call_route_invalid")
    _validate_lifecycle_call_fields(body)
    receipt_id = str(payload.get("receipt_id") or "")
    expected = _digest("lm_studio_model_topology_proposal_call", body)
    if not hmac.compare_digest(receipt_id, expected):
        raise ValueError("lm_studio_topology_proposer_call_receipt_id_invalid")
    return LMStudioTopologyProposalCallReceipt(receipt_id=receipt_id, **body)


def validate_lm_studio_topology_lifecycle_binding(
    call_receipt: LMStudioTopologyProposalCallReceipt | Mapping[str, Any],
    lifecycle_receipt: LMStudioModelLifecycleReceipt | Mapping[str, Any],
) -> tuple[LMStudioTopologyProposalCallReceipt, LMStudioModelLifecycleReceipt]:
    """Verify structural call/lifecycle binding; signer provenance supplies trust."""

    call_payload = (
        call_receipt.to_dict()
        if isinstance(call_receipt, LMStudioTopologyProposalCallReceipt)
        else call_receipt
    )
    lifecycle_payload = (
        lifecycle_receipt.to_dict()
        if isinstance(lifecycle_receipt, LMStudioModelLifecycleReceipt)
        else lifecycle_receipt
    )
    call = rehydrate_lm_studio_topology_proposal_call_receipt(call_payload)
    lifecycle = rehydrate_lm_studio_model_lifecycle_receipt(lifecycle_payload)
    expected = {
        "lifecycle_receipt_id": lifecycle.receipt_id,
        "lifecycle_receipt_digest": _digest(
            "lm_studio_model_lifecycle_payload", lifecycle.to_dict()
        ),
        "lifecycle_instance_id": lifecycle.instance_id,
        "lifecycle_residency_origin": lifecycle.residency_origin,
        "lifecycle_observed_config_digest": lifecycle.observed_config_digest,
        "lifecycle_load_confirmed": lifecycle.load_confirmed,
        "lifecycle_unload_confirmed": lifecycle.unload_confirmed,
    }
    if any(getattr(call, name) != value for name, value in expected.items()):
        raise ValueError("lm_studio_topology_proposer_lifecycle_binding_invalid")
    return call, lifecycle


def _call_receipt_body(
    payload: Mapping[str, Any],
    output_digest: str,
    output_bytes: int,
    expected_flags: Mapping[str, bool],
) -> dict[str, Any]:
    return {
        "schema_version": CALL_SCHEMA_VERSION,
        "proposer_model_id": _required("proposer_model_id", payload.get("proposer_model_id")),
        "catalog_snapshot_id": _required("catalog_snapshot_id", payload.get("catalog_snapshot_id")),
        "requirements_digest": _required("requirements_digest", payload.get("requirements_digest")),
        "output_digest": output_digest,
        "output_bytes": output_bytes,
        "provider": str(payload.get("provider") or ""),
        "lifecycle_receipt_id": _required_lifecycle_id(
            payload.get("lifecycle_receipt_id")
        ),
        "lifecycle_receipt_digest": _required_digest(
            "lifecycle_receipt_digest", payload.get("lifecycle_receipt_digest")
        ),
        "lifecycle_instance_id": _required(
            "lifecycle_instance_id", payload.get("lifecycle_instance_id")
        ),
        "lifecycle_residency_origin": str(
            payload.get("lifecycle_residency_origin") or ""
        ),
        "lifecycle_observed_config_digest": _required_hex_digest(
            "lifecycle_observed_config_digest",
            payload.get("lifecycle_observed_config_digest"),
        ),
        "lifecycle_load_confirmed": payload.get("lifecycle_load_confirmed"),
        "lifecycle_unload_confirmed": payload.get("lifecycle_unload_confirmed"),
        **expected_flags,
        "native_reasoning_control": str(payload.get("native_reasoning_control") or ""),
    }


def propose_lm_studio_shadow_topologies(
    *,
    catalog_snapshot: ModelCatalogSnapshot,
    requirements: ModelTaskRequirements,
    proposer_model_id: str,
    max_completion_tokens: int = 2_048,
    backend_factory: Callable[[str], Any] = _require_proposer_backend,
) -> LMStudioTopologyProposalResult:
    """Call exact local proposer once, then deterministically admit its output."""

    request = _prepare_request(
        catalog_snapshot, requirements, proposer_model_id, max_completion_tokens
    )
    proposal, output_bytes, lifecycle_receipt = _execute_request(
        request, backend_factory
    )
    output_digest = f"sha256:{hashlib.sha256(output_bytes).hexdigest()}"
    call_receipt = _call_receipt(
        proposer_model_id=request.model_id,
        catalog_snapshot_id=catalog_snapshot.snapshot_id,
        requirements_digest=request.requirements_digest,
        output_digest=output_digest,
        output_bytes=len(output_bytes),
        lifecycle_receipt_id=lifecycle_receipt.receipt_id,
        lifecycle_receipt_digest=_digest(
            "lm_studio_model_lifecycle_payload", lifecycle_receipt.to_dict()
        ),
        lifecycle_instance_id=lifecycle_receipt.instance_id,
        lifecycle_residency_origin=lifecycle_receipt.residency_origin,
        lifecycle_observed_config_digest=lifecycle_receipt.observed_config_digest,
        lifecycle_load_confirmed=lifecycle_receipt.load_confirmed,
        lifecycle_unload_confirmed=lifecycle_receipt.unload_confirmed,
    )
    call_receipt, lifecycle_receipt = validate_lm_studio_topology_lifecycle_binding(
        call_receipt, lifecycle_receipt
    )
    admission = admit_model_topology_proposal(
        catalog_snapshot=catalog_snapshot,
        requirements=request.requirements,
        proposer_model_id=request.model_id,
        proposal=proposal,
        proposer_call_receipt_id=call_receipt.receipt_id,
        proposer_output_digest=output_digest,
    )
    return LMStudioTopologyProposalResult(call_receipt, admission, lifecycle_receipt)


def _prepare_request(
    catalog_snapshot: ModelCatalogSnapshot,
    requirements: ModelTaskRequirements,
    proposer_model_id: str,
    max_completion_tokens: int,
) -> _ProposalRequest:
    normalized = requirements.normalized()
    if normalized.purpose != SelectionPurpose.EVALUATION:
        raise ValueError("lm_studio_topology_proposer_evaluation_only")
    completion_cap = int(max_completion_tokens)
    if not 1 <= completion_cap <= MAX_COMPLETION_TOKENS:
        raise ValueError("lm_studio_topology_proposer_completion_cap_invalid")
    eligible = tuple(
        select_models_for_task(catalog_snapshot, normalized).rankings[:MAX_ELIGIBLE_MODELS]
    )
    if not eligible:
        raise ValueError("lm_studio_topology_proposer_no_eligible_models")
    roles = _expected_roles(normalized)
    providers = _eligible_provider_map(eligible)
    schema = _choice_schema(
        roles=roles,
        model_ids=tuple(providers),
        candidate_count=PROPOSER_CANDIDATE_COUNT,
    )
    prompt = _proposal_prompt(roles=roles, eligible=eligible, response_schema=schema)
    if len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
        raise ValueError("lm_studio_topology_proposer_prompt_too_large")
    return _ProposalRequest(
        normalized,
        _required("proposer_model_id", proposer_model_id),
        completion_cap,
        roles,
        providers,
        catalog_snapshot.snapshot_id,
        model_task_requirements_digest(normalized),
        prompt,
    )


def _expected_roles(requirements: ModelTaskRequirements) -> tuple[str, ...]:
    roles = (
        ("principal",)
        if requirements.selection_mode == SelectionMode.SINGLE
        else requirements.panel_roles[: requirements.max_candidates]
    )
    if not roles:
        raise ValueError("lm_studio_topology_proposer_roles_missing")
    return roles


def _execute_request(
    request: _ProposalRequest,
    backend_factory: Callable[[str], Any],
) -> tuple[dict[str, Any], bytes, LMStudioModelLifecycleReceipt]:
    backend = backend_factory(request.model_id)
    response = backend.create_native_chat(
        input_text=request.prompt,
        system_prompt=(
            f"Return exactly {PROPOSER_CANDIDATE_COUNT} candidate arrays. Each candidate "
            f"array must contain exactly {len(request.roles)} model ID strings, one for "
            "each ordered role. Use only supplied IDs and return only the JSON object."
        ),
        max_output_tokens=request.completion_cap,
        reasoning="off",
        temperature=1.0,
        top_p=0.95,
        max_response_bytes=MAX_PROPOSAL_BYTES,
    )
    lifecycle_receipt = _lifecycle_receipt_from_backend(backend)
    output = _native_response_text(response)
    output_bytes = output.encode("utf-8")
    if not output_bytes or len(output_bytes) > MAX_PROPOSAL_BYTES:
        raise ValueError("lm_studio_topology_proposer_output_size_invalid")
    try:
        choices = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ValueError("lm_studio_topology_proposer_output_json_invalid") from exc
    if not isinstance(choices, Mapping):
        raise ValueError("lm_studio_topology_proposer_output_schema_invalid")
    proposal = _compile_proposal(
        choices=choices,
        catalog_snapshot_id=request.catalog_snapshot_id,
        requirements_digest=request.requirements_digest,
        roles=request.roles,
        eligible_providers=request.eligible_providers,
    )
    return proposal, output_bytes, lifecycle_receipt


def _lifecycle_receipt_from_backend(
    backend: Any,
) -> LMStudioModelLifecycleReceipt:
    value = getattr(backend, "lifecycle_receipt", None)
    if value is None:
        raise ValueError("lm_studio_topology_proposer_lifecycle_receipt_missing")
    payload = value.to_dict() if isinstance(value, LMStudioModelLifecycleReceipt) else value
    if not isinstance(payload, Mapping):
        raise ValueError("lm_studio_topology_proposer_lifecycle_receipt_invalid")
    return rehydrate_lm_studio_model_lifecycle_receipt(payload)


def _proposal_prompt(*, roles: tuple[str, ...], eligible: tuple[Any, ...], response_schema: Mapping[str, Any]) -> str:
    payload = {
        "ordered_roles": list(roles),
        "required_candidate_count": PROPOSER_CANDIDATE_COUNT,
        "required_models_per_candidate": len(roles),
        "shape_rule": (
            f"topologies has exactly {PROPOSER_CANDIDATE_COUNT} arrays; "
            f"each inner array has exactly {len(roles)} model ID strings"
        ),
        "required_json_schema": response_schema,
        "eligible_models": [
            {
                "model_id": item.canonical_model_id,
                "score": item.score,
            }
            for item in eligible
        ],
        "objective": (
            "Return multiple diverse candidate assignments for held-out AutoResearch. "
            "Do not choose a verifier and do not claim production authority."
        ),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _choice_schema(*, roles: tuple[str, ...], model_ids: tuple[str, ...], candidate_count: int) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["topologies"],
        "properties": {
            "topologies": {
                "type": "array",
                "minItems": candidate_count,
                "maxItems": candidate_count,
                "items": {
                    "type": "array",
                    "minItems": len(roles),
                    "maxItems": len(roles),
                    "items": {"type": "string", "enum": list(model_ids)},
                },
            },
        },
    }


def _eligible_provider_map(eligible: tuple[Any, ...]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in eligible:
        existing = result.get(item.canonical_model_id)
        if existing is not None and existing != item.provider:
            raise ValueError("lm_studio_topology_proposer_ambiguous_model_provider")
        result[item.canonical_model_id] = item.provider
    return result


def _compile_proposal(
    *,
    choices: Mapping[str, Any],
    catalog_snapshot_id: str,
    requirements_digest: str,
    roles: tuple[str, ...],
    eligible_providers: Mapping[str, str],
) -> dict[str, Any]:
    topologies = choices.get("topologies")
    if not isinstance(topologies, list) or len(topologies) != PROPOSER_CANDIDATE_COUNT:
        raise ValueError("lm_studio_topology_proposer_output_schema_invalid")
    candidates = []
    for topology in topologies:
        if not isinstance(topology, list) or len(topology) != len(roles):
            raise ValueError("lm_studio_topology_proposer_output_schema_invalid")
        if any(not isinstance(model_id, str) for model_id in topology):
            raise ValueError("lm_studio_topology_proposer_output_schema_invalid")
        candidates.append(
            {
                "role_assignments": [
                    {
                        "role": role,
                        "model_id": model_id,
                        "provider": eligible_providers.get(model_id, "unknown"),
                    }
                    for role, model_id in zip(roles, topology)
                ]
            }
        )
    return {
        "schema_version": PROPOSAL_SCHEMA_VERSION,
        "catalog_snapshot_id": catalog_snapshot_id,
        "requirements_digest": requirements_digest,
        "candidates": candidates,
    }


def _native_response_text(response: Any) -> str:
    if not isinstance(response, Mapping) or not isinstance(response.get("output"), list):
        raise ValueError("lm_studio_topology_proposer_response_invalid")
    content = "".join(
        str(item.get("content") or "")
        for item in response["output"]
        if isinstance(item, Mapping) and item.get("type") == "message"
    ).strip()
    return content


def _call_receipt(**values: Any) -> LMStudioTopologyProposalCallReceipt:
    body = {
        "schema_version": CALL_SCHEMA_VERSION,
        **values,
        "provider": "lm_studio_local",
        "structured_output_requested": False,
        "json_schema_prompted": True,
        "native_reasoning_control": "off",
        "no_provider_fallback_performed": True,
        "no_server_launch_performed": True,
        "shadow_only": True,
    }
    receipt_id = _digest("lm_studio_model_topology_proposal_call", body)
    return LMStudioTopologyProposalCallReceipt(receipt_id=receipt_id, **body)


def _required(name: str, value: Any) -> str:
    text = str(value or "").strip()
    if not text or len(text.encode("utf-8")) > 256:
        raise ValueError(f"lm_studio_topology_proposer_{name}_invalid")
    return text


def _required_digest(name: str, value: Any) -> str:
    text = _required(name, value)
    if not text.startswith("lm_studio_model_lifecycle_payload:"):
        raise ValueError(f"lm_studio_topology_proposer_{name}_invalid")
    suffix = text.rsplit(":", 1)[-1]
    if len(suffix) != 64 or any(character not in "0123456789abcdef" for character in suffix):
        raise ValueError(f"lm_studio_topology_proposer_{name}_invalid")
    return text


def _required_lifecycle_id(value: Any) -> str:
    text = _required("lifecycle_receipt_id", value)
    prefix = "lm_studio_model_lifecycle:"
    suffix = text.removeprefix(prefix)
    if not text.startswith(prefix) or len(suffix) != 64:
        raise ValueError("lm_studio_topology_proposer_lifecycle_receipt_id_invalid")
    if any(character not in "0123456789abcdef" for character in suffix):
        raise ValueError("lm_studio_topology_proposer_lifecycle_receipt_id_invalid")
    return text


def _required_hex_digest(name: str, value: Any) -> str:
    text = str(value or "")
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"lm_studio_topology_proposer_{name}_invalid")
    return text


def _validate_lifecycle_call_fields(body: Mapping[str, Any]) -> None:
    origin = body["lifecycle_residency_origin"]
    expected = origin == "explicit_load"
    if origin not in {"preexisting", "explicit_load"}:
        raise ValueError("lm_studio_topology_proposer_lifecycle_origin_invalid")
    if body["lifecycle_load_confirmed"] is not expected:
        raise ValueError("lm_studio_topology_proposer_lifecycle_flags_invalid")
    if body["lifecycle_unload_confirmed"] is not expected:
        raise ValueError("lm_studio_topology_proposer_lifecycle_flags_invalid")


def _digest(prefix: str, value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


__all__ = [
    "LMStudioTopologyProposalCallReceipt",
    "LMStudioTopologyProposalResult",
    "propose_lm_studio_shadow_topologies",
    "rehydrate_lm_studio_topology_proposal_call_receipt",
    "validate_lm_studio_topology_lifecycle_binding",
]
