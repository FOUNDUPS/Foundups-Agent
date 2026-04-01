#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for gateway terms gate restoration.

Verifies that the ENTER button on the landing page shows the
eligibility/terms gate before any login is available, and that
the gate contains the required deterrence language.
"""

import re
from pathlib import Path

import pytest


GATEWAY = Path(__file__).resolve().parents[4] / "public" / "index.html"


# ---------------------------------------------------------------------------
# ENTER button handler — must show terms gate, not Clerk.openSignIn
# ---------------------------------------------------------------------------

class TestEnterButtonGate:
    """ENTER button must show disclaimer modal for unsigned users."""

    def test_gateway_exists(self):
        assert GATEWAY.is_file(), "public/index.html must exist"

    def test_enter_button_exists(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'id="enterBtn"' in html
        assert "ENTER" in html

    def test_enter_handler_shows_disclaimer_modal(self):
        """ENTER click handler shows disclaimerModal for unsigned users."""
        html = GATEWAY.read_text(encoding="utf-8")
        # Find the ENTER button handler section (from addEventListener to next top-level comment)
        start = html.index("enterBtn.addEventListener('click'")
        # Grab a generous chunk — handler is ~15 lines
        handler_body = html[start:start + 800]
        assert "disclaimerModal" in handler_body, (
            "ENTER handler must reference disclaimerModal for unsigned users"
        )
        assert "display = 'flex'" in handler_body or "display='flex'" in handler_body, (
            "ENTER handler must show disclaimerModal (display flex)"
        )

    def test_enter_handler_does_not_directly_open_clerk_signin(self):
        """ENTER click handler must NOT call Clerk.openSignIn() directly."""
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index("enterBtn.addEventListener('click'")
        handler_body = html[start:start + 800]
        assert "openSignIn" not in handler_body, (
            "ENTER handler must NOT call Clerk.openSignIn() — terms gate first"
        )

    def test_user_portal_icon_also_gated(self):
        """User portal icon must also show terms gate for unsigned users."""
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index("userPortalIcon.addEventListener('click'")
        handler_body = html[start:start + 600]
        assert "disclaimerModal" in handler_body, (
            "User portal icon must show disclaimerModal for unsigned users"
        )
        assert "openSignIn" not in handler_body, (
            "User portal icon must NOT call Clerk.openSignIn() directly"
        )


# ---------------------------------------------------------------------------
# Disclaimer modal content — deterrence language
# ---------------------------------------------------------------------------

class TestDisclaimerModalContent:
    """Disclaimer modal contains required deterrence language."""

    def test_disclaimer_modal_exists(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'id="disclaimerModal"' in html

    def test_not_accredited_investor_language(self):
        """Modal explicitly mentions accredited investor exclusion."""
        html = GATEWAY.read_text(encoding="utf-8")
        lower = html.lower()
        assert "not accredited investor" in lower or "not an accredited investor" in lower

    def test_not_company_representative_language(self):
        """Modal explicitly deters company representatives."""
        html = GATEWAY.read_text(encoding="utf-8")
        lower = html.lower()
        assert "representative" in lower
        assert "company" in lower or "organization" in lower or "entity" in lower

    def test_terms_of_access_link(self):
        """Modal links to Terms of Access."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "terms-of-access.html" in html

    def test_alpha_nda_link(self):
        """Modal links to Alpha NDA."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "alpha-nda.html" in html

    def test_oauth_confirm_buttons_have_deterrence(self):
        """OAuth sign-in buttons include deterrence confirmation text."""
        html = GATEWAY.read_text(encoding="utf-8")
        # Each OAuth button should have the CONFIRM attestation
        assert html.count("CONFIRM") >= 3, (
            "All 3 OAuth buttons should have CONFIRM attestation text"
        )

    def test_confirm_text_includes_investor_deterrence(self):
        """CONFIRM button text explicitly mentions accredited investor."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "not an accredited investor" in html


# ---------------------------------------------------------------------------
# Accredited investor decline path
# ---------------------------------------------------------------------------

class TestAccreditedDeclinePath:
    """Decline path exists for accredited investors / company reps."""

    def test_i_am_accredited_button_exists(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'id="iAmAccredited"' in html
        assert "accredited investor or company rep" in html.lower()

    def test_accredited_sorry_modal_exists(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert 'id="accreditedSorryModal"' in html

    def test_sorry_modal_has_clear_message(self):
        html = GATEWAY.read_text(encoding="utf-8")
        assert "non-accredited individuals" in html.lower() or "not available" in html.lower()

    def test_sorry_modal_has_alternative_paths(self):
        """Decline modal offers waitlist or contact options."""
        html = GATEWAY.read_text(encoding="utf-8")
        # Should have either waitlist or contact option
        assert "waitlist" in html.lower() or "contact" in html.lower()


# ---------------------------------------------------------------------------
# Signed-in users still go to /member/
# ---------------------------------------------------------------------------

class TestSignedInFlow:
    """Already-authenticated users still route directly to /member/."""

    def test_signed_in_enter_goes_to_member(self):
        html = GATEWAY.read_text(encoding="utf-8")
        start = html.index("enterBtn.addEventListener('click'")
        handler_body = html[start:start + 800]
        # The if branch (signed in) must go to /member/
        assert "/member/" in handler_body

    def test_clerk_listener_redirects_on_signin(self):
        """Clerk auth listener redirects to /member/ after sign-in."""
        html = GATEWAY.read_text(encoding="utf-8")
        assert "addListener" in html
        # After sign-in, should redirect to /member/
        listener_section = html[html.index("addListener"):]
        redirect_end = listener_section[:500]
        assert "/member/" in redirect_end
