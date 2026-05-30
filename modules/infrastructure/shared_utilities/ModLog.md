# WSP Module ModLog: Shared Utilities
**WSP Compliance**: WSP 22 (Module ModLog and Roadmap Protocol)

## 2026-05-30 - LM Studio Dependency Boundary Doc + Gate (LM_STUDIO_DEPENDENCY_BOUNDARY_DOC_AND_GATE_PHASE1)

- **Problem**: LM Studio is an optional local dependency, but absence produced a
  silent `None` from `resolve_*_backend` / `ai_engine_singletons` and an
  ambiguous, non-actionable warning. Required-LM-Studio callers had no named
  state to branch on.
- **Solution** (probe-only, additive — no existing signature/return type changed):
  - `local_llm_resolver.py`:
    - `LocalLLMAvailability` (Enum): `LM_STUDIO_READY` / `FALLBACK_LLAMA_CPP` / `UNAVAILABLE`
    - `probe_backend_availability(model_path=None)`: probe-only classifier (HTTP probe + GGUF filesystem check); never launches LM Studio
    - `operator_action_for(status)`: operator-actionable guidance per state
    - `LMStudioUnavailableError` + `require_lm_studio_backend(model_id, base_url=None)`: named error for paths that strictly require LM Studio
    - `resolve_qwen_backend` / `resolve_gemma_backend`: clearer fallback INFO ("using local GGUF fallback via llama.cpp … resolver does not auto-launch it") and operator-actionable WARNING when no fallback exists
- **Boundary preserved**: LM Studio launch stays solely in
  `dependency_launcher.dae_dependencies.launch_lm_studio` (explicit DAE/menu path).
  Resolver imports no `subprocess`/launch symbols.
- **Non-scope (verified)**: `main.py` never probes/launches LM Studio at boot;
  HoloIndex timeout defaults (#730) and OBS boundaries (#720/#721) untouched.
- **Files**:
  - `local_llm_resolver.py` (UPDATED — additive)
  - `tests/test_lm_studio_dependency_boundary.py` (NEW — 16 tests)
  - `docs/audits/architecture/LM_STUDIO_DEPENDENCY_BOUNDARY_DOC_AND_GATE_PHASE1.md` (NEW)
- **Predecessors**: #720, #721, #728, #730, #732
- **WSP Compliance**: WSP 77 (Agent Coordination), WSP 91 (Observability), WSP 97 (Truthful state distinction)

## 2026-04-13 - Local LLM Backend Adapter Layer (LM Studio API Support)

- **Problem**: Qwen/Gemma model loading fails when LM Studio holds file locks on GGUF files. Startup log shows `PermissionError` or silent failures.
- **Solution**: Added backend adapter layer with LM Studio API fallback.
  - `local_llm_backends.py` (NEW): Abstract `LocalLLMBackend` base + two implementations:
    - `LlamaCppBackend`: Direct GGUF file loading via llama_cpp (original behavior)
    - `LMStudioBackend`: OpenAI-compatible API client for LM Studio (localhost:1234)
    - `is_lm_studio_available()`: Health check for LM Studio API
    - Compatibility methods: `.generate_response()` and `__call__()` for existing callers
  - `local_llm_resolver.py` (NEW): Backend selection logic
    - `resolve_qwen_backend()`: Try LM Studio first, fall back to llama_cpp
    - `resolve_gemma_backend()`: Same pattern
    - Model ID mapping: `{"qwen": "qwen-coder-7b", "gemma": "gemma-270m"}`
  - `ai_engine_singletons.py` (UPDATED): Now uses resolver instead of direct loading
    - `get_qwen_engine()` / `get_gemma_engine()` call resolvers
    - Returns `LocalLLMBackend` with API-compatible methods
    - Singletons remain cache/lifecycle only
- **Caller Compatibility**:
  - Qwen callers: `.generate_response(prompt, max_tokens)` works (returns string)
  - Gemma callers: `engine(prompt, max_tokens, temperature)` callable works (returns dict)
- **Impact**: Qwen/Gemma load succeeds when LM Studio is running (verified). Fallback to direct llama_cpp loading is implemented but not yet verified in production (LM Studio currently always available).
- **Files**:
  - `local_llm_backends.py` (NEW)
  - `local_llm_resolver.py` (NEW)
  - `ai_engine_singletons.py` (UPDATED)
- **WSP Compliance**: WSP 77 (Agent Coordination), WSP 91 (DAEMON Observability)

## 2026-03-30 - Audio Provider Registry and Voice Cloning Policy

- **Context**: News integration pass for Cohere Transcribe, Qwen3-TTS, Mistral Voxtral.
- **Changes**:
  - `local_model_selection.py`: Added `asr` and `tts` roles with Cohere Transcribe 2B and Qwen3-TTS defaults
  - `local_model_selection.py`: Added `TRANSFORMERS_FORMAT_ROLES` for non-GGUF models (ASR uses transformers format)
  - `audio_provider_registry.py` (NEW): Provider registry with production/eval-only flags
    - `cohere_transcribe`: preferred ASR, production_enabled=true
    - `qwen3_tts`: preferred TTS, production_enabled=true
    - `voxtral_tts_eval`: production_enabled=false (eval-only, licensing restrictions)
  - `voice_cloning_policy.py` (NEW): Safety gate for voice cloning operations
    - Consent + whitelist requirements
    - Emergency kill switch
    - Audit logging hook
- **Model Storage**: `E:/LM_studio/models/local/` (zero-config default via LOCAL_MODEL_ROOT)
- **Model Formats**: GGUF (tts/triage/general/code) vs transformers (asr)
- **Research Doc**: `docs/research/2026-03-30-audio-agents.md`
- **WSP Compliance**: WSP 3 (shared utilities), WSP 60 (module memory)

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
