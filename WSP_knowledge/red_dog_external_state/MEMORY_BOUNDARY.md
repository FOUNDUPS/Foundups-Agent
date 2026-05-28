# Memory Boundary - What CAN and MUST NOT Be Remembered

**Purpose**: Define the curated/forbidden boundary for RedDog session continuity.

## What CAN Be Remembered

- **PR chain lineage**: Merged PRs with one-line summaries
- **Slice completion records**: Which slices completed, key decisions
- **Architectural decisions**: ADRs, WSP amendments, scope rulings
- **Carry-forward queues**: Next-slice IDs from session closeout
- **Worker lane assignments**: Which lanes are active, role assignments
- **Research thread status**: Open investigations with named next actions

## What MUST NOT Be Remembered

### Secrets (Non-Negotiable)

- API keys: `AIza*`, `sk-*`, `hf_*`, `ghp_*`, `gho_*`, `github_pat_*`
- OAuth tokens, refresh tokens, JWTs, bearer strings
- `.env` key=value pairs (especially `*_SECRET`, `*_KEY`, `*_TOKEN`)
- Database connection strings with credentials
- Stream keys, OBS passwords, YouTube API keys
- Personal email addresses (except committer's)

### Raw Content (Curated Summaries Only)

- Raw assistant/user transcripts (role-by-role dialogue)
- Multi-paragraph brain artifact copies
- DPO/SFT training data format examples
- Absolute paths to private directories (repo-relative OK)

## Precedent References

- **PR #720**: Redaction protocol for OBS WebSocket secrets
- **PR #724**: Session validator rules (SCHEMA.md redaction section)
- **SCHEMA.md**: Field-by-field contract including redaction rules

## Validator Enforcement

The validator at `modules/infrastructure/wre_core/scripts/validate_session_closeout.py`:

1. Rejects secret-pattern matches
2. Rejects raw transcript markers (`"assistant":`, `"user":`, `"role":`)
3. Rejects `work_summary` over 2000 characters
4. Exits non-zero on any violation

## Slice Chain

- Created by: `REDDOG_BOOTSTRAP_CONTEXT_RETRIEVAL_PHASE1`
- Linked to: BOOTSTRAP.md read-order position 1
