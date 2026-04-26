"""Kosei Shell Route Contract Tests

Validates that the pfMALL shell can parse and route to Kosei via the
canonical /f/{foundup_id} landing surface.

WSP References:
- WSP 97: System Execution Prompting Protocol (truth boundaries)
- WSP 104: FoundUp Route Namespace and Tenant Isolation Protocol

Contract: modules/foundups/docs/PFMALL_SHELL_CONTRACT.md

WSP 97 Truth Boundaries:
- This test asserts static file and parsing contract facts.
- It does NOT assert live URL reachability.
- It does NOT assert SoftProto gestures work.
- It does NOT assert Kosei appears in mall-video-catalog.json discovery.
"""
import json
import os
import re
from pathlib import Path

import pytest


def _find_repo_root():
    """Walk up to find repo root (contains .git)."""
    current = Path(__file__).parent
    for _ in range(10):
        if (current / ".git").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return Path(__file__).parent.parent.parent.parent


REPO_ROOT = _find_repo_root()
PUBLIC_F_INDEX = REPO_ROOT / "public" / "f" / "index.html"
KOSEI_MANIFEST = REPO_ROOT / "modules" / "foundups" / "kosei" / "foundup_manifest.json"


class TestShellRouteParsesKoseiId:
    """Shell landing page can parse 'kosei' from /f/kosei route."""

    def test_canonical_landing_exists(self):
        """public/f/index.html exists for canonical route handling."""
        assert PUBLIC_F_INDEX.is_file(), "public/f/index.html must exist"

    def test_landing_has_pathname_parsing(self):
        """Landing parses foundup_id from pathname per WSP 97."""
        html = PUBLIC_F_INDEX.read_text(encoding="utf-8")
        # WSP 97: Identity parsed from pathname, not query params
        assert "pathname" in html, "Must parse pathname for foundup_id"
        assert "location.pathname" in html or "window.location.pathname" in html

    def test_landing_has_f_route_regex(self):
        """Landing has regex to extract foundup_id from /f/{id} path."""
        html = PUBLIC_F_INDEX.read_text(encoding="utf-8")
        # Should have a regex pattern like /^\/f\/([^\/]+)/
        assert re.search(r'/f/', html), "Must handle /f/ route prefix"

    def test_kosei_routing_prefix_is_parseable(self):
        """Kosei's routing_prefix '/f/kosei' is parseable by shell.

        This validates the manifest value aligns with shell parsing contract.
        """
        manifest = json.loads(KOSEI_MANIFEST.read_text(encoding="utf-8"))
        routing_prefix = manifest.get("routing_prefix", "")

        # Must start with /f/
        assert routing_prefix.startswith("/f/"), (
            f"routing_prefix must start with /f/, got '{routing_prefix}'"
        )

        # Extract the foundup_id portion
        match = re.match(r"^/f/([^/]+)$", routing_prefix)
        assert match, f"routing_prefix must match /f/{{id}} pattern: '{routing_prefix}'"

        extracted_id = match.group(1)
        assert extracted_id == manifest.get("foundup_id"), (
            f"Extracted id '{extracted_id}' must match foundup_id"
        )

    def test_landing_fetches_catalog(self):
        """Landing fetches catalog to resolve FoundUp metadata."""
        html = PUBLIC_F_INDEX.read_text(encoding="utf-8")
        # Should fetch a catalog file
        assert "fetch(" in html, "Must use fetch() for catalog"
        # The catalog could be mall-video-catalog.json or other
        assert ".json" in html, "Must reference a JSON catalog"


class TestKoseiManifestRouteContract:
    """Kosei manifest aligns with shell route contract."""

    @pytest.fixture
    def kosei_manifest(self):
        """Load Kosei manifest."""
        return json.loads(KOSEI_MANIFEST.read_text(encoding="utf-8"))

    def test_foundup_id_is_kosei(self, kosei_manifest):
        """foundup_id is exactly 'kosei'."""
        assert kosei_manifest.get("foundup_id") == "kosei"

    def test_routing_prefix_matches_wsp104(self, kosei_manifest):
        """routing_prefix follows WSP 104: /f/{foundup_id}."""
        expected = f"/f/{kosei_manifest['foundup_id']}"
        assert kosei_manifest.get("routing_prefix") == expected
