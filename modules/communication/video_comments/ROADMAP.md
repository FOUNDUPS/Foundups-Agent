# Video Comments - ROADMAP

**Module:** communication/video_comments
**WSP Reference:** WSP 22 (Module Roadmap Protocol)

---

## Vision Statement

Transform YouTube comment engagement from manual interaction to fully autonomous 0102 operation with intelligent, context-aware responses that enhance community engagement.

---

## LLME Progression

| Level | Status | Description |
|-------|--------|-------------|
| A1 | ✅ | Basic comment retrieval (API) |
| A2 | ✅ | Comment monitoring DAE |
| A3 | ✅ | Browser automation (Like/Heart/Reply) |
| A4 | ✅ | Grounded local-Qwen reply system + classified response skills |
| A5 | ✅ | YouTube DAE integration (Phase 3A/3B) |
| **A6** | 🚧 | Unlimited engagement + Vision stream detection |
| A7 | 🔮 | Cross-platform engagement intelligence |

---

## Phase 1: PoC Validation ✅ COMPLETE

**Objective:** Prove browser automation can perform Like/Heart/Reply

- [x] UI-TARS + Selenium hybrid approach
- [x] DOM selectors for Like/Heart buttons
- [x] Textarea handling for Reply input
- [x] Page refresh and batch processing
- [x] Vision verification for state changes

**Artifacts:**
- `skills/tars_like_heart_reply/comment_engagement_dae.py`
- `skills/tars_like_heart_reply/run_skill.py`

---

## Phase 2: Intelligent Response System ✅ COMPLETE

**Objective:** Replace static replies with context-aware responses

### 2.1 Commenter Classification ✅
- [x] Extract author name from DOM
- [x] Detect moderator badge (from auto_moderator.db)
- [x] Detect subscriber badge
- [x] MAGA troll detection (expanded triggers)
- [x] **HOSTILE_PATTERNS** integration (Phase 1 from FLOW_ANALYSIS_20251223)
  - "don't come back", "go away", "gtfo", "stfu", "nobody asked", etc.
  - Score 0.75 (provisional troll) for hostile comments even without MAGA content

### 2.2 Response Generation ✅
- [x] MOD_RESPONSES for moderators
- [x] TROLL_RESPONSES for MAGA trolls (Whack-a-MAGA style)
- [x] SUBSCRIBER_RESPONSES for subscribers
- [x] Digital Twin drafting + decisioning (primary)
- [x] LM Studio/general-Qwen contextual route (primary)
- [x] Embedded general-Qwen fallback
- [x] Grok removed from the default route; explicit legacy opt-in only
- [ ] Governed RedDog/OpenRouter execution after typed autonomous authorization is defined
- [x] Pattern responses (song → #FFCPLN, FFCPLN → ICE promo)
- [x] Emoji-to-emoji replies (✊✋🖐️ sequences)

### 2.3 Integration ✅
- [x] `intelligent_reply_generator.py` created
- [x] DAE updated with `use_intelligent_reply` flag
- [x] Tested with live YouTube Studio
- [x] No @Unknown in replies

### 2.4 Per-Comment Context Integrity ✅
- [x] Extract video title/ID/URL from each YouTube Studio inbox row
- [x] Forward target channel ID for channel-personality routing
- [x] Preserve original comment when semantic guidance is added
- [x] Query verified VoiceMemory with video title plus comment
- [x] Record the actual provider source instead of labeling templates as LLM output
- [x] Skip generic template posting by default when grounded generation fails

**Artifacts:**
- `src/intelligent_reply_generator.py`

---

## Phase 3: YouTube DAE Integration ✅ COMPLETE

**Objective:** Hook comment engagement into main YouTube DAE flow

### 3A: CommunityMonitor Integration ✅
- [x] CommunityMonitor class for periodic checking
- [x] Heartbeat integration (every 20 pulses = 10 min)
- [x] Fire-and-forget subprocess execution
- [x] Chat announcement on completion

### 3B: Unlimited Comment Processing ✅
- [x] `max_comments=0` for UNLIMITED mode
- [x] Loop until 0 comments remain
- [x] `all_processed` flag in stats
- [x] "Community tab clear!" announcement

### 3C: Dependency Launcher ✅
- [x] Auto-launch Chrome on port 9222
- [x] Auto-launch LM Studio (optional)
- [x] Phase -2 in DAE startup flow

### 3D: Pluggable Execution Modes ✅
- [x] Strategy pattern interface (EngagementRunner)
- [x] Subprocess mode (DEFAULT): SIGKILL guarantee, 2-3s startup
- [x] Thread mode: <500ms startup, thread isolation
- [x] InProc mode: Debug only (blocks event loop)
- [x] First-principles analysis: Selenium blocking requires process/thread isolation
- [x] Configuration: COMMUNITY_EXEC_MODE env variable

**Architecture Rationale:**
Selenium/WebDriver is synchronous and blocks event loop. asyncio.wait_for() can timeout the await, but CANNOT interrupt blocked C/IO calls inside Selenium. Only subprocess termination guarantees recovery of Chrome control.

**Execution Modes:**
- subprocess (default): Strongest kill switch + crash isolation
- thread: Fast startup, thread-local event loop, acceptable risk
- inproc: Development debugging only

**Engagement Flow:**
```
main.py → Option 1 → Option 5
    ↓
Phase -2: ensure_dependencies() → Chrome + LM Studio
    ↓
Phase -2.1: Startup comment engagement (configurable mode)
    ↓
Heartbeat Pulse 20 → CommunityMonitor.check_and_engage(max_comments=0)
    ↓
EngagementRunner.run_engagement() [subprocess/thread/inproc]
    ↓
Process ALL comments → LIKE + HEART + REPLY → REFRESH
    ↓
stats['all_processed'] = True
    ↓
Chat: "✅ ALL 15 comments processed! Community tab clear! ✊✋🖐️"
```

---

## Phase 4: Memory & Learning 🔮 FUTURE

**Objective:** Remember users across sessions and learn from engagement outcomes

### 4.1 Commenter Database
- [ ] Store commenter profiles
- [ ] Track engagement history
- [ ] Remember mod status across videos

### 4.2 Pattern Learning
- [ ] Record successful engagement patterns
- [ ] Learn which replies get positive reactions
- [ ] Adaptive troll detection

### 4.3 Cross-Platform Memory
- [ ] Link YouTube commenters to X accounts
- [ ] Share profiles with LinkedIn agent
- [ ] Unified community database

---

## Dependencies

| Module | Purpose | Status |
|--------|---------|--------|
| ai_intelligence/digital_twin | Draft/decide engine | ✅ Available |
| ai_intelligence/banter_engine | Fallback responses | ✅ Available |
| gamification/whack_a_magat | Troll mockery style | ✅ Referenced |
| communication/livechat | YouTube DAE | ✅ Available |
| infrastructure/browser_actions | Selenium + Vision | ✅ Available |
| infrastructure/foundups_vision | UI-TARS bridge | ✅ Available |

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Troll misclassification | Conservative threshold (0.7), human override option |
| Rate limiting by YouTube | Respect API quotas, throttle browser actions |
| DOM selector changes | Abstract selectors, version detection |
| Vision model accuracy | DOM-first approach, vision as verification |

---

**Document Maintained By:** 0102 autonomous operation
**WSP Compliance:** WSP 22, WSP 27, WSP 80

