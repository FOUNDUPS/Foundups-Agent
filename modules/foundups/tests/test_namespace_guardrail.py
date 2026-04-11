"""
Namespace Guardrail Validator - WSP 104 Enforcement

Validates FoundUp namespace rules to ensure safe scaling to 100+ tenants:
1. Namespace uniqueness (foundup_id, routing_prefix, data_namespace)
2. Canonical route shape (/f/{foundup_id})
3. Catalog/manifest consistency
4. No root sprawl rejection

WSP 104: FoundUp Route Namespace and Tenant Isolation Protocol
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

# Canonical route pattern: /f/{foundup_id}
CANONICAL_ROUTE_PATTERN = re.compile(r"^/f/[a-z0-9_]+$")

# Data namespace pattern: idb_{foundup_id}
DATA_NAMESPACE_PATTERN = re.compile(r"^idb_[a-z0-9_]+$")

# Reserved root paths that FoundUps must NOT claim
RESERVED_ROOT_PATHS = frozenset({
    "/member", "/foundups", "/media", "/f", "/api", "/admin",
    "/assets", "/static", "/js", "/css", "/images", "/public"
})


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _foundups_root() -> Path:
    return _repo_root() / "modules" / "foundups"


def _load_catalog() -> list[dict[str, Any]]:
    """Load mall-video-catalog.json as array."""
    catalog_path = _repo_root() / "public" / "member" / "mall-video-catalog.json"
    if not catalog_path.exists():
        return []
    with open(catalog_path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("items", [])


def _load_manifests() -> dict[str, dict[str, Any]]:
    """Load all foundup_manifest.json files keyed by foundup_id."""
    manifests: dict[str, dict[str, Any]] = {}
    for d in _foundups_root().iterdir():
        if not d.is_dir():
            continue
        manifest_path = d / "foundup_manifest.json"
        if manifest_path.exists():
            with open(manifest_path, encoding="utf-8") as f:
                data = json.load(f)
            fid = data.get("foundup_id")
            if fid:
                manifests[fid] = data
    return manifests


def _get_catalog_entries_with_routing() -> list[dict[str, Any]]:
    """Return catalog entries that have routing_prefix set."""
    catalog = _load_catalog()
    return [e for e in catalog if e.get("routing_prefix")]


def _get_manifests_with_routing() -> list[tuple[str, dict[str, Any]]]:
    """Return (foundup_id, manifest) tuples for manifests with routing_prefix."""
    manifests = _load_manifests()
    return [(fid, m) for fid, m in manifests.items() if m.get("routing_prefix")]


class TestNamespaceUniqueness:
    """Enforce globally unique namespaces across all FoundUps (catalog + manifests)."""

    def test_foundup_ids_unique_in_catalog(self):
        """No duplicate foundup_id values in catalog."""
        catalog = _load_catalog()
        ids = [e.get("foundup_id") for e in catalog if e.get("foundup_id")]
        duplicates = [fid for fid in ids if ids.count(fid) > 1]
        assert not duplicates, f"Duplicate foundup_ids in catalog: {set(duplicates)}"

    def test_routing_prefixes_unique_globally(self):
        """No duplicate routing_prefix across catalog AND manifests."""
        # Collect all routing_prefix values from both sources
        all_prefixes: list[tuple[str, str, str]] = []  # (prefix, source, foundup_id)

        for e in _get_catalog_entries_with_routing():
            all_prefixes.append((e["routing_prefix"], "catalog", e.get("foundup_id", "?")))

        for fid, m in _get_manifests_with_routing():
            all_prefixes.append((m["routing_prefix"], "manifest", fid))

        # Check for duplicates (same prefix from different foundup_ids)
        prefix_to_sources: dict[str, list[str]] = {}
        for prefix, source, fid in all_prefixes:
            key = f"{source}:{fid}"
            prefix_to_sources.setdefault(prefix, []).append(key)

        violations = []
        for prefix, sources in prefix_to_sources.items():
            # Dedupe by foundup_id (catalog and manifest for same foundup is OK)
            unique_fids = {s.split(":")[1] for s in sources}
            if len(unique_fids) > 1:
                violations.append(f"{prefix} claimed by: {sources}")

        assert not violations, f"Duplicate routing_prefixes: {violations}"

    def test_data_namespaces_unique_globally(self):
        """No duplicate data_namespace across catalog AND manifests."""
        all_namespaces: list[tuple[str, str, str]] = []  # (namespace, source, foundup_id)

        catalog = _load_catalog()
        for e in catalog:
            ns = e.get("data_namespace")
            if ns:
                all_namespaces.append((ns, "catalog", e.get("foundup_id", "?")))

        manifests = _load_manifests()
        for fid, m in manifests.items():
            ns = m.get("data_namespace")
            if ns:
                all_namespaces.append((ns, "manifest", fid))

        # Check for duplicates (same namespace from different foundup_ids)
        ns_to_sources: dict[str, list[str]] = {}
        for ns, source, fid in all_namespaces:
            key = f"{source}:{fid}"
            ns_to_sources.setdefault(ns, []).append(key)

        violations = []
        for ns, sources in ns_to_sources.items():
            unique_fids = {s.split(":")[1] for s in sources}
            if len(unique_fids) > 1:
                violations.append(f"{ns} claimed by: {sources}")

        assert not violations, f"Duplicate data_namespaces: {violations}"

    def test_foundup_ids_unique_in_manifests(self):
        """No duplicate foundup_id across manifest files."""
        seen: dict[str, Path] = {}
        for d in _foundups_root().iterdir():
            if not d.is_dir():
                continue
            manifest_path = d / "foundup_manifest.json"
            if manifest_path.exists():
                with open(manifest_path, encoding="utf-8") as f:
                    data = json.load(f)
                fid = data.get("foundup_id")
                if fid:
                    if fid in seen:
                        pytest.fail(f"Duplicate foundup_id '{fid}' in {manifest_path} and {seen[fid]}")
                    seen[fid] = manifest_path


class TestCanonicalRouteShape:
    """Enforce /f/{foundup_id} canonical route structure (catalog + manifests)."""

    def test_catalog_routing_prefix_matches_canonical_pattern(self):
        """Catalog routing_prefix values must match /f/{foundup_id} pattern."""
        entries = _get_catalog_entries_with_routing()
        violations = []
        for e in entries:
            prefix = e["routing_prefix"]
            if not CANONICAL_ROUTE_PATTERN.match(prefix):
                violations.append(f"catalog:{e.get('foundup_id')}: {prefix}")
        assert not violations, f"Non-canonical routing_prefix in catalog: {violations}"

    def test_manifest_routing_prefix_matches_canonical_pattern(self):
        """Manifest routing_prefix values must match /f/{foundup_id} pattern."""
        violations = []
        for fid, m in _get_manifests_with_routing():
            prefix = m["routing_prefix"]
            if not CANONICAL_ROUTE_PATTERN.match(prefix):
                violations.append(f"manifest:{fid}: {prefix}")
        assert not violations, f"Non-canonical routing_prefix in manifests: {violations}"

    def test_catalog_routing_prefix_contains_foundup_id(self):
        """Catalog routing_prefix must contain the foundup_id."""
        entries = _get_catalog_entries_with_routing()
        violations = []
        for e in entries:
            fid = e.get("foundup_id", "")
            prefix = e["routing_prefix"]
            expected = f"/f/{fid}"
            if prefix != expected:
                violations.append(f"catalog:{fid}: got {prefix}, expected {expected}")
        assert not violations, f"routing_prefix mismatch in catalog: {violations}"

    def test_manifest_routing_prefix_contains_foundup_id(self):
        """Manifest routing_prefix must contain the foundup_id."""
        violations = []
        for fid, m in _get_manifests_with_routing():
            prefix = m["routing_prefix"]
            expected = f"/f/{fid}"
            if prefix != expected:
                violations.append(f"manifest:{fid}: got {prefix}, expected {expected}")
        assert not violations, f"routing_prefix mismatch in manifests: {violations}"

    def test_catalog_data_namespace_matches_pattern(self):
        """Catalog data_namespace must match idb_{foundup_id} pattern."""
        catalog = _load_catalog()
        violations = []
        for e in catalog:
            ns = e.get("data_namespace")
            if ns and not DATA_NAMESPACE_PATTERN.match(ns):
                violations.append(f"catalog:{e.get('foundup_id')}: {ns}")
        assert not violations, f"Non-canonical data_namespace in catalog: {violations}"

    def test_manifest_data_namespace_matches_pattern(self):
        """Manifest data_namespace must match idb_{foundup_id} pattern."""
        manifests = _load_manifests()
        violations = []
        for fid, m in manifests.items():
            ns = m.get("data_namespace")
            if ns and not DATA_NAMESPACE_PATTERN.match(ns):
                violations.append(f"manifest:{fid}: {ns}")
        assert not violations, f"Non-canonical data_namespace in manifests: {violations}"

    def test_catalog_data_namespace_contains_foundup_id(self):
        """Catalog data_namespace must contain the foundup_id."""
        catalog = _load_catalog()
        violations = []
        for e in catalog:
            fid = e.get("foundup_id", "")
            ns = e.get("data_namespace")
            if ns:
                expected = f"idb_{fid}"
                if ns != expected:
                    violations.append(f"catalog:{fid}: got {ns}, expected {expected}")
        assert not violations, f"data_namespace mismatch in catalog: {violations}"

    def test_manifest_data_namespace_contains_foundup_id(self):
        """Manifest data_namespace must contain the foundup_id."""
        manifests = _load_manifests()
        violations = []
        for fid, m in manifests.items():
            ns = m.get("data_namespace")
            if ns:
                expected = f"idb_{fid}"
                if ns != expected:
                    violations.append(f"manifest:{fid}: got {ns}, expected {expected}")
        assert not violations, f"data_namespace mismatch in manifests: {violations}"


class TestCatalogManifestConsistency:
    """Ensure catalog entries and manifest files are consistent."""

    def test_manifest_foundup_id_matches_catalog(self):
        """Manifest foundup_id must match corresponding catalog entry."""
        manifests = _load_manifests()
        catalog = _load_catalog()
        catalog_ids = {e.get("foundup_id") for e in catalog}

        for fid, manifest in manifests.items():
            if fid in catalog_ids:
                # Manifest exists and is in catalog - check consistency
                catalog_entry = next(e for e in catalog if e.get("foundup_id") == fid)

                # Check routing_prefix consistency
                manifest_prefix = manifest.get("routing_prefix")
                catalog_prefix = catalog_entry.get("routing_prefix")
                if manifest_prefix and catalog_prefix:
                    assert manifest_prefix == catalog_prefix, \
                        f"{fid}: manifest routing_prefix '{manifest_prefix}' != catalog '{catalog_prefix}'"

                # Check data_namespace consistency
                manifest_ns = manifest.get("data_namespace")
                catalog_ns = catalog_entry.get("data_namespace")
                if manifest_ns and catalog_ns:
                    assert manifest_ns == catalog_ns, \
                        f"{fid}: manifest data_namespace '{manifest_ns}' != catalog '{catalog_ns}'"

    def test_manifest_entry_url_matches_catalog(self):
        """Manifest entry_url must match catalog entry_url when both exist."""
        manifests = _load_manifests()
        catalog = _load_catalog()

        for fid, manifest in manifests.items():
            catalog_entry = next((e for e in catalog if e.get("foundup_id") == fid), None)
            if catalog_entry:
                manifest_url = manifest.get("entry_url")
                catalog_url = catalog_entry.get("entry_url")
                if manifest_url and catalog_url:
                    assert manifest_url == catalog_url, \
                        f"{fid}: manifest entry_url '{manifest_url}' != catalog '{catalog_url}'"


class TestNoRootSprawl:
    """Prevent FoundUps from claiming reserved root paths (catalog + manifests)."""

    def test_catalog_routing_prefix_not_reserved_root(self):
        """Catalog routing_prefix must not be a reserved root path."""
        entries = _get_catalog_entries_with_routing()
        violations = []
        for e in entries:
            prefix = e["routing_prefix"]
            for reserved in RESERVED_ROOT_PATHS:
                if prefix == reserved or (prefix.startswith(reserved + "/") and reserved != "/f"):
                    violations.append(f"catalog:{e.get('foundup_id')}: {prefix} conflicts with {reserved}")
        assert not violations, f"Root sprawl in catalog: {violations}"

    def test_manifest_routing_prefix_not_reserved_root(self):
        """Manifest routing_prefix must not be a reserved root path."""
        violations = []
        for fid, m in _get_manifests_with_routing():
            prefix = m["routing_prefix"]
            for reserved in RESERVED_ROOT_PATHS:
                if prefix == reserved or (prefix.startswith(reserved + "/") and reserved != "/f"):
                    violations.append(f"manifest:{fid}: {prefix} conflicts with {reserved}")
        assert not violations, f"Root sprawl in manifests: {violations}"

    def test_catalog_no_root_level_routing_prefix(self):
        """Catalog routing_prefix must not be a single segment (root level)."""
        entries = _get_catalog_entries_with_routing()
        violations = []
        for e in entries:
            prefix = e["routing_prefix"]
            segments = [s for s in prefix.split("/") if s]
            if len(segments) < 2:
                violations.append(f"catalog:{e.get('foundup_id')}: {prefix} is root-level")
        assert not violations, f"Root-level routing in catalog: {violations}"

    def test_manifest_no_root_level_routing_prefix(self):
        """Manifest routing_prefix must not be a single segment (root level)."""
        violations = []
        for fid, m in _get_manifests_with_routing():
            prefix = m["routing_prefix"]
            segments = [s for s in prefix.split("/") if s]
            if len(segments) < 2:
                violations.append(f"manifest:{fid}: {prefix} is root-level")
        assert not violations, f"Root-level routing in manifests: {violations}"


class TestManifestStructure:
    """Validate manifest files have required WSP 104 fields."""

    def test_manifest_has_required_fields(self):
        """Manifest must have foundup_id, routing_prefix, data_namespace."""
        manifests = _load_manifests()
        violations = []
        for fid, manifest in manifests.items():
            missing = []
            if not manifest.get("foundup_id"):
                missing.append("foundup_id")
            if not manifest.get("routing_prefix"):
                missing.append("routing_prefix")
            if not manifest.get("data_namespace"):
                missing.append("data_namespace")
            if missing:
                violations.append(f"{fid}: missing {missing}")
        assert not violations, f"Manifest missing required fields: {violations}"


class TestCatalogRoutedRequiresManifest:
    """Catalog entries with routing must have a corresponding manifest."""

    def test_routed_catalog_entry_has_manifest(self):
        """Any catalog entry with routing_prefix must have a manifest file.

        This ensures the "100+ FoundUps" guardrail is meaningful:
        - Catalog alone is not sufficient for namespace claims
        - Shell runtime needs manifest for full tenant binding
        """
        catalog_routed = _get_catalog_entries_with_routing()
        manifests = _load_manifests()

        violations = []
        for e in catalog_routed:
            fid = e.get("foundup_id")
            if fid and fid not in manifests:
                violations.append(f"{fid}: has routing_prefix in catalog but no manifest")

        assert not violations, (
            f"Catalog-routed FoundUps missing manifest: {violations}. "
            "Create modules/foundups/{name}/foundup_manifest.json per WSP 104."
        )


class TestGotJunkFirstTenant:
    """GotJunk is the first bound tenant - verify WSP 104 compliance."""

    def test_gotjunk_manifest_exists(self):
        """GotJunk manifest exists at expected location."""
        manifest_path = _foundups_root() / "gotjunk" / "foundup_manifest.json"
        assert manifest_path.exists(), "gotjunk/foundup_manifest.json must exist"

    def test_gotjunk_canonical_routing(self):
        """GotJunk has canonical /f/gotjunk_001 routing."""
        manifests = _load_manifests()
        assert "gotjunk_001" in manifests, "gotjunk_001 manifest must exist"

        manifest = manifests["gotjunk_001"]
        assert manifest.get("routing_prefix") == "/f/gotjunk_001"
        assert manifest.get("data_namespace") == "idb_gotjunk_001"

    def test_gotjunk_in_catalog(self):
        """GotJunk appears in mall-video-catalog with consistent routing."""
        catalog = _load_catalog()
        gotjunk = next((e for e in catalog if e.get("foundup_id") == "gotjunk_001"), None)
        assert gotjunk is not None, "gotjunk_001 must be in catalog"
        assert gotjunk.get("routing_prefix") == "/f/gotjunk_001"
        assert gotjunk.get("data_namespace") == "idb_gotjunk_001"
