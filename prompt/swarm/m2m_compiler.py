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

    def to_compact(self) -> str:
        """Serialize to 012 compact format (single line)."""
        parts = [
            f"L:{self.lane.value}",
            f"S:{self.scope}",
            f"M:{self.mode.value}",
            f"T:{self.task_hash}",
        ]

        if self.wsp_refs:
            parts.append(f"R:{self.wsp_refs}")

        if self.invariants:
            inv_str = ",".join(f"{k}:{v}" for k, v in self.invariants.items())
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
            invariants=invariants or {},
            outputs=outputs or [],
            fail_conditions=fail_conditions or [],
            sender=sender,
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

        # Action based on mode
        if m2m.mode == Mode.EXEC:
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
        for match in re.finditer(r'([LSMTRIOFC]):(\[[^\]]+\]|\{[^}]+\}|\S+)', compact):
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
