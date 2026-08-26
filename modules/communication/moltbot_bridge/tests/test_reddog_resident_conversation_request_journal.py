"""Adversarial tests for durable resident conversation request reservations."""

from __future__ import annotations

import ast
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_authenticated_conversation_scope_state import (
    advance_authenticated_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_request import (
    ConversationScopeAdvanceRequest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    VerifiedConversationScopeAuthority,
    derive_resident_conversation_request_journal_authority,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_request_journal import (
    AgentDbResidentConversationRequestJournal,
    reserve_bound_resident_conversation_request,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_request_reservation_contract import (
    reservation_identity,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_test_support import (
    FOCUS,
    NOW,
    ROOT,
    SNAPSHOT_DIGEST,
    SNAPSHOT_ID,
    TestAgentDb,
    capability,
    digest,
    grounding_receipt,
    state_patch,
)
from modules.communication.moltbot_bridge.tests.test_reddog_resident_conversation_scope_binding import (
    _bind,
    _create,
    _request,
    _store,
)


def _journal(
    path: Path, now_epoch: int = NOW
) -> AgentDbResidentConversationRequestJournal:
    return AgentDbResidentConversationRequestJournal(
        lambda: TestAgentDb(path), clock=lambda: now_epoch
    )


def _reserve(path: Path, request, binding=None, *, now_epoch: int = NOW):
    admitted = binding if binding is not None else _bind(path, request, now_epoch=now_epoch)
    return reserve_bound_resident_conversation_request(
        journal=_journal(path, now_epoch), request=request, binding=admitted,
        now_epoch=now_epoch,
    )


def test_reservation_is_content_free_and_does_not_mutate_scope(tmp_path: Path) -> None:
    path = tmp_path / "journal.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    before = _store(path).load(created.conversation_id)["record"]

    result = _reserve(path, request)

    assert result.accepted is True
    assert result.stored is True
    assert result.idempotent_replay is False
    assert result.status == "RESIDENT_CONVERSATION_REQUEST_RESERVED"
    assert result.conversation_cas_reserved is False
    assert result.conversation_scope_mutation_performed is False
    assert result.grants_identity_authority is False
    assert result.grants_effect_authority is False
    assert _store(path).load(created.conversation_id)["record"] == before

    loaded = _journal(path).load(created.conversation_id, request.idempotency_key)
    serialized = json.dumps(loaded, sort_keys=True)
    assert loaded["ok"] is True
    assert request.operator_text not in serialized
    assert "principal_012" not in serialized
    assert '"trade"' not in serialized
    assert "operator_text" not in serialized


def test_exact_retry_returns_original_reservation_after_restart(tmp_path: Path) -> None:
    path = tmp_path / "restart.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    first = _reserve(path, request)

    replay = reserve_bound_resident_conversation_request(
        journal=AgentDbResidentConversationRequestJournal(
            lambda: TestAgentDb(path), clock=lambda: NOW + 1
        ),
        request=request,
        binding=_bind(path, request),
        now_epoch=NOW + 1,
    )

    assert first.accepted is replay.accepted is True
    assert first.reservation_id == replay.reservation_id
    assert replay.stored is False
    assert replay.idempotent_replay is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"operator_text": "Altered request under the same idempotency key."},
        {
            "idempotency_key": digest({"idempotency": "other"}),
            "client_nonce": digest({"nonce": "other"}),
        },
        {
            "idempotency_key": digest({"idempotency": "other"}),
            "request_id": digest({"request": "other"}),
        },
    ],
)
def test_divergent_key_request_or_nonce_reuse_rejects(
    tmp_path: Path, overrides: dict[str, object]
) -> None:
    path = tmp_path / "conflict.sqlite"
    created = _create(path)
    assert _reserve(path, _request(created.conversation_id)).accepted is True

    divergent = _request(created.conversation_id, **overrides)
    rejected = _reserve(path, divergent)

    assert rejected.accepted is False
    assert rejected.rejection_reasons == (
        "resident_conversation_request_idempotency_conflict",
    )


def test_scope_change_between_binding_and_reservation_rejects(tmp_path: Path) -> None:
    path = tmp_path / "scope-race.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    binding = _bind(path, request)
    current = _store(path).load(created.conversation_id)["record"]
    advanced = advance_authenticated_conversation_scope(
        store=_store(path), capability=capability(), repo_root=ROOT,
        request=ConversationScopeAdvanceRequest(
            conversation_id=created.conversation_id, expected_revision=0,
            work_focus=FOCUS, grounding_receipt=grounding_receipt(),
            state_patch=state_patch(current["turn_id"]),
            expected_source_snapshot_id=SNAPSHOT_ID,
            expected_source_snapshot_digest=SNAPSHOT_DIGEST,
        ),
        now_epoch=NOW + 1,
    )
    assert advanced.accepted is True

    rejected = _reserve(path, request, binding, now_epoch=NOW + 1)

    assert rejected.rejection_reasons == (
        "resident_conversation_request_scope_changed",
    )
    assert _journal(path).load(
        created.conversation_id, request.idempotency_key
    )["reason"] == "resident_conversation_request_reservation_missing"


@pytest.mark.parametrize("operation", ["STATUS", "CANCEL"])
def test_control_operations_reserve_current_turn_only(
    tmp_path: Path, operation: str
) -> None:
    path = tmp_path / f"{operation.lower()}.sqlite"
    created = _create(path)
    current_turn = _store(path).load(created.conversation_id)["record"]["turn_id"]
    request = _request(
        created.conversation_id, operation=operation,
        turn_id=current_turn, operator_text="",
    )

    result = _reserve(path, request)

    assert result.accepted is True
    assert result.operation == operation


def test_rejected_or_tampered_binding_cannot_create_reservation(tmp_path: Path) -> None:
    path = tmp_path / "binding.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    accepted = _bind(path, request)
    tampered = replace(accepted, record_digest="sha256:" + "0" * 64)

    rejected = _reserve(path, request, tampered)

    assert rejected.rejection_reasons == (
        "resident_conversation_scope_binding_invalid",
    )
    assert _journal(path).load(
        created.conversation_id, request.idempotency_key
    )["reason"] == "resident_conversation_request_reservation_missing"


def test_constructed_binding_without_opaque_admission_proof_rejects(tmp_path: Path) -> None:
    path = tmp_path / "forged-binding.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    forged = replace(_bind(path, request))

    rejected = _reserve(path, request, forged)

    assert rejected.rejection_reasons == (
        "resident_conversation_scope_binding_invalid",
    )
    assert "_reservation_capability" not in forged.to_dict()


def test_unregistered_verified_authority_cannot_mint_journal_proof() -> None:
    forged_parent = object.__new__(VerifiedConversationScopeAuthority)

    forged_child = derive_resident_conversation_request_journal_authority(
        forged_parent,
        reservation_id=digest({"reservation": "forged"}),
        not_before_epoch=NOW,
        scope_expires_at=NOW + 60,
    )

    assert forged_child is None


def test_scope_expiry_between_binding_and_insert_rejects(tmp_path: Path) -> None:
    path = tmp_path / "scope-expiry.sqlite"
    created = _create(path, ttl_seconds=10)
    request = _request(created.conversation_id)
    binding = _bind(path, request)

    rejected = _reserve(path, request, binding, now_epoch=NOW + 10)

    assert rejected.rejection_reasons == (
        "resident_conversation_scope_binding_invalid",
    )


def test_expiry_and_store_failure_remain_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "closed.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    binding = _bind(path, request)

    expired = _reserve(path, request, binding, now_epoch=NOW + 60)
    assert expired.rejection_reasons == (
        "resident_conversation_request_expired",
    )

    def unavailable():
        raise RuntimeError("store unavailable")

    failed = reserve_bound_resident_conversation_request(
        journal=AgentDbResidentConversationRequestJournal(
            unavailable, clock=lambda: NOW
        ),
        request=request, binding=binding, now_epoch=NOW,
    )
    assert failed.rejection_reasons == (
        "resident_conversation_request_journal_unavailable",
    )

    class RaisingJournal:
        def reserve(self, _record, **_kwargs):
            raise RuntimeError("adapter failure")

    failed_adapter = reserve_bound_resident_conversation_request(
        journal=RaisingJournal(), request=request, binding=_bind(path, request),
        now_epoch=NOW,
    )
    assert failed_adapter.rejection_reasons == (
        "resident_conversation_request_journal_unavailable",
    )


def test_concurrent_exact_reservation_has_one_writer(tmp_path: Path) -> None:
    path = tmp_path / "concurrent.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    bindings = [_bind(path, request) for _index in range(8)]

    def reserve_once(index: int):
        return _reserve(path, request, bindings[index])

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(reserve_once, range(8)))

    assert all(result.accepted for result in results)
    assert sum(result.stored for result in results) == 1
    assert sum(result.idempotent_replay for result in results) == 7
    assert len({result.reservation_id for result in results}) == 1


