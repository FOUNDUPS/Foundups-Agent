# HoloIndex Auto-pip Opt-In — Phase 1

**Slice**: `HOLOINDEX_AUTO_PIP_OPT_IN_PHASE1`
**Worker**: W6
**Agent**: 0102
**Date**: 2026-05-24
**Mode**: Security boundary hardening (fail-closed default)
**Branch**: `feat/holoindex-auto-pip-opt-in-phase1`
**Base commit**: `bf14adcb5` (origin/main, post-PR #705)
**Authorizing Audit**: PR #704 `HOLOINDEX_CODEINDEX_RETRIEVAL_SYSTEM_AUDIT_PHASE1.md` (merge `247eeac9b`) — surfaced the chromadb auto-install subprocess as the only network-capable code path in the HoloIndex surface, and named this slice as the follow-on fix.
**Predecessor**: PR #705 `HOLOINDEX_COLLECTION_HEALTH_COMPLETENESS_PHASE1` (merge `bf14adcb5`) — F2 from the #704 follow-on queue.
**WSP Lock**: WSP_00 → WSP_15 → WSP_50 → WSP_64 → WSP_83 → WSP_87 → WSP_97 → WSP_22 → WSP_93

---

## A. Mission + Scope Statement

Flip the default chromadb auto-install behavior from **opt-out** (install unless blocked) to **opt-in** (never install unless explicitly allowed). This is a subprocess security boundary hardening.

**Before**: `pip install chromadb` executes by default unless `HOLO_DISABLE_PIP_INSTALL=1` or `HOLO_OFFLINE=1`.
**After**: `pip install chromadb` NEVER executes unless `HOLO_ALLOW_PIP_INSTALL=1|true|yes`.

This is a **fail-closed** change. Network calls and subprocess spawns require explicit operator consent.

---

## WSP_97 Truth Boundary Checklist

| Truth Boundary Checklist Item | Status |
|-------------------------------|--------|
| HOLOINDEX_AUTO_PIP_OPT_IN_ONLY | YES |
| FAIL_CLOSED_BY_DEFAULT | YES |
| NO_SUBPROCESS_UNLESS_OPT_IN | YES |
| NO_NETWORK_CALL_UNLESS_OPT_IN | YES |
| PRESERVES_HOLO_DISABLE_PIP_INSTALL_SEMANTICS | YES |
| PRESERVES_HOLO_OFFLINE_SEMANTICS | YES |
| ERROR_MESSAGE_NAMES_ENV_VAR | YES |
| ERROR_MESSAGE_GIVES_MANUAL_INSTALL_HINT | YES |
| NO_INDEXER_CHANGE | YES |
| NO_SEARCH_ENGINE_CHANGE | YES |
| NO_CHROMA_MUTATION | YES |
| NO_REINDEX | YES |
| NO_GENERATED_INDEX_ARTIFACTS | YES |
| NO_RANKING_TUNING | YES |
| NO_TURBOQUANT_PROMOTION | YES |
| NO_TRADE_MUTATION | YES |
| NO_REGISTRY_MUTATION | YES |
| NO_CATALOG_MUTATION | YES |
| NO_MANIFEST_MUTATION | YES |
| NO_PROJECTION_MUTATION | YES |
| NO_WSP_MUTATION | YES |
| NO_CI_CHANGE | YES |
| NO_DEPENDENCY_INSTALL | YES |
| USES_MOCKS_NOT_LIVE_PIP | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |
| TESTS_VERIFY_FAIL_CLOSED | YES |

**Verdict**: PASS (28/28)

---

## B. Before/After Env-Var Contract

### B.1 Before State (opt-out default)

```python
# Default: auto-install enabled
# Blocking required explicit env vars
if os.getenv("HOLO_DISABLE_PIP_INSTALL") == "1":
    # Don't install
elif os.getenv("HOLO_OFFLINE") == "1":
    # Don't install
else:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "chromadb"])
```

| Scenario | HOLO_ALLOW_PIP_INSTALL | HOLO_DISABLE_PIP_INSTALL | HOLO_OFFLINE | Result |
|----------|------------------------|--------------------------|--------------|--------|
| Default | (unset) | (unset) | (unset) | **INSTALLS** ← Problem |
| Blocked | (unset) | 1 | (unset) | No install |
| Offline | (unset) | (unset) | 1 | No install |

### B.2 After State (opt-in default)

```python
def _is_pip_install_allowed() -> bool:
    """Check if pip auto-install is explicitly allowed."""
    if os.getenv("HOLO_DISABLE_PIP_INSTALL") == "1":
        return False
    if os.getenv("HOLO_OFFLINE") == "1":
        return False
    allow_val = os.getenv("HOLO_ALLOW_PIP_INSTALL", "").strip().lower()
    return allow_val in ("1", "true", "yes")
```

| Scenario | HOLO_ALLOW_PIP_INSTALL | HOLO_DISABLE_PIP_INSTALL | HOLO_OFFLINE | Result |
|----------|------------------------|--------------------------|--------------|--------|
| Default | (unset) | (unset) | (unset) | **No install** ← Fixed |
| Opt-in | 1 | (unset) | (unset) | Installs |
| Opt-in (true) | true | (unset) | (unset) | Installs |
| Opt-in (yes) | yes | (unset) | (unset) | Installs |
| Opt-in (TRUE) | TRUE | (unset) | (unset) | Installs |
| Disable overrides | 1 | 1 | (unset) | **No install** |
| Offline overrides | 1 | (unset) | 1 | **No install** |
| Explicit off | 0 | (unset) | (unset) | No install |
| Explicit off | false | (unset) | (unset) | No install |
| Explicit off | no | (unset) | (unset) | No install |

---

## C. Fail-Closed Error Message

When chromadb is not importable and auto-install is not allowed:

```
chromadb is required but not installed.
Recommended (most reliable): pip install chromadb
Or set HOLO_ALLOW_PIP_INSTALL=1 to enable auto-install.
```

**Verification**: Error message names `HOLO_ALLOW_PIP_INSTALL=1` and provides `pip install chromadb` manual instruction.

---

## D. Files Changed

| File | Lines Changed | Purpose |
|------|---------------|---------|
| `holo_index/core/holo_index.py` | +35, -6 | Add `_is_pip_install_allowed()`, flip default, update error message |
| `holo_index/tests/test_auto_pip_opt_in.py` | +233 (new) | 18 tests for fail-closed behavior |
| `docs/audits/holoindex_search_quality/HOLOINDEX_AUTO_PIP_OPT_IN_PHASE1.md` | +250 (new) | This audit doc |

---

## E. Per-Scenario Test Results

### E.1 `_is_pip_install_allowed()` Function Tests

| Test | Input | Expected | Result |
|------|-------|----------|--------|
| `test_default_not_allowed` | (all unset) | False | PASS |
| `test_allow_pip_install_1_allowed` | HOLO_ALLOW_PIP_INSTALL=1 | True | PASS |
| `test_allow_pip_install_true_allowed` | HOLO_ALLOW_PIP_INSTALL=true | True | PASS |
| `test_allow_pip_install_TRUE_allowed` | HOLO_ALLOW_PIP_INSTALL=TRUE | True | PASS |
| `test_allow_pip_install_yes_allowed` | HOLO_ALLOW_PIP_INSTALL=yes | True | PASS |
| `test_allow_pip_install_0_not_allowed` | HOLO_ALLOW_PIP_INSTALL=0 | False | PASS |
| `test_allow_pip_install_false_not_allowed` | HOLO_ALLOW_PIP_INSTALL=false | False | PASS |
| `test_allow_pip_install_no_not_allowed` | HOLO_ALLOW_PIP_INSTALL=no | False | PASS |
| `test_disable_pip_install_overrides_allow` | HOLO_ALLOW=1, DISABLE=1 | False | PASS |
| `test_offline_overrides_allow` | HOLO_ALLOW=1, OFFLINE=1 | False | PASS |

### E.2 Error Message Tests

| Test | Purpose | Result |
|------|---------|--------|
| `test_error_message_names_env_var` | Message contains "HOLO_ALLOW_PIP_INSTALL=1" | PASS |
| `test_error_message_gives_manual_install_hint` | Message contains "pip install chromadb" | PASS |

### E.3 Subprocess Behavior Tests

| Test | Purpose | Result |
|------|---------|--------|
| `test_chromadb_importable_no_subprocess` | When chromadb exists, no subprocess | PASS |
| `test_opt_in_triggers_subprocess_when_import_fails` | Opt-in + missing → would trigger | PASS |
| `test_no_opt_in_no_subprocess_when_import_fails` | No opt-in + missing → no trigger | PASS |

### E.4 Regression Tests

| Test | Purpose | Result |
|------|---------|--------|
| `test_holoindex_class_importable` | HoloIndex class still imports | PASS |
| `test_collection_health_importable` | collection_health module still imports | PASS |
| `test_search_engine_importable` | search_engine module still imports | PASS |

**Total**: 18/18 PASS

---

## F. Test Execution Summary

```bash
pytest holo_index/tests/test_auto_pip_opt_in.py -v
# Result: 18 passed

pytest holo_index/tests/test_collection_health.py -v
# Result: 27 passed

pytest holo_index/tests/ -v
# Result: 154 passed (total)
```

---

## G. Indexer Impact Analysis

All 6 indexers are UNAFFECTED by this change:

| Indexer | File | chromadb Import Path | Impact |
|---------|------|---------------------|--------|
| code_indexer | `holo_index/core/code_indexer.py` | Via holo_index.py | None (import unchanged) |
| wsp_indexer | `holo_index/core/wsp_indexer.py` | Via holo_index.py | None (import unchanged) |
| docs_indexer | `holo_index/core/docs_indexer.py` | Via holo_index.py | None (import unchanged) |
| symbol_indexer | `holo_index/core/symbol_indexer.py` | Via holo_index.py | None (import unchanged) |
| work_ledger_indexer | `holo_index/core/work_ledger_indexer.py` | Via holo_index.py | None (import unchanged) |
| vocabulary_indexer | `holo_index/core/vocabulary_indexer.py` | Via holo_index.py | None (import unchanged) |

The change only affects the initial `import chromadb` path in `holo_index.py`. Once chromadb is installed (manually or via opt-in), all indexers function identically.

---

## H. CLI Surface Unchanged

| CLI Command | Behavior | Changed? |
|-------------|----------|----------|
| `python holo_index.py --search` | Requires chromadb | NO |
| `python holo_index.py --index` | Requires chromadb | NO |
| `python holo_index.py --collection-health` | Requires chromadb | NO |
| `python holo_index.py --index-work-ledger` | Requires chromadb | NO |

All CLI commands require chromadb. The change affects HOW chromadb becomes available, not WHAT depends on it.

---

## I. Chain-of-Thought / Chain-of-Action / Chain-of-Evidence (CoT/CoA/CoE)

### I.1 Chain-of-Thought (Reasoning)

This is a subprocess security boundary fix because:
- Default behavior spawned `pip install chromadb` without consent
- This violates fail-closed security principles
- Network calls and subprocess spawns require explicit operator consent
- The fix inverts the default: no action unless explicitly allowed

### I.2 Chain-of-Action

| Step | Action | Mutates Code? |
|------|--------|---------------|
| 1 | Read holo_index.py chromadb import block | NO |
| 2 | Design `_is_pip_install_allowed()` function | NO |
| 3 | Implement fail-closed default | YES |
| 4 | Update error message | YES |
| 5 | Create test_auto_pip_opt_in.py | YES (new file) |
| 6 | Run test suite | NO |
| 7 | Write audit doc | NO (new file) |

### I.3 Chain-of-Evidence

| Evidence | Source | Value |
|----------|--------|-------|
| Before default | holo_index.py (pre-fix) | Auto-install enabled |
| After default | holo_index.py (post-fix) | Auto-install disabled |
| Function added | holo_index.py:33-44 | `_is_pip_install_allowed()` |
| Tests pass | pytest | 18/18 |
| Error message | holo_index.py:58-60 | Names env var + manual hint |

---

## J. Completion Summary

| Item | Value |
|------|-------|
| Branch | `feat/holoindex-auto-pip-opt-in-phase1` |
| Base commit | `bf14adcb5` |
| Files changed | 3 |
| Worker-Lane | W6 |
| Slice | HOLOINDEX_AUTO_PIP_OPT_IN_PHASE1 |
| Before default | Auto-install enabled |
| After default | Auto-install disabled (fail-closed) |
| Opt-in env var | HOLO_ALLOW_PIP_INSTALL=1\|true\|yes |
| Override env vars | HOLO_DISABLE_PIP_INSTALL=1, HOLO_OFFLINE=1 |
| Tests | 18/18 passed |
| WSP_97 | PASS (28/28) |
| Authorizing worker packet | W6 HOLOINDEX_AUTO_PIP_OPT_IN_PHASE1 |

---

**Worker**: W6
**Slice**: HOLOINDEX_AUTO_PIP_OPT_IN_PHASE1
**WSP Lock**: WSP_00 → WSP_15 → WSP_50 → WSP_64 → WSP_83 → WSP_87 → WSP_97 → WSP_22 → WSP_93
