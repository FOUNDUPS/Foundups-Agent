from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "frontend" / "app" / "yumori" / "page.tsx"
QR = ROOT / "frontend" / "public" / "YUMORIme-qr-code.png"
PUBLIC_ASSET_README = ROOT / "frontend" / "public" / "README.md"


def source() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_yumori_landing_exists_and_is_japanese_first() -> None:
    text = source()
    assert "YUMORI.me / 湯守" in text
    assert "私は湯守。" in text
    assert "YUMORI.me" in text
    assert "me GUARDIAN!" not in text
    assert "I am a guardian" not in text
    assert "日本の地域を守り、地域のAIをつくる。" not in text
    assert "準備委員会の最初の目標：1,000人" in text


def test_yumori_branding_and_report_link_are_canonical() -> None:
    text = source()
    assert "JOIN YUMORI.me / 湯守になる ↗" in text
    assert "JOIN YUMORI / 湯守になる" not in text
    assert "ジャパン・ハイパースケーラー・レポート（JHR）を読む →" in text
    assert "JAPAN HYPERSCALER REPORTを読む" not in text


def test_yumori_is_pro_community_compute_not_blanket_anti_dc() -> None:
    text = source()
    assert "YUMORI.meはデータセンターそのものに反対する運動ではありません" in text
    assert "地域の学校、大学、農業、病院、自治体、ものづくり、企業" in text
    assert "1MWから始め、地域需要に合わせて5→10→20MW" in text
    assert "地域の知" in text


def test_yumori_remains_the_join_first_three_panel_movement_funnel() -> None:
    text = source()
    why = "01 / なぜ — 何が来るのかを知る"
    what = "02 / 何をする — 解体前に再利用を"
    how = "03 / どう進める — コンピュートを地域再生へ"
    assert text.index(why) < text.index(what) < text.index(how)
    assert text.count("<Join") == 5
    assert "行動 / 1,000 YUMORI.me" in text
    assert "01 / WHY — KNOW WHAT IS COMING" not in text
    assert "02 / WHAT — REUSE BEFORE DEMOLITION" not in text
    assert "03 / HOW — TURN COMPUTE INTO REVITALIZATION" not in text


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


def test_yumori_official_qr_asset_is_canonical_png() -> None:
    assert QR.is_file()
    assert QR.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    contract = PUBLIC_ASSET_README.read_text(encoding="utf-8")
    assert "YUMORIme-qr-code.png" in contract
    assert "https://YUMORI.me" in contract
    assert "official YUMORI.me QR-code asset" in contract
