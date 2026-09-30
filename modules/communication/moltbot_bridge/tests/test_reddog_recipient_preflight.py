import hashlib
import inspect
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_correspondence_state import (
    AskRecord,
    AskStatus,
    CorrespondenceEvent,
    CorrespondenceState,
    FollowUpGate,
    Freshness,
    RedDogCorrespondenceStateStore,
    SentCoverageState,
    build_scope_key,
    state_digest,
    state_payload,
    summarize_ask_state,
)
from modules.communication.moltbot_bridge.src.reddog_recipient_preflight import (
    EvidenceLevel,
    PreflightDecision,
    ProposedRecipient,
    RecipientRole,
    RouteEvidence,
    RoutePolicy,
    normalize_address,
    preflight_recipients,
    verify_sent_readback,
)
from modules.communication.moltbot_bridge.src.reddog_correspondence_sender_boundary import (
    CorrespondenceTransaction,
    ProviderSendResult,
    SenderBoundaryDecision,
    bind_preflight_receipt,
    execute_sender_boundary,
    transaction_digest,
)
from modules.infrastructure.database.src.db_manager import DatabaseManager


def ev(identity, address, level=EvidenceLevel.CONTACTS, **kw):
    return RouteEvidence(identity, address, "test", level, **kw)


def test_newer_explicit_provider_route_overrides_stale_contacts():
    receipt = preflight_recipients(
        [ProposedRecipient("org-1", RecipientRole.TO, "new-route@example.org")],
        [
            ev("org-1", "old-route@example.org", EvidenceLevel.CONTACTS),
            ev("org-1", "new-route@example.org", EvidenceLevel.EXPLICIT_PROVIDER),
        ],
    )
    assert receipt.decision is PreflightDecision.SEND
    assert receipt.checks[0].authoritative_address == "new-route@example.org"


def test_near_match_hyphen_difference_blocks():
    receipt = preflight_recipients(
        [ProposedRecipient("org-1", RecipientRole.TO, "team-a@example.org")],
        [ev("org-1", "teama@example.org", EvidenceLevel.EXPLICIT_PROVIDER)],
    )
    assert receipt.decision is PreflightDecision.BLOCK
    assert "org-1:EXACT_ADDRESS_MISMATCH" in receipt.reasons


def test_personal_route_closed_blocks_even_exact_address():
    receipt = preflight_recipients(
        [ProposedRecipient("person-1", RecipientRole.TO, "person@example.org")],
        [
            ev(
                "person-1",
                "person@example.org",
                EvidenceLevel.ROUTING_POLICY,
                policy=RoutePolicy.PERSONAL_ROUTE_CLOSED,
                entity_kind="person",
            )
        ],
    )
    assert receipt.decision is PreflightDecision.BLOCK
    assert "person-1:PERSONAL_ROUTE_CLOSED" in receipt.reasons


def test_bcc_only_policy_blocks_cc():
    receipt = preflight_recipients(
        [ProposedRecipient("observer-1", RecipientRole.CC, "observer@example.org")],
        [
            ev(
                "observer-1",
                "observer@example.org",
                EvidenceLevel.ROUTING_POLICY,
                policy=RoutePolicy.BCC_ONLY,
            )
        ],
    )
    assert receipt.decision is PreflightDecision.BLOCK
    assert "observer-1:ROLE_POLICY_VIOLATION_BCC_ONLY" in receipt.reasons


def test_newer_address_evidence_does_not_silently_reopen_closed_route():
    receipt = preflight_recipients(
        [ProposedRecipient("person-1", RecipientRole.TO, "person@example.org")],
        [
            ev(
                "person-1",
                "person@example.org",
                EvidenceLevel.ROUTING_POLICY,
                policy=RoutePolicy.PERSONAL_ROUTE_CLOSED,
                entity_kind="person",
            ),
            ev(
                "person-1",
                "person@example.org",
                EvidenceLevel.EXPLICIT_PROVIDER,
                entity_kind="person",
            ),
        ],
    )
    assert receipt.decision is PreflightDecision.BLOCK
    assert "person-1:PERSONAL_ROUTE_CLOSED" in receipt.reasons


