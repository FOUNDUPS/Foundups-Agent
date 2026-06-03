# -*- coding: utf-8 -*-
"""
PolicyFlags chain regression guards (Phase 1) - structural + behavioral CI guards.

Slice: HXA_POLICYFLAGS_REGRESSION_GUARDS_PHASE1
Worker-Lane: W6

This module is the CI-coverage capstone named by the #755 router-security-chain
closeout. It does NOT re-prove the per-slice behavior (that lives in the existing
suites listed below); it installs durable INVARIANT guards that TRIP if a future
edit silently re-opens a closed hole in the PolicyFlags trust chain (#746, #752,
#754, #755).

Guards in this file:
  G1  NO-PRODUCTION-CALLER INVARIANT (AST-based, allowlist):
        - FoundUpJob.from_dict has ZERO production callers.
        - Every PolicyFlags.from_dict production caller is in the ALLOWLIST
          {contract __post_init__, contract from_dict body,
           router _sanitize_untrusted_policy_flags_dict}.
        Strings/comments/docstrings are excluded because only ast.Call nodes are
        counted; tests/archives are excluded by path.
  G4  SANITIZATION FUZZ (stdlib, DYNAMIC field enumeration):
        - dataclasses.fields(PolicyFlags) enumerated at runtime (no hardcoding).
        - For all-True and itertools.product representative combos, BOTH
          PolicyFlags.from_dict(...).to_dict() AND the router sanitizer force
          every non-dry_run field False; every such field name is in
          _SERVER_AUTHORED_FLAGS; router + contract sanitizers are CONSISTENT.
  G6  WRITE-BACK-BEFORE-GUARD ORDERING:
        - Static source-order check that _writeback_token_verdict precedes
          _evaluate_destructive_action_guard inside HermesJobExecutor.execute.
        - Behavioral mock call-order spy on both, asserting write-back precedes
          guard.

Predecessor chain (see audit doc HXA_POLICYFLAGS_REGRESSION_GUARDS_PHASE1.md):
  #746 PolicyFlags write-back remediation (server-authored truth)
  #752 router policy_flags boundary sanitization + Gate 2 fail-closed
  #754 chain continuation
  #755 router security chain closeout (named this capstone)

Mirrors existing patterns:
  test_foundup_job_router_policyflags_boundary.py
  test_hxa_policyflags_writeback_remediation.py
  test_route_foundup_job_live_mode_gate.py

WSP Compliance:
  WSP 5  : Test coverage (durable regression guards)
  WSP 97 : Truthful, fail-closed assertions; no overclaims

NO network / NO model / NO live DAE / NO WRE start. Pure structural + in-process
unit guards. No production source is modified by this file.
"""

from __future__ import annotations

import ast
import itertools
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import dataclasses

import pytest

# Import via the FULL package path so class identity matches production imports.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.communication.moltbot_bridge.src.foundup_job_contract import (  # noqa: E402
    PolicyFlags,
    _SERVER_AUTHORED_FLAGS,
)
from modules.infrastructure.wre_core.src.foundup_job_router import (  # noqa: E402
    _sanitize_untrusted_policy_flags_dict,
)


# ---------------------------------------------------------------------------
# Shared AST helper: find ATTRIBUTE.from_dict CALL sites in a source file.
# Only ast.Call nodes are inspected, so docstrings, comments, and string
# literals that merely mention "from_dict" are never counted.
# ---------------------------------------------------------------------------


def _read_source(source_path: Path) -> str:
    """Read a .py file tolerating a UTF-8 BOM (some repo files carry U+FEFF).

    ``utf-8-sig`` strips a leading BOM so ``ast.parse`` does not choke on a
    pre-existing non-printable char. We do NOT mutate the file - this is a
    read-only normalization for parsing.
    """
    return source_path.read_text(encoding="utf-8-sig")


def _find_from_dict_call_sites(
    source_path: Path, owner_name: str
) -> List[int]:
    """Return line numbers of ``<owner_name>.from_dict(...)`` CALL expressions.

    Parses the file with the stdlib ``ast`` module and walks for ``ast.Call``
    nodes whose ``func`` is ``Attribute(value=Name(id=owner_name), attr='from_dict')``.
    Strings / comments / docstrings cannot match because they are not Call nodes.
    """
    tree = ast.parse(_read_source(source_path), filename=str(source_path))
    hits: List[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "from_dict"
            and isinstance(func.value, ast.Name)
            and func.value.id == owner_name
        ):
            hits.append(node.lineno)
    return hits


