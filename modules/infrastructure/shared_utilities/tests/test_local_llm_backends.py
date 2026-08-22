"""
Tests for Local LLM Backend Adapter Layer

WSP 77: Agent Coordination
WSP 91: DAEMON Observability

Tests:
1. Backend selection (LM Studio vs llama_cpp fallback)
2. Singleton cache reuse
3. Compatibility methods (generate_response, __call__)
"""

import json

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

        with patch(
            "modules.infrastructure.shared_utilities.lm_studio_native_transport._open_no_redirect"
        ) as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"models": []}'
            mock_response.geturl.return_value = "http://localhost:1234/api/v1/models"
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            assert is_lm_studio_available() is True

    def test_lm_studio_unavailable_returns_false_on_connection_error(self):
        """When LM Studio API is unreachable, return False."""
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            is_lm_studio_available,
        )

        with patch(
            "modules.infrastructure.shared_utilities.lm_studio_native_transport._open_no_redirect"
        ) as mock_urlopen:
            mock_urlopen.side_effect = Exception("Connection refused")

            assert is_lm_studio_available() is False

    def test_lm_studio_reachable_returns_true_on_empty_native_inventory(self):
        """An empty inventory proves server reachability, not model readiness."""
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            is_lm_studio_available,
        )

        with patch(
            "modules.infrastructure.shared_utilities.lm_studio_native_transport._open_no_redirect"
        ) as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"models": []}'
            mock_response.geturl.return_value = "http://localhost:1234/api/v1/models"
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            assert is_lm_studio_available() is True


