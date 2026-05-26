# -*- coding: utf-8 -*-
"""Tests for main menu startup boundary enforcement.

MAIN_MENU_ANTIFAFM_STARTUP_BOUNDARY_FIX_PHASE1

Verifies that `python main.py` performs lightweight startup only:
- Environment preflight
- Logging setup (including OBS logging guard)
- Menu display / menu routing

It must NOT launch AntifaFM, OBS, metadata daemon, boot layer rotator,
YouTube broadcast setup, or broadcaster tasks before explicit user action.

The legacy ANTIFAFM_AUTO_START env var is ignored at menu boot.
"""

import re
from pathlib import Path


# Project root for file path assertions
PROJECT_ROOT = Path(__file__).parents[4]


class TestMainMenuStartupBoundary:
    """Verify main.py does not contain auto-start execution paths."""

    def test_main_py_does_not_execute_on_antifafm_auto_start_env(self):
        """main.py does not have executable code gated by ANTIFAFM_AUTO_START."""
        main_py = PROJECT_ROOT / "main.py"
        content = main_py.read_text(encoding="utf-8")

        # The old pattern was: if os.getenv("ANTIFAFM_AUTO_START", "0") == "1":
        # followed by OBS/broadcaster launch code. This should be gone.
        pattern = r'if\s+os\.getenv\s*\(\s*["\']ANTIFAFM_AUTO_START["\']'
        matches = re.findall(pattern, content)

        assert len(matches) == 0, (
            f"main.py still contains ANTIFAFM_AUTO_START execution gate. "
            f"Found {len(matches)} matches. The auto-start block should be removed."
        )

    def test_main_py_does_not_import_obs_controller_at_module_level_for_autostart(self):
        """main.py does not import OBSController for auto-start purposes."""
        main_py = PROJECT_ROOT / "main.py"
        content = main_py.read_text(encoding="utf-8")

        # The old pattern had: from ...obs_controller import OBSController
        # inside the ANTIFAFM_AUTO_START block. This should be gone.
        # Check for the specific auto-start pattern (OBSController + start_obs_stream)
        autostart_pattern = r'OBSController.*start_obs_stream|start_obs_stream.*OBSController'
        matches = re.findall(autostart_pattern, content, re.DOTALL)

        assert len(matches) == 0, (
            "main.py still contains OBSController auto-start pattern. "
            "The auto-start block should be removed."
        )

    def test_main_py_does_not_start_metadata_daemon_at_startup(self):
        """main.py does not start DynamicMetadataDaemon at module startup."""
        main_py = PROJECT_ROOT / "main.py"
        content = main_py.read_text(encoding="utf-8")

        # The old pattern had init_dynamic_metadata() call in the auto-start block
        pattern = r'init_dynamic_metadata\s*\(\s*\)'
        matches = re.findall(pattern, content)

        assert len(matches) == 0, (
            "main.py still contains init_dynamic_metadata() call. "
            "The auto-start block should be removed."
        )

    def test_main_py_does_not_start_boot_rotator_at_startup(self):
        """main.py does not start boot layer rotator at module startup."""
        main_py = PROJECT_ROOT / "main.py"
        content = main_py.read_text(encoding="utf-8")

        # The old pattern had run_boot_rotator() in a thread in the auto-start block
        pattern = r'rotator_thread\.start\s*\(\s*\)'
        matches = re.findall(pattern, content)

        assert len(matches) == 0, (
            "main.py still contains rotator_thread.start() call. "
            "The auto-start block should be removed."
        )

    def test_main_py_documents_boundary_fix(self):
        """main.py contains documentation about the startup boundary fix."""
        main_py = PROJECT_ROOT / "main.py"
        content = main_py.read_text(encoding="utf-8")

        assert "MAIN_MENU_ANTIFAFM_STARTUP_BOUNDARY_FIX_PHASE1" in content, (
            "main.py should document the startup boundary fix slice ID"
        )
        assert "ANTIFAFM_AUTO_START" in content, (
            "main.py should mention that ANTIFAFM_AUTO_START is now ignored"
        )


