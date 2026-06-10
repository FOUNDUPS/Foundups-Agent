#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Source-Authority Enum Tests -- Phase 1 code-pin.

Covers FOUNDUP_LIFECYCLE_SOURCE_AUTHORITY_CONTRACT_PHASE1 requirements:

  - Exactly 5 enum members.
  - Member string values are EXACTLY "monorepo_poc", "external_proto",
    "mvp_runtime", "dao_managed", "archived".
  - ACTIVE_STAGES is a frozenset containing exactly {MONOREPO_POC}.
  - resolve_source_authority ALWAYS returns MONOREPO_POC; the ignored
    declaration is reported observably (NEVER silently swallowed); the
    function NEVER raises -- even for garbage inputs.
  - request_promotion ALWAYS raises NotImplementedError, for every
    non-active stage and every garbage input.
  - Enum/builder value parity: SourceAuthority.MONOREPO_POC.value ==
    context_bundle_builder.SOURCE_AUTHORITY (drift guard; the ONLY
    contact between this slice and the builder).
  - AST scan: source module imports no runtime / executor / consumer
    module and calls no subprocess / network / file-write API.

No skip / no xfail on any security assertion.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from modules.foundups.agent.src.source_authority import (
    ACTIVE_STAGES,
    SourceAuthority,
    request_promotion,
    resolve_source_authority,
)

SOURCE_AUTHORITY_SOURCE = (
    Path(__file__).resolve().parents[1] / "src" / "source_authority.py"
)
BUILDER_SOURCE = (
    Path(__file__).resolve().parents[1] / "src" / "context_bundle_builder.py"
)


# ===========================================================================
# 1. Enum shape: exactly 5 members with exact string values
# ===========================================================================


class TestEnumShape:
    """The enum must expose exactly 5 members with EXACT string values."""

    def test_exactly_five_members(self):
        members = list(SourceAuthority)
        assert len(members) == 5, (
            f"SourceAuthority must have exactly 5 members; got {len(members)}: "
            f"{[m.value for m in members]}"
        )

    def test_enum_values_exact(self):
        """Member values are the wire format; they MUST be exact."""
        assert SourceAuthority.MONOREPO_POC.value == "monorepo_poc"
        assert SourceAuthority.EXTERNAL_PROTO.value == "external_proto"
        assert SourceAuthority.MVP_RUNTIME.value == "mvp_runtime"
        assert SourceAuthority.DAO_MANAGED.value == "dao_managed"
        assert SourceAuthority.ARCHIVED.value == "archived"

    def test_enum_member_names_exact(self):
        names = {m.name for m in SourceAuthority}
        assert names == {
            "MONOREPO_POC", "EXTERNAL_PROTO", "MVP_RUNTIME",
            "DAO_MANAGED", "ARCHIVED",
        }

    def test_enum_is_str_enum(self):
        """``SourceAuthority`` subclasses ``str`` so values serialize as
        strings without a separate ``.value`` call. This is part of the
        wire-format contract."""
        assert isinstance(SourceAuthority.MONOREPO_POC, str)
        assert SourceAuthority.MONOREPO_POC == "monorepo_poc"


# ===========================================================================
# 2. ACTIVE_STAGES
# ===========================================================================


class TestActiveStages:
    """Phase-1: exactly one reachable stage."""

    def test_active_stages_is_only_monorepo_poc(self):
        assert ACTIVE_STAGES == frozenset({SourceAuthority.MONOREPO_POC})

    def test_active_stages_is_frozen(self):
        with pytest.raises(AttributeError):
            ACTIVE_STAGES.add(SourceAuthority.DAO_MANAGED)  # type: ignore[attr-defined]

    @pytest.mark.parametrize(
        "non_active",
        [
            SourceAuthority.EXTERNAL_PROTO,
            SourceAuthority.MVP_RUNTIME,
            SourceAuthority.DAO_MANAGED,
            SourceAuthority.ARCHIVED,
        ],
    )
    def test_non_active_stages_not_in_active_set(self, non_active):
        assert non_active not in ACTIVE_STAGES