def _enclosing_def_name(source_path: Path, lineno: int) -> str:
    """Return the name of the innermost function/method enclosing ``lineno``.

    Used to classify a PolicyFlags.from_dict call site against the allowlist by
    the function it lives in (e.g. ``__post_init__``, ``from_dict``,
    ``_sanitize_untrusted_policy_flags_dict``). Returns ``"<module>"`` if the
    call is at module scope.
    """
    tree = ast.parse(_read_source(source_path), filename=str(source_path))
    best_name = "<module>"
    best_span = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = getattr(node, "end_lineno", start)
            if start <= lineno <= end:
                span = end - start
                if best_span is None or span < best_span:
                    best_span = span
                    best_name = node.name
    return best_name


# Production source files (NOT tests, NOT archives).
_CONTRACT_SRC = (
    PROJECT_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "foundup_job_contract.py"
)
_ROUTER_SRC = (
    PROJECT_ROOT
    / "modules"
    / "infrastructure"
    / "wre_core"
    / "src"
    / "foundup_job_router.py"
)
_HERMES_SRC = (
    PROJECT_ROOT
    / "modules"
    / "infrastructure"
    / "wre_core"
    / "src"
    / "hermes_job_executor.py"
)


def _scan_owner_calls_safe(
    src: Path, owner_name: str
) -> List[int]:
    """AST-scan ``src`` for ``owner_name.from_dict`` calls, tolerating bad files.

    If a production file fails to parse for a reason unrelated to our target
    (e.g. a pre-existing syntax error in some other module), we must NOT crash
    the whole guard. But we also must NOT silently miss a real caller: if the
    raw text of an unparseable file contains the ``owner_name.from_dict`` token,
    we re-raise so the failure is visible. Files that don't even mention the
    token are safely skipped.
    """
    try:
        return _find_from_dict_call_sites(src, owner_name)
    except SyntaxError:
        raw = _read_source(src)
        if f"{owner_name}.from_dict" in raw:
            raise  # a potential caller hides in an unparseable file - surface it
        return []


