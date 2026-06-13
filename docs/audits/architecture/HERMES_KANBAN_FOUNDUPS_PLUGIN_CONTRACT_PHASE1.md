# Hermes Kanban FoundUps Plugin Contract -- Phase 1 (Decision-Only)

- Slice: HERMES_KANBAN_FOUNDUPS_PLUGIN_CONTRACT_PHASE1
- Worker-Lane: A / AUTHOR | Base SHA: ed3ad2066 (origin/main after #801)
- Type: READ-ONLY contract definition. ONE doc + ONE root ModLog entry. Decision-only.
  No code, no runtime wiring, no vendoring, no submodule change, no Kanban install.
- Predecessor: HERMES_KANBAN_FORK_STATUS_AND_WRE_SURFACE_AUDIT_PHASE1 (PR #803, OPEN) --
  established the surface-not-authority verdict and that the Kanban code is in neither
  vendored-and-present location.
- Method: WSP_00 / WSP_50 / WSP_97. Merge: STOP at MERGE_READY (external 0102 gate authorizes LAND).

## 1. Mission

Define the FoundUps plugin boundary for Hermes Kanban: what data WRE may PUBLISH into Kanban, what a
Kanban worker may RETURN, what Kanban is FORBIDDEN to decide, and what adapter surface is needed --
BEFORE any vendoring or runtime wiring. The mental model is NOT "use Kanban as WRE"; it is "build a
FoundUps/WRE plugin-adapter so Hermes workers can run FoundUps-shaped work without Kanban becoming the
authority."

This slice DEFINES the contract; it builds nothing. The contract is what a later vendoring decision and
adapter implementation must satisfy.

## 2. Layered Architecture

    Hermes Kanban        -- external surface / board / worker process manager (SQLite + dispatcher + OS-process workers)
    FoundUps Kanban Plugin -- translates Kanban tasks <-> WRE slice contracts (THIS contract defines its boundary)
    WRE / OpenClaw       -- AUTHORITY for dispatch, WSP, gates, source_authority, ContextBundle
    Hermes worker        -- executes ONE bounded task from a ContextBundle / prompt pack
    LAND / SENTINEL / W10 -- merge and truth-boundary governance; repo/WSP/PR are the source of truth

The plugin is a thin ADAPTER. It never holds authority; it carries WRE-authored work out to the board and
worker results back in, with WRE deciding every state transition.

## 3. The Plugin's Three Functions (and ONLY these three)

### 3.1 Publish work to Kanban (WRE -> card; one-way)

WRE emits a card from a dispatched slice. The card is a PROJECTION of WRE-authored state; the worker may
read it but may not treat any field as an authorization.

| Card field | Source (WRE authority) | Meaning |
|---|---|---|
| `slice_id` | WRE dispatch | The slice this card represents |
| `lane` | WRE state -> lane map (#803 Section 6) | todo/ready/running/blocked/done -- set BY WRE, not the worker |
| `contextbundle_id` | ContextBundle (#775/#786) `bundle_id` | The ONLY work-package authority for the task |
| `required_gates` | manifest `required_gates` / `gates_to_recheck` | Gates the work must pass (genesis/manifest/dry_run/test/D0-D6/typed_exec/no_live_launch/sovereign_valve) |
| `allowed_paths` | manifest `safe_mutation_surface` | The worker's permitted mutation surface; everything else is forbidden |
| `forbidden_paths` | manifest `forbidden_paths` | main.py / *_dae.py / secrets / registry / etc. |
| `branch` / `worktree` | WRE | Isolated worktree-per-task (aligns with Kanban `worktree` workspace) |
| `expected_evidence` | evidence-ref schema (path, sha256, size_bytes, role) | What the worker must return -- refs, not bodies |
| `risk_class` | WRE | DOCS_DECISION_ONLY vs SPINE_CODE (drives the land path) |

The card carries NO gate-pass booleans, NO source_authority promotion, NO merge token. It is a work
description plus the pointer to its ContextBundle.

### 3.2 Constrain workers (the fence)

A Kanban worker is a bounded executor, not a free agent. The contract REQUIRES:

- The worker receives a ContextBundle (via `contextbundle_id`), NOT raw repo authority. No ContextBundle =
  no work (a card without a resolvable bundle is `blocked`, never executed).
- No arbitrary task picking: the worker executes the card it is assigned; it does not self-select or
  re-scope. (Kanban's own dispatcher auto-pick must be disabled or fenced -- see #803 Section 8.)
- No self-promotion from card metadata: nothing the worker writes into card/metadata can grant itself a
  gate pass, a source_authority stage, or merge rights.
- No merge authority: the worker stops at MERGE_READY; LAND/SENTINEL/W10 merge.
- No real execution unless a WRE gate says so: dry-run is the default; real execution requires the WRE
  gate (HERMES_DELEGATE_ENABLED + destructive-action guard + sovereign valve), never a Kanban flag.
- Mutation only within `allowed_paths`; `forbidden_paths` are hard-denied.

### 3.3 Ingest evidence back (Kanban -> WRE; advisory until verified)

On completion the worker returns an evidence packet (Kanban `kanban_complete` metadata maps onto it). WRE
decides the resulting state transition; Kanban does not.

| Evidence field | Meaning |
|---|---|
| `slice_id` / `contextbundle_id` | Binds the result to the dispatched work |
| `pr_url` / `head_sha` | The PR opened and its head commit (re-verified against the repo by WRE) |
| `tests_run` | Test command(s) + pass/fail counts (re-runnable by WRE) |
| `wsp97_rows` | The WSP_97 checklist rows + statuses claimed |
| `artifact_refs` | refs only: `{path, sha256, size_bytes, role}` -- never file bodies |
| `changed_files` | Declared diff surface (checked against `allowed_paths`) |
| `residual_risk` / `blocked_reason` | Honest carry-forward, mapped to Kanban `blocked` when set |

Redaction is REQUIRED before storage (reuse #768 `redact_sensitive`): no tokens/secrets/OAuth/raw env in
returned stdout/stderr or notes. The packet is ADVISORY -- it is not trusted as truth until WRE verifies
it against the repo/PR/WSP_97 (the EVIDENCE_RETURNED_NOT_TRUSTED_UNTIL_WRE_VERIFIED rule).

## 4. What Kanban Is FORBIDDEN to Decide

- WSP compliance (WRE/SENTINEL decides).
- SourceAuthority stage promotion (stays `monorepo_poc`; cannot self-promote).
- ContextBundle validity / bypass (the resolver + validator are authority).
- Real execution authorization (WRE gate only).
- PR merge (LAND/W10 only).
- Dispatch/scheduling of FoundUps build work as a second orchestrator.
- Canonical state: the Kanban SQLite DB is a derived view; repo/WSP/PR is the source of truth.

## 5. The Adapter Surface Needed (spec; build nothing)

The minimal plugin adapter (a FoundUps-owned module, future slice) needs exactly three operations,
mirroring Section 3:

- `publish_slice_card(slice, context_bundle) -> card_id` -- WRE -> Kanban (`kanban_create`), one-way; no
  authority leaves WRE.
- `constrain_worker(card) -> WorkerTaskSpec` -- emits the bounded task (ContextBundle ref + allowed_paths +
  required_gates + dry-run default); the worker prompt-pack is derived from the ContextBundle, not the repo.
- `ingest_result(kanban_metadata) -> WreEvidencePacket` -- Kanban -> WRE, redacted, advisory; WRE verifies
  before any state transition.

The adapter imports NO Kanban authority primitive (no dispatcher control, no DB-as-truth). It must be
AST-fenced from queue mutators and real-exec (same denylist pattern as the manifest validator / module-path
resolver / the autonomous_slice_worker non-orchestration constraint).

## 6. Mapping to Existing WRE Primitives (reused vs net-new)

REUSED (already in the repo): ContextBundle (`context_bundle_builder.py`, `bundle_id`, `source_authority`,
`evidence_refs`, `gates_to_recheck`, `readiness_flags`); FoundUpJob + JobStatus
(`foundup_job_contract.py`); the one-way publish precedents (`work_completion_publisher`, the
`github_orchestrator` FAM->board mirror, `public_catalog_projector`); #768 EvidencePacket + `redact_sensitive`
for the return path; LAND/SENTINEL (`autonomous_slice_worker` SKILLz); FAM `VERIFICATION_RECORDED` for the
receipt.

NET-NEW (future slices, NOT now): the three adapter operations in Section 5; the WRE-state -> Kanban-lane
publisher; a fenced kanban-worker profile bounded to a ContextBundle.

## 7. Trust Model: Evidence Returned Is Not Truth

The single load-bearing rule: a Kanban worker's returned evidence is ADVISORY and untrusted until WRE
re-verifies it against the repo/PR/WSP_97. The worker can CLAIM tests passed, a PR is open, gates were met
-- WRE re-runs/re-reads to confirm before any state transition or land. This is the same separation that
makes the autonomous-verifier not a second brain: the executor proposes; the authority verifies.

## 8. Forbidden Directions (this slice)

No code, no adapter implementation, no Kanban install/vendoring, no `.gitmodules`/`vendor/` change, no
runtime wiring, no dispatcher control, no real execution. This slice only DEFINES the contract.

## 9. Verdict and Ordered Next Slices

Verdict: the plugin-adapter boundary is well-formed and sits entirely on the surface-not-authority side of
the #803 ruling. PLUGIN_ADAPTER_BEFORE_VENDORING: define this contract first; the vendoring choice depends
on which Kanban source can satisfy it.

1. (this) HERMES_KANBAN_FOUNDUPS_PLUGIN_CONTRACT_PHASE1 -- decision-only contract.
2. HERMES_KANBAN_VENDORING_DECISION_PHASE1 -- decide which source (newer FOUNDUPS/hermes-agent with the
   official SQLite kanban vs FOUNDUPS/foundups-agent-workspace) can satisfy THIS contract; re-verify remotes.
3. HERMES_KANBAN_PLUGIN_CONTRACT_IMPL_PHASE1 -- pure typed contract module (CardSpec / WorkerTaskSpec /
   WreEvidencePacket dataclasses + validator + tests), AST-fenced, no Kanban import, no wiring.
4. WRE_TO_KANBAN_CARD_PUBLISHER_PHASE1 -- one-way publisher (dispatch off).
5. KANBAN_FENCED_WORKER_PILOT_PHASE1 -- one ContextBundle-bounded worker, stops at MERGE_READY.

## 10. Operator Decision Points

- ODP-1: prompt-pack derivation -- should the worker prompt-pack be derived ONLY from the ContextBundle, or
  may it include a read-only repo snapshot? (Recommend: ContextBundle + read-only refs; never raw write authority.)
- ODP-2: evidence re-verification depth -- does WRE re-RUN tests on ingest, or re-READ the PR/CI only?
  (Trade-off: cost vs trust. Recommend: re-read PR/CI + spot re-run for SPINE_CODE.)
- ODP-3: which Kanban source (ODP carried from #803) -- gates the vendoring slice; the contract is
  source-agnostic by design.

## 11. Internal Sentinel Review

An independent adversarial SENTINEL (separate lane from the author) attacked all eight load-bearing claims
by direct read; all SURVIVE, none refuted. Confirmed: Kanban is held as surface/board/worker-manager with
WRE as sole authority (Section 4 forbids WSP/promotion/bypass/real-exec/merge/scheduling/DB-canonical);
"No ContextBundle = no work" and the worker receives a bundle not raw repo authority; nothing written to
card/metadata grants a gate pass / source_authority / merge; the worker stops at MERGE_READY and real
execution requires the WRE gate (never a Kanban flag); returned evidence is ADVISORY until WRE re-verifies
against repo/PR/WSP_97; `git status` is exactly two files (this doc + root ModLog) with zero
`.py`/`.gitmodules`/`vendor/`/adapter artifacts; the contract is ordered before vendoring; and all eight
operator-required WSP_97 rows are present and YES (canonical header, Declared 18 == 18 rows, 0 non-ASCII).
Internal Review Verdict: READY. Blocking findings: NONE. This verdict does not authorize merge -- the
external 0102 gate does.

## 12. WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | KANBAN_SURFACE_NOT_AUTHORITY | YES | Sections 2,4: Kanban is surface/board/worker-manager; authority list forbidden. |
| 2 | WRE_OWNS_DISPATCH_STATE | YES | Section 3.1: lane set by WRE; Section 4: no Kanban scheduling/state authority. |
| 3 | CONTEXTBUNDLE_REQUIRED_FOR_WORKER | YES | Section 3.2: no ContextBundle = no work; Section 3.1 `contextbundle_id` is the work-package authority. |
| 4 | KANBAN_METADATA_CANNOT_SELF_AUTHORIZE | YES | Section 3.2: no self-promotion from card/metadata; Section 4. |
| 5 | NO_MERGE_AUTHORITY | YES | Sections 3.2,4: worker stops at MERGE_READY; LAND/SENTINEL/W10 merge. |
| 6 | NO_REAL_EXECUTION_GATE_BYPASS | YES | Section 3.2: real exec only via WRE gate (HERMES_DELEGATE_ENABLED + guard + valve), never a Kanban flag. |
| 7 | EVIDENCE_RETURNED_NOT_TRUSTED_UNTIL_WRE_VERIFIED | YES | Sections 3.3,7: advisory packet; WRE re-verifies against repo/PR/WSP_97. |
| 8 | PLUGIN_ADAPTER_BEFORE_VENDORING | YES | Sections 1,9: contract defined first; vendoring depends on it. |
| 9 | DECISION_ONLY_NO_CODE | YES | Section 8: no code/adapter/typed module authored. |
| 10 | NO_RUNTIME_WIRING_OR_DISPATCH | YES | Section 8: no publisher/worker/dispatch wired. |
| 11 | NO_VENDORING_OR_SUBMODULE_CHANGE | YES | Section 8: no `.gitmodules`/`vendor/` change; diff = 2 docs. |
| 12 | REUSES_EXISTING_WRE_PRIMITIVES | YES | Section 6: ContextBundle/FoundUpJob/publishers/#768 redaction/LAND-SENTINEL/FAM. |
| 13 | REDACTION_REQUIRED_ON_RETURN | YES | Section 3.3: reuse #768 `redact_sensitive`; no secrets in returned output. |
| 14 | CITES_FORK_STATUS_AUDIT | YES | Predecessor #803 cited; surface-not-authority + lane map referenced. |
| 15 | NEXT_SLICES_ORDERED | YES | Section 9: 5 ordered slices (contract -> vendoring -> impl -> publisher -> pilot). |
| 16 | OPERATOR_DECISION_POINTS_EXPLICIT | YES | Section 10: ODP-1..3. |
| 17 | ASCII_CLEAN | YES | Byte-checked 0 non-ASCII before commit. |
| 18 | FILE_SCOPE_EXACTLY_TWO | YES | git diff = this doc + root ModLog. |

Declared 18 / Rows 18 / All YES.
