"""Pure trust boundary for direct-provider catalog candidate snapshots."""
from __future__ import annotations
import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence
from .model_intelligence_catalog import ModelCatalogSnapshot, build_canonical_model_catalog
INVOCATION_SCHEMA = "model_provider_catalog_discovery_invocation.v1"
RECEIPT_SCHEMA = "model_provider_catalog_discovery_receipt.v1"
CANDIDATE_SCHEMA = "model_provider_catalog_candidate_snapshot.v1"
PROVIDER, ENDPOINT_ID = "openrouter", "openrouter_models_api_v1"
DEFAULT_FRESHNESS_MS = 86_400_000
MAX_RESPONSE_BYTES, MAX_RECORDS = 8 * 1024 * 1024, 2048
MAX_CONTEXT_LENGTH, MAX_PRICE = 100_000_000, Decimal("1000")
_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}/[a-z0-9][a-z0-9._/-]{0,126}(?::free)?\Z")
_TOKEN = re.compile(r"[a-z0-9][a-z0-9._:-]{0,63}\Z")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_CONTENT_ID = re.compile(r"[a-z0-9_.]+:[0-9a-f]{64}\Z")
_PRICE = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
_SECRET = re.compile(
    r"(?i)(?:bearer\s+\S+|(?:api[_-]?key|token|secret)\s*[:=]|"
    r"\bsk-[a-z0-9_-]{12,}\b|\bgh[opusr]_[a-z0-9_]{12,}\b|"
    r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.)"
)
_REASONS = frozenset(
    """completed transport_pending invocation_invalid scheduled_invocation_not_due
    scheduled_invocation_expired output_path_invalid precall_write_failed
    transport_timeout transport_failed redirect_rejected http_status_rejected
    content_type_rejected body_too_large json_invalid top_level_invalid
    record_limit_exceeded no_acceptable_records candidate_write_failed
    terminal_receipt_write_failed""".split()
)
_OUTCOMES = frozenset("BLOCKED_PRECALL INDETERMINATE COMPLETED FAILED".split())
_INVOCATION_KEYS = frozenset(
    "schema_version invocation_id mode schedule_id scheduled_for_ms expires_at_ms".split()
)
_RECEIPT_KEYS = frozenset(
    """schema_version receipt_id call_id invocation provider endpoint_id
    request_envelope_digest attempted outcome reason started_at_ms completed_at_ms
    http_status response_body_digest response_byte_count candidate_snapshot_id
    accepted_record_count rejected_record_count rejection_counts""".split()
)
_CANDIDATE_KEYS = frozenset(
    """schema_version snapshot_id provider endpoint_id catalog_payload_digest
    catalog_payload accepted_record_count rejected_record_count rejection_counts
    observed_at_ms fresh_until_ms observation_receipt trust_class""".split()
)
def _serialized(value: Any) -> dict[str, Any]:
    return json.loads(json.dumps(asdict(value), sort_keys=True, separators=(",", ":")))
@dataclass(frozen=True)
class DiscoveryInvocation:
    invocation_id: str
    mode: str
    schedule_id: str | None
    scheduled_for_ms: int | None
    expires_at_ms: int | None
    schema_version: str = field(init=False, default=INVOCATION_SCHEMA)
    def to_dict(self) -> dict[str, Any]:
        return _serialized(self)
@dataclass(frozen=True)
class DiscoveryReceipt:
    receipt_id: str
    call_id: str
    invocation: DiscoveryInvocation
    request_envelope_digest: str
    attempted: bool
    outcome: str
    reason: str
    started_at_ms: int
    completed_at_ms: int
    http_status: int | None
    response_body_digest: str | None
    response_byte_count: int | None
    candidate_snapshot_id: str | None
    accepted_record_count: int
    rejected_record_count: int
    rejection_counts: Mapping[str, int]
    provider: str = field(init=False, default=PROVIDER)
    endpoint_id: str = field(init=False, default=ENDPOINT_ID)
    schema_version: str = field(init=False, default=RECEIPT_SCHEMA)
    def to_dict(self) -> dict[str, Any]:
        return _serialized(self)
@dataclass(frozen=True)
class ProviderCatalogCandidateSnapshot:
    snapshot_id: str
    catalog_payload_digest: str
    catalog_payload: Mapping[str, Any]
    accepted_record_count: int
    rejected_record_count: int
    rejection_counts: Mapping[str, int]
    observed_at_ms: int
    fresh_until_ms: int
    observation_receipt: DiscoveryReceipt
    provider: str = field(init=False, default=PROVIDER)
    endpoint_id: str = field(init=False, default=ENDPOINT_ID)
    trust_class: str = field(init=False, default="provider_asserted_candidate_metadata")
    schema_version: str = field(init=False, default=CANDIDATE_SCHEMA)
    def to_dict(self) -> dict[str, Any]:
        return _serialized(self)