def _production_source_files() -> List[Path]:
    """Every production .py file under modules/ and holo_index/.

    Excludes any path component named ``tests`` and any ``archive``/``_archive``
    directory, plus ``__pycache__``. This is the production scan surface for G1.
    """
    roots = [PROJECT_ROOT / "modules", PROJECT_ROOT / "holo_index"]
    excluded_parts = {"tests", "test", "archive", "_archive", "archived", "__pycache__"}
    files: List[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            parts = set(p.lower() for p in path.parts)
            if parts & excluded_parts:
                continue
            files.append(path)
    return files


# ---------------------------------------------------------------------------
# G1: NO-PRODUCTION-CALLER INVARIANT (AST-based, allowlist)
# ---------------------------------------------------------------------------


# Allowlist for PolicyFlags.from_dict production callers, keyed by (source file,
# enclosing function name). These are the ONLY legitimate deserialization
# chokepoints (#746 / #752). Any new production caller TRIPS G1.
_POLICYFLAGS_FROM_DICT_ALLOWLIST = {
    (_CONTRACT_SRC, "__post_init__"),  # contract:461 - FoundUpJob.__post_init__
    (_CONTRACT_SRC, "from_dict"),      # contract:662 - FoundUpJob.from_dict body
    (_ROUTER_SRC, "_sanitize_untrusted_policy_flags_dict"),  # router:372
}


class TestG1NoProductionCallerInvariant:
    """G1: from_dict deserialization chokepoints are locked to the allowlist."""

    def test_foundupjob_from_dict_has_zero_production_callers(self):
        """FoundUpJob.from_dict must have ZERO production callers (only tests call it)."""
        offenders: List[Tuple[str, int]] = []
        for src in _production_source_files():
            for lineno in _scan_owner_calls_safe(src, "FoundUpJob"):
                offenders.append((str(src.relative_to(PROJECT_ROOT)), lineno))
        assert offenders == [], (
            "FoundUpJob.from_dict gained production caller(s) - the untrusted "
            "deserialization path must only be exercised by tests. Offenders: "
            f"{offenders}"
        )

    def test_policyflags_from_dict_callers_are_all_allowlisted(self):
        """Every PolicyFlags.from_dict production CALL must be in the allowlist."""
        found_callers: List[Tuple[Path, str, int]] = []
        for src in _production_source_files():
            for lineno in _scan_owner_calls_safe(src, "PolicyFlags"):
                fn_name = _enclosing_def_name(src, lineno)
                found_callers.append((src, fn_name, lineno))

        # Every found caller must be allowlisted by (file, enclosing function).
        non_allowlisted = [
            (str(src.relative_to(PROJECT_ROOT)), fn_name, lineno)
            for (src, fn_name, lineno) in found_callers
            if (src, fn_name) not in _POLICYFLAGS_FROM_DICT_ALLOWLIST
        ]
        assert non_allowlisted == [], (
            "PolicyFlags.from_dict gained a NON-allowlisted production caller. "
            "Deserialization must route only through the 3 known chokepoints. "
            f"Offenders: {non_allowlisted}"
        )

        # And the three known chokepoints must STILL be present (the guard would
        # be vacuous if the calls were silently removed/renamed).
        present_keys = {(src, fn_name) for (src, fn_name, _ln) in found_callers}
        for key in _POLICYFLAGS_FROM_DICT_ALLOWLIST:
            assert key in present_keys, (
                "Expected PolicyFlags.from_dict chokepoint missing (refactor "
                f"may have moved/removed it): {key[0].name}:{key[1]}. present={present_keys}"
            )

    def test_policyflags_from_dict_naive_count_would_be_wrong(self):
        """Document why naive count==0 is INVALID for PolicyFlags.from_dict.

        PolicyFlags.from_dict legitimately has multiple production callers; a
        count==0 assertion would falsely fail. This guard pins the exact count
        (3) so a silent ADD is still caught even though count!=0.
        """
        total = 0
        for src in _production_source_files():
            total += len(_scan_owner_calls_safe(src, "PolicyFlags"))
        assert total == 3, (
            "PolicyFlags.from_dict production call-site count changed (expected 3 "
            f"allowlisted chokepoints, found {total}). Re-verify the allowlist."
        )

    # --- Negative controls (synthetic source strings; no production edit) ---

    def test_g1_negative_control_synthetic_extra_caller_trips(self):
        """SYNTHETIC: an extra FoundUpJob.from_dict caller is detected by the AST scan."""
        synthetic = (
            "def rogue(data):\n"
            "    # a comment mentioning FoundUpJob.from_dict must NOT count\n"
            "    '''docstring FoundUpJob.from_dict must NOT count'''\n"
            "    return FoundUpJob.from_dict(data)\n"
        )
        tree = ast.parse(synthetic)
        hits = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "from_dict"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "FoundUpJob"
            ):
                hits.append(node.lineno)
        # Exactly one CALL detected (line 4); the comment + docstring are ignored.
        assert hits == [4], (
            "G1 negative control failed: AST scan should detect exactly the one "
            f"real FoundUpJob.from_dict CALL, got {hits}"
        )

    def test_g1_negative_control_comment_and_docstring_excluded(self):
        """SYNTHETIC: a file that ONLY mentions from_dict in strings/comments => 0 hits."""
        synthetic = (
            '"""module docstring: PolicyFlags.from_dict and FoundUpJob.from_dict"""\n'
            "# inline comment PolicyFlags.from_dict\n"
            "X = 'PolicyFlags.from_dict in a string literal'\n"
        )
        tree = ast.parse(synthetic)
        hits = [
            n.lineno
            for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "from_dict"
        ]
        assert hits == [], (
            "G1 negative control failed: strings/comments must never be counted "
            f"as callers, got {hits}"
        )


# ---------------------------------------------------------------------------
# G4: SANITIZATION FUZZ (stdlib, DYNAMIC field enumeration)
# ---------------------------------------------------------------------------


