# Active Research Threads - Open Investigations

**Purpose**: Track open research threads with named next-action slices.

**Maintenance**: Update at session close (not live auto-refresh).

## Open Threads

### T1 Ranking Quality (HoloIndex)

- **Status**: Phase 1 audit in progress
- **Artifacts**: `docs/audits/holoindex_search_quality/HOLOINDEX_T1_RANKING_QUALITY_PHASE1.md`
- **Tests**: `holo_index/tests/test_t1_ranking_quality.py`
- **Next slice**: T1 ranking implementation based on audit findings

### Cursor Adapter

- **Status**: Explicitly deferred per PR #724 architect ruling
- **Blocker**: Requires separate discovery of Cursor app database
- **Next slice**: `CURSOR_ADAPTER_DISCOVERY_PHASE1` (not yet dispatched)

### Cleanup Execution

- **Status**: Worktree artifact cleanup validated
- **Predecessor**: `WORKTREE_AUTONOMOUS_ARTIFACT_CLEANUP_DECISION_PHASE1`
- **Next slice**: Pending execution decision

### Bootstrap Live Update

- **Status**: Explicitly deferred per architect ruling
- **Blocker**: This slice establishes seeded-only protocol
- **Next slice**: `REDDOG_BOOTSTRAP_LIVE_UPDATE_PHASE2`

## Closed Threads (Recent)

| Thread | Resolution | PR |
|--------|------------|-----|
| Session continuity capture | Storage layer complete | #724 |
| OBS secret redaction | Redaction protocol merged | #720 |
| ANTIFAFM startup boundary | Auto-start block removed | #721 |

## Seeded State Notice

This file is SEEDED, not live-updated. Content reflects session start threads.
Live auto-refresh deferred to `REDDOG_BOOTSTRAP_LIVE_UPDATE_PHASE2`.

## Slice Chain

- Created by: `REDDOG_BOOTSTRAP_CONTEXT_RETRIEVAL_PHASE1`
- Linked to: BOOTSTRAP.md read-order position 4
