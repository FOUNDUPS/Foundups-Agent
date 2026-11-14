"""Exact-type and consumed-authority boundary regressions."""

from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    consume_conversation_scope_capability,
    sign_record_with_scope_authority,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    UNSIGNED_RECORD_FIELDS,
    validate_unsigned_record,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    build_conversation_scope_signing_request,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_signing_test_support import (
    NOW,
    capability,
    context,
    create,
    credential,
    store,
)


def _stored_unsigned_record(tmp_path: Path):
    serialized = credential()
    signing_context, _anchor = context(serialized)
    created = create(tmp_path / "scope.sqlite", signing_context, serialized)
    stored = store(tmp_path / "scope.sqlite").load(created.conversation_id)["record"]
    unsigned = {name: stored[name] for name in UNSIGNED_RECORD_FIELDS}
    return serialized, signing_context, stored, unsigned


@pytest.mark.parametrize(
    ("field", "value", "expected_reason"),
    (
        ("source_snapshot_id", None, "conversation_scope_record_string_type_invalid"),
        ("conversation_revision", "0", "conversation_scope_record_integer_type_invalid"),
        ("discussion_foundup_ids", [1], "conversation_scope_record_list_item_type_invalid"),
    ),
)
def test_unsigned_record_rejects_json_type_coercion_before_signing(
    tmp_path: Path,
    field: str,
    value: object,
    expected_reason: str,
) -> None:
    _serialized, signing_context, _stored, unsigned = _stored_unsigned_record(tmp_path)
    unsigned[field] = value

    assert validate_unsigned_record(unsigned) == (expected_reason,)
    request = build_conversation_scope_signing_request(signing_context, unsigned)
    assert request is not None
    assert signing_context.signer.sign(request).accepted is False


def test_unsigned_record_rejects_nested_type_coercion(tmp_path: Path) -> None:
    _serialized, _context, _stored, unsigned = _stored_unsigned_record(tmp_path)
    bad_item = dict(unsigned)
    bad_item["accepted_decisions"] = [
        {**unsigned["accepted_decisions"][0], "kind": None}
    ]
    assert "conversation_scope_accepted_decisions_invalid" in validate_unsigned_record(
        bad_item
    )

    bad_revision = dict(unsigned)
    bad_revision["revision_receipts"] = [
        {**unsigned["revision_receipts"][0], "revision": "0"}
    ]
    assert validate_unsigned_record(bad_revision) == (
        "conversation_scope_revision_receipt_type_invalid",
    )


def test_consumed_authority_seal_rejects_scope_widening(tmp_path: Path) -> None:
    serialized, signing_context, stored, _unsigned = _stored_unsigned_record(tmp_path)
    authority = consume_conversation_scope_capability(
        capability(signing_context, serialized, NOW),
        scope_kind="foundup",
        active_foundup_id="trade",
        discussion_foundup_ids=("trade",),
        now_epoch=NOW,
    )
    assert authority is not None

    widened = {**stored, "discussion_foundup_ids": ["trade", "gotjunk_001"]}
    assert sign_record_with_scope_authority(authority, widened) is None
