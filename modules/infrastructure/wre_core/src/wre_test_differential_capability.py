"""Opaque admission for verifier-produced test differential evidence."""

from __future__ import annotations

import hashlib
import json
import threading
from typing import Any, Mapping
from weakref import WeakKeyDictionary


_MAX_DEPTH = 16
_MAX_ITEMS = 200_000
_MAX_STRING = 2 * 1024 * 1024
_BINDING_FIELDS = (
    "work_order_id", "slice_name", "worker_id", "verifier_id",
    "assurance_reservation_id", "assurance_reservation_digest",
    "verifier_task_id", "base_sha", "head_sha", "expected_changed_paths",
    "test_impact_policy", "bound_work_order", "exact_sha_commit_receipt",
    "signed_authority",
)


class ProducedTestDifferentialCapability:
    """One-use provenance proof for locally produced differential evidence."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "ProducedTestDifferentialCapability":
        raise TypeError("test_differential_capability_direct_construction_forbidden")

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("test_differential_capability_is_immutable")

    def __copy__(self) -> Any:
        raise TypeError("test_differential_capability_copy_forbidden")

    def __deepcopy__(self, _memo: Any) -> Any:
        raise TypeError("test_differential_capability_copy_forbidden")

    def __reduce__(self) -> Any:
        raise TypeError("test_differential_capability_pickle_forbidden")


_LOCK = threading.Lock()
_CAPABILITIES: WeakKeyDictionary[ProducedTestDifferentialCapability, tuple[str, str]] = (
    WeakKeyDictionary()
)


def issue_test_differential_capability(
    evidence: Mapping[str, Any], *, request: Mapping[str, Any]
) -> ProducedTestDifferentialCapability:
    """Bind one opaque capability to exact evidence and request context."""

    evidence_digest = bounded_canonical_digest(evidence)
    request_digest = bounded_canonical_digest(_request_binding(request))
    capability = object.__new__(ProducedTestDifferentialCapability)
    with _LOCK:
        _CAPABILITIES[capability] = (evidence_digest, request_digest)
    return capability


def consume_test_differential_capability(
    capability: Any, evidence: Mapping[str, Any], *, request: Mapping[str, Any]
) -> bool:
    """Consume one matching proof; malformed or replayed inputs fail closed."""

    if type(capability) is not ProducedTestDifferentialCapability:
        return False
    try:
        expected = (
            bounded_canonical_digest(evidence),
            bounded_canonical_digest(_request_binding(request)),
        )
    except (TypeError, ValueError, RecursionError):
        return False
    with _LOCK:
        recorded = _CAPABILITIES.get(capability)
        if recorded != expected:
            return False
        _CAPABILITIES.pop(capability, None)
    return True


def bounded_canonical_digest(value: Any) -> str:
    """Digest bounded JSON-compatible data without recursive blowups."""

    _validate_tree(value)
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _request_binding(request: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        raise TypeError("test_differential_request_must_be_mapping")
    return {name: request.get(name) for name in _BINDING_FIELDS}


def _validate_tree(root: Any) -> None:
    stack = [(root, 0)]
    count = 0
    while stack:
        value, depth = stack.pop()
        count += 1
        if count > _MAX_ITEMS or depth > _MAX_DEPTH:
            raise ValueError("test_differential_evidence_bounds_exceeded")
        if value is None or type(value) in {bool, int, float}:
            continue
        if isinstance(value, str):
            if len(value) > _MAX_STRING:
                raise ValueError("test_differential_string_bound_exceeded")
            continue
        if isinstance(value, Mapping):
            if not all(isinstance(key, str) for key in value):
                raise TypeError("test_differential_mapping_key_invalid")
            stack.extend((item, depth + 1) for item in value.values())
            continue
        if isinstance(value, (list, tuple)):
            stack.extend((item, depth + 1) for item in value)
            continue
        raise TypeError("test_differential_value_not_json_compatible")


__all__ = [
    "ProducedTestDifferentialCapability", "bounded_canonical_digest",
    "consume_test_differential_capability", "issue_test_differential_capability",
]
