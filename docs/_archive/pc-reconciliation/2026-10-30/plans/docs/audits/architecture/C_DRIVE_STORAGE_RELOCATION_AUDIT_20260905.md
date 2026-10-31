# Preserved historical record: C_DRIVE_STORAGE_RELOCATION_AUDIT_20260905.md

> Historical/proposal material. This is not a current acceptance receipt, runtime check or instruction to apply old code. The original dates and claimed outcomes below retain their historical scope.

- Original relative path: `docs/audits/architecture/C_DRIVE_STORAGE_RELOCATION_AUDIT_20260905.md`
- Original PC base: `0c81418fe94a7786cfd55f01e138ddc5d510583d`
- Original full file SHA-256: `3e73ed16af8f2d7246cbccc7252e838310d158c53d88d9a733fdf565f48d4c82`
- Preserved record SHA-256: `3e73ed16af8f2d7246cbccc7252e838310d158c53d88d9a733fdf565f48d4c82`
- Projection created: `2026-10-30T02:00:12.626831+00:00` (processing time only; not a new observation)
- Comparison reference: `cbef41fbae1ba1105398183e42b008f2e7dfd3dc`
- Publication: proposed; independent auditor acceptance pending.
- Current owner(s): [extract_brain_artifacts.py](../../../../../../../../modules/infrastructure/wre_core/scripts/extract_brain_artifacts.py)

Disposition: Publish a sanitized historical relocation inventory and decision method; exact host/profile layout remains in private custody. Its sizes, processes and completed junction actions are September claims only. Any new relocation needs current observations and a separate recovery checkpoint.

Private host paths and unresolved external identifiers may be omitted only in this projection; raw originals remain in the private custody backmap. External citations are retained as historical references and have not been refreshed. Runtime and commenting remain unverified.

## Historical content

# C: Drive Storage Relocation Audit

**Audit ID**: `C_DRIVE_STORAGE_RELOCATION_AUDIT_20260905`  
**Date**: 2026-09-05  
**Owner**: 0102 architect  
**Authorization origin**: 012 requested an audit, assessment, relocation, maximum safe relief, and WSP 97 application  
**Execution plane**: Local Windows system operations; WRE is not applicable to the relocation itself  
**WSP lock**: WSP 00, WSP 50, WSP 64, WSP 84, WSP 97

## 1. Problem Statement

The Windows C: volume is critically full. The measured baseline was 0.88 GiB free
of 464.25 GiB (0.19%). Windows Storage classified approximately 200 GB as
"Other" and identified user-local tool state as the dominant source.

The goal is to recover capacity without deleting authoritative Foundups-Agent
work, active Codex state, credentials, models, or personal files.

## 2. Evidence and Truth Classification

| Claim | Evidence | Classification |
|---|---|---|
| Foundups-Agent is rooted on O: | Git worktree and current working directory resolve to `[PRIVATE_HOST_PATH_OMITTED]` | `VERIFIED_LOCAL` |
| HoloIndex storage is intended for E: | `main.py` defaults `HOLO_SSD_PATH` to `[PRIVATE_HOST_PATH_OMITTED]`; repository configuration points there | `VERIFIED_REPO` |
| C: is critically full | `Get-Volume` measured 0.88 GiB free of 464.25 GiB | `VERIFIED_RUNTIME` |
| Codex archive is the dominant safe relocation candidate | `robocopy /L /E /BYTES` measured 781 files and 163,017,412,676 bytes under `[PRIVATE_HOST_PATH_OMITTED]` | `VERIFIED_RUNTIME` |
| Active Codex sessions are materially smaller | Per-directory inventory measured `sessions` at 6.15 GiB | `VERIFIED_RUNTIME` |
| O: has capacity for Codex archives | `Get-Volume` measured 743.16 GiB free after the interrupted partial copy | `VERIFIED_RUNTIME` |
| E: has capacity for local-model data | `Get-Volume` measured 606.17 GiB free | `VERIFIED_RUNTIME` |
| Foundups maintenance storage optimization is operational | `optimize_storage()` uses hard-coded demo values and performs no storage audit or relocation | `SPECIFIED_NOT_IMPLEMENTED` |
| HoloIndex supplied current retrieval evidence | Owner query returned `ok=false`, `freshness=UNKNOWN`, `index_gap_detected=true`, and `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH` | `RETRIEVAL_DEGRADED` |

The failed HoloIndex query was not treated as repository truth and no reindex was
performed. Direct repository reads were used as the declared degraded fallback.

## 3. Foundups-Agent Storage Audit

### Correctly placed

- Repository and current checkout: O:
- HoloIndex model/index convention: E:
- Repository-local memory and SQLite paths: relative to the O: checkout

### Gaps

- `modules/infrastructure/dae_infrastructure/maintenance_operations_dae`
  contains the existing cleanup/storage LEGO block, but `perform_cleanup()` and
  `optimize_storage()` are simulated.
- That module is missing `README.md`, `INTERFACE.md`, `ROADMAP.md`, `ModLog.md`,
  `requirements.txt`, `tests/README.md`, and `tests/TestModLog.md`. WSP_CORE's
  Tier-0 rule blocks implementation until at least README and INTERFACE memory
  are present.
- Generated validation artifacts record a C:-resident Codex runtime path. This
  is evidence of the current environment, not proof that Foundups-Agent owns
  or creates the runtime cache.
- The external Codex Desktop store has no repository-owned retention guard, so
  archived session files grew without a local capacity threshold.

## 4. Relocation Inventory

