# pfMALL FoundUp Identity Report

**Worker**: D
**Date**: 2026-04-05
**Slice**: `PFMALL_FOUNDUP_IDENTITY_CATALOG_AUDIT_PHASE1`
**Status**: Read-only audit

---

## 1. Current pfMALL Catalog Lanes

Source: `public/member/mall-video-catalog.json` — 8 lanes.

| # | `foundup_id` | Entity | Source | Videos | Lifecycle | Tier |
|---|-------------|--------|--------|--------|-----------|------|
| 1 | `move2japan` | Move2Japan | youtube_channel (@MOVE2JAPAN) | 573 | active | F0_DAE |
| 2 | `undaodu` | UnDaoDu | youtube_channel (@UnDaoDu) | 512 | active | F0_DAE |
| 3 | `foundups_main` | FoundUps | youtube_channel (@FoundUps) | 44 | active | F0_DAE |
| 4 | `antifafm` | antifaFM | youtube_channel (@antifaFM) | 34 | proto | F0_DAE |
| 5 | `linkedin_012` | UnDaoDu Michael J Trout | linkedin_profile (@openstartup) | 0 | staging | F0_DAE |
| 6 | `linkedin_esingularity` | eSingularity | linkedin_profile (esingularity) | 0 | staging | F0_DAE |
| 7 | `linkedin_tsingularity` | tSingularity | linkedin_profile (tsingularity) | 0 | staging | F0_DAE |
| 8 | `linkedin_foundups` | FoundUps | linkedin_profile (foundups) | 0 | staging | F0_DAE |

**Evidence**: PROVEN — direct parse of `mall-video-catalog.json`.

---

## 2. Classification Per Entity

### Active pfMALL FoundUps (YouTube-sourced, have videos)

| `foundup_id` | Classification | Evidence |
|-------------|----------------|----------|
| `move2japan` | `ACTIVE_PFMALL_FOUNDUP` | 573 videos, lifecycle=active, has submodule at `modules/foundups/move2japan/`, domain canonical index lists it as "incubating FoundUp". PROVEN. |
| `undaodu` | `FOUNDUP_BRAND_META` | 512 videos, lifecycle=active, but this is 012's personal channel — a brand/identity, not a venture. It functions as a content lane in pfMALL but is not a FoundUp in the pAVS sense (no independent economic entity). INFERRED. |
| `foundups_main` | `FOUNDUP_BRAND_META` | 44 videos, lifecycle=active. This is the meta-channel for the FoundUps project itself. It's the umbrella, not a FoundUp within it. INFERRED. |
| `antifafm` | `ACTIVE_PFMALL_FOUNDUP` | 34 videos, lifecycle=proto, has full module at `modules/platform_integration/antifafm_broadcaster/`, active 24/7 broadcaster with skillz, OBS controller, telemetry. PROVEN. |

### LinkedIn Staging Lanes (zero videos, staging lifecycle)

| `foundup_id` | Classification | Evidence |
|-------------|----------------|----------|
| `linkedin_012` | `IDENTITY_ONLY` | 012's personal LinkedIn profile. Not a FoundUp — it's the operator's identity. Zero videos. PROVEN. |
| `linkedin_esingularity` | `LINKEDIN_MICRO_FOUNDUP` | LinkedIn company page (company_id: 2199715). Has domain description "AI education and singularity research". Could become a FoundUp. Currently zero content in pfMALL. INFERRED. |
| `linkedin_tsingularity` | `LINKEDIN_MICRO_FOUNDUP` | LinkedIn company page (company_id: 65471449). Has domain "Technological Singularity — 0201 channel". Currently zero content in pfMALL. INFERRED. |
| `linkedin_foundups` | `FOUNDUP_BRAND_META` | LinkedIn mirror of the FoundUps umbrella. Not itself a FoundUp. INFERRED. |

---

## 3. Geoze Status

**Is Geoze a current pfMALL FoundUp?** NO. **PROVEN.**

- Not present in `mall-video-catalog.json` (0 matches for `geoze` in `foundup_id` field)
- Not present in `linkedin_account_registry.py` constants
- Not present in `.env.example` LinkedIn accounts JSON

**What is Geoze today?**

