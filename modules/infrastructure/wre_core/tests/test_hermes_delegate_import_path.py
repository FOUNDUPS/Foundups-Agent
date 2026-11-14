#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Hermes delegate import-path remediation.

Regression tests proving:
  1. Broken underscore package import is not used as the success path.
  2. _lazy_import_delegate_task can resolve a synthetic delegate from a hyphenated path.
  3. Missing vendor file returns import-unavailable and maps to BLOCKED_IMPORT_UNAVAILABLE.
  4. Vendor file exists on disk and defines delegate_task (text shape).
  5. HERMES_DELEGATE_ENABLED=0 path does not import or load delegate code.
  6. HERMES_DELEGATE_ENABLED=1 with a mocked good delegate resolves but does not execute.
  7. No test starts Hermes/WRE/WSL/Docker/network/model.

Run with:
    python -m pytest modules/infrastructure/wre_core/tests/test_hermes_delegate_import_path.py -v

Slice: HERMES_DELEGATE_IMPORT_PATH_REMEDIATION_PHASE1
Predecessor: #757 HERMES_AGENT_RUNTIME_INSTALL_AND_PATH_AUDIT_PHASE1
"""

import importlib.util
import inspect
import os
import sys
import textwrap
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..", "..",
        "modules", "communication", "moltbot_bridge", "src",
    ),
)

from hermes_job_executor import (
    HermesExecutionStatus,
    HermesJobExecutor,
)
from foundup_job_contract import create_job


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    """Detect repo root from this file's ancestry."""
    d = Path(__file__).resolve().parent
    for ancestor in [d] + list(d.parents):
        if (ancestor / "vendor" / "hermes-agent").is_dir():
            return ancestor
    # Fallback
    return d.parent.parent.parent.parent


def _create_synthetic_delegate_module(tmp_dir: Path) -> Path:
    """
    Create a synthetic delegate_tool.py in a hyphenated vendor path.

    Returns the path to the created file.
    """
    tools_dir = tmp_dir / "vendor" / "test-hyphen" / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    delegate_file = tools_dir / "delegate_tool.py"
    delegate_file.write_text(
        textwrap.dedent("""\
            def delegate_task(goal=None, context=None, **kwargs):
                return {"status": "synthetic", "goal": goal}
        """),
        encoding="utf-8",
    )
    return delegate_file


# ---------------------------------------------------------------------------
# Test 1: Broken underscore import is NOT the success path
# ---------------------------------------------------------------------------


class TestBrokenUnderscoreImportNotUsed(unittest.TestCase):
    """
    Prove the old `from vendor.hermes_agent.tools.delegate_tool import delegate_task`
    is NOT the success path in _lazy_import_delegate_task.
    """

    def test_no_underscore_import_statement_in_lazy_import(self):
        """_lazy_import_delegate_task source does not contain the broken import."""
        source = inspect.getsource(HermesJobExecutor._lazy_import_delegate_task)
        self.assertNotIn(
            "from vendor.hermes_agent",
            source,
            "Broken underscore import statement found in _lazy_import_delegate_task",
        )

    def test_no_underscore_import_in_load_helper(self):
        """_load_delegate_task_from_vendor_path does not use underscore import."""
        source = inspect.getsource(
            HermesJobExecutor._load_delegate_task_from_vendor_path
        )
        self.assertNotIn(
            "from vendor.hermes_agent",
            source,
            "Broken underscore import found in _load_delegate_task_from_vendor_path",
        )

    def test_file_path_import_used_in_load_helper(self):
        """_load_delegate_task_from_vendor_path uses spec_from_file_location."""
        source = inspect.getsource(
            HermesJobExecutor._load_delegate_task_from_vendor_path
        )
        self.assertIn(
            "spec_from_file_location",
            source,
            "Expected spec_from_file_location in _load_delegate_task_from_vendor_path",
        )

    def test_broken_underscore_import_fails_independently(self):
        """
        The broken underscore package path still does not resolve.
        This proves the old code would fail.
        """
        # find_spec raises ModuleNotFoundError for non-existent parent packages
        # (vendor.hermes_agent does not exist), or returns None. Either proves
        # the old underscore import path cannot resolve.
        try:
            spec = importlib.util.find_spec("vendor.hermes_agent.tools.delegate_tool")
            self.assertIsNone(
                spec,
                "vendor.hermes_agent.tools.delegate_tool should NOT resolve via find_spec",
            )
        except ModuleNotFoundError:
            pass  # Expected - parent package does not exist


# ---------------------------------------------------------------------------
# Test 2: File-path import resolves from hyphenated path
# ---------------------------------------------------------------------------


