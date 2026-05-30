"""Tests for the LM Studio dependency boundary gate.

Slice: LM_STUDIO_DEPENDENCY_BOUNDARY_DOC_AND_GATE_PHASE1

Verifies that LM Studio is a clearly bounded OPTIONAL local dependency:
1. LM Studio absent + GGUF fallback available -> fallback state/message is clear.
2. LM Studio absent + required path -> named unavailable error w/ operator action.
3. LM Studio available -> happy path (LMStudioBackend) preserved.
4. local_llm_resolver never launches LM Studio (no subprocess, no launcher).
5. No live LM Studio process, no network calls, no .env reads (all probes mocked).
6. Existing YouTube/DAE dependency launch still lives in the explicit launcher.

WSP 77: Agent Coordination
WSP 97: Truthful state distinction - LM Studio absence is explicit, not silent.
"""

import inspect
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

RESOLVER = "modules.infrastructure.shared_utilities.local_llm_resolver"


# ---------------------------------------------------------------------------
# (1)/(3) Probe-only availability classification - named states
# ---------------------------------------------------------------------------
class TestProbeAvailabilityState:
    def test_lm_studio_ready_when_probe_succeeds(self):
        from modules.infrastructure.shared_utilities.local_llm_resolver import (
            LocalLLMAvailability,
            probe_backend_availability,
        )

        with patch(f"{RESOLVER}.is_lm_studio_available", return_value=True):
            assert probe_backend_availability() is LocalLLMAvailability.LM_STUDIO_READY

    def test_fallback_state_when_lm_studio_absent_but_gguf_exists(self):
        from modules.infrastructure.shared_utilities.local_llm_resolver import (
            LocalLLMAvailability,
            probe_backend_availability,
        )

        with patch(f"{RESOLVER}.is_lm_studio_available", return_value=False):
            with patch.object(Path, "exists", return_value=True):
                status = probe_backend_availability(model_path=Path("E:/models/qwen.gguf"))

        assert status is LocalLLMAvailability.FALLBACK_LLAMA_CPP

    def test_unavailable_state_when_no_lm_studio_and_no_fallback(self):
        from modules.infrastructure.shared_utilities.local_llm_resolver import (
            LocalLLMAvailability,
            probe_backend_availability,
        )

        with patch(f"{RESOLVER}.is_lm_studio_available", return_value=False):
            status = probe_backend_availability(model_path=None)

        assert status is LocalLLMAvailability.UNAVAILABLE


# ---------------------------------------------------------------------------
# (1) Fallback messaging is clear (no false/silent warnings)
# ---------------------------------------------------------------------------
class TestFallbackMessageClarity:
    def test_fallback_operator_action_states_llama_cpp_and_non_launch(self):
        from modules.infrastructure.shared_utilities.local_llm_resolver import (
            LocalLLMAvailability,
            operator_action_for,
        )

        msg = operator_action_for(LocalLLMAvailability.FALLBACK_LLAMA_CPP)
        assert "llama.cpp" in msg
        assert "does not auto-launch" in msg

    def test_unavailable_operator_action_is_actionable(self):
        from modules.infrastructure.shared_utilities.local_llm_resolver import (
            LocalLLMAvailability,
            operator_action_for,
        )

        msg = operator_action_for(LocalLLMAvailability.UNAVAILABLE)
        assert "dependency launcher" in msg
        assert "model_path" in msg

    def test_resolver_logs_clear_fallback_when_lm_studio_absent(self, caplog):
        from modules.infrastructure.shared_utilities.local_llm_resolver import (
            resolve_qwen_backend,
        )

        with patch(f"{RESOLVER}.is_lm_studio_available", return_value=False):
            with patch(f"{RESOLVER}.LlamaCppBackend") as mock_cls:
                mock_backend = MagicMock()
                mock_backend.initialize.return_value = True
                mock_backend.backend_name = "llama_cpp"
                mock_cls.return_value = mock_backend
                with caplog.at_level(logging.INFO):
                    backend = resolve_qwen_backend(model_path=Path("E:/models/qwen.gguf"))

        assert backend is mock_backend
        assert any("llama.cpp" in r.getMessage() for r in caplog.records), (
            "Resolver should log a clear fallback message naming llama.cpp"
        )


