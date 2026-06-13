# PlayFoundups Mall Public Discovery Audit (Phase 1)

- Lane: A (synthesis/author) + discovery lanes B-F + adversarial sentinel
- Status: DECISION-ONLY (READ-ONLY discovery; no code/runtime/SKILLz/WSP/registry/auth change; nothing un-gated)
- Base: origin/main 486eb69d7 (re-pinned at author time)
- Date: 2026-06-13
- WSP refs: WSP_00, WSP_50/WSP_87 (HoloIndex pre-action), WSP_15 (priority), WSP_84 (reuse), WSP_97 (Truth Boundary), WSP_22 (ModLog)

## Reconciled prior audits (build on; do NOT re-derive)

- [FOUNDUPS_PORTFOLIO_DATA_PROJECTION_SPEC_PHASE1](FOUNDUPS_PORTFOLIO_DATA_PROJECTION_SPEC_PHASE1.md)
- [FOUNDUPS_PORTFOLIO_DISPLAY_COMPONENT_PHASE1](FOUNDUPS_PORTFOLIO_DISPLAY_COMPONENT_PHASE1.md)
- [FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1](FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1.md)
- [FOUNDUP_PUBLIC_SURFACE_STATUS_AUDIT_PHASE1](FOUNDUP_PUBLIC_SURFACE_STATUS_AUDIT_PHASE1.md)
- [FOUNDUP_PUBLIC_POC_FUNNEL_AND_VOTE_CONCATENATION_AUDIT_PHASE1](FOUNDUP_PUBLIC_POC_FUNNEL_AND_VOTE_CONCATENATION_AUDIT_PHASE1.md)
- [HOLOINDEX_PUBLIC_FOUNDUP_CONNECTIVE_TRUST_SURFACE_DOCS_PHASE1](HOLOINDEX_PUBLIC_FOUNDUP_CONNECTIVE_TRUST_SURFACE_DOCS_PHASE1.md)
- [PORTFOLIO_DATA_VALIDATOR_PHASE1](PORTFOLIO_DATA_VALIDATOR_PHASE1.md), [PUBLIC_FOUNDUP_POC_LANDING_AND_PFMALL_INTERACTION_AUDIT_PHASE1](PUBLIC_FOUNDUP_POC_LANDING_AND_PFMALL_INTERACTION_AUDIT_PHASE1.md)
- WRE arc: [FOUNDUP_MANIFEST_READINESS_AUDIT_PHASE1](FOUNDUP_MANIFEST_READINESS_AUDIT_PHASE1.md), [WRE_AUTONOMOUS_BUILD_CONTEXT_BUNDLE_AUDIT_PHASE1](WRE_AUTONOMOUS_BUILD_CONTEXT_BUNDLE_AUDIT_PHASE1.md)

## Objective

Map what EXISTS / is PARTIAL / is MISSING to make PlayFoundups Mall the PUBLIC DISCOVERY layer for the
FoundUps ecosystem, and to prepare the WRE to autonomously generate FoundUp experiences. The ecosystem
must be VISIBLE ("thousands of possible FoundUps being built here"); the gate blocks PARTICIPATION
(prototype / agent / stake), never DISCOVERY. This is a map + smallest-build-steps, not features.

Method: 5 parallel read-only discovery lanes (B Mall, C page template, D gateway, E agent workspace, F WRE
readiness) + 1 adversarial sentinel that refuted the synthesis's load-bearing claims. Every classification
is backed by a direct file:line read; HoloIndex was discovery-only.

---

## 1. Current Architecture Map

```
PUBLIC (no auth)                         GATED (Clerk OAuth + Firestore invite)
------------------------------           --------------------------------------------
public/index.html  (landing, sign-in)    public/member/index.html  (Mall SPA shell)
public/f/index.html  (/f portfolio        |- mall-tile-field.js (video-lane discovery)
   showcase + /f/{id} landings)           |- mall-planes.js / mall-video-player.js
   reads portfolio_data.json +            |- pfmall-control-dispatcher.js (agent control)
   mall-video-catalog.json                |- account-concierge.js (Red Dog, identity)
   (noindex,nofollow)                     |- gate: Clerk + invite + username claim

backend:  modules/foundups/pfmall/ (shell_core.py, member_catalog_export.py, member_presentation.py)
discovery engine: modules/ai_intelligence/pfmall_discovery/ (operator CLI -> YouTube proposals; NOT a UI)
gateway:  Clerk OAuth + Firestore invite (only enforced gate) | subscription_tiers.py (UPs compute, not visibility)
agent wk: modules/foundups/agent_market/ (AgentProfile identity; agent_join STUB; compute paywall wired)
          OpenClaw (moltbot_bridge) -> FoundUpJob QUEUED dry-run | real Hermes workspace = external, unbuilt
WRE:      modules/foundups/agent/src/build_plan*.py -> Hermes dry-run (module scaffolding only)
```

