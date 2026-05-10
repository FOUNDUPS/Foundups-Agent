"""Link Sentinel - Static Analyzer Tests

Status: POC_IMPLEMENTED
WSP: 97 (Truth Boundaries)

Tests for static URL analysis. No network calls performed.
"""

import pytest
from unittest.mock import patch

from modules.infrastructure.link_sentinel.src.analyzer import analyze_link
from modules.infrastructure.link_sentinel.src.models import (
    LinkContext,
    LinkDecision,
    DecisionAction,
    RiskReasonCode,
)


class TestBasicURLAnalysis:
    """Test basic URL parsing and decisions."""

    def test_normal_https_url_allowed(self):
        """Normal HTTPS URL should be allowed."""
        result = analyze_link("https://example.com/page")

        assert result.decision == DecisionAction.ALLOW
        assert result.risk_score == 0.0
        assert RiskReasonCode.CLEAN in result.reason_codes
        assert result.scheme == "https"
        assert result.host == "example.com"

    def test_normal_http_url_allowed(self):
        """Normal HTTP URL should be allowed."""
        result = analyze_link("http://example.org/path/to/resource")

        assert result.decision == DecisionAction.ALLOW
        assert result.scheme == "http"
        assert result.host == "example.org"

    def test_url_with_port_allowed(self):
        """URL with explicit port should be allowed."""
        result = analyze_link("https://example.com:8443/api")

        assert result.decision == DecisionAction.ALLOW
        assert result.port == 8443

    def test_url_with_query_allowed(self):
        """URL with query string should be allowed."""
        result = analyze_link("https://example.com/search?q=test&page=1")

        assert result.decision == DecisionAction.ALLOW
        assert "q=test" in result.normalized_url


class TestInvalidURLs:
    """Test invalid and missing URL handling."""

    def test_empty_url_blocked(self):
        """Empty URL should be blocked."""
        result = analyze_link("")

        assert result.decision == DecisionAction.BLOCK
        assert RiskReasonCode.EMPTY_URL in result.reason_codes
        assert result.risk_score == 1.0

    def test_whitespace_only_url_blocked(self):
        """Whitespace-only URL should be blocked."""
        result = analyze_link("   ")

        assert result.decision == DecisionAction.BLOCK
        assert RiskReasonCode.EMPTY_URL in result.reason_codes

    def test_none_url_blocked(self):
        """None URL should be blocked."""
        result = analyze_link(None)

        assert result.decision == DecisionAction.BLOCK

    def test_missing_host_blocked(self):
        """URL without host should be blocked."""
        result = analyze_link("https:///path")

        assert result.decision == DecisionAction.BLOCK
        assert RiskReasonCode.MISSING_HOST in result.reason_codes


class TestUnsupportedSchemes:
    """Test unsupported URL schemes."""

    def test_javascript_scheme_quarantined(self):
        """JavaScript scheme should be quarantined."""
        result = analyze_link("javascript:alert(1)")

        assert result.decision == DecisionAction.QUARANTINE
        assert RiskReasonCode.UNSUPPORTED_SCHEME in result.reason_codes

    def test_file_scheme_quarantined(self):
        """File scheme should be quarantined."""
        result = analyze_link("file:///etc/passwd")

        assert result.decision == DecisionAction.QUARANTINE
        assert RiskReasonCode.UNSUPPORTED_SCHEME in result.reason_codes

    def test_data_scheme_quarantined(self):
        """Data scheme should be quarantined."""
        result = analyze_link("data:text/html,<h1>test</h1>")

        assert result.decision == DecisionAction.QUARANTINE
        assert RiskReasonCode.UNSUPPORTED_SCHEME in result.reason_codes

    def test_ftp_scheme_quarantined(self):
        """FTP scheme should be quarantined."""
        result = analyze_link("ftp://ftp.example.com/file.txt")

        assert result.decision == DecisionAction.QUARANTINE
        assert RiskReasonCode.UNSUPPORTED_SCHEME in result.reason_codes


class TestLocalhost:
    """Test localhost detection."""

    def test_localhost_blocked(self):
        """Localhost should be blocked."""
        result = analyze_link("http://localhost/admin")

        assert result.decision == DecisionAction.BLOCK
        assert RiskReasonCode.LOCALHOST in result.reason_codes
        assert result.risk_score >= 0.9

    def test_localhost_localdomain_blocked(self):
        """localhost.localdomain should be blocked."""
        result = analyze_link("http://localhost.localdomain/")

        assert result.decision == DecisionAction.BLOCK
        assert RiskReasonCode.LOCALHOST in result.reason_codes

    def test_127_0_0_1_blocked(self):
        """127.0.0.1 should be blocked."""
        result = analyze_link("http://127.0.0.1:8080/api")

        assert result.decision == DecisionAction.BLOCK
        assert RiskReasonCode.LOOPBACK_IP in result.reason_codes


