"""Strict projection of optional provider-asserted execution controls."""

from __future__ import annotations

from typing import Any, Mapping


MAX_CONTEXT_LENGTH = 100_000_000
REASONING_EFFORTS = (
    "max",
    "xhigh",
    "high",
    "medium",
    "low",
    "minimal",
    "none",
)


def project_optional_controls(value: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if "reasoning" in value:
        reasoning = sanitize_reasoning_control(value["reasoning"])
        if reasoning:
            result["reasoning"] = reasoning
    if "top_provider" in value:
        top_provider = sanitize_top_provider_control(value["top_provider"])
        if top_provider:
            result["top_provider"] = top_provider
    return result


def sanitize_reasoning_control(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("record_invalid")
    result: dict[str, Any] = {}
    if "supported_efforts" in value:
        efforts = value["supported_efforts"]
        if efforts is not None:
            _validate_efforts(efforts)
        result["supported_efforts"] = (
            None if efforts is None else list(efforts)
        )
    if "default_effort" in value:
        effort = value["default_effort"]
        if effort is not None and (
            not isinstance(effort, str) or effort not in REASONING_EFFORTS
        ):
            raise ValueError("record_invalid")
        result["default_effort"] = effort
    for key in ("default_enabled", "supports_max_tokens", "mandatory"):
        if key in value:
            if type(value[key]) is not bool:
                raise ValueError("record_invalid")
            result[key] = value[key]
    _validate_reasoning_relationships(result)
    return result


def sanitize_top_provider_control(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("record_invalid")
    result: dict[str, Any] = {}
    for key in ("context_length", "max_completion_tokens"):
        if key in value:
            item = value[key]
            if item is not None and (
                type(item) is not int or not 0 < item <= MAX_CONTEXT_LENGTH
            ):
                raise ValueError("record_invalid")
            result[key] = item
    if (
        type(result.get("context_length")) is int
        and type(result.get("max_completion_tokens")) is int
        and result["max_completion_tokens"] > result["context_length"]
    ):
        raise ValueError("record_invalid")
    if "is_moderated" in value:
        if type(value["is_moderated"]) is not bool:
            raise ValueError("record_invalid")
        result["is_moderated"] = value["is_moderated"]
    return result


def _validate_efforts(value: Any) -> None:
    if not isinstance(value, list) or len(value) > len(REASONING_EFFORTS):
        raise ValueError("record_invalid")
    if any(
        not isinstance(item, str) or item not in REASONING_EFFORTS
        for item in value
    ):
        raise ValueError("record_invalid")
    positions = [REASONING_EFFORTS.index(item) for item in value]
    if positions != sorted(set(positions)):
        raise ValueError("record_invalid")


def _validate_reasoning_relationships(value: Mapping[str, Any]) -> None:
    efforts = value.get("supported_efforts")
    default = value.get("default_effort")
    if isinstance(efforts, list) and default is not None and default not in efforts:
        raise ValueError("record_invalid")
    if value.get("mandatory") is True and (
        value.get("default_enabled") is False
        or default == "none"
        or isinstance(efforts, list) and "none" in efforts
    ):
        raise ValueError("record_invalid")


__all__ = [
    "MAX_CONTEXT_LENGTH",
    "REASONING_EFFORTS",
    "project_optional_controls",
    "sanitize_reasoning_control",
    "sanitize_top_provider_control",
]