| Surface | Status | Evidence |
|---------|--------|----------|
| X/Twitter | `ACCOUNT_ONLY` — `GeozeAi` username exists in `social_accounts.yaml` (line 161), display name "GeozeAi (Move2Japan)", credentials key `X_GEOZEAI`. PROVEN. |
| LinkedIn | `ACCOUNT_ONLY` — `GEOZE COIN` (company_id: 29041031) appears in `LN_DAE_CONCATENATED_TRIGGER_2026-03-27.md` (line 236). One article: "The Rebirth of Man by GEOZE.AI". Not in `social_accounts.yaml` active accounts, not in `linkedin_account_registry.py`. PROVEN. |
| pfMALL | Not present. PROVEN. |
| Repo | No `modules/foundups/geoze/` or similar. PROVEN. |

**Classification**: `CANDIDATE_FOUNDUP` — has X/Twitter account and LinkedIn company page, associated with Move2Japan, but no catalog entry, no module, no videos, no repo.

---

## 4. EDUIT Status

**Is EDUIT a current pfMALL FoundUp?** NO. **PROVEN.**

- Not present in `mall-video-catalog.json` as a `foundup_id`
- Two EDUIT-titled videos exist but are filed under `undaodu` lane: "Eduit: The vision" and "EduIT CEO Michael Trout"

**What is EDUIT today?**

| Surface | Status | Evidence |
|---------|--------|----------|
| LinkedIn | Active company page — `EDUIT, Inc` (company_id: 377243) in `social_accounts.yaml` (line 66), `LN_DAE_CONCATENATED_TRIGGER` (line 145), `LINKEDIN_CHANNEL_STRATEGY.md` (line 23). Domain: "FoundUP for autonomous learning on any device". Has 3 web resources (faq.eduit.org, exe.eduit.org, hapticsign.eduit.org). PROVEN. |
| LinkedIn Registry | Present in `linkedin_account_registry.py` as `LinkedInCompany.EDUIT = "eduit"` (line 69), company_id: 377243. PROVEN. |
| pfMALL | Not a lane. 2 videos exist on 012's `undaodu` YouTube channel (@UnDaoDu) — correctly hosted there because EDUIT has no YouTube channel of its own. The video indexer should tag these as EDUIT content so they can surface under a derived EDUIT lane in pfMALL. This is the indexer's core job: one YouTube channel, multiple FoundUp lanes via classification. PROVEN. |
| Repo | No `modules/foundups/eduit/`. PROVEN. |
| social_accounts.yaml | Has entry with domain "FoundUP for autonomous learning on any device", posting rules for `education_update` and `esingularity` events. PROVEN. |

**Classification**: `CANDIDATE_FOUNDUP` — explicitly described as "FoundUP for autonomous learning on any device" in social config. Has LinkedIn company page, 3 web domains, and 2 videos (filed under wrong lane). Stronger candidate than Geoze — already has external web presence.

---

## 5. Full Entity Inventory (All Surfaces)

Sources cross-referenced: `mall-video-catalog.json`, `social_accounts.yaml`, `linkedin_account_registry.py`, `LN_DAE_CONCATENATED_TRIGGER`, `LINKEDIN_CHANNEL_STRATEGY.md`, `modules/foundups/` submodules.

| Entity | pfMALL | LinkedIn | X/Twitter | Module | Classification |
|--------|--------|----------|-----------|--------|----------------|
| Move2Japan | `move2japan` (573 vids) | — | — | `modules/foundups/move2japan/` | `ACTIVE_PFMALL_FOUNDUP` |
| antifaFM | `antifafm` (34 vids) | — | — | `modules/platform_integration/antifafm_broadcaster/` | `ACTIVE_PFMALL_FOUNDUP` |
| UnDaoDu | `undaodu` (512 vids) | personal profile + company page | — | — | `FOUNDUP_BRAND_META` |
| FoundUps | `foundups_main` (44 vids) | company page (1263645) | @FoundUps | — | `FOUNDUP_BRAND_META` |
| eSingularity | `linkedin_esingularity` (0 vids) | company page (2199715) | — | — | `LINKEDIN_MICRO_FOUNDUP` |
| tSingularity | `linkedin_tsingularity` (0 vids) | company page (65471449) | — | — | `LINKEDIN_MICRO_FOUNDUP` |
| EDUIT | — | company page (377243) | — | — | `CANDIDATE_FOUNDUP` |
| GeozeAi | — | GEOZE COIN (29041031) | @GeozeAi | — | `CANDIDATE_FOUNDUP` |
| Science Swarm Hub | — | — | — | `modules/foundups/pqn_swarm_hub/` + external repo | `CANDIDATE_FOUNDUP` |
| GotJunk | — | — | — | `modules/foundups/gotjunk/` | `CANDIDATE_FOUNDUP` |
| Social Twin | — | — | — | `modules/foundups/social_twin/` | `CANDIDATE_FOUNDUP` |
| PQN Portal | — | — | — | `modules/foundups/pqn_portal/` | `CANDIDATE_FOUNDUP` |
| DAEs | — | company page | — | — | `IDENTITY_ONLY` |
| Social Beneficial Capitalism | — | company page (33431374) | — | — | `IDENTITY_ONLY` |
| BitCloutFork | — | company page | — | — | `IDENTITY_ONLY` |
| Duism | — | company page (68267516) | — | — | `IDENTITY_ONLY` |
| rESP | — | company page (107481170) | — | — | `IDENTITY_ONLY` |
| EIAH | — | company page (90392853) | — | — | `UNKNOWN` |
| Disney Plus Freelancer | — | company page | — | — | `IDENTITY_ONLY` |
| LN Republican Voters | — | company page (68353110) | — | — | `IDENTITY_ONLY` (restricted) |
| 012 Personal | `linkedin_012` (0 vids) | personal profile | — | — | `IDENTITY_ONLY` |

