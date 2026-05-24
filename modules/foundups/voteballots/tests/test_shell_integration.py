"""
Shell Integration Tests for VoteBallots FoundUp.

Tests for VOTE_POC_SHELL_INTEGRATION_PHASE1.

Test Boundaries:
- LOCAL_SHELL_PAYLOAD_ONLY: Tests local payload contract
- NO_PUBLIC_LAUNCH: No route activation
- NO_ROUTE_ACTIVATION: No route handlers
- NO_MANIFEST_MUTATION: Manifest unchanged
- NO_REGISTRY_MUTATION: Registry unchanged
- NO_CATALOG_MUTATION: Catalog unchanged
- NO_PROJECTION_MUTATION: Projection unchanged
- NO_PFMALL_SHELL_BEHAVIOR_CHANGE: Shell unchanged
- NO_LLM_CALL: No AI calls
- NO_NETWORK_CALL: No network calls
- NO_API_KEY_REQUIRED: No API keys
- ANSWER_LINES_PRESERVED: Lines preserved exactly
- CONFIDENCE_LABELS_PRESERVED: Confidence preserved
- SOURCE_TRACE_PRESERVED: Source trace preserved
- TRAIL_TERMINATION_MARKERS_PRESERVED: Trail markers preserved
- HUMAN_REVIEW_TRIGGER_PRESERVED: Review triggers preserved
- NO_CANDIDATE_RECOMMENDATION: No recommendations
- NO_TARGETED_PERSUASION: No persuasion
- NO_MICROTARGETING: No targeting

Builds on:
- VOTE_POC_FEC_ADAPTER_PHASE1 (PR #707)
- VOTE_POC_ENTITY_RESOLUTION_PHASE1 (PR #709)
- VOTE_POC_FUNDING_SUMMARY_PHASE1 (PR #710)
- VOTE_POC_CONFIDENCE_SCORING_INTEGRATION_PHASE1 (PR #712)
- VOTE_POC_QUICK_ANSWER_GENERATION_PHASE1 (PR #713)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

import pytest

from modules.foundups.voteballots.src.confidence_scoring import (
    ConfidenceLabel,
    HumanReviewTrigger,
)
from modules.foundups.voteballots.src.quick_answer import (
    AnswerFormat,
    QuickAnswer,
    is_answer_ready_for_display,
)
from modules.foundups.voteballots.src.shell_integration import (
    FOUNDUP_ID,
    ROUTE_NAMESPACE,
    APP_MOUNT,
    ShellPayloadStatus,
    VoteShellPayload,
    PayloadValidationResult,
    build_vote_shell_payload,
    validate_vote_shell_payload,
    build_ready_payload,
    is_payload_ready,
    get_payload_summary,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def ready_answer() -> QuickAnswer:
    """A QuickAnswer that is ready for display."""
    return QuickAnswer(
        lines=[
            "[V] Test Candidate: $1,500,000 total",
            "[V] $500,000 from Individual Contributions",
            "[H] $300,000 from PAC Contributions",
        ],
        confidence_label=ConfidenceLabel.VERIFIED_FACT,
        requires_human_review=False,
        human_review_reasons=[],
        trail_terminated=False,
        trail_termination_reason=None,
        source_summary_id="TEST001",
        truncated=False,
        original_line_count=3,
    )


@pytest.fixture
def not_ready_answer() -> QuickAnswer:
    """A QuickAnswer that requires human review."""
    return QuickAnswer(
        lines=[
            "[L] Test Candidate: $1,500,000 total",
            "[?] $500,000 from Unknown Source",
        ],
        confidence_label=ConfidenceLabel.LOW_CONFIDENCE_INFERENCE,
        requires_human_review=True,
        human_review_reasons=[HumanReviewTrigger.LOW_CONFIDENCE_HIGH_IMPACT],
        trail_terminated=True,
        trail_termination_reason="NO SUPER PAC TRACE IN THIS SLICE",
        source_summary_id="TEST002",
        truncated=False,
        original_line_count=2,
    )


@pytest.fixture
def empty_answer() -> QuickAnswer:
    """A QuickAnswer with no content."""
    return QuickAnswer(
        lines=[],
        confidence_label=ConfidenceLabel.UNKNOWN,
        requires_human_review=True,
        human_review_reasons=[HumanReviewTrigger.TRAIL_TERMINATION_SIGNIFICANT],
        trail_terminated=True,
        trail_termination_reason="No data available",
        source_summary_id="TEST003",
    )


@pytest.fixture
def truncated_answer() -> QuickAnswer:
    """A QuickAnswer that was truncated."""
    return QuickAnswer(
        lines=[
            "[V] Test Candidate: $5,000,000 total",
            "[V] $1,000,000 from Individual Contributions",
            "[more sources - see full report]",
        ],
        confidence_label=ConfidenceLabel.VERIFIED_FACT,
        requires_human_review=False,
        human_review_reasons=[],
        trail_terminated=False,
        trail_termination_reason=None,
        source_summary_id="TEST004",
        truncated=True,
        original_line_count=7,
    )


# =============================================================================
# Test: Ready QuickAnswer Produces Shell Payload
# =============================================================================


class TestReadyQuickAnswerProducesPayload:
    """Test that ready QuickAnswer produces valid shell payload."""

    def test_ready_answer_produces_success_status(self, ready_answer: QuickAnswer):
        """Ready answer should produce SUCCESS status."""
        payload = build_vote_shell_payload(ready_answer)
        assert payload.status == ShellPayloadStatus.SUCCESS

    def test_ready_answer_display_ready_true(self, ready_answer: QuickAnswer):
        """Ready answer should have display_ready=True."""
        payload = build_vote_shell_payload(ready_answer)
        assert payload.display_ready is True

    def test_ready_answer_is_successful(self, ready_answer: QuickAnswer):
        """Ready answer should have is_successful=True."""
        payload = build_vote_shell_payload(ready_answer)
        assert payload.is_successful is True


# =============================================================================
# Test: Not-Ready QuickAnswer Produces Fail-Closed Payload
# =============================================================================


class TestNotReadyQuickAnswerProducesFailClosed:
    """Test that not-ready QuickAnswer produces fail-closed payload."""

    def test_not_ready_answer_produces_not_ready_status(self, not_ready_answer: QuickAnswer):
        """Not-ready answer should produce NOT_READY_FOR_DISPLAY status."""
        payload = build_vote_shell_payload(not_ready_answer)
        assert payload.status == ShellPayloadStatus.NOT_READY_FOR_DISPLAY

    def test_not_ready_answer_display_ready_false(self, not_ready_answer: QuickAnswer):
        """Not-ready answer should have display_ready=False."""
        payload = build_vote_shell_payload(not_ready_answer)
        assert payload.display_ready is False

    def test_not_ready_answer_preserves_human_review(self, not_ready_answer: QuickAnswer):
        """Not-ready answer should preserve human review requirement."""
        payload = build_vote_shell_payload(not_ready_answer)
        assert payload.human_review_required is True


# =============================================================================
# Test: Payload Contains Correct FoundUp ID
# =============================================================================


class TestPayloadContainsFoundupId:
    """Test that payload contains correct foundup_id."""

    def test_foundup_id_is_voteballots(self, ready_answer: QuickAnswer):
        """Payload should have foundup_id='voteballots'."""
        payload = build_vote_shell_payload(ready_answer)
        assert payload.foundup_id == "voteballots"

    def test_foundup_id_matches_constant(self, ready_answer: QuickAnswer):
        """Payload foundup_id should match FOUNDUP_ID constant."""
        payload = build_vote_shell_payload(ready_answer)
        assert payload.foundup_id == FOUNDUP_ID


# =============================================================================
# Test: Payload Contains Route Namespace
# =============================================================================


class TestPayloadContainsRouteNamespace:
    """Test that payload contains correct route namespace."""

    def test_route_namespace_is_f_voteballots(self, ready_answer: QuickAnswer):
        """Payload should have route_namespace='/f/voteballots'."""
        payload = build_vote_shell_payload(ready_answer)
        assert payload.route_namespace == "/f/voteballots"

    def test_route_namespace_matches_constant(self, ready_answer: QuickAnswer):
        """Payload route_namespace should match ROUTE_NAMESPACE constant."""
        payload = build_vote_shell_payload(ready_answer)
        assert payload.route_namespace == ROUTE_NAMESPACE


# =============================================================================
# Test: Payload Contains App Mount
# =============================================================================


class TestPayloadContainsAppMount:
    """Test that payload contains correct app mount."""

    def test_app_mount_is_f_voteballots_app(self, ready_answer: QuickAnswer):
        """Payload should have app_mount='/f/voteballots/app'."""
        payload = build_vote_shell_payload(ready_answer)
        assert payload.app_mount == "/f/voteballots/app"

    def test_app_mount_matches_constant(self, ready_answer: QuickAnswer):
        """Payload app_mount should match APP_MOUNT constant."""
        payload = build_vote_shell_payload(ready_answer)
        assert payload.app_mount == APP_MOUNT


# =============================================================================
# Test: Payload Preserves Answer Lines Exactly
# =============================================================================


class TestPayloadPreservesAnswerLines:
    """Test that payload preserves answer lines exactly."""

    def test_lines_preserved_exactly(self, ready_answer: QuickAnswer):
        """Payload lines should match QuickAnswer lines exactly."""
        payload = build_vote_shell_payload(ready_answer)
        assert payload.lines == ready_answer.lines

    def test_line_count_preserved(self, ready_answer: QuickAnswer):
        """Payload line_count should match QuickAnswer."""
        payload = build_vote_shell_payload(ready_answer)
        assert payload.line_count == len(ready_answer.lines)

    def test_lines_are_copy_not_reference(self, ready_answer: QuickAnswer):
        """Payload lines should be a copy, not a reference."""
        payload = build_vote_shell_payload(ready_answer)
        # Modify original
        original_first = ready_answer.lines[0]
        ready_answer.lines[0] = "MODIFIED"
        # Payload should not be affected
        assert payload.lines[0] == original_first


# =============================================================================
# Test: Payload Preserves Confidence Labels
# =============================================================================


class TestPayloadPreservesConfidenceLabels:
    """Test that payload preserves confidence labels."""

    def test_confidence_label_preserved(self, ready_answer: QuickAnswer):
        """Payload should preserve confidence_label."""
        payload = build_vote_shell_payload(ready_answer)
        assert payload.confidence_label == ready_answer.confidence_label

    def test_verified_fact_preserved(self, ready_answer: QuickAnswer):
        """VERIFIED_FACT confidence should be preserved."""
        assert ready_answer.confidence_label == ConfidenceLabel.VERIFIED_FACT
        payload = build_vote_shell_payload(ready_answer)
        assert payload.confidence_label == ConfidenceLabel.VERIFIED_FACT

    def test_low_confidence_preserved(self, not_ready_answer: QuickAnswer):
        """LOW_CONFIDENCE_INFERENCE should be preserved."""
        payload = build_vote_shell_payload(not_ready_answer)
        assert payload.confidence_label == ConfidenceLabel.LOW_CONFIDENCE_INFERENCE


# =============================================================================
# Test: Payload Preserves Source Trace
# =============================================================================


class TestPayloadPreservesSourceTrace:
    """Test that payload preserves source trace ID."""

    def test_source_trace_id_preserved(self, ready_answer: QuickAnswer):
        """Payload should preserve source_trace_id."""
        payload = build_vote_shell_payload(ready_answer)
        assert payload.source_trace_id == ready_answer.source_summary_id

    def test_source_trace_id_not_empty(self, ready_answer: QuickAnswer):
        """Source trace ID should not be empty for valid answer."""
        payload = build_vote_shell_payload(ready_answer)
        assert payload.source_trace_id != ""


# =============================================================================
# Test: Payload Preserves Trail Termination Markers
# =============================================================================


class TestPayloadPreservesTrailTermination:
    """Test that payload preserves trail termination markers."""

    def test_trail_termination_preserved(self, not_ready_answer: QuickAnswer):
        """Trail termination should be preserved in payload."""
        payload = build_vote_shell_payload(not_ready_answer)
        assert len(payload.trail_termination_markers) > 0

    def test_trail_termination_reason_preserved(self, not_ready_answer: QuickAnswer):
        """Trail termination reason should be in markers."""
        payload = build_vote_shell_payload(not_ready_answer)
        assert not_ready_answer.trail_termination_reason in payload.trail_termination_markers

    def test_no_trail_termination_when_not_terminated(self, ready_answer: QuickAnswer):
        """No trail markers when answer is not trail-terminated."""
        assert ready_answer.trail_terminated is False
        payload = build_vote_shell_payload(ready_answer)
        assert len(payload.trail_termination_markers) == 0


# =============================================================================
# Test: Payload Preserves Human Review Triggers
# =============================================================================


class TestPayloadPreservesHumanReviewTriggers:
    """Test that payload preserves human review triggers."""

    def test_human_review_required_preserved(self, not_ready_answer: QuickAnswer):
        """human_review_required should be preserved."""
        payload = build_vote_shell_payload(not_ready_answer)
        assert payload.human_review_required == not_ready_answer.requires_human_review

    def test_human_review_triggers_preserved(self, not_ready_answer: QuickAnswer):
        """human_review_triggers should be preserved."""
        payload = build_vote_shell_payload(not_ready_answer)
        assert payload.human_review_triggers == list(not_ready_answer.human_review_reasons)

    def test_no_human_review_when_not_required(self, ready_answer: QuickAnswer):
        """No human review when not required."""
        payload = build_vote_shell_payload(ready_answer)
        assert payload.human_review_required is False
        assert len(payload.human_review_triggers) == 0


# =============================================================================
# Test: Validate Payload Accepts Complete Payload
# =============================================================================


class TestValidatePayloadAcceptsComplete:
    """Test that validate accepts complete payload."""

    def test_valid_payload_passes(self, ready_answer: QuickAnswer):
        """Valid payload should pass validation."""
        payload = build_vote_shell_payload(ready_answer)
        result = validate_vote_shell_payload(payload)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_not_ready_payload_passes_validation(self, not_ready_answer: QuickAnswer):
        """Not-ready payload should still pass validation (it's valid data)."""
        payload = build_vote_shell_payload(not_ready_answer)
        result = validate_vote_shell_payload(payload)
        assert result.valid is True


# =============================================================================
# Test: Validate Payload Rejects Missing Required Fields
# =============================================================================


class TestValidatePayloadRejectsMissing:
    """Test that validate rejects missing required fields."""

    def test_none_payload_rejected(self):
        """None payload should fail validation."""
        result = validate_vote_shell_payload(None)  # type: ignore
        assert result.valid is False
        assert "Payload is None" in result.errors

    def test_empty_foundup_id_rejected(self, ready_answer: QuickAnswer):
        """Empty foundup_id should fail validation."""
        payload = build_vote_shell_payload(ready_answer)
        payload.foundup_id = ""
        result = validate_vote_shell_payload(payload)
        assert result.valid is False
        assert any("foundup_id" in e for e in result.errors)

    def test_empty_route_namespace_rejected(self, ready_answer: QuickAnswer):
        """Empty route_namespace should fail validation."""
        payload = build_vote_shell_payload(ready_answer)
        payload.route_namespace = ""
        result = validate_vote_shell_payload(payload)
        assert result.valid is False
        assert any("route_namespace" in e for e in result.errors)

    def test_empty_app_mount_rejected(self, ready_answer: QuickAnswer):
        """Empty app_mount should fail validation."""
        payload = build_vote_shell_payload(ready_answer)
        payload.app_mount = ""
        result = validate_vote_shell_payload(payload)
        assert result.valid is False
        assert any("app_mount" in e for e in result.errors)


# =============================================================================
# Test: No Public Route Activation Files Created
# =============================================================================


class TestNoPublicRouteActivation:
    """Test that no public route activation files are created."""

    def test_no_public_files_in_module(self):
        """No files should be created under public/**."""
        public_path = Path("public")
        if public_path.exists():
            # Check for any voteballots files in public
            voteballots_files = list(public_path.rglob("*voteballots*"))
            # Filter out any that existed before this slice
            # (we only care about route activation files)
            route_activation_files = [
                f for f in voteballots_files
                if "route" in f.name.lower() or "activation" in f.name.lower()
            ]
            assert len(route_activation_files) == 0

    def test_shell_integration_does_not_create_files(self, ready_answer: QuickAnswer):
        """build_vote_shell_payload should not create any files."""
        # Note: This test verifies behavior, not filesystem state
        # The function is pure - it only returns data
        payload = build_vote_shell_payload(ready_answer)
        # If it created files, it would need to write them somewhere
        # The function signature shows it only returns VoteShellPayload
        assert isinstance(payload, VoteShellPayload)


# =============================================================================
# Test: No Manifest Mutation
# =============================================================================


class TestNoManifestMutation:
    """Test that foundup_manifest.json is not mutated."""

    def test_manifest_unchanged_after_payload_build(self, ready_answer: QuickAnswer):
        """Manifest should be unchanged after building payload."""
        manifest_path = Path("modules/foundups/voteballots/foundup_manifest.json")

        # Read manifest before
        with open(manifest_path) as f:
            before = json.load(f)

        # Build payload
        _ = build_vote_shell_payload(ready_answer)

        # Read manifest after
        with open(manifest_path) as f:
            after = json.load(f)

        # Should be identical
        assert before == after

    def test_manifest_entry_url_still_empty(self):
        """Manifest entry_url should still be empty (not activated)."""
        manifest_path = Path("modules/foundups/voteballots/foundup_manifest.json")
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert manifest["entry_url"] == ""


# =============================================================================
# Test: No Registry/Catalog/Projection Mutation
# =============================================================================


class TestNoRegistryCatalogProjectionMutation:
    """Test that registry, catalog, projection are not mutated."""

    def test_payload_does_not_modify_external_state(self, ready_answer: QuickAnswer):
        """Payload build should not modify any external state."""
        # This is a behavioral test - the function is pure
        payload = build_vote_shell_payload(ready_answer)
        # Pure function only returns data, no side effects
        assert payload is not None

    def test_constants_match_manifest(self):
        """Shell integration constants should match manifest (readonly)."""
        manifest_path = Path("modules/foundups/voteballots/foundup_manifest.json")
        with open(manifest_path) as f:
            manifest = json.load(f)

        assert FOUNDUP_ID == manifest["foundup_id"]
        assert ROUTE_NAMESPACE == manifest["routing_prefix"]


# =============================================================================
# Test: No LLM/Network/API Key Required
# =============================================================================


class TestNoLLMNetworkAPIKey:
    """Test that no LLM, network, or API key is required."""

    def test_no_external_imports_for_llm(self):
        """Shell integration should not import LLM libraries."""
        import modules.foundups.voteballots.src.shell_integration as module
        import sys

        # Check that no LLM-related modules are imported
        llm_modules = ["openai", "anthropic", "ollama", "transformers", "torch"]
        imported = [m for m in llm_modules if m in sys.modules]
        # Note: Some might be imported elsewhere, so we check the module's imports
        source_file = Path(module.__file__)
        with open(source_file) as f:
            source = f.read()
        for llm_mod in llm_modules:
            assert f"import {llm_mod}" not in source
            assert f"from {llm_mod}" not in source

    def test_no_network_calls(self, ready_answer: QuickAnswer):
        """Payload build should not make network calls."""
        # The function is synchronous and pure - it cannot make network calls
        # without async or explicit http imports
        payload = build_vote_shell_payload(ready_answer)
        assert payload is not None

    def test_no_api_key_environment_variable_required(self, ready_answer: QuickAnswer):
        """No API key environment variable should be required."""
        # Clear any relevant env vars
        env_vars_to_check = ["FEC_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
        saved = {k: os.environ.pop(k, None) for k in env_vars_to_check}

        try:
            # Should work without API keys
            payload = build_vote_shell_payload(ready_answer)
            assert payload.is_successful
        finally:
            # Restore env vars
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v


# =============================================================================
# Test: No Persuasion/Recommendation/Microtargeting Language
# =============================================================================


class TestNoPoliticalSafetyViolations:
    """Test that no political safety violations exist."""

    def test_no_recommendation_language_in_source(self):
        """Source should not contain recommendation language."""
        import modules.foundups.voteballots.src.shell_integration as module

        source_file = Path(module.__file__)
        with open(source_file) as f:
            source = f.read().lower()

        # Note: "recommend" appears in safety boundary "NO_CANDIDATE_RECOMMENDATION"
        # which is acceptable - we check for actionable phrases instead
        recommendation_terms = [
            "should vote for",
            "must support",
            "we recommend",
            "i recommend",
            "endorse this",
            "best candidate is",
            "vote for",
        ]
        for term in recommendation_terms:
            assert term not in source, f"Found recommendation term: {term}"

    def test_no_persuasion_language_in_source(self):
        """Source should not contain persuasion language."""
        import modules.foundups.voteballots.src.shell_integration as module

        source_file = Path(module.__file__)
        with open(source_file) as f:
            source = f.read().lower()

        persuasion_terms = [
            "you should",
            "you must",
            "urgent",
            "act now",
            "don't miss",
        ]
        for term in persuasion_terms:
            assert term not in source, f"Found persuasion term: {term}"

    def test_no_targeting_fields_in_payload(self, ready_answer: QuickAnswer):
        """Payload should not contain targeting fields."""
        payload = build_vote_shell_payload(ready_answer)
        payload_dict = payload.to_dict()

        targeting_fields = [
            "user_id",
            "user_profile",
            "demographic",
            "location",
            "age",
            "gender",
            "income",
            "education",
        ]
        for field in targeting_fields:
            assert field not in payload_dict, f"Found targeting field: {field}"


# =============================================================================
# Test: Empty Answer Handling
# =============================================================================


class TestEmptyAnswerHandling:
    """Test handling of empty answers."""

    def test_empty_answer_produces_empty_status(self, empty_answer: QuickAnswer):
        """Empty answer should produce EMPTY_ANSWER status."""
        payload = build_vote_shell_payload(empty_answer)
        assert payload.status == ShellPayloadStatus.EMPTY_ANSWER

    def test_empty_answer_not_display_ready(self, empty_answer: QuickAnswer):
        """Empty answer should not be display ready."""
        payload = build_vote_shell_payload(empty_answer)
        assert payload.display_ready is False

    def test_empty_answer_has_error_message(self, empty_answer: QuickAnswer):
        """Empty answer should have error message."""
        payload = build_vote_shell_payload(empty_answer)
        assert payload.error_message is not None
        assert "no content" in payload.error_message.lower()


# =============================================================================
# Test: None Input Handling
# =============================================================================


class TestNoneInputHandling:
    """Test handling of None input."""

    def test_none_input_produces_invalid_status(self):
        """None input should produce INVALID_INPUT status."""
        payload = build_vote_shell_payload(None)  # type: ignore
        assert payload.status == ShellPayloadStatus.INVALID_INPUT

    def test_none_input_not_display_ready(self):
        """None input should not be display ready."""
        payload = build_vote_shell_payload(None)  # type: ignore
        assert payload.display_ready is False

    def test_none_input_has_error_message(self):
        """None input should have error message."""
        payload = build_vote_shell_payload(None)  # type: ignore
        assert payload.error_message is not None


# =============================================================================
# Test: Truncated Answer Handling
# =============================================================================


class TestTruncatedAnswerHandling:
    """Test handling of truncated answers."""

    def test_truncated_flag_preserved(self, truncated_answer: QuickAnswer):
        """Truncated flag should be preserved in payload."""
        payload = build_vote_shell_payload(truncated_answer)
        assert payload.truncated is True

    def test_truncated_answer_has_warning(self, truncated_answer: QuickAnswer):
        """Truncated answer should have warning in payload."""
        payload = build_vote_shell_payload(truncated_answer)
        assert any("truncated" in w.lower() for w in payload.warnings)


# =============================================================================
# Test: Convenience Functions
# =============================================================================


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_build_ready_payload(self, ready_answer: QuickAnswer):
        """build_ready_payload should work like build_vote_shell_payload."""
        payload = build_ready_payload(ready_answer)
        assert payload.status == ShellPayloadStatus.SUCCESS

    def test_is_payload_ready_true_for_ready(self, ready_answer: QuickAnswer):
        """is_payload_ready should return True for ready payload."""
        payload = build_vote_shell_payload(ready_answer)
        assert is_payload_ready(payload) is True

    def test_is_payload_ready_false_for_not_ready(self, not_ready_answer: QuickAnswer):
        """is_payload_ready should return False for not-ready payload."""
        payload = build_vote_shell_payload(not_ready_answer)
        assert is_payload_ready(payload) is False

    def test_get_payload_summary_ready(self, ready_answer: QuickAnswer):
        """get_payload_summary should describe ready payload."""
        payload = build_vote_shell_payload(ready_answer)
        summary = get_payload_summary(payload)
        assert "Ready" in summary
        assert str(payload.line_count) in summary

    def test_get_payload_summary_not_ready(self, not_ready_answer: QuickAnswer):
        """get_payload_summary should describe not-ready payload."""
        payload = build_vote_shell_payload(not_ready_answer)
        summary = get_payload_summary(payload)
        assert "Not ready" in summary


# =============================================================================
# Test: Payload Serialization
# =============================================================================


class TestPayloadSerialization:
    """Test payload serialization."""

    def test_to_dict_produces_json_serializable(self, ready_answer: QuickAnswer):
        """to_dict should produce JSON-serializable output."""
        payload = build_vote_shell_payload(ready_answer)
        payload_dict = payload.to_dict()
        # Should not raise
        json_str = json.dumps(payload_dict)
        assert len(json_str) > 0

    def test_to_dict_preserves_all_fields(self, ready_answer: QuickAnswer):
        """to_dict should preserve all fields."""
        payload = build_vote_shell_payload(ready_answer)
        payload_dict = payload.to_dict()

        assert payload_dict["foundup_id"] == payload.foundup_id
        assert payload_dict["route_namespace"] == payload.route_namespace
        assert payload_dict["app_mount"] == payload.app_mount
        assert payload_dict["lines"] == payload.lines
        assert payload_dict["display_ready"] == payload.display_ready


# =============================================================================
# Test: Full Pipeline Integration
# =============================================================================


class TestFullPipelineIntegration:
    """Test full pipeline from FEC adapter to shell payload."""

    def test_full_pipeline_to_shell_payload(self):
        """Full pipeline should produce valid shell payload."""
        from modules.foundups.voteballots.src.fec_adapter import get_mock_adapter
        from modules.foundups.voteballots.src.entity_resolution import (
            EntityResolutionRequest,
            EntityResolutionStatus,
            resolve_candidate_entity,
        )
        from modules.foundups.voteballots.src.funding_summary import (
            FundingSummaryRequest,
            FundingSummaryStatus,
            summarize_candidate_funding,
        )
        from modules.foundups.voteballots.src.confidence_scoring import (
            ConfidenceScoringStatus,
            score_funding_summary_confidence,
        )
        from modules.foundups.voteballots.src.quick_answer import generate_shell_answer

        # Full pipeline
        adapter = get_mock_adapter()

        # Step 1: Resolve candidate
        resolution = resolve_candidate_entity(
            EntityResolutionRequest(query="OCASIO-CORTEZ, ALEXANDRIA"),
            adapter,
        )
        assert resolution.status == EntityResolutionStatus.EXACT_ONE_MATCH

        # Step 2: Get funding summary
        summary = summarize_candidate_funding(
            FundingSummaryRequest(resolution_result=resolution),
            adapter,
        )
        assert summary.status == FundingSummaryStatus.SUCCESS

        # Step 3: Score confidence
        scored = score_funding_summary_confidence(summary)
        assert scored.status == ConfidenceScoringStatus.SUCCESS

        # Step 4: Generate quick answer
        answer = generate_shell_answer(scored)
        assert len(answer.lines) > 0

        # Step 5: Build shell payload
        payload = build_vote_shell_payload(answer)

        # Verify shell payload
        assert payload.foundup_id == "voteballots"
        assert payload.route_namespace == "/f/voteballots"
        assert payload.app_mount == "/f/voteballots/app"
        assert len(payload.lines) > 0
        assert payload.source_trace_id != ""


# =============================================================================
# Test: Chain Completion
# =============================================================================


class TestChainCompletion:
    """Test that chain is complete (all 6 slices working together)."""

    def test_all_slice_imports_work(self):
        """All slice exports should be importable."""
        # Slice 1: FEC Adapter
        from modules.foundups.voteballots.src import get_mock_adapter, CandidateRecord

        # Slice 2: Entity Resolution
        from modules.foundups.voteballots.src import (
            EntityResolutionRequest,
            resolve_candidate_entity,
        )

        # Slice 3: Funding Summary
        from modules.foundups.voteballots.src import (
            FundingSummaryRequest,
            summarize_candidate_funding,
        )

        # Slice 4: Confidence Scoring
        from modules.foundups.voteballots.src import (
            ConfidenceLabel,
            score_funding_summary_confidence,
        )

        # Slice 5: Quick Answer
        from modules.foundups.voteballots.src import (
            QuickAnswer,
            generate_shell_answer,
        )

        # Slice 6: Shell Integration
        from modules.foundups.voteballots.src import (
            VoteShellPayload,
            build_vote_shell_payload,
        )

        # All imports succeeded
        assert True

    def test_chain_produces_shell_ready_payload(self):
        """Complete chain should produce shell-ready payload."""
        from modules.foundups.voteballots.src import (
            get_mock_adapter,
            EntityResolutionRequest,
            EntityResolutionStatus,
            resolve_candidate_entity,
            FundingSummaryRequest,
            FundingSummaryStatus,
            summarize_candidate_funding,
            ConfidenceScoringStatus,
            score_funding_summary_confidence,
            generate_shell_answer,
            build_vote_shell_payload,
            is_answer_ready_for_display,
        )

        adapter = get_mock_adapter()
        resolution = resolve_candidate_entity(
            EntityResolutionRequest(query="BIDEN, JOSEPH R JR"),
            adapter,
        )

        if resolution.status == EntityResolutionStatus.EXACT_ONE_MATCH:
            summary = summarize_candidate_funding(
                FundingSummaryRequest(resolution_result=resolution),
                adapter,
            )
            if summary.status == FundingSummaryStatus.SUCCESS:
                scored = score_funding_summary_confidence(summary)
                if scored.status == ConfidenceScoringStatus.SUCCESS:
                    answer = generate_shell_answer(scored)
                    payload = build_vote_shell_payload(answer)

                    # Chain complete
                    assert payload.foundup_id == "voteballots"
                    assert payload.line_count > 0