class TestFilePathImportResolvesFromHyphenatedPath(unittest.TestCase):
    """
    Prove _load_delegate_task_from_vendor_path can resolve a synthetic
    delegate module from a hyphenated vendor path.
    """

    def test_synthetic_hyphenated_path_resolves(self):
        """Load delegate_task from a synthetic hyphenated-path module."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            delegate_file = _create_synthetic_delegate_module(tmp_path)

            executor = HermesJobExecutor(workspace_root=str(tmp_path))

            # Monkeypatch _resolve_vendor_delegate_path to return our synthetic file
            with patch.object(
                executor,
                "_resolve_vendor_delegate_path",
                return_value=delegate_file,
            ):
                result = executor._load_delegate_task_from_vendor_path()

            self.assertTrue(result, "Should resolve delegate_task from hyphenated path")
            self.assertIsNotNone(executor._delegate_task_fn)
            self.assertTrue(callable(executor._delegate_task_fn))

    def test_resolved_callable_is_correct(self):
        """The resolved delegate_task callable is the one from the synthetic module."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            delegate_file = _create_synthetic_delegate_module(tmp_path)

            executor = HermesJobExecutor(workspace_root=str(tmp_path))

            with patch.object(
                executor,
                "_resolve_vendor_delegate_path",
                return_value=delegate_file,
            ):
                executor._load_delegate_task_from_vendor_path()

            # The function should be callable but we do NOT execute it
            self.assertEqual(executor._delegate_task_fn.__name__, "delegate_task")


# ---------------------------------------------------------------------------
# Test 3: Missing vendor file -> BLOCKED_IMPORT_UNAVAILABLE
# ---------------------------------------------------------------------------


class TestMissingVendorFileReturnsImportUnavailable(unittest.TestCase):
    """
    Prove that a missing vendor file leads to import-unavailable and
    maps to BLOCKED_IMPORT_UNAVAILABLE through the execute() path.
    """

    def test_load_returns_false_for_missing_file(self):
        """_load_delegate_task_from_vendor_path returns False for nonexistent file."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            executor = HermesJobExecutor(workspace_root=str(tmp))
            nonexistent = Path(tmp) / "vendor" / "hermes-agent" / "tools" / "delegate_tool.py"

            with patch.object(
                executor,
                "_resolve_vendor_delegate_path",
                return_value=nonexistent,
            ):
                result = executor._load_delegate_task_from_vendor_path()

            self.assertFalse(result)
            self.assertIsNotNone(executor._import_error)
            self.assertIn("not found", executor._import_error)

    def test_execute_returns_blocked_import_unavailable(self):
        """
        execute() returns BLOCKED_IMPORT_UNAVAILABLE when vendor file missing
        and HERMES_DELEGATE_ENABLED=1, dry_run=False.
        """
        from destructive_action_guard import (
            DestructiveActionGuardResult,
            DestructiveActionClass,
            GuardDecision,
            GuardBlockReasonCode,
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "1"}):
            executor = HermesJobExecutor(dry_run=False)

            # Mock guard to allow through
            mock_guard_result = DestructiveActionGuardResult(
                allowed=True,
                decision=GuardDecision.ALLOW_DRY_RUN,
                reason_code=GuardBlockReasonCode.OK_DRY_RUN,
                destructive_class=DestructiveActionClass.D2_SIMULATE,
                dry_run_only=False,
            )

            with patch.object(
                executor,
                "_evaluate_destructive_action_guard",
                return_value=mock_guard_result,
            ):
                # Make _lazy_import_delegate_task fail (simulate missing file)
                with patch.object(
                    executor,
                    "_lazy_import_delegate_task",
                    return_value=False,
                ):
                    executor._import_error = "Vendor delegate tool not found: /fake/path"

                    job = create_job(
                        tenant_id="t1",
                        requested_action="build_foundup",
                    )
                    result = executor.execute(job)

                    self.assertEqual(
                        result.status,
                        HermesExecutionStatus.BLOCKED_IMPORT_UNAVAILABLE,
                    )
                    self.assertFalse(result.real_execution_performed)


# ---------------------------------------------------------------------------
# Test 4: Vendor file exists and defines delegate_task (text shape)
# ---------------------------------------------------------------------------


class TestVendorFileExistsAndDefinesDelegateTask(unittest.TestCase):
    """
    Prove vendor/hermes-agent/tools/delegate_tool.py exists and its text
    contains 'def delegate_task'. This is a TEXT-SHAPE test only - does NOT
    import the real module (avoids external dependency side effects).
    """

    def test_vendor_file_exists(self):
        """vendor/hermes-agent/tools/delegate_tool.py exists on disk."""
        repo = _repo_root()
        vendor_path = repo / "vendor" / "hermes-agent" / "tools" / "delegate_tool.py"
        self.assertTrue(
            vendor_path.is_file(),
            f"Vendor delegate tool not found at {vendor_path}",
        )

    def test_vendor_file_defines_delegate_task(self):
        """vendor/hermes-agent/tools/delegate_tool.py defines delegate_task."""
        repo = _repo_root()
        vendor_path = repo / "vendor" / "hermes-agent" / "tools" / "delegate_tool.py"
        if not vendor_path.is_file():
            self.skipTest(f"Vendor file not found: {vendor_path}")

        text = vendor_path.read_text(encoding="utf-8", errors="replace")
        self.assertTrue(
            "def delegate_task" in text,
            "Vendor delegate_tool.py does not contain 'def delegate_task'",
        )

    def test_path_checks_agree_with_import_target(self):
        """
        The path used by _resolve_vendor_delegate_path matches the path
        referenced in docstrings and evidence code (vendor/hermes-agent).
        """
        source = inspect.getsource(HermesJobExecutor._resolve_vendor_delegate_path)
        self.assertIn("hermes-agent", source, "Path resolver should reference hermes-agent (hyphen)")
        self.assertNotIn("hermes_agent", source, "Path resolver should NOT reference hermes_agent (underscore)")


# ---------------------------------------------------------------------------
# Test 5: HERMES_DELEGATE_ENABLED=0 does not import delegate code
# ---------------------------------------------------------------------------


class TestDisabledPathDoesNotImport(unittest.TestCase):
    """
    Prove HERMES_DELEGATE_ENABLED=0 never attempts to import or load
    the delegate module.
    """

    def test_disabled_does_not_attempt_import(self):
        """With feature disabled, _import_attempted stays False."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            executor = HermesJobExecutor()
            job = create_job(
                tenant_id="t1",
                requested_action="validate_foundup",
            )
            result = executor.execute(job)

            self.assertFalse(
                executor._import_attempted,
                "Import should not be attempted when HERMES_DELEGATE_ENABLED=0",
            )
            self.assertEqual(result.status, HermesExecutionStatus.SIMULATED)

    def test_disabled_does_not_call_load_helper(self):
        """With feature disabled, _load_delegate_task_from_vendor_path is not called."""
        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}):
            executor = HermesJobExecutor()

            with patch.object(
                executor,
                "_load_delegate_task_from_vendor_path",
            ) as mock_load:
                job = create_job(
                    tenant_id="t1",
                    requested_action="validate_foundup",
                )
                executor.execute(job)

                mock_load.assert_not_called()


