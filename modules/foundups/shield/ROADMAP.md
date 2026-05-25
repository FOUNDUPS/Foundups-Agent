# Shield Roadmap

**Module**: `modules/foundups/shield`  
**Created**: 2026-05-25  
**Last Updated**: 2026-05-25  

---

## Vision

Shield empowers individuals to understand and respond to legal and administrative documents without requiring legal expertise or expensive professional services. Through staged trust-building, Shield demonstrates value before asking for commitment.

---

## Stage Progression

### Stage 1: AutoCase POC
**Slice**: `SHIELD_AUTOCASE_POC_PHASE1`  
**Status**: NEXT  
**Objective**: Free trust wedge through document classification

**Deliverables**:
- [ ] Document type classification (legal notice, bill, contract, etc.)
- [ ] Urgency assessment (immediate, soon, routine, informational)
- [ ] Deadline extraction (dates only, no content storage)
- [ ] Generic action suggestions (not legal advice)
- [ ] Clear disclaimers in every response

**Constraints**:
- NO raw document storage
- NO PID/PII retention
- NO legal advice claims
- NO payment/membership gates

**Success Criteria**:
- Classification accuracy > 80% on test corpus
- User trust demonstrated (return usage)
- Zero privacy violations

---

### Stage 2: Prototype Intelligence
**Slice**: `SHIELD_INTELLIGENCE_PROTOTYPE_PHASE1`  
**Status**: FUTURE (after Stage 1 validated)  
**Objective**: Action-plan generation hooks

**Deliverables**:
- [ ] Action plan generation from classification
- [ ] Timeline suggestions
- [ ] Public resource linking (legal aid, government sites)
- [ ] Integration with 0102 intelligence layer

**Locked Prototype Hooks**:
```python
# Hooks defined but not implemented until Stage 2
class PrototypeHooks:
    def generate_action_plan(self, classification: AutoCaseResponse) -> ActionPlanResponse:
        raise NotImplementedError("Stage 2 prototype")
    
    def suggest_resources(self, document_type: str, jurisdiction: str) -> List[Resource]:
        raise NotImplementedError("Stage 2 prototype")
```

---

### Stage 3: MVP Defense Twin
**Slice**: `SHIELD_DEFENSE_TWIN_MVP_PHASE1`  
**Status**: FUTURE (after Stage 2 validated)  
**Objective**: Persistent 0102 defense companion

**Deliverables**:
- [ ] Twin session management
- [ ] Case tracking (metadata only)
- [ ] Deadline monitoring and reminders
- [ ] Multi-case aggregation
- [ ] User preference learning

**Privacy Architecture**:
- Private facts stay with user
- Twin stores only safe metadata
- Aggregate patterns used only when non-identifying

---

### Stage 4: Launch
**Slice**: `SHIELD_PUBLIC_LAUNCH_PHASE1`  
**Status**: FUTURE (after MVP validated)  
**Objective**: Public availability

**Deliverables**:
- [ ] shield.foundups.com activation
- [ ] Public landing page
- [ ] p.fMALL catalog entry (listed)
- [ ] Portfolio inclusion
- [ ] Token economics activation (if approved)

---

## Safe Metadata Schema

The following metadata is SAFE to extract and store:

```json
{
  "document_type": "string (enum)",
  "urgency_level": "string (enum)",
  "deadlines": [
    {
      "date": "ISO date",
      "action_type": "string (enum)",
      "days_remaining": "integer"
    }
  ],
  "jurisdiction_hint": "string (state/country code only)",
  "classification_confidence": "float 0-1",
  "timestamp": "ISO datetime"
}
```

**PROHIBITED from storage**:
- Raw document content
- Names, addresses, SSN, account numbers
- Case numbers with identifying context
- Any PID/PII

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| HoloIndex retrieval | Available | For knowledge lookup |
| OpenClaw routing | Available | For intent classification |
| OCR pipeline | NOT IMPLEMENTED | Future Stage 1 requirement |
| LLM classification | Available | Via existing infrastructure |

---

## Version History

| Date | Change |
|------|--------|
| 2026-05-25 | Initial roadmap created (Stage 1 defined) |
