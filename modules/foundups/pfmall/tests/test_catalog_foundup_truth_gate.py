"""
Catalog FoundUp Truth Gate — WSP 97 Validation

Every entry in mall-video-catalog.json is a FoundUp.
Some FoundUps also have bound tenant manifests (foundup_manifest.json).
The catalog needs its own validator and must join against manifests when present.

Truth labels:
  BOUND_TENANT:       Has catalog entry + foundup_manifest.json + routing_prefix + data_namespace
  DISCOVERABLE_ONLY:  Has catalog entry, no manifest binding required

This test module enforces:
  - All catalog entries are valid FoundUps with required fields
  - Category values match VALID_CATEGORIES (shell_core.py)
  - Lifecycle stages match VALID_STAGES (shell_core.py)
  - Launch readiness matches VALID_READINESS (shell_core.py)
  - Bound tenants have matching manifests with consistent data
  - Discoverable-only FoundUps pass without manifests

Slice: PFMALL-CATALOG-FOUNDUP-TRUTH-GATE
WSP: 97 (Truth), 104 (Namespace)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from modules.foundups.pfmall.shell_core import (
    VALID_CATEGORIES,
    VALID_READINESS,
    VALID_STAGES,
    VALID_TIERS,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[4]
CATALOG_PATH = REPO_ROOT / "public" / "member" / "mall-video-catalog.json"
FOUNDUPS_ROOT = REPO_ROOT / "modules" / "foundups"


@pytest.fixture
def catalog() -> list[dict[str, Any]]:
    """Load mall-video-catalog.json."""
    assert CATALOG_PATH.exists(), f"Catalog not found: {CATALOG_PATH}"
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def manifests() -> dict[str, dict[str, Any]]:
    """Load all foundup_manifest.json files keyed by foundup_id."""
    result: dict[str, dict[str, Any]] = {}
    for d in FOUNDUPS_ROOT.iterdir():
        if not d.is_dir():
            continue
        manifest_path = d / "foundup_manifest.json"
        if manifest_path.exists():
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            fid = data.get("foundup_id")
            if fid:
                result[fid] = data
    return result


def _bound_entries(catalog: list[dict]) -> list[dict]:
    """Return catalog entries that have routing_prefix and data_namespace."""
    return [e for e in catalog if e.get("routing_prefix") and e.get("data_namespace")]


def _discoverable_entries(catalog: list[dict]) -> list[dict]:
    """Return catalog entries without full binding."""
    return [e for e in catalog if not e.get("routing_prefix") or not e.get("data_namespace")]


# ---------------------------------------------------------------------------
# Every catalog entry is a FoundUp
# ---------------------------------------------------------------------------

class TestEveryEntryIsAFoundUp:
    """Every catalog entry must have the fields that make it a FoundUp."""

    def test_all_entries_have_foundup_id(self, catalog):
        for entry in catalog:
            assert "foundup_id" in entry and entry["foundup_id"], (
                f"Entry missing foundup_id: {entry.get('title', '?')}"
            )

    def test_foundup_ids_are_unique(self, catalog):
        ids = [e["foundup_id"] for e in catalog]
        duplicates = [fid for fid in ids if ids.count(fid) > 1]
        assert not duplicates, f"Duplicate foundup_ids: {set(duplicates)}"

    def test_all_entries_have_category(self, catalog):
        for entry in catalog:
            assert "category" in entry and entry["category"], (
                f"{entry['foundup_id']}: missing category"
            )

    def test_all_entries_have_lifecycle_stage(self, catalog):
        for entry in catalog:
            assert "lifecycle_stage" in entry and entry["lifecycle_stage"], (
                f"{entry['foundup_id']}: missing lifecycle_stage"
            )

    def test_all_entries_have_launch_readiness(self, catalog):
        for entry in catalog:
            assert "launch_readiness" in entry and entry["launch_readiness"], (
                f"{entry['foundup_id']}: missing launch_readiness"
            )

    def test_all_entries_have_tier(self, catalog):
        for entry in catalog:
            assert "tier" in entry and entry["tier"], (
                f"{entry['foundup_id']}: missing tier"
            )


# ---------------------------------------------------------------------------
# Category validation — no drift allowed
# ---------------------------------------------------------------------------

class TestCategoryEnum:
    """Category values must match VALID_CATEGORIES from shell_core.py."""

    def test_all_categories_are_valid(self, catalog):
        violations = []
        for entry in catalog:
            cat = entry.get("category", "")
            if cat not in VALID_CATEGORIES:
                violations.append(f"{entry['foundup_id']}: '{cat}'")
        assert not violations, (
            f"Invalid categories (not in VALID_CATEGORIES): {violations}\n"
            f"Valid: {sorted(VALID_CATEGORIES)}"
        )

    def test_catalog_does_not_use_unknown_categories(self, catalog):
        """Catch new categories that haven't been added to VALID_CATEGORIES."""
        catalog_cats = {e.get("category") for e in catalog}
        unknown = catalog_cats - VALID_CATEGORIES
        assert not unknown, (
            f"Catalog uses categories not in VALID_CATEGORIES: {unknown}. "
            "Add them to shell_core.py VALID_CATEGORIES."
        )