def _policyflags_field_names() -> List[str]:
    """Runtime enumeration of PolicyFlags fields (NO hardcoded field list)."""
    return [f.name for f in dataclasses.fields(PolicyFlags)]


def _non_dry_run_fields() -> List[str]:
    return [f for f in _policyflags_field_names() if f != "dry_run_mode"]


class TestG4SanitizationFuzz:
    """G4: every non-dry_run field is forced False by BOTH sanitizers."""

    def test_field_enumeration_is_dynamic_and_nonempty(self):
        """Sanity: fields are discovered at runtime, dry_run_mode is present."""
        names = _policyflags_field_names()
        assert "dry_run_mode" in names
        assert len(names) >= 2  # at least dry_run_mode + one server-authored flag

    def test_every_non_dry_run_field_is_server_authored(self):
        """Structural invariant: each non-dry_run field name is in the frozenset.

        This is the property that makes the sanitizers' 'force everything except
        dry_run_mode to False' equivalent to 'force every _SERVER_AUTHORED_FLAGS
        member to False'. If a new gate field is added WITHOUT registering it in
        _SERVER_AUTHORED_FLAGS, this trips.
        """
        for name in _non_dry_run_fields():
            assert name in _SERVER_AUTHORED_FLAGS, (
                f"PolicyFlags field '{name}' is non-dry_run but NOT in "
                "_SERVER_AUTHORED_FLAGS - a new field may have been added without "
                "registering it as server-authored (sanitization hole)."
            )

    def test_all_true_inbound_dict_is_fully_sanitized_both_paths(self):
        """All-True inbound dict: contract + router both zero every non-dry_run field."""
        names = _policyflags_field_names()
        all_true = {name: True for name in names}

        contract_out = PolicyFlags.from_dict(all_true).to_dict()
        router_out, _dry_defaulted = _sanitize_untrusted_policy_flags_dict(all_true)

        for name in _non_dry_run_fields():
            assert contract_out[name] is False, (
                f"contract from_dict failed to zero '{name}' from all-True input"
            )
            assert router_out[name] is False, (
                f"router sanitizer failed to zero '{name}' from all-True input"
            )
        # dry_run_mode=True is operator-authored and preserved on both paths.
        assert contract_out["dry_run_mode"] is True
        assert router_out["dry_run_mode"] is True

    def test_product_combos_are_consistent_across_sanitizers(self):
        """itertools.product over representative combos: router == contract for non-dry_run.

        We fuzz dry_run_mode plus a representative subset of server-authored
        fields (full 2**12 product would be wasteful). For each combo BOTH
        sanitizers must agree on every non-dry_run field (all False), and on the
        operator-authored dry_run_mode value when explicitly supplied.
        """
        non_dry = _non_dry_run_fields()
        # Representative subset: span one of each gate family + a token field.
        sampled = [
            f
            for f in (
                "security_gate_passed",
                "permission_gate_passed",
                "exfoliation_gate_passed",
                "wsp_preflight_passed",
                "capability_token_validated",
            )
            if f in non_dry
        ]
        assert sampled, "expected representative server-authored fields to exist"

        for dry in (True, False):
            for combo in itertools.product([False, True], repeat=len(sampled)):
                inbound: Dict[str, bool] = {"dry_run_mode": dry}
                for fname, fval in zip(sampled, combo):
                    inbound[fname] = fval

                contract_out = PolicyFlags.from_dict(inbound).to_dict()
                router_out, _dd = _sanitize_untrusted_policy_flags_dict(inbound)

                for name in _non_dry_run_fields():
                    assert contract_out[name] is False, (
                        f"contract leaked '{name}'=True for inbound {inbound}"
                    )
                    assert router_out[name] is False, (
                        f"router leaked '{name}'=True for inbound {inbound}"
                    )
                # Explicit dry_run_mode is preserved identically by both paths.
                assert contract_out["dry_run_mode"] is dry
                assert router_out["dry_run_mode"] is dry

    def test_router_defaults_dry_run_true_when_absent_contract_does_not(self):
        """Router restores safe dry_run default; contract from_dict yields False.

        This documents the ONE intentional divergence: the router adds the safe
        'absent => dry-run' default (so a missing flag is never treated live),
        while raw contract from_dict yields dry_run_mode=False. Both still zero
        every server-authored flag - the security-relevant behavior is identical.
        """
        inbound = {"security_gate_passed": True}  # no dry_run_mode key

        contract_out = PolicyFlags.from_dict(inbound).to_dict()
        router_out, dry_defaulted = _sanitize_untrusted_policy_flags_dict(inbound)

        assert contract_out["security_gate_passed"] is False
        assert router_out["security_gate_passed"] is False
        assert contract_out["dry_run_mode"] is False  # raw from_dict
        assert router_out["dry_run_mode"] is True      # router safe default
        assert dry_defaulted is True

    # --- Negative control (test-local fake dataclass; no production edit) ---

    def test_g4_negative_control_leaky_sanitizer_is_caught(self):
        """SYNTHETIC: a fake 'sanitizer' that leaks a True flag fails the property.

        Proves the G4 assertion actually trips when the sanitization invariant is
        violated, using a test-local fake (no production code touched).
        """
        def _leaky_sanitizer(inbound: Dict[str, bool]) -> Dict[str, bool]:
            # Deliberately preserves security_gate_passed (the bug shape).
            out = {name: False for name in _policyflags_field_names()}
            out["dry_run_mode"] = bool(inbound.get("dry_run_mode", False))
            out["security_gate_passed"] = bool(inbound.get("security_gate_passed", False))
            return out

        leaked = _leaky_sanitizer({"security_gate_passed": True, "dry_run_mode": False})

        with pytest.raises(AssertionError):
            for name in _non_dry_run_fields():
                assert leaked[name] is False, f"leaked {name}"


