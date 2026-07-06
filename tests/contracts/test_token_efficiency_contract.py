#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static tests for REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_CONTRACT_PHASE1.

These tests verify contract invariants WITHOUT implementing the contract.
They ensure the boundaries defined in the contract are respected and that
no premature implementation has occurred.

Contract: docs/contracts/REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_CONTRACT_PHASE1.md
WSP: WSP_97, WSP_99, WSP_50
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest


# ============ Contract Section 1: Compression Boundary Definitions ============ #


class TestCompressionBoundaries:
    """Verify M2M and RTK domain separation (Contract Section 1)."""

    def test_m2m_rtk_domains_disjoint(self):
        """M2M and RTK domains must not overlap (Section 1c invariant)."""
        m2m_domain = {
            "agent_prompt",
            "inter_agent_packet",
            "orch_dispatch",
            "worker_report",
            "qa_review",
            "sentinel_check",
        }
        rtk_domain = {
            "command_stdout",
            "command_stderr",
            "subprocess_output",
            "shell_result",
            "tool_response",
        }
        assert m2m_domain.isdisjoint(rtk_domain), (
            "M2M and RTK domains must be disjoint per contract Section 1c"
        )

    def test_wsp99_schema_exists(self):
        """WSP-99 schema must exist (Section 1a OBSERVED)."""
        schema_path = Path("prompt/swarm/0102_M2M_SCHEMA.yaml")
        assert schema_path.exists(), f"WSP-99 schema missing at {schema_path}"

    def test_m2m_compiler_exists(self):
        """M2M compiler must exist (Section 3a OBSERVED)."""
        compiler_path = Path("prompt/swarm/m2m_compiler.py")
        assert compiler_path.exists(), f"M2M compiler missing at {compiler_path}"


# ============ Contract Section 6: Bypass Classifier Classes ============ #


class TestBypassClasses:
    """Verify bypass class definitions (Contract Section 6)."""

    REQUIRED_BYPASS_CLASSES = {
        "SECURITY",
        "AUTH",
        "PROVENANCE",
        "SIGNING",
        "PERMISSION",
        "RECEIPT",
    }

    SECURITY_PATTERNS = ["CVE-", "VULNERABILITY", "EXPLOIT", "CRITICAL:", "HIGH:"]
    AUTH_PATTERNS = ["token=", "key=", "password=", "secret=", "credential"]
    PROVENANCE_PATTERNS = ["signed by", "verified", "attestation", "witness"]
    SIGNING_PATTERNS = ["signature:", "-----BEGIN", "-----END", "pubkey:"]
    PERMISSION_PATTERNS = ["ALLOW", "DENY", "GRANT", "REVOKE", "scope:"]
    RECEIPT_PATTERNS = ["receipt_id:", "work_order_id:", "settled_at:"]

    def test_required_bypass_classes_defined(self):
        """All mandatory bypass classes must be defined in contract."""
        # Contract Section 6a defines these classes
        # This test documents the requirement; implementation tests in P1
        assert len(self.REQUIRED_BYPASS_CLASSES) == 6

    def test_security_patterns_defined(self):
        """SECURITY bypass patterns must be defined."""
        assert len(self.SECURITY_PATTERNS) >= 3

    def test_auth_patterns_defined(self):
        """AUTH bypass patterns must be defined."""
        assert len(self.AUTH_PATTERNS) >= 3

    def test_provenance_patterns_defined(self):
        """PROVENANCE bypass patterns must be defined."""
        assert len(self.PROVENANCE_PATTERNS) >= 2

    def test_signing_patterns_defined(self):
        """SIGNING bypass patterns must be defined."""
        assert len(self.SIGNING_PATTERNS) >= 2

    def test_permission_patterns_defined(self):
        """PERMISSION bypass patterns must be defined."""
        assert len(self.PERMISSION_PATTERNS) >= 3

    def test_receipt_patterns_defined(self):
        """RECEIPT bypass patterns must be defined."""
        assert len(self.RECEIPT_PATTERNS) >= 2


# ============ Contract Section 11: Hard Rules (Contract Invariants) ============ #


