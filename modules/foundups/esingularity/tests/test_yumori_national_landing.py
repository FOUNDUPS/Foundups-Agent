from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "frontend" / "app" / "yumori" / "page.tsx"


def source() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_yumori_landing_exists_and_is_japanese_first() -> None:
    text = source()
    assert "YUMORI.me / 湯守" in text
    assert "I am a guardian" in text
    assert "地域を守り、地域のAIをつくる" in text


def test_yumori_is_pro_community_compute_not_blanket_anti_dc() -> None:
    text = source()
    assert "YUMORIは「データセンター反対」ではありません" in text
    assert "計算力を、まず地域へ" in text
    assert "オープンソース" in text
    assert "1MW → 5MW → 10MW → 20MW" in text


def test_yumori_connects_jhr_esingularity_and_join_form() -> None:
    text = source()
    assert "'/reports/jhr'" in text
    assert "Educational Singularity Lab" in text
    assert "docs.google.com/forms" in text
    assert "embedded=true" in text


def test_yumori_truth_boundary_uses_candidate_language() -> None:
    text = source()
    assert "最初の実証候補" in text
    assert "再生投資へ転換できるかを検証" in text
