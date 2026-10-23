# RedDog External State - Session Continuity Capture

> **ARCHIVAL CONTEXT ONLY:** Files in this directory are manually curated
> snapshots, never live authority for Git HEAD, PR state, workers, runtimes, or
> HoloIndex freshness. WSP_00 may route here for continuity, but WSP 50 and
> WSP 97 require fresh evidence from each owning system before action.

**Canonical Red Dog vision:** `docs/REDDOG_OUTCOME_VISION.md`

**Slice**: `REDDOG_SESSION_CONTINUITY_CAPTURE_PHASE1`

This directory provides a curated, manually-imported continuity channel for work
happening in RedDog, ChatGPT, Cursor, and other external AI tools that the
Antigravity brain extractor does not watch.

## Purpose

The existing brain artifact extractor at
`modules/infrastructure/wre_core/scripts/extract_brain_artifacts.py`
hardcodes its source to `C:\Users\user\.gemini\antigravity\brain`.

Since work moved to Cursor/ChatGPT/RedDog lanes on 2026-05-25, the
`WSP_knowledge/reasoning_traces/brain_artifact_*` files have been stale.
This channel captures that work without coupling to the Antigravity extractor.

## What This Is

- **Curated summaries** of completed session work
- **PR chain tracking** across external tools
- **Decision records** for architectural choices
- **Carry-forward queues** for next-slice planning

## What This Is NOT

- Raw chat transcripts
- Browser scraping or automated capture
- Cursor app database reading
- A replacement for the Antigravity extractor

## Hard Rules (Non-Negotiable)

Session files MUST NOT contain:

- API keys (`AIza*`, `sk-*`, `hf_*`, `ghp_*`, `gho_*`, `github_pat_*`)
- OAuth tokens, refresh tokens, JWTs
- `.env` key=value pairs
- Database connection strings with credentials
- Personal email addresses (except committer's)
- Stream keys, OBS passwords, YouTube API keys
- Raw assistant/user transcripts (curated summaries only)

## Operator Workflow

1. At session end, create a JSON file following [SCHEMA.md](SCHEMA.md)
2. Save under `sessions/<captured_at>__<session_id>.json`
3. Run the validator:
   ```bash
   python modules/infrastructure/wre_core/scripts/validate_session_closeout.py \
     WSP_knowledge/red_dog_external_state/sessions/<your-file>.json
   ```
4. Validator exits 0 = safe to commit
5. Validator exits non-zero = fix issues before committing

## Directory Structure

```
WSP_knowledge/red_dog_external_state/
  README.md                      # This file (human index)
  SCHEMA.md                      # Field-by-field contract
  BOOTSTRAP.md                   # Historical boot card with strict read-order
  MEMORY_BOUNDARY.md             # What CAN and MUST NOT be remembered
  CURRENT_CONTEXT.md             # Historical lanes, HEAD, worker-role snapshot
  WORK_TO_WORK_LINEAGE.md        # Historical PR/slice-chain snapshot
  ACTIVE_RESEARCH_THREADS.md     # Historical research-thread snapshot
  sessions/
    <captured_at>__<session_id>.json
```

## Future Adapters (Not Built Here)

Reserved sibling directories for future source-specific adapters:

- `WSP_knowledge/cursor_external_state/` (gated by separate discovery)
- `WSP_knowledge/external_state_common/` (shared schema if multi-source)

## Related

- `docs/REDDOG_OUTCOME_VISION.md` - Canonical Red Dog outcome / north star
- [BOOTSTRAP.md](BOOTSTRAP.md) - Boot card with strict read-order (referenced by WSP_00)
- [SCHEMA.md](SCHEMA.md) - Session closeout schema specification
- [MEMORY_BOUNDARY.md](MEMORY_BOUNDARY.md) - Curated vs forbidden memory boundary
- [CURRENT_CONTEXT.md](CURRENT_CONTEXT.md) - Active session state snapshot
- [WORK_TO_WORK_LINEAGE.md](WORK_TO_WORK_LINEAGE.md) - PR/slice chain
- [ACTIVE_RESEARCH_THREADS.md](ACTIVE_RESEARCH_THREADS.md) - Open research threads
- `modules/infrastructure/wre_core/scripts/validate_session_closeout.py` - Validator
- `modules/infrastructure/wre_core/scripts/extract_brain_artifacts.py` - Antigravity extractor (unchanged)
- PR #723: `WORKTREE_AUTONOMOUS_ARTIFACT_CLEANUP_DECISION_PHASE1` (coordination)
- PR #724: `REDDOG_SESSION_CONTINUITY_CAPTURE_PHASE1` (storage layer)

## WSP Chain

- WSP 60 (Module Memory)
- WSP 87 (Code Navigation)
- WSP 22 (ModLog)
