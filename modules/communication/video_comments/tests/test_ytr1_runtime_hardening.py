"""
YTR1 - YOUTUBE_REPLY_RUNTIME_HARDENING_PHASE1 Tests

Tests PRODUCTION CODE PATHS for:
1. TTS model exclusion from text model selection (intelligent_reply_generator._check_lm_studio)
2. TTS token rejection in LLM output (intelligent_reply_generator._analyze_username_agentically)
3. Default topic "general" not "politics" (comment_content_analyzer.analyze_video_context)
4. Stale element recovery (reply_executor - mocked driver)

WSP 97: Mocks external systems (LM Studio API, Selenium driver) - tests production code paths.
"""

import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest


# =============================================================================
# TEST A: TTS Model Exclusion - _check_lm_studio() production path
# =============================================================================

class TestTTSModelExclusion:
    """Test IntelligentReplyGenerator._check_lm_studio() TTS exclusion logic."""

    @patch('modules.communication.video_comments.src.intelligent_reply_generator.requests.get')
    @patch.dict(os.environ, {"LM_STUDIO_MODEL": ""}, clear=False)
    def test_tts_model_excluded_selects_text_model(self, mock_get):
        """_check_lm_studio excludes TTS models and selects qwen text model."""
        from modules.communication.video_comments.src.intelligent_reply_generator import IntelligentReplyGenerator

        # Mock LM Studio /v1/models response with TTS and text models
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "qwen3-tts"},           # TTS - should be excluded
                {"id": "bark-tts-large"},      # TTS - should be excluded
                {"id": "whisper-large-v3"},    # TTS - should be excluded
                {"id": "kokoro-tts"},          # TTS - should be excluded
                {"id": "qwen3.5-4b-instruct"}, # TEXT - should be selected (preferred)
                {"id": "gemma-4-4b"},          # TEXT - fallback
            ]
        }
        mock_get.return_value = mock_response

        # Instantiate and call production code
        gen = IntelligentReplyGenerator()
        gen.lm_studio_model_id = None  # Force auto-selection
        gen._check_lm_studio()

        # Verify production code selected text model, not TTS
        assert gen.lm_studio_available is True
        assert gen.lm_studio_model_id == "qwen3.5-4b-instruct"
        assert "tts" not in gen.lm_studio_model_id.lower()

    @patch('modules.communication.video_comments.src.intelligent_reply_generator.requests.get')
    @patch.dict(os.environ, {"LM_STUDIO_MODEL": ""}, clear=False)
    def test_only_tts_models_sets_unavailable(self, mock_get):
        """_check_lm_studio sets unavailable when only TTS models present."""
        from modules.communication.video_comments.src.intelligent_reply_generator import IntelligentReplyGenerator

        # Mock LM Studio with ONLY TTS models
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "qwen3-tts"},
                {"id": "bark-audio"},
                {"id": "dia-speech"},
            ]
        }
        mock_get.return_value = mock_response

        gen = IntelligentReplyGenerator()
        gen.lm_studio_model_id = None
        gen._check_lm_studio()

        # Production code should mark LM Studio unavailable
        assert gen.lm_studio_available is False

    @patch('modules.communication.video_comments.src.intelligent_reply_generator.requests.get')
    @patch.dict(os.environ, {"LM_STUDIO_MODEL": "my-explicit-model"}, clear=False)
    def test_explicit_env_var_overrides_auto_selection(self, mock_get):
        """Explicit LM_STUDIO_MODEL env var bypasses auto-selection."""
        from modules.communication.video_comments.src.intelligent_reply_generator import IntelligentReplyGenerator

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "qwen3-tts"}, {"id": "gemma-4-4b"}]
        }
        mock_get.return_value = mock_response

        gen = IntelligentReplyGenerator()
        # Constructor reads env var into lm_studio_model_id
        gen._check_lm_studio()

        # Explicit env var should be preserved (not overwritten by auto-selection)
        assert gen.lm_studio_model_id == "my-explicit-model"


# =============================================================================
# TEST B/C: TTS Token Rejection - _analyze_username_agentically() production path
# =============================================================================

