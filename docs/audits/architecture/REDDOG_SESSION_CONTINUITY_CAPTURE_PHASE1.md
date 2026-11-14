# RedDog Session Continuity Capture - Phase 1

**Slice**: `REDDOG_SESSION_CONTINUITY_CAPTURE_PHASE1`
**Worker**: W6
**Date**: 2026-05-27
**Mode**: Infrastructure (new capability, not refactor)
**Branch**: `feat/reddog-session-continuity-capture-phase1`
**Base commit**: `84314016` (origin/main)
**Predecessors**:
  - PR #720 `OBS_WEBSOCKET_SECRET_LOGGING_FIX_PHASE1` (secret-safety pattern)
  - PR #721 `MAIN_MENU_ANTIFAFM_STARTUP_BOUNDARY_FIX_PHASE1` (boundary pattern)
  - PR #723 `WORKTREE_AUTONOMOUS_ARTIFACT_CLEANUP_DECISION_PHASE1` (coordination - OPEN)

---

## 1. Mission and Scope

### Mission

Create a curated, manually-imported continuity channel for work happening in
RedDog, ChatGPT, Cursor, and other external AI tools that the Antigravity brain
extractor does not watch.

### Why

The Antigravity brain artifact extractor at
`modules/infrastructure/wre_core/scripts/extract_brain_artifacts.py`
hardcodes its source to `C:\Users\user\.gemini\antigravity\brain`.

Since work moved to Cursor/ChatGPT/RedDog lanes on 2026-05-25T08:43:51, the
`WSP_knowledge/reasoning_traces/brain_artifact_*` files have been stale.
The system did not break - it is watching the wrong source.

### Scope

This slice creates STRUCTURE + manual import path only. It does NOT:
- Scrape browser tabs
- Read Cursor's local app database
- Store raw transcripts
- Move/rename the existing Antigravity extractor
- Make HoloIndex or WRE consume RedDog external state (deferred)

---

## 2. HoloIndex Retrieval Evaluation

### Searches Performed

```bash
python holo_index.py --search "reasoning trace brain artifact session continuity"
# Result: extract_brain_artifacts.py, wre_master_orchestrator.py top hits

python holo_index.py --search "session closeout ledger memory persistence"
# Result: sqlite_adapter.py, session_utils.py, chat_memory_manager.py top hits
```

### Retrieval Quality

| Metric | Rating | Notes |
|--------|--------|-------|
| Relevance | Good | Found brain artifact extractor and memory systems |
| Ordering | Good | Key files in top 5 |
| Missing | None critical | All required docs found via explicit paths |
| Noise | Low | Results highly relevant |

---

## 3. Memory-Gap Evidence

### Stale Since

`WSP_knowledge/reasoning_traces/brain_artifact_state.json` shows last scan:
`2026-05-25T08:43:51` (Antigravity brain)

### Uncaptured Work (2026-05-25 to 2026-05-27)

| PR | Slice | Lane |
|----|-------|------|
| #707-#715 | Vote PoC chain | Various |
| #717 | Shield GitHub onboarding | W6 |
| #718 | WSP 109 hardening | W6 |
| #720 | OBS secret logging fix | W6 |
| #721 | AntifaFM startup boundary | W6 |
| #708 | IndexResult observability parity | W6 |
| #723 | Worktree artifact cleanup | W10 |

This work happened in Cursor/ChatGPT/RedDog and was invisible to the
Antigravity brain extractor.

---

## 4. Source-Agnostic Layout Design

### Directory Structure

```
WSP_knowledge/red_dog_external_state/
  README.md          # Human index, workflow docs
  SCHEMA.md          # JSON schema specification
  sessions/
    <captured_at>__<session_id>.json
```

### Schema Format Decision

**Chosen**: JSON

**Rationale**:
1. Python stdlib support (`json` module)
2. Deterministic validation (no ambiguous YAML types)
3. No new dependency required
4. Easier secret pattern scanning

### Future Adapters (Reserved, Not Built)