class TestExplicitLaunchPathPreserved:
    """Verify explicit AntifaFM launch paths exist in code."""

    def test_youtube_menu_has_broadcaster_handler(self):
        """youtube_menu.py contains the broadcaster menu handler function."""
        youtube_menu_py = (
            PROJECT_ROOT
            / "modules"
            / "infrastructure"
            / "cli"
            / "src"
            / "youtube_menu.py"
        )
        content = youtube_menu_py.read_text(encoding="utf-8")

        assert "def _handle_antifafm_broadcaster_menu" in content, (
            "youtube_menu.py should contain _handle_antifafm_broadcaster_menu function"
        )

    def test_preflight_module_exists(self):
        """The preflight module exists with expected functions."""
        preflight_py = (
            PROJECT_ROOT
            / "modules"
            / "platform_integration"
            / "antifafm_broadcaster"
            / "src"
            / "preflight.py"
        )
        content = preflight_py.read_text(encoding="utf-8")

        assert "def preflight_check_for_menu" in content, (
            "preflight.py should contain preflight_check_for_menu function"
        )
        assert "def run_preflight" in content, (
            "preflight.py should contain run_preflight function"
        )


class TestOBSLoggingGuardPreserved:
    """Verify PR #720 OBS logging guard remains effective."""

    def test_obs_logging_guard_module_exists(self):
        """The OBS logging guard module exists with expected functions."""
        guard_py = (
            PROJECT_ROOT
            / "modules"
            / "platform_integration"
            / "antifafm_broadcaster"
            / "src"
            / "obs_logging_guard.py"
        )
        content = guard_py.read_text(encoding="utf-8")

        assert "def install_obs_logging_guard" in content, (
            "obs_logging_guard.py should contain install_obs_logging_guard function"
        )

    def test_main_py_installs_logging_guard_early(self):
        """main.py installs OBS logging guard early in startup."""
        main_py = PROJECT_ROOT / "main.py"
        content = main_py.read_text(encoding="utf-8")

        # The guard should be installed near the top of main.py
        guard_pattern = r'install_obs_logging_guard\s*\(\s*\)'
        matches = list(re.finditer(guard_pattern, content))

        assert len(matches) >= 1, (
            "main.py should call install_obs_logging_guard() at startup"
        )

        # Verify it's early in the file (before line 200)
        first_match_pos = matches[0].start()
        lines_before = content[:first_match_pos].count('\n')
        assert lines_before < 200, (
            f"install_obs_logging_guard() should be called early in main.py "
            f"(found at line {lines_before + 1})"
        )

    def test_obs_controller_module_imports_guard(self):
        """OBSController module imports the logging guard."""
        obs_controller_py = (
            PROJECT_ROOT
            / "modules"
            / "platform_integration"
            / "antifafm_broadcaster"
            / "src"
            / "obs_controller.py"
        )
        content = obs_controller_py.read_text(encoding="utf-8")

        assert "install_obs_logging_guard" in content, (
            "obs_controller.py should import and call install_obs_logging_guard"
        )


class TestEnvSourceHandling:
    """Verify env source handling without reading real secrets."""

    def test_env_example_documents_auto_start_deprecation(self):
        """The .env.example file documents ANTIFAFM_AUTO_START deprecation."""
        env_example = PROJECT_ROOT / ".env.example"
        content = env_example.read_text(encoding="utf-8")

        assert "ANTIFAFM_AUTO_START" in content
        # Should indicate it's deprecated and/or set to 0
        assert "DEPRECATED" in content or "ANTIFAFM_AUTO_START=0" in content, (
            ".env.example should mark ANTIFAFM_AUTO_START as deprecated or set to 0"
        )

    def test_no_real_secrets_in_test_file(self):
        """This test file does not contain real secret values."""
        test_file = Path(__file__)
        content = test_file.read_text(encoding="utf-8")

        # Check for common secret patterns that should NOT appear
        # Long alphanumeric strings (potential API keys), OpenAI keys, Google keys
        dangerous_patterns = [
            r'sk-[a-zA-Z0-9]{20,}',  # OpenAI-style keys
            r'AIza[a-zA-Z0-9]{30,}',  # Google API keys
        ]

        for pattern in dangerous_patterns:
            matches = re.findall(pattern, content)
            assert len(matches) == 0, (
                f"Test file should not contain real-looking secrets. "
                f"Found pattern matching {pattern}"
            )
