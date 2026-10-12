"""Offline smoke/guard tests for the bounded AI Koban municipal asset pulse."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "ai_koban_official_asset_scan.py"


def test_offline_scan_does_not_access_network_or_promote_assets(tmp_path):
    out = tmp_path / "pulse.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(out)],
        capture_output=True, text=True, check=True, timeout=20,
    )
    assert result.returncode == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["mode"] == "OFFLINE_VALIDATE"
    assert payload["lead_count"] == 7
    assert payload["sources"]
    assert all(x["outcome"] == "NOT_FETCHED_OFFLINE" for x in payload["sources"])


def test_leads_have_distinct_ids_and_official_sources_only():
    content = json.loads((ROOT / "docs" / "AI_KOBAN_REGIONAL_PUBLIC_ASSET_LEADS.json").read_text(encoding="utf-8"))
    leads = content["leads"]
    assert len({x["id"] for x in leads}) == len(leads)
    assert all(x["source_url"].startswith("https://www.city.") for x in leads)
    assert all(x["power_capacity_verified"] is False and x["site_rights_verified"] is False for x in leads)
    assert len([x for x in leads if x["status"] == "CLOSED_2026_ROUND_RECHECK"]) == 2
