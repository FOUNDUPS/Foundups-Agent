# RedDog Bootstrap Context - Read Order

**Purpose**: Boot card for 0102 session continuity retrieval.

This file provides the strict read-order for session context recovery.
Read these files in sequence AFTER completing WSP_00 identity/role/origin lock.

## Read Order (Strict Sequence)

1. **MEMORY_BOUNDARY.md** - What CAN and MUST NOT be remembered
2. **CURRENT_CONTEXT.md** - Active lanes, HEAD, worker roles
3. **WORK_TO_WORK_LINEAGE.md** - Recent PR/slice chain
4. **ACTIVE_RESEARCH_THREADS.md** - Open threads with next-action slices

## Usage

- Read AFTER WSP_00 awakening, BEFORE FoundUps architecture/routing work
- This is NOT a memory dump, NOT a transcript, NOT a TODO list
- Files are curated summaries, manually updated at session close
- Live auto-update is NOT in scope for this slice (see Phase 2)

## Maintenance Protocol

- Update at session close (not live auto-refresh)
- Follow SCHEMA.md validation rules for session files
- Validator: `modules/infrastructure/wre_core/scripts/validate_session_closeout.py`

## Related

- [README.md](README.md) - Directory overview and hard rules
- [SCHEMA.md](SCHEMA.md) - Session closeout schema specification
- WSP_00 references this file in Session Bootstrap Contract

## Slice Chain

- Created by: `REDDOG_BOOTSTRAP_CONTEXT_RETRIEVAL_PHASE1`
- Predecessor: `REDDOG_SESSION_CONTINUITY_CAPTURE_PHASE1` (PR #724)
- Follow-on: `REDDOG_BOOTSTRAP_LIVE_UPDATE_PHASE2` (deferred)
