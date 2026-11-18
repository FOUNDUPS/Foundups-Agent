# FoundUp Campaign Operator SKILLz Placeholder (Phase 1)

**Slice**: FOUNDUP_CAMPAIGN_OPERATOR_SKILLZ_PLACEHOLDER_PHASE1
**Worker-Lane**: 0102 (solo author / CTO architect)
**Branch**: docs/foundup-campaign-operator-skillz-placeholder-phase1
**Base**: origin/main @ 329db7113 (post-#893)
**Date**: 2026-06-13
**Status**: Placeholder + contract only. No executor, no posting, no scheduling, no API.

---

## 1. Mission + Scope

Establish a discoverable, non-executing placeholder contract for a future
**FoundUp Campaign Operator SKILLz**: the wardrobe capability that will one day take a
FoundUp campaign brief (sourced from WSP 109 intake evidence) and drive it through
creative packaging and gated social distribution.

The intended end-to-end arc (NOT built here):

```
WSP 109 FoundUp intake
  -> campaign brief
  -> creative package request
  -> optional external creative engine (e.g. Runway Agent 2.0, availability NOT assumed)
  -> AutoPost / social distribution
  -> analytics feedback
```

### Hard boundary (this slice creates NONE of the following)

- No live campaign execution, no campaign scheduling, no runtime executor.
- No Runway API calls. No assumption that any external creative engine API exists.
- No AutoPost execution. No posting to any platform. No account auth. No secrets.
- No browser automation. No `.py` runtime files. No tests that import runtime code.
- No HoloIndex ranking-code changes.
- No registry mutation, no manifest mutation, no public-surface promotion.

Deliverables are documentary/static only:

1. This audit + contract document.
2. One non-executing placeholder marker at the canonical module-local SKILLz location.
3. One scoped ModLog pointer.

---

## 2. Reference Citations (direct-read, not inferred)

Per Addendum A, the governing artifacts were direct-read from the repo (the RedDog
extension smoke returned `skill_hits: 0` and surfaced neither WSP 95 nor WSP 109; see
Section 4 for the recorded retrieval gap). Direct evidence used:

| Reference | File / Location | Relationship |
|-----------|-----------------|--------------|
| WSP 95 (v1.4) WRE Skills Wardrobe Protocol | `WSP_framework/src/WSP_95_WRE_SKILLz_Wardrobe_Protocol.md` | Governs SKILLz placement, naming, promotion. Authority for the placement decision in Section 6. |
| WSP 109 (v1.1.0) FoundUp Onboarding Intake Protocol | `WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md` | Source of campaign-brief evidence refs (8 intake artifacts). Addendum D + lines 583-591 define the `modules/foundups/skillz/` proposed location and its candidate-only status. |
| WSP 109 lines 719/726 | same file | "No canonical `modules/foundups/skillz/` directory exists yet"; `modules/foundups/skillz/onboarding/` is a "candidate placement only". |
| WSP 15 MPS | `WSP_framework/src/WSP_15_Module_Prioritization_Scoring_System.md` | Scoring for Section 12 next-slice ordering. |
| WSP 97 | Truth / Execution boundary discipline | Applies to this slice (Section 11 checklist). |
| Social Media Orchestrator | `modules/platform_integration/social_media_orchestrator/` (README, ROADMAP, `skillz/antifafm_linkedin_post/`) | Existing module-local SKILLz home; chosen placeholder host. |
| LinkedIn Agent | `modules/platform_integration/linkedin_agent/` | Future distribution target (DOM/Selenium + scheduled posts). |
| YouTube Shorts | `modules/communication/youtube_shorts/` | Future creative/distribution target (Veo 3 generation + upload). |
| AutoPost readiness audit | `docs/audits/architecture/AUTOPOST_REUSABLE_CAPTURE_ENGINE_AUDIT_PHASE1.md`, `docs/audits/autopost_external_foundup/AUTOPOST_EXTERNAL_OPERATIONAL_READINESS_AUDIT.md` | External capture/listing engine; publish leg currently mock/blocked. |
| RedDog -> OpenClaw policy gate | `modules/communication/moltbot_bridge/src/reddog_openclaw_work_order_policy_gate.py` (decision enum lines 54-56, `no_execution_performed` line 76) | Governance pattern reused in Section 8. |
| Sibling precedent | `docs/audits/architecture/FOUNDUP_ONBOARDING_SKILLZ_WARDROBE_DISCOVERY_PHASE1.md` | House style + the parallel onboarding placement question. |

---

## 3. Convention Audit

### 3.1 WSP 95 wardrobe phases (placement + naming)

WSP 95 (title verified: "WSP 95: WRE Skills Wardrobe Protocol", Version 1.4) defines a
three-phase lifecycle and a placement rule "skills belong WITH the modules they serve":

| Phase | Location | File | Context |
|-------|----------|------|---------|
| Prototype | `.claude/skills/<name>_prototype/` | `SKILL.md` | 0102 testing sandbox |
| Staged | `.claude/skills/<name>_staged/` | `SKILL.md` | extended metrics |
| Production | `modules/<domain>/<block>/skillz/<name>/` | `SKILLz.md` (+ `executor.py`) | native agent execution |

The runtime loader (`modules/infrastructure/wre_core/skillz/wre_skills_loader.py`,
lines 377-383) resolves a skill **by explicit name** to `SKILLz.md` / `SKILL.md` and
"should not force-load" content (line 107). It never loads `README.md`. Consequence: a
`README.md` placeholder in a skill folder is non-executing and fail-closed -- any attempt
to load skill `foundup_campaign_operator` raises `FileNotFoundError` because no
`SKILLz.md` exists yet. This is the desired behavior for an unauthorized placeholder.

### 3.2 WSP 109 campaign-brief evidence source

WSP 109 produces 8 intake artifacts. The four that seed a campaign brief are:

- `PAIN.md` -> campaign `pain`
- `OUTCOME.md` -> campaign `outcome`
- `SOLUTION.md` -> campaign `solution`
- `INTAKE_SOURCE.md` + `FOUNDUP_MANIFEST_DRAFT.md` -> `foundup_id` + provenance

WSP 109 Addendum D is explicit: WSP 109 lists candidate SKILLz; **WSP 95 governs their
creation**; **WRE governs their execution**. This placeholder respects that boundary --
it creates neither a skill nor an executor, only the location marker and the contract.

### 3.3 Existing distribution surfaces (future routing targets, untouched here)

| Module | Entry surface (read-only ref) | Auth / mechanism | Campaign concept today |
|--------|-------------------------------|------------------|------------------------|
| `social_media_orchestrator` | `RefactoredPostingOrchestrator.handle_stream_detected(...)`; `skillz/antifafm_linkedin_post/` | browser automation (X + LinkedIn) | none |
| `linkedin_agent` | `LinkedInAgent.create_post/schedule_post`; `GitLinkedInBridge.push_and_post` | DOM/Selenium + scheduled | none |
| `youtube_shorts` | `ShortsOrchestrator.create_and_upload(topic, duration)` | Veo 3 API + youtube_auth (read-only) | none |
| AutoPost (external `O:/repos/AutoPost`) | `postOrchestrator` (TS) | capture only; publish mock/blocked | none |

Confirmed: **no `campaign`, `CampaignBrief`, `CampaignWorkOrder`, "creative package", or
"Runway" concept exists anywhere in `modules/`** today. This slice defines new ground as a
contract only.

---

## 4. HoloIndex Retrieval Evaluation (before-state + recorded gap)

### 4.1 CLI query set (run before edits, per HoloIndex Addendum)

Six required queries were run via `python holo_index.py --search "<q>"`:

| Query | Surfaced the governing artifacts? | Verdict |
|-------|-----------------------------------|---------|
| `FoundUp campaign operator Skillz` | No campaign-operator skill (none exists); top hits = simulator/economics + `WSP_SKILL_BUILDER.md` | EXPECTED MISS (greenfield) |
| `WSP_95 Skillz Wardrobe campaign` | YES in WSP lane: `WSP_95_WRE_SKILLz_Wardrobe_Protocol.md` + `FOUNDUP_ONBOARDING_SKILLZ_WARDROBE_DISCOVERY_PHASE1.md` | HIT (WSP lane) |
| `WSP_109 FoundUp intake campaign` | YES: `WSP_109_FoundUp_Onboarding_Intake_Protocol.md` + its Phase1 audit | HIT (WSP lane) |
| `AutoPost FoundUp campaign automation` | `AUTOPOST_EXTERNAL_OPERATIONAL_READINESS_AUDIT.md` | PARTIAL (no campaign concept) |
| `social media orchestrator campaign` | `social_media_orchestrator/README.md` + `ROADMAP.md` | HIT (module, no campaign concept) |
| `Runway Agent creative campaign` | `engagement_campaigns.py`, `youtube_shorts/.../MULTI_CLIP_SYSTEM.md`; no Runway anything | EXPECTED MISS |

### 4.2 Retrieval quality (first principles)

- **Noise**: moderate. Campaign queries pull simulator/economics code that is unrelated to
  wardrobe placement -- expected for a term ("campaign") with no code anchor.
- **Ordering**: WSP 95 / WSP 109 rank correctly in the WSP lane for their targeted queries.
- **Missing artifacts (the in-scope gap, Addendum B)**: The **RedDog extension smoke**
  returned `skill_hits: 0` and surfaced **neither WSP 95 nor WSP 109** for campaign/skillz
  queries, even though both exist and the `holo_index.py` CLI WSP-lane DID surface them.
  The skill_hits channel returns nothing because no campaign SKILLz is indexed yet, and the
  RedDog smoke retrieval path did not promote the WSP lane. This divergence between the CLI
  WSP lane and the RedDog skill_hits channel is the recorded INDEX_GAP.
- **Staleness**: low. WSP 95 (Feb 2026) and WSP 109 (May 2026) are current.
- **Duplication**: none observed.

### 4.3 Recorded INDEX_GAP

```
INDEX_GAP: HOLOINDEX_FOUNDUP_CAMPAIGN_SKILLZ
  symptom_1 = RedDog smoke skill_hits: 0 for campaign/skillz queries
  symptom_2 = WSP_95 exists but not retrieved by RedDog smoke
  symptom_3 = WSP_109 exists but not retrieved by RedDog smoke
  symptom_4 = campaign/social distribution surfaces exist but were not retrieved as skill_hits
  root_cause (provisional) = no campaign SKILLz indexed; RedDog skill_hits channel
                             not cross-promoting the WSP lane; new docs require re-index
  remediation = follow-up slice HOLOINDEX_FOUNDUP_CAMPAIGN_SKILLZ_DISCOVERABILITY_PHASE1
  constraint = do NOT change HoloIndex ranking code in this placeholder slice
```

### 4.4 After-edit discoverability

New markdown (this audit + the README placeholder) is NOT auto-indexed; ChromaDB
collections require an explicit re-index (`--index-docs` / `--index-code`). Therefore a
fresh search immediately after this slice will NOT return the new files. This is an
expected, recorded gap -- not a ranking defect -- and is folded into the follow-up slice
in Section 12. This slice does not run a re-index (out of scope; heavy side effect).

### 4.5 Required follow-up query set (post re-index, for the discoverability slice)

- `foundup campaign operator skillz placeholder`
- `campaign work order brief schema foundup`
- `campaign operator governance reddog openclaw hermes`
- `social media orchestrator campaign skillz`
- `creative package request distribution policy gate`

---

## 5. CampaignBrief / CampaignWorkOrder Contract (NON-EXECUTING SCHEMA)

This is a documentary contract only. No serializer, validator, or runtime type is created
in this slice. Field naming follows the existing `modules/foundups/foundup_registry.schema.json`
style (`foundup_id` pattern `^[a-z0-9_]+$`, lowercase_underscore enums).

```jsonc
// CampaignBrief - the FoundUp-facing intent (derived from WSP 109 intake evidence)
{
  "schema_version": "0.1.0-placeholder",
  "execution_status": "PLACEHOLDER_NO_EXECUTION",   // hard invariant for this slice

  "foundup_id": "string  // ^[a-z0-9_]+$ ; matches a foundup_registry entity",

  "wsp_109_evidence_refs": {
    "intake_source": "path  // INTAKE_SOURCE.md",
    "pain":          "path  // PAIN.md",
    "outcome":       "path  // OUTCOME.md",
    "solution":      "path  // SOLUTION.md",
    "manifest_draft":"path  // FOUNDUP_MANIFEST_DRAFT.md"
  },

  "target_audience": {
    "segments":   ["string"],
    "geos":       ["string"],
    "languages":  ["string"],
    "exclusions": ["string"]
  },

  "pain":     "string  // sourced from PAIN.md",
  "outcome":  "string  // sourced from OUTCOME.md",
  "solution": "string  // sourced from SOLUTION.md",

  "cta": {
    "primary":     "string",
    "secondary":   "string | null",
    "destination": "string  // route or external url; NOT auto-published here"
  },

  "platform_matrix": [
    {
      "platform":     "enum [linkedin, x_twitter, youtube_shorts, autopost_external]",
      "module_ref":   "string  // future Hermes route target; informational only",
      "enabled":      "bool   // default false in placeholder",
      "priority":     "int    // lower = earlier; mirrors orchestrator sequencing"
    }
  ],

  "creative_asset_requests": [
    {
      "asset_type":   "enum [text_post, image, short_video, thumbnail, carousel]",
      "engine_hint":  "enum [internal_template, external_creative_engine, manual]",
      "engine_name":  "string | null  // e.g. runway_agent_2 ; availability NOT assumed",
      "spec":         "string  // freeform brief; no generation triggered here",
      "status":       "enum [requested, deferred] // never 'generated' in placeholder"
    }
  ],

  "brand_voice": {
    "tone":         ["string"],
    "do":           ["string"],
    "dont":         ["string"],
    "reference_handle": "string | null"
  },

  "compliance_constraints": {
    "disclosures":     ["string"],
    "prohibited_claims":["string"],
    "platform_policy_refs": ["string"],
    "requires_human_review": "bool  // default true"
  },

  "kpi_targets": [
    {
      "metric":  "enum [impressions, reach, engagement_rate, clicks, conversions, followers]",
      "target":  "number",
      "window_days": "int"
    }
  ],

  "analytics_feedback": {
    "status":          "enum [pending, partial, complete] // 'pending' in placeholder",
    "collected_at":    "iso8601 | null",
    "per_platform":    [
      { "platform": "string", "metric": "string", "value": "number | null" }
    ],
    "feeds_back_to":   "string  // foundup analytics surface; not wired here"
  }
}
```

```jsonc
// CampaignWorkOrder - the governance envelope that WOULD carry a brief through the
// RedDog -> OpenClaw -> Hermes -> WRE chain. Mirrors the existing
// reddog_governed_work_order_dryrun.py shape. NON-EXECUTING.
{
  "work_order_id":   "string",
  "foundup_id":      "string  // ^[a-z0-9_]+$",
  "brief_ref":       "path    // CampaignBrief above",
  "requested_operation": "campaign_distribution",
  "authority_tier":  "enum [recommend_only, dry_run, authorized]  // 'recommend_only' here",
  "recommended_by":  "reddog",
  "no_execution_performed": true,           // hard invariant
  "allowed_paths":   [],                     // empty until authorized
  "denied_paths":    ["**/*"],               // deny-all in placeholder
  "forbidden_tokens":["secret","oauth_token","credential","deploy_production","publish"]
}
```

---

## 6. Canonical Placeholder Location Decision (WSP_50 + dialectic sweep)

**Decision**: the placeholder lives at

```
modules/platform_integration/social_media_orchestrator/skillz/foundup_campaign_operator/README.md
```

### Candidates considered (CoR dialectic)

| Candidate | Verdict | Reason |
|-----------|---------|--------|
| `skillz/campaign_operator/` at **repo root** | REJECTED | Addendum A forbids it; WSP 95 has no repo-root wardrobe; repo-root `skillz/` does not exist. |
| `modules/foundups/skillz/campaign/` | REJECTED (for now) | WSP 109 lines 719/726 state this tree "does not exist yet" and is "candidate placement only" pending WSP 95 review. Creating it would invent a new top-level tree, contradicting "prefer existing module-local conventions." |
| `.claude/skills/foundup_campaign_operator_prototype/SKILL.md` | REJECTED | `.claude/skills/` is the prototype sandbox; a `SKILL.md` there is loadable/invocable -- violates "placeholder only, no executor." |
| `modules/platform_integration/social_media_orchestrator/skillz/foundup_campaign_operator/README.md` | **CHOSEN** | Existing module-local SKILLz dir (sibling `antifafm_linkedin_post/SKILLz.md` already present). WSP 95 rule "skills belong with the modules they serve" -- the campaign operator serves social distribution/orchestration. `README.md` is never loaded by the resolver, so it is non-executing and fail-closed. |

### Why social_media_orchestrator and not foundups domain

The campaign **brief** originates in the foundups domain (WSP 109), but the campaign
**operator** is an orchestration/distribution capability. WSP 95 places a skill with the
module it serves; the orchestrator already hosts a distribution SKILLz
(`antifafm_linkedin_post`). When WSP 95 review later blesses a `modules/foundups/skillz/`
tree (the parallel onboarding question in the sibling audit), a cross-pointer can be added
then. This slice does not pre-empt that review.

---

## 7. Placeholder Marker (what gets created)

A single non-executing `README.md` at the chosen path. It:

- Declares `execution_status: PLACEHOLDER_NO_EXECUTION`.
- Carries the contract summary and points to this audit doc.
- States that `SKILLz.md` and `executor.py` are **intentionally absent** until authorization.
- Is invisible to the WRE skills loader (README is never resolved), so no skill is registered.

No `SKILLz.md`, no `executor.py`, no `.py` of any kind is created.

---

## 8. Governance Contract (recommend -> gate -> route -> execute -> publish)

Maps onto existing primitives; nothing is wired live in this slice.

| Stage | Actor | Artifact / primitive (existing) | This slice |
|-------|-------|----------------------------------|------------|
| 1. Recommend | **RedDog** | emits a `CampaignWorkOrder` at `authority_tier: recommend_only` | contract only |
| 2. Gate | **OpenClaw** | `PolicyGateReceipt` decision in {`POLICY_ACCEPT`, `POLICY_REJECT`, `POLICY_ACCEPT_WITH_RETRIEVAL_GAP`}, `no_execution_performed: true` (`reddog_openclaw_work_order_policy_gate.py:54-76`) | contract only |
| 3. Route | **Hermes** | routes an accepted, authorized work order to the executor module_path | not wired |
| 4. Execute | **WRE / SKILLz** | runs `foundup_campaign_operator` SKILLz **only after future authorization** (012 / DAO go) | SKILLz absent -> fail-closed |
| 5. Publish | **AutoPost / social modules** | publish **only behind policy**; AutoPost publish leg already mock/blocked | no posting |

Invariants asserted by the placeholder:

- Execution requires `authority_tier: authorized` AND a future `SKILLz.md`. Neither exists.
- `denied_paths: ["**/*"]` and `forbidden_tokens` include `publish` -> deny-all default.
- The creative engine (Runway Agent 2.0 or any) is `engine_hint`/`engine_name` metadata
  only; no API binding, no availability assumption.

---

## 9. Scoped Pointer Updates

| File | Change | Justification |
|------|--------|---------------|
| `modules/platform_integration/social_media_orchestrator/ModLog.md` | one new dated entry pointing to this audit + the placeholder | WSP 22 -- the placeholder physically lands in this module |
| ROADMAP / INTERFACE | **NOT touched** | No public API changes; placeholder registers no skill. Touching them would overstate readiness. |
| `modules/foundups/ModLog.md` | **NOT touched** | Capability is FoundUp-facing but no foundups files change; cross-pointer deferred to the WSP 95 review of `modules/foundups/skillz/`. |

---

## 10. Validation Performed

- `git diff --check`: run pre-PR (whitespace / conflict markers). See PR.
- Mojibake scan: both new files authored ASCII-clean (no smart quotes, em-dash, ellipsis,
  middot). The appended ModLog entry adds ASCII-only bytes (the file already carries a
  leading BOM from prior history; not introduced here).
- No runtime files: confirmed -- two `.md` created, one `.md` appended; zero `.py`.
- Static contract check: the schema is a fenced documentary block, not imported anywhere.

---

## 11. WSP 97 Truth Boundary Checklist

| Guard | State |
|-------|-------|
| NO_RUNTIME_EXECUTION | PASS -- no executor, no posting, no scheduling, no API call |
| NO_REGISTRY_MUTATION | PASS -- `foundup_registry*.json` untouched |
| NO_MANIFEST_MUTATION | PASS -- no manifest created or edited |
| NO_PUBLIC_SURFACE_PROMOTION | PASS -- no public-surface / portfolio field changed |
| NO_SECRETS | PASS -- no `.env`, keys, tokens, or auth touched or displayed |
| NO_BROWSER_AUTOMATION | PASS -- no Selenium / Playwright / DOM code |
| NO_HOLOINDEX_RANKING_CHANGE | PASS -- no ranking/index code edited; gap recorded only |
| NO_SKILL_REGISTRATION | PASS -- README placeholder is non-loadable; no `SKILLz.md` |
| EVIDENCE_BACKED (CoT) | PASS -- WSP 95/109 + modules direct-read; file:line cited |
| DIALECTIC_SWEEP (CoR) | PASS -- 4 placement candidates compared in Section 6 |
| RETRIEVAL_GAP_RECORDED | PASS -- INDEX_GAP logged (Section 4.3) + follow-up slice |

---

## 12. WSP 15 Next Slices (MPS scored)

MPS = Complexity + Importance + Deferability + Impact (4-20). Higher Deferability score =
less deferrable.

| Next slice | C | I | D | Im | MPS | Pri | Note |
|------------|---|---|---|----|-----|-----|------|
| `HOLOINDEX_FOUNDUP_CAMPAIGN_SKILLZ_DISCOVERABILITY_PHASE1` | 2 | 4 | 4 | 4 | 14 | P1 | Re-index docs; close the RedDog skill_hits gap; run the Section 4.5 query set. No ranking-code change unless local tests require it. |
| `FOUNDUP_CAMPAIGN_BRIEF_SCHEMA_FIXTURES_PHASE1` | 2 | 4 | 3 | 4 | 13 | P1 | Turn the Section 5 contract into a JSON Schema + example fixtures (still no executor). |
| `FOUNDUP_CAMPAIGN_OPERATOR_DRYRUN_GATE_PHASE1` | 3 | 4 | 3 | 4 | 14 | P1 | RedDog -> OpenClaw `PolicyGateReceipt` dry-run for a `CampaignWorkOrder`; `no_execution_performed: true`. |
| `WSP_95_FOUNDUPS_SKILLZ_TREE_REVIEW_PHASE1` | 2 | 3 | 2 | 3 | 10 | P2 | WSP 95 review of whether `modules/foundups/skillz/` should exist; resolves cross-pointer deferred in Section 9. |
| `FOUNDUP_CAMPAIGN_OPERATOR_SKILLZ_AUTHORING_PHASE1` | 4 | 4 | 2 | 5 | 15 | P1 | Author `SKILLz.md` + `executor.py` -- GATED on 012/DAO authorization; the first slice that makes the skill loadable. |

---

*End of FOUNDUP_CAMPAIGN_OPERATOR_SKILLZ_PLACEHOLDER_PHASE1.*
