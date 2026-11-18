# -*- coding: utf-8 -*-
"""
RedDog Compute Governor Tests (P4)

Tests per hardened M2M prompt requirements:
- safe command without output -> ALLOW_EVALUATION_DRY_RUN (not compression authority)
- safe command + sensitive output_preview -> BYPASS_REQUIRED
- unknown command -> NEEDS_REVIEW
- security command -> BYPASS_REQUIRED
- runtime_reindex_allowed=true -> REJECT (via validation)
- index_gap on security context -> REJECT
- raw command not in serialized decision
- command_digest deterministic
- telemetry event created in memory only
- no RTK/subprocess/shell/HoloIndex mutation

Contract: docs/contracts/REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_CONTRACT_PHASE1.md Section 2
WSP: WSP_97, WSP_99
"""

import pytest
import ast
import sys
from pathlib import Path

# Add module parent to path for package imports
sys.path.insert(0, str(Path(__file__).parents[2]))

from modules.infrastructure.token_efficiency.src.compute_governor import (
    ComputeGovernor,
    RedDogComputeDecision,
    Phase,
    Routing,
    CommandType,
    compute_command_digest,
    redact_command,
    extract_command_type,
    is_bypass_command,
    is_safe_command,
    generate_decision_id,
    record_decision_telemetry,
    validate_decision,
    get_compute_governor,
    reset_compute_governor,
)

from modules.infrastructure.token_efficiency.src.telemetry_service import (
    reset_telemetry_store,
    get_telemetry_store,
)


class TestCommandDigest:
    """Command digest tests."""

    def test_digest_deterministic(self):
        """command_digest is deterministic."""
        cmd = "ls -la"
        assert compute_command_digest(cmd) == compute_command_digest(cmd)

    def test_digest_different_for_different_commands(self):
        """Different commands produce different digests."""
        assert compute_command_digest("ls") != compute_command_digest("cat")

    def test_digest_sha256_length(self):
        """Digest is SHA256 hex (64 chars)."""
        digest = compute_command_digest("test")
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)


class TestRedactCommand:
    """Command redaction tests."""

    def test_redacts_token(self):
        """Redacts token patterns."""
        cmd = "curl -H 'Authorization: token abc123secret'"
        redacted = redact_command(cmd)
        assert "abc123secret" not in redacted
        assert "***" in redacted

    def test_redacts_password(self):
        """Redacts password patterns."""
        cmd = "mysql --password=mysecretpass"
        redacted = redact_command(cmd)
        assert "mysecretpass" not in redacted

    def test_truncates_long_commands(self):
        """Truncates commands over 100 chars."""
        cmd = "x" * 150
        redacted = redact_command(cmd)
        assert len(redacted) <= 100
        assert redacted.endswith("...")


class TestExtractCommandType:
    """Command type extraction tests."""

    def test_git_command(self):
        """Extracts git command type."""
        assert extract_command_type("git status") == CommandType.GIT

    def test_npm_command(self):
        """Extracts npm command type."""
        assert extract_command_type("npm install") == CommandType.NPM

    def test_python_command(self):
        """Extracts python command type."""
        assert extract_command_type("python script.py") == CommandType.PYTHON

    def test_unknown_command(self):
        """Unknown command returns UNKNOWN."""
        assert extract_command_type("mycustomtool --help") == CommandType.UNKNOWN


class TestBypassCommand:
    """Bypass command detection tests."""

    def test_npm_audit_requires_bypass(self):
        """npm audit requires bypass."""
        is_bypass, bypass_class = is_bypass_command("npm audit")
        assert is_bypass
        assert bypass_class == "BYPASS_SECURITY"

    def test_gh_auth_requires_bypass(self):
        """gh auth requires bypass (classified as security/auth)."""
        is_bypass, bypass_class = is_bypass_command("gh auth login")
        assert is_bypass
        assert bypass_class in ("BYPASS_AUTH", "BYPASS_SECURITY")

    def test_git_secrets_requires_bypass(self):
        """git secrets requires bypass."""
        is_bypass, bypass_class = is_bypass_command("git secrets --scan")
        assert is_bypass
        assert bypass_class == "BYPASS_SECURITY"

    def test_safe_command_no_bypass(self):
        """Safe command does not require bypass."""
        is_bypass, _ = is_bypass_command("ls -la")
        assert not is_bypass


class TestSafeCommand:
    """Safe command detection tests."""

    def test_ls_is_safe(self):
        """ls is safe."""
        assert is_safe_command("ls -la")

    def test_echo_is_safe(self):
        """echo is safe."""
        assert is_safe_command("echo hello")

    def test_git_status_is_safe(self):
        """git status is safe."""
        assert is_safe_command("git status")

    def test_npm_audit_not_safe(self):
        """npm audit is not in safe list."""
        assert not is_safe_command("npm audit")


