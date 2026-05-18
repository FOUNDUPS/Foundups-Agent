# Move2Japan FoundUp Role Audit - Phase 1

**Slice**: `M2JRA-W9B`
**Worker**: W9 sub-worker B (audit/spec)
**Date**: 2026-05-18
**WSP References**: WSP 00 (Zen State), WSP 97 (Truth Boundaries), WSP 87 (HoloIndex), WSP 15 (Token Policy), WSP 50 (Pre-Action Verification)

---

## WSP 97 Constraints

```yaml
DOCS_ONLY: true
AUDIT_ONLY: true
NO_IMPLEMENTATION: true
NO_MODULE_DELETION: true
NO_MANIFEST_CREATION: true
NO_TOKEN_ASSIGNMENT: true
TOKEN_DEFERRED_WHERE_UNKNOWN: true
NO_RUNTIME_CHANGE: true
NO_CABR_READY: true
NO_PAYOUT_READY: true
NO_DAO_ACTIVATION: true
```

---

## 1. Executive Summary

Move2Japan is a **purpose-built YouTube monitor and live-stream access solution** that provides a stakeholder intake funnel for relocation services to Japan. It operates as an **access service** for FoundUps, not a standalone FoundUp itself, and MUST NOT be deleted, renamed, or deprecated.

**Classification**: ACCESS_SERVICE (YT monitor / stakeholder funnel)
**Deletion Risk**: CRITICAL - Loss of implemented stakeholder DB, base camp state machine, and livechat integration
**Token Assignment**: TOKEN_DEFERRED - Not applicable for access service layer

---

## 2. HoloIndex vs Grep Preflight Comparison

| Metric | HoloIndex | Grep |
|--------|-----------|------|
| Query | `move2japan stakeholder YouTube monitor` | `move2japan\|m2j_handler\|Move2Japan` |
| Results returned | 8 hits (0 code, 3 WSP, 5 docs) | 250 files (limit reached) |
| move2japan module files | 1 (INTERFACE.md) | All 21 files in module |
| Livechat integration | 0 files | 12+ files |
| YouTube tests | 0 files | 40+ files |
| Coverage quality | LOW (missed primary code) | HIGH (comprehensive) |
| Precision | LOW (WSP noise) | MODERATE |

**Verdict**: HoloIndex semantic search FAILED to locate primary implementation files. Grep was required for comprehensive code inventory. This indicates HoloIndex indexing gap for foundups module.

---

## 3. Code Inventory

### 3.1 Module Structure

```
modules/foundups/move2japan/
├── README.md              (191 lines) - FoundUp overview, mountain model
├── INTERFACE.md           (134 lines) - WSP 11 contract, state model
├── ROADMAP.md             (118 lines) - POC/Prototype/MVP layering
├── ModLog.md              (32 lines) - V0.1.0 inception
├── module.json            (34 lines) - Module config
├── src/
│   ├── __init__.py
│   └── m2j_stakeholder_db.py  (176 lines) - SQLite stakeholder persistence
├── tests/
│   ├── __init__.py
│   ├── README.md
│   ├── test_m2j_handler.py
│   └── test_m2j_stakeholder_db.py  (79 lines) - Full DB test coverage
├── memory/
│   └── README.md
└── docs/
    ├── 01_OVERVIEW.md
    ├── 02_SYSTEM_ARCHITECTURE.md    (140 lines) - Core modules, state model
    ├── 03_PREMIUM_MODEL.md
    ├── 04_POC_PROTOTYPE_MVP.md
    ├── 05_BASECAMP_ZERO_SPEC.md     (369 lines) - Complete BC0 dialogue spec
    ├── 06_BLINDSPOTS.md
    └── 07_FUNNEL_ARCHITECTURE.md
```

**Total**: 21 files, ~1,500 lines of documentation + code

### 3.2 Livechat Integration Files

| File | Lines | Purpose |
|------|-------|---------|
| `modules/communication/livechat/src/m2j_handler.py` | 374 | BC0 state machine implementation |
| `modules/communication/livechat/skillz/bc0_m2j_intake.json` | 93 | BC0 intake skill config |
| `modules/communication/livechat/skillz/bc1_m2j_passport.json` | 17 | BC1 passport skill (stub) |
| `modules/communication/livechat/skillz/bc2_m2j_pathway.json` | 24 | BC2 pathway skill (stub) |
| `modules/communication/livechat/skillz/persona_move2japan.json` | 22 | M2J persona config |