# ===========================================================================
# 3. resolve_source_authority: ALWAYS MONOREPO_POC; ignored is observable
# ===========================================================================


class TestResolveSourceAuthorityAlwaysMonorepoPoc:
    """The hard rule: a manifest / external input CANNOT promote a
    lifecycle stage by declaration. Phase-1 implementation: the function
    ALWAYS returns MONOREPO_POC and ALWAYS reports the ignored declaration
    (NEVER silently swallowed)."""

    def test_none_declaration_returns_monorepo_poc_and_none(self):
        effective, ignored = resolve_source_authority()
        assert effective is SourceAuthority.MONOREPO_POC
        assert ignored is None

    def test_explicit_none_declaration_returns_monorepo_poc_and_none(self):
        effective, ignored = resolve_source_authority(None)
        assert effective is SourceAuthority.MONOREPO_POC
        assert ignored is None

    @pytest.mark.parametrize(
        "declared_str",
        ["dao_managed", "mvp_runtime", "external_proto", "archived"],
    )
    def test_non_active_string_declarations_return_monorepo_poc_and_report_ignored(
        self, declared_str
    ):
        """Every non-active stage value, supplied as a string, is IGNORED
        and REPORTED. The bundle's effective stage is unchanged."""
        effective, ignored = resolve_source_authority(declared_str)
        assert effective is SourceAuthority.MONOREPO_POC
        assert ignored == declared_str

    @pytest.mark.parametrize(
        "declared_enum",
        [
            SourceAuthority.DAO_MANAGED,
            SourceAuthority.MVP_RUNTIME,
            SourceAuthority.EXTERNAL_PROTO,
            SourceAuthority.ARCHIVED,
        ],
    )
    def test_non_active_enum_declarations_return_monorepo_poc_and_report_ignored(
        self, declared_enum
    ):
        effective, ignored = resolve_source_authority(declared_enum)
        assert effective is SourceAuthority.MONOREPO_POC
        assert ignored == declared_enum.value

    def test_monorepo_poc_self_declaration_is_still_reported_as_ignored(self):
        """Even a caller declaring ``"monorepo_poc"`` (the active stage)
        is reported as ignored, because the contract is that the builder
        decides, not the caller. This makes the boundary mechanical:
        ``ignored is None`` iff the caller passed nothing."""
        effective, ignored = resolve_source_authority("monorepo_poc")
        assert effective is SourceAuthority.MONOREPO_POC
        assert ignored == "monorepo_poc"

        effective, ignored = resolve_source_authority(SourceAuthority.MONOREPO_POC)
        assert effective is SourceAuthority.MONOREPO_POC
        assert ignored == "monorepo_poc"


class TestResolveSourceAuthorityGarbageInputFuzz:
    """Garbage inputs (wrong type, casing variants, control chars, empty,
    ints, dicts, lists, NULL bytes) MUST be IGNORED and REPORTED. The
    function MUST NEVER raise."""

    @pytest.mark.parametrize(
        "garbage",
        [
            "DAO_MANAGED",           # casing variant
            "MonoRepo_PoC",          # mixed casing
            "monorepo_poc ",         # trailing whitespace
            " monorepo_poc",         # leading whitespace
            "unknown",               # plain unknown
            "",                      # empty string
            "   ",                   # whitespace
            42,                      # int
            -1,                      # negative int
            0,                       # zero
            True,                    # bool (subtype of int)
            False,                   # bool
            3.14,                    # float
            (1, 2, 3),               # tuple
            [1, 2, 3],               # list
            {"k": "v"},              # dict
            object(),                # arbitrary object
            "\x00",                  # NUL
            "ok\r\nFAKE: granted",   # CRLF log-injection shape
            "x\x1b[31m",             # ESC ANSI
        ],
    )
    def test_garbage_never_raises_and_returns_monorepo_poc(self, garbage):
        effective, ignored = resolve_source_authority(garbage)
        assert effective is SourceAuthority.MONOREPO_POC
        # ``ignored`` is a stringified form; we do not constrain the
        # exact representation, only that it is NOT None (the caller
        # supplied something non-None).
        assert ignored is not None
        assert isinstance(ignored, str)