class TestDecisionId:
    """Decision ID tests."""

    def test_decision_id_deterministic(self):
        """decision_id is deterministic for same input."""
        digest = compute_command_digest("test")
        id1 = generate_decision_id(digest, Phase.PRE_OUTPUT)
        id2 = generate_decision_id(digest, Phase.PRE_OUTPUT)
        assert id1 == id2

    def test_decision_id_different_for_different_phase(self):
        """Different phases produce different IDs."""
        digest = compute_command_digest("test")
        id1 = generate_decision_id(digest, Phase.PRE_OUTPUT)
        id2 = generate_decision_id(digest, Phase.OUTPUT_PREVIEW)
        assert id1 != id2


class TestComputeGovernor:
    """Compute governor tests."""

    def setup_method(self):
        """Reset governor and telemetry before each test."""
        reset_compute_governor()
        reset_telemetry_store()

    def test_safe_command_without_output_returns_evaluation_candidate(self):
        """Safe command without output -> ALLOW_EVALUATION_DRY_RUN."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation("ls -la")
        assert decision.routing == Routing.ALLOW_EVALUATION_DRY_RUN
        assert decision.phase == Phase.PRE_OUTPUT
        assert "SAFE_COMMAND_EVALUATION_CANDIDATE" in decision.reason_codes

    def test_safe_command_with_sensitive_output_returns_bypass(self):
        """Safe command + sensitive output_preview -> BYPASS_REQUIRED."""
        governor = get_compute_governor()
        # Safe command but output contains secret
        decision = governor.get_routing_recommendation(
            command="cat .env",
            output_preview="API_KEY=sk-secret123abc"
        )
        assert decision.routing == Routing.BYPASS_REQUIRED
        assert decision.phase == Phase.OUTPUT_PREVIEW
        assert "OUTPUT_CONTENT_REQUIRES_BYPASS" in decision.reason_codes

    def test_safe_command_with_auth_token_output_returns_bypass(self):
        """Safe command + auth token output_preview -> BYPASS_REQUIRED."""
        governor = get_compute_governor()
        # Use a pattern the bypass classifier recognizes
        decision = governor.get_routing_recommendation(
            command="echo test",
            output_preview="token=sk-secret123456789"
        )
        assert decision.routing == Routing.BYPASS_REQUIRED
        assert decision.bypass_class is not None

    def test_safe_command_with_secret_output_returns_bypass(self):
        """Safe command + secret output_preview -> BYPASS_REQUIRED."""
        governor = get_compute_governor()
        decision = governor.get_routing_recommendation(
            command="grep password",
            output_preview="password=hunter2"
        )
        assert decision.routing == Routing.BYPASS_REQUIRED

    def test_unknown_command_returns_needs_review(self):
        """Unknown command -> NEEDS_REVIEW."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation("mycustomtool --help")
        assert decision.routing == Routing.NEEDS_REVIEW
        assert "UNKNOWN_COMMAND" in decision.reason_codes

    def test_security_command_returns_bypass(self):
        """Security command -> BYPASS_REQUIRED."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation("npm audit")
        assert decision.routing == Routing.BYPASS_REQUIRED
        assert decision.bypass_class == "BYPASS_SECURITY"

    def test_auth_command_returns_bypass(self):
        """Auth command -> BYPASS_REQUIRED."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation("gh auth login")
        assert decision.routing == Routing.BYPASS_REQUIRED
        # May be classified as either AUTH or SECURITY (both are bypassed)
        assert decision.bypass_class in ("BYPASS_AUTH", "BYPASS_SECURITY")

    def test_index_gap_on_security_context_returns_reject(self):
        """index_gap on security context -> REJECT."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation(
            "npm audit",
            index_gap_detected=True
        )
        assert decision.routing == Routing.REJECT
        assert "INDEX_GAP_ON_SECURITY_CONTEXT" in decision.reason_codes


class TestDecisionValidation:
    """Decision validation tests."""

    def setup_method(self):
        reset_compute_governor()

    def test_valid_decision_passes(self):
        """Valid decision passes validation."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation("ls")
        valid, errors = validate_decision(decision)
        assert valid
        assert len(errors) == 0

    def test_runtime_reindex_true_rejected(self):
        """runtime_reindex_allowed=true is rejected."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation("ls")
        decision.runtime_reindex_allowed = True
        valid, errors = validate_decision(decision)
        assert not valid
        assert any("runtime_reindex_allowed" in e for e in errors)

    def test_no_command_execution_false_rejected(self):
        """no_command_execution=false is rejected."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation("ls")
        decision.no_command_execution = False
        valid, errors = validate_decision(decision)
        assert not valid

    def test_no_rtk_invocation_false_rejected(self):
        """no_rtk_invocation=false is rejected."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation("ls")
        decision.no_rtk_invocation = False
        valid, errors = validate_decision(decision)
        assert not valid

    def test_no_compression_performed_false_rejected(self):
        """no_compression_performed=false is rejected."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation("ls")
        decision.no_compression_performed = False
        valid, errors = validate_decision(decision)
        assert not valid


