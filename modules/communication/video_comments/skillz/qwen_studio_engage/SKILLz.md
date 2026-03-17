---
name: qwen_studio_engage
description: Autonomous YouTube Studio comment engagement (like/reply) using Vision AI
version: 1.0.0
author: 0102_communication_team
agents: [qwen, gemma]
dependencies: [browser_actions, foundups_vision, pattern_memory]
domain: autonomous_engagement
intent_type: ENGAGEMENT
promotion_state: prototype
category: workflow
evals: []
---
# Qwen YouTube Studio Engagement Skill

**Skill Type**: Micro Chain-of-Thought (WSP 96)
**Intent**: ENGAGEMENT (autonomous comment analysis & response)
**Agents**: Qwen 1.5B (strategic), Gemma 270M (validation)
**Promotion State**: prototype
**Version**: 1.0.0
**Created**: 2025-12-03
**Last Updated**: 2025-12-03

---

## Skill Purpose

Autonomously monitor YouTube Studio comments inbox and engage (like/reply) with high-value comments using Vision AI. **Uses existing browser session** (no new login required).

**Trigger Source**: Event queue (`youtube_comment_notification`) or periodic check (15-30 min)

**Success Criteria**:
- Pattern fidelity >90% (Gemma validation)
- Engagement decisions align with brand voice
- Vision successfully interacts with Studio UI
- No false positives (spam/troll comments ignored)

---

## Architecture: Existing Browser Reuse

```
User's Chrome Browser (Already Logged In)
    ↓
BrowserManager connects to existing session
    ↓
Navigate to: studio.youtube.com/channel/{CHANNEL_ID}/comments/inbox
    ↓
Vision AI identifies comment elements
    ↓
Qwen analyzes → Gemma validates → Vision engages
```

**Key Insight**: User is already logged into YouTube Studio, so we **connect to existing browser** (no new window, no login).

---

## Input Context Required

```python
{
    "channel_id": "UC-LSSlOZwpGIRIYihaz8zCw",  # YouTube channel ID
    "max_comments_to_check": 10,  # Limit per execution
    "engagement_policy": {
        "like_threshold": 0.7,      # Qwen confidence for liking
        "reply_threshold": 0.8,     # Qwen confidence for replying
        "ignore_spam": True,
        "ignore_toxicity": True,
        "brand_voice": "helpful, friendly, professional"
    },
    "existing_browser": True  # Use existing logged-in session
}
```

---

## Micro Chain-of-Thought Steps

### Step 1: Navigate to Studio Inbox (Selenium)

**Action**: Connect to existing browser and navigate to comments inbox

**Browser Connection** (No New Window):
```python
# BrowserManager already handles this - user is logged in
from modules.infrastructure.foundups_selenium.src.browser_manager import get_browser_manager

browser_manager = get_browser_manager()
browser = browser_manager.get_browser(
    profile='youtube_move2japan',  # Already logged in
    browser_type='chrome'
)

# Navigate using existing session
studio_url = f"https://studio.youtube.com/channel/{channel_id}/comments/inbox"
browser.get(studio_url)
```

**Why Studio (not regular YouTube)**:
- Studio = Unified inbox for ALL videos
- Creator-specific features (heart button)
- More efficient than checking each video
- API confirmed: "Must use YouTube Studio interface" (MOVE2JAPAN_COMMENT_INTERACTION_REPORT.md)

**Gemma Validation**:
- [ ] Browser connected to existing session (no new window)
- [ ] URL navigated successfully
- [ ] Studio UI loaded (wait 3-5 seconds for React)

**Expected Duration**: 2-3 seconds

---

### Step 2: Analyze Comment Sentiment (Qwen Strategic)

**Input Context** (from Vision):
```python
{
    "comment_text": str,  # Comment content
    "author_name": str,   # Commenter name
    "video_title": str,   # Which video (context)
    "timestamp": str,     # When posted
    "likes_count": int    # Community engagement
}
```

