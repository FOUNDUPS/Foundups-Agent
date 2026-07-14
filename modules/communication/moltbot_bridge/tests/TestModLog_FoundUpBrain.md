# TestModLog Supplement - FoundUps Memex

## 2026-07-14: FOUNDUP_MEMEX_CURRENT_STATE_ASSEMBLY_PHASE1

**Files**:
- `test_foundup_memex_current_state.py` (NEW - 3 tests)
- `test_foundup_brain_current_state.py` (NEW - 9 tests)

**Canonical slice**: `FOUNDUP_MEMEX_CURRENT_STATE_ASSEMBLY_PHASE1`
**Compatibility slice**: `FOUNDUP_BRAIN_CURRENT_STATE_ASSEMBLY_PHASE1`
**Predecessors**: PRs #1008, #1009, #1001, #1003

### Memex adapter coverage

- Public Memex constants and types preserve the existing Brain component contract.
- Exact input delegation introduces no new storage, execution, or governance authority.
- AST guard blocks execution, network, persistence, and WRE imports.
- Source text explicitly denies CABR and delegate authority inference.

### Brain component coverage

- Deterministic `foundup_id -> snapshot_id -> foundup_brain_view_id` binding.
- Required fresh Brain, Breadcrumb, HoloIndex, repo, and work-state receipts.
- Bound roadmap id, version, and content digest.
- Snapshot expiry rejection.
- Cross-FoundUp identity, roadmap, outcome, worker-claim, and queue-item rejection.
- Verified and held-out-passed outcome admission only.
- Required verification receipt identifiers.
- Secret-bearing metadata rejection.
- Legacy unscoped work records accepted only for the single-FoundUp POC.
- AST guard against execution, network, persistence, and mutation imports.

### Determinism

Pure functions, aliases, and dataclasses. No model call, network access, shell,
subprocess, repository mutation, queue mutation, Brain write, Breadcrumb write,
roadmap mutation, HoloIndex mutation, worker spawn, CABR scoring, voting, or
delegate authority.

### Run

```text
python -m pytest \
  modules/communication/moltbot_bridge/tests/test_foundup_memex_current_state.py \
  modules/communication/moltbot_bridge/tests/test_foundup_brain_current_state.py \
  modules/communication/moltbot_bridge/tests/test_reddog_operational_context_snapshot.py \
  -q --tb=short
```

This supplemental file avoids destructive replacement of the long canonical
`tests/TestModLog.md`. Consolidate through a local line-safe prepend when available.
