#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for ROC-first snap-shell gateway redesign.

Verifies that public/index.html is a simplified, vertical snap-based
gateway shell with ROC-first framing, required sections, and no stale
public-facing PoB hero language.
"""

from pathlib import Path

import pytest


GATEWAY = Path(__file__).resolve().parents[4] / "public" / "index.html"
MANIFEST = Path(__file__).resolve().parents[4] / "public" / "manifest.json"


# ---------------------------------------------------------------------------
# Snap shell structure
# ---------------------------------------------------------------------------

class TestSnapShellStructure:
    """Gateway uses vertical scroll-snap sections."""

    def test_gateway_exists(self):
        assert GATEWAY.is_file(), "public/index.html must exist"

    def test_scroll_snap_type_on_html(self):
        """HTML element must have scroll-snap-type: y mandatory."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "scroll-snap-type: y mandatory" in html

    def test_snap_section_class_defined(self):
        """CSS must define .snap-section with scroll-snap-align."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "scroll-snap-align: start" in html

    def test_snap_section_min_height(self):
        """Snap sections must be full viewport height."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "min-height: 100vh" in html

    def test_hero_is_snap_section(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'class="hero snap-section"' in html

    def test_how_is_snap_section(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'snap-section" id="how"' in html

    def test_build_is_snap_section(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'snap-section" id="build"' in html

    def test_roc_is_snap_section(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'snap-section" id="roc"' in html

    def test_terms_is_snap_section(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'snap-section" id="terms"' in html

    def test_at_least_four_snap_sections(self):
        """Gateway must have at least 4 snap sections."""
        html = GATEWAY.read_text(encoding="utf-8")
        count = html.count('snap-section')
        # Subtract 1 for the CSS class definition
        assert count >= 5, f"Expected >= 5 snap-section occurrences (4 sections + CSS), got {count}"


# ---------------------------------------------------------------------------
# Required sections present
# ---------------------------------------------------------------------------

class TestRequiredSections:
    """All required snap sections are present."""

    def test_hero_section_has_enter_button(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'id="enterBtn"' in html

    def test_hero_has_compute_statement(self):
        """Hero must contain compute-first language."""
        html = GATEWAY.read_text(encoding="utf-8")
        hero_start = html.index('class="hero snap-section"')
        hero_end = html.index('</section>', hero_start)
        hero = html[hero_start:hero_end]
        assert "Compute" in hero

    def test_how_section_has_three_steps(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'class="step-num">00' in html
        assert 'class="step-num">01' in html
        assert 'class="step-num">02' in html

    def test_build_section_has_canvas(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'id="buildCanvas"' in html

    def test_roc_section_has_cabr_framing(self):
        """ROC section must explain CABR drives ROC."""
        html = GATEWAY.read_text(encoding="utf-8")
        lower = html.lower()
        assert "cabr" in lower
        assert "roc" in lower

    def test_roc_section_has_value_first_framing(self):
        """ROC section must explain value before acronyms."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "CABR" in html
        assert "ROC" in html

    def test_terms_section_has_requirements(self):
        """Terms section must list access requirements."""
        html = GATEWAY.read_text(encoding="utf-8")
        lower = html.lower()
        assert "not" in lower and "accredited investor" in lower
        assert "representative" in lower

    def test_terms_section_has_legal_links(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert "terms-of-access.html" in html
        assert "alpha-nda.html" in html


# ---------------------------------------------------------------------------
# ROC-first framing — stale PoB hero language removed
# ---------------------------------------------------------------------------

class TestROCFirstFraming:
    """Public-facing language is ROC-first, not PoB-first."""

    def test_hero_does_not_lead_with_pob(self):
        """Hero section must NOT have PoB as the primary framing."""
        html = GATEWAY.read_text(encoding="utf-8")
        # Find hero section
        hero_start = html.index('class="hero snap-section"')
        hero_end = html.index('</section>', hero_start)
        hero = html[hero_start:hero_end]
        assert "Proof of Benefit" not in hero, "Hero must not use Proof of Benefit as primary framing"

    def test_meta_descriptions_use_roc(self):
        """Meta descriptions must use ROC language, not PoB."""
        html = GATEWAY.read_text(encoding="utf-8")
        # Check all meta descriptions
        import re
        descs = re.findall(r'content="([^"]*)"', html[:500])
        for desc in descs:
            if "idea" in desc.lower() or "agent" in desc.lower():
                assert "Proof of Benefit" not in desc, f"Meta description still uses PoB: {desc}"

    def test_roc_section_uses_verified_work_language(self):
        """ROC section uses verified-work language, not PoB-first."""
        html = GATEWAY.read_text(encoding="utf-8")
        roc_start = html.index('id="roc"')
        roc_end = html.index('</section>', roc_start)
        roc = html[roc_start:roc_end]
        assert "verified work" in roc.lower(), "ROC section should mention verified work"
        assert "Return on Compute" in roc, "ROC section title must be Return on Compute"

    def test_no_pob_in_tokenomics_strip(self):
        """Tokenomics strip should be removed from gateway."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'class="tok-strip' not in html or 'tok-val c4">PoB' not in html

    def test_no_pob_class_names_in_source(self):
        """Phase 2: All pob- CSS class names must be renamed to roc-."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'pob-section' not in html, "pob-section class still present"
        assert 'pob-grid' not in html, "pob-grid class still present"
        assert 'pob-col' not in html, "pob-col class still present"
        assert 'pob-text' not in html, "pob-text class still present"
        assert 'pob-visual' not in html, "pob-visual class still present"
        assert 'pob-compare' not in html, "pob-compare class still present"

    def test_roc_section_uses_roc_class_names(self):
        """Phase 2: ROC section must use roc- prefixed class names."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'roc-section' in html
        assert 'roc-grid' in html
        assert 'roc-compare' in html

    def test_roc_canvas_renamed(self):
        """Phase 2: PoB canvas must be renamed to rocCanvas."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'id="rocCanvas"' in html
        assert 'pobCanvas' not in html

    def test_no_dead_tokenomics_css(self):
        """Phase 2: Dead tokenomics CSS must be removed."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert '.tok-strip' not in html
        assert '.tok-val' not in html
        assert '.tok-cell' not in html

    def test_no_dead_beta_css(self):
        """Phase 2: Dead beta signup CSS must be removed."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert '.beta-section' not in html
        assert '.beta-card' not in html
        assert '.beta-form' not in html
        assert '.beta-submit' not in html

    def test_no_equity_ownership_language(self):
        """Landing must not imply equity-like ownership."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "99% own every idea" not in html
        assert "99% will own" not in html

    def test_no_securities_framing_in_meta(self):
        """Meta descriptions must not use securities-style language."""
        html = GATEWAY.read_text(encoding="utf-8")
        head = html[:html.index('</head>')]
        assert "21M tokens" not in head
        assert "backed by BTC" not in head

    def test_hero_tagline_no_securities(self):
        """Hero tagline must not use securities language."""
        html = GATEWAY.read_text(encoding="utf-8")
        hero_start = html.index('class="hero snap-section"')
        hero_end = html.index('</section>', hero_start)
        hero = html[hero_start:hero_end]
        assert "backed by BTC" not in hero
        assert "21M tokens" not in hero


# ---------------------------------------------------------------------------
# Terms gate behavior preserved
# ---------------------------------------------------------------------------

class TestTermsGateBehavior:
    """ENTER button still gates via disclaimerModal."""

    def test_enter_handler_shows_disclaimer(self):
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index("enterBtn.addEventListener('click'")
        handler_body = html[start:start + 800]
        assert "disclaimerModal" in handler_body

    def test_signed_in_goes_to_member(self):
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index("enterBtn.addEventListener('click'")
        handler_body = html[start:start + 800]
        assert "navigateToMember" in handler_body

    def test_disclaimer_modal_exists(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'id="disclaimerModal"' in html

    def test_accredited_sorry_modal_exists(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'id="accreditedSorryModal"' in html


# ---------------------------------------------------------------------------
# PWA Phase 1
# ---------------------------------------------------------------------------

SW = Path(__file__).resolve().parents[4] / "public" / "sw.js"


class TestPWAPhase1:
    """PWA manifest, service worker, and metadata present."""

    def test_manifest_link_in_head(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'rel="manifest"' in html
        assert 'manifest.json' in html

    def test_manifest_file_exists(self):
        assert MANIFEST.is_file(), "public/manifest.json must exist"

    def test_manifest_has_required_fields(self):
        import json
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        assert "name" in data
        assert "short_name" in data
        assert "start_url" in data
        assert "display" in data
        assert "icons" in data

    def test_manifest_has_scope(self):
        import json
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        assert "scope" in data
        assert data["scope"] == "/"

    def test_manifest_has_id(self):
        import json
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        assert "id" in data

    def test_manifest_has_192_icon(self):
        """Chrome requires a 192x192 icon for installability."""
        import json
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        sizes = [icon.get("sizes") for icon in data["icons"]]
        assert "192x192" in sizes, f"Missing 192x192 icon, got: {sizes}"

    def test_manifest_has_512_icon(self):
        import json
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        sizes = [icon.get("sizes") for icon in data["icons"]]
        assert "512x512" in sizes

    def test_theme_color_meta(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'name="theme-color"' in html

    def test_service_worker_file_exists(self):
        assert SW.is_file(), "public/sw.js must exist"

    def test_service_worker_registration_in_gateway(self):
        """Gateway must register the service worker."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "serviceWorker" in html
        assert "register" in html
        assert "sw.js" in html

    def test_service_worker_does_not_cache_clerk(self):
        """Service worker must never cache Clerk SDK."""
        sw = SW.read_text(encoding="utf-8")
        assert "clerk" in sw.lower(), "SW must have Clerk in NEVER_CACHE list"

    def test_service_worker_does_not_cache_member(self):
        """Service worker must never cache /member/ routes."""
        sw = SW.read_text(encoding="utf-8")
        assert "/member/" in sw

    def test_service_worker_does_not_cache_firebase(self):
        """Service worker must never cache Firebase SDK/API."""
        sw = SW.read_text(encoding="utf-8")
        assert "firebase" in sw.lower()

    def test_service_worker_has_cache_name(self):
        """Service worker must define a versioned cache name."""
        sw = SW.read_text(encoding="utf-8")
        assert "CACHE_NAME" in sw

    def test_install_banner_exists(self):
        """Install banner element must exist in gateway."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'id="installBanner"' in html

    def test_install_button_exists(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'id="installBtn"' in html

    def test_install_dismiss_exists(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'id="installDismiss"' in html

    def test_beforeinstallprompt_captured(self):
        """Gateway must capture beforeinstallprompt event."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "beforeinstallprompt" in html

    def test_install_does_not_force_prompt(self):
        """Install must check localStorage before showing banner."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "installDismissed" in html

    def test_appinstalled_hides_banner(self):
        """Banner must hide on appinstalled event."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "appinstalled" in html


# ---------------------------------------------------------------------------
# Install Fallback Phase 3
# ---------------------------------------------------------------------------

class TestInstallFallbackPhase3:
    """Installed-state suppression + unsupported-browser fallback."""

    def test_standalone_detection_exists(self):
        """Gateway must detect standalone/installed state."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "display-mode: standalone" in html

    def test_navigator_standalone_check(self):
        """Gateway must check navigator.standalone for iOS."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "navigator.standalone" in html

    def test_standalone_css_suppression(self):
        """CSS must hide install affordances in standalone mode."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "@media (display-mode: standalone)" in html

    def test_standalone_suppresses_install_banner(self):
        """Standalone CSS rule must target install-banner."""
        html = GATEWAY.read_text(encoding="utf-8")
        # Find the standalone media query block
        start = html.index("@media (display-mode: standalone)")
        block = html[start:start + 200]
        assert ".install-banner" in block

    def test_fallback_hint_element_exists(self):
        """Fallback hint element must exist for unsupported browsers."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'id="installFallbackHint"' in html

    def test_fallback_hint_class_defined(self):
        """Fallback hint CSS class must be defined."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert ".install-fallback-hint" in html

    def test_ios_detection_for_fallback(self):
        """Fallback must detect iOS for Add to Home Screen hint."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "iPad|iPhone|iPod" in html

    def test_fallback_respects_dismiss_persistence(self):
        """Fallback must check installDismissed before showing."""
        html = GATEWAY.read_text(encoding="utf-8")
        # Find the fallback setTimeout block (not the variable declaration)
        fallback_start = html.index("installFallbackHint.textContent")
        fallback_block = html[fallback_start - 500:fallback_start]
        assert "installDismissed" in fallback_block

    def test_fallback_respects_accepted_persistence(self):
        """Fallback must not show if install was already accepted."""
        html = GATEWAY.read_text(encoding="utf-8")
        fallback_start = html.index("installFallbackHint.textContent")
        fallback_block = html[fallback_start - 500:fallback_start]
        assert "installAccepted" in fallback_block

    def test_deferred_prompt_still_works(self):
        """Original beforeinstallprompt capture must still exist."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "deferredInstallPrompt" in html
        assert "beforeinstallprompt" in html

    def test_standalone_suppresses_fallback_hint(self):
        """Standalone CSS rule must also target fallback hint."""
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index("@media (display-mode: standalone)")
        block = html[start:start + 200]
        assert ".install-fallback-hint" in block

    def test_isStandalone_guards_beforeinstallprompt(self):
        """beforeinstallprompt handler must check isStandalone."""
        html = GATEWAY.read_text(encoding="utf-8")
        bip_start = html.index("beforeinstallprompt")
        bip_block = html[bip_start:bip_start + 300]
        assert "isStandalone" in bip_block

    def test_appinstalled_hides_fallback_hint(self):
        """appinstalled handler must also hide fallback hint."""
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index("appinstalled")
        block = html[start:start + 300]
        assert "installFallbackHint" in block


# ---------------------------------------------------------------------------
# Member Handoff Phase 4
# ---------------------------------------------------------------------------

class TestMemberHandoffPhase4:
    """Root-to-member handoff overlay and navigateToMember function."""

    def test_handoff_overlay_exists(self):
        """Handoff overlay element must exist."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'id="handoffOverlay"' in html

    def test_handoff_status_element_exists(self):
        """Handoff status text element must exist."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'id="handoffStatus"' in html

    def test_handoff_overlay_css_defined(self):
        """Handoff overlay CSS class must be defined."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert ".handoff-overlay" in html

    def test_navigate_to_member_function_exists(self):
        """navigateToMember function must be defined."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "function navigateToMember" in html

    def test_navigate_to_member_shows_overlay(self):
        """navigateToMember must show the handoff overlay."""
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index("function navigateToMember")
        block = html[start:start + 300]
        assert "handoffOverlay" in block

    def test_navigate_to_member_redirects(self):
        """navigateToMember must redirect to /member/."""
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index("function navigateToMember")
        block = html[start:start + 300]
        assert "/member/" in block

    def test_signed_in_enter_uses_handoff(self):
        """Signed-in ENTER click must use navigateToMember."""
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index("enterBtn.addEventListener('click'")
        block = html[start:start + 800]
        assert "navigateToMember" in block

    def test_clerk_listener_uses_handoff(self):
        """Clerk addListener sign-in must use navigateToMember."""
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index("Clerk.addListener")
        block = html[start:start + 300]
        assert "navigateToMember" in block

    def test_portal_icon_uses_handoff(self):
        """userPortalIcon click must use navigateToMember when signed in."""
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index("userPortalIcon.addEventListener")
        block = html[start:start + 400]
        assert "navigateToMember" in block

    def test_no_direct_member_redirect_outside_handoff(self):
        """Only navigateToMember should contain direct /member/ redirect."""
        html = GATEWAY.read_text(encoding="utf-8")
        import re
        # Find all window.location.href = '/member/' occurrences
        matches = [m.start() for m in re.finditer(r"window\.location\.href\s*=\s*'/member/'", html)]
        # Should be exactly 1 (inside navigateToMember)
        assert len(matches) == 1, f"Expected 1 direct /member/ redirect, found {len(matches)}"

    def test_terms_gate_still_works_for_unsigned(self):
        """Unsigned ENTER must still show disclaimerModal, not handoff."""
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index("enterBtn.addEventListener('click'")
        block = html[start:start + 800]
        assert "disclaimerModal" in block


# ---------------------------------------------------------------------------
# Public Metadata Phase 5
# ---------------------------------------------------------------------------

class TestPublicMetadataPhase5:
    """Public metadata is ROC-first, consistent, and non-securities."""

    def test_title_contains_compute(self):
        """Title must use compute-first language."""
        html = GATEWAY.read_text(encoding="utf-8")
        head = html[:html.index("</head>")]
        assert "<title>" in head
        title_start = head.index("<title>") + len("<title>")
        title_end = head.index("</title>")
        title = head[title_start:title_end]
        assert "Compute" in title

    def test_meta_description_expands_roc(self):
        """Meta description must spell out Return on Compute, not just ROC."""
        html = GATEWAY.read_text(encoding="utf-8")
        import re
        match = re.search(r'<meta name="description"[^>]*content="([^"]*)"', html)
        assert match, "Meta description not found"
        desc = match.group(1)
        assert "Return on Compute" in desc

    def test_og_title_matches_page_title(self):
        """OG title must match page title."""
        html = GATEWAY.read_text(encoding="utf-8")
        head = html[:html.index("</head>")]
        import re
        title_match = re.search(r"<title>(.*?)</title>", head)
        og_match = re.search(r'og:title" content="([^"]*)"', head)
        assert title_match and og_match
        assert title_match.group(1) == og_match.group(1)

    def test_og_description_matches_meta(self):
        """OG description must match meta description."""
        html = GATEWAY.read_text(encoding="utf-8")
        head = html[:html.index("</head>")]
        import re
        meta_match = re.search(r'<meta name="description"[^>]*content="([^"]*)"', head)
        og_match = re.search(r'og:description"[^>]*content="([^"]*)"', head)
        assert meta_match and og_match
        assert meta_match.group(1) == og_match.group(1)

    def test_twitter_description_matches_meta(self):
        """Twitter description must match meta description."""
        html = GATEWAY.read_text(encoding="utf-8")
        head = html[:html.index("</head>")]
        import re
        meta_match = re.search(r'<meta name="description"[^>]*content="([^"]*)"', head)
        tw_match = re.search(r'twitter:description" content="([^"]*)"', head)
        assert meta_match and tw_match
        assert meta_match.group(1) == tw_match.group(1)

    def test_twitter_title_matches_og(self):
        """Twitter title must match OG title."""
        html = GATEWAY.read_text(encoding="utf-8")
        head = html[:html.index("</head>")]
        import re
        og_match = re.search(r'og:title" content="([^"]*)"', head)
        tw_match = re.search(r'twitter:title" content="([^"]*)"', head)
        assert og_match and tw_match
        assert og_match.group(1) == tw_match.group(1)

    def test_no_pob_in_metadata(self):
        """No Proof of Benefit language in any metadata."""
        html = GATEWAY.read_text(encoding="utf-8")
        head = html[:html.index("</head>")]
        assert "Proof of Benefit" not in head

    def test_no_securities_in_metadata(self):
        """No securities-style language in metadata."""
        html = GATEWAY.read_text(encoding="utf-8")
        head = html[:html.index("</head>")]
        assert "21M tokens" not in head
        assert "backed by BTC" not in head
        assert "tokenomics" not in head.lower()

    def test_og_image_uses_logo(self):
        """OG image must reference the logo asset."""
        html = GATEWAY.read_text(encoding="utf-8")
        import re
        match = re.search(r'og:image" content="([^"]*)"', html)
        assert match
        assert "logo-dog.png" in match.group(1)

    def test_canonical_url_present(self):
        """Canonical URL must be present."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'rel="canonical"' in html
        assert "foundups.com" in html


# ---------------------------------------------------------------------------
# Structured Data Phase 6
# ---------------------------------------------------------------------------

class TestStructuredDataPhase6:
    """JSON-LD structured data is truthful and aligned."""

    def _get_jsonld(self):
        import json, re
        html = GATEWAY.read_text(encoding="utf-8")
        match = re.search(
            r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
            html, re.DOTALL
        )
        assert match, "JSON-LD script block not found"
        return json.loads(match.group(1))

    def test_jsonld_script_exists(self):
        """Structured data script must exist in head."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'application/ld+json' in html

    def test_jsonld_is_valid_json(self):
        """JSON-LD must parse as valid JSON."""
        self._get_jsonld()  # will assert if invalid

    def test_jsonld_has_context(self):
        data = self._get_jsonld()
        assert data["@context"] == "https://schema.org"

    def test_jsonld_has_organization(self):
        """Organization schema must be present."""
        data = self._get_jsonld()
        types = [item["@type"] for item in data["@graph"]]
        assert "Organization" in types

    def test_jsonld_has_website(self):
        """WebSite schema must be present."""
        data = self._get_jsonld()
        types = [item["@type"] for item in data["@graph"]]
        assert "WebSite" in types

    def test_organization_has_required_fields(self):
        data = self._get_jsonld()
        org = [item for item in data["@graph"] if item["@type"] == "Organization"][0]
        assert "name" in org
        assert "url" in org
        assert "logo" in org
        assert "description" in org

    def test_organization_name_is_foundups(self):
        data = self._get_jsonld()
        org = [item for item in data["@graph"] if item["@type"] == "Organization"][0]
        assert org["name"] == "FoundUPS"

    def test_organization_url_matches_canonical(self):
        data = self._get_jsonld()
        org = [item for item in data["@graph"] if item["@type"] == "Organization"][0]
        assert org["url"] == "https://foundups.com/"

    def test_organization_description_matches_meta(self):
        """Structured data description must match meta description."""
        import re
        html = GATEWAY.read_text(encoding="utf-8")
        meta_match = re.search(r'<meta name="description"[^>]*content="([^"]*)"', html)
        data = self._get_jsonld()
        org = [item for item in data["@graph"] if item["@type"] == "Organization"][0]
        assert org["description"] == meta_match.group(1)

    def test_organization_logo_matches_og_image(self):
        data = self._get_jsonld()
        org = [item for item in data["@graph"] if item["@type"] == "Organization"][0]
        assert "logo-dog.png" in org["logo"]

    def test_organization_has_sameas(self):
        """Organization must have sameAs social links."""
        data = self._get_jsonld()
        org = [item for item in data["@graph"] if item["@type"] == "Organization"][0]
        assert "sameAs" in org
        assert len(org["sameAs"]) >= 1

    def test_no_pob_in_structured_data(self):
        """No Proof of Benefit in structured data."""
        html = GATEWAY.read_text(encoding="utf-8")
        import re
        match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            html, re.DOTALL
        )
        assert "Proof of Benefit" not in match.group(1)

    def test_no_securities_in_structured_data(self):
        """No securities language in structured data."""
        html = GATEWAY.read_text(encoding="utf-8")
        import re
        match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            html, re.DOTALL
        )
        block = match.group(1)
        assert "21M tokens" not in block
        assert "backed by BTC" not in block


# ---------------------------------------------------------------------------
# Modal Accessibility Phase 7
# ---------------------------------------------------------------------------

class TestModalAccessibilityPhase7:
    """Modal dialog semantics, focus management, and keyboard behavior."""

    def test_disclaimer_modal_has_dialog_role(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'id="disclaimerModal"' in html
        start = html.index('id="disclaimerModal"')
        tag = html[html.rfind('<', 0, start):html.index('>', start) + 1]
        assert 'role="dialog"' in tag

    def test_disclaimer_modal_has_aria_modal(self):
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index('id="disclaimerModal"')
        tag = html[html.rfind('<', 0, start):html.index('>', start) + 1]
        assert 'aria-modal="true"' in tag

    def test_disclaimer_modal_has_aria_labelledby(self):
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index('id="disclaimerModal"')
        tag = html[html.rfind('<', 0, start):html.index('>', start) + 1]
        assert 'aria-labelledby=' in tag

    def test_signin_modal_has_dialog_role(self):
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index('id="signInModal"')
        tag = html[html.rfind('<', 0, start):html.index('>', start) + 1]
        assert 'role="dialog"' in tag

    def test_signin_modal_has_aria_modal(self):
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index('id="signInModal"')
        tag = html[html.rfind('<', 0, start):html.index('>', start) + 1]
        assert 'aria-modal="true"' in tag

    def test_sorry_modal_has_dialog_role(self):
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index('id="accreditedSorryModal"')
        tag = html[html.rfind('<', 0, start):html.index('>', start) + 1]
        assert 'role="dialog"' in tag

    def test_sorry_modal_has_aria_modal(self):
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index('id="accreditedSorryModal"')
        tag = html[html.rfind('<', 0, start):html.index('>', start) + 1]
        assert 'aria-modal="true"' in tag

    def test_modal_title_ids_exist(self):
        """Each dialog must have a title element with matching id."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'id="disclaimerModalTitle"' in html
        assert 'id="signInModalTitle"' in html
        assert 'id="accreditedSorryModalTitle"' in html

    def test_escape_handler_exists(self):
        """Keydown handler must listen for Escape to close modals."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "Escape" in html

    def test_focus_trap_exists(self):
        """trapFocus function must exist for Tab cycling."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "trapFocus" in html

    def test_open_modal_function_exists(self):
        """openModal function must exist for focus management."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "function openModal" in html

    def test_close_modal_function_exists(self):
        """closeModal function must exist for focus restoration."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "function closeModal" in html

    def test_close_modal_restores_focus(self):
        """closeModal must restore focus to lastFocusedElement."""
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index("function closeModal")
        block = html[start:start + 200]
        assert "lastFocusedElement" in block

    def test_handoff_overlay_is_not_dialog(self):
        """Handoff overlay must NOT have dialog role (it is a transition)."""
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index('id="handoffOverlay"')
        tag = html[html.rfind('<', 0, start):html.index('>', start) + 1]
        assert 'role="dialog"' not in tag

    def test_close_buttons_have_aria_label(self):
        """Modal close buttons should have aria-label."""
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index('id="closeSignInModal"')
        tag = html[html.rfind('<', 0, start):html.index('>', start) + 1]
        assert 'aria-label=' in tag
