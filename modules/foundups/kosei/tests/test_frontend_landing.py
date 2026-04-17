"""
Kosei Public Landing PWA - Frontend Validation Tests

Validates static file correctness for index.html, manifest.json, sw.js,
kosei-i18n.js, kosei-intake.js without a running browser or server.

WSP 5: Test coverage for all public-facing PWA contracts.
"""

import json
import re
import pytest
from pathlib import Path

# --------------------------------------------------------------------- paths
MODULE_ROOT = Path(__file__).parent.parent
FRONTEND_ROOT = MODULE_ROOT / "frontend"
INDEX_HTML = FRONTEND_ROOT / "index.html"
MANIFEST_JSON = FRONTEND_ROOT / "manifest.json"
SW_JS = FRONTEND_ROOT / "sw.js"
I18N_JS = FRONTEND_ROOT / "js" / "kosei-i18n.js"
INTAKE_JS = FRONTEND_ROOT / "js" / "kosei-intake.js"


# ================================================================
# TestLandingStructure — HTML structure
# ================================================================

class TestLandingStructure:
    """Validate index.html structure and required PWA scaffolding."""

    @pytest.fixture(scope="class")
    def html(self):
        return INDEX_HTML.read_text(encoding="utf-8")

    def test_file_exists(self):
        assert INDEX_HTML.exists(), f"index.html not found at {INDEX_HTML}"

    def test_html5_doctype(self, html):
        assert html.strip().startswith("<!DOCTYPE html>"), "Missing HTML5 DOCTYPE declaration"

    def test_has_html_tag(self, html):
        assert re.search(r"<html\b", html, re.IGNORECASE), "Missing <html> tag"

    def test_has_head_tag(self, html):
        assert re.search(r"<head\b", html, re.IGNORECASE), "Missing <head> tag"

    def test_has_body_tag(self, html):
        assert re.search(r"<body\b", html, re.IGNORECASE), "Missing <body> tag"

    def test_meta_viewport(self, html):
        assert re.search(
            r'<meta\s[^>]*name=["\']viewport["\']', html, re.IGNORECASE
        ), "Missing meta viewport tag"

    def test_manifest_link(self, html):
        assert re.search(
            r'<link\s[^>]*rel=["\']manifest["\']', html, re.IGNORECASE
        ), "Missing <link rel='manifest'> tag"

    def test_theme_color_meta(self, html):
        assert re.search(
            r'<meta\s[^>]*name=["\']theme-color["\']', html, re.IGNORECASE
        ), "Missing meta theme-color tag"

    def test_service_worker_registration(self, html):
        assert "serviceWorker" in html, "No service worker registration found in index.html"
        assert "serviceWorker.register" in html, "serviceWorker.register() call missing"

    def test_kosei_i18n_script_reference(self, html):
        assert "kosei-i18n.js" in html, "kosei-i18n.js script not referenced in index.html"

    def test_kosei_intake_script_reference(self, html):
        assert "kosei-intake.js" in html, "kosei-intake.js script not referenced in index.html"

    def test_exactly_one_intake_form(self, html):
        forms = re.findall(r'<form\b[^>]*>', html, re.IGNORECASE)
        assert len(forms) == 1, f"Expected exactly 1 <form> element, found {len(forms)}"

    def test_form_id_koseiIntakeForm(self, html):
        assert re.search(
            r'<form\s[^>]*id=["\']koseiIntakeForm["\']', html, re.IGNORECASE
        ), "Form element missing id='koseiIntakeForm'"

    def test_form_field_name(self, html):
        assert re.search(r'name=["\']name["\']', html), "Form field 'name' not found"

    def test_form_field_email(self, html):
        assert re.search(r'name=["\']email["\']', html), "Form field 'email' not found"

    def test_form_field_business(self, html):
        assert re.search(r'name=["\']business["\']', html), "Form field 'business' not found"

    def test_form_field_platforms(self, html):
        assert re.search(r'name=["\']platforms["\']', html), "Form field 'platforms' not found"

    def test_form_field_handle(self, html):
        assert re.search(r'name=["\']handle["\']', html), "Form field 'handle' not found"

    def test_form_field_frequency(self, html):
        assert re.search(r'name=["\']frequency["\']', html), "Form field 'frequency' not found"

    def test_form_field_goals(self, html):
        assert re.search(r'name=["\']goals["\']', html), "Form field 'goals' not found"

    def test_form_field_consent(self, html):
        assert re.search(r'name=["\']consent["\']', html), "Form field 'consent' not found"

    def test_nav_audit_link(self, html):
        assert re.search(r'href=["\']#audit["\']', html), "Nav link to #audit section missing"

    def test_nav_pricing_link(self, html):
        assert re.search(r'href=["\']#pricing["\']', html), "Nav link to #pricing section missing"

    def test_nav_login_link(self, html):
        """Client Login must point at the real app mount, not a dead /kosei/login route."""
        assert "/kosei/app/" in html, "Nav link to /kosei/app/ (Client Login) missing"

    def test_hero_section_exists(self, html):
        assert "kosei-hero" in html, "Hero section (kosei-hero) not found in index.html"

    def test_value_section_exists(self, html):
        assert "kosei-values-grid" in html, "Value propositions section (kosei-values-grid) not found"

    def test_audit_section_exists(self, html):
        assert 'id="audit"' in html or "id='audit'" in html, "Audit section (id=audit) not found"

    def test_trust_section_exists(self, html):
        assert "kosei-trust-stats" in html, "Trust section (kosei-trust-stats) not found"

    def test_footer_exists(self, html):
        assert re.search(r"<footer\b", html, re.IGNORECASE), "Missing <footer> element"

    def test_lang_toggle_button(self, html):
        assert re.search(
            r'id=["\']langToggle["\']', html
        ), "Lang toggle button (id=langToggle) not found"


