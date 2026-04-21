# -*- coding: utf-8 -*-
"""
Tests for mps_m_scorer.py - MPS-M Quality Rating Tests

Tests run in HOLO_SKIP_MODEL=1 mode (no model dependencies).

WSP Compliance:
    WSP 5: Test Coverage
    WSP 15: MPS System
"""
import pytest

from holo_index.core.mps_m_scorer import (
    MemoryPriority,
    MpsScore,
    MpsMScorer,
    TRUST_WEIGHTS,
    score_holo_output,
)


class TestMemoryPriority:
    """Tests for MemoryPriority enum"""

    def test_priority_values(self):
        """Priority enum has expected values"""
        assert MemoryPriority.P0_CRITICAL.value == "P0"
        assert MemoryPriority.P1_HIGH.value == "P1"
        assert MemoryPriority.P2_MEDIUM.value == "P2"
        assert MemoryPriority.P3_LOW.value == "P3"
        assert MemoryPriority.P4_BACKLOG.value == "P4"


class TestMpsScore:
    """Tests for MpsScore dataclass"""

    def test_total_calculation(self):
        """Total is sum of all components"""
        score = MpsScore(
            reconstruction_cost=3,
            correctness_impact=4,
            time_sensitivity=2,
            decision_leverage=5
        )
        assert score.total == 14

    def test_priority_p0_critical(self):
        """Score >= 16 returns P0_CRITICAL"""
        score = MpsScore(5, 5, 4, 4)  # total = 18
        assert score.priority == MemoryPriority.P0_CRITICAL

    def test_priority_p1_high(self):
        """Score 13-15 returns P1_HIGH"""
        score = MpsScore(4, 4, 3, 3)  # total = 14
        assert score.priority == MemoryPriority.P1_HIGH

    def test_priority_p2_medium(self):
        """Score 10-12 returns P2_MEDIUM"""
        score = MpsScore(3, 3, 2, 3)  # total = 11
        assert score.priority == MemoryPriority.P2_MEDIUM

    def test_priority_p3_low(self):
        """Score 7-9 returns P3_LOW"""
        score = MpsScore(2, 2, 2, 2)  # total = 8
        assert score.priority == MemoryPriority.P3_LOW

    def test_priority_p4_backlog(self):
        """Score < 7 returns P4_BACKLOG"""
        score = MpsScore(1, 1, 1, 1)  # total = 4
        assert score.priority == MemoryPriority.P4_BACKLOG

    def test_boundary_16_is_p0(self):
        """Score exactly 16 is P0"""
        score = MpsScore(4, 4, 4, 4)  # total = 16
        assert score.priority == MemoryPriority.P0_CRITICAL

    def test_boundary_13_is_p1(self):
        """Score exactly 13 is P1"""
        score = MpsScore(4, 3, 3, 3)  # total = 13
        assert score.priority == MemoryPriority.P1_HIGH

    def test_boundary_10_is_p2(self):
        """Score exactly 10 is P2"""
        score = MpsScore(3, 3, 2, 2)  # total = 10
        assert score.priority == MemoryPriority.P2_MEDIUM

    def test_boundary_7_is_p3(self):
        """Score exactly 7 is P3"""
        score = MpsScore(2, 2, 2, 1)  # total = 7
        assert score.priority == MemoryPriority.P3_LOW


class TestTrustWeights:
    """Tests for TRUST_WEIGHTS constant"""

    def test_wsp_protocol_highest_trust(self):
        """WSP protocols have highest trust weight"""
        assert TRUST_WEIGHTS["wsp_protocol"] == 1.0

    def test_interface_high_trust(self):
        """Interface docs have high trust"""
        assert TRUST_WEIGHTS["interface"] == 0.9

    def test_generated_lowest_trust(self):
        """Generated content has lowest trust"""
        assert TRUST_WEIGHTS["generated"] == 0.5

    def test_all_weights_between_0_and_1(self):
        """All trust weights are between 0 and 1"""
        for weight in TRUST_WEIGHTS.values():
            assert 0 <= weight <= 1