**Total**: 530+ lines of integration code

### 3.3 Message Processor Integration

`modules/communication/livechat/src/message_processor.py` references move2japan at:
- Line 50-54: Import Move2JapanHandler
- Line 387: Priority 3.4 command check
- Line 700: Handle M2J commands
- Lines 1186-1202: Command detection
- Lines 1396-1410: Delegation to M2J handler

---

## 4. Stakeholder DB / Access Logic Analysis

### 4.1 Database Schema

```sql
CREATE TABLE IF NOT EXISTS m2j_stakeholders (
    stakeholder_id  TEXT PRIMARY KEY,      -- YouTube channel ID
    chat_handle     TEXT,                   -- YouTube username
    urgency_level   TEXT DEFAULT 'unknown', -- explorer/planner/serious/imminent/urgent
    passport_status TEXT DEFAULT 'unknown', -- yes/no/expired/in_progress/unknown
    current_stage   TEXT DEFAULT 'BC0',     -- Base camp stage
    timeline_estimate TEXT DEFAULT 'unknown',
    intent_source   TEXT DEFAULT 'youtube_chat',
    bc0_state       TEXT DEFAULT 'BC0.1',   -- Conversation state (BC0.1-BC0.6)
    move_reason     TEXT DEFAULT '',
    language_level  TEXT DEFAULT '',
    target_region   TEXT DEFAULT '',
    first_seen      TEXT,
    last_seen       TEXT,
    notes           TEXT DEFAULT ''
);
```

**Location**: `modules/foundups/move2japan/memory/m2j_stakeholders.db`

### 4.2 Public API (M2JStakeholderDB)

| Method | Purpose |
|--------|---------|
| `get_stakeholder(id)` | Retrieve by YouTube channel ID |
| `create_stakeholder(id, handle, source)` | Create new record |
| `update_stakeholder(id, updates)` | Update fields, auto-bump last_seen |
| `get_or_create(id, handle, source)` | Upsert pattern |
| `get_stats()` | Aggregate analytics (total, by_stage, by_urgency) |

### 4.3 State Machine (BC0)

| State | Name | Description |
|-------|------|-------------|
| BC0.1 | intent_captured | Trigger detected |
| BC0.2 | timeframe_requested | Agent asks urgency |
| BC0.3 | timeframe_classified | Urgency classified |
| BC0.4 | passport_requested | Agent asks passport |
| BC0.5 | passport_classified | Passport status known |
| BC0.6 | route_decision | Final routing |

---

## 5. Base Camp Model

### 5.1 Mountain Metaphor

Move2Japan implements a **guided ascent model** where stakeholders progress through base camps:

| BC | Name | Purpose |
|----|------|---------|
| BC0 | Intent Capture | Triage, urgency, passport gate |
| BC1 | Passport Readiness | Passport acquisition guidance |
| BC2 | Migration Pathway | Work/student/spouse/entrepreneur/remote/retiree |
| BC3 | Economic Viability | Job, savings, income, sponsorship |
| BC4 | Location Fit | Tokyo/Osaka/Fukuoka/countryside |
| BC5 | Housing Pathway | Rental/share house/akiya |
| BC6 | Paperwork Execution | Visa docs, forms, timelines |
| BC7 | Landing Settlement | Bank, phone, insurance, taxes |

### 5.2 Implementation Status

| BC | Status | Code Location |
|----|--------|---------------|
| BC0 | IMPLEMENTED | `m2j_handler.py`, `bc0_m2j_intake.json` |
| BC1 | STUB | `bc1_m2j_passport.json` |
| BC2 | STUB | `bc2_m2j_pathway.json` |
| BC3-7 | NOT_STARTED | Specified in docs |

---

## 6. YouTube Monitor Relationship

### 6.1 Trigger Commands

- `!move2japan` - Primary trigger
- `!m2j` - Short alias
- `!japan` - Alternative alias

### 6.2 Integration Points

| Component | Integration |
|-----------|-------------|
| `message_processor.py` | Priority 3.4 command routing |
| `Move2JapanHandler` | BC0 state machine |
| `M2JStakeholderDB` | SQLite persistence |
| `persona_move2japan.json` | Response persona config |
| `bc0_m2j_intake.json` | Skill templates and routing matrix |

### 6.3 Channel Environment Variables