def test_concurrent_divergent_collision_has_one_acceptance(tmp_path: Path) -> None:
    path = tmp_path / "divergent-concurrent.sqlite"
    created = _create(path)
    original = _request(created.conversation_id)
    divergent = _request(
        created.conversation_id,
        operator_text="Divergent content under the same request identities.",
    )
    requests = (original, divergent)
    bindings = tuple(_bind(path, request) for request in requests)

    def reserve_once(index: int):
        return _reserve(path, requests[index], bindings[index])

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reserve_once, range(2)))

    assert sum(result.accepted for result in results) == 1
    assert sum(
        result.rejection_reasons
        == ("resident_conversation_request_idempotency_conflict",)
        for result in results
    ) == 1


@pytest.mark.parametrize("payload", [None, {"ok": True, "record": {}}])
def test_malformed_journal_success_never_escapes_or_accepts(
    tmp_path: Path, payload
) -> None:
    path = tmp_path / "malformed-adapter.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)

    class MalformedJournal:
        def reserve(self, _record, **_kwargs):
            return payload

    result = reserve_bound_resident_conversation_request(
        journal=MalformedJournal(), request=request, binding=_bind(path, request),
        now_epoch=NOW,
    )

    assert result.rejection_reasons == (
        "resident_conversation_request_journal_unavailable",
    )


