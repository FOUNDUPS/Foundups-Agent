# WSP Module ModLog: Shared Utilities
**WSP Compliance**: WSP 22 (Module ModLog and Roadmap Protocol)

## 2026-03-22 - AI Engine Singletons (Prevent Redundant Model Loading)
- **Problem**: Multiple components (autonomous_refactoring.py, daemon_monitor_mixin.py, fam_adapter.py) each loaded Qwen/Gemma models independently, causing 2-10 second startup lag per component.
- **Solution**: Added `ai_engine_singletons.py` with centralized singleton access to AI engines.
  - `get_qwen_engine()` - Returns singleton QwenInferenceEngine (lazy loaded)
  - `get_gemma_engine()` - Returns singleton Llama/Gemma instance (lazy loaded)
  - `is_qwen_loaded()` / `is_gemma_loaded()` - Check load state without side effects
  - `get_engine_status()` - Get status of all singletons
- **Impact**: First component to request an engine loads it (~3-5s), all subsequent requests return cached instance (~0ms).
- **Files**:
  - `ai_engine_singletons.py` (NEW)
  - `holo_index/qwen_advisor/orchestration/autonomous_refactoring.py` (UPDATED - uses singletons)
- **WSP Compliance**: WSP 77 (Agent Coordination), WSP 91 (DAEMON Observability - load time logging)

## 2026-03-07 - LinkedIn Account Registry (Central Source of Truth)
- **Problem**: LinkedIn company IDs were hardcoded across ~14+ modules, making account management fragile and creating duplication.
- **Solution**: Added `linkedin_account_registry.py` as single source of truth for LinkedIn company accounts.
  - Loads from `LINKEDIN_ACCOUNTS_JSON` env var for flexibility
  - Provides fuzzy matching via `ACCOUNT_ALIASES` (monk→undaodu, m2j→move2japan, 012→undaodu)
  - URL generators: `get_article_url()`, `get_admin_url()`, `get_company_page_url()`
  - Default fallback via `LINKEDIN_DEFAULT_COMPANY` env var
- **Impact**: All LinkedIn modules can import from central registry instead of hardcoding IDs.
- **Files**:
  - `linkedin_account_registry.py` (NEW)
  - `.env.example` (updated with LINKEDIN_* vars)
  - `modules/ai_intelligence/ai_overseer/skillz/linkedin_company_poster/executor.py` (migrated)
- **WSP Compliance**: WSP 60 (Module Memory Architecture), WSP 3 (shared utilities for cross-domain config)
- **Migration Status**: COMPLETE - 13 files migrated across 6 modules:
  - linkedin_agent (2 files)
  - social_media_orchestrator (6 files)
  - foundups_selenium (1 file)
  - browser_actions (1 file)
  - git_push_dae (1 file)
  - wre_core/development_monitor (1 file)
  - git_social_posting (1 file)
- **LinkedInCompany Constants**: Added `LinkedInCompany` class with name constants for type-safety
  - Constants: FOUNDUPS, UNDAODU, MOVE2JAPAN, AUTONOMOUSWALL, ESINGULARITY, etc.
  - Enables IDE autocomplete and reduces string typos
- **CTO Note**: Added fork documentation to INTERFACE.md
  - Documents ~72 hardcoded company name usages across 13 files
  - Instructions for forkers to customize company names
  - Reference to `qwen_bulk_import_migration` skill for automated refactoring
- **YouTube Registry Integration**: Updated `youtube_channel_registry.py` to use linkedin_account_registry
  - Added `linkedin_company` field to channel social config
  - Resolves company names to IDs via `get_company_id()` at normalization time
  - Updated `memory/youtube_channels.json` with linkedin_company values
  - WSP 84 (Code Reuse) - single source of truth for LinkedIn IDs

## 2026-03-07 - Managed Environment Loader (0102 Autopilot)
- **Problem**: `.env` had ordering drift, duplicate keys, and non-parseable lines, causing unclear runtime precedence and operator overhead.
- **Solution**: Added managed env utility: `env_managed.py`.
  - Builds `.env.managed` from `.env` with deterministic policy:
    - last duplicate key wins
    - non-parseable/orphan lines preserved as comments for auditability
  - Exposes stats (`duplicate_keys`, `duplicate_overwrites`, `orphan_lines`) for runtime diagnostics.
