"""
Unit tests for SHORTS_PRIORITY_WIRING_PHASE1.

Slice: SHORTS_PRIORITY_WIRING_PHASE1

What is wired
-------------
1. REGISTER: `what_should_i_schedule` SKILLz.md carries `domain: youtube` so the
   existing WRE SkillTriggerMixin (domain-discovery, skill_trigger.py:91-115;
   auto_moderator_dae.py:221 domain="youtube") auto-fires it every cadence cycle.
2. STEER: `_prioritize_channels` in scripts/launch.py reorders the rotation
   highest scheduling-need first and DROPS channels at the hard cap (deficit==0),
   gated on YT_SCHEDULE_PRIORITY_ENABLED (default-off), fallback-safe.

These tests are MOCK-ONLY (no browser, no daemon, no live model, no real
registry/tracker) and NON-VACUOUS:
  - flag on  -> channels reordered by need AND deficit==0 channels skipped
  - flag off -> original order, no skip
  - rank error -> fallback to original order (no exception escapes)
  - the reorder MUST respond to the ranking (a ranking-ignoring impl fails):
    swapping which channel has the highest deficit swaps the chosen head.
  - SKILLz.md has `domain: youtube` and still parses with Skills 2.0 fields.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import modules.platform_integration.youtube_shorts_scheduler.scripts.launch as launch


# --- Fixtures: a deterministic registry + ranking, no real I/O ---------------

# channel_id -> key, mirroring the shorts registry shape used by launch.
_REGISTRY = [
    {"id": "UC_M2J", "key": "move2japan", "name": "Move2Japan"},
    {"id": "UC_UDU", "key": "undaodu", "name": "UnDaoDu"},
    {"id": "UC_FUP", "key": "foundups", "name": "FoundUps"},
    {"id": "UC_AFM", "key": "antifafm", "name": "antifaFM"},
]


def _registry_channels(role=None):
    """Stand-in for youtube_channel_registry.get_channels(role='shorts')."""
    return list(_REGISTRY)


def _ranking(*ordered_pairs):
    """Build a rank_channels_by_need-shaped list: (channel_id, total_deficit)."""
    return [
        {
            "channel_id": cid,
            "name": cid,
            "total_deficit": deficit,
            "days_empty": 0,
            "recommend": "schedule" if deficit > 0 else "sufficient",
        }
        for cid, deficit in ordered_pairs
    ]


# === STEER tests =============================================================


def test_flag_off_returns_original_order(monkeypatch):
    """Default-off: with the flag unset the rotation is untouched (no skip)."""
    monkeypatch.delenv("YT_SCHEDULE_PRIORITY_ENABLED", raising=False)
    original = ["move2japan", "undaodu", "foundups", "antifafm"]
    # If anything tried to rank here it would blow up -> patch nothing on purpose.
    assert launch._prioritize_channels(original) == original


def test_flag_off_explicit_zero(monkeypatch):
    """Explicit '0' is also off."""
    monkeypatch.setenv("YT_SCHEDULE_PRIORITY_ENABLED", "0")
    original = ["foundups", "antifafm"]
    assert launch._prioritize_channels(original) == original


def test_flag_on_reorders_by_need_and_skips_deficit_zero(monkeypatch):
    """Flag on: reorder by need; channels at the cap (deficit==0) are dropped."""
    monkeypatch.setenv("YT_SCHEDULE_PRIORITY_ENABLED", "1")
    original = ["move2japan", "undaodu", "foundups", "antifafm"]

    # Need order (desc): foundups(21) > move2japan(7) > undaodu(3); antifafm==0 -> skip.
    ranking = _ranking(("UC_FUP", 21), ("UC_M2J", 7), ("UC_UDU", 3), ("UC_AFM", 0))

    with patch.object(launch, "_emit_priority_breadcrumb") as mock_bc, \
         patch(
             "modules.infrastructure.shared_utilities.youtube_channel_registry.get_channels",
             side_effect=_registry_channels,
         ), \
         patch(
             "modules.platform_integration.youtube_shorts_scheduler.skillz."
             "what_should_i_schedule.executor.rank_channels_by_need",
             return_value=ranking,
         ):
        result = launch._prioritize_channels(original)

    # Highest-need first, antifafm (deficit==0) skipped entirely.
    assert result == ["foundups", "move2japan", "undaodu"]
    assert "antifafm" not in result
    # Breadcrumb emitted with the chosen order + the skipped channel.
    mock_bc.assert_called_once()
    args = mock_bc.call_args.args
    assert args[1] == ["foundups", "move2japan", "undaodu"]  # chosen
    assert args[2] == ["antifafm"]  # skipped (deficit==0)


def test_reorder_responds_to_ranking_NONVACUOUS(monkeypatch):
    """NON-VACUITY: swapping which channel has the top deficit swaps the head.

    A ranking-ignoring implementation (e.g. returning the original order) would
    fail BOTH assertions below, because the only thing that changes between the
    two calls is the injected deficit ordering.
    """
    monkeypatch.setenv("YT_SCHEDULE_PRIORITY_ENABLED", "1")
    original = ["move2japan", "undaodu", "foundups", "antifafm"]

    rank_a = _ranking(("UC_FUP", 21), ("UC_M2J", 7), ("UC_UDU", 3), ("UC_AFM", 1))
    rank_b = _ranking(("UC_M2J", 21), ("UC_FUP", 7), ("UC_UDU", 3), ("UC_AFM", 1))

    with patch.object(launch, "_emit_priority_breadcrumb"), \
         patch(
             "modules.infrastructure.shared_utilities.youtube_channel_registry.get_channels",
             side_effect=_registry_channels,
         ):
        with patch(
            "modules.platform_integration.youtube_shorts_scheduler.skillz."
            "what_should_i_schedule.executor.rank_channels_by_need",
            return_value=rank_a,
        ):
            result_a = launch._prioritize_channels(original)
        with patch(
            "modules.platform_integration.youtube_shorts_scheduler.skillz."
            "what_should_i_schedule.executor.rank_channels_by_need",
            return_value=rank_b,
        ):
            result_b = launch._prioritize_channels(original)

    # Head must follow the injected top-deficit channel, not the original order.
    assert result_a[0] == "foundups"
    assert result_b[0] == "move2japan"
    assert result_a != result_b
    # And neither equals the original order (proving the ranking actually steered).
    assert result_a != original
    assert result_b != original


def test_rank_error_falls_back_to_original_order(monkeypatch):
    """Fallback-safe: if ranking raises, return the original order, no exception."""
    monkeypatch.setenv("YT_SCHEDULE_PRIORITY_ENABLED", "1")
    original = ["move2japan", "undaodu", "foundups", "antifafm"]

    with patch(
        "modules.infrastructure.shared_utilities.youtube_channel_registry.get_channels",
        side_effect=_registry_channels,
    ), patch(
        "modules.platform_integration.youtube_shorts_scheduler.skillz."
        "what_should_i_schedule.executor.rank_channels_by_need",
        side_effect=RuntimeError("tracker JSON corrupt"),
    ):
        result = launch._prioritize_channels(original)

    assert result == original  # untouched, scheduler never breaks


def test_all_at_cap_falls_back_to_original(monkeypatch):
    """If every channel is deficit==0, don't hand the scheduler an empty list."""
    monkeypatch.setenv("YT_SCHEDULE_PRIORITY_ENABLED", "1")
    original = ["foundups", "antifafm"]
    ranking = _ranking(("UC_FUP", 0), ("UC_AFM", 0))

    with patch.object(launch, "_emit_priority_breadcrumb"), \
         patch(
             "modules.infrastructure.shared_utilities.youtube_channel_registry.get_channels",
             side_effect=_registry_channels,
         ), \
         patch(
             "modules.platform_integration.youtube_shorts_scheduler.skillz."
             "what_should_i_schedule.executor.rank_channels_by_need",
             return_value=ranking,
         ):
        result = launch._prioritize_channels(original)

    assert result == original


