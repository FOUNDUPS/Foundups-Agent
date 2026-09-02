"""Contract tests for the eSingularity FoundUp migration."""

import json
import re
from pathlib import Path
from urllib.parse import urlparse

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
    styles = (FRONTEND_ROOT / "app" / "globals.css").read_text(encoding="utf-8")
    switcher = (FRONTEND_ROOT / "components" / "LanguageSwitcher.tsx").read_text(encoding="utf-8")
    assert "SITE CONCEPT" in page
    assert "ONSEN CONCEPT" in page
    assert "日本初を目指す" in page
    assert "ENGINEERING VALIDATION REQUIRED" in page
    assert "長谷川章氏" in page
    assert "GROUND FLOOR" in page
    assert (FRONTEND_ROOT / "public" / "satellite-view.jpeg").is_file()
    assert (FRONTEND_ROOT / "public" / "concept-onsen.jpg").is_file()
    assert (FRONTEND_ROOT / "public" / "akira-hasegawa.jpeg").is_file()
    assert 'className="card-reference-image awara-reference-image"' in page
    assert 'className="card-reference-image dk-reference-image"' in page
    assert "See the real example: Awara Onsen Yukemuri Yokocho" in switcher
    assert "Open the official D-K gallery" in switcher
    assert ".artist-reference img{width:52px;height:52px" in styles
    assert ".card-reference-image{position:relative;display:block;width:calc(100% + 56px);height:150px" in styles
    assert not (FRONTEND_ROOT / "public" / "onsen-future-concept-v1.webp").exists()
    assert not (FRONTEND_ROOT / "public" / "onsen-future-concept-v2.webp").exists()
    assert not (FRONTEND_ROOT / "public" / "onsen-future-concept-v3.webp").exists()
    assert not (FRONTEND_ROOT / "public" / "onsen-future-concept-v4.webp").exists()


