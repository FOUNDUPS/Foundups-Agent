"""Executable contract for canonical HoloIndex search results."""

from __future__ import annotations

import math
import re
from typing import Any, Mapping, Sequence

from holo_index.query_result_contract_schema import load_search_result_contract

SEARCH_RESULT_CONTRACT = load_search_result_contract()
SEARCH_RESPONSE_KEYS = tuple(SEARCH_RESULT_CONTRACT["response_keys"])
SEARCH_METADATA_KEYS = tuple(SEARCH_RESULT_CONTRACT["metadata_keys"])
COLLECTION_NAMES = frozenset(SEARCH_RESULT_CONTRACT["collection_names"])
_BACKENDS = frozenset(SEARCH_RESULT_CONTRACT["collection_backends"])
_SCHEMAS = SEARCH_RESULT_CONTRACT["hit_schemas"]
_FAMILIES = {
    bucket: tuple(
        (frozenset(_SCHEMAS[name]["required"]), frozenset(_SCHEMAS[name]["optional"]))
        for name in names
    )
    for bucket, names in SEARCH_RESULT_CONTRACT["bucket_schemas"].items()
}
_ALIASES = SEARCH_RESULT_CONTRACT["aliases"]
_COUNTS = SEARCH_RESULT_CONTRACT["counts"]
_HIT_RULES = SEARCH_RESULT_CONTRACT["hit_value_rules"]
_METADATA_RULES = SEARCH_RESULT_CONTRACT["metadata_value_rules"]
_VALUE_RULE_IDS = frozenset({
    "finite_number", "finite_number_0_1", "positive_integer",
    "nonnegative_integer", "percent_string_0_100", "boolean",
    "collection_backend", "embedding_fingerprint", "string", "string_or_null",
})


def validate_search_result(result: Mapping[str, Any], *, expected_query: str) -> None:
    """Fail closed unless result exactly matches the canonical producer contract."""
    if not isinstance(result, Mapping) or set(result) != set(SEARCH_RESPONSE_KEYS):
        _reject()
    for bucket, families in _FAMILIES.items():
        _validate_bucket(result[bucket], families)
    metadata = _validate_metadata(result["metadata"], expected_query)
    if any(result[alias] != result[source] for alias, source in _ALIASES.items()):
        _reject()
    if any(metadata[key] != len(result[bucket]) for key, bucket in _COUNTS.items()):
        _reject()


def _validate_bucket(value: Any, families: Sequence[tuple[frozenset[str], frozenset[str]]]) -> None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        _reject()
    for item in value:
        if not isinstance(item, Mapping) or not any(
            required <= set(item) <= required | optional
            for required, optional in families
        ):
            _reject()
        _validate_hit_values(item)


def _validate_hit_values(item: Mapping[str, Any]) -> None:
    for key, value in item.items():
        _validate_value(_HIT_RULES.get(key, _HIT_RULES["default"]), value)


def _validate_metadata(value: Any, expected_query: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(SEARCH_METADATA_KEYS):
        _reject()
    for key, field in value.items():
        rule = _METADATA_RULES["field_rules"].get(key, _METADATA_RULES["default"])
        if isinstance(rule, str) and rule.startswith("map:"):
            _validate_map(field, rule.removeprefix("map:"))
        else:
            _validate_value(rule, field)
    if value["query"] != expected_query:
        _reject()
    return value


def _validate_map(value: Any, item_rule: str) -> None:
    if not isinstance(value, Mapping) or set(value) != COLLECTION_NAMES:
        _reject()
    for field in value.values():
        _validate_value(item_rule, field)


def _validate_value(rule: str, value: Any) -> None:
    if rule == "finite_number":
        _finite_number(value)
    elif rule == "finite_number_0_1":
        if not 0.0 <= _finite_number(value) <= 1.0:
            _reject()
    elif rule == "positive_integer":
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            _reject()
    elif rule == "nonnegative_integer":
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            _reject()
    elif rule == "percent_string_0_100":
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?%", value):
            _reject()
        if not 0.0 <= float(value[:-1]) <= 100.0:
            _reject()
    elif rule == "boolean":
        if not isinstance(value, bool):
            _reject()
    elif rule == "collection_backend":
        if not isinstance(value, str) or value not in _BACKENDS:
            _reject()
    elif rule == "embedding_fingerprint":
        if not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
            _reject()
    elif rule == "string":
        if not isinstance(value, str):
            _reject()
    elif rule == "string_or_null":
        if value is not None and not isinstance(value, str):
            _reject()
    else:
        _reject()


def _finite_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _reject()
    try:
        converted = float(value)
    except (OverflowError, ValueError):
        _reject()
    if not math.isfinite(converted):
        _reject()
    return converted


def _validate_declared_rules() -> None:
    schema_fields = {
        field
        for schema in _SCHEMAS.values()
        for group in (schema["required"], schema["optional"])
        for field in group
    }
    if not isinstance(_HIT_RULES, Mapping) or "default" not in _HIT_RULES:
        _contract_reject()
    if set(_HIT_RULES) - schema_fields - {"default"}:
        _contract_reject()
    if any(
        not isinstance(rule, str) or rule not in _VALUE_RULE_IDS
        for rule in _HIT_RULES.values()
    ):
        _contract_reject()
    if not isinstance(_METADATA_RULES, Mapping):
        _contract_reject()
    field_rules = _METADATA_RULES.get("field_rules")
    default_rule = _METADATA_RULES.get("default")
    if (
        not isinstance(field_rules, Mapping)
        or not isinstance(default_rule, str)
        or default_rule not in _VALUE_RULE_IDS
    ):
        _contract_reject()
    if set(field_rules) - set(SEARCH_METADATA_KEYS):
        _contract_reject()
    for rule in field_rules.values():
        if not isinstance(rule, str):
            _contract_reject()
        item_rule = rule.removeprefix("map:") if rule.startswith("map:") else rule
        if item_rule not in _VALUE_RULE_IDS:
            _contract_reject()


def _contract_reject() -> None:
    raise RuntimeError("holoindex_machine_contract_invalid")


def _reject() -> None:
    raise ValueError("query_evidence_schema_invalid")


_validate_declared_rules()


__all__ = ["COLLECTION_NAMES", "SEARCH_METADATA_KEYS", "SEARCH_RESPONSE_KEYS",
           "SEARCH_RESULT_CONTRACT", "validate_search_result"]
