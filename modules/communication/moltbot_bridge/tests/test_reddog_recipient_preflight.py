import hashlib
import inspect
import json
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




# Post-development contract-transfer controls; candidate was already visible.
# Separate evaluator review and frozen comparison precede any execution.
@pytest.mark.parametrize("case,observed,expected_error", [
    pytest.param('digest_mismatch', [], 'correspondence state digest mismatch', id='digest_mismatch-list'),
    pytest.param('digest_mismatch', b"fixture-watermark", 'correspondence state digest mismatch', id='digest_mismatch-bytes'),
    pytest.param('unsupported_schema', [], 'unsupported correspondence state schema', id='unsupported_schema-list'),
    pytest.param('unsupported_schema', b"fixture-watermark", 'unsupported correspondence state schema', id='unsupported_schema-bytes'),
    pytest.param('missing_schema', [], 'unsupported correspondence state schema', id='missing_schema-list'),
    pytest.param('missing_schema', b"fixture-watermark", 'unsupported correspondence state schema', id='missing_schema-bytes'),
    pytest.param('empty_scope', [], 'scope_key is required', id='empty_scope-list'),
    pytest.param('empty_scope', b"fixture-watermark", 'scope_key is required', id='empty_scope-bytes'),
    pytest.param('scope_mismatch', [], 'correspondence state scope mismatch', id='scope_mismatch-list'),
    pytest.param('scope_mismatch', b"fixture-watermark", 'correspondence state scope mismatch', id='scope_mismatch-bytes'),
    pytest.param('duplicate_ask_ids', [], 'ask_id values must be unique within a scope', id='duplicate_ask_ids-list'),
    pytest.param('duplicate_ask_ids', b"fixture-watermark", 'ask_id values must be unique within a scope', id='duplicate_ask_ids-bytes'),
    pytest.param('dangling_delta', [], 'new_delta_ask_ids must refer to declared asks', id='dangling_delta-list'),
    pytest.param('dangling_delta', b"fixture-watermark", 'new_delta_ask_ids must refer to declared asks', id='dangling_delta-bytes'),
    pytest.param('negative_outbound_count', [], 'outbound_since_latest_inbound must be >= 0', id='negative_outbound_count-list'),
    pytest.param('negative_outbound_count', b"fixture-watermark", 'outbound_since_latest_inbound must be >= 0', id='negative_outbound_count-bytes'),
])
def test_correspondence_transfer_invalid_observation_preserves_all_read_errors(
    isolated_correspondence_db, case, observed, expected_error,
):
    store = RedDogCorrespondenceStateStore()
    _persist_read_case(store, case)
    before = store.select("state")
    events_before = store.select("events")
    with pytest.raises(ValueError) as caught:
        store.provider_refresh_required("ORG::TOPIC", observed)
    assert str(caught.value) == expected_error
    assert store.select("state") == before
    assert store.select("events") == events_before == []


@pytest.mark.parametrize("cached,observed,refresh", [
    pytest.param("caf\u00e9", "caf\u00e9", False, id='unicode-nfc-equal'),
    pytest.param("cafe\u0301", "cafe\u0301", False, id='unicode-nfd-equal'),
    pytest.param("caf\u00e9", "cafe\u0301", True, id='unicode-normalization-distinct'),
    pytest.param("\uff11", "1", True, id='unicode-fullwidth-distinct'),
    pytest.param("(7,)", (7,), True, id='collision-tuple'),
    pytest.param("(1+2j)", (1+2j), True, id='collision-complex'),
    pytest.param("nan", float("nan"), True, id='collision-nan'),
    pytest.param("inf", float("inf"), True, id='collision-infinity'),
    pytest.param("nan", "nan", False, id='literal-nan'),
    pytest.param("inf", "inf", False, id='literal-infinity'),
])
def test_correspondence_transfer_opaque_watermark_domain(
    isolated_correspondence_db, cached, observed, refresh,
):
    store = RedDogCorrespondenceStateStore()
    store.upsert_state(CorrespondenceState(
        scope_key="ORG::TRANSFER", provider_watermark=cached,
        freshness=Freshness.VALID,
    ))
    before = store.select("state")
    events_before = store.select("events")
    assert store.provider_refresh_required("ORG::TRANSFER", observed) is refresh
    assert store.select("state") == before
    assert store.select("events") == events_before == []