- `WSP_knowledge/cursor_external_state/` - Cursor sessions
- `WSP_knowledge/external_state_common/` - Shared schema

---

## 5. Curated Schema

See [SCHEMA.md](../../../WSP_knowledge/red_dog_external_state/SCHEMA.md)

### Required Fields

| Field | Type |
|-------|------|
| `schema_version` | string |
| `record_type` | string (`reddog_session_closeout`) |
| `session_id` | string |
| `source` | enum |
| `captured_at` | ISO 8601 |
| `lane` | string |
| `work_summary` | string (max 2000 chars) |

---

## 6. Secret-Safety Rules

Based on PR #720 redaction precedent.

### Validator Rejects

- API keys: `AIza*`, `sk-*`, `hf_*`, `ghp_*`, `gho_*`, `github_pat_*`
- OAuth tokens, refresh tokens, bearer strings
- Env var patterns: `*_SECRET=*`, `*_KEY=*`, `*_TOKEN=*`
- Raw transcript markers: `"role": "assistant"`, `"role": "user"`

### Tests Cover

- `test_openai_key_detected`
- `test_google_api_key_detected`
- `test_github_pat_detected`
- `test_env_secret_pattern_detected`
- `test_role_assistant_detected`

---

## 7. Manual Import Workflow

See [README.md](../../../WSP_knowledge/red_dog_external_state/README.md)

1. At session end, create JSON following SCHEMA.md
2. Save under `sessions/<captured_at>__<session_id>.json`
3. Run validator:
   ```bash
   python modules/infrastructure/wre_core/scripts/validate_session_closeout.py \
     WSP_knowledge/red_dog_external_state/sessions/<file>.json
   ```
4. Exit 0 = safe to commit
5. Exit non-zero = fix issues

---

## 8. Out of Scope (Explicit)

| Item | Reason |
|------|--------|
| Browser scraping | Privacy, complexity |
| Cursor app DB reading | Local app, no stable API |
| Raw transcript storage | Privacy, size |
| Automated capture | Manual curation required |
| Antigravity extractor mutation | Separate concern |
| HoloIndex/WRE consumer integration | Future slice |

---

## 9. Carry-Forward Slices

| Slice | Purpose | Gate |
|-------|---------|------|
| `CURSOR_SESSION_ARTIFACT_ADAPTER_PHASE1` | Cursor session capture | Discovery + opt-in review |
| `REASONING_TRACES_SOURCE_AGNOSTIC_REFACTOR_PHASE1` | Multi-source consumption | If load-bearing |
| `REDDOG_SESSION_VALIDATOR_HARDENING_PHASE2` | Tighten secret patterns | v1 ships first |

---

## 10. Internal Review Verdict

**Verdict**: READY

**Checklist**:
- [x] Directory structure created
- [x] README.md documents workflow
- [x] SCHEMA.md defines JSON contract
- [x] Seed session file captures recent work
- [x] Validator implemented (read-only)
- [x] 29 tests pass
- [x] Validator exit 0 on seed file
- [x] No live network calls in validator/tests
- [x] No .env reads in tests
- [x] Antigravity extractor unchanged
- [x] PR #723 coordination documented

---

