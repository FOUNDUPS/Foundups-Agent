"""
Test: Kosei Issue Triage and Priority Features

Worker: Y2
Slice: KOSEI_ISSUES_TRIAGE_AND_PRIORITY_PHASE2

Validates:
- Admin Issues tab exists in HTML
- Admin issue subscription path exists
- Admin triage controls exist
- Client priority selector exists
- submitIssue accepts priority parameter
- Client issue list renders priority badge
- Client boundary hides admin-only fields
"""

import pytest
from pathlib import Path

# Module root
KOSEI_ROOT = Path(__file__).parent.parent


class TestAdminIssuesTab:
    """Admin surface: Issues tab and triage controls."""

    def test_admin_html_has_issues_tab(self):
        """Issues tab button must exist in admin HTML."""
        admin_html = KOSEI_ROOT / "admin" / "index.html"
        content = admin_html.read_text(encoding="utf-8")
        assert 'data-tab="issues"' in content, "Missing Issues tab button"
        assert "Issues" in content, "Tab label not found"

    def test_admin_html_has_issues_panel(self):
        """Issues panel section must exist."""
        admin_html = KOSEI_ROOT / "admin" / "index.html"
        content = admin_html.read_text(encoding="utf-8")
        assert 'id="tab-issues"' in content, "Missing Issues panel section"
        assert 'id="issuesList"' in content, "Missing issues list container"

    def test_admin_html_has_issue_filters(self):
        """Status and priority filters must exist."""
        admin_html = KOSEI_ROOT / "admin" / "index.html"
        content = admin_html.read_text(encoding="utf-8")
        assert 'id="issueStatusFilter"' in content, "Missing issue status filter"
        assert 'id="issuePriorityFilter"' in content, "Missing issue priority filter"

    def test_admin_data_has_subscribe_issues(self):
        """subscribeIssues function must exist."""
        admin_data = KOSEI_ROOT / "admin" / "js" / "kosei-admin-data.js"
        content = admin_data.read_text(encoding="utf-8")
        assert "subscribeIssues" in content, "Missing subscribeIssues function"
        assert "_unsubIssues" in content, "Missing issues unsubscribe handle"

    def test_admin_data_has_triage_methods(self):
        """Triage methods must exist."""
        admin_data = KOSEI_ROOT / "admin" / "js" / "kosei-admin-data.js"
        content = admin_data.read_text(encoding="utf-8")
        assert "getIssue" in content, "Missing getIssue function"
        assert "updateIssueStatus" in content, "Missing updateIssueStatus function"
        assert "updateIssuePriority" in content, "Missing updateIssuePriority function"
        assert "resolveIssue" in content, "Missing resolveIssue function"

    def test_admin_ui_has_render_issues(self):
        """renderIssues function must exist."""
        admin_ui = KOSEI_ROOT / "admin" / "js" / "kosei-admin-ui.js"
        content = admin_ui.read_text(encoding="utf-8")
        assert "renderIssues" in content, "Missing renderIssues function"
        assert "_issues" in content, "Missing _issues cache array"

    def test_admin_ui_has_triage_handlers(self):
        """Triage handler functions must exist."""
        admin_ui = KOSEI_ROOT / "admin" / "js" / "kosei-admin-ui.js"
        content = admin_ui.read_text(encoding="utf-8")
        assert "saveIssueTriage" in content, "Missing saveIssueTriage function"
        assert "resolveIssueTriage" in content, "Missing resolveIssueTriage function"
        assert "openIssueDetail" in content, "Missing openIssueDetail function"

    def test_admin_ui_exports_issues(self):
        """renderIssues must be exported."""
        admin_ui = KOSEI_ROOT / "admin" / "js" / "kosei-admin-ui.js"
        content = admin_ui.read_text(encoding="utf-8")
        assert "renderIssues" in content and "window.koseiAdminUI" in content

    def test_admin_css_has_issue_badges(self):
        """Issue status and priority badges must exist."""
        admin_css = KOSEI_ROOT / "admin" / "css" / "kosei-admin.css"
        content = admin_css.read_text(encoding="utf-8")
        assert ".ka-badge--open" in content, "Missing open status badge"
        assert ".ka-badge--resolved" in content, "Missing resolved status badge"
        assert ".ka-badge--priority-low" in content, "Missing low priority badge"
        assert ".ka-badge--priority-urgent" in content, "Missing urgent priority badge"


