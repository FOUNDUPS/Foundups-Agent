from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "frontend" / "app" / "yumori" / "page.tsx"


def source() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_yumori_landing_exists_and_is_japanese_first() -> None:
    text = source()
    assert "YUMORI.me / 湯守" in text
    assert "I am a guardian" in text
    assert "日本の地域を守り、地域のAIをつくる。" in text
    assert "準備委員会の最初の目標：1,000人" in text


def test_yumori_is_pro_community_compute_not_blanket_anti_dc() -> None:
    text = source()
    assert "YUMORIはデータセンターそのものに反対する運動ではありません" in text
    assert "地域の学校、大学、農業、病院、自治体、ものづくり、企業" in text
    assert "1MWから始め、地域需要に合わせて5→10→20MW" in text
    assert "地域の知" in text


def test_yumori_remains_the_join_first_three_panel_movement_funnel() -> None:
    text = source()
    why = "01 / WHY — KNOW WHAT IS COMING"
    what = "02 / WHAT — REUSE BEFORE DEMOLITION"
    how = "03 / HOW — TURN COMPUTE INTO REVITALIZATION"
    assert text.index(why) < text.index(what) < text.index(how)
    assert text.count("<Join") == 5
    assert "ACT / 1,000 YUMORI" in text


def test_yumori_connects_jhr_esingularity_and_join_form_without_embedding() -> None:
    text = source()
    assert "'/reports/jhr'" in text
    assert "Educational Singularity Lab" in text
    assert "docs.google.com/forms" in text
    assert "embedded=true" not in text
    assert "eSingularity / 福井の実証を見る" in text


def test_yumori_truth_boundary_uses_candidate_language() -> None:
    text = source()
    assert "成立する場所では" in text
    assert "技術検証する" in text
    assert "構想です" in text
