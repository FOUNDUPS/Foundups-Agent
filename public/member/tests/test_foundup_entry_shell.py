"""
FoundUp Entry Shell Tests

Tests for the transitional FoundUp entry page.
Route: /member/foundup.html?id={foundup_id}

This is a shell-owned preview/entry surface, not a full FoundUp interior.
"""
import os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(relpath):
    with open(os.path.join(ROOT, relpath), encoding="utf-8") as f:
        return f.read()


class TestEntryShellBranding:
    """Test that entry shell branding aligns with current Mall truth."""

    def test_title_uses_foundups_mall(self):
        """Page title uses FoundUps Mall branding."""
        html = _read("foundup.html")
        assert "FoundUps Mall" in html
        assert "p.fMALL" not in html

    def test_meta_description_aligned(self):
        """Meta description uses current branding."""
        html = _read("foundup.html")
        assert 'content="FoundUp entry view in the FoundUps Mall shell."' in html

    def test_dynamic_title_uses_foundups_mall(self):
        """JS sets document title with FoundUps Mall branding."""
        html = _read("foundup.html")
        assert "document.title = 'FoundUps Mall | '" in html


class TestRouteContractTruth:
    """Test that route contract is represented truthfully."""

    def test_target_route_label(self):
        """Route is labeled as 'Target Route' not just 'Route'."""
        html = _read("foundup.html")
        assert "Target Route" in html

    def test_routing_prefix_displayed(self):
        """routing_prefix field is shown in details."""
        html = _read("foundup.html")
        assert "routing_prefix" in html

    def test_no_live_route_claims(self):
        """No claims that /f/ routes are live."""
        html = _read("foundup.html")
        # Should not have href="/f/" links (only showing the prefix as text)
        assert 'href="/f/' not in html


class TestNavigationCopy:
    """Test navigation copy is aligned with current Mall."""

    def test_no_carousel_reference(self):
        """No references to old carousel navigation."""
        html = _read("foundup.html")
        assert "carousel" not in html.lower()

    def test_back_to_mall_exists(self):
        """Back to Mall link exists."""
        html = _read("foundup.html")
        assert "Back to Mall" in html

    def test_return_to_mall_exists(self):
        """Return to Mall link exists."""
        html = _read("foundup.html")
        assert "Return to Mall" in html

    def test_deep_link_copy_present(self):
        """Deep-linkable explanation is present."""
        html = _read("foundup.html")
        assert "deep-linkable" in html


class TestEntryShellStructure:
    """Test entry shell structural elements."""

    def test_entry_shell_container(self):
        """Entry shell container exists."""
        html = _read("foundup.html")
        assert "entry-shell" in html

    def test_entry_content_container(self):
        """Entry content container exists."""
        html = _read("foundup.html")
        assert 'id="entryContent"' in html

    def test_concierge_sheet_exists(self):
        """Concierge sheet exists."""
        html = _read("foundup.html")
        assert 'id="conciergeSheet"' in html

    def test_red_dog_button_exists(self):
        """Red Dog button exists."""
        html = _read("foundup.html")
        assert 'id="entryRedDog"' in html

    def test_catalog_url_correct(self):
        """Catalog URL points to mall-video-catalog.json."""
        html = _read("foundup.html")
        assert "/member/mall-video-catalog.json" in html


class TestTransitionalPath:
    """Test transitional entry path works correctly."""

    def test_id_param_used(self):
        """Page reads foundup_id from URL param."""
        html = _read("foundup.html")
        assert "params.get('id')" in html

    def test_not_found_handled(self):
        """Not found state is handled."""
        html = _read("foundup.html")
        assert "Not Found" in html
        assert "renderNotFound" in html

    def test_member_css_loaded(self):
        """Member CSS is loaded."""
        html = _read("foundup.html")
        assert 'href="css/member.css"' in html

    def test_red_dog_concierge_loaded(self):
        """Red Dog concierge JS is loaded."""
        html = _read("foundup.html")
        assert 'src="js/red-dog-concierge.js"' in html
