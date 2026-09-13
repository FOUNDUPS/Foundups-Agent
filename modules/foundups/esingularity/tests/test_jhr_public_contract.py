"""Public-content contracts for JHR and the YUMORI live field status."""

from pathlib import Path
from datetime import datetime
import re


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


def test_live_field_status_has_one_canonical_source_for_the_campaign_ticker() -> None:
    status = read(FRONTEND_ROOT / "content" / "current-field-status.ts")
    ticker = read(FRONTEND_ROOT / "components" / "CampaignTicker.tsx")

    timestamp = re.search(r"updatedAt: '([^']+)'", status)
    assert timestamp is not None
    assert datetime.fromisoformat(timestamp.group(1)).utcoffset().total_seconds() == 9 * 3600
    for field in ("updatedLabelJa", "locationJa", "tickerJa", "detailJa", "detailEn", "href"):
        assert re.search(rf"{field}: '[^']+'", status)
    assert "currentFieldStatus.href" in ticker
    project = read(FRONTEND_ROOT / "app" / "page.tsx")
    movement = read(FRONTEND_ROOT / "app" / "yumori" / "page.tsx")
    assert project.count("<CampaignTicker />") == 1
    assert movement.count("<CampaignTicker movement />") == 1
    assert "../../components/CampaignTicker" in movement
    assert "https://esingularity.ai/${action.href}" in ticker
    assert "currentFieldStatus.tickerJa" in ticker
    assert "label: 'JHR'" in ticker
    assert "href: '/reports/jhr'" in ticker


def test_jhr_is_visibly_reachable_across_esingularity_and_yumori_panels() -> None:
    project_page = read(FRONTEND_ROOT / "app" / "page.tsx")
    movement_page = read(FRONTEND_ROOT / "app" / "yumori" / "page.tsx")

    assert project_page.count('href="/reports/jhr') >= 3
    assert "JHR・最新レポート" in project_page
    assert "const JHR_URL = '/reports/jhr'" in movement_page
    assert "JAPAN HYPERSCALER REPORTを読む" in movement_page
