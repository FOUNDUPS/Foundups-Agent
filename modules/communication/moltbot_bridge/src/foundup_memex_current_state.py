"""Canonical FoundUp Memex current-state adapter.

The existing FoundUp Brain assembler remains the implementation component for
backward compatibility. This module establishes the public Memex terminology:
Brain is one durable-consolidation component inside the complete FoundUp Memex.

WSP_00 / WSP_97 boundary:
- pure delegation to the verified read-only assembler;
- no Brain, Breadcrumb, roadmap, HoloIndex, queue, worker, or repository write;
- no CABR, stakeholder, delegate, or governance authority is inferred.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.foundup_brain_current_state import (
    FOUNDUP_BRAIN_VIEW_ACCEPTED,
    FOUNDUP_BRAIN_VIEW_REJECTED,
    FOUNDUP_BRAIN_VIEW_SCHEMA_VERSION,
    FoundUpBrainAssemblyResult,
    FoundUpBrainView,
    assemble_foundup_brain_current_state,
)
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    OperationalContextSnapshot,
)

FOUNDUP_MEMEX_VIEW_SCHEMA_VERSION = FOUNDUP_BRAIN_VIEW_SCHEMA_VERSION
FOUNDUP_MEMEX_VIEW_ACCEPTED = FOUNDUP_BRAIN_VIEW_ACCEPTED
FOUNDUP_MEMEX_VIEW_REJECTED = FOUNDUP_BRAIN_VIEW_REJECTED

FoundUpMemexView = FoundUpBrainView
FoundUpMemexAssemblyResult = FoundUpBrainAssemblyResult


def assemble_foundup_memex_current_state(
    *,
    foundup_id: str,
    snapshot: OperationalContextSnapshot,
    identity: Mapping[str, Any],
    roadmap_state: Mapping[str, Any] | None = None,
    verified_outcomes: Sequence[Mapping[str, Any]] = (),
    now_iso: str | None = None,
    resident_mode: bool = True,
    legacy_single_foundup_compatibility: bool = False,
    policy_foundup_scope: Sequence[str] | None = None,
) -> FoundUpMemexAssemblyResult:
    """Assemble the read-only current-state Memex view for one FoundUp.

    This compatibility-safe adapter intentionally delegates to the existing
    proven Brain assembler. It does not add a storage system or new authority.
    """

    return assemble_foundup_brain_current_state(
        foundup_id=foundup_id,
        snapshot=snapshot,
        identity=identity,
        roadmap_state=roadmap_state,
        verified_outcomes=verified_outcomes,
        now_iso=now_iso,
        resident_mode=resident_mode,
        legacy_single_foundup_compatibility=legacy_single_foundup_compatibility,
        policy_foundup_scope=policy_foundup_scope,
    )
