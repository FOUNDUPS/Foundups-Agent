"""Public-content contracts for JHR and the YUMORI live field status."""

from pathlib import Path
from datetime import datetime
import json
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
    status = json.loads(read(FRONTEND_ROOT / "content" / "current-field-status.json"))
    ticker = read(FRONTEND_ROOT / "components" / "CampaignTicker.tsx")

    assert status["schemaVersion"] == 1
    assert datetime.fromisoformat(status["updatedAt"]).utcoffset().total_seconds() == 9 * 3600
    assert datetime.fromisoformat(status["expiresAt"]) > datetime.fromisoformat(status["updatedAt"])
    for field in ("label", "message"):
        assert set(status[field]) == {"ja", "en", "pt"}
        assert all(status[field][language] for language in ("ja", "en", "pt"))
    assert status["href"].startswith("https://")
    assert "current-field-status.json" in ticker
    project = read(FRONTEND_ROOT / "app" / "page.tsx")
    movement = read(FRONTEND_ROOT / "app" / "yumori" / "page.tsx")
    assert project.count("<CampaignTicker />") == 1
    assert movement.count("<CampaignTicker movement />") == 1
    assert "../../components/CampaignTicker" in movement
    assert "https://esingularity.ai/${action.href}" in ticker
    assert "fieldStatus.message" in ticker
    assert "label: { ja: 'JHR', en: 'JHR', pt: 'JHR' }" in ticker
    assert "href: '/reports/jhr#jhr-002'" in ticker
    assert "https://yumori.me/vote-no#council" in ticker
    assert "https://yumori.me/vote-no#mayor" in ticker
    assert "Monkとつながる" not in ticker
    assert "width <= 600 ? 10 : width <= 1200 ? 20 : 32" in ticker


def test_runtime_field_status_feed_is_multilingual_bounded_and_fail_safe() -> None:
    ticker = read(FRONTEND_ROOT / "components" / "CampaignTicker.tsx")

    assert "refs/heads/live/yumori-field-status" in ticker
    assert "LIVE_FIELD_STATUS_POLL_MS = 60_000" in ticker
    assert "cache: 'no-store'" in ticker
    assert "payload.visible !== true" in ticker
    assert "now >= expiresAt" in ticker
    assert "['ja', 'en', 'pt']" in ticker
    assert "ALLOWED_STATUS_ORIGINS" in ticker
    assert "parseFieldStatus(compiledFieldStatus)" in ticker
    assert "fallbackAction" in ticker
    assert "data-yumori-localized" in ticker


def test_vote_no_public_record_is_reachable_and_privacy_bounded() -> None:
    page = read(FRONTEND_ROOT / "app" / "vote-no" / "page.tsx")
    messages = read(FRONTEND_ROOT / "content" / "civic-messages.ts")

    assert "設立準備委員会から福井市議会へ" in page
    assert "設立準備委員会から福井市長へ" in page
    assert "履歴注記" in page and "その後撤回" in page
    assert "gikai@city.fukui.lg.jp" in page
    assert "BCC" in page
    assert "60日間は可逆です。解体は不可逆です。" in messages
    assert "YUMORI.me 設立準備委員会" in messages


def test_phone_ticker_is_bottom_docked_and_swipeable_when_stopped() -> None:
    css = read(FRONTEND_ROOT / "app" / "globals.css")

    assert "Phone ticker: thumb-reachable bottom dock" in css
    assert "position:fixed!important" in css
    assert "bottom:0" in css
    assert "env(safe-area-inset-bottom)" in css
    assert "touch-action:pan-x" in css
    assert "scroll-snap-type:x proximity" in css


def test_jhr_is_visibly_reachable_across_esingularity_and_yumori_panels() -> None:
    project_page = read(FRONTEND_ROOT / "app" / "page.tsx")
    movement_page = read(FRONTEND_ROOT / "app" / "yumori" / "page.tsx")

    assert project_page.count('href="/reports/jhr') >= 3
    assert "JHR・最新レポート" in project_page
    assert "const JHR_URL = '/reports/jhr'" in movement_page
    assert "JAPAN HYPERSCALER REPORTを読む" in movement_page
