# Social Media Orchestrator

**Domain**: platform_integration  
**Classification**: Social Media Orchestration Service  
**WSP Compliance**: WSP 3, WSP 11, WSP 22, WSP 49

## Purpose

Unified orchestration layer for social media platforms (X/Twitter and LinkedIn) that eliminates redundancy and provides a cohesive interface for cross-platform content management, OAuth coordination, and scheduling.

**Digital Twin POC**: This is the execution layer for the 012 Digital Twin comment pipeline (LinkedIn-first), including comment scheduling and cross-platform routing.

## Rotation Flow (YouTube → Scheduling → LinkedIn)

This module sits in the post-YouTube rotation:
1. **YouTube Live Chat**: reply loop completes.
2. **YouTube Studio Comments**: inbox engagement complete.
3. **YouTube Scheduling**: verify all scheduled posts complete.
4. **LinkedIn Digital Twin**: run L0–L3 flow (comment → identity likes → scheduled repost).

This keeps the DAE rotation minimal and deterministic for POC validation.

## Key Features

- **Unified OAuth Management**: Single coordinator for all platform authentication
- **Cross-Platform Content Distribution**: Consistent content formatting across platforms
- **Multi-Stream Handling**: Orchestrates posting for multiple detected streams with priority sequencing
- **Intelligent Scheduling**: Advanced scheduling engine with platform-specific optimizations
- **Natural Language Understanding**: 0102 understands commands like "post in 2 hours" (NEW)
- **Human Scheduling Interface**: 012 can schedule posts for future execution (NEW)
- **Anti-Detection Posting**: Browser automation with human-like behavior
- **Browser Selection**: Automatic browser selection (Chrome for Move2Japan/UnDaoDu, Edge for FoundUps)
- **Channel-to-Platform Mapping**: Maps YouTube channels to correct LinkedIn pages and X accounts
- **Platform Adapters**: Clean abstraction layer for platform-specific implementations
- **WSP Compliance**: Full adherence to WSP standards for modular architecture
- **QWEN Intelligence Integration**: Platform health monitoring and intelligent posting decisions (NEW)
- **Heat Level Management**: Automatic rate limit tracking and cooling periods
- **Pattern Learning**: Learns from successful posts and platform responses
- **Digital Twin Routing**: Accepts Digital Twin drafts/decisions and routes to LinkedIn execution and scheduling

## Architecture

### Refactored Modular Architecture (V021)
The module has been refactored from a monolithic 996-line file into focused, single-responsibility components:

**Core Components** (in `src/core/`):
- `DuplicatePreventionManager`: Duplicate detection with QWEN platform health monitoring and intelligent decisions
- `LiveStatusVerifier`: Stream status verification with 5-minute caching to reduce API calls
- `ChannelConfigurationManager`: Channel configuration and platform account mapping
- `PlatformPostingService`: Platform-specific posting (LinkedIn + X/Twitter) with browser configuration
- `RefactoredPostingOrchestrator`: Clean coordinator with QWEN pre-posting intelligence checks

**Migration Support**:
- `orchestrator_migration.py`: Backward compatibility bridge (drop-in replacement)
- Migration bridge ensures zero breaking changes to existing code

**Legacy Components** (being phased out):
- `SimplePostingOrchestrator`: Original monolithic implementation (996 lines)
- Will be removed once migration is complete

### Integration Points
- X/Twitter module: `modules/platform_integration/x_twitter/`
- LinkedIn modules: Replaces fragmented linkedin_agent, linkedin_scheduler, linkedin_proxy
- AI Intelligence: Content generation via banter_engine
- Infrastructure: OAuth management, logging, compliance

## Dependencies

- Python 3.8+
- asyncio support
- Platform-specific APIs (tweepy, linkedin-api)
- WRE integration for autonomous operations

## Usage

### New Refactored API (Recommended)
```python
from modules.platform_integration.social_media_orchestrator.src.refactored_posting_orchestrator import get_orchestrator

# Get orchestrator instance
orchestrator = get_orchestrator()

# Handle single stream detection event
result = orchestrator.handle_stream_detected(
    video_id='VIDEO_123',
    title='My Live Stream',
    url='https://youtube.com/watch?v=VIDEO_123',
    channel_name='@FoundUps'
)

# Handle multiple streams detected (NEW - WSP 3 compliant)
detected_streams = [
    {'video_id': 'VIDEO_1', 'channel_id': 'UCklMTNnu5POwRmQsg5JJumA', 'channel_name': 'Move2Japan'},
    {'video_id': 'VIDEO_2', 'channel_id': 'UC-LSSlOZwpGIRIYihaz8zCw', 'channel_name': 'UnDaoDu'},
    {'video_id': 'VIDEO_3', 'channel_id': 'UCSNTUXjAgpd4sgWYP0xoJgw', 'channel_name': 'FoundUps'}
]
result = orchestrator.handle_multiple_streams_detected(detected_streams)
# Automatically sorts by priority and handles sequencing
```

