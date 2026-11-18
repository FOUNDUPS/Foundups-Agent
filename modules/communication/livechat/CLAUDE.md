## Current conversation memory — 2026-11-07

Ordinary replies use MessageProcessor._conversation_response and the shared
assess/write/review gateway. Observe quietly; native-ID/session context replaces
name-based history, and generic platform badges do not prioritize conversation.
WSP15 is for approved repair work. The canonical host workflow is
`.claude/skills/youtube-conversation-stewardship/SKILL.md`; it is not a registered
native WRE executor. Preserve command permissions, initial capture-only history,
STOP and uncertain writes. See current README/INTERFACE before older patterns below.

# CLAUDE.md - LiveChat Module Memory

## [STOP] STOP - ANTI-VIBECODING CHECKPOINT

### BEFORE ANY CODE CHANGES IN THIS MODULE:

#### 1️⃣ MANDATORY RESEARCH (4 minutes minimum)
- [ ] Read this entire CLAUDE.md file
- [ ] Check `docs/` folder for architecture docs
- [ ] Read `README.md` for module overview
- [ ] Read `INTERFACE.md` for public API
- [ ] Check `ModLog.md` for recent changes
- [ ] Review `tests/README.md` for test coverage

#### 2️⃣ EXISTING CODE CHECK (2 minutes)
```bash
# List all source files
ls -la src/

# Search for the functionality you want to add
grep -r "your_function" src/

# Check imports to understand dependencies
grep -r "from modules.communication.livechat" ../../

# Check if orchestrator handles this
grep -r "orchestrator\|coordinator" src/
```

#### 3️⃣ ARCHITECTURE QUESTIONS (Answer ALL before coding)
- What is the entry point for this functionality?
- Which file currently handles this logic?
- Is there an orchestrator or coordinator managing this?
- Are there existing tests for this behavior?
- What patterns are already established?

#### 4️⃣ VIBECODING RED FLAGS [ALERT]
**YOU ARE VIBECODING IF YOU:**
- Started typing code without completing steps 1-3
- Created a new file without checking if functionality exists
- Added imports without verifying they work
- Modified core logic without understanding flow
- Fixed a "bug" without reading logs/documentation

**REMEMBER**: This module has 29 source files, 20+ test files, and extensive documentation. The functionality you need probably already exists!

## Module Structure (WSP 83 Compliant)
This document helps 0102 remember all module components and paths.

## Core Components

### Main Engine (`src/`)
- `livechat_core.py` - Core chat monitoring with agentic stream switching
- `auto_moderator_dae.py` - WSP-compliant DAE orchestration with quick_check_mode
- `message_processor.py` - Processes messages and consciousness triggers
- `command_handler.py` - Handles /slash commands and whack gamification
- `event_handler.py` - Processes YouTube chat events (timeouts, messages)
- `chat_sender.py` - Sends messages to YouTube chat (handles markdown removal)
- `throttle_manager.py` - Rate limiting and quota management
- `agentic_chat_engine.py` - AI response generation
- `greeting_generator.py` - Stream greeting generation
- `mcp_youtube_integration.py` - Model Context Protocol integration

### Key Features

#### Agentic Stream Switching
- **Inactivity Detection**: 3-minute timeout triggers stream search
- **Quick Check Mode**: 5-15 second intervals after stream ends
- **Cache Clearing**: Automatic cache clear when streams end
- **Seamless Reconnection**: No restart required

#### Consciousness Triggers ([U+270A][U+270B][U+1F590])
- Pattern: `[U+270A][U+270B][U+1F590]` followed by question
- Modes: `mod_only` or `everyone`
- Toggle: `/toggle` command (MOD/OWNER only)

#### Command Processing
- All commands in `command_handler.py`
- Quiz responses stripped of markdown for YouTube compatibility
- Extensive logging with [AI] emoji markers

### Integration Points
- **Platform**: `modules/platform_integration/stream_resolver/`
- **Gamification**: `modules/gamification/whack_a_magat/`
- **Auth**: `modules/platform_integration/youtube_auth/`

### Recent Fixes
1. Stream switching now truly agentic (no restart needed)
2. Quiz messages work (markdown removed)
3. Cache clearing ensures fresh stream detection
4. Quick check mode for rapid reconnection

### WSP Compliance
- WSP 3: Module organization
- WSP 17: Pattern registry compliance
- WSP 22: ModLog for changes
- WSP 27: DAE architecture
- WSP 83: Documentation attached to tree
- WSP 84: Check existing code first

## Remember
- YouTube API rejects markdown formatting
- Cache must be cleared for fresh stream detection
- Quick check mode activates after stream ends
- All /quiz logging uses [AI] emoji markers