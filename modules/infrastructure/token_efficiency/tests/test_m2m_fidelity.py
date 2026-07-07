# -*- coding: utf-8 -*-
"""
M2M Fidelity Gate Tests (WSP 99 + Contract Section 7a + ADDENDUM_HOLOINDEX_M2M_INVARIANT)

Tests compile->parse->decompile roundtrip preserves semantic content.

WSP_97 Truth Labels:
- Tests per Contract Section 7a (M2M fidelity tests)
- Tests per ADDENDUM_HOLOINDEX_M2M_INVARIANT (CTX.HOLO tests)
"""

import pytest
import sys
from pathlib import Path

# Add module to path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from m2m_fidelity_gate import (
    M2MFidelityGate,
    FidelityError,
    CTXHolo,
    HoloStatus,
    HoloMode,
    HoloInvariants,
    IndexGapEvent,
    RawRef,
    assert_m2m_fidelity,
    to_m2m_compact,
    to_m2m_yaml,
    HOLO_REQUIRED_MODES,
)


class TestM2MFidelityBasics:
    """Contract Section 7a: Basic fidelity tests."""

    def test_action_preserved(self):
        """Action verb must survive roundtrip."""
        gate = M2MFidelityGate()
        result = gate.assert_fidelity(
            original_prose="ANALYZE the auth module",
            lane="A",
            wsp_refs=[50, 71],
            mode="plan",  # Use plan mode to avoid CTX.HOLO requirement
        )
        assert result.passed
        assert result.original_action == "ANALYZE"

    def test_scope_preserved(self):
        """Scope must survive roundtrip if present."""
        gate = M2MFidelityGate()
        result = gate.assert_fidelity(
            original_prose="Fix auth.py security issues",
            lane="B",
            wsp_refs=[50],
            mode="plan",
        )
        assert result.passed
        assert "auth.py" in result.original_scope or result.roundtrip_scope

    def test_wsp_refs_preserved(self):
        """WSP refs must match exactly."""
        gate = M2MFidelityGate()
        result = gate.assert_fidelity(
            original_prose="Implement feature",
            lane="A",
            wsp_refs=[50, 22, 97],
            mode="plan",
        )
        assert result.passed
        assert result.wsp_refs_match

    def test_lane_preserved(self):
        """Lane must survive roundtrip."""
        gate = M2MFidelityGate()
        for lane in ["A", "B", "QA", "SENTINEL"]:
            result = gate.assert_fidelity(
                original_prose="Test task",
                lane=lane,
                wsp_refs=[50],
                mode="plan",
            )
            assert result.passed

    def test_mode_preserved(self):
        """Mode must survive roundtrip."""
        gate = M2MFidelityGate()
        # Use plan mode to test mode preservation without CTX.HOLO
        result = gate.assert_fidelity(
            original_prose="Plan feature",
            lane="A",
            wsp_refs=[50],
            mode="plan",
        )
        assert result.passed

    def test_empty_handling(self):
        """Empty input raises FidelityError."""
        gate = M2MFidelityGate()
        with pytest.raises(FidelityError) as exc_info:
            gate.assert_fidelity(
                original_prose="",
                lane="A",
                wsp_refs=[50],
            )
        assert "Empty input" in str(exc_info.value)

    def test_empty_whitespace_handling(self):
        """Whitespace-only input raises FidelityError."""
        gate = M2MFidelityGate()
        with pytest.raises(FidelityError):
            gate.assert_fidelity(
                original_prose="   \n\t  ",
                lane="A",
                wsp_refs=[50],
            )

    def test_unicode_handling(self):
        """Unicode prose roundtrips without corruption."""
        gate = M2MFidelityGate()
        unicode_prose = "Analyze 日本語 module with émojis 🔒"
        result = gate.assert_fidelity(
            original_prose=unicode_prose,
            lane="A",
            wsp_refs=[50],
            mode="plan",
        )
        assert result.passed

    def test_fail_conditions_preserved(self):
        """Fail conditions must be preserved."""
        gate = M2MFidelityGate()
        fail_conditions = ["test_fail", "lint_error"]
        result = gate.assert_fidelity(
            original_prose="Implement feature",
            lane="A",
            wsp_refs=[50],
            mode="plan",
            fail_conditions=fail_conditions,
        )
        assert result.passed
        assert result.fail_conditions_match


