from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "frontend" / "app" / "yumori" / "page.tsx"


def source() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_yumori_landing_exists_and_is_japanese_first() -> None:
    text = source()
    assert "YUMORI.me / 湯守" in text
    assert "I am a guardian" in text
    assert "地域を守る。地域のAIを、地域のためにつくる。" in text


def test_yumori_is_pro_community_compute_not_blanket_anti_dc() -> None:
    text = source()
    assert "YUMORIはデータセンターそのものに反対するのではなく" in text
    assert "地域の学校、大学、農業、病院、自治体、ものづくり、企業" in text
    assert "1MWから始め、5→10→20MW" in text
    assert "大型キャンパスだけを唯一の未来にしない" in text


def test_yumori_connects_jhr_esingularity_and_join_form_without_embedding() -> None:
    text = source()
    assert "'/reports/jhr'" in text
    assert "Educational Singularity Lab" in text
    assert "docs.google.com/forms" in text
    assert "embedded=true" not in text
    assert "YUMORI.info / 資料" in text


def test_yumori_truth_boundary_uses_candidate_language() -> None:
    text = source()
    assert "再利用可能性を検討するための概念図" in text
    assert "再生案は成立性を検証する構想" in text
    assert "福井に巨大データセンターが来ることが決まったわけではありません" in text
