"""Static skill/registry contracts, not proof of a deployed media executor."""

import json
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]
MODULES_ROOT = Path(__file__).resolve().parents[3]
SKILL_PATH = MODULE_ROOT / "skillz" / "yumori_contact_ledger" / "SKILLz.md"
CONTEXT_PATH = MODULE_ROOT / "docs" / "YUMORI_CONTACT_LEDGER_CONTEXT.md"
ROLE_PATH = SKILL_PATH.parent / "MEDIA_DAE_ROLES.json"
SKILL_REGISTRY_PATH = (
    MODULES_ROOT / "infrastructure" / "wre_core" / "skillz" / "skills_registry_v2.json"
)


def test_yumori_contact_skill_is_registered_as_prototype() -> None:
    registry = json.loads(SKILL_REGISTRY_PATH.read_text(encoding="utf-8"))
    entry = registry["skills"]["yumori_contact_ledger"]
    assert registry["total_skills"] == len(registry["skills"])
    assert entry["location"] == "modules/foundups/esingularity/skillz/yumori_contact_ledger"
    assert entry["version"] == "0.5.0"
    assert entry["promotion_state"] == "prototype"
    assert entry["intent_type"] == "MAINTENANCE"
    assert "WSP 95" in entry["wsp_chain"]
    assert "WSP 97" in entry["wsp_chain"]


def test_skill_preserves_gmail_lineage_and_external_truth_boundary() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    assert "message_id" in skill
    assert "thread_id" in skill
    assert "Do not add a custom campaign tracking signature" in skill
    assert "YUMORI.me Contacts" in skill
    assert "YUMORI.me Moshpit" in skill
    assert "YUMORI.me Contacts Pics" in skill
    assert "NEEDS_VERIFICATION" in skill
    assert "The Skillz grants no Gmail or Drive mutation authority by itself" in skill
    assert "GMAIL_RECEIPT_REQUIRED" in skill
    assert "Asia/Tokyo" in skill
    assert "Materiality controls summary prominence, not receipt retention" in skill


def test_government_correspondence_uses_live_routing_without_repo_pii() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    assert "Government correspondence operating contract" in skill
    assert "Repo first for project truth" in skill
    assert "Read correspondence before drafting" in skill
    assert "Card fallback" in skill
    assert "Japanese-first government drafting" in skill
    assert "Correspondence Routing" in skill
    assert "DEFAULT_BCC" in skill
    assert "No private addresses in Git" in skill
    assert "Do not guess undisclosed internal addresses" in skill
    assert "Post-send reconciliation" in skill


def test_context_contract_names_the_live_sources_without_private_dump() -> None:
    context = CONTEXT_PATH.read_text(encoding="utf-8")
    assert "`YUMORI.me Contacts`" in context
    assert "`Email Log` tab" in context
    assert "`YUMORI.me Moshpit`" in context
    assert "`YUMORI.me Contacts Pics`" in context
    assert "Do not hard-code Drive file IDs or private contact dumps" in context
    assert "Gmail `Message ID`" in context
    assert "Gmail `thread_id`" in context


def test_media_profiles_define_role_bound_deliverables() -> None:
    packet = json.loads(ROLE_PATH.read_text(encoding="utf-8"))
    roles = packet["roles"]
    assert set(roles) == {
        "LOCAL_MEDIA_DAE", "REGIONAL_MEDIA_DAE", "NATIONAL_MEDIA_DAE",
        "PRESS_WRITER", "PRESS_EDITOR", "RELEASE_MANAGER", "CORRESPONDENCE_CURATOR",
    }
    for profile in roles.values():
        for field in ("trigger", "objective", "required_sources", "output", "acceptance", "handoff"):
            assert profile[field], field
        assert profile["handoff"] in set(roles) | {"RECONCILED"}


def test_media_profiles_separate_editorial_hooks() -> None:
    packet = json.loads(ROLE_PATH.read_text(encoding="utf-8"))
    profiles = [packet["roles"][name] for name in (
        "LOCAL_MEDIA_DAE", "REGIONAL_MEDIA_DAE", "NATIONAL_MEDIA_DAE"
    )]
    assert len({p["hook"] for p in profiles}) == 3
    assert len({p["editorial_scope"] for p in profiles}) == 3
    assert "onsen" in profiles[0]["hook"]
    assert "existing data-center disputes" in profiles[2]["hook"]
    assert "documented editorial remit" in packet["scope_rule"]
    assert all(p["handoff"] == "PRESS_WRITER" for p in profiles)


def test_media_roles_preserve_duty_authority_boundary() -> None:
    packet = json.loads(ROLE_PATH.read_text(encoding="utf-8"))
    roles = packet["roles"]
    assert packet["identity"] == "0102"
    assert packet["status"] == "SPECIFIED_NOT_RUNTIME_BOUND"
    assert packet["parent_skill"] == "yumori_contact_ledger"
    for role in ("PRESS_WRITER", "PRESS_EDITOR", "CORRESPONDENCE_CURATOR"):
        assert roles[role]["can_send"] is False
    assert roles["RELEASE_MANAGER"]["can_send"] == (
        "ONLY_WITH_CURRENT_PRINCIPAL_AUTHORIZATION_AND_CONNECTOR_PERMISSION"
    )
    assert roles["PRESS_WRITER"]["handoff"] == "PRESS_EDITOR"
    assert roles["PRESS_EDITOR"]["handoff"] == "RELEASE_MANAGER"
    assert roles["RELEASE_MANAGER"]["handoff"] == "CORRESPONDENCE_CURATOR"
    assert "HOLD" in packet["workflow_states"]
    assert "unresolved_prior_send" in packet["hold_conditions"]


def test_media_profiles_bind_sources_and_receipt_requirements() -> None:
    packet = json.loads(ROLE_PATH.read_text(encoding="utf-8"))
    assert packet["canonical_report_url"] == "https://esingularity.ai/reports/jhr"
    assert "Prefer the website JHR hub over LinkedIn" in packet["link_rule"]
    assert {
        "hook", "why_now", "verified_evidence", "strongest_counterpoint",
        "single_reporting_request", "source_urls", "photo_provenance",
        "press_contact_source", "dedupe_result", "authorization", "send_state",
    } <= set(packet["required_pitch_fields"])
    curator = packet["roles"]["CORRESPONDENCE_CURATOR"]
    assert "message_id" in curator["output"]
    assert "Asia/Tokyo" in curator["output"]
    assert "Draft creation is never a sent event" in curator["acceptance"]
    assert "All scoped emails retain receipts, not just prominent milestones" in curator["acceptance"]


def test_media_profiles_are_registered_without_new_skill_entries() -> None:
    packet = json.loads(ROLE_PATH.read_text(encoding="utf-8"))
    registry = json.loads(SKILL_REGISTRY_PATH.read_text(encoding="utf-8"))
    entry = registry["skills"]["yumori_contact_ledger"]
    assert set(entry["logical_roles"]) == set(packet["roles"])
    assert not (set(packet["roles"]) & set(registry["skills"]))
