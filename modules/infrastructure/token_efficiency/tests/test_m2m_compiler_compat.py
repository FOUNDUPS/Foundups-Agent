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

import copy
import json
import math

import pytest
import sys
from pathlib import Path

# Add prompt/swarm to path for import
sys.path.insert(0, str(Path(__file__).parents[4] / "prompt" / "swarm"))

from m2m_compiler import M2MCompiler, M2MPrompt, Mode, Lane, compile_m2m, decompile_m2m
import m2m_compiler as m2m_module


@pytest.fixture
def canonical_envelope():
    """An already-normalized order; serialization cannot confer admission."""
    return {
        "schema": "0102_m2m_v1", "ROLE": "worker", "ORIGIN": "internal_handoff",
        "PRINCIPAL_REF": "012", "L": "A", "S": "modules/foundups/detect_ai",
        "M": "plan", "T": "AMI-A01-stable", "A": "Validate the declared package",
        "R": [0, 15, 97, 99, 109],
        "I": {"allowed_paths": ["modules/foundups/detect_ai"], "dependencies": [],
              "wsp15": {"complexity": 4, "importance": 5, "deferability": 5,
                        "impact": 4, "total": 18, "priority": "P0"},
              "invariants": ["hold, do not deploy", "{identity}: preserved"],
              "values": [True, False, None, 1, 1.0, -0.0, "", "  text  ",
                         "\u65e5\u672c\U0001f916", "two\nlines\t\"quoted\""],
              " key:with,delimiters{} ": {"": "\u2028\u2029\u0085"}},
        "O": ["test evidence", "receipt"], "F": ["scope violation", "missing evidence"],
    }


def test_canonical_envelope_roundtrip_preserves_identity_and_typed_tree(canonical_envelope):
    original = copy.deepcopy(canonical_envelope)
    wire = m2m_module.encode_m2m_envelope(canonical_envelope)
    restored = m2m_module.decode_m2m_envelope(wire)
    assert restored == original == canonical_envelope
    assert wire == m2m_module.encode_m2m_envelope(dict(reversed(list(original.items()))))
    assert wire == json.dumps(original, sort_keys=True, ensure_ascii=False,
                              separators=(",", ":"), allow_nan=False)
    assert [type(v) for v in restored["I"]["values"]] == [
        type(v) for v in original["I"]["values"]]
    assert math.copysign(1, restored["I"]["values"][5]) == -1
    restored["I"]["dependencies"].append("changed")
    assert canonical_envelope == original


@pytest.mark.parametrize("role", ["architect", "worker", "verifier", "coordinator", "validator"])
@pytest.mark.parametrize("origin", ["external_principal", "internal_handoff", "autonomous_trigger"])
def test_canonical_roles_origins_preserved_without_principal_default(canonical_envelope, role, origin):
    canonical_envelope.update(ROLE=role, ORIGIN=origin)
    del canonical_envelope["PRINCIPAL_REF"]
    assert m2m_module.decode_m2m_envelope(
        m2m_module.encode_m2m_envelope(canonical_envelope)) == canonical_envelope


@pytest.mark.parametrize("field", [
    "schema", "ROLE", "ORIGIN", "L", "S", "M", "T", "A", "R", "I", "O", "F",
])
@pytest.mark.parametrize("entry", ["encode", "decode"])
def test_canonical_missing_fields_fail_closed(canonical_envelope, field, entry):
    del canonical_envelope[field]
    with pytest.raises(ValueError, match="^invalid canonical M2M envelope$"):
        if entry == "encode":
            m2m_module.encode_m2m_envelope(canonical_envelope)
        else:
            m2m_module.decode_m2m_envelope(json.dumps(canonical_envelope))


@pytest.mark.parametrize("field,value", [
    ("schema", "legacy"), ("ROLE", "Worker"), ("ORIGIN", "012"), ("M", "audit"),
    ("L", "D"), ("S", "  "), ("T", None), ("T", ""), ("A", "\n"),
    ("PRINCIPAL_REF", 12), ("PRINCIPAL_REF", ""), ("R", [True]), ("R", [-1]),
    ("R", [15.0]), ("R", ["97"]), ("I", []), ("O", [1]), ("F", "stop"),
    ("authority", "admitted"),
])
@pytest.mark.parametrize("entry", ["encode", "decode"])
def test_canonical_invalid_fields_reject_without_value_leak(canonical_envelope, field, value, entry):
    canonical_envelope[field] = value
    with pytest.raises(ValueError, match="^invalid canonical M2M envelope$"):
        if entry == "encode":
            m2m_module.encode_m2m_envelope(canonical_envelope)
        else:
            m2m_module.decode_m2m_envelope(json.dumps(canonical_envelope))


