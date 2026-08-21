# shared_utilities Interface Specification

**WSP 11 Compliance:** Complete
**Last Updated:** 2026-08-21
**Version:** 0.4.0

## [OVERVIEW] Module Overview

**Domain:** infrastructure
**Purpose:** Cross-cutting utilities for model selection, registry management, and policy enforcement

## [API] Public API

### Local Model Selection

### Local LM Studio Backend

```python
require_lm_studio_backend(model_id, base_url=None, request_timeout=30.0)
LMStudioBackend.create_native_chat(
    input_text=...,
    system_prompt=...,
    max_output_tokens=...,
    reasoning="off",
    max_response_bytes=...,
)
```

The required resolver probes but never starts LM Studio and rejects when the
exact model ID is not loaded. The native call accepts only bounded reasoning,
token, timeout, and response-byte controls; uses `store=false` and
`stream=false`; and performs no provider/model fallback. The OpenAI-compatible
chat method forwards only an allowlist of sampling/structured controls and
constructs chat-template thinking control from a strict boolean rather than
accepting caller-supplied arbitrary `extra_body`.

Role-based model path resolution for local AI models. Models stored at `E:/HoloIndex/models/`.

```python
from modules.infrastructure.shared_utilities.local_model_selection import (
    resolve_model_selection,
    resolve_model_path,
    resolve_triage_model_path,
    resolve_general_model_path,
    resolve_code_model_path,
    resolve_asr_model_path,
    resolve_tts_model_path,
    get_model_selections,
    ModelSelection,
)

# Resolve best-available model for a role
selection = resolve_model_selection("triage")
print(f"Path: {selection.path}, Exists: {selection.exists}")

# Convenience helpers
triage_path = resolve_triage_model_path()  # Gemma 270M
general_path = resolve_general_model_path()  # Qwen3.5 4B
code_path = resolve_code_model_path()  # Qwen Coder 7B
asr_path = resolve_asr_model_path()  # Cohere Transcribe 2B
tts_path = resolve_tts_model_path()  # Qwen3-TTS

# Get all role selections
all_selections = get_model_selections()
```

#### Supported Roles

| Role | Default Model | Env Override |
|------|--------------|--------------|
| `triage` | gemma-270m | `LOCAL_MODEL_TRIAGE_PATH` |
| `general` | qwen3.5-4b | `LOCAL_MODEL_GENERAL_PATH` |
| `code` | qwen-coder-7b | `LOCAL_MODEL_CODE_PATH` |
| `asr` | cohere-transcribe-2b | `LOCAL_MODEL_ASR_PATH` |
| `tts` | qwen3-tts | `LOCAL_MODEL_TTS_PATH` |

### Audio Provider Registry

Provider metadata with production/eval-only gating.

```python
from modules.infrastructure.shared_utilities.audio_provider_registry import (
    get_audio_registry,
    get_preferred_asr,
    get_preferred_tts,
    is_voxtral_allowed,
    AudioProvider,
    AudioProviderType,
    AudioLicense,
)

# Get preferred providers
asr = get_preferred_asr()  # cohere_transcribe (preferred=True, production_enabled=True)
tts = get_preferred_tts()  # qwen3_tts (preferred=True, production_enabled=True)

# Check production gating
registry = get_audio_registry()
registry.is_production_enabled("voxtral_tts_eval")  # False (eval-only)

# List providers
all_tts = registry.list_providers("tts")
prod_only = registry.list_providers(production_only=True)
cloning_capable = registry.list_voice_cloning_providers()

# Voxtral is blocked unless AUDIO_ALLOW_EVAL_PROVIDERS=1
is_voxtral_allowed()  # False in production
```

#### Registered Providers

| Provider | Type | License | Production | Preferred |
|----------|------|---------|------------|-----------|
| `cohere_transcribe` | ASR | Apache 2.0 | Yes | Yes |
| `whisper_local` | ASR | MIT | Yes | No |
| `qwen3_tts` | TTS | Apache 2.0 | Yes | Yes |
| `edge_tts` | TTS | Proprietary | Yes | No |
| `voxtral_tts_eval` | TTS | Eval-only | **No** | No |

### Voice Cloning Policy

Safety gate enforcing consent + whitelist + kill switch for voice cloning.

