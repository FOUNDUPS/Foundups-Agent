#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSP 109 Intake Packet Builder (dry-run only).

Converts unstructured chat/idea text into a populated ``FoundUpGenesisEnvelope``,
validates it through the EXISTING OpenClaw genesis gate, and returns a dry-run
result. It proves the WSP 109 handoff artifact reaches the gate. It does NOT
scaffold a monorepo module tree, enqueue a build job, or mutate any registry.

Slice: WSP109_INTAKE_PACKET_BUILDER_PHASE1
WSP:   00, 15, 22, 50, 97, 109

Hard boundary (fail closed):
    - NO import of HermesFoundUpBuilder / fam_adapter / launch_foundup /
      FoundUpJobConsumer anywhere in this module (AST-guarded by tests).
    - NO filesystem write, NO registry/catalog mutation, NO enqueue.
    - ``dry_run`` is always True; ``fam_called`` / ``hermes_called`` /
      ``registry_mutated`` are always False.

Parser strategy (Phase 1): structured ``key: value`` section headers in the idea
text, conservative defaults, and validator rejection on incomplete input. This is
deliberately NOT a free-form LLM step -- the builder only normalises structured
intake into the typed envelope; the existing genesis validator is the authority
on validity.

NAVIGATION:
    -> Uses: foundup_genesis/envelope.py (FoundUpGenesisEnvelope schema)
    -> Uses (lazy, call-time): moltbot_bridge/openclaw_foundup_orchestrator.py
       (validate_genesis_before_execution) -- the existing genesis gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .envelope import (
    AcceptanceCriterion,
    BindingState,
    FoundUpGenesisEnvelope,
    LifecycleStage,
    TruthMarker,
    TruthStateEntry,
)

# Reason strings surfaced by the genesis gate (mirrors GenesisGateReason values).
GATE_REASON_NO_ENVELOPE = "NO_ENVELOPE"
GATE_REASON_GATE_PASSED = "GATE_PASSED"

# Structured scalar keys recognised in idea text (case-insensitive).
_SCALAR_KEYS = frozenset({
    "name",
    "tagline",
    "description",
    "category",
    "foundup_id",
    "lifecycle_stage",
    "binding_state",
})

# Keys that introduce a single acceptance criterion (pipe-delimited, 4 fields).
_ACCEPTANCE_KEYS = frozenset({"acceptance", "acceptance_criterion", "criterion"})


@dataclass
class IntakePacketBuilderResult:
    """Return-value-only dry-run result. No side effect produced it."""

    envelope: Optional[Dict[str, Any]]
    gate_result: Dict[str, Any]
    gate_reason: str
    gate_passed: bool
    dry_run: bool = True
    fam_called: bool = False
    hermes_called: bool = False
    registry_mutated: bool = False
    evidence_refs: List[str] = field(default_factory=list)
    parse_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "envelope": self.envelope,
            "gate_result": self.gate_result,
            "gate_reason": self.gate_reason,
            "gate_passed": self.gate_passed,
            "dry_run": self.dry_run,
            "fam_called": self.fam_called,
            "hermes_called": self.hermes_called,
            "registry_mutated": self.registry_mutated,
            "evidence_refs": self.evidence_refs,
            "parse_notes": self.parse_notes,
        }


def _derive_foundup_id(name: str) -> str:
    """Best-effort WSP 104 id from a human name. Returns '' if underivable.

    Lowercases, maps every non ``[a-z0-9_]`` run to a single underscore, strips
    leading/trailing underscores, and prefixes ``f_`` if it would start with a
    digit. The genesis validator remains the authority: an underivable/invalid
    result is returned as-is (possibly '') so validation rejects it rather than
    this builder guessing a "valid-looking" id.
    """
    slug = re.sub(r"[^a-z0-9_]+", "_", (name or "").lower()).strip("_")
    if not slug:
        return ""
    if slug[0].isdigit():
        slug = f"f_{slug}"
    return slug[:50]


def _parse_lifecycle(value: Optional[str]) -> LifecycleStage:
    """Map a lifecycle string to a genesis-valid stage; default IDEA.

    Only IDEA/INCUBATING are representable in the envelope enum; any other value
    conservatively defaults to IDEA (genesis is always idea/incubating).
    """
    try:
        return LifecycleStage((value or "idea").strip().lower())
    except ValueError:
        return LifecycleStage.IDEA


def _parse_binding(value: Optional[str]) -> BindingState:
    """Map a binding string to a genesis-valid state; default UNBOUND."""
    try:
        return BindingState((value or "unbound").strip().lower())
    except ValueError:
        return BindingState.UNBOUND


