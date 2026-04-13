"""
Tests for Local LLM Backend Adapter Layer

WSP 77: Agent Coordination
WSP 91: DAEMON Observability

Tests:
1. Backend selection (LM Studio vs llama_cpp fallback)
2. Singleton cache reuse
3. Compatibility methods (generate_response, __call__)
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestIsLMStudioAvailable:
    """Test LM Studio availability detection."""

    def test_lm_studio_available_returns_true_when_api_responds(self):
        """When LM Studio API responds with models, return True."""
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            is_lm_studio_available,
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"data": [{"id": "test-model"}]}'
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            assert is_lm_studio_available() is True

    def test_lm_studio_unavailable_returns_false_on_connection_error(self):
        """When LM Studio API is unreachable, return False."""
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            is_lm_studio_available,
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("Connection refused")

            assert is_lm_studio_available() is False

    def test_lm_studio_unavailable_returns_false_on_empty_models(self):
        """When LM Studio has no models loaded, return False."""
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            is_lm_studio_available,
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"data": []}'
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            assert is_lm_studio_available() is False


class TestResolverBackendSelection:
    """Test resolver selects correct backend based on availability."""

    def test_resolve_qwen_prefers_lm_studio_when_available(self):
        """When LM Studio is available with qwen model, use LMStudioBackend."""
        from modules.infrastructure.shared_utilities.local_llm_resolver import (
            resolve_qwen_backend,
        )

        with patch(
            "modules.infrastructure.shared_utilities.local_llm_resolver.is_lm_studio_available"
        ) as mock_available:
            mock_available.return_value = True

            with patch(
                "modules.infrastructure.shared_utilities.local_llm_backends.LMStudioBackend.initialize"
            ) as mock_init:
                mock_init.return_value = True

                backend = resolve_qwen_backend(
                    model_path=Path("E:/models/qwen.gguf"), n_ctx=2048
                )

                assert backend is not None
                assert backend.backend_name == "lm_studio"

    def test_resolve_qwen_falls_back_to_llama_cpp_when_lm_studio_unavailable(self):
        """When LM Studio is unavailable, fall back to LlamaCppBackend."""
        from modules.infrastructure.shared_utilities.local_llm_resolver import (
            resolve_qwen_backend,
        )

        with patch(
            "modules.infrastructure.shared_utilities.local_llm_resolver.is_lm_studio_available"
        ) as mock_available:
            mock_available.return_value = False

            with patch(
                "modules.infrastructure.shared_utilities.local_llm_backends.LlamaCppBackend.initialize"
            ) as mock_init:
                mock_init.return_value = True

                backend = resolve_qwen_backend(
                    model_path=Path("E:/models/qwen.gguf"), n_ctx=2048
                )

                assert backend is not None
                assert backend.backend_name == "llama_cpp"

    def test_resolve_gemma_prefers_lm_studio_when_available(self):
        """When LM Studio is available with gemma model, use LMStudioBackend."""
        from modules.infrastructure.shared_utilities.local_llm_resolver import (
            resolve_gemma_backend,
        )

        with patch(
            "modules.infrastructure.shared_utilities.local_llm_resolver.is_lm_studio_available"
        ) as mock_available:
            mock_available.return_value = True

            with patch(
                "modules.infrastructure.shared_utilities.local_llm_backends.LMStudioBackend.initialize"
            ) as mock_init:
                mock_init.return_value = True

                backend = resolve_gemma_backend(
                    model_path=Path("E:/models/gemma.gguf"), n_ctx=1024
                )

                assert backend is not None
                assert backend.backend_name == "lm_studio"

    def test_resolve_gemma_falls_back_to_llama_cpp_when_lm_studio_unavailable(self):
        """When LM Studio is unavailable, fall back to LlamaCppBackend."""
        from modules.infrastructure.shared_utilities.local_llm_resolver import (
            resolve_gemma_backend,
        )

        with patch(
            "modules.infrastructure.shared_utilities.local_llm_resolver.is_lm_studio_available"
        ) as mock_available:
            mock_available.return_value = False

            with patch(
                "modules.infrastructure.shared_utilities.local_llm_backends.LlamaCppBackend.initialize"
            ) as mock_init:
                mock_init.return_value = True

                backend = resolve_gemma_backend(
                    model_path=Path("E:/models/gemma.gguf"), n_ctx=1024
                )

                assert backend is not None
                assert backend.backend_name == "llama_cpp"


class TestSingletonCacheReuse:
    """Test singleton engines are cached and reused."""

    def test_qwen_singleton_reuses_cached_engine(self):
        """Second call to get_qwen_engine returns cached instance."""
        from modules.infrastructure.shared_utilities import ai_engine_singletons

        # Reset state
        ai_engine_singletons.unload_engines()

        with patch(
            "modules.infrastructure.shared_utilities.local_llm_resolver.resolve_qwen_backend"
        ) as mock_resolve:
            mock_backend = MagicMock()
            mock_backend.backend_name = "lm_studio"
            mock_resolve.return_value = mock_backend

            # First call
            engine1 = ai_engine_singletons.get_qwen_engine()
            # Second call
            engine2 = ai_engine_singletons.get_qwen_engine()

            # Resolver should only be called once
            assert mock_resolve.call_count == 1
            assert engine1 is engine2

        # Cleanup
        ai_engine_singletons.unload_engines()

    def test_gemma_singleton_reuses_cached_engine(self):
        """Second call to get_gemma_engine returns cached instance."""
        from modules.infrastructure.shared_utilities import ai_engine_singletons

        # Reset state
        ai_engine_singletons.unload_engines()

        with patch(
            "modules.infrastructure.shared_utilities.local_llm_resolver.resolve_gemma_backend"
        ) as mock_resolve:
            mock_backend = MagicMock()
            mock_backend.backend_name = "lm_studio"
            mock_resolve.return_value = mock_backend

            # First call
            engine1 = ai_engine_singletons.get_gemma_engine()
            # Second call
            engine2 = ai_engine_singletons.get_gemma_engine()

            # Resolver should only be called once
            assert mock_resolve.call_count == 1
            assert engine1 is engine2

        # Cleanup
        ai_engine_singletons.unload_engines()

    def test_force_reinit_bypasses_cache(self):
        """force_reinit=True creates new engine even if cached."""
        from modules.infrastructure.shared_utilities import ai_engine_singletons

        # Reset state
        ai_engine_singletons.unload_engines()

        with patch(
            "modules.infrastructure.shared_utilities.local_llm_resolver.resolve_qwen_backend"
        ) as mock_resolve:
            mock_backend = MagicMock()
            mock_backend.backend_name = "lm_studio"
            mock_resolve.return_value = mock_backend

            # First call
            ai_engine_singletons.get_qwen_engine()
            # Second call with force_reinit
            ai_engine_singletons.get_qwen_engine(force_reinit=True)

            # Resolver should be called twice
            assert mock_resolve.call_count == 2

        # Cleanup
        ai_engine_singletons.unload_engines()


class TestCompatibilityMethods:
    """Test compatibility methods for existing callers."""

    def test_generate_response_extracts_text_from_completion(self):
        """generate_response() returns string extracted from completion dict."""
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            LMStudioBackend,
        )

        backend = LMStudioBackend(model_id="test-model")
        backend._initialized = True
        backend._client = MagicMock()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(text="Hello world")]
        backend._client.completions.create.return_value = mock_response

        result = backend.generate_response("Test prompt", max_tokens=10)

        assert isinstance(result, str)
        assert result == "Hello world"

    def test_callable_returns_dict_with_choices(self):
        """__call__() returns dict with 'choices' key."""
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            LMStudioBackend,
        )

        backend = LMStudioBackend(model_id="test-model")
        backend._initialized = True
        backend._client = MagicMock()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(text="Response text")]
        backend._client.completions.create.return_value = mock_response

        result = backend("Test prompt", max_tokens=10, temperature=0.1)

        assert isinstance(result, dict)
        assert "choices" in result

    def test_generate_response_returns_empty_on_failure(self):
        """generate_response() returns empty string on error."""
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            LMStudioBackend,
        )

        backend = LMStudioBackend(model_id="test-model")
        backend._initialized = False  # Not initialized

        result = backend.generate_response("Test prompt")

        assert result == ""

    def test_callable_returns_empty_choices_on_failure(self):
        """__call__() returns dict with empty text on error."""
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            LMStudioBackend,
        )

        backend = LMStudioBackend(model_id="test-model")
        backend._initialized = False  # Not initialized

        result = backend("Test prompt")

        assert "choices" in result
        assert result["choices"][0]["text"] == ""


class TestLlamaCppFallbackPath:
    """Test the llama_cpp fallback path works correctly."""

    def test_llama_cpp_backend_initializes_with_valid_model(self):
        """LlamaCppBackend.initialize() succeeds with valid model path."""
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            LlamaCppBackend,
        )

        # Llama is imported inside initialize(), so patch at llama_cpp module
        with patch("llama_cpp.Llama") as mock_llama:
            mock_llama.return_value = MagicMock()

            backend = LlamaCppBackend(
                model_path=Path("E:/models/test.gguf"), n_ctx=1024
            )

            # Mock path.exists()
            with patch.object(Path, "exists", return_value=True):
                result = backend.initialize()

            assert result is True
            assert backend._llm is not None

    def test_llama_cpp_backend_fails_with_missing_model(self):
        """LlamaCppBackend.initialize() fails if model file doesn't exist."""
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            LlamaCppBackend,
        )

        backend = LlamaCppBackend(
            model_path=Path("E:/models/nonexistent.gguf"), n_ctx=1024
        )

        # Model file doesn't exist
        with patch.object(Path, "exists", return_value=False):
            result = backend.initialize()

        assert result is False
        assert backend._llm is None

    def test_llama_cpp_create_completion_delegates_to_llm(self):
        """LlamaCppBackend.create_completion() calls underlying Llama instance."""
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            LlamaCppBackend,
        )

        backend = LlamaCppBackend(model_path=Path("E:/models/test.gguf"), n_ctx=1024)
        backend._llm = MagicMock()
        backend._llm.return_value = {"choices": [{"text": "Test output"}]}

        result = backend.create_completion("Test prompt", max_tokens=50)

        backend._llm.assert_called_once()
        assert "choices" in result
