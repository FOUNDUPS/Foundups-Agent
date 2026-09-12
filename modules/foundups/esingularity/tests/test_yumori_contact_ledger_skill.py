"""Contract tests for the YUMORI.me contact-ledger Skillz/Rolodex entry."""

import json
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]
MODULES_ROOT = Path(__file__).resolve().parents[3]
SKILL_PATH = MODULE_ROOT / "skillz" / "yumori_contact_ledger" / "SKILLz.md"
CONTEXT_PATH = MODULE_ROOT / "docs" / "YUMORI_CONTACT_LEDGER_CONTEXT.md"
SKILL_REGISTRY_PATH = (
    MODULES_ROOT / "infrastructure" / "wre_core" / "skillz" / "skills_registry_v2.json"
)


def test_yumori_contact_skill_is_registered_as_prototype() -> None:
    registry = json.loads(SKILL_REGISTRY_PATH.read_text(encoding="utf-8"))
    entry = registry["skills"]["yumori_contact_ledger"]

    assert registry["total_skills"] == len(registry["skills"])
    assert entry["location"] == "modules/foundups/esingularity/skillz/yumori_contact_ledger"
    assert entry["version"] == "0.1.0"
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
