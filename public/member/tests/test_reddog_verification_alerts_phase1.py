#!/usr/bin/env python3
"""Tests for RedDog verification alert skeleton (PFM9 Phase 1).

Validates:
  1. Verification alert storage variables exist
  2. showVerificationAlert() method exists with correct signature
  3. dismissVerificationAlert() method exists with correct signature
  4. getVerificationAlertCount() method exists
  5. getVerificationAlerts() method exists
  6. Event listener for 'reddog:verification_alert' exists
  7. WSP 97 truth boundary comments present

WSP Compliance:
  WSP 97: RedDog may notify/summarize/open panels. RedDog may NOT judge/deny/finalize.
  WSP 11: Interface contract for verification alerts.

Slice: PFM9_REDDOG_VERIFICATION_ALERT_SKELETON_PHASE1
"""

import re
from pathlib import Path

import pytest

MEMBER_ROOT = Path(__file__).resolve().parents[1]
CONCIERGE_JS = MEMBER_ROOT / "js" / "account-concierge.js"
INTERFACE_MD = MEMBER_ROOT / "INTERFACE.md"


# -- 1. Verification alert storage --


class TestVerificationAlertStorage:
    """Verify in-memory storage variables exist."""

    def test_verification_alerts_var_exists(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "var verificationAlerts = {}" in content

    def test_verification_alert_count_var_exists(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "var verificationAlertCount = 0" in content

    def test_storage_has_wsp97_comment(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "WSP 97" in content
        assert "may notify" in content.lower() or "may NOT" in content


# -- 2. showVerificationAlert method --


class TestShowVerificationAlert:
    """Verify showVerificationAlert method exists with correct structure."""

    def test_method_exists(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "showVerificationAlert:" in content or "showVerificationAlert =" in content

    def test_method_accepts_alert_param(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert re.search(r"showVerificationAlert\s*:\s*function\s*\(\s*alert\s*\)", content)

    def test_validates_alert_object(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Should check that alert is an object
        assert "typeof alert" in content

    def test_validates_alert_id(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Should check that alert_id exists
        assert "alert.alert_id" in content or "alert_id" in content

    def test_stores_in_verification_alerts(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "verificationAlerts[" in content

    def test_increments_count(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "verificationAlertCount++" in content

    def test_returns_boolean(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Method should return true or false
        method_match = re.search(
            r"showVerificationAlert\s*:\s*function.*?(?=\n\s*\w+\s*:|$)",
            content,
            re.DOTALL
        )
        assert method_match
        method_body = method_match.group()
        assert "return true" in method_body or "return false" in method_body


# -- 3. dismissVerificationAlert method --


class TestDismissVerificationAlert:
    """Verify dismissVerificationAlert method exists with correct structure."""

    def test_method_exists(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "dismissVerificationAlert:" in content or "dismissVerificationAlert =" in content

    def test_method_accepts_alertid_param(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert re.search(r"dismissVerificationAlert\s*:\s*function\s*\(\s*alertId\s*\)", content)

    def test_deletes_from_storage(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "delete verificationAlerts[" in content

    def test_decrements_count(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Should decrement but not go below 0
        assert "verificationAlertCount" in content
        assert "Math.max(0" in content or "verificationAlertCount--" in content


# -- 4. getVerificationAlertCount method --


class TestGetVerificationAlertCount:
    """Verify count getter exists."""

    def test_method_exists(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "getVerificationAlertCount:" in content

    def test_returns_count(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert re.search(r"getVerificationAlertCount.*return\s+verificationAlertCount", content, re.DOTALL)


# -- 5. getVerificationAlerts method --


class TestGetVerificationAlerts:
    """Verify alerts getter exists."""

    def test_method_exists(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "getVerificationAlerts:" in content

    def test_returns_copy_not_reference(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Should create a copy to prevent external mutation
        method_match = re.search(
            r"getVerificationAlerts\s*:\s*function.*?(?=\n\s*\w+\s*:|};)",
            content,
            re.DOTALL
        )
        assert method_match
        method_body = method_match.group()
        # Should create a copy (var copy = {} or Object.assign or spread)
        assert "copy" in method_body or "Object.assign" in method_body


# -- 6. Event listener --


class TestVerificationAlertEventListener:
    """Verify event listener for reddog:verification_alert exists."""

    def test_event_listener_exists(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reddog:verification_alert" in content

    def test_listener_uses_addeventlistener(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert re.search(r"addEventListener\s*\(\s*['\"]reddog:verification_alert['\"]", content)

    def test_listener_calls_show_method(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Listener should call showVerificationAlert with event detail
        assert "showVerificationAlert" in content
        assert "e.detail" in content or "event.detail" in content


# -- 7. WSP 97 truth boundary --


class TestWSP97TruthBoundary:
    """Verify WSP 97 compliance comments are present."""

    def test_wsp97_reference_in_storage_section(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Find the storage section and check for WSP 97
        storage_idx = content.find("verification alerts (skeleton)")
        assert storage_idx != -1, "Skeleton section comment must exist"
        section = content[storage_idx:storage_idx + 300]
        assert "WSP 97" in section

    def test_wsp97_reference_in_methods_section(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Find the methods section and check for WSP 97
        method_idx = content.find("verification alert skeleton (PFM9)")
        assert method_idx != -1, "Methods section comment must exist"
        section = content[method_idx:method_idx + 300]
        assert "WSP 97" in section

    def test_truth_boundary_statement(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        # Should have the truth boundary statement
        assert "may NOT" in content or "may not" in content
        assert "notify" in content.lower() or "summarize" in content.lower()


# -- 8. INTERFACE.md documentation --


class TestInterfaceDocumentation:
    """Verify INTERFACE.md is updated with new methods."""

    def test_show_method_documented(self):
        content = INTERFACE_MD.read_text(encoding="utf-8")
        assert "showVerificationAlert" in content

    def test_dismiss_method_documented(self):
        content = INTERFACE_MD.read_text(encoding="utf-8")
        assert "dismissVerificationAlert" in content

    def test_count_method_documented(self):
        content = INTERFACE_MD.read_text(encoding="utf-8")
        assert "getVerificationAlertCount" in content

    def test_get_alerts_method_documented(self):
        content = INTERFACE_MD.read_text(encoding="utf-8")
        assert "getVerificationAlerts" in content

    def test_alert_schema_documented(self):
        content = INTERFACE_MD.read_text(encoding="utf-8")
        assert "RedDogVerificationAlert" in content
        assert "alert_id" in content
        assert "event_id" in content
        assert "foundup_id" in content
        assert "action_required" in content

    def test_events_documented(self):
        content = INTERFACE_MD.read_text(encoding="utf-8")
        assert "reddog:verification_alert" in content
        assert "reddog:alert_stored" in content
        assert "reddog:alert_dismissed" in content

    def test_wsp97_documented(self):
        content = INTERFACE_MD.read_text(encoding="utf-8")
        assert "WSP 97" in content


# -- 9. Event emission --


class TestEventEmission:
    """Verify events are emitted on store/dismiss."""

    def test_alert_stored_event_emitted(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reddog:alert_stored" in content

    def test_alert_dismissed_event_emitted(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "reddog:alert_dismissed" in content

    def test_events_use_custom_event(self):
        content = CONCIERGE_JS.read_text(encoding="utf-8")
        assert "new CustomEvent" in content