class TestCTXHoloPreservation:
    """ADDENDUM_HOLOINDEX_M2M_INVARIANT: CTX.HOLO preservation tests."""

    def _make_ctx_holo(self, **overrides) -> CTXHolo:
        """Helper to create CTXHolo with defaults."""
        defaults = {
            "query": "test query",
            "mode": HoloMode.BUNDLE_JSON,
            "status": HoloStatus.OK,
            "code_hits": 5,
            "wsp_hits": 2,
            "skill_hits": 1,
        }
        defaults.update(overrides)
        return CTXHolo(**defaults)

    def test_compile_parse_decompile_preserves_ctx_holo(self):
        """CTX.HOLO must survive compile->parse->decompile."""
        gate = M2MFidelityGate()
        ctx = self._make_ctx_holo()
        result = gate.assert_fidelity(
            original_prose="Implement auth fix",
            lane="A",
            wsp_refs=[50],
            mode="exec",
            ctx_holo=ctx,
        )
        assert result.passed
        assert result.ctx_holo_preserved

    def test_missing_ctx_holo_fails_for_exec(self):
        """Missing CTX.HOLO fails for exec mode."""
        gate = M2MFidelityGate()
        result = gate.assert_fidelity(
            original_prose="Execute task",
            lane="A",
            wsp_refs=[50],
            mode="exec",
            ctx_holo=None,  # Missing!
        )
        assert not result.passed
        assert result.ctx_holo_preserved is False
        assert any("CTX.HOLO required" in e for e in result.errors)

    def test_missing_ctx_holo_fails_for_qa(self):
        """Missing CTX.HOLO fails for qa mode."""
        gate = M2MFidelityGate()
        result = gate.assert_fidelity(
            original_prose="QA review",
            lane="QA",
            wsp_refs=[50],
            mode="qa",
            ctx_holo=None,
        )
        assert not result.passed

    def test_missing_ctx_holo_fails_for_review(self):
        """Missing CTX.HOLO fails for review mode."""
        gate = M2MFidelityGate()
        result = gate.assert_fidelity(
            original_prose="Review code",
            lane="A",
            wsp_refs=[50],
            mode="review",
            ctx_holo=None,
        )
        assert not result.passed

    def test_holo_not_applicable_requires_reason(self):
        """status=not_applicable requires not_applicable_reason."""
        gate = M2MFidelityGate()
        ctx = self._make_ctx_holo(
            status=HoloStatus.NOT_APPLICABLE,
            not_applicable_reason=None,  # Missing!
        )
        result = gate.assert_fidelity(
            original_prose="Execute",
            lane="A",
            wsp_refs=[50],
            mode="exec",
            ctx_holo=ctx,
        )
        assert not result.passed
        assert any("not_applicable_reason required" in e for e in result.errors)

    def test_holo_not_applicable_with_reason_passes(self):
        """status=not_applicable passes with reason."""
        gate = M2MFidelityGate()
        ctx = self._make_ctx_holo(
            status=HoloStatus.NOT_APPLICABLE,
            not_applicable_reason="No code search needed for this task",
        )
        result = gate.assert_fidelity(
            original_prose="Execute",
            lane="A",
            wsp_refs=[50],
            mode="exec",
            ctx_holo=ctx,
        )
        assert result.passed

    def test_index_gap_event_survives_roundtrip(self):
        """index_gap_event must survive CTX.HOLO roundtrip."""
        gap_event = IndexGapEvent(
            gap_id="gap_001",
            query="find bypass_classifier",
            missing_target="modules/infrastructure/token_efficiency/",
            expected_surface="code",
            observed_hits=["wsp_hits: 0", "code_hits: 0"],
            recommended_owner="WRE_CI_INDEX_MAINTENANCE",
            live_enqueue_performed=False,
        )
        ctx = self._make_ctx_holo(
            status=HoloStatus.INDEX_GAP,
            index_gap_detected=True,
            index_gap_event=gap_event,
        )

        # Roundtrip through serialization
        serialized = ctx.to_dict()
        restored = CTXHolo.from_dict(serialized)

        assert restored.index_gap_detected == ctx.index_gap_detected
        assert restored.index_gap_event is not None
        assert restored.index_gap_event.gap_id == gap_event.gap_id
        assert restored.index_gap_event.missing_target == gap_event.missing_target
        assert restored.index_gap_event.expected_surface == gap_event.expected_surface

    def test_index_gap_detected_without_event_fails(self):
        """index_gap_detected=true without event fails."""
        gate = M2MFidelityGate()
        ctx = self._make_ctx_holo(
            index_gap_detected=True,
            index_gap_event=None,  # Missing!
        )
        result = gate.assert_fidelity(
            original_prose="Execute",
            lane="A",
            wsp_refs=[50],
            mode="exec",
            ctx_holo=ctx,
        )
        assert not result.passed
        assert any("index_gap_detected=true but no index_gap_event" in e for e in result.errors)

    def test_runtime_reindex_allowed_remains_false(self):
        """runtime_reindex_allowed invariant must remain False."""
        gate = M2MFidelityGate()
        ctx = self._make_ctx_holo()
        invariants = HoloInvariants(
            runtime_reindex_allowed=True,  # VIOLATION!
        )
        result = gate.assert_fidelity(
            original_prose="Execute",
            lane="A",
            wsp_refs=[50],
            mode="exec",
            ctx_holo=ctx,
            invariants=invariants,
        )
        assert not result.passed
        assert any("runtime_reindex_allowed must be False" in e for e in result.errors)

    def test_explicit_paths_require_direct_read_invariant(self):
        """direct_read_required_if_explicit_paths invariant preserved."""
        invariants = HoloInvariants(
            direct_read_required_if_explicit_paths=True,
        )
        serialized = invariants.to_dict()
        restored = HoloInvariants.from_dict(serialized)
        assert restored.direct_read_required_if_explicit_paths is True

    def test_decompile_exposes_holoindex_status_for_012_review(self):
        """CTX.HOLO status visible in decompiled output."""
        ctx = self._make_ctx_holo(
            status=HoloStatus.OK,
            code_hits=10,
            wsp_hits=5,
        )
        serialized = ctx.to_dict()
        assert serialized["status"] == "ok"
        assert serialized["code_hits"] == 10
        assert serialized["wsp_hits"] == 5


