import json

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
from modules.infrastructure.database.src.db_manager import DatabaseManager


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDUPS_DB_ENGINE", "sqlite")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "correspondence.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    DatabaseManager.reset_for_tests()
    try:
        yield
    finally:
        DatabaseManager.reset_for_tests()


def test_scope_key_is_deterministic_and_machine_safe():
    assert build_scope_key("Fukui City", "Sukatto", "financial disclosure") == (
        "FUKUI_CITY::SUKATTO::FINANCIAL_DISCLOSURE"
    )


def test_event_insert_is_idempotent_and_metadata_only(isolated_db):
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


def test_state_roundtrip_preserves_ask_accounting_and_digest(isolated_db):
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
            AskRecord("ASK-FIN-001", AskStatus.FORMAL_ROUTE_REQUIRED, "OPERATING_ACTUALS"),
            AskRecord("ASK-FIN-002", AskStatus.FORMAL_ROUTE_REQUIRED, "UTILITY_COSTS"),
            AskRecord("ASK-ROUTE-001", AskStatus.ANSWERED, "USE_FORMAL_DISCLOSURE"),
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


def test_provider_watermark_is_change_detector_not_ordering_claim(isolated_db):
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


def test_invalid_delta_reference_fails_closed(isolated_db):
    store = RedDogCorrespondenceStateStore()
    state = CorrespondenceState(
        scope_key="ORG::TOPIC",
        asks=(AskRecord("ASK-1", AskStatus.OPEN),),
        new_delta_ask_ids=("ASK-2",),
    )
    with pytest.raises(ValueError, match="new_delta_ask_ids"):
        store.upsert_state(state)


def test_serialized_state_contains_codes_not_raw_message_content():
    state = CorrespondenceState(
        scope_key="ORG::TOPIC",
        asks=(AskRecord("ASK-1", AskStatus.WAITING_PROVIDER, "PROCUREMENT_STAGE"),),
        next_allowed_action="WAIT_PROVIDER",
        provider_watermark="provider:opaque",
        freshness=Freshness.VALID,
    )
    payload = state_payload(state)
    encoded = json.dumps(payload, sort_keys=True)

    assert "raw_body" not in encoded
    assert "recipient_addresses" not in encoded
    assert "PROCUREMENT_STAGE" in encoded