# ================================================================
# TestI18nCompleteness — internationalisation
# ================================================================

class TestI18nCompleteness:
    """Validate EN/JA key parity and data-i18n attribute coverage."""

    @pytest.fixture(scope="class")
    def i18n_js(self):
        return I18N_JS.read_text(encoding="utf-8")

    @pytest.fixture(scope="class")
    def html(self):
        return INDEX_HTML.read_text(encoding="utf-8")

    @pytest.fixture(scope="class")
    def en_keys(self, i18n_js):
        """Extract keys from the EN block of KOSEI_STRINGS."""
        # Isolate the en: { ... } block
        en_match = re.search(r'\ben:\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}', i18n_js, re.DOTALL)
        assert en_match, "Could not find 'en:' block in KOSEI_STRINGS"
        block = en_match.group(1)
        return set(re.findall(r'^\s{4}(\w+)\s*:', block, re.MULTILINE))

    @pytest.fixture(scope="class")
    def ja_keys(self, i18n_js):
        """Extract keys from the JA block of KOSEI_STRINGS."""
        ja_match = re.search(r'\bja:\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}', i18n_js, re.DOTALL)
        assert ja_match, "Could not find 'ja:' block in KOSEI_STRINGS"
        block = ja_match.group(1)
        return set(re.findall(r'^\s{4}(\w+)\s*:', block, re.MULTILINE))

    def test_file_exists(self):
        assert I18N_JS.exists(), f"kosei-i18n.js not found at {I18N_JS}"

    def test_kosei_strings_defined(self, i18n_js):
        assert "KOSEI_STRINGS" in i18n_js, "KOSEI_STRINGS object not found in kosei-i18n.js"

    def test_en_and_ja_blocks_present(self, i18n_js):
        assert re.search(r'\ben\s*:', i18n_js), "EN locale block missing from KOSEI_STRINGS"
        assert re.search(r'\bja\s*:', i18n_js), "JA locale block missing from KOSEI_STRINGS"

    def test_en_and_ja_have_same_keys(self, en_keys, ja_keys):
        en_only = en_keys - ja_keys
        ja_only = ja_keys - en_keys
        assert not en_only, f"Keys in EN but missing from JA: {sorted(en_only)}"
        assert not ja_only, f"Keys in JA but missing from EN: {sorted(ja_only)}"

    def test_html_data_i18n_attributes_have_matching_keys(self, html, en_keys):
        """Every data-i18n attribute value used in index.html must exist in KOSEI_STRINGS.en."""
        used_keys = set(re.findall(r'data-i18n=["\'](\w+)["\']', html))
        missing = used_keys - en_keys
        assert not missing, (
            f"data-i18n keys used in index.html but absent from KOSEI_STRINGS.en: {sorted(missing)}"
        )

    def test_en_has_required_nav_keys(self, en_keys):
        for key in ("nav_audit", "nav_pricing", "nav_login", "lang_toggle"):
            assert key in en_keys, f"Required i18n key '{key}' missing from EN strings"

    def test_en_has_form_keys(self, en_keys):
        for key in ("form_title", "form_name", "form_email", "form_submit",
                    "form_consent", "form_success", "form_error"):
            assert key in en_keys, f"Required form key '{key}' missing from EN strings"


