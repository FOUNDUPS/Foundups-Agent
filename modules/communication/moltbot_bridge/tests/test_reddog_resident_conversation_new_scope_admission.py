"""Adversarial tests for trusted resident new-scope admission."""

from __future__ import annotations

import ast
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import pytest

from modules.ai_intelligence.digital_twin.src.resident_conversation_transport_contract import (
    request_from_mapping,
)
from modules.communication.moltbot_bridge.src import (
    reddog_resident_conversation_new_scope_admission as admission,
)
from modules.communication.moltbot_bridge.src.reddog_authenticated_conversation_scope_state import (
    create_authenticated_conversation_scope_from_verified_authority,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_session_authority_source import (
    ConversationSessionAuthoritySourceError,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_authentication import (
    authenticate_signed_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    VerifiedConversationScopeAuthority,
    consume_conversation_scope_capability,
    conversation_scope_authority_view,
    discard_conversation_scope_capability,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
    AgentDbConversationScopeStore,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_digest import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_new_scope_resolution import (
    resolve_resident_conversation_new_scope_request,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_signing_test_support import (
    REPO,
    Resolver as SignedResolver,
    capability as signed_root_capability,
    context as signed_context,
    credential as signed_credential,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_test_support import (
    FOCUS,
    NOW,
    ROOT,
    TestAgentDb,
    capability,
    digest,
    grounding_receipt,
)


def _store(path: Path) -> AgentDbConversationScopeStore:
    return AgentDbConversationScopeStore(lambda: TestAgentDb(path))


def _request(**overrides: object):
    payload: dict[str, object] = {
        "schema_version": "reddog_resident_conversation_request.v1",
        "operation": "TURN",
        "request_id": digest({"new-scope-request": "one"}),
        "conversation_id": "",
        "expected_revision": -1,
        "turn_id": digest({"new-scope-turn": "one"}),
        "client_nonce": digest({"new-scope-nonce": "one"}),
        "idempotency_key": digest({"new-scope-idempotency": "one"}),
        "issued_at": NOW,
        "expires_at": NOW + 60,
        "operator_text": FOCUS,
    }
    payload.update(overrides)
    return request_from_mapping(payload, now_epoch=NOW)


def _intent(request: Any, **overrides: object) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "reddog_intent.v2",
        "source_surface": "editor_thin_client",
        "origin": "extension",
        "principal_ref": "principal_012",
        "foundup_id": "trade",
        "work_focus": request.operator_text,
        "grounding_receipt": grounding_receipt(),
        "submits_executable_authority": False,
        "client_request_id": request.request_id,
    }
    payload.update(overrides)
    payload["intent_id"] = canonical_digest(payload)
    return payload


def _authority() -> Any:
    return consume_conversation_scope_capability(
        capability(), active_foundup_id="trade",
        discussion_foundup_ids=("trade",), now_epoch=NOW,
    )


def _signed_authority(
    serialized: str, signing_context: Any, *, session_binding: str,
) -> Any:
    authenticated = authenticate_signed_conversation_scope(
        serialized_credential=serialized, transport="editor",
        session_binding=session_binding, expected_repo_full_name=REPO,
        principal_resolver=SignedResolver(), now_epoch=NOW,
        record_signing_context=signing_context,
    )
    assert authenticated is not None
    return consume_conversation_scope_capability(
        authenticated[0], active_foundup_id="trade",
        discussion_foundup_ids=("trade",), now_epoch=NOW,
    )


def _install_lease(
    monkeypatch: pytest.MonkeyPatch, factory: Callable[[], Any],
    calls: list[dict[str, Any]],
) -> list[Any]:
    authorities: list[Any] = []

    @contextmanager
    def fake_lease(**kwargs: Any):
        calls.append(kwargs)
        authority = factory()
        authorities.append(authority)
        try:
            yield SimpleNamespace(authority=authority)
        finally:
            discard_conversation_scope_capability(authority)

    monkeypatch.setattr(
        admission, "lease_current_generation_conversation_session", fake_lease
    )
    return authorities


def _admit(path: Path, request: Any, intent: Any, **overrides: Any):
    values = {
        "repo_root": ROOT,
        "intent": intent,
        "grounding_receipt_id": intent["grounding_receipt"]["receipt_id"],
        "serialized_credential": "signed-session-secret",
        "owner_config_path": "O:/RedDog/runtime/owner.ini",
        "now_epoch": NOW,
        "scope_store": _store(path),
        "request": request,
    }
    values.update(overrides)
    return admission.create_current_generation_resident_conversation_scope(**values)


def test_new_turn_creates_content_minimized_scope_under_required_signer_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "new-scope.sqlite"
    request = _request()
    intent = _intent(request)
    calls: list[dict[str, Any]] = []
    authorities = _install_lease(monkeypatch, _authority, calls)

    result = _admit(path, request, intent)

    assert result.accepted is True
    assert result.conversation_revision == 0
    assert len(calls) == 1
    assert calls[0]["require_record_signing_context"] is True
    assert calls[0]["include_principal_scope_capability"] is False
    assert conversation_scope_authority_view(authorities[0]) is None
    stored = _store(path).load(result.conversation_id)["record"]
    serialized = json.dumps({"result": result.projection, "record": stored})
    assert request.operator_text not in serialized
    assert "signed-session-secret" not in serialized
    assert "principal_012" not in json.dumps(result.projection)
    assert stored["turn_id"] == request.turn_id
    assert stored["created_at"] == request.issued_at


def test_exact_retry_recovers_one_authenticated_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "new-scope-retry.sqlite"
    request = _request()
    intent = _intent(request)
    _install_lease(monkeypatch, _authority, [])

    first = _admit(path, request, intent)
    replay = _admit(path, request, intent, now_epoch=NOW + 1)
    rows = TestAgentDb(path).db.execute_query(
        "SELECT conversation_id FROM reddog_conversation_scopes"
    )

    assert first.accepted is replay.accepted is True
    assert first.conversation_id == replay.conversation_id
    assert len(rows) == 1


def test_same_nonce_with_divergent_turn_does_not_recover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "new-scope-divergent.sqlite"
    first_request = _request()
    _install_lease(monkeypatch, _authority, [])
    assert _admit(path, first_request, _intent(first_request)).accepted is True
    second = _request(
        request_id=digest({"new-scope-request": "two"}),
        turn_id=digest({"new-scope-turn": "two"}),
        idempotency_key=digest({"new-scope-idempotency": "two"}),
    )

    rejected = _admit(path, second, _intent(second))

    assert rejected.rejection_reasons == (
        "conversation_scope_creation_conflict",
    )


def test_same_nonce_with_divergent_grounded_text_does_not_recover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "new-scope-divergent-text.sqlite"
    first_request = _request()
    _install_lease(monkeypatch, _authority, [])
    assert _admit(path, first_request, _intent(first_request)).accepted is True
    focus = "Assess the TRADE FoundUp through a different grounded request."
    second = _request(
        request_id=digest({"new-scope-request": "different-text"}),
        idempotency_key=digest({"new-scope-idempotency": "different-text"}),
        operator_text=focus,
    )
    intent = _intent(second, work_focus=focus, grounding_receipt=grounding_receipt(focus=focus))

    rejected = _admit(path, second, intent)

    assert rejected.rejection_reasons == (
        "conversation_scope_creation_conflict",
    )


@pytest.mark.parametrize("divergence", ("turn", "text"))
def test_real_signed_session_binding_cannot_split_one_nonce_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, divergence: str,
) -> None:
    path = tmp_path / f"signed-binding-{divergence}.sqlite"
    first_request = _request()
    second_values: dict[str, object] = {
        "request_id": digest({"signed-request": divergence}),
        "idempotency_key": digest({"signed-idempotency": divergence}),
    }
    if divergence == "turn":
        second_values["turn_id"] = digest({"signed-turn": "different"})
    else:
        second_values["operator_text"] = "Assess TRADE using alternate evidence."
    second_request = _request(**second_values)
    first_intent = _intent(first_request)
    second_intent = _intent(
        second_request,
        grounding_receipt=grounding_receipt(focus=second_request.operator_text),
    )
    serialized = signed_credential()
    signing_context, _anchor = signed_context(serialized)
    bindings = iter(
        canonical_digest({
            "intent_id": intent["intent_id"],
            "grounding_receipt_id": intent["grounding_receipt"]["receipt_id"],
            "source_surface": intent["source_surface"],
        })
        for intent in (first_intent, second_intent)
    )
    _install_lease(
        monkeypatch,
        lambda: _signed_authority(
            serialized, signing_context, session_binding=next(bindings)
        ),
        [],
    )

    assert _admit(path, first_request, first_intent).accepted is True
    rejected = _admit(path, second_request, second_intent)

    assert rejected.rejection_reasons == ("conversation_scope_creation_conflict",)
    assert len(TestAgentDb(path).db.execute_query(
        "SELECT conversation_id FROM reddog_conversation_scopes"
    )) == 1


def test_concurrent_exact_requests_converge_on_one_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "new-scope-concurrent.sqlite"
    request = _request()
    intent = _intent(request)
    _install_lease(monkeypatch, _authority, [])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _item: _admit(path, request, intent), range(2)))

    assert all(result.accepted for result in results)
    assert len({result.conversation_id for result in results}) == 1
    assert len(TestAgentDb(path).db.execute_query(
        "SELECT conversation_id FROM reddog_conversation_scopes"
    )) == 1


@pytest.mark.parametrize(
    "case", ("existing", "future", "intent", "focus", "receipt")
)
def test_invalid_resolution_rejects_before_credential_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str,
) -> None:
    request = _request()
    intent = _intent(request)
    grounding_id = intent["grounding_receipt"]["receipt_id"]
    if case == "existing":
        request = _request(
            conversation_id=digest({"conversation": "existing"}),
            expected_revision=0,
        )
    elif case == "future":
        request = _request(issued_at=NOW + 1, expires_at=NOW + 61)
        intent = _intent(request)
    elif case == "intent":
        intent = {**intent, "client_request_id": digest({"wrong": "request"})}
        intent["intent_id"] = canonical_digest(
            {key: value for key, value in intent.items() if key != "intent_id"}
        )
    elif case == "focus":
        intent = _intent(request, work_focus="Different grounded focus.")
    else:
        grounding_id = digest({"wrong": "receipt"})
    calls: list[dict[str, Any]] = []
    _install_lease(monkeypatch, _authority, calls)

    result = _admit(
        tmp_path / f"prelease-{case}.sqlite", request, intent,
        grounding_receipt_id=grounding_id,
    )

    assert result.accepted is False
    assert calls == []


