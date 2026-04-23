"""
YTR3 - Undetected Browser Anti-Detection Test Harness

Tests UndetectedBrowserManager with mocked undetected_chromedriver.
No live browser, no Chrome process, deterministic.

WSP 97: Mocks external systems (undetected_chromedriver), tests production code.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import os

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest


# =============================================================================
# TEST A: create_undetected_chrome - anti-detection options
# =============================================================================

class TestUndetectedChromeCreation:
    """Test UndetectedBrowserManager.create_undetected_chrome() options."""

    @patch('modules.infrastructure.foundups_selenium.src.undetected_browser.uc', create=True)
    def test_includes_anti_detection_arguments(self, mock_uc_module):
        """create_undetected_chrome includes standard anti-detection arguments."""
        # Import with mocked uc
        with patch.dict('sys.modules', {'undetected_chromedriver': mock_uc_module}):
            from modules.infrastructure.foundups_selenium.src.undetected_browser import UndetectedBrowserManager

            # Setup mocks
            mock_options = MagicMock()
            mock_uc_module.ChromeOptions.return_value = mock_options

            mock_driver = MagicMock()
            mock_uc_module.Chrome.return_value = mock_driver

            # Call production code
            UndetectedBrowserManager.create_undetected_chrome()

            # Verify anti-detection arguments were added
            add_argument_calls = [str(call) for call in mock_options.add_argument.call_args_list]
            call_str = ' '.join(add_argument_calls)

            assert 'window-size' in call_str, "Should set window size"
            assert 'disable-gpu' in call_str, "Should disable GPU"
            assert 'no-sandbox' in call_str, "Should disable sandbox"
            assert 'user-agent' in call_str, "Should set user agent"

    @patch('modules.infrastructure.foundups_selenium.src.undetected_browser.uc', create=True)
    def test_profile_path_added_when_provided(self, mock_uc_module):
        """create_undetected_chrome adds profile path when provided."""
        with patch.dict('sys.modules', {'undetected_chromedriver': mock_uc_module}):
            from modules.infrastructure.foundups_selenium.src.undetected_browser import UndetectedBrowserManager

            mock_options = MagicMock()
            mock_uc_module.ChromeOptions.return_value = mock_options

            mock_driver = MagicMock()
            mock_uc_module.Chrome.return_value = mock_driver

            # Call with profile path
            UndetectedBrowserManager.create_undetected_chrome(profile_path="/path/to/profile")

            # Verify profile path was added
            add_argument_calls = [str(call) for call in mock_options.add_argument.call_args_list]
            call_str = ' '.join(add_argument_calls)

            assert 'user-data-dir' in call_str, "Should add user-data-dir for profile"

    @patch('modules.infrastructure.foundups_selenium.src.undetected_browser.uc', create=True)
    def test_custom_options_added(self, mock_uc_module):
        """create_undetected_chrome adds custom options when provided."""
        with patch.dict('sys.modules', {'undetected_chromedriver': mock_uc_module}):
            from modules.infrastructure.foundups_selenium.src.undetected_browser import UndetectedBrowserManager

            mock_options = MagicMock()
            mock_uc_module.ChromeOptions.return_value = mock_options

            mock_driver = MagicMock()
            mock_uc_module.Chrome.return_value = mock_driver

            # Call with custom options
            UndetectedBrowserManager.create_undetected_chrome(
                options={"custom-flag": "value"}
            )

            # Verify custom option was added
            add_argument_calls = [str(call) for call in mock_options.add_argument.call_args_list]
            call_str = ' '.join(add_argument_calls)

            assert 'custom-flag' in call_str, "Should add custom options"


# =============================================================================
# TEST B: _inject_stealth_js - JavaScript injection
# =============================================================================

class TestStealthJsInjection:
    """Test UndetectedBrowserManager._inject_stealth_js() behavior."""

    def test_inject_stealth_js_calls_cdp(self):
        """_inject_stealth_js uses CDP to inject JavaScript."""
        from modules.infrastructure.foundups_selenium.src.undetected_browser import UndetectedBrowserManager

        mock_driver = MagicMock()

        UndetectedBrowserManager._inject_stealth_js(mock_driver)

        # Verify execute_cdp_cmd was called
        mock_driver.execute_cdp_cmd.assert_called_once()
        call_args = mock_driver.execute_cdp_cmd.call_args

        assert call_args[0][0] == 'Page.addScriptToEvaluateOnNewDocument'
        assert 'source' in call_args[0][1]
        assert 'navigator' in call_args[0][1]['source']

    def test_inject_stealth_js_handles_failure(self):
        """_inject_stealth_js handles CDP failure gracefully."""
        from modules.infrastructure.foundups_selenium.src.undetected_browser import UndetectedBrowserManager

        mock_driver = MagicMock()
        mock_driver.execute_cdp_cmd.side_effect = Exception("CDP not supported")

        # Should not raise
        UndetectedBrowserManager._inject_stealth_js(mock_driver)

        # Verify it tried
        mock_driver.execute_cdp_cmd.assert_called_once()


# =============================================================================
# TEST C: test_detection - detection analysis
# =============================================================================

class TestDetectionAnalysis:
    """Test UndetectedBrowserManager.test_detection() logic."""

    def test_detection_returns_dict(self):
        """test_detection returns dict with expected keys."""
        from modules.infrastructure.foundups_selenium.src.undetected_browser import UndetectedBrowserManager

        mock_driver = MagicMock()
        # Mock all execute_script calls to return "safe" values
        mock_driver.execute_script.side_effect = [
            False,           # navigator.webdriver
            False,           # chrome.webdriver
            5,               # plugins.length
            ['en-US', 'en'], # languages
            'present',       # connection
            8,               # hardwareConcurrency
        ]

        result = UndetectedBrowserManager.test_detection(mock_driver)

        assert isinstance(result, dict)
        assert 'detected' in result
        assert 'tests' in result
        assert 'verdict' in result

    def test_detection_identifies_bot(self):
        """test_detection identifies bot when webdriver=True."""
        from modules.infrastructure.foundups_selenium.src.undetected_browser import UndetectedBrowserManager

        mock_driver = MagicMock()
        # webdriver=True indicates bot
        mock_driver.execute_script.side_effect = [
            True,            # navigator.webdriver - BOT INDICATOR
            False,
            5,
            ['en-US', 'en'],
            'present',
            8,
        ]

        result = UndetectedBrowserManager.test_detection(mock_driver)

        assert result['detected'] is True
        assert 'BOT' in result['verdict']

    def test_detection_passes_human(self):
        """test_detection passes human when all checks pass."""
        from modules.infrastructure.foundups_selenium.src.undetected_browser import UndetectedBrowserManager

        mock_driver = MagicMock()
        # All values indicate human
        mock_driver.execute_script.side_effect = [
            False,           # webdriver
            False,           # chrome.webdriver
            5,               # plugins > 0
            ['en-US', 'en'], # languages present
            'present',       # connection present
            8,               # hardware
        ]

        result = UndetectedBrowserManager.test_detection(mock_driver)

        assert result['detected'] is False
        assert 'HUMAN' in result['verdict']

    def test_detection_catches_empty_plugins(self):
        """test_detection catches empty plugins (bot indicator)."""
        from modules.infrastructure.foundups_selenium.src.undetected_browser import UndetectedBrowserManager

        mock_driver = MagicMock()
        mock_driver.execute_script.side_effect = [
            False,
            False,
            0,               # plugins.length = 0 - BOT INDICATOR
            ['en-US', 'en'],
            'present',
            8,
        ]

        result = UndetectedBrowserManager.test_detection(mock_driver)

        assert result['detected'] is True


# =============================================================================
# TEST D: ImportError handling
# =============================================================================

class TestImportErrorHandling:
    """Test graceful handling of missing undetected-chromedriver."""

    def test_import_error_raised_when_missing(self):
        """create_undetected_chrome raises ImportError when uc not installed."""
        # This test verifies the error path exists in production code
        # We can't easily test actual ImportError without uninstalling the package
        # Instead we verify the code structure handles it

        from modules.infrastructure.foundups_selenium.src.undetected_browser import UndetectedBrowserManager

        # The method has try/except ImportError - verify by reading signature
        import inspect
        source = inspect.getsource(UndetectedBrowserManager.create_undetected_chrome)
        assert 'ImportError' in source, "Should handle ImportError"


# =============================================================================
# TEST E: Factory function
# =============================================================================

class TestFactoryFunction:
    """Test get_undetected_browser factory function."""

    @patch('modules.infrastructure.foundups_selenium.src.undetected_browser.UndetectedBrowserManager.create_undetected_chrome')
    def test_factory_calls_create(self, mock_create):
        """get_undetected_browser calls create_undetected_chrome."""
        from modules.infrastructure.foundups_selenium.src.undetected_browser import get_undetected_browser

        mock_driver = MagicMock()
        mock_create.return_value = mock_driver

        result = get_undetected_browser("/path/to/profile")

        mock_create.assert_called_once_with("/path/to/profile")
        assert result == mock_driver


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