---

## 6. LinkedIn Company Pages Summary

012 manages **11 LinkedIn entities** (1 personal + 10 company pages via switcher):

| # | Entity | Company ID | In pfMALL? | In social_accounts.yaml? | Classification |
|---|--------|-----------|------------|-------------------------|----------------|
| 1 | UnDaoDu (personal) | — | Yes (`linkedin_012`) | Yes | IDENTITY_ONLY |
| 2 | EDUIT, Inc | 377243 | No | Yes | CANDIDATE_FOUNDUP |
| 3 | FoundUps | 1263645 | Yes (`linkedin_foundups`) | Yes | FOUNDUP_BRAND_META |
| 4 | eSingularity | 2199715 | Yes (`linkedin_esingularity`) | No (in registry only) | LINKEDIN_MICRO_FOUNDUP |
| 5 | tSingularity | 65471449 | Yes (`linkedin_tsingularity`) | Yes | LINKEDIN_MICRO_FOUNDUP |
| 6 | rESP | 107481170 | No | No | IDENTITY_ONLY |
| 7 | Social Beneficial Capitalism | 33431374 | No | Yes | IDENTITY_ONLY |
| 8 | Duism | 68267516 | No | Yes (restricted) | IDENTITY_ONLY |
| 9 | EIAH | 90392853 | No | No | UNKNOWN |
| 10 | LN Republican Voters | 68353110 | No | Yes (restricted) | IDENTITY_ONLY |
| 11 | GEOZE COIN | 29041031 | No | No (X only) | CANDIDATE_FOUNDUP |

Additional LinkedIn entries in `social_accounts.yaml` NOT in trigger doc:
- DAEs (company page, no ID listed)
- UnDaoDu (company page, separate from personal)
- Disney Plus Freelancer (company page)

Additional LinkedIn entries in `linkedin_account_registry.py` NOT in other sources:
- autonomouswall, aiharmonic, foundups100x100, decentralizedcrypto (IDs in `.env.example`)

---

## 7. Discrepancies Found

| Discrepancy | Details | Severity |
|-------------|---------|----------|
| EDUIT videos not yet indexed as EDUIT content | "Eduit: The vision" and "EduIT CEO Michael Trout" live on 012's @UnDaoDu YouTube channel (correctly — EDUIT has no own channel). The video indexer should tag these as EDUIT content so they surface under a derived EDUIT lane in pfMALL. This is the indexer's core value: one source channel → multiple FoundUp lanes via classification. | MEDIUM (blocks EDUIT pfMALL lane) |
| LinkedIn entities inconsistent across sources | `social_accounts.yaml` has 10 LinkedIn entries, trigger doc has 11, `linkedin_account_registry.py` has ~11 constants. Sets don't fully overlap. | MEDIUM |
| GeozeAi X/Twitter only | Has X account configured but no LinkedIn in `social_accounts.yaml` despite having a LinkedIn company page (GEOZE COIN) | LOW |
| 4 LinkedIn registry entries have no other surface | autonomouswall, aiharmonic, foundups100x100, decentralizedcrypto — in `.env.example` but not in social_accounts.yaml or pfMALL | LOW |

---

**WSP 97 Applied**: All claims verified against file contents. No assumptions from naming. Each classification cites source file and line where possible. Evidence standard met.