class TestMpsMScorer:
    """Tests for MpsMScorer class"""

    def test_initialization(self):
        """Scorer initializes with default scores"""
        scorer = MpsMScorer()
        assert scorer.doc_type_scores is not None
        assert "wsp_protocol" in scorer.doc_type_scores

    def test_default_scores_exist(self):
        """Default scores defined for common doc types"""
        scorer = MpsMScorer()
        expected_types = [
            "wsp_protocol", "interface", "readme", "modlog",
            "roadmap", "code", "skill", "vocabulary"
        ]
        for doc_type in expected_types:
            assert doc_type in scorer.doc_type_scores

    def test_score_result_adds_mps_m_field(self):
        """score_result adds mps_m field to result"""
        scorer = MpsMScorer()
        result = {"location": "test/INTERFACE.md"}

        scored = scorer.score_result(result)

        assert "mps_m" in scored
        assert "doc_type" in scored["mps_m"]
        assert "total" in scored["mps_m"]

    def test_score_result_detects_wsp(self):
        """Detects WSP protocol from path"""
        scorer = MpsMScorer()
        result = {"location": "WSP_framework/src/WSP_15_Module.md"}

        scored = scorer.score_result(result)

        assert scored["mps_m"]["doc_type"] == "wsp_protocol"
        assert scored["mps_m"]["trust_weight"] == 1.0

    def test_score_result_detects_interface(self):
        """Detects interface doc from path"""
        scorer = MpsMScorer()
        result = {"location": "modules/test/INTERFACE.md"}

        scored = scorer.score_result(result)

        assert scored["mps_m"]["doc_type"] == "interface"

    def test_score_result_detects_readme(self):
        """Detects readme from path"""
        scorer = MpsMScorer()
        result = {"location": "modules/test/README.md"}

        scored = scorer.score_result(result)

        assert scored["mps_m"]["doc_type"] == "readme"

    def test_score_result_detects_modlog(self):
        """Detects modlog from path"""
        scorer = MpsMScorer()
        result = {"location": "modules/test/ModLog.md"}

        scored = scorer.score_result(result)

        assert scored["mps_m"]["doc_type"] == "modlog"

    def test_score_result_detects_roadmap(self):
        """Detects roadmap from path"""
        scorer = MpsMScorer()
        result = {"location": "modules/test/ROADMAP.md"}

        scored = scorer.score_result(result)

        assert scored["mps_m"]["doc_type"] == "roadmap"

    def test_score_result_detects_code(self):
        """Detects code from .py extension"""
        scorer = MpsMScorer()
        result = {"location": "modules/test/src/main.py"}

        scored = scorer.score_result(result)

        assert scored["mps_m"]["doc_type"] == "code"

    def test_score_result_detects_skill(self):
        """Detects skill from path"""
        scorer = MpsMScorer()
        result = {"location": "modules/test/skillz/my_skill.md"}

        scored = scorer.score_result(result)

        assert scored["mps_m"]["doc_type"] == "skill"

    def test_score_result_detects_vocabulary(self):
        """Detects vocabulary from path"""
        scorer = MpsMScorer()
        result = {"location": "memory/vocabulary/channel.json"}

        scored = scorer.score_result(result)

        assert scored["mps_m"]["doc_type"] == "vocabulary"

    def test_score_result_defaults_to_generated(self):
        """Unknown doc type defaults to generated"""
        scorer = MpsMScorer()
        result = {"location": "random/file.txt"}

        scored = scorer.score_result(result)

        assert scored["mps_m"]["doc_type"] == "generated"

    def test_score_result_from_explicit_type(self):
        """Uses explicit type field when available"""
        scorer = MpsMScorer()
        result = {"type": "wsp_protocol", "location": "any.txt"}

        scored = scorer.score_result(result)

        assert scored["mps_m"]["doc_type"] == "wsp_protocol"

    def test_effective_score_calculation(self):
        """Effective score = total * trust_weight"""
        scorer = MpsMScorer()
        result = {"location": "WSP_framework/src/WSP_15.md"}

        scored = scorer.score_result(result)

        expected_total = 17  # WSP default: 4+5+3+5
        expected_effective = expected_total * 1.0  # WSP trust = 1.0
        assert scored["mps_m"]["total"] == expected_total
        assert scored["mps_m"]["effective_score"] == expected_effective

    def test_score_bundle_adds_quality_metrics(self):
        """score_bundle adds quality_metrics to results"""
        scorer = MpsMScorer()
        results = {
            "code": [{"location": "test.py"}],
            "wsps": [],
            "skills": []
        }

        scored = scorer.score_bundle(results)

        assert "quality_metrics" in scored
        assert "total_mps_m" in scored["quality_metrics"]
        assert "avg_score" in scored["quality_metrics"]

    def test_score_bundle_with_multiple_results(self):
        """score_bundle handles multiple result types"""
        scorer = MpsMScorer()
        results = {
            "code": [
                {"location": "modules/test/src/main.py"},
                {"location": "modules/test/INTERFACE.md"},
            ],
            "wsps": [
                {"path": "WSP_framework/src/WSP_15.md"},
            ],
            "skills": [
                {"location": "modules/test/skillz/skill.md"},
            ]
        }

        scored = scorer.score_bundle(results)

        assert scored["quality_metrics"]["result_count"] == 4

    def test_score_bundle_empty_results(self):
        """score_bundle handles empty results"""
        scorer = MpsMScorer()
        results = {"code": [], "wsps": [], "skills": []}

        scored = scorer.score_bundle(results)

        assert scored["quality_metrics"]["result_count"] == 0
        assert scored["quality_metrics"]["avg_score"] == 0

    def test_score_bundle_priority_levels(self):
        """score_bundle sets correct priority based on avg_score"""
        scorer = MpsMScorer()
        # WSP has high score, so single WSP result should be high priority
        results = {
            "code": [],
            "wsps": [{"path": "WSP_framework/src/WSP_15.md"}],
            "skills": []
        }

        scored = scorer.score_bundle(results)

        # WSP effective = 17 * 1.0 = 17, avg = 17, P0
        assert scored["quality_metrics"]["priority"] == "P0"


