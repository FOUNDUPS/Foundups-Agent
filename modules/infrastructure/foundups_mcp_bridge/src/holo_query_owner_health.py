"""Authenticated health parsing for the private Holo query owner."""

from __future__ import annotations

import http.client
import json
from dataclasses import dataclass

from holo_index.retrieval_runtime_binding import (
    is_retrieval_ranker_digest,
    is_retrieval_runtime_digest,
)

from .holo_query_binding import parse_exact_binding
from .holo_query_replica_binding import parse_replica_binding
from .holo_query_semantic_proof import PRODUCER_FAILURE_CODES
from .holo_query_transport import (
    OWNER_HOST, exact_bearer_token, normalize_health_transport,
)


HEALTH_PATH = "/holoindex/v1/health"
HEALTH_SCHEMA_VERSION = "holoindex_query_service.v1"
MAX_HEALTH_RESPONSE_BYTES = 65_536
MAX_HEALTH_JSON_DEPTH = 128
BINDING_MISMATCH_ERROR = "HOLOINDEX_QUERY_SERVICE_BINDING_MISMATCH"
EMPTY_BINDING = ("", "", "", "")


@dataclass(frozen=True)
class AuthenticatedOwnerHealthProof:
    ready: bool
    rejection: str
    binding: tuple[str, str, str, str]
    replica_binding: tuple[str, str, str, str] = EMPTY_BINDING
    runtime_environment_digest: str = ""


class _InvalidHealthJson(ValueError):
    pass


def _exact_health_payload(value: object) -> dict[str, object] | None:
    return value if type(value) is dict else None


def _health_json_depth_allowed(body: bytes) -> bool:
    depth = 0
    in_string = False
    escaped = False
    for byte in body:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:
                escaped = True
            elif byte == 0x22:
                in_string = False
            continue
        if byte == 0x22:
            in_string = True
        elif byte in {0x5B, 0x7B}:
            depth += 1
            if depth > MAX_HEALTH_JSON_DEPTH:
                return False
        elif byte in {0x5D, 0x7D}:
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and not in_string and not escaped