# Sender-boundary regressions extend this existing recipient/state test owner.
from copy import deepcopy
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor

from modules.communication.moltbot_bridge.src.reddog_correspondence_sender_boundary import (
    CorrespondenceSenderBoundary, ReconciledContext, digest,
)


@pytest.fixture
def sender(isolated_correspondence_db):
    tx = {
        "account_key": "test-account", "scope_key": "FUKUI_COUNCIL::PPP",
        "purpose": "circulation reply", "operation": "send_email",
        "recipients": [
            {"identity_id": "council", "role": "TO", "address": "council@example.org"},
            {"identity_id": "commission", "role": "CC", "address": "commission@example.org"},
            {"identity_id": "hasegawa", "role": "BCC", "address": "akira@example.org"},
        ],
        "subject": "Three-site PPP", "payload": {"mime_type": "text/plain", "body": {"content": "reply"}},
        "draft_id": None, "draft_message_id": None, "thread_id": None,
        "reply_message_id": None, "from_address": None, "reply_to": None,
    }
    evidence = tuple(ev(r["identity_id"], r["address"]) for r in tx["recipients"])
    state = CorrespondenceState(
        scope_key=tx["scope_key"], active_thread_ids=("thread-1",),
        sent_coverage_state=SentCoverageState.NO_SENT_MATCH_IN_CHECKED_SCOPE,
        follow_up_gate=FollowUpGate.CLEAR, freshness=Freshness.VALID,
        routing_state="ALLOW", next_allowed_action="SEND", provider_watermark="watermark-1",
        reconciled_at="2026-10-02T09:00:00+00:00",
    )
    class Host:
        now = 1790931601.0  # 2026-10-02 09:00:01 UTC; deterministic test clock
        submits = 0
        reads = 0
        fail_submit = False
        fail_read = False
        result = {"id": "sent-1", "thread_id": "thread-1"}
        patch = {}
        draft_patch = {}
        after_draft = None
        after_reconcile = None
        reconcile_calls = 0
        context = ReconciledContext(
            tx, state, evidence,
            {k: "test:" + k for k in ("gmail_sent", "full_thread", "drafts", "email_log",
                                     "action_queue", "correspondence_routing")},
        )
        def reconcile(self, account, scope):
            assert account == "test-account" and scope == tx["scope_key"]
            self.reconcile_calls += 1
            result = self.context
            if self.after_reconcile:
                self.after_reconcile(self)
            return result
        def read_draft(self, account, draft_id):
            result = {"draft_id": "draft-1", "message_id": "draft-mid-1", "thread_id": "thread-1",
                      "subject": self.context.intended_transaction["subject"],
                      "payload": deepcopy(self.context.intended_transaction["payload"]),
                      **self.headers() , **self.draft_patch}
            if self.after_draft:
                self.after_draft(self)
            return result
        def headers(self):
            intended = self.context.intended_transaction
            return {role.lower(): [r["address"] for r in intended["recipients"] if r["role"] == role]
                    for role in ("TO", "CC", "BCC")}
        def submit(self, args):
            self.submits += 1
            for role, addresses in self.headers().items():
                assert sorted(args[role]) == sorted(addresses)
            self.submitted = deepcopy(args)
            if self.fail_submit:
                raise TimeoutError("unknown provider state")
            return self.result
        def read_sent(self, account, mid):
            self.reads += 1
            if self.fail_read:
                raise TimeoutError("readback unavailable")
            return {"id": mid, "thread_id": "thread-1", "label_ids": ["SENT"], **self.headers(), **self.patch}
    host = Host()
    store = RedDogCorrespondenceStateStore()
    boundary = CorrespondenceSenderBoundary(provider=host, reconcile=host.reconcile,
                                            store=store, clock=lambda: host.now)
    return tx, host, store, boundary


