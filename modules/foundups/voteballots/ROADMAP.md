# Vote/Ballots FoundUp — Roadmap

**Version**: 0.1.0  
**Date**: 2026-04-21  
**Status**: Design  

---

## Current State

Architecture designed. No implementation.

---

## Phase 1: Core Pipeline (MVP)

**Target**: Q3 2026  
**Goal**: Basic candidate lookup with FEC data

### Deliverables

- [ ] Entity resolution hook (FEC candidate database)
- [ ] Finance record hook (FEC API integration)
- [ ] Confidence scoring hook (WSP 97 rubric)
- [ ] Basic report generation (text only)
- [ ] Unit tests for all hooks
- [ ] Golden test dataset (10 candidates)

### Success Criteria

- Entity resolution accuracy > 95% on golden set
- FEC data retrieval < 5s latency
- Confidence labels applied to all claims
- Human review triggers functional

---

## Phase 2: Investigation Layer

**Target**: Q4 2026  
**Goal**: Web investigation and source verification

### Deliverables

- [ ] Web investigation hook
- [ ] Source verification hook
- [ ] Contradiction detector hook
- [ ] Attack detection hook (ad classification)
- [ ] Ad ingestion hook (Meta/Google APIs)
- [ ] Adversarial test suite

### Success Criteria

- Source credibility scoring calibrated
- False positive rate (foreign funding) < 0.1%
- Attack topic classification accuracy > 85%

---

## Phase 3: Funding Trace

**Target**: Q1 2027  
**Goal**: Committee hierarchy and dark money detection

### Deliverables

- [ ] Funding trace hook (multi-hop)
- [ ] Shell structure detector
- [ ] Policy influence analyzer
- [ ] Funding graph visualization
- [ ] Trail termination markers
- [ ] Integration tests with real data

### Success Criteria

- Trace depth up to 5 hops
- Shell structure detection > 70% recall
- Dark money estimates bounded and labeled

---

## Phase 4: User Experience

**Target**: Q2 2027  
**Goal**: Speech input and challenge system

### Deliverables

- [ ] Speech-to-text hook (Whisper integration)
- [ ] Challenge/correction hook
- [ ] Human review queue
- [ ] Report generation (all formats)
- [ ] Model routing optimization
- [ ] End-to-end tests

### Success Criteria

- Speech transcription accuracy > 90%
- Challenge processing < 24h
- Average report latency < 30s

---

## Phase 5: Production Launch

**Target**: Q3 2027  
**Goal**: Public availability

### Deliverables

- [ ] pfMALL listing
- [ ] PWA shell integration
- [ ] Monitoring and alerting
- [ ] Rate limiting and abuse prevention
- [ ] Documentation (user-facing)
- [ ] Load testing

### Success Criteria

- 99.9% uptime
- Human review rate 5-15%
- No hallucinated accusations in production

---

## Dependencies

### Blocking

| Dependency | Owner | Status |
|------------|-------|--------|
| FEC API key | Ops | Not started |
| State API access | Ops | Not started |
| Meta Ad Library access | Ops | Not started |
| Whisper model deployment | Infrastructure | Available |

### Non-Blocking

| Dependency | Notes |
|------------|-------|
| pfMALL shell | Can develop without full shell |
| Stake gate | Not required for MVP |

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| FEC API rate limits | Medium | Implement caching, batch requests |
| State data inconsistency | Medium | Standardize parsing, note gaps |
| Model hallucination | High | WSP 97 confidence labeling, human review |
| Defamation claims | High | Strict evidence requirements, challenge system |
| Political bias accusations | High | Transparent methodology, source-only claims |

---

## Out of Scope (This Roadmap)

- Real-time election night tracking
- Ballot initiative analysis
- International elections
- Campaign strategy recommendations
- Predictive analytics

---

*0102 pArtifact: Phased approach to political transparency. Evidence-first, no hallucinations, human review for dangerous claims.*