def test_duplicate_sent_coverage_blocks_by_default():
    receipt = preflight_recipients(
        [ProposedRecipient("org-1", RecipientRole.TO, "route@example.org")],
        [ev("org-1", "route@example.org")],
        already_sent_addresses=["route@example.org"],
    )
    assert receipt.decision is PreflightDecision.BLOCK
    assert "org-1:DUPLICATE_SENT_COVERAGE" in receipt.reasons


def test_conflicting_top_precedence_routes_block():
    receipt = preflight_recipients(
        [ProposedRecipient("org-1", RecipientRole.TO, "a@example.org")],
        [
            ev("org-1", "a@example.org", EvidenceLevel.EXPLICIT_PROVIDER),
            ev("org-1", "b@example.org", EvidenceLevel.EXPLICIT_PROVIDER),
        ],
    )
    assert receipt.decision is PreflightDecision.BLOCK
    assert "org-1:CONFLICTING_AUTHORITATIVE_ADDRESSES" in receipt.reasons


def test_unknown_route_blocks():
    receipt = preflight_recipients(
        [ProposedRecipient("missing", RecipientRole.TO, "x@example.org")],
        [],
    )
    assert receipt.decision is PreflightDecision.BLOCK
    assert "missing:UNKNOWN_ROUTE" in receipt.reasons


def test_sent_only_or_unverified_contact_route_blocks():
    receipt = preflight_recipients(
        [ProposedRecipient("org-1", RecipientRole.TO, "route@example.org")],
        [
            ev(
                "org-1",
                "route@example.org",
                EvidenceLevel.CONTACTS,
                verified=False,
            )
        ],
    )
    assert receipt.decision is PreflightDecision.BLOCK
    assert "org-1:UNVERIFIED_ROUTE" in receipt.reasons


def test_verified_public_directory_can_authorize_when_contact_history_is_unverified():
    receipt = preflight_recipients(
        [ProposedRecipient("org-1", RecipientRole.TO, "route@example.org")],
        [
            ev(
                "org-1",
                "route@example.org",
                EvidenceLevel.CONTACTS,
                verified=False,
            ),
            ev(
                "org-1",
                "route@example.org",
                EvidenceLevel.PUBLIC_DIRECTORY,
                verified=True,
            ),
        ],
    )
    assert receipt.decision is PreflightDecision.SEND
    assert receipt.checks[0].authoritative_source == "test"


def test_display_name_and_case_normalize_without_character_rewrite():
    assert normalize_address("Example Person <User.Name+tag@Example.Org>") == (
        "user.name+tag@example.org"
    )


def test_mixed_transaction_blocks_if_one_recipient_fails():
    receipt = preflight_recipients(
        [
            ProposedRecipient("good", RecipientRole.TO, "good@example.org"),
            ProposedRecipient("bad", RecipientRole.CC, "wrong@example.org"),
        ],
        [
            ev("good", "good@example.org"),
            ev("bad", "right@example.org"),
        ],
    )
    assert receipt.decision is PreflightDecision.BLOCK
    assert receipt.checks[0].allowed is True
    assert receipt.checks[1].allowed is False


def test_sent_readback_matches_approved_transaction():
    receipt = preflight_recipients(
        [
            ProposedRecipient("a", RecipientRole.TO, "a@example.org"),
            ProposedRecipient("b", RecipientRole.BCC, "B Person <b@example.org>"),
        ],
        [ev("a", "a@example.org"), ev("b", "b@example.org")],
    )
    result = verify_sent_readback(
        receipt,
        {
            RecipientRole.TO: ["A <A@example.org>"],
            RecipientRole.CC: [],
            RecipientRole.BCC: ["b@example.org"],
        },
    )
    assert result.ok is True


