# Agentic RAG Baseline Gate

**Date**: 2026-05-05
**Slice**: HIA_AGENTIC_RAG_BASELINE_GATE_PHASE1
**Status**: COMPLETE - PASS
**Author**: 0102 W1

---

## Purpose

Make HoloIndex answer: "Is retrieval sufficient for 0102 to act?"

This slice adds a verdict helper that classifies retrieval results before 0102 takes action. It enforces WSP 97 truth boundaries - queries that return wrong-bucket evidence cannot claim success.

---

## Why Federation Is Deferred

Federation (cross-FoundUp search) is intentionally P4:

1. **Local retrieval must be optimal first** - if local is weak, federation amplifies noise
2. **TurboQuant is performance, not truth** - must prove parity before default use
3. **External package verified but not deployed** - gotjunk/science-swarm not integrated yet
4. **Document now, build later** - Hermes/OpenClaw can build from spec

Priority order (WSP 15):
- P0: Internal Agentic RAG correctness (this slice)
- P1: Search quality gates
- P2: TurboQuant parity testing
- P3: External package adoption
- P4: Federation

---

## Why TurboQuant Is Not Promoted

TurboQuant (ONNX int8 backend) remains `HOLO_USE_TURBOQUANT=0` default because:

1. **3.65% cosine drift** measured in HIA3 baseline
2. **Quality parity not proven** for WSP/docs retrieval
3. **Performance optimization, not truth source**
4. **Must pass sentinel gates before promotion**

TurboQuant question to answer:
> Can int8 retrieval preserve the same decisions as fp32 for WSP-critical queries?

If yes, promote. If not, keep experimental.

---

## What Makes Retrieval Sufficient for 0102 Action

### Verdict Classification

| Verdict | Meaning | 0102 Action |
|---------|---------|-------------|
| SUFFICIENT | Evidence adequate | Proceed with confidence |
| DEGRADED | Incomplete but usable | Proceed with caution, flag uncertainty |
| UNSAFE_TO_ACT | Failed or wrong bucket | Do not proceed, escalate or retry |

### Intent-Bucket Alignment

| Query Intent | Required Bucket | If Missing |
|--------------|-----------------|------------|
| WSP | wsp_hits > 0 | DEGRADED or UNSAFE |
| DOCS | docs_hits > 0 | DEGRADED |
| KNOWLEDGE | knowledge_hits > 0 | DEGRADED |
| CODE | code_hits > 0 or symbol_hits > 0 | DEGRADED or UNSAFE |
| SKILL | skill_hits > 0 | DEGRADED |
| GENERAL | any hits | SUFFICIENT |

### WSP 97 Rules

1. **WSP intent with zero WSP hits** => Never SUFFICIENT
2. **Empty all buckets** => UNSAFE_TO_ACT
3. **Backend error** => UNSAFE_TO_ACT
4. **Code-only for WSP query** => DEGRADED (may miss protocol context)

---

## How Degraded Mode Must Be Reported

When retrieval is degraded:

```python
from holo_index.core.agentic_rag_verdict import (
    classify_retrieval_evidence,
    format_verdict_for_agent,
)

# After search
payload = holo.search("WSP 97 compliance")
summary = classify_retrieval_evidence(payload)

if summary.verdict != RetrievalVerdict.SUFFICIENT:
    print(format_verdict_for_agent(summary))
    # [WARN] Retrieval verdict: degraded
    #   Intent: wsp
    #   Hits: code=5, wsp=0, docs=0, knowledge=0
    #   Reason: WSP intent but only code hits — may miss protocol context
```

The verdict helper does NOT suppress degraded results. It surfaces them truthfully.

---

## Files Added

| File | Lines | Purpose |
|------|-------|---------|
| `holo_index/core/agentic_rag_verdict.py` | ~280 | Verdict helper |
| `holo_index/tests/test_agentic_rag_baseline_gate.py` | ~300 | 24 verdict tests |

---

## Test Results

| Test Suite | Result |
|------------|--------|
| test_agentic_rag_baseline_gate.py | 24/24 passed |
| test_search_quality_baseline.py | 10/10 passed |
| git diff --check | clean |

---

## WSP 97 Explicit Claims

| Claim | Status |
|-------|--------|
| Tests use mock payloads, not live retrieval | TRUE |
| Live retrieval quality tested in baseline tests | TRUE |
| TurboQuant not promoted | TRUE |
| Federation not built | TRUE |
| Verdict helper is pure, does not modify search | TRUE |

---

## Next Slice

**HIA_AGENTIC_RAG_LIVE_COLLECTION_HEALTH_PHASE2**

Goal: Run verdict classification against live HoloIndex retrieval and measure real collection health across WSP/docs/code/knowledge buckets.