### Migration Bridge (Zero Changes Needed)
```python
from modules.platform_integration.social_media_orchestrator.src.orchestrator_migration import handle_stream_detected

# Drop-in replacement - no code changes needed!
result = handle_stream_detected('VIDEO_123', 'My Live Stream', 'https://youtube.com/...', '@FoundUps')
```

### Individual Core Components
```python
from modules.platform_integration.social_media_orchestrator.src.core import (
    DuplicatePreventionManager,
    PlatformPostingService,
    ChannelConfigurationManager
)

# Use components independently
duplicate_mgr = DuplicatePreventionManager()
posting_service = PlatformPostingService()
```

## Refactoring Benefits (V021)

### Before vs After
- **Before**: 996 lines in single monolithic file
- **After**: 1,539 lines across 6 focused modules (better organized + enhanced docs/logging)

### Architecture Improvements
- [OK] **Single Responsibility**: Each module has one clear purpose
- [OK] **Testability**: Easy to write focused unit tests (23+ tests created)
- [OK] **Maintainability**: Changes isolated to specific modules
- [OK] **Reusability**: Components work independently
- [OK] **Debugging**: Issues traced to specific modules
- [OK] **Performance**: 5-minute caching reduces API calls
- [OK] **Browser Config**: Edge for @Foundups, Chrome for @GeozeAi
- [OK] **Migration**: Zero breaking changes with migration bridge

### Enhanced Features
- Duplicate prevention with visual logging indicators and QWEN intelligence
- Live status verification with intelligent caching
- Channel configuration with JSON persistence
- Platform-specific posting with proper browser assignment
- Multi-stream orchestration with priority sequencing
- Automatic channel-to-platform mapping
- Comprehensive error handling and validation
- QWEN platform health monitoring (HEALTHY -> WARMING -> HOT -> OVERHEATED)
- Intelligent posting decisions based on platform heat levels
- Pattern learning from successful posts and rate limits

### Channel-to-Platform Mapping
The orchestrator automatically maps YouTube channels to the correct social media accounts:

| YouTube Channel | Channel ID | LinkedIn Page | X Account | Browser |
|-----------------|------------|---------------|-----------|---------|
| Move2Japan | UCklMTNnu5POwRmQsg5JJumA | GeoZai (104834798) | @Move2Japan | Chrome |
| UnDaoDu | UC-LSSlOZwpGIRIYihaz8zCw | UnDaoDu (165749317) | @Move2Japan | Chrome |
| FoundUps | UCSNTUXjAgpd4sgWYP0xoJgw | FoundUps (1263645) | @Foundups | Edge |

**Posting Priority**: Move2Japan -> UnDaoDu -> FoundUps (15-second delays between posts)

## Documentation

For detailed technical architecture documentation:
- [Duplicate Prevention Database Architecture](docs/DUPLICATE_PREVENTION_DATABASE_ARCHITECTURE.md) - Complete analysis of write-through cache pattern and database integration
- [Vision Enhancement Proposal](docs/VISION_ENHANCEMENT_PROPOSAL.md)
- [Posting Scenarios Map](docs/POSTING_SCENARIOS_MAP.md)
- [LinkedIn URL Fix](docs/LINKEDIN_URL_FIX.md)

## WSP Compliance

- **WSP 3**: Proper domain placement in platform_integration
- **WSP 11**: Complete interface documentation
- **WSP 22**: Comprehensive ModLog maintenance
- **WSP 49**: Full directory structure compliance
- **WSP 50**: Pre-action verification in all operations
- **WSP 72**: Block independence achieved through modularization
- **WSP 87**: HoloIndex navigation entries for all components
## Runtime Control (2026-03-18)
- main.py now registers social_media as a broker-managed runtime with a real stop hook.
- stop social media dae maps to stop_social_media_dae() instead of returning stop_unsupported.
- The cadence wait is interruptible, so stop requests do not sit behind the full sleep interval.

