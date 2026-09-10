"""Public-content contracts for JHR and the YUMORI live field status."""

from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = MODULE_ROOT / "frontend"
REPORT_PATH = MODULE_ROOT / "jhr" / "reports" / "JHR_001_2026-09_JAPAN_HYPERSCALER_REPORT.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_jhr_001_is_updated_in_place_japanese_first_and_bilingual() -> None:
    report = read(REPORT_PATH)
    page = read(FRONTEND_ROOT / "app" / "reports" / "jhr" / "page.tsx")

    assert "最終更新 2026-09-10" in report
    assert "仙台200MW" in report
    assert "地区計画の変更" in report
    assert report.index("# 日本は") < report.index("# English")
    assert "YUMORI.me" in report and "https://yumori.me/" in report
    assert "YUMORI.info" in report and "https://yumori.info/" in report

    assert "ENGLISH / SECONDARY LANGUAGE" in page
    assert "YUMORI.me / JOIN" in page
    assert "YUMORI.info / 資料" in page
    assert "candidate status, operator intent" in page


def test_live_field_status_has_one_canonical_source_for_public_surfaces() -> None:
    status = read(FRONTEND_ROOT / "content" / "current-field-status.ts")
    ticker = read(FRONTEND_ROOT / "components" / "CampaignTicker.tsx")
    yumori = read(FRONTEND_ROOT / "app" / "yumori" / "page.tsx")

    assert "2026-09-10T09:15:00+09:00" in status
    assert "福井市役所前" in status
    assert "YUMORI Tシャツ" in status
    assert "準備委員会" in status
    assert "currentFieldStatus.tickerJa" in ticker
    assert "currentFieldStatus.detailJa" in yumori
    assert "currentFieldStatus.detailEn" in yumori
    assert "label: 'JHR'" in ticker
    assert "href: '/reports/jhr'" in ticker
