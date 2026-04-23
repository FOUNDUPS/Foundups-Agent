# CFZ3 — Corpus Hygiene and Sentinel Hardening (Phase 1)

**Slice**: `CFZ3_CORPUS_HYGIENE_AND_SENTINEL_HARDENING_PHASE1`
**Date**: 2026-04-24
**Worker**: CFZ3
**Decision**: HOLD (both TQ2 and TQ3 hold; corpus hygiene and sentinel fixes applied)

---

## Context

TQ2/TQ3 audits were producing unreliable gate signals due to two issues:

1. **Corpus pollution**: `navigation_wsp` included 129 documents from hidden/backup directories that should have been excluded (e.g., `.consciousness_migration_backup/`)

2. **Ambiguous sentinel**: Query `"WSP 97 truth distinction protocol"` did not match the actual WSP 97 title `"WSP 97 System Execution Prompting Protocol"`, causing false sentinel failures

---

## Deliverables

| Artifact | Path |
|----------|------|
| Indexing hygiene fix | `holo_index/core/indexing_engine.py` (lines 372-381) |
| Sentinel hardening | `holo_index/scripts/benchmarks/tq2_real_corpus_audit.py` (line 117) |
| Hygiene tests | `holo_index/tests/test_cfz3_corpus_hygiene.py` |
| Report | `docs/audits/holoindex_turboquant/CFZ3_CORPUS_HYGIENE_AND_SENTINEL_HARDENING_REPORT.md` |

---

## Exclusion Rule Implemented

**File**: `holo_index/core/indexing_engine.py` (lines 372-381)

```python
filtered_files = [
    f for f in all_doc_files
    if 'node_modules' not in str(f)
    and 'CHANGELOG' not in f.name.upper()
    and 'package-lock' not in f.name.lower()
    # CFZ3: Corpus hygiene - exclude hidden/backup/archive paths
    and not any(part.startswith('.') for part in f.parts)
    and '_backup' not in str(f).lower()
    and '/archive/' not in str(f).lower()
    and '\\archive\\' not in str(f).lower()
]
```

**Exclusions added**:
- Hidden directories (paths with components starting with `.`)
- Backup directories (paths containing `_backup`)
- Archive directories (paths containing `/archive/` or `\archive\`)

---

## Sentinel Change

| Field | Before | After |
|-------|--------|-------|
| Query text | `"WSP 97 truth distinction protocol"` | `"WSP 97 System Execution Prompting Protocol"` |
| Rationale | Ambiguous - didn't match WSP 97 title | Canonical - matches actual WSP 97 title |

---

## Corpus Counts Before/After

| Collection | Before CFZ3 | After CFZ3 | Delta |
|------------|-------------|------------|-------|
| navigation_code | 296 | 296 | 0 |
| navigation_wsp | 3,451 | 3,322 | -129 |
| navigation_tests | 0 | 0 | 0 |
| navigation_skills | 59 | 59 | 0 |
| navigation_symbols | 20,000 | 20,000 | 0 |
| navigation_vocabulary | 30 | 85 | +55* |
| **Total** | **23,836** | **23,762** | **-74** |

*Vocabulary increased due to separate reindex after ChromaDB disk error; this is independent of hygiene fix.

---

## TQ2/TQ3 Gate Results (After CFZ3)

### TQ2 — Pure int8 vs fp32

| Metric | Value | Gate | Status |
|--------|-------|------|--------|
| Top-1 Agreement | 88.7% | ≥90% | **FAIL** |
| Top-5 Set Agreement | 63.3% | ≥95% | **FAIL** |
| Sentinels | 29/30 | 30/30 | **FAIL** |
| **Decision** | **HOLD_INT8** | | |

**Failing sentinel**: `HOLO_USE_TURBOQUANT environment switch` on `navigation_vocabulary` (int8 top-1 diverges from fp32)

### TQ3 — Per-Collection Routing

| Metric | Value | Gate | Status |
|--------|-------|------|--------|
| Top-1 Agreement | 95.3% | ≥90% | **PASS** |
| Top-5 Set Agreement | 74.7% | ≥95% | **FAIL** |
| Sentinels | 30/30 | 30/30 | **PASS** |
| **Decision** | **HOLD_ROUTING** | | |

**Blocker**: Top-5 set-agreement still below 95% threshold

---

## Routing Policy (TQ3)

```json
{
  "navigation_code": "turboquant_onnx_int8",
  "navigation_wsp": "turboquant_onnx_int8",
  "navigation_tests": "sentence_transformers",
  "navigation_skills": "turboquant_onnx_int8",
  "navigation_symbols": "turboquant_onnx_int8",
  "navigation_vocabulary": "sentence_transformers"
}
```

---

## Sentinel Results (After CFZ3)

| Sentinel Query | TQ2 | TQ3 |
|----------------|-----|-----|
| WSP 97 System Execution Prompting Protocol | PASS | PASS |
| WSP 87 size limits for modules | PASS | PASS |
| AgentPermissionManager.request_permission | PASS | PASS |
| modules/ai_intelligence/agent_permissions | PASS | PASS |
| modules/platform_integration/youtube_auth | PASS | PASS |
| HOLO_USE_TURBOQUANT environment switch | **FAIL** (vocab) | PASS |

---

## Test Results

### Hygiene Tests
```
holo_index/tests/test_cfz3_corpus_hygiene.py: 10 passed
```

### TQ Test Suite
```
holo_index/tests/test_tq_corpus_freeze.py: 15 passed
holo_index/tests/test_turboquant_backend.py: 26 passed
holo_index/tests/test_turboquant_wiring.py: 16 passed, 1 skipped
Total: 57 passed, 1 skipped
```

---

## HoloIndex Search Command

```bash
python holo_index.py --search "index_wsp_entries gitignore backup corpus freeze sentinel WSP 97" --limit 3
```

**Top hit**: `holo_index/docs/HOLO_INDEX_REMEDIATION.md`

---

## WSP 97 Applied

- **Truthful state reporting**: Gate metrics reported exactly as measured, no synthetic pass claims
- **Evidence before facts**: Corpus counts and sentinel results verified via actual TQ2/TQ3 runs
- **First principles**: Identified root causes (corpus pollution, ambiguous sentinel) before attempting fixes
- **No production policy flip**: `HOLO_USE_TURBOQUANT=0` remains default

---

## Remaining Blockers

1. **TQ3 top-5 agreement (74.7%)**: Still below 95% threshold. Root cause investigation needed:
   - Likely int8 quantization loss on semantic similarity rankings beyond top-1
   - May require higher-precision quantization (int16?) or calibration tuning

2. **TQ2 vocabulary sentinel**: int8 cannot serve vocabulary collection without quality loss. Routing policy correctly addresses this by using fp32 for vocabulary.

---

## Next Steps

1. Investigate TQ3 top-5 blocker — is this int8 precision limit or query distribution issue?
2. Consider relaxing top-5 threshold if top-1 quality is deemed sufficient
3. Monitor for corpus drift via preflight checks on future audits
