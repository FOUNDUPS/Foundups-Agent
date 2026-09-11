"""Contract tests for the eSingularity FoundUp and YUMORI public deck."""

import json
import re
from pathlib import Path

from modules.foundups.agent.src.foundup_manifest_validator import validate_manifest_file


MODULE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = MODULE_ROOT / "foundup_manifest.json"
REGISTRY_PATH = REPO_ROOT / "foundups" / "foundup_registry.json"
FRONTEND_ROOT = MODULE_ROOT / "frontend"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read(relative: str) -> str:
    return (FRONTEND_ROOT / relative).read_text(encoding="utf-8")


def test_manifest_passes_shared_build_contract_validator() -> None:
    result = validate_manifest_file(MANIFEST_PATH)
    assert result.ok, result.errors


def test_wsp104_identity_is_stable_and_public() -> None:
    manifest = load_json(MANIFEST_PATH)
    assert manifest["foundup_id"] == "esingularity_001"
    assert manifest["routing_prefix"] == "/f/esingularity_001"
    assert manifest["data_namespace"] == "idb_esingularity_001"
    assert manifest["entry_url"] == "https://esingularity.ai/"
    assert manifest["required_subscription_tier"] == "free"
    assert manifest["is_invite_only"] is False


def test_no_token_is_invented_for_the_campaign() -> None:
    manifest = load_json(MANIFEST_PATH)
    registry = load_json(REGISTRY_PATH)
    entry = next(item for item in registry["entities"] if item["foundup_id"] == manifest["foundup_id"])
    assert not manifest.get("token_symbol")
    assert entry["token_status"] == "TOKEN_DEFERRED"
    assert entry["token_symbol"] is None


def test_sites_configuration_and_primary_routes_are_present() -> None:
    hosting = load_json(FRONTEND_ROOT / ".openai" / "hosting.json")
    package = load_json(FRONTEND_ROOT / "package.json")
    assert hosting["project_id"] == "appgprj_6a917b21b1a4819181a61738ed5274a5"
    assert hosting["d1"] == "DB"
    assert package["scripts"]["build"] == "vinext build"
    for route in ("app/page.tsx", "app/future/page.tsx", "app/team/page.tsx"):
        assert (FRONTEND_ROOT / route).is_file()


def test_existing_ticker_receives_one_deck_notification() -> None:
    page = read("app/page.tsx")
    ticker = read("components/CampaignTicker.tsx")
    assert page.count("<CampaignTicker />") == 1
    assert "<YumoriPresentation />" in page
    assert "{ label: 'NEW', text: 'YUMORI / COG DC 10枚のプレゼンを見る', href: '#yumori-deck' }" in ticker
    assert ticker.count("href: '#yumori-deck'") == 1
    for existing_label in ("VISIT", "LISTEN", "LEARN", "EXPLORE", "CONNECT", "JOIN", "ACT"):
        assert f"label: '{existing_label}'" in ticker


def test_fullscreen_vision_has_ten_japanese_first_slides_and_derived_languages() -> None:
    content = read("content/yumori-vision.ts")
    component = read("components/YumoriPresentation.tsx")
    source_block = content.split("export const visionUi", 1)[0]
    assert len(re.findall(r"\n\s+id: '[a-z-]+'", source_block)) == 10
    for locale in ("ja", "en", "pt"):
        assert f"{locale}:" in content
    assert "getYumoriVisionSlides" in content
    assert "data-yumori-localized" in component
    assert "MutationObserver" in component
    assert "vision=1" not in component  # URLSearchParams is used rather than hard-coded query text.
    assert "url.searchParams.get('vision') === '1'" in component


def test_current_vision_propositions_and_progressive_disclosure_are_present() -> None:
    content = read("content/yumori-vision.ts")
    component = read("components/YumoriPresentation.tsx")
    for proposition in (
        "壊す前に、未来を比べる。",
        "なぜ15.8億円を使って、選択肢を壊すのか。",
        "毎夜、違う景色。",
        "24時間温泉。大きな露天風呂。滞在したくなる場所。",
        "コンピュートは、新しい「田んぼ」だ。",
        "熱を捨てない。地域へ戻す。",
        "60 FoundUps。1チーム最大3人。あとはAI。",
        "福井の課題から、福井の会社をつくる。",
        "福井から、日本の分散型コンピュートへ。",
        "建物は、まだ立っている。選択肢も、まだ残っている。",
    ):
        assert proposition in content
    assert "<details className=\"yumori-slide-details\"" in component
    assert "slide.evidence.map" in component
    assert "slide.link.href" in component