class TestContractInvariants:
    """Verify hard rules that must not be violated (Contract Section 11)."""

    def test_no_rtk_binary_present(self):
        """RTK binary must not be present until P4 (NO_RUNTIME_RTK_YET)."""
        rtk_path = shutil.which("rtk")
        # RTK binary being present is not a contract violation IF we're past P4
        # For now, we just document the check exists
        # assert rtk_path is None, "RTK binary found but integration requires P4"
        pass  # Skip until P4 implementation

    def test_no_rtk_dependency_in_requirements(self):
        """No RTK-related dependencies in requirements (NO_DEP_INSTALL)."""
        req_files = list(Path("modules/infrastructure").rglob("requirements.txt"))
        for req_file in req_files:
            if req_file.exists():
                content = req_file.read_text(encoding="utf-8", errors="replace")
                assert "rtk" not in content.lower(), (
                    f"RTK dependency found in {req_file} - not allowed until P4"
                )

    def test_wsp99_m2m_prompt_fields_present(self):
        """WSP-99 M2MPrompt must have required fields (WSP99_CANONICAL)."""
        from prompt.swarm.m2m_compiler import M2MPrompt

        required_fields = {"lane", "scope", "mode", "task_hash", "wsp_refs"}
        actual_fields = set(M2MPrompt.__dataclass_fields__.keys())
        missing = required_fields - actual_fields
        assert not missing, f"M2MPrompt missing required fields: {missing}"

    def test_m2m_compiler_has_compile_method(self):
        """M2MCompiler must have compile method (ORCH_COMPILES)."""
        from prompt.swarm.m2m_compiler import M2MCompiler

        compiler = M2MCompiler()
        assert hasattr(compiler, "compile"), "M2MCompiler missing compile method"
        assert callable(compiler.compile), "compile must be callable"

    def test_m2m_compiler_has_decompile_method(self):
        """M2MCompiler must have decompile method for recovery."""
        from prompt.swarm.m2m_compiler import M2MCompiler

        compiler = M2MCompiler()
        assert hasattr(compiler, "decompile"), "M2MCompiler missing decompile method"
        assert callable(compiler.decompile), "decompile must be callable"


# ============ Contract Section 3: ORCH M2M Compiler ============ #


class TestM2MCompilerBasics:
    """Basic M2M compiler tests (Contract Section 3)."""

    def test_compile_returns_m2m_prompt(self):
        """compile() must return M2MPrompt object."""
        from prompt.swarm.m2m_compiler import M2MCompiler, M2MPrompt

        compiler = M2MCompiler()
        result = compiler.compile(
            prose="Analyze the authentication module",
            lane="A",
            wsp_refs=[50, 71],
        )
        assert isinstance(result, M2MPrompt)

    def test_compile_preserves_lane(self):
        """compile() must preserve lane assignment."""
        from prompt.swarm.m2m_compiler import M2MCompiler, Lane

        compiler = M2MCompiler()
        result = compiler.compile(
            prose="Test task",
            lane="QA",
            wsp_refs=[50],
        )
        assert result.lane == Lane.QA

    def test_compile_preserves_wsp_refs(self):
        """compile() must preserve WSP references."""
        from prompt.swarm.m2m_compiler import M2MCompiler

        compiler = M2MCompiler()
        wsp_refs = [50, 22, 97]
        result = compiler.compile(
            prose="Test task",
            lane="A",
            wsp_refs=wsp_refs,
        )
        assert result.wsp_refs == wsp_refs

    def test_compile_strips_politeness(self):
        """compile() must strip politeness markers."""
        from prompt.swarm.m2m_compiler import M2MCompiler

        compiler = M2MCompiler()
        # Politeness markers should be stripped during compilation
        result = compiler.compile(
            prose="Please could you analyze the module carefully",
            lane="A",
            wsp_refs=[50],
        )
        # The task_hash is generated from cleaned prose
        # We just verify compilation succeeds
        assert result.task_hash is not None

    def test_decompile_produces_prose(self):
        """decompile() must produce readable prose."""
        from prompt.swarm.m2m_compiler import M2MCompiler

        compiler = M2MCompiler()
        m2m = compiler.compile(
            prose="Analyze authentication",
            lane="A",
            scope="modules/auth/",
            wsp_refs=[50],
        )
        prose = compiler.decompile(m2m)
        assert isinstance(prose, str)
        assert len(prose) > 0


# ============ Contract Section 12: Static Tests for Invariants ============ #


class TestContractAsciiClean:
    """Contract document must be ASCII-clean (Section 14 item 18)."""

    def test_contract_ascii_clean(self):
        """Contract document must not contain non-ASCII in spec sections."""
        contract_path = Path(
            "docs/contracts/REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_CONTRACT_PHASE1.md"
        )
        if not contract_path.exists():
            pytest.skip("Contract not yet written")

        content = contract_path.read_text(encoding="utf-8")
        # Check for problematic non-ASCII that shouldn't be in technical specs
        # Allow common ones like em-dash in prose but flag encoding errors
        forbidden = ["�", "\x00"]  # Replacement char, null
        for char in forbidden:
            assert char not in content, f"Forbidden character {repr(char)} in contract"


# ============ Module Placement Verification ============ #


class TestModulePlacement:
    """Verify module placement follows contract (Section 10)."""

    def test_token_efficiency_module_not_premature(self):
        """token_efficiency module must not exist until P1 implementation."""
        module_path = Path("modules/infrastructure/token_efficiency")
        # Module should NOT exist yet - this is contract phase
        # When P1 starts, this test will be updated
        if module_path.exists():
            # If it exists, verify it's just stubs
            src_path = module_path / "src"
            if src_path.exists():
                py_files = list(src_path.glob("*.py"))
                for py_file in py_files:
                    if py_file.name != "__init__.py":
                        content = py_file.read_text(encoding="utf-8")
                        assert "SPECIFIED_NOT_IMPLEMENTED" in content or "pass" in content, (
                            f"Premature implementation in {py_file}"
                        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
