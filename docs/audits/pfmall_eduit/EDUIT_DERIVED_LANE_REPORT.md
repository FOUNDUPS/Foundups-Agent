# EDUIT Derived Lane Feasibility Report

**Worker C** · `PFMALL_EDUIT_DERIVED_LANE_FEASIBILITY_PHASE1` · 2026-04-05

---

## Verdict: FEASIBLE — 21 videos, minimal indexer change, no new infrastructure

---

## 1. Feasibility Summary

| Question | Answer |
|----------|--------|
| Is EDUIT a real FoundUp? | YES — described as "FoundUP for autonomous learning on any device" in `social_accounts.yaml` line 70. Has 3 web domains, LinkedIn company page (377243), and `LinkedInCompany.EDUIT` constant in registry. |
| Does enough content exist? | YES — 21 videos in `undaodu` lane match EDUIT/eSingularity topics (~114 min runtime). More content than antifaFM (34 videos). |
| Can it land without new infrastructure? | YES — no new YouTube channel, no new API keys, no new module directory. Content is classified from existing undaodu source. |
| What blocks it? | One new `source_type` value ("derived"), video object copy into catalog, poster image. Category `ai-education` and its CSS theme already exist. All changes are additive, no breaking changes. |

---

## 2. Which existing videos in undaodu are EDUIT/eSingularity content?

**21 out of 512 undaodu videos (4.1%)**. Full list: [EDUIT_SOURCE_VIDEO_CANDIDATES.md](EDUIT_SOURCE_VIDEO_CANDIDATES.md)

Breakdown:
- 2 explicitly titled "Eduit" (vision + CEO intro)
- 14 explicitly titled "eSingularity" (EDUIT's product platform)
- 5 education/singularity topic (global education, certification, higher ed)

**eSingularity IS EDUIT's product** — confirmed by `social_accounts.yaml` which lists `esingularity` as a posting event type under the `eduit` LinkedIn account.

Worker D's earlier audit reported "2 videos" — that only counted explicit `Eduit` in title. The actual corpus is 10x larger when including eSingularity content.

---

## 3. What minimum evidence set justifies an EDUIT lane?

EDUIT passes all 5 promotion criteria from `NEXT_FOUNDUP_ADDITIONS.md`:

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Named entity with identity | PASS | "EDUIT, Inc" — LinkedIn company page 377243 |
| External web presence | PASS | faq.eduit.org, exe.eduit.org, hapticsign.eduit.org |
| Content exists | PASS | 21 videos, ~114 minutes |
| Described as FoundUp | PASS | "FoundUP for autonomous learning on any device" |
| In account registry | PASS | `LinkedInCompany.EDUIT = "eduit"` (linkedin_account_registry.py:69) |

Additional evidence:
- `social_accounts.yaml` lines 66-80: full EDUIT account config with posting rules
- `LN_DAE_CONCATENATED_TRIGGER` line 145: EDUIT in LinkedIn posting chain
- `LINKEDIN_CHANNEL_STRATEGY.md` line 23: EDUIT in channel strategy

---

## 4. What indexer/tagging change is needed for one source channel -> multiple FoundUp lanes?

### Current Architecture

```
YouTube Channel (@UnDaoDu) → VideoIndexer("undaodu") → undaodu lane in catalog
```

The `VideoIndexer` class in `video_indexer.py` is channel-locked: `__init__(self, channel)` requires a key from `CHANNEL_CONFIG` (line 145-146). There is no concept of derived lanes or cross-lane classification.

The `gemini_video_analyzer.py` does content-derived tagging (line 925-942) — it generates hashtags from video content. But tags are flat strings with no lane-routing semantics.

### What Needs to Change

**For EDUIT specifically (minimal path — no indexer changes):**

The 21 videos can be identified by title keyword matching at catalog build time. No indexer change needed — the classification is deterministic from existing title data.

```python
EDUIT_KEYWORDS = ["eduit", "esingularity", "e-singularity", "hapticsign"]

def is_eduit_video(video: dict) -> bool:
    title = (video.get("title") or "").lower()
    return any(kw in title for kw in EDUIT_KEYWORDS)
```

**For general derived lanes (future — indexer enhancement):**

If more FoundUps need derived lanes from shared channels, the indexer should gain:

1. **Lane classification layer** — a new processing layer (alongside audio/visual/multimodal) that tags each video with zero or more `derived_lanes` based on content analysis
2. **Classification config** — a mapping from keywords/topics to `foundup_id` values, stored alongside `CHANNEL_CONFIG`
3. **Catalog builder** — a build step that reads indexed videos and distributes them across lanes based on `derived_lanes` tags

This is a Tier 2 enhancement. For EDUIT alone, title-matching at catalog level is sufficient.

### Architecture Diagram

```
Current (1:1):
  @UnDaoDu channel → undaodu lane

Proposed (1:N, EDUIT only):
  @UnDaoDu channel → undaodu lane (all 512 videos)
                    → eduit lane   (21 videos, title-classified subset)

Future (1:N, general):
  @UnDaoDu channel → VideoIndexer → derived_lanes tagger
                    → undaodu lane (all videos)
                    → eduit lane   (education/eSingularity tagged)
                    → [future]     (other topic-derived lanes)
```

---

## 5. Implementation Cost

| Change | Effort | Files |
|--------|--------|-------|
| Add `eduit` entry to `mall-video-catalog.json` | Small | 1 |
| Copy 21 video objects from undaodu into eduit lane | Small | 1 (same file) |
| ~~Add CSS class~~ | NONE | `theme-cat-ai-education` already exists in both CSS files |
| Add poster image | Small | 1 (`/media/posters/eduit.jpg`) |
| Update undaodu `related_lanes` to include `eduit` | Small | 1 (same catalog) |
| Update catalog schema doc for `source_type: derived` | Small | 1 |

**Total: ~5 small changes across 3 files + 1 image asset.**

No indexer changes. No module creation. No new env vars. No new API keys.

---

## 6. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Video duplication in catalog (same video in 2 lanes) | LOW | Acceptable — catalog is build artifact, source of truth is undaodu. Document that eduit videos are references. |
| `source_type: "derived"` is a new enum value | LOW | Schema doc update + pfMALL runtime already handles unknown source_types gracefully (only used for display text). |
| Future undaodu videos about EDUIT won't auto-classify | MEDIUM | Title-match at catalog build time catches new additions. Full indexer classification is Tier 2. |
| ~~Category CSS~~ | RESOLVED | `ai-education` category and `theme-cat-ai-education` CSS already exist in schema and stylesheets. |

---

## 7. Recommendation

**Ship it as a catalog-only change.** The 21 videos justify the lane. The implementation is 4-file additive. No indexer rework needed for this specific case.

**Build order:**
1. Add `eduit` lane entry to `mall-video-catalog.json` with 21 video objects (category: `ai-education`)
2. Add poster image
3. Update schema doc for `source_type: derived`
4. Test: pfMALL renders EDUIT tile, videos play, entry page works

---

**Worker C** · All four required questions answered. Three deliverables written. No code changes made. EDUIT is feasible and the smallest truthful path is catalog-level classification, not indexer rework.