@dataclass(frozen=True)
class CatalogBridgeResult:
    candidate: ProviderCatalogCandidateSnapshot
    catalog_build_required: bool
    catalog_snapshot: ModelCatalogSnapshot | None
def build_discovery_invocation(
    *, mode: str, schedule_id: str | None = None,
    scheduled_for_ms: int | None = None, expires_at_ms: int | None = None,
) -> DiscoveryInvocation:
    body = {
        "schema_version": INVOCATION_SCHEMA, "mode": mode, "schedule_id": schedule_id,
        "scheduled_for_ms": scheduled_for_ms, "expires_at_ms": expires_at_ms,
    }
    body["invocation_id"] = _content_id("model_provider_catalog_discovery_invocation", body)
    return rehydrate_discovery_invocation(body)
def rehydrate_discovery_invocation(data: Mapping[str, Any]) -> DiscoveryInvocation:
    _exact(data, _INVOCATION_KEYS, "invocation_invalid")
    if data["schema_version"] != INVOCATION_SCHEMA or data["mode"] not in {"manual", "scheduled"}:
        raise ValueError("invocation_invalid")
    mode, schedule_id = data["mode"], data["schedule_id"]
    scheduled, expires = data["scheduled_for_ms"], data["expires_at_ms"]
    if mode == "manual" and any(value is not None for value in (schedule_id, scheduled, expires)):
        raise ValueError("invocation_invalid")
    if mode == "scheduled" and (
        not _token_string(schedule_id, 128) or not _uint(scheduled)
        or not _uint(expires) or scheduled > expires
    ):
        raise ValueError("invocation_invalid")
    expected = _content_id(
        "model_provider_catalog_discovery_invocation",
        {key: data[key] for key in _INVOCATION_KEYS if key != "invocation_id"},
    )
    if data["invocation_id"] != expected:
        raise ValueError("invocation_invalid")
    return DiscoveryInvocation(str(data["invocation_id"]), mode, schedule_id, scheduled, expires)
def admit_discovery_invocation(invocation: DiscoveryInvocation, *, now_ms: int) -> None:
    if not _uint(now_ms):
        raise ValueError("invocation_invalid")
    item = rehydrate_discovery_invocation(invocation.to_dict())
    if item.mode == "scheduled" and now_ms < item.scheduled_for_ms:
        raise ValueError("scheduled_invocation_not_due")
    if item.mode == "scheduled" and now_ms > item.expires_at_ms:
        raise ValueError("scheduled_invocation_expired")
def build_discovery_receipt(**values: Any) -> DiscoveryReceipt:
    invocation = values["invocation"]
    body = {
        "schema_version": RECEIPT_SCHEMA, "call_id": values["call_id"],
        "invocation": invocation.to_dict() if isinstance(invocation, DiscoveryInvocation) else invocation,
        "provider": PROVIDER, "endpoint_id": ENDPOINT_ID,
        "request_envelope_digest": values["request_envelope_digest"],
        "attempted": values["attempted"], "outcome": values["outcome"], "reason": values["reason"],
        "started_at_ms": values["started_at_ms"], "completed_at_ms": values["completed_at_ms"],
        "http_status": values.get("http_status"), "response_body_digest": values.get("response_body_digest"),
        "response_byte_count": values.get("response_byte_count"),
        "candidate_snapshot_id": values.get("candidate_snapshot_id"),
        "accepted_record_count": values.get("accepted_record_count", 0),
        "rejected_record_count": values.get("rejected_record_count", 0),
        "rejection_counts": values.get("rejection_counts", {}),
    }
    body["receipt_id"] = _content_id("model_provider_catalog_discovery_receipt", body)
    return rehydrate_discovery_receipt(body)
