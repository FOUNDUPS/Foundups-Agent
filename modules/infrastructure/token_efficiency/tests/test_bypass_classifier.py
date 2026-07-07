#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for Bypass Classifier (P1 Token Efficiency).

Contract: docs/contracts/REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_CONTRACT_PHASE1.md Section 6
WSP: WSP_97, WSP_99

Tests:
    - Every bypass class pattern detection
    - Fail-closed behavior
    - M2M output format
    - Adversarial tests for fake-safe labels hiding sensitive output
"""

from __future__ import annotations

import json

import pytest

from modules.infrastructure.token_efficiency.src.bypass_classifier import (
    BypassClass,
    BypassClassifier,
    BypassDecision,
    get_bypass_classifier,
)


# ============ Fixtures ============ #


@pytest.fixture
def classifier() -> BypassClassifier:
    """Create fresh classifier instance."""
    return BypassClassifier()


# ============ BYPASS_SECURITY Tests ============ #


class TestBypassSecurity:
    """Test BYPASS_SECURITY class detection."""

    def test_detects_cve(self, classifier: BypassClassifier):
        """CVE identifiers must trigger security bypass."""
        output = "Found CVE-2024-12345 in dependency xyz"
        decision = classifier.classify("npm audit", output)
        assert decision.bypassed is True
        assert decision.classification == BypassClass.BYPASS_SECURITY

    def test_detects_vulnerability(self, classifier: BypassClassifier):
        """VULNERABILITY keyword must trigger bypass."""
        output = "VULNERABILITY detected in authentication module"
        decision = classifier.classify("scan", output)
        assert decision.bypassed is True
        assert BypassClass.BYPASS_SECURITY in decision.matched_classes

    def test_detects_exploit(self, classifier: BypassClassifier):
        """EXPLOIT keyword must trigger bypass."""
        output = "Potential EXPLOIT path identified"
        decision = classifier.classify("security check", output)
        assert decision.bypassed is True

    def test_detects_critical_severity(self, classifier: BypassClassifier):
        """CRITICAL: severity marker must trigger bypass."""
        output = "CRITICAL: SQL injection vulnerability found"
        decision = classifier.classify("scan", output)
        assert decision.bypassed is True
        assert decision.classification == BypassClass.BYPASS_SECURITY

    def test_detects_high_severity(self, classifier: BypassClassifier):
        """HIGH: severity marker must trigger bypass."""
        output = "HIGH: XSS vulnerability in user input handler"
        decision = classifier.classify("scan", output)
        assert decision.bypassed is True

    def test_detects_xss(self, classifier: BypassClassifier):
        """XSS keyword must trigger bypass."""
        output = "XSS attack vector found in comment field"
        decision = classifier.classify("semgrep", output)
        assert decision.bypassed is True

    def test_detects_sqli(self, classifier: BypassClassifier):
        """SQLi keyword must trigger bypass."""
        output = "SQLi vulnerability detected in login form"
        decision = classifier.classify("bandit", output)
        assert decision.bypassed is True


# ============ BYPASS_AUTH Tests ============ #


class TestBypassAuth:
    """Test BYPASS_AUTH class detection."""

    def test_detects_token_assignment(self, classifier: BypassClassifier):
        """token= patterns must trigger auth bypass."""
        output = "auth_token=abc123def456"
        decision = classifier.classify("echo", output)
        assert decision.bypassed is True
        assert BypassClass.BYPASS_AUTH in decision.matched_classes

    def test_detects_password_assignment(self, classifier: BypassClassifier):
        """password= patterns must trigger auth bypass."""
        output = "DB_PASSWORD=secretvalue"
        decision = classifier.classify("env", output)
        assert decision.bypassed is True

    def test_detects_api_key(self, classifier: BypassClassifier):
        """api_key patterns must trigger auth bypass."""
        output = "Using api_key for authentication"
        decision = classifier.classify("config", output)
        assert decision.bypassed is True

    def test_detects_bearer_token(self, classifier: BypassClassifier):
        """Bearer token patterns must trigger auth bypass."""
        output = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        decision = classifier.classify("curl", output)
        assert decision.bypassed is True

    def test_detects_openai_key(self, classifier: BypassClassifier):
        """OpenAI-style sk- keys must trigger auth bypass."""
        output = "OPENAI_API_KEY=sk-proj-abc123"
        decision = classifier.classify("env", output)
        assert decision.bypassed is True

    def test_detects_google_key(self, classifier: BypassClassifier):
        """Google AIza keys must trigger auth bypass."""
        output = "GOOGLE_API_KEY=AIzaSyAbc123def456"
        decision = classifier.classify("env", output)
        assert decision.bypassed is True


# ============ BYPASS_PROVENANCE Tests ============ #


class TestBypassProvenance:
    """Test BYPASS_PROVENANCE class detection."""

    def test_detects_signed_by(self, classifier: BypassClassifier):
        """signed by patterns must trigger provenance bypass."""
        output = "This commit was signed by user@example.com"
        decision = classifier.classify("git verify-commit", output)
        assert decision.bypassed is True
        assert BypassClass.BYPASS_PROVENANCE in decision.matched_classes

    def test_detects_git_commit_hash(self, classifier: BypassClassifier):
        """Git commit hashes must trigger provenance bypass."""
        output = "commit abc123def456789 (HEAD -> main)"
        decision = classifier.classify("git log", output)
        assert decision.bypassed is True

    def test_detects_git_diff_command(self, classifier: BypassClassifier):
        """git diff output must trigger provenance bypass."""
        output = "diff --git a/file.py b/file.py"
        decision = classifier.classify("git diff", output)
        assert decision.bypassed is True

    def test_detects_author_field(self, classifier: BypassClassifier):
        """author: fields must trigger provenance bypass."""
        output = "Author: John Doe <john@example.com>"
        decision = classifier.classify("git show", output)
        assert decision.bypassed is True

    def test_sensitive_git_commands_always_bypass(self, classifier: BypassClassifier):
        """Sensitive git commands bypass regardless of output."""
        output = "Just some normal output"
        decision = classifier.classify("git log --oneline", output)
        assert decision.bypassed is True
        assert decision.classification == BypassClass.BYPASS_PROVENANCE


# ============ BYPASS_SIGNING Tests ============ #


class TestBypassSigning:
    """Test BYPASS_SIGNING class detection."""

    def test_detects_signature_field(self, classifier: BypassClassifier):
        """signature: fields must trigger signing bypass."""
        output = "signature: abc123def456"
        decision = classifier.classify("verify", output)
        assert decision.bypassed is True
        assert BypassClass.BYPASS_SIGNING in decision.matched_classes

    def test_detects_pem_begin(self, classifier: BypassClassifier):
        """PEM BEGIN markers must trigger signing bypass."""
        output = "-----BEGIN RSA PRIVATE KEY-----"
        decision = classifier.classify("cat key.pem", output)
        assert decision.bypassed is True

    def test_detects_pem_end(self, classifier: BypassClassifier):
        """PEM END markers must trigger signing bypass."""
        output = "-----END CERTIFICATE-----"
        decision = classifier.classify("openssl", output)
        assert decision.bypassed is True

    def test_detects_public_key(self, classifier: BypassClassifier):
        """public_key patterns must trigger signing bypass."""
        output = "public_key: ssh-rsa AAAA..."
        decision = classifier.classify("ssh-keygen", output)
        assert decision.bypassed is True

    def test_detects_fingerprint(self, classifier: BypassClassifier):
        """fingerprint: fields must trigger signing bypass."""
        output = "fingerprint: SHA256:abc123def456"
        decision = classifier.classify("ssh-keyscan", output)
        assert decision.bypassed is True

    def test_detects_ssh_key_types(self, classifier: BypassClassifier):
        """SSH key type identifiers must trigger signing bypass."""
        for key_type in ["ssh-rsa", "ssh-ed25519", "ecdsa-sha2"]:
            output = f"{key_type} AAAAB3NzaC1yc2E..."
            decision = classifier.classify("cat ~/.ssh/id_rsa.pub", output)
            assert decision.bypassed is True, f"Failed for {key_type}"


# ============ BYPASS_PERMISSION Tests ============ #


class TestBypassPermission:
    """Test BYPASS_PERMISSION class detection."""

    def test_detects_allow(self, classifier: BypassClassifier):
        """ALLOW keyword must trigger permission bypass."""
        output = "ALLOW read access to /data"
        decision = classifier.classify("acl", output)
        assert decision.bypassed is True
        assert BypassClass.BYPASS_PERMISSION in decision.matched_classes

    def test_detects_deny(self, classifier: BypassClassifier):
        """DENY keyword must trigger permission bypass."""
        output = "DENY write access to /system"
        decision = classifier.classify("acl", output)
        assert decision.bypassed is True

    def test_detects_grant(self, classifier: BypassClassifier):
        """GRANT keyword must trigger permission bypass."""
        output = "GRANT SELECT ON users TO readonly_user"
        decision = classifier.classify("psql", output)
        assert decision.bypassed is True

    def test_detects_revoke(self, classifier: BypassClassifier):
        """REVOKE keyword must trigger permission bypass."""
        output = "REVOKE ALL ON database FROM public"
        decision = classifier.classify("psql", output)
        assert decision.bypassed is True

    def test_detects_scope_field(self, classifier: BypassClassifier):
        """scope: fields must trigger permission bypass."""
        output = "scope: read:user write:repo"
        decision = classifier.classify("oauth", output)
        assert decision.bypassed is True

    def test_detects_principal_id(self, classifier: BypassClassifier):
        """principal_id patterns must trigger permission bypass."""
        output = "principal_id: github:user123"
        decision = classifier.classify("identity", output)
        assert decision.bypassed is True


# ============ BYPASS_RECEIPT Tests ============ #


class TestBypassReceipt:
    """Test BYPASS_RECEIPT class detection."""

    def test_detects_receipt_id(self, classifier: BypassClassifier):
        """receipt_id: fields must trigger receipt bypass."""
        output = "receipt_id: rx-2024-001"
        decision = classifier.classify("settle", output)
        assert decision.bypassed is True
        assert BypassClass.BYPASS_RECEIPT in decision.matched_classes

    def test_detects_work_order_id(self, classifier: BypassClassifier):
        """work_order_id: fields must trigger receipt bypass."""
        output = "work_order_id: wo-2024-001"
        decision = classifier.classify("execute", output)
        assert decision.bypassed is True

    def test_detects_settled_at(self, classifier: BypassClassifier):
        """settled_at: fields must trigger receipt bypass."""
        output = "settled_at: 2024-01-01T00:00:00Z"
        decision = classifier.classify("ledger", output)
        assert decision.bypassed is True

    def test_detects_proof_of_compute(self, classifier: BypassClassifier):
        """proof_of_compute patterns must trigger receipt bypass."""
        output = "proof_of_compute: hash:abc123"
        decision = classifier.classify("wre", output)
        assert decision.bypassed is True


# ============ ALLOW_COMPRESSION Tests ============ #


class TestAllowCompression:
    """Test ALLOW_COMPRESSION (safe commands)."""

    def test_ls_allows_compression(self, classifier: BypassClassifier):
        """ls output without sensitive content can be compressed."""
        output = "file1.txt  file2.txt  directory/"
        decision = classifier.classify("ls", output)
        assert decision.bypassed is False
        assert decision.classification == BypassClass.ALLOW_COMPRESSION

    def test_cat_allows_compression(self, classifier: BypassClassifier):
        """cat output without sensitive content can be compressed."""
        output = "This is just a normal text file content"
        decision = classifier.classify("cat readme.txt", output)
        assert decision.bypassed is False

    def test_safe_command_with_sensitive_output_bypasses(self, classifier: BypassClassifier):
        """Safe command with sensitive OUTPUT still bypasses."""
        output = "password=secret123"  # Sensitive content
        decision = classifier.classify("cat config.txt", output)
        assert decision.bypassed is True
        assert decision.classification == BypassClass.BYPASS_AUTH


# ============ NEEDS_HUMAN_REVIEW Tests ============ #


class TestNeedsHumanReview:
    """Test NEEDS_HUMAN_REVIEW (unknown commands)."""

    def test_unknown_command_needs_review(self, classifier: BypassClassifier):
        """Unknown commands without patterns need human review."""
        output = "Some ambiguous output"
        decision = classifier.classify("mysterycommand", output)
        assert decision.bypassed is True
        assert decision.classification == BypassClass.NEEDS_HUMAN_REVIEW
        assert decision.bypass_reason == "unknown_command"

    def test_custom_script_needs_review(self, classifier: BypassClassifier):
        """Custom scripts need human review."""
        output = "Processing complete"
        decision = classifier.classify("./my_custom_script.sh", output)
        assert decision.bypassed is True
        assert decision.classification == BypassClass.NEEDS_HUMAN_REVIEW


# ============ Fail-Closed Behavior Tests ============ #


class TestFailClosed:
    """Test fail-closed behavior (Contract requirement)."""

    def test_should_bypass_returns_true_on_match(self, classifier: BypassClassifier):
        """should_bypass returns (True, class) on pattern match."""
        bypassed, class_name = classifier.should_bypass("CVE-2024-12345")
        assert bypassed is True
        assert class_name == "BYPASS_SECURITY"

    def test_should_bypass_returns_false_on_no_match(self, classifier: BypassClassifier):
        """should_bypass returns (False, None) when safe."""
        bypassed, class_name = classifier.should_bypass("just normal text")
        assert bypassed is False
        assert class_name is None

    def test_get_matched_classes_returns_all(self, classifier: BypassClassifier):
        """get_matched_classes returns all matching classes."""
        # Output with multiple bypass triggers
        output = "CVE-2024-12345 found, api_key=abc123"
        matched = classifier.get_matched_classes(output)
        assert BypassClass.BYPASS_SECURITY in matched
        assert BypassClass.BYPASS_AUTH in matched


# ============ M2M Output Format Tests ============ #


class TestM2MOutput:
    """Test WSP-99 M2M output format."""

    def test_to_m2m_compact_format(self, classifier: BypassClassifier):
        """Decision serializes to M2M compact format."""
        decision = classifier.classify("npm audit", "CVE-2024-12345 found")
        compact = decision.to_m2m_compact()

        assert compact.startswith("L:BYPASS")
        assert "S:BYPASS_SECURITY" in compact
        assert "M:classify" in compact
        assert "R:[97,99]" in compact
        assert "bypassed:true" in compact

    def test_to_m2m_yaml_format(self, classifier: BypassClassifier):
        """Decision serializes to M2M YAML format."""
        decision = classifier.classify("npm audit", "CVE-2024-12345 found")
        yaml_out = decision.to_m2m_yaml()

        assert "M2M_VERSION: 1.0" in yaml_out
        assert "SENDER: 0102-BYPASS" in yaml_out
        assert "RECEIVER: 0102-ORCH" in yaml_out
        assert "CLASS: BYPASS_SECURITY" in yaml_out
        assert "BYPASSED: true" in yaml_out

    def test_as_dict_json_serializable(self, classifier: BypassClassifier):
        """Decision.as_dict() produces JSON-serializable output."""
        decision = classifier.classify("npm audit", "CVE-2024-12345 found")
        d = decision.as_dict()
        json_str = json.dumps(d)
        assert isinstance(json_str, str)
        assert "BYPASS_SECURITY" in json_str


# ============ Adversarial Tests ============ #


class TestAdversarial:
    """Adversarial tests for fake-safe commands hiding sensitive output."""

    def test_fake_ls_with_password(self, classifier: BypassClassifier):
        """ls-like command output hiding password must bypass."""
        output = "password=admin123\nfile1.txt"
        decision = classifier.classify("ls", output)
        assert decision.bypassed is True
        assert decision.classification == BypassClass.BYPASS_AUTH

    def test_fake_cat_with_api_key(self, classifier: BypassClassifier):
        """cat-like command output hiding API key must bypass."""
        output = "OPENAI_API_KEY=sk-proj-realkey123"
        decision = classifier.classify("cat file.txt", output)
        assert decision.bypassed is True

    def test_echo_hiding_token(self, classifier: BypassClassifier):
        """echo command hiding auth token must bypass."""
        output = "auth_token=secret_token_value"
        decision = classifier.classify("echo $TOKEN", output)
        assert decision.bypassed is True

    def test_npm_list_with_vulnerability(self, classifier: BypassClassifier):
        """npm list output with vulnerability must bypass."""
        output = "package@1.0.0\nCRITICAL: Remote code execution"
        decision = classifier.classify("npm list", output)
        assert decision.bypassed is True
        assert decision.classification == BypassClass.BYPASS_SECURITY

    def test_tree_hiding_pem_key(self, classifier: BypassClassifier):
        """tree output hiding PEM key must bypass."""
        output = "-----BEGIN RSA PRIVATE KEY-----\nbase64content"
        decision = classifier.classify("tree", output)
        assert decision.bypassed is True
        assert decision.classification == BypassClass.BYPASS_SIGNING

    def test_mixed_safe_and_sensitive(self, classifier: BypassClassifier):
        """Output mixing safe and sensitive content must bypass."""
        output = """
        README.md
        config.yaml
        password=admin123
        setup.py
        """
        decision = classifier.classify("ls", output)
        assert decision.bypassed is True

    def test_obfuscated_key_pattern(self, classifier: BypassClassifier):
        """Key patterns even without standard format must bypass."""
        # sk- pattern for OpenAI keys
        output = "Using sk-abc123def456 for API access"
        decision = classifier.classify("echo", output)
        assert decision.bypassed is True

    def test_base64_pem_in_safe_command(self, classifier: BypassClassifier):
        """PEM markers in any command must bypass."""
        output = "-----BEGIN CERTIFICATE-----\nMIIB..."
        decision = classifier.classify("head file", output)
        assert decision.bypassed is True


# ============ Priority Tests ============ #


class TestPriority:
    """Test bypass class priority ordering."""

    def test_security_over_auth(self, classifier: BypassClassifier):
        """SECURITY takes priority over AUTH."""
        output = "CVE-2024-12345 in auth_token=abc"
        decision = classifier.classify("scan", output)
        assert decision.classification == BypassClass.BYPASS_SECURITY

    def test_auth_over_provenance(self, classifier: BypassClassifier):
        """AUTH takes priority over PROVENANCE."""
        output = "signed by user with password=abc"
        decision = classifier.classify("verify", output)
        # AUTH has higher priority than PROVENANCE
        assert decision.classification in [BypassClass.BYPASS_AUTH, BypassClass.BYPASS_SECURITY]


# ============ Singleton Tests ============ #


class TestSingleton:
    """Test classifier singleton behavior."""

    def test_get_bypass_classifier_singleton(self):
        """get_bypass_classifier returns same instance."""
        c1 = get_bypass_classifier()
        c2 = get_bypass_classifier()
        assert c1 is c2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