def test_sent_readback_detects_extra_or_missing_recipient():
    receipt = preflight_recipients(
        [ProposedRecipient("a", RecipientRole.TO, "a@example.org")],
        [ev("a", "a@example.org")],
    )
    result = verify_sent_readback(
        receipt,
        {
            RecipientRole.TO: ["other@example.org"],
            RecipientRole.CC: [],
            RecipientRole.BCC: [],
        },
    )
    assert result.ok is False
    assert "SENT_READBACK_MISSING_RECIPIENT" in result.reasons
    assert "SENT_READBACK_EXTRA_RECIPIENT" in result.reasons



def _boundary_transaction(
    *,
    address="route@example.org",
    role=RecipientRole.TO,
    content_digest="sha256:content-v1",
    provider_object_id="draft-1",
):
    return CorrespondenceTransaction(
        provider="gmail",
        purpose_scope="YUMORI::UTILITY::PROCEDURE_INQUIRY",
        recipients=(ProposedRecipient("org-1", role, address),),
        content_digest=content_digest,
        provider_object_id=provider_object_id,
        thread_id="thread-1",
    )


def _boundary_send_receipt(transaction, *, issued_at=None, ttl_seconds=300):
    receipt = preflight_recipients(
        list(transaction.recipients),
        [ev("org-1", "route@example.org", EvidenceLevel.PUBLIC_DIRECTORY)],
    )
    assert receipt.decision is PreflightDecision.SEND
    return bind_preflight_receipt(
        receipt,
        transaction,
        issued_at=issued_at or datetime(2026, 9, 30, 8, 0, tzinfo=timezone.utc),
        ttl_seconds=ttl_seconds,
    )


def test_sender_boundary_transaction_digest_binds_recipient_role_and_content():
    base = _boundary_transaction()
    assert transaction_digest(base) == transaction_digest(_boundary_transaction())
    assert transaction_digest(base) != transaction_digest(
        _boundary_transaction(role=RecipientRole.CC)
    )
    assert transaction_digest(base) != transaction_digest(
        _boundary_transaction(content_digest="sha256:content-v2")
    )


def test_sender_boundary_missing_receipt_never_invokes_provider():
    calls = {"send": 0}

    def provider_send(_transaction):
        calls["send"] += 1
        return ProviderSendResult("mid-1", "thread-1")

    result = execute_sender_boundary(
        authorization=None,
        load_current_transaction=_boundary_transaction,
        provider_send=provider_send,
        provider_readback=lambda _result: {},
        now=datetime(2026, 9, 30, 8, 1, tzinfo=timezone.utc),
    )

    assert result.decision is SenderBoundaryDecision.BLOCK
    assert result.reasons == ("MISSING_PREFLIGHT_RECEIPT",)
    assert result.provider_invoked is False
    assert calls["send"] == 0


def test_sender_boundary_block_receipt_never_invokes_provider():
    tx = _boundary_transaction()
    blocked = preflight_recipients(
        list(tx.recipients),
        [ev("org-1", "different@example.org", EvidenceLevel.PUBLIC_DIRECTORY)],
    )
    authorization = bind_preflight_receipt(
        blocked,
        tx,
        issued_at=datetime(2026, 9, 30, 8, 0, tzinfo=timezone.utc),
    )
    calls = {"send": 0}

    def provider_send(_transaction):
        calls["send"] += 1
        return ProviderSendResult("mid-1", "thread-1")

    result = execute_sender_boundary(
        authorization=authorization,
        load_current_transaction=lambda: tx,
        provider_send=provider_send,
        provider_readback=lambda _result: {},
        now=datetime(2026, 9, 30, 8, 1, tzinfo=timezone.utc),
    )

    assert result.decision is SenderBoundaryDecision.BLOCK
    assert "PREFLIGHT_NOT_SEND" in result.reasons
    assert calls["send"] == 0


