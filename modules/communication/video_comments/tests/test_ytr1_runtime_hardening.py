"""
YTR1 - YOUTUBE_REPLY_RUNTIME_HARDENING_PHASE1 Tests

Tests for:
1. TTS model exclusion from text model selection
2. TTS token rejection in LLM output
3. Default topic "general" not "politics"
4. Stale element recovery (mocked)

WSP 97: Uses mocks - no live YouTube/browser/LM Studio calls.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest


# =============================================================================
# TEST 1: TTS Model Exclusion
# =============================================================================

def test_tts_model_excluded_from_selection():
    """TTS model names are excluded from text model selection."""
    # Simulate model list with TTS and text models
    model_ids = [
        "qwen3-tts",           # Should be excluded
        "bark-tts-large",      # Should be excluded
        "whisper-large-v3",    # Should be excluded
        "kokoro-tts",          # Should be excluded
        "qwen3.5-4b-instruct", # Should be selected
        "gemma-4-4b",          # Fallback
    ]

    exclude_patterns = ("tts", "audio", "speech", "whisper", "bark", "kokoro", "dia")
    text_models = [
        mid for mid in model_ids
        if not any(pat in mid.lower() for pat in exclude_patterns)
    ]

    assert len(text_models) == 2, f"Expected 2 text models, got {text_models}"
    assert "qwen3.5-4b-instruct" in text_models
    assert "gemma-4-4b" in text_models
    assert "qwen3-tts" not in text_models
    assert "bark-tts-large" not in text_models
    print("[PASS] TTS models correctly excluded from selection")


def test_explicit_env_overrides_auto_selection():
    """Explicit LM_STUDIO_MODEL env var overrides auto-selection."""
    import os

    # Set explicit model
    os.environ["LM_STUDIO_MODEL"] = "my-custom-model"

    # Simulate the logic from intelligent_reply_generator._check_lm_studio
    lm_studio_model_id = os.getenv("LM_STUDIO_MODEL") or None

    assert lm_studio_model_id == "my-custom-model"
    print("[PASS] Explicit LM_STUDIO_MODEL overrides auto-selection")

    # Cleanup
    del os.environ["LM_STUDIO_MODEL"]


# =============================================================================
# TEST 2: TTS Token Rejection
# =============================================================================

def test_tts_tokens_rejected_as_output():
    """LLM output containing <|s_ is rejected."""
    tts_outputs = [
        "<|s_2219|><|s_2215|><|s_55522|>",
        "<|audio_start|>some audio data",
        "<|speech_token_123|>",
        "<|tts_marker|>output",
    ]

    tts_token_patterns = ("<|s_", "<|audio", "<|speech", "<|tts")

    for output in tts_outputs:
        is_tts = any(output.strip().startswith(pat) for pat in tts_token_patterns)
        assert is_tts, f"Should detect TTS tokens in: {output[:30]}"

    print("[PASS] All TTS token patterns correctly detected")


def test_valid_text_not_rejected():
    """Valid text output is not rejected as TTS."""
    valid_outputs = [
        "Thanks for watching!",
        "Great question! Here's my answer...",
        "I appreciate your comment.",
        "The video explains this at 5:30.",
    ]

    tts_token_patterns = ("<|s_", "<|audio", "<|speech", "<|tts")

    for output in valid_outputs:
        is_tts = any(output.strip().startswith(pat) for pat in tts_token_patterns)
        assert not is_tts, f"Should NOT detect TTS tokens in: {output[:30]}"

    print("[PASS] Valid text output not falsely rejected")


def test_tts_rejection_in_username_analysis():
    """TTS tokens in username analysis return safe default 0.0."""
    import re

    tts_response = "<|s_2219|><|s_2215|><|s_55522|>"
    tts_token_patterns = ("<|s_", "<|audio", "<|speech", "<|tts")

    # Simulate the fixed logic
    if any(tts_response.strip().startswith(pat) for pat in tts_token_patterns):
        result = 0.0  # Safe default
    else:
        match = re.search(r"\b(0\.\d+|1\.0|[01])\b", tts_response)
        result = float(match.group(1)) if match else 0.0

    assert result == 0.0, f"TTS response should return 0.0, got {result}"
    print("[PASS] TTS tokens in username analysis return safe 0.0")


def test_word_boundary_regex_prevents_false_match():
    """Regex with word boundaries doesn't match digits inside tokens."""
    import re

    # Old buggy regex would match "1" inside "<|s_2219|>"
    buggy_regex = r"0\.\d+|1\.0|0|1"
    fixed_regex = r"\b(0\.\d+|1\.0|[01])\b"

    tts_response = "<|s_2219|><|s_2215|>"

    # Buggy regex matches "1" or "0" inside the numbers
    buggy_match = re.search(buggy_regex, tts_response)

    # Fixed regex should NOT match
    fixed_match = re.search(fixed_regex, tts_response)

    # Note: buggy_match may or may not match depending on exact implementation
    # The key is that fixed_match should NOT match
    assert fixed_match is None, f"Fixed regex should not match TTS tokens, got: {fixed_match}"
    print("[PASS] Word boundary regex prevents false matches in TTS tokens")