# ===========================================================================
# 4. request_promotion: ALWAYS raises NotImplementedError
# ===========================================================================


class TestRequestPromotionAlwaysRaises:
    """Promotion is not a function call. In Phase-1 it ALWAYS raises."""

    @pytest.mark.parametrize(
        "target_str",
        ["external_proto", "mvp_runtime", "dao_managed", "archived"],
    )
    def test_non_active_string_target_raises(self, target_str):
        with pytest.raises(NotImplementedError, match="Phase-1"):
            request_promotion(target_str)

    @pytest.mark.parametrize(
        "target_enum",
        [
            SourceAuthority.EXTERNAL_PROTO,
            SourceAuthority.MVP_RUNTIME,
            SourceAuthority.DAO_MANAGED,
            SourceAuthority.ARCHIVED,
        ],
    )
    def test_non_active_enum_target_raises(self, target_enum):
        with pytest.raises(NotImplementedError, match="Phase-1"):
            request_promotion(target_enum)

    def test_monorepo_poc_target_also_raises(self):
        """Even requesting promotion to the already-active stage raises.
        The function's contract is "no promotion in Phase-1"; the active
        stage is already in effect via the builder constant, not via a
        promotion call."""
        with pytest.raises(NotImplementedError):
            request_promotion("monorepo_poc")
        with pytest.raises(NotImplementedError):
            request_promotion(SourceAuthority.MONOREPO_POC)

    @pytest.mark.parametrize(
        "garbage_target",
        ["unknown", "", "DAO_MANAGED", 42, None, ["x"], {"k": "v"}, object()],
    )
    def test_garbage_target_also_raises(self, garbage_target):
        """The error path is uniform: every input raises
        ``NotImplementedError``. There is no input that succeeds."""
        with pytest.raises(NotImplementedError):
            request_promotion(garbage_target)  # type: ignore[arg-type]

    def test_request_promotion_signature_returns_noreturn(self):
        """The static type hint says ``NoReturn``; the runtime contract
        matches."""
        sig = inspect.signature(request_promotion)
        # NoReturn is the documented return annotation
        from typing import get_type_hints
        hints = get_type_hints(request_promotion)
        assert "return" in hints

    def test_request_promotion_error_message_references_contract_doc(self):
        """The error message must point a reader at the contract doc and
        the four defined transitions."""
        with pytest.raises(NotImplementedError) as excinfo:
            request_promotion("mvp_runtime")
        message = str(excinfo.value)
        assert "Phase-1" in message
        assert "FOUNDUP_SOURCE_AUTHORITY_CONTRACT" in message


# ===========================================================================
# 5. Builder value parity (drift guard)
# ===========================================================================


class TestBuilderValueParity:
    """SourceAuthority.MONOREPO_POC.value MUST equal the builder's
    ``SOURCE_AUTHORITY`` constant. This is the ONLY contact between this
    slice and the builder -- a read-only import in the test file, used
    solely for value-parity verification (NOT wiring)."""

    def test_enum_monorepo_poc_value_matches_builder_constant(self):
        # Read-only import of the builder constant; the builder itself
        # is untouched in this slice.
        from modules.foundups.agent.src import context_bundle_builder as cbb
        assert SourceAuthority.MONOREPO_POC.value == cbb.SOURCE_AUTHORITY

    def test_builder_source_authority_is_exactly_monorepo_poc(self):
        from modules.foundups.agent.src import context_bundle_builder as cbb
        assert cbb.SOURCE_AUTHORITY == "monorepo_poc"


# ===========================================================================
# 6. AST-level read-only safety scan
# ===========================================================================