@pytest.fixture
def council_reply_shape(sender):
    """October 2 transaction topology only: no live IDs, contacts or content."""
    tx, host, _, _ = sender
    tx.update(operation="reply", thread_id="thread-1", reply_message_id="inbound-1")
    tx["recipients"] = [
        {"identity_id": "office", "role": "TO", "address": "office@example.org"},
        {"identity_id": "association", "role": "CC", "address": "association@example.org"},
        {"identity_id": "supporter-c", "role": "BCC", "address": "supporter-c@example.org"},
    ]
    tx["recipients"].extend([
        {"identity_id": "supporter-a", "role": "BCC", "address": "supporter-a@example.org"},
        {"identity_id": "supporter-b", "role": "BCC", "address": "supporter-b@example.org"},
    ])
    tx["payload"] = {"mime_type": "multipart/mixed", "parts": [
        {"mime_type": "text/plain", "body": {"content": "Synthetic regression content"}},
        {"mime_type": "application/pdf", "filename": "synthetic-three-site.pdf",
         "body": {"content": "Synthetic PDF attachment bytes"}},
    ]}
    host.context = replace(host.context, evidence=tuple(
        ev(r["identity_id"], r["address"]) for r in tx["recipients"]
    ))
    return sender


def test_council_reply_shape_exact_submission_and_consumed_receipt(council_reply_shape):
    tx, host, store, boundary = council_reply_shape
    receipt = boundary.issue(tx)
    assert receipt["decision"] == "SEND", receipt
    result = boundary.execute(tx, receipt)
    assert result["decision"] == "VERIFIED_SENT", result
    assert (result["message_id"], result["thread_id"]) == ("sent-1", "thread-1")
    assert host.submits == 1 and host.reads == 1
    assert [len(host.submitted[r]) for r in ("to", "cc", "bcc")] == [1, 1, 3]
    for field in ("payload", "reply_message_id", "thread_id"):
        assert host.submitted[field] == tx[field]
    assert len(store.select("recipient_submission_state")) == 5
    assert boundary.execute(tx, receipt)["decision"] == "BLOCK"
    assert host.submits == 1


@pytest.mark.parametrize("change", ["remove_bcc", "add_bcc", "bcc_to_cc", "one_character",
                                   "thread", "reply", "purpose", "scope", "attachment", "watermark"])
def test_council_reply_shape_drift_blocks_with_zero_provider_calls(council_reply_shape, change):
    tx, host, _, boundary = council_reply_shape
    receipt = boundary.issue(tx)
    assert receipt["decision"] == "SEND", receipt
    proposed = deepcopy(tx)
    bcc = next(r for r in proposed["recipients"] if r["identity_id"] == "supporter-a")
    if change == "remove_bcc":
        proposed["recipients"].remove(bcc)
    elif change == "add_bcc":
        proposed["recipients"].append(
            {"identity_id": "extra", "role": "BCC", "address": "extra@example.org"})
    elif change == "bcc_to_cc":
        bcc["role"] = "CC"
    elif change == "one_character":
        bcc["address"] = "supporter-x@example.org"
    elif change in {"thread", "reply", "purpose", "scope"}:
        proposed[{"thread": "thread_id", "reply": "reply_message_id",
                  "scope": "scope_key"}.get(change, change)] = "changed"
    elif change == "attachment":
        proposed["payload"]["parts"][1]["body"]["content"] = "Different attachment"
    else:
        host.context = replace(host.context, state=replace(
            host.context.state, provider_watermark="watermark-after-new-sent"))
    _assert_block(council_reply_shape, proposed, receipt)
    assert host.reads == 0


@pytest.mark.parametrize("patch", [{"id": "different-mid"}, {"thread_id": "different-tid"},
    {"bcc": ["supporter-c@example.org", "supporter-a@example.org"]},
    {"cc": ["association@example.org", "supporter-a@example.org"]}])