| Source | Measured size | Proposed target | Treatment |
|---|---:|---|---|
| `[PRIVATE_HOST_PATH_OMITTED]` | 151.82 GiB | `[PRIVATE_HOST_PATH_OMITTED]` | Copy, compare, atomic rename, junction, then remove verified backup |
| `[PRIVATE_HOST_PATH_OMITTED]` | 11,930,457,895 bytes | `[PRIVATE_HOST_PATH_OMITTED]` | Stop Ollama; verified relocation with junction |
| `[PRIVATE_HOST_PATH_OMITTED]` | 5,653,428,215 bytes | `[PRIVATE_HOST_PATH_OMITTED]` | Ensure LM Studio stopped; verified relocation with junction |
| `[PRIVATE_HOST_PATH_OMITTED]` | 4,105,727,908 bytes | `[PRIVATE_HOST_PATH_OMITTED]` | Stop Antigravity/Gemini writers; verified relocation with junction |
| `[PRIVATE_HOST_PATH_OMITTED]` | 3,751,482,475 bytes | `[PRIVATE_HOST_PATH_OMITTED]` | Stop Cursor and child writers; verified relocation with junction |

Current active `.codex` configuration, credentials, SQLite databases, plugins,
and `sessions` remain on C: in this slice.

## 5. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|---|
| A1 | Archived Codex sessions are inactive historical data | Directory role and separation from current `sessions` | HIGH |
| A2 | A same-path NTFS directory junction is transparent to consumers | C:, O:, and E: are healthy NTFS volumes | HIGH |
| A3 | O: is the correct bulk-history tier | O: holds Foundups-Agent and has 743.16 GiB free | HIGH |
| A4 | E: is the correct local-model tier | Existing HoloIndex model convention and 606.17 GiB free | HIGH |
| A5 | Current Codex operation does not require archived history files | Current session is stored separately and no live-root move is planned | MEDIUM |

## 6. Failure Modes

| ID | Failure mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| F1 | Copy is incomplete or corrupt | LOW | HIGH | Compare file count/bytes and run a no-copy mirror comparison before cutover |
| F2 | An application writes during migration | MEDIUM | HIGH | Stop relevant writer processes; migrate Codex archive only while leaving live state untouched |
| F3 | Junction points to the wrong destination | LOW | HIGH | Resolve and verify the exact junction target before deleting the source backup |
| F4 | Source deletion removes unverified data | LOW | CRITICAL | Rename source to an explicit backup; delete only after destination and junction checks pass |
| F5 | O: or E: is unavailable later | LOW | MEDIUM | Preserve stable original paths through junctions; report dependency on the destination volume |
| F6 | Existing uncommitted repo work is overwritten | LOW | HIGH | Do not reset, clean, stage, or modify unrelated dirty worktree files |

## 7. Alternatives Considered

| Alternative | Verdict | Reason |
|---|---|---|
| Delete Codex archives | Rejected | Maximum relief but destructive and loses potentially useful history |
| Move the whole live `.codex` root | Rejected for this slice | Risks the running task, credentials, state databases, and plugins |
| Set `CODEX_HOME` and restart immediately | Deferred | Clean long-term option, but changing the live root requires a controlled app restart and migration of active state |
| Move only `archived_sessions` with a junction | Selected | Recovers most capacity while minimizing the active surface |
| Delete model/tool data | Rejected | Models and agent state are useful; relocation preserves them |

## 8. WSP 97 Dialectic and Decision

### Micro pass

The exact pressure point is the inactive Codex archive directory, not the
Foundups-Agent checkout or active Codex session store.

### Macro pass

The surrounding system has three storage tiers: C: for Windows and small live
profiles, O: for repository/history data, and E: for model/index data. Tool
defaults have bypassed that tiering and require a governed relocation pattern.

### First-principles decision

Preserve data, change only its physical tier, keep the original logical path,
and validate before source removal. The first implementation layer is the
Codex archive relocation because it yields approximately 152 GiB while touching
no live Codex configuration.

**Decision**: `PROCEED` with the Codex archive layer. Proceed with other tool
directories only after their writers are stopped and each layer passes the
same copy/compare/junction verification.  
**Owner**: 0102 architect  
**Timestamp**: 2026-09-05T03:56:00+09:00

## 9. Acceptance Evidence Required

- Source and destination totals match: 781 files and 163,017,412,676 bytes.
- Comparison reports zero failed files, zero mismatches, and zero pending copies.
- `[PRIVATE_HOST_PATH_OMITTED]` resolves as a junction to the exact O: target.
- A sample of archive files is readable through both destination and junction.
- C: free-space measurement increases by approximately the source allocation.
- Active Codex task remains operational.
- Repository dirty state is unchanged except for this authorized audit and later scoped implementation files.

## 10. Execution Results

- `C:` recovered from 0.88 GiB free (0.19%) to 177.41 GiB free (38.21%).
- All five original paths resolve as exact NTFS junctions to their selected
  [PRIVATE_HOST_PATH_OMITTED] destinations. Each source was copied and compared before cutover; each
  redundant backup was removed only after zero-copy mirror verification.
- The Ollama API is reachable after relocation and reports four models,
  including `qwen-overseer:latest` and `gemma2:2b`. LM Studio's CLI runs through
  the junction; Gemini and Cursor configuration markers are readable through
  their original paths.
- The Foundups OpenClaw bridge now uses the installed `qwen-overseer:latest`
  model and a bounded 120-second default cold-start timeout. A live
  `_execute_conversation()` call returned `0102: CODEBASE_OLLAMA_OK` through
  `engine=ollama`.
- Full module validation: `106 passed, 2 warnings` in 43.20 seconds. The two
  warnings are existing pytest configuration warnings. During validation, a
  pre-existing fail-open downgrade from blocked command to model conversation
  was exposed and changed to an immediate deterministic security block.
- Final truth classification: `VALIDATED_OPERATIONAL` for this machine's
  relocation, junctions, local Ollama runtime, and tested OpenClaw path;
  cross-host deployment remains unclaimed.