# ================================================================
# TestPWAManifest — manifest.json
# ================================================================

class TestPWAManifest:
    """Validate manifest.json PWA requirements."""

    @pytest.fixture(scope="class")
    def manifest(self):
        raw = MANIFEST_JSON.read_text(encoding="utf-8")
        return json.loads(raw)

    def test_file_exists(self):
        assert MANIFEST_JSON.exists(), f"manifest.json not found at {MANIFEST_JSON}"

    def test_valid_json(self):
        raw = MANIFEST_JSON.read_text(encoding="utf-8")
        try:
            json.loads(raw)
        except json.JSONDecodeError as exc:
            pytest.fail(f"manifest.json is not valid JSON: {exc}")

    def test_has_name(self, manifest):
        assert "name" in manifest and manifest["name"], "manifest.json missing 'name' field"

    def test_has_short_name(self, manifest):
        assert "short_name" in manifest and manifest["short_name"], \
            "manifest.json missing 'short_name' field"

    def test_has_start_url(self, manifest):
        assert "start_url" in manifest and manifest["start_url"], \
            "manifest.json missing 'start_url' field"

    def test_has_display(self, manifest):
        assert "display" in manifest, "manifest.json missing 'display' field"

    def test_display_is_standalone(self, manifest):
        assert manifest.get("display") == "standalone", \
            f"manifest display should be 'standalone', got '{manifest.get('display')}'"

    def test_has_icons(self, manifest):
        assert "icons" in manifest and manifest["icons"], \
            "manifest.json missing 'icons' array"

    def test_has_at_least_two_icon_sizes(self, manifest):
        icons = manifest.get("icons", [])
        sizes = [icon.get("sizes") for icon in icons if icon.get("sizes")]
        assert len(sizes) >= 2, \
            f"manifest.json should have at least 2 icon sizes, found {len(sizes)}: {sizes}"

    def test_scope_is_kosei(self, manifest):
        assert manifest.get("scope") == "/kosei/", \
            f"manifest.json scope should be '/kosei/', got '{manifest.get('scope')}'"

    def test_name_value(self, manifest):
        assert manifest["name"] == "Kosei AI Systems", \
            f"Unexpected manifest name: '{manifest['name']}'"

    def test_short_name_value(self, manifest):
        assert manifest["short_name"] == "Kosei", \
            f"Unexpected manifest short_name: '{manifest['short_name']}'"

    def test_start_url_value(self, manifest):
        assert manifest["start_url"] == "/kosei/", \
            f"Unexpected start_url: '{manifest['start_url']}'"


# ================================================================
# TestServiceWorker — sw.js
# ================================================================

