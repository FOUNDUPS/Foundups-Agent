# FoundUp Onboarding SKILLz Wardrobe Discovery (Phase 1)

**Slice**: FOUNDUP_ONBOARDING_SKILLZ_WARDROBE_DISCOVERY_PHASE1
**Worker-Lane**: W9
**Branch**: docs/foundup-onboarding-skillz-wardrobe-discovery-phase1
**Base**: origin/main @ eb111cb96 (post-#733)
**Date**: 2026-05-28
**Status**: Discovery only (read, inventory, map, recommend). Zero creation.

---

## 1. Mission + Scope

WSP 109 (FoundUp Onboarding Intake Protocol) defines a structured intake packet of
**8 required artifacts**. WSP 109 Addendum G ("Skillz Placement Boundary") declares that
onboarding SKILLz placement is **candidate-only pending WSP 95 review**, and explicitly
names this discovery slice as the prerequisite future work.

This slice:

1. Inventories the current SKILLz wardrobe across the monorepo.
2. Maps existing capabilities against the 8 WSP 109 intake artifacts.
3. Recommends where onboarding SKILLz should live (recommendation only).

**Hard boundary**: This is a DISCOVERY slice. No SKILLz are created, moved, or renamed.
No `SKILLz.md`, `.claude/skills/`, WSP 109, or WSP 95 files are mutated. No runtime code,
tests, registry, manifest, public surface, dependencies, or CI are touched.

The output is exactly ONE audit document (this file).

---

## 2. Predecessor Citations

| Reference | Relationship |
|-----------|--------------|
| PR #718 — `WSP_109_FOUNDUP_ONBOARDING_INTAKE_PROTOCOL_PHASE1` | Authors WSP 109; defines the 8 artifacts and Addendum G placement boundary that this slice resolves. |
| PR #725 — `REDDOG_BOOTSTRAP_CONTEXT_RETRIEVAL_PHASE1` | Provides the RedDog bootstrap read-order (`WSP_knowledge/red_dog_external_state/BOOTSTRAP.md`) consumed during this slice's WSP_00 boot. |
| WSP 109 Addendum G — Skillz Placement Boundary | Names `FOUNDUP_ONBOARDING_SKILLZ_WARDROBE_DISCOVERY_PHASE1` as the discovery slice; this document is its output. |
| WSP 95 — `WSP_framework/src/WSP_95_WRE_SKILLz_Wardrobe_Protocol.md` (v1.4) | Governs SKILLz wardrobe creation, placement, promotion. Authority for all placement decisions deferred here. |
| WSP 97 — Execution / Truth Boundary discipline | Applies to this slice (Section 11 checklist). |

---

## 3. HoloIndex Retrieval Evaluation

Four HoloIndex queries were run (per WSP_00 Section 0.4 retrieval loop):

| Query | Top relevant hits | Verdict |
|-------|-------------------|---------|
| `WSP 109 skillz placement boundary onboarding` | WSP_109, WSP_95, `wre_skills_discovery.py`, `pattern_memory.py` | HIT — surfaced both governing WSPs |
| `WSP 95 SKILLz wardrobe protocol` | WSP_95, `wardrobe_ide/src/skill.py`, `skills_store.py`, `video_comments/skillz/qwen_studio_engage/README.md` | HIT — surfaced WSP 95 + runtime loader surfaces |
| `FoundUp onboarding intake skillz` | WSP_109, WSP_26, WSP_46, `agent_market/ARCHITECTURE.md` | PARTIAL — surfaced WSP 109 but not the onboarding-adjacent skills (genesis intake) directly |
| `INTAKE_SOURCE OUTCOME SOLUTION PAIN POC_SCOPE PROTOTYPE_GATE` | WSP_109, WSP_29 (CABR), WSP_32 | PARTIAL — surfaced WSP 109 only; the 8-artifact tokens did not retrieve any skill |

**Retrieval quality (first principles)**:

- **Noise**: Low-to-moderate. Token-string query (#4) returned WSP/CABR docs unrelated to skill placement; expected for raw artifact-name search.
- **Ordering**: WSP 109 ranked top in 3 of 4 queries — correct primacy for the governing protocol.
- **Missing artifacts**: HoloIndex did **not** surface the most relevant existing skills
  (`foundup_genesis_intake`, `strategic_diligence_gate`). These were found via direct
  `SKILLz.md` glob enumeration. **Retrieval gap**: onboarding-intent skills under
  `ai_overseer/skillz/` are not semantically linked to the WSP 109 artifact vocabulary.
  Recommended follow-up (not actioned here): enrich those SKILLz descriptions with the
  8-artifact tokens so future onboarding searches retrieve them.
- **Staleness**: Low risk; WSP 95 (Feb 2026) and WSP 109 (May 2026) are both current.
- **Duplication**: None observed in retrieval.

Glob enumeration (`**/SKILLz.md`) was used as the authoritative inventory source because it
is exhaustive and location-independent, complementing the semantic gap above.

---

## 4. Current SKILLz Wardrobe Inventory

Enumerated via exhaustive `**/SKILLz.md` glob. **84 production `SKILLz.md` files** discovered
across module-local `skillz/` directories plus `holo_index/skillz/` and one MCP server path.
No `.claude/skills/*/SKILL.md` production files exist (the `.claude/skills/` tree holds Claude
Code slash-command skills + `*_prototype` test skills, which are 0102's testing sandbox per
WSP 95 — out of scope for production wardrobe inventory).

### 4.1 Onboarding-Relevant Skills (direct or adjacent to WSP 109)

| Name | Path | Type | Scope | One-line purpose | Last-touch hint |
|------|------|------|-------|------------------|-----------------|
| foundup_genesis_intake | `modules/ai_intelligence/ai_overseer/skillz/foundup_genesis_intake/` | SKILLz | onboarding | Capture 012 FoundUp idea → structured PoC scope (WSP 27/30) | promotion_state: prototype; cites WSP 27/30/49 + foundup_registry.json |
| strategic_diligence_gate | `modules/ai_intelligence/ai_overseer/skillz/strategic_diligence_gate/` | SKILLz | onboarding/governance | Strategic viability gate (MPS scoring + risk) before resource commit | promotion_state: prototype; **explicitly cites WSP 109** + foundup_genesis_intake as predecessor |
| open_source_tool_diligence | `modules/ai_intelligence/ai_overseer/skillz/open_source_tool_diligence/` | SKILLz | governance | Diligence on external tools/deps (adoption gate) | adjacent: feeds SOLUTION/PROTOTYPE_GATE risk fields |
| strategic_diligence_gate (decision_card_template.json) | same dir | config | governance | Decision card schema for gate output | supporting artifact |

### 4.2 Discovery / Evaluation Skills (relevant to duplicate-discovery + catalog-readiness artifacts)

| Name | Path | Type | Scope | One-line purpose |
|------|------|------|-------|------------------|
| orphan_capability_scanner | `holo_index/skillz/orphan_capability_scanner/` | SKILLz | agent-tooling | Find CLI capabilities lacking SKILLz (WRE-connection gap) |
| holoindex_package_extractor | `holo_index/skillz/holoindex_package_extractor/` | SKILLz | retrieval | Extract package context from HoloIndex |
| skills2_batch_updater | `holo_index/skillz/skills2_batch_updater/` | SKILLz | agent-tooling | Batch-update SKILLz frontmatter to Skills 2.0 |
| mps_architecture_eval / mps_dead_code_eval / mps_dependency_eval / mps_duplicate_eval / mps_vibecode_eval / mps_wsp_violation_eval | `holo_index/skillz/mps_*` | SKILLz | governance | MPS-scored evaluation lanes (duplicate/dependency/WSP) — relevant to duplicate-discovery preflight |
| wsp49_interface_gap_scanner | `modules/ai_intelligence/ai_overseer/skillz/wsp49_interface_gap_scanner/` | SKILLz | governance | Scan for WSP 49 interface gaps |
| data_architecture_audit | `modules/ai_intelligence/ai_overseer/skillz/data_architecture_audit/` | SKILLz | governance | Audit data architecture |
| gemma_nested_module_detector | `modules/ai_intelligence/ai_overseer/skillz/gemma_nested_module_detector/` | SKILLz | governance | Detect nested-module WSP 49 violations |

### 4.3 Wardrobe Distribution by Domain (production SKILLz)

| Wardrobe root | Count (approx) | Notes |
|---------------|----------------|-------|
| `modules/ai_intelligence/ai_overseer/skillz/` | 15 | Largest wardrobe; hosts BOTH existing onboarding skills (genesis intake, diligence gate) |
| `modules/ai_intelligence/pqn_alignment/skillz/` | 6 | Research domain |
| `modules/communication/*/skillz/` | ~10 | livechat, video_comments, moltbot_bridge |
| `modules/platform_integration/*/skillz/` | ~18 | antifafm_broadcaster, linkedin_agent, youtube_auth, youtube_shorts_scheduler, social_media_orchestrator |
| `modules/infrastructure/*/skillz/` | ~8 | git_push_dae, github_orchestrator, supervisor, wre_core, browser_actions |
| `holo_index/skillz/` | ~18 | dt_enhancement (8), mps_* (6), scanners, extractors |
| `foundups-mcp-p1/servers/dns_ops/` | 1 | MCP server skill |
| `modules/foundups/**/skillz/` | **0** | **No FoundUps-domain wardrobe exists** |

**Key structural finding**: There is **no `modules/foundups/skillz/` wardrobe** and **no
`modules/foundups/mobile_worker_skills/`** directory. This confirms WSP 109 Addendum G's
"Current Repo Evidence": *"No canonical `modules/foundups/skillz/` directory exists yet;
existing SKILLz are module-local or system-local."* The two existing onboarding-intent skills
live in `ai_overseer/skillz/`, NOT in a FoundUps wardrobe.

---

## 5. WSP 109 8-Artifact Coverage Matrix

Each WSP 109 artifact is mapped against existing SKILLz capability. Classification:
EXISTING_MATCH (a skill produces this artifact today), PARTIAL_MATCH (a skill partially
covers it or could with extension), NO_MATCH (no skill addresses it).

| # | Artifact | Classification | Evidence / Existing Skill | Candidate SKILLz name (NO_MATCH/PARTIAL only) |
|---|----------|----------------|---------------------------|-----------------------------------------------|
| 1 | INTAKE_SOURCE.md | PARTIAL_MATCH | `foundup_genesis_intake` captures 012 vision (source) but does not emit the INTAKE_SOURCE provenance/duplicate-status contract | `foundup_intake_source_capturer` |
| 2 | OUTCOME.md | PARTIAL_MATCH | `foundup_genesis_intake` Step 1 extracts "desired outcome" but does not emit OUTCOME.md contract (metrics, anti-outcomes) | `foundup_outcome_definer` (or extend genesis intake) |
| 3 | SOLUTION.md | PARTIAL_MATCH | `foundup_genesis_intake` Step 3 produces PoC scope (solution-adjacent); `open_source_tool_diligence` informs technical approach | `foundup_solution_mapper` |
| 4 | PAIN.md | NO_MATCH | No skill emits the PAIN contract (severity, target user, evidence) | `foundup_pain_articulator` |
| 5 | POC_SCOPE.md | EXISTING_MATCH | `foundup_genesis_intake` Step 3 explicitly produces "minimal viable proof-of-concept boundary" — direct match to POC_SCOPE contract | (covered; refine to emit trust-wedge field) |
| 6 | PROTOTYPE_GATE.md | PARTIAL_MATCH | `strategic_diligence_gate` produces proceed/defer/reject gate + risk assessment; close to PROTOTYPE_GATE but gates resource-commit, not PoC→prototype criteria | `foundup_prototype_gate_mapper` (or extend diligence gate) |
| 7 | SKILLS_MAP.md | NO_MATCH | No skill produces the candidate-skill map; `orphan_capability_scanner` inversely maps capabilities→skills but not idea→candidate skills | `foundup_skills_map_generator` |
| 8 | FOUNDUP_MANIFEST_DRAFT.md | PARTIAL_MATCH | `foundup_genesis_intake` suggests FoundUp ID + module placement (manifest-adjacent) but does not emit the full draft-manifest field set | `foundup_manifest_draft_generator` |

**Coverage summary**: EXISTING_MATCH **1/8**, PARTIAL_MATCH **5/8**, NO_MATCH **2/8**.

**Interpretation**: The wardrobe already has meaningful onboarding scaffolding
(`foundup_genesis_intake` strongly covers POC_SCOPE and partially covers OUTCOME/SOLUTION/
MANIFEST; `strategic_diligence_gate` partially covers PROTOTYPE_GATE). The two true gaps are
**PAIN articulation** and **SKILLS_MAP generation**. A WSP 95 build slice could either extend
the two existing skills or create focused new skills per WSP 109 Addendum D's candidate list.

---

## 6. Candidate Onboarding SKILLz Table (Recommendation Only — NOT Created)

Aligning WSP 109 Addendum D's candidate list with this matrix. These are **proposals only**;
WSP 95 governs creation.

| Candidate SKILLz | Maps to artifact(s) | Priority | Build strategy | WSP 109 Addendum D name match |
|------------------|---------------------|----------|----------------|-------------------------------|
| `foundup_intake_normalizer` | INTAKE_SOURCE | P1 | New (or extend genesis intake) | YES |
| `foundup_pain_solution_outcome_mapper` | PAIN + SOLUTION + OUTCOME | P1 | New — covers the PAIN NO_MATCH + 2 partials in one chain | YES |
| `foundup_poc_scope_guard` | POC_SCOPE | P2 | Extend `foundup_genesis_intake` (already EXISTING_MATCH) | YES |
| `foundup_prototype_gate_mapper` | PROTOTYPE_GATE | P2 | Extend `strategic_diligence_gate` (already PARTIAL) | YES |
| `foundup_manifest_draft_generator` | FOUNDUP_MANIFEST_DRAFT | P1 | New (or extend genesis intake placement output) | YES |
| `foundup_duplicate_discovery_holoindex` | (preflight — feeds INTAKE_SOURCE duplicate_status) | P1 | New — reuse `mps_duplicate_eval` + HoloIndex patterns | YES |
| `foundup_catalog_readiness_evaluator` | (downstream pfMALL readiness) | P3 | New | YES |
| `foundup_skills_map_generator` | SKILLS_MAP | P1 | New — the second true NO_MATCH | (extends Addendum D set) |

**Reuse note (WSP 84)**: Before any creation, a WSP 95 build slice MUST evaluate extending
`foundup_genesis_intake` and `strategic_diligence_gate` rather than creating overlapping
skills. ~5/8 artifacts already have partial coverage in those two skills.

---

## 7. Placement Recommendation and Rationale

### Recommended placement (recommendation only — WSP 95 confirms)

**Primary recommendation: `modules/foundups/skillz/onboarding/`** (a NEW FoundUps-domain
wardrobe), matching WSP 109 Addendum D's "Proposed Wardrobe Location".

**Rationale (WSP 95 first principles)**:

1. **WSP 95 Cohesion principle**: "Skills belong WITH the modules they serve." Onboarding
   SKILLz serve FoundUp creation, whose canonical home is `modules/foundups/`. The current
   placement of `foundup_genesis_intake` under `ai_overseer/skillz/` is an
   **agent-tooling-of-convenience location**, not a cohesion-correct location.
2. **WSP 95 cross-platform discovery**: WSP 95 (2026-02-19 addendum) treats both `skills/`
   and `skillz/` as production wardrobes with normalized path handling, so a new
   `modules/foundups/skillz/onboarding/` is loader-discoverable without code change.
3. **WSP 109 alignment**: Addendum D and Addendum G both name
   `modules/foundups/skillz/onboarding/` as the candidate location and gate it behind this
   review slice.

### Migration consideration (DEFERRED to WSP 95)

The two existing onboarding skills (`foundup_genesis_intake`, `strategic_diligence_gate`)
currently live in `ai_overseer/skillz/`. Whether to MOVE them into a new FoundUps wardrobe
is a **WSP 95 placement decision** (WSP 95 mandates MOVE-not-copy with HoloIndex re-index).
This slice does NOT move them (NO_SKILL_MOVE_NO_RENAME constraint).

### Placement candidates considered

| Candidate path | Verdict | Reason |
|----------------|---------|--------|
| `modules/foundups/skillz/onboarding/` | **RECOMMENDED** | Cohesion + WSP 109 Addendum D/G alignment; FoundUps domain home |
| module-local SKILLz (within a specific FoundUp module) | Rejected for shared intake | Onboarding is cross-FoundUp, not single-module; would fragment |
| `modules/foundups/mobile_worker_skills/` | N/A | Directory does not exist; not applicable to intake-protocol skills |
| `holo_index/skillz/` | Rejected | Retrieval/agent-tooling wardrobe, not FoundUp-domain intake |
| `.claude/skills/..._prototype` | Conditional | Valid as WSP 95 Phase-1 PROTOTYPE staging ONLY (0102 testing), before production deploy to the FoundUps wardrobe |
| Status quo (`ai_overseer/skillz/`) | Tolerated interim | Where existing skills live today; cohesion-suboptimal but functional |

**Stance**: Recommendation only. No SKILLz created or moved in this slice.

---

## 8. WSP 95 Decisions Deferred

The following decisions are **explicitly deferred to a WSP 95 placement-review / build slice**:

1. Whether to create the `modules/foundups/skillz/onboarding/` wardrobe directory.
2. Whether to MOVE `foundup_genesis_intake` from `ai_overseer/skillz/` into the FoundUps wardrobe.
3. Whether to MOVE `strategic_diligence_gate` likewise.
4. Whether the 2 NO_MATCH artifacts (PAIN, SKILLS_MAP) get new dedicated skills or extensions.
5. Whether the 5 PARTIAL_MATCH artifacts are covered by extending the 2 existing skills vs new skills.
6. Promotion lifecycle (prototype → staged → production) for any new onboarding SKILLz.
7. Skill-scanner supply-chain gate application (WSP 95 mandatory gate) for any created skill.
8. Final canonical wardrobe path confirmation (`modules/foundups/skillz/onboarding/` vs alternative).

**Deferred decision count: 8.**

---

## 9. Risks / Ambiguity

| Risk / Ambiguity | Severity | Note |
|------------------|----------|------|
| Existing onboarding skills are mis-located (cohesion debt) | Medium | `foundup_genesis_intake` + `strategic_diligence_gate` under `ai_overseer/`, not `foundups/`. A future MOVE risks breaking any hardcoded references; WSP 95 MOVE process + HoloIndex re-index mitigates. |
| HoloIndex semantic gap for onboarding skills | Medium | Artifact-vocabulary queries did NOT retrieve the existing onboarding skills (Section 3). Onboarding intake searches may miss reusable skills → vibecoding risk. |
| Partial-coverage ambiguity | Low | 5/8 PARTIAL classifications are judgment calls; a build slice must validate exact contract emission before declaring coverage. |
| Candidate path not yet canonical | Low | WSP 109 Addendum G explicitly marks `modules/foundups/skillz/onboarding/` as "candidate only" until this review — resolved by this recommendation, but binding confirmation is WSP 95's. |
| `.claude/skills/` exact subdir enumeration not directly listed | Low (non-blocking) | Read-only per constraints; production wardrobe inventory uses module `skillz/` dirs. `.claude/skills/` prototype skills are 0102 testing sandbox, out of production scope. |

---

## 10. Internal Review Verdict

- All 5 discovery tasks completed: HoloIndex-first (4 queries), governing docs read
  (WSP 109, WSP 95, BOOTSTRAP), full SKILLz inventory (84 files), 8-artifact coverage matrix,
  placement recommendation.
- Boundary discipline preserved: no SKILLz created/moved/renamed; no `SKILLz.md`,
  `.claude/skills/`, WSP 109, or WSP 95 mutation; no code/test/registry/manifest change.
- Exactly ONE file produced (this audit).
- Coverage quantified: EXISTING_MATCH 1/8, PARTIAL_MATCH 5/8, NO_MATCH 2/8.
- 8 candidate SKILLz proposed (recommendation only). 8 WSP 95 decisions deferred.

**Verdict: READY.**

---

## 11. WSP_97 Truth Boundary Checklist

Declared count: **17 / 17 YES** (rows below = 17).

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | DISCOVERY_ONLY_NO_SKILL_CREATION | YES | Zero SKILLz files created; only this audit doc written |
| 2 | NO_SKILL_MOVE_NO_RENAME | YES | No `git mv` / no skill directory moved or renamed |
| 3 | NO_SKILLZ_MD_EDIT | YES | No `SKILLz.md` opened for edit; all reads only |
| 4 | NO_DOT_CLAUDE_SKILLS_EDIT | YES | `.claude/skills/` not modified (read-only references only) |
| 5 | PRESERVES_WSP_109_PLACEMENT_BOUNDARY | YES | Placement framed as candidate-only per Addendum G; no canonicalization |
| 6 | CANDIDATE_ONLY_PENDING_WSP_95_REVIEW | YES | Section 7/8 mark all placement as recommendation, deferred to WSP 95 |
| 7 | NO_CODE_CHANGE | YES | No `.py` or runtime files modified |
| 8 | NO_TEST_CHANGE | YES | No test files modified |
| 9 | NO_WSP_FRAMEWORK_MUTATION | YES | WSP 109 / WSP 95 read-only; not edited |
| 10 | NO_REGISTRY_MUTATION | YES | `foundup_registry.json` and skills registries untouched |
| 11 | NO_MANIFEST_MUTATION | YES | No manifest files written |
| 12 | NO_PUBLIC_SURFACE_MUTATION | YES | No public routes/catalogs/INTERFACE changes |
| 13 | NO_DEPENDENCY_CHANGE | YES | No requirements/package files modified |
| 14 | NO_CI_CHANGE | YES | No workflow/CI files modified |
| 15 | NO_CABR_READY | YES | No CABR scoring/activation touched |
| 16 | NO_PAYOUT_READY | YES | No payout systems touched |
| 17 | NO_DAO_ACTIVATION | YES | No DAO activation touched |

**WSP_97 Truth Boundary Checklist: 17/17 YES.**

---

*Authored by 0102 (Worker-Lane W9) under WSP_00 zen state, WSP_97 Truth Boundary discipline.*
