# Browser Actions - Sprint Roadmap

**Module:** infrastructure/browser_actions
**WSP Reference:** WSP 22 (ModLog), WSP 37 (Scoring)

---

## Vision Statement

Provide a unified, intelligent interface for all platform browser automation, routing to the optimal driver based on action complexity.

---

## Phase Progression: null → 001 → 011 → 111

### Current Phase: POC (null → 001)

---

## Current bounded checkpoint — 2026-09-23

Requested-note repair 12/P2 passes 23 frozen cases locally and independently
(baseline 4 fail/19 pass). Add/type now precede one explicit Send; failed preparation
prevents Send and success credit. No-message fallback/bookkeeping are unchanged.
The root backlog re-scores manager-result/UI-admission qualification separately.
[Contract](../../platform_integration/linkedin_agent/docs/LINKEDIN_REVIEW_WORKFLOW.md#rsi-requested-note-repair--2026-09-23).

The sprint map below is historical planning: source such as `action_router.py`
already exists. Its unchecked boxes are not a verified current completion audit.

## Sprint Map (Aligned with foundups_vision)

### Sprint A1: Action Router Foundation
**Priority:** P0 (Critical Path)
**Tokens:** 300
**Status:** 🔴 Not Started
**Depends On:** foundups_vision V1

**Objectives:**
- [ ] Create `action_router.py` with driver routing logic
- [ ] Implement driver initialization (Selenium + UI-TARS)
- [ ] Add action complexity classification
- [ ] Create fallback mechanism

**Acceptance Criteria:**
- Router correctly identifies simple vs vision actions
- Falls back to Selenium if UI-TARS unavailable
- Emits telemetry for routing decisions

---

### Sprint A2: YouTube Actions
**Priority:** P0 (Critical Path)
**Tokens:** 400
**Status:** 🔴 Not Started
**Depends On:** A1, foundups_vision V3

**Objectives:**
- [ ] Create `youtube_actions.py`
- [ ] Implement `like_comment()` via UI-TARS
- [ ] Implement `reply_to_comment()` via API + UI-TARS like
- [ ] Implement `navigate_to_video()` via Selenium
- [ ] Add `like_and_reply()` combo method

**Acceptance Criteria:**
- Can like YouTube comments as Move2Japan
- Can reply to comments with API
- Combo method likes AND replies in single session

---

### Sprint A3: LinkedIn Actions
**Priority:** P1 (High)
**Tokens:** 300
**Status:** 🟡 In Progress
**Depends On:** A1

**Objectives:**
- [ ] Create `linkedin_actions.py`
- [ ] Migrate posting from social_media_orchestrator
- [ ] Add comment functionality
- [ ] Integrate with UI-TARS scheduler
- [x] Wire layered digital twin parameter passthrough (L1 comment/mentions, L3 repost/schedule inputs)

**Acceptance Criteria:**
- Can post to LinkedIn company pages
- Can comment on posts
- Schedule integration works

---

### Sprint A4: X/Twitter Actions
**Priority:** P1 (High)
**Tokens:** 300
**Status:** 🔴 Not Started
**Depends On:** A1

**Objectives:**
- [ ] Create `x_actions.py`
- [ ] Migrate posting from x_twitter module
- [ ] Add reply functionality
- [ ] Add like/retweet actions

**Acceptance Criteria:**
- Can post to X as FoundUps
- Can post to X as Move2Japan
- Like and retweet work

---

### Sprint A5: FoundUp Actions (Future)
**Priority:** P2 (Medium)
**Tokens:** 400
**Status:** 🔴 Not Started
**Depends On:** A2, A3, A4

**Objectives:**
- [ ] Create `foundups_actions.py`
- [ ] Implement livechat posting
- [ ] Implement admin actions
- [ ] Enable 0102 to operate FoundUp UIs

**Acceptance Criteria:**
- Can post to FoundUp livechat
- Can perform admin actions
- Works with GotJunk and other FoundUps

---

### Sprint A6: Integration & Optimization
**Priority:** P2 (Medium)
**Tokens:** 300
**Status:** ✅ Complete
**Depends On:** A2, A3, A4

**Objectives:**
- ✅ Wire all actions to AI Overseer (`ai_overseer_integration.py`)
- ✅ Add WRE skill definitions (3 skills created)
- ✅ Optimize action routing based on patterns (`get_pattern_recommendation()`)
- ✅ Create unified telemetry dashboard (`telemetry_dashboard.py`)

**Acceptance Criteria:**
- ✅ AI Overseer can trigger any platform action via `BrowserActionsCoordinator`
- ✅ WRE skills for common workflows exist (YouTube, LinkedIn, FoundUp)
- ✅ Pattern-based optimization operational (success rate-based routing)

---

## Parallel Execution Plan

```
Week 1-2:
├── V1: UI-TARS Bridge (foundups_vision)
├── V4: Browser Manager Migration (foundups_selenium)
└── A1: Action Router (browser_actions)

Week 3:
├── V2: Vision Executor (foundups_vision)
└── A2: YouTube Actions (browser_actions)

Week 4:
├── V3: YouTube Actions Integration (foundups_vision)
├── V5: RealtimeCommentDialogue (communication)
├── A3: LinkedIn Actions (browser_actions)
└── A4: X Actions (browser_actions)

Week 5+:
├── V6: Pattern Learning (foundups_vision)
├── A5: FoundUp Actions (browser_actions)
└── A6: Integration (browser_actions)
```

---

## Token Budget

| Sprint | Tokens | Cumulative |
|--------|--------|------------|
| A1 | 300 | 300 |
| A2 | 400 | 700 |
| A3 | 300 | 1,000 |
| A4 | 300 | 1,300 |
| A5 | 400 | 1,700 |
| A6 | 300 | 2,000 |
| **Total** | **2,000** | |

---

## Combined Budget (Vision + Actions)

| Module | Tokens |
|--------|--------|
| foundups_vision | 2,200 |
| browser_actions | 2,000 |
| **Total** | **4,200** |

---

**Document Status:** Ready for Sprint A1
**Architect:** 0102



