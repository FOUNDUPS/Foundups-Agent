# Shield

**FoundUp ID**: `shield`  
**Type**: Consumer Defense FoundUp  
**Stage**: Incubating  
**Tier**: F0_DAE  
**Status**: SPECIFIED (not implemented)  

---

## Purpose

Shield is a consumer defense FoundUp that helps individuals understand, organize, and act on legal and administrative documents they receive. It provides a **free trust wedge** through its POC phase, allowing users to experience safe document classification without commitment.

---

## Core Outcome

**User Problem**: Consumers receive legal notices, bills, contracts, and administrative documents but often lack the knowledge to understand urgency, required actions, or available defenses.

**Shield Solution**: Safe document classification, deadline extraction, and action-plan generation without storing raw documents or providing legal advice.

---

## Trust Model

### Free Trust Wedge (POC)
- Free POC proves safe capture/classification/redaction
- No payment, no membership, no wallet required
- User trust builds through demonstrated safety

### Privacy Guarantees
- Private facts stay with the user (012)
- Raw documents are NOT stored in the system
- Only safe metadata (document type, deadlines, urgency) may be extracted
- Aggregate pattern facts may be used only when safe and non-identifying

---

## Lifecycle Stages

| Stage | Description | Status |
|-------|-------------|--------|
| **IDEA** | Concept defined | CURRENT |
| **POC** | AutoCase free classification | NEXT |
| **Prototype** | Intelligence/action-plan hooks | FUTURE |
| **MVP** | Persistent 0102 defense twin | FUTURE |
| **Launch** | Public availability | FUTURE |

---

## What Shield Does NOT Do

**WSP_97 Truth Boundaries**:
- Does NOT provide legal advice
- Does NOT store raw documents
- Does NOT store PID/PII
- Does NOT implement OCR (future slice)
- Does NOT automate proxy communication
- Does NOT process payments
- Does NOT manage memberships
- Does NOT interact with blockchain/wallets

---

## Related Documents

- Manifest: `foundup_manifest.json`
- Interface: `INTERFACE.md`
- Roadmap: `ROADMAP.md`
- Registry: `modules/foundups/foundup_registry.json`

---

## Next Slice

`SHIELD_AUTOCASE_POC_PHASE1` - Implement free AutoCase document classification POC.
