# Canonical FoundUp Inventory

**Worker**: D
**Date**: 2026-04-05
**Slice**: `PFMALL_FOUNDUP_IDENTITY_CATALOG_AUDIT_PHASE1`
**Status**: Read-only audit

---

## Classification Key

| Classification | Meaning |
|----------------|---------|
| `ACTIVE_PFMALL_FOUNDUP` | In pfMALL catalog with videos, has module/code |
| `LINKEDIN_MICRO_FOUNDUP` | LinkedIn company page functioning as a content lane, in pfMALL staging |
| `FOUNDUP_BRAND_META` | Umbrella/brand/personal identity — not itself a FoundUp |
| `CANDIDATE_FOUNDUP` | Has enough surface presence to become a FoundUp but isn't one yet |
| `ACCOUNT_ONLY` | Social media account with no FoundUp structure |
| `IDENTITY_ONLY` | LinkedIn company page or identity used for posting, not a venture |
| `UNKNOWN` | Insufficient evidence to classify |

---

## Active FoundUps (in pfMALL today)

| FoundUp | `foundup_id` | Videos | Module | Classification |
|---------|-------------|--------|--------|----------------|
| **Move2Japan** | `move2japan` | 573 | `modules/foundups/move2japan/` | ACTIVE_PFMALL_FOUNDUP |
| **antifaFM** | `antifafm` | 34 | `modules/platform_integration/antifafm_broadcaster/` | ACTIVE_PFMALL_FOUNDUP |

These are the only two entities that qualify as active FoundUps in pfMALL: they have video content, dedicated code modules, and distinct venture identity.

---

## Brand/Meta Lanes (in pfMALL, but not FoundUps)

| Entity | `foundup_id` | Videos | Why not a FoundUp |
|--------|-------------|--------|-------------------|
| **UnDaoDu** | `undaodu` | 512 | 012's personal channel. A brand, not a venture. |
| **FoundUps** | `foundups_main` | 44 | The umbrella project itself. FoundUps is the system, not a FoundUp within it. |

These occupy pfMALL catalog lanes but are structurally different — they're the operator and the platform, not ventures.

---

## LinkedIn Micro-FoundUps (in pfMALL staging, zero videos)

| Entity | `foundup_id` | LinkedIn Company ID | Why micro |
|--------|-------------|--------------------|----|
| **eSingularity** | `linkedin_esingularity` | 2199715 | Has domain ("AI education"), company page, but zero pfMALL content. Could become full FoundUp if content is produced. |
| **tSingularity** | `linkedin_tsingularity` | 65471449 | Has domain ("Technological Singularity — 0201"), company page, zero pfMALL content. |

---

## Candidate FoundUps (not in pfMALL yet)

| Entity | Surfaces | Readiness | Notes |
|--------|----------|-----------|-------|
| **EDUIT** | LinkedIn (377243), 3 web domains, 2 videos on 012's @UnDaoDu channel (no own YT channel) | HIGH | Described as "FoundUP for autonomous learning on any device" in social config. Has external web presence. Strongest candidate. Videos live on `undaodu` source channel — the indexer's job is to tag them as EDUIT content and surface under a derived lane. This is the core indexer value prop: one channel, multiple FoundUp lanes via classification. |
| **AutoPost** | GitHub repo (FOUNDUPS/AutoPost), already externalized | HIGH | Both a FoundUp AND a tool. Content pipeline: users post unlisted videos → YouTube → routed to FoundUp → pfMALL display + social distribution. Part of AI Automation service FoundUp. Infrastructure-as-a-venture. |
| **GeozeAi** | X/Twitter (@GeozeAi), LinkedIn (GEOZE COIN, 29041031) | MEDIUM | Associated with Move2Japan. Has 2 social accounts but no videos, no module, no repo. |
| **Science Swarm Hub** | External repo (`github.com/FOUNDUPS/science-swarm-hub`), module stub (`modules/foundups/pqn_swarm_hub/`) | HIGH | v0.12.0, 108 tests, CONTRIBUTING.md. Ready for pfMALL listing. |
| **GotJunk** | Module (`modules/foundups/gotjunk/`), Cloud Run deployment | MEDIUM | Proto-ready spin-out per domain canonical index. No pfMALL presence. |
| **Social Twin** | Module (`modules/foundups/social_twin/`) | LOW | PoC architecture lock. Not ready for pfMALL. |
| **PQN Portal** | Module (`modules/foundups/pqn_portal/`) | LOW | Still incubating. |

---

## Identity-Only Entities (not FoundUps)

These are LinkedIn company pages or social accounts used for posting/engagement. They do not have venture identity, independent economics, or FoundUp structure.

| Entity | Surface | Purpose |
|--------|---------|---------|
| 012 Personal | LinkedIn profile, pfMALL (`linkedin_012`) | Operator identity |
| FoundUps LinkedIn | LinkedIn page (1263645), pfMALL (`linkedin_foundups`) | Umbrella brand mirror |
| DAEs | LinkedIn page | Conceptual channel for DAE content |
| Social Beneficial Capitalism | LinkedIn page (33431374) | Philosophy/economics content |
| BitCloutFork | LinkedIn page | Historical web3 identity |
| Duism | LinkedIn page (68267516) | Reserved — Oracle counter-narratives |
| rESP | LinkedIn page (107481170) | PQN/CMST research channel |
| Disney Plus Freelancer | LinkedIn page | Gig economy content |
| LN Republican Voters | LinkedIn page (68353110) | Restricted — political |
| EIAH | LinkedIn page (90392853) | Unknown purpose |

---

## Orphaned LinkedIn Registry Entries

These exist in `linkedin_account_registry.py` and/or `.env.example` but have no corresponding entry in `social_accounts.yaml`, pfMALL, or any other active surface:

- `autonomouswall` (company ID: 35532191)
- `aiharmonic` (company ID: 96096638)
- `foundups100x100` (company ID: 64659868)
- `decentralizedcrypto` (company ID: 33433199)

Classification: UNKNOWN — no evidence of active use or FoundUp intent.

---

## Summary Counts

| Classification | Count |
|---------------|-------|
| ACTIVE_PFMALL_FOUNDUP | 2 (Move2Japan, antifaFM) |
| FOUNDUP_BRAND_META | 3 (UnDaoDu, FoundUps main, FoundUps LinkedIn) |
| LINKEDIN_MICRO_FOUNDUP | 2 (eSingularity, tSingularity) |
| CANDIDATE_FOUNDUP | 6 (EDUIT, GeozeAi, Science Swarm Hub, GotJunk, Social Twin, PQN Portal) |
| IDENTITY_ONLY | 11 |
| UNKNOWN | 5 (EIAH + 4 orphaned registry entries) |

**Total entities tracked across all surfaces**: ~29

---

*This inventory is a point-in-time snapshot. Update when entities are promoted or retired.*