def test_sender_boundary_stale_receipt_never_invokes_provider():
    tx = _boundary_transaction()
    authorization = _boundary_send_receipt(tx, ttl_seconds=60)
    calls = {"send": 0}

    def provider_send(_transaction):
        calls["send"] += 1
        return ProviderSendResult("mid-1", "thread-1")

    result = execute_sender_boundary(
        authorization=authorization,
        load_current_transaction=lambda: tx,
        provider_send=provider_send,
        provider_readback=lambda _result: {},
        now=datetime(2026, 9, 30, 8, 2, 1, tzinfo=timezone.utc),
    )

    assert result.decision is SenderBoundaryDecision.BLOCK
    assert "STALE_PREFLIGHT_RECEIPT" in result.reasons
    assert calls["send"] == 0


def test_sender_boundary_changed_draft_invalidates_receipt_before_provider():
    authorized_tx = _boundary_transaction()
    current_tx = _boundary_transaction(content_digest="sha256:changed-after-preflight")
    authorization = _boundary_send_receipt(authorized_tx)
    calls = {"send": 0}

    def provider_send(_transaction):
        calls["send"] += 1
        return ProviderSendResult("mid-1", "thread-1")

    result = execute_sender_boundary(
        authorization=authorization,
        load_current_transaction=lambda: current_tx,
        provider_send=provider_send,
        provider_readback=lambda _result: {},
        now=datetime(2026, 9, 30, 8, 1, tzinfo=timezone.utc),
    )

    assert result.decision is SenderBoundaryDecision.BLOCK
    assert "TRANSACTION_MISMATCH" in result.reasons
    assert calls["send"] == 0


def test_sender_boundary_valid_receipt_requires_exact_post_send_readback():
    tx = _boundary_transaction()
    authorization = _boundary_send_receipt(tx)
    calls = {"send": 0, "readback": 0}

    def provider_send(current):
        calls["send"] += 1
        assert current == tx
        return ProviderSendResult("mid-1", "thread-1")

    def provider_readback(result):
        calls["readback"] += 1
        assert result.provider_message_id == "mid-1"
        return {
            RecipientRole.TO: ["Route <route@example.org>"],
            RecipientRole.CC: [],
            RecipientRole.BCC: [],
        }

    result = execute_sender_boundary(
        authorization=authorization,
        load_current_transaction=lambda: tx,
        provider_send=provider_send,
        provider_readback=provider_readback,
        now=datetime(2026, 9, 30, 8, 1, tzinfo=timezone.utc),
    )

    assert result.decision is SenderBoundaryDecision.VERIFIED_SENT
    assert result.provider_invoked is True
    assert result.reasons == ()
    assert calls == {"send": 1, "readback": 1}


def test_sender_boundary_readback_mismatch_is_integrity_incident_not_verified_sent():
    tx = _boundary_transaction()
    authorization = _boundary_send_receipt(tx)

    result = execute_sender_boundary(
        authorization=authorization,
        load_current_transaction=lambda: tx,
        provider_send=lambda _transaction: ProviderSendResult("mid-1", "thread-1"),
        provider_readback=lambda _result: {
            RecipientRole.TO: ["wrong@example.org"],
            RecipientRole.CC: [],
            RecipientRole.BCC: [],
        },
        now=datetime(2026, 9, 30, 8, 1, tzinfo=timezone.utc),
    )

    assert result.decision is SenderBoundaryDecision.PROVIDER_SENT_INTEGRITY_INCIDENT
    assert "SENT_READBACK_MISSING_RECIPIENT" in result.reasons
    assert "SENT_READBACK_EXTRA_RECIPIENT" in result.reasons


def test_sender_boundary_provider_exception_requires_sent_reconciliation_before_retry():
    tx = _boundary_transaction()
    authorization = _boundary_send_receipt(tx)

    def provider_send(_transaction):
        raise RuntimeError("ambiguous transport failure")

    result = execute_sender_boundary(
        authorization=authorization,
        load_current_transaction=lambda: tx,
        provider_send=provider_send,
        provider_readback=lambda _result: {},
        now=datetime(2026, 9, 30, 8, 1, tzinfo=timezone.utc),
    )

    assert result.decision is SenderBoundaryDecision.PROVIDER_STATE_UNKNOWN
    assert result.provider_invoked is True
    assert result.reasons == ("PROVIDER_SEND_RAISED_RECONCILE_BEFORE_RETRY",)