def test_fullscreen_deck_uses_real_building_sprite_and_accessible_controls() -> None:
    component = read("components/YumoriPresentation.tsx")
    css = read("components/YumoriPresentation.module.css")
    assert (FRONTEND_ROOT / "public" / "vision" / "vision-sprite.jpg").is_file()
    assert "SPRITE_URL = '/vision/vision-sprite.jpg'" in component
    assert "backgroundPosition" in component
    assert "background-size:100% 1000%" in css
    assert "role=\"img\"" in component
    assert "aria-label={slide.alt}" in component
    assert "ArrowLeft" in component and "ArrowRight" in component and "Escape" in component
    assert "prefers-reduced-motion: reduce" in component
    assert "Math.abs(distance) > 55" in component
    assert "AUTOPLAY_MS = 9000" in component
    assert "https://yumori.me" in component
    assert 'href="/reports/jhr"' in component


def test_cog_dc_and_floor_model_match_current_truth_boundary() -> None:
    page = read("app/page.tsx")
    content = read("content/yumori-presentation.ts")
    vision = read("content/yumori-vision.ts")
    combined = page + content + vision
    for required in (
        "COMMUNITY-OWNED GREEN DATA CENTER",
        "私たちのCOG DCコンピュート",
        "THIRD FLOOR · EMERGING",
        "TOP FLOOR · ADVANCED",
        "SEPARATE INFRASTRUCTURE",
        "IDEA → PROJECT → FOUNDUP → VALIDATED FOUNDUP → INDEPENDENT AI-NATIVE BUSINESS",
        "地下をジム・休憩・回復",
    ):
        assert required in combined
    for obsolete in ("2ND FLOOR · LEARN", "4TH FLOOR · LAUNCH"):
        assert obsolete not in page
    assert "長谷川章氏の参加は未承認" in page


def test_economic_claims_are_labeled_and_arithmetic_is_sound() -> None:
    content = read("content/yumori-presentation.ts")
    vision = read("content/yumori-vision.ts")
    assert 129_649 * 1_000 == 129_649_000
    assert 129_649 * 5_546 == 719_033_354
    for label in ("VERIFIED", "REPORTED", "MODELLED"):
        assert label in vision
    assert "5年売上 約53.7億円" in vision
    assert "5年累計FCFE 約19.4億円" in vision
    assert "予測・保証ではありません" in vision
    assert "予算・契約額ではありません" in content


def test_existing_public_assets_and_local_sources_remain_present() -> None:
    for asset in (
        "public/yumori-compute-field.png",
        "public/yumori-autonomous-agriculture.png",
        "public/concept-onsen.jpg",
        "public/satellite-view.jpeg",
    ):
        assert (FRONTEND_ROOT / asset).is_file()
    page = read("app/page.tsx")
    for source in (
        "https://www.dsai.u-fukui.ac.jp/system/",
        "https://www.pref.fukui.lg.jp/doc/021037/service/service.html",
        "https://www.pref.fukui.lg.jp/doc/chisangi/fukusat/suisen_syokai.html",
        "https://kigyoritti.pref.fukui.lg.jp/outline/technical",
        "https://www.digital-kakejiku.com/",
    ):
        assert source in page
    assert "長谷川章氏の参加は未承認" in page


def test_future_route_is_utf8_and_uses_cog_dc_compute() -> None:
    future = read("app/future/page.tsx")
    assert "福井に、" in future
    assert "私たちのCOG DCコンピュート" in future
    assert "まず約1 MWを検討単位" in future
    assert "容量、時期、費用、熱利用、収益は未確定" in future
    assert not re.search(r"縺|蜿|蝓|譛|險育", future)