**Qwen Instructions**:
```
You are analyzing a YouTube comment to decide if it warrants engagement.

Context:
- Channel: Move2Japan (Japan relocation content)
- Brand Voice: Helpful, friendly, professional
- Audience: People interested in moving to Japan

Analyze the comment for:

1. **Sentiment** (positive/neutral/negative):
   - Positive: Appreciation, questions, constructive feedback
   - Neutral: Observations, general statements
   - Negative: Complaints, spam, trolling

2. **Engagement Value** (1-5):
   - 5: High-value question or thoughtful feedback
   - 4: Positive comment showing genuine interest
   - 3: Neutral but on-topic comment
   - 2: Off-topic or low-quality
   - 1: Spam, troll, or toxic

3. **Recommended Action**:
   - "like_only": Like the comment (quick acknowledgment)
   - "like_and_reply": Like + personalized reply (high value)
   - "creator_heart": Give creator heart (special engagement)
   - "ignore": Skip (spam/troll/low-quality)

4. **Reply Template** (if replying):
   - Keep under 200 characters
   - Address their specific point/question
   - Encourage further engagement
   - Use 1-2 relevant emojis (🎌🗾🏯🍜🌸)

Output format:
{
    "sentiment": "positive|neutral|negative",
    "engagement_value": 1-5,
    "recommended_action": "like_only|like_and_reply|creator_heart|ignore",
    "reply_text": "Optional reply if like_and_reply",
    "confidence": 0.85,
    "reasoning": "Brief explanation"
}
```

**Gemma Validation Pattern**:
- [ ] Did Qwen identify sentiment?
- [ ] Is engagement_value in range 1-5?
- [ ] Is recommended_action one of valid options?
- [ ] If like_and_reply, is reply_text present?
- [ ] Is confidence score between 0.0-1.0?
- [ ] Does reply match brand voice (if present)?

**Expected Reasoning Time**: 300-600ms (Qwen 1.5B)

---

### Step 3: Execute Engagement (Vision AI)

**Scenario A: Like Only**

**Vision Instructions**:
```python
# Use ActionRouter with Vision driver
from modules.infrastructure.browser_actions.src.action_router import ActionRouter, DriverType

router = ActionRouter(profile='youtube_move2japan')

result = await router.execute(
    'click_element',
    {
        'description': 'thumbs up like button on the first visible comment',
        'target': 'like button',
        'context': 'YouTube Studio comments inbox',
    },
    driver=DriverType.VISION
)
```

**Fallback Strategy**:
If regular like fails → Try creator heart button:
```python
heart_result = await router.execute(
    'click_element',
    {
        'description': 'heart button to give creator heart',
        'target': 'heart icon',
        'context': 'YouTube Studio comments inbox',
    },
    driver=DriverType.VISION
)
```

---

**Scenario B: Like and Reply**

**Step 1**: Click like (as above)

**Step 2**: Click reply button
```python
reply_button_result = await router.execute(
    'click_element',
    {
        'description': 'reply button to open reply text box',
        'target': 'reply button',
    },
    driver=DriverType.VISION
)
```

**Step 3**: Type reply
```python
type_result = await router.execute(
    'type_text',
    {
        'text': reply_text,
        'target': 'reply text input box',
    },
    driver=DriverType.VISION
)
```

**Step 4**: Submit reply
```python
submit_result = await router.execute(
    'click_element',
    {
        'description': 'submit reply button',
        'target': 'submit button',
    },
    driver=DriverType.VISION
)
```

---

**Gemma Validation**:
- [ ] Did Vision find target element?
- [ ] Was action completed successfully?
- [ ] Is duration within expected range (<5 seconds)?
- [ ] No errors reported?

**Expected Duration**: 2-8 seconds (Vision + interaction)

---

### Step 4: Record Pattern (Pattern Memory)

**Store Engagement Outcome**:
```python
from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory

memory = PatternMemory()

outcome = {
    "skill_name": "qwen_studio_engage",
    "agent": "qwen",
    "comment_sentiment": sentiment,
    "engagement_value": engagement_value,
    "action_taken": recommended_action,
    "success": result.success,
    "pattern_fidelity": gemma_validation_score,
    "execution_time_ms": duration_ms
}

memory.store_outcome(outcome)
```

**Learning Over Time**:
- Which sentiment types get best engagement?
- Optimal reply length/style?
- Vision success rate on different UI elements?
- Time of day impact on engagement?

---

## Execution Flow

```
1. Trigger (Event or Periodic)
   ├─> Event: New comment notification from YouTube DAE
   └─> Periodic: Every 15-30 minutes

2. Connect to Existing Browser
   └─> BrowserManager.get_browser('youtube_move2japan')

3. Navigate to Studio Inbox
   └─> studio.youtube.com/channel/{CHANNEL_ID}/comments/inbox

4. Get First Unread Comment (Vision)
   └─> Identify comment element, extract text

5. Qwen Analysis
   ├─> Analyze sentiment, engagement value
   ├─> Decide action (like/reply/ignore)
   └─> Generate reply if needed

6. Gemma Validation
   ├─> Validate Qwen output structure
   ├─> Verify reply quality (if present)
   └─> Check confidence threshold

7. Vision Engagement
   ├─> If ignore: Skip
   ├─> If like_only: Click like button
   ├─> If like_and_reply: Click like + reply workflow
   └─> If creator_heart: Click heart button

8. Record Outcome
   └─> Pattern Memory for learning

9. Repeat for Next Comment
   └─> Up to max_comments_to_check limit
```

