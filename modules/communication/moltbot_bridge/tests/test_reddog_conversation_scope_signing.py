"""Security tests for durable E0 conversation-scope authentication."""

from __future__ import annotations

import json
import threading
from dataclasses import replace
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src.reddog_authenticated_conversation_scope_state import resume_authenticated_conversation_scope
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_authentication import (
    authenticate_signed_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_digest import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_request import (
    ConversationScopeAdvanceRequest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_record import (
    revision_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_advance import (
    advance_authenticated_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_pending_store import (
    RECOVERY_VOLATILE_FIELDS,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    CONVERSATION_SCOPE_SIGNING_PREFIX,
    MAX_SIGNING_INPUT_BYTES,
    MIN_SOCKET_REQUEST_BYTES,
    ConversationScopeSigningContext,
    build_conversation_scope_signing_request,
    verify_signed_conversation_scope_record,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    REJECT_ED25519_SIGNER_CONVERSATION_ANCHOR_MISSING,
    REJECT_ED25519_SIGNER_CONVERSATION_POLICY_MISSING,
    REJECT_ED25519_SIGNER_CONVERSATION_REJECTED,
    REJECT_ED25519_SIGNER_CONVERSATION_RESOLVER_MISSING,
)
from modules.communication.moltbot_bridge.src.reddog_signer_conversation_scope_anchor import (
    AtomicSignerConversationScopeAnchorStore,
    InMemorySignerConversationScopeAnchorStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_test_support import (
    FOCUS,
    HOLO_GENERATION,
    SNAPSHOT_DIGEST,
    SNAPSHOT_ID,
    TestAgentDb,
    digest,
    grounding_receipt,
    item,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_signing_test_support import (
    NOW,
    REPO,
    REPO_ROOT,
    BackendClient,
    ChangingAuditMacBuilder,
    CrashBeforeFinalizeStore,
    Resolver,
    UnavailableSignerClient,
    anchor_payload as _anchor_payload,
    capability as _capability,
    context as _context,
    create as _create,
    credential as _credential,
    store as _store,
)


def test_e0_signature_survives_store_restart_and_bearer_is_not_persisted(tmp_path: Path) -> None:
    serialized = _credential()
    context, _anchor = _context(serialized)
    path = tmp_path / "scope.sqlite"
    created = _create(path, context, serialized)
    assert created.accepted is True
    stored = _store(path).load(created.conversation_id)["record"]
    assert stored["record_auth_scheme"] == "ed25519-e0-v1"
    assert serialized not in json.dumps(stored, sort_keys=True)

    resumed = resume_authenticated_conversation_scope(
        store=_store(path),
        capability=_capability(context, serialized, NOW),
        conversation_id=created.conversation_id,
        expected_head_sha=grounding_receipt()["holoindex_repo_head_sha"],
        expected_holoindex_generation_id=HOLO_GENERATION,
        expected_source_snapshot_id=SNAPSHOT_ID,
        expected_source_snapshot_digest=SNAPSHOT_DIGEST,
        now_epoch=NOW,
    )
    assert resumed.accepted is True


def test_e0_signer_authenticates_principal_scope_without_foundup_authority(
    tmp_path: Path,
) -> None:
    serialized = _credential()
    context, _anchor = _context(serialized)
    path = tmp_path / "principal-scope.sqlite"
    created = _create(
        path,
        context,
        serialized,
        request_overrides={
            "scope_kind": "principal",
            "work_focus": "Discuss principal operating principles.",
            "grounding_receipt": {},
            "discussion_foundup_ids": (),
            "accepted_decisions": (item("Audit before implementation."),),
            "open_questions": (),
            "repository_evidence_refs": (),
            "source_snapshot_id": "",
            "source_snapshot_digest": "",
        },
    )
    assert created.accepted is True
    stored = _store(path).load(created.conversation_id)["record"]
    assert stored["scope_kind"] == "principal"
    assert stored["authorized_foundup_id"] == ""
    assert verify_signed_conversation_scope_record(context, stored) is True


def test_tamper_and_forged_credential_fail_closed(tmp_path: Path) -> None:
    serialized = _credential()
    context, _anchor = _context(serialized)
    created = _create(tmp_path / "scope.sqlite", context, serialized)
    assert created.accepted is True
    stored = _store(tmp_path / "scope.sqlite").load(created.conversation_id)["record"]
    assert verify_signed_conversation_scope_record(
        context, {**stored, "current_objective": "attacker-selected"}
    ) is False
    assert verify_signed_conversation_scope_record(
        context, {**stored, "record_auth_audit_mac": "attacker-rehashed-audit"}
    ) is False

    forged = _credential(key=Ed25519PrivateKey.generate())
    forged_context = ConversationScopeSigningContext(
        signer=context.signer,
        signer_public_key=context.signer_public_key,
        key_epoch=context.key_epoch,
        serialized_session_credential=forged,
    )
    request = build_conversation_scope_signing_request(forged_context, stored)
    assert request is not None
    response = forged_context.signer.sign(request)
    assert response.accepted is False
    assert response.rejection_code == REJECT_ED25519_SIGNER_CONVERSATION_REJECTED


def test_anchor_rejects_fork_and_is_idempotent() -> None:
    anchor = InMemorySignerConversationScopeAnchorStore()
    first = _anchor_payload()
    prepared = anchor.prepare(first)
    response = {"signature": "ed25519-sig-v1:first"}
    anchor.commit(first, response, expected_revision=prepared.expected_revision)
    replay = anchor.prepare(first)
    assert replay.replay_response == response

    fork = {
        **first,
        "conversation_revision": 1,
        "record_state_digest": "sha256:" + "6" * 64,
        "record_auth_nonce": "sha256:" + "7" * 64,
        "previous_record_auth_signature_digest": "sha256:" + "8" * 64,
    }
    try:
        anchor.prepare(fork)
    except ValueError as exc:
        assert str(exc) == "conversation_scope_anchor_rollback_or_fork"
    else:
        raise AssertionError("fork accepted")


def test_agentdb_pending_create_recovers_after_signer_commit_crash(
    tmp_path: Path,
) -> None:
    serialized = _credential()
    clock = [NOW]
    context, anchor = _context(serialized, clock=clock)
    path = tmp_path / "scope.sqlite"
    base = _store(path)

    with pytest.raises(RuntimeError, match="simulated_process_crash"):
        _create(
            path,
            context,
            serialized,
            store=CrashBeforeFinalizeStore(base),
        )

    rows = TestAgentDb(path).db.execute_query(
        "SELECT conversation_id FROM reddog_conversation_scope_pending"
    )
    assert len(rows) == 1
    conversation_id = str(rows[0][0])
    assert base.load(conversation_id)["record"] is None
    assert anchor.load()["heads"][conversation_id]["conversation_revision"] == 0

    clock[0] = NOW + 10
    recovered = _create(path, context, serialized, now_epoch=NOW + 10)
    assert recovered.accepted is True
    assert recovered.conversation_id == conversation_id
    assert TestAgentDb(path).db.execute_query(
        "SELECT COUNT(*) FROM reddog_conversation_scope_pending"
    )[0][0] == 0


def test_agentdb_pending_advance_recovers_after_signer_commit_crash(
    tmp_path: Path,
) -> None:
    serialized = _credential()
    clock = [NOW]
    context, anchor = _context(serialized, clock=clock)
    path = tmp_path / "scope.sqlite"
    created = _create(path, context, serialized)
    current = _store(path).load(created.conversation_id)["record"]
    request = ConversationScopeAdvanceRequest(
        conversation_id=created.conversation_id,
        expected_revision=0,
        work_focus=FOCUS,
        grounding_receipt=grounding_receipt(),
        state_patch={
            "turn_id": digest({"turn": "crash-recovery-second"}),
            "parent_turn_id": current["turn_id"],
            "active_topic": "TRADE runtime",
            "current_objective": "Recover the exact signed revision.",
            "repository_evidence_refs": ("code:trade",),
        },
        expected_source_snapshot_id=SNAPSHOT_ID,
        expected_source_snapshot_digest=SNAPSHOT_DIGEST,
    )

    with pytest.raises(RuntimeError, match="simulated_process_crash"):
        advance_authenticated_conversation_scope(
            store=CrashBeforeFinalizeStore(_store(path)),
            capability=_capability(context, serialized),
            repo_root=REPO_ROOT,
            request=request,
            now_epoch=NOW,
        )

    assert _store(path).load(created.conversation_id)["record"][
        "conversation_revision"
    ] == 0
    assert anchor.load()["heads"][created.conversation_id][
        "conversation_revision"
    ] == 1
    clock[0] = NOW + 10
    recovered = advance_authenticated_conversation_scope(
        store=_store(path),
        capability=_capability(context, serialized, NOW + 10),
        repo_root=REPO_ROOT,
        request=request,
        now_epoch=NOW + 10,
    )
    assert recovered.accepted is True
    assert recovered.conversation_revision == 1


def test_attacker_rehashed_pending_record_cannot_change_signed_state(
    tmp_path: Path,
) -> None:
    serialized = _credential()
    context, _anchor = _context(serialized)
    path = tmp_path / "scope.sqlite"
    with pytest.raises(RuntimeError, match="simulated_process_crash"):
        _create(
            path,
            context,
            serialized,
            store=CrashBeforeFinalizeStore(_store(path)),
        )
    layer = TestAgentDb(path).db
    row = layer.execute_query(
        "SELECT conversation_id, unsigned_json FROM reddog_conversation_scope_pending"
    )[0]
    tampered = json.loads(row[1])
    tampered["updated_at"] += 1
    tampered["record_auth_nonce"] = canonical_digest(
        {
            "conversation_id": tampered["conversation_id"],
            "conversation_revision": tampered["conversation_revision"],
            "turn_id": tampered["turn_id"],
            "updated_at": tampered["updated_at"],
            "previous_record_auth_signature_digest": tampered[
                "previous_record_auth_signature_digest"
            ],
        }
    )
    tampered["revision_receipts"] = [
        revision_receipt(tampered, previous="", revision=0)
    ]
    tampered_digest = canonical_digest(tampered)
    tampered_recovery = canonical_digest(
        {
            key: value
            for key, value in tampered.items()
            if key not in RECOVERY_VOLATILE_FIELDS
        }
    )
    with layer.get_connection() as connection:
        connection.execute(
            "UPDATE reddog_conversation_scope_pending SET unsigned_json = ?, unsigned_digest = ?, recovery_digest = ? WHERE conversation_id = ?",
                (
                    json.dumps(tampered, sort_keys=True, separators=(",", ":")),
                    tampered_digest,
                    tampered_recovery,
                    row[0],
                ),
        )

    rejected = _create(path, context, serialized, now_epoch=NOW + 10)
    assert rejected.accepted is False
    assert rejected.rejection_reasons == (
        "conversation_scope_record_authentication_unavailable",
    )
    assert _store(path).load(str(row[0]))["record"] is None


def test_recovery_only_request_without_signer_anchor_fails_closed(
    tmp_path: Path,
) -> None:
    serialized = _credential()
    clock = [NOW]
    context, anchor = _context(serialized, clock=clock)
    unavailable = replace(context, signer=UnavailableSignerClient())
    path = tmp_path / "scope.sqlite"

    first = _create(path, unavailable, serialized)
    assert first.accepted is False
    assert not anchor.load()

    clock[0] = NOW + 10
    rejected = _create(path, context, serialized, now_epoch=NOW + 10)
    assert rejected.accepted is False
    assert rejected.rejection_reasons == (
        "conversation_scope_record_authentication_unavailable",
    )
    assert not anchor.load()


def test_exact_pending_retry_after_signer_outage_can_sign_normally(
    tmp_path: Path,
) -> None:
    serialized = _credential()
    context, anchor = _context(serialized)
    unavailable = replace(context, signer=UnavailableSignerClient())
    path = tmp_path / "scope.sqlite"

    assert _create(path, unavailable, serialized).accepted is False
    recovered = _create(path, context, serialized)

    assert recovered.accepted is True
    assert anchor.load()["heads"][recovered.conversation_id][
        "conversation_revision"
    ] == 0


def test_exact_retry_after_anchor_commit_replays_without_resigning(
    tmp_path: Path,
) -> None:
    serialized = _credential()
    audit = ChangingAuditMacBuilder()
    context, _anchor = _context(serialized, audit_builder=audit)
    path = tmp_path / "scope.sqlite"

    with pytest.raises(RuntimeError, match="simulated_process_crash"):
        _create(
            path,
            context,
            serialized,
            store=CrashBeforeFinalizeStore(_store(path)),
        )
    recovered = _create(path, context, serialized)

    assert recovered.accepted is True
    assert audit.calls == 1


def test_atomic_anchor_survives_restart_and_never_persists_bearer(
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "signer-runtime"
    path = runtime_root / "conversation-anchor.json"
    first = _anchor_payload()
    response = {"signature": "ed25519-sig-v1:first"}
    initial = AtomicSignerConversationScopeAnchorStore(
        path, runtime_root=runtime_root, repo_root=REPO_ROOT
    )
    prepared = initial.prepare(first)
    initial.commit(first, response, expected_revision=prepared.expected_revision)

    restarted = AtomicSignerConversationScopeAnchorStore(
        path, runtime_root=runtime_root, repo_root=REPO_ROOT
    )
    replay = restarted.prepare(first)
    assert replay.replay_response == response
    persisted = path.read_text(encoding="utf-8")
    assert "serialized_session_credential" not in persisted
    assert _credential() not in persisted


def test_atomic_anchor_allows_only_one_concurrent_successor(tmp_path: Path) -> None:
    runtime_root = tmp_path / "signer-runtime"
    path = runtime_root / "conversation-anchor.json"
    first = _anchor_payload()
    first_response = {"signature": "ed25519-sig-v1:first"}
    store = AtomicSignerConversationScopeAnchorStore(
        path, runtime_root=runtime_root, repo_root=REPO_ROOT
    )
    prepared = store.prepare(first)
    store.commit(first, first_response, expected_revision=prepared.expected_revision)
    previous = canonical_digest({"record_auth_signature": first_response["signature"]})
    successors = (
        {
            **_anchor_payload(revision=1, state="6", nonce="7"),
            "previous_record_auth_signature_digest": previous,
        },
        {
            **_anchor_payload(revision=1, state="8", nonce="9"),
            "previous_record_auth_signature_digest": previous,
        },
    )
    stores = tuple(
        AtomicSignerConversationScopeAnchorStore(
            path, runtime_root=runtime_root, repo_root=REPO_ROOT
        )
        for _ in successors
    )
    preparations = tuple(
        candidate.prepare(payload)
        for candidate, payload in zip(stores, successors, strict=True)
    )
    barrier = threading.Barrier(2)
    results: list[str] = []

    def commit(index: int) -> None:
        barrier.wait()
        try:
            stores[index].commit(
                successors[index],
                {"signature": f"ed25519-sig-v1:successor-{index}"},
                expected_revision=preparations[index].expected_revision,
            )
            results.append("committed")
        except (RuntimeError, ValueError):
            results.append("rejected")

    workers = tuple(threading.Thread(target=commit, args=(index,)) for index in range(2))
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=5)
    assert results.count("committed") == 1
    assert results.count("rejected") == 1


def test_stale_credential_and_unavailable_signer_fail_before_active_persistence(
    tmp_path: Path,
) -> None:
    serialized = _credential()
    context, _anchor = _context(serialized)
    assert authenticate_signed_conversation_scope(
        serialized_credential=serialized,
        transport="editor",
        session_binding="window:one",
        expected_repo_full_name=REPO,
        principal_resolver=Resolver(),
        now_epoch=NOW + 301,
        record_signing_context=context,
    ) is None

    unavailable = replace(context, signer=UnavailableSignerClient())
    path = tmp_path / "scope.sqlite"
    result = _create(path, unavailable, serialized)
    assert result.accepted is False
    missing = _store(path).load(result.conversation_id or "missing")
    assert missing == {
        "ok": False,
        "reason": "conversation_scope_missing",
        "record": None,
    }
    raw = path.read_bytes()
    assert serialized.encode("utf-8") not in raw


def test_conversation_request_cannot_cross_signing_domain(tmp_path: Path) -> None:
    serialized = _credential()
    context, _anchor = _context(serialized)
    created = _create(tmp_path / "scope.sqlite", context, serialized)
    stored = _store(tmp_path / "scope.sqlite").load(
        created.conversation_id
    )["record"]
    request = build_conversation_scope_signing_request(context, stored)
    assert request is not None
    response = context.signer.sign(
        replace(request, requested_operation="attest_control_loop_receipt")
    )
    assert response.accepted is False


def test_escape_heavy_maximum_input_fits_declared_socket_budget() -> None:
    signing_input = CONVERSATION_SCOPE_SIGNING_PREFIX + "\\" * (
        MAX_SIGNING_INPUT_BYTES - len(CONVERSATION_SCOPE_SIGNING_PREFIX)
    )
    request = SigningRequest(
        signing_input=signing_input,
        payload_digest="sha256:" + "a" * 64,
        signer_role="reddog",
        signer_public_key="ed25519-pub-v1:" + "b" * 43,
        requester_principal_id="principal_012",
        nonce="sha256:" + "c" * 64,
        key_epoch="epoch-1",
        requested_operation="attest_conversation_scope_state",
        authority_tier="NONE",
        consensus_receipt_digest=None,
    )
    raw = (
        json.dumps(
            {"schema_version": "reddog_signer_socket_request.v1", "request": request.to_dict()},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")
    assert len(raw) <= MIN_SOCKET_REQUEST_BYTES <= 262144


def test_context_rejects_wrong_signer_key_and_epoch(tmp_path: Path) -> None:
    serialized = _credential()
    context, _anchor = _context(serialized)
    created = _create(tmp_path / "scope.sqlite", context, serialized)
    assert created.accepted is True
    stored = _store(tmp_path / "scope.sqlite").load(created.conversation_id)["record"]
    wrong_key = encode_ed25519_public_key(
        Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    )
    assert verify_signed_conversation_scope_record(
        ConversationScopeSigningContext(
            signer=context.signer,
            signer_public_key=wrong_key,
            key_epoch=context.key_epoch,
            serialized_session_credential=serialized,
        ),
        stored,
    ) is False
    assert verify_signed_conversation_scope_record(
        ConversationScopeSigningContext(
            signer=context.signer,
            signer_public_key=context.signer_public_key,
            key_epoch="epoch-2",
            serialized_session_credential=serialized,
        ),
        stored,
    ) is False


def test_signer_rejects_missing_conversation_dependencies(tmp_path: Path) -> None:
    serialized = _credential()
    context, _anchor = _context(serialized)
    created = _create(tmp_path / "scope.sqlite", context, serialized)
    stored = _store(tmp_path / "scope.sqlite").load(
        created.conversation_id
    )["record"]
    request = build_conversation_scope_signing_request(context, stored)
    assert request is not None
    backend = context.signer.backend
    cases = (
        (
            replace(backend, conversation_scope_signer_policy=None),
            REJECT_ED25519_SIGNER_CONVERSATION_POLICY_MISSING,
        ),
        (
            replace(backend, conversation_scope_principal_resolver=None),
            REJECT_ED25519_SIGNER_CONVERSATION_RESOLVER_MISSING,
        ),
        (
            replace(backend, conversation_scope_anchor_store=None),
            REJECT_ED25519_SIGNER_CONVERSATION_ANCHOR_MISSING,
        ),
    )
    for candidate, expected in cases:
        response = BackendClient(candidate).sign(request)
        assert response.accepted is False
        assert response.rejection_code == expected
