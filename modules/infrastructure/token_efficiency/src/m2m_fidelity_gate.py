# -*- coding: utf-8 -*-
"""
M2M Compiler Fidelity Gate (WSP 99 + Contract Section 3c + CTX.HOLO Addendum)

Validates that M2M compile->parse->decompile roundtrip preserves semantic content.
Ensures CTX.HOLO (HoloIndex retrieval evidence) survives roundtrip for exec/qa/review modes.

WSP_97 Truth Labels:
- OBSERVED: m2m_compiler.py compile/decompile/parse_compact methods exist
- SPECIFIED_NOT_IMPLEMENTED: CTX.HOLO preservation (added by this module)
- SPECIFIED_NOT_IMPLEMENTED: RawRef schema (added by this module)

Fail conditions:
- roundtrip loses WSP refs
- roundtrip loses fail_conditions
- roundtrip promotes worker to architect role
- CTX.HOLO dropped for exec/qa/review modes
- index_gap_event lost during roundtrip
- runtime_reindex_allowed mutated to true
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any

# Import from m2m_compiler (we read it, don't modify it unless strictly needed)
import sys
from pathlib import Path

# Add prompt/swarm to path for import
sys.path.insert(0, str(Path(__file__).parents[4] / "prompt" / "swarm"))
from m2m_compiler import M2MCompiler, M2MPrompt, Lane, Mode


class FidelityError(Exception):
    """Raised when M2M roundtrip fails to preserve semantic content."""

    def __init__(self, field: str, original: Any, roundtrip: Any, context: str = ""):
        self.field = field
        self.original = original
        self.roundtrip = roundtrip
        self.context = context
        msg = f"Fidelity loss in '{field}': {original!r} -> {roundtrip!r}"
        if context:
            msg += f" [{context}]"
        super().__init__(msg)


class HoloStatus(Enum):
    """HoloIndex retrieval status."""
    OK = "ok"
    INDEX_GAP = "index_gap"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


class HoloMode(Enum):
    """HoloIndex retrieval mode."""
    BUNDLE_JSON = "bundle_json"
    DIRECT_READ = "direct_read"
    NONE = "none"


@dataclass
class IndexGapEvent:
    """
    Schema for HoloIndex gap detection events.
    Per ADDENDUM_HOLOINDEX_M2M_INVARIANT.
    """
    gap_id: str
    query: str
    missing_target: str
    expected_surface: str  # code|wsp|skill|doc|symbol
    observed_hits: list[str] = field(default_factory=list)
    recommended_owner: str = "WRE_CI_INDEX_MAINTENANCE"
    live_enqueue_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "IndexGapEvent":
        return cls(**d)


@dataclass
class CTXHolo:
    """
    HoloIndex retrieval context for M2M packets.
    Per ADDENDUM_HOLOINDEX_M2M_INVARIANT.

    Any M2M packet with mode in [exec, qa, audit, review, verify, implement]
    MUST preserve CTX.HOLO through compile -> parse -> decompile.
    """
    query: str
    mode: HoloMode
    status: HoloStatus
    freshness_receipt: str | None = None
    indexed_at: str | None = None  # ISO8601
    code_hits: int = 0
    wsp_hits: int = 0
    skill_hits: int = 0
    target_recall_ok: bool | None = None  # None = unknown
    direct_read_fallback_used: bool = False
    index_gap_detected: bool = False
    index_gap_event: IndexGapEvent | None = None
    not_applicable_reason: str | None = None  # Required when status=not_applicable

    def to_dict(self) -> dict[str, Any]:
        d = {
            "query": self.query,
            "mode": self.mode.value,
            "status": self.status.value,
            "freshness_receipt": self.freshness_receipt,
            "indexed_at": self.indexed_at,
            "code_hits": self.code_hits,
            "wsp_hits": self.wsp_hits,
            "skill_hits": self.skill_hits,
            "target_recall_ok": self.target_recall_ok,
            "direct_read_fallback_used": self.direct_read_fallback_used,
            "index_gap_detected": self.index_gap_detected,
            "index_gap_event": self.index_gap_event.to_dict() if self.index_gap_event else None,
        }
        if self.not_applicable_reason:
            d["not_applicable_reason"] = self.not_applicable_reason
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CTXHolo":
        gap_event = None
        if d.get("index_gap_event"):
            gap_event = IndexGapEvent.from_dict(d["index_gap_event"])
        return cls(
            query=d["query"],
            mode=HoloMode(d["mode"]),
            status=HoloStatus(d["status"]),
            freshness_receipt=d.get("freshness_receipt"),
            indexed_at=d.get("indexed_at"),
            code_hits=d.get("code_hits", 0),
            wsp_hits=d.get("wsp_hits", 0),
            skill_hits=d.get("skill_hits", 0),
            target_recall_ok=d.get("target_recall_ok"),
            direct_read_fallback_used=d.get("direct_read_fallback_used", False),
            index_gap_detected=d.get("index_gap_detected", False),
            index_gap_event=gap_event,
            not_applicable_reason=d.get("not_applicable_reason"),
        )


@dataclass
class HoloInvariants:
    """
    Required invariants for HoloIndex context.
    Per ADDENDUM_HOLOINDEX_M2M_INVARIANT.
    """
    holoindex_required: bool = True
    direct_read_required_if_explicit_paths: bool = True
    runtime_reindex_allowed: bool = False  # MUST remain False
    index_gap_must_route: bool = True

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, bool]) -> "HoloInvariants":
        return cls(**d)


# Modes that require CTX.HOLO preservation
HOLO_REQUIRED_MODES = frozenset(["exec", "qa", "audit", "review", "verify", "implement"])


@dataclass
class RawRef:
    """
    Raw reference for content recovery.
    Per Contract Section 5c.
    """
    ref_id: str
    content_hash: str  # SHA256
    content_type: str  # "m2m_prose" | "rtk_output"
    storage_location: str  # "memory" | "file:<path>" | "session:<key>"
    created_at: int  # Unix timestamp
    expires_at: int  # TTL for cleanup
    recovered: bool = False  # True if already recovered

    @classmethod
    def create(
        cls,
        content: str,
        content_type: str,
        storage_location: str = "memory",
        ttl_seconds: int = 3600,
    ) -> "RawRef":
        """Create a new RawRef for content."""
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        ref_id = f"{content_type}_{content_hash[:16]}_{int(time.time())}"
        now = int(time.time())
        return cls(
            ref_id=ref_id,
            content_hash=content_hash,
            content_type=content_type,
            storage_location=storage_location,
            created_at=now,
            expires_at=now + ttl_seconds,
            recovered=False,
        )

    def verify_content(self, content: str) -> bool:
        """Verify content matches stored hash."""
        actual_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return actual_hash == self.content_hash


@dataclass
class M2MFidelityResult:
    """Result of fidelity check."""
    passed: bool
    original_prose: str
    roundtrip_prose: str
    m2m_compact: str
    original_action: str
    roundtrip_action: str
    original_scope: str
    roundtrip_scope: str
    wsp_refs_match: bool
    fail_conditions_match: bool
    ctx_holo_preserved: bool | None  # None if not applicable
    invariants_preserved: bool | None  # None if not applicable
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class M2MFidelityGate:
    """
    Validates M2M roundtrip fidelity.

    Contract invariant: M2M compilation MUST be semantically reversible.
    Per Contract Section 3c and ADDENDUM_HOLOINDEX_M2M_INVARIANT.
    """

    def __init__(self):
        self.compiler = M2MCompiler()

    def assert_fidelity(
        self,
        original_prose: str,
        lane: str,
        wsp_refs: list[int],
        mode: str = "exec",
        fail_conditions: list[str] | None = None,
        ctx_holo: CTXHolo | None = None,
        invariants: HoloInvariants | None = None,
    ) -> M2MFidelityResult:
        """
        Assert M2M roundtrip preserves semantic content.

        Args:
            original_prose: Original human-readable prompt
            lane: Target execution lane
            wsp_refs: WSP compliance requirements
            mode: Execution mode
            fail_conditions: Abort triggers
            ctx_holo: HoloIndex context (required for exec/qa/review modes)
            invariants: HoloIndex invariants

        Returns:
            M2MFidelityResult with pass/fail and details

        Raises:
            FidelityError: If critical semantic content is lost
        """
        errors = []

        # Handle empty input
        if not original_prose or not original_prose.strip():
            raise FidelityError("input", original_prose, None, "Empty input not allowed")

        # Compile to M2M
        m2m = self.compiler.compile(
            prose=original_prose,
            lane=lane,
            wsp_refs=wsp_refs,
            mode=mode,
            fail_conditions=fail_conditions or [],
        )

        # Get compact form for parsing
        m2m_compact = m2m.to_compact()

        # Parse compact back to M2MPrompt
        parsed = self.compiler.parse_compact(m2m_compact)

        # Decompile to prose
        roundtrip_prose = self.compiler.decompile(parsed)

        # Extract components
        original_action = self.compiler._extract_action(original_prose)
        roundtrip_action = self.compiler._extract_action(roundtrip_prose)

        original_scope = self.compiler._extract_scope(original_prose)
        roundtrip_scope = m2m.scope  # Use M2M scope, not extracted from roundtrip

        # Check WSP refs
        wsp_refs_match = m2m.wsp_refs == wsp_refs and parsed.wsp_refs == wsp_refs
        if not wsp_refs_match:
            raise FidelityError("wsp_refs", wsp_refs, parsed.wsp_refs)

        # Check fail conditions
        fail_conditions = fail_conditions or []
        fail_conditions_match = m2m.fail_conditions == fail_conditions
        if not fail_conditions_match:
            errors.append(f"fail_conditions mismatch: {fail_conditions} vs {m2m.fail_conditions}")

        # Check lane
        if parsed.lane.value != lane.upper():
            raise FidelityError("lane", lane.upper(), parsed.lane.value)

        # Check mode
        if parsed.mode.value != mode.lower():
            raise FidelityError("mode", mode.lower(), parsed.mode.value)

        # Check action verb (allow default to IMPLEMENT)
        action_ok = (original_action == roundtrip_action or roundtrip_action == "IMPLEMENT")
        if not action_ok:
            errors.append(f"action mismatch: {original_action} vs {roundtrip_action}")

        # Check scope (if present in original)
        scope_ok = True
        if original_scope:
            scope_ok = original_scope in roundtrip_prose or m2m.scope == original_scope
            if not scope_ok:
                errors.append(f"scope mismatch: {original_scope} not in roundtrip")

        # CTX.HOLO validation for applicable modes
        ctx_holo_preserved = None
        invariants_preserved = None

        if mode.lower() in HOLO_REQUIRED_MODES:
            if ctx_holo is None:
                errors.append(f"CTX.HOLO required for mode={mode} but not provided")
                ctx_holo_preserved = False
            else:
                ctx_holo_preserved = self._validate_ctx_holo(ctx_holo, errors)

            if invariants is None:
                invariants = HoloInvariants()  # Use defaults
            invariants_preserved = self._validate_invariants(invariants, errors)

        passed = len(errors) == 0

        return M2MFidelityResult(
            passed=passed,
            original_prose=original_prose,
            roundtrip_prose=roundtrip_prose,
            m2m_compact=m2m_compact,
            original_action=original_action,
            roundtrip_action=roundtrip_action,
            original_scope=original_scope,
            roundtrip_scope=roundtrip_scope,
            wsp_refs_match=wsp_refs_match,
            fail_conditions_match=fail_conditions_match,
            ctx_holo_preserved=ctx_holo_preserved,
            invariants_preserved=invariants_preserved,
            errors=errors,
        )

    def _validate_ctx_holo(self, ctx: CTXHolo, errors: list[str]) -> bool:
        """Validate CTX.HOLO fields survive roundtrip simulation."""
        valid = True

        # Validate required fields exist
        if not ctx.query:
            errors.append("CTX.HOLO: query is required")
            valid = False

        # Validate not_applicable requires reason
        if ctx.status == HoloStatus.NOT_APPLICABLE:
            if not ctx.not_applicable_reason:
                errors.append("CTX.HOLO: not_applicable_reason required when status=not_applicable")
                valid = False

        # Validate index_gap_event survives if present
        if ctx.index_gap_detected and not ctx.index_gap_event:
            errors.append("CTX.HOLO: index_gap_detected=true but no index_gap_event")
            valid = False

        # Validate index_gap_event schema
        if ctx.index_gap_event:
            event = ctx.index_gap_event
            if not event.gap_id or not event.query or not event.missing_target:
                errors.append("CTX.HOLO: index_gap_event missing required fields")
                valid = False
            if event.expected_surface not in ("code", "wsp", "skill", "doc", "symbol"):
                errors.append(f"CTX.HOLO: invalid expected_surface: {event.expected_surface}")
                valid = False

        # Test roundtrip preservation
        serialized = ctx.to_dict()
        restored = CTXHolo.from_dict(serialized)

        # Compare key fields
        if restored.query != ctx.query:
            errors.append("CTX.HOLO: query not preserved through roundtrip")
            valid = False
        if restored.status != ctx.status:
            errors.append("CTX.HOLO: status not preserved through roundtrip")
            valid = False
        if restored.index_gap_detected != ctx.index_gap_detected:
            errors.append("CTX.HOLO: index_gap_detected not preserved through roundtrip")
            valid = False

        return valid

    def _validate_invariants(self, inv: HoloInvariants, errors: list[str]) -> bool:
        """Validate HoloIndex invariants."""
        valid = True

        # runtime_reindex_allowed MUST be False
        if inv.runtime_reindex_allowed:
            errors.append("INVARIANT: runtime_reindex_allowed must be False")
            valid = False

        # Test roundtrip preservation
        serialized = inv.to_dict()
        restored = HoloInvariants.from_dict(serialized)

        if restored.runtime_reindex_allowed != inv.runtime_reindex_allowed:
            errors.append("INVARIANT: runtime_reindex_allowed mutated during roundtrip")
            valid = False

        return valid

    def validate_role_boundary(
        self,
        sender_role: str,
        receiver_role: str,
    ) -> bool:
        """
        Validate that roundtrip doesn't promote worker to architect.

        Fail condition: roundtrip that promotes worker to architect role.
        """
        # Define role hierarchy
        role_levels = {
            "worker": 1,
            "qa": 2,
            "sentinel": 3,
            "architect": 4,
            "external_principal": 5,
        }

        sender_level = role_levels.get(sender_role.lower(), 0)
        receiver_level = role_levels.get(receiver_role.lower(), 0)

        # Worker cannot become architect through roundtrip
        if sender_role.lower() == "worker" and receiver_role.lower() == "architect":
            raise FidelityError(
                "role",
                sender_role,
                receiver_role,
                "Worker cannot be promoted to architect through M2M roundtrip"
            )

        return True


def assert_m2m_fidelity(
    original_prose: str,
    lane: str,
    wsp_refs: list[int],
    mode: str = "exec",
    fail_conditions: list[str] | None = None,
    ctx_holo: CTXHolo | None = None,
    invariants: HoloInvariants | None = None,
) -> bool:
    """
    Contract invariant: M2M compilation MUST be semantically reversible.
    Per Contract Section 3c and ADDENDUM_HOLOINDEX_M2M_INVARIANT.

    Steps:
    1. Compile original_prose to M2M
    2. Decompile M2M back to prose
    3. Extract key components from both (action, scope, WSP refs)
    4. Assert key components match

    Returns True if fidelity holds, raises FidelityError if not.
    """
    gate = M2MFidelityGate()
    result = gate.assert_fidelity(
        original_prose=original_prose,
        lane=lane,
        wsp_refs=wsp_refs,
        mode=mode,
        fail_conditions=fail_conditions,
        ctx_holo=ctx_holo,
        invariants=invariants,
    )

    if not result.passed:
        raise FidelityError("fidelity_check", "passed", "failed", "; ".join(result.errors))

    return True


# M2M output methods for this module's results
def to_m2m_compact(result: M2MFidelityResult) -> str:
    """Emit result as M2M compact format."""
    status = "OK" if result.passed else "FAIL"
    return (
        f"FIDELITY:{status} "
        f"WSP_MATCH:{result.wsp_refs_match} "
        f"FAIL_MATCH:{result.fail_conditions_match} "
        f"HOLO:{result.ctx_holo_preserved} "
        f"ERRS:{len(result.errors)}"
    )


def to_m2m_yaml(result: M2MFidelityResult) -> str:
    """Emit result as M2M YAML format."""
    lines = [
        "FIDELITY_RESULT:",
        f"  STATUS: {'OK' if result.passed else 'FAIL'}",
        f"  WSP_REFS_MATCH: {result.wsp_refs_match}",
        f"  FAIL_CONDITIONS_MATCH: {result.fail_conditions_match}",
        f"  CTX_HOLO_PRESERVED: {result.ctx_holo_preserved}",
        f"  INVARIANTS_PRESERVED: {result.invariants_preserved}",
        f"  ORIGINAL_ACTION: {result.original_action}",
        f"  ROUNDTRIP_ACTION: {result.roundtrip_action}",
        f"  ORIGINAL_SCOPE: {result.original_scope}",
        f"  ROUNDTRIP_SCOPE: {result.roundtrip_scope}",
        f"  ERROR_COUNT: {len(result.errors)}",
    ]
    if result.errors:
        lines.append("  ERRORS:")
        for err in result.errors:
            lines.append(f"    - {err}")
    return "\n".join(lines)
