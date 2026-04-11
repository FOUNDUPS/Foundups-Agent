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


class TestNamespaceUniqueness:
    """Enforce globally unique namespaces across all FoundUps."""

    def test_foundup_ids_unique_in_catalog(self):
        """No duplicate foundup_id values in catalog."""
        catalog = _load_catalog()
        ids = [e.get("foundup_id") for e in catalog if e.get("foundup_id")]
        duplicates = [fid for fid in ids if ids.count(fid) > 1]
        assert not duplicates, f"Duplicate foundup_ids in catalog: {set(duplicates)}"

    def test_routing_prefixes_unique_in_catalog(self):
        """No duplicate routing_prefix values in catalog."""
        entries = _get_catalog_entries_with_routing()
        prefixes = [e["routing_prefix"] for e in entries]
        duplicates = [p for p in prefixes if prefixes.count(p) > 1]
        assert not duplicates, f"Duplicate routing_prefixes: {set(duplicates)}"

    def test_data_namespaces_unique_in_catalog(self):
        """No duplicate data_namespace values in catalog."""
        catalog = _load_catalog()
        namespaces = [e.get("data_namespace") for e in catalog if e.get("data_namespace")]
        duplicates = [ns for ns in namespaces if namespaces.count(ns) > 1]
        assert not duplicates, f"Duplicate data_namespaces: {set(duplicates)}"

    def test_foundup_ids_unique_in_manifests(self):
        """No duplicate foundup_id across manifest files."""
        manifests = _load_manifests()
        # Manifests are keyed by foundup_id, so duplicates would overwrite.
        # Check by scanning all manifest files directly.
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
    """Enforce /f/{foundup_id} canonical route structure."""

    def test_routing_prefix_matches_canonical_pattern(self):
        """All routing_prefix values must match /f/{foundup_id} pattern."""
        entries = _get_catalog_entries_with_routing()
        violations = []
        for e in entries:
            prefix = e["routing_prefix"]
            if not CANONICAL_ROUTE_PATTERN.match(prefix):
                violations.append(f"{e.get('foundup_id')}: {prefix}")
        assert not violations, f"Non-canonical routing_prefix: {violations}"

    def test_routing_prefix_contains_foundup_id(self):
        """routing_prefix must contain the foundup_id."""
        entries = _get_catalog_entries_with_routing()
        violations = []
        for e in entries:
            fid = e.get("foundup_id", "")
            prefix = e["routing_prefix"]
            expected = f"/f/{fid}"
            if prefix != expected:
                violations.append(f"{fid}: got {prefix}, expected {expected}")
        assert not violations, f"routing_prefix does not match foundup_id: {violations}"

    def test_data_namespace_matches_pattern(self):
        """data_namespace must match idb_{foundup_id} pattern."""
        catalog = _load_catalog()
        violations = []
        for e in catalog:
            ns = e.get("data_namespace")
            if ns and not DATA_NAMESPACE_PATTERN.match(ns):
                violations.append(f"{e.get('foundup_id')}: {ns}")
        assert not violations, f"Non-canonical data_namespace: {violations}"

    def test_data_namespace_contains_foundup_id(self):
        """data_namespace must contain the foundup_id."""
        catalog = _load_catalog()
        violations = []
        for e in catalog:
            fid = e.get("foundup_id", "")
            ns = e.get("data_namespace")
            if ns:
                expected = f"idb_{fid}"
                if ns != expected:
                    violations.append(f"{fid}: got {ns}, expected {expected}")
        assert not violations, f"data_namespace does not match foundup_id: {violations}"


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
    """Prevent FoundUps from claiming reserved root paths."""

    def test_routing_prefix_not_reserved_root(self):
        """routing_prefix must not be a reserved root path."""
        entries = _get_catalog_entries_with_routing()
        violations = []
        for e in entries:
            prefix = e["routing_prefix"]
            # Check if prefix is or starts with a reserved path
            for reserved in RESERVED_ROOT_PATHS:
                if prefix == reserved or (prefix.startswith(reserved + "/") and reserved != "/f"):
                    violations.append(f"{e.get('foundup_id')}: {prefix} conflicts with {reserved}")
        assert not violations, f"Root sprawl violations: {violations}"

    def test_no_root_level_routing_prefix(self):
        """routing_prefix must not be a single segment (root level)."""
        entries = _get_catalog_entries_with_routing()
        violations = []
        for e in entries:
            prefix = e["routing_prefix"]
            # Valid: /f/gotjunk_001 (3+ segments), Invalid: /gotjunk (2 segments)
            segments = [s for s in prefix.split("/") if s]
            if len(segments) < 2:
                violations.append(f"{e.get('foundup_id')}: {prefix} is root-level (needs /f/ prefix)")
        assert not violations, f"Root-level routing violations: {violations}"


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