```python
# From message_processor.py lines 88-99
MOVE2JAPAN_CHANNEL_ID  # Environment variable for M2J bot channel
```

---

## 7. FoundUps Access/Funnel Relationship

### 7.1 Dual-Surface Architecture

| Domain | Type | Purpose |
|--------|------|---------|
| `movetojapan.info` | Public funnel | Newsletter, low-friction capture |
| `movetojapan.foundups.com` | Stakeholder PWA | Roadmap, dashboard, premium tiers |

### 7.2 Funnel Flow

```
YouTube Live Chat → BC0 (intent + urgency + passport)
    → movetojapan.info (newsletter)
    → movetojapan.foundups.com (PWA signup)
    → Roadmap progression → Premium tiers → Relocation execution
```

### 7.3 Routing Matrix

| Timeframe | Passport | Route |
|-----------|----------|-------|
| exploring | no | passport-first + newsletter |
| exploring | yes | discovery later |
| 1-2 years | no | passport-first + nurture |
| 1-2 years | yes | pathway discovery queue |
| 12 months | no | passport-first + stronger CTA |
| 12 months | yes | next skill |
| 6 months | no | passport-first urgent |
| 6 months | yes | fast-track next skill |
| ASAP | no | urgent passport-first + reality framing |
| ASAP | yes | fast-track + PWA CTA |

---

## 8. Classification Analysis

### 8.1 Is Move2Japan a FoundUp?

**Evidence FOR FoundUp status:**
- Located in `modules/foundups/`
- Has `module.json` with `"type": "foundup"`
- Documented as "Move2Japan FoundUp"
- Has stakeholder model (not customer model)
- Planned premium tiers and revenue model

**Evidence AGAINST FoundUp status:**
- No `foundup_manifest.json` (manifest-bearing FoundUps have one)
- No token assignment
- No CABR hooks
- Serves as intake funnel for other services
- Primary value is YT monitor + stakeholder capture

### 8.2 Is Move2Japan a Platform Service?

**Evidence FOR platform service:**
- Provides livechat integration used by YT monitor
- Has reusable skillz patterns (BC0-BC7)
- Stakeholder DB could serve multiple FoundUps

**Evidence AGAINST platform service:**
- Specific to Japan relocation domain
- Not referenced by other FoundUps
- Domain-specific persona and routing

### 8.3 Is Move2Japan an Access Service?

**Evidence FOR access service:**
- YouTube monitor capability (primary function)
- Stakeholder intake funnel
- Routes to movetojapan.info / movetojapan.foundups.com
- Stage-gated progression model
- Soft conversion architecture

**Verdict**: ACCESS_SERVICE is the correct classification. Move2Japan provides:
1. YT live-stream access (livechat monitoring)
2. Stakeholder intake (BC0 state machine)
3. Funnel routing (newsletter + PWA)
4. Relocation guidance (base camp progression)

---

## 9. Risks of Deletion

### 9.1 Code Loss Impact

| Component | Lines | Impact |
|-----------|-------|--------|
| `m2j_stakeholder_db.py` | 176 | SQLite persistence layer LOST |
| `m2j_handler.py` | 374 | BC0 state machine LOST |
| BC0 skillz | 93 | Intake routing LOST |
| Module docs | ~800 | 012 architecture vision LOST |
| Tests | 79+ | Test coverage LOST |

**Total**: ~1,500+ lines of implemented code and documentation

### 9.2 Integration Breakage

| File | Lines Affected | Failure Mode |
|------|----------------|--------------|
| `message_processor.py` | 6 integration points | Import errors, dead code |
| Livechat skillz | 5 JSON files | Orphaned skill definitions |
| Environment vars | MOVE2JAPAN_CHANNEL_ID | Missing config |

### 9.3 Stakeholder Data Risk

Existing stakeholder records in `m2j_stakeholders.db` would be orphaned. Historical intake data would be lost.

---

## 10. Recommended Classification

```yaml
entity_type: ACCESS_SERVICE
classification: youtube_monitor_stakeholder_funnel
domain: foundups
parent_platform: pfmall
relationship_to_foundups: intake_funnel

token_status: TOKEN_DEFERRED  # Not applicable for access service
manifest_status: NONE         # Access services don't need manifests
cabr_status: NOT_APPLICABLE   # No CABR hooks for access services

registry_representation:
  type: ACCESS_SERVICE
  subtype: youtube_monitor
  surfaces:
    - youtube_livechat
    - movetojapan.info
    - movetojapan.foundups.com
  stakeholder_db: true
  state_machine: BC0_implemented
```

