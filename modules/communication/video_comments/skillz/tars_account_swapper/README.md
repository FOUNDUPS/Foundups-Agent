# TARS Account Swapper Skill

## 2026-10-29 receiving-channel verification

`swap_to(target, navigate_to_comments=True)` preserves comments as its default.
Scheduling callers pass `False`; every recovery path honors that surface,
including direct-URL recovery to Studio content. Success requires the exact
native Studio channel ID and HTTPS Studio URL to agree, with an observed
accessible Studio shell. Missing native identity, conflicting URLs, unknown
permission observations and permission errors cannot certify access. Screenshots
and account-picker clicks do not establish this result.

The scheduler also freezes the canonical receiving ID for each rotation entry
and passes it through the shared verifier. A later environment/registry change
cannot retarget the existing scheduler or its tracker. Offline qualification
does not establish a successful live account switch.

**WSP Reference:** WSP 96 (WRE Skills Protocol)
**Status:** ✅ PRODUCTION READY
**Last Validated:** 2025-12-28

## Overview
Handles autonomous account switching between YouTube channels (Move2Japan, UnDaoDu) within the same Google account. This skill uses a hybrid approach of direct navigation and DOM-based menu interaction to ensure high stability.

## Features
- **Smart Detection**: Detects current active channel at startup via script execution and URL regex.
- **Fast Path**: Skips navigation if already on the target channel (WSP 00 - Occam's Razor).
- **Environment Driven**: Channel IDs are read from `.env` (`MOVE2JAPAN_CHANNEL_ID`, `UNDAODU_CHANNEL_ID`).
- **Human Behavior**: Uses Bezier curves and random delays to mimic human interaction.
- **Permission Recovery**: Detects "No Permission" pages and attempts automatic re-authentication or switching.

## Public API
```python
from modules.communication.video_comments.skillz.tars_account_swapper.account_swapper_skill import TarsAccountSwapper

swapper = TarsAccountSwapper(driver)

# Attempt swap to UnDaoDu
success = await swapper.swap_to("UnDaoDu")
```

## Implementation (WSP 27)
1. **Phase -1 (Signal)**: Detect current browser URL and channel ID.
2. **Phase 0 (Knowledge)**: Map target channel name to ID and URL.
3. **Phase 1 (Protocol)**: Compare target vs current (Fast Path).
4. **Phase 2 (Agentic)**: Execute click sequence (Avatar -> Switch Account -> Target Item).

## Environment Variables
- `MOVE2JAPAN_CHANNEL_ID`: UC-LSSlOZwpGIRIYihaz8zCw
- `UNDAODU_CHANNEL_ID`: UCfHM9Fw9HD-NwiS0seD_oIA
- `FOUNDUPS_LIVECHAT_CHROME_PORT`: 9222 (Target port for Chrome)

---
*Autonomous coordination via 0102 pArtifact*
