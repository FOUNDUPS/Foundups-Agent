"""Adversarial tests for resident request-to-scope admission binding."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from modules.ai_intelligence.digital_twin.src.resident_conversation_transport_contract import (
    request_from_mapping,
)
from modules.communication.moltbot_bridge.src.reddog_authenticated_conversation_scope_state import (
    create_authenticated_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_request import (
    ConversationScopeCreateRequest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    with_record_digest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
    AgentDbConversationScopeStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_scope_binding import (
    bind_resident_conversation_request_to_authenticated_scope,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_test_support import (
    FOCUS,
    NOW,
    SNAPSHOT_DIGEST,
    SNAPSHOT_ID,
    TestAgentDb,
    capability,
    digest,
    grounding_receipt,
    item,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_signing_test_support import (
    capability as signed_capability,
    context as signed_context,
    create as create_signed_scope,
    credential as signed_credential,
)


_UNSET = object()


def _store(path: Path) -> AgentDbConversationScopeStore:
    return AgentDbConversationScopeStore(lambda: TestAgentDb(path))


def _create(path: Path, *, ttl_seconds: int = 3600):
    return create_authenticated_conversation_scope(
        store=_store(path),
        capability=capability(),
        repo_root=Path(__file__).resolve().parents[4],
        request=ConversationScopeCreateRequest(
            work_focus=FOCUS,
            grounding_receipt=grounding_receipt(),
            discussion_foundup_ids=("trade",),
            conversation_nonce="resident-service-binding",
            turn_id=digest({"turn": "first"}),
            active_topic="TRADE runtime",
            current_objective="Bind one authenticated resident request.",
            accepted_decisions=(
                item("Use current repository evidence.", "repository_fact"),
            ),
            repository_evidence_refs=("code:trade",),
            source_snapshot_id=SNAPSHOT_ID,
            source_snapshot_digest=SNAPSHOT_DIGEST,
            ttl_seconds=ttl_seconds,
        ),
        now_epoch=NOW,
    )


def _request(conversation_id: str, **overrides: object):
    payload: dict[str, object] = {
        "schema_version": "reddog_resident_conversation_request.v1",
        "operation": "TURN",
        "request_id": digest({"request": "one"}),
        "conversation_id": conversation_id,
        "expected_revision": 0,
        "turn_id": digest({"turn": "second"}),
        "client_nonce": digest({"nonce": "one"}),
        "idempotency_key": digest({"idempotency": "one"}),
        "issued_at": NOW,
        "expires_at": NOW + 60,
        "operator_text": "Continue the grounded RedDog audit.",
    }
    payload.update(overrides)
    return request_from_mapping(payload, now_epoch=NOW)


def _bind(path: Path, request, *, scope_capability=_UNSET, now_epoch: int = NOW):
    return bind_resident_conversation_request_to_authenticated_scope(
        store=_store(path),
        capability=(capability() if scope_capability is _UNSET else scope_capability),
        request=request,
        now_epoch=now_epoch,
    )


def test_existing_turn_binds_current_authenticated_cas_without_mutation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "scope.sqlite"
    created = _create(path)
    current = _store(path).load(created.conversation_id)["record"]

    result = _bind(path, _request(created.conversation_id))

    assert result.accepted is True
    assert result.status == "RESIDENT_CONVERSATION_SCOPE_BOUND"
    assert result.operation == "TURN"
    assert result.expected_revision == result.current_revision == 0
    assert result.current_turn_id == current["turn_id"]
    assert result.record_digest == current["record_digest"]
    assert result.binding_id.startswith("sha256:")
    assert result.cas_reserved is False
    assert result.grants_identity_authority is False
    assert result.grants_effect_authority is False
    assert _store(path).load(created.conversation_id)["record"] == current

    serialized = json.dumps(result.to_dict(), sort_keys=True)
    assert "Continue the grounded RedDog audit" not in serialized
    assert "principal_012" not in serialized
    assert '"trade"' not in serialized


def test_capability_is_consumed_once_even_though_binding_grants_no_authority(
    tmp_path: Path,
) -> None:
    path = tmp_path / "scope.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    one_use = capability()

    assert _bind(path, request, scope_capability=one_use).accepted is True
    replay = _bind(path, request, scope_capability=one_use)
    assert replay.accepted is False
    assert replay.rejection_reasons == ("resident_conversation_access_denied",)


def test_current_principal_signed_e0_scope_is_admitted(tmp_path: Path) -> None:
    path = tmp_path / "signed-scope.sqlite"
    serialized = signed_credential()
    signing_context, _anchor = signed_context(serialized)
    created = create_signed_scope(path, signing_context, serialized)

    result = _bind(
        path,
        _request(created.conversation_id),
        scope_capability=signed_capability(signing_context, serialized),
    )

    assert result.accepted is True
    assert result.status == "RESIDENT_CONVERSATION_SCOPE_BOUND"


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"expected_revision": 1}, "resident_conversation_revision_conflict"),
        (
            {"turn_id": digest({"turn": "first"})},
            "resident_conversation_turn_conflict",
        ),
    ],
)
def test_turn_rejects_stale_revision_or_current_turn_reuse(
    tmp_path: Path, overrides: dict[str, object], reason: str
) -> None:
    path = tmp_path / "scope.sqlite"
    created = _create(path)
    result = _bind(path, _request(created.conversation_id, **overrides))
    assert result.accepted is False
    assert result.rejection_reasons == (reason,)


@pytest.mark.parametrize("operation", ["STATUS", "CANCEL"])
def test_control_operations_bind_only_the_current_turn(
    tmp_path: Path, operation: str
) -> None:
    path = tmp_path / f"{operation.lower()}.sqlite"
    created = _create(path)
    current_turn = _store(path).load(created.conversation_id)["record"]["turn_id"]
    request = _request(
        created.conversation_id,
        operation=operation,
        turn_id=current_turn,
        operator_text="",
    )
    assert _bind(path, request).accepted is True

    stale = _request(
        created.conversation_id,
        operation=operation,
        turn_id=digest({"turn": "stale-control"}),
        operator_text="",
    )
    rejected = _bind(path, stale)
    assert rejected.rejection_reasons == ("resident_conversation_turn_conflict",)


def test_new_scope_expiry_and_store_failures_remain_fail_closed(
    tmp_path: Path,
) -> None:
    path = tmp_path / "scope.sqlite"
    created = _create(path, ttl_seconds=10)
    new_scope = _request("", expected_revision=-1)
    assert _bind(path, new_scope).rejection_reasons == (
        "resident_conversation_new_scope_resolution_required",
    )
    assert _bind(path, _request(created.conversation_id), now_epoch=NOW + 10).rejection_reasons == (
        "resident_conversation_scope_expired",
    )
    missing = _bind(path, _request(digest({"conversation": "missing"})))
    assert missing.rejection_reasons == ("resident_conversation_access_denied",)


def test_expired_or_mutated_envelope_retires_the_operation_capability(
    tmp_path: Path,
) -> None:
    path = tmp_path / "scope.sqlite"
    created = _create(path)
    expired = _request(created.conversation_id)
    one_use = capability()
    rejected = _bind(path, expired, scope_capability=one_use, now_epoch=NOW + 60)
    assert rejected.rejection_reasons == ("resident_conversation_request_expired",)
    assert _bind(
        path, _request(created.conversation_id), scope_capability=one_use
    ).rejection_reasons == ("resident_conversation_access_denied",)

    mutated = _request(created.conversation_id)
    object.__setattr__(mutated, "schema_version", "forged")
    assert _bind(path, mutated).rejection_reasons == (
        "resident_conversation_schema_invalid",
    )


def test_invalid_clock_and_store_exception_reject_without_state_oracle(
    tmp_path: Path,
) -> None:
    path = tmp_path / "scope.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    assert _bind(path, request, now_epoch=True).rejection_reasons == (
        "resident_conversation_now_invalid",
    )

    class RaisingStore:
        def load(self, _conversation_id: str):
            raise RuntimeError("must not escape")

    result = bind_resident_conversation_request_to_authenticated_scope(
        store=RaisingStore(),  # type: ignore[arg-type]
        capability=capability(),
        request=request,
        now_epoch=NOW,
    )
    assert result.rejection_reasons == ("resident_conversation_access_denied",)

    class RaisingPayload(dict):
        def get(self, _key, _default=None):
            raise RuntimeError("malformed mapping must not escape")

    class MalformedStore:
        def load(self, _conversation_id: str):
            return RaisingPayload()

    malformed = bind_resident_conversation_request_to_authenticated_scope(
        store=MalformedStore(),  # type: ignore[arg-type]
        capability=capability(),
        request=request,
        now_epoch=NOW,
    )
    assert malformed.rejection_reasons == ("resident_conversation_access_denied",)

    class NonMappingStore:
        def load(self, _conversation_id: str):
            return None

    non_mapping = bind_resident_conversation_request_to_authenticated_scope(
        store=NonMappingStore(),  # type: ignore[arg-type]
        capability=capability(),
        request=request,
        now_epoch=NOW,
    )
    assert non_mapping.rejection_reasons == ("resident_conversation_access_denied",)


def test_dependency_exceptions_and_empty_validation_reasons_fail_closed(
    tmp_path: Path, monkeypatch
) -> None:
    path = tmp_path / "scope.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    target = (
        "modules.communication.moltbot_bridge.src."
        "reddog_resident_conversation_scope_binding"
    )
    monkeypatch.setattr(
        f"{target}.consume_conversation_scope_capability",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("closed")),
    )
    assert _bind(path, request).rejection_reasons == (
        "resident_conversation_access_denied",
    )

    monkeypatch.undo()
    monkeypatch.setattr(
        f"{target}.enforce_request_freshness",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError()),
    )
    assert _bind(path, request).rejection_reasons == (
        "resident_conversation_request_invalid",
    )


@pytest.mark.parametrize(
    "scope_capability",
    [
        pytest.param(None, id="not-a-capability"),
        pytest.param("forged", id="forged-string"),
    ],
)
def test_forged_capability_and_cross_session_authority_are_denied(
    tmp_path: Path, scope_capability
) -> None:
    path = tmp_path / "scope.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    if scope_capability is None:
        scope_capability = object()
    assert _bind(
        path, request, scope_capability=scope_capability
    ).rejection_reasons == ("resident_conversation_access_denied",)
    assert _bind(
        path,
        request,
        scope_capability=capability(session_binding="window:other"),
    ).rejection_reasons == ("resident_conversation_access_denied",)
    wrong_principal = _request(created.conversation_id, expected_revision=99)
    assert _bind(
        path,
        wrong_principal,
        scope_capability=capability(principal_id="principal_999"),
    ).rejection_reasons == ("resident_conversation_access_denied",)


def test_attacker_rehashed_record_still_fails_record_authentication(
    tmp_path: Path,
) -> None:
    path = tmp_path / "tampered.sqlite"
    created = _create(path)
    record = dict(_store(path).load(created.conversation_id)["record"])
    record["active_topic"] = "attacker-selected"
    tampered = with_record_digest(record)
    with TestAgentDb(path).db.get_connection() as connection:
        connection.execute(
            "UPDATE reddog_conversation_scopes SET scope_json = ? WHERE conversation_id = ?",
            (
                json.dumps(tampered, sort_keys=True, separators=(",", ":")),
                created.conversation_id,
            ),
        )

    result = _bind(path, _request(created.conversation_id))
    assert result.rejection_reasons == ("resident_conversation_access_denied",)


def test_binding_implementation_respects_wsp62_limits() -> None:
    source_path = (
        Path(__file__).parents[1]
        / "src"
        / "reddog_resident_conversation_scope_binding.py"
    )
    source = source_path.read_text(encoding="utf-8")
    functions = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert len(source.splitlines()) <= 500
    assert all(node.end_lineno - node.lineno + 1 <= 50 for node in functions)