def _decode_health_payload(body: bytes) -> dict[str, object] | None:
    def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise _InvalidHealthJson("duplicate health JSON key")
            result[key] = value
        return result

    def reject_constant(_value: str) -> None:
        raise _InvalidHealthJson("nonstandard health JSON constant")

    if not _health_json_depth_allowed(body):
        return None
    try:
        value = json.loads(
            body.decode("utf-8"), object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except (
        UnicodeError, json.JSONDecodeError, _InvalidHealthJson, RecursionError,
    ):
        return None
    return _exact_health_payload(value)


def _read_health_payload(
    connection: http.client.HTTPConnection, token: str,
) -> dict[str, object] | None:
    bearer = exact_bearer_token(token)
    if bearer is None:
        return None
    connection.request("GET", HEALTH_PATH, headers={
        "Authorization": f"Bearer {bearer}", "Accept": "application/json",
        "Connection": "close",
    })
    response = connection.getresponse()
    body = response.read(MAX_HEALTH_RESPONSE_BYTES + 1)
    if response.status not in {200, 400, 409, 503, 504} or len(body) > MAX_HEALTH_RESPONSE_BYTES:
        return None
    return _decode_health_payload(body)


def _health_binding(payload: object) -> tuple[str, str, str, str]:
    value = _exact_health_payload(payload)
    if value is None:
        return EMPTY_BINDING
    candidate = tuple(value.get(key) for key in (
        "repo_head_sha", "repo_root_digest", "freshness_generation_id",
        "freshness_receipt_digest",
    ))
    return parse_exact_binding(candidate) or EMPTY_BINDING


def _exact_text(value: object, expected: str) -> bool:
    return type(value) is str and value == expected


def _ready_metadata_contract(value: dict[str, object]) -> bool:
    stale_reasons = value.get("stale_reasons")
    return all((
        _exact_text(value.get("schema_version"), HEALTH_SCHEMA_VERSION),
        value.get("ok") is True,
        _exact_text(value.get("source"), "holoindex"),
        _exact_text(value.get("status"), "ready"),
        value.get("loopback_only") is True,
        _exact_text(value.get("freshness"), "CURRENT"),
        _exact_text(value.get("error"), ""),
        type(stale_reasons) is list and len(stale_reasons) == 0,
        value.get("index_gap_detected") is False,
        value.get("no_holoindex_reindex_performed") is True,
        _exact_text(value.get("retrieval_mode"), "semantic"),
        is_retrieval_ranker_digest(value.get("retrieval_runtime_ranker_digest")),
        is_retrieval_runtime_digest(value.get("runtime_environment_digest")),
    ))


def _health_replica_binding(
    payload: object,
) -> tuple[str, str, str, str]:
    value = _exact_health_payload(payload)
    if value is None:
        return EMPTY_BINDING
    candidate = tuple(value.get(key) for key in (
        "query_replica_descriptor_digest", "query_replica_generation_id",
        "query_replica_id", "query_replica_path_identity_digest",
    ))
    return parse_replica_binding(candidate) or EMPTY_BINDING


def _health_runtime_environment_digest(payload: object) -> str:
    value = _exact_health_payload(payload)
    digest = value.get("runtime_environment_digest") if value is not None else ""
    return str(digest) if is_retrieval_runtime_digest(digest) else ""


def _health_contract_ready(
    payload: object, *, expected_repo_head_sha: str,
    expected_repo_root_digest: str, expected_generation_id: str,
    expected_receipt_digest: str,
    expected_replica_binding: tuple[str, str, str, str] = EMPTY_BINDING,
    expected_runtime_environment_digest: str = "",
) -> bool:
    value = _exact_health_payload(payload)
    if value is None:
        return False
    expected = parse_exact_binding((
        expected_repo_head_sha, expected_repo_root_digest,
        expected_generation_id, expected_receipt_digest,
    ), allow_empty_fields=True)
    expected_replica = parse_replica_binding(expected_replica_binding)
    if expected is None or expected_replica is None:
        return False
    actual = _health_binding(value)
    actual_replica = _health_replica_binding(value)
    actual_runtime = _health_runtime_environment_digest(value)
    contract = (
        _ready_metadata_contract(value),
        actual != EMPTY_BINDING,
        actual_replica != EMPTY_BINDING,
        bool(actual_runtime),
    )
    matches = tuple(not wanted or wanted == found for wanted, found in zip(
        expected + expected_replica,
        actual + actual_replica,
    ))
    runtime_matches = (
        not expected_runtime_environment_digest
        or expected_runtime_environment_digest == actual_runtime
    )
    return all(contract + matches + (runtime_matches,))


def _health_rejection_code(payload: object) -> str:
    value = _exact_health_payload(payload)
    if value is None:
        return ""
    raw_error = value.get("error")
    error = raw_error if type(raw_error) is str else ""
    terminal = {
        "QUERY_OWNER_POISONED", "QUERY_TIMEOUT", "SEMANTIC_BACKEND_UNAVAILABLE",
        *PRODUCER_FAILURE_CODES, "SEMANTIC_CANARY_EMPTY",
        "MISSING_GENERATION_BINDING", "REPO_HEAD_MISMATCH", "STALE_INDEX",
        "GENERATION_CHANGED_DURING_QUERY", "QUERY_REPLICA_INVALID",
        "QUERY_REPLICA_CHANGED",
    }
    valid = (
        _exact_text(value.get("schema_version"), HEALTH_SCHEMA_VERSION)
        and value.get("ok") is False
        and _exact_text(value.get("source"), "holoindex")
        and value.get("loopback_only") is True
        and value.get("no_holoindex_reindex_performed") is True
    )
    return error if valid and error in terminal else ""


def _health_binding_rejection_code(
    payload: object, *, expected_repo_head_sha: str,
    expected_repo_root_digest: str, expected_generation_id: str,
    expected_receipt_digest: str,
    expected_replica_binding: tuple[str, str, str, str] = EMPTY_BINDING,
    expected_runtime_environment_digest: str = "",
) -> str:
    expected = parse_exact_binding((
        expected_repo_head_sha, expected_repo_root_digest,
        expected_generation_id, expected_receipt_digest,
    ), allow_empty_fields=True)
    expected_replica = parse_replica_binding(expected_replica_binding)
    if expected is None or expected_replica is None:
        return BINDING_MISMATCH_ERROR
    value = _exact_health_payload(payload)
    if value is None:
        return ""
    actual_canonical = _health_binding(value)
    if not _ready_metadata_contract(value):
        return ""
    actual_replica = _health_replica_binding(value)
    actual_runtime = _health_runtime_environment_digest(value)
    actual = actual_canonical + actual_replica
    wanted_binding = expected + expected_replica
    binding_invalid = (
        actual_canonical == EMPTY_BINDING or actual_replica == EMPTY_BINDING
        or not actual_runtime
    )
    mismatch = any(
        wanted and wanted != found for wanted, found in zip(wanted_binding, actual)
    ) or bool(
        expected_runtime_environment_digest
        and expected_runtime_environment_digest != actual_runtime
    )
    return BINDING_MISMATCH_ERROR if binding_invalid or mismatch else ""


def _close_health_connection(connection: http.client.HTTPConnection) -> None:
    """Preserve the decided proof across expected transport-close failures."""

    try:
        connection.close()
    except (OSError, http.client.HTTPException):
        pass


def _health_exchange_proof(
    payload: object,
    expected: tuple[str, str, str, str],
    expected_replica: tuple[str, str, str, str],
    expected_runtime_environment_digest: str,
) -> AuthenticatedOwnerHealthProof:
    binding = _health_binding(payload)
    replica = _health_replica_binding(payload)
    runtime_digest = _health_runtime_environment_digest(payload)
    kwargs = dict(
        expected_repo_head_sha=expected[0],
        expected_repo_root_digest=expected[1],
        expected_generation_id=expected[2],
        expected_receipt_digest=expected[3],
        expected_replica_binding=expected_replica,
        expected_runtime_environment_digest=expected_runtime_environment_digest,
    )
    if payload is not None and _health_contract_ready(payload, **kwargs):
        return AuthenticatedOwnerHealthProof(True, "", binding, replica, runtime_digest)
    rejection = _health_rejection_code(payload) or _health_binding_rejection_code(
        payload, **kwargs
    )
    return AuthenticatedOwnerHealthProof(
        False, rejection, binding, replica, runtime_digest
    )


def _authenticated_health_exchange(
    *, host: str, port: int, token: str, timeout_seconds: float,
    expected_repo_head_sha: str = "", expected_repo_root_digest: str = "",
    expected_generation_id: str = "", expected_receipt_digest: str = "",
    expected_replica_binding: tuple[str, str, str, str] = EMPTY_BINDING,
    expected_runtime_environment_digest: str = "",
) -> AuthenticatedOwnerHealthProof:
    unavailable = AuthenticatedOwnerHealthProof(False, "", EMPTY_BINDING)
    expected = parse_exact_binding((
        expected_repo_head_sha, expected_repo_root_digest,
        expected_generation_id, expected_receipt_digest,
    ), allow_empty_fields=True)
    if expected is None:
        return AuthenticatedOwnerHealthProof(
            False, BINDING_MISMATCH_ERROR, EMPTY_BINDING
        )
    expected_replica = parse_replica_binding(expected_replica_binding)
    if expected_replica is None:
        return AuthenticatedOwnerHealthProof(
            False, BINDING_MISMATCH_ERROR, EMPTY_BINDING
        )
    transport = normalize_health_transport(
        host=host, port=port, token=token, timeout_seconds=timeout_seconds,
    )
    if transport is None:
        return unavailable
    connection = http.client.HTTPConnection(
        transport.host, transport.port, timeout=transport.timeout_seconds,
    )
    try:
        payload = _read_health_payload(connection, transport.token)
        return _health_exchange_proof(
            payload, expected, expected_replica,
            expected_runtime_environment_digest,
        )
    except (OSError, http.client.HTTPException, UnicodeError, ValueError, json.JSONDecodeError):
        return unavailable
    finally:
        _close_health_connection(connection)


def _authenticated_health_probe(**kwargs: object) -> bool:
    return _authenticated_health_exchange(**kwargs).ready  # type: ignore[arg-type]


def _authenticated_health_rejection(**kwargs: object) -> str:
    return _authenticated_health_exchange(**kwargs).rejection  # type: ignore[arg-type]


__all__ = [
    "AuthenticatedOwnerHealthProof", "BINDING_MISMATCH_ERROR",
    "HEALTH_SCHEMA_VERSION", "MAX_HEALTH_JSON_DEPTH", "MAX_HEALTH_RESPONSE_BYTES",
    "_authenticated_health_exchange", "_authenticated_health_probe",
    "_authenticated_health_rejection", "_health_binding_rejection_code",
    "_health_contract_ready", "_health_rejection_code",
]
