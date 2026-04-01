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
        assert "/member/" in handler_body

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