class TestPrivateIP:
    """Test private IP detection."""

    def test_private_ip_10_blocked(self):
        """10.x.x.x private IP should be blocked."""
        result = analyze_link("http://10.0.0.1/internal")

        assert result.decision == DecisionAction.BLOCK
        assert RiskReasonCode.PRIVATE_IP in result.reason_codes

    def test_private_ip_172_blocked(self):
        """172.16.x.x private IP should be blocked."""
        result = analyze_link("http://172.16.0.1/internal")

        assert result.decision == DecisionAction.BLOCK
        assert RiskReasonCode.PRIVATE_IP in result.reason_codes

    def test_private_ip_192_blocked(self):
        """192.168.x.x private IP should be blocked."""
        result = analyze_link("http://192.168.1.1/router")

        assert result.decision == DecisionAction.BLOCK
        assert RiskReasonCode.PRIVATE_IP in result.reason_codes


class TestLinkLocalIP:
    """Test link-local IP detection."""

    def test_link_local_ipv4_blocked(self):
        """169.254.x.x link-local IP should be blocked."""
        result = analyze_link("http://169.254.169.254/metadata")

        assert result.decision == DecisionAction.BLOCK
        assert RiskReasonCode.LINK_LOCAL_IP in result.reason_codes


class TestCredentialsInURL:
    """Test credential detection in URLs."""

    def test_username_in_url_quarantined(self):
        """URL with username should be quarantined."""
        result = analyze_link("https://user@example.com/page")

        assert result.decision == DecisionAction.QUARANTINE
        assert RiskReasonCode.CREDENTIALS_IN_URL in result.reason_codes

    def test_username_password_in_url_quarantined(self):
        """URL with username:password should be quarantined."""
        result = analyze_link("https://user:pass@example.com/page")

        assert result.decision == DecisionAction.QUARANTINE
        assert RiskReasonCode.CREDENTIALS_IN_URL in result.reason_codes


class TestPunycodeDomain:
    """Test punycode domain detection."""

    def test_punycode_domain_warned(self):
        """Punycode domain should trigger warning."""
        # xn--n3h is punycode for a Unicode domain
        result = analyze_link("https://xn--n3h.com/")

        assert result.decision == DecisionAction.WARN
        assert RiskReasonCode.PUNYCODE_DOMAIN in result.reason_codes
        assert result.punycode_host is not None

    def test_punycode_subdomain_warned(self):
        """Punycode in subdomain should trigger warning."""
        result = analyze_link("https://xn--80ak6aa92e.example.com/")

        assert result.decision == DecisionAction.WARN
        assert RiskReasonCode.PUNYCODE_DOMAIN in result.reason_codes


class TestURLShortener:
    """Test URL shortener detection."""

    def test_bitly_warned(self):
        """bit.ly should trigger warning."""
        result = analyze_link("https://bit.ly/abc123")

        assert result.decision == DecisionAction.WARN
        assert RiskReasonCode.URL_SHORTENER in result.reason_codes

    def test_tinyurl_warned(self):
        """tinyurl.com should trigger warning."""
        result = analyze_link("https://tinyurl.com/xyz789")

        assert result.decision == DecisionAction.WARN
        assert RiskReasonCode.URL_SHORTENER in result.reason_codes

    def test_t_co_warned(self):
        """t.co should trigger warning."""
        result = analyze_link("https://t.co/abcdef")

        assert result.decision == DecisionAction.WARN
        assert RiskReasonCode.URL_SHORTENER in result.reason_codes


class TestExcessiveSubdomains:
    """Test excessive subdomain detection."""

    def test_excessive_subdomains_warned(self):
        """Too many subdomains should trigger warning."""
        result = analyze_link("https://a.b.c.d.e.example.com/")

        assert result.decision == DecisionAction.WARN
        assert RiskReasonCode.EXCESSIVE_SUBDOMAINS in result.reason_codes

    def test_normal_subdomain_allowed(self):
        """Normal subdomain depth should be allowed."""
        result = analyze_link("https://www.api.example.com/")

        assert result.decision == DecisionAction.ALLOW
        assert RiskReasonCode.EXCESSIVE_SUBDOMAINS not in result.reason_codes


