"""Tests for Kosei Client Workspace (Phase 1).

Validates HTML structure, auth gating, Firestore collection usage,
data boundary enforcement, and issue submission wiring.
"""

import json
import re
from pathlib import Path

import pytest

MODULE_ROOT = Path(__file__).parent.parent
APP_ROOT = MODULE_ROOT / "app"


class TestClientWorkspaceStructure:
    """HTML structure matches KOSEI_SERVICE_CONTRACT.md Section 1.2."""

    @pytest.fixture(autouse=True)
    def load_html(self):
        self.html = (APP_ROOT / "index.html").read_text(encoding="utf-8")

    def test_file_exists(self):
        assert (APP_ROOT / "index.html").exists()

    def test_html5_doctype(self):
        assert self.html.strip().startswith("<!DOCTYPE html>")

    def test_has_head_and_body(self):
        assert "<head>" in self.html
        assert "<body" in self.html

    def test_meta_viewport(self):
        assert 'name="viewport"' in self.html

    def test_noindex_nofollow(self):
        assert 'content="noindex, nofollow"' in self.html

    def test_title_contains_kosei(self):
        assert "Kosei" in self.html.split("<title>")[1].split("</title>")[0]

    def test_shared_css_loaded(self):
        assert "/kosei/css/kosei.css" in self.html

    def test_app_css_loaded(self):
        assert "/kosei/app/css/kosei-app.css" in self.html

    def test_firebase_app_sdk(self):
        assert "firebase-app-compat.js" in self.html

    def test_firebase_auth_sdk(self):
        assert "firebase-auth-compat.js" in self.html

    def test_firebase_firestore_sdk(self):
        assert "firebase-firestore-compat.js" in self.html

    def test_auth_gate_element(self):
        assert 'id="authGate"' in self.html

    def test_app_shell_element(self):
        assert 'id="appShell"' in self.html

    def test_app_shell_hidden_by_default(self):
        # appShell starts display:none
        assert re.search(r'id="appShell"[^>]*style="display:none', self.html)

    def test_no_workspace_state(self):
        assert 'id="noWorkspace"' in self.html

    def test_google_signin_button(self):
        assert 'id="googleSignIn"' in self.html

    def test_email_signin_fields(self):
        assert 'id="emailInput"' in self.html
        assert 'id="passwordInput"' in self.html

    def test_signout_button(self):
        assert 'id="signOutBtn"' in self.html

    def test_client_email_display(self):
        assert 'id="clientEmail"' in self.html

    def test_tab_dashboard(self):
        assert 'data-tab="dashboard"' in self.html

    def test_tab_platforms(self):
        assert 'data-tab="platforms"' in self.html

    def test_tab_support(self):
        assert 'data-tab="support"' in self.html


class TestDashboardSections:
    """Dashboard shows required sections per mission spec."""

    @pytest.fixture(autouse=True)
    def load_html(self):
        self.html = (APP_ROOT / "index.html").read_text(encoding="utf-8")

    def test_workspace_name(self):
        assert 'id="wsName"' in self.html

    def test_workspace_tier(self):
        assert 'id="wsTier"' in self.html

    def test_workspace_locale(self):
        assert 'id="wsLocale"' in self.html

    def test_trial_section(self):
        assert 'id="trialSection"' in self.html

    def test_trial_days(self):
        assert 'id="trialDays"' in self.html

    def test_trial_usage(self):
        assert 'id="trialUsage"' in self.html

    def test_trial_progress(self):
        assert 'id="trialProgress"' in self.html

    def test_onboarding_step(self):
        assert 'id="onboardStep"' in self.html

    def test_onboarding_checklist(self):
        assert 'id="onboardChecklist"' in self.html

    def test_preferences_section(self):
        assert 'id="preferencesSection"' in self.html

    def test_platforms_list(self):
        assert 'id="platformsList"' in self.html

    # Reporting stats
    def test_stat_created(self):
        assert 'id="statCreated"' in self.html

    def test_stat_published(self):
        assert 'id="statPublished"' in self.html

    def test_stat_pending(self):
        assert 'id="statPending"' in self.html

    def test_stat_replies(self):
        assert 'id="statReplies"' in self.html

    def test_stat_platforms(self):
        assert 'id="statPlatforms"' in self.html

    def test_stat_days_left(self):
        assert 'id="statDaysLeft"' in self.html


class TestIssueSubmission:
    """Issue form and list per KOSEI_DATA_MODEL.md Section 7."""

    @pytest.fixture(autouse=True)
    def load_files(self):
        self.html = (APP_ROOT / "index.html").read_text(encoding="utf-8")
        self.data_js = (APP_ROOT / "js" / "kosei-app-data.js").read_text(encoding="utf-8")

    def test_issue_form_exists(self):
        assert 'id="issueForm"' in self.html

    def test_issue_title_field(self):
        assert 'name="issueTitle"' in self.html

    def test_issue_category_field(self):
        assert 'name="issueCat"' in self.html

    def test_issue_description_field(self):
        assert 'name="issueDesc"' in self.html

    def test_issue_status_display(self):
        assert 'id="issueStatus"' in self.html

    def test_issues_list(self):
        assert 'id="issuesList"' in self.html

    def test_data_layer_writes_kosei_issues(self):
        assert "kosei_issues" in self.data_js

    def test_issue_has_workspace_id(self):
        assert "workspace_id" in self.data_js

    def test_issue_has_author_role_client(self):
        assert "'client'" in self.data_js

    def test_category_options(self):
        assert 'value="general"' in self.html
        assert 'value="bug"' in self.html
        assert 'value="feature_request"' in self.html
        assert 'value="content_issue"' in self.html