class TestSerialization:
    """Serialization tests."""

    def setup_method(self):
        reset_compute_governor()

    def test_raw_command_not_in_serialized_decision(self):
        """Raw command is NOT present in serialized decision."""
        governor = get_compute_governor()
        raw_command = "secret-command --password=hunter2"
        decision = governor.classify_command_for_evaluation(raw_command)

        # Check to_dict
        d = decision.to_dict()
        # Raw command should not be present
        assert raw_command not in str(d)
        assert "hunter2" not in str(d)
        # Only digest and redacted summary
        assert "command_digest" in d
        assert "command_redacted_summary" in d

    def test_to_dict_from_dict_roundtrip(self):
        """to_dict/from_dict roundtrip works."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation("ls -la")
        d = decision.to_dict()
        restored = RedDogComputeDecision.from_dict(d)
        assert restored.decision_id == decision.decision_id
        assert restored.routing == decision.routing
        assert restored.command_type == decision.command_type

    def test_to_m2m_compact_format(self):
        """to_m2m_compact produces valid format."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation("ls")
        compact = decision.to_m2m_compact()
        assert "GOVERNOR:" in compact
        assert "ROUTING:" in compact

    def test_to_m2m_yaml_format(self):
        """to_m2m_yaml produces valid format."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation("ls")
        yaml = decision.to_m2m_yaml()
        assert "REDDOG_COMPUTE_DECISION:" in yaml
        assert "routing:" in yaml


class TestTelemetry:
    """Telemetry integration tests."""

    def setup_method(self):
        reset_compute_governor()
        reset_telemetry_store()

    def test_telemetry_event_recorded_in_memory(self):
        """Telemetry event is recorded in memory only."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation("ls")

        # Record telemetry
        event = record_decision_telemetry(decision)

        # Check event was recorded
        store = get_telemetry_store()
        assert store.count() == 1
        assert store.get_all()[0].event_id == event.event_id

    def test_telemetry_event_has_correct_source(self):
        """Telemetry event has correct source layer."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation("npm audit")
        event = record_decision_telemetry(decision)

        from modules.infrastructure.token_efficiency.src.telemetry_service import SourceLayer
        assert event.source_layer == SourceLayer.BYPASS_CLASSIFIER


class TestInvariants:
    """Invariant tests."""

    def setup_method(self):
        reset_compute_governor()

    def test_invariants_always_safe_values(self):
        """Decisions always have safe invariant values."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation("any command")
        assert decision.runtime_reindex_allowed is False
        assert decision.no_command_execution is True
        assert decision.no_rtk_invocation is True
        assert decision.no_compression_performed is True


class TestNoRTKOrSubprocess:
    """AST denylist tests."""

    def test_no_subprocess_import(self):
        """compute_governor.py has no subprocess import."""
        module_path = Path(__file__).parents[1] / "src" / "compute_governor.py"
        source = module_path.read_text()
        tree = ast.parse(source)

        forbidden = {"subprocess", "os.system", "os.popen"}
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        for imp in imports:
            for f in forbidden:
                assert f not in imp, f"Forbidden import found: {imp}"

    def test_no_rtk_import(self):
        """compute_governor.py has no RTK import."""
        module_path = Path(__file__).parents[1] / "src" / "compute_governor.py"
        source = module_path.read_text()
        assert "import rtk" not in source.lower()
        assert "from rtk" not in source.lower()

    def test_no_eval_exec(self):
        """compute_governor.py has no eval/exec calls."""
        module_path = Path(__file__).parents[1] / "src" / "compute_governor.py"
        source = module_path.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in ("eval", "exec"), \
                        f"Forbidden call: {node.func.id}"

    def test_no_socket_or_requests(self):
        """compute_governor.py has no network imports."""
        module_path = Path(__file__).parents[1] / "src" / "compute_governor.py"
        source = module_path.read_text()
        forbidden = ["import socket", "import requests", "import aiohttp", "import urllib"]
        for f in forbidden:
            assert f not in source, f"Forbidden import: {f}"

    def test_no_holoindex_mutation(self):
        """compute_governor.py has no HoloIndex mutation imports."""
        module_path = Path(__file__).parents[1] / "src" / "compute_governor.py"
        source = module_path.read_text()
        # Should not have index mutation commands
        assert "--index" not in source
        assert "reindex" not in source.lower() or "runtime_reindex" in source.lower()


class TestNoExtensionRuntime:
    """Verify no extension runtime files touched."""

    def test_no_extension_js_reference(self):
        """Module does not reference extension.js."""
        module_path = Path(__file__).parents[1] / "src" / "compute_governor.py"
        source = module_path.read_text()
        assert "extension.js" not in source
        assert "package.json" not in source


class TestContextFlags:
    """Context flag tests."""

    def setup_method(self):
        reset_compute_governor()

    def test_ctx_holo_present_propagated(self):
        """ctx_holo_present flag propagated to decision."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation(
            "ls",
            ctx_holo_present=True
        )
        assert decision.ctx_holo_present is True

    def test_index_gap_detected_propagated(self):
        """index_gap_detected flag propagated to decision."""
        governor = get_compute_governor()
        decision = governor.classify_command_for_evaluation(
            "ls",
            index_gap_detected=True
        )
        assert decision.index_gap_detected is True
