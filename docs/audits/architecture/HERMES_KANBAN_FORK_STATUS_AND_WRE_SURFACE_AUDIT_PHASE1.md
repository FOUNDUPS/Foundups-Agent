# Hermes Kanban Fork Status and WRE Surface Audit -- Phase 1 (Decision-Only)

- Slice: HERMES_KANBAN_FORK_STATUS_AND_WRE_SURFACE_AUDIT_PHASE1
- Worker-Lane: A / AUTHOR | Base SHA: ed3ad2066 (origin/main after #801)
- Type: READ-ONLY architecture audit. ONE audit doc + ONE root ModLog entry. Decision-only.
  No code, no runtime wiring, no submodule update, no vendoring, no integration.
- Method: WSP_00 / WSP_50 (pre-action) / WSP_97 (truth boundary)
- Merge: STOP at MERGE_READY. Not self-merged; external 0102 gate authorizes LAND.

Evidence-class key:
- [AV] Audit-verified in THIS repo at base ed3ad2066 (grep / git / file read).
- [XR] Verified-external: fetched from the official Hermes Agent docs (cited URL).
- [OP] Operator-provided (recorded as stated; not re-verified against a remote).

## 1. Mission

Determine whether `FOUNDUPS/hermes-agent` (vendored submodule) or
`FOUNDUPS/foundups-agent-workspace` (workspace fork) actually contains the
Kanban/swarm surface FoundUps could use as a durable WRE worker board -- and
whether that surface should be catalog-only, inspiration-only, or a governed
external worker surface. WRE/OpenClaw must remain the orchestration authority.

Verdict tested: KANBAN_AS_SURFACE_YES / KANBAN_AS_AUTHORITY_NO.

Bottom line: the useful Kanban code is in NEITHER vendored-and-present location.
The pinned `vendor/hermes-agent` fork carries no kanban; the workspace fork that
holds the swarm-kanban control plane is not cloned/vendored in this repo. So the
honest Phase-1 verdict is INSPIRATION + GOVERNED-EXTERNAL-CANDIDATE, NOT WIRE_NOW
and NOT EVEN VENDORED_YET. The surface-vs-authority contract below is the
governance a later, deliberate vendoring decision must satisfy.

## 2. Fork-Status Truth Boundary (the corrected reality)

| Claim | Status | Evidence |
|---|---|---|
| FOUNDUPS forked Hermes Agent and vendored it | TRUE | `.gitmodules`: `vendor/hermes-agent` -> `https://github.com/FOUNDUPS/hermes-agent.git` [AV] |
| The vendored fork is pinned | TRUE | `git submodule status`: `d1d425e9d0e0...` `(v2026.4.13-182-gd1d425e9)`; gitlink `160000 commit d1d425e9 vendor/hermes-agent` [AV] |
| The pinned vendored fork contains the Kanban feature | FALSE | grep `kanban`/`Kanban` over `vendor/hermes-agent` at the pinned SHA = ZERO matches [AV] |
| The pinned fork version predates the official SQLite kanban | TRUE (inference) | pinned v2026.4.13; the official kanban (SQLite + gateway dispatcher) is a newer hermes-agent feature [XR] |
| Local submodule is behind FOUNDUPS/hermes-agent/main by 2 commits | RECORDED | [OP] -- not re-verified against the fork remote (no network fetch performed) |
| FOUNDUPS forked the workspace/Kanban control plane | PLANNED, NOT PRESENT HERE | `FOUNDUPS_AGENT_WORKSPACE_FORK_PLAN.md:272` is an UNCHECKED checkbox "[ ] Fork outsourc-e/hermes-workspace to FOUNDUPS/foundups-agent-workspace"; `ROADMAP.md:205` "Source: Fork from outsourc-e/hermes-workspace (external, NOT cloned/vendored)" [AV] |
| `foundups-agent-workspace` / `hermes-workspace` code is in this repo | FALSE | grep across the repo (excluding vendor) returns ONLY docs that DESCRIBE the external repo; no `src/server/swarm-kanban-store.ts` and no submodule [AV] |
| The swarm-Kanban code location | EXTERNAL | `HERMES_WORKSPACE_EXTERNAL_REPO_AUDIT.md:134,150,286` places `src/server/swarm-kanban-store.ts` + persistence `~/.hermes/swarm2-kanban.json` in `outsourc-e/hermes-workspace` (external) [AV doc-grounded] |
| The workspace "fork plan" is current | STALE | `EXTERNAL_SWARM_OPENCLAW_HERMES_CURRENT_STATE_RECONCILIATION_PHASE1.md:128,158`: "v2 is zero-fork wrapper, not fork -- update doc" [AV] |

Net: there are THREE layers, and the Kanban surface is in the one NOT vendored here.

1. NousResearch upstream `hermes-agent` -- the official Kanban feature lives here (newer than the pin).
2. `FOUNDUPS/hermes-agent` @ `d1d425e9` (v2026.4.13), vendored at `vendor/hermes-agent` -- the runtime backend; NO kanban.
3. `outsourc-e/hermes-workspace` (+ a PLANNED `FOUNDUPS/foundups-agent-workspace`) -- the swarm-Kanban control-plane UI; NOT cloned/vendored in this repo.

## 3. What Hermes Kanban Is (verified external)

From the official Hermes Agent docs [XR] (https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban):

- Persistence: SQLite `~/.hermes/kanban.db` (per-board `~/.hermes/kanban/boards/<slug>/kanban.db`);
  tables `task_events` (append-only audit), `task_runs` (one row per attempt),
  `task_links` (parent->child edges).
- Task model: status enum `triage | todo | ready | running | blocked | done | archived`;
  fields incl. `assignee` (profile), `priority`, `scheduled_at`, `max_retries`,
  `current_run_id`, `idempotency_key`. Promotion rule: `todo -> ready` when all parents `done`.
- Workers: named OS processes, each "a full OS process with its own identity"
  (profile), env `HERMES_KANBAN_TASK` / `HERMES_KANBAN_BOARD`, terminal + file tools,
  auto-loaded `kanban-worker` skill.
- Tools (in-process, not shell): `kanban_show/list/complete/block/heartbeat/comment/create/link/unblock`.
  Handoff via `kanban_complete(summary, metadata={changed_files, verification, dependencies, blocked_reason, retry_notes, residual_risk})`.
- Workspaces: `scratch` (ephemeral tmp), `dir:<path>` (absolute, persistent), `worktree`
  (git worktree under `.worktrees/<id>/`, preserved) -- coding tasks use worktree.
- Dispatcher: gateway-embedded long-lived loop (`dispatch_in_gateway: true`, 60s); reclaims
  stale/crashed workers, promotes ready, atomically claims, spawns profiles; concurrency caps;
  auto-block after `failure_limit`. Standalone `hermes kanban daemon` is deprecated.
- Security: explicit "trusted-local-user threat model; kanban is single-host by design";
  "the worker runs with your uid"; dashboard plugin routes unauthenticated on localhost.

The `outsourc-e/hermes-workspace` wrapper [AV doc-grounded] adds a web UI + its own
`swarm-kanban-store.ts` with lanes `[backlog, ready, running, review, blocked, done]`
persisted to `~/.hermes/swarm2-kanban.json`, plus role lanes (builder/reviewer/docs/research/ops/triage/QA/lab).

## 4. Phase 0 HoloIndex + Internal Anchors

| # | Query | Rating | Anchor |
|---|-------|--------|--------|
| 1 | Hermes Kanban task board worker assignment surface | MEDIUM-HIGH | `worker_assignment_protocol.py`, `REAL_WORKER_ASSIGNMENT_PROTOCOL.md` (internal role assignment); no Kanban code (correct -- external) |
| 2 | WRE slice state task card publisher kanban | HIGH | `ai_intelligence/work_completion_publisher/` (an existing one-way publisher), `wre_monitor.py`, WSP_51 WRE_CHRONICLE |
| 3 | FoundUpJob ConsumerResult status work item board | HIGH | `foundup_job_contract.py` (JobStatus), `worker_queue_observability.py` |
| 4 | Hermes worker execute bounded task ContextBundle handoff | MEDIUM-HIGH | `hermes_foundup_job_executor.py`; HXA Hermes guard/token/scope audits (the execution fence) |
| 5 | kanban board persistence model task state | MEDIUM | `agent_market/persistence/sqlite_adapter.py` (FoundUps already uses SQLite), WSP_56/51/60 |

No query surfaced a Kanban code module in this repo -- consistent with Section 2. HoloIndex
located the authority layer (job contract, publisher, chronicle); the Kanban facts came from
the official doc and the external-repo audits by direct read.

## 5. The WRE Authority Layer (what FoundUps already owns)

- Orchestration authority: OpenClaw create -> `FoundUpJob` queue -> WRE `FoundUpJobConsumer` drain
  -> Hermes executor (dry-run SIMULATED). JobStatus = `queued | running | blocked | failed | succeeded`
  (`foundup_job_contract.py:85-113`).
- Work-package authority: the ContextBundle (#775/#786) -- the validated work definition; the shared
  resolver derives module_path from the validated manifest and stamps `source_authority=monorepo_poc`.
- Truth/evidence boundary: WSP_97; FAM is the append-only event log; receipts are refs+sha256.
- Merge governance: LAND / SENTINEL (the AUTHOR -> SENTINEL -> LAND loop;
  `holo_index/skillz/autonomous_slice_worker/SKILLz.md`). PRs in the repo are the source of truth.
- One-way publish precedent ALREADY in the repo: `ai_intelligence/work_completion_publisher/`, the
  `github_orchestrator` FAM listener (mirrors `task_state_changed -> move_card`), and the
  `public_catalog_projector` (#799/#801, projects the registry -> read-only public catalog). Each is a
  projection of authoritative WRE/registry state onto a surface -- never the reverse.

## 6. State Mapping: WRE state -> Kanban lanes

A one-way projection (WRE authoritative state -> Kanban display). Kanban lane changes that imply a
decision (promotion, done) must REFLECT WRE/PR/LAND truth, not be authored by Kanban's dispatcher.

| WRE / slice state | Kanban lane | Note |
|---|---|---|
| slice dispatched, deps unmet | `todo` | parents not yet `done` |
| FoundUpJob QUEUED, deps met | `ready` | `todo -> ready` when parents done |
| AUTHOR executing (worktree) | `running` | Kanban `worktree` workspace aligns with FoundUps worktree-per-slice |
| BLOCKED on a gate/dependency | `blocked` | `kanban_block(reason)` |
| SENTINEL review / MERGE_READY | `blocked` (escalated) | LAND is an external/human gate; stays blocked until LAND/`kanban_unblock` |
| LANDED (PR merged via LAND) | `done` | terminal; reflects an ACTUAL repo merge, not a Kanban mark |
| FAILED | `blocked` (retry) or `archived` | `task_runs.outcome` crashed/timed_out/gave_up |

Note the official lanes have NO `review` lane (that is the workspace-wrapper's). MERGE_READY maps to
`blocked` + a metadata handoff, so the LAND/SENTINEL gate is explicit, not a silent Kanban transition.

## 7. Surface vs Authority -- Boundary Analysis

Load-bearing distinction (one sentence): Hermes Kanban is an ALLOWED governed SURFACE when it
displays WRE-authored state and runs only bounded executor tasks whose work-package is a WRE
ContextBundle and whose completion stops at MERGE_READY for LAND -- and it becomes a FORBIDDEN
AUTHORITY the moment its dispatcher schedules FoundUps build work independently, its workers act
outside WRE gates, or its SQLite DB is treated as canonical over the repo/WSP/PR.

KANBAN_AS_SURFACE_YES: durable task board; worker-assignment/role surface (AUTHOR/SENTINEL/LAND/CRITIC/
RESEARCH map to profiles); dependency graph (`task_links`); blocked/ready/running/done visibility;
durable comments + handoffs; retry/run history; worktree-per-task discipline; an operator dashboard
that does NOT make 012 a runtime gate.

KANBAN_AS_AUTHORITY_NO: it must NOT decide WSP compliance; promote SourceAuthority stage; bypass
ContextBundle validation; launch real execution directly; merge PRs without LAND/W10; become a
parallel WRE scheduler; or treat its DB as canonical state over repo/WSP/PR evidence.

## 8. The Dispatcher / Second-Orchestrator Conflict

The single sharpest risk: Hermes Kanban ships its OWN gateway-embedded dispatcher that atomically
claims tasks and SPAWNS OS-process workers every 60s [XR]. That is a scheduler. Pointed at FoundUps
build work it is a SECOND orchestrator competing with OpenClaw -> FoundUpJob -> WRE consumer -- the
exact "no second brain" hazard ruled in the multi-agent evolution + autonomous-verification audits.
Compounding it: workers run with the local uid and full filesystem/tool access (trusted-local-user),
so an unfenced worker can mutate the repo, run real execution, or touch secrets OUTSIDE the WRE gates
(genesis/manifest/dry-run/destructive-action-guard/typed-exec/no-live-launch).

Only ONE dispatch authority may own FoundUps build work. Two governed options (Phase-1 prefers (a)):

- (a) SURFACE-ONLY: Kanban dispatch DISABLED for FoundUps boards (no assignees / `dispatch_in_gateway`
  off); WRE remains the sole scheduler; Kanban is a read-only board WRE publishes into.
- (b) FENCED-WORKER (later pilot): Kanban dispatch enabled but each worker is a BOUNDED executor whose
  work-package is a WRE ContextBundle, AST-fenced from queue mutators and real-exec, completing at
  MERGE_READY (`kanban_block` -> LAND); the worker never decides WSP/source-authority/merge.

## 9. One-Way Publisher Architecture (safe first integration; build nothing now)

Reuse the existing projection pattern (work_completion_publisher / github_orchestrator FAM mirror /
public_catalog_projector):

    WRE/FAM authoritative state (FoundUpJob, ContextBundle, PR/LAND)
      -> one-way publisher  [kanban_create / kanban_comment]
      -> Hermes Kanban board (display + bounded worker assignment)
      -> bounded handoff metadata back  [kanban_complete metadata: changed_files, verification, residual_risk]
      -> ADVISORY evidence into WRE (like a SENTINEL receipt), gated by WSP_97 + LAND -- never authority

Reused vs net-new: REUSE the publisher/projector pattern, FoundUpJob/JobStatus, the ContextBundle, the
SENTINEL/LAND gate, worktree-per-task. NET-NEW (future, not now): a WRE->Kanban card publisher; a
fenced kanban-worker profile bounded to a ContextBundle; a vendoring decision for the Kanban code.

## 10. Forbidden Directions

- Do NOT vendor/clone/submodule the Kanban code in this slice (decision-only).
- Do NOT update `vendor/hermes-agent` or change `.gitmodules`.
- Kanban dispatcher must NOT schedule FoundUps build work as a second orchestrator.
- Kanban workers must NOT run outside WRE gates (no ContextBundle bypass, no real exec, no secrets).
- Kanban SQLite DB must NOT be treated as canonical over repo/WSP/PR.
- Kanban must NOT promote SourceAuthority or merge PRs without LAND/W10.
- No `--host 0.0.0.0` exposure of the (unauthenticated) Kanban dashboard plugin.

## 11. Verdict

KANBAN_AS_SURFACE_YES / KANBAN_AS_AUTHORITY_NO.

Recommendation: GOVERNED_EXTERNAL_WORKER_BOARD_CANDIDATE -- but qualified by fork status:
INSPIRATION_AND_GOVERNED_EXTERNAL_CANDIDATE, NOT WIRE_NOW, and NOT_EVEN_VENDORED_YET. The Kanban
surface is a strong external model for FoundUps' durable worker board (durable task rows, named worker
profiles, worktree-per-task, parent-child dependencies, reviewer/synthesizer handoffs, retry history,
dashboard visibility) -- but the code is in neither vendored-and-present location, and its dispatcher +
trusted-local-user worker model would bypass WRE unless fenced. NOT CATALOG_ONLY (it is a real worker
runner, not merely a catalog); NOT WIRE_NOW (no fence, no publisher, code not vendored).

## 12. Ordered Next Slices

1. (this audit) HERMES_KANBAN_FORK_STATUS_AND_WRE_SURFACE_AUDIT_PHASE1 -- decision-only.
2. HERMES_KANBAN_VENDORING_DECISION_PHASE1 -- decide WHICH source carries the surface to adopt
   (newer FOUNDUPS/hermes-agent with the official SQLite kanban, vs FOUNDUPS/foundups-agent-workspace),
   and whether to vendor as a submodule; re-verify the fork remotes (the "2 commits behind" claim).
3. WRE_TO_KANBAN_CARD_PUBLISHER_PHASE1 -- one-way publisher (WRE emits cards; read-only; dispatch off).
4. KANBAN_FENCED_WORKER_PILOT_PHASE1 -- a single bounded kanban-worker profile executing one
   ContextBundle, AST-fenced from queue mutators + real-exec, completing at MERGE_READY.
5. (later) bounded handoff-metadata ingestion back into WRE as advisory evidence.

## 13. Operator Decision Points

- ODP-1: WHICH fork carries the surface to adopt -- update `vendor/hermes-agent` to a newer
  FOUNDUPS/hermes-agent that has the official SQLite kanban, OR vendor `FOUNDUPS/foundups-agent-workspace`
  (the swarm-Kanban control plane)? They are different surfaces (SQLite kanban vs JSON swarm-kanban).
- ODP-2: surface-only first (dispatch off) vs a fenced-worker pilot -- 012's risk tolerance for letting a
  Kanban worker execute under the trusted-local-user model.
- ODP-3: where the board's durable state lives relative to the repo -- confirm the repo/WSP/PR remain
  canonical and the Kanban DB is a derived view (not a second source of truth).
- ODP-4: dashboard exposure -- keep localhost-only (the plugin routes are unauthenticated by design).

## 14. Internal Sentinel Review

An independent adversarial SENTINEL (separate lane from the author) re-verified every load-bearing claim
against the real repo. All SURVIVE; none refuted. It independently re-ran the evidence: `.gitmodules` ->
FOUNDUPS/hermes-agent, `git submodule status` d1d425e9 (v2026.4.13); `vendor/hermes-agent` is fully
checked out (1706 files) yet `grep -ri kanban` = 0 (the ZERO claim is meaningful, not an empty tree); the
workspace fork is referenced by exactly 5 files, ALL `.md` docs (no `src/`, no submodule, no `.gitmodules`
entry); the verdict's WIRE_NOW tokens are all negated (no drift); the working tree is exactly the audit
doc + root ModLog (no `.gitmodules`/`vendor/`/code/submodule change); the surface-vs-authority distinction
is a single testable sentence (Section 7) with concrete forbidden powers (Section 10); the dispatcher
("single sharpest risk", second-orchestrator) and trusted-local-user gate-bypass are stated in strong
terms (Section 8); the "2 commits behind" claim is honestly labeled [OP]/unverified; and the WSP_97 table
is canonical (declared 20 == 20 rows, all YES, 0 non-ASCII). Internal Review Verdict: READY. Blocking
findings: NONE. Per the merge boundary this verdict does not authorize merge -- the external 0102 gate does.

## 15. WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | KANBAN_AS_SURFACE_YES | YES | Sections 7,11: governed surface (board/roles/deps/handoffs/worktree). |
| 2 | KANBAN_AS_AUTHORITY_NO | YES | Sections 7,10: no WSP/source-authority/merge/scheduler/canonical-DB authority. |
| 3 | FORK_STATUS_VERIFIED_FROM_REPO | YES | Section 2: .gitmodules, submodule status d1d425e9, grep evidence. |
| 4 | VENDORED_HERMES_AGENT_HAS_NO_KANBAN | YES | grep vendor/hermes-agent at pin = 0 kanban hits. |
| 5 | WORKSPACE_FORK_NOT_PRESENT_HERE | YES | Only docs; FORK_PLAN unchecked; ROADMAP "external, NOT cloned/vendored". |
| 6 | KANBAN_CODE_LOCATION_IDENTIFIED | YES | Section 2: external outsourc-e/hermes-workspace; official kanban newer than pin. |
| 7 | EXTERNAL_FACTS_SOURCED | YES | Section 3 [XR] official doc; wrapper facts [AV doc-grounded]; "2 behind" [OP]. |
| 8 | WRE_REMAINS_ORCHESTRATION_AUTHORITY | YES | Section 5: OpenClaw->FoundUpJob->WRE->Hermes; ContextBundle work-package authority. |
| 9 | STATE_MAPPING_DEFINED | YES | Section 6: WRE state -> Kanban lanes (one-way). |
| 10 | ONE_WAY_PUBLISHER_FIRST | YES | Section 9: reuse publisher/projector pattern; dispatch off first. |
| 11 | DISPATCHER_NOT_A_SECOND_WRE_SCHEDULER | YES | Section 8: only one dispatch authority; surface-only option (a). |
| 12 | WORKERS_FENCED_NO_GATE_BYPASS | YES | Sections 8,10: trusted-local-user risk; fenced-worker = ContextBundle-bounded, AST-fenced. |
| 13 | KANBAN_DB_NOT_CANONICAL | YES | Sections 7,10,ODP-3: repo/WSP/PR canonical; DB is a derived view. |
| 14 | NO_SUBMODULE_OR_VENDORING_CHANGE | YES | Decision-only; no .gitmodules / vendor/ change; diff = 2 docs. |
| 15 | NO_RUNTIME_WIRING | YES | No publisher/worker/dispatch built; spec-only. |
| 16 | VERDICT_NOT_WIRE_NOW | YES | Section 11: INSPIRATION + GOVERNED-CANDIDATE; not WIRE_NOW; not vendored yet. |
| 17 | NEXT_SLICES_ORDERED | YES | Section 12: 5 ordered slices (vendoring decision first). |
| 18 | OPERATOR_DECISION_POINTS_EXPLICIT | YES | Section 13: ODP-1..4. |
| 19 | ASCII_CLEAN | YES | Byte-checked 0 non-ASCII before commit. |
| 20 | FILE_SCOPE_EXACTLY_TWO | YES | git diff = this doc + root ModLog. |

Declared 20 / Rows 20 / All YES.
