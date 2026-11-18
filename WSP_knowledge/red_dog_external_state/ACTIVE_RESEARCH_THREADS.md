# Active Research Threads - Open Investigations

> **NON-AUTHORITATIVE HISTORICAL SNAPSHOT:** These were open investigations at
> capture time. They are not a live queue or proof of present runtime status.
> Revalidate each thread and next action against current owner evidence.

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

### Hermes Agent Runtime (WSL/Docker)

- **Status**: Bootstrapped + bounded; live delegation BLOCKED pending audits
- **Captured by**: `HERMES_WSL_DOCKER_BOOTSTRAP_CAPTURE_PHASE1` (session `2026-06-02T12-00-00Z__hermes-wsl-docker-bootstrap.json`)
- **State**: Hermes 0.15.1 in WSL Ubuntu, Docker terminal backend confirmed; OpenClaw import / Nous Portal login / messaging-gateway intentionally not enabled
- **Blocker**: WRE→`delegate_task` binding is RUNTIME_DEPENDENCY_MISSING + IMPORT_PATH_DRIFT (PR #745)
- **Next slices**:
  - `HERMES_NOUS_AGENT_DELEGATE_BINDING_AUDIT_PHASE1` (done — PR #745) → follow-on `HERMES_AGENT_RUNTIME_INSTALL_AND_PATH_AUDIT_PHASE1`
  - `HERMES_OPENCLAW_IMPORT_PREVIEW_AUDIT_PHASE1` (not yet dispatched)
  - `HERMES_POLICY_AND_TOOL_PERMISSION_AUDIT_PHASE1` (not yet dispatched)

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