def rehydrate_discovery_receipt(data: Mapping[str, Any]) -> DiscoveryReceipt:
    _exact(data, _RECEIPT_KEYS, "discovery_receipt_invalid")
    invocation = rehydrate_discovery_invocation(_mapping(data["invocation"], "discovery_receipt_invalid"))
    if (data["schema_version"], data["provider"], data["endpoint_id"]) != (
        RECEIPT_SCHEMA, PROVIDER, ENDPOINT_ID
    ):
        raise ValueError("discovery_receipt_invalid")
    if not _token_string(data["call_id"], 160) or not _DIGEST.fullmatch(str(data["request_envelope_digest"])):
        raise ValueError("discovery_receipt_invalid")
    outcome, attempted, reason = data["outcome"], data["attempted"], data["reason"]
    if outcome not in _OUTCOMES or type(attempted) is not bool or reason not in _REASONS:
        raise ValueError("discovery_receipt_invalid")
    if (outcome == "BLOCKED_PRECALL" and attempted) or (outcome in {"COMPLETED", "FAILED"} and not attempted):
        raise ValueError("discovery_receipt_invalid")
    started, completed = data["started_at_ms"], data["completed_at_ms"]
    if not _uint(started) or not _uint(completed) or completed < started:
        raise ValueError("discovery_receipt_invalid")
    status = data["http_status"]
    if status is not None and (type(status) is not int or not 100 <= status <= 599):
        raise ValueError("discovery_receipt_invalid")
    digest, size = data["response_body_digest"], data["response_byte_count"]
    if (digest is None) != (size is None) or (digest is not None and not _DIGEST.fullmatch(str(digest))):
        raise ValueError("discovery_receipt_invalid")
    if size is not None and (not _uint(size) or size > MAX_RESPONSE_BYTES):
        raise ValueError("discovery_receipt_invalid")
    snapshot_id = data["candidate_snapshot_id"]
    if snapshot_id is not None and not _CONTENT_ID.fullmatch(str(snapshot_id)):
        raise ValueError("discovery_receipt_invalid")
    accepted, rejected, counts = data["accepted_record_count"], data["rejected_record_count"], _counts(data["rejection_counts"])
    if not _uint(accepted) or not _uint(rejected) or rejected != sum(counts.values()):
        raise ValueError("discovery_receipt_invalid")
    if outcome == "COMPLETED" and (reason != "completed" or snapshot_id is None or accepted == 0):
        raise ValueError("discovery_receipt_invalid")
    expected = _content_id(
        "model_provider_catalog_discovery_receipt",
        {key: data[key] for key in _RECEIPT_KEYS if key != "receipt_id"},
    )
    if data["receipt_id"] != expected:
        raise ValueError("discovery_receipt_invalid")
    return DiscoveryReceipt(
        str(data["receipt_id"]), str(data["call_id"]), invocation, str(data["request_envelope_digest"]),
        attempted, outcome, reason, started, completed, status, digest, size, snapshot_id,
        accepted, rejected, counts,
    )