def test_authority_expiring_before_request_is_consumed_and_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "short-authority.sqlite"
    request = _request()
    intent = _intent(request)

    def short_authority():
        root = capability(now_epoch=NOW - 1)
        return consume_conversation_scope_capability(
            root, active_foundup_id="trade",
            discussion_foundup_ids=("trade",), now_epoch=NOW,
        )

    authorities = _install_lease(monkeypatch, short_authority, [])
    result = _admit(path, request, intent)

    assert result.rejection_reasons == ("conversation_scope_expired",)
    assert conversation_scope_authority_view(authorities[0]) is None
    assert _store(path).load(digest({"missing": "scope"}))["reason"] == (
        "conversation_scope_missing"
    )


def test_scope_ttl_must_span_the_resident_request_lifetime(tmp_path: Path) -> None:
    request = _request()
    intent = _intent(request)
    creation, reason = resolve_resident_conversation_new_scope_request(
        repo_root=ROOT, intent=intent,
        grounding_receipt_id=intent["grounding_receipt"]["receipt_id"],
        request=request, now_epoch=NOW,
    )
    assert reason == "" and creation is not None
    result = create_authenticated_conversation_scope_from_verified_authority(
        store=_store(tmp_path / "short-scope.sqlite"), authority=_authority(),
        repo_root=ROOT, request=replace(creation, ttl_seconds=30), now_epoch=NOW,
        record_epoch=request.issued_at, minimum_expires_at=request.expires_at,
    )

    assert result.rejection_reasons == ("conversation_scope_expired",)