class TestLMStudioNativeResidency:
    """Backend initialization must use native loaded-instance truth."""

    @patch("openai.OpenAI")
    @patch("modules.infrastructure.shared_utilities.lm_studio_native_transport._open_no_redirect")
    def test_installed_but_not_resident_is_not_initialized(self, urlopen, openai):
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            LMStudioBackend,
        )

        response = MagicMock()
        response.geturl.return_value = "http://localhost:1234/api/v1/models"
        response.read.return_value = json.dumps(
            {
                "models": [
                    {
                        "type": "llm",
                        "key": "nvidia/nemotron-3.5-lightning",
                        "loaded_instances": [],
                    }
                ]
            }
        ).encode()
        urlopen.return_value.__enter__.return_value = response
        backend = LMStudioBackend(model_id="nvidia/nemotron-3.5-lightning")

        assert backend.initialize() is False
        openai.assert_not_called()

    def test_native_openers_disable_environment_proxy_inheritance(self):
        import urllib.request

        from modules.infrastructure.shared_utilities import (
            lm_studio_native_transport as transport,
        )
        from modules.infrastructure.shared_utilities import local_llm_backends

        request = urllib.request.Request("http://localhost:1234/api/v1/models")
        for open_request in (
            transport._open_no_redirect,
            local_llm_backends._open_lm_studio_request,
        ):
            with patch("urllib.request.build_opener") as build:
                build.return_value.open.return_value = MagicMock()
                open_request(request, timeout=1.0)
            proxy = build.call_args.args[0]
            assert isinstance(proxy, urllib.request.ProxyHandler)
            assert proxy.proxies == {}

    @patch("openai.OpenAI")
    @patch("modules.infrastructure.shared_utilities.lm_studio_native_transport._open_no_redirect")
    def test_exact_native_instance_initializes_backend(self, urlopen, openai):
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            LMStudioBackend,
        )

        response = MagicMock()
        response.geturl.return_value = "http://localhost:1234/api/v1/models"
        response.read.return_value = json.dumps(
            {
                "models": [
                    {
                        "type": "llm",
                        "key": "nvidia/nemotron-3.5-lightning",
                        "loaded_instances": [
                            {"id": "nemotron-owned", "config": {"context_length": 32768}}
                        ],
                    }
                ]
            }
        ).encode()
        urlopen.return_value.__enter__.return_value = response
        backend = LMStudioBackend(
            model_id="nvidia/nemotron-3.5-lightning",
            expected_instance_id="nemotron-owned",
            api_token="test-token",
        )

        assert backend.initialize() is True
        assert backend.expected_instance_id == "nemotron-owned"
        assert openai.call_args.kwargs["api_key"] == "test-token"

    @patch("openai.OpenAI")
    @patch("modules.infrastructure.shared_utilities.lm_studio_native_transport._open_no_redirect")
    def test_unexpected_instance_identity_fails_closed(self, urlopen, openai):
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            LMStudioBackend,
        )

        response = MagicMock()
        response.geturl.return_value = "http://localhost:1234/api/v1/models"
        response.read.return_value = json.dumps(
            {
                "models": [
                    {
                        "type": "llm",
                        "key": "nvidia/nemotron-3.5-lightning",
                        "loaded_instances": [
                            {"id": "different", "config": {"context_length": 32768}}
                        ],
                    }
                ]
            }
        ).encode()
        urlopen.return_value.__enter__.return_value = response
        backend = LMStudioBackend(
            model_id="nvidia/nemotron-3.5-lightning",
            expected_instance_id="nemotron-owned",
        )

        assert backend.initialize() is False
        openai.assert_not_called()

    @patch(
        "modules.infrastructure.shared_utilities.local_llm_backends.inspect_lm_studio_model"
    )
    def test_openai_call_rejects_external_unload_before_provider_use(self, inspect):
        from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
            LMStudioModelState,
            LMStudioResidencyState,
        )
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            LMStudioBackend,
        )

        inspect.return_value = LMStudioModelState(
            "model", LMStudioResidencyState.INSTALLED_NOT_RESIDENT, ()
        )
        backend = LMStudioBackend(model_id="model", expected_instance_id="owned")
        backend._initialized = True
        backend._client = MagicMock()

        result = backend.create_completion("prompt")

        assert result == {"choices": [{"text": ""}]}
        backend._client.completions.create.assert_not_called()

    @patch(
        "modules.infrastructure.shared_utilities.local_llm_backends.inspect_lm_studio_model"
    )
    def test_openai_call_discards_output_if_instance_changes_after_use(self, inspect):
        from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
            LMStudioLoadedInstance,
            LMStudioModelState,
            LMStudioResidencyState,
        )
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            LMStudioBackend,
        )

        inspect.side_effect = [
            LMStudioModelState(
                "model",
                LMStudioResidencyState.RESIDENT,
                (LMStudioLoadedInstance("owned", {}),),
            ),
            LMStudioModelState(
                "model",
                LMStudioResidencyState.RESIDENT,
                (LMStudioLoadedInstance("changed", {}),),
            ),
        ]
        backend = LMStudioBackend(model_id="model", expected_instance_id="owned")
        backend._initialized = True
        backend._client = MagicMock()
        response = MagicMock()
        response.choices = [MagicMock(text="must be discarded")]
        backend._client.completions.create.return_value = response

        assert backend.create_completion("prompt") == {"choices": [{"text": ""}]}

    def test_native_chat_rejects_oversized_request_before_network(self):
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            LMStudioBackend,
        )

        backend = LMStudioBackend(model_id="model", expected_instance_id="owned")
        backend._initialized = True
        backend._require_exact_instance_unchanged = MagicMock()

        with patch(
            "modules.infrastructure.shared_utilities.local_llm_backends._open_lm_studio_request"
        ) as request:
            with pytest.raises(ValueError, match="native_request_too_large"):
                backend.create_native_chat(
                    input_text="x" * (LMStudioBackend.MAX_NATIVE_REQUEST_BYTES + 1),
                    system_prompt="bounded",
                    max_output_tokens=1,
                )

        request.assert_not_called()

    def test_native_chat_preserves_named_authentication_failure(self):
        import urllib.error

        from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
            LMStudioAuthenticationError,
        )
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            LMStudioBackend,
        )

        backend = LMStudioBackend(model_id="model", expected_instance_id="owned")
        backend._initialized = True
        backend._require_exact_instance_unchanged = MagicMock()
        error = urllib.error.HTTPError(
            "http://localhost:1234/api/v1/chat", 401, "secret", {}, None
        )

        with patch(
            "modules.infrastructure.shared_utilities.local_llm_backends._open_lm_studio_request",
            side_effect=error,
        ):
            with pytest.raises(LMStudioAuthenticationError):
                backend.create_native_chat(
                    input_text="bounded",
                    system_prompt="bounded",
                    max_output_tokens=1,
                )


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
        backend._require_exact_instance_unchanged = MagicMock()

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
        backend._require_exact_instance_unchanged = MagicMock()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(text="Response text")]
        backend._client.completions.create.return_value = mock_response

        result = backend("Test prompt", max_tokens=10, temperature=0.1)

        assert isinstance(result, dict)
        assert "choices" in result

    def test_lm_studio_chat_forwards_only_allowlisted_structured_controls(self):
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            LMStudioBackend,
        )

        backend = LMStudioBackend(model_id="test-model")
        backend._initialized = True
        backend._client = MagicMock()
        backend._require_exact_instance_unchanged = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"ok":true}'
        backend._client.chat.completions.create.return_value = mock_response
        response_format = {"type": "json_schema", "json_schema": {"name": "test"}}

        result = backend.create_chat_completion(
            [{"role": "user", "content": "Return JSON"}],
            max_tokens=64,
            temperature=0,
            response_format=response_format,
            seed=7,
            top_p=0.95,
            enable_thinking=False,
            extra_body={"not": "forwarded"},
            unauthorized_control="blocked",
        )

        assert result["choices"][0]["message"]["content"] == '{"ok":true}'
        call = backend._client.chat.completions.create.call_args.kwargs
        assert call["response_format"] == response_format
        assert call["seed"] == 7
        assert call["top_p"] == 0.95
        assert call["extra_body"] == {
            "chat_template_kwargs": {"enable_thinking": False}
        }
        assert "unauthorized_control" not in call

    @patch(
        "modules.infrastructure.shared_utilities.local_llm_backends._open_lm_studio_request"
    )
    def test_lm_studio_native_chat_uses_reasoning_off_and_bounded_read(self, urlopen):
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            LMStudioBackend,
        )

        response = MagicMock()
        response.geturl.return_value = "http://localhost:1234/api/v1/chat"
        response.read.return_value = (
            b'{"model_instance_id":"test-instance","stats":{"input_tokens":1},'
            b'"output":[{"type":"message","content":"{\\"ok\\":true}"}]}'
        )
        urlopen.return_value.__enter__.return_value = response
        backend = LMStudioBackend(
            model_id="test-model",
            request_timeout=90,
            expected_instance_id="test-instance",
            api_token="test-token",
        )
        backend._initialized = True
        backend._require_exact_instance_unchanged = MagicMock()

        result = backend.create_native_chat(
            input_text="Return JSON",
            system_prompt="JSON only",
            max_output_tokens=128,
            reasoning="off",
            max_response_bytes=4096,
        )

        assert result["output"][0]["content"] == '{"ok":true}'
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data)
        assert request.full_url == "http://localhost:1234/api/v1/chat"
        assert request.get_header("Authorization") == "Bearer test-token"
        assert payload["model"] == "test-instance"
        assert payload["reasoning"] == "off"
        assert payload["store"] is False
        assert payload["stream"] is False
        response.read.assert_called_once_with(4097)

    @pytest.mark.parametrize(
        "response_payload",
        [
            {"model_instance_id": "different", "stats": {}, "output": []},
            {
                "model_instance_id": "expected",
                "stats": {"model_load_time_seconds": 1.0},
                "output": [],
            },
        ],
    )
    @patch(
        "modules.infrastructure.shared_utilities.local_llm_backends._open_lm_studio_request"
    )
    def test_lm_studio_native_chat_rejects_wrong_or_jit_instance(
        self, urlopen, response_payload
    ):
        from modules.infrastructure.shared_utilities.local_llm_backends import (
            LMStudioBackend,
        )

        response = MagicMock()
        response.geturl.return_value = "http://localhost:1234/api/v1/chat"
        response.read.return_value = json.dumps(response_payload).encode()
        urlopen.return_value.__enter__.return_value = response
        backend = LMStudioBackend(
            model_id="model-key", expected_instance_id="expected"
        )
        backend._initialized = True
        backend._require_exact_instance_unchanged = MagicMock()

        result = backend.create_native_chat(
            input_text="Return JSON",
            system_prompt="JSON only",
            max_output_tokens=128,
        )

        assert result == {"output": []}

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