@pytest.mark.parametrize("value", [
    ("tuple",), {"set"}, b"bytes", {1: "key"}, float("nan"), float("inf"),
    float("-inf"), "\ud800", "\udfff", Mode.PLAN,
])
def test_canonical_encoder_rejects_non_json_values(canonical_envelope, value):
    canonical_envelope["I"]["value"] = value
    with pytest.raises(ValueError, match="^invalid canonical M2M envelope$"):
        m2m_module.encode_m2m_envelope(canonical_envelope)


@pytest.mark.parametrize("fragment", [
    '"T":"changed",', '"I":{"x":1,"x":2},',
    '"I":{"nested":[{"x":1,"x":2}]},', '"I":{"x":NaN},',
    '"I":{"x":Infinity},', '"I":{"x":-Infinity},', '"I":{"x":1e9999},',
    '"I":{"x":"\\ud800"},',
])
def test_canonical_decoder_rejects_ambiguous_wire(canonical_envelope, fragment):
    # Remove I so nested duplicates/non-finite values cannot fail only on top-level I.
    if not fragment.startswith('"T"'):
        del canonical_envelope["I"]
    wire = "{" + fragment + json.dumps(canonical_envelope)[1:]
    with pytest.raises(ValueError, match="^invalid canonical M2M envelope$"):
        m2m_module.decode_m2m_envelope(wire)


@pytest.mark.parametrize("wire", [
    None, b"{}", "[]", "null", "{} trailing", "{", "[" * 2000,
    "L:A S:module M:plan T:legacy R:[50]", "\ud800", " " * 65537,
], ids=["none", "bytes", "list", "null", "trailing", "truncated", "deep",
        "legacy", "surrogate", "oversize"])
def test_canonical_decoder_has_no_legacy_or_malformed_fallback(wire):
    with pytest.raises(ValueError, match="^invalid canonical M2M envelope$"):
        m2m_module.decode_m2m_envelope(wire)


@pytest.mark.parametrize("value", ["x" * 65536, "\u65e5" * 22000, [0] * 4096],
                         ids=["ascii_bytes", "utf8_bytes", "nodes"])
@pytest.mark.parametrize("entry", ["encode", "decode"])
def test_canonical_resource_limits_fail_closed(canonical_envelope, value, entry):
    canonical_envelope["I"]["value"] = value
    with pytest.raises(ValueError, match="^invalid canonical M2M envelope$"):
        if entry == "encode":
            m2m_module.encode_m2m_envelope(canonical_envelope)
        else:
            m2m_module.decode_m2m_envelope(json.dumps(canonical_envelope, ensure_ascii=False))


def test_canonical_depth_cycles_and_huge_integer_fail_closed(canonical_envelope):
    nested = []
    for _ in range(17):
        nested = [nested]
    cycle = []
    cycle.append(cycle)
    for value in (nested, cycle, 1 << 300000):
        canonical_envelope["I"]["value"] = value
        with pytest.raises(ValueError, match="^invalid canonical M2M envelope$"):
            m2m_module.encode_m2m_envelope(canonical_envelope)
    canonical_envelope["I"]["value"] = nested
    with pytest.raises(ValueError, match="^invalid canonical M2M envelope$"):
        m2m_module.decode_m2m_envelope(json.dumps(canonical_envelope))


def test_canonical_encoder_never_coerces_custom_containers(canonical_envelope):
    class TrapDict(dict):
        def items(self):
            raise AssertionError("custom accessor must not run")

    class TrapString(str):
        def __str__(self):
            raise AssertionError("custom conversion must not run")

    for value in (TrapDict(), TrapString("text")):
        canonical_envelope["I"]["value"] = value
        with pytest.raises(ValueError, match="^invalid canonical M2M envelope$"):
            m2m_module.encode_m2m_envelope(canonical_envelope)


@pytest.mark.parametrize("lane", ["A", "B", "C", "QA", "SENTINEL", "ORCH"])
@pytest.mark.parametrize("mode", ["exec", "plan", "qa"])
def test_canonical_lane_mode_and_declared_text_preserved(canonical_envelope, lane, mode):
    canonical_envelope.update(L=lane, M=mode, T="  stable:id,01  ",
                              A=" Verify scope, hold {delivery}\nthen report ")
    canonical_envelope["R"] = []
    canonical_envelope["O"] = []
    canonical_envelope["F"] = []
    canonical_envelope["I"]["integer"] = 10 ** 100
    assert m2m_module.decode_m2m_envelope(
        m2m_module.encode_m2m_envelope(canonical_envelope)) == canonical_envelope