- **Main Integration**:
  - `main.py` now uses managed env flow by default (`FOUNDUPS_ENV_MANAGED=1`).
  - Fallback to legacy direct `.env` loading if managed loader fails or is disabled.
- **Operational Outcome**:
  - 0102 can run with stable env precedence without manual `.env` reordering.
  - Operator no longer needs to actively curate duplicate ordering in large env files.
- **Files**:
  - `modules/infrastructure/shared_utilities/env_managed.py`
  - `main.py`
  - `.env.example` (`FOUNDUPS_ENV_MANAGED=1`)

## 2026-03-07 - Env Exposure Hardening (no managed copy on disk)
- **Problem**: Persisting `.env.managed` on disk creates unnecessary secret-copy exposure risk.
- **Solution**:
  - Switched managed env runtime to in-memory normalization/application by default.
  - Added explicit controls:
    - `FOUNDUPS_ENV_MANAGED_DISK_COPY=0` (default)
    - `FOUNDUPS_ENV_MANAGED_PURGE_COPY=1` (default)
  - Auto-purges stale `.env.managed` copy when purge is enabled.
  - Removed existing `.env.managed` from workspace.
- **Operational Result**:
  - Runtime keeps deterministic duplicate resolution without creating extra env files.
  - `.env` remains the single authoritative secret file.

## 2026-02-02 - YouTube Channel Registry (Central Source of Truth)
- **Problem**: Channel rotation lists were duplicated across modules, making new channel onboarding fragile.
- **Solution**: Added `youtube_channel_registry.py` + registry JSON in module memory to centralize channel metadata (roles, browser grouping, shorts config).
- **Impact**: Live checks, comment rotation, and shorts scheduling can pull from a shared registry instead of hard-coded lists.
- **Files**: `youtube_channel_registry.py`, `memory/youtube_channels.json`, README/INTERFACE updates.

## Critical Safety Enhancement System Implementation
- **Problem**: Multiple unauthorized social media posting attempts bypassing safety checks
- **Solution**: Implemented comprehensive 5-layer safety system with global posting lock
- **Files Modified**: 7 posting interfaces across 4 modules
- **Safety Impact**: 100% blocking of unauthorized social media posting
- **WSP Compliance**: WSP 27, WSP 50, WSP 80

### Files Enhanced with Safety Checks:
1. `modules/platform_integration/x_twitter/src/simple_x_poster.py` - SimpleXPoster.post_to_x()
2. `modules/platform_integration/social_media_orchestrator/src/unified_posting_interface.py` - UnifiedLinkedInPoster.post() & UnifiedXPoster.post()
3. `modules/platform_integration/linkedin_agent/src/git_linkedin_bridge.py` - GitLinkedInBridge.post_recent_commits()
4. `modules/platform_integration/linkedin_agent/src/youtube_linkedin_bridge.py` - YouTubeLinkedInBridge.post_to_company_page()
5. `tools/monitors/auto_stream_monitor.py` - AutoStreamMonitor.post_to_x_twitter() & post_to_linkedin()

### Global Safety Lock Features:
- **Master Switch**: `PostingSafetyLock.SAFETY_ENABLED = True` blocks all posting
- **Platform-Specific Blocking**: Individual platform controls (LinkedIn, X/Twitter)
- **Emergency Functions**: `emergency_posting_shutdown()` for immediate lockdown
- **Monitoring**: Real-time safety status checking
- **Graceful Fallbacks**: Handles missing safety module gracefully

### Root Cause Analysis:
- **Issue**: Multiple posting interfaces bypassed existing safety checks
- **Discovery**: Simple posting classes, unified interfaces, and bridge classes lacked safety validation
- **Resolution**: Added global safety lock integration to ALL posting methods
- **Prevention**: Centralized safety system prevents future bypasses

### WSP Protocol Compliance:
- **WSP 27**: Partifact DAE Architecture - Maintained modular safety design
- **WSP 50**: Pre-Action Verification Protocol - Added verification to all posting actions
- **WSP 80**: Cube-Level DAE Orchestration - Enhanced orchestration safety
- **WSP 22**: Module ModLog Protocol - Documented all changes per protocol