def test_wrong_valid_journal_record_rejects(tmp_path: Path) -> None:
    path = tmp_path / "wrong-adapter-record.sqlite"
    created = _create(path)
    request = _request(created.conversation_id)
    binding = _bind(path, request)

    class WrongJournal:
        def reserve(self, candidate, **_kwargs):
            wrong = dict(candidate)
            wrong["turn_id"] = digest({"turn": "wrong-adapter"})
            wrong["reservation_id"] = canonical_digest(reservation_identity(wrong))
            return {
                "ok": True, "reason": "", "record": wrong,
                "stored": True, "idempotent_replay": False,
            }

    result = reserve_bound_resident_conversation_request(
        journal=WrongJournal(), request=request, binding=binding, now_epoch=NOW,
    )

    assert result.rejection_reasons == (
        "resident_conversation_request_journal_unavailable",
    )


def test_request_journal_respects_wsp62_limits() -> None:
    source_root = Path(__file__).parents[1] / "src"
    names = (
        "reddog_resident_conversation_request_journal.py",
        "reddog_resident_conversation_request_journal_store.py",
        "reddog_resident_conversation_request_reservation_contract.py",
        "reddog_conversation_scope_capability.py",
        "reddog_resident_conversation_scope_binding.py",
        "reddog_conversation_scope_pending_store.py",
    )
    for name in names:
        source = (source_root / name).read_text(encoding="utf-8")
        functions = [
            node for node in ast.walk(ast.parse(source))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assert len(source.splitlines()) <= 500
        assert all(node.end_lineno - node.lineno + 1 <= 50 for node in functions)
    contract = (source_root / names[2]).read_text(encoding="utf-8")
    assert '"operator_text"' not in contract.split("_RECORD_FIELDS", 1)[1].split(")", 1)[0]