class TestClientPriorityFeatures:
    """Client surface: Priority selector and display."""

    def test_client_html_has_priority_selector(self):
        """Priority selector must exist in issue form."""
        client_html = KOSEI_ROOT / "app" / "index.html"
        content = client_html.read_text(encoding="utf-8")
        assert 'name="issuePriority"' in content, "Missing priority select field"
        assert 'value="medium" selected' in content, "Medium not default"
        assert 'value="urgent"' in content, "Missing urgent option"

    def test_client_ui_reads_priority(self):
        """handleIssueSubmit must read priority field."""
        client_ui = KOSEI_ROOT / "app" / "js" / "kosei-app-ui.js"
        content = client_ui.read_text(encoding="utf-8")
        assert 'issuePriority' in content, "Not reading issuePriority field"

    def test_client_ui_passes_priority_to_submit(self):
        """submitIssue call must include priority parameter."""
        client_ui = KOSEI_ROOT / "app" / "js" / "kosei-app-ui.js"
        content = client_ui.read_text(encoding="utf-8")
        # Check that submitIssue is called with 4 args (title, desc, cat, priority)
        assert "submitIssue(title, desc, cat, priority)" in content, "Not passing priority to submitIssue"

    def test_client_data_accepts_priority(self):
        """submitIssue function must accept priority parameter."""
        client_data = KOSEI_ROOT / "app" / "js" / "kosei-app-data.js"
        content = client_data.read_text(encoding="utf-8")
        assert "submitIssue(title, description, category, priority)" in content, "Missing priority param"
        assert "priority: priority" in content or 'priority || "medium"' in content

    def test_client_ui_renders_priority_badge(self):
        """Issue list must show priority badge."""
        client_ui = KOSEI_ROOT / "app" / "js" / "kosei-app-ui.js"
        content = client_ui.read_text(encoding="utf-8")
        assert "kc-badge--priority-" in content, "Missing priority badge class in render"

    def test_client_css_has_priority_badges(self):
        """Priority badge styles must exist."""
        client_css = KOSEI_ROOT / "app" / "css" / "kosei-app.css"
        content = client_css.read_text(encoding="utf-8")
        assert ".kc-badge--priority-low" in content, "Missing low priority badge"
        assert ".kc-badge--priority-medium" in content, "Missing medium priority badge"
        assert ".kc-badge--priority-high" in content, "Missing high priority badge"
        assert ".kc-badge--priority-urgent" in content, "Missing urgent priority badge"


class TestClientAdminBoundary:
    """Client must not see admin-only triage fields."""

    def test_client_ui_no_assigned_to(self):
        """Client issue list must NOT show assigned_to field."""
        client_ui = KOSEI_ROOT / "app" / "js" / "kosei-app-ui.js"
        content = client_ui.read_text(encoding="utf-8")
        # In loadIssues / issue card rendering
        # assigned_to should only appear in admin, not in client render
        # Check the issue card template in loadIssues
        lines = content.split('\n')
        in_load_issues = False
        for line in lines:
            if 'async function loadIssues' in line or 'function loadIssues' in line:
                in_load_issues = True
            if in_load_issues and 'assigned_to' in line.lower():
                pytest.fail("Client UI should not render assigned_to field")
            if in_load_issues and line.strip().startswith('//') is False and 'container.innerHTML' in line:
                # We're past the render, stop checking
                pass

    def test_client_html_no_triage_controls(self):
        """Client HTML must not have triage controls."""
        client_html = KOSEI_ROOT / "app" / "index.html"
        content = client_html.read_text(encoding="utf-8")
        assert "issueStatusSelect" not in content, "Client has status triage select"
        assert "issuePrioritySelect" not in content, "Client has priority triage select"
        assert "issueAssignedInput" not in content, "Client has assigned input"
        assert "resolveIssueTriage" not in content, "Client has resolve triage handler"


class TestStatusPriorityModel:
    """Verify status/priority values match KOSEI_DATA_MODEL.md."""

    def test_admin_status_options(self):
        """Admin status filter options match data model."""
        admin_html = KOSEI_ROOT / "admin" / "index.html"
        content = admin_html.read_text(encoding="utf-8")
        expected_statuses = ["open", "in_progress", "waiting_client", "resolved", "closed"]
        for status in expected_statuses:
            assert f'value="{status}"' in content or f"'{status}'" in content, f"Missing status: {status}"

    def test_admin_priority_options(self):
        """Admin priority filter options match data model."""
        admin_html = KOSEI_ROOT / "admin" / "index.html"
        content = admin_html.read_text(encoding="utf-8")
        expected_priorities = ["low", "medium", "high", "urgent"]
        for priority in expected_priorities:
            assert f'value="{priority}"' in content, f"Missing priority: {priority}"

    def test_client_priority_options(self):
        """Client priority selector options match data model."""
        client_html = KOSEI_ROOT / "app" / "index.html"
        content = client_html.read_text(encoding="utf-8")
        expected_priorities = ["low", "medium", "high", "urgent"]
        for priority in expected_priorities:
            assert f'value="{priority}"' in content, f"Missing priority: {priority}"