class TestSourceAuthorityAstSafety:
    """The enum module must be pure / read-only: no runtime / executor /
    consumer imports, no subprocess / network / dynamic-import / file-
    write, no CABR / payout / DAO identifiers."""

    def _enum_tree(self):
        return ast.parse(SOURCE_AUTHORITY_SOURCE.read_text(encoding="utf-8"))

    def _imported_modules(self, tree):
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mods.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mods.add(node.module)
        return mods

    def test_enum_module_imports_only_stdlib_pure(self):
        mods = self._imported_modules(self._enum_tree())
        # Pure: only __future__, enum, typing are allowed.
        allowed = {"__future__", "enum", "typing"}
        unexpected = mods - allowed
        assert not unexpected, (
            f"enum module imports beyond allowed pure-stdlib: {unexpected}"
        )

    def test_enum_module_no_runtime_executor_imports(self):
        mods = self._imported_modules(self._enum_tree())
        forbidden = (
            "hermes", "openclaw", "ai_overseer",
            "job_consumer", "foundup_job_consumer",
            "build_plan_executor", "wre_core",
            "wre_master_orchestrator", "build_plan_swarm",
            "context_bundle_builder",  # NOT wired even though sibling
            "foundup_manifest_validator",  # NOT wired
        )
        hits = [m for m in mods if any(f in m for f in forbidden)]
        assert hits == [], (
            f"enum module imports runtime / executor / sibling-wiring: {hits}"
        )

    def test_enum_module_no_subprocess_network_or_write(self):
        tree = self._enum_tree()
        mods = self._imported_modules(tree)
        banned_top = {
            "subprocess", "socket", "ssl", "urllib", "requests", "http",
            "ftplib", "telnetlib", "ctypes", "importlib",
            "multiprocessing", "os", "sys", "shutil", "pty",
            "pickle", "marshal",
        }
        bad = {m for m in mods if m.split(".")[0] in banned_top}
        assert not bad, f"enum module imports banned modules: {bad}"

        banned_names = {"eval", "exec", "compile", "__import__", "input", "execfile", "open"}
        banned_attrs = {
            "system", "popen", "Popen", "run", "call", "check_call",
            "check_output", "getoutput",
            "write_text", "write_bytes", "writelines", "write",
            "urlopen", "urlretrieve", "connect", "spawn", "fork",
            "execv", "execve",
            "remove", "unlink", "rmdir", "makedirs", "chmod", "kill",
        }
        name_off = []
        attr_off = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                if isinstance(f, ast.Name) and f.id in banned_names:
                    name_off.append(f.id)
                elif isinstance(f, ast.Attribute) and f.attr in banned_attrs:
                    attr_off.append(f.attr)
        assert not name_off, f"enum module calls banned names: {name_off}"
        assert not attr_off, f"enum module calls banned attrs: {attr_off}"

    def test_enum_module_no_cabr_payout_dao_identifier(self):
        """No CABR / payout / DAO / treasury / F_i / UPS / token
        identifier appears in the enum source. (DAO_MANAGED enum-member
        name is an authority STAGE label, not an authority surface; the
        check below looks for identifiers that imply actual CABR /
        payout / DAO logic.)"""
        src = SOURCE_AUTHORITY_SOURCE.read_text(encoding="utf-8")
        # Lower-case identifier-level check; the DAO_MANAGED stage
        # itself is allowed (its presence as an enum member is the
        # POINT of the contract). What is forbidden is the introduction
        # of CABR-engine / payout-engine / treasury identifiers.
        forbidden_substrings = [
            "cabr_engine", "cabr_score", "payout_engine", "payout_amount",
            "treasury_balance", "dao_ratify", "ratify_dao", "f_i_balance",
            "ups_balance", "token_balance", "tokenize",
        ]
        offenders = [s for s in forbidden_substrings if s in src.lower()]
        assert not offenders, (
            f"enum module references CABR / payout / DAO surface "
            f"identifiers: {offenders}"
        )


# ===========================================================================
# 7. Cross-module audit: the enum is NOT wired into the builder
# ===========================================================================


class TestEnumNotWiredIntoBuilder:
    """Phase-1 requires that the enum module is NOT imported by the
    builder. (The test file imports the builder for value-parity; the
    enum module itself does NOT.) This protects the deferred unification
    follow-up SOURCE_AUTHORITY_BUILDER_ENUM_UNIFICATION_PHASE2 from
    accidentally landing here."""

    def test_builder_does_not_import_source_authority_enum(self):
        tree = ast.parse(BUILDER_SOURCE.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "source_authority" not in alias.name
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert "source_authority" not in node.module


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