@pytest.fixture
def isolated_correspondence_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDUPS_DB_ENGINE", "sqlite")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "correspondence.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    DatabaseManager.reset_for_tests()
    try:
        yield
    finally:
        DatabaseManager.reset_for_tests()


def test_correspondence_scope_key_is_deterministic_and_machine_safe():
    assert build_scope_key("Fukui City", "Sukatto", "financial disclosure") == (
        "FUKUI_CITY::SUKATTO::FINANCIAL_DISCLOSURE"
    )


def test_correspondence_event_insert_is_idempotent_and_metadata_only(
    isolated_correspondence_db,
):
    store = RedDogCorrespondenceStateStore()
    event = CorrespondenceEvent(
        provider="gmail",
        account_key="primary",
        message_id="mid-1",
        thread_id="tid-1",
        scope_key="FUKUI_CITY::SUKATTO::FINANCIAL_DISCLOSURE",
        direction="IN",
        occurred_at="2026-09-17T17:10:23+09:00",
        event_type="PROCEDURAL_REPLY",
        subject_digest="sha256:subject",
        content_digest="sha256:content",
        provider_status="RECEIVED",
    )

    assert store.record_event(event) is True
    assert store.record_event(event) is False

    rows = store.list_events(event.scope_key)
    assert len(rows) == 1
    assert rows[0]["message_id"] == "mid-1"
    assert "body" not in rows[0]
    assert "to" not in rows[0]
    assert "cc" not in rows[0]
    assert "bcc" not in rows[0]


def test_correspondence_state_roundtrip_preserves_ask_accounting_and_digest(
    isolated_correspondence_db,
):
    store = RedDogCorrespondenceStateStore()
    state = CorrespondenceState(
        scope_key="FUKUI_CITY::SUKATTO::FINANCIAL_DISCLOSURE",
        procedure_lane="INFO_DISCLOSURE",
        active_thread_ids=("tid-1",),
        latest_inbound_mid="mid-city",
        latest_inbound_at="2026-09-17T17:10:23+09:00",
        latest_outbound_mid="mid-yumori",
        latest_outbound_at="2026-09-17T17:39:05+09:00",
        asks=(
            AskRecord(
                "ASK-FIN-001",
                AskStatus.FORMAL_ROUTE_REQUIRED,
                "OPERATING_ACTUALS",
            ),
            AskRecord(
                "ASK-FIN-002",
                AskStatus.FORMAL_ROUTE_REQUIRED,
                "UTILITY_COSTS",
            ),
            AskRecord(
                "ASK-ROUTE-001",
                AskStatus.ANSWERED,
                "USE_FORMAL_DISCLOSURE",
            ),
        ),
        sent_coverage_state=SentCoverageState.SAME_MESSAGE_SENT,
        routing_state="FORMAL_DISCLOSURE_ONLY",
        follow_up_gate=FollowUpGate.BLOCK_DUPLICATE,
        procedure_state="OFFICIAL_EFORM_VERIFIED_NOT_FILED",
        next_expected_event="FORMAL_DISCLOSURE_RECEIPT",
        next_allowed_action="FILE_OFFICIAL_DISCLOSURE",
        provider_watermark="gmail:mid-yumori",
        reconciled_at="2026-09-28T08:30:00+09:00",
        freshness=Freshness.VALID,
    )

    digest = store.upsert_state(state)
    restored = store.load_state(state.scope_key)

    assert restored == state
    assert digest == state_digest(state)
    summary = summarize_ask_state(restored.asks)
    assert summary["open"] == ("ASK-FIN-001", "ASK-FIN-002")
    assert summary["answered"] == ("ASK-ROUTE-001",)


