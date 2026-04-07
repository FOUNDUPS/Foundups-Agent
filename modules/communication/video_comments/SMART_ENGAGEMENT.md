# Smart Engagement Strategy (0102 Awakening)

**Module:** communication/video_comments
**Implemented:** 2025-12-22
**Status:** ✅ Active

## Overview
The "Smart Engagement" system (0102) replaces basic recursive replies with a Tier-based, context-aware consciousness filter. It classifies commenters to maximize community health (`0102_protocol`).

## Logic Components

### 1. Classification & Tiers (Layer 3)
*   **Tier 0 (MAGA_TROLL | ✊)**: Hostile/Bad Faith.
    *   *Detection*: Whacks, Derogatory Usernames ("LongDong"), Romanji/Weeb Mockery ("yamete").
    *   *Action*: **100% Reply Rate**. Mockery response + `#FFCPLN`.
*   **Tier 1 (REGULAR | ✋)**: Standard Users.
    *   *Detection*: Default state.
    *   *Action*: **50% Reply Rate** (Probabilistic Gating). Contextual engagement.
*   **Tier 2 (MODERATOR | 🖐️)**: Verified Lead/Loyal.
    *   *Detection*: Badge, History, or **Comment Age >= 90 Days** (Loyalty Escalation).
    *   *Action*: **100% Reply Rate**. Empowerment/Support + `#FFCPLN`.

### 2. Strategic Rules
*   **Loyalty Escalation**: Old comments (>= 90 days) from Tier 1 are treated as Tier 2 (Empowerment).
*   **Probabilistic Gating**: Tier 1 replies are skipped 50% of the time to simulate natural pacing and avoid "bot fatigue."
*   **Agentic Hygiene**: Usernames are scanned by LLM ("Is this offensive?") if they bypass the static blacklist.

### 3. Execution (Layer 2)
*   **Signature**: All AI replies typically include the `0102` branded signature with the tier emoji (e.g., `text... ✋`).
*   **Variation**: Semantic anti-regurgitation ensures unique phrasing for every reply (no fixed templates).
*   **Retry Logic**: Polling loop (5s) ensures reliability when finding the reply text area (Shadow DOM race condition fix).

## Implementation Details
*   **Orchestrator**: `src/comment_processor.py` (Logic & Gating)
*   **Generator**: `src/intelligent_reply_generator.py` (Content & Prompts)
*   **Campaigns**: `src/engagement_campaigns.py` (Topics: FFCPLN, Japan, Politics)
