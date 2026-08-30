"""Contract tests for the eSingularity FoundUp migration."""

import json
from pathlib import Path

from modules.foundups.agent.src.foundup_manifest_validator import validate_manifest_file


MODULE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = MODULE_ROOT / "foundup_manifest.json"
REGISTRY_PATH = REPO_ROOT / "foundups" / "foundup_registry.json"
FRONTEND_ROOT = MODULE_ROOT / "frontend"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_manifest_passes_shared_build_contract_validator() -> None:
    result = validate_manifest_file(MANIFEST_PATH)
    assert result.ok, result.errors


def test_wsp104_identity_is_stable_and_isolated() -> None:
    manifest = load_json(MANIFEST_PATH)
    assert manifest["foundup_id"] == "esingularity_001"
    assert manifest["routing_prefix"] == "/f/esingularity_001"
    assert manifest["data_namespace"] == "idb_esingularity_001"


def test_public_campaign_is_not_invite_gated() -> None:
    manifest = load_json(MANIFEST_PATH)
    assert manifest["entry_url"] == "https://esingularity.ai/"
    assert manifest["required_subscription_tier"] == "free"
    assert manifest["is_invite_only"] is False


def test_no_token_is_invented_for_the_campaign() -> None:
    manifest = load_json(MANIFEST_PATH)
    assert not manifest.get("token_symbol")

    registry = load_json(REGISTRY_PATH)
    entry = next(item for item in registry["entities"] if item["foundup_id"] == "esingularity_001")
    assert entry["token_status"] == "TOKEN_DEFERRED"
    assert entry["token_symbol"] is None


def test_registry_matches_manifest_and_module_location() -> None:
    manifest = load_json(MANIFEST_PATH)
    registry = load_json(REGISTRY_PATH)
    entry = next(item for item in registry["entities"] if item["foundup_id"] == manifest["foundup_id"])
    assert entry["module_path"] == "modules/foundups/esingularity"
    assert entry["manifest_path"] == "modules/foundups/esingularity/foundup_manifest.json"
    assert entry["public_url_or_route"] == manifest["entry_url"]


def test_sites_configuration_and_primary_routes_are_present() -> None:
    hosting = load_json(FRONTEND_ROOT / ".openai" / "hosting.json")
    package = load_json(FRONTEND_ROOT / "package.json")
    assert hosting["project_id"] == "appgprj_6a917b21b1a4819181a61738ed5274a5"
    assert hosting["d1"] == "DB"
    assert package["scripts"]["build"] == "vinext build"
    assert (FRONTEND_ROOT / "app" / "page.tsx").is_file()
    assert (FRONTEND_ROOT / "app" / "future" / "page.tsx").is_file()
    assert (FRONTEND_ROOT / "app" / "team" / "page.tsx").is_file()
    for required_library in ("db.ts", "event.ts", "i18n.ts", "project-data.ts", "team.ts"):
        assert (FRONTEND_ROOT / "lib" / required_library).is_file()


def test_hero_campaign_message_is_equivalent_across_languages() -> None:
    page = (FRONTEND_ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    switcher = (FRONTEND_ROOT / "components" / "LanguageSwitcher.tsx").read_text(encoding="utf-8")
    assert "温泉を守り、" in page
    assert "地域のAI基盤でまちを元気に。" in page
    assert "Save the Onsen." in switcher
    assert "Revitalize the Community with Local Compute." in switcher
    assert "Salve o onsen." in switcher
    assert "Revitalize a comunidade com computação local." in switcher
    assert "壊すために公費を使う前に" in page
    assert "Before spending public money to demolish this place" in switcher
    assert "Antes de gastar dinheiro público para demolir este lugar" in switcher


def test_landing_music_is_opt_in_and_project_owned() -> None:
    page = (FRONTEND_ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    music = (FRONTEND_ROOT / "components" / "HeroMusic.tsx").read_text(encoding="utf-8")
    assert "<HeroMusic />" in page
    assert "autoplay" not in music.lower()
    assert "IntersectionObserver" in music
    assert (FRONTEND_ROOT / "public" / "audio" / "9dragonheads.mp3").is_file()


def test_future_place_is_labeled_as_a_conditional_concept() -> None:
    page = (FRONTEND_ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    assert "CONCEPT RENDER" in page
    assert "日本初を目指す" in page
    assert "ENGINEERING VALIDATION REQUIRED" in page
    assert "長谷川章氏" in page
    assert "GROUND FLOOR" in page
    assert (FRONTEND_ROOT / "public" / "onsen-future-concept-v4.webp").is_file()
    assert not (FRONTEND_ROOT / "public" / "onsen-future-concept-v1.webp").exists()
    assert not (FRONTEND_ROOT / "public" / "onsen-future-concept-v2.webp").exists()
    assert not (FRONTEND_ROOT / "public" / "onsen-future-concept-v3.webp").exists()


def test_landing_journey_uses_plain_campaign_questions() -> None:
    page = (FRONTEND_ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    for label in ("WHY · 温泉を守る", "WHAT · ここがどう変わる？", "HOW · ESINGULARITY INNOVATION HUB", "WHEN · COMMUNITY MEETINGS"):
        assert label in page
    for removed_index in ("08 <span>", "09 <span>", "10 <span>"):
        assert removed_index not in page
    assert "PRE-CONSTRUCTION ACTION PLAN" not in page
    assert "SOURCES & TRANSPARENCY" not in page