class TestServiceWorker:
    """Validate service worker correctness and NEVER_CACHE contract."""

    @pytest.fixture(scope="class")
    def sw(self):
        return SW_JS.read_text(encoding="utf-8")

    def test_file_exists(self):
        assert SW_JS.exists(), f"sw.js not found at {SW_JS}"

    def test_defines_cache_name(self, sw):
        assert re.search(r"const\s+CACHE_NAME\s*=", sw), \
            "sw.js does not define CACHE_NAME constant"

    def test_cache_name_value(self, sw):
        match = re.search(r"const\s+CACHE_NAME\s*=\s*['\"]([^'\"]+)['\"]", sw)
        assert match, "Could not parse CACHE_NAME value from sw.js"
        assert match.group(1).startswith("kosei-"), \
            f"CACHE_NAME should start with 'kosei-', got '{match.group(1)}'"

    def test_install_event_listener(self, sw):
        assert re.search(
            r"self\.addEventListener\s*\(\s*['\"]install['\"]", sw
        ), "sw.js missing 'install' event listener"

    def test_activate_event_listener(self, sw):
        assert re.search(
            r"self\.addEventListener\s*\(\s*['\"]activate['\"]", sw
        ), "sw.js missing 'activate' event listener"

    def test_fetch_event_listener(self, sw):
        assert re.search(
            r"self\.addEventListener\s*\(\s*['\"]fetch['\"]", sw
        ), "sw.js missing 'fetch' event listener"

    def test_never_cache_list_exists(self, sw):
        assert "NEVER_CACHE" in sw, "sw.js does not define NEVER_CACHE list"

    def test_never_cache_includes_firebaseapp(self, sw):
        assert "firebaseapp.com" in sw, \
            "NEVER_CACHE should include 'firebaseapp.com'"

    def test_never_cache_includes_firestore(self, sw):
        assert "firestore.googleapis.com" in sw, \
            "NEVER_CACHE should include 'firestore.googleapis.com'"

    def test_never_cache_includes_gstatic_firebase(self, sw):
        assert "gstatic.com/firebasejs" in sw, \
            "NEVER_CACHE should include 'gstatic.com/firebasejs'"

    def test_never_cache_includes_identitytoolkit(self, sw):
        assert "googleapis.com/identitytoolkit" in sw, \
            "NEVER_CACHE should include 'googleapis.com/identitytoolkit'"

    def test_does_not_cache_firebase_sdk_url(self, sw):
        """The STATIC_ASSETS pre-cache list must not include Firebase CDN URLs."""
        static_match = re.search(
            r"const\s+STATIC_ASSETS\s*=\s*\[([^\]]+)\]", sw, re.DOTALL
        )
        assert static_match, "Could not locate STATIC_ASSETS list in sw.js"
        static_block = static_match.group(1)
        assert "gstatic.com/firebasejs" not in static_block, \
            "Firebase SDK CDN URL must not appear in STATIC_ASSETS (NEVER_CACHE conflict)"
        assert "firebase" not in static_block.lower(), \
            "Firebase-related URL must not appear in STATIC_ASSETS"

    def test_skips_non_get_requests(self, sw):
        """Service worker must not intercept non-GET requests (protects form POST)."""
        assert re.search(
            r'method\s*!==\s*["\']GET["\']', sw
        ), "sw.js should skip non-GET requests to protect form submissions"


# ================================================================
# TestFirestoreIntegration — kosei-intake.js
# ================================================================

class TestFirestoreIntegration:
    """Validate intake form handler against the KOSEI_DATA_MODEL contract."""

    @pytest.fixture(scope="class")
    def intake(self):
        return INTAKE_JS.read_text(encoding="utf-8")

    def test_file_exists(self):
        assert INTAKE_JS.exists(), f"kosei-intake.js not found at {INTAKE_JS}"

    def test_references_collection_name(self, intake):
        assert "kosei_audit_requests" in intake, \
            "kosei-intake.js must reference Firestore collection 'kosei_audit_requests'"

    def test_document_has_lead_source(self, intake):
        assert "lead_source" in intake, \
            "Audit request document missing 'lead_source' field"

    def test_document_has_contact_email(self, intake):
        assert "contact_email" in intake, \
            "Audit request document missing 'contact_email' field"

    def test_document_has_locale(self, intake):
        assert "locale" in intake, \
            "Audit request document missing 'locale' field"

    def test_document_has_audit_status(self, intake):
        assert "audit_status" in intake, \
            "Audit request document missing 'audit_status' field"

    def test_audit_status_default_pending(self, intake):
        assert re.search(r"audit_status\s*:\s*['\"]pending['\"]", intake), \
            "audit_status should default to 'pending'"

    def test_document_has_platform_handles(self, intake):
        assert "platform_handles" in intake, \
            "Audit request document missing 'platform_handles' field"

    def test_localstorage_fallback_exists(self, intake):
        assert "localStorage" in intake, \
            "kosei-intake.js must include a localStorage fallback for offline resilience"

    def test_localstorage_fallback_key(self, intake):
        assert "kosei_pending_audits" in intake, \
            "localStorage fallback key 'kosei_pending_audits' not found"

    def test_email_validation_present(self, intake):
        assert re.search(r"formData\.email", intake), \
            "kosei-intake.js must validate formData.email"

    def test_email_required_guard(self, intake):
        """Guard clause that bails early when email is falsy must exist."""
        assert re.search(r"if\s*\(\s*!formData\.email\s*\)", intake), \
            "Missing email-required guard: 'if (!formData.email)'"

    def test_platform_handles_builder_function(self, intake):
        assert "buildPlatformHandles" in intake, \
            "buildPlatformHandles() helper function not found in kosei-intake.js"

    def test_exports_window_koseiIntake(self, intake):
        assert "window.koseiIntake" in intake, \
            "kosei-intake.js must export window.koseiIntake for init() binding"


