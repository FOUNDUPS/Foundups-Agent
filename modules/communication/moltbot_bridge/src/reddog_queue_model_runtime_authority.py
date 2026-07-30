"""Model-runtime lineage validation for RedDog queue authority requests."""

from __future__ import annotations

from typing import Any, Mapping


def model_runtime_authority_fields(
    source: Mapping[str, Any],
) -> dict[str, str]:
    return {
        f"{prefix}_{suffix}": str(source.get(f"{prefix}_{suffix}") or "")
        for prefix in (
            "model_runtime_binding",
            "model_runtime_binding_verification",
        )
        for suffix in ("receipt_id", "digest")
    }


def materialized_model_runtime_authority_fields(
    source: Mapping[str, Any],
) -> dict[str, Any]:
    """Project the signed model lineage into a materialized work order."""

    fields: dict[str, Any] = {}
    for prefix in (
        "model_selection",
        "model_runtime_binding",
        "model_runtime_binding_verification",
    ):
        receipt = source.get(f"{prefix}_receipt")
        fields[f"{prefix}_receipt"] = dict(receipt) if isinstance(receipt, Mapping) else {}
        fields[f"{prefix}_receipt_id"] = str(source.get(f"{prefix}_receipt_id") or "")
        fields[f"{prefix}_digest"] = str(source.get(f"{prefix}_digest") or "")
    return fields


def model_runtime_authority_values_valid(source: Mapping[str, Any]) -> bool:
    fields = model_runtime_authority_fields(source)
    binding = _fields_pair(fields, "model_runtime_binding")
    verification = _fields_pair(
        fields,
        "model_runtime_binding_verification",
    )
    if not any((*binding, *verification)):
        return True
    return (
        binding[0].startswith("reddog_model_runtime_binding:")
        and binding[1].startswith("sha256:")
        and verification[0].startswith(
            "model_runtime_binding_verification:"
        )
        and verification[1].startswith("sha256:")
    )


def validate_queue_model_runtime_authority(
    queue_receipt: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> bool:
    queue_binding = _pair(queue_receipt, "model_runtime_binding")
    profile_binding = _profile_pair(profile, "model_runtime_binding")
    queue_verification = _pair(
        queue_receipt, "model_runtime_binding_verification"
    )
    profile_verification = _profile_pair(
        profile, "model_runtime_binding_verification"
    )
    if not any((*queue_binding, *profile_binding)):
        return not any((*queue_verification, *profile_verification))
    return (
        queue_binding[0].startswith("reddog_model_runtime_binding:")
        and queue_binding[1].startswith("sha256:")
        and profile_binding == queue_binding
        and queue_verification[0].startswith(
            "model_runtime_binding_verification:"
        )
        and queue_verification[1].startswith("sha256:")
        and profile_verification == queue_verification
    )


def _pair(source: Mapping[str, Any], prefix: str) -> tuple[str, str]:
    return (
        str(source.get(f"{prefix}_receipt_id") or ""),
        str(source.get(f"{prefix}_digest") or ""),
    )


def _fields_pair(source: Mapping[str, str], prefix: str) -> tuple[str, str]:
    return (
        source[f"{prefix}_receipt_id"],
        source[f"{prefix}_digest"],
    )


def _profile_pair(
    profile: Mapping[str, Any],
    prefix: str,
) -> tuple[str, str]:
    context = profile.get("operational_context_binding")
    binding = context if isinstance(context, Mapping) else {}
    return (
        str(
            profile.get(f"{prefix}_receipt_id")
            or binding.get(f"{prefix}_receipt_id")
            or ""
        ),
        str(
            profile.get(f"{prefix}_digest")
            or binding.get(f"{prefix}_digest")
            or ""
        ),
    )


__all__ = [
    "materialized_model_runtime_authority_fields",
    "model_runtime_authority_fields",
    "model_runtime_authority_values_valid",
    "validate_queue_model_runtime_authority",
]