# ---------------------------------------------------------------------------
# Lifecycle stage validation
# ---------------------------------------------------------------------------

class TestLifecycleStageEnum:
    """Lifecycle stages must match VALID_STAGES from shell_core.py."""

    def test_all_lifecycle_stages_are_valid(self, catalog):
        violations = []
        for entry in catalog:
            stage = entry.get("lifecycle_stage", "")
            if stage not in VALID_STAGES:
                violations.append(f"{entry['foundup_id']}: '{stage}'")
        assert not violations, (
            f"Invalid lifecycle_stages (not in VALID_STAGES): {violations}\n"
            f"Valid: {sorted(VALID_STAGES)}"
        )


# ---------------------------------------------------------------------------
# Launch readiness validation
# ---------------------------------------------------------------------------

class TestLaunchReadinessEnum:
    """Launch readiness must match VALID_READINESS from shell_core.py."""

    def test_all_launch_readiness_are_valid(self, catalog):
        violations = []
        for entry in catalog:
            lr = entry.get("launch_readiness", "")
            if lr not in VALID_READINESS:
                violations.append(f"{entry['foundup_id']}: '{lr}'")
        assert not violations, (
            f"Invalid launch_readiness (not in VALID_READINESS): {violations}\n"
            f"Valid: {sorted(VALID_READINESS)}"
        )


# ---------------------------------------------------------------------------
# Tier validation
# ---------------------------------------------------------------------------

class TestTierEnum:
    """Tier must match VALID_TIERS from shell_core.py."""

    def test_all_tiers_are_valid(self, catalog):
        violations = []
        for entry in catalog:
            tier = entry.get("tier", "")
            if tier not in VALID_TIERS:
                violations.append(f"{entry['foundup_id']}: '{tier}'")
        assert not violations, (
            f"Invalid tiers (not in VALID_TIERS): {violations}\n"
            f"Valid: {sorted(VALID_TIERS)}"
        )


# ---------------------------------------------------------------------------
# Bound tenant validation
# ---------------------------------------------------------------------------

class TestBoundTenants:
    """Bound FoundUps (routing_prefix + data_namespace) must have matching manifests."""

    def test_bound_entries_exist(self, catalog):
        """At least one bound tenant should exist."""
        bound = _bound_entries(catalog)
        assert len(bound) >= 1, "No bound tenants found in catalog"

    def test_bound_entry_has_manifest(self, catalog, manifests):
        """Every bound catalog entry must have a corresponding manifest file."""
        violations = []
        for entry in _bound_entries(catalog):
            fid = entry["foundup_id"]
            if fid not in manifests:
                violations.append(f"{fid}: bound in catalog but no foundup_manifest.json")
        assert not violations, (
            f"Bound FoundUps missing manifest: {violations}. "
            "Create modules/foundups/{name}/foundup_manifest.json."
        )

    def test_bound_entry_routing_prefix_matches_manifest(self, catalog, manifests):
        """Bound entry routing_prefix must match manifest routing_prefix."""
        violations = []
        for entry in _bound_entries(catalog):
            fid = entry["foundup_id"]
            if fid in manifests:
                cat_rp = entry.get("routing_prefix")
                man_rp = manifests[fid].get("routing_prefix")
                if cat_rp and man_rp and cat_rp != man_rp:
                    violations.append(f"{fid}: catalog='{cat_rp}' vs manifest='{man_rp}'")
        assert not violations, f"routing_prefix mismatch: {violations}"

    def test_bound_entry_data_namespace_matches_manifest(self, catalog, manifests):
        """Bound entry data_namespace must match manifest data_namespace."""
        violations = []
        for entry in _bound_entries(catalog):
            fid = entry["foundup_id"]
            if fid in manifests:
                cat_ns = entry.get("data_namespace")
                man_ns = manifests[fid].get("data_namespace")
                if cat_ns and man_ns and cat_ns != man_ns:
                    violations.append(f"{fid}: catalog='{cat_ns}' vs manifest='{man_ns}'")
        assert not violations, f"data_namespace mismatch: {violations}"

    def test_bound_entry_launch_readiness_not_discoverable_only(self, catalog):
        """Bound tenants should not have launch_readiness=discoverable_only."""
        violations = []
        for entry in _bound_entries(catalog):
            if entry.get("launch_readiness") == "discoverable_only":
                violations.append(entry["foundup_id"])
        assert not violations, (
            f"Bound tenants with discoverable_only readiness: {violations}. "
            "Bound tenants should be 'ready' or 'conditional'."
        )