class TestNormalizedURL:
    """Test URL normalization stability."""

    def test_normalized_url_stable(self):
        """Same URL should produce same normalized form."""
        url = "https://EXAMPLE.COM/PATH"

        result1 = analyze_link(url)
        result2 = analyze_link(url)

        assert result1.normalized_url == result2.normalized_url
        assert result1.host == result2.host

    def test_www_normalized(self):
        """www. prefix should be normalized away."""
        result = analyze_link("https://www.example.com/")

        assert "www." not in result.normalized_url
        assert result.host == "example.com"

    def test_default_port_normalized(self):
        """Default ports should be normalized away."""
        result = analyze_link("https://example.com:443/")

        assert ":443" not in result.normalized_url

    def test_uppercase_host_normalized(self):
        """Uppercase host should be normalized to lowercase."""
        result = analyze_link("https://EXAMPLE.COM/Page")

        assert result.host == "example.com"


class TestAuditID:
    """Test audit ID generation."""

    def test_audit_id_present(self):
        """Audit ID should always be present."""
        result = analyze_link("https://example.com/")

        assert result.audit_id is not None
        assert len(result.audit_id) > 0

    def test_audit_id_unique(self):
        """Different calls should produce different audit IDs."""
        result1 = analyze_link("https://example.com/")
        result2 = analyze_link("https://example.com/")

        assert result1.audit_id != result2.audit_id


class TestContextPreservation:
    """Test context field preservation."""

    def test_context_preserved(self):
        """Context should be preserved in decision."""
        context = LinkContext(
            surface="browser_actions",
            actor_id="user123",
            actor_tier="verified",
            foundup_id="gotjunk",
            dao_id="dao1",
            correlation_id="corr-abc-123"
        )

        result = analyze_link("https://example.com/", context=context)

        assert result.context is not None
        assert result.context.surface == "browser_actions"
        assert result.context.actor_id == "user123"
        assert result.context.foundup_id == "gotjunk"
        assert result.context.correlation_id == "corr-abc-123"

    def test_no_context_is_none(self):
        """Missing context should be None."""
        result = analyze_link("https://example.com/")

        assert result.context is None


class TestNoNetworkCalls:
    """Verify no network calls are made."""

    def test_no_socket_calls(self):
        """No socket calls should be made during analysis."""
        with patch("socket.socket") as mock_socket:
            analyze_link("https://example.com/")
            mock_socket.assert_not_called()

    def test_no_dns_resolution(self):
        """No DNS resolution should be performed."""
        with patch("socket.getaddrinfo") as mock_dns:
            analyze_link("https://example.com/")
            mock_dns.assert_not_called()


class TestTruthFlags:
    """Test WSP 97 truth flags."""

    def test_analysis_type_static(self):
        """Analysis type should be static."""
        result = analyze_link("https://example.com/")

        assert result.analysis_type == "static"

    def test_redirect_not_resolved(self):
        """Redirect should not be resolved."""
        result = analyze_link("https://bit.ly/abc")

        assert result.redirect_resolved is False

    def test_reputation_not_checked(self):
        """Reputation should not be checked."""
        result = analyze_link("https://example.com/")

        assert result.reputation_checked is False

    def test_sandbox_not_analyzed(self):
        """Sandbox should not be analyzed."""
        result = analyze_link("https://example.com/")

        assert result.sandbox_analyzed is False


class TestNumericHost:
    """Test numeric host (public IP) handling."""

    def test_public_ip_warned(self):
        """Public IP should trigger warning."""
        result = analyze_link("http://8.8.8.8/")

        assert result.decision == DecisionAction.WARN
        assert RiskReasonCode.NUMERIC_HOST in result.reason_codes


class TestSuspiciousTLD:
    """Test suspicious TLD detection."""

    def test_xyz_tld_warned(self):
        """.xyz TLD should trigger warning."""
        result = analyze_link("https://example.xyz/")

        assert result.decision == DecisionAction.WARN
        assert RiskReasonCode.SUSPICIOUS_TLD in result.reason_codes

    def test_normal_tld_allowed(self):
        """.com TLD should be allowed."""
        result = analyze_link("https://example.com/")

        assert result.decision == DecisionAction.ALLOW
        assert RiskReasonCode.SUSPICIOUS_TLD not in result.reason_codes


class TestSchemeNormalization:
    """Test URL scheme handling."""

    def test_missing_scheme_defaults_to_https(self):
        """Missing scheme should default to https."""
        result = analyze_link("example.com/page")

        assert result.scheme == "https"
        assert result.normalized_url.startswith("https://")

    def test_scheme_relative_url(self):
        """Scheme-relative URL should default to https."""
        result = analyze_link("//example.com/page")

        assert result.scheme == "https"
