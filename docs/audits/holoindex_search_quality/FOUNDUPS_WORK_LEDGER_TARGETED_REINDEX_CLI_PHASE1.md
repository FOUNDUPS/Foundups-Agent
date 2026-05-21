# FoundUps Work Ledger Targeted Reindex CLI — Phase 1

**Date**: 2026-05-22
**Slice**: FOUNDUPS_WORK_LEDGER_TARGETED_REINDEX_CLI_PHASE1
**Base Commit**: `bde914836` (origin/main after PR #648 merge)
**Branch**: `feat/work-ledger-targeted-reindex-cli`
**Worktree**: `.claude/worktrees/work-ledger-targeted-reindex-cli`
**Mode**: IMPLEMENTATION

---

## WSP 97 Truth Boundary Labels

| Label | Status |
|-------|--------|
| HOLOINDEX_CLI_TARGETED_INDEX_ONLY | YES |
| WORK_LEDGER_INDEX_FLAG_ONLY | YES |
| NO_LIVE_REINDEX | YES |
| NO_GENERATED_INDEX_ARTIFACTS | YES |
| NO_LEDGER_MUTATION | YES |
| NO_AGENTDB_MUTATION | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_RUNTIME_WRE_CHANGE | YES |
| NO_MCP_CHANGE | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Purpose

Add a targeted HoloIndex CLI path for indexing work ledger entries only, closing the gap identified in `FOUNDUPS_WORK_LEDGER_CONTROLLED_REINDEX_PHASE1` where no CLI flag existed to invoke `HoloIndex.index_work_ledger_entries()`.

---

## 2. HoloIndex Assessment (WSP 87)

| Query | Hits | Quality |
|-------|------|---------|
| `holo_index CLI index-code index-docs index-knowledge index_work_ledger_entries` | 32 | PARTIAL - found CLI module references |
| `navigation_work_ledger targeted reindex CLI _cli_main` | 32 | LOW - generic CLI/audit hits |
| `work ledger controlled reindex missing CLI flag` | 32 | LOW - prior audit referenced |

**Fallback Required**: YES — direct code reading for integration points.

---

## 3. Implementation Summary

### 3.1 Files Modified

| File | Changes |
|------|---------|
| `holo_index/_cli_main.py` | Added 3 argparse flags + `_run_work_ledger_indexing()` helper + dispatch call |
| `holo_index/tests/test_work_ledger_indexing.py` | Added 10 tests across 2 new test classes |
| `docs/audits/holoindex_search_quality/FOUNDUPS_WORK_LEDGER_TARGETED_REINDEX_CLI_PHASE1.md` | NEW (this audit) |

### 3.2 CLI Flags Added

```python
# Line 614-616 of _cli_main.py
parser.add_argument('--index-work-ledger', dest='index_work_ledger', action='store_true',
    help='Index work ledger slices into navigation_work_ledger (targeted, opt-in)')
parser.add_argument('--reindex-work-ledger', dest='index_work_ledger', action='store_true',
    help='Alias for --index-work-ledger')
parser.add_argument('--reindex-ledger', dest='index_work_ledger', action='store_true',
    help='Alias for --index-work-ledger')
```

### 3.3 Dispatch Helper (NEW)

`_run_work_ledger_indexing(holo, args) -> bool` — opt-in only, fail-closed on missing source, exception-safe.

Key behaviours:
- Returns `False` immediately if `args.index_work_ledger` is unset or missing.
- Prints `[WORK-LEDGER] Source: <path>` and `[WORK-LEDGER] Collection: navigation_work_ledger`.
- Skips with `[WORK-LEDGER] Status: SKIPPED - source file missing (fail-closed)` if `work_ledger.example.json` is absent.
- Invokes `holo.index_work_ledger_entries()` and reports entry count + duration.
- Catches any wrapper exception and reports `[WORK-LEDGER] Status: FAILURE`.

### 3.4 Dispatch Call (inserted after `--index-cli` block)

```python
# Targeted work-ledger reindex (FOUNDUPS_WORK_LEDGER_TARGETED_REINDEX_CLI_PHASE1)
if _run_work_ledger_indexing(holo, args):
    indexing_awarded = True
```

### 3.5 Design Decisions

| Decision | Rationale |
|----------|-----------|
| Opt-in only (NOT cascaded by `--index-all`) | Operator-gated reindex per slice spec ("indexes only work ledger entries", "does not trigger full repo reindex"). Cascading would expand `--index-all` scope beyond this slice. |
| Three flag aliases | Matches existing convention (`--index-skillz` has 4 aliases). Aligned with prior gap analysis recommendations. |
| Helper function isolated | Independently testable; minimal blast radius into `main()`. |
| `safe_print` only | No `vprint` dependency — output is always visible to confirm targeted reindex executed. |

---

## 4. Test Results

### 4.1 New Tests (10 tests)

```
============================= 10 passed in 6.85s ==============================
```

| Class | Test | Status |
|-------|------|--------|
| `TestCLITargetedReindex` | `test_helper_returns_false_when_flag_unset` | PASS |
| `TestCLITargetedReindex` | `test_helper_returns_false_when_flag_missing` | PASS |
| `TestCLITargetedReindex` | `test_helper_fail_closed_when_source_missing` | PASS |
| `TestCLITargetedReindex` | `test_helper_invokes_wrapper_when_source_exists` | PASS |
| `TestCLITargetedReindex` | `test_helper_handles_wrapper_exception_gracefully` | PASS |
| `TestCLITargetedReindex` | `test_helper_does_not_invoke_other_index_methods` | PASS |
| `TestCLIFlagParsing` | `test_help_advertises_index_work_ledger_flag` | PASS |
| `TestCLIFlagParsing` | `test_help_advertises_reindex_work_ledger_alias` | PASS |
| `TestCLIFlagParsing` | `test_help_advertises_reindex_ledger_alias` | PASS |
| `TestCLIFlagParsing` | `test_existing_index_flags_still_advertised` | PASS |

### 4.2 Full Work Ledger Suite

```
============================= 63 passed in 6.85s ==============================
```

All 53 existing work-ledger tests pass + 10 new = **63/63 passing**.

### 4.3 Regression Suites

```
============================= 32 passed in 1.25s ==============================
```

| Suite | Tests | Status |
|-------|-------|--------|
| `test_hxa_retrieval_fix.py` | 22 | PASS |
| `test_search_quality_baseline.py` | 10 | PASS |

### 4.4 Pre-existing test_cli.py failure

`test_check_module_exists_recognizes_ric_dae` (in `test_cli.py`) fails with stale expectation (`[VIOLATION]` vs current `[COMPLIANT]`). Verified pre-existing and **unrelated** to this slice — the failing test exercises `holo.check_module_exists()`, which this slice does not touch.

### 4.5 Total

**95 tests passing in modified scope, 0 regressions introduced.**

---

## 5. Implementation Verification

### 5.1 Required Checks

| Check | Status | Evidence |
|-------|--------|----------|
| CLI flag `--index-work-ledger` accepted by parser | PASS | `--help` lists flag; test_help_advertises_index_work_ledger_flag |
| Aliases `--reindex-work-ledger`, `--reindex-ledger` accepted | PASS | `--help` lists aliases; 2 alias tests |
| Wired to `HoloIndex.index_work_ledger_entries()` | PASS | test_helper_invokes_wrapper_when_source_exists |
| Indexes only work ledger entries | PASS | test_helper_does_not_invoke_other_index_methods |
| Does not trigger full repo reindex | PASS | No `--index-all` cascade; isolated dispatch block |
| Print clear summary (source, collection, count, status) | PASS | `[WORK-LEDGER] Source:`, `Collection:`, `Entries indexed:`, `Status:` lines |
| Fail gracefully on missing source file | PASS | test_helper_fail_closed_when_source_missing |
| No live reindex executed | PASS | No CLI invocation of `--index-work-ledger` in this slice |
| Existing index flag tests still pass | PASS | test_existing_index_flags_still_advertised + regression suites |

### 5.2 Argparse Aliasing Semantics

All three flags share `dest='index_work_ledger'` — any of them sets the same namespace attribute. The dispatch helper only checks `args.index_work_ledger`, so aliases behave identically without code duplication in dispatch logic.

### 5.3 Cascade Isolation

| Other Flag | Triggers `index_work_ledger`? |
|------------|-------------------------------|
| `--index-all` | NO |
| `--index` | NO |
| `--index-code` | NO |
| `--index-wsp` | NO |
| `--index-docs` | NO |
| `--index-knowledge` | NO |
| `--index-skillz` | NO |
| `--index-cli` | NO |
| `--index-symbols` | NO |

Targeted reindex is strictly opt-in.

---

## 6. Usage (For Future Slice)

The next slice (`FOUNDUPS_WORK_LEDGER_CONTROLLED_REINDEX_PHASE1` re-run) will execute:

```bash
python holo_index.py --index-work-ledger
```

Expected output on success:
```
[WORK-LEDGER] Source: <repo>/docs/0102_session_briefings/work_ledger.example.json
[WORK-LEDGER] Collection: navigation_work_ledger
[WORK-LEDGER] Entries indexed: <N>
[WORK-LEDGER] Status: SUCCESS (<T>s)
```

Expected output if source missing:
```
[WORK-LEDGER] Source: <repo>/docs/0102_session_briefings/work_ledger.example.json
[WORK-LEDGER] Collection: navigation_work_ledger
[WORK-LEDGER] Status: SKIPPED - source file missing (fail-closed)
```

---

## 7. What This Does NOT Do

| Action | Why Not |
|--------|---------|
| Execute live reindex | NO_LIVE_REINDEX (deferred to next controlled-reindex slice) |
| Commit ChromaDB artifacts | NO_GENERATED_INDEX_ARTIFACTS |
| Cascade with `--index-all` | Operator-gated only; preserves narrow safe scope |
| Modify ledger JSON | NO_LEDGER_MUTATION |
| Touch AgentDB / registry / WRE / OpenClaw / MCP | NO_*_MUTATION / NO_*_CHANGE labels |
| Run pFMALL catalog changes | Out of scope |

---

## 8. Next Slice

**Slice ID**: `FOUNDUPS_WORK_LEDGER_CONTROLLED_REINDEX_PHASE1` (re-execution)

**Purpose**: Now that `--index-work-ledger` exists, re-run the controlled reindex slice. Operator/W10 invokes:

```bash
python holo_index.py --index-work-ledger
```

then re-runs the verification queries documented in Phase 1 controlled reindex audit to confirm `navigation_work_ledger` is populated and slices are retrievable.

---

## 9. Summary

### 9.1 Deliverables

1. `--index-work-ledger` CLI flag with two aliases (`--reindex-work-ledger`, `--reindex-ledger`)
2. `_run_work_ledger_indexing()` helper function (testable, fail-closed)
3. Dispatch wiring in `main()`
4. 10 new tests (6 dispatch + 4 parser)
5. Audit documentation

### 9.2 WSP 97 Verdict

| Check | Result |
|-------|--------|
| False claims detected? | NO |
| Live reindex executed? | NO |
| Generated index artifacts committed? | NO |
| Ledger mutated? | NO |
| Existing index flags broken? | NO |

**WSP 97 VERDICT: PASS**

### 9.3 W10 Readiness

| Gate | Status |
|------|--------|
| Implementation complete | YES |
| All new tests pass | YES (10/10) |
| Full work-ledger suite passes | YES (63/63) |
| Regression suites pass | YES (32/32) |
| No live reindex performed | YES |
| Audit doc complete | YES |
| Ready for PR | YES |

---

**Implementation Complete**: 2026-05-22
**Author**: Implementation worker
**WSP Lock**: WSP_00, WSP_50, WSP_87, WSP_97, WSP_22, WSP_60, WSP_70
