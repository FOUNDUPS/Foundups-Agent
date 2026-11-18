"""Adversarial tests for the resident RedDog conversation envelope."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from modules.ai_intelligence.digital_twin.src.conversation_plane import MAX_TURN_CHARS
from modules.ai_intelligence.digital_twin.src.resident_conversation_transport_contract import (
    MAX_CLOCK_SKEW_SECONDS,
    MAX_OPERATOR_TEXT_SCALARS,
    ResidentConversationOperation,
    ResidentConversationRequest,
    enforce_request_freshness,
    request_from_mapping,
    resident_conversation_request_reasons,
)


NOW = 1_800_000_000


def _digest(character: str) -> str:
    return "sha256:" + character * 64


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "reddog_resident_conversation_request.v1",
        "operation": "TURN",
        "request_id": _digest("a"),
        "conversation_id": _digest("b"),
        "expected_revision": 2,
        "turn_id": _digest("c"),
        "client_nonce": _digest("d"),
        "idempotency_key": _digest("e"),
        "issued_at": NOW,
        "expires_at": NOW + 60,
        "operator_text": "Hello RedDog.",
    }
    payload.update(overrides)
    return payload


def test_turn_round_trip_normalizes_text_and_projects_content_free_binding() -> None:
    request = request_from_mapping(
        _payload(operator_text="  Ｈｅｌｌｏ RedDog.  "), now_epoch=NOW
    )
    assert request.operation is ResidentConversationOperation.TURN
    assert request.operator_text == "Hello RedDog."
    assert request_from_mapping(request.to_dict(), now_epoch=NOW) == request
    binding = request.content_free_binding()
    assert binding["request_digest"] == request.request_digest()
    assert binding["grants_identity_authority"] is False
    assert binding["grants_effect_authority"] is False
    serialized = json.dumps(binding, sort_keys=True)
    assert "operator_text" not in serialized
    assert "Hello RedDog" not in serialized


@pytest.mark.parametrize(
    "injected",
    [
        "principal_id",
        "foundup_id",
        "credential",
        "provider",
        "model",
        "effect_ceiling",
        "work_authority",
    ],
)
def test_identity_routing_and_effect_injection_is_rejected(injected: str) -> None:
    payload = _payload()
    payload[injected] = "attacker-selected"
    with pytest.raises(ValueError, match="resident_conversation_request_shape_invalid"):
        request_from_mapping(payload, now_epoch=NOW)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("expected_revision", True),
        ("issued_at", False),
        ("expires_at", 1.5),
        ("operator_text", ["hello"]),
        ("request_id", 7),
    ],
)
def test_non_native_scalar_types_fail_closed(field: str, value: object) -> None:
    with pytest.raises(ValueError, match="resident_conversation_request_type_invalid"):
        request_from_mapping(_payload(**{field: value}), now_epoch=NOW)


@pytest.mark.parametrize("operation", ["EXECUTE", "AUTHORIZE", "turn"])
def test_unknown_or_authority_operations_fail_closed(operation: str) -> None:
    with pytest.raises(ValueError, match="resident_conversation_operation_invalid"):
        request_from_mapping(_payload(operation=operation), now_epoch=NOW)


def test_new_and_existing_turn_revision_shapes_are_distinct() -> None:
    created = request_from_mapping(
        _payload(conversation_id="", expected_revision=-1), now_epoch=NOW
    )
    assert created.conversation_id == ""
    with pytest.raises(ValueError, match="resident_conversation_revision_invalid"):
        request_from_mapping(
            _payload(conversation_id="", expected_revision=0), now_epoch=NOW
        )
    with pytest.raises(ValueError, match="resident_conversation_revision_invalid"):
        request_from_mapping(_payload(expected_revision=-1), now_epoch=NOW)


@pytest.mark.parametrize("operation", ["STATUS", "CANCEL"])
def test_control_operations_require_target_and_forbid_operator_text(
    operation: str,
) -> None:
    accepted = request_from_mapping(
        _payload(operation=operation, operator_text=""), now_epoch=NOW
    )
    assert accepted.operation.value == operation
    with pytest.raises(
        ValueError, match="resident_conversation_operator_text_forbidden"
    ):
        request_from_mapping(_payload(operation=operation), now_epoch=NOW)
    with pytest.raises(
        ValueError, match="resident_conversation_conversation_id_required"
    ):
        request_from_mapping(
            _payload(
                operation=operation,
                operator_text="",
                conversation_id="",
                expected_revision=-1,
            ),
            now_epoch=NOW,
        )


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"expires_at": NOW}, "resident_conversation_request_ttl_invalid"),
        ({"expires_at": NOW + 301}, "resident_conversation_request_ttl_invalid"),
        (
            {"issued_at": NOW + MAX_CLOCK_SKEW_SECONDS + 1, "expires_at": NOW + 90},
            "resident_conversation_request_not_yet_valid",
        ),
    ],
)
def test_ttl_and_clock_bounds_fail_closed(
    overrides: dict[str, object], reason: str
) -> None:
    with pytest.raises(ValueError, match=reason):
        request_from_mapping(_payload(**overrides), now_epoch=NOW)


def test_expiry_is_rechecked_at_use_time() -> None:
    request = request_from_mapping(_payload(), now_epoch=NOW)
    enforce_request_freshness(request, now_epoch=NOW + 59)
    with pytest.raises(ValueError, match="resident_conversation_request_expired"):
        enforce_request_freshness(request, now_epoch=NOW + 60)
    with pytest.raises(ValueError, match="resident_conversation_now_invalid"):
        enforce_request_freshness(request, now_epoch=True)
    with pytest.raises(ValueError, match="resident_conversation_request_type_invalid"):
        enforce_request_freshness(object(), now_epoch=NOW)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field",
    ["request_id", "conversation_id", "turn_id", "client_nonce", "idempotency_key"],
)
def test_all_transport_bindings_use_canonical_digest_shape(field: str) -> None:
    with pytest.raises(ValueError, match="resident_conversation_.*_invalid"):
        request_from_mapping(_payload(**{field: "client-selected-text"}), now_epoch=NOW)


@pytest.mark.parametrize(
    "operator_text",
    ["hello\x00world", "hello\x01world", "x" * (MAX_OPERATOR_TEXT_SCALARS + 1)],
)
def test_invalid_operator_text_fails_closed(operator_text: str) -> None:
    with pytest.raises(ValueError, match="resident_conversation_operator_text_invalid"):
        request_from_mapping(_payload(operator_text=operator_text), now_epoch=NOW)


def test_empty_turn_and_negative_control_revision_fail_closed() -> None:
    with pytest.raises(
        ValueError, match="resident_conversation_operator_text_required"
    ):
        request_from_mapping(_payload(operator_text="  "), now_epoch=NOW)
    with pytest.raises(ValueError, match="resident_conversation_revision_invalid"):
        request_from_mapping(
            _payload(operation="STATUS", operator_text="", expected_revision=-1),
            now_epoch=NOW,
        )


def test_transport_and_classifier_scalar_limits_are_identical() -> None:
    assert MAX_OPERATOR_TEXT_SCALARS == MAX_TURN_CHARS


def test_direct_construction_cannot_bypass_static_contract() -> None:
    with pytest.raises(
        ValueError, match="resident_conversation_request_binding_invalid"
    ):
        ResidentConversationRequest(
            operation=ResidentConversationOperation.TURN,
            request_id="not-a-digest",
            conversation_id="",
            expected_revision=-1,
            turn_id=_digest("c"),
            client_nonce=_digest("d"),
            idempotency_key=_digest("e"),
            issued_at=NOW,
            expires_at=NOW + 60,
            operator_text="hello",
        )
    for operator_text in (
        "  hello  ",
        "hello\x00world",
        "hello\x01world",
        "x" * 12_001,
    ):
        with pytest.raises(
            ValueError, match="resident_conversation_operator_text_invalid"
        ):
            ResidentConversationRequest(
                operation=ResidentConversationOperation.TURN,
                request_id=_digest("a"),
                conversation_id="",
                expected_revision=-1,
                turn_id=_digest("c"),
                client_nonce=_digest("d"),
                idempotency_key=_digest("e"),
                issued_at=NOW,
                expires_at=NOW + 60,
                operator_text=operator_text,
            )


def test_mutated_or_forged_request_objects_report_stable_reasons() -> None:
    request = request_from_mapping(_payload(), now_epoch=NOW)
    object.__setattr__(request, "schema_version", "forged")
    assert resident_conversation_request_reasons(request) == (
        "resident_conversation_schema_invalid",
    )
    request = request_from_mapping(_payload(), now_epoch=NOW)
    object.__setattr__(request, "operation", "TURN")
    assert "resident_conversation_operation_invalid" in (
        resident_conversation_request_reasons(request)
    )
    request = request_from_mapping(_payload(), now_epoch=NOW)
    object.__setattr__(request, "issued_at", True)
    assert "resident_conversation_request_type_invalid" in (
        resident_conversation_request_reasons(request)
    )
    assert resident_conversation_request_reasons(object()) == (
        "resident_conversation_request_type_invalid",
    )


def test_transport_contract_respects_wsp62_limits() -> None:
    source_path = (
        Path(__file__).parents[1]
        / "src"
        / "resident_conversation_transport_contract.py"
    )
    source = source_path.read_text(encoding="utf-8")
    functions = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert len(source.splitlines()) <= 500
    assert all(node.end_lineno - node.lineno + 1 <= 50 for node in functions)