## 11. WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | REDDOG_CONTINUITY_CAPTURE_ONLY | YES | Only RedDog channel created |
| 2 | CURATED_NOT_RAW | YES | Schema enforces summary, rejects transcripts |
| 3 | JSON_SCHEMA_ONLY_NO_YAML | YES | SCHEMA.md specifies JSON |
| 4 | RESUME_EXISTING_BRANCH_OR_PR_IF_PRESENT | YES | Checked at start, none found |
| 5 | USES_012_NOT_USER_REFERENCE_DISCIPLINE | YES | No "user" in docs |
| 6 | CURATED_REPLACEMENT_FOR_RAW_BRAIN_ARTIFACTS | YES | This is the curated channel |
| 7 | MERGE_ORDER_COORDINATED_WITH_723 | YES | PR #723 OPEN, this merges first |
| 8 | NO_RAW_TRANSCRIPT_STORAGE | YES | Validator rejects transcript markers |
| 9 | NO_BROWSER_SCRAPING | YES | Manual import only |
| 10 | NO_CURSOR_APP_DB_READ | YES | Not implemented |
| 11 | NO_AUTOMATED_CAPTURE | YES | Manual workflow documented |
| 12 | MANUAL_IMPORT_ONLY | YES | README documents workflow |
| 13 | NO_ANTIGRAVITY_EXTRACTOR_MUTATION | YES | extract_brain_artifacts.py unchanged |
| 14 | PURELY_ADDITIVE_TO_REASONING_TRACES | YES | New directory, no existing changes |
| 15 | NO_SECRET_VALUES_IN_SEED_OR_TESTS | YES | Validator passes seed, tests use synthetic |
| 16 | VALIDATOR_REJECTS_SECRET_PATTERNS | YES | 5 secret detection tests pass |
| 17 | VALIDATOR_REJECTS_RAW_TRANSCRIPT_MARKERS | YES | 4 transcript detection tests pass |
| 18 | VALIDATOR_NO_MUTATION | YES | 2 no-mutation tests pass |
| 19 | NO_NETWORK_CALL_IN_VALIDATOR | YES | No imports that trigger network |
| 20 | NO_NETWORK_CALL_IN_TESTS | YES | All tests use tmp_path fixtures |
| 21 | NO_DOTENV_READ_IN_TESTS | YES | No dotenv imports |
| 22 | NO_DEPENDENCY_INSTALL | YES | Uses stdlib json, re, pathlib only |
| 23 | NO_CI_CHANGE | YES | No workflow files changed |
| 24 | NO_WSP_FRAMEWORK_MUTATION | YES | No WSP_*.md changed |
| 25 | NO_REGISTRY_MUTATION | YES | No registry files changed |
| 26 | NO_MANIFEST_MUTATION | YES | No manifest files changed |
| 27 | NO_PUBLIC_SURFACE_MUTATION | YES | No public/ changes |
| 28 | NO_DNS_CHANGE | YES | No DNS configuration |
| 29 | PRESERVES_PR_720_OBS_LOGGING_GUARD | YES | Not touched |
| 30 | PRESERVES_PR_721_STARTUP_BOUNDARY | YES | Not touched |
| 31 | CITES_PR_723_COORDINATION | YES | Documented in predecessors |
| 32 | FUTURE_CURSOR_ADAPTER_NAMED_BUT_NOT_BUILT | YES | Listed in carry-forward |
| 33 | NO_CONSUMER_INTEGRATION_YET | YES | HoloIndex/WRE not modified |
| 34 | NO_CABR_READY | YES | Not a CABR slice |
| 35 | NO_PAYOUT_READY | YES | Not a payout slice |
| 36 | NO_DAO_ACTIVATION | YES | No DAO changes |

**Verdict**: PASS (36/36)

---

## 12. Files Changed

| File | Change | Lines |
|------|--------|-------|
| `WSP_knowledge/red_dog_external_state/README.md` | NEW | ~80 |
| `WSP_knowledge/red_dog_external_state/SCHEMA.md` | NEW | ~95 |
| `WSP_knowledge/red_dog_external_state/sessions/2026-05-27T10-00-00Z__reddog-continuity-seed.json` | NEW | ~40 |
| `modules/infrastructure/wre_core/scripts/validate_session_closeout.py` | NEW | ~160 |
| `modules/infrastructure/wre_core/tests/test_validate_session_closeout.py` | NEW | ~240 |
| `modules/infrastructure/wre_core/ModLog.md` | EXTENDED | +35 |
| `modules/infrastructure/wre_core/tests/TestModLog.md` | EXTENDED | +25 |
| `docs/audits/architecture/REDDOG_SESSION_CONTINUITY_CAPTURE_PHASE1.md` | NEW (this file) | ~250 |

**Total**: 8 files

---

**Worker**: W6
**Slice**: REDDOG_SESSION_CONTINUITY_CAPTURE_PHASE1
**PR #723 State**: OPEN (coordination: this PR merges first)