```python
from modules.infrastructure.shared_utilities.voice_cloning_policy import (
    get_voice_policy,
    VoiceCloneRequest,
    PolicyResult,
    VoiceCloningPolicy,
)

policy = get_voice_policy()

# Check if cloning is allowed
request = VoiceCloneRequest(
    voice_id="voice_012",
    requester="system",
    purpose="stream_tts",
)
result = policy.check(request)
if result.allowed:
    # Proceed with voice cloning
    ...
else:
    print(f"Denied: {result.reason}")

# Admin operations
policy.add_to_whitelist("voice_012")
policy.record_consent("voice_012", consented_by="operator_012")
policy.engage_kill_switch()  # Emergency disable all cloning
policy.disengage_kill_switch()
```

#### Policy Requirements

Voice cloning is **denied** unless ALL conditions are met:
1. Kill switch is not engaged
2. Voice ID is in `allowed_voices` whitelist
3. Valid (non-expired) consent is recorded for voice ID

#### Consent Storage

Consents persist to `memory/voice_cloning_consents.json` (configurable via `VOICE_CONSENT_STORE` env var).

### YouTube Channel Registry
```python
from modules.infrastructure.shared_utilities.youtube_channel_registry import (
    get_channels,
    get_channel_ids,
    get_channel_keys,
    get_rotation_order,
    add_channel,
)

# Load registry
channels = get_channels()
channel_ids = get_channel_ids(role="live_check")
rotation_keys = get_rotation_order(role="comments")

# Add new channel
ok, msg = add_channel({
    "key": "newchannel",
    "id": "UCxxxxxxxxxxxx",
    "name": "NewChannel",
    "handle": "@NewChannel",
})
```

### LinkedIn Account Registry
```python
from modules.infrastructure.shared_utilities.linkedin_account_registry import (
    get_accounts,
    get_company_id,
    get_article_url,
    get_admin_url,
    get_company_page_url,
    get_default_company,
    list_all_accounts,
    ACCOUNT_ALIASES,
)

# Get all accounts from LINKEDIN_ACCOUNTS_JSON env var
accounts = get_accounts()  # {"foundups": "1263645", "undaodu": "68706058", ...}

# Get company ID with fuzzy matching/aliases
company_id = get_company_id("foundups")  # "1263645"
company_id = get_company_id("monk")      # "68706058" (alias for undaodu)
company_id = get_company_id("m2j")       # "104834798" (alias for move2japan)

# Get URLs for company pages
article_url = get_article_url("foundups")  # Direct article editor URL
admin_url = get_admin_url("undaodu")       # Company admin posts URL
page_url = get_company_page_url("move2japan")  # Public company page

# Get default company (from LINKEDIN_DEFAULT_COMPANY env var)
default_id = get_default_company()  # Falls back to "1263645" (foundups)

# List all accounts with URLs (for debugging)
all_info = list_all_accounts()
```

#### Environment Configuration
```bash
# .env or .env.example
LINKEDIN_DEFAULT_COMPANY=foundups
LINKEDIN_ACCOUNTS_JSON={"foundups":"1263645","undaodu":"68706058","move2japan":"104834798",...}
```

#### Available Aliases
| Alias | Maps To | Company ID |
|-------|---------|------------|
| monk, 012, michael, mjt | undaodu | 68706058 |
| m2j, japan | move2japan | 104834798 |
| fu, foundups® | foundups | 1263645 |
| aw, wall | autonomouswall | 35532191 |
| See ACCOUNT_ALIASES dict for full list |||

#### LinkedInCompany Constants
```python
from modules.infrastructure.shared_utilities.linkedin_account_registry import LinkedInCompany

# Use constants instead of string literals for type safety
company_id = get_company_id(LinkedInCompany.FOUNDUPS)
company_id = get_company_id(LinkedInCompany.UNDAODU)
company_id = get_company_id(LinkedInCompany.MOVE2JAPAN)
```

### CTO Note: Forking This Codebase

> **For teams forking FoundUps-Agent to build their own pAVS ecosystem:**

**What's Externalized (Easy)**:
- Company **IDs** are loaded from `LINKEDIN_ACCOUNTS_JSON` env var
- Default company from `LINKEDIN_DEFAULT_COMPANY` env var
- No code changes needed for ID-only customization

**What's Hardcoded (Requires Changes)**:
- Company **names** (e.g., "foundups", "undaodu") appear in ~72 places across 13 files
- These are used in: enum definitions, config mappings, string comparisons, default values

**To Fork**:
1. Update `LinkedInCompany` class in `linkedin_account_registry.py` with your company names
2. Run the bulk migration skill to find/replace across codebase:
   ```bash
   python -m modules.infrastructure.wre_core.skillz.qwen_bulk_import_migration.executor \
     --preset linkedin_registry --dry-run
   ```