class TestCTXHoloFailConditions:
    """ADDENDUM_HOLOINDEX_M2M_INVARIANT: Fail condition tests."""

    def test_index_gap_event_invalid_surface_fails(self):
        """Invalid expected_surface in index_gap_event fails."""
        gate = M2MFidelityGate()
        gap_event = IndexGapEvent(
            gap_id="gap_001",
            query="test",
            missing_target="test_path",
            expected_surface="invalid_surface",  # VIOLATION
            observed_hits=[],
        )
        ctx = CTXHolo(
            query="test",
            mode=HoloMode.BUNDLE_JSON,
            status=HoloStatus.INDEX_GAP,
            index_gap_detected=True,
            index_gap_event=gap_event,
        )
        result = gate.assert_fidelity(
            original_prose="Execute",
            lane="A",
            wsp_refs=[50],
            mode="exec",
            ctx_holo=ctx,
        )
        assert not result.passed
        assert any("invalid expected_surface" in e for e in result.errors)

    def test_index_gap_event_missing_required_fields_fails(self):
        """Missing required fields in index_gap_event fails."""
        gate = M2MFidelityGate()
        gap_event = IndexGapEvent(
            gap_id="",  # MISSING
            query="",  # MISSING
            missing_target="",  # MISSING
            expected_surface="code",
            observed_hits=[],
        )
        ctx = CTXHolo(
            query="test",
            mode=HoloMode.BUNDLE_JSON,
            status=HoloStatus.INDEX_GAP,
            index_gap_detected=True,
            index_gap_event=gap_event,
        )
        result = gate.assert_fidelity(
            original_prose="Execute",
            lane="A",
            wsp_refs=[50],
            mode="exec",
            ctx_holo=ctx,
        )
        assert not result.passed
        assert any("missing required fields" in e for e in result.errors)


class TestRoleBoundary:
    """Fail condition: roundtrip that promotes worker to architect role."""

    def test_worker_to_architect_promotion_fails(self):
        """Worker cannot be promoted to architect through roundtrip."""
        gate = M2MFidelityGate()
        with pytest.raises(FidelityError) as exc_info:
            gate.validate_role_boundary(
                sender_role="worker",
                receiver_role="architect",
            )
        assert "Worker cannot be promoted to architect" in str(exc_info.value)

    def test_worker_to_qa_allowed(self):
        """Worker to QA role change allowed."""
        gate = M2MFidelityGate()
        result = gate.validate_role_boundary(
            sender_role="worker",
            receiver_role="qa",
        )
        assert result is True

    def test_architect_to_worker_allowed(self):
        """Architect to worker (demotion) allowed."""
        gate = M2MFidelityGate()
        result = gate.validate_role_boundary(
            sender_role="architect",
            receiver_role="worker",
        )
        assert result is True


