# Hermes Kanban Vendoring Decision -- Phase 1 (Decision-Only)

- Slice: HERMES_KANBAN_VENDORING_DECISION_PHASE1
- Worker-Lane: A / AUTHOR | Base SHA: ed3ad2066 (origin/main after #801)
- Type: READ-ONLY decision. ONE doc + ONE root ModLog entry. Decision-only.
  No vendoring, no submodule update, no fetch-into-tree, no wiring, no code.
- Predecessors: #803 (fork-status + surface-not-authority), #804 (plugin contract). Both OPEN.
- Method: WSP_00 / WSP_50 / WSP_97. Merge: STOP at MERGE_READY (external 0102 gate authorizes LAND).

## 1. Mission

Decide which substrate can satisfy the #804 FoundUps plugin contract with LEAST risk, before any code or
vendoring. The decision is the operator's (012's) to ratify; this audit produces the evidence-backed
recommendation and the conditions under which it would change.

Recommendation: OPTION D -- do not vendor yet; build the external adapter first. The value is the
board/workflow SURFACE, not code ownership; the FoundUps source of truth is already WRE / ContextBundle /
WSP / PR. Vendoring early would inherit a second scheduler and a second persistence model before the
plugin boundary (#804) is proven.

## 2. Decision Question and the Four Options

Which substrate backs the FoundUps Kanban plugin contract (#804)?

- A. Official Hermes Agent SQLite Kanban (upstream NousResearch) -- interact with the official
  `~/.hermes/kanban.db` board + `kanban_*` tools as-is.
- B. FOUNDUPS/hermes-agent updated to include the official Kanban (advance the vendored fork past the pin).
- C. FOUNDUPS/foundups-agent-workspace / `swarm-kanban` JSON surface (the web control-plane wrapper).
- D. Do not vendor; interact externally through CLI / API / export only (external adapter first).

## 3. Evaluation Criterion

The single criterion is: which option lets us satisfy the #804 plugin contract -- publish (WRE -> card),
constrain (ContextBundle-bounded worker), ingest (advisory evidence, WRE-verified) -- while keeping WRE the
authority, with the LEAST inherited risk (second scheduler, second persistence model, trusted-local-user
worker, integration surface area, reversibility).

## 4. Fork-State Inputs (re-verified at base)

- `.gitmodules` vendors `FOUNDUPS/hermes-agent` at `vendor/hermes-agent`; pinned `d1d425e9` (v2026.4.13).
  grep over the pinned submodule = ZERO kanban [AV, #803].
- `FOUNDUPS/hermes-agent` remote main = `0d25e1c1...` (read-only `ls-remote`), AHEAD of the pin (the pin is
  behind fork main, consistent with the "2 commits behind" claim). Whether fork main `0d25e1c1` CARRIES the
  official kanban is UNVERIFIED without a fetch (ls-remote returns SHAs, not tree content); deferred -- not
  load-bearing for Option D [AV: SHAs; kanban-in-fork-main UNVERIFIED].
- `FOUNDUPS/foundups-agent-workspace` is NOT cloned/vendored here -- only docs; `ROADMAP.md:205` "external,
  NOT cloned/vendored"; `FORK_PLAN` checkbox unchecked [AV, #803].
- The official SQLite kanban (`~/.hermes/kanban.db`, OS-process workers, gateway dispatcher, worktree-per-task,
  trusted-local-user) is a NEWER hermes-agent feature than the pin [XR official doc, this session].
- The workspace wrapper's `swarm-kanban-store.ts` persists to `~/.hermes/swarm2-kanban.json` (a different,
  JSON surface) [AV doc-grounded, #803].

## 5. Option-by-Option Evaluation

| Option | Satisfies #804 contract? | Inherited risk | Effort / reversibility | Verdict |
|---|---|---|---|---|
| A. Official SQLite kanban as-is | Yes, in principle | HIGH: its own gateway dispatcher (second scheduler) + OS-process workers (trusted-local-user) + SQLite as a second state store; must be fenced | Medium; external dependency on upstream; reversible if kept external | Viable later; not first |
| B. Advance FOUNDUPS/hermes-agent to include kanban | Yes, if fork main carries it (UNVERIFIED) | HIGH (same as A) PLUS submodule advance = vendored second scheduler/persistence INSIDE the repo; harder to keep fenced | Higher; submodule bump + re-pin + re-verify; less reversible (vendored) | Premature -- requires fetch + verification first |
| C. foundups-agent-workspace / swarm-kanban JSON | Partially -- it is a UI/control-plane wrapper, not the SQLite board; different persistence (JSON) | MEDIUM-HIGH: wrapper + its own swarm dispatch; "v2 is zero-fork wrapper" (stale fork plan); not vendored | High to adopt; not present here | Not first; reconcile wrapper-vs-official before considering |
| D. Do not vendor; external CLI/API/export adapter | Yes -- the #804 plugin's 3 ops can run over an external boundary with NO vendored scheduler/persistence | LOWEST: no second scheduler/persistence inherited; WRE stays the only authority; trusted-local-user worker stays OUTSIDE the repo trust boundary | Lowest; fully reversible (nothing vendored); proves the plugin boundary first | RECOMMENDED |

## 6. Recommendation: Option D (external adapter first; do not vendor yet)

Build the FoundUps plugin adapter (#804) against an EXTERNAL Kanban boundary (CLI / API / export), with
nothing vendored. This proves the publish / constrain / ingest contract and the surface-not-authority
boundary before we inherit any external scheduler or persistence model. Concretely:

- WRE publishes cards to an external board through the adapter (one-way); the adapter holds no authority.
- A Kanban worker (external process) receives a ContextBundle-bounded task; WRE owns the gates.
- The worker returns an evidence packet; WRE re-verifies before any state transition (advisory-until-verified).
- The FoundUps repo / WSP / PR / WRE remain the sole source of truth and the only scheduler.

If and when the external boundary proves the contract, a LATER, deliberate slice can reconsider A or B with
the fence already validated.

## 7. Why Not A / B / C Now

- Not B now: advancing the vendored fork inherits the gateway dispatcher + OS-process worker model + SQLite
  state INSIDE the repo before the fence is proven, and it is the least reversible; and fork main carrying
  kanban is still UNVERIFIED (needs a fetch).
- Not A/C first: both still attach an external scheduler/persistence; doing them before the plugin boundary
  is validated risks the exact "second orchestrator + trusted-local-user gate-bypass" hazard #803 flagged.
- All of A/B/C remain open AFTER D proves the contract; D is the least-risk, fully-reversible first step.

## 8. What "External Adapter First" Means (no vendoring)

Interact with Kanban as an external tool over a boundary (its CLI / API / a JSON/DB export), the same way
FoundUps already projects to external surfaces (`work_completion_publisher`, the `github_orchestrator` FAM
mirror, `public_catalog_projector`). The adapter is a FoundUps-owned, AST-fenced module that speaks the
#804 contract; it imports no Kanban authority primitive and never updates the submodule.

## 9. Boundaries (this slice)

Decision-only. No vendoring, no submodule update, no fetch-into-working-tree, no `.gitmodules`/`vendor/`
change, no adapter code, no Kanban install, no runtime wiring. The read-only `ls-remote` performed for
Section 4 changed nothing in the tree or the pin.

## 10. Verdict and Ordered Next Slices

Verdict: OPTION D (external adapter first; do not vendor yet) -- least risk, fully reversible, proves the
#804 boundary first. WRE remains the authority; A/B/C stay open for a later, fence-validated decision.

1. (this) HERMES_KANBAN_VENDORING_DECISION_PHASE1 -- decision-only.
2. HERMES_KANBAN_PLUGIN_CONTRACT_IMPL_PHASE1 -- pure typed contract module: `KanbanCardSpec`,
   `WorkerTaskSpec`, `WreEvidencePacket` (+ validator + tests proving forbidden fields cannot carry
   authority); NO Hermes import, NO Kanban DB write, NO worker spawn, NO runtime wiring. The clean seam
   before touching either fork.
3. HERMES_KANBAN_EXTERNAL_ADAPTER_PILOT_PHASE1 -- the three adapter ops over an EXTERNAL boundary
   (CLI/API/export), dispatch off, one bounded ContextBundle task, stops at MERGE_READY.
4. (only if D proves out) HERMES_KANBAN_VENDORING_EXECUTION_PHASE1 -- re-open A/B with the fence validated;
   fetch + verify fork main kanban; re-pin.

## 11. Operator Decision Points

- ODP-1 (the ratification): confirm OPTION D (do not vendor yet; external adapter first). This audit
  recommends D on the evidence; 012 ratifies at the external gate.
- ODP-2 (flip conditions): name what would move the decision to B/A later -- e.g., the external boundary
  proves insufficient (latency, fidelity, or the worker genuinely needs in-repo tooling), AND the fence
  (one dispatch authority, ContextBundle-bounded worker, advisory-until-verified evidence) is validated.
- ODP-3 (fork-main kanban verification): when Option B is reconsidered, a future slice must FETCH
  `FOUNDUPS/hermes-agent` main (`0d25e1c1`) and verify whether it carries the official kanban + count the
  exact delta from the pin.

## 12. Internal Sentinel Review

An independent adversarial SENTINEL (separate lane from the author) attacked all claims by direct read and
LIVE repo cross-check; all SURVIVE. Confirmed: all four options are scored on contract-fit/risk/effort/
reversibility -- Option C gets a fair "Partially", A/B retain real later-viability (not strawmanned); the
criterion is the #804 publish/constrain/ingest surface-not-authority contract; Option D is recommended with
evidence-backed reasons and A/B/C stay open AFTER D; fork-state is re-verified against the real repo
(`git submodule status` = d1d425e9, `grep kanban vendor/hermes-agent` = 0, workspace fork not vendored) with
the fork-main kanban status honestly marked UNVERIFIED-without-fetch and non-load-bearing for D; `git status`
is exactly two files (decision doc + root ModLog) with no `.gitmodules`/`vendor/`/`.py` and the ls-remote
stated as read-only; and the decision is operator-ratified (012 confirms at the external gate). WSP_97 table
canonical, 16/16 all YES, 0 non-ASCII. Internal Review Verdict: READY. Blocking findings: NONE. This verdict
does not authorize merge -- the external 0102 gate does.

## 13. WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | DECISION_ONLY_NO_VENDOR_NO_WIRE | YES | Section 9: no vendoring/submodule/fetch-into-tree/code/wiring; diff = 2 docs. |
| 2 | FOUR_OPTIONS_EVALUATED | YES | Section 5: A/B/C/D each scored (contract-fit, risk, effort, reversibility). |
| 3 | EVALUATED_AGAINST_804_CONTRACT | YES | Section 3 criterion = the #804 publish/constrain/ingest boundary. |
| 4 | RECOMMEND_D_EXTERNAL_ADAPTER_FIRST | YES | Sections 6,10: Option D recommended, least-risk + reversible. |
| 5 | DO_NOT_VENDOR_YET | YES | Sections 6,7: no vendoring; A/B/C stay open after D. |
| 6 | PIN_HAS_NO_KANBAN_REVERIFIED | YES | Section 4: pinned d1d425e9 = 0 kanban (#803, re-stated). |
| 7 | FORK_MAIN_AHEAD_KANBAN_UNVERIFIED | YES | Section 4: fork main 0d25e1c1 ahead of pin; kanban-in-main UNVERIFIED without fetch. |
| 8 | WORKSPACE_FORK_NOT_VENDORED | YES | Section 4: only docs; ROADMAP "external, NOT cloned/vendored". |
| 9 | NO_SUBMODULE_UPDATE_OR_FETCH_INTO_TREE | YES | Section 9: ls-remote was read-only; pin + tree unchanged. |
| 10 | WRE_REMAINS_AUTHORITY | YES | Sections 6,8: WRE/ContextBundle/WSP/PR sole source of truth + scheduler. |
| 11 | EVIDENCE_BACKED_NOT_ASSERTED | YES | Section 4 cites [AV]/[XR]; UNVERIFIED items marked, not asserted. |
| 12 | OPERATOR_RATIFIES_VENDORING | YES | Section 11 ODP-1: 012 ratifies D at the external gate. |
| 13 | NEXT_SLICE_IS_CONTRACT_IMPL | YES | Section 10: #2 = HERMES_KANBAN_PLUGIN_CONTRACT_IMPL_PHASE1 (typed specs + tests). |
| 14 | CITES_803_804 | YES | Predecessors #803/#804 cited throughout. |
| 15 | ASCII_CLEAN | YES | Byte-checked 0 non-ASCII before commit. |
| 16 | FILE_SCOPE_EXACTLY_TWO | YES | git diff = this doc + root ModLog. |

Declared 16 / Rows 16 / All YES.