def test_council_reply_shape_readback_incident_never_allows_repair(council_reply_shape, patch):
    tx, host, store, boundary = council_reply_shape
    receipt = boundary.issue(tx)
    host.patch = patch
    assert boundary.execute(tx, receipt)["decision"] == "PROVIDER_SENT_INTEGRITY_INCIDENT"
    restarted = CorrespondenceSenderBoundary(provider=host, reconcile=host.reconcile,
                                             store=store, clock=lambda: host.now)
    # Changing operation to repair does not release the same-state claim.
    tx["operation"] = "delivery_repair"
    assert restarted.execute(tx, restarted.issue(tx))["decision"] == "BLOCK"
    assert host.submits == 1


def test_council_reply_shape_ambiguity_is_unknown_and_cannot_resend(council_reply_shape):
    tx, host, store, boundary = council_reply_shape
    host.fail_submit = True
    assert boundary.execute(tx, boundary.issue(tx))["decision"] == "PROVIDER_STATE_UNKNOWN"
    restarted = CorrespondenceSenderBoundary(provider=host, reconcile=host.reconcile,
                                             store=store, clock=lambda: host.now)
    host.fail_submit = False
    assert restarted.execute(tx, restarted.issue(tx))["decision"] == "BLOCK"
    assert host.submits == 1 and host.reads == 0


def test_council_reply_shape_already_sent_cannot_be_delivery_repair(council_reply_shape):
    tx, host, _, boundary = council_reply_shape
    tx["operation"] = "delivery_repair"
    host.context = replace(host.context, sent_message_ids=("synthetic-council-already-sent",))
    assert boundary.issue(tx)["decision"] == "BLOCK"
    _assert_block(council_reply_shape, tx, None)


def _assert_block(sender, tx, receipt):
    _, host, _, boundary = sender
    result = boundary.execute(tx, receipt)
    assert result["decision"] in {"BLOCK", "HOLD"}, result
    assert host.submits == 0
    return result


@pytest.mark.parametrize("defect", ["missing", "BLOCK", "expired", "malformed", "digest",
    "to", "cc", "bcc", "missing_recipient", "extra_recipient", "role", "identity", "purpose", "scope",
    "account", "payload", "subject", "reply", "fabricated", "empty_checks"])
def test_sender_presubmission_failures_have_zero_mutations(sender, defect):
    tx, host, _, boundary = sender
    receipt = boundary.issue(tx)
    assert receipt["decision"] == "SEND", receipt
    changed = deepcopy(tx)
    if defect == "missing":
        receipt = None
    elif defect == "malformed":
        receipt = []
    elif defect == "BLOCK":
        receipt["decision"] = "BLOCK"
    elif defect == "expired":
        host.now += 120
    elif defect == "digest":
        receipt["transaction_digest"] = "wrong"
    elif defect in {"to", "cc", "bcc"}:
        next(r for r in changed["recipients"] if r["role"] == defect.upper())["address"] = "wrong@example.org"
    elif defect == "missing_recipient":
        changed["recipients"].pop()
    elif defect == "extra_recipient":
        changed["recipients"].append({"identity_id": "extra", "role": "BCC", "address": "extra@example.org"})
    elif defect == "role":
        changed["recipients"][1]["role"], changed["recipients"][2]["role"] = "BCC", "CC"
    elif defect == "identity":
        changed["recipients"][0]["identity_id"] = "another-contact"
    elif defect in {"purpose", "scope", "account"}:
        changed[{"scope": "scope_key", "account": "account_key"}.get(defect, defect)] = "different"
    elif defect == "payload":
        changed["payload"]["body"]["content"] = "changed"
    elif defect == "subject":
        changed["subject"] = "changed"
    elif defect == "reply":
        changed["reply_message_id"] = "different-inbound"
    elif defect == "fabricated":
        receipt["receipt_id"] = "caller-invented"
    elif defect == "empty_checks":
        receipt["checks"] = []
    _assert_block(sender, changed, receipt)


@pytest.mark.parametrize("gate", list(FollowUpGate)[1:])
@pytest.mark.parametrize("operation", ["send_email", "create_draft", "update_draft"])
def test_sender_capsule_gates_send_and_finalized_drafts(sender, gate, operation):
    tx, host, _, boundary = sender
    tx["operation"] = operation
    if operation == "update_draft":
        tx.update(draft_id="draft-1", draft_message_id="draft-mid-1", thread_id="thread-1")
    receipt = boundary.issue(tx)
    host.context = replace(host.context, state=replace(host.context.state, follow_up_gate=gate))
    _assert_block(sender, tx, receipt)
    assert boundary.issue(tx)["decision"] == "BLOCK"


