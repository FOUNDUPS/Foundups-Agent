"""Contract tests for the eSingularity FoundUp migration."""

import json
from pathlib import Path

from modules.foundups.agent.src.foundup_manifest_validator import validate_manifest_file


MODULE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = MODULE_ROOT / "foundup_manifest.json"
REGISTRY_PATH = REPO_ROOT / "foundups" / "foundup_registry.json"
FRONTEND_ROOT = MODULE_ROOT / "frontend"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_manifest_passes_shared_build_contract_validator() -> None:
    result = validate_manifest_file(MANIFEST_PATH)
    assert result.ok, result.errors


def test_wsp104_identity_is_stable_and_isolated() -> None:
    manifest = load_json(MANIFEST_PATH)
    assert manifest["foundup_id"] == "esingularity_001"
    assert manifest["routing_prefix"] == "/f/esingularity_001"
    assert manifest["data_namespace"] == "idb_esingularity_001"


def test_public_campaign_is_not_invite_gated() -> None:
    manifest = load_json(MANIFEST_PATH)
    assert manifest["entry_url"] == "https://esingularity.ai/"
    assert manifest["required_subscription_tier"] == "free"
    assert manifest["is_invite_only"] is False


def test_no_token_is_invented_for_the_campaign() -> None:
    manifest = load_json(MANIFEST_PATH)
    assert not manifest.get("token_symbol")

    registry = load_json(REGISTRY_PATH)
    entry = next(item for item in registry["entities"] if item["foundup_id"] == "esingularity_001")
    assert entry["token_status"] == "TOKEN_DEFERRED"
    assert entry["token_symbol"] is None


def test_registry_matches_manifest_and_module_location() -> None:
    manifest = load_json(MANIFEST_PATH)
    registry = load_json(REGISTRY_PATH)
    entry = next(item for item in registry["entities"] if item["foundup_id"] == manifest["foundup_id"])
    assert entry["module_path"] == "modules/foundups/esingularity"
    assert entry["manifest_path"] == "modules/foundups/esingularity/foundup_manifest.json"
    assert entry["public_url_or_route"] == manifest["entry_url"]


def test_sites_configuration_and_primary_routes_are_present() -> None:
    hosting = load_json(FRONTEND_ROOT / ".openai" / "hosting.json")
    package = load_json(FRONTEND_ROOT / "package.json")
    assert hosting["project_id"] == "appgprj_6a917b21b1a4819181a61738ed5274a5"
    assert hosting["d1"] == "DB"
    assert package["scripts"]["build"] == "vinext build"
    assert (FRONTEND_ROOT / "app" / "page.tsx").is_file()
    assert (FRONTEND_ROOT / "app" / "future" / "page.tsx").is_file()
    assert (FRONTEND_ROOT / "app" / "team" / "page.tsx").is_file()
    for required_library in ("db.ts", "event.ts", "i18n.ts", "project-data.ts", "team.ts"):
        assert (FRONTEND_ROOT / "lib" / required_library).is_file()
