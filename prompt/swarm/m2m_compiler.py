# -*- coding: utf-8 -*-
"""
M2M Prompt Compiler (WSP 99)
Qwen-delegatable compiler for 012 prose -> 0102 M2M format conversion.

Usage:
    from prompt.swarm.m2m_compiler import M2MCompiler

    compiler = M2MCompiler()
    m2m = compiler.compile(prose="Analyze auth module", lane="A", wsp_refs=[50, 71])
    prose = compiler.decompile(m2m)
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Lane(Enum):
    """Execution lanes for 0102 swarm."""
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    QA = "QA"
    SENTINEL = "SENTINEL"
    ORCH = "ORCH"


class Mode(Enum):
    """Execution modes."""
    EXEC = "exec"
    PLAN = "plan"
    QA = "qa"
    AUDIT = "audit"
    REVIEW = "review"
    VERIFY = "verify"
    IMPLEMENT = "implement"


class Status(Enum):
    """Execution status codes."""
    OK = "OK"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    PENDING = "PENDING"
    SKIP = "SKIP"


# Action verbs recognized by M2M parser (single token each)
ACTION_VERBS = frozenset([
    "ANALYZE", "CREATE", "DELETE", "ENHANCE", "FIX",
    "IMPLEMENT", "MIGRATE", "REFACTOR", "TEST", "VALIDATE",
    "VERIFY", "REVIEW", "DEPLOY", "ROLLBACK"
])

# Politeness markers to strip from 012 prose
POLITENESS_MARKERS = re.compile(
    r'\b(please|could you|would you|i would like|make sure to|'
    r'ensure that|be careful to|remember to|don\'t forget to)\b',
    re.IGNORECASE
)


# Local JSON transport profile, not WSP admission or a signing canonicalization.
M2M_ENVELOPE_MAX_BYTES = 65536
M2M_ENVELOPE_MAX_DEPTH = 16
M2M_ENVELOPE_MAX_NODES = 4096
_ENVELOPE_ERROR = "invalid canonical M2M envelope"
_ENVELOPE_REQUIRED = frozenset("schema ROLE ORIGIN L S M T A R I O F".split())
_ENVELOPE_ENUMS = {
    "schema": {"0102_m2m_v1"},
    "ROLE": {"architect", "worker", "verifier", "coordinator", "validator"},
    "ORIGIN": {"external_principal", "internal_handoff", "autonomous_trigger"},
    "L": {"A", "B", "C", "QA", "SENTINEL", "ORCH"},
    "M": {"exec", "plan", "qa"},
}


def _snapshot_m2m_json(value: Any, budget: list[int], depth: int = 0) -> Any:
    """Copy exact JSON types with bounded traversal and compact UTF-8 accounting."""
    budget[0] -= 1
    kind = type(value)
    if depth > M2M_ENVELOPE_MAX_DEPTH or budget[0] < 0:
        raise ValueError(_ENVELOPE_ERROR)
    if kind not in (dict, list, str, bool, int, float, type(None)):
        raise ValueError(_ENVELOPE_ERROR)
    if kind in (dict, list):
        count = len(value)
        multiplier = 2 if kind is dict else 1  # Dict keys count as nodes too.
        budget[1] -= 2 + max(0, multiplier * count - 1)
        if multiplier * count > budget[0] or budget[1] < 0:
            raise ValueError(_ENVELOPE_ERROR)
        if kind is list:
            return [_snapshot_m2m_json(v, budget, depth + 1) for v in value]
        snapshot = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(_ENVELOPE_ERROR)
            copied_key = _snapshot_m2m_json(key, budget, depth + 1)
            snapshot[copied_key] = _snapshot_m2m_json(item, budget, depth + 1)
        return snapshot
    if kind is str and len(value) > M2M_ENVELOPE_MAX_BYTES:
        raise ValueError(_ENVELOPE_ERROR)
    if kind is int and value.bit_length() > M2M_ENVELOPE_MAX_BYTES * 4:
        raise ValueError(_ENVELOPE_ERROR)
    if kind is float and not math.isfinite(value):
        raise ValueError(_ENVELOPE_ERROR)
    scalar = json.dumps(value, ensure_ascii=False, allow_nan=False)
    budget[1] -= len(scalar.encode("utf-8"))
    if budget[1] < 0:
        raise ValueError(_ENVELOPE_ERROR)
    return value


def _validate_m2m_envelope(envelope: dict[str, Any]) -> None:
    """Check WSP 99 section 0 shape after copying to plain JSON types."""
    if type(envelope) is not dict:
        raise ValueError(_ENVELOPE_ERROR)
    fields = set(envelope)
    if not _ENVELOPE_REQUIRED <= fields or fields - _ENVELOPE_REQUIRED - {"PRINCIPAL_REF"}:
        raise ValueError(_ENVELOPE_ERROR)
    for name, choices in _ENVELOPE_ENUMS.items():
        if type(envelope[name]) is not str or envelope[name] not in choices:
            raise ValueError(_ENVELOPE_ERROR)
    for name in ("S", "T", "A", "PRINCIPAL_REF"):
        if name in envelope and (type(envelope[name]) is not str or not envelope[name].strip()):
            raise ValueError(_ENVELOPE_ERROR)
    if type(envelope["I"]) is not dict or type(envelope["R"]) is not list:
        raise ValueError(_ENVELOPE_ERROR)
    if any(type(ref) is not int or ref < 0 for ref in envelope["R"]):
        raise ValueError(_ENVELOPE_ERROR)
    for name in ("O", "F"):
        if type(envelope[name]) is not list or any(type(v) is not str for v in envelope[name]):
            raise ValueError(_ENVELOPE_ERROR)


def _unique_m2m_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate wire keys at every depth instead of accepting last-wins."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(_ENVELOPE_ERROR)
        result[key] = value
    return result


def encode_m2m_envelope(envelope: dict[str, Any]) -> str:
    """Encode normalized WSP 99 fields without inference, coercion or admission.

    Produces deterministic compact JSON for this Python codec, not signing bytes.
    PRINCIPAL_REF remains optional. Local limits: 64 KiB UTF-8, depth 16 (root 0),
    4096 nodes including dictionary keys; Python integer conversion limits apply.
    """
    try:
        snapshot = _snapshot_m2m_json(
            envelope, [M2M_ENVELOPE_MAX_NODES, M2M_ENVELOPE_MAX_BYTES])
        _validate_m2m_envelope(snapshot)
        wire = json.dumps(snapshot, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
        if len(wire.encode("utf-8")) > M2M_ENVELOPE_MAX_BYTES:
            raise ValueError(_ENVELOPE_ERROR)
        return wire
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ValueError(_ENVELOPE_ERROR) from None


def decode_m2m_envelope(wire: str) -> dict[str, Any]:
    """Decode only the bounded canonical JSON envelope; never fall back to legacy.

    Preserves Python JSON value types, not original whitespace/number spellings.
    Does not qualify other consumers, paths, WSP references or execution authority.
    """
    try:
        if type(wire) is not str or len(wire) > M2M_ENVELOPE_MAX_BYTES:
            raise ValueError(_ENVELOPE_ERROR)
        if len(wire.encode("utf-8")) > M2M_ENVELOPE_MAX_BYTES:
            raise ValueError(_ENVELOPE_ERROR)
        parsed = json.loads(wire, object_pairs_hook=_unique_m2m_json_object)
        snapshot = _snapshot_m2m_json(
            parsed, [M2M_ENVELOPE_MAX_NODES, M2M_ENVELOPE_MAX_BYTES])
        _validate_m2m_envelope(snapshot)
        return snapshot
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ValueError(_ENVELOPE_ERROR) from None


def _encode_legacy_invariants(invariants: dict[str, Any]) -> str:
    """Reject constraints that the legacy flat-text grammar cannot preserve."""
    error = "legacy compact invariants require lossless scalar fields"
    if type(invariants) is not dict:
        raise ValueError(error)
    fields = []
    for key, value in invariants.items():
        if (type(key) is not str or not key or key != key.strip()
                or any(c in ",:{}\x85\u2028\u2029" or ord(c) < 32 for c in key)):
            raise ValueError(error)
        if type(value) not in (str, bool, int, float, type(None)):
            raise ValueError(error)
        if type(value) is float and not math.isfinite(value):
            raise ValueError(error)
        text = str(value)
        if text != text.strip() or any(c in ",{}\x85\u2028\u2029" or ord(c) < 32 for c in text):
            raise ValueError(error)
        fields.append(f"{key}:{text}")
    return ",".join(fields)


@dataclass
class M2MPrompt:
    """Compact M2M prompt structure (WSP 99)."""
    lane: Lane
    scope: str
    mode: Mode
    task_hash: str
    wsp_refs: list[int] = field(default_factory=list)
    invariants: dict[str, Any] = field(default_factory=dict)
    outputs: list[str] = field(default_factory=list)
    fail_conditions: list[str] = field(default_factory=list)

    # Optional metadata
    sender: str = "0102-ORCH"
    receiver: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    action: str = ""  # Empty only for legacy packets without an explicit action.

    def to_compact(self) -> str:
        """Serialize to 012 compact format (single line)."""
        parts = [
            f"L:{self.lane.value}",
            f"S:{self.scope}",
            f"M:{self.mode.value}",
            f"T:{self.task_hash}",
        ]

        if self.action:
            parts.append(f"A:{self.action}")

        if self.wsp_refs:
            parts.append(f"R:{self.wsp_refs}")

        inv_str = _encode_legacy_invariants(self.invariants)
        if inv_str:
            parts.append(f"I:{{{inv_str}}}")

        if self.outputs:
            parts.append(f"O:{self.outputs}")

        if self.fail_conditions:
            parts.append(f"F:{self.fail_conditions}")

        return " ".join(parts)

    def to_yaml(self) -> str:
        """Serialize to YAML format (verbose, for 012 review)."""
        lines = [
            "M2M_VERSION: 1.0",
            f"SENDER: {self.sender}",
            f"RECEIVER: {self.receiver or '0102-' + self.lane.value}",
            f"TS: {self.timestamp}",
            "",
            "MISSION:",
            f"  LANE: {self.lane.value}",
            f"  SCOPE: {self.scope}",
            f"  MODE: {self.mode.value}",
            f"  TASK: {self.task_hash}",
            f"  WSP: {self.wsp_refs}",
        ]

        if self.action:
            lines.append(f"  ACTION: {self.action}")

        if self.invariants:
            lines.append("  INVARIANTS:")
            for k, v in self.invariants.items():
                lines.append(f"    {k}: {v}")

        if self.outputs:
            lines.append(f"  OUTPUTS: {self.outputs}")

        if self.fail_conditions:
            lines.append(f"  FAIL_CONDITIONS: {self.fail_conditions}")

        return "\n".join(lines)


class M2MCompiler:
    """
    Compiler for 012 prose -> 0102 M2M format.

    Qwen-delegatable: Can be invoked by Qwen for autonomous compilation.
    """

    def __init__(self):
        self.action_verbs = ACTION_VERBS
        self.politeness_re = POLITENESS_MARKERS

    def compile(
        self,
        prose: str,
        lane: str = "A",
        scope: str = "",
        mode: str = "exec",
        wsp_refs: list[int] | None = None,
        invariants: dict[str, Any] | None = None,
        outputs: list[str] | None = None,
        fail_conditions: list[str] | None = None,
        sender: str = "0102-ORCH",
    ) -> M2MPrompt:
        """
        Compile 012 prose prompt to M2M format.

        Args:
            prose: Human-readable prompt text
            lane: Target execution lane (A, B, C, QA, SENTINEL, ORCH)
            scope: File/module scope (extracted from prose if not provided)
            mode: Execution mode (exec, plan, qa)
            wsp_refs: Required WSP compliance numbers
            invariants: Constraint key-value pairs
            outputs: Required output artifacts
            fail_conditions: Abort triggers
            sender: Sending agent ID

        Returns:
            M2MPrompt object ready for serialization
        """
        # Strip politeness markers
        clean_prose = self.politeness_re.sub("", prose).strip()
        clean_prose = re.sub(r'\s+', ' ', clean_prose)

        # Extract action verb
        action = self._extract_action(clean_prose)

        # Extract scope from prose if not provided
        if not scope:
            scope = self._extract_scope(clean_prose)

        # Generate task hash
        task_hash = self._generate_task_hash(clean_prose, scope)

        # Build M2M prompt
        return M2MPrompt(
            lane=Lane(lane.upper()),
            scope=scope,
            mode=Mode(mode.lower()),
            task_hash=task_hash,
            wsp_refs=wsp_refs or [50],  # WSP 50 always required
            invariants=invariants if invariants is not None else {},
            outputs=outputs or [],
            fail_conditions=fail_conditions or [],
            sender=sender,
            action=action,
        )

    def decompile(self, m2m: M2MPrompt) -> str:
        """
        Decompile M2M prompt back to 012-readable prose.

        Args:
            m2m: M2MPrompt object

        Returns:
            Human-readable prompt string
        """
        parts = []

        # Preserve an explicit action; retain mode-only rendering for legacy packets.
        if m2m.action:
            parts.append(f"{m2m.action} task {m2m.task_hash} (mode: {m2m.mode.value})")
        elif m2m.mode == Mode.EXEC:
            parts.append(f"Execute task {m2m.task_hash}")
        elif m2m.mode == Mode.PLAN:
            parts.append(f"Plan implementation for {m2m.task_hash}")
        else:
            parts.append(f"Review {m2m.task_hash}")

        # Scope
        if m2m.scope:
            parts.append(f"in scope: {m2m.scope}")

        # WSP refs
        if m2m.wsp_refs:
            wsp_str = ", ".join(f"WSP {n}" for n in m2m.wsp_refs)
            parts.append(f"following {wsp_str}")

        # Outputs
        if m2m.outputs:
            parts.append(f"producing: {', '.join(m2m.outputs)}")

        if m2m.fail_conditions:
            parts.append(f"Abort if any condition holds: {m2m.fail_conditions!r}")

        return ". ".join(parts) + "."

    def parse_compact(self, compact: str) -> M2MPrompt:
        """
        Parse compact M2M format back to M2MPrompt object.

        Args:
            compact: Single-line compact format string

        Returns:
            M2MPrompt object
        """
        # Parse key:value pairs
        parts = {}
        for match in re.finditer(r'([LSMTRIOFCA]):(\[[^\]]+\]|\{[^}]+\}|\S+)', compact):
            key, value = match.groups()
            parts[key] = value

        # Extract values
        lane = parts.get("L", "A")
        scope = parts.get("S", "")
        mode = parts.get("M", "exec")
        task_hash = parts.get("T", "unknown")

        # Parse WSP refs
        wsp_refs = []
        if "R" in parts:
            wsp_str = parts["R"].strip("[]")
            wsp_refs = [int(x.strip()) for x in wsp_str.split(",") if x.strip().isdigit()]

        # Parse invariants
        invariants = {}
        if "I" in parts:
            inv_str = parts["I"].strip("{}")
            for pair in inv_str.split(","):
                if ":" in pair:
                    k, v = pair.split(":", 1)
                    invariants[k.strip()] = v.strip()

        # Parse outputs
        outputs = []
        if "O" in parts:
            out_str = parts["O"].strip("[]")
            outputs = [x.strip().strip("'\"") for x in out_str.split(",")]

        # Parse fail conditions
        fail_conditions = []
        if "F" in parts:
            fail_str = parts["F"].strip("[]")
            fail_conditions = [x.strip().strip("'\"") for x in fail_str.split(",")]

        return M2MPrompt(
            lane=Lane(lane.upper()),
            scope=scope,
            mode=Mode(mode.lower()),
            task_hash=task_hash,
            wsp_refs=wsp_refs,
            invariants=invariants,
            outputs=outputs,
            fail_conditions=fail_conditions,
            action=parts.get("A", ""),
        )

    def _extract_action(self, text: str) -> str:
        """Extract action verb from text."""
        words = text.upper().split()
        for word in words:
            clean_word = re.sub(r'[^A-Z]', '', word)
            if clean_word in self.action_verbs:
                return clean_word
        return "IMPLEMENT"  # Default

    def _extract_scope(self, text: str) -> str:
        """Extract file/module scope from text."""
        # Look for file paths
        path_match = re.search(r'[\w/\\]+\.(py|md|js|ts|yaml|json)', text)
        if path_match:
            return path_match.group(0)

        # Look for module references
        module_match = re.search(r'modules?/[\w/]+', text, re.IGNORECASE)
        if module_match:
            return module_match.group(0)

        # Look for "the X module/file"
        ref_match = re.search(r'the\s+(\w+)\s+(module|file|component)', text, re.IGNORECASE)
        if ref_match:
            return ref_match.group(1)

        return ""

    def _generate_task_hash(self, text: str, scope: str) -> str:
        """Generate deterministic task hash."""
        content = f"{text}:{scope}".encode('utf-8')
        return hashlib.sha256(content).hexdigest()[:8]


# Qwen-callable entry point
def compile_m2m(
    prose: str,
    lane: str = "A",
    wsp_refs: list[int] | None = None,
    **kwargs
) -> str:
    """
    Qwen-callable function to compile 012 prose to M2M compact format.

    This function is designed for delegation from ORCH to Qwen.

    Args:
        prose: Human-readable prompt
        lane: Target lane
        wsp_refs: WSP compliance requirements
        **kwargs: Additional M2MPrompt fields

    Returns:
        Compact M2M format string
    """
    compiler = M2MCompiler()
    m2m = compiler.compile(prose, lane=lane, wsp_refs=wsp_refs, **kwargs)
    return m2m.to_compact()


def decompile_m2m(compact: str) -> str:
    """
    Qwen-callable function to decompile M2M back to prose.

    Args:
        compact: M2M compact format string

    Returns:
        Human-readable prose
    """
    compiler = M2MCompiler()
    m2m = compiler.parse_compact(compact)
    return compiler.decompile(m2m)


if __name__ == "__main__":
    # Demo usage
    compiler = M2MCompiler()

    # Compile 012 prose
    prompt = compiler.compile(
        prose="Please analyze the authentication module and fix any security issues",
        lane="A",
        scope="modules/auth/",
        wsp_refs=[50, 71],
        outputs=["ModLog.md", "security_report.md"],
    )

    print("=== Compact Format ===")
    print(prompt.to_compact())
    print()
    print("=== YAML Format ===")
    print(prompt.to_yaml())
    print()
    print("=== Decompiled ===")
    print(compiler.decompile(prompt))