def test_correspondence_provider_watermark_is_change_detector_not_ordering_claim(
    isolated_correspondence_db,
):
    store = RedDogCorrespondenceStateStore()
    state = CorrespondenceState(
        scope_key="ORG::TOPIC",
        provider_watermark="opaque-a",
        freshness=Freshness.VALID,
    )
    store.upsert_state(state)

    assert store.provider_refresh_required("ORG::TOPIC", "opaque-a") is False
    assert store.provider_refresh_required("ORG::TOPIC", "opaque-b") is True
    assert store.provider_refresh_required("ORG::UNKNOWN", "opaque-a") is True


def test_correspondence_invalid_delta_reference_fails_closed(
    isolated_correspondence_db,
):
    store = RedDogCorrespondenceStateStore()
    state = CorrespondenceState(
        scope_key="ORG::TOPIC",
        asks=(AskRecord("ASK-1", AskStatus.OPEN),),
        new_delta_ask_ids=("ASK-2",),
    )
    with pytest.raises(ValueError, match="new_delta_ask_ids"):
        store.upsert_state(state)


def test_correspondence_serialized_state_contains_codes_not_raw_message_content():
    state = CorrespondenceState(
        scope_key="ORG::TOPIC",
        asks=(
            AskRecord(
                "ASK-1",
                AskStatus.WAITING_PROVIDER,
                "PROCUREMENT_STAGE",
            ),
        ),
        next_allowed_action="WAIT_PROVIDER",
        provider_watermark="provider:opaque",
        freshness=Freshness.VALID,
    )
    payload = state_payload(state)
    encoded = json.dumps(payload, sort_keys=True)

    assert "raw_body" not in encoded
    assert "recipient_addresses" not in encoded
    assert "PROCUREMENT_STAGE" in encoded


def _persist_read_case(store, case):
    """Seed synthetic cache corruption without going through writer validation."""
    if case == "absent":
        return
    state = CorrespondenceState(
        scope_key="ORG::TOPIC",
        asks=(AskRecord("ASK-1", AskStatus.OPEN),),
        provider_watermark="fixture-watermark",
        freshness=Freshness.VALID,
    )
    initial_digest = store.upsert_state(state)
    payload = state_payload(state)
    if case == "unsupported_schema":
        payload["schema_version"] = "unsupported.v99"
    elif case == "missing_schema":
        del payload["schema_version"]
    elif case == "empty_scope":
        payload["scope_key"] = ""
    elif case == "scope_mismatch":
        payload["scope_key"] = "ORG::OTHER"
    elif case == "duplicate_ask_ids":
        payload["asks"].append(dict(payload["asks"][0]))
    elif case == "dangling_delta":
        payload["new_delta_ask_ids"] = ["ASK-UNKNOWN"]
    elif case == "negative_outbound_count":
        payload["outbound_since_latest_inbound"] = -1
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    digest = "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    if case == "missing_schema":
        digest = initial_digest  # Expose implicit schema defaulting, not a hash error.
    elif case == "digest_mismatch":
        digest = "sha256:" + "0" * 64
    store.update(
        "state", {"state_json": encoded, "state_digest": digest},
        "scope_key = ?", (state.scope_key,),
    )


