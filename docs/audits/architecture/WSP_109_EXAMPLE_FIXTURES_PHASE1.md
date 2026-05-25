# WSP_109_EXAMPLE_FIXTURES_PHASE1

**Worker**: 0102  
**Slice**: `WSP_109_EXAMPLE_FIXTURES_PHASE1`  
**Date**: 2026-05-25  
**Status**: REFERENCE  

---

## Purpose

This document contains concrete FoundUp intake examples for WSP 109.

Examples are separated from the canonical WSP 109 to prevent semantic drift.

WSP 109 defines the protocol. This document provides worked examples.

---

## Example 1: Shield FoundUp

### Raw Idea

"Shield - protection from medical debt, debt scams, fake collection threats, suspicious documents. User takes a picture; AI tells them what it is and what to do."

### Intake Artifacts

| Artifact | Content Summary |
|----------|-----------------|
| INTAKE_SOURCE.md | source_type: spoken_012, duplicate_status: NEW_FOUNDUP |
| OUTCOME.md | User knows if a debt/document is legitimate and what action to take |
| SOLUTION.md | AI-powered document analysis and threat classification |
| PAIN.md | Users receive threatening debt letters and don't know if they're real or scams |
| POC_SCOPE.md | Photo upload -> AI classification -> action recommendation |
| PROTOTYPE_GATE.md | Classification accuracy validated, user trust established |
| SKILLS_MAP.md | Candidates: shield_document_classifier, shield_threat_evaluator |
| FOUNDUP_MANIFEST_DRAFT.md | entity_type: foundup, tier: F0_DAE |

### Reference

- PR #717 (merged)
- `modules/foundups/shield/`

---

## Example 2: External Sleeve Pattern

### Raw Idea

"External repo FoundUp with registry representation but no monorepo source."

### Intake Artifacts

| Artifact | Content Summary |
|----------|-----------------|
| INTAKE_SOURCE.md | source_type: spoken_012, duplicate_status: NEW_FOUNDUP |
| OUTCOME.md | FoundUp visible in registry/catalog without monorepo dependency |
| SOLUTION.md | Registry entry with module_path: null pointing to external repo |
| PAIN.md | Some FoundUps have source elsewhere but need registry visibility |
| POC_SCOPE.md | Registry entry creation, catalog visibility |
| PROTOTYPE_GATE.md | Registry sync working, no source duplication |
| SKILLS_MAP.md | Candidates: external_foundup_sync, registry_null_path_handler |
| FOUNDUP_MANIFEST_DRAFT.md | entity_type: external_foundup, module_path: null |

---

## Example 3: Trust Wedge Pattern

### Raw Idea

"Free PoC builds trust before paid engagement."

### Intake Artifacts

| Artifact | Content Summary |
|----------|-----------------|
| INTAKE_SOURCE.md | source_type: spoken_012, duplicate_status: NEW_FOUNDUP |
| OUTCOME.md | User validates vendor capability before commitment |
| SOLUTION.md | Free proof-of-concept delivery as trust signal |
| PAIN.md | Buyers distrust untested vendors |
| POC_SCOPE.md | One free PoC per prospect |
| PROTOTYPE_GATE.md | PoC accepted -> paid engagement conversion |
| SKILLS_MAP.md | Candidates: trust_wedge_poc_scoper, conversion_gate_evaluator |
| FOUNDUP_MANIFEST_DRAFT.md | entity_type: foundup, tier: F0_DAE |

---

## Usage

When executing WSP 109, workers may reference these fixtures as concrete examples.

These fixtures do not override WSP 109 protocol.

WSP 109 protocol is canonical. Fixtures are illustrative.

---

## Future Fixtures

Additional FoundUp intake examples may be added to this document without modifying WSP 109.