class TestRawRef:
    """Contract Section 5c: RawRef schema tests."""

    def test_rawref_create(self):
        """RawRef creation works."""
        content = "Original prose content"
        ref = RawRef.create(
            content=content,
            content_type="m2m_prose",
        )
        assert ref.ref_id.startswith("m2m_prose_")
        assert ref.content_type == "m2m_prose"
        assert ref.recovered is False

    def test_rawref_verify_content(self):
        """RawRef verifies content hash."""
        content = "Test content"
        ref = RawRef.create(content=content, content_type="m2m_prose")
        assert ref.verify_content(content) is True
        assert ref.verify_content("Different content") is False

    def test_rawref_ttl(self):
        """RawRef TTL calculation correct."""
        ref = RawRef.create(
            content="test",
            content_type="m2m_prose",
            ttl_seconds=3600,
        )
        assert ref.expires_at == ref.created_at + 3600


class TestAssertFidelityFunction:
    """Test standalone assert_m2m_fidelity function."""

    def test_assert_fidelity_passes(self):
        """assert_m2m_fidelity returns True on success."""
        ctx = CTXHolo(
            query="test",
            mode=HoloMode.BUNDLE_JSON,
            status=HoloStatus.OK,
        )
        result = assert_m2m_fidelity(
            original_prose="Implement feature",
            lane="A",
            wsp_refs=[50],
            mode="exec",
            ctx_holo=ctx,
        )
        assert result is True

    def test_assert_fidelity_raises_on_failure(self):
        """assert_m2m_fidelity raises FidelityError on failure."""
        with pytest.raises(FidelityError):
            assert_m2m_fidelity(
                original_prose="Execute task",
                lane="A",
                wsp_refs=[50],
                mode="exec",
                ctx_holo=None,  # Missing for exec mode
            )


class TestM2MOutput:
    """Test M2M output methods."""

    def test_to_m2m_compact(self):
        """to_m2m_compact produces valid format."""
        gate = M2MFidelityGate()
        ctx = CTXHolo(
            query="test",
            mode=HoloMode.BUNDLE_JSON,
            status=HoloStatus.OK,
        )
        result = gate.assert_fidelity(
            original_prose="Test",
            lane="A",
            wsp_refs=[50],
            mode="exec",
            ctx_holo=ctx,
        )
        compact = to_m2m_compact(result)
        assert "FIDELITY:OK" in compact
        assert "WSP_MATCH:True" in compact

    def test_to_m2m_yaml(self):
        """to_m2m_yaml produces valid YAML format."""
        gate = M2MFidelityGate()
        ctx = CTXHolo(
            query="test",
            mode=HoloMode.BUNDLE_JSON,
            status=HoloStatus.OK,
        )
        result = gate.assert_fidelity(
            original_prose="Test",
            lane="A",
            wsp_refs=[50],
            mode="exec",
            ctx_holo=ctx,
        )
        yaml_out = to_m2m_yaml(result)
        assert "FIDELITY_RESULT:" in yaml_out
        assert "STATUS: OK" in yaml_out


class TestHoloRequiredModes:
    """Test which modes require CTX.HOLO."""

    def test_holo_required_modes_constant(self):
        """HOLO_REQUIRED_MODES contains expected values."""
        assert "exec" in HOLO_REQUIRED_MODES
        assert "qa" in HOLO_REQUIRED_MODES
        assert "audit" in HOLO_REQUIRED_MODES
        assert "review" in HOLO_REQUIRED_MODES
        assert "verify" in HOLO_REQUIRED_MODES
        assert "implement" in HOLO_REQUIRED_MODES

    def test_plan_mode_no_holo_required(self):
        """plan mode does NOT require CTX.HOLO."""
        gate = M2MFidelityGate()
        result = gate.assert_fidelity(
            original_prose="Plan feature",
            lane="A",
            wsp_refs=[50],
            mode="plan",
            ctx_holo=None,  # OK for plan mode
        )
        assert result.passed
        assert result.ctx_holo_preserved is None  # Not applicable


class TestInvariantsSerialization:
    """Test HoloInvariants roundtrip."""

    def test_invariants_roundtrip(self):
        """HoloInvariants survives to_dict/from_dict."""
        original = HoloInvariants(
            holoindex_required=True,
            direct_read_required_if_explicit_paths=True,
            runtime_reindex_allowed=False,
            index_gap_must_route=True,
        )
        serialized = original.to_dict()
        restored = HoloInvariants.from_dict(serialized)

        assert restored.holoindex_required == original.holoindex_required
        assert restored.direct_read_required_if_explicit_paths == original.direct_read_required_if_explicit_paths
        assert restored.runtime_reindex_allowed == original.runtime_reindex_allowed
        assert restored.index_gap_must_route == original.index_gap_must_route

    def test_invariants_defaults(self):
        """HoloInvariants defaults correct."""
        inv = HoloInvariants()
        assert inv.holoindex_required is True
        assert inv.runtime_reindex_allowed is False
