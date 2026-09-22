# Browser Actions - ModLog

**Module:** infrastructure/browser_actions
**WSP Reference:** WSP 22 (ModLog Protocol)

---

## Change Log

## 2026-09-22: Connection dry-run state qualification

- WSP00/15/22/50/62/84/97; 12/P2. Ten fixed current-behavior cases pass locally and independently; four original tests remain unchanged/deselected. Production source unchanged; inert routing, constructor bypass and patched sleep only.
- Preview currently calls the manager before its guard: pending/history mutation, blocked-history quota and simulation are observable. Existing policy evaluation supports a narrow future no-bookkeeping-mutation preview; browser access remains separate.
- [Current evidence and prospective repair](../../platform_integration/linkedin_agent/docs/LINKEDIN_REVIEW_WORKFLOW.md#rsi-connection-policy-qualification--2026-09-22). No live action, runtime update or retained-learning claim.


### 2026-03-07: LinkedIn Registry Migration
**By:** 0102
**WSP References:** WSP 22, WSP 60, WSP 3

**Changes:**
- `src/ai_overseer_integration.py`: Default LinkedIn profile now uses registry lookup
- Import: `from modules.infrastructure.shared_utilities.linkedin_account_registry import get_default_company`

**Impact:**
- LinkedIn company IDs managed via `LINKEDIN_ACCOUNTS_JSON` env var

---

### 2026-03-05: Digital Twin parameter passthrough (L1/L3)
**By:** 0102
**WSP References:** WSP 22, WSP 50, WSP 73

**Changes:**
- `src/linkedin_actions.py` (`run_digital_twin_flow`):
  - L1 call now passes orchestrated `comment_text` and `mentions`
  - L3 call now passes `repost_text` alongside `schedule_date` and `schedule_time`

**Impact:**
- Removes silent drift between CLI intent and LN layered execution.
- Keeps DOM/Selenium execution aligned with UI-TARS verification layers.
- Synced module docs: `README.md`, `INTERFACE.md`, `ROADMAP.md`.

---

### 2026-02-24: LinkedIn SKILLz + Template-Only Fix
**By:** 0102 (with 012 supervision)
**WSP References:** WSP 22, WSP 96 (WRE Skills Protocol)

**Changes:**
- Created `skillz/linkedin_post_hunter/SKILLz.md`:
  - DOM-first post detection (AI/capital/target authors)
  - Keyword matching without LLM
  - Repost filtering
  - Fast ~10ms per post

- Created `skillz/linkedin_engagement_poster/SKILLz.md`:
  - 3 engagement modes: like, reply, like_reply
  - Proactive account switching (BEFORE engaging)
  - Brand-compliant templates ONLY (no YouTube LLM)
  - Execution order: Switch -> Reply -> Like

- Fixed `_generate_reply_for_post()`:
  - **REMOVED** YouTube LLMCommentGenerator usage
  - **NOW** uses templates only (`_template_reply_for_reason`)
  - Prevents off-brand content (e.g., "MAGAts")

- Updated `linkedin_feed_engagement.json` to v2.0.0:
  - Added mode parameter (like/reply/like_reply)
  - Added as_page for account switching
  - Added brand_guardrails (REQUIRED/FORBIDDEN)
  - Added reply_templates by engagement reason

**Root Cause:** YouTube LLM (`LLMCommentGenerator`) was generating
YouTube live chat content for LinkedIn posts - wrong context.

---

### 2026-02-24: Engagement Order Fix + Actor Selection
**By:** 0102 (with 012 supervision)
**WSP References:** WSP 22 (ModLog Protocol), WSP 50 (Pre-Action Verification)

**Changes:**
- `linkedin_actions.py`:
  - Fixed `like_and_reply()` order: **Reply FIRST → Like AFTER** (per 012)
  - Added `as_page` parameter for actor selection (e.g., "foundups")
  - Added `_select_actor_for_reaction(page_name)` - Opens actor dropdown at END
  - Updated Like button selectors for LinkedIn 2024: `button[aria-label*="Reaction button"]`
  - Updated repost detection: checks for "Reaction button state: Like" = already liked
  - Updated FoundUps messaging templates with ROC (Return on Compute) language

**Correct Engagement Flow:**
1. Reply FIRST (comment on post)
2. Like AFTER (reaction after comment posted)
3. Actor selection AT END (012 manually selects page for next engagement)

**DOM Selectors (LinkedIn 2024):**
- Like button: `button[aria-label*="Reaction button"]`
- Actor dropdown: `[aria-label="Open actor selection screen"]`
- Post content: `span[data-testid="expandable-text-box"]`

**FoundUps Messaging (Capital Pushback):**
- "foundups.com is building on different rails"
- "ROI capitalism → ROC Return on Compute post-capitalism"
- "Incentives align with communities instead of exits"

---

### 2026-02-24: Feed Iterator with DOM-First Processing
**By:** 0102
**WSP References:** WSP 22 (ModLog Protocol), WSP 50 (Pre-Action Verification)

**Changes:**
- `linkedin_actions.py`:
  - Added `refresh_feed()` - Navigate to feed URL (F5 equivalent)
  - Added `feed_iterator_reset()` - Reset iterator to index 0
  - Added `feed_iterator_next()` - Get next post with auto-scroll
  - Added `feed_iterator_current()` - Get current post without advancing
  - Added `feed_iterator_skip(count)` - Skip posts without reading
  - Added `_read_feed_post_at_index(index)` - DOM-based post extraction
  - Added `_scroll_feed_down()` - Scroll to load more posts
  - Added `iterate_feed(max_posts, skip_reposts, engagement_filter)` - Convenience wrapper
  - Updated `run_engagement_session()` - Now uses DOM iterator by default
  - Added `_generate_reply_for_post()` - Context-aware reply generation
  - Added `_template_reply_for_reason()` - Template replies by engagement reason

- `test_feed_iterator.py` (new):
  - `--selenium` mode: Pure Selenium DOM iteration
  - `--iterate` mode: Async LinkedInActions iterator
  - `--engagement` mode: Full engagement session test
  - `--dry-run` flag: Read only, no actions

**Feed Iterator Features:**
- Repost detection (skip reposts)
- AI topic detection (engagement-worthy)
- Capital pushback detection (FoundUps alternative perspective)
- Target author detection (Salim Ismail, Peter Diamandis, etc.)
- Auto-scroll for loading more posts
- Position tracking for engagement clicks

**LLME Transition:** COMPLETE → COMPLETE (iterator added)

---

### 2026-02-24: DOM-First + Vision-Diagnose Architecture
**By:** 0102
**WSP References:** WSP 22 (ModLog Protocol), WSP 77 (Agent Coordination), WSP 48 (Pattern Learning)

**Architectural Change:** Restructured from "vision-first with Selenium fallback" to "DOM-first with vision diagnosis".

**Old Architecture (wrong):**
```
Vision (UI-TARS) → Execute Action → If fails → Fallback to Selenium
```

**New Architecture (correct per 012):**
```
Selenium (DOM) → Execute → If success → Done (fast)
                    ↓ failure
              UI-TARS Diagnose → "What broke?" → Fix selector → Retry
```

**Changes:**
- `action_router.py`:
  - Renamed `VISION_ACTIONS` to `DOM_FIRST_ACTIONS` + `VISION_ONLY_ACTIONS`
  - `get_driver_for_action()` now returns SELENIUM for DOM_FIRST_ACTIONS
  - `execute()` now tries DOM first, calls `_diagnose_with_vision()` on failure
  - Added `_diagnose_with_vision()` - asks UI-TARS "why did this fail?"
  - Added `_update_selector_pattern()` - stores fixes for future use
- `ui_tars_bridge.py`:
  - Added `diagnose` action type - locates element without clicking
  - Returns diagnosis info: coordinates, suggested selector, reason
- Added Selenium implementations for `scroll_to_element`, `find_by_description`, `click_by_description`

**Benefits:**
- 99% of actions: Pure Selenium (~10ms) - fast
- 1% failures: UI-TARS diagnoses (~2-5s) - self-healing
- Pattern learning: System improves over time as selectors are updated

**Impact:**
- LinkedIn engagement sessions now DOM-first (faster, more reliable)
- UI-TARS becomes the debugger, not the executor
- Self-healing automation when DOM selectors break

**LLME Transition:** COMPLETE → COMPLETE (architecture alignment per 012)

---

### 2026-01-26: Digital Twin Flow Wired to LinkedInActions
**By:** 0102
**WSP References:** WSP 22 (ModLog Protocol), WSP 73 (Digital Twin Architecture), WSP 77 (Agent Coordination)

**Changes:**
- Added `run_digital_twin_flow()` method to `LinkedInActions` class in `src/linkedin_actions.py`.
- Method orchestrates L0-L3 layered tests (context gate, comment, identity likes, scheduled repost).
- Imports layer tests from `platform_integration/linkedin_agent/tests/`.

**Impact:**
- Enables AI Overseer and DAEs to invoke full Digital Twin flow via `LinkedInActions`.
- Completes handoff step: "Wire linkedin_comment_digital_twin skill into ActionRouter".

---

### 2026-01-20: LinkedIn Digital Twin Comment + Schedule Skill
**By:** 0102
**WSP References:** WSP 22 (ModLog Protocol), WSP 73 (Digital Twin Architecture), WSP 77 (Agent Coordination)

**Changes:**
- Added `skillz/linkedin_comment_digital_twin.json` for UI-TARS validated comment, identity-like loop, and scheduled repost.

**Impact:**
- Establishes repeatable LinkedIn Digital Twin flow with explicit validation gates and scheduling constraints.

---

### 2025-12-30: Edge Debug-Port Attach + Telemetry Preflight
**By:** 0102
**WSP References:** WSP 22 (ModLog Protocol)

**Problem:** Port-based ActionRouter attach always used `FoundUpsDriver` (Chrome), which fails when connecting to Edge (FoundUps) on port 9223.

**Changes:**
- `action_router.py` now detects browser type via `FOUNDUPS_BROWSER_TYPE`/`ACTION_ROUTER_BROWSER_TYPE` (or Edge port match) and attaches with `webdriver.Edge` when appropriate.
- Adds warnings for mismatched browser type vs port to aid troubleshooting.
- Adds DevTools UA preflight: fails fast if a Chrome/Edge port mismatch is detected.
- Adds Edge telemetry shim via Selenium event listener to emit FoundUps-style events into `logs/foundups_browser_events.log`.

**Impact:**
- Edge (9223) sessions attach safely without breaking Chrome flows.
- Chrome port-based and BrowserManager flows unchanged.
- Edge actions now participate in the standard browser telemetry stream.

---

### 2025-12-08: Multiple Browser Window Fix - BrowserManager Integration
**By:** 0102
**WSP References:** WSP 91 (Observability), WSP 3 (Architecture), WSP 50 (Pre-Action Verification)

**Problem:** ActionRouter was creating duplicate browser instances, bypassing BrowserManager singleton

**Root Cause Analysis:**
- ActionRouter._ensure_selenium() creating FoundUpsDriver directly
- Tests creating browsers via webdriver.Chrome() directly
- Result: 26+ Chrome windows for same profile (confirmed by health check tool)

**Changes:**
- `action_router.py:156-190` - Modified _ensure_selenium() to use BrowserManager for profile-based connections
- `tools/browser_health_check.py` (NEW) - Diagnostic tool for detecting duplicate browsers
- `docs/BROWSER_CONNECTION_PATTERNS.md` (NEW) - Documentation on port-based vs profile-based patterns

**Implementation:**
```python
# Before (created duplicate browsers)
self._selenium_driver = FoundUpsDriver(profile_dir=..., port=...)

# After (uses singleton)
if port_val:
    self._selenium_driver = FoundUpsDriver(port=port_val)  # Port-based (test/dev)
else:
    browser_manager = get_browser_manager()
    self._selenium_driver = browser_manager.get_browser('chrome', self.profile)  # Profile-based (production)
```

**Behavior:**
- Port-based connection (test/dev): Direct FoundUpsDriver creation (port 9222)
- Profile-based connection (production): BrowserManager singleton (no duplicates)

**Impact:**
- ✅ Eliminates multiple browser window spawning in production
- ✅ Preserves test workflow (port 9222 connection)
- ✅ BrowserManager telemetry observers now active
- ✅ Browser reuse across ActionRouter instances

**Health Check Usage:**
```bash
python modules/infrastructure/browser_actions/tools/browser_health_check.py
python modules/infrastructure/browser_actions/tools/browser_health_check.py --profile youtube_move2japan
```

**Migration Pattern:**
- Tests with existing Chrome: Continue using port-based connection
- Production code: Use BrowserManager.get_browser() (singleton)
- See BROWSER_CONNECTION_PATTERNS.md for full migration guide

**LLME:** BBB → CCC (architecture hardened with singleton enforcement)

---

### Module Creation - Browser Actions Router
**By:** 0102
**WSP References:** WSP 3 (Architecture), WSP 49 (Module Structure)

**Changes:**
- Created `browser_actions/` module in infrastructure domain
- Added README.md with router architecture
- Added ROADMAP.md with 6-sprint development plan
- Added INTERFACE.md with platform action APIs
- Added ModLog.md (this file)

**Rationale:**
- Platform actions need unified interface
- Intelligent routing to Selenium or UI-TARS
- Enables gradual migration to vision-based automation
- Foundation for multi-platform 0102 autonomy

**Impact:**
- YouTube comment engagement becomes possible
- Platform actions are driver-agnostic
- AI Overseer can trigger any platform action

**LLME Transition:** null → BBB (module created with structure)

---

## Architecture Decision Records

### ADR-001: Router Pattern
**Decision:** Use router pattern to delegate to appropriate driver

**Rationale:**
1. Platform actions shouldn't know implementation details
2. Enables A/B testing between drivers
3. Fallback capability for reliability
4. Telemetry at routing decision point

---

### ADR-002: Profile-Based Sessions
**Decision:** Each platform/account has its own browser profile

**Rationale:**
1. Session persistence (stay logged in)
2. Multi-account support (FoundUps, Move2Japan, etc.)
3. Isolation between accounts
4. Matches existing browser_manager pattern

---

## Sprint Progress

| Sprint | Status | Tokens Used |
|--------|--------|-------------|
| A1: Action Router | 🟢 Complete | ~400 |
| A2: YouTube Actions | 🟢 Complete | ~350 |
| A3: LinkedIn Actions | 🟢 Complete | ~450 |
| A4: X Actions | 🟢 Complete | ~400 |
| A5: FoundUp Actions | 🟢 Complete | ~380 |
| A6: Integration & Optimization | 🟢 Complete | ~300 |

---

## Sprint A1 Completion

### A1: Action Router Foundation
**Status:** ✅ Complete
**By:** 0102 (parallel execution with foundups_vision V1/V2)
**WSP References:** WSP 77 (AI Overseer telemetry), WSP 48 (routing patterns), WSP 91 (observability)

**Files Created:**
- `src/action_router.py` (370 lines)

**Features Implemented:**
- ActionRouter class with intelligent driver routing
- ActionComplexity enum (SIMPLE, VISION, HYBRID)
- DriverType enum (SELENIUM, UI_TARS, FALLBACK)
- RoutingDecision dataclass with metadata
- Driver availability checking (UI-TARS at E:/HoloIndex/models/ui-tars-1.5)
- Action complexity classification (vision vs DOM)
- Fallback mechanism (Selenium when UI-TARS unavailable)
- Routing statistics tracking (WSP 48 learning)
- Telemetry emission for AI Overseer (WSP 77)
- Factory function create_action_router()

**Routing Logic:**
```python
# Simple actions → Selenium (fast)
router.route_action("navigate_to_url", {"url": "..."})  # → SELENIUM

# Vision actions → UI-TARS (required)
router.route_action("like_comment", {"platform": "youtube"})  # → UI_TARS

# Hybrid actions → UI-TARS with fallback
router.route_action("click_visual", {"element": "submit"})  # → UI_TARS (fallback: SELENIUM)
```

**Token Efficiency:**
- Routing decision: <5ms, 0 AI tokens
- Avoids loading both drivers (lazy initialization)
- Telemetry to AI Overseer enables pattern learning (WSP 48)

**Integration Ready:**
- YouTube Actions (Sprint A2) can use router immediately
- LinkedIn Actions (Sprint A3) can use router immediately
- X Actions (Sprint A4) can use router immediately

**LLME Transition:** null → 001 (router foundation complete)

---

## Sprint A2 Completion

### A2: YouTube Actions
**Status:** ✅ Complete
**By:** 0102 (parallel with other 0102 session)
**WSP References:** WSP 77 (AI coordination), WSP 3 (platform_integration reuse)

**Files Created:**
- `src/youtube_actions.py` (~320 lines)

**Features Implemented:**
- YouTubeActions class for YouTube engagement
- navigate_to_video(video_id) via Selenium
- like_comment(video_id, comment_id) via UI-TARS Vision
- reply_to_comment(video_id, comment_id, text) via API + vision fallback
- like_and_reply(video_id, comment_id, text) combo method
- subscribe_channel(channel_id) via Vision
- YouTubeActionResult dataclass for outcomes
- Integration with youtube_auth API module

**Key Design Decisions:**
1. **Liking uses Vision** - YouTube API doesn't support comment likes
2. **Reply uses API first** - More reliable, falls back to vision
3. **Navigation uses Selenium** - Fast, reliable for known URLs
4. **Combo methods** - Single session for multiple actions

**LLME Transition:** 001 → 011 (YouTube engagement operational)

---

## Sprint A3 & A4 Completion

### A3: LinkedIn Actions (Vision-Based)
**Status:** ✅ Complete
**By:** 0102
**WSP References:** WSP 77 (AI coordination), WSP 80 (DAE)

**Files Created:**
- `src/linkedin_actions.py` (~450 lines)

**Features Implemented:**
- LinkedInActions class for vision-based engagement
- `read_feed(max_posts)` - Read and understand posts via UI-TARS
- `like_post(post_id)` - Like via vision
- `reply_to_post(post_id, text)` - Vision-based reply
- `like_and_reply(post_id, text)` - Combo method
- `run_engagement_session(duration, max)` - Autonomous engagement
- LLM integration for intelligent replies
- Relevance detection for 012's interests

**Key Design: Full UI-TARS**
- Selenium only for navigation (known URLs)
- UI-TARS for ALL engagement (reading, understanding, replying)
- Enables 0102 to "see" and intelligently engage

### A4: X Actions (Vision-Based)
**Status:** ✅ Complete
**By:** 0102
**WSP References:** WSP 77 (AI coordination), WSP 80 (DAE)

**Files Created:**
- `src/x_actions.py` (~480 lines)

**Features Implemented:**
- XActions class for vision-based engagement
- `read_timeline(max_tweets)` - Read and understand tweets via UI-TARS
- `like_tweet(tweet_id)` - Like via vision
- `retweet(tweet_id)` - Retweet via vision
- `reply_to_tweet(tweet_id, text)` - Vision-based reply
- `post_tweet(content)` - Post new tweet via vision
- `run_engagement_session(duration, max)` - Autonomous engagement
- LLM integration for witty, platform-appropriate replies

**LLME Transition:** 011 → 111 (multi-platform engagement operational)

---

### A5: FoundUp Actions (Vision-Based)
**Status:** ✅ Complete
**By:** 0102
**WSP References:** WSP 77 (AI coordination), WSP 80 (DAE), WSP 27 (DAE phases)

**Files Created:**
- `src/foundups_actions.py` (~380 lines)

**Features Implemented:**
- FoundUpActions class for livechat engagement
- `read_livechat(foundup_id, max)` - Read and understand messages via UI-TARS
- `post_to_livechat(foundup_id, message)` - Post via vision
- `respond_to_message(foundup_id, message)` - Reply to specific message
- `send_greeting(foundup_id)` - Welcome message
- `run_livechat_session(foundup_id, duration)` - Autonomous engagement loop
- Question detection and priority response
- LLM integration for contextual replies
- 012 typing speed (character by character per WSP)

**LLME Transition:** 111 → 1111 (all platforms operational)

---

## Sprint A6 Completion

### A6: Integration & Optimization
**Status:** ✅ Complete
**By:** 0102 (final sprint of browser_actions)
**WSP References:** WSP 77 (AI Overseer coordination), WSP 91 (Observability), WSP 48 (Pattern Learning)

**Files Created:**
- `src/ai_overseer_integration.py` (~240 lines) - AI Overseer mission coordinator
- `src/telemetry_dashboard.py` (~210 lines) - Unified telemetry and metrics
- `skillz/youtube_comment_engagement.json` - YouTube engagement workflow
- `skillz/linkedin_feed_engagement.json` - LinkedIn engagement workflow
- `skillz/foundup_livechat_moderation.json` - FoundUp livechat workflow

**Files Modified:**
- `src/action_router.py` - Added `get_pattern_recommendation()` for pattern-based optimization
- `src/__init__.py` - Exported AI Overseer and telemetry modules

**Features Implemented:**

**1. AI Overseer Integration (Wire all actions)**
- `BrowserActionsCoordinator` class for mission-based execution
- `ActionMission` dataclass for mission definitions
- Platform routing: youtube, linkedin, x, foundup
- Mission history tracking and statistics
- Factory function: `get_coordinator()`

**2. WRE Skill Definitions**
- YouTube Comment Engagement skill (4-step workflow)
- LinkedIn Feed Engagement skill (4-step workflow)
- FoundUp Livechat Moderation skill (5-step workflow)
- Each skill includes AI coordination phases (Gemma → Qwen → 0102 → Learning)
- Telemetry events and metrics defined

**3. Pattern-Based Routing Optimization**
- `get_pattern_recommendation()` method in ActionRouter
- Uses historical success rates to optimize routing
- Adapts routing if success rate < 50%
- Maintains current routing if success rate > 80%

**4. Unified Telemetry Dashboard**
- `TelemetryDashboard` class for metrics aggregation
- Per-platform statistics (actions, success rate, avg duration)
- Router usage stats (Selenium vs Vision calls)
- Human-readable summary output
- JSON export capability
- Factory function: `get_dashboard()`

**Integration Example:**
```python
from modules.infrastructure.browser_actions import get_coordinator, get_dashboard

# AI Overseer sends mission
coordinator = get_coordinator()
mission = ActionMission(
    mission_id="mission_001",
    platform="youtube",
    action_type="engage",
    params={"video_id": "abc123", "max_comments": 5}
)

result = await coordinator.execute_mission(mission)

# View telemetry
dashboard = get_dashboard()
print(dashboard.get_summary())
```

**Token Efficiency:** 300 tokens (as budgeted) ✅

**LLME Transition:** 1111 → **COMPLETE** (all browser_actions sprints operational)

**Module Status:** browser_actions fully operational - all 6 sprints complete

---

**Document Maintained By:** 0102 autonomous operation