# ---------------------------------------------------------------------------
# Discoverable-only validation
# ---------------------------------------------------------------------------

class TestDiscoverableOnly:
    """Discoverable-only FoundUps are valid without manifests."""

    def test_discoverable_entries_exist(self, catalog):
        """Discoverable-only entries should exist."""
        disc = _discoverable_entries(catalog)
        assert len(disc) >= 1, "No discoverable-only FoundUps found"

    def test_discoverable_entries_do_not_require_manifest(self, catalog, manifests):
        """Discoverable-only entries must NOT fail for lacking a manifest."""
        for entry in _discoverable_entries(catalog):
            fid = entry["foundup_id"]
            # This test PASSES regardless of whether manifest exists.
            # The point is: no manifest is OK for discoverable-only.
            assert entry.get("launch_readiness") == "discoverable_only" or fid in manifests, (
                f"{fid}: not discoverable_only and has no manifest — ambiguous state"
            )

    def test_discoverable_entries_have_no_routing(self, catalog):
        """Discoverable-only entries should not claim routing_prefix."""
        violations = []
        for entry in _discoverable_entries(catalog):
            if entry.get("routing_prefix"):
                violations.append(f"{entry['foundup_id']}: has routing_prefix but missing data_namespace")
        # This catches partial binding (route without namespace or vice versa)
        assert not violations, f"Partial binding found: {violations}"


# ---------------------------------------------------------------------------
# Truth labels
# ---------------------------------------------------------------------------

class TestTruthLabels:
    """Verify WSP 97 truth classification for all catalog entries."""

    def test_every_entry_classifiable(self, catalog):
        """Every entry must be either BOUND_TENANT or DISCOVERABLE_ONLY."""
        for entry in catalog:
            fid = entry["foundup_id"]
            has_route = bool(entry.get("routing_prefix"))
            has_ns = bool(entry.get("data_namespace"))
            bound = has_route and has_ns
            discoverable = not has_route and not has_ns

            assert bound or discoverable, (
                f"{fid}: partial binding (route={has_route}, namespace={has_ns}). "
                "Must be fully bound or fully unbound."
            )

    def test_bound_tenant_count(self, catalog):
        """Verify expected bound tenant count."""
        bound = _bound_entries(catalog)
        bound_ids = sorted(e["foundup_id"] for e in bound)
        # At least gotjunk_001 and kosei
        assert "gotjunk_001" in bound_ids, "gotjunk_001 must be a bound tenant"
        assert "kosei" in bound_ids, "kosei must be a bound tenant"

    def test_discoverable_only_count(self, catalog):
        """Verify discoverable-only count is majority."""
        disc = _discoverable_entries(catalog)
        total = len(catalog)
        assert len(disc) >= total // 2, (
            f"Expected majority discoverable-only, got {len(disc)}/{total}"
        )


# ---------------------------------------------------------------------------
# Regression guards
# ---------------------------------------------------------------------------

class TestRegressionGuards:
    """Catch common drift patterns discovered during reconciliation."""

    def test_no_angel_ultimate_tier(self, catalog):
        """Catch stale tier values from old spec."""
        for entry in catalog:
            tier = entry.get("tier", "")
            assert tier not in ("angel", "ultimate"), (
                f"{entry['foundup_id']}: uses deprecated tier '{tier}'"
            )

    def test_foundup_id_is_slug_not_hash(self, catalog):
        """foundup_id should be human-readable slug, not SHA256 hash."""
        import re
        sha256_pattern = re.compile(r"^[a-f0-9]{16,64}$")
        for entry in catalog:
            fid = entry["foundup_id"]
            assert not sha256_pattern.match(fid), (
                f"{fid}: looks like a hash — foundup_id should be human-readable slug"
            )

    def test_catalog_count_minimum(self, catalog):
        """Catalog should have at least 13 FoundUps (current truth)."""
        assert len(catalog) >= 13, (
            f"Expected at least 13 FoundUps, got {len(catalog)}. "
            "Did someone remove entries?"
        )
