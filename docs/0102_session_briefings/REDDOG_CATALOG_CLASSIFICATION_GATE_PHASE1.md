# RedDog Catalog Classification Gate - Phase 1

**Worker**: W2 — **Slice**: `REDDOG-CATALOG-CLASSIFICATION-GATE`
**Date**: 2026-04-21
**WSP References**: WSP 97 (Truth), WSP 104 (Namespace), WSP 29 (CABR Engine)

---

## WSP 97 Truthfulness Statement

> This document is an **architecture and schema specification only**. No implementation code was written. No catalog entries were modified. No manifests were created or updated. All claims about system behavior are architectural requirements, not assertions of current implementation. The RedDog classification gate does not exist yet — this spec defines what it will be.

---

## 1. Purpose

Define the RedDog Catalog Classification Gate — the advisory layer that classifies raw discoveries as FoundUp candidates before they reach the catalog validator or FAM pipeline.

**Problem solved**: p.fMALL currently has two FoundUp truth paths that don't talk to each other:

1. **Manifest path** (dynamic file discovery via `shell_core.py`) — 2 bound tenants
2. **Catalog path** (hand-edited `mall-video-catalog.json`) — 13 FoundUps

When a new signal arrives (video, community signal, agent discovery, 012 directive), there is no classification layer to determine:
- Is this a new FoundUp?
- Does it match an existing FoundUp?
- Is it non-FoundUp content?
- What evidence supports the classification?

**RedDog's role**: **classify / question / propose** — NOT declare / register / promote. RedDog is advisory until FAM or the catalog validator accepts.

