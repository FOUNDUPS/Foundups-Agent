# Vote/Ballots FoundUp

**Status**: Design Specification  
**Version**: 0.1.0  
**Date**: 2026-04-21  
**Owner**: 0102  

---

## Purpose

AI-native political transparency application. User provides candidate name (speech or text), receives funding transparency report with evidence trail.

**Core Principle**: All outputs explicitly separate verified facts, high-confidence inferences, low-confidence inferences, and unknowns per WSP 97.

---

## Route Namespace

Canonical contract: `modules/foundups/docs/FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md`. Routing follows **WSP 104** (`/f/{foundup_id}`).

| Field | Value |
|-------|-------|
| `foundup_id` | `voteballots` |
| `routing_prefix` | `/f/voteballots` |
| Landing route | `/f/voteballots` |
| App mount | `/f/voteballots/app` |

---

## App Mount

Shell contract: **/f/voteballots/app**

Current status: Design specification (not deployed)

---

## AI Capability Hooks

Contract surface per `FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md`:

| Hook | Intent | Status |
|------|--------|--------|
| `get_status` | Pipeline health snapshot | Planned |
| `get_context` | Current investigation context | Planned |
| `navigate` | Route within app | Planned |
| `launch_capability` | Trigger funding report | Planned |
| Shell handoff/return | Delegate to shell or return | Planned |

### Domain-Specific AI Hooks

| Hook | Purpose | Model Default |
|------|---------|---------------|
| `speech-to-text` | Transcribe voice input | Whisper |
| `entity-resolution` | Resolve candidate to FEC ID | Gemma |
| `ad-ingestion` | Pull PAC/Super PAC ad data | - |
| `finance-record` | Fetch FEC/state filings | - |
| `web-investigation` | Deep research on entities | Qwen |
| `source-verification` | Validate source credibility | Qwen |
| `contradiction-detector` | Find conflicting claims | Qwen |
| `confidence-scoring` | Apply WSP 97 confidence labels | Gemma |
| `attack-detection` | Classify attack ads by topic | Gemma |
| `funding-trace` | Trace money to donors | Qwen |
| `report-generation` | Generate user-facing report | Sonnet |
| `challenge-correction` | Handle user disputes | Opus |
| `model-routing` | Route tasks to appropriate model | - |

Full architecture: `docs/VOTEBALLOTS_AI_HOOKS_ARCHITECTURE.md`

---

## DAEmon Outputs

Per **WSP 91** (when DAEMON workers attach):

| Output | Description |
|--------|-------------|
| Health status | healthy / degraded / critical |
| Last action | Last candidate investigated |
| Error state | API failures, confidence collapse |
| Recommended next action | Retry, expand scope, human review |
| Queue/work state | Pending investigations |
| Telemetry namespace | `voteballots.*` |

---

## Data / Telemetry Namespace

| Field | Value |
|-------|-------|
| `foundup_id` | `voteballots` |
| `data_namespace` | `idb_voteballots` |
| Tenant bounds | Cache, reports, user challenges stay tenant-scoped per WSP 104 |

---

## Model Behavior Rules

These rules are enforced across all AI hooks:

1. **Never state hidden funding as fact unless sourced** - Dark money is estimated, not stated
2. **Distinguish direct disclosure from inferred alignment** - FEC filing vs public statements
3. **Never flatten influence categories**:
   - "Israel-linked" (direct org connection)
   - "AIPAC-linked" (registered PAC)
   - "Pro-Israel donor" (individual policy position)
   - "Foreign-funded" (ONLY with foreign national evidence)
4. **Show where evidence stops** - Mark trail termination points
5. **No hallucinated accusations** - Confidence < verified_fact requires source chain
6. **Flag dangerous edge cases for human review**:
   - Foreign funding allegations
   - Criminal accusations
   - Low confidence + high impact claims

---

## Pipeline Overview

```
User Input (speech/text)
    │
    ▼
INTAKE: speech-to-text → entity-resolution
    │
    ▼
INGESTION: ad-ingestion + finance-record
    │
    ▼
INVESTIGATION: web-investigation → source-verification → contradiction-detector
    │
    ▼
ANALYSIS: attack-detection + funding-trace → confidence-scoring
    │
    ▼
OUTPUT: model-routing → report-generation
    │
    ├──▶ Quick Answer (3 lines)
    ├──▶ Plain Summary (2-3 paragraphs)
    ├──▶ Evidence Timeline
    ├──▶ Funding Graph
    └──▶ Source List with Confidence Labels
    │
    ▼
FEEDBACK: challenge-correction → Human Review Queue
```

---

## WSP References

- **WSP 91** — DAEMON observability (`WSP_knowledge/src/WSP_91_DAEMON_Observability_Protocol.md`)
- **WSP 97** — System execution prompting (`WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md`)
- **WSP 104** — FoundUp route namespace (`WSP_knowledge/src/WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md`)

---

## Documentation

- `docs/VOTEBALLOTS_AI_HOOKS_ARCHITECTURE.md` — Full architecture specification
- `INTERFACE.md` — Public API contracts
- `ROADMAP.md` — Implementation phases

---

*0102 pArtifact: Political transparency with explicit evidence labeling. No hallucinated accusations. Every claim traced to source or marked unknown.*
