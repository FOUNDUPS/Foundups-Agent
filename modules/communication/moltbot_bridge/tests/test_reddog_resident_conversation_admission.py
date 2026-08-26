"""Adversarial tests for current-session resident request admission."""

from __future__ import annotations

import ast
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from typing import Any, Callable
from collections.abc import Mapping

import pytest

from modules.ai_intelligence.digital_twin.src.resident_conversation_transport_contract import (
    ResidentConversationRequest,
)
from modules.communication.moltbot_bridge.src import (
    reddog_resident_conversation_admission as admission,
    reddog_resident_conversation_scope_binding as scope_binding,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_authentication import (
    authenticate_signed_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_session_authority_source import (
    ConversationSessionAuthoritySourceError,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    VerifiedConversationScopeAuthority,
    consume_conversation_scope_capability,
    consume_verified_scope_authority_for_request_journal,
    conversation_scope_authority_view,
    discard_conversation_scope_capability,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_request_journal import (
    AgentDbResidentConversationRequestJournal,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_test_support import (
    NOW,
    ROOT,
    TestAgentDb,
    capability,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_signing_test_support import (
    REPO as SIGNED_REPO,
    Resolver as SignedResolver,
    context as signed_context,
    create as create_signed_scope,
    credential as signed_credential,
)
from modules.communication.moltbot_bridge.tests.test_reddog_resident_conversation_scope_binding import (
    _create,
    _request,
    _store,
)


def _journal(path: Path, now_epoch: int = NOW):
    return AgentDbResidentConversationRequestJournal(
        lambda: TestAgentDb(path), clock=lambda: now_epoch
    )


def _authority(path: Path, conversation_id: str, **capability_kwargs: Any):
    record = _store(path).load(conversation_id)["record"]
    return consume_conversation_scope_capability(
        capability(**capability_kwargs),
        active_foundup_id=str(record["authorized_foundup_id"]),
        discussion_foundup_ids=tuple(record["discussion_foundup_ids"]),
        now_epoch=NOW,
        scope_kind=str(record["scope_kind"]),
    )


def _install_lease(
    monkeypatch: pytest.MonkeyPatch,
    authority_factory: Callable[[], Any],
    calls: list[dict[str, Any]],
) -> None:
    @contextmanager
    def fake_lease(**kwargs: Any):
        calls.append(kwargs)
        authority = authority_factory()
        try:
            yield SimpleNamespace(authority=authority)
        finally:
            discard_conversation_scope_capability(authority)

    monkeypatch.setattr(
        admission, "lease_current_generation_conversation_session", fake_lease
    )


def _reserve(path: Path, request, **overrides: Any):
    values = {
        "repo_root": ROOT,
        "intent": {"intent_id": "intent:one", "source_surface": "editor"},
        "grounding_receipt_id": "sha256:" + "7" * 64,
        "serialized_credential": "signed-credential-secret",
        "owner_config_path": "O:/RedDog/runtime/owner.ini",
        "now_epoch": NOW,
        "scope_store": _store(path),
        "journal": _journal(path),
        "request": request,
    }
    values.update(overrides)
    return admission.reserve_current_generation_resident_conversation_request(**values)


def test_current_signed_session_binds_and_reserves_content_free(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "aggregate.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    calls: list[dict[str, Any]] = []
    authorities: list[Any] = []

    def authority_factory():
        value = _authority(path, created.conversation_id)
        authorities.append(value)
        return value

    _install_lease(monkeypatch, authority_factory, calls)
    result = _reserve(path, request)

    assert result.accepted is result.stored is True
    assert result.idempotent_replay is False
    assert len(calls) == 1
    assert calls[0]["include_principal_scope_capability"] is False
    assert calls[0]["serialized_credential"] == "signed-credential-secret"
    assert conversation_scope_authority_view(authorities[0]) is None
    stored = _journal(path).load(created.conversation_id, request.idempotency_key)
    serialized = json.dumps({"result": result.to_dict(), "stored": stored})
    assert request.operator_text not in serialized
    assert "signed-credential-secret" not in serialized
    assert "principal_012" not in serialized


def test_exact_retry_after_restart_returns_original_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "restart.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    calls: list[dict[str, Any]] = []
    _install_lease(
        monkeypatch, lambda: _authority(path, created.conversation_id), calls
    )

    first = _reserve(path, request)
    replay = _reserve(path, request, journal=_journal(path, NOW + 1), now_epoch=NOW + 1)

    assert first.reservation_id == replay.reservation_id
    assert replay.accepted is replay.idempotent_replay is True
    assert replay.stored is False
    assert len(calls) == 2


@pytest.mark.parametrize(
    ("envelope", "now_epoch", "reason"),
    [
        (object(), NOW, "resident_conversation_request_type_invalid"),
        (
            object.__new__(ResidentConversationRequest),
            NOW,
            "resident_conversation_request_invalid",
        ),
        (object(), -1, "resident_conversation_now_invalid"),
        (
            replace(
                _request("sha256:" + "6" * 64),
                issued_at=NOW - 60,
                expires_at=NOW,
            ),
            NOW,
            "resident_conversation_request_expired",
        ),
        (
            replace(
                _request("sha256:" + "6" * 64),
                issued_at=NOW + 31,
                expires_at=NOW + 61,
            ),
            NOW,
            "resident_conversation_request_not_yet_valid",
        ),
        (
            _request("", expected_revision=-1),
            NOW,
            "resident_conversation_new_scope_resolution_required",
        ),
    ],
)
def test_invalid_or_new_scope_request_rejects_before_session_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    envelope: object,
    now_epoch: int,
    reason: str,
) -> None:
    calls: list[dict[str, Any]] = []
    _install_lease(monkeypatch, lambda: None, calls)

    result = _reserve(tmp_path / "preflight.sqlite", envelope, now_epoch=now_epoch)

    assert result.rejection_reasons == (reason,)
    assert calls == []


def test_session_source_reason_is_preserved_and_unknown_failure_is_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "source.sqlite"
    created = _create(path)

    @contextmanager
    def unavailable(**_kwargs: Any):
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_authority_source_missing"
        )
        yield

    monkeypatch.setattr(
        admission, "lease_current_generation_conversation_session", unavailable
    )
    rejected = _reserve(path, _request(created.conversation_id))
    assert rejected.rejection_reasons == (
        "conversation_session_authority_source_missing",
    )

    @contextmanager
    def secret_bearing(**_kwargs: Any):
        raise ConversationSessionAuthoritySourceError("synthetic-credential-detail")
        yield

    monkeypatch.setattr(
        admission, "lease_current_generation_conversation_session", secret_bearing
    )
    sanitized = _reserve(path, _request(created.conversation_id))
    assert sanitized.rejection_reasons == (admission.UNAVAILABLE_REASON,)

    @contextmanager
    def broken(**_kwargs: Any):
        raise RuntimeError("private detail")
        yield

    monkeypatch.setattr(
        admission, "lease_current_generation_conversation_session", broken
    )
    closed = _reserve(path, _request(created.conversation_id))
    assert closed.rejection_reasons == (admission.UNAVAILABLE_REASON,)


def test_constructed_unregistered_authority_cannot_admit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "forged.sqlite"
    created = _create(path)
    calls: list[dict[str, Any]] = []
    _install_lease(
        monkeypatch,
        lambda: object.__new__(VerifiedConversationScopeAuthority),
        calls,
    )

    result = _reserve(path, _request(created.conversation_id))

    assert result.rejection_reasons == ("resident_conversation_access_denied",)
    assert _journal(path).load(
        created.conversation_id, _request(created.conversation_id).idempotency_key
    )["reason"] == "resident_conversation_request_reservation_missing"


def test_mismatched_live_authority_is_consumed_without_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "mismatch.sqlite"
    created = _create(path)
    authorities: list[Any] = []

    def mismatched():
        value = _authority(
            path, created.conversation_id, session_binding="window:other"
        )
        authorities.append(value)
        return value

    _install_lease(monkeypatch, mismatched, [])
    result = _reserve(path, _request(created.conversation_id))

    assert result.rejection_reasons == ("resident_conversation_access_denied",)
    assert conversation_scope_authority_view(authorities[0]) is None


def test_atomic_consumer_rejects_e0_record_from_another_session(
    tmp_path: Path,
) -> None:
    path = tmp_path / "e0-session-transplant.sqlite"
    serialized = signed_credential()
    signing_context, _anchor = signed_context(serialized)
    created = create_signed_scope(path, signing_context, serialized)
    record = _store(path).load(created.conversation_id)["record"]
    authenticated = authenticate_signed_conversation_scope(
        serialized_credential=serialized,
        transport="editor",
        session_binding="window:other",
        expected_repo_full_name=SIGNED_REPO,
        principal_resolver=SignedResolver(),
        now_epoch=NOW,
        record_signing_context=signing_context,
    )
    assert authenticated is not None
    parent = consume_conversation_scope_capability(
        authenticated[0],
        active_foundup_id=str(record["authorized_foundup_id"]),
        discussion_foundup_ids=tuple(record["discussion_foundup_ids"]),
        now_epoch=NOW,
        scope_kind=str(record["scope_kind"]),
    )

    child = consume_verified_scope_authority_for_request_journal(
        parent,
        record=record,
        reservation_id="sha256:" + "5" * 64,
        not_before_epoch=NOW,
        scope_expires_at=min(
            int(record["expires_at"]),
            int(conversation_scope_authority_view(parent)["expires_at"]),
        ),
    )

    assert child is None
    assert conversation_scope_authority_view(parent) is None


def test_atomic_consumer_retires_parent_on_hostile_record_mapping(
    tmp_path: Path,
) -> None:
    path = tmp_path / "hostile-record.sqlite"
    created = _create(path)
    parent = _authority(path, created.conversation_id)

    class HostileRecord(Mapping):
        def __getitem__(self, _key: object):
            raise RuntimeError("record callback")

        def __iter__(self):
            return iter(())

        def __len__(self):
            return 0

        def get(self, _key: object, _default: object = None):
            raise RuntimeError("record callback")

    child = consume_verified_scope_authority_for_request_journal(
        parent,
        record=HostileRecord(),
        reservation_id="sha256:" + "4" * 64,
        not_before_epoch=NOW,
        scope_expires_at=NOW + 60,
    )

    assert child is None
    assert conversation_scope_authority_view(parent) is None


def test_journal_failure_remains_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "journal-failure.sqlite"
    created = _create(path)
    _install_lease(
        monkeypatch, lambda: _authority(path, created.conversation_id), []
    )

    class BrokenJournal:
        def reserve(self, *_args: Any, **_kwargs: Any):
            raise RuntimeError("store detail")

    result = _reserve(
        path, _request(created.conversation_id), journal=BrokenJournal()
    )
    assert result.rejection_reasons == (
        "resident_conversation_request_journal_unavailable",
    )


def test_generation_lease_remains_held_through_journal_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "lease-lifetime.sqlite"
    created = _create(path)
    active = {"value": False}

    @contextmanager
    def held_lease(**_kwargs: Any):
        authority = _authority(path, created.conversation_id)
        active["value"] = True
        try:
            yield SimpleNamespace(authority=authority)
        finally:
            active["value"] = False
            discard_conversation_scope_capability(authority)

    class ObservedJournal(AgentDbResidentConversationRequestJournal):
        def reserve(self, *args: Any, **kwargs: Any):
            assert active["value"] is True
            return super().reserve(*args, **kwargs)

    monkeypatch.setattr(
        admission, "lease_current_generation_conversation_session", held_lease
    )
    result = _reserve(
        path,
        _request(created.conversation_id),
        journal=ObservedJournal(lambda: TestAgentDb(path), clock=lambda: NOW),
    )

    assert result.accepted is True
    assert active["value"] is False


def test_verified_authority_is_atomically_one_use_sequentially_and_concurrently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "atomic-parent.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    sequential = _authority(path, created.conversation_id)

    first = scope_binding.bind_resident_conversation_request_to_verified_scope_authority(
        store=_store(path), authority=sequential, request=request, now_epoch=NOW
    )
    second = scope_binding.bind_resident_conversation_request_to_verified_scope_authority(
        store=_store(path), authority=sequential, request=request, now_epoch=NOW
    )
    assert first.accepted is True
    assert second.rejection_reasons == ("resident_conversation_access_denied",)
    discard_conversation_scope_capability(first._reservation_capability)

    shared = _authority(path, created.conversation_id)
    barrier = Barrier(2)
    original = scope_binding._current_record_request_rejection_reason

    def synchronized(record: Any, candidate: Any, now_epoch: int):
        barrier.wait(timeout=5)
        return original(record, candidate, now_epoch)

    monkeypatch.setattr(
        scope_binding, "_current_record_request_rejection_reason", synchronized
    )

    def bind_once():
        return scope_binding.bind_resident_conversation_request_to_verified_scope_authority(
            store=_store(path), authority=shared, request=request, now_epoch=NOW
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: bind_once(), range(2)))

    assert sum(result.accepted for result in results) == 1
    assert sorted(
        result.rejection_reasons for result in results if not result.accepted
    ) == [("resident_conversation_access_denied",)]
    for result in results:
        discard_conversation_scope_capability(result._reservation_capability)


def test_admission_slice_respects_wsp62_caps_and_has_no_effect_wiring() -> None:
    paths = (
        Path(admission.__file__),
        ROOT
        / "modules/communication/moltbot_bridge/src/"
        / "reddog_conversation_scope_capability.py",
        ROOT
        / "modules/communication/moltbot_bridge/src/"
        / "reddog_resident_conversation_scope_binding.py",
    )
    for path in paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert len(source.splitlines()) <= 500
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 50
    source = paths[0].read_text(encoding="utf-8")
    assert "model.invoke" not in source
    assert "worker_dispatch" not in source
    assert "conversation_handler" not in source