class TestScoreHoloOutput:
    """Tests for score_holo_output convenience function"""

    def test_function_returns_scored_results(self):
        """Convenience function scores results"""
        results = {
            "code": [{"location": "test.py"}],
            "wsps": [],
            "skills": []
        }

        scored = score_holo_output(results)

        assert "quality_metrics" in scored

    def test_function_scores_all_hit_types(self):
        """Convenience function processes all hit types"""
        results = {
            "code": [{"location": "main.py"}],
            "wsps": [{"path": "WSP_framework/src/WSP.md"}],
            "skills": [{"location": "skillz/skill.md"}]
        }

        scored = score_holo_output(results)

        assert scored["quality_metrics"]["result_count"] == 3
        assert "mps_m" in scored["code"][0]
        assert "mps_m" in scored["wsps"][0]
        assert "mps_m" in scored["skills"][0]


class TestDocTypeDetection:
    """Additional tests for document type detection edge cases"""

    def test_wsp_underscore_pattern(self):
        """Detects WSP_ prefix pattern"""
        scorer = MpsMScorer()
        result = {"location": "docs/WSP_50_something.md"}
        assert scorer._detect_doc_type(result) == "wsp_protocol"

    def test_wsp_dash_pattern(self):
        """Detects WSP- prefix pattern"""
        scorer = MpsMScorer()
        result = {"location": "docs/wsp-50-something.md"}
        assert scorer._detect_doc_type(result) == "wsp_protocol"

    def test_type_field_wsp_detection(self):
        """Type field containing 'wsp' is detected"""
        scorer = MpsMScorer()
        result = {"type": "WSP Protocol", "location": "any.txt"}
        assert scorer._detect_doc_type(result) == "wsp_protocol"

    def test_type_field_exact_match(self):
        """Type field exact match in TRUST_WEIGHTS"""
        scorer = MpsMScorer()
        result = {"type": "code", "location": "any.txt"}
        assert scorer._detect_doc_type(result) == "code"

    def test_path_field_fallback(self):
        """Falls back to 'path' if 'location' missing"""
        scorer = MpsMScorer()
        result = {"path": "modules/test/INTERFACE.md"}
        assert scorer._detect_doc_type(result) == "interface"