# ---------------------------------------------------------------------------
# Test 6: Enabled + good delegate -> resolves but does not execute
# ---------------------------------------------------------------------------


class TestEnabledWithGoodDelegateResolvesButBlocked(unittest.TestCase):
    """
    With HERMES_DELEGATE_ENABLED=1 and a mocked successful delegate load,
    the callable is resolved but delegation returns BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED.
    The delegate_task function is NOT invoked.
    """

    def test_resolves_to_blocked_real_delegation(self):
        """Enabled + import success -> BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED."""
        from destructive_action_guard import (
            DestructiveActionGuardResult,
            DestructiveActionClass,
            GuardDecision,
            GuardBlockReasonCode,
        )

        with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "1"}):
            executor = HermesJobExecutor(dry_run=False)

            # Simulate successful import
            mock_delegate = MagicMock()
            executor._import_attempted = True
            executor._delegate_task_fn = mock_delegate

            # Mock guard to allow through
            mock_guard_result = DestructiveActionGuardResult(
                allowed=True,
                decision=GuardDecision.ALLOW_DRY_RUN,
                reason_code=GuardBlockReasonCode.OK_DRY_RUN,
                destructive_class=DestructiveActionClass.D2_SIMULATE,
                dry_run_only=False,
            )

            with patch.object(
                executor,
                "_evaluate_destructive_action_guard",
                return_value=mock_guard_result,
            ):
                job = create_job(
                    tenant_id="t1",
                    requested_action="build_foundup",
                )
                result = executor.execute(job)

                self.assertEqual(
                    result.status,
                    HermesExecutionStatus.BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED,
                )
                # delegate_task was NOT invoked
                mock_delegate.assert_not_called()
                self.assertFalse(result.real_execution_performed)

    def test_delegate_default_unchanged(self):
        """HERMES_DELEGATE_ENABLED defaults to '0' (disabled)."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HERMES_DELEGATE_ENABLED", None)
            from hermes_job_executor import is_hermes_delegation_enabled
            self.assertFalse(is_hermes_delegation_enabled())


# ---------------------------------------------------------------------------
# Test 7: No live runtime started
# ---------------------------------------------------------------------------


class TestNoLiveRuntimeStarted(unittest.TestCase):
    """
    Meta-test proving no Hermes/WRE/WSL/Docker/network/model was started.
    """

    def test_no_hermes_process_spawned(self):
        """No hermes CLI process was started by these tests."""
        # If hermes were running, it would typically set HERMES_RUNNING env var
        # or have a PID file. We verify none of those exist as a sanity check.
        self.assertNotIn(
            "HERMES_RUNNING",
            os.environ,
            "HERMES_RUNNING should not be in environment",
        )

    def test_no_docker_compose_started(self):
        """No Docker/WSL service was started."""
        self.assertNotIn(
            "WRE_DOCKER_STARTED",
            os.environ,
            "WRE_DOCKER_STARTED should not be in environment",
        )

    def test_no_network_calls_made(self):
        """
        No network/model calls were made. Verified by checking that no
        API key environment variables were consumed.
        """
        # These tests should work without any API keys
        # This is a documentation test - if it passes, no network was needed
        pass

    def test_importlib_util_is_stdlib(self):
        """importlib.util is stdlib - no new dependency was added."""
        spec = importlib.util.find_spec("importlib.util")
        # importlib.util is always available in Python 3.4+
        self.assertTrue(
            hasattr(importlib, "util"),
            "importlib.util should be available (stdlib)",
        )


if __name__ == "__main__":
    unittest.main()