@pytest.mark.parametrize("case,expected_error", [
    ("absent", None),
    ("digest_mismatch", "correspondence state digest mismatch"),
    ("unsupported_schema", "unsupported correspondence state schema"),
    ("missing_schema", "unsupported correspondence state schema"),
    ("empty_scope", "scope_key is required"),
    ("scope_mismatch", "correspondence state scope mismatch"),
    ("duplicate_ask_ids", "ask_id values must be unique within a scope"),
    ("dangling_delta", "new_delta_ask_ids must refer to declared asks"),
    ("negative_outbound_count", "outbound_since_latest_inbound must be >= 0"),
], ids=[
    "absent", "digest_mismatch", "unsupported_schema", "missing_schema",
    "empty_scope", "scope_mismatch", "duplicate_ask_ids", "dangling_delta",
    "negative_outbound_count",
])
def test_correspondence_persisted_read_validation(
    isolated_correspondence_db, tmp_path, case, expected_error,
):
    store = RedDogCorrespondenceStateStore()
    source = Path(inspect.getfile(RedDogCorrespondenceStateStore)).resolve()
    assert source == Path(__file__).resolve().parents[1] / "src/reddog_correspondence_state.py"
    assert store.db._backend["engine"] == "sqlite"
    assert Path(store.db._backend["db_path"]).resolve() == tmp_path / "correspondence.db"
    _persist_read_case(store, case)
    before = store.select("state")
    events_before = store.select("events")
    restored, error = None, None
    try:
        restored = store.load_state("ORG::TOPIC")
    except ValueError as exc:
        error = str(exc)
    after = store.select("state")
    events_after = store.select("events")
    print("CORRESPONDENCE_READ_EVIDENCE " + json.dumps({
        "case": case,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "expected_error": expected_error, "observed_error": error,
        "returned_state": state_payload(restored) if restored is not None else None,
        "rows_before": before, "rows_after": after,
        "events_before": events_before, "events_after": events_after,
        "sqlite_isolated": True,
    }, sort_keys=True))
    assert after == before
    assert events_after == events_before == []
    assert restored is None
    assert error == expected_error


@pytest.mark.parametrize("cached,observed,freshness,refresh", [
    pytest.param("None", None, Freshness.VALID, True, id="missing-observation"),
    pytest.param("True", True, Freshness.VALID, True, id="boolean-observation"),
    pytest.param("0", 0, Freshness.VALID, True, id="integer-observation"),
    pytest.param("1.5", 1.5, Freshness.VALID, True, id="float-observation"),
    pytest.param("[]", [], Freshness.VALID, True, id="list-observation"),
    pytest.param("{}", {}, Freshness.VALID, True, id="mapping-observation"),
    pytest.param("b'token'", b"token", Freshness.VALID, True, id="bytes-observation"),
    pytest.param("", "", Freshness.VALID, True, id="empty-evidence"),
    pytest.param("None", "None", Freshness.VALID, False, id="literal-none"),
    pytest.param("True", "True", Freshness.VALID, False, id="literal-true"),
    pytest.param("0", "0", Freshness.VALID, False, id="literal-zero"),
    pytest.param(" opaque ", " opaque ", Freshness.VALID, False, id="opaque-spaces"),
    pytest.param(" ", " ", Freshness.VALID, False, id="opaque-whitespace"),
    pytest.param("001", "1", Freshness.VALID, True, id="no-numeric-normalization"),
    pytest.param(" opaque ", "opaque", Freshness.VALID, True, id="no-trimming"),
    pytest.param("", "opaque", Freshness.VALID, True, id="missing-cached-token"),
    pytest.param("opaque", "opaque", Freshness.STALE, True, id="stale-equality"),
    pytest.param("opaque", "opaque", Freshness.UNKNOWN, True, id="unknown-equality"),
])
def test_correspondence_refresh_requires_nonempty_string_evidence(
    isolated_correspondence_db, cached, observed, freshness, refresh,
):
    store = RedDogCorrespondenceStateStore()
    store.upsert_state(CorrespondenceState(
        scope_key="ORG::TOPIC", provider_watermark=cached, freshness=freshness,
    ))
    before = store.select("state")
    assert store.provider_refresh_required("ORG::TOPIC", observed) is refresh
    assert store.select("state") == before
    assert store.list_events("ORG::TOPIC") == []


def test_correspondence_invalid_observation_preserves_cache_integrity_error(
    isolated_correspondence_db,
):
    store = RedDogCorrespondenceStateStore()
    _persist_read_case(store, "digest_mismatch")
    before = store.select("state")
    with pytest.raises(ValueError, match="correspondence state digest mismatch"):
        store.provider_refresh_required("ORG::TOPIC", None)
    assert store.select("state") == before
    assert store.list_events("ORG::TOPIC") == []
