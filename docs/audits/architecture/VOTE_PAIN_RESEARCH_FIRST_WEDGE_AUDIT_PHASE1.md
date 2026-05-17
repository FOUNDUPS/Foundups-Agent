# VOTE Pain Research First Wedge Audit - Phase 1

**Status**: DOCS_ONLY | PAIN_RESEARCH_ONLY  
**Worker**: W9  
**Date**: 2026-05-14  
**WSP Compliance**: WSP_00, WSP_97, WSP_87, WSP_15, WSP_50  

---

## Safety Labels

```
DOCS_ONLY
PAIN_RESEARCH_ONLY
NO_IMPLEMENTATION
NO_TARGETED_PERSUASION
NO_MICROTARGETING
NO_GOVERNANCE_EXECUTION
NO_CABR_READY
NO_PAYOUT_READY
NO_DAO_ACTIVATION
```

---

## 1. Executive Summary

This audit researches and ranks pain points VOTE (VoteBallots FoundUp) could address, identifies the smallest high-value first wedge, and defines a scoped PoC problem statement. The goal is scope discipline: prevent VOTE from expanding into an unscoped political/governance blob.

**Key Finding**: The strongest first wedge is **"012 asks naturally about a candidate or attack and receives a simple evidence-backed answer showing what is known, inferred, unresolved, and where the public trail stops."**

This wedge is:
- User-initiated (no push, no targeting)
- Evidence-backed (sources cited)
- WSP 97 compliant (explicit confidence labels)
- Public interest (transparency, not persuasion)
- Minimal viable scope (single Q&A, not full investigation pipeline)

---

## 2. HoloIndex Assessment

### 2.1 Search Results Summary

| Search Query | Files Found | Relevant Hits |
|--------------|-------------|---------------|
| VOTE FoundUp vote candidate governance | 34 | `voteballots/` module, shell_core.py, consensus docs |
| candidate funding PAC donor evidence | 10 | `voteballots/` AI hooks arch, FEC API refs |
| support signals issue signals | 8 | trade contracts, pqn_alignment skills |
| 3V verification validation valuation | 40 | CABR engine (WSP 29), pavs_mcp, trade module |
| FoundUp shell Mall conversational routing | 78 | pfmall routing/discovery model, shell contracts |

### 2.2 Existing Capabilities Found

| Capability | Location | Status | Reusability |
|------------|----------|--------|-------------|
| VoteBallots FoundUp shell | `modules/foundups/voteballots/` | SPECIFIED_NOT_IMPLEMENTED | High - architecture exists |
| AI Hooks Architecture | `docs/VOTEBALLOTS_AI_HOOKS_ARCHITECTURE.md` | Complete spec (1307 lines) | High - ready for impl |
| WSP 97 Confidence Scoring | `WSP_framework/src/WSP_97*` | Implemented | High - core system |
| 3V CABR Engine | `WSP_knowledge/src/WSP_29_CABR_Engine.md` | Framework ready | Medium - needs oracle binding |
| pfMALL Shell Router | `modules/foundups/pfmall/shell_core.py` | Phase 1 implemented | High - conversational entry |
| pfMALL Discovery Model | `PFMALL_ROUTING_DISCOVERY_MODEL.md` | Phase 1 tile field | Medium - search planned Phase 2 |
| Web Search MCP | `mcp_manager` (DuckDuckGo, Serper) | Operational | High - immediate use |

### 2.3 Missing Capabilities

| Capability | Gap | Priority for First Wedge |
|------------|-----|--------------------------|
| FEC API integration | No wrapper exists | P1 - required for funding data |
| Entity resolution (candidate lookup) | Spec only, no impl | P1 - required for name->ID |
| Funding trace graph | Spec only, no impl | P2 - later phase |
| Attack ad classification | Spec only, no impl | P2 - later phase |
| Real-time ad ingestion | No implementation | P3 - much later |

---

## 3. Ranked Pain Map