# ---------------------------------------------------------------------------
# G6: WRITE-BACK-BEFORE-GUARD ORDERING
# ---------------------------------------------------------------------------


def _ordered_call_linenos_in_execute(method_name_a: str, method_name_b: str) -> Tuple[int, int]:
    """Return (lineno_a, lineno_b) of self.<a>(...) and self.<b>(...) inside execute().

    Uses AST to locate HermesJobExecutor.execute and find the FIRST self-method
    call to each named method within it. Raises if either is absent.
    """
    tree = ast.parse(_HERMES_SRC.read_text(encoding="utf-8"), filename=str(_HERMES_SRC))

    # Find the HermesJobExecutor.execute FunctionDef (the one taking a 'job' arg,
    # not the DAE-plugin execute(input_data)).
    execute_nodes = []
    for cls in ast.walk(tree):
        if isinstance(cls, ast.ClassDef) and cls.name == "HermesJobExecutor":
            for item in cls.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "execute":
                    execute_nodes.append(item)
    assert len(execute_nodes) == 1, (
        f"expected exactly one HermesJobExecutor.execute, found {len(execute_nodes)}"
    )
    execute = execute_nodes[0]

    line_a = None
    line_b = None
    for node in ast.walk(execute):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func
            # self.<method>(...)
            if isinstance(attr.value, ast.Name) and attr.value.id == "self":
                if attr.attr == method_name_a and line_a is None:
                    line_a = node.lineno
                if attr.attr == method_name_b and line_b is None:
                    line_b = node.lineno
    assert line_a is not None, f"{method_name_a} call not found in execute()"
    assert line_b is not None, f"{method_name_b} call not found in execute()"
    return line_a, line_b