class TestTTSTokenRejection:
    """Test IntelligentReplyGenerator._analyze_username_agentically() TTS rejection."""

    @patch('modules.communication.video_comments.src.intelligent_reply_generator.requests.post')
    def test_tts_tokens_return_safe_default(self, mock_post):
        """_analyze_username_agentically returns 0.0 for TTS token responses."""
        from modules.communication.video_comments.src.intelligent_reply_generator import IntelligentReplyGenerator

        # Mock LM Studio returning TTS tokens
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "<|s_2219|><|s_2215|><|s_55522|>"}}]
        }
        mock_post.return_value = mock_response

        gen = IntelligentReplyGenerator()
        gen.lm_studio_available = True
        gen.lm_studio_model_id = "test-model"
        gen.grok_connector = None  # Force LM Studio path

        # Call production method
        score = gen._analyze_username_agentically("TestUser")

        # Production code should reject TTS tokens and return 0.0
        assert score == 0.0

    @patch('modules.communication.video_comments.src.intelligent_reply_generator.requests.post')
    def test_valid_score_extracted_from_response(self, mock_post):
        """_analyze_username_agentically extracts valid float scores."""
        from modules.communication.video_comments.src.intelligent_reply_generator import IntelligentReplyGenerator

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "0.85"}}]
        }
        mock_post.return_value = mock_response

        gen = IntelligentReplyGenerator()
        gen.lm_studio_available = True
        gen.lm_studio_model_id = "test-model"
        gen.grok_connector = None

        score = gen._analyze_username_agentically("OffensiveName123")

        assert score == 0.85

    @patch('modules.communication.video_comments.src.intelligent_reply_generator.requests.post')
    def test_word_boundary_regex_prevents_false_match(self, mock_post):
        """Word boundary regex doesn't match digits inside TTS tokens."""
        from modules.communication.video_comments.src.intelligent_reply_generator import IntelligentReplyGenerator

        # Response that would trick buggy regex (contains "1" in token ID)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "<|audio_start|>1234"}}]
        }
        mock_post.return_value = mock_response

        gen = IntelligentReplyGenerator()
        gen.lm_studio_available = True
        gen.lm_studio_model_id = "test-model"
        gen.grok_connector = None

        score = gen._analyze_username_agentically("TestUser")

        # TTS token prefix detection should return 0.0 before regex runs
        assert score == 0.0


# =============================================================================
# TEST D: Default Topic - CommentContentAnalyzer.analyze_video_context() production path
# =============================================================================

class TestDefaultTopic:
    """Test CommentContentAnalyzer.analyze_video_context() default topic logic."""

    def test_default_topic_is_general(self):
        """Unknown video titles default to 'general' not 'politics'."""
        from modules.communication.video_comments.src.comment_content_analyzer import CommentContentAnalyzer

        analyzer = CommentContentAnalyzer()

        # Generic titles should get "general" topic
        test_cases = [
            "How to cook pasta",
            "My trip to Tokyo",
            "Weird camera angle",
            "Tech review 2026",
        ]

        for title in test_cases:
            result = analyzer.analyze_video_context(title)
            assert result.topic == "general", f"'{title}' should be 'general', got '{result.topic}'"

    def test_explicit_politics_keywords_detected(self):
        """Explicit politics keywords correctly detect 'politics' topic."""
        from modules.communication.video_comments.src.comment_content_analyzer import CommentContentAnalyzer

        analyzer = CommentContentAnalyzer()

        political_titles = [
            ("Trump rally footage", "politics"),
            ("Biden press conference", "politics"),
            ("Democrat convention highlights", "politics"),
            ("Republican debate 2026", "politics"),
        ]

        for title, expected in political_titles:
            result = analyzer.analyze_video_context(title)
            assert result.topic == expected, f"'{title}' should be '{expected}', got '{result.topic}'"

    def test_regional_topics_detected(self):
        """Regional topic keywords correctly detected."""
        from modules.communication.video_comments.src.comment_content_analyzer import CommentContentAnalyzer

        analyzer = CommentContentAnalyzer()

        regional_titles = [
            ("Gaza situation update", "Gaza/Palestine"),
            ("Palestine news today", "Gaza/Palestine"),
            ("Israel defense forces", "Israel"),
            ("Election 2026 results", "elections"),
        ]

        for title, expected in regional_titles:
            result = analyzer.analyze_video_context(title)
            assert result.topic == expected, f"'{title}' should be '{expected}', got '{result.topic}'"


# =============================================================================
# TEST E: Stale Element Recovery - BrowserReplyExecutor production path
# =============================================================================

