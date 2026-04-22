---
name: foundup_genesis_intake
description: RedDog intake capability for new FoundUp ideation
version: 1.0_prototype
author: 0102
created: 2026-04-23
agents: [qwen]
primary_agent: qwen
intent_type: INTAKE
promotion_state: prototype
pattern_fidelity_threshold: 0.90
category: workflow
evals: []
trigger:
  event: 012_foundup_request
---
# FoundUp Genesis Intake — RedDog Capability

## Overview

AI Overseer capability for validating and creating FoundUpGenesisEnvelope
artifacts when 012 requests a new FoundUp.

**Status**: `SPECIFIED` — Schema and validator implemented, intake flow Phase 2
**Location**: `modules/ai_intelligence/ai_overseer/src/foundup_genesis/`

## Purpose

When 012 says "Add a new FoundUp for X", 0102 invokes this capability to:

1. **Recall** — Search HoloIndex for similar patterns, existing FoundUps, prior art
2. **Classify** — Determine category, lifecycle stage, binding state
3. **Validate** — Check WSP 97 truth claims, acceptance criteria format
4. **Create** — Generate validated FoundUpGenesisEnvelope artifact
5. **Gate** — Only valid envelopes proceed to scaffold

## Invocation

```
012: "Add a new FoundUp for X"
  → 0102: invoke foundup_genesis_intake
  → AI Overseer: create and validate envelope
  → Output: modules/foundups/{id}/foundup_genesis.json
```

## Envelope Schema

```python
@dataclass
class FoundUpGenesisEnvelope:
    # Identity
    foundup_id: str          # WSP 104 format: lowercase, 3-50 chars
    name: str                # Human-readable name
    tagline: str             # One-line description
    description: str         # Full description
    category: str            # Domain category
    
    # State (constrained at genesis)
    lifecycle_stage: LifecycleStage  # IDEA or INCUBATING only
    binding_state: BindingState      # UNBOUND or DISCOVERABLE_ONLY
    external_repo_requested: bool    # Must be False at genesis
    
    # Acceptance criteria (required)
    acceptance_criteria: List[AcceptanceCriterion]
    
    # Truth state (WSP 97)
    truth_state_map: List[TruthStateEntry]
    
    # HoloIndex recall
    holo_recall_results: List[Dict]
    prior_art: List[str]
```

## Acceptance Criterion Format

Every acceptance criterion must have four fields:

```python
@dataclass
class AcceptanceCriterion:
    observable: str      # What can be observed when met
    method: str          # How to observe it
    oracle: str          # What determines pass/fail
    pass_condition: str  # Concrete condition that must be true
```

**Example**:
```json
{
  "observable": "User can list an item for sale",
  "method": "UI test: create listing flow",
  "oracle": "Listing appears in user's active listings",
  "pass_condition": "listing_id exists AND status=active"
}
```

## WSP 97 Truth Markers

Valid markers at genesis:

| Marker | Meaning |
|--------|---------|
| `IDEA_ONLY` | Concept described, no spec |
| `SPECIFIED` | Spec written, no code |
| `FUTURE_PHASE` | Planned, not started |

Invalid at genesis (require evidence):

| Marker | Requires |
|--------|----------|
| `IMPLEMENTED` | Code path |
| `IMPLEMENTED_IN_TESTS` | Test file path |
| `PARTIAL` | Code path + scope description |

## Validation Rules

The validator enforces:

1. **foundup_id format** — WSP 104 (lowercase, 3-50 chars, starts with letter)
2. **foundup_id not reserved** — Not infrastructure (openclaw, wre, etc.)
3. **lifecycle_stage** — IDEA or INCUBATING only
4. **binding_state** — UNBOUND or DISCOVERABLE_ONLY only
5. **external_repo_requested** — Must be False
6. **acceptance_criteria** — All four fields present
7. **truth_state_map** — No implementation claims without evidence
8. **required fields** — name, tagline, description non-empty

## Output Artifact

Validated envelope saved to:
```
modules/foundups/{foundup_id}/foundup_genesis.json
```

Or session briefing if scaffold not yet created:
```
docs/0102_session_briefings/{SLICE}_GENESIS_ENVELOPE.md
```

## What Happens Next

After valid envelope:

```
Genesis Envelope (validated)
  → Scaffold creation (separate slice)
  → Manifest generation
  → pfMALL catalog entry (discoverable_only)
  → Hermes/Claw build plan (if approved)
```

**Not at genesis**:
- No code implementation
- No external repo creation
- No pfMALL "ready" binding
- No agent route activation

## Dependencies

- `modules/ai_intelligence/ai_overseer/src/foundup_genesis/envelope.py`
- `modules/ai_intelligence/ai_overseer/src/foundup_genesis/validator.py`
- HoloIndex MCP for pattern recall

## WSP Compliance

- **WSP 97**: Implementation Truth — truth_state_map enforced
- **WSP 104**: Namespace Protocol — foundup_id validation
- **WSP 49**: Module Structure — scaffold follows standard
- **WSP 3**: Domain Organization — correct placement
