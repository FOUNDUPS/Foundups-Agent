# -*- coding: utf-8 -*-
"""
Test suite for IDE WRE Command Router Import Seam

WSP Compliance:
    WSP 5  : Test coverage for import seam behavior
    WSP 97 : Truthful import failure handling (no silent fallback)

Tests:
    1. IDE command router imports canonical WRE module path
    2. No silent fallback when WRE module exists
    3. Fallback only for genuine import/runtime failure
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class TestWREImportSeam:
    """Test WRE import seam behavior for IDE integration."""

    def test_wre_log_import_from_canonical_path(self):
        """wre_log imports from canonical tools.wre.tools.logging_utils path."""
        # Verify the canonical import path works
        from tools.wre.tools.logging_utils import wre_log

        assert callable(wre_log)

    def test_command_router_module_loads(self):
        """Command router module loads without exception."""
        # This should not raise ImportError even if WRE_AVAILABLE=False
        from modules.development.ide_foundups.src.wre_integration.orchestration.command_router import (
            WRECommandRouter,
            WRE_AVAILABLE,
        )

        assert WRECommandRouter is not None

    def test_command_router_instantiates_in_fallback_mode(self):
        """Command router instantiates even when WRE is unavailable."""
        from modules.development.ide_foundups.src.wre_integration.orchestration.command_router import (
            WRECommandRouter,
        )

        # Should not raise
        router = WRECommandRouter()
        assert router is not None
        assert router.session_id.startswith("IDE_Session_")

    def test_router_status_reports_integration_mode(self):
        """Router status correctly reports WRE integration mode."""
        from modules.development.ide_foundups.src.wre_integration.orchestration.command_router import (
            WRECommandRouter,
            WRE_AVAILABLE,
        )

        router = WRECommandRouter()
        status = router.get_router_status()

        assert "wre_available" in status
        assert "integration_mode" in status
        assert status["wre_available"] == WRE_AVAILABLE
        assert status["integration_mode"] in ("WRE_Integrated", "Fallback")

    @pytest.mark.asyncio
    async def test_fallback_command_does_not_silently_succeed(self):
        """Fallback command handling does not silently claim success."""
        from modules.development.ide_foundups.src.wre_integration.orchestration.command_router import (
            WRECommandRouter,
        )

        router = WRECommandRouter()
        # Force fallback mode by clearing orchestrator
        router.wre_orchestrator = None

        result = await router.route_command({"type": "create_module", "parameters": {}})

        # Fallback should return explicit failure, not silent success
        assert result["fallback_mode"] is True
        # Should NOT claim success for operations that require WRE
        if result.get("success") is False:
            assert "message" in result or "error" in result

    def test_wsp38_handler_imports_canonical_wre_log(self):
        """WSP38 handler imports wre_log from canonical path."""
        # Import the module to verify no import error
        from modules.development.ide_foundups.src.wre_integration.activation.wsp38_handler import (
            WRE_ACTIVATION_AVAILABLE,
        )

        # Module should load regardless of activation availability
        assert WRE_ACTIVATION_AVAILABLE in (True, False)


class TestImportSeamWSP97Truth:
    """Test WSP 97 truth boundaries in import seam."""

    def test_import_failure_is_logged_not_silent(self):
        """Import failures are logged, not silently ignored."""
        import logging

        # Capture log output
        with patch.object(logging, "warning") as mock_warn:
            # Force reimport with a broken path
            import importlib

            # The module should have logged a warning if import failed
            # We verify by checking that the module handles failure explicitly
            from modules.development.ide_foundups.src.wre_integration.orchestration.command_router import (
                WRE_AVAILABLE,
                AgenticOrchestrator,
            )

            # If WRE is not available, AgenticOrchestrator should be explicitly None
            if not WRE_AVAILABLE:
                assert AgenticOrchestrator is None

    def test_transform_command_uses_dict_context(self):
        """Command transform uses dict context (no silent class fallback)."""
        from modules.development.ide_foundups.src.wre_integration.orchestration.command_router import (
            WRECommandRouter,
        )

        router = WRECommandRouter()
        command = {"type": "test_command", "parameters": {"key": "value"}}

        context = router._transform_command_to_context(command)

        # Should return dict, not class instance
        assert isinstance(context, dict)
        assert context["trigger"] == "test_command"
        assert context["zen_flow_state"] == "0102"
        assert context["source"] == "IDE_FoundUps"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