| Rank | Pain Point | User Value | Implementation Cost | Risk Level | First Wedge Fit |
|------|------------|------------|---------------------|------------|-----------------|
| 1 | **Candidate funding transparency** | HIGH - direct answer to "who funds X?" | MEDIUM - FEC API + confidence labels | LOW | **YES** |
| 2 | Attack-source transparency | HIGH - "who paid for this attack ad?" | MEDIUM - Meta/Google Ad APIs | LOW | Partial |
| 3 | Hidden funding / PAC motive opacity | HIGH - dark money awareness | HIGH - multi-hop tracing | MEDIUM | No |
| 4 | Evidence-to-values decision support | MEDIUM - personal alignment check | HIGH - inference engine | MEDIUM | No |
| 5 | Discovery of useful channels/voices | MEDIUM - find trusted sources | MEDIUM - HoloIndex | LOW | No |
| 6 | Narrative coordination detection | MEDIUM - spot coordinated messaging | HIGH - ML + timeline | HIGH | No |
| 7 | Channel/influencer usefulness scoring | LOW - derivative value | MEDIUM | MEDIUM | No |
| 8 | Earliest visible spread / provenance | LOW - niche interest | HIGH - timeline reconstruction | MEDIUM | No |
| 9 | Support signals / governance hooks | LOW - DAO mechanics | MEDIUM | LOW | No |

### 3.1 Pain Ranking Rationale

**Rank 1 (Candidate Funding Transparency)** wins because:
- Most common user question: "Who funds [Candidate]?"
- Data source exists: FEC API is public, documented, rate-limited but accessible
- WSP 97 applies cleanly: verified_fact (FEC filing) vs inference vs unknown
- Trail termination is explicit: "Dark money estimate" with confidence bounds
- No persuasion required: just answer the question with evidence

**Rank 2-3 deferred** because they require:
- Multi-API integration (Meta, Google, FEC cross-reference)
- Complex inference chains (pass-through detection, shell committee analysis)
- Higher risk of false positives or defamation

---

## 4. 012/Operator Role Hypotheses

### 4.1 Primary Role: Question Initiator

012 (operator) is the user who asks the question. VOTE is reactive, not proactive.

```
012: "Who funds [Candidate Name]?"
VOTE: [Funding report with confidence labels]
```

**CRITICAL BOUNDARY**: VOTE does not:
- Recommend who to vote for
- Push unsolicited candidate information
- Score candidates on "goodness" or "alignment with your values"
- Target messages based on user profile

### 4.2 Secondary Role: Challenge Submitter

012 can dispute claims in a report:

```
012: "Your report says X but I have evidence of Y"
VOTE: [Challenge recorded, flagged for review]
```

### 4.3 Tertiary Role: Feedback Provider

012 provides implicit feedback through:
- Query patterns (which candidates are asked about)
- Challenge frequency (which claims are disputed)
- No explicit ratings or thumbs up/down to avoid gaming

---

## 5. Strongest First Wedge

### 5.1 Definition

**First Wedge**: Candidate Funding Quick Answer

**User Story**: As a voter, I ask "Who funds [Candidate Name]?" and receive a 3-line answer showing top funding sources with explicit confidence labels.

### 5.2 Scope Boundary

**IN SCOPE**:
- Text query input (candidate name + optional hints: state, office, year)
- FEC API lookup (federal candidates)
- Top 5 funding sources by amount
- WSP 97 confidence labels on each claim
- Source URLs for verification
- Trail termination marker (where evidence stops)

**OUT OF SCOPE** (Phase 2+):
- Voice/speech input
- State-level candidate data
- PAC/Super PAC tracing beyond direct contributions
- Attack ad analysis
- Dark money estimation
- Funding graph visualization
- Challenge/correction mechanism
- Historical comparison ("vs last cycle")

### 5.3 Example Output

```
WHO FUNDS: Alexandria Ocasio-Cortez (NY-14, D)

TOP SOURCES [VERIFIED]: 
1. Individual contributions < $200: $X.XM (65%)
2. ActBlue (earmarked): $X.XM (20%)
3. Labor unions (PAC): $X.XK (5%)
[Source: FEC Filing FEC-xxxxxxx, accessed 2026-05-14]

CONFIDENCE: All amounts from FEC filings (verified_fact).
UNKNOWN: Super PAC independent expenditures not traced in this query.
TRAIL STOPS AT: 501(c)(4) dark money not disclosed by law.
```

---

## 6. Exact PoC Problem Statement

**Problem**: A user asks naturally about a candidate (e.g., "who funds AOC?") and currently receives no structured, evidence-backed answer within the FoundUps ecosystem.

**PoC Goal**: Given a candidate name query, return a 3-line quick answer with:
1. Top funding sources (from FEC API)
2. Confidence labels per WSP 97
3. Explicit trail termination marker

**Input**: `{ "query": "who funds [candidate name]", "hints": { "state?", "office?", "cycle?" } }`

