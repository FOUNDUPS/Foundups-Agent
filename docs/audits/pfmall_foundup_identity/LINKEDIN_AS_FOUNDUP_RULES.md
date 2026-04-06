# LinkedIn Lanes as FoundUps — Classification Rules

**Worker**: D
**Date**: 2026-04-05
**Slice**: `PFMALL_FOUNDUP_IDENTITY_CATALOG_AUDIT_PHASE1`
**Status**: Read-only audit

---

## 1. The Question

012 manages 10+ LinkedIn company pages. Some are described as "FoundUPs" in their config (e.g., EDUIT: "FoundUP for autonomous learning"). Others are content channels (e.g., Social Beneficial Capitalism), personal brands (UnDaoDu page), or restricted pages (LN Republican Voters).

**When should a LinkedIn company page be treated as a full FoundUp?**

---

## 2. Proposed Rule: The FoundUp Promotion Test

A LinkedIn company page should be promoted to `CANDIDATE_FOUNDUP` (and eventually `ACTIVE_PFMALL_FOUNDUP`) when it passes **3 of 5** criteria:

| # | Criterion | What It Means |
|---|-----------|---------------|
| 1 | **Independent venture identity** | Has a name, mission, and domain that is distinct from 012's personal brand or the FoundUps umbrella |
| 2 | **External presence** | Has at least one surface beyond LinkedIn: website, GitHub repo, product, or app |
| 3 | **Content production** | Produces or can produce video/article content suitable for pfMALL |
| 4 | **Economic potential** | Could plausibly have its own F_i token, UPS staking, and stakeholder interior |
| 5 | **Distinct audience** | Serves a user base that is not identical to another existing FoundUp |

### Applying the test

| Entity | Criterion 1 | Criterion 2 | Criterion 3 | Criterion 4 | Criterion 5 | Score | Verdict |
|--------|:-----------:|:-----------:|:-----------:|:-----------:|:-----------:|:-----:|---------|
| EDUIT | Yes | Yes (3 web domains) | Yes (2 videos exist) | Yes (edtech product) | Yes (learners) | **5/5** | CANDIDATE_FOUNDUP |
| eSingularity | Yes | No | No (0 videos) | Maybe | Partial (overlaps tSingularity) | **1.5/5** | Stay MICRO |
| tSingularity | Yes | No | No (0 videos) | Maybe | Partial (overlaps eSingularity) | **1.5/5** | Stay MICRO |
| GeozeAi | Yes | No (X account only) | No (0 videos) | Maybe | Partial (overlaps Move2Japan) | **1.5/5** | Stay CANDIDATE (X gives it edge) |
| DAEs | Yes | No | No | No (conceptual) | No (same as FoundUps) | **1/5** | IDENTITY_ONLY |
| Social Beneficial Capitalism | Yes | No | No | No (philosophy) | No (same as FoundUps) | **1/5** | IDENTITY_ONLY |
| BitCloutFork | Yes | No | No | Maybe (historical) | No | **1/5** | IDENTITY_ONLY |
| Duism | Yes | No | No | No (reserved) | Maybe | **1/5** | IDENTITY_ONLY |
| rESP | Yes | No | No | Maybe (research) | Partial (overlaps PQN) | **1.5/5** | IDENTITY_ONLY (until PQN grows) |
| EIAH | Unknown | No | No | Unknown | Unknown | **0/5** | UNKNOWN |
| Disney Plus Freelancer | Yes | No | No | No | Yes (gig workers) | **2/5** | IDENTITY_ONLY |
| LN Republican Voters | Yes | No | No | No | Yes (political) | **2/5** | IDENTITY_ONLY (restricted) |

---

## 3. The eSingularity/tSingularity Question

These two are interesting edge cases:

- Both are in pfMALL catalog as `linkedin_esingularity` and `linkedin_tsingularity`
- Both have zero videos and zero external presence beyond LinkedIn
- Their domains overlap: "AI education" vs "Technological Singularity"
- They share `related_lanes` with each other

**Options**:
1. **Merge into one FoundUp** — "Singularity" covering both educational and technological angles
2. **Keep separate as micro-FoundUps** — let them grow independently, promote whichever produces content first
3. **Demote to IDENTITY_ONLY** — they're LinkedIn posting channels, not ventures

**Current recommendation**: Option 2 (keep separate, no action). Neither meets the promotion threshold. If one produces content, reassess. If neither does within 2 quarters, demote to IDENTITY_ONLY and remove from pfMALL catalog.

---

## 4. The "Already Called a FoundUp" Problem

`social_accounts.yaml` line 71 explicitly says EDUIT is a "FoundUP for autonomous learning on any device". `social_accounts.yaml` line 111 says BitCloutFork is "= FoundUP (the original BitClout fork IS a foundup)".

These self-descriptions don't make something a FoundUp in the pAVS architecture sense. A FoundUp needs:
- A repeating unit (pfMALL listing + PWA + Discord + GitHub + sentinel + gate + interior) per `FOUNDUPS_MASTER_ARCHITECTURE.md`
- Or at minimum: content in pfMALL + distinct venture identity

Calling yourself a FoundUp in a config comment is not the same as being one. EDUIT passes the promotion test on merit. BitCloutFork does not.

---

## 5. LinkedIn → pfMALL Pipeline

When a LinkedIn company page is promoted to CANDIDATE_FOUNDUP, the pipeline is:

```
1. Confirm 3/5 criteria met
2. Create pfMALL catalog entry (foundup_id, source_type: linkedin_profile, lifecycle: staging)
3. If videos exist, index them into the lane
4. When content reaches threshold (>10 items), promote lifecycle to active
5. Consider module creation when engineering work is needed
6. Add Discord category per FOUNDUP_TEMPLATE.md when community forms
```

The pipeline is gradual. Not every LinkedIn page needs a catalog entry. Only those that pass the promotion test.

---

## 6. Reverse Rule: When to Demote

A pfMALL lane should be demoted from LINKEDIN_MICRO_FOUNDUP to IDENTITY_ONLY when:

- 2+ quarters with zero content production
- No distinct audience has formed
- The entity has been absorbed by another FoundUp's scope
- 012 decides the identity is a posting channel, not a venture

Demotion means removing from `mall-video-catalog.json`, not deleting the LinkedIn page.

---

*These rules are proposed, not enacted. 012 approval required before any promotions or demotions.*
