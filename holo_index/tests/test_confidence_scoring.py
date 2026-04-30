# -*- coding: utf-8 -*-
"""Tests for HIA2 confidence scoring (pure heuristic, no LLM).

WSP 97: Confidence computed without LLM. Feature-flagged.
"""

import os
import pytest
from unittest.mock import patch


class TestEmitConfidenceFlag:
    """Test HOLO_EMIT_CONFIDENCE flag behavior."""

    def test_emit_confidence_false_by_default(self):
        from holo_index.core.search_engine import _emit_confidence
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("HOLO_EMIT_CONFIDENCE", None)
            assert _emit_confidence() is False

    def test_emit_confidence_false_when_zero(self):
        from holo_index.core.search_engine import _emit_confidence
        with patch.dict(os.environ, {"HOLO_EMIT_CONFIDENCE": "0"}):
            assert _emit_confidence() is False

    def test_emit_confidence_true_when_one(self):
        from holo_index.core.search_engine import _emit_confidence
        with patch.dict(os.environ, {"HOLO_EMIT_CONFIDENCE": "1"}):
            assert _emit_confidence() is True

    def test_emit_confidence_true_variants(self):
        from holo_index.core.search_engine import _emit_confidence
        for value in ["1", "true", "TRUE", "yes", "YES", "on", "ON"]:
            with patch.dict(os.environ, {"HOLO_EMIT_CONFIDENCE": value}):
                assert _emit_confidence() is True


class TestComputeConfidence:
    """Test _compute_confidence heuristic."""

    def test_confidence_basic_calculation(self):
        from holo_index.core.search_engine import _compute_confidence
        conf = _compute_confidence(0.5, 2.0, "code")
        assert abs(conf - 0.8) < 0.001

    def test_confidence_clamped_to_one(self):
        from holo_index.core.search_engine import _compute_confidence
        conf = _compute_confidence(0.9, 5.0, "code")
        assert conf == 1.0

    def test_confidence_clamped_to_zero(self):
        from holo_index.core.search_engine import _compute_confidence
        conf = _compute_confidence(0.0, 0.0, "code")
        assert conf == 0.1

    def test_confidence_between_zero_and_one(self):
        from holo_index.core.search_engine import _compute_confidence
        for sim in [0.0, 0.3, 0.5, 0.7, 1.0]:
            for kw in [0.0, 1.0, 5.0, 10.0]:
                for typ in ["code", "wsp", "test", "skillz", "other"]:
                    conf = _compute_confidence(sim, kw, typ)
                    assert 0.0 <= conf <= 1.0

    def test_confidence_increases_with_keyword_score(self):
        from holo_index.core.search_engine import _compute_confidence
        conf_low = _compute_confidence(0.5, 1.0, "code")
        conf_high = _compute_confidence(0.5, 5.0, "code")
        assert conf_high > conf_low


class TestFormatHitConfidence:
    """Test that _format_hit respects HOLO_EMIT_CONFIDENCE."""

    def test_confidence_absent_by_default(self):
        from holo_index.core.search_engine import _format_hit
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("HOLO_EMIT_CONFIDENCE", None)
            result = _format_hit("code", {"need": "test", "type": "code"}, "test.py", 0.8, 2.0, 1)
            assert "confidence" not in result

    def test_confidence_absent_when_zero(self):
        from holo_index.core.search_engine import _format_hit
        with patch.dict(os.environ, {"HOLO_EMIT_CONFIDENCE": "0"}):
            result = _format_hit("wsp", {"wsp": "WSP 97"}, "test.md", 0.7, 1.0, 1)
            assert "confidence" not in result

    def test_confidence_present_when_enabled(self):
        from holo_index.core.search_engine import _format_hit
        with patch.dict(os.environ, {"HOLO_EMIT_CONFIDENCE": "1"}):
            result = _format_hit("code", {"need": "test", "type": "code"}, "test.py", 0.8, 2.0, 1)
            assert "confidence" in result
            assert 0.0 <= result["confidence"] <= 1.0

    def test_confidence_for_all_kinds(self):
        from holo_index.core.search_engine import _format_hit
        test_cases = [
            ("code", {"need": "test", "type": "code"}, "test.py"),
            ("wsp", {"wsp": "WSP 97", "title": "Test"}, "test.md"),
            ("test", {"test_id": "test_1", "path": "test.py"}, "test.py"),
            ("skill", {"skill_name": "test_skill"}, "skill.md"),
        ]
        with patch.dict(os.environ, {"HOLO_EMIT_CONFIDENCE": "1"}):
            for kind, meta, doc in test_cases:
                result = _format_hit(kind, meta, doc, 0.7, 1.5, 1)
                assert "confidence" in result


class TestSortOrderUnchanged:
    """Verify confidence does not affect sort order."""

    def test_sort_key_unchanged_with_confidence(self):
        from holo_index.core.search_engine import _format_hit
        with patch.dict(os.environ, {"HOLO_EMIT_CONFIDENCE": "0"}):
            result_without = _format_hit("code", {"need": "test", "type": "code"}, "test.py", 0.8, 2.0, 1)
        with patch.dict(os.environ, {"HOLO_EMIT_CONFIDENCE": "1"}):
            result_with = _format_hit("code", {"need": "test", "type": "code"}, "test.py", 0.8, 2.0, 1)
        assert result_without["_sort_key"] == result_with["_sort_key"]


class TestNoLLMImports:
    """Verify search_engine.py has no Gemma/Qwen LLM imports."""

    def test_no_gemma_import(self):
        import inspect
        from holo_index.core import search_engine
        source = inspect.getsource(search_engine)
        assert "gemma_rag_inference" not in source
        assert "GemmaRAGInference" not in source

    def test_no_qwen_import(self):
        import inspect
        from holo_index.core import search_engine
        source = inspect.getsource(search_engine)
        assert "QwenAdvisor" not in source
        assert "llm_engine" not in source

    def test_no_llama_cpp_import(self):
        import inspect
        from holo_index.core import search_engine
        source = inspect.getsource(search_engine)
        assert "llama_cpp" not in source