**Output**:
```json
{
  "candidate": { "name": "...", "fec_id": "...", "office": "..." },
  "quick_answer": "...",
  "top_sources": [ { "name": "...", "amount": N, "confidence": "verified_fact" } ],
  "trail_ends_at": "...",
  "sources": [ { "url": "...", "accessed": "..." } ]
}
```

---

## 7. Exact PoC Success Condition

| Criterion | Threshold | Measurement |
|-----------|-----------|-------------|
| Entity resolution accuracy | >= 90% on 20 test candidates | Manual verification |
| FEC API success rate | >= 95% of queries | API response tracking |
| Confidence label accuracy | 100% verified_fact claims from FEC | Audit sample |
| Trail termination present | 100% of responses | Schema validation |
| Response latency | < 10s | Timer |
| No hallucinated funding sources | 0 | Adversarial test |
| No persuasion language | 0 | Manual review |

---

## 8. Certainty/Probability Matrix

| Claim Type | Certainty | Evidence Source | Example |
|------------|-----------|-----------------|---------|
| Direct FEC contribution | HIGH (0.95) | FEC filing | "Individual X donated $2800" |
| PAC contribution | HIGH (0.90) | FEC filing | "IBEW PAC gave $5000" |
| Super PAC independent expenditure | MEDIUM (0.75) | FEC IE filings | "SolarPAC spent $50K opposing" |
| Dark money estimate | LOW (0.40) | Inference from 990s | "501c4 spent ~$200K (estimated)" |
| Policy alignment inference | LOW (0.35) | Public statements | "Donor supports X policy" |
| Foreign funding allegation | REQUIRES_HUMAN | Cannot verify without investigation | BLOCKED |

### 8.1 Confidence Label Mapping

```python
def map_to_wsp97_label(certainty: float, source_type: str) -> str:
    if source_type in ['fec_filing', 'state_filing']:
        return 'verified_fact'
    elif certainty >= 0.70:
        return 'high_confidence_inference'
    elif certainty >= 0.40:
        return 'low_confidence_inference'
    else:
        return 'unknown'
```

---

## 9. Evidence-Source Matrix

| Data Need | Public Source | API Available | Rate Limit | Cost |
|-----------|---------------|---------------|------------|------|
| Federal candidate ID | FEC.gov | Yes (REST) | 1000/hr | Free |
| Federal contributions | FEC.gov | Yes (REST) | 1000/hr | Free |
| Federal expenditures | FEC.gov | Yes (REST) | 1000/hr | Free |
| Super PAC IE filings | FEC.gov | Yes (REST) | 1000/hr | Free |
| State contributions | Varies by state | Partial | Varies | Free-$$ |
| 501(c)(4) 990s | IRS.gov / ProPublica | Yes | Varies | Free |
| Political ad archive | Meta Ad Library | Yes (REST) | Varies | Free |
| Political ad archive | Google Ads Transparency | Yes (REST) | Varies | Free |
| News mentions | DuckDuckGo/Serper | Yes (MCP) | Varies | Free/Paid |

### 9.1 First Wedge Data Sources

**Required for PoC**:
1. FEC Candidate API - entity resolution
2. FEC Committee API - contributions
3. FEC Schedule A API - itemized receipts

**Deferred to Phase 2+**:
- State APIs
- Meta/Google Ad APIs
- ProPublica 990 API

---

## 10. PoC Exclusions

| Feature | Reason for Exclusion | Phase Target |
|---------|----------------------|--------------|
| Speech-to-text input | Complexity, not core value | Phase 2 |
| Attack ad analysis | Multi-API, classification needed | Phase 2 |
| Funding graph visualization | UI complexity | Phase 2 |
| Dark money estimation | Multi-hop tracing, inference risk | Phase 3 |
| Challenge/correction | Moderation infrastructure | Phase 3 |
| State-level candidates | 50+ API integrations | Phase 4 |
| Historical comparison | Data volume, UI | Phase 4 |
| Real-time ad ingestion | Pipeline infrastructure | Phase 5 |

---

## 11. Prototype-Only Features

These features are PoC scope but NOT production-ready:

| Feature | PoC Implementation | Production Requirement |
|---------|-------------------|------------------------|
| FEC API calls | Direct REST, no caching | Cache layer, rate limit queue |
| Entity resolution | Exact match + fuzzy | ML disambiguation |
| Error handling | Fail-fast with error message | Graceful degradation |
| Output format | JSON | Multi-format (JSON, text, graph) |
| Audit logging | Console | Structured telemetry (WSP 91) |

---

## 12. Later Governance-Only Features

These features are VOTE roadmap but require governance infrastructure (CABR, DAO):

