"""Strict bounded projection of supplied OpenRouter endpoint-list payloads."""

from __future__ import annotations

import hashlib
import json
import math
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence


MAX_ENDPOINT_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_ENDPOINT_RECORDS = 256
MAX_TOKEN_BOUND = 100_000_000
DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
PAYLOAD_ID_PATTERN = re.compile(r"openrouter_endpoint_payload:[0-9a-f]{64}\Z")
MODEL_ID_PATTERN = re.compile(
    r"[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?/"
    r"[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?(?::free)?\Z"
)
ENDPOINT_TAG_PATTERN = re.compile(
    r"[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?"
    r"(?:/[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?)?\Z"
)
_TOKEN = re.compile(r"[a-z0-9][a-z0-9._:-]{0,63}\Z")
_PRICE = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
_ROOT_KEYS = frozenset("id name created description architecture endpoints".split())
_ENDPOINT_KEYS = frozenset(
    """name model_id model_name context_length pricing provider_name tag
    quantization max_completion_tokens max_prompt_tokens supported_parameters
    uptime_last_30m uptime_last_5m uptime_last_1d supports_implicit_caching
    latency_last_30m throughput_last_30m""".split()
)
_OPTIONAL_PRICES = frozenset(
    """request internal_reasoning input_cache_read input_cache_write
    input_cache_write_1h web_search audio audio_output image image_output
    image_token input_audio_cache""".split()
)
_PRICING_KEYS = _OPTIONAL_PRICES | {
    "prompt",
    "completion",
    "discount",
    "overrides",
}
_ENDPOINT_STATUS_CODES = frozenset((0, -1, -2, -3, -5, -10))


def parse_and_sanitize_openrouter_endpoint_payload(
    raw: bytes, *, requested_model_id: str
) -> dict[str, Any]:
    if not isinstance(raw, bytes):
        raise ValueError("endpoint_payload_json_invalid")
    if len(raw) > MAX_ENDPOINT_RESPONSE_BYTES:
        raise ValueError("endpoint_payload_too_large")
    try:
        parsed = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_invalid_constant,
        )
        _bound_json(parsed)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
        raise ValueError("endpoint_payload_json_invalid") from None
    data = _validated_root(parsed, requested_model_id)
    endpoints = [_sanitize_endpoint(item, requested_model_id) for item in data["endpoints"]]
    tags = [item["tag"] for item in endpoints]
    if len(tags) != len(set(tags)):
        raise ValueError("endpoint_duplicate_tag")
    return {
        "model_id": requested_model_id,
        "endpoints": sorted(endpoints, key=lambda item: item["tag"]),
    }


def endpoint_payload_id(payload: Mapping[str, Any]) -> str:
    return content_id("openrouter_endpoint_payload", payload)


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def digest_payload(value: object) -> str:
    return sha256_bytes(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    )


def content_id(prefix: str, value: object) -> str:
    return f"{prefix}:{digest_payload(value)[7:]}"


def valid_model_id(value: Any) -> bool:
    return isinstance(value, str) and MODEL_ID_PATTERN.fullmatch(value) is not None


def valid_endpoint_tag(value: Any) -> bool:
    return (
        isinstance(value, str)
        and ENDPOINT_TAG_PATTERN.fullmatch(value) is not None
    )


def is_uint(value: Any) -> bool:
    return type(value) is int and 0 <= value < 2**63


def _validated_root(parsed: Any, requested_model_id: str) -> Mapping[str, Any]:
    if not valid_model_id(requested_model_id) or not isinstance(parsed, Mapping):
        raise ValueError("endpoint_payload_top_level_invalid")
    data = parsed.get("data")
    if not isinstance(data, Mapping) or not _ROOT_KEYS.issubset(data):
        raise ValueError("endpoint_payload_top_level_invalid")
    if data["id"] != requested_model_id:
        raise ValueError("endpoint_payload_model_mismatch")
    if not _bounded_text(data["name"], 256) or not _bounded_text(
        data["description"], 4096
    ):
        raise ValueError("endpoint_payload_top_level_invalid")
    if not is_uint(data["created"]):
        raise ValueError("endpoint_payload_top_level_invalid")
    _validate_architecture(data["architecture"])
    endpoints = data["endpoints"]
    if not isinstance(endpoints, list) or len(endpoints) > MAX_ENDPOINT_RECORDS:
        raise ValueError("endpoint_record_limit_exceeded")
    return data


