# FoundUps Work Ledger Search Retrieval Priority Hotfix — Phase 1

**Date**: 2026-05-22
**Slice**: FOUNDUPS_WORK_LEDGER_SEARCH_RETRIEVAL_PRIORITY_HOTFIX_PHASE1
**Base Commit**: `600eee482` (main; PR #649 + later merges, ancestry includes `1c937cf5c`)
**Branch**: `feat/work-ledger-priority-hotfix`
**Worktree**: `.claude/worktrees/work-ledger-priority-hotfix`
**Mode**: IMPLEMENTATION (hotfix)

---

## WSP 97 Truth Boundary Labels

| Label | Status |
|-------|--------|
| HOLOINDEX_RETRIEVAL_HOTFIX_ONLY | YES |
| WORK_LEDGER_SEARCH_FIX_ONLY | YES |
| NO_LIVE_REINDEX | YES (only end-to-end read against pre-existing populated collection) |
| NO_LEDGER_MUTATION | YES |
| NO_AGENTDB_MUTATION | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_RUNTIME_WRE_CHANGE | YES |
| NO_MCP_CHANGE | YES |
| NO_GENERATED_INDEX_ARTIFACTS | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Defect Context

`FOUNDUPS_WORK_LEDGER_CONTROLLED_REINDEX_PHASE1_RETRY` documented:

- `navigation_work_ledger` collection populated with 5 entries via `python holo_index.py --index-work-ledger`
- CLI search returns `0 WorkLedger` despite collection being populated
- Root cause: `priority = meta.get("priority", 1)` in `_search_collection` returns string `"P3"` for work-ledger entries; `_format_hit` then evaluates `0.5 * "P3"` → `TypeError`
- The exception was silently swallowed by `except Exception: work_ledger_hits = []`, erasing the entire bucket without diagnostic signal

---

## 2. HoloIndex Assessment (WSP 87)

| Query | Hits | Quality |
|-------|------|---------|
| `work ledger priority_num priority P3 search_engine _format_hit` | 32 | LOW — generic CLI/economics hits |
| `work_ledger_slice search_engine execute_search exception logging` | 32 | LOW — generic search hits |

Fallback to direct code reading was required (consistent with prior search-engine slices).

---

## 3. Implementation Summary

### 3.1 Files Modified

| File | Changes |
|------|---------|
| `holo_index/core/search_engine.py` | Added `_PRIORITY_LABEL_WEIGHTS` constant, added `_coerce_priority()` helper, replaced bare `meta.get("priority", 1)` lookup, upgraded silent `except Exception` in work-ledger block to logged warning |
| `holo_index/tests/test_work_ledger_indexing.py` | Added 11 tests across 3 new test classes |
| `docs/audits/holoindex_search_quality/FOUNDUPS_WORK_LEDGER_SEARCH_RETRIEVAL_PRIORITY_HOTFIX_PHASE1.md` | NEW (this audit) |

### 3.2 New helper: `_coerce_priority(meta, default=1.0)`

Resolution order, never raises:
1. `priority_num` if numeric (work-ledger indexer always writes this).
2. `priority` if numeric (standard collections).
3. `priority` interpreted as P0..P4 label via `_PRIORITY_LABEL_WEIGHTS` (`P0=5, P1=4, P2=3, P3=2, P4=1`).
4. `priority` interpreted as a numeric string.
5. `default`.

Boolean values are explicitly rejected from the numeric branches (Python booleans subclass `int`).

### 3.3 Replaced call site

In `_search_collection` (~line 686):
```python
# Before
priority = meta.get("priority", 1)

# After
priority = _coerce_priority(meta)
```

This is the single arithmetic input that `_format_hit` consumes for the `_sort_key` calculation. Coercing at the source ensures every downstream usage receives a number.

### 3.4 Logging upgrade in `execute_search` (lines 1088-1099)

```python
# Before
except Exception:
    work_ledger_hits = []

# After
except Exception as exc:
    logger.warning(
        "Work-ledger search failed (%s): %s. Falling back to empty hits — normal search continues.",
        type(exc).__name__, exc, exc_info=True,
    )
    work_ledger_hits = []
```

Silent failure is the operational hazard that caused W6/W10 to waste a full reindex cycle before detection. Logging here makes future regressions surface in normal observability.

### 3.5 Design Decisions

| Decision | Rationale |
|----------|-----------|
| Coerce at `_search_collection` rather than `_format_hit` | Single chokepoint; downstream signature stays numeric. Less surface area than touching `_format_hit` across all collection types. |
| Defensive label fallback (P0..P4) | Indexer currently writes both `priority_num` AND `priority`. The label fallback protects against future indexer changes that drop one or the other. |
| Reject booleans explicitly | Python `bool` subclasses `int`. Without explicit rejection, `priority=True` would propagate as `1.0`, masking metadata bugs. |
| Keep work-ledger fallback returning `[]` (not raising) | Other search buckets (code/wsp/docs) still need to work even if work-ledger errors. Continuity > strict failure. |
| Log at `WARNING`, not `ERROR` | Operationally important but the search still returns useful results. `WARNING` is the right severity for a degraded-but-functional state. |

---

## 4. End-to-End Verification (Read-Only Against Live Collection)

The previous reindex slice left the `navigation_work_ledger` collection populated with 5 entries on E:/HoloIndex. **No reindex was executed in this slice** — the existing index was queried read-only to verify the fix end-to-end.

### 4.1 Before this hotfix (per RETRY audit)
```
[HOLO-0102] Search complete: ... 0 WorkLedger
result['work_ledger_hits'] == []
```

### 4.2 After this hotfix
```
$ python -c "from holo_index.core.holo_index import HoloIndex; ..."
[HOLO-0102] Search complete: 0 code, 0 WSP, 0 Tests, 0 Skillz, 0 Docs, 0 Knowledge, 5 WorkLedger
work_ledger_hits: 5
  - Work Ledger JSON Schema Definition (priority=10.0)
  - Patch Brain Existing Artifacts into Work Ledger Audit (priority=10.0)
  - I_i Bonding Curve Legal Review Packet (priority=10.0)
  - Du Pool Staker Model Truth Alignment (priority=10.0)
  - OpenClaw Security Fail Dispatch to AI Overseer (priority=10.0)
```

All 5 slices retrievable. Priority correctly coerced to numeric (10.0 from `priority_num`).

---

## 5. Test Results

### 5.1 New Tests (11 added)

| Class | Test | Status |
|-------|------|--------|
| `TestPriorityCoercion` | `test_priority_num_wins_over_string_priority` | PASS |
| `TestPriorityCoercion` | `test_numeric_priority_returned_unchanged` | PASS |
| `TestPriorityCoercion` | `test_p_label_coerced_to_weight` | PASS |
| `TestPriorityCoercion` | `test_p_label_case_and_whitespace_tolerated` | PASS |
| `TestPriorityCoercion` | `test_unknown_label_falls_back_to_default` | PASS |
| `TestPriorityCoercion` | `test_numeric_string_parsed` | PASS |
| `TestPriorityCoercion` | `test_missing_metadata_returns_default` | PASS |
| `TestPriorityCoercion` | `test_bool_priority_rejected_falls_through` | PASS |
| `TestFormatHitWithStringPriority` | `test_search_collection_does_not_crash_with_string_priority` | PASS |
| `TestExecuteSearchWorkLedgerLogging` | `test_work_ledger_exception_is_logged_and_search_continues` | PASS |
| `TestExecuteSearchWorkLedgerLogging` | `test_work_ledger_collection_none_does_not_log_warning` | PASS |

### 5.2 Full Work-Ledger Suite

```
============================= 74 passed in 7.21s ==============================
```

All prior 63 tests + 11 new = **74/74 passing**.

### 5.3 Regression Suites

```
============================= 32 passed in 1.28s ==============================
```

| Suite | Tests | Status |
|-------|-------|--------|
| `test_hxa_retrieval_fix.py` | 22 | PASS |
| `test_search_quality_baseline.py` | 10 | PASS |

### 5.4 Total

**106 tests passing in modified scope, 0 regressions.**

---

## 6. Verification Matrix

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Work-ledger result with `priority="P3"` and `priority_num=10` does not crash | PASS | test_search_collection_does_not_crash_with_string_priority |
| Query by slice_id returns ≥1 hit in mocked search path | PASS | test_search_collection_does_not_crash_with_string_priority (returns 1 hit) |
| `_sort_key` uses numeric priority | PASS | Live e2e shows `priority=10.0` (float) |
| Missing `priority_num` with label `P1` coerces safely | PASS | test_p_label_coerced_to_weight |
| Invalid priority label falls back safely | PASS | test_unknown_label_falls_back_to_default |
| Exception in work-ledger block logged, not silenced | PASS | test_work_ledger_exception_is_logged_and_search_continues |
| Normal search continues when work-ledger errors | PASS | Other hits still returned; only `work_ledger_hits=[]` |
| Existing work-ledger tests pass | PASS | 63/63 |
| HXA retrieval tests pass | PASS | 22/22 |
| Search quality baseline pass | PASS | 10/10 |
| No live reindex executed | PASS | No `--index-work-ledger` invocation in this slice |
| No source mutations outside allowed scope | PASS | Only `search_engine.py` + tests + audit |
| No generated index artifacts | PASS | No reindex, no Chroma writes from this slice |

---

## 7. Outputs

### 7.1 Files Changed by This Slice

| File | Type |
|------|------|
| `holo_index/core/search_engine.py` | Modified — added `_coerce_priority` helper, replaced call site, upgraded exception handler |
| `holo_index/tests/test_work_ledger_indexing.py` | Modified — added 3 test classes / 11 tests |
| `docs/audits/holoindex_search_quality/FOUNDUPS_WORK_LEDGER_SEARCH_RETRIEVAL_PRIORITY_HOTFIX_PHASE1.md` | NEW |

Zero ledger, AgentDB, registry, WRE, OpenClaw, MCP, or pFMALL catalog changes.

### 7.2 Generated Artifacts Status

None. No reindex executed. The end-to-end verification queried the pre-existing collection state from the prior controlled-reindex slice (read-only).

---

## 8. WSP 97 Verdict

| Check | Result |
|-------|--------|
| False claims detected? | NO |
| Live reindex executed? | NO |
| Ledger JSON modified? | NO |
| AgentDB / Registry / WRE / OpenClaw / MCP changed? | NO |
| Generated index artifacts committed? | NO |
| Defect fully fixed (retrieval working end-to-end)? | YES |
| New test coverage prevents regression? | YES (11 tests) |

**WSP 97 VERDICT**: **PASS**

---

## 9. Next Slice Recommendation

**Slice ID**: `FOUNDUPS_WORK_LEDGER_CONTROLLED_REINDEX_PHASE1_RETRY` — **search-verification mode**

**Purpose**: With the hotfix merged, re-run the controlled reindex verification slice in **search-verification mode only** (do NOT re-execute `--index-work-ledger`; the existing collection state is intact and already-correct metadata). Confirm:
1. All 5 verification queries return `>0` work-ledger hits via the CLI summary line `(... N WorkLedger)`.
2. slice_id, PR number, owner_worker, status, and related_foundup_id queries each return the expected slice.
3. No regression in normal HoloIndex queries.

If the operator/W10 chooses to re-reindex first (e.g., to verify the indexer side still writes correctly), use `python holo_index.py --index-work-ledger` — the wrapper is unchanged by this slice.

---

## 10. Summary

| Aspect | State |
|--------|-------|
| Retrieval defect identified by RETRY slice | FIXED |
| Search returns work-ledger hits | YES (5/5 against live collection) |
| Silent exception swallowing | REPLACED with logged warning |
| Test coverage added | 11 tests across coercion, format-hit, and exception logging |
| Regression risk | LOW (no behavior change for non-work-ledger collections, helper is purely additive) |
| Ready for W10 | YES |

---

**Implementation Complete**: 2026-05-22
**Author**: Targeted HoloIndex bugfix worker
**WSP Lock**: WSP_00, WSP_15, WSP_50, WSP_87, WSP_97, WSP_22