# ================================================================
# TestBoundaryEnforcement — landing page isolation
# ================================================================

class TestBoundaryEnforcement:
    """Confirm the landing page does not bleed into app / admin / auth space."""

    @pytest.fixture(scope="class")
    def html(self):
        return INDEX_HTML.read_text(encoding="utf-8")

    @pytest.fixture(scope="class")
    def i18n_js(self):
        return I18N_JS.read_text(encoding="utf-8")

    @pytest.fixture(scope="class")
    def intake_js(self):
        return INTAKE_JS.read_text(encoding="utf-8")

    def test_no_app_route_in_form_action(self, html):
        """No form action should point into the /app/ namespace."""
        form_tags = re.findall(r'<form\b[^>]*>', html, re.IGNORECASE)
        for tag in form_tags:
            assert "/app/" not in tag, \
                f"Form action must not reference /app/ route: {tag}"

    def test_no_admin_route_in_form_action(self, html):
        """No form action should point into the /admin/ namespace."""
        form_tags = re.findall(r'<form\b[^>]*>', html, re.IGNORECASE)
        for tag in form_tags:
            assert "/admin/" not in tag, \
                f"Form action must not reference /admin/ route: {tag}"

    def test_no_firebase_auth_import_in_landing_scripts(self, html):
        """Firebase Auth SDK must not be imported from the landing page HTML."""
        assert "firebase-auth" not in html, \
            "firebase-auth SDK must not be imported on the public landing page"

    def test_no_firebase_auth_import_in_intake(self, intake_js):
        """Intake handler must use only Firestore — no Auth SDK."""
        assert "firebase-auth" not in intake_js, \
            "kosei-intake.js must not import firebase-auth (landing page boundary)"

    def test_no_autopost_references_in_html(self, html):
        """AutoPost is a separate module — no references in the landing page."""
        assert "autopost" not in html.lower() and "auto_post" not in html.lower(), \
            "AutoPost references must not appear in the Kosei landing page"

    def test_no_autopost_references_in_i18n(self, i18n_js):
        assert "autopost" not in i18n_js.lower() and "auto_post" not in i18n_js.lower(), \
            "AutoPost references must not appear in kosei-i18n.js"

    def test_no_autopost_references_in_intake(self, intake_js):
        assert "autopost" not in intake_js.lower() and "auto_post" not in intake_js.lower(), \
            "AutoPost references must not appear in kosei-intake.js"

    def test_sw_js_does_not_cache_app_routes(self):
        """Service worker STATIC_ASSETS must not pre-cache any /app/ routes."""
        sw_content = SW_JS.read_text(encoding="utf-8")
        static_match = re.search(
            r"const\s+STATIC_ASSETS\s*=\s*\[([^\]]+)\]", sw_content, re.DOTALL
        )
        assert static_match, "Could not locate STATIC_ASSETS in sw.js"
        static_block = static_match.group(1)
        assert "/app/" not in static_block, \
            "sw.js STATIC_ASSETS must not include /app/ routes (landing-only scope)"

    def test_landing_serves_only_kosei_scope(self):
        """manifest.json scope must be /kosei/ — not / or /app/."""
        manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
        scope = manifest.get("scope", "")
        assert scope == "/kosei/", \
            f"manifest scope must be '/kosei/' to isolate the landing PWA, got '{scope}'"


# ================================================================
# TestTruthfulRoutes — every href must resolve to a real surface (WSP 97)
# ================================================================

