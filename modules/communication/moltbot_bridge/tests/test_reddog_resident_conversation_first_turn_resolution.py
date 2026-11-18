"""Adversarial tests for durable empty-ID first-TURN resolution."""

from __future__ import annotations

import ast
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from threading import Barrier

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_resident_conversation_first_turn_binding as binding,
    reddog_resident_conversation_first_turn_resolution as resolution,
)
from modules.communication.moltbot_bridge.src.reddog_authenticated_conversation_scope_state import (
    advance_authenticated_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    consume_conversation_scope_capability,
    conversation_scope_authority_view,
    discard_conversation_scope_capability,
    split_foundup_conversation_scope_capability_pair,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_request import (
    ConversationScopeAdvanceRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_first_turn_contract import (
    RESERVATION_KIND,
    SCHEMA_VERSION,
    first_turn_request_binding_digest,
    first_turn_reservation_identity,
    first_turn_scope_binding_id,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_request_journal_store import (
    AgentDbResidentConversationRequestJournal,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_test_support import (
    FOCUS,
    NOW,
    ROOT,
    TestAgentDb,
    capability,
    digest,
    grounding_receipt,
    state_patch,
)
from modules.communication.moltbot_bridge.tests.test_reddog_resident_conversation_new_scope_admission import (
    _intent,
    _request,
    _store,
)


def _journal(path: Path, *, fail_reserve: bool = False):
    class Journal(AgentDbResidentConversationRequestJournal):
        def reserve(self, record, *, admission_authority=None):
            if fail_reserve:
                raise RuntimeError("injected_journal_failure")
            return super().reserve(record, admission_authority=admission_authority)

    return Journal(lambda: TestAgentDb(path), clock=lambda: NOW)


def _install_lease(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, Any]]:
    issued: list[tuple[Any, Any]] = []

    @contextmanager
    def fake_lease(**kwargs: Any):
        children = split_foundup_conversation_scope_capability_pair(
            capability(now_epoch=kwargs["now_epoch"])
        )
        assert children is not None
        authorities = tuple(
            consume_conversation_scope_capability(
                child, active_foundup_id="trade",
                discussion_foundup_ids=("trade",), now_epoch=kwargs["now_epoch"],
            )
            for child in children
        )
        assert all(authority is not None for authority in authorities)
        issued.append(authorities)
        view = conversation_scope_authority_view(authorities[0])
        assert view is not None
        session = SimpleNamespace(
            principal_id=view["principal_id"],
            session_binding_digest=view["session_binding_digest"],
            authority_receipt={"session_id": view["session_id"]},
            authority=authorities[0], secondary_authority=authorities[1],
        )
        try:
            yield session
        finally:
            for authority in authorities:
                discard_conversation_scope_capability(authority)

    monkeypatch.setattr(
        resolution, "lease_current_generation_conversation_session", fake_lease
    )
    return issued


def _resolve(
    path: Path, request: Any, intent: Any, *, now_epoch: int = NOW,
    journal: Any = None,
):
    return resolution.resolve_current_generation_resident_conversation_first_turn(
        repo_root=ROOT, intent=intent,
        grounding_receipt_id=intent["grounding_receipt"]["receipt_id"],
        serialized_credential="signed-session-secret",
        owner_config_path="O:/RedDog/runtime/owner.ini", now_epoch=now_epoch,
        scope_store=_store(path), request_journal=journal or _journal(path),
        request=request,
    )


def _stored_reservation(path: Path) -> dict[str, Any]:
    row = TestAgentDb(path).db.execute_query(
        "SELECT reservation_json FROM reddog_conversation_request_journal"
    )[0]
    return json.loads(row["reservation_json"])


def _write_reservation(path: Path, record: dict[str, Any]) -> None:
    raw = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    with TestAgentDb(path).db.get_connection() as connection:
        connection.execute(
            "UPDATE reddog_conversation_request_journal SET conversation_id = ?, "
            "idempotency_key = ?, request_id = ?, client_nonce = ?, "
            "reservation_json = ?, reservation_digest = ?",
            (
                record["conversation_id"], record["idempotency_key"],
                record["request_id"], record["client_nonce"], raw,
                canonical_digest(record),
            ),
        )


def test_initial_turn_creates_one_scope_and_explicit_content_free_v2_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "first-turn.sqlite"
    request = _request()
    issued = _install_lease(monkeypatch)

    result = _resolve(path, request, _intent(request))

    assert result.accepted is True
    assert result.stored is True
    assert result.expected_revision == 0
    assert result.source_request_digest == request.request_digest()
    assert len(issued) == 1
    assert all(conversation_scope_authority_view(item) is None for item in issued[0])
    record = _stored_reservation(path)
    assert record["schema_version"] == SCHEMA_VERSION
    assert record["reservation_kind"] == RESERVATION_KIND
    assert record["source_conversation_id"] == ""
    assert record["source_expected_revision"] == -1
    assert record["request_digest"] == replace(
        request, conversation_id=result.conversation_id, expected_revision=0
    ).request_digest()
    serialized = json.dumps({"result": result.to_dict(), "record": record})
    assert request.operator_text not in serialized
    assert "signed-session-secret" not in serialized
    assert len(TestAgentDb(path).db.execute_query(
        "SELECT conversation_id FROM reddog_conversation_scopes"
    )) == 1


def test_exact_restart_replays_one_v2_link_without_creating_another_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "restart.sqlite"
    request = _request()
    _install_lease(monkeypatch)
    first = _resolve(path, request, _intent(request))
    second = _resolve(path, request, _intent(request))

    assert first.accepted is second.accepted is True
    assert first.reservation_id == second.reservation_id
    assert second.stored is False
    assert second.idempotent_replay is True
    assert len(TestAgentDb(path).db.execute_query(
        "SELECT conversation_id FROM reddog_conversation_scopes"
    )) == 1


def test_replay_rejects_rewritten_idempotency_even_with_rehashed_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "request-binding-tamper.sqlite"
    request = _request()
    _install_lease(monkeypatch)
    first = _resolve(path, request, _intent(request))
    forged = replace(
        request, idempotency_key=digest({"first-turn-idempotency": "forged"})
    )
    resolved = replace(
        forged, conversation_id=first.conversation_id, expected_revision=0
    )
    record = _stored_reservation(path)
    scope = _store(path).load(first.conversation_id)["record"]
    commitment = first_turn_request_binding_digest(forged, resolved)
    record.update(
        {
            "request_digest": resolved.request_digest(),
            "source_request_digest": forged.request_digest(),
            "idempotency_key": forged.idempotency_key,
            "initial_turn_request_binding_digest": commitment,
            "binding_id": first_turn_scope_binding_id(
                request_binding_digest=commitment,
                revision_receipt_id=record["revision_receipt_id"],
                initial_scope_state_digest=record["initial_scope_state_digest"],
                principal_record_digest=scope["principal_record_digest"],
                session_binding_digest=scope["session_binding_digest"],
            ),
        }
    )
    record["reservation_id"] = canonical_digest(first_turn_reservation_identity(record))
    _write_reservation(path, record)

    replayed = _resolve(path, forged, _intent(forged))

    assert replayed.accepted is False
    assert replayed.rejection_reasons == (
        "resident_conversation_first_turn_replay_invalid",
    )


def test_scope_only_crash_is_recovered_then_journaled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "crash-recovery.sqlite"
    request = _request()
    _install_lease(monkeypatch)
    failed = _resolve(
        path, request, _intent(request), journal=_journal(path, fail_reserve=True)
    )
    recovered = _resolve(path, request, _intent(request))

    assert failed.accepted is False
    assert failed.rejection_reasons == (resolution.UNAVAILABLE_REASON,)
    assert recovered.accepted is True
    assert recovered.stored is True
    assert len(TestAgentDb(path).db.execute_query(
        "SELECT conversation_id FROM reddog_conversation_scopes"
    )) == 1


def test_related_key_divergence_and_nonce_reuse_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "divergence.sqlite"
    original = _request()
    _install_lease(monkeypatch)
    assert _resolve(path, original, _intent(original)).accepted is True
    related = _request(
        request_id=digest({"first-turn-request": "related"}),
        operator_text="Divergent but reuses the idempotency key.",
    )
    conflict = _resolve(
        path, related,
        _intent(related, grounding_receipt=grounding_receipt(focus=related.operator_text)),
    )
    distinct = _request(
        request_id=digest({"first-turn-request": "distinct"}),
        turn_id=digest({"first-turn-turn": "distinct"}),
        idempotency_key=digest({"first-turn-idempotency": "distinct"}),
        operator_text="Divergent request with only the nonce reused.",
    )
    nonce_conflict = _resolve(
        path, distinct,
        _intent(distinct, grounding_receipt=grounding_receipt(focus=distinct.operator_text)),
    )

    assert conflict.rejection_reasons == (
        "resident_conversation_request_idempotency_conflict",
    )
    assert nonce_conflict.accepted is False
    assert nonce_conflict.rejection_reasons == (
        "resident_conversation_request_idempotency_conflict",
    )


def test_concurrent_exact_requests_converge_on_one_scope_and_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "concurrent.sqlite"
    request = _request()
    intent = _intent(request)
    _install_lease(monkeypatch)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _index: _resolve(path, request, intent), range(8)))

    assert all(result.accepted for result in results)
    assert len({result.reservation_id for result in results}) == 1
    assert sum(result.stored for result in results) == 1
    assert len(TestAgentDb(path).db.execute_query(
        "SELECT conversation_id FROM reddog_conversation_scopes"
    )) == 1
    assert len(TestAgentDb(path).db.execute_query(
        "SELECT reservation_id FROM (SELECT reservation_digest AS reservation_id "
        "FROM reddog_conversation_request_journal)"
    )) == 1


def test_authenticated_replay_accepts_later_revision_but_rejects_link_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "later-revision.sqlite"
    request = _request()
    _install_lease(monkeypatch)
    first = _resolve(path, request, _intent(request))
    current = _store(path).load(first.conversation_id)["record"]
    advanced = advance_authenticated_conversation_scope(
        store=_store(path), capability=capability(now_epoch=NOW + 1), repo_root=ROOT,
        request=ConversationScopeAdvanceRequest(
            conversation_id=first.conversation_id, expected_revision=0,
            work_focus=FOCUS, grounding_receipt=grounding_receipt(),
            state_patch=state_patch(current["turn_id"]),
            expected_source_snapshot_id="", expected_source_snapshot_digest="",
        ),
        now_epoch=NOW + 1,
    )
    assert advanced.accepted is True
    replayed = _resolve(path, request, _intent(request), now_epoch=NOW + 2)
    assert replayed.accepted is True
    assert replayed.idempotent_replay is True

    record = _stored_reservation(path)
    record["revision_receipt_id"] = digest({"forged": "initial-receipt"})
    record["reservation_id"] = canonical_digest(first_turn_reservation_identity(record))
    _write_reservation(path, record)
    rejected = _resolve(path, request, _intent(request), now_epoch=NOW + 2)
    assert rejected.rejection_reasons == (
        "resident_conversation_first_turn_replay_invalid",
    )


def test_same_replay_authority_is_consumed_atomically_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "atomic-replay.sqlite"
    request = _request()
    _install_lease(monkeypatch)
    first = _resolve(path, request, _intent(request))
    resolved = replace(
        request, conversation_id=first.conversation_id, expected_revision=0
    )
    reservation = _stored_reservation(path)
    authority = consume_conversation_scope_capability(
        capability(now_epoch=NOW + 1), active_foundup_id="trade",
        discussion_foundup_ids=("trade",), now_epoch=NOW + 1,
    )
    assert authority is not None
    barrier = Barrier(2)
    original_load = binding._load_record

    def synchronized_load(store: Any, conversation_id: str):
        record = original_load(store, conversation_id)
        barrier.wait()
        return record

    monkeypatch.setattr(binding, "_load_record", synchronized_load)
    with ThreadPoolExecutor(max_workers=2) as pool:
        reasons = list(pool.map(
            lambda _index: binding.validate_resolved_initial_turn_replay(
                store=_store(path), authority=authority, source_request=request,
                resolved_request=resolved, reservation=reservation,
                now_epoch=NOW + 1,
            ),
            range(2),
        ))

    assert reasons.count("") == 1
    assert reasons.count("resident_conversation_access_denied") == 1


def test_first_turn_slice_respects_wsp62_and_has_no_effect_wiring() -> None:
    root = ROOT / "modules/communication/moltbot_bridge/src"
    paths = (
        root / "reddog_conversation_scope_identity.py",
        root / "reddog_conversation_scope_capability.py",
        root / "reddog_conversation_session_authority_source.py",
        root / "reddog_resident_conversation_first_turn_contract.py",
        root / "reddog_resident_conversation_first_turn_binding.py",
        Path(resolution.__file__),
        root / "reddog_resident_conversation_request_journal_store.py",
    )
    forbidden = (
        "execute_handler(", "model_client(", "dispatch_worker(",
        "subprocess.", "git ",
    )
    for path in paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert len(source.splitlines()) <= 500
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 50
        if "first_turn" in path.name:
            lowered = source.lower()
            assert all(token not in lowered for token in forbidden)
