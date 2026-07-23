#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the natural-language schedule evaluator.

Tests cover:
- Phrase parsing (supported and unsupported patterns)
- Schedule persistence
- Due schedule evaluation
- Duplicate prevention
"""

import json
import pytest
from datetime import datetime, timedelta, UTC
from pathlib import Path

from modules.infrastructure.idle_automation.src.schedule_evaluator import (
    ScheduleParser,
    ScheduleEvaluator,
    ScheduleSpec,
    SUPPORTED_ROUTINES,
    CADENCE_WINDOWS,
    get_supported_phrases,
)
from modules.infrastructure.idle_automation.src.schedule_claim_state import (
    LEASE_SECONDS,
)


class TestScheduleParser:
    """Test the deterministic phrase parser."""

    @pytest.mark.parametrize(
        "phrase,expected_routine,expected_cadence",
        [
            ("run self research daily", "self_research", "daily"),
            ("run self-research daily", "self_research", "daily"),
            ("run research nightly", "self_research", "nightly"),
            ("run nightly self research", "self_research", "nightly"),
            ("self research every morning", "self_research", "morning"),
            ("run queue audit daily", "queue_audit", "daily"),
            ("run queue refresh nightly", "queue_audit", "nightly"),
            ("queue daily", "queue_audit", "daily"),
            ("run grant watchlist daily", "grant_watchlist", "daily"),
            ("run grants every evening", "grant_watchlist", "evening"),
            ("run watchlist morning", "grant_watchlist", "morning"),
            ("RUN SELF RESEARCH DAILY", "self_research", "daily"),  # Case insensitive
        ],
    )
    def test_parse_valid_phrases(self, phrase, expected_routine, expected_cadence):
        """Valid phrases parse to expected routine and cadence."""
        result = ScheduleParser.parse(phrase)
        assert result is not None
        routine, cadence = result
        assert routine == expected_routine
        assert cadence == expected_cadence

    @pytest.mark.parametrize(
        "phrase",
        [
            "hello world",
            "run something daily",
            "run self research",  # Missing cadence
            "daily",  # Missing routine
            "run self research hourly",  # Invalid cadence
            "run database migration daily",  # Invalid routine
        ],
    )
    def test_parse_invalid_phrases_returns_none(self, phrase):
        """Invalid phrases return None."""
        result = ScheduleParser.parse(phrase)
        assert result is None

    def test_generate_id_is_stable(self):
        """Same phrase always generates same ID."""
        phrase = "run self research daily"
        id1 = ScheduleParser.generate_id(phrase)
        id2 = ScheduleParser.generate_id(phrase)
        assert id1 == id2
        assert len(id1) == 12

    def test_generate_id_is_case_insensitive(self):
        """ID generation is case-insensitive."""
        id1 = ScheduleParser.generate_id("Run Self Research Daily")
        id2 = ScheduleParser.generate_id("run self research daily")
        assert id1 == id2

    def test_generate_id_semantic_dedup(self):
        """Different phrasings of same logical schedule produce same ID."""
        # All these represent the same logical schedule: self_research + daily
        id1 = ScheduleParser.generate_id("run self research daily")
        id2 = ScheduleParser.generate_id("self research daily")
        id3 = ScheduleParser.generate_id("run research daily")
        id4 = ScheduleParser.generate_id("self-research daily")
        assert id1 == id2 == id3 == id4

    def test_generate_id_different_for_different_routines(self):
        """Different routines produce different IDs."""
        id1 = ScheduleParser.generate_id("run self research daily")
        id2 = ScheduleParser.generate_id("run queue audit daily")
        assert id1 != id2

    def test_generate_id_different_for_different_cadences(self):
        """Different cadences produce different IDs."""
        id1 = ScheduleParser.generate_id("run self research daily")
        id2 = ScheduleParser.generate_id("run self research nightly")
        assert id1 != id2


class TestScheduleEvaluator:
    """Test the schedule evaluator."""

    @pytest.fixture
    def temp_schedules_path(self, tmp_path):
        """Create a temporary schedules.json path."""
        return tmp_path / "schedules.json"

    @pytest.fixture
    def evaluator(self, temp_schedules_path):
        """Create an evaluator with temporary storage."""
        return ScheduleEvaluator(schedules_path=temp_schedules_path)

    def test_add_schedule_creates_spec(self, evaluator):
        """Adding a schedule creates a ScheduleSpec."""
        spec = evaluator.add_schedule("run self research daily")
        assert spec is not None
        assert spec.routine == "self_research"
        assert spec.cadence == "daily"
        assert spec.enabled is True

    def test_add_duplicate_schedule_returns_existing(self, evaluator):
        """Adding duplicate phrase returns existing spec."""
        spec1 = evaluator.add_schedule("run self research daily")
        spec2 = evaluator.add_schedule("run self research daily")
        assert spec1.id == spec2.id

    def test_add_invalid_phrase_returns_none(self, evaluator):
        """Adding invalid phrase returns None."""
        spec = evaluator.add_schedule("run something invalid")
        assert spec is None

    def test_schedules_persist_across_instances(self, temp_schedules_path):
        """Schedules persist to disk and reload."""
        evaluator1 = ScheduleEvaluator(schedules_path=temp_schedules_path)
        spec1 = evaluator1.add_schedule("run self research daily")

        evaluator2 = ScheduleEvaluator(schedules_path=temp_schedules_path)
        schedules = evaluator2.list_schedules()
        assert len(schedules) == 1
        assert schedules[0].id == spec1.id

    def test_remove_schedule(self, evaluator):
        """Removing a schedule works correctly."""
        spec = evaluator.add_schedule("run self research daily")
        assert evaluator.remove_schedule(spec.id) is True
        assert evaluator.list_schedules() == []

    def test_remove_nonexistent_schedule_returns_false(self, evaluator):
        """Removing nonexistent schedule returns False."""
        assert evaluator.remove_schedule("nonexistent") is False

    def test_set_enabled(self, evaluator):
        """Enabling/disabling schedules works."""
        spec = evaluator.add_schedule("run self research daily")
        evaluator.set_enabled(spec.id, False)
        updated = evaluator.get_schedule(spec.id)
        assert updated.enabled is False

    def test_record_execution_updates_last_run(self, evaluator):
        """Recording execution updates last_run."""
        spec = evaluator.add_schedule("run self research daily")
        assert spec.last_run is None

        evaluator.record_execution(spec.id, True, "completed")
        updated = evaluator.get_schedule(spec.id)
        assert updated.last_run is not None
        assert "success" in updated.last_result


class TestDueScheduleEvaluation:
    """Test due schedule evaluation logic."""

    @pytest.fixture
    def temp_schedules_path(self, tmp_path):
        """Create a temporary schedules.json path."""
        return tmp_path / "schedules.json"

    def test_schedule_never_run_is_due_in_window(self, temp_schedules_path):
        """A schedule that never ran is due if in cadence window."""
        evaluator = ScheduleEvaluator(schedules_path=temp_schedules_path)
        evaluator.add_schedule("run self research daily")

        # Check at noon - daily window is 0-24
        now = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)
        due = evaluator.get_due_schedules(now)
        assert len(due) == 1

    def test_schedule_already_ran_today_not_due(self, temp_schedules_path):
        """A schedule that ran today is not due again."""
        evaluator = ScheduleEvaluator(schedules_path=temp_schedules_path)
        spec = evaluator.add_schedule("run self research daily")

        # Record execution at 8am
        now = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)
        ran_at = now.replace(hour=8)
        evaluator._schedules[spec.id].last_run = ran_at.isoformat()
        evaluator._save_schedules()

        # Check at noon - should not be due
        due = evaluator.get_due_schedules(now)
        assert len(due) == 0

    def test_nightly_schedule_outside_window_not_due(self, temp_schedules_path):
        """A nightly schedule outside 0-6 window is not due."""
        evaluator = ScheduleEvaluator(schedules_path=temp_schedules_path)
        evaluator.add_schedule("run self research nightly")

        # Check at noon - nightly window is 0-6
        now = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)
        due = evaluator.get_due_schedules(now)
        assert len(due) == 0

    def test_nightly_schedule_in_window_is_due(self, temp_schedules_path):
        """A nightly schedule at 3am is due."""
        evaluator = ScheduleEvaluator(schedules_path=temp_schedules_path)
        evaluator.add_schedule("run self research nightly")

        # Check at 3am - nightly window is 0-6
        now = datetime.now(UTC).replace(hour=3, minute=0, second=0, microsecond=0)
        due = evaluator.get_due_schedules(now)
        assert len(due) == 1

    def test_disabled_schedule_not_due(self, temp_schedules_path):
        """A disabled schedule is never due."""
        evaluator = ScheduleEvaluator(schedules_path=temp_schedules_path)
        spec = evaluator.add_schedule("run self research daily")
        evaluator.set_enabled(spec.id, False)

        now = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)
        due = evaluator.get_due_schedules(now)
        assert len(due) == 0

    def test_morning_schedule_window(self, temp_schedules_path):
        """Morning schedule is due between 6-12."""
        evaluator = ScheduleEvaluator(schedules_path=temp_schedules_path)
        evaluator.add_schedule("run self research morning")

        # At 9am - should be due
        now_9am = datetime.now(UTC).replace(hour=9, minute=0, second=0, microsecond=0)
        due = evaluator.get_due_schedules(now_9am)
        assert len(due) == 1

        # At 2pm - should not be due
        now_2pm = datetime.now(UTC).replace(hour=14, minute=0, second=0, microsecond=0)
        due = evaluator.get_due_schedules(now_2pm)
        assert len(due) == 0


class TestGetSupportedPhrases:
    """Test the helper for getting supported phrases."""

    def test_returns_examples(self):
        """Returns example phrases."""
        examples = get_supported_phrases()
        assert len(examples) > 0
        assert all(isinstance(e, str) for e in examples)

    def test_all_examples_are_parseable(self):
        """All returned examples are parseable."""
        examples = get_supported_phrases()
        for phrase in examples:
            result = ScheduleParser.parse(phrase)
            assert result is not None, f"Example phrase not parseable: {phrase}"


class TestScheduleSpec:
    """Test ScheduleSpec dataclass."""

    def test_to_dict_roundtrip(self):
        """ScheduleSpec can roundtrip through dict."""
        spec = ScheduleSpec(
            id="abc123",
            phrase="run self research daily",
            routine="self_research",
            cadence="daily",
            enabled=True,
            last_run="2026-03-23T10:00:00+00:00",
            last_result="success: completed",
            created_on="2026-03-20T08:00:00+00:00",
        )
        data = spec.to_dict()
        restored = ScheduleSpec.from_dict(data)
        assert restored.id == spec.id
        assert restored.phrase == spec.phrase
        assert restored.routine == spec.routine
        assert restored.last_run == spec.last_run


class TestDurableScheduleClaims:
    """Test evaluator-to-claim-store integration boundaries."""

    def test_two_due_windows_are_claimed_one_at_a_time(self, tmp_path):
        evaluator = ScheduleEvaluator(schedules_path=tmp_path / "schedules.json")
        first = evaluator.add_schedule("run self research daily")
        second = evaluator.add_schedule("run queue audit daily")
        now = datetime(2026, 7, 24, 1, tzinfo=UTC)

        first_claim = evaluator.claim_schedule(first, now=now)
        assert first_claim is not None
        state = json.loads(
            evaluator.claim_store.state_path.read_text(encoding="utf-8")
        )
        assert list(state["executions"]) == [first_claim.execution_id]

        second_claim = evaluator.claim_schedule(second, now=now)
        assert second_claim is not None
        assert second_claim.execution_id != first_claim.execution_id

    def test_next_cadence_window_has_new_execution_id(self, tmp_path):
        evaluator = ScheduleEvaluator(schedules_path=tmp_path / "schedules.json")
        spec = evaluator.add_schedule("run self research daily")
        first_now = datetime(2026, 7, 24, 1, tzinfo=UTC)
        first = evaluator.claim_schedule(spec, now=first_now)
        assert first is not None
        assert evaluator.finalize_claim(
            first.token,
            success=True,
            outcome_code="success",
            now=first_now,
        )

        second = evaluator.claim_schedule(
            spec, now=first_now + timedelta(days=1)
        )
        assert second is not None
        assert second.execution_id != first.execution_id

    def test_disabled_or_unknown_schedule_is_never_claimed(self, tmp_path):
        evaluator = ScheduleEvaluator(schedules_path=tmp_path / "schedules.json")
        spec = evaluator.add_schedule("run self research daily")
        now = datetime(2026, 7, 24, 1, tzinfo=UTC)
        evaluator.set_enabled(spec.id, False)
        assert evaluator.claim_schedule(spec, now=now) is None
        unknown = ScheduleSpec(
            id="unknown",
            phrase="unknown",
            routine="not_supported",
            cadence="daily",
        )
        assert evaluator.claim_schedule(unknown, now=now) is None
        assert not evaluator.claim_store.state_path.exists()

    def test_before_cadence_window_is_never_claimed(self, tmp_path):
        evaluator = ScheduleEvaluator(schedules_path=tmp_path / "schedules.json")
        spec = evaluator.add_schedule("run self research morning")
        before = datetime(2026, 7, 24, 5, 59, tzinfo=UTC)
        assert evaluator.claim_schedule(spec, now=before) is None
        assert not evaluator.claim_store.state_path.exists()

    def test_claim_lease_exceeds_maximum_dispatch_timeout(self):
        assert LEASE_SECONDS >= 3660

    def test_payload_like_phrase_cannot_select_claim_path(self, tmp_path):
        untrusted = tmp_path / "payload-owned"
        evaluator = ScheduleEvaluator(schedules_path=tmp_path / "schedules.json")
        phrase = f"run self research daily runtime_root={untrusted}"
        spec = evaluator.add_schedule(phrase)
        claim = evaluator.claim_schedule(
            spec, now=datetime(2026, 7, 24, 1, tzinfo=UTC)
        )
        assert claim is not None
        assert evaluator.claim_store.runtime_root != untrusted
        assert not untrusted.exists()
