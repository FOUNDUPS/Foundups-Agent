# -*- coding: utf-8 -*-
"""
M2M Compiler Backward Compatibility Tests

Per FAIL condition: compiler changes must be covered by backward-compat tests.
This test file verifies that adding new modes (audit, review, verify, implement)
does not break existing functionality.

WSP_97 Truth Labels:
- OBSERVED: m2m_compiler.py Mode enum originally had [exec, plan, qa]
- SPECIFIED_NOT_IMPLEMENTED: added [audit, review, verify, implement] for CTX.HOLO
"""

import pytest
import sys
from pathlib import Path

# Add prompt/swarm to path for import
sys.path.insert(0, str(Path(__file__).parents[4] / "prompt" / "swarm"))

from m2m_compiler import M2MCompiler, M2MPrompt, Mode, Lane, compile_m2m, decompile_m2m


class TestModeEnumBackwardCompat:
    """Verify original modes still work after adding new ones."""

    def test_exec_mode_still_valid(self):
        """exec mode unchanged."""
        assert Mode.EXEC.value == "exec"
        assert Mode("exec") == Mode.EXEC

    def test_plan_mode_still_valid(self):
        """plan mode unchanged."""
        assert Mode.PLAN.value == "plan"
        assert Mode("plan") == Mode.PLAN

    def test_qa_mode_still_valid(self):
        """qa mode unchanged."""
        assert Mode.QA.value == "qa"
        assert Mode("qa") == Mode.QA

    def test_new_modes_exist(self):
        """New modes added for CTX.HOLO preservation."""
        assert Mode.AUDIT.value == "audit"
        assert Mode.REVIEW.value == "review"
        assert Mode.VERIFY.value == "verify"
        assert Mode.IMPLEMENT.value == "implement"


class TestCompilerBackwardCompat:
    """Verify compiler behavior unchanged for original modes."""

    def test_compile_exec_unchanged(self):
        """compile() with mode=exec works as before."""
        compiler = M2MCompiler()
        m2m = compiler.compile(
            prose="Test task",
            lane="A",
            mode="exec",
            wsp_refs=[50],
        )
        assert m2m.mode == Mode.EXEC
        assert m2m.lane == Lane.A

    def test_compile_plan_unchanged(self):
        """compile() with mode=plan works as before."""
        compiler = M2MCompiler()
        m2m = compiler.compile(
            prose="Plan task",
            lane="B",
            mode="plan",
            wsp_refs=[50],
        )
        assert m2m.mode == Mode.PLAN

    def test_compile_qa_unchanged(self):
        """compile() with mode=qa works as before."""
        compiler = M2MCompiler()
        m2m = compiler.compile(
            prose="QA review",
            lane="QA",
            mode="qa",
            wsp_refs=[50],
        )
        assert m2m.mode == Mode.QA

    def test_compile_new_modes_work(self):
        """compile() works with new modes."""
        compiler = M2MCompiler()
        for mode in ["audit", "review", "verify", "implement"]:
            m2m = compiler.compile(
                prose=f"Test {mode}",
                lane="A",
                mode=mode,
                wsp_refs=[50],
            )
            assert m2m.mode.value == mode


class TestCompactFormatBackwardCompat:
    """Verify compact format unchanged."""

    def test_to_compact_exec(self):
        """to_compact() with exec mode produces expected format."""
        compiler = M2MCompiler()
        m2m = compiler.compile(
            prose="Test",
            lane="A",
            mode="exec",
            wsp_refs=[50],
        )
        compact = m2m.to_compact()
        assert "L:A" in compact
        assert "M:exec" in compact
        assert "R:[50]" in compact

    def test_parse_compact_exec_unchanged(self):
        """parse_compact() with M:exec works as before."""
        compiler = M2MCompiler()
        compact = "L:A S:test M:exec T:test123 R:[50]"
        m2m = compiler.parse_compact(compact)
        assert m2m.mode == Mode.EXEC
        assert m2m.lane == Lane.A

    def test_parse_compact_plan_unchanged(self):
        """parse_compact() with M:plan works as before."""
        compiler = M2MCompiler()
        compact = "L:B S:test M:plan T:test123 R:[50]"
        m2m = compiler.parse_compact(compact)
        assert m2m.mode == Mode.PLAN


class TestDecompileBackwardCompat:
    """Verify decompile unchanged."""

    def test_decompile_exec(self):
        """decompile() for exec mode produces expected prose."""
        compiler = M2MCompiler()
        m2m = M2MPrompt(
            lane=Lane.A,
            scope="test/",
            mode=Mode.EXEC,
            task_hash="abc123",
            wsp_refs=[50],
        )
        prose = compiler.decompile(m2m)
        assert "Execute task" in prose
        assert "abc123" in prose

    def test_decompile_plan(self):
        """decompile() for plan mode produces expected prose."""
        compiler = M2MCompiler()
        m2m = M2MPrompt(
            lane=Lane.B,
            scope="test/",
            mode=Mode.PLAN,
            task_hash="abc123",
            wsp_refs=[50],
        )
        prose = compiler.decompile(m2m)
        assert "Plan implementation" in prose


class TestQwenCallableBackwardCompat:
    """Verify Qwen-callable functions unchanged."""

    def test_compile_m2m_function(self):
        """compile_m2m() function works as before."""
        compact = compile_m2m(
            prose="Test task",
            lane="A",
            wsp_refs=[50],
        )
        assert "L:A" in compact
        assert "R:[50]" in compact

    def test_decompile_m2m_function(self):
        """decompile_m2m() function works as before."""
        compact = "L:A S:test M:exec T:test123 R:[50]"
        prose = decompile_m2m(compact)
        assert "Execute" in prose
        assert "test123" in prose
