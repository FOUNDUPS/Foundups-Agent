# -*- coding: utf-8 -*-
"""FX1-IMPL: HoloIndex Truth Restoration Tests

Tests for:
- FX1-A: logger defined in _cli_main
- FX1-D: retrieval_mode surfaced in search results
- FX1-E: offline mode disables telemetry
- FX1-C: WSP00 zen state tracker permission fallback

WSP 97: Truthful state distinction - no false claims.
"""

import os
import sys
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestFX1A_LoggerDefined:
    """FX1-A: Verify logger is defined in _cli_main."""

    def test_cli_logger_defined(self):
        """Import _cli_main and verify logger exists."""
        from holo_index import _cli_main
        assert hasattr(_cli_main, 'logger'), "logger not defined in _cli_main"
        assert isinstance(_cli_main.logger, logging.Logger), "logger is not a Logger instance"

    def test_logger_has_correct_name(self):
        """Verify logger uses module name."""
        from holo_index import _cli_main
        assert _cli_main.logger.name == "holo_index._cli_main"


class TestFX1D_RetrievalMode:
    """FX1-D: Verify retrieval_mode is surfaced."""

    def test_holo_skip_model_reports_lexical(self):
        """With HOLO_SKIP_MODEL=1, retrieval_mode should be 'lexical'."""
        # Set env before import
        os.environ['HOLO_SKIP_MODEL'] = '1'
        os.environ['HOLO_SILENT'] = '1'

        try:
            # Force reimport
            if 'holo_index.core.holo_index' in sys.modules:
                del sys.modules['holo_index.core.holo_index']

            from holo_index.core.holo_index import HoloIndex

            # Reset shared state to force fresh init
            HoloIndex._initialized = False
            HoloIndex._shared_state = {}

            holo = HoloIndex(quiet=True)
            assert holo.retrieval_mode == "lexical", f"Expected 'lexical', got '{holo.retrieval_mode}'"
        finally:
            os.environ.pop('HOLO_SKIP_MODEL', None)
            os.environ.pop('HOLO_SILENT', None)

    def test_retrieval_mode_in_search_metadata(self):
        """Search results should include retrieval_mode in metadata."""
        os.environ['HOLO_SKIP_MODEL'] = '1'
        os.environ['HOLO_SILENT'] = '1'

        try:
            if 'holo_index.core.holo_index' in sys.modules:
                del sys.modules['holo_index.core.holo_index']

            from holo_index.core.holo_index import HoloIndex

            HoloIndex._initialized = False
            HoloIndex._shared_state = {}

            holo = HoloIndex(quiet=True)
            result = holo.search("test query", limit=1)

            assert "metadata" in result, "Search result missing 'metadata'"
            assert "retrieval_mode" in result["metadata"], "metadata missing 'retrieval_mode'"
            assert result["metadata"]["retrieval_mode"] == "lexical"
        finally:
            os.environ.pop('HOLO_SKIP_MODEL', None)
            os.environ.pop('HOLO_SILENT', None)


class TestFX1E_OfflineTelemetry:
    """FX1-E: Verify offline mode disables telemetry."""

    def test_offline_sets_telemetry_disabled(self):
        """--offline should set ANONYMIZED_TELEMETRY=false."""
        # Simulate early argv check
        original_argv = sys.argv.copy()
        sys.argv = ['holo_index', '--offline', '--search', 'test']

        try:
            # Clear and reimport to trigger early env setting
            if 'holo_index._cli_main' in sys.modules:
                del sys.modules['holo_index._cli_main']

            # The import should set env vars
            import importlib
            import holo_index._cli_main
            importlib.reload(holo_index._cli_main)

            assert os.environ.get('ANONYMIZED_TELEMETRY') == 'false', \
                "ANONYMIZED_TELEMETRY not set to 'false' in offline mode"
            assert os.environ.get('HOLO_OFFLINE') == '1', \
                "HOLO_OFFLINE not set in offline mode"
        finally:
            sys.argv = original_argv
            os.environ.pop('ANONYMIZED_TELEMETRY', None)
            os.environ.pop('HOLO_OFFLINE', None)