class TestTruthfulRoutes:
    """No dead /kosei/ subroutes. The only deployed kosei surfaces are
    the landing (/kosei/) and the app mount (/kosei/app/)."""

    @pytest.fixture(scope="class")
    def html(self):
        return INDEX_HTML.read_text(encoding="utf-8")

    def test_no_dead_login_route(self, html):
        assert "/kosei/login" not in html, \
            "Dead route /kosei/login must not appear (use /kosei/app/ - the real auth gate)"

    def test_no_dead_pricing_route(self, html):
        assert "/kosei/pricing" not in html, \
            "Dead route /kosei/pricing must not appear (pricing is an on-page #pricing anchor)"

    def test_no_dead_privacy_route(self, html):
        assert "/kosei/privacy" not in html, \
            "Dead route /kosei/privacy must not appear (no privacy page deployed)"

    def test_no_dead_terms_route(self, html):
        assert "/kosei/terms" not in html, \
            "Dead route /kosei/terms must not appear (no terms page deployed)"

    def test_client_login_points_at_app_mount(self, html):
        """Both nav and footer 'Client Login' must resolve to /kosei/app/."""
        login_hrefs = re.findall(
            r'href=["\']([^"\']*)["\'][^>]*data-i18n=["\']nav_login["\']', html
        )
        assert login_hrefs, "No href found bound to data-i18n='nav_login'"
        for href in login_hrefs:
            assert href == "/kosei/app/", \
                f"nav_login href must be '/kosei/app/', got '{href}'"


# ================================================================
# TestMojibakeFree — landing sources decode as clean UTF-8 (WSP 97)
# ================================================================

class TestMojibakeFree:
    """Every landing file must be UTF-8-clean with no replacement chars or
    double-encoded sequences. Valid non-ASCII (emoji, em-dash, JP glyphs)
    is fine; garbled glyphs are not."""

    TARGETS = [INDEX_HTML, MANIFEST_JSON, SW_JS, I18N_JS, INTAKE_JS]

    # Byte sequences that indicate mis-decoded UTF-8 shown as Latin-1.
    BAD_SEQUENCES = [
        b"\xef\xbf\xbd",              # U+FFFD replacement char
        b"\xc3\x82\xc2",              # classic Â... mojibake
        b"\xc3\x83\xc2",              # double-encoded
        b"\xc3\xaf\xc2\xbb\xc2\xbf",  # double-encoded BOM
    ]

    @pytest.mark.parametrize("target", TARGETS, ids=lambda p: p.name)
    def test_file_is_valid_utf8(self, target):
        raw = target.read_bytes()
        try:
            raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            pytest.fail(f"{target} is not valid UTF-8: {exc}")

    @pytest.mark.parametrize("target", TARGETS, ids=lambda p: p.name)
    def test_file_has_no_mojibake_sequences(self, target):
        raw = target.read_bytes()
        for seq in self.BAD_SEQUENCES:
            assert seq not in raw, \
                f"{target} contains mojibake byte sequence {seq.hex()}"


# ================================================================
# TestDeployParity — public/kosei/ mirrors the source landing exactly
# ================================================================

class TestDeployParity:
    """The Firebase deploy target public/kosei/ must match the module source
    modules/foundups/kosei/frontend/ byte-for-byte, so what ships is what the
    module audits."""

    REPO_ROOT = MODULE_ROOT.parent.parent.parent  # modules/foundups/kosei -> repo root
    DEPLOY_ROOT = REPO_ROOT / "public" / "kosei"

    PAIRS = [
        ("index.html", "index.html"),
        ("manifest.json", "manifest.json"),
        ("sw.js", "sw.js"),
        ("js/kosei-i18n.js", "js/kosei-i18n.js"),
        ("js/kosei-intake.js", "js/kosei-intake.js"),
    ]

    @pytest.mark.parametrize("source_rel,deploy_rel", PAIRS,
                             ids=[s for s, _ in PAIRS])
    def test_source_and_deploy_match(self, source_rel, deploy_rel):
        src = FRONTEND_ROOT / source_rel
        dst = self.DEPLOY_ROOT / deploy_rel
        assert src.exists(), f"Source missing: {src}"
        assert dst.exists(), f"Deploy target missing: {dst}"
        assert src.read_bytes() == dst.read_bytes(), (
            f"Deploy target {dst} drifted from source {src}. "
            "Re-sync public/kosei/ after editing modules/foundups/kosei/frontend/."
        )