@pytest.mark.parametrize("defect", ["watermark", "conflict", "missing_source", "unknown", "third",
    "duplicate", "closed", "near_match", "unverified", "route_change", "thread"])
def test_sender_state_or_route_change_invalidates_receipt(sender, defect):
    tx, host, _, boundary = sender
    receipt = boundary.issue(tx)
    ctx = host.context
    if defect == "watermark":
        ctx = replace(ctx, state=replace(ctx.state, provider_watermark="new"))
    elif defect == "conflict":
        ctx = replace(ctx, conflicts=("queue/provider disagreement",))
    elif defect == "missing_source":
        ctx = replace(ctx, source_refs={})
    elif defect == "unknown":
        ctx = replace(ctx, state=replace(ctx.state, freshness=Freshness.UNKNOWN))
    elif defect == "third":
        ctx = replace(ctx, state=replace(ctx.state, outbound_since_latest_inbound=2))
    elif defect == "duplicate":
        ctx = replace(ctx, sent_message_ids=("historical-integrity-incident",))
    elif defect == "closed":
        ctx = replace(ctx, evidence=(replace(ctx.evidence[0], policy=RoutePolicy.PERSONAL_ROUTE_CLOSED), *ctx.evidence[1:]))
    elif defect == "near_match":
        ctx = replace(ctx, evidence=(replace(ctx.evidence[0], address="counci1@example.org"), *ctx.evidence[1:]))
    elif defect == "unverified":
        ctx = replace(ctx, evidence=(replace(ctx.evidence[0], verified=False), *ctx.evidence[1:]))
    elif defect == "route_change":
        ctx = replace(ctx, source_refs={**ctx.source_refs, "correspondence_routing": "new-route-generation"})
    else:
        ctx = replace(ctx, state=replace(ctx.state, active_thread_ids=("new-thread",)))
    host.context = ctx
    _assert_block(sender, tx, receipt)


@pytest.mark.parametrize("operation", ["send_email", "reply", "send_draft", "delivery_repair",
                                       "create_draft", "update_draft"])
def test_sender_all_operations_require_receipt_and_submit_once(sender, operation):
    tx, host, store, boundary = sender
    tx["operation"] = operation
    if operation in {"send_draft", "update_draft"}:
        tx.update(draft_id="draft-1", draft_message_id="draft-mid-1", thread_id="thread-1")
    if operation == "reply":
        tx.update(reply_message_id="inbound-1", thread_id="thread-1")
    _assert_block(sender, tx, None)
    receipt = boundary.issue(tx)
    assert receipt["decision"] == "SEND", receipt
    result = boundary.execute(tx, receipt)
    assert result["decision"] == ("DRAFT_SAVED" if "draft" in operation and operation != "send_draft" else "VERIFIED_SENT"), result
    assert host.submits == 1
    result = boundary.execute(tx, receipt)
    assert result["decision"] in {"BLOCK", "HOLD"}
    assert host.submits == 1
    statuses = store.select("recipient_submission_state")
    assert len(statuses) == 3
    assert {r["identity_id"] for r in statuses} == {"council", "commission", "hasegawa"}
    assert all("address" not in r for r in statuses)


@pytest.mark.parametrize("patch", [{"to": []}, {"cc": []}, {"bcc": []}, {"bcc": ["extra@example.org"]},
    {"to": ["commission@example.org"], "cc": ["council@example.org"]}, {"id": "wrong"},
    {"thread_id": "wrong"}, {"label_ids": []}, {"bcc": None}])