class TestStaleElementRecovery:
    """
    Test stale element recovery in BrowserReplyExecutor.execute_reply().

    Note: Full execute_reply() testing requires complex DOM interaction mocking.
    These tests exercise the production code with mocked Selenium driver,
    verifying the stale recovery branch is reachable and behaves correctly.
    """

    @pytest.mark.asyncio
    async def test_execute_reply_recovers_from_stale_textarea(self):
        """
        BrowserReplyExecutor.execute_reply() recovers from StaleElementReferenceException.

        Tests the production code path in reply_executor.py lines 588-639.
        """
        from selenium.common.exceptions import StaleElementReferenceException
        from modules.communication.video_comments.skillz.tars_like_heart_reply.src.reply_executor import BrowserReplyExecutor

        # Track execute_script calls to inject stale at the right moment
        call_log = []
        typing_call_count = 0
        stale_raised = False

        def mock_execute_script(script, *args):
            nonlocal typing_call_count, stale_raised
            call_log.append(script[:50] if isinstance(script, str) else "non-string")

            # Detect typing call by script content (contains textContent +=)
            if isinstance(script, str) and "textContent +=" in script:
                typing_call_count += 1
                if typing_call_count == 1 and not stale_raised:
                    stale_raised = True
                    raise StaleElementReferenceException("textarea stale during typing")
                # Subsequent calls succeed
                return None

            # Reply button open - return success
            if isinstance(script, str) and "reply-button" in script.lower():
                return {"success": True}

            # Textarea find - return mock element
            if isinstance(script, str) and ("contenteditable-textarea" in script or "textarea" in script):
                return MagicMock()  # Mock textarea element

            # Submit button - return success
            if isinstance(script, str) and "submit" in script.lower():
                return {"success": True}

            # Default - return something truthy
            return MagicMock()

        mock_driver = MagicMock()
        mock_driver.execute_script.side_effect = mock_execute_script

        # Create executor with mocked driver
        selectors = {"comment_thread": "ytcp-comment-thread"}
        executor = BrowserReplyExecutor(
            driver=mock_driver,
            human=None,
            selectors=selectors,
            delay_multiplier=0.01  # Fast for testing
        )

        # Execute reply - should recover from stale and complete
        # Using short text to minimize async time
        result = await executor.execute_reply(comment_idx=1, reply_text="Hi")

        # Verify stale was raised and recovery attempted
        assert stale_raised, "StaleElementReferenceException should have been raised"
        assert typing_call_count >= 2, f"Should have retried typing after stale, got {typing_call_count} calls"

    @pytest.mark.asyncio
    async def test_execute_reply_fails_on_double_stale(self):
        """
        BrowserReplyExecutor.execute_reply() returns False after second stale failure.

        Tests the production code path in reply_executor.py lines 602-606.
        """
        from selenium.common.exceptions import StaleElementReferenceException
        from modules.communication.video_comments.skillz.tars_like_heart_reply.src.reply_executor import BrowserReplyExecutor

        stale_count = 0

        def mock_execute_script(script, *args):
            nonlocal stale_count

            # Always raise stale on typing calls
            if isinstance(script, str) and "textContent +=" in script:
                stale_count += 1
                raise StaleElementReferenceException(f"stale #{stale_count}")

            # Textarea find - return mock
            if isinstance(script, str) and ("contenteditable-textarea" in script or "textarea" in script):
                return MagicMock()

            # Other calls succeed
            return MagicMock()

        mock_driver = MagicMock()
        mock_driver.execute_script.side_effect = mock_execute_script

        selectors = {"comment_thread": "ytcp-comment-thread"}
        executor = BrowserReplyExecutor(
            driver=mock_driver,
            human=None,
            selectors=selectors,
            delay_multiplier=0.01
        )

        # Execute reply - should fail after double stale
        result = await executor.execute_reply(comment_idx=1, reply_text="X")

        # Verify double stale was hit and method returned False
        assert result is False, "Should return False after double stale"
        assert stale_count == 2, f"Should have exactly 2 stale exceptions, got {stale_count}"


# =============================================================================
# MAIN - pytest discovery
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("YTR1 - YOUTUBE_REPLY_RUNTIME_HARDENING_PHASE1 Tests")
    print("=" * 60)
    pytest.main([__file__, "-v"])