def test_uncovered_rotation_key_is_kept(monkeypatch):
    """A rotation key the ranking didn't cover is kept (no silent work loss)."""
    monkeypatch.setenv("YT_SCHEDULE_PRIORITY_ENABLED", "1")
    original = ["foundups", "antifafm"]
    # Ranking only mentions foundups; antifafm is uncovered -> appended after.
    ranking = _ranking(("UC_FUP", 9))

    with patch.object(launch, "_emit_priority_breadcrumb"), \
         patch(
             "modules.infrastructure.shared_utilities.youtube_channel_registry.get_channels",
             side_effect=_registry_channels,
         ), \
         patch(
             "modules.platform_integration.youtube_shorts_scheduler.skillz."
             "what_should_i_schedule.executor.rank_channels_by_need",
             return_value=ranking,
         ):
        result = launch._prioritize_channels(original)

    assert result == ["foundups", "antifafm"]


# === REGISTER test (orphaning fix) ==========================================


def test_skillz_has_domain_youtube_and_skills2_intact():
    """SKILLz.md must carry `domain: youtube` (WRE auto-fire) and keep Skills 2.0."""
    skillz_path = (
        Path(__file__).resolve().parent.parent
        / "skillz"
        / "what_should_i_schedule"
        / "SKILLz.md"
    )
    content = skillz_path.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    end = content.find("\n---\n", 4)
    assert end != -1, "frontmatter must terminate"
    fm = yaml.safe_load(content[4:end])

    # The orphaning fix: domain tag matched by SkillTriggerMixin (domain="youtube").
    assert fm.get("domain") == "youtube"
    # Skills 2.0 fields still present and parseable.
    assert "category" in fm
    assert "evals" in fm
    assert "retirement_date" in fm
    assert fm.get("name") == "what_should_i_schedule"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