def _validate_architecture(value: Any) -> None:
    required = {
        "tokenizer", "instruct_type", "modality",
        "input_modalities", "output_modalities",
    }
    if not isinstance(value, Mapping) or not required.issubset(value):
        raise ValueError("endpoint_payload_top_level_invalid")
    for key in ("tokenizer", "instruct_type", "modality"):
        if value[key] is not None and not _bounded_text(value[key], 128):
            raise ValueError("endpoint_payload_top_level_invalid")
    for key in ("input_modalities", "output_modalities"):
        if not _token_list(value[key], maximum=16):
            raise ValueError("endpoint_payload_top_level_invalid")


def _sanitize_endpoint(raw: Any, requested_model_id: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or not _ENDPOINT_KEYS.issubset(raw):
        raise ValueError("endpoint_record_invalid")
    if raw["model_id"] != requested_model_id:
        raise ValueError("endpoint_record_invalid")
    if not _bounded_text(raw["name"], 256) or not _bounded_text(raw["model_name"], 256):
        raise ValueError("endpoint_record_invalid")
    if not _bounded_text(raw["provider_name"], 128) or not valid_endpoint_tag(raw["tag"]):
        raise ValueError("endpoint_record_invalid")
    context = _positive_tokens(raw["context_length"])
    prompt_cap = _nullable_positive_tokens(raw["max_prompt_tokens"])
    completion_cap = _nullable_positive_tokens(raw["max_completion_tokens"])
    if prompt_cap is not None and prompt_cap > context:
        raise ValueError("endpoint_record_invalid")
    if completion_cap is not None and completion_cap > context:
        raise ValueError("endpoint_record_invalid")
    pricing, unsafe = _pricing(raw["pricing"])
    result = _project_endpoint(
        raw, requested_model_id, context, prompt_cap, completion_cap, pricing, unsafe
    )
    if "status" in raw:
        status = raw["status"]
        if type(status) is not int or status not in _ENDPOINT_STATUS_CODES:
            raise ValueError("endpoint_record_invalid")
        result["status"] = status
    return result


def _project_endpoint(
    raw, model_id, context, prompt_cap, completion_cap, pricing, unsafe
) -> dict[str, Any]:
    parameters = _parameters(raw["supported_parameters"])
    _validate_metrics(raw)
    quantization = raw["quantization"]
    if quantization is not None and not _TOKEN.fullmatch(str(quantization)):
        raise ValueError("endpoint_record_invalid")
    return {
        "model_id": model_id,
        "tag": raw["tag"],
        "provider_name": raw["provider_name"],
        "context_length": context,
        "max_prompt_tokens": prompt_cap,
        "max_completion_tokens": completion_cap,
        "pricing": pricing,
        "unsafe_cost_dimensions": list(unsafe),
        "supported_parameters": list(parameters),
        "quantization": quantization,
        "supports_implicit_caching": _strict_bool(raw["supports_implicit_caching"]),
    }


def _pricing(value: Any) -> tuple[dict[str, Any], tuple[str, ...]]:
    if not isinstance(value, Mapping) or not {"prompt", "completion"}.issubset(value):
        raise ValueError("endpoint_record_invalid")
    if not set(value).issubset(_PRICING_KEYS):
        raise ValueError("endpoint_record_invalid")
    result = {
        "prompt": _canonical_price(value["prompt"]),
        "completion": _canonical_price(value["completion"]),
    }
    unsafe: list[str] = []
    for key in sorted(_OPTIONAL_PRICES.intersection(value)):
        price = _canonical_price(value[key])
        result[key] = price
        if price != "0":
            unsafe.append(key)
    _project_discount_and_overrides(value, result, unsafe)
    return result, tuple(sorted(unsafe))


def _project_discount_and_overrides(
    source: Mapping[str, Any], result: dict[str, Any], unsafe: list[str]
) -> None:
    if "discount" in source:
        discount = _canonical_fraction(source["discount"])
        result["discount"] = discount
        if discount != "0":
            unsafe.append("discount")
    if "overrides" in source:
        overrides = source["overrides"]
        if not isinstance(overrides, list) or len(overrides) > 32:
            raise ValueError("endpoint_record_invalid")
        result["overrides_count"] = len(overrides)
        if overrides:
            unsafe.append("overrides")


def _validate_metrics(raw: Mapping[str, Any]) -> None:
    for key in ("uptime_last_30m", "uptime_last_5m", "uptime_last_1d"):
        value = raw[key]
        if value is not None and (
            type(value) not in (int, float)
            or not math.isfinite(value)
            or not 0 <= value <= 100
        ):
            raise ValueError("endpoint_record_invalid")
    for key in ("latency_last_30m", "throughput_last_30m"):
        _validate_percentiles(raw[key])


def _validate_percentiles(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, Mapping) or set(value) != {"p50", "p75", "p90", "p99"}:
        raise ValueError("endpoint_record_invalid")
    if any(
        type(item) not in (int, float) or not math.isfinite(item) or item < 0
        for item in value.values()
    ):
        raise ValueError("endpoint_record_invalid")


def _parameters(value: Any) -> tuple[str, ...]:
    if not _token_list(value, maximum=64):
        raise ValueError("endpoint_record_invalid")
    result = tuple(sorted(value))
    if len(set(result)) != len(result):
        raise ValueError("endpoint_record_invalid")
    return result


def _canonical_price(value: Any) -> str:
    if not isinstance(value, str) or not _PRICE.fullmatch(value):
        raise ValueError("endpoint_record_invalid")
    try:
        decimal = Decimal(value)
    except InvalidOperation:
        raise ValueError("endpoint_record_invalid") from None
    if decimal < 0 or decimal > Decimal("1000"):
        raise ValueError("endpoint_record_invalid")
    return format(decimal.normalize(), "f")


def _canonical_fraction(value: Any) -> str:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("endpoint_record_invalid")
    decimal = Decimal(str(value))
    if decimal < 0 or decimal > 1:
        raise ValueError("endpoint_record_invalid")
    return format(decimal.normalize(), "f")


def _bound_json(value: Any, depth: int = 0) -> None:
    if depth > 12:
        raise ValueError("json_depth")
    if isinstance(value, str) and len(value) > 4096:
        raise ValueError("json_string")
    if isinstance(value, list):
        if len(value) > 4096:
            raise ValueError("json_array")
        for item in value:
            _bound_json(item, depth + 1)
    elif isinstance(value, Mapping):
        if len(value) > 256:
            raise ValueError("json_object")
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > 128:
                raise ValueError("json_key")
            _bound_json(item, depth + 1)


def _unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


def _invalid_constant(_value: str) -> None:
    raise ValueError("invalid_constant")


def _positive_tokens(value: Any) -> int:
    if type(value) is not int or not 0 < value <= MAX_TOKEN_BOUND:
        raise ValueError("endpoint_record_invalid")
    return value


def _nullable_positive_tokens(value: Any) -> int | None:
    return None if value is None else _positive_tokens(value)


def _strict_bool(value: Any) -> bool:
    if type(value) is not bool:
        raise ValueError("endpoint_record_invalid")
    return value


def _token_list(value: Any, maximum: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) <= maximum
        and all(isinstance(item, str) and _TOKEN.fullmatch(item) for item in value)
    )


def _bounded_text(value: Any, maximum: int) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= maximum
        and value.isascii()
        and all(character.isprintable() for character in value)
    )


__all__ = [
    "DIGEST_PATTERN",
    "MAX_ENDPOINT_RESPONSE_BYTES",
    "PAYLOAD_ID_PATTERN",
    "content_id",
    "digest_payload",
    "endpoint_payload_id",
    "is_uint",
    "parse_and_sanitize_openrouter_endpoint_payload",
    "sha256_bytes",
    "valid_endpoint_tag",
    "valid_model_id",
]