---

## Error Handling

### Error: Browser Not Logged In

**Detection**: Studio redirects to login page

**Solution**: User must be logged into YouTube Studio first. Skill assumes existing session.

---

### Error: Vision Can't Find Element

**Detection**: Vision returns "element not found"

**Fallback**:
1. Wait 2 seconds (UI might still be loading)
2. Try alternate description
3. If still fails, skip comment and log for manual review

---

### Error: Comment Already Engaged

**Detection**: Like button is already highlighted

**Action**: Skip to next comment (pattern memory records "already_engaged")

---

## Integration Points

### Event Queue Integration

**Trigger from YouTube DAE**:
```python
# modules/communication/livechat/src/auto_moderator_dae.py
# When new comment detected:

from modules.ai_intelligence.ai_overseer.src.mcp_integration import MCPIntegration

mcp = MCPIntegration()
event = {
    'event_type': 'youtube_comment',
    'source_daemon': 'auto_moderator_dae',
    'payload': {
        'comment_id': comment_id,
        'video_id': video_id,
        'author': author,
        'text': text,
    },
    'priority': 1  # High priority
}

await mcp.event_queue.put(event)
```

**HoloDAE Consumption**:
```python
# holo_index/qwen_advisor/services/monitoring_loop.py
# Event handler triggers Skillz execution

async def _handle_youtube_comment_event(self, event):
    skill_result = await self.skill_executor.execute_skill(
        skill_name='qwen_studio_engage',
        agent='qwen',
        input_context=event['payload']
    )
```

---

### Pattern Learning Integration

**Successful Engagement** → Pattern Memory stores:
- Sentiment patterns that get likes
- Reply templates that get responses
- Time of day impact on engagement
- Vision success rate on UI elements

**Over Time**:
- Qwen learns optimal engagement strategies
- Vision gets faster at finding elements
- Reply quality improves based on community response

---

## Testing & Validation

### Manual Test (First Run)

```python
# tests/test_qwen_studio_engage.py

from modules.infrastructure.wre_core.skills.qwen_studio_engage import execute_skill

result = await execute_skill(
    channel_id="UC-LSSlOZwpGIRIYihaz8zCw",
    max_comments_to_check=3,  # Test with 3 comments
    engagement_policy={
        "like_threshold": 0.7,
        "reply_threshold": 0.9,  # High threshold for testing
        "ignore_spam": True,
    },
    existing_browser=True  # Use logged-in session
)

print(f"Comments analyzed: {result['comments_analyzed']}")
print(f"Engagements made: {result['engagements_made']}")
print(f"Success rate: {result['success_rate']}")
```

### Autonomous Deployment

**Trigger 1**: Event-driven (real-time)
```python
# Auto Moderator DAE monitors → enqueues events → HoloDAE executes Skillz
```

**Trigger 2**: Periodic (backup)
```python
# HoloDAE runs every 30 minutes to check for new comments
```

---

## WSP Compliance

- **WSP 96**: Micro Chain-of-Thought paradigm ✅
- **WSP 77**: Qwen+Gemma coordination ✅
- **WSP 91**: Observability (telemetry logging) ✅
- **WSP 48**: Pattern learning (recursive improvement) ✅
- **WSP 50**: Pre-Action Verification (Gemma validates) ✅

---

## Metrics & Observability

**Track via Pattern Memory**:
```python
{
    "total_comments_analyzed": 142,
    "engagements_made": 67,
    "engagement_rate": 0.47,
    "avg_qwen_confidence": 0.83,
    "avg_gemma_fidelity": 0.91,
    "vision_success_rate": 0.94,
    "avg_execution_time_ms": 4231,
    "top_sentiment": "positive",
    "reply_templates_used": {
        "thanks_for_watching": 24,
        "answer_question": 31,
        "encouragement": 12
    }
}
```

---

## Future Enhancements

**Phase 2**: Multi-channel support
- Expand to all YouTube channels (Move2Japan, FoundUps, GeoZai, UnDaoDu)

**Phase 3**: Advanced sentiment analysis
- Detect questions vs comments
- Identify potential community members
- Flag content ideas

**Phase 4**: Cross-platform learning
- Apply YouTube engagement patterns to X/LinkedIn
- Unified brand voice across platforms

---

**Maintained By:** 0102 Communication Team
**Last Updated:** 2025-12-03
**Status:** Prototype - Ready for testing with existing browser session