class TestG6WriteBackBeforeGuardOrdering:
    """G6: validator write-back must precede the destructive-action guard (#746)."""

    def test_static_source_order_writeback_precedes_guard(self):
        """Static AST source-order: _writeback_token_verdict before guard in execute()."""
        wb_line, guard_line = _ordered_call_linenos_in_execute(
            "_writeback_token_verdict",
            "_evaluate_destructive_action_guard",
        )
        assert wb_line < guard_line, (
            "ORDERING REGRESSION: _writeback_token_verdict must be called BEFORE "
            f"_evaluate_destructive_action_guard in execute() (write-back line "
            f"{wb_line} >= guard line {guard_line}). Server-authored token truth "
            "must be written before the guard reads policy_flags."
        )

    def test_g6_negative_control_inverted_source_trips(self):
        """SYNTHETIC: an inverted source snippet (guard before write-back) is caught.

        Builds a synthetic in-memory source where the guard call precedes the
        write-back, runs the SAME ordering logic against it, and asserts the
        order check fails. No production file is edited.
        """
        inverted_src = (
            "class HermesJobExecutor:\n"
            "    def execute(self, job):\n"
            "        # INVERTED (defect shape): guard BEFORE write-back\n"
            "        guard_result = self._evaluate_destructive_action_guard(job, None)\n"
            "        self._writeback_token_verdict(job, None)\n"
            "        return guard_result\n"
        )
        tree = ast.parse(inverted_src)
        execute = None
        for cls in ast.walk(tree):
            if isinstance(cls, ast.ClassDef) and cls.name == "HermesJobExecutor":
                for item in cls.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "execute":
                        execute = item
        assert execute is not None

        wb_line = guard_line = None
        for node in ast.walk(execute):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "self"
            ):
                if node.func.attr == "_writeback_token_verdict" and wb_line is None:
                    wb_line = node.lineno
                if node.func.attr == "_evaluate_destructive_action_guard" and guard_line is None:
                    guard_line = node.lineno

        # In the inverted source the write-back does NOT precede the guard:
        assert not (wb_line < guard_line), (
            "G6 negative control failed: inverted source should NOT satisfy "
            f"write-back<guard (wb={wb_line}, guard={guard_line})"
        )

    def test_behavioral_writeback_precedes_guard_via_spy(self):
        """Behavioral: spy both methods, assert write-back is invoked before guard.

        Drives HermesJobExecutor.execute on a D-class job with spies installed on
        _writeback_token_verdict and _evaluate_destructive_action_guard. We assert
        the RELATIVE call order only (write-back recorded before guard). No
        network / model / live delegation occurs - the guard blocks dry-run
        bounded execution, and we never reach real delegation.
        """
        import os
        import shutil
        import tempfile
        from unittest.mock import patch

        from modules.infrastructure.wre_core.src.hermes_job_executor import (
            HermesJobExecutor,
        )
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            create_job,
        )
        from modules.infrastructure.wre_core.src.capability_token_validator import (
            LocalCapabilityTokenValidator,
        )

        call_order: List[str] = []

        tmpdir = tempfile.mkdtemp(prefix="g6_writeback_order_")
        try:
            # dry_run=True + HERMES_DELEGATE_ENABLED=0 -> bounded, no live delegate.
            executor = HermesJobExecutor(
                dry_run=True,
                workspace_root=tmpdir,
                token_validator=LocalCapabilityTokenValidator(),
            )

            real_writeback = executor._writeback_token_verdict
            real_guard = executor._evaluate_destructive_action_guard

            def spy_writeback(*args, **kwargs):
                call_order.append("writeback")
                return real_writeback(*args, **kwargs)

            def spy_guard(*args, **kwargs):
                call_order.append("guard")
                return real_guard(*args, **kwargs)

            # A job WITHOUT a real capability token: write-back zeroes the token
            # verdict (server-authored), then the guard evaluates and (for a
            # destructive class) blocks. We only assert ordering, not the verdict.
            job = create_job(
                tenant_id="tenant_g6",
                requested_action="build_foundup",  # D3 destructive class
                foundup_id="gotjunk",
            )

            with patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"}), \
                 patch.object(executor, "_writeback_token_verdict", side_effect=spy_writeback), \
                 patch.object(executor, "_evaluate_destructive_action_guard", side_effect=spy_guard):
                try:
                    executor.execute(job)
                except Exception:
                    # Ordering is the contract under test; downstream bounded
                    # failures (no live delegation) do not invalidate call order.
                    pass

            assert "writeback" in call_order, (
                "execute() did not call _writeback_token_verdict at all"
            )
            assert "guard" in call_order, (
                "execute() did not call _evaluate_destructive_action_guard at all"
            )
            assert call_order.index("writeback") < call_order.index("guard"), (
                "ORDERING REGRESSION (behavioral): write-back must be invoked "
                f"before the guard. Observed order: {call_order}"
            )
        finally:
            import gc

            gc.collect()  # release SQLite/file handles before cleanup (Windows)
            shutil.rmtree(tmpdir, ignore_errors=True)
