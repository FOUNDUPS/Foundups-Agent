"""Immutable policy, intent, and eligibility receipt contracts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any, Mapping


SCHEMA_VERSION = "canonical_single_call_admission.v1"
POLICY_SCHEMA_VERSION = "canonical_single_call_job_policy.v1"
INTENT_SCHEMA_VERSION = "canonical_single_call_intent.v1"
TRUST_CLASS = "trusted_job_policy_over_provider_asserted_route_evidence"
RUNTIME_AUTHORITY = "eligibility_only"
GATEWAY_BASE_URL = "https://openrouter.ai/api/v1"
HTTP_METHOD = "POST"
REQUEST_PATH = "/chat/completions"
PRICE_RECONCILIATION = "endpoint_specific_supersedes_model_summary"
MANDATORY_REQUEST_PARAMETERS = ("max_tokens", "reasoning")
PUBLIC_PRICING_SCHEMA_POLICY = (
    "openrouter_public_pricing_request_optional_absence_as_zero.v1"
)
HALTED_REASONS = (
    "atomic_admission_consumption_missing",
    "authenticated_endpoint_supply_missing",
    "authoritative_endpoint_availability_missing",
    "authoritative_usage_missing",
    "caller_wiring_absent",
    "prebuffer_response_bound_missing",
    "runtime_directory_identity_missing",
)
OMITTED_SAMPLING_PARAMETERS = (
    "min_p", "seed", "temperature", "top_a", "top_k", "top_p",
)
ADMISSION_KEYS = frozenset(
    """schema_version admission_id provider model_control_evidence_id
    model_control_digest endpoint_route_evidence_id endpoint_record_digest
    policy_id intent_id route_contract_digest gateway_base_url http_method
    request_path model_id endpoint_tag provider_order allow_fallbacks
    require_parameters data_collection require_zdr enforce_distillable_text
    reasoning_effort omitted_sampling_parameters mandatory_request_parameters
    endpoint_status
    accepted_endpoint_statuses endpoint_status_policy_accepted
    prompt_token_upper_bound
    max_completion_tokens context_length max_response_bytes prompt_price
    completion_price prompt_price_per_million completion_price_per_million
    request_price request_price_present request_price_schema_policy
    request_price_schema_policy_digest request_price_schema_policy_accepted
    model_summary_prompt_price model_summary_completion_price
    price_reconciliation reserved_upper_cost request_control output_use
    output_training_permission issued_at_ms fresh_until_ms max_calls
    halted_reasons trust_class runtime_authority""".split()
)
ADMISSION_ID_PATTERN = re.compile(
    r"canonical_single_call_admission:[0-9a-f]{64}\Z"
)
_MODEL_ID = re.compile(
    r"[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?/"
    r"[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?(?::free)?\Z"
)
_TOKEN = re.compile(r"[a-z0-9][a-z0-9._:/-]{0,127}\Z")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_NONCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,159}\Z")
_MAX_TOKEN_BOUND = 100_000_000
_MAX_RESPONSE_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True)
class CanonicalSingleCallJobPolicy:
    task_type: str
    model_id: str
    endpoint_tag: str
    accepted_endpoint_statuses: tuple[int, ...]
    max_prompt_tokens: int
    max_completion_tokens: int
    max_response_bytes: int
    reasoning_effort: str
    required_parameters: tuple[str, ...]
    omitted_sampling_parameters: tuple[str, ...]
    data_collection: str
    require_zdr: bool
    output_use: str
    enforce_distillable_text: bool
    max_prompt_price_per_million: str
    max_completion_price_per_million: str
    max_request_price: str
    expires_at_ms: int
    max_calls: int
    schema_version: str = field(init=False, default=POLICY_SCHEMA_VERSION)

    @property
    def policy_id(self) -> str:
        return content_id("canonical_single_call_job_policy", self.normalized().to_dict())

    def normalized(self) -> "CanonicalSingleCallJobPolicy":
        _validate_policy_scalars(self)
        required = unique_tokens(self.required_parameters)
        omitted = unique_tokens(self.omitted_sampling_parameters)
        if required != MANDATORY_REQUEST_PARAMETERS:
            raise ValueError("single_call_required_parameters_invalid")
        if omitted != OMITTED_SAMPLING_PARAMETERS:
            raise ValueError("single_call_sampling_policy_invalid")
        return CanonicalSingleCallJobPolicy(
            task_type=self.task_type,
            model_id=self.model_id,
            endpoint_tag=self.endpoint_tag,
            accepted_endpoint_statuses=_accepted_statuses(
                self.accepted_endpoint_statuses
            ),
            max_prompt_tokens=positive_int(self.max_prompt_tokens),
            max_completion_tokens=positive_int(self.max_completion_tokens),
            max_response_bytes=_response_bytes(self.max_response_bytes),
            reasoning_effort=self.reasoning_effort,
            required_parameters=required,
            omitted_sampling_parameters=omitted,
            data_collection="deny",
            require_zdr=self.require_zdr,
            output_use=self.output_use,
            enforce_distillable_text=self.enforce_distillable_text,
            max_prompt_price_per_million=canonical_price(
                self.max_prompt_price_per_million
            ),
            max_completion_price_per_million=canonical_price(
                self.max_completion_price_per_million
            ),
            max_request_price=canonical_price(self.max_request_price),
            expires_at_ms=self.expires_at_ms,
            max_calls=1,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_type": self.task_type,
            "model_id": self.model_id,
            "endpoint_tag": self.endpoint_tag,
            "accepted_endpoint_statuses": list(self.accepted_endpoint_statuses),
            "max_prompt_tokens": self.max_prompt_tokens,
            "max_completion_tokens": self.max_completion_tokens,
            "max_response_bytes": self.max_response_bytes,
            "reasoning_effort": self.reasoning_effort,
            "required_parameters": list(self.required_parameters),
            "omitted_sampling_parameters": list(self.omitted_sampling_parameters),
            "data_collection": self.data_collection,
            "require_zdr": self.require_zdr,
            "output_use": self.output_use,
            "enforce_distillable_text": self.enforce_distillable_text,
            "max_prompt_price_per_million": self.max_prompt_price_per_million,
            "max_completion_price_per_million": self.max_completion_price_per_million,
            "max_request_price": self.max_request_price,
            "expires_at_ms": self.expires_at_ms,
            "max_calls": self.max_calls,
        }


@dataclass(frozen=True)
class CanonicalSingleCallIntent:
    task_type: str
    model_id: str
    prompt_digest: str
    prompt_token_upper_bound: int
    output_use: str
    nonce: str
    issued_at_ms: int
    expires_at_ms: int
    schema_version: str = field(init=False, default=INTENT_SCHEMA_VERSION)

    @property
    def intent_id(self) -> str:
        return content_id("canonical_single_call_intent", self.normalized().to_dict())

    def normalized(self) -> "CanonicalSingleCallIntent":
        if (
            self.schema_version != INTENT_SCHEMA_VERSION
            or not valid_token(self.task_type)
            or not valid_model(self.model_id)
            or not _DIGEST.fullmatch(str(self.prompt_digest))
            or not _NONCE.fullmatch(str(self.nonce))
            or self.output_use not in {"evaluation_only", "training"}
            or not is_uint(self.issued_at_ms)
            or not is_uint(self.expires_at_ms)
            or self.issued_at_ms > self.expires_at_ms
        ):
            raise ValueError("single_call_intent_invalid")
        return CanonicalSingleCallIntent(
            task_type=self.task_type,
            model_id=self.model_id,
            prompt_digest=self.prompt_digest,
            prompt_token_upper_bound=positive_int(self.prompt_token_upper_bound),
            output_use=self.output_use,
            nonce=self.nonce,
            issued_at_ms=self.issued_at_ms,
            expires_at_ms=self.expires_at_ms,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_type": self.task_type,
            "model_id": self.model_id,
            "prompt_digest": self.prompt_digest,
            "prompt_token_upper_bound": self.prompt_token_upper_bound,
            "output_use": self.output_use,
            "nonce": self.nonce,
            "issued_at_ms": self.issued_at_ms,
            "expires_at_ms": self.expires_at_ms,
        }


@dataclass(frozen=True)
class CanonicalSingleCallAdmission:
    admission_id: str
    model_control_evidence_id: str
    model_control_digest: str
    endpoint_route_evidence_id: str
    endpoint_record_digest: str
    policy_id: str
    intent_id: str
    route_contract_digest: str
    model_id: str
    endpoint_tag: str
    provider_order: tuple[str, ...]
    allow_fallbacks: bool
    require_parameters: bool
    data_collection: str
    require_zdr: bool
    enforce_distillable_text: bool
    reasoning_effort: str
    omitted_sampling_parameters: tuple[str, ...]
    mandatory_request_parameters: tuple[str, ...]
    endpoint_status: int
    accepted_endpoint_statuses: tuple[int, ...]
    endpoint_status_policy_accepted: bool
    prompt_token_upper_bound: int
    max_completion_tokens: int
    context_length: int
    max_response_bytes: int
    prompt_price: str
    completion_price: str
    prompt_price_per_million: str
    completion_price_per_million: str
    request_price: str
    request_price_present: bool
    request_price_schema_policy: str
    request_price_schema_policy_digest: str
    request_price_schema_policy_accepted: bool
    model_summary_prompt_price: str
    model_summary_completion_price: str
    price_reconciliation: str
    reserved_upper_cost: str
    request_control: Mapping[str, Any]
    output_use: str
    output_training_permission: bool
    issued_at_ms: int
    fresh_until_ms: int
    max_calls: int
    halted_reasons: tuple[str, ...]
    provider: str = field(init=False, default="openrouter")
    gateway_base_url: str = field(init=False, default=GATEWAY_BASE_URL)
    http_method: str = field(init=False, default=HTTP_METHOD)
    request_path: str = field(init=False, default=REQUEST_PATH)
    trust_class: str = field(init=False, default=TRUST_CLASS)
    runtime_authority: str = field(init=False, default=RUNTIME_AUTHORITY)
    schema_version: str = field(init=False, default=SCHEMA_VERSION)

    def to_dict(self) -> dict[str, Any]:
        result = {
            key: getattr(self, key)
            for key in ADMISSION_KEYS
            if key not in {
                "provider_order", "omitted_sampling_parameters",
                "mandatory_request_parameters",
                "accepted_endpoint_statuses",
                "halted_reasons", "request_control",
            }
        }
        result["provider_order"] = list(self.provider_order)
        result["omitted_sampling_parameters"] = list(self.omitted_sampling_parameters)
        result["mandatory_request_parameters"] = list(
            self.mandatory_request_parameters
        )
        result["accepted_endpoint_statuses"] = list(self.accepted_endpoint_statuses)
        result["halted_reasons"] = list(self.halted_reasons)
        result["request_control"] = mutable(self.request_control)
        return result


def canonical_price(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("single_call_policy_invalid")
    try:
        decimal = Decimal(value)
    except InvalidOperation:
        raise ValueError("single_call_policy_invalid") from None
    if not decimal.is_finite() or decimal < 0 or decimal > Decimal("1000000000"):
        raise ValueError("single_call_policy_invalid")
    canonical = decimal_text(decimal)
    if value != canonical:
        raise ValueError("single_call_policy_invalid")
    return canonical


def positive_int(value: Any) -> int:
    if type(value) is not int or not 0 < value <= _MAX_TOKEN_BOUND:
        raise ValueError("single_call_policy_invalid")
    return value


def unique_tokens(values: Any) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not values:
        raise ValueError("single_call_policy_invalid")
    result = tuple(sorted(values))
    if len(result) != len(set(result)) or not all(valid_token(item) for item in result):
        raise ValueError("single_call_policy_invalid")
    return result


def valid_token(value: Any) -> bool:
    return isinstance(value, str) and _TOKEN.fullmatch(value) is not None


def valid_model(value: Any) -> bool:
    return isinstance(value, str) and _MODEL_ID.fullmatch(value) is not None


def is_uint(value: Any) -> bool:
    return type(value) is int and 0 <= value < 2**63


def decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def frozen(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType({
        key: frozen(item) if isinstance(item, Mapping)
        else tuple(item) if isinstance(item, list)
        else item
        for key, item in value.items()
    })


def mutable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: mutable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [mutable(item) for item in value]
    return value


def content_id(prefix: str, value: object) -> str:
    return f"{prefix}:{digest_payload(value)[7:]}"


def digest_payload(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _validate_policy_scalars(policy: CanonicalSingleCallJobPolicy) -> None:
    if (
        policy.schema_version != POLICY_SCHEMA_VERSION
        or not valid_token(policy.task_type)
        or not valid_model(policy.model_id)
        or not valid_token(policy.endpoint_tag)
        or not valid_token(policy.reasoning_effort)
        or policy.data_collection != "deny"
        or type(policy.require_zdr) is not bool
        or type(policy.enforce_distillable_text) is not bool
        or policy.output_use not in {"evaluation_only", "training"}
        or policy.max_calls != 1
        or not is_uint(policy.expires_at_ms)
    ):
        raise ValueError("single_call_policy_invalid")


def _response_bytes(value: Any) -> int:
    result = positive_int(value)
    if result > _MAX_RESPONSE_BYTES:
        raise ValueError("single_call_policy_invalid")
    return result


def _accepted_statuses(value: Any) -> tuple[int, ...]:
    if (
        not isinstance(value, tuple)
        or value != (0,)
        or any(type(item) is not int for item in value)
    ):
        raise ValueError("single_call_policy_invalid")
    return (0,)


__all__ = [
    "ADMISSION_ID_PATTERN",
    "ADMISSION_KEYS",
    "CanonicalSingleCallAdmission",
    "CanonicalSingleCallIntent",
    "CanonicalSingleCallJobPolicy",
    "GATEWAY_BASE_URL",
    "HALTED_REASONS",
    "HTTP_METHOD",
    "MANDATORY_REQUEST_PARAMETERS",
    "OMITTED_SAMPLING_PARAMETERS",
    "PRICE_RECONCILIATION",
    "PUBLIC_PRICING_SCHEMA_POLICY",
    "REQUEST_PATH",
    "RUNTIME_AUTHORITY",
    "SCHEMA_VERSION",
    "TRUST_CLASS",
    "content_id",
    "decimal_text",
    "digest_payload",
    "frozen",
    "is_uint",
]
