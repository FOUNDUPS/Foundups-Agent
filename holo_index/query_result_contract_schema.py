"""Load and structurally validate the canonical HoloIndex result contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


MACHINE_SPEC_PATH = (
    Path(__file__).resolve().parent
    / "docs"
    / "HOLO_INDEX_MACHINE_LANGUAGE_SPEC_0102.json"
)
_MAPPING_KEYS = (
    "hit_schemas", "bucket_schemas", "aliases", "counts",
    "hit_value_rules", "metadata_value_rules",
)
_CONTRACT_KEYS = frozenset({
    "response_keys", "metadata_keys", "collection_names", "collection_backends",
    *_MAPPING_KEYS,
})


def load_search_result_contract() -> Mapping[str, Any]:
    """Return the checked-in contract or a stable fail-closed error."""
    try:
        payload = json.loads(MACHINE_SPEC_PATH.read_text(encoding="utf-8"))
        contract = payload["contracts"]["search_response_contract"]
        _validate_structure(contract)
    except OSError as exc:
        raise RuntimeError("holoindex_machine_contract_unavailable") from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("holoindex_machine_contract_invalid") from exc
    return contract


def _validate_structure(contract: Any) -> None:
    if not isinstance(contract, Mapping) or set(contract) != _CONTRACT_KEYS:
        raise TypeError("machine contract mapping required")
    if any(not isinstance(contract.get(key), Mapping) for key in _MAPPING_KEYS):
        raise TypeError("machine contract child mapping required")
    response_keys = _string_set(contract["response_keys"])
    metadata_keys = _string_set(contract["metadata_keys"])
    _string_set(contract["collection_names"])
    _string_set(contract["collection_backends"])
    schemas = contract["hit_schemas"]
    if any(not isinstance(name, str) or not name for name in schemas):
        raise TypeError("hit schema name invalid")
    for schema in schemas.values():
        if not isinstance(schema, Mapping) or set(schema) != {"required", "optional"}:
            raise TypeError("hit schema mapping invalid")
        required = _string_set(schema["required"])
        optional = _string_set(schema["optional"], allow_empty=True)
        if not required or required & optional:
            raise TypeError("hit schema fields invalid")
    buckets = contract["bucket_schemas"]
    for bucket, families in buckets.items():
        if not isinstance(bucket, str) or bucket not in response_keys:
            raise TypeError("bucket response reference invalid")
        if not _string_set(families) <= set(schemas):
            raise TypeError("bucket schema reference invalid")
    if set(buckets) != response_keys - {"metadata"}:
        raise TypeError("bucket response coverage invalid")
    _validate_references(contract["aliases"], response_keys, set(buckets))
    _validate_references(contract["counts"], metadata_keys, set(buckets))


def _string_set(value: Any, *, allow_empty: bool = False) -> set[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise TypeError("unique string list required")
    if len(set(value)) != len(value) or (not allow_empty and not value):
        raise TypeError("unique string list required")
    return set(value)


def _validate_references(value: Mapping[Any, Any], keys: set[str], targets: set[str]) -> None:
    for key, target in value.items():
        if not isinstance(key, str) or not isinstance(target, str):
            raise TypeError("mapping reference must be a string")
        if key not in keys or target not in targets:
            raise TypeError("mapping reference invalid")


__all__ = ["MACHINE_SPEC_PATH", "load_search_result_contract"]
