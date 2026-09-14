"""Japanese-first public-copy regression checks for eSingularity."""

from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = MODULE_ROOT / "frontend"


def read(relative: str) -> str:
    return (FRONTEND_ROOT / relative).read_text(encoding="utf-8")


def test_japanese_copy_polisher_is_mounted_globally() -> None:
    layout = read("app/layout.tsx")
    assert "JapaneseSurfacePolisher" in layout
    assert "<JapaneseSurfacePolisher />" in layout


def test_japanese_surface_uses_innovation_space_not_hub() -> None:
    polisher = read("components/JapaneseSurfacePolisher.tsx")
    assert "イノベーション・スペース" in polisher
    assert "Innovation Space" in polisher
    assert "HOW · ESINGULARITY INNOVATION HUB" in polisher  # legacy alias only
    assert "HOW · eSINGULARITY INNOVATION SPACE" in polisher


def test_foundup_is_a_project_not_a_person_label() -> None:
    polisher = read("components/JapaneseSurfacePolisher.tsx")
    yumori = read("app/yumori/page.tsx")
    future = read("app/future/page.tsx")
    assert "学生・チームと初期FoundUpプロジェクト" in polisher
    assert "実証を通過したFoundUpプロジェクト" in polisher
    assert "課題を解くFoundUpプロジェクト" in polisher
    assert "収益化は目的ではなく" in polisher
    assert "そこで働く学生、FoundUpプロジェクト、研究・地域プロジェクト" in polisher
    assert "FoundUpプロジェクトと地域企業" in yumori
    assert "学生・FoundUpプロジェクト" in future


def test_japanese_structural_labels_are_available() -> None:
    polisher = read("components/JapaneseSurfacePolisher.tsx")
    for phrase in (
        "下層階 · 温泉・地域スペース",
        "3階 · 挑戦・育成スペース",
        "最上階 · 実証・発展スペース",
        "別棟 · COG DC",
        "見る · 知る · 共有する · 動く",
        "なぜ残すのか · 建物の価値",
        "来訪者経済 · 試算シナリオ",
        "議会に求める判断",
        "しくみ · AIの田んぼ",
        "誰がつくるか · 地域",
        "福井の経済的な未来",
        "組織より、まず人から",
        "この人がここにいる理由",
    ):
        assert phrase in polisher


def test_japanese_tab_replaces_decorative_english_labels() -> None:
    polisher = read("components/JapaneseSurfacePolisher.tsx")
    for phrase in (
        "なぜ · 温泉を守る",
        "未来像 · ここがどう変わる？",
        "敷地構想",
        "温泉構想",
        "01 · 露天風呂",
        "技術検証が必要",
        "02 · 食",
        "03 · 夜",
        "写真",
        "聴く",
        "計画",
        "詳しく",
        "反対票",
        "10枚のビジョン",
        "僧の現在地",
        "新着",
        "停止",
        "チーム形成",
        "顧客・協力者",
    ):
        assert phrase in polisher


def test_secondary_routes_point_to_current_root_sections() -> None:
    future = read("app/future/page.tsx")
    team = read("app/team/page.tsx")
    profile = read("app/team/[slug]/page.tsx")
    for source in (future, team, profile):
        assert '/#innovation-hub' not in source
        assert '/#innovation-space' in source
    assert '/#join' not in team
    assert 'https://yumori.me/' in team


def test_default_secondary_route_source_is_japanese_first() -> None:
    future = read("app/future/page.tsx")
    team = read("app/team/page.tsx")
    profile = read("app/team/[slug]/page.tsx")
    for forbidden in (
        'FUKUI ECONOMIC FUTURE',
        'WHAT FUKUI GETS',
        'KEEP VALUE IN FUKUI',
        'START SMALL · GROW WITH DEMAND',
    ):
        assert forbidden not in future
    for forbidden in ('PEOPLE BEFORE ORGANIZATION', 'LAUNCH TEAM', 'FOUNDING PAIR', 'THE DIRECTORY GROWS WITH PERMISSION'):
        assert forbidden not in team
    for forbidden in ('WHY THIS PERSON IS HERE', 'A MEMORY FROM THE ONSEN', 'FIELD NOTES', 'VERIFIED PUBLIC LINKS', 'BACK TO THE PEOPLE'):
        assert forbidden not in profile


def test_deck_action_uses_current_vote_request_and_clean_live_text() -> None:
    component = read("components/YumoriPresentation.tsx")
    assert "CURRENT_VOTE_ACTION" in component
    assert "解体準備予算に反対を。VOTE NO" in component
    assert "<span>YUMORI.me</span>" in component
    assert "liveDescription" in component
    assert "{slide.title}. {slide.summary}" not in component