def test_unregistered_authority_and_private_source_failures_are_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "new-scope-failures.sqlite"
    request = _request()
    intent = _intent(request)
    _install_lease(
        monkeypatch, lambda: object.__new__(VerifiedConversationScopeAuthority), []
    )
    forged = _admit(path, request, intent)
    assert forged.rejection_reasons == ("conversation_scope_access_denied",)

    @contextmanager
    def secret_failure(**_kwargs: Any):
        raise ConversationSessionAuthoritySourceError("private-secret-detail")
        yield

    monkeypatch.setattr(
        admission, "lease_current_generation_conversation_session", secret_failure
    )
    closed = _admit(path, request, intent)
    assert closed.rejection_reasons == (admission.UNAVAILABLE_REASON,)


def test_e0_authority_native_scope_creation_and_replay(tmp_path: Path) -> None:
    path = tmp_path / "new-scope-e0.sqlite"
    request = _request()
    intent = _intent(request)
    creation, reason = resolve_resident_conversation_new_scope_request(
        repo_root=ROOT, intent=intent,
        grounding_receipt_id=intent["grounding_receipt"]["receipt_id"],
        request=request, now_epoch=NOW,
    )
    assert reason == "" and creation is not None
    serialized = signed_credential()
    signing_context, _anchor = signed_context(serialized)

    def verified_authority():
        root = signed_root_capability(signing_context, serialized)
        return consume_conversation_scope_capability(
            root, active_foundup_id="trade",
            discussion_foundup_ids=("trade",), now_epoch=NOW,
        )

    first = create_authenticated_conversation_scope_from_verified_authority(
        store=_store(path), authority=verified_authority(), repo_root=ROOT,
        request=creation, now_epoch=NOW, record_epoch=request.issued_at,
        minimum_expires_at=request.expires_at,
    )
    replay = create_authenticated_conversation_scope_from_verified_authority(
        store=_store(path), authority=verified_authority(), repo_root=ROOT,
        request=creation, now_epoch=NOW + 1, record_epoch=request.issued_at,
        minimum_expires_at=request.expires_at,
    )

    assert first.accepted is replay.accepted is True
    assert first.conversation_id == replay.conversation_id
    assert _store(path).load(first.conversation_id)["record"]["record_auth_scheme"] == (
        "ed25519-e0-v1"
    )


def test_new_scope_slice_respects_wsp62_and_has_no_effect_wiring() -> None:
    paths = (
        Path(admission.__file__),
        ROOT / "modules/communication/moltbot_bridge/src/reddog_resident_conversation_new_scope_resolution.py",
        ROOT / "modules/communication/moltbot_bridge/src/reddog_conversation_session_signing_context.py",
        ROOT / "modules/communication/moltbot_bridge/src/reddog_conversation_session_authority_source.py",
        ROOT / "modules/communication/moltbot_bridge/src/reddog_conversation_scope_capability.py",
        ROOT / "modules/communication/moltbot_bridge/src/reddog_authenticated_conversation_scope_state.py",
    )
    for path in paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert len(source.splitlines()) <= 500
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 50
    source = Path(admission.__file__).read_text(encoding="utf-8")
    for forbidden in ("model.invoke", "worker_dispatch", "conversation_handler", "journal"):
        assert forbidden not in source
