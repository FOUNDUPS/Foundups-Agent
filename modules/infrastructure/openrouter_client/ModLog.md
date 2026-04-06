# OpenRouter Client - ModLog

## V0.1.1 - Canonicalized into tracked repo (2026-04-05)

### Changed
- Module committed to git (was untracked since V0.1.0)
- Classification: standalone, default-off, secret-required, non-gateway
- Integration manifest entry added at `modules/communication/moltbot_bridge/config/openclaw_integration_manifest.json`
- Audit docs updated to reflect tracked status

### Worker
- Worker G, slice `OPENROUTER_MODULE_CANONICALIZE_PHASE1`

---

## V0.1.0 - Initial Implementation (2026-03-26)

### Added
- `OpenRouterConfig` dataclass for env-based configuration
- `OpenRouterResponse` dataclass with cost tracking
- `OpenRouterClient` class with:
  - `chat_completion()` - OpenAI-compatible chat API
  - `health()` - API health check
  - `list_models()` - Available models
  - `startup_probe()` - Startup verification with remediation
- Model aliases (sonnet, gpt4, llama, mistral, gemini)
- Preset support (@preset/foundups-agent)
- Web search plugin support
- Singleton pattern via `get_openrouter_client()`
- Quick functions: `openrouter_chat()`, `openrouter_health()`

### Configuration
- Dashboard configured with routing rules
- Preset `foundups-agent` created (temp=0.3, max_tokens=4096)
- Web search plugin enabled per-request

### WSP Compliance
- WSP 3: Infrastructure domain placement
- WSP 49: Module structure (README, INTERFACE, src/, tests/)
- WSP 50: Pre-action verification (health probes)

### Integration Points
- Fallback for OpenClaw/IronClaw when local models fail
- Direct usage for modules needing LLM capabilities