def test_sender_readback_mismatch_never_verifies_and_never_retries(sender, patch):
    tx, host, store, boundary = sender
    receipt = boundary.issue(tx)
    host.patch = patch
    result = boundary.execute(tx, receipt)
    assert result["decision"] == "PROVIDER_SENT_INTEGRITY_INCIDENT", result
    assert host.submits == 1
    # Restart service, make a new fresh receipt, and attempt 'repair' again.
    restarted = CorrespondenceSenderBoundary(provider=host, reconcile=host.reconcile, store=store, clock=lambda: host.now)
    second = restarted.issue(tx)
    assert restarted.execute(tx, second)["decision"] == "BLOCK"
    assert host.submits == 1


@pytest.mark.parametrize("failure", ["submit", "readback", "missing_mid", "missing_thread"])
def test_sender_provider_ambiguity_is_durable_no_retry(sender, failure):
    tx, host, _, boundary = sender
    receipt = boundary.issue(tx)
    if failure == "submit":
        host.fail_submit = True
    elif failure == "readback":
        host.fail_read = True
    elif failure == "missing_mid":
        host.result = {"thread_id": "thread-1"}
    else:
        host.result = {"id": "sent-1"}
    result = boundary.execute(tx, receipt)
    assert result["decision"] in {"PROVIDER_STATE_UNKNOWN", "PROVIDER_SENT_INTEGRITY_INCIDENT"}
    assert boundary.execute(tx, boundary.issue(tx))["decision"] == "BLOCK"
    assert host.submits == 1


@pytest.mark.parametrize("change", ["expiry", "sent", "bcc", "subject", "thread"])
def test_sender_draft_drift_and_slow_read_expiry_fail_before_submission(sender, change):
    tx, host, _, boundary = sender
    tx.update(operation="send_draft", draft_id="draft-1", draft_message_id="draft-mid-1", thread_id="thread-1")
    receipt = boundary.issue(tx)
    if change == "expiry":
        host.after_draft = lambda h: setattr(h, "now", h.now + 120)
    elif change == "sent":
        host.after_draft = lambda h: setattr(h, "context", replace(h.context, sent_message_ids=("new-send",)))
    elif change == "bcc":
        host.draft_patch = {"bcc": ["another@example.org"]}
    elif change == "subject":
        host.draft_patch = {"subject": "changed subject"}
    else:
        host.draft_patch = {"thread_id": "another-thread"}
    _assert_block(sender, tx, receipt)


def test_sender_concurrent_replay_claim_is_atomic(sender):
    tx, host, _, boundary = sender
    receipt = boundary.issue(tx)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: boundary.execute(tx, receipt), range(2)))
    assert sorted(r["decision"] for r in results) == ["BLOCK", "VERIFIED_SENT"]
    assert host.submits == 1


def test_sender_dry_run_cannot_authorize_provider(sender):
    tx, host, _, boundary = sender
    audit = boundary.issue(tx, dry_run=True)
    assert audit["decision"] == "AUDIT_ONLY"
    _assert_block(sender, tx, audit["receipt"])


def test_sender_historical_integrity_incident_blocks_delivery_repair(sender):
    tx, host, _, boundary = sender
    tx["operation"] = "delivery_repair"
    host.context = replace(host.context, sent_message_ids=("historical-provider-sent",))
    assert boundary.issue(tx)["decision"] == "BLOCK"
    _assert_block(sender, tx, {"decision": "SEND"})


def test_sender_scheduled_or_helper_caller_has_no_alternate_boundary(sender):
    tx, host, _, boundary = sender
    def scheduled_job(receipt):
        return boundary.execute(tx, receipt)
    def delivery_helper(receipt):
        return scheduled_job(receipt)
    assert delivery_helper(None)["decision"] == "BLOCK"
    assert host.submits == 0
    assert delivery_helper(boundary.issue(tx))["decision"] == "VERIFIED_SENT"
    assert host.submits == 1


def test_sender_same_provider_state_cannot_authorize_parallel_different_transaction(sender):
    tx, host, _, boundary = sender
    first = boundary.issue(tx)
    assert boundary.execute(tx, first)["decision"] == "VERIFIED_SENT"
    tx["subject"] = "different subject after send"
    second = boundary.issue(tx)
    assert boundary.execute(tx, second)["decision"] == "BLOCK"
    assert host.submits == 1

