"""Typed contract for authenticated, FoundUp-scoped RedDog conversation state."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from modules.foundups.agent.src.kanban_plugin_contract import redact_sensitive
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_digest import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_revision import (
    REVISION_RECEIPT_FIELDS,
    REVISION_RECEIPT_SCHEMA,
    valid_revision_receipts,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_kind import (
    SCOPE_KIND_FOUNDUP,
    scope_record_reasons,
)


SCHEMA_VERSION = "reddog_authenticated_conversation_scope.v4"
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
HEAD_RE = re.compile(r"^[0-9a-f]{7,64}$")
MAX_TEXT = 720
MAX_ITEMS = 32
MAX_EVIDENCE_REFS = 64
ITEM_KINDS = frozenset(
    {"operator_statement", "repository_fact", "model_inference", "unresolved"}
)
IMMUTABLE_FIELDS = frozenset(
    {
        "schema_version", "conversation_id", "scope_kind", "principal_id", "principal_provider",
        "verified_subject_digest", "principal_record_digest", "principal_key_fingerprint",
        "transport", "session_binding_digest", "authorized_foundup_id", "created_at",
        "credential_id", "session_id", "repo_full_name",
        "initial_turn_request_binding_digest",
    }
)
MUTABLE_FIELDS = frozenset(
    {
        "conversation_revision", "turn_id", "parent_turn_id", "discussion_foundup_ids",
        "active_topic", "current_objective", "accepted_decisions", "rejected_options",
        "open_questions", "repository_evidence_refs", "source_snapshot_id",
        "source_snapshot_digest", "last_grounded_head_sha", "holoindex_generation_id",
        "holoindex_freshness_receipt_id", "grounding_receipt_id", "pending_work_proposal_id",
        "pending_work_proposal_digest", "updated_at", "expires_at", "revision_receipts",
        "record_auth_scheme", "record_auth_signature",
        "record_auth_signer_public_key", "record_auth_key_fingerprint",
        "record_auth_key_epoch", "record_auth_nonce", "record_auth_audit_mac",
        "record_auth_audit_attestation_signature",
        "previous_record_auth_signature_digest", "record_digest",
    }
)
RECORD_FIELDS = IMMUTABLE_FIELDS | MUTABLE_FIELDS
AUTH_RESPONSE_FIELDS = frozenset(
    {
        "record_auth_signature", "record_auth_signer_public_key",
        "record_auth_key_fingerprint", "record_auth_key_epoch",
        "record_auth_audit_mac", "record_auth_audit_attestation_signature",
    }
)
UNSIGNED_RECORD_FIELDS = RECORD_FIELDS - AUTH_RESPONSE_FIELDS - {"record_digest"}
INTEGER_FIELDS = frozenset(
    {"conversation_revision", "created_at", "updated_at", "expires_at"}
)
STRING_LIST_FIELDS = frozenset(
    {"discussion_foundup_ids", "repository_evidence_refs"}
)
ITEM_LIST_FIELDS = frozenset(
    {"accepted_decisions", "rejected_options", "open_questions"}
)
LIST_FIELDS = STRING_LIST_FIELDS | ITEM_LIST_FIELDS | {"revision_receipts"}
STRING_FIELDS = RECORD_FIELDS - INTEGER_FIELDS - LIST_FIELDS


def sanitized_text(value: Any, *, limit: int = MAX_TEXT) -> str:
    text = redact_sensitive(str(value or "")).strip()
    if "\x00" in text or any(ord(char) < 32 and char not in "\n\r\t" for char in text):
        raise ValueError("conversation_scope_text_invalid")
    return text[:limit]


def typed_items(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ValueError("conversation_scope_items_invalid")
    if len(values) > MAX_ITEMS:
        raise ValueError("conversation_scope_items_limit")
    items: list[dict[str, Any]] = []
    for raw in values:
        if not isinstance(raw, Mapping) or set(raw) != {"item_id", "kind", "summary", "evidence_refs"}:
            raise ValueError("conversation_scope_item_shape_invalid")
        if any(type(raw[name]) is not str for name in ("item_id", "kind", "summary")):
            raise ValueError("conversation_scope_item_type_invalid")
        kind = raw["kind"]
        refs = string_list(raw["evidence_refs"], maximum=MAX_EVIDENCE_REFS)
        item = {
            "item_id": raw["item_id"],
            "kind": kind,
            "summary": sanitized_text(raw["summary"]),
            "evidence_refs": refs,
        }
        if not SHA256_RE.fullmatch(item["item_id"]) or kind not in ITEM_KINDS or not item["summary"]:
            raise ValueError("conversation_scope_item_invalid")
        if kind == "repository_fact" and not refs:
            raise ValueError("conversation_scope_repository_fact_unreferenced")
        items.append(item)
    if len({item["item_id"] for item in items}) != len(items):
        raise ValueError("conversation_scope_item_duplicate")
    return items


def string_list(values: Any, *, maximum: int) -> list[str]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or len(values) > maximum:
        raise ValueError("conversation_scope_list_invalid")
    if any(type(item) is not str for item in values):
        raise ValueError("conversation_scope_list_type_invalid")
    result = [sanitized_text(item, limit=320) for item in values]
    if any(not item for item in result) or len(set(result)) != len(result):
        raise ValueError("conversation_scope_list_invalid")
    return result


def validate_record(record: Mapping[str, Any]) -> tuple[str, ...]:
    if (
        type(record) is not dict
        or set(record) != RECORD_FIELDS
        or record.get("schema_version") != SCHEMA_VERSION
    ):
        return ("conversation_scope_record_shape_invalid",)
    type_reasons = _exact_json_type_reasons(record)
    if type_reasons:
        return tuple(type_reasons)
    reasons = [*_binding_reasons(record), *_state_reasons(record)]
    return tuple(dict.fromkeys(reasons))


def _binding_reasons(record: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    digest_payload = dict(record)
    supplied_digest = str(digest_payload.pop("record_digest", ""))
    if not SHA256_RE.fullmatch(supplied_digest) or supplied_digest != canonical_digest(digest_payload):
        reasons.append("conversation_scope_record_digest_invalid")
    required_digests = [
        "verified_subject_digest", "principal_record_digest", "principal_key_fingerprint",
        "session_binding_digest",
    ]
    if record.get("scope_kind") == SCOPE_KIND_FOUNDUP:
        required_digests.append("grounding_receipt_id")
    if any(not SHA256_RE.fullmatch(str(record.get(field) or "")) for field in required_digests):
        reasons.append("conversation_scope_binding_digest_invalid")
    if not SHA256_RE.fullmatch(str(record.get("conversation_id") or "")):
        reasons.append("conversation_scope_id_invalid")
    reasons.extend(_record_auth_reasons(record))
    if (
        record.get("scope_kind") == SCOPE_KIND_FOUNDUP
        and not HEAD_RE.fullmatch(str(record.get("last_grounded_head_sha") or ""))
    ):
        reasons.append("conversation_scope_head_invalid")
    if not _valid_optional_digest_pair(record, "pending_work_proposal_id", "pending_work_proposal_digest"):
        reasons.append("conversation_scope_pending_proposal_invalid")
    if not _valid_optional_digest_pair(record, "source_snapshot_id", "source_snapshot_digest"):
        reasons.append("conversation_scope_snapshot_binding_invalid")
    binding = str(record.get("initial_turn_request_binding_digest") or "")
    if binding and not SHA256_RE.fullmatch(binding):
        reasons.append("conversation_scope_initial_turn_binding_invalid")
    if not _valid_optional_digest_pair(
        record, "holoindex_generation_id", "holoindex_freshness_receipt_id"
    ):
        reasons.append("conversation_scope_holoindex_binding_invalid")
    return reasons


def _record_auth_reasons(record: Mapping[str, Any]) -> list[str]:
    scheme = str(record.get("record_auth_scheme") or "")
    signature = str(record.get("record_auth_signature") or "")
    nonce = str(record.get("record_auth_nonce") or "")
    previous = str(record.get("previous_record_auth_signature_digest") or "")
    revision = _integer(record.get("conversation_revision"), default=-1)
    reasons: list[str] = []
    if not SHA256_RE.fullmatch(nonce):
        reasons.append("conversation_scope_record_auth_nonce_invalid")
    if (revision == 0 and previous) or (
        revision > 0 and not SHA256_RE.fullmatch(previous)
    ):
        reasons.append("conversation_scope_record_auth_lineage_invalid")
    if scheme == "hmac-sha256-v1":
        if not re.fullmatch(r"hmac-sha256:[0-9a-f]{64}", signature):
            reasons.append("conversation_scope_record_auth_signature_invalid")
        if any(record.get(field) for field in _E0_ONLY_AUTH_FIELDS):
            reasons.append("conversation_scope_record_auth_scheme_mismatch")
    elif scheme == "ed25519-e0-v1":
        reasons.extend(_e0_auth_reasons(record, signature))
    else:
        reasons.append("conversation_scope_record_auth_scheme_invalid")
    return reasons


_E0_ONLY_AUTH_FIELDS = (
    "record_auth_signer_public_key", "record_auth_key_fingerprint",
    "record_auth_key_epoch", "record_auth_audit_mac",
    "record_auth_audit_attestation_signature",
)


def _e0_auth_reasons(record: Mapping[str, Any], signature: str) -> list[str]:
    reasons: list[str] = []
    if not re.fullmatch(r"ed25519-sig-v1:[A-Za-z0-9_-]+", signature):
        reasons.append("conversation_scope_record_auth_signature_invalid")
    if not re.fullmatch(
        r"ed25519-pub-v1:[A-Za-z0-9_-]+",
        str(record.get("record_auth_signer_public_key") or ""),
    ):
        reasons.append("conversation_scope_record_auth_public_key_invalid")
    required_digests = (
        "record_auth_key_fingerprint", "credential_id", "session_id",
    )
    if any(
        not SHA256_RE.fullmatch(str(record.get(field) or ""))
        for field in required_digests
    ):
        reasons.append("conversation_scope_record_auth_binding_invalid")
    if any(
        not isinstance(record.get(field), str) or not record.get(field)
        for field in (
            "repo_full_name", "record_auth_key_epoch", "record_auth_audit_mac",
            "record_auth_audit_attestation_signature",
        )
    ):
        reasons.append("conversation_scope_record_auth_e0_metadata_invalid")
    return reasons


def _state_reasons(record: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if any(not str(record.get(field) or "") for field in (
        "principal_id", "principal_provider", "transport",
        "turn_id", "active_topic", "current_objective", "created_at", "updated_at",
    )):
        reasons.append("conversation_scope_required_value_missing")
    if not SHA256_RE.fullmatch(str(record.get("turn_id") or "")):
        reasons.append("conversation_scope_turn_id_invalid")
    parent_turn_id = str(record.get("parent_turn_id") or "")
    revision_value = _integer(record.get("conversation_revision"), default=-1)
    if (
        (revision_value == 0 and parent_turn_id)
        or (revision_value > 0 and not SHA256_RE.fullmatch(parent_turn_id))
    ):
        reasons.append("conversation_scope_parent_turn_invalid")
    discussions = record.get("discussion_foundup_ids")
    try:
        string_list(discussions, maximum=16)
    except (TypeError, ValueError):
        reasons.append("conversation_scope_discussion_set_invalid")
    reasons.extend(scope_record_reasons(record))
    created_at = _integer(record.get("created_at"), default=-1)
    updated_at = _integer(record.get("updated_at"), default=-1)
    expires_at = _integer(record.get("expires_at"), default=-1)
    if (
        revision_value < 0 or created_at < 0 or updated_at < created_at
        or expires_at <= updated_at
    ):
        reasons.append("conversation_scope_revision_or_expiry_invalid")
    for field in ("accepted_decisions", "rejected_options", "open_questions"):
        try:
            typed_items(record.get(field))
        except (TypeError, ValueError):
            reasons.append(f"conversation_scope_{field}_invalid")
    try:
        string_list(record.get("repository_evidence_refs"), maximum=MAX_EVIDENCE_REFS)
    except (TypeError, ValueError):
        reasons.append("conversation_scope_evidence_refs_invalid")
    if not valid_revision_receipts(record):
        reasons.append("conversation_scope_revision_receipts_invalid")
    return reasons


def with_record_digest(record: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(record)
    value.pop("record_digest", None)
    value["record_digest"] = canonical_digest(value)
    return value


def validate_unsigned_record(record: Mapping[str, Any]) -> tuple[str, ...]:
    """Validate exact pre-sign state without trusting caller auth outputs."""

    if set(record) != UNSIGNED_RECORD_FIELDS:
        return ("conversation_scope_unsigned_record_shape_invalid",)
    candidate = dict(record)
    if candidate.get("record_auth_scheme") == "hmac-sha256-v1":
        candidate.update({
            "record_auth_signature": "hmac-sha256:" + "0" * 64,
            **{field: "" for field in _E0_ONLY_AUTH_FIELDS},
        })
    else:
        candidate.update({
            "record_auth_signature": "ed25519-sig-v1:fixture",
            "record_auth_signer_public_key": "ed25519-pub-v1:fixture",
            "record_auth_key_fingerprint": "sha256:" + "0" * 64,
            "record_auth_key_epoch": "validation-fixture",
            "record_auth_audit_mac": "validation-fixture",
            "record_auth_audit_attestation_signature": "validation-fixture",
        })
    return validate_record(with_record_digest(candidate))


def _valid_optional_digest_pair(record: Mapping[str, Any], left: str, right: str) -> bool:
    values = (str(record.get(left) or ""), str(record.get(right) or ""))
    return values == ("", "") or all(SHA256_RE.fullmatch(value) for value in values)


def _integer(value: Any, *, default: int) -> int:
    return value if type(value) is int else default


def _exact_json_type_reasons(record: Mapping[str, Any]) -> list[str]:
    if any(type(record.get(name)) is not str for name in STRING_FIELDS):
        return ["conversation_scope_record_string_type_invalid"]
    if any(type(record.get(name)) is not int for name in INTEGER_FIELDS):
        return ["conversation_scope_record_integer_type_invalid"]
    if any(not isinstance(record.get(name), list) for name in LIST_FIELDS):
        return ["conversation_scope_record_list_type_invalid"]
    if any(
        any(type(item) is not str for item in record[name])
        for name in STRING_LIST_FIELDS
    ):
        return ["conversation_scope_record_list_item_type_invalid"]
    for name in ITEM_LIST_FIELDS:
        for item in record[name]:
            if type(item) is not dict:
                return ["conversation_scope_record_item_type_invalid"]
    return _revision_receipt_type_reasons(record["revision_receipts"])


def _revision_receipt_type_reasons(receipts: Sequence[Any]) -> list[str]:
    string_fields = REVISION_RECEIPT_FIELDS - {"revision"}
    for receipt in receipts:
        if type(receipt) is not dict or set(receipt) != REVISION_RECEIPT_FIELDS:
            return ["conversation_scope_revision_receipt_type_invalid"]
        if type(receipt.get("revision")) is not int:
            return ["conversation_scope_revision_receipt_type_invalid"]
        if any(type(receipt.get(name)) is not str for name in string_fields):
            return ["conversation_scope_revision_receipt_type_invalid"]
    return []


__all__ = [
    "AUTH_RESPONSE_FIELDS", "IMMUTABLE_FIELDS", "ITEM_KINDS", "MUTABLE_FIELDS",
    "RECORD_FIELDS", "UNSIGNED_RECORD_FIELDS",
    "REVISION_RECEIPT_FIELDS", "REVISION_RECEIPT_SCHEMA", "SCHEMA_VERSION",
    "canonical_digest", "sanitized_text",
    "string_list", "typed_items", "validate_record", "validate_unsigned_record",
    "with_record_digest",
]
