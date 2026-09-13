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
    assert "学生・チームと初期FoundUpプロジェクト" in polisher
    assert "実証を通過したFoundUpプロジェクト" in polisher
    assert "課題を解くFoundUpプロジェクト" in polisher
    assert "収益化は目的ではなく" in polisher
    assert "そこで働く学生、FoundUpプロジェクト、研究・地域プロジェクト" in polisher


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