| Feature | Governance Dependency | Earliest Phase |
|---------|----------------------|----------------|
| Challenge arbitration | CABR V2 proof | Phase 4 |
| Report accuracy bounties | Token system | Phase 5 |
| Source credibility scoring | Validator consensus | Phase 5 |
| Community fact-checking | DAO participation | Phase 6 |
| Algorithmic transparency reports | Regulatory compliance | Phase 7 |

---

## 13. Scope Risks and Contradictions

### 13.1 Identified Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Scope creep into persuasion | HIGH | Strict output schema, no recommendations |
| False confidence labels | HIGH | Automated tests, adversarial suite |
| Defamation from inference | HIGH | Human review queue for sensitive claims |
| API rate limiting | MEDIUM | Queue + cache + backoff |
| Entity resolution ambiguity | MEDIUM | Disambiguation prompt, not guess |
| Dark money overstatement | MEDIUM | Always label as estimate + range |

### 13.2 Contradictions Detected

| Contradiction | Resolution |
|---------------|------------|
| "Expose dark money" vs "Only verified facts" | Dark money is labeled as `unknown` with estimated range, never stated as fact |
| "Comprehensive transparency" vs "Minimal PoC" | PoC answers one question well; comprehensive is Phase N |
| "User-initiated" vs "Discovery surface" | Mall discovery shows VOTE exists; user must click/ask to get info |

---

## 14. Political Safety Boundary

### 14.1 VOTE Must

1. **Be user-initiated**: No push notifications about candidates
2. **Provide evidence-backed answers**: Every claim has a source or is labeled unknown
3. **Separate fact from inference**: WSP 97 confidence labels are mandatory
4. **Show trail termination**: Where evidence stops is always stated
5. **Be neutral on candidates**: No "better" or "worse" language
6. **Flag dangerous claims**: Foreign funding, criminal allegations go to human review

### 14.2 VOTE Must NOT

1. Recommend who to vote for
2. Score candidates on political alignment
3. Microtarget users based on profile
4. Push information the user did not ask for
5. State dark money amounts as if verified
6. Conflate "pro-Israel donor" with "foreign-funded"
7. Make criminal accusations without court records
8. Use persuasion language ("you should consider", "alarming", "concerning")

---

## 15. WSP_15 Next-Slice Recommendation

### 15.1 Recommended Next Slice

**Slice**: `VOTE_FEC_ENTITY_RESOLUTION_POC_PHASE2`

**Scope**:
1. Implement `entity-resolution` hook from `VOTEBALLOTS_AI_HOOKS_ARCHITECTURE.md`
2. Wrap FEC Candidate Search API
3. Return candidate list with disambiguation if ambiguous
4. Unit tests with 20 known candidates

**Inputs**:
- Raw name string
- Optional hints (state, office, cycle)

**Outputs**:
- Resolved candidate(s) with FEC ID
- Disambiguation question if ambiguous
- Confidence score

**Exit Criteria**:
- 90% accuracy on 20-candidate test set
- No hallucinated candidates
- Disambiguation works for common names

### 15.2 Subsequent Slices

| Order | Slice | Depends On |
|-------|-------|------------|
| Phase 2 | FEC Entity Resolution | This audit |
| Phase 3 | FEC Contribution Fetch | Phase 2 |
| Phase 4 | Confidence Scoring Integration | Phase 3 |
| Phase 5 | Quick Answer Generation | Phase 4 |
| Phase 6 | Shell Integration (pfMALL query) | Phase 5 |
| Phase 7 | Trail Termination Markers | Phase 5 |
| Phase 8 | Adversarial Test Suite | Phase 5 |
| Phase 9 | Production Hardening | Phase 8 |

---

## 16. WSP_97 Verdict

**Verdict**: COMPLIANT

This audit document:
- Follows pain research scope (no implementation)
- Defines explicit PoC problem statement
- Specifies success conditions
- Ranks pains with rationale
- Identifies strongest first wedge
- Documents exclusions and later phases
- Maintains political safety boundary
- Provides next-slice recommendation per WSP 15

---

## 17. Commit Metadata

**Branch**: `docs/vote-pain-research-first-wedge-audit-phase1`  
**Files Changed**: This file only  
**Status**: STAGED (not pushed per W9 instructions)  
**Next Worker**: W10 (audit review)

---

*0102 pArtifact: Pain research and scope discipline for VOTE first wedge. User asks, system answers with evidence and confidence labels. No persuasion, no targeting, no governance until infrastructure exists.*
