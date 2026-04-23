# CFZ1 — Corpus Freeze Mechanism (Phase 1)

**Slice**: `CFZ1_HOLOINDEX_CORPUS_FREEZE_MECHANISM_PHASE1`
**Date**: 2026-04-23
**Worker**: CY
**Decision**: IMPLEMENTED (mechanism operational; TQ2/TQ3 now gated by corpus verification)

---

## Context

TQ3 audit revealed **corpus drift** as the root cause of gate failure: `navigation_wsp`
dropped from 3,446 to 1,916 documents between TQ2 and TQ3 runs. This made the TQ3
metrics incomparable to TQ2, invalidating the promotion decision.

CFZ1 implements a deterministic corpus freeze mechanism that:
1. Snapshots the current corpus state with per-collection fingerprints
2. Verifies corpus stability before any TQ audit runs
3. Aborts audits with clear error messaging if drift is detected

---

## Deliverables

| Artifact | Path |
|----------|------|
| Freeze utility | `holo_index/scripts/benchmarks/tq_corpus_freeze.py` |
| Frozen manifest | `docs/audits/holoindex_turboquant/corpus_freeze_manifest.json` |
| Tests | `holo_index/tests/test_tq_corpus_freeze.py` |
| Report | `docs/audits/holoindex_turboquant/CFZ1_CORPUS_FREEZE_REPORT.md` |

---

## Manifest Structure

```json
{
  "vector_path": "E:/HoloIndex/vectors",
  "created_at_utc": "2026-04-23T12:50:33.347298+00:00",
  "git_sha": "85dc42baf217",
  "total_documents": 23835,
  "collections": {
    "<collection_name>": {
      "count": <int>,
      "ids_sha256": "<deterministic hash of sorted IDs>",
      "documents_sha256": "<deterministic hash of sorted documents>",
      "metadatas_sha256": "<deterministic hash of sorted metadata>"
    }
  }
}
```

---

## Frozen Collection Counts

| Collection | Documents |
|------------|----------:|
| navigation_code | 296 |
| navigation_wsp | 3,450 |
| navigation_tests | 0 |
| navigation_skills | 59 |
| navigation_symbols | 20,000 |
| navigation_vocabulary | 30 |
| **Total** | **23,835** |

---

## Hash Fields Produced

For each collection:
- `ids_sha256` — SHA256 of newline-joined sorted IDs
- `documents_sha256` — SHA256 of separator-joined sorted documents (or "empty")
- `metadatas_sha256` — SHA256 of sorted JSON-serialized metadata entries (or "empty")

---

## Operator Commands

### Create Snapshot

```bash
python holo_index/scripts/benchmarks/tq_corpus_freeze.py snapshot \
    --out docs/audits/holoindex_turboquant/corpus_freeze_manifest.json
```

### Verify Corpus

```bash
python holo_index/scripts/benchmarks/tq_corpus_freeze.py verify \
    --manifest docs/audits/holoindex_turboquant/corpus_freeze_manifest.json
```

---

## Verify Pass Output

```
[TQ_CORPUS_FREEZE] Verifying corpus against manifest...
[VERIFY] Checking against manifest from 2026-04-23T12:50:33.347298+00:00
[VERIFY] Manifest git SHA: 85dc42baf217
[VERIFY] Current git SHA: 85dc42baf217

  [VERIFY] navigation_code: OK (296 docs)
  [VERIFY] navigation_wsp: OK (3450 docs)
  [VERIFY] navigation_tests: OK (0 docs)
  [VERIFY] navigation_skills: OK (59 docs)
  [VERIFY] navigation_symbols: OK (20000 docs)
  [VERIFY] navigation_vocabulary: OK (30 docs)

[VERIFY] PASS - corpus matches frozen manifest
```

---

## Verify Fail Output (Simulated Drift)

```
[TQ_CORPUS_FREEZE] Verifying corpus against manifest...
[VERIFY] Checking against manifest from 2026-04-23T12:00:00+00:00
[VERIFY] Manifest git SHA: test123
[VERIFY] Current git SHA: 85dc42baf217

  [VERIFY] navigation_code: DRIFT - count 100 → 296, ids_sha256 changed, documents_sha256 changed, metadatas_sha256 changed
  [VERIFY] navigation_wsp: DRIFT - count 5000 → 3450, ids_sha256 changed, documents_sha256 changed, metadatas_sha256 changed
  [VERIFY] navigation_tests: OK (0 docs)
  [VERIFY] navigation_skills: DRIFT - ids_sha256 changed, documents_sha256 changed, metadatas_sha256 changed
  [VERIFY] navigation_symbols: DRIFT - ids_sha256 changed, documents_sha256 changed, metadatas_sha256 changed
  [VERIFY] navigation_vocabulary: DRIFT - ids_sha256 changed, documents_sha256 changed, metadatas_sha256 changed

[VERIFY] FAIL - 5 drift(s) detected:
  - navigation_code: count 100 → 296, ids_sha256 changed, documents_sha256 changed, metadatas_sha256 changed
  - navigation_wsp: count 5000 → 3450, ids_sha256 changed, documents_sha256 changed, metadatas_sha256 changed
  - navigation_skills: ids_sha256 changed, documents_sha256 changed, metadatas_sha256 changed
  - navigation_symbols: ids_sha256 changed, documents_sha256 changed, metadatas_sha256 changed
  - navigation_vocabulary: ids_sha256 changed, documents_sha256 changed, metadatas_sha256 changed
Exit code: 1
```

---

## TQ2/TQ3 Preflight Wiring

Both audit scripts now call `preflight_check()` before any measurement:

**tq2_real_corpus_audit.py** (line ~214):
```python
from holo_index.scripts.benchmarks.tq_corpus_freeze import preflight_check
print("[TQ2] preflight — corpus freeze verification")
preflight_check(CORPUS_MANIFEST)
```

**tq3_routed_corpus_audit.py** (line ~88):
```python
from holo_index.scripts.benchmarks.tq_corpus_freeze import preflight_check
print("[TQ3] preflight - corpus freeze verification")
preflight_check(CORPUS_MANIFEST)
```

---

## Emergency Override

Set `TQ_CORPUS_ALLOW_DRIFT=1` to skip verification (use only when intentionally
measuring against a different corpus state):

```bash
TQ_CORPUS_ALLOW_DRIFT=1 python holo_index/scripts/benchmarks/tq2_real_corpus_audit.py
```

---

## Test Coverage

15 tests covering:
- Hash determinism (7 tests)
- Manifest structure (1 test)
- Verify drift detection (3 tests)
- Preflight behavior (4 tests)

---

## WSP 97 Applied

- Manifest contents are **VERIFIED_FACT** (computed from live corpus at freeze time)
- Collection counts and hashes are deterministically reproducible
- Preflight check truthfully reports pass/fail with operator-visible drift details
- No runtime policy promotion occurred in this slice

---

## Next Steps

1. Re-run TQ2 with frozen corpus → expect stable metrics
2. Re-run TQ3 with frozen corpus → expect stable metrics
3. If gates pass, consider routing promotion
4. If corpus needs intentional update, re-snapshot before re-audit