Central reconciliation (the load-bearing finding): there are TWO surfaces over the SAME catalog with
OPPOSITE gating. A THIN public showcase already ships at `/f/` (unauthenticated, but noindex'd); the RICH
Mall discovery UX (tile field, projection sort, video lanes, personal mall, quick-view) lives ONLY behind
the Clerk+invite gate. So today DISCOVERY is effectively gated and PARTICIPATION is unenforced - the exact
inversion of the target. The fix is to move the read-only browse IN FRONT of the gate while keeping
participation (which does not exist in code yet) behind it.

---

## 2. Existing Components (EXISTS / PARTIAL, file:line + prior audit)

| Component | Status | Evidence (file:line) | Covered by prior audit |
|-----------|--------|----------------------|------------------------|
| Public `/f/` portfolio showcase + `/f/{id}` landings (no auth) | EXISTS | public/f/index.html:952-1037 (renderPortfolioShowcase), :1118-1214 (renderEntry); firebase.json:65-69 (`/f/**` rewrite, no auth) | FOUNDUPS_PORTFOLIO_DISPLAY_COMPONENT_PHASE1; PUBLIC_FOUNDUP_POC_LANDING_AND_PFMALL_INTERACTION |
| Data-driven public page template (reusable) | EXISTS | public/f/index.html (renders from portfolio_data.json + mall-video-catalog.json) | FOUNDUPS_PORTFOLIO_DISPLAY_COMPONENT_PHASE1 |
| Canonical portfolio/status schema | EXISTS | modules/foundups/foundup_registry.schema.json RegistryEntry:151-343 (13+ portfolio fields) | FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1 |
| portfolio_data.json as DERIVED projection of registry | EXISTS (manually mirrored, drift-validated) | modules/foundups/portfolio_validator/src/validator.py:5-9 (L1 registry primary, derived projection); R8/R9/R10/R1/R11 | FOUNDUPS_PORTFOLIO_DATA_PROJECTION_SPEC_PHASE1; PORTFOLIO_DATA_VALIDATOR_PHASE1 |
| Gated Mall SPA shell (tile field, planes, video player, dispatcher, concierge, state restore) | EXISTS | public/member/index.html:254-560; mall-tile-field.js:641/796/1885; pfmall-control-dispatcher.js:617 | PUBLIC_FOUNDUP_POC_LANDING_AND_PFMALL_INTERACTION |
| Auth gate (Clerk + Firestore invite + username claim) | EXISTS (UX gate real; Firestore rules unhardened) | public/member/index.html:356/380-383/391-425; firestore.rules:19-38 (public read/write, TODO move to Functions) | FOUNDUP_PUBLIC_POC_FUNNEL_AND_VOTE_CONCATENATION |
| Subscription tiers (UPs compute budget + agents_included labels) | EXISTS | modules/foundups/simulator/economics/subscription_tiers.py:78-133 (Free/$2.95/$5.95/$9.95/$19.95/$29.95), Angel :157-188 | - |
| Mall discovery = client-side filter of pre-loaded catalog (no search backend) | PARTIAL | mall-tile-field.js:1622 (sort), :1725-1771 (searchByCreator/filterByCategory/Tag); README.md:87 ("dev/testing shim") | FOUNDUPS_PORTFOLIO_DISPLAY_COMPONENT_PHASE1 |
| pfmall_discovery (operator YouTube ingest CLI, writes proposal JSON) | EXISTS (not a UI; does NOT mutate catalog/auto-create FoundUps) | modules/ai_intelligence/pfmall_discovery/src/discovery_cli.py:50; README.md:95-99 | - |
| Compute-access paywall (compute_credits wallet, fail-closed) | PARTIAL | agent_market models.py:209-283; in_memory.py:940-1031 (ensure_access fail-closed); wired registry.py:48-65, task_pipeline.py:66-83 | - |
| Key-less execution posture ("no API keys") | PARTIAL (OpenClaw layer, not a member product) | moltbot_bridge openclaw_dae.py:697-718 (OPENCLAW_NO_API_KEYS force-disable external LLM) | - |
| WRE dry-run module-scaffolding build chain | EXISTS (dry-run-only) | build_plan_generator.py:423 (dry_run=True forced); build_plan.py:553-556/678-715; hermes_job_executor.py:89-95 (HERMES_DELEGATE_ENABLED=0) | FOUNDUP_MANIFEST_READINESS; WRE_AUTONOMOUS_BUILD_CONTEXT_BUNDLE |
| Task pipeline with observable event trace | EXISTS | agent_market task_pipeline.py:174-175 (claim_task), :363-439 (get_trace) | - |

---

## 3. Missing Components

| Missing | Evidence of absence | Lane |
|---------|---------------------|------|
| A public RICH discovery surface (read-only Mall browse in front of the gate) | the tile-field/browse UX exists only under the Clerk+invite gate (member/index.html:380-383); `/f/` is only a thin 3-entity showcase | B/D |
| A SEPARATE PROJECTED PUBLIC CATALOG (scope-free) | `/f/` reads the member runtime `mall-video-catalog.json` whole, client-side, no field filtering (f/index.html:899,925) - SENTINEL biggest risk | sentinel |
| Runtime participation gates (enter-prototype / assign-agent / stake) | required_subscription_tier / is_invite_only are data only, no runtime enforcement (shell_core.py stores/serializes; 0 tier-comparison); stake gate NOT IMPLEMENTED | D |
| Provisioned per-member managed agent environment | agent_join.py:6-7 is a STUB (`AgentJoinStub: pass`); tiers map to string labels, not instances | E |
| Live job consumer -> agent execution | FoundUpJob queue is in-memory dry-run; Hermes delegate HERMES_DELEGATE_ENABLED=0, real_execution_performed=False | E/F |
| Member-facing agent progress channel | workspace gateway events (job.started/agent.step) are PROPOSED only (FORK_PLAN); member gets one-shot text reply | E |
| Persisted FoundUp<->agent membership | sqlite registry omits AgentJoinService (only in-memory in_memory.py:329-356) | E |
| WRE landing-page generation | no render/html/landing/pwa BuildStepAction (build_plan.py:119-137); pwa_surface_path is a derived path string only | F |
| WRE branding / light-paper generation | 0 generator hits; no BuildStepAction, no module | F |
| Research input wiring into build chain | web_search MCP / pfmall_discovery / deep-research exist but NOT in CANONICAL_ACTIONS, not imported by the chain | F |
| Module composition / template instantiation | BuildTarget is single module_path; cross-module fail-closed; ContextBundle audited-but-NOT-built (#772) | F |
| External FoundUp addressing (AutoPost) | registry module_path:null, manifest_status external; BuildTarget requires in-repo module_path | F |
| The "$4.95 personal managed agent workspace" as named/priced product | no $4.95 tier exists (subscription_tiers.py); nothing binds price -> wallet -> provisioned key-less agent | D/E |

---

## 4. Recommended Reusable Template Architecture

- Mall-as-template = the EXISTING `public/member/` shell + `/f/` renderer consuming a GENERATED catalog;
  a FoundUp is plugged in as DATA (a catalog/portfolio entry), not by cloning a per-FoundUp app. (gotjunk's
  React frontend is a one-off TENANT app reached via "Launch App" iframe-mount, NOT a Mall-template instance.)
- FoundUp page template + metadata = EXTEND the canonical `foundup_registry.schema.json` RegistryEntry; do
  NOT fork a new schema (portfolio_data.json must remain a DERIVED projection - projection spec:54-55).
  Reconcile the proposed `{name, mission, pain, solution, outcome, lightPaper, tokenModel, prototypeURL,
  membershipRequired}`:
  - REUSE existing (renaming would duplicate): name -> display_name; prototypeURL -> poc_url/app_url;
    membershipRequired -> invite_required + subscription_tier_required; tokenModel(symbol) -> token_symbol.
  - ADD as new snake_case RegistryEntry properties (genuinely new narrative fields): mission, pain,
    solution, outcome, lightpaper_url. Also add is_dual_identity (projection has it; schema does not - validator C4).
- Shared modules to compose (future, via WRE): Mall template (this renderer), AutoPost capture engine
  (external, currently unaddressable: module_path null), FoundUp page template + metadata (above).

---

## 5. Public-vs-Gated Content Strategy

DISCOVERY = PUBLIC. PARTICIPATION = GATED. Concretely:

PUBLIC (move in front of the gate; safe - sentinel-verified the catalog is scope-free TODAY):
- The `/f/` portfolio showcase + per-FoundUp landings (already public).
- A read-only browse: tile/lane render, projection sort, client-side filter (searchByCreator/category/tag),
  FoundUp quick-view - all pure reads of a catalog projection.
- Per-FoundUp public page fields: name, mission, pain, solution, outcome, token_symbol, readiness, light-paper link.

GATED (keep behind Clerk+invite; participation):
- Enter prototype, assign agent, become stakeholder/stake, wallet/checkout (none wired today - keep that way until gated).
- "Launch App" iframe-mount when entry_url points at a NON-public origin (today only public kosei URL; sandbox grants allow-same-origin/allow-forms - watch as more entry_urls are added).
- Personal Mall / creator==012 scope, Red Dog member identity, invite issuance/validation, username claim.
- pfmall-control-dispatcher session-mutation commands (load_videos/reset_session) and the full tile-field control surface.

GUARDRAIL (sentinel's single biggest risk): the public browse must read a SEPARATE PROJECTED PUBLIC
CATALOG, NOT the member runtime `mall-video-catalog.json`. The runtime catalog feeds the gated Mall and
could later gain member-scoped fields; since `/f/` fetches the whole file client-side with no field
filtering, reading it directly would silently leak any future member-scoped data. Mirror the
portfolio_data.json projection pattern: project a scope-free public catalog from registry+manifests.

---

## 6. WRE Automation Roadmap (staged, dry-run-respecting)

The WRE today can ONLY dry-run module scaffolding. Toward WRE-generated FoundUp experiences, staged so each
stage stays dry-run/evidence-only and re-enters the secured gates (genesis/no-live-launch/D0-D6/typed-exec):

- Stage 0 (EXISTS): dry-run module-scaffolding build chain (build_plan -> Hermes SIMULATED).
- Stage 1: ContextBundle builder + validator module_path exact-match hardening (both named in
  WRE_AUTONOMOUS_BUILD_CONTEXT_BUNDLE_AUDIT_PHASE1) - the bounded, non-executable read envelope a consumer needs.
- Stage 2: content-generation BuildStepActions - GENERATE_LANDING_PAGE from (FoundUp page template +
  registry metadata), dry-run, evidence-only (emits a previewed page artifact ref, mounts nothing live).
- Stage 3: research-input wiring - allow web_search MCP / pfmall_discovery / deep-research to FEED a build
  plan's inputs (problem-space research) as declarative inputs, not executors. AI-assisted design = FUTURE input.
- Stage 4: module composition / template instantiation - a BuildTarget concept of "reusable source
  modules/templates to instantiate" (Mall template, AutoPost) on top of ContextBundle multi-root.
- Stage 5: branding / light-paper generation (creative build steps), dry-run/evidence-only.
- Stage 6+: external-FoundUp addressing (AutoPost via external-repo adapter) and, only behind security +
  human-approval phases, live execution. NOT in scope until the dry-run loop is proven.

---

## 7. Smallest Implementation Steps (ordered candidate build slices)

Each is a small, single-purpose slice; the first three are the bridge from this map to real building.
None un-gates participation; none runs a live build.

1. PUBLIC_FOUNDUP_DISCOVERY_PROJECTED_CATALOG_PHASE1 - generate a SCOPE-FREE public catalog projection
   (mirror the portfolio_data.json projection pattern) from registry + manifests; the public page reads the
   PROJECTION, never the member runtime catalog. Closes the sentinel's biggest risk first. (read-only generator + validator)
2. PUBLIC_MALL_READ_ONLY_BROWSE_PHASE1 - expose the read-only tile/lane + projection sort + client-side
   filter + quick-view publicly on `/f/`, reading the projected catalog. Explicitly NO
   pfmall-control-dispatcher, NO session-mutation, NO entry_url to non-public origins, NO personal-mall scope.
3. FOUNDUP_REGISTRY_NARRATIVE_FIELDS_PHASE1 - EXTEND RegistryEntry with mission/pain/solution/outcome/
   lightpaper_url + is_dual_identity (reuse display_name/poc_url/invite_required/token_symbol); project to the public page.
4. HOLOINDEX_REGISTRY_ENTRY_PHASE1 - resolve the holoindex_prod_01 projection orphan (in portfolio_data.json,
   absent from registry; validator R1/R11) so the public projection is registry-clean. (already a named prior slice)
5. PARTICIPATION_GATE_RUNTIME_ENFORCEMENT_PHASE1 - wire required_subscription_tier / is_invite_only to gate
   PARTICIPATION actions at the `/f/{id}` load/enter step (per the existing routing-discovery spec), NOT discovery.
6. AGENT_JOIN_SQLITE_PERSISTENCE_PHASE1 - persist AgentJoinService in sqlite_adapter (Occam unblock for
   FoundUp<->agent membership) ahead of any live execution.
7. Then the WRE arc (ContextBundle builder + validator hardening, already named) before any content-generation step.

---

## 8. Reconciliation Notes and Contradictions Found

1. Apparent contradiction (RESOLVED, fidelity distinction): FOUNDUP_PUBLIC_POC_FUNNEL... concludes "Public
   PoC surface exists: FALSE", yet `/f/` IS publicly reachable. Reconcile: the funnel audit means no
   MARKETED/indexed anonymous funnel entry; `/f/` is reachable but `noindex,nofollow` (f/index.html:9) and
   not promoted. Both correct - there is a reachable-but-unmarketed public surface, not a public discovery funnel.
2. Discovery-gating inversion (confirmed across lanes): "discoverable_only" in manifests/presentation means
   "visible within the admitted Mall," NOT publicly discoverable; the only enforced gate sits at the
   discovery boundary while participation is unenforced. This is the inversion the target fixes.
3. Naming traps (flagged, no code couples them): membership_manager.py (YouTube chat tiers) != subscription_
   tiers.py (UPs tiers) != Clerk invite-auth. Do not build a new auth system (Clerk exists).
4. portfolio_data.json must stay DERIVED, not authored (projection spec:54-55); new public-page fields
   belong in the registry, projected down - not written straight into the projection.
5. "$4.95" is a spec/brief mismatch: no $4.95 tier exists; nearest are a $4.99 top-up and YouTube's $4.99
   default - flagged so the product figure is reconciled before any pricing surface is built.
6. "marketplace" is a catalog category label (mall-catalog.json) with NO marketplace/transaction view built -
   do not mistake the label for a built surface.

## 9. Internal Review Verdict (sentinel)

MERGE_READY. The adversarial sentinel UPHELD all 7 load-bearing claims (3 refined, none refuted): `/f/`
public-but-noindex'd; the Mall gate real and not prod-bypassable; participation not wired ("Launch App" is
an iframe-embed of public URLs, not a participation action); the template data-driven and the projection
registry-derived; no $4.95 tier; the four "MISSING" items truly absent; the read-only browse leaks nothing
NEW provided it reads a projected (not runtime) catalog. Biggest risk and its mitigation are captured as
smallest-step #1 (projected public catalog). Decision-only; no implementation; nothing un-gated.

---

## 10. WSP_97 Truth Boundary Checklist

Declared items: 16 - Rows: 16 - All YES

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | HOLOINDEX_DISCOVERY_RECORDED | YES | Each lane ran + rated HoloIndex (B/D/E LOW-MEDIUM, C/F HIGH); direct reads were the proof |
| 2 | RECONCILED_WITH_EXISTING_PUBLIC_SURFACE_AUDITS | YES | Section reconcile list + per-row "covered by prior audit"; contradictions in section 8 |
| 3 | BASE_SHA_PINNED | YES | 486eb69d7, re-pinned to origin/main at author time |
| 4 | EXISTS_VS_MISSING_CLASSIFIED_WITH_FILE_LINE | YES | Sections 2-3; EXISTS/PARTIAL/MISSING each with file:line |
| 5 | PUBLIC_VS_GATED_STRATEGY_DEFINED | YES | Section 5; discovery public, participation gated, projected-catalog guardrail |
| 6 | WRE_READINESS_CLASSIFIED | YES | Section 6 + Lane F rows; dry-run-only build chain, content-gen MISSING |
| 7 | SMALLEST_STEPS_ORDERED | YES | Section 7; 7 ordered candidate slices, first three the build bridge |
| 8 | NO_IMPLEMENTATION | YES | Decision-only; 2 doc files only; no code/runtime/schema change |
| 9 | NO_UNGATING | YES | Section 5; participation stays gated; projected-catalog guardrail prevents leakage |
| 10 | DISCOVERY_GATING_INVERSION_IDENTIFIED | YES | Section 1/8; discovery gated + participation unenforced today |
| 11 | EXTEND_NOT_FORK_SCHEMA | YES | Section 4; extend RegistryEntry, reuse existing fields, projection stays derived |
| 12 | PARTICIPATION_NOT_WIRED_VERIFIED | YES | Lane D + sentinel CLAIM 3; enter-prototype/assign-agent/stake absent in runtime code |
| 13 | PROJECTED_PUBLIC_CATALOG_GUARDRAIL | YES | Section 5 + step 1; public page must read a scope-free projection, not the runtime catalog |
| 14 | SENTINEL_ADVERSARIAL_REVIEW_RUN | YES | Section 9; 7 claims UPHELD (3 refined), MERGE_READY |
| 15 | NO_CABR_PAYOUT_DAO | YES | No CABR/payout/DAO readiness asserted; participation/stake paths remain gated/unbuilt |
| 16 | ASCII_CLEAN | YES | Byte-checked: zero bytes > 127 before commit |