3. Create custom replacement_map in migration spec for your company names
4. Update `ACCOUNT_ALIASES` dict for your team's preferred shortcuts

**Files Most Affected**:
- `linkedin_agent/` - 2 files (posting, engagement)
- `social_media_orchestrator/` - 6 files (channel config, routing)
- `browser_actions/` - 1 file (LinkedIn actions)
- `ai_overseer/skillz/` - 1 file (company poster skill)

**Design Decision (2026-03-07)**: Company names were kept as readable strings rather than UUIDs for developer ergonomics. The `LinkedInCompany` constants provide type-safety while maintaining readability.

## [CONFIG] Configuration

### Model Selection Environment Variables
```bash
# Model root directory
LOCAL_MODEL_ROOT=E:/LM_studio/models/local

# Role-specific overrides (optional)
LOCAL_MODEL_TRIAGE_PATH=/path/to/triage.gguf
LOCAL_MODEL_GENERAL_PATH=/path/to/general.gguf
LOCAL_MODEL_CODE_PATH=/path/to/code.gguf
LOCAL_MODEL_ASR_PATH=/path/to/asr.gguf
LOCAL_MODEL_TTS_PATH=/path/to/tts.gguf

# Legacy fallback (disabled by default)
LOCAL_MODEL_ENABLE_LEGACY_FALLBACK=0
```

### Audio Provider Environment Variables
```bash
# Allow eval-only providers (for research environments only)
AUDIO_ALLOW_EVAL_PROVIDERS=0

# Voice cloning consent storage
VOICE_CONSENT_STORE=memory/voice_cloning_consents.json
```

## [DEPENDENCIES] Dependencies

### Internal Dependencies
- modules.[domain].[dependency_module] - [Reason for dependency]

### External Dependencies
- [package_name]>=x.y.z - [Purpose of dependency]

## [TESTING] Testing

### Running Tests
```bash
# All shared utilities tests
python -m pytest modules/infrastructure/shared_utilities/tests/ -v

# Model selection tests
python -m pytest modules/infrastructure/shared_utilities/tests/test_local_model_selection.py -q

# Audio provider and voice cloning tests
python -m pytest modules/infrastructure/shared_utilities/tests/test_audio_provider_registry.py -q
```

### Test Coverage
- **Model Selection:** 4 tests (role resolution, legacy fallback, env overrides)
- **Audio Registry:** 7 tests (preferred providers, production gating, voice cloning list)
- **Voice Policy:** 7 tests (whitelist, consent, expiry, kill switch, persistence)

## [PERFORMANCE] Performance Characteristics

### Expected Performance
- **Latency:** [expected latency]
- **Throughput:** [expected throughput]
- **Resource Usage:** [memory/CPU expectations]

## [ERRORS] Error Handling

### Common Errors
- **[ErrorType1]:** [Description and resolution]
- **[ErrorType2]:** [Description and resolution]

### Exception Hierarchy
```python
class [ModuleName]Error(Exception):
    """Base exception for [module_name]"""
    pass

class [SpecificError]([ModuleName]Error):
    """Specific error type"""
    pass
```

## [HISTORY] Version History

### 0.4.0 (2026-08-21)
- Added bounded LM Studio native chat with explicit reasoning control, exact
  model identity, disabled storage/streaming, timeout/response caps, and no
  launch or fallback.
- Restricted OpenAI-compatible controls and added strict thinking projection.

### 0.3.0 (2026-03-30)
- Added `asr` and `tts` roles to local_model_selection.py
- Added audio_provider_registry.py with production/eval-only gating
- Added voice_cloning_policy.py with consent/whitelist/kill-switch enforcement
- Research doc: docs/research/2026-03-30-audio-agents.md

### 0.2.0 (2026-03-07)
- Added LinkedIn account registry
- Added YouTube channel registry
- Added managed environment loader

### 0.1.0 (2025-09-25)
- Initial interface specification

## [NOTES] Development Notes

### Runtime Boundary

This module provides **substrate only** — metadata, model paths, policy gates.

**Not wired to runtime:**
- `openclaw_voice.py` still uses legacy STT/TTS chain (WhisperSTT, EdgeTTS)
- Future integration will replace backends using these registries
- Voice cloning requires explicit policy check before any TTS synthesis

### Future Enhancements
- Wire cohere_transcribe into openclaw_voice.py STT chain
- Wire qwen3_tts into openclaw_voice.py TTS chain

---

**WSP 11 Interface Compliance:** Complete