# ---------------------------------------------------------------------------
# (2) Required path -> named unavailable error with operator action
# ---------------------------------------------------------------------------
class TestRequiredPathNamedError:
    def test_require_raises_named_error_when_lm_studio_absent(self):
        from modules.infrastructure.shared_utilities.local_llm_resolver import (
            LMStudioUnavailableError,
            require_lm_studio_backend,
        )

        with patch(f"{RESOLVER}.is_lm_studio_available", return_value=False):
            with pytest.raises(LMStudioUnavailableError) as exc:
                require_lm_studio_backend(model_id="ui-tars")

        text = str(exc.value)
        assert "LM Studio" in text
        assert "dependency launcher" in text

    def test_require_returns_backend_when_available(self):
        from modules.infrastructure.shared_utilities.local_llm_resolver import (
            require_lm_studio_backend,
        )

        with patch(f"{RESOLVER}.is_lm_studio_available", return_value=True):
            with patch(f"{RESOLVER}.LMStudioBackend") as mock_cls:
                mock_backend = MagicMock()
                mock_backend.initialize.return_value = True
                mock_backend.backend_name = "lm_studio"
                mock_cls.return_value = mock_backend
                backend = require_lm_studio_backend(model_id="ui-tars")

        assert backend is mock_backend
        assert backend.backend_name == "lm_studio"

    def test_require_raises_when_reachable_but_model_not_loaded(self):
        from modules.infrastructure.shared_utilities.local_llm_resolver import (
            LMStudioUnavailableError,
            require_lm_studio_backend,
        )

        with patch(f"{RESOLVER}.is_lm_studio_available", return_value=True):
            with patch(f"{RESOLVER}.LMStudioBackend") as mock_cls:
                mock_backend = MagicMock()
                mock_backend.initialize.return_value = False
                mock_cls.return_value = mock_backend
                with pytest.raises(LMStudioUnavailableError) as exc:
                    require_lm_studio_backend(model_id="ui-tars")

        assert "not loaded" in str(exc.value)


# ---------------------------------------------------------------------------
# (3) Happy path preserved (no model behavior change)
# ---------------------------------------------------------------------------
class TestHappyPathPreserved:
    def test_resolve_qwen_uses_lm_studio_when_available(self):
        from modules.infrastructure.shared_utilities.local_llm_resolver import (
            resolve_qwen_backend,
        )

        with patch(f"{RESOLVER}.is_lm_studio_available", return_value=True):
            with patch(f"{RESOLVER}.LMStudioBackend") as mock_cls:
                mock_backend = MagicMock()
                mock_backend.initialize.return_value = True
                mock_backend.backend_name = "lm_studio"
                mock_cls.return_value = mock_backend
                backend = resolve_qwen_backend(model_path=Path("E:/models/qwen.gguf"))

        assert backend.backend_name == "lm_studio"

    def test_resolve_gemma_falls_back_to_llama_cpp_when_lm_studio_absent(self):
        from modules.infrastructure.shared_utilities.local_llm_resolver import (
            resolve_gemma_backend,
        )

        with patch(f"{RESOLVER}.is_lm_studio_available", return_value=False):
            with patch(f"{RESOLVER}.LlamaCppBackend") as mock_cls:
                mock_backend = MagicMock()
                mock_backend.initialize.return_value = True
                mock_backend.backend_name = "llama_cpp"
                mock_cls.return_value = mock_backend
                backend = resolve_gemma_backend(model_path=Path("E:/models/gemma.gguf"))

        assert backend.backend_name == "llama_cpp"


# ---------------------------------------------------------------------------
# (4)/(5) Resolver is probe-only - never launches LM Studio / no subprocess
# ---------------------------------------------------------------------------
class TestResolverProbesOnly:
    def test_resolve_never_calls_subprocess(self):
        from modules.infrastructure.shared_utilities.local_llm_resolver import (
            resolve_qwen_backend,
        )

        with patch(f"{RESOLVER}.is_lm_studio_available", return_value=False):
            with patch("subprocess.Popen") as mock_popen:
                backend = resolve_qwen_backend(model_path=None)

        assert backend is None
        mock_popen.assert_not_called()

    def test_require_never_calls_subprocess(self):
        from modules.infrastructure.shared_utilities.local_llm_resolver import (
            LMStudioUnavailableError,
            require_lm_studio_backend,
        )

        with patch(f"{RESOLVER}.is_lm_studio_available", return_value=False):
            with patch("subprocess.Popen") as mock_popen:
                with pytest.raises(LMStudioUnavailableError):
                    require_lm_studio_backend(model_id="ui-tars")

        mock_popen.assert_not_called()

    def test_resolver_does_not_import_launch_symbols(self):
        import modules.infrastructure.shared_utilities.local_llm_resolver as resolver_mod

        # The resolver must not pull launch/subprocess machinery into its namespace.
        assert not hasattr(resolver_mod, "launch_lm_studio")
        assert not hasattr(resolver_mod, "ensure_dependencies")
        assert not hasattr(resolver_mod, "subprocess")


# ---------------------------------------------------------------------------
# (6) Launch behavior still lives in the explicit dependency launcher
# ---------------------------------------------------------------------------
class TestDaeLaunchBoundaryIntact:
    def test_launch_lives_in_dependency_launcher(self):
        from modules.infrastructure.dependency_launcher.src import dae_dependencies

        assert hasattr(dae_dependencies, "launch_lm_studio")
        assert hasattr(dae_dependencies, "ensure_dependencies")

    def test_ensure_dependencies_still_gates_lm_studio(self):
        from modules.infrastructure.dependency_launcher.src import dae_dependencies

        sig = inspect.signature(dae_dependencies.ensure_dependencies)
        assert "require_lm_studio" in sig.parameters


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