def test_innovation_hub_uses_learn_create_launch_without_language_leakage() -> None:
    page = (FRONTEND_ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    styles = (FRONTEND_ROOT / "app" / "globals.css").read_text(encoding="utf-8")
    switcher = (FRONTEND_ROOT / "components" / "LanguageSwitcher.tsx").read_text(encoding="utf-8")

    for floor_label in (
        "GROUND FLOOR · GATHER",
        "2ND FLOOR · LEARN",
        "3RD FLOOR · CREATE",
        "4TH FLOOR · LAUNCH",
    ):
        assert floor_label in page

    for english_copy in (
        "build Fukui’s place to learn, create and launch.",
        "AI Learning Studio — Primary and Middle School",
        "A parent- and teacher-guided studio",
        "AI Creation Lab — High School and University",
        "collaborate with AI to research local and regional challenges",
        "AI Launch Hub — University Projects and Startups",
        "new projects, startups, and work in Fukui",
    ):
        assert english_copy in switcher

    assert ".section h2 em,.return-heading h3{font-family:inherit;font-style:normal}" in styles
    assert ".return-heading h3{font-weight:850}" in styles
    assert "[placeholder],[aria-label],[title],[alt]" in switcher


def test_public_action_section_replaces_the_repeated_vision_summary() -> None:
    page = (FRONTEND_ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    switcher = (FRONTEND_ROOT / "components" / "LanguageSwitcher.tsx").read_text(encoding="utf-8")
    ticker = (FRONTEND_ROOT / "components" / "CampaignTicker.tsx").read_text(encoding="utf-8")
    share = (FRONTEND_ROOT / "components" / "CampaignShareButton.tsx").read_text(encoding="utf-8")

    assert 'className="choice-path"' not in page
    assert "再生後の五つの役割" not in page
    assert "見る。知る。共有する。" in page
    assert 'id="city-action"' in page
    assert "0776-20-5400" in page
    assert "mailform101607.html?PAGE_NO=15196" in page
    for vanity_url in ("pics.yumori.info", "music.yumori.info", "pc.yumori.info", "yumori.me"):
        assert vanity_url in page
    for english_copy in (
        "See the site and the vision",
        "Listen to the music of Kuzuryu",
        "Understand the renewal plan",
        "Share with family and friends",
        "Join the citizens’ declaration",
        "make your voice heard.",
    ):
        assert english_copy in switcher
    for action in ("VISIT", "LISTEN", "LEARN", "SHARE", "JOIN", "ACT", "SAVE THE DRAGON"):
        assert action in ticker
    assert "8月31日" not in ticker
    assert "navigator.share" in share
    assert "navigator.clipboard.writeText" in share


def test_stakeholder_campaign_sequence_is_native_and_multilingual() -> None:
    page = (FRONTEND_ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    switcher = (FRONTEND_ROOT / "components" / "LanguageSwitcher.tsx").read_text(encoding="utf-8")
    styles = (FRONTEND_ROOT / "app" / "globals.css").read_text(encoding="utf-8")

    assert 'src="/why-preserve.jpg"' not in page
    assert 'className="campaign-sequence"' in page
    for phase in ("STOP", "ASSEMBLE", "LAND", "CITY", "UNIVERSITIES", "CUSTOMERS + PARTNERS"):
        assert phase in page
    for english_copy in (
        "Stop Demolition. Keep Time to Compare.",
        "Build the COGDC Coalition",
        "Secure Landowner Agreement",
        "Present a City-Ready Alternative",
        "Define Use with Fukui Universities",
        "Secure Corporate Customers and Partners",
    ):
        assert english_copy in switcher
    assert ".campaign-sequence" in styles


def test_landing_journey_uses_plain_campaign_questions() -> None:
    page = (FRONTEND_ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    for label in ("WHY · 温泉を守る", "WHAT · ここがどう変わる？", "HOW · ESINGULARITY INNOVATION HUB", "WHEN · COMMUNITY MEETINGS"):
        assert label in page
    for removed_index in ("08 <span>", "09 <span>", "10 <span>"):
        assert removed_index not in page
    assert "PRE-CONSTRUCTION ACTION PLAN" not in page
    assert "SOURCES & TRANSPARENCY" not in page


def test_fukui_compute_story_is_local_specific_and_multilingual() -> None:
    page = (FRONTEND_ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    switcher = (FRONTEND_ROOT / "components" / "LanguageSwitcher.tsx").read_text(encoding="utf-8")

    for claim in ("Computeが、", "福井の学生と大学", "福井の田んぼ", "県民衛星「すいせん」", "福井のものづくり"):
        assert claim in page
    for official_source in (
        "https://www.dsai.u-fukui.ac.jp/",
        "https://www.pref.fukui.lg.jp/doc/021037/service/service.html",
        "https://www.pref.fukui.lg.jp/doc/chisangi/fukusat/suisen_syokai.html",
        "https://kigyoritti.pref.fukui.lg.jp/outline/technical",
    ):
        assert official_source in page

    assert "The future runs on " in switcher
    assert "Fukui energy → Fukui compute → Fukui’s future." in switcher
    assert "From Fukui power, create computing power Fukui can use." not in switcher
    assert "Demolition is madness." in switcher
    assert "Fukui would pay to erase an asset—" in switcher
    assert "and 30 years of possibility." in switcher


def test_english_ai_rice_field_has_complete_plain_language_copy() -> None:
    switcher = (FRONTEND_ROOT / "components" / "LanguageSwitcher.tsx").read_text(encoding="utf-8")

    for english_copy in (
        "AI needs",
        "“food,” too.",
        "Just as rice fields produce food for people",
        "Electricity, data, and",
        "Computing power",
        "AI gets to work",
        "This facility would not directly operate farm machinery.",
        "Fukui energy → Fukui compute → Fukui knowledge → Fukui jobs",
        "Research for drones, field monitoring, weed detection, and yield forecasting.",
        "Give students and researchers a local place to learn and test AI.",
        "Develop AI in Fukui for manufacturing, design, and better operations.",
    ):
        assert english_copy in switcher


def test_visitor_spending_scenario_is_transparent_not_a_forecast() -> None:
    page = (FRONTEND_ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    switcher = (FRONTEND_ROOT / "components" / "LanguageSwitcher.tsx").read_text(encoding="utf-8")

    assert 129_649 * 1_000 == 129_649_000
    assert 129_649 * 5_546 == 719_033_354
    assert 129_649 * 1_000 * 30 == 3_889_470_000
    assert 129_649 * 5_546 * 30 == 21_571_000_620
    assert "約1.3億〜7.2億円 / 年" in page
    assert "約38.9億〜215.7億円 / 30年" in page
    assert "129,649 visits × ¥1,000–¥5,546" in page
    assert "PROJECT SCENARIO — NOT A FORECAST" in page
    assert "holds attendance and spending constant and is not discounted" in switcher
    assert "multiplier effects" in switcher
    assert "日本最大" not in page
    assert "Japan’s largest" not in switcher
    assert "This is the only layer currently quantified." in switcher
    assert "Supplier effects, income, jobs, and tax revenue remain excluded" in switcher
    assert "Fukui Prefecture economic-impact analysis" in switcher
    assert "See the illustrative 30-year total and method" in switcher
    assert "About ¥130M–¥720M / year" not in switcher
    assert "About ¥3.9B–¥21.6B / 30 years" not in switcher
    assert "¥129.6M–¥719.0M / year" in switcher
    assert "¥3.89B–¥21.57B / 30 years" in switcher
    assert "Track attendance, repeat visits, overnight stays" in switcher
    assert "Separate construction from permanent jobs" in switcher
    assert "What successful community campaigns measure" in switcher
    assert "https://www.ncdsinc.net/case-studies/forward-sioux-falls" in page
    assert "https://www.ncdsinc.net/case-studies/aspire-clarksville" in page
    assert "These outcomes and ratios are not transferred to Fukui." in switcher
    assert 'className="impact-layers"' in page


def test_hasegawa_profile_links_to_dk_video_without_autoplay() -> None:
    team = (FRONTEND_ROOT / "lib" / "team.ts").read_text(encoding="utf-8")
    profile = (FRONTEND_ROOT / "app" / "team" / "[slug]" / "page.tsx").read_text(encoding="utf-8")
    external_hrefs = [urlparse(href) for href in re.findall(r"href: '([^']+)'", team)]

    assert "https://www.youtube.com/watch?v=jI9decHbUIY" in team
    assert any(
        href.scheme == "https"
        and href.hostname == "www.digital-kakejiku.com"
        and href.path == "/"
        for href in external_hrefs
    )
    assert "profile.feature?.kind === 'video'" in profile
    assert "自動再生はしません" in profile
    assert "<iframe" not in profile
