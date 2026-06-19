"""
Auto-fire registration tests for the shorts scheduling SKILLz.

Slice: SHORTS_SKILLZ_AUTONOMOUS_REGISTRATION_PHASE1

What these pin (mock-only, no daemon, no browser, no live models)
----------------------------------------------------------------
The WRE skill-trigger discovers + fires skills whose SKILLz.md frontmatter carries
`domain: youtube` (SkillTriggerMixin domain-discovery, skill_trigger.py:91-115; the
match is `skill.metadata.get("domain") == self._trigger_domain`). So a scheduling
SKILLz that LACKS `domain:` is orphaned -- it never auto-fires from the daemon.

These tests assert the two remaining read-only scheduling SKILLz now carry
`domain: youtube` AND still parse as valid YAML with their Skills 2.0 hygiene fields
intact, using the SAME frontmatter parser the WRE discovery uses
(WRESkillsDiscovery._extract_frontmatter -> yaml.safe_load). They are NON-VACUOUS:
the assertion is on the parsed metadata dict the trigger actually reads, not on raw
text -- a malformed frontmatter (e.g. a stray tab) would FAIL the parse.
"""

from pathlib import Path

import pytest

from modules.infrastructure.wre_core.skillz.wre_skills_discovery import (
    WRESkillsDiscovery,
)

# Repo root: .../youtube_shorts_scheduler/tests -> parents[4]
_REPO_ROOT = Path(__file__).resolve().parents[4]
_SKILLZ_DIR = (
    _REPO_ROOT
    / "modules"
    / "platform_integration"
    / "youtube_shorts_scheduler"
    / "skillz"
)

_DISCOVERY = WRESkillsDiscovery(_REPO_ROOT)


def _frontmatter(skill_dir: str) -> dict:
    """Parse a SKILLz.md frontmatter exactly as the WRE discovery does."""
    path = _SKILLZ_DIR / skill_dir / "SKILLz.md"
    content = path.read_text(encoding="utf-8")
    meta = _DISCOVERY._extract_frontmatter(content)
    assert isinstance(meta, dict) and meta, f"{skill_dir}: frontmatter failed to parse"
    return meta


# The two SKILLz this slice registers for auto-fire (the live one is also self-gated).
AUTO_FIRE_SKILLS = ["reschedule_plan", "shorts_live_schedule_signal"]


@pytest.mark.parametrize("skill_dir", AUTO_FIRE_SKILLS)
def test_skill_has_domain_youtube(skill_dir):
    """The trigger fires iff metadata['domain'] == 'youtube' -- assert exactly that."""
    meta = _frontmatter(skill_dir)
    domain = str(meta.get("domain", "")).lower().strip()
    assert domain == "youtube", (
        f"{skill_dir}: domain must be 'youtube' for WRE auto-fire "
        f"(skill_trigger.py:103); got {meta.get('domain')!r}"
    )
    # name must still match the directory (sanity that we edited the right file).
    assert meta.get("name") == skill_dir


@pytest.mark.parametrize("skill_dir", AUTO_FIRE_SKILLS)
def test_skills_2_0_fields_intact(skill_dir):
    """Adding domain must NOT drop the Skills 2.0 hygiene fields."""
    meta = _frontmatter(skill_dir)
    assert "category" in meta, f"{skill_dir}: missing Skills 2.0 'category'"
    assert "evals" in meta, f"{skill_dir}: missing Skills 2.0 'evals'"
    assert "retirement_date" in meta, f"{skill_dir}: missing Skills 2.0 'retirement_date'"
    # version/intent_type still present (the rest of the frontmatter survived).
    assert meta.get("version")
    assert meta.get("intent_type")


def test_what_should_i_schedule_already_registered():
    """Control: the prior-landed skill is the registration template (must stay youtube)."""
    meta = _frontmatter("what_should_i_schedule")
    assert str(meta.get("domain", "")).lower().strip() == "youtube"


def test_discovery_tags_both_skills_youtube():
    """End-to-end via the REAL discovery scan: both skills surface with domain=youtube.

    Non-vacuous: this runs WRESkillsDiscovery.discover_all_skills() (the same call the
    trigger uses) and confirms the two skills appear with the youtube domain tag, i.e.
    the trigger's `domain == 'youtube'` filter would include them.
    """
    skills = _DISCOVERY.discover_all_skills()
    by_name = {s.skill_name: s for s in skills}
    for name in AUTO_FIRE_SKILLS:
        assert name in by_name, f"{name} not discovered by WRESkillsDiscovery"
        domain = str(by_name[name].metadata.get("domain", "")).lower().strip()
        assert domain == "youtube", f"{name}: discovery domain={domain!r}, expected youtube"


def test_reschedule_apply_NOT_auto_registered():
    """Out-of-scope guard: the MUTATING reschedule_apply must stay manual/gated.

    It must NOT carry domain:youtube (it would auto-fire its mutating path). If the
    skill exists it is asserted orphan-by-design; if it does not exist, that is fine too.
    """
    path = _SKILLZ_DIR / "reschedule_apply" / "SKILLz.md"
    if not path.exists():
        pytest.skip("reschedule_apply SKILLz.md not present")
    meta = _DISCOVERY._extract_frontmatter(path.read_text(encoding="utf-8"))
    assert str(meta.get("domain", "")).lower().strip() != "youtube", (
        "reschedule_apply (mutating) must NOT auto-fire -- keep it manual/gated"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