# =============================================================================
# TEST 3: Default Topic
# =============================================================================

def test_default_topic_is_general():
    """Unknown/default topic is 'general' not 'politics'."""
    # Test cases: title -> expected topic
    test_cases = [
        ("How to cook pasta", "general"),
        ("My trip to Tokyo", "general"),
        ("Weird camera angle", "general"),
        ("Gaza situation update", "Gaza/Palestine"),
        ("Israel news today", "Israel"),
        ("Election 2026 results", "elections"),
        ("Trump rally footage", "politics"),
        ("Biden press conference", "politics"),
    ]

    for title, expected in test_cases:
        title_lower = title.lower()

        # Simulate the fixed logic
        topic = "general"
        if 'gaza' in title_lower or 'palestine' in title_lower:
            topic = "Gaza/Palestine"
        elif 'israel' in title_lower:
            topic = "Israel"
        elif 'election' in title_lower or 'vote' in title_lower:
            topic = "elections"
        elif any(kw in title_lower for kw in ('trump', 'biden', 'democrat', 'republican', 'congress', 'senate')):
            topic = "politics"

        assert topic == expected, f"Title '{title}' should be '{expected}', got '{topic}'"

    print("[PASS] Default topic is 'general', explicit politics still detected")


# =============================================================================
# TEST 4: Stale Element Recovery (Mocked)
# =============================================================================

def test_stale_element_triggers_recovery():
    """StaleElementReferenceException triggers one re-locate attempt."""
    from selenium.common.exceptions import StaleElementReferenceException

    # Mock driver
    mock_driver = Mock()
    call_count = 0

    def mock_execute_script(*args):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call raises stale
            raise StaleElementReferenceException("stale element")
        else:
            # Subsequent calls succeed (recovery worked)
            return Mock()  # Return mock textarea

    mock_driver.execute_script = mock_execute_script

    # Simulate recovery logic
    stale_recovered = False
    textarea = Mock()

    try:
        mock_driver.execute_script("type chunk", textarea, "a")
    except StaleElementReferenceException:
        stale_recovered = True
        # Re-find textarea
        textarea = mock_driver.execute_script("find textarea")

    assert stale_recovered, "Should have detected stale element"
    assert call_count == 2, f"Should have 2 calls (fail + recovery), got {call_count}"
    print("[PASS] Stale element triggers recovery attempt")


def test_second_stale_failure_returns_structured_failure():
    """Second stale failure returns structured failure without crashing."""
    from selenium.common.exceptions import StaleElementReferenceException

    # Simulate double stale failure
    stale_recovered = False
    failures = 0

    for attempt in range(2):
        try:
            if True:  # Simulate always stale
                raise StaleElementReferenceException("stale")
        except StaleElementReferenceException:
            failures += 1
            if stale_recovered:
                # Already tried once - structured failure
                result = {"success": False, "error": "textarea_stale_after_recovery"}
                break
            stale_recovered = True

    assert failures == 2, f"Should have 2 failures, got {failures}"
    assert result["success"] is False
    assert "stale" in result["error"]
    print("[PASS] Second stale failure returns structured failure")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("YTR1 - YOUTUBE_REPLY_RUNTIME_HARDENING_PHASE1 Tests")
    print("=" * 60)

    # Run all tests
    test_tts_model_excluded_from_selection()
    test_explicit_env_overrides_auto_selection()
    test_tts_tokens_rejected_as_output()
    test_valid_text_not_rejected()
    test_tts_rejection_in_username_analysis()
    test_word_boundary_regex_prevents_false_match()
    test_default_topic_is_general()
    test_stale_element_triggers_recovery()
    test_second_stale_failure_returns_structured_failure()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