def parse_and_sanitize_openrouter_catalog(raw: bytes) -> tuple[dict[str, Any], int, Mapping[str, int]]:
    if not isinstance(raw, bytes) or len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("body_too_large")
    try:
        payload = json.loads(
            raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique_object,
            parse_constant=_invalid_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
        raise ValueError("json_invalid") from None
    if not isinstance(payload, Mapping) or not isinstance(payload.get("data"), list):
        raise ValueError("top_level_invalid")
    if len(payload["data"]) > MAX_RECORDS:
        raise ValueError("record_limit_exceeded")
    _bound_json(payload)
    return sanitize_openrouter_catalog_payload(payload)
def sanitize_openrouter_catalog_payload(payload: Mapping[str, Any]) -> tuple[dict[str, Any], int, Mapping[str, int]]:
    records = payload.get("data")
    if not isinstance(records, list):
        raise ValueError("top_level_invalid")
    groups: dict[str, list[dict[str, Any] | None]] = {}
    ungrouped = 0
    for raw in records:
        if not isinstance(raw, Mapping) or not _valid_model_id(raw.get("id")):
            ungrouped += 1
            continue
        try:
            item = _sanitize_record(raw)
        except ValueError:
            item = None
        groups.setdefault(raw["id"], []).append(item)
    accepted, counts = [], ({"record_invalid": ungrouped} if ungrouped else {})
    for members in groups.values():
        if any(item is None for item in members):
            key = "duplicate_group_poisoned" if len(members) > 1 else "record_invalid"
            count = len(members)
        elif any(item != members[0] for item in members[1:]):
            key, count = "duplicate_id_conflict", len(members)
        else:
            accepted.append(members[0])
            key, count = "duplicate_identical_collapsed", len(members) - 1
        if count:
            counts[key] = counts.get(key, 0) + count
    if not accepted:
        raise ValueError("no_acceptable_records")
    accepted.sort(key=lambda item: item["id"])
    return {"data": accepted}, len(records) - len(accepted), dict(sorted(counts.items()))
def build_candidate_snapshot(
    *, catalog_payload: Mapping[str, Any], rejected_record_count: int,
    rejection_counts: Mapping[str, int], observed_at_ms: int,
    observation_receipt: DiscoveryReceipt, freshness_ms: int = DEFAULT_FRESHNESS_MS,
) -> ProviderCatalogCandidateSnapshot:
    payload, _, _ = sanitize_openrouter_catalog_payload(catalog_payload)
    snapshot_id = _candidate_id(payload)
    if observation_receipt.candidate_snapshot_id != snapshot_id or freshness_ms != DEFAULT_FRESHNESS_MS:
        raise ValueError("candidate_snapshot_invalid")
    data = {
        "schema_version": CANDIDATE_SCHEMA, "snapshot_id": snapshot_id,
        "provider": PROVIDER, "endpoint_id": ENDPOINT_ID,
        "catalog_payload_digest": _sha256(payload), "catalog_payload": payload,
        "accepted_record_count": len(payload["data"]), "rejected_record_count": rejected_record_count,
        "rejection_counts": dict(sorted(rejection_counts.items())), "observed_at_ms": observed_at_ms,
        "fresh_until_ms": observed_at_ms + freshness_ms,
        "observation_receipt": observation_receipt.to_dict(),
        "trust_class": "provider_asserted_candidate_metadata",
    }
    return rehydrate_candidate_snapshot(data, now_ms=observed_at_ms)
def rehydrate_candidate_snapshot(
    data: Mapping[str, Any], *, now_ms: int,
) -> ProviderCatalogCandidateSnapshot:
    _exact(data, _CANDIDATE_KEYS, "candidate_snapshot_invalid")
    if (data["schema_version"], data["provider"], data["endpoint_id"], data["trust_class"]) != (
        CANDIDATE_SCHEMA, PROVIDER, ENDPOINT_ID, "provider_asserted_candidate_metadata"
    ):
        raise ValueError("candidate_snapshot_invalid")
    payload, _, _ = sanitize_openrouter_catalog_payload(
        _mapping(data["catalog_payload"], "candidate_snapshot_invalid")
    )
    if payload != data["catalog_payload"] or data["catalog_payload_digest"] != _sha256(payload):
        raise ValueError("candidate_snapshot_invalid")
    if data["snapshot_id"] != _candidate_id(payload):
        raise ValueError("candidate_snapshot_invalid")
    accepted, rejected, counts = data["accepted_record_count"], data["rejected_record_count"], _counts(data["rejection_counts"])
    observed, fresh = data["observed_at_ms"], data["fresh_until_ms"]
    if accepted != len(payload["data"]) or not _uint(rejected) or rejected != sum(counts.values()):
        raise ValueError("candidate_snapshot_invalid")
    if (not _uint(observed) or observed > 253_402_300_799_999
            or fresh != observed + DEFAULT_FRESHNESS_MS or not _uint(now_ms) or now_ms > fresh):
        raise ValueError("candidate_snapshot_stale")
    receipt = rehydrate_discovery_receipt(_mapping(data["observation_receipt"], "candidate_snapshot_invalid"))
    if receipt.outcome != "COMPLETED" or receipt.candidate_snapshot_id != data["snapshot_id"]:
        raise ValueError("candidate_snapshot_invalid")
    if receipt.completed_at_ms != observed or (
        receipt.accepted_record_count, receipt.rejected_record_count, dict(receipt.rejection_counts)
    ) != (accepted, rejected, counts):
        raise ValueError("candidate_snapshot_invalid")
    return ProviderCatalogCandidateSnapshot(
        str(data["snapshot_id"]), str(data["catalog_payload_digest"]), payload, accepted,
        rejected, counts, observed, fresh, receipt,
    )
def bridge_candidate_to_canonical_catalog(
    candidate: Mapping[str, Any] | ProviderCatalogCandidateSnapshot, *, now_ms: int,
    prior_admitted_candidate_id: str | None = None,
) -> CatalogBridgeResult:
    raw = candidate.to_dict() if isinstance(candidate, ProviderCatalogCandidateSnapshot) else candidate
    item = rehydrate_candidate_snapshot(raw, now_ms=now_ms)
    if prior_admitted_candidate_id is not None:
        if not _CONTENT_ID.fullmatch(prior_admitted_candidate_id):
            raise ValueError("prior_candidate_id_invalid")
        if prior_admitted_candidate_id == item.snapshot_id:
            return CatalogBridgeResult(item, False, None)
    generated = datetime.fromtimestamp(item.observed_at_ms / 1000, tz=timezone.utc).isoformat()
    catalog = build_canonical_model_catalog(
        static_registry=False, openrouter_payload=item.catalog_payload,
        source_receipts=(item.observation_receipt.receipt_id,), generated_at=generated,
    )
    return CatalogBridgeResult(item, True, catalog)
def candidate_snapshot_id(catalog_payload: Mapping[str, Any]) -> str:
    payload, _, _ = sanitize_openrouter_catalog_payload(catalog_payload)
    return _candidate_id(payload)
def sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"
def _sanitize_record(raw: Mapping[str, Any]) -> dict[str, Any]:
    pricing, architecture = raw.get("pricing", {}), raw.get("architecture", {})
    if not isinstance(pricing, Mapping) or not isinstance(architecture, Mapping):
        raise ValueError("record_invalid")
    result: dict[str, Any] = {"id": raw["id"]}
    if "context_length" in raw:
        value = raw["context_length"]
        if type(value) is not int or not 0 < value <= MAX_CONTEXT_LENGTH:
            raise ValueError("record_invalid")
        result["context_length"] = value
    result["pricing"] = {
        key: _canonical_price(pricing[key]) for key in ("prompt", "completion") if key in pricing
    }
    result["architecture"] = {
        key: list(_tokens(architecture.get(key, [])))
        for key in ("input_modalities", "output_modalities")
    }
    result["supported_parameters"] = list(_tokens(raw.get("supported_parameters", [])))
    return result
def _canonical_price(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 64 or not _PRICE.fullmatch(value):
        raise ValueError("record_invalid")
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ValueError("record_invalid") from None
    if not number.is_finite() or number < 0 or number > MAX_PRICE:
        raise ValueError("record_invalid")
    fixed = format(number, "f")
    return (fixed.rstrip("0").rstrip(".") if "." in fixed else fixed) or "0"
def _tokens(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > 64:
        raise ValueError("record_invalid")
    normalized: set[str] = set()
    for item in value:
        if not isinstance(item, str) or len(item) > 64 or _SECRET.search(item):
            raise ValueError("record_invalid")
        token = item.strip().lower().replace(" ", "_")
        if not _TOKEN.fullmatch(token):
            raise ValueError("record_invalid")
        normalized.add(token)
    return tuple(sorted(normalized))
def _bound_json(value: Any, *, depth: int = 0) -> None:
    if depth > 12 or isinstance(value, str) and len(value) > 4096:
        raise ValueError("json_invalid")
    if isinstance(value, list):
        if len(value) > MAX_RECORDS:
            raise ValueError("json_invalid")
        for item in value:
            _bound_json(item, depth=depth + 1)
    elif isinstance(value, Mapping):
        if len(value) > 128:
            raise ValueError("json_invalid")
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > 256:
                raise ValueError("json_invalid")
            _bound_json(item, depth=depth + 1)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("json_invalid")
def _unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result
def _invalid_constant(_value: str) -> None:
    raise ValueError("invalid_json_constant")
def _candidate_id(payload: Mapping[str, Any]) -> str:
    return _content_id("model_provider_catalog_candidate_snapshot", {
        "schema_version": CANDIDATE_SCHEMA, "provider": PROVIDER,
        "endpoint_id": ENDPOINT_ID, "catalog_payload": payload,
    })
def _sha256(value: Any) -> str:
    return sha256_bytes(_canonical(value))
def _content_id(prefix: str, value: Any) -> str:
    return f"{prefix}:{hashlib.sha256(_canonical(value)).hexdigest()}"
def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
def _counts(value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping) or len(value) > 32:
        raise ValueError("counts_invalid")
    if any(not _token_string(key, 80) or not _uint(count) for key, count in value.items()):
        raise ValueError("counts_invalid")
    return dict(sorted((str(key), count) for key, count in value.items()))
def _valid_model_id(value: Any) -> bool:
    return (
        isinstance(value, str) and len(value) <= 200
        and _ID.fullmatch(value) is not None and not _SECRET.search(value)
    )
def _exact(value: Any, keys: frozenset[str], reason: str) -> None:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(reason)
def _mapping(value: Any, reason: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(reason)
    return value
def _uint(value: Any) -> bool:
    return type(value) is int and value >= 0
def _token_string(value: Any, limit: int) -> bool:
    return isinstance(value, str) and 0 < len(value) <= limit and not _SECRET.search(value)
__all__ = [
    "CatalogBridgeResult", "DiscoveryInvocation", "DiscoveryReceipt",
    "ProviderCatalogCandidateSnapshot", "admit_discovery_invocation",
    "bridge_candidate_to_canonical_catalog", "build_candidate_snapshot",
    "build_discovery_invocation", "build_discovery_receipt", "candidate_snapshot_id",
    "parse_and_sanitize_openrouter_catalog", "rehydrate_candidate_snapshot",
    "rehydrate_discovery_invocation", "rehydrate_discovery_receipt",
    "sanitize_openrouter_catalog_payload", "sha256_bytes",
]
