#!/usr/bin/env python3
"""Integration manifest drift check.

Verifies that the canonical machine-readable ledger
(openclaw_integration_manifest.json) stays aligned with
env surfaces documented in main.py and wre_defaults.env.

Slice: OPENCLAW_INTEGRATION_MANIFEST_LINT_PHASE1
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
MANIFEST_PATH = REPO_ROOT / "modules" / "communication" / "moltbot_bridge" / "config" / "openclaw_integration_manifest.json"
MAIN_PY = REPO_ROOT / "main.py"
WRE_DEFAULTS = REPO_ROOT / "modules" / "infrastructure" / "wre_core" / "config" / "wre_defaults.env"


@pytest.fixture(scope="module")
def manifest():
    assert MANIFEST_PATH.exists(), f"Manifest not found: {MANIFEST_PATH}"
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return data


@pytest.fixture(scope="module")
def integrations(manifest):
    return manifest["integrations"]


@pytest.fixture(scope="module")
def all_manifest_env_keys(integrations):
    """Collect every env key declared across all manifest entries."""
    keys = set()
    for entry in integrations:
        keys.update(entry.get("env_keys", []))
        keys.update(entry.get("secret_keys", []))
    return keys


# -- 1. Schema validity --


class TestManifestSchema:
    """Manifest is valid JSON with expected top-level shape."""

    def test_manifest_is_valid_json(self, manifest):
        assert isinstance(manifest, dict)

    def test_has_schema_version(self, manifest):
        assert "$schema" in manifest

    def test_has_integrations_list(self, manifest):
        assert "integrations" in manifest
        assert isinstance(manifest["integrations"], list)

    def test_integration_count_nonzero(self, integrations):
        assert len(integrations) > 0, "Manifest has zero integrations"


# -- 2. Entry completeness --


REQUIRED_FIELDS = {"name", "type", "owner_module", "status", "default", "env_keys", "secret_keys", "fail_mode"}


class TestEntryCompleteness:
    """Every integration entry has all required fields."""

    def test_all_entries_have_required_fields(self, integrations):
        for entry in integrations:
            missing = REQUIRED_FIELDS - set(entry.keys())
            assert not missing, f"{entry.get('name', '???')}: missing fields {missing}"

    def test_all_entries_have_string_name(self, integrations):
        for entry in integrations:
            assert isinstance(entry["name"], str) and len(entry["name"]) > 0

    def test_env_keys_are_lists(self, integrations):
        for entry in integrations:
            assert isinstance(entry["env_keys"], list), f"{entry['name']}: env_keys not a list"
            assert isinstance(entry["secret_keys"], list), f"{entry['name']}: secret_keys not a list"

    def test_status_is_known(self, integrations):
        allowed = {"landed", "planned", "parked", "removed"}
        for entry in integrations:
            assert entry["status"] in allowed, f"{entry['name']}: unknown status '{entry['status']}'"


# -- 3. Critical env key coverage --
#    These keys are read by main.py at startup via os.getenv().
#    If they exist in main.py, they must appear in the manifest
#    so operators know which integration owns them.


CRITICAL_MAIN_PY_KEYS = {
    "OPENCLAW_CONVERSATION_BACKEND",
    "OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK",
    "OPENCLAW_RESIDENT_ENABLED",
    "OPENCLAW_RESIDENT_AUTOSTART",
    "OPENCLAW_SUPERVISOR_ENABLED",
    "OPENCLAW_DEP_SECURITY_PREFLIGHT",
    "OPENCLAW_DEP_SECURITY_PREFLIGHT_ENFORCED",
    "OPENCLAW_SELF_AUDIT_ENABLED",
    "OPENCLAW_SELF_AUDIT_INTERVAL_SEC",
}


class TestCriticalEnvCoverage:
    """Critical env keys from main.py appear in the manifest."""

    @pytest.mark.parametrize("key", sorted(CRITICAL_MAIN_PY_KEYS))
    def test_critical_key_in_manifest(self, key, all_manifest_env_keys):
        assert key in all_manifest_env_keys, (
            f"main.py reads os.getenv(\"{key}\") but it is not declared "
            f"in any manifest integration entry"
        )


# -- 4. WRE defaults coverage --
#    Keys in wre_defaults.env that start with OPENCLAW_ should
#    have a corresponding manifest entry.


class TestWreDefaultsCoverage:
    """OPENCLAW_* keys in wre_defaults.env appear in the manifest."""

    @pytest.fixture(scope="class")
    def wre_openclaw_keys(self):
        if not WRE_DEFAULTS.exists():
            pytest.skip("wre_defaults.env not found")
        keys = set()
        for line in WRE_DEFAULTS.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k = line.split("=", 1)[0].strip()
            if k.startswith("OPENCLAW_"):
                keys.add(k)
        return keys

    def test_wre_openclaw_keys_in_manifest(self, wre_openclaw_keys, all_manifest_env_keys):
        # Only check the core keys, not every granular sub-flag.
        # Granular flags (TTL, cooldown, etc.) are owned by the same
        # integration as their parent key.
        core_prefixes = {
            "OPENCLAW_DEP_SECURITY_PREFLIGHT",
            "OPENCLAW_SELF_AUDIT_ENABLED",
            "OPENCLAW_SELF_AUDIT_AUTO_FIX",
            "OPENCLAW_SELF_AUDIT_INTERVAL_SEC",
        }
        missing = []
        for k in sorted(wre_openclaw_keys):
            if k in core_prefixes and k not in all_manifest_env_keys:
                missing.append(k)
        assert not missing, f"wre_defaults.env keys not in manifest: {missing}"


# -- 5. OpenRouter module coverage --


class TestOpenRouterCoverage:
    """OpenRouter integration is tracked in manifest."""

    def test_openrouter_entry_exists(self, integrations):
        names = [e["name"] for e in integrations]
        assert "OpenRouter" in names, "OpenRouter integration missing from manifest"

    def test_openrouter_has_key_envs(self, integrations):
        entry = next(e for e in integrations if e["name"] == "OpenRouter")
        expected = {"OPENROUTER_BASE_URL", "OPENROUTER_DEFAULT_MODEL"}
        actual = set(entry["env_keys"])
        missing = expected - actual
        assert not missing, f"OpenRouter missing env_keys: {missing}"

    def test_openrouter_secret_key(self, integrations):
        entry = next(e for e in integrations if e["name"] == "OpenRouter")
        assert "OPENROUTER_API_KEY" in entry["secret_keys"]


# -- 6. No duplicate integration names --


class TestNoDuplicates:

    def test_unique_names(self, integrations):
        names = [e["name"] for e in integrations]
        dupes = [n for n in names if names.count(n) > 1]
        assert not dupes, f"Duplicate integration names: {set(dupes)}"