class TestFirestoreCollections:
    """Data layer reads correct collections, scoped to workspace."""

    @pytest.fixture(autouse=True)
    def load_data(self):
        self.data_js = (APP_ROOT / "js" / "kosei-app-data.js").read_text(encoding="utf-8")

    def test_reads_workspaces(self):
        assert "kosei_workspaces" in self.data_js

    def test_reads_integrations(self):
        assert "integrations" in self.data_js

    def test_reads_content_queue(self):
        assert "content_queue" in self.data_js

    def test_reads_post_history(self):
        assert "post_history" in self.data_js

    def test_reads_trials(self):
        assert "kosei_trials" in self.data_js

    def test_scoped_by_owner_uid(self):
        assert "owner_uid" in self.data_js

    def test_writes_kosei_issues(self):
        assert "kosei_issues" in self.data_js

    def test_fetches_my_issues(self):
        assert "fetchMyIssues" in self.data_js


class TestAuthGating:
    """Auth module gates access without admin claims."""

    @pytest.fixture(autouse=True)
    def load_auth(self):
        self.auth_js = (APP_ROOT / "js" / "kosei-app-auth.js").read_text(encoding="utf-8")

    def test_firebase_auth_used(self):
        assert "firebase.auth()" in self.auth_js

    def test_google_signin(self):
        assert "GoogleAuthProvider" in self.auth_js

    def test_email_signin(self):
        assert "signInWithEmailAndPassword" in self.auth_js

    def test_no_admin_claim_check(self):
        # Client workspace must NOT check for admin claims
        assert "kosei_admin" not in self.auth_js

    def test_auth_state_listener(self):
        assert "onAuthStateChanged" in self.auth_js

    def test_sign_out(self):
        assert "signOut" in self.auth_js

    def test_exports_window_koseiAppAuth(self):
        assert "window.koseiAppAuth" in self.auth_js


class TestBoundaryEnforcement:
    """Client workspace does not expose admin-only data or AutoPost."""

    @pytest.fixture(autouse=True)
    def load_files(self):
        self.html = (APP_ROOT / "index.html").read_text(encoding="utf-8")
        self.auth_js = (APP_ROOT / "js" / "kosei-app-auth.js").read_text(encoding="utf-8")
        self.data_js = (APP_ROOT / "js" / "kosei-app-data.js").read_text(encoding="utf-8")
        self.ui_js = (APP_ROOT / "js" / "kosei-app-ui.js").read_text(encoding="utf-8")

    def test_no_admin_claim_in_auth(self):
        assert "kosei_admin" not in self.auth_js

    def test_no_operator_notes_in_data(self):
        # Data layer must not read notes subcollection
        # It reads integrations, content_queue, post_history but NOT notes
        assert ".collection('notes')" not in self.data_js

    def test_no_audit_requests_read_in_data(self):
        # Data layer must not query kosei_audit_requests collection
        # (it may appear in JSDoc comments documenting what's excluded)
        assert ".collection('kosei_audit_requests')" not in self.data_js

    def test_no_autopost_in_html(self):
        assert "autopost" not in self.html.lower()

    def test_no_autopost_in_data(self):
        assert "autopost" not in self.data_js.lower()

    def test_no_autopost_in_ui(self):
        assert "autopost" not in self.ui_js.lower()

    def test_no_admin_route_in_html(self):
        # No links to /admin/ from client workspace
        assert "/admin/" not in self.html

    def test_no_billing_category_in_issue_form(self):
        # billing category is admin-only per data model
        assert 'value="billing"' not in self.html

    def test_no_internal_triage_labels(self):
        # No priority=urgent or assigned_to in UI
        assert "assigned_to" not in self.ui_js
        assert "urgent" not in self.html


class TestFileStructure:
    """All required files exist."""

    REQUIRED_FILES = [
        "index.html",
        "css/kosei-app.css",
        "js/kosei-app-auth.js",
        "js/kosei-app-data.js",
        "js/kosei-app-ui.js",
        "README.md",
    ]

    def test_required_files_exist(self):
        for filename in self.REQUIRED_FILES:
            path = APP_ROOT / filename
            assert path.exists(), f"Missing required file: {filename}"

    def test_css_uses_kc_prefix(self):
        css = (APP_ROOT / "css" / "kosei-app.css").read_text(encoding="utf-8")
        assert ".kc-" in css

    def test_css_does_not_use_ka_prefix(self):
        # ka- is admin prefix, kc- is client prefix
        css = (APP_ROOT / "css" / "kosei-app.css").read_text(encoding="utf-8")
        assert ".ka-" not in css
