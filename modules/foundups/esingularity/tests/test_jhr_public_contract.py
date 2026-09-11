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


def test_jhr_publication_registry_drives_ticker_and_sitemap() -> None:
    registry = read(FRONTEND_ROOT / "content" / "jhr-issues.ts")
    ticker = read(FRONTEND_ROOT / "components" / "CampaignTicker.tsx")
    sitemap = read(FRONTEND_ROOT / "app" / "sitemap.ts")

    assert "getLatestPublishedJhrIssue" in registry
    assert "https://esingularity.ai/reports/jhr" in registry
    assert "status: 'published'" in registry
    assert "heroImage: 'https://esingularity.ai/yumori-inzai-fukui-comparison.webp'" in registry
    assert "latestJhrIssue.tickerJa" in ticker
    assert "latestJhrIssue.href" in ticker
    assert "UPDATE 9/10｜仙台200MW・印西の地区計画・福井の選択肢" not in ticker
    assert "jhrIssues" in sitemap
    assert "issue.href" in sitemap
    assert "new Date(issue.updatedAt)" in sitemap


def test_jhr_is_visibly_promoted_with_existing_comparison_image() -> None:
    layout = read(FRONTEND_ROOT / "app" / "layout.tsx")
    promo = read(FRONTEND_ROOT / "components" / "JhrPromo.tsx")
    report_layout = read(FRONTEND_ROOT / "app" / "reports" / "jhr" / "layout.tsx")
    presentation = read(FRONTEND_ROOT / "components" / "YumoriPresentation.tsx")

    assert "<JhrPromo />" in layout
    assert "issue.heroImage" in promo
    assert "issue.href" in promo
    assert "pathname.startsWith('/reports/jhr')" in promo
    assert "JAPAN HYPERSCALER REPORT" in promo
    assert "3 SIGNALS / まず知ってほしい3点" in report_layout
    assert "概念比較図。福井でこの規模の開発が決定したことを示すものではありません。" in report_layout
    assert "const reportLabels" in presentation
    assert "JAPAN HYPERSCALER REPORTを読む" in presentation
    assert "READ THE JAPAN HYPERSCALER REPORT" in presentation