def test_canonical_byte_boundary_accepts_exact_limit(canonical_envelope):
    canonical_envelope["I"] = {"padding": ""}
    remaining = 65536 - len(m2m_module.encode_m2m_envelope(canonical_envelope).encode("utf-8"))
    canonical_envelope["I"]["padding"] = "x" * remaining
    wire = m2m_module.encode_m2m_envelope(canonical_envelope)
    assert len(wire.encode("utf-8")) == 65536
    assert m2m_module.decode_m2m_envelope(wire) == canonical_envelope
    canonical_envelope["I"]["padding"] += "x"
    for operation, value in ((m2m_module.encode_m2m_envelope, canonical_envelope),
                             (m2m_module.decode_m2m_envelope, wire + " ")):
        with pytest.raises(ValueError, match="^invalid canonical M2M envelope$"):
            operation(value)


def test_canonical_depth_boundary_accepts_sixteen(canonical_envelope):
    nested = 0
    for _ in range(14):
        nested = [nested]
    canonical_envelope["I"] = {"nested": nested}  # Scalar at depth 16, root at 0.
    assert m2m_module.decode_m2m_envelope(
        m2m_module.encode_m2m_envelope(canonical_envelope)) == canonical_envelope
    canonical_envelope["I"]["nested"] = [nested]
    with pytest.raises(ValueError, match="^invalid canonical M2M envelope$"):
        m2m_module.encode_m2m_envelope(canonical_envelope)


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
        assert m2m.action == ""  # Legacy packets do not establish an action.

    def test_explicit_action_survives_compact_and_yaml(self):
        compiler = M2MCompiler()
        m2m = compiler.compile("Rollback the registry module", mode="plan")
        parsed = compiler.parse_compact(m2m.to_compact())
        assert parsed.action == "ROLLBACK"
        assert "  ACTION: ROLLBACK" in parsed.to_yaml()
        assert compiler._extract_action(compiler.decompile(parsed)) == "ROLLBACK"

    def test_legacy_object_compact_shape_unchanged(self):
        m2m = M2MPrompt(Lane.A, "registry", Mode.PLAN, "abc123", [50])
        assert m2m.to_compact() == "L:A S:registry M:plan T:abc123 R:[50]"

    def test_parse_compact_plan_unchanged(self):
        """parse_compact() with M:plan works as before."""
        compiler = M2MCompiler()
        compact = "L:B S:test M:plan T:test123 R:[50]"
        m2m = compiler.parse_compact(compact)
        assert m2m.mode == Mode.PLAN

    @pytest.mark.parametrize("invariants", [
        {"allowed_paths": ["modules/example"]}, {"wsp15": {"total": 18}},
        {"dependencies": ("first", "second")}, {"skills": {"one", "two"}},
        {"stop": "hold, do not deploy"}, {"scope": "owner} S:other"},
        {"scope": "{owner"}, {" key": "value"}, {"key:part": "value"},
        {"policy": " leading"}, {"policy": "two\nlines"},
        {"cost": float("nan")}, {"cost": float("inf")}, {1: "value"},
        [], "invalid mapping", {"key\x00": "value"}, {"policy": "two\twords"},
        {"policy": "two\u2028lines"}, {"policy": "two\u2029lines"},
        {"policy": "two\x85lines"}, {"two\u2028keys": "value"},
    ])
    @pytest.mark.parametrize("entry", ["object", "public_wrapper"])
    def test_lossy_invariants_reject_before_wire(self, invariants, entry):
        """Legacy compact syntax must not silently damage a structured work order."""
        with pytest.raises(ValueError, match="invariants"):
            if entry == "public_wrapper":
                compile_m2m("Validate package", mode="plan", invariants=invariants)
            else:
                M2MPrompt(Lane.ORCH, "module", Mode.PLAN, "AMI-A01",
                          invariants=invariants).to_compact()

    @pytest.mark.parametrize("key", ["policy", "public status"])
    @pytest.mark.parametrize("value", ["", "hold delivery", "C:/scratch", "a:b", True, 4, 0.5, None])
    def test_flat_invariants_keep_legacy_text_semantics(self, key, value):
        """Existing scalar values remain textual; this is not a typed envelope."""
        compiler = M2MCompiler()
        packet = compiler.compile("Validate package", invariants={key: value})
        assert compiler.parse_compact(packet.to_compact()).invariants == {key: str(value)}


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
        assert prose == "Execute task abc123. in scope: test/. following WSP 50."

    def test_decompile_legacy_stop_conditions(self):
        """Existing actionless packets must also render their explicit stops."""
        prose = decompile_m2m(
            "L:A S:registry M:plan T:abc123 R:[50] F:['missing approval']"
        )
        assert "Plan implementation for abc123" in prose
        assert "Abort if any condition holds: ['missing approval']." in prose

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