**Relationship to prior specs**:
- `REDDOG_FAM_GENESIS_FLOW_SPEC_PHASE1.md` defines the RedDog → Genesis Envelope → Hermes/Claw build pipeline
- This spec sits **upstream** of that flow — it defines how RedDog decides *what* something is before producing an envelope
- The catalog truth gate (`test_catalog_foundup_truth_gate.py`, PR #421) enforces enum and binding constraints — RedDog classification feeds INTO that gate

---

## 2. RedDogCatalogClassification Schema

```python
@dataclass
class RedDogCatalogClassification:
    """RedDog's advisory classification of a raw discovery.

    RedDog classifies, questions, and proposes. It does NOT:
    - Write to the catalog
    - Create manifests
    - Promote lifecycle stages
    - Assign definitive foundup_ids

    The classification is consumed by:
    - FAM/Genesis (if new FoundUp → genesis envelope flow)
    - Catalog Validator (if existing FoundUp update)
    - 012 escalation queue (if ambiguous or conflicting)
    """

    # --- Classification verdict ---
    candidate_type: str
    # One of:
    #   "new_foundup"              — No match in catalog or manifests
    #   "existing_foundup_update"  — Matches existing catalog entry or manifest
    #   "non_foundup_content"      — Content that belongs to a FoundUp but is not itself one
    #   "ambiguous"                — Cannot classify with sufficient confidence

    confidence: float
    # 0.0–1.0. Threshold rules:
    #   >= 0.8: Auto-propose to downstream (FAM or catalog validator)
    #   0.5–0.79: Propose with advisory flag, downstream decides
    #   < 0.5: Escalate to 012 regardless of candidate_type

    # --- WSP 97 truth state ---
    wsp97_state: str
    # One of:
    #   "DISCOVERED"   — Signal received, no classification yet
    #   "CLASSIFIED"   — RedDog has assigned candidate_type + confidence
    #   "PROPOSED"     — Classification forwarded to FAM/catalog validator
    #   "ACCEPTED"     — Downstream accepted the classification
    #   "REJECTED"     — Downstream rejected (with reason)

    # --- FoundUp matching ---
    matched_foundup_id: str | None
    # Non-null when candidate_type == "existing_foundup_update"
    # Must match a foundup_id in mall-video-catalog.json OR a manifest

    proposed_foundup_id: str | None
    # Non-null when candidate_type == "new_foundup"
    # Human-readable slug (NOT hash — per regression guard in truth gate)
    # Format: lowercase, underscores, 3–40 chars
    # Example: "vote_ballots", "whack_a_magot"

    # --- Discovery source ---
    source_type: str
    # One of:
    #   "video"              — YouTube/media content detected
    #   "document"           — Architecture doc, README, spec
    #   "community_signal"   — Discord, chat, social mention
    #   "agent_discovery"    — 0102/Hermes/Claw automated discovery
    #   "012_directive"      — Direct 012 instruction

    source_ref: str
    # URI or path to the source material
    # Examples:
    #   "https://youtube.com/watch?v=abc123"
    #   "modules/foundups/voteballots/docs/VOTEBALLOTS_AI_HOOKS_ARCHITECTURE.md"
    #   "discord://foundups/general/msg-12345"
    #   "012-directive:2026-04-21T14:30:00Z"

    # --- Evidence ---
    evidence: list[str]
    # Why RedDog thinks this classification is correct
    # Each entry is a short statement with truth-state suffix:
    # Examples:
    #   "Source handle @MOVE2JAPAN matches catalog entry move2japan [VERIFIED_FACT]"
    #   "Title contains 'GotJunk' keyword [HIGH_CONFIDENCE_INFERENCE]"
    #   "No catalog entry with similar name found [LOW_CONFIDENCE_INFERENCE]"

    conflicts: list[str]
    # What doesn't match or raises questions
    # Examples:
    #   "category 'gaming' not in VALID_CATEGORIES"
    #   "lifecycle_stage 'beta' not in VALID_STAGES"
    #   "routing_prefix /f/gotjunk conflicts with existing /f/gotjunk_001"

    # --- Recommended action ---
    recommended_action: str
    # One of:
    #   "add_to_catalog"       — New FoundUp, add entry to mall-video-catalog.json
    #   "update_existing"      — Update fields on matched catalog entry
    #   "propose_new_foundup"  — Route to FAM/Genesis envelope flow
    #   "escalate_012"         — Requires 012 decision
    #   "reject"               — Not a FoundUp, not actionable

    requires_012: bool
    # True when:
    #   - confidence < 0.5
    #   - conflicts is non-empty
    #   - candidate_type == "ambiguous"
    #   - recommended_action == "escalate_012"
    #   - proposed_foundup_id would create a new FoundUp (012 approval required for FoundUp creation)

    # --- Metadata ---
    classification_id: str
    # Deterministic: sha256(source_type:source_ref:timestamp)[:16]

    classified_at: str
    # ISO 8601 timestamp

    classified_by: str
    # Agent identifier, e.g., "reddog_concierge_v1"
```

---

## 3. Decision Rules

### 3.1 Rule Matrix

| # | Condition | candidate_type | recommended_action | requires_012 |
|---|-----------|----------------|--------------------|--------------|
| R1 | Source matches existing `foundup_id` in catalog | `existing_foundup_update` | `update_existing` | Only if conflicts |
| R2 | Source matches manifest `foundup_id` but NOT in catalog | `existing_foundup_update` | `add_to_catalog` | Yes (catalog gap = binding decision) |
| R3 | Source has FoundUp markers but no match anywhere | `new_foundup` | `propose_new_foundup` | Yes (new FoundUp = always 012) |
| R4 | Source is content for an existing FoundUp (e.g., new video) | `non_foundup_content` | `update_existing` | No |
| R5 | Multiple partial matches, can't disambiguate | `ambiguous` | `escalate_012` | Yes |
| R6 | Source has no FoundUp markers | `non_foundup_content` | `reject` | No |

### 3.2 Rule Evaluation Order

```
1. Exact ID match against catalog      → R1 or R4
2. Exact ID match against manifests    → R2
3. Fuzzy name/handle match             → R1 (high conf) or R5 (low conf)
4. FoundUp marker detection            → R3
5. No markers detected                 → R6
```

### 3.3 FoundUp Marker Detection

RedDog looks for these signals to determine if a source represents a FoundUp:

| Marker | Weight | Example |
|--------|--------|---------|
| `foundup_manifest.json` exists in module directory | 1.0 | `modules/foundups/kosei/foundup_manifest.json` |
| Source handle matches catalog `source_handle` | 0.9 | `@MOVE2JAPAN` matches move2japan entry |
| Module directory exists under `modules/foundups/` | 0.8 | `modules/foundups/voteballots/` |
| Architecture doc references FoundUp lifecycle | 0.7 | Doc mentions `lifecycle_stage`, `tier`, `launch_readiness` |
| 012 directive explicitly names as FoundUp | 1.0 | "voteballots is a FoundUp" |
| YouTube channel with `source_type: youtube_channel` | 0.6 | New channel fitting catalog pattern |
| Multiple related videos/content around one theme | 0.5 | Enough signal for a catalog tile |

### 3.4 Confidence Calculation

```python
def calculate_confidence(markers: list[FoundUpMarker]) -> float:
    """Combine marker weights into overall confidence.

    Uses max-weight-with-decay model:
    - Start with highest weight marker
    - Each additional marker adds diminishing contribution
    - Never exceeds 1.0
    """
    if not markers:
        return 0.0

    weights = sorted([m.weight for m in markers], reverse=True)
    confidence = weights[0]
    for w in weights[1:]:
        confidence += w * (1.0 - confidence) * 0.5  # Diminishing returns
    return min(confidence, 1.0)
```

### 3.5 Confidence Thresholds

| Range | Behavior | Rationale |
|-------|----------|-----------|
| `>= 0.8` | Auto-propose to downstream | High certainty, multiple strong markers |
| `0.5–0.79` | Propose with advisory flag | Moderate certainty, downstream makes final call |
| `< 0.5` | Escalate to 012 | Insufficient evidence, human judgment required |

---

## 4. Classification Pipeline

### 4.1 End-to-End Flow

```
                    RedDog Catalog Classification Pipeline

    Raw Signal
    (video / doc / community / agent / 012)
        |
        v
+------------------------+
|  1. Signal Intake      |  RedDog receives raw discovery
|     - Normalize source |
|     - Extract metadata |
+------------------------+
        |
        v
+------------------------+
|  2. Catalog Lookup     |  Check against existing truth
|     - mall-video-      |
|       catalog.json     |
|     - foundup_manifest |
|       .json files      |
|     - shell_core.py    |
|       enums            |
+------------------------+
        |
        v
+------------------------+
|  3. Marker Detection   |  Scan for FoundUp markers
|     - ID matching      |
|     - Handle matching  |
|     - Module directory |
|     - Architecture doc |
|     - 012 directive    |
+------------------------+
        |
        v
+------------------------+
|  4. Classification     |  Apply decision rules (R1–R6)
|     - candidate_type   |
|     - confidence       |
|     - evidence[]       |
|     - conflicts[]      |
+------------------------+
        |
        v
+------------------------+
|  5. Enum Validation    |  Validate against truth gate
|     - VALID_CATEGORIES |  (shell_core.py)
|     - VALID_STAGES     |
|     - VALID_READINESS  |
|     - VALID_TIERS      |
+------------------------+
        |
        v
+------------------------+
|  6. WSP 97 Truth       |  Assign truth state
|     State Assignment   |
|     - DISCOVERED →     |
|       CLASSIFIED       |
+------------------------+
        |
        v
+------- requires_012? --------+
|                               |
v (Yes)                    v (No, conf >= 0.5)
+------------------+   +--------------------+
| 012 Escalation   |   | Downstream Router  |
| Queue            |   |                    |
+------------------+   +--------------------+
        |                       |
        v                  +----+----+
   012 decides             |         |
        |                  v         v
        v           +---------+ +-----------+
   Manual          | FAM /   | | Catalog   |
   classification  | Genesis | | Validator |
                   +---------+ +-----------+
                        |           |
                        v           v
                   Genesis     Catalog
                   Envelope    Update
                   Flow        (validated by
                   (per REDDOG_  truth gate
                   FAM_GENESIS_  tests)
                   FLOW_SPEC)
```

### 4.2 Pipeline Boundary Rules

| Boundary | Rule | Enforcement |
|----------|------|-------------|
| RedDog → Catalog | RedDog NEVER writes to `mall-video-catalog.json` | Code review + test |
| RedDog → Manifest | RedDog NEVER creates `foundup_manifest.json` | Code review + test |
| RedDog → FAM | RedDog proposes, FAM decides | FAM validates envelope before accepting |
| Catalog Validator → Catalog | Only path for catalog writes | `test_catalog_foundup_truth_gate.py` enforces |
| 012 → Override | 012 can override any classification | `requires_012` flag + audit trail |

### 4.3 Integration with Existing Truth Gate

The catalog truth gate (PR #421, `test_catalog_foundup_truth_gate.py`) validates:
- Every catalog entry has `foundup_id`, `category`, `lifecycle_stage`, `launch_readiness`, `tier`
- All enum values match `shell_core.py` canonical frozensets
- Bound tenants have matching manifests
- No partial binding (route without namespace or vice versa)

RedDog classification targets this gate:
- When RedDog proposes `add_to_catalog`, the proposed entry MUST pass all 25 truth gate tests
- When RedDog proposes `update_existing`, the updated fields MUST maintain truth gate compliance
- Enum validation in step 5 of the pipeline pre-validates against the same `VALID_CATEGORIES`, `VALID_STAGES`, `VALID_READINESS`, `VALID_TIERS` frozensets

---

## 5. WSP 97 Truth States for Classification

### 5.1 Classification-Specific Truth States

| State | Definition | Transition From | Transition To |
|-------|------------|-----------------|---------------|
| `DISCOVERED` | Raw signal received, no analysis yet | (entry point) | `CLASSIFIED` |
| `CLASSIFIED` | RedDog assigned candidate_type + confidence | `DISCOVERED` | `PROPOSED` |
| `PROPOSED` | Classification forwarded to FAM or catalog validator | `CLASSIFIED` | `ACCEPTED` or `REJECTED` |
| `ACCEPTED` | Downstream validated and acted on classification | `PROPOSED` | (terminal) |
| `REJECTED` | Downstream rejected classification (with reason) | `PROPOSED` | `DISCOVERED` (re-classify) |

### 5.2 State Machine

```
DISCOVERED ──classify──> CLASSIFIED ──propose──> PROPOSED ──accept──> ACCEPTED
                                                    |
                                                    └──reject──> REJECTED
                                                                    |
                                                                    └──re-discover──> DISCOVERED
```

### 5.3 State Persistence

| State | Stored Where | Retention |
|-------|-------------|-----------|
| `DISCOVERED` | In-memory (RedDog session) | Session lifetime |
| `CLASSIFIED` | FAM event bus (`reddog_classification_created`) | Permanent |
| `PROPOSED` | FAM event bus (`reddog_classification_proposed`) | Permanent |
| `ACCEPTED` | FAM event bus + catalog/manifest mutation | Permanent |
| `REJECTED` | FAM event bus (`reddog_classification_rejected`) | Permanent |

---

## 6. FAM Event Types for Classification

| Event | When Emitted | Payload |
|-------|-------------|---------|
| `reddog_classification_created` | RedDog produces a classification | Full `RedDogCatalogClassification` object |
| `reddog_classification_proposed` | Classification forwarded downstream | classification_id, target (FAM or catalog_validator) |
| `reddog_classification_accepted` | Downstream accepts | classification_id, accepted_by, resulting_action |
| `reddog_classification_rejected` | Downstream rejects | classification_id, rejected_by, reason |
| `reddog_classification_escalated` | Sent to 012 queue | classification_id, escalation_reason |

---

## 7. Catalog Validator Boundary

### 7.1 What the Catalog Validator Does (Future Implementation)

The catalog validator is the **authority** that accepts or rejects catalog mutations. It sits between RedDog (advisory) and the catalog file (truth).

| Responsibility | Input | Output |
|----------------|-------|--------|
| Validate proposed entry against truth gate | `RedDogCatalogClassification` with `add_to_catalog` | Accept/reject with reasons |
| Validate proposed update against truth gate | `RedDogCatalogClassification` with `update_existing` | Accept/reject with reasons |
| Enforce enum constraints | Proposed values | Pass/fail against `shell_core.py` frozensets |
| Enforce binding rules | routing_prefix + data_namespace | Must be both or neither |
| Write to catalog | Accepted classification | Mutated `mall-video-catalog.json` |

### 7.2 What the Catalog Validator Does NOT Do

| Forbidden | Reason |
|-----------|--------|
| Classify signals | That's RedDog's job |
| Create manifests | That's Hermes/Claw's job via genesis envelope |
| Promote lifecycle stages | That's FAM's job with evidence gates |
| Override 012 decisions | 012 is always final authority |

### 7.3 Current State (WSP 97: SPECIFIED_NOT_IMPLEMENTED)

The catalog validator does not exist as code. Currently:
- Catalog is hand-edited by 012/0102
- Truth gate tests (`test_catalog_foundup_truth_gate.py`) validate after the fact
- No automated write path exists

The classification gate spec defines the contract the future validator must implement.

---

## 8. Worked Examples

### 8.1 Example A: New YouTube Video for Existing FoundUp

**Signal**: New video uploaded to `@MOVE2JAPAN` channel

```json
{
  "candidate_type": "non_foundup_content",
  "confidence": 0.95,
  "wsp97_state": "CLASSIFIED",
  "matched_foundup_id": "move2japan",
  "proposed_foundup_id": null,
  "source_type": "video",
  "source_ref": "https://youtube.com/watch?v=newvideo123",
  "evidence": [
    "Channel handle @MOVE2JAPAN matches catalog source_handle [VERIFIED_FACT]",
    "foundup_id 'move2japan' exists in catalog [VERIFIED_FACT]"
  ],
  "conflicts": [],
  "recommended_action": "update_existing",
  "requires_012": false,
  "classification_id": "a1b2c3d4e5f67890",
  "classified_at": "2026-04-21T15:00:00Z",
  "classified_by": "reddog_concierge_v1"
}
```

**Outcome**: Content added to move2japan's video array. No new FoundUp created.

### 8.2 Example B: New FoundUp from 012 Directive

**Signal**: 012 says "whack-a-magot is a FoundUp"

```json
{
  "candidate_type": "new_foundup",
  "confidence": 1.0,
  "wsp97_state": "CLASSIFIED",
  "matched_foundup_id": null,
  "proposed_foundup_id": "whack_a_magot",
  "source_type": "012_directive",
  "source_ref": "012-directive:2026-04-21T10:00:00Z",
  "evidence": [
    "012 explicitly declared as FoundUp [VERIFIED_FACT]",
    "No existing catalog entry with this ID [VERIFIED_FACT]",
    "Module directory does not exist yet [VERIFIED_FACT]"
  ],
  "conflicts": [],
  "recommended_action": "propose_new_foundup",
  "requires_012": true,
  "classification_id": "b2c3d4e5f6789012",
  "classified_at": "2026-04-21T10:05:00Z",
  "classified_by": "reddog_concierge_v1"
}
```

**Outcome**: Routes to FAM/Genesis envelope flow. 012 confirms. New catalog entry created after genesis flow completes.

### 8.3 Example C: Manifest Exists but No Catalog Entry

**Signal**: Agent discovers `modules/foundups/voteballots/foundup_manifest.json` but no catalog entry

```json
{
  "candidate_type": "existing_foundup_update",
  "confidence": 0.85,
  "wsp97_state": "CLASSIFIED",
  "matched_foundup_id": null,
  "proposed_foundup_id": "voteballots",
  "source_type": "agent_discovery",
  "source_ref": "modules/foundups/voteballots/foundup_manifest.json",
  "evidence": [
    "foundup_manifest.json exists with valid schema [VERIFIED_FACT]",
    "No catalog entry with foundup_id 'voteballots' [VERIFIED_FACT]",
    "Manifest has routing_prefix and data_namespace (bound tenant) [VERIFIED_FACT]"
  ],
  "conflicts": [
    "Manifest exists but catalog entry missing — catalog gap"
  ],
  "recommended_action": "add_to_catalog",
  "requires_012": true,
  "classification_id": "c3d4e5f678901234",
  "classified_at": "2026-04-21T16:00:00Z",
  "classified_by": "reddog_concierge_v1"
}
```

**Outcome**: Routes to catalog validator. 012 approves. Catalog entry created as bound tenant.

### 8.4 Example D: Ambiguous Multi-Match

**Signal**: Community mention of "GotJunk" — could be the existing gotjunk_001 FoundUp or a new junk removal service

```json
{
  "candidate_type": "ambiguous",
  "confidence": 0.35,
  "wsp97_state": "CLASSIFIED",
  "matched_foundup_id": null,
  "proposed_foundup_id": null,
  "source_type": "community_signal",
  "source_ref": "discord://foundups/general/msg-99999",
  "evidence": [
    "Term 'GotJunk' partially matches gotjunk_001 [LOW_CONFIDENCE_INFERENCE]",
    "Context suggests external service, not pAVS FoundUp [LOW_CONFIDENCE_INFERENCE]"
  ],
  "conflicts": [
    "Partial name match with gotjunk_001 but context unclear",
    "Could be reference to existing FoundUp or unrelated mention"
  ],
  "recommended_action": "escalate_012",
  "requires_012": true,
  "classification_id": "d4e5f67890123456",
  "classified_at": "2026-04-21T17:00:00Z",
  "classified_by": "reddog_concierge_v1"
}
```

**Outcome**: Escalated to 012. 012 clarifies. Re-classified as `non_foundup_content` (external reference).

---

## 9. Implementation Roadmap

### Phase 1: REDDOG-CATALOG1 — Schema + Tests

**Deliverables**:
- `RedDogCatalogClassification` dataclass in a new module
- Unit tests for schema validation (all fields, enum values, constraint checks)
- Test that `proposed_foundup_id` format matches truth gate expectations (slug, not hash)
- Test that enum values pre-validate against `shell_core.py` frozensets

**Acceptance criteria**:
- Schema can be serialized to/from JSON
- All enum constraints enforced at construction
- `classification_id` is deterministic (sha256-based)
- Truth gate tests still pass (no regressions)

### Phase 2: REDDOG-CATALOG2 — Decision Rules Engine

**Deliverables**:
- Rule engine implementing R1–R6 from Section 3.1
- Catalog lookup integration (read `mall-video-catalog.json`)
- Manifest lookup integration (scan `modules/foundups/*/foundup_manifest.json`)
- Marker detection with confidence calculation
- Integration tests with real catalog data

**Acceptance criteria**:
- Each of the 13 current catalog entries, when fed as input, returns `existing_foundup_update` with confidence >= 0.9
- A fabricated new signal returns `new_foundup` with appropriate confidence
- Enum violations are caught and added to `conflicts[]`

### Phase 3: REDDOG-CATALOG3 — Pipeline Integration

**Deliverables**:
- FAM event emission for classification lifecycle
- Catalog validator stub (accepts/rejects based on truth gate)
- 012 escalation queue (FAM event with `requires_012: true`)
- Integration with RedDog concierge (`red-dog-concierge.js` or backend equivalent)

**Acceptance criteria**:
- End-to-end flow: signal → classification → proposal → accept/reject
- All FAM events emitted with correct payloads
- 012 escalation works for low-confidence and conflicting classifications
- No direct catalog writes from RedDog (boundary enforced)

---

## 10. Current System Truth Assessment

| Component | Truth State | Evidence |
|-----------|-------------|----------|
| RedDogCatalogClassification schema | `SPECIFIED_NOT_IMPLEMENTED` | This spec document |
| Decision rules (R1–R6) | `SPECIFIED_NOT_IMPLEMENTED` | Section 3 of this spec |
| Catalog truth gate (test_catalog_foundup_truth_gate.py) | `IMPLEMENTED_IN_TESTS` | PR #421 merged, 25 tests passing |
| shell_core.py VALID_CATEGORIES | `IMPLEMENTED_IN_TESTS` | PR #421, used by truth gate |
| Catalog validator (write path) | `SPECIFIED_NOT_IMPLEMENTED` | Section 7 of this spec |
| FAM classification events | `SPECIFIED_NOT_IMPLEMENTED` | Section 6 of this spec |
| RedDog concierge (current) | `IMPLEMENTED_IN_CATALOG` | `red-dog-concierge.js` — contextual help only, no classification |
| FAM Genesis Envelope flow | `SPECIFIED_NOT_IMPLEMENTED` | `REDDOG_FAM_GENESIS_FLOW_SPEC_PHASE1.md` |
| 012 escalation queue | `SPECIFIED_NOT_IMPLEMENTED` | Section 5 of this spec |
| Confidence calculation algorithm | `SPECIFIED_NOT_IMPLEMENTED` | Section 3.4 of this spec |

---

## 11. Open Questions (for 012 Decision)

| # | Question | Options | Impact |
|---|----------|---------|--------|
| 1 | Where does classification run? | Browser-side (concierge JS) vs Backend (Python/OpenClaw) | JS = fast, limited; Python = full catalog/manifest access |
| 2 | Should RedDog auto-classify on catalog refresh? | Yes (proactive) vs No (on-demand only) | Proactive catches drift but costs compute |
| 3 | Is 012 approval required for ALL new FoundUps? | Yes (always) vs No (high-confidence auto-accept) | Controls FoundUp creation rate |
| 4 | Should classification history be persisted? | FAM events only vs Dedicated classification store | Affects auditability |
| 5 | What is the minimum confidence for auto-proposal? | 0.8 (conservative) vs 0.6 (permissive) | False positive rate |

---

## 12. Related Documents

| Document | Location | Relationship |
|----------|----------|--------------|
| RedDog FAM Genesis Flow | `docs/0102_session_briefings/REDDOG_FAM_GENESIS_FLOW_SPEC_PHASE1.md` | Downstream: classification feeds genesis envelope |
| Catalog Truth Gate Tests | `modules/foundups/pfmall/tests/test_catalog_foundup_truth_gate.py` | Validation target: classifications must pass these tests |
| Shell Core | `modules/foundups/pfmall/shell_core.py` | Enum source: VALID_CATEGORIES, VALID_STAGES, VALID_READINESS, VALID_TIERS |
| Mall Video Catalog | `public/member/mall-video-catalog.json` | Truth source: 13 FoundUp entries |
| Red Dog Concierge | `public/member/js/red-dog-concierge.js` | Current RedDog: contextual help only |
| Manifest Schema | `modules/foundups/docs/PFMALL_FOUNDUP_MANIFEST_SCHEMA.md` | Manifest structure for bound tenants |
| WSP 97 | `WSP_knowledge/src/WSP_97_System_Execution_Prompting_Protocol.md` | Truth-state framework |
| WSP 104 | `WSP_knowledge/src/WSP_104_FoundUp_Namespace_Guardrail.md` | Namespace constraints for bound tenants |

---

## 13. Acceptance Criteria for This Spec

| Criterion | Status |
|-----------|--------|
| RedDogCatalogClassification schema fully defined | PASS |
| All fields documented with types, constraints, and examples | PASS |
| Decision rules (R1–R6) defined with clear conditions | PASS |
| Pipeline flow documented end-to-end | PASS |
| WSP 97 truth states for classification lifecycle defined | PASS |
| FAM event types for classification documented | PASS |
| Catalog validator boundary clearly drawn | PASS |
| Integration with existing truth gate (PR #421) specified | PASS |
| Worked examples cover all candidate_types | PASS |
| Implementation roadmap with 3 phases defined | PASS |
| No implementation code written | PASS |
| No catalog or manifest modifications | PASS |

---

*Specification Author: 0102 (W2)*
*Slice: REDDOG-CATALOG-CLASSIFICATION-GATE*
*Date: 2026-04-21*
*Status: ARCHITECTURE + SCHEMA SPEC ONLY — No implementation*
