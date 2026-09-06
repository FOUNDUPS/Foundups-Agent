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


def test_existing_ticker_receives_one_new_deck_notification() -> None:
    page = read("app/page.tsx")
    ticker = read("components/CampaignTicker.tsx")
    assert page.count("<CampaignTicker />") == 1
    assert "<YumoriPresentation />" in page
    assert "{ label: 'NEW', text: 'YUMORI / COG DC 10枚のプレゼンを見る', href: '#yumori-deck' }" in ticker
    assert ticker.count("href: '#yumori-deck'") == 1
    for existing_label in ("VISIT", "LISTEN", "LEARN", "EXPLORE", "CONNECT", "JOIN", "ACT"):
        assert f"label: '{existing_label}'" in ticker


def test_deck_has_ten_japanese_canonical_slides_and_derived_languages() -> None:
    content = read("content/yumori-presentation.ts")
    component = read("components/YumoriPresentation.tsx")
    japanese_block = content.split("export const yumoriEn", 1)[0]
    assert len(re.findall(r"\n\s+id: '[a-z-]+'", japanese_block)) == 10
    assert "CANONICAL SOURCE STATE: Japanese" in content
    assert "export const yumoriEn" in content
    assert "export const yumoriPt" in content
    assert "Concept image transitioning from a Fukui rice field" in content
    assert "Imagem conceitual passando de um arrozal de Fukui" in content
    assert "data-yumori-localized" in component
    assert "MutationObserver" in component
    assert "const visualLabels" in component


def test_canonical_propositions_and_progressive_disclosure_are_present() -> None:
    content = read("content/yumori-presentation.ts")
    component = read("components/YumoriPresentation.tsx")
    for proposition in (
        "コンピュートは、この温泉を救い、この地域を再生し、日本を変える力になれるだろうか。",
        "壊す前に、この資産の価値を測っただろうか。",
        "データセンターは、コンピュートを育てる田んぼだ。",
        "なぜ、その熱を捨てるのか。",
        "一つの資産。いくつもの経済。",
        "福井は、自分たちのコンピュートで何をつくるのか。",
        "毎夜、違う風景。",
        "建物は、まだ立っている。選択肢も、まだ残っている。",
    ):
        assert proposition in content
    assert "<details className=\"yumori-slide-details\"" in component
    assert "slide.evidence.map" in component
    assert "slide.link.href" in component


def test_cog_dc_and_floor_model_match_current_truth_boundary() -> None:
    page = read("app/page.tsx")
    content = read("content/yumori-presentation.ts")
    combined = page + content
    for required in (
        "COMMUNITY-OWNED GREEN DATA CENTER",
        "私たちのCOG DCコンピュート",
        "THIRD FLOOR · EMERGING",
        "TOP FLOOR · ADVANCED",
        "SEPARATE INFRASTRUCTURE",
        "IDEA → PROJECT → FOUNDUP → VALIDATED FOUNDUP → INDEPENDENT AI-NATIVE BUSINESS",
    ):
        assert required in combined
    for obsolete in ("2ND FLOOR · LEARN", "4TH FLOOR · LAUNCH"):
        assert obsolete not in page
    assert "長谷川章氏の参加は未承認" in page


def test_economic_claims_are_labeled_and_arithmetic_is_sound() -> None:
    content = read("content/yumori-presentation.ts")
    assert 129_649 * 1_000 == 129_649_000
    assert 129_649 * 5_546 == 719_033_354
    for label in ("VERIFIED", "REPORTED", "MODELLED", "PROJECT RANGE", "PROJECT VISION"):
        assert label in content
    assert "予測ではありません" in content
    assert "予算・契約額ではありません" in content
    assert "施工者見積もり未取得" in content


def test_autoplay_is_optional_and_pauses_for_interaction() -> None:
    component = read("components/YumoriPresentation.tsx")
    assert "prefers-reduced-motion: reduce" in component
    assert "onFocusCapture={() => setPlaying(false)}" in component
    assert "onWheel={() => setPlaying(false)}" in component
    assert "setPlaying(false); pointerStart.current" in component
    assert "Math.abs(distance) > 55" in component
    assert "AUTOPLAY_MS = 9000" in component


def test_deck_assets_and_outreach_sources_are_present() -> None:
    for asset in (
        "public/yumori-compute-field.png",
        "public/yumori-autonomous-agriculture.png",
        "public/concept-onsen.jpg",
        "public/satellite-view.jpeg",
    ):
        assert (FRONTEND_ROOT / asset).is_file()
    component = read("components/YumoriPresentation.tsx")
    for source in (
        "https://www.dsai.u-fukui.ac.jp/system/",
        "https://www.eng.u-fukui.ac.jp/graduate_school/knowledge_society/his/research/index.html",
        "https://haselab.fuis.u-fukui.ac.jp/",
        "https://www.fukui-ut.ac.jp/robotics/",
        "https://www.fpu.ac.jp/faculty_members/d000000f.html",
    ):
        assert source in component
    assert "参加・支持を示すものではありません" in component


def test_future_route_is_utf8_and_uses_cog_dc_compute() -> None:
    future = read("app/future/page.tsx")
    assert "福井に、" in future
    assert "私たちのCOG DCコンピュート" in future
    assert "まず約1 MWを検討単位" in future
    assert "容量、時期、費用、熱利用、収益は未確定" in future
    assert not re.search(r"縺|蜿|蝓|譛|險育", future)
