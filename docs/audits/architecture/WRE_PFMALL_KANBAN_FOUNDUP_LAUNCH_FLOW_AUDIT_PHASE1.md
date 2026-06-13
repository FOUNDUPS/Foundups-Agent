# WRE / PFmall / Kanban FoundUp Launch Flow Audit -- Phase 1 (Decision-Only)

- Slice: WRE_PFMALL_KANBAN_FOUNDUP_LAUNCH_FLOW_AUDIT_PHASE1
- Window: W9 | Worker-Lane: A / AUTHOR | Base SHA: ed3ad2066 (origin/main after #801)
- Type: READ-ONLY architecture/design audit. Decision-only. ONE doc + ONE root ModLog entry.
  No code, no CLI/MCP/PFmall/adapter implementation, no Kanban vendoring, no submodule change,
  no repo provisioning, no manifest/registry/public_catalog mutation, no real execution.
- Predecessors (cited, not re-litigated): #803 (Kanban surface-not-authority + fork status),
  #804 (Kanban plugin contract publish/constrain/ingest), #805 (vendoring = Option D external-first),
  #802 (GetK monorepo PoC), #799/#801 (public_catalog_projector + /f/ browse).
- Method: WSP_00 / WSP_50 / WSP_97. Merge: STOP at MERGE_READY (external 0102 gate authorizes LAND).

Evidence-class: [AV] audit-verified in-repo at base; [XR] verified-external (official doc, prior session).

## 1. Mission

Define the full public-to-worker-to-PR-to-PFmall loop for creating a new FoundUp, using Hermes Kanban as
the worker surface while preserving WRE as the orchestration authority. Define the FoundUp Launch Flow
Contract and the launch state machine end-to-end; build nothing. This is the missing SYSTEM CONTRACT that
ties PFmall intake/status, WRE authority, the Kanban worker surface, and PR/registry projection together.

## 2. System Mental Model (roles + non-goals)

    PFmall     = public discovery + gated launch/intake + public status surface (NOT authority)
    WRE/OpenClaw = orchestration authority (dispatch, WSP, gates, source_authority, ContextBundle)
    Hermes Kanban = external worker board/surface (NOT orchestrator)
    Hermes worker = bounded executor of a ContextBundle-shaped task
    FoundUps repos / PRs / manifests / WSP = source of truth

Non-goals (forbidden): Kanban owns the system; PFmall creates code or repos; workers self-authorize
launches/merges/promotions; public input becomes code.

## 3. Phase-0 HoloIndex Results

| # | Query | Rating | Anchor (direct read confirmed) |
|---|-------|--------|--------------------------------|
| 1 | PFmall public catalog projector discovery browse intake | HIGH | `public_catalog_projector` (derived catalog), `pfmall_discovery`, `pfmall_catalog`, catalog truth-gate test |
| 2 | FoundUp proposal genesis intake LaunchRequest validate | HIGH | `ai_overseer/src/foundup_genesis/envelope.py` + `validator.py`; WSP 109 (Onboarding Intake Protocol) |
| 3 | ContextBundle dry-run consumer FoundUpJob validate_foundup | HIGH | `context_bundle_dry_run_consumer.py`, `context_bundle_builder.py` |
| 4 | source authority transition gate external repo provisioning | HIGH | `FOUNDUP_SOURCE_AUTHORITY_CONTRACT.md`, `HXA19_REPO_CREATION_APPROVAL_GATE.md`, WSP 100 |
| 5 | foundups CLI entrypoint launch publish project | MEDIUM | per-module `__main__.py` (projector), `foundups_sdk`; no unified `foundups` CLI yet |
| 6 | public catalog registry projection /f/ browse | LOW | degraded (CODE_LOCATION intent); resolved by direct read of the projector |
| 7-13 | (allowlist fields / genesis envelope / CardSpec / LAND / source_authority / PFmall intake / GetK) | MIXED | same anchor families; every load-bearing claim below is by direct read |

HOLOINDEX note: Q6 degraded and queries about not-yet-existing surfaces (intake, the CLI verbs) returned
the nearest existing module; absence (no intake, no unified CLI) was proven by direct read, not search.

## 4. The Controlled Closed Loop (load-bearing)

The system is a CONTROLLED CLOSED LOOP, not omnidirectional. It is bidirectional ONLY through four
governed seams; every other arrow is forbidden.

    [1] PFmall  -> WRE     : public LaunchRequest / FoundUpProposal ONLY (no code, no repo, no gate pass, no source_authority promotion)
    [2] WRE     -> Kanban  : WRE publishes bounded work cards; Kanban receives ContextBundle/CardSpec ONLY; Kanban does not select canonical work
    [3] Kanban  -> WRE     : workers return EvidencePacket + PR reference ONLY; evidence is ADVISORY until WRE/SENTINEL/LAND re-verifies
    [4] WRE     -> PFmall  : public status + catalog projection ONLY after PR/registry/manifest source-of-truth updates

Forbidden direct paths (each MUST be impossible by construction):
- PFmall -> Kanban (no public-to-worker path; only WRE publishes cards)
- Kanban -> PFmall (no worker-to-public path; only WRE projects status)
- public input -> repo/code (intake yields a proposal, never code or a repo)
- worker evidence -> public catalog without WRE verification (advisory cannot self-publish)
- Kanban DB -> canonical state (the board is a view, never the source of truth)

## 5. The Correct Flow (10 steps; authority owner per hop)

| # | Step | Authority owner | Crosses a governed seam? |
|---|------|-----------------|--------------------------|
| 1 | Public sees PFmall | PFmall (read-only projection) | - |
| 2 | Someone initiates "Launch a FoundUp" | PFmall intake (gated) | - |
| 3 | PFmall creates a typed LaunchRequest / FoundUpProposal (NOT code) | PFmall -> WRE [seam 1] | yes |
| 4 | WRE validates the proposal and creates a ContextBundle | WRE | - |
| 5 | WRE publishes bounded work cards to Kanban | WRE -> Kanban [seam 2] | yes |
| 6 | Kanban workers execute AUTHOR/SENTINEL/LAND-shaped work | Worker (ContextBundle-bounded) | - |
| 7 | Workers return evidence packets + PRs | Kanban -> WRE [seam 3] | yes |
| 8 | WRE / W10 / LAND verifies and merges | WRE / LAND | - |
| 9 | Registry / manifest / public projection update | WRE / Registry / projector | - |
| 10 | PFmall becomes populated with the new FoundUp | WRE -> PFmall [seam 4] | yes |

## 6. The FoundUp Launch Flow Contract (typed pipeline)

    PFmall LaunchRequest -> WRE FoundUpProposal -> ContextBundle -> Kanban CardSpec -> WorkerTaskSpec
      -> EvidencePacket -> PR -> Manifest/Registry -> public_catalog.json -> PFmall

| Arrow | Data that crosses | Owner | Forbidden to cross |
|---|---|---|---|
| LaunchRequest -> FoundUpProposal | name/problem/users/category/refs (Section 10) | PFmall intake -> WRE | code, repo request, secrets, gate/source_authority/merge tokens |
| FoundUpProposal -> ContextBundle | validated proposal (reused genesis envelope, Section 11) | WRE | self-promotion; external_repo_requested=true at genesis |
| ContextBundle -> CardSpec | bundle_id, required_gates, allowed/forbidden paths, branch/worktree, risk_class (#804) | WRE -> Kanban | gate-pass booleans, source_authority, merge token |
| CardSpec -> WorkerTaskSpec | the bounded task derived from the bundle (#804) | WRE/adapter | raw repo authority, arbitrary task pick |
| WorkerTaskSpec -> EvidencePacket | pr_url/head_sha/tests/wsp97_rows/artifact_refs, redacted (#804) | Worker | file bodies, secrets, self-authorization |
| EvidencePacket -> PR | the opened PR | Worker (proposes) | merge (LAND only) |
| PR -> Manifest/Registry | merged source-of-truth update | WRE/LAND | registry write by Kanban/worker/PFmall |
| Manifest/Registry -> public_catalog.json | allowlist-only derived projection (#799/#801) | projector | member-scoped/internal fields (leak guard) |
| public_catalog.json -> PFmall | public read-only catalog/status | PFmall | worker internals, advisory evidence |

## 7. The Launch State Machine

States, owner, allowed transition, required evidence, forbidden shortcut:

| State | Authority owner | Allowed transition | Required evidence | Forbidden shortcut |
|---|---|---|---|---|
| PUBLIC_DISCOVERY | PFmall | -> PROPOSAL_SUBMITTED | none (read-only browse) | jumping to code/repo |
| PROPOSAL_SUBMITTED | PFmall intake | -> PROPOSAL_VALIDATED or REJECTED | LaunchRequest shape (Section 10) | accepting code/secrets/tokens |
| PROPOSAL_VALIDATED | WRE | -> CONTEXTBUNDLE_CREATED or REJECTED | validated genesis envelope (external_repo_requested=False) | self-promotion of source_authority |
| CONTEXTBUNDLE_CREATED | WRE | -> KANBAN_PUBLISHED | ContextBundle (bundle_id, source_authority=monorepo_poc) | bypassing the validator/resolver |
| KANBAN_PUBLISHED | WRE (-> Kanban) | -> WORKER_IN_PROGRESS | CardSpec bound to the bundle | Kanban self-selecting canonical work |
| WORKER_IN_PROGRESS | Worker | -> EVIDENCE_RETURNED or BLOCKED | heartbeat/run | mutating outside allowed_paths; real exec without WRE gate |
| EVIDENCE_RETURNED | Worker -> WRE | -> PR_OPEN or BLOCKED | EvidencePacket (advisory, redacted) | treating evidence as truth |
| PR_OPEN | GitHub/PR + WRE | -> VERIFIED_READY or BLOCKED | PR url/head_sha re-read by WRE | merging without verify |
| VERIFIED_READY | SENTINEL | -> LANDED or BLOCKED | SENTINEL verdict + re-verified checks | self-merge by worker/Kanban |
| LANDED | LAND / W10 | -> REGISTRY_PROJECTED | merged PR (source-of-truth update) | landing without LAND/W10 |
| REGISTRY_PROJECTED | Registry + projector | -> PUBLIC_VISIBLE | allowlist-only derived public_catalog.json | direct catalog write |
| PUBLIC_VISIBLE | PFmall | (terminal; or back to DISCOVERY) | derived projection only | publishing worker internals |
| BLOCKED | WRE | -> prior state or REJECTED | blocked_reason | silent unblock by Kanban |
| REJECTED | WRE / PFmall intake | (terminal) | rejection reason | reviving without re-proposal |

WRE owns every transition decision. PFmall/Kanban/Worker/GitHub are surfaces or executors that supply
evidence; SENTINEL/LAND/W10 are the merge-governance owners. No state advances on a surface's say-so.

## 8. Canonical vs Derived vs Advisory Stores

| Class | Store | Rule |
|---|---|---|
| CANONICAL (source of truth) | repo / PRs / `foundup_manifest.json` / `foundup_registry.json` / WSP | the only authority for state |
| DERIVED (projection) | `public/f/public_catalog.json` (allowlist-only, from registry) | regenerated from canonical; never written directly as truth |
| ADVISORY (untrusted until verified) | Kanban `EvidencePacket`; Kanban SQLite DB (`~/.hermes/kanban.db`) | inputs to WRE verification; never canonical |

KANBAN_DB_NOT_CANONICAL: the board's SQLite DB is a worker-coordination view; WRE/repo/PR/registry remain
the source of truth (the #803/#804 ruling).

## 9. PFmall Surface Reality + the Net-New Intake/Status Gate

Today [AV]: PFmall is catalog + browse only. `public_catalog_projector/src/projector.py` derives
`public/f/public_catalog.json` from the registry, ALLOWLIST-ONLY + DERIVED-FROM-REGISTRY, fail-closed,
"no invented entries"; validation never writes (only `write_projection` emits). The /f/ browse (#801)
reads the projection. There is NO intake surface today.

Net-new (designed here, not built): (a) a public INTAKE gate (LaunchRequest -> proposal), (b) a public
STATUS surface (a derived view of registry/PR state). Both are surfaces; neither holds authority.

## 10. Public Intake Boundary (hostile input)

Phase-1 PFmall launch intake MUST be treated as hostile public input. Recommendation:
PFMALL_INTAKE_PHASE1_INVITE_OR_AUTHN_GATED (consistent with most FoundUps' `is_invite_only: true`),
shape-validated and moderation-queued.

LaunchRequest MAY contain: proposed FoundUp name; problem statement; intended users/stakeholders;
category/domain; optional public URLs as references only; requester contact/account handle (if
authenticated); requested FoundUp type.

LaunchRequest MUST NOT contain: code; shell commands; repo-creation instructions; API keys/secrets;
payment/DAO/payout claims; source_authority stage claims; merge/approval tokens; external-agent
instructions. The intake validator rejects fail-closed on any forbidden field.

## 11. Genesis Intake Reuse (WSP 64 enhance-before-create)

The `FoundUpGenesisEnvelope` already exists (`ai_overseer/src/foundup_genesis/envelope.py` + `validator.py`,
trigger `012_foundup_request`) [AV] with: identity (foundup_id/name/tagline/description/category);
genesis-constrained state (`lifecycle_stage` IDEA/INCUBATING only, `binding_state` UNBOUND/DISCOVERABLE_ONLY,
`external_repo_requested` must be False at genesis); required acceptance criteria; WSP 97 truth markers;
HoloIndex recall/prior_art.

Decision: REUSE/EXTEND (Option A/B), do NOT invent a parallel envelope. The FoundUpProposal IS the
`FoundUpGenesisEnvelope`; the PFmall LaunchRequest is a thin, hostile-input-validated PUBLIC front-door
that produces a genesis envelope after the Section 10 boundary. The existing `012_foundup_request` trigger
and the new public intake are two front-doors to the SAME validated envelope. WSP 109 (FoundUp Onboarding
Intake Protocol) governs the intake. Note: the envelope already enforces external_repo_requested=False at
genesis -- the public path cannot request a repo.

## 12. WRE Authority and State Ownership

WRE owns: validating the proposal; creating the ContextBundle (`source_authority=monorepo_poc`, builder-set
and un-self-promotable, `context_bundle_builder.py:132`); the FoundUpJob/JobStatus lifecycle; publishing
cards; verifying returned evidence; and every state transition (Section 7). LAND/SENTINEL/W10 own merge.
The registry + projector own the derived public projection. No surface advances state.

## 13. Kanban Worker Seam (mapping onto #804)

Seam 2/3 are exactly the #804 plugin contract: publish (WRE -> CardSpec, one-way), constrain (worker gets a
ContextBundle not raw repo authority; no arbitrary pick; no self-promotion; no merge; no real exec without a
WRE gate), ingest (EvidencePacket, redacted, advisory-until-verified). Per #805 the substrate is an EXTERNAL
adapter first (do not vendor yet).

## 14. PFmall Population Rule (Addendum D)

A new FoundUp becomes public-visible ONLY after: (1) PR lands; (2) registry/manifest source-of-truth
updates; (3) `public_catalog_projector` regenerates the scope-free projection; (4) /f/ reads
public_catalog.json. No worker, Kanban card, PFmall intake form, or evidence packet may directly write
public_catalog.json as canonical truth. The projector's allowlist-only + derived-from-registry fail-closed
design already enforces this [AV].

## 15. External Git Rule

- PoC default: NO external repo -- build inside the monorepo (`modules/foundups/<id>`), as GetK did (#802).
- external_proto: a repo under `FOUNDUPS/<foundup_id>` may be created ONLY by a governed WRE provisioner,
  AFTER the source_authority transition out of `monorepo_poc` -- which cannot happen by declaration.
- HARD: Kanban cannot create repos; PFmall cannot create repos; only the WRE provisioner, gated.
- Named future slice (BLOCKED): WRE_FOUNDUP_EXTERNAL_REPO_PROVISIONER_PHASE1 -- blocked until ALL hold:
  (i) source_authority transition out of monorepo_poc approved; (ii) registry/manifest contract exists;
  (iii) repo-name policy exists; (iv) secret-scanning/push-protection enabled; (v) LAND/W10 merge governance
  preserved; (vi) PFmall and Kanban proven unable to create repos directly. Prior art: `HXA19_REPO_CREATION_APPROVAL_GATE.md` [AV].

## 16. CLI-First / MCP-Later Seam

Deterministic CLI verbs first (testable, CI-friendly, no agent-transport ambiguity):

| Verb | Maps to | Status |
|---|---|---|
| `foundups launch propose` | LaunchRequest -> FoundUpProposal (genesis envelope) | NET-NEW |
| `foundups kanban publish` | WRE -> CardSpec (one-way, #804) | NET-NEW |
| `foundups kanban ingest` | EvidencePacket -> WRE (advisory, #804) | NET-NEW |
| `foundups pfmall project` | registry -> public_catalog.json | EXISTS as `python -m modules.foundups.public_catalog_projector --generate/--validate/--check` [AV] |

MCP later: wrap the SAME CLI actions as tools so Hermes/OpenClaw/Kanban agents call them. Use both, NOT
simultaneously. CLI first = deterministic + CI-testable + no transport ambiguity; MCP later = agent tool
access. Migration seam: each CLI verb is a thin command over a pure function; the MCP tool calls the same
function. (No CLI/MCP is built in this slice.)

## 17. GetK End-to-End PoC Walkthrough

GetK (#802) is a faithful PoC of steps 4-10: it has a registry entry + valid manifest + ContextBundle-
resolvable module_path + a dry-run proof through the existing OpenClaw->consumer->ContextBundle seam,
source_authority=monorepo_poc, readiness false, no real execution. The missing front of the loop (steps
1-3, PFmall intake -> proposal) and the Kanban worker seam (steps 5-7) are exactly the net-new pieces this
contract defines. Minimal first test: `foundups launch propose` produces a GetK-shaped genesis envelope ->
WRE ContextBundle -> (later) one Kanban-published card -> evidence -> PR -> projection -> /f/.

## 18. Forbidden Directions (this slice)

No code/CLI/MCP/PFmall/adapter implementation; no Kanban vendoring/install/submodule change; no manifest/
registry/public_catalog mutation; no repo provisioning; no real execution; no HERMES_DELEGATE_ENABLED
change; no source_authority promotion; no WSP/NAVIGATION mutation. PFmall intake must never accept code or a
repo request. Decision-only: typed shapes are DEFINED as tables, not authored as a module.

## 19. Verdict and Ordered Next Slices

Verdict: the controlled closed loop is well-formed and sits entirely on the surface-not-authority side of
the #803/#804 rulings; PFmall is a public surface, WRE the authority, Kanban a worker board, repo/PR/
registry the source of truth, public_catalog a derived projection. Build nothing yet.

1. (this) WRE_PFMALL_KANBAN_FOUNDUP_LAUNCH_FLOW_AUDIT_PHASE1 -- decision-only.
2. HERMES_KANBAN_PLUGIN_CONTRACT_IMPL_PHASE1 -- typed CardSpec/WorkerTaskSpec/WreEvidencePacket (+ tests),
   AST-fenced, no Hermes import (per #804/#805).
3. FOUNDUP_LAUNCH_REQUEST_CONTRACT_IMPL_PHASE1 -- typed LaunchRequest wrapper + hostile-input validator
   that REUSES the genesis envelope (Section 11), no PFmall UI.
4. FOUNDUPS_CLI_LAUNCH_SEAM_PHASE1 -- the `propose` / `kanban publish` / `kanban ingest` CLI verbs
   (deterministic, CI-tested), reusing the existing `project` verb.
5. KANBAN_EXTERNAL_ADAPTER_PILOT_PHASE1 -- the three adapter ops over an external boundary (dispatch off).
6. (BLOCKED) WRE_FOUNDUP_EXTERNAL_REPO_PROVISIONER_PHASE1 -- only after the Section 15 gates.

## 20. Operator Decision Points

- ODP-1: PFmall intake Phase-1 posture -- invite/authn-gated (recommended) vs public+rate-limited+moderated.
- ODP-2: genesis reuse shape -- reuse the envelope directly (A) vs a thin LaunchRequest wrapper (B);
  recommend B (a public wrapper that produces the envelope).
- ODP-3: CLI namespace -- confirm `foundups <verb>` (vs reusing per-module `__main__`); subworker verified
  only `project` exists today.
- ODP-4: status-surface depth -- what registry/PR state is public vs internal (status must not leak worker
  internals or member-scoped fields; allowlist-only).
- ODP-5: external-repo timing -- the provisioner stays BLOCKED until the Section 15 gates; 012 owns the
  source_authority transition.

## 21. Internal Sentinel Review

An independent adversarial SENTINEL (separate lane from the author) attacked all nine load-bearing claims by
direct read AND live repo cross-check; all SURVIVE, none refuted. Confirmed: the loop is controlled/closed
(exactly 4 governed seams + 5 forbidden direct paths, not omnidirectional); the 14-state machine assigns an
owner/transition/evidence/forbidden-shortcut per state and WRE owns every transition (no surface
self-advances); stores are separated and the Kanban DB is advisory-not-canonical; public intake is a
hostile-input boundary yielding a proposal not code (invite/authn-gated default). The genesis reuse is
real-repo-grounded -- `foundup_genesis/envelope.py:206` `external_repo_requested = False`, `LifecycleStage`
IDEA/INCUBATING only, and `validator.py` Check-5 actively rejects `external_repo_requested=True`. The
source-authority gate is grounded -- `context_bundle_builder.py:132` `SOURCE_AUTHORITY = "monorepo_poc"` is
a builder constant never read from the manifest (cannot promote by declaration), and the external-repo
provisioner is named-but-BLOCKED with 6 conditions (prior art `HXA19_REPO_CREATION_APPROVAL_GATE.md`). The
projector is allowlist-only + derived-from-registry + fail-closed with "validation never writes," so PFmall
is populated only by derived projection. `git status` is exactly two files (audit doc + root ModLog) with no
`.py`/`.gitmodules`/`vendor/`/registry/catalog mutation; WSP_97 is 27/27 all YES with 0 non-ASCII. Internal
Review Verdict: READY. Blocking findings: NONE. This verdict does not authorize merge -- the external 0102
gate does.

## 22. WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | CONTROLLED_CLOSED_LOOP_DEFINED | YES | Section 4: four governed seams; not omnidirectional. |
| 2 | FORBIDDEN_DIRECT_PATHS_LISTED | YES | Section 4: 5 forbidden direct paths enumerated. |
| 3 | PFMALL_IS_PUBLIC_SURFACE_NOT_AUTHORITY | YES | Sections 2,9,14: catalog/intake/status surface; no authority. |
| 4 | WRE_OWNS_FOUNDUP_LAUNCH_STATE | YES | Sections 7,12: WRE owns every state transition. |
| 5 | KANBAN_IS_WORKER_BOARD_NOT_ORCHESTRATOR | YES | Sections 2,13: board/worker surface; does not select canonical work. |
| 6 | CONTEXTBUNDLE_REQUIRED_FOR_WORK | YES | Sections 6,13: worker gets a ContextBundle, not raw repo authority. |
| 7 | WORKER_OUTPUT_IS_EVIDENCE_NOT_TRUTH | YES | Sections 6,7,8,13: EvidencePacket advisory until WRE-verified. |
| 8 | CANONICAL_VS_DERIVED_VS_ADVISORY_STORES_SEPARATED | YES | Section 8 table. |
| 9 | KANBAN_DB_NOT_CANONICAL | YES | Section 8: SQLite DB is a view; repo/PR/registry canonical. |
| 10 | PR_MERGE_IS_SOURCE_OF_TRUTH_UPDATE | YES | Sections 5,7,12: LAND/W10 merge updates the source of truth. |
| 11 | PUBLIC_CATALOG_DERIVED_FROM_REGISTRY | YES | Section 9: projector derives + allowlist-only, fail-closed [AV]. |
| 12 | PFMALL_POPULATED_ONLY_BY_DERIVED_PROJECTION | YES | Section 14: 4-step derive; no direct catalog write. |
| 13 | STATUS_SURFACE_DOES_NOT_LEAK_WORKER_INTERNALS | YES | Sections 9,14, ODP-4: allowlist-only; no worker internals public. |
| 14 | PUBLIC_INTAKE_HOSTILE_INPUT_BOUNDARY | YES | Section 10: treated as hostile; invite/authn-gated default. |
| 15 | PFMALL_INTAKE_ACCEPTS_PROPOSAL_NOT_CODE | YES | Section 10: allowed vs forbidden fields; no code/repo/secrets/tokens. |
| 16 | GENESIS_INTAKE_REUSE_EVALUATED | YES | Section 11: reuse/extend FoundUpGenesisEnvelope (WSP 64). |
| 17 | EXTERNAL_REPO_CREATION_GATED_BY_SOURCE_AUTHORITY | YES | Section 15: only WRE provisioner, after source_authority transition. |
| 18 | EXTERNAL_REPO_PROVISIONER_BLOCKED_UNTIL_GATE | YES | Section 15: WRE_FOUNDUP_EXTERNAL_REPO_PROVISIONER_PHASE1 BLOCKED until 6 conditions. |
| 19 | CLI_FIRST_MCP_LATER | YES | Section 16: 4 verbs; project exists; propose/publish/ingest net-new; MCP wraps later. |
| 20 | NO_REAL_EXECUTION_GATE_BYPASS | YES | Sections 7,13,18: real exec only via WRE gate; never a Kanban flag. |
| 21 | STATE_MACHINE_DEFINED_WITH_OWNERS | YES | Section 7: 14 states x owner/transition/evidence/forbidden-shortcut. |
| 22 | DECISION_ONLY_NO_CODE_NO_WIRING | YES | Section 18: no code/CLI/MCP/PFmall/adapter/vendoring; diff = 2 docs. |
| 23 | CITES_803_804_805 | YES | Predecessors cited throughout; seam = #804, substrate = #805. |
| 24 | NEXT_SLICES_ORDERED | YES | Section 19: 6 ordered slices (impl after contract). |
| 25 | OPERATOR_DECISION_POINTS_EXPLICIT | YES | Section 20: ODP-1..5. |
| 26 | ASCII_CLEAN | YES | Byte-checked 0 non-ASCII before commit. |
| 27 | FILE_SCOPE_EXACTLY_TWO | YES | git diff = this doc + root ModLog. |

Declared 27 / Rows 27 / All YES.
