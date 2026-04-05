# Next FoundUp Additions to pfMALL

**Worker**: D
**Date**: 2026-04-05
**Slice**: `PFMALL_FOUNDUP_IDENTITY_CATALOG_AUDIT_PHASE1`
**Status**: Read-only audit — recommendations only

---

## Recommended Additions (Priority Order)

### 1. EDUIT — HIGH priority

**Why**: Strongest candidate. Explicitly described as "FoundUP for autonomous learning on any device". Has 3 external web domains (faq.eduit.org, exe.eduit.org, hapticsign.eduit.org). Has LinkedIn company page (377243). Has 2 videos already indexed (currently filed under `undaodu` — wrong lane). Passes 5/5 promotion criteria.

**What to do**:
- Add `eduit` as a **derived lane** in `mall-video-catalog.json`
- EDUIT has no YouTube channel — its videos live on 012's @UnDaoDu channel. The video indexer must tag EDUIT-topic videos and surface them under the derived lane. Do NOT move videos out of `undaodu` — they stay on the source channel, but appear in both lanes via classification.
- This is the indexer's core value proposition: one YouTube channel → multiple FoundUp lanes via content classification.
- Set `lifecycle: staging`, `source_type: derived` (new type — content classified from parent channels, not a direct source)
- Add Discord category when ready (per `FOUNDUP_TEMPLATE.md`)

**Evidence**: PROVEN — `social_accounts.yaml` line 66-80, `LN_DAE_CONCATENATED_TRIGGER` line 145, `linkedin_account_registry.py` line 69.

---

### 2. Science Swarm Hub — HIGH priority

**Why**: Has external GitHub repo (v0.12.0, 108 tests), module stub at `modules/foundups/pqn_swarm_hub/`, FoundUp brief at `PQN_SWARM_HUB_FOUNDUP_BRIEF.md`, Discord runbook artifacts complete. Missing only a pfMALL catalog entry.

**What to do**:
- Add `science_swarm` lane to `mall-video-catalog.json`
- Set `lifecycle: staging`, `source_type: github_repo` (new source type — no YouTube/LinkedIn content yet)
- Discord category per the FOUNDUPS Discord Blueprint
- May need video content created (intro video, demo, explainer)

**Evidence**: PROVEN — `github.com/FOUNDUPS/science-swarm-hub` live, `modules/foundups/pqn_swarm_hub/` exists, `PQN_SWARM_HUB_FOUNDUP_BRIEF.md` canonical.

---

### 3. AutoPost — HIGH priority

**Why**: Both a FoundUp and a tool. Has its own GitHub repo (`FOUNDUPS/AutoPost`, already externalized per domain canonical index). AutoPost is the content pipeline for the entire ecosystem — users post unlisted videos to YouTube channels, which get routed to the right FoundUp and displayed on pfMALL or shared on social media. Part of the AI Automation service FoundUp. Infrastructure-as-a-venture.

**What to do**:
- Add `autopost` lane to `mall-video-catalog.json` (source_type: `github_repo` or `tool`)
- Add Discord category: `#autopost-general`, `#autopost-github`, `#autopost-work`, `autopost-voice`
- Add roles: `@autopost-contributor`, `@autopost-notify`
- GitHub webhook from `FOUNDUPS/AutoPost` to `#autopost-github`

**Evidence**: PROVEN — repo exists at `FOUNDUPS/AutoPost` (per domain canonical index: "Already Externalized"), 012 confirmed it is both a FoundUp and a tool (2026-04-06).

---

### 4. GotJunk — MEDIUM priority

**Why**: Has module at `modules/foundups/gotjunk/`, Cloud Run deployment exists, domain canonical index classifies it as "Proto-Ready Spin-Out Candidate" with "roadmap already in Prototype". But no pfMALL presence, no videos, no LinkedIn page.

**What to do**:
- Assess whether GotJunk should appear in pfMALL before exfoliation
- If yes: add catalog entry with available content
- If no: skip pfMALL, proceed to exfoliation per `FOUNDUP_EXFOLIATION_PROTOCOL.md`

**Evidence**: PROVEN for module existence. INFERRED for pfMALL readiness (needs 012 decision).

---

### 5. GeozeAi — LOW priority

**Why**: Has X/Twitter account (@GeozeAi) and LinkedIn company page (GEOZE COIN, 29041031). Associated with Move2Japan. But zero videos, no module, no repo, no web presence beyond social accounts. Passes only 1.5/5 promotion criteria.

**What to do**:
- No pfMALL addition until content exists
- If GeozeAi starts producing video content (via Move2Japan or independently), reassess
- Consider whether GeozeAi is a sub-identity of Move2Japan or a distinct venture

**Evidence**: PROVEN for account existence. INFERRED for FoundUp potential.

---

## Not Recommended for Addition

| Entity | Why Not |
|--------|---------|
| eSingularity | Zero content, no external presence. Keep as LINKEDIN_MICRO_FOUNDUP in current staging lane. |
| tSingularity | Zero content, overlaps eSingularity. Keep as staging. |
| DAEs | Conceptual channel, not a venture. |
| Social Beneficial Capitalism | Philosophy content channel, not a venture. |
| BitCloutFork | Historical identity, no active content or product. |
| Duism | Reserved for Oracle execution. Not a venture. |
| rESP | Research identity, overlaps Science Swarm Hub scope. |
| Social Twin | PoC architecture lock. Not ready. |
| PQN Portal | Still incubating. Not ready. |

---

## Catalog Impact Summary

If all HIGH recommendations are implemented:

| Metric | Before | After |
|--------|--------|-------|
| Total pfMALL lanes | 8 | 10 |
| Active FoundUps (with content) | 2 | 2 (EDUIT starts with 2 videos; Science Swarm starts staging) |
| Brand/meta lanes | 3 | 3 (unchanged) |
| LinkedIn micro-FoundUps | 2 | 2 (unchanged) |
| Staging lanes | 4 | 5 (Science Swarm added) |

---

## Prerequisite Actions

Before any additions:

1. **EDUIT**: Confirm 012 wants EDUIT treated as a FoundUp (not just a LinkedIn posting channel)
2. **Science Swarm Hub**: Decide if `source_type: github_repo` is valid (current schema only has `youtube_channel` and `linkedin_profile`)
3. **Catalog schema**: Check if `PFMALL_VIDEO_MALL_CATALOG_SCHEMA.md` needs updating for new source types
4. **Video indexer**: Confirm `video_indexer.py` can handle lanes with zero YouTube videos

---

*These are recommendations. No changes made. 012 decides order and timing.*