class TestFX1C_ZenStatePermissionFallback:
    """FX1-C: Verify WSP00 zen state tracker handles permission errors."""

    def test_zen_state_tracker_import_no_crash(self):
        """Importing zen state tracker should not crash."""
        from modules.infrastructure.monitoring.src.wsp_00_zen_state_tracker import WSP00ZenStateTracker
        assert WSP00ZenStateTracker is not None

    def test_zen_state_tracker_permission_fallback(self):
        """_ensure_writable_state_file should return None when no path is writable."""
        from modules.infrastructure.monitoring.src.wsp_00_zen_state_tracker import WSP00ZenStateTracker

        # Create a tracker normally first
        tracker = WSP00ZenStateTracker()

        # Test the method directly with a mock that makes all paths fail
        test_path = Path("/nonexistent/impossible/path/state.json")

        # Patch both mkdir and open to always fail
        with patch.object(Path, 'mkdir', side_effect=PermissionError("Mocked")):
            with patch('builtins.open', side_effect=PermissionError("Mocked")):
                result = tracker._ensure_writable_state_file(test_path)
                # Should return None (non-persistent mode) instead of crashing
                assert result is None, f"Expected None for non-persistent mode, got {result}"

    def test_zen_state_tracker_none_state_file_save(self):
        """Saving with None state_file should be a no-op, not crash."""
        from modules.infrastructure.monitoring.src.wsp_00_zen_state_tracker import WSP00ZenStateTracker

        tracker = WSP00ZenStateTracker()
        original_state_file = tracker.state_file

        # Force non-persistent mode
        tracker.state_file = None

        # This should not crash
        try:
            tracker._save_zen_state()
            assert True
        except Exception as e:
            pytest.fail(f"_save_zen_state crashed with None state_file: {e}")
        finally:
            tracker.state_file = original_state_file


class TestFX2C_TimeoutDefaults:
    """FX2-C: Verify timeout defaults are usable for semantic retrieval.

    HOLOINDEX_COLD_MODEL_TIMEOUT_BOUNDARY_PHASE1: Defaults raised to 120s
    to prevent false "not found" results on cold-process model load.
    """

    def test_default_import_timeout_is_sufficient(self):
        """Default HOLO_MODEL_IMPORT_TIMEOUT should be >= 60s for cold imports."""
        original = os.environ.pop('HOLO_MODEL_IMPORT_TIMEOUT', None)
        try:
            for mod in list(sys.modules.keys()):
                if mod.startswith('holo_index.core'):
                    del sys.modules[mod]
            from holo_index.core.holo_index import HOLO_MODEL_IMPORT_TIMEOUT
            assert HOLO_MODEL_IMPORT_TIMEOUT >= 60, \
                f"Default import timeout {HOLO_MODEL_IMPORT_TIMEOUT}s is too short (need >= 60s for cold process)"
        finally:
            if original is not None:
                os.environ['HOLO_MODEL_IMPORT_TIMEOUT'] = original

    def test_default_load_timeout_is_sufficient(self):
        """Default HOLO_MODEL_LOAD_TIMEOUT should be >= 60s for cold model load."""
        original = os.environ.pop('HOLO_MODEL_LOAD_TIMEOUT', None)
        try:
            for mod in list(sys.modules.keys()):
                if mod.startswith('holo_index.core'):
                    del sys.modules[mod]
            from holo_index.core.holo_index import HOLO_MODEL_LOAD_TIMEOUT
            assert HOLO_MODEL_LOAD_TIMEOUT >= 60, \
                f"Default load timeout {HOLO_MODEL_LOAD_TIMEOUT}s is too short (need >= 60s for cold process)"
        finally:
            if original is not None:
                os.environ['HOLO_MODEL_LOAD_TIMEOUT'] = original

    def test_env_override_controls_import_timeout(self):
        """HOLO_MODEL_IMPORT_TIMEOUT env var should override default."""
        os.environ['HOLO_MODEL_IMPORT_TIMEOUT'] = '42'
        try:
            for mod in list(sys.modules.keys()):
                if mod.startswith('holo_index.core'):
                    del sys.modules[mod]
            from holo_index.core.holo_index import HOLO_MODEL_IMPORT_TIMEOUT
            assert HOLO_MODEL_IMPORT_TIMEOUT == 42.0, \
                f"Env override not applied: got {HOLO_MODEL_IMPORT_TIMEOUT}"
        finally:
            os.environ.pop('HOLO_MODEL_IMPORT_TIMEOUT', None)

    def test_skip_model_still_produces_lexical(self):
        """HOLO_SKIP_MODEL=1 should still produce retrieval_mode=lexical."""
        os.environ['HOLO_SKIP_MODEL'] = '1'
        os.environ['HOLO_SILENT'] = '1'
        try:
            if 'holo_index.core.holo_index' in sys.modules:
                del sys.modules['holo_index.core.holo_index']
            from holo_index.core.holo_index import HoloIndex
            HoloIndex._initialized = False
            HoloIndex._shared_state = {}
            holo = HoloIndex(quiet=True)
            assert holo.retrieval_mode == "lexical", \
                f"Expected 'lexical' with HOLO_SKIP_MODEL=1, got '{holo.retrieval_mode}'"
        finally:
            os.environ.pop('HOLO_SKIP_MODEL', None)
            os.environ.pop('HOLO_SILENT', None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