@pytest.mark.parametrize("defect", ["schema", "negative_count", "duplicate_asks", "dangling_delta", "policy"])
def test_sender_malformed_capsule_or_policy_fails_closed(sender, defect):
    tx, host, _, boundary = sender
    receipt = boundary.issue(tx)
    ctx = host.context
    if defect == "schema":
        ctx = replace(ctx, state=replace(ctx.state, schema_version="unknown"))
    elif defect == "negative_count":
        ctx = replace(ctx, state=replace(ctx.state, outbound_since_latest_inbound=-1))
    elif defect == "duplicate_asks":
        ctx = replace(ctx, state=replace(ctx.state, asks=(AskRecord("x", AskStatus.OPEN),)*2))
    elif defect == "dangling_delta":
        ctx = replace(ctx, state=replace(ctx.state, new_delta_ask_ids=("not-declared",)))
    else:
        ctx = replace(ctx, evidence=(replace(ctx.evidence[0], policy="UNKNOWN"), *ctx.evidence[1:]))
    host.context = ctx
    _assert_block(sender, tx, receipt)


def test_sender_capsule_invalidation_during_second_read_blocks(sender):
    tx, host, _, boundary = sender
    receipt = boundary.issue(tx)
    host.after_reconcile = lambda h: setattr(h, "context", replace(h.context, conflicts=("changed queue",)))
    _assert_block(sender, tx, receipt)


def test_sender_missing_intended_recipient_cannot_be_authorized_by_composer(sender):
    tx, host, _, boundary = sender
    proposed = deepcopy(tx)
    proposed["recipients"].pop()
    assert boundary.issue(proposed)["decision"] == "BLOCK"
    assert host.submits == 0


def test_sender_new_receipt_after_actual_bcc_policy_change_blocks(sender):
    tx, host, _, boundary = sender
    host.context = replace(host.context, evidence=tuple(
        replace(e, policy=RoutePolicy.DO_NOT_ADDRESS_OR_CC) if e.identity_id == "hasegawa" else e
        for e in host.context.evidence
    ))
    assert boundary.issue(tx)["decision"] == "BLOCK"
    assert host.submits == 0


def test_sender_finalized_draft_third_followup_fresh_session(sender):
    tx, host, store, _ = sender
    tx["operation"] = "create_draft"
    host.context = replace(host.context, state=replace(
        host.context.state, outbound_since_latest_inbound=2,
        follow_up_gate=FollowUpGate.BLOCK_THIRD_FOLLOWUP,
        next_allowed_action="HOLD / AWAIT INBOUND",
    ))
    fresh = CorrespondenceSenderBoundary(provider=host, reconcile=host.reconcile, store=store, clock=lambda: host.now)
    assert fresh.issue(tx)["decision"] == "BLOCK"
    assert fresh.execute(tx, None)["decision"] == "HOLD"
    assert host.submits == 0


def test_sender_fresh_read_timestamp_does_not_invalidate_or_release_state_claim(sender):
    tx, host, _, boundary = sender
    receipt = boundary.issue(tx)
    host.now += 10
    host.context = replace(host.context, state=replace(host.context.state, reconciled_at="2026-10-02T09:00:10+00:00"))
    assert boundary.execute(tx, receipt)["decision"] == "VERIFIED_SENT"
    host.now += 10
    host.context = replace(host.context, state=replace(host.context.state, reconciled_at="2026-10-02T09:00:20+00:00"))
    tx["subject"] = "changed after timestamp-only reconciliation"
    assert boundary.execute(tx, boundary.issue(tx))["decision"] == "BLOCK"
    assert host.submits == 1


def test_sender_receipt_expiring_during_durable_claim_never_submits(sender, monkeypatch):
    tx, host, store, boundary = sender
    receipt = boundary.issue(tx)
    claim = store.claim_submission
    def slow_claim(*args):
        claim(*args)
        host.now += 120
    monkeypatch.setattr(store, "claim_submission", slow_claim)
    _assert_block(sender, tx, receipt)
    assert len(store.select("send_claims")) == 1
