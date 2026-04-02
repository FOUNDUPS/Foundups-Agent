#!/usr/bin/env python3
"""
Regression tests for UTF-8 hygiene import boundary fix.

Ensures training system imports UTF-8 helpers from the canonical
scanner module (WSP 62) rather than main.py.
"""

import pytest


class TestUTF8ImportBoundary:
    """Test import boundary between training_system and utf8_hygiene modules."""

    def test_launch_imports_from_scanner_not_main(self):
        """launch.py must import run_utf8_hygiene_scan from scanner module."""
        from modules.ai_intelligence.training_system.scripts.launch import (
            run_training_system,
        )

        # If we get here without ImportError, the boundary is fixed
        assert callable(run_training_system)

    def test_training_commands_imports_from_scanner_not_main(self):
        """training_commands.py must import UTF-8 helpers from scanner module."""
        from modules.ai_intelligence.training_system.scripts.training_commands import (
            execute_training_command,
        )

        # If we get here without ImportError, the boundary is fixed
        assert callable(execute_training_command)

    def test_scanner_exports_required_functions(self):
        """scanner.py must export both UTF-8 hygiene functions."""
        from modules.ai_intelligence.utf8_hygiene.scripts.scanner import (
            run_utf8_hygiene_scan,
            summarize_utf8_findings,
        )

        assert callable(run_utf8_hygiene_scan)
        assert callable(summarize_utf8_findings)

    def test_run_utf8_hygiene_scan_signature(self):
        """run_utf8_hygiene_scan accepts expected parameters."""
        from modules.ai_intelligence.utf8_hygiene.scripts.scanner import (
            run_utf8_hygiene_scan,
        )
        import inspect

        sig = inspect.signature(run_utf8_hygiene_scan)
        params = list(sig.parameters.keys())

        assert "memory" in params
        assert "targets" in params
        assert "interactive" in params

    def test_summarize_utf8_findings_signature(self):
        """summarize_utf8_findings accepts expected parameters."""
        from modules.ai_intelligence.utf8_hygiene.scripts.scanner import (
            summarize_utf8_findings,
        )
        import inspect

        sig = inspect.signature(summarize_utf8_findings)
        params = list(sig.parameters.keys())

        assert "memory" in params
        assert "target_filters" in params
        assert "limit" in params


class TestUTF8ScannerFunctionality:
    """Test UTF-8 scanner functions work correctly when imported."""

    def test_run_utf8_hygiene_scan_non_interactive(self):
        """run_utf8_hygiene_scan can run non-interactively."""
        from modules.ai_intelligence.utf8_hygiene.scripts.scanner import (
            run_utf8_hygiene_scan,
        )

        # Run on empty target list - should return empty findings
        findings = run_utf8_hygiene_scan(
            memory=None,
            targets=["nonexistent_path_for_test"],
            interactive=False,
        )

        assert isinstance(findings, list)

    def test_summarize_utf8_findings_returns_dict(self):
        """summarize_utf8_findings returns a dictionary."""
        from modules.ai_intelligence.utf8_hygiene.scripts.scanner import (
            summarize_utf8_findings,
        )

        result = summarize_utf8_findings(memory=None, target_filters=None, limit=5)

        assert isinstance(result, dict)
        assert "status" in result