def _parse_idea_text(text: str) -> Optional[Dict[str, Any]]:
    """Parse structured idea text into a field dict, or None if unparseable.

    Returns None for empty input OR input with no recognised structured keys --
    both route to the gate as an empty envelope (NO_ENVELOPE). Structured but
    incomplete input returns a partial dict so the validator rejects it with
    specific errors (ENVELOPE_INVALID / FOUNDUP_ID_INVALID).
    """
    text = (text or "").strip()
    if not text:
        return None

    parsed: Dict[str, Any] = {"acceptance_criteria": [], "_notes": []}
    found_any = False

    for raw in text.splitlines():
        line = raw.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()
        if not value:
            continue
        if key in _SCALAR_KEYS:
            parsed[key] = value
            found_any = True
        elif key in _ACCEPTANCE_KEYS:
            parts = [p.strip() for p in value.split("|")]
            if len(parts) == 4 and all(parts):
                parsed["acceptance_criteria"].append({
                    "observable": parts[0],
                    "method": parts[1],
                    "oracle": parts[2],
                    "pass_condition": parts[3],
                })
                found_any = True
            else:
                parsed["_notes"].append(
                    "acceptance_line_ignored: needs 4 pipe-delimited fields "
                    "(observable | method | oracle | pass_condition)"
                )

    if not found_any:
        return None
    return parsed


def _build_envelope(parsed: Dict[str, Any], source_channel: str) -> FoundUpGenesisEnvelope:
    """Assemble a typed envelope from parsed fields (conservative defaults)."""
    name = parsed.get("name", "")
    foundup_id = parsed.get("foundup_id") or _derive_foundup_id(name)

    acceptance = [
        AcceptanceCriterion.from_dict(ac)
        for ac in parsed.get("acceptance_criteria", [])
    ]
    # A single IDEA_ONLY truth entry keeps the map WSP-97 clean without claiming
    # any implementation (IDEA_ONLY requires no evidence).
    truth_map = [
        TruthStateEntry(
            feature=foundup_id or name or "foundup",
            marker=TruthMarker.IDEA_ONLY,
            evidence="",
        )
    ]

    return FoundUpGenesisEnvelope(
        foundup_id=foundup_id,
        name=name,
        tagline=parsed.get("tagline", ""),
        description=parsed.get("description", ""),
        category=parsed.get("category", "uncategorized"),
        requested_by="012",
        lifecycle_stage=_parse_lifecycle(parsed.get("lifecycle_stage")),
        binding_state=_parse_binding(parsed.get("binding_state")),
        external_repo_requested=False,
        acceptance_criteria=acceptance,
        truth_state_map=truth_map,
        created_by="0102",
        notes=f"intake_source_channel={source_channel}",
    )


def _run_genesis_gate(envelope_data: Dict[str, Any], actor_id: str) -> Any:
    """Run the EXISTING OpenClaw genesis gate (lazy import to avoid coupling).

    Returns the orchestrator's ``GenesisGateResult``. This is the only external
    call the builder makes: it neither launches, enqueues, nor mutates -- the
    orchestrator's ``validate_genesis_envelope`` is read-only validation.
    """
    from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
        validate_genesis_before_execution,
    )

    return validate_genesis_before_execution(envelope_data, actor_id)


def build_intake_packet_dry_run(
    idea_text: str,
    *,
    actor_id: str = "0102",
    source_channel: str = "reddog",
) -> IntakePacketBuilderResult:
    """Parse idea text into a genesis envelope and run it through the gate.

    Dry-run only. NEVER calls FAM, Hermes, registry, or any writer.

    Args:
        idea_text: Unstructured (but section-header structured) FoundUp idea.
        actor_id: Who is requesting intake (default 0102).
        source_channel: Where the idea came from (telemetry only).

    Returns:
        IntakePacketBuilderResult with the envelope dict (or None), the gate
        result/reason, and dry-run telemetry (fam/hermes/registry all False).
    """
    parsed = _parse_idea_text(idea_text or "")

    if not parsed:
        # Empty or unparseable -> present an empty envelope to the gate, which
        # returns NO_ENVELOPE (allowed=False) -> NOT_READY upstream.
        gate = _run_genesis_gate({}, actor_id)
        return IntakePacketBuilderResult(
            envelope=None,
            gate_result=gate.to_dict(),
            gate_reason=gate.reason.value,
            gate_passed=gate.allowed,
            evidence_refs=[],
            parse_notes=["empty_or_unparseable_idea_text"],
        )

    envelope = _build_envelope(parsed, source_channel)
    envelope_data = envelope.to_dict()
    gate = _run_genesis_gate(envelope_data, actor_id)

    evidence_refs: List[str] = []
    if envelope.foundup_id:
        evidence_refs.append(f"foundup_id:{envelope.foundup_id}")
    evidence_refs.append(f"acceptance_criteria:{len(envelope.acceptance_criteria)}")

    return IntakePacketBuilderResult(
        envelope=envelope_data,
        gate_result=gate.to_dict(),
        gate_reason=gate.reason.value,
        gate_passed=gate.allowed,
        evidence_refs=evidence_refs,
        parse_notes=list(parsed.get("_notes", [])),
    )