---

## 11. Comparison with Other Entities

| Entity | Type | Manifest | Token | CABR | Move2Japan Similar? |
|--------|------|----------|-------|------|---------------------|
| gotjunk_001 | FoundUp | YES | JUNK | YES | NO - has manifest |
| kosei | FoundUp | YES | KOSEI | YES | NO - has manifest |
| voteballots | FoundUp | YES | VOTE | YES | NO - has manifest |
| pfmall | PLATFORM | NO | N/A | N/A | PARTIAL - platform layer |
| agent_market | INFRA | NO | N/A | N/A | NO - infrastructure |
| simulator | TOOL | NO | N/A | N/A | NO - economic tool |
| move2japan | ACCESS_SERVICE | NO | DEFERRED | N/A | N/A |

---

## 12. WSP 97 Verdict

```yaml
DOCS_ONLY: PASS
AUDIT_ONLY: PASS
NO_IMPLEMENTATION: PASS
NO_MODULE_DELETION: PASS - Move2Japan NOT deleted
NO_MANIFEST_CREATION: PASS - No manifest created
NO_TOKEN_ASSIGNMENT: PASS - Token deferred
TOKEN_DEFERRED_WHERE_UNKNOWN: PASS
NO_RUNTIME_CHANGE: PASS
NO_CABR_READY: PASS
NO_PAYOUT_READY: PASS
NO_DAO_ACTIVATION: PASS

OVERALL: COMPLIANT
```

---

## 13. Findings Summary

1. **Move2Japan is an ACCESS_SERVICE**, not a FoundUp or platform layer
2. **1,500+ lines of implemented code** including SQLite stakeholder DB and BC0 state machine
3. **Active livechat integration** at message_processor.py Priority 3.4
4. **BC0 fully implemented**, BC1-BC7 stubbed/specified
5. **Dual-surface funnel** to movetojapan.info and movetojapan.foundups.com
6. **HoloIndex coverage gap** - failed to locate primary implementation files
7. **Deletion would break** message_processor.py and orphan stakeholder data

---

## 14. Next Slice Recommendation

**Slice**: `MOVE2JAPAN_MANIFEST_OR_SERVICE_CLASSIFICATION_PHASE1`

**Scope**:
1. Determine if move2japan should have a service manifest (not FoundUp manifest)
2. Define service manifest schema for ACCESS_SERVICE type
3. Integrate into typed registry from FCISRA audit
4. Document relationship to pfmall platform layer
5. Clarify token policy for access services

**Constraints**:
```yaml
DOCS_ONLY: true
SCHEMA_DESIGN_ONLY: true
NO_IMPLEMENTATION: true
NO_MANIFEST_CREATION: true  # Schema only, no actual manifest
```

---

## Appendix A: File Reference Table

| File Path | Type | Lines |
|-----------|------|-------|
| `modules/foundups/move2japan/README.md` | doc | 191 |
| `modules/foundups/move2japan/INTERFACE.md` | spec | 134 |
| `modules/foundups/move2japan/ROADMAP.md` | doc | 118 |
| `modules/foundups/move2japan/ModLog.md` | log | 32 |
| `modules/foundups/move2japan/module.json` | config | 34 |
| `modules/foundups/move2japan/src/m2j_stakeholder_db.py` | code | 176 |
| `modules/foundups/move2japan/tests/test_m2j_stakeholder_db.py` | test | 79 |
| `modules/foundups/move2japan/docs/02_SYSTEM_ARCHITECTURE.md` | spec | 140 |
| `modules/foundups/move2japan/docs/05_BASECAMP_ZERO_SPEC.md` | spec | 369 |
| `modules/communication/livechat/src/m2j_handler.py` | code | 374 |
| `modules/communication/livechat/skillz/bc0_m2j_intake.json` | config | 93 |
| `modules/communication/livechat/skillz/bc1_m2j_passport.json` | config | 17 |
| `modules/communication/livechat/skillz/bc2_m2j_pathway.json` | config | 24 |
| `modules/communication/livechat/skillz/persona_move2japan.json` | config | 22 |
| `modules/communication/livechat/src/message_processor.py` | code | 1400+ |

---

*Audit completed by W9B under WSP 97 constraints. Move2Japan preserved as ACCESS_SERVICE.*
