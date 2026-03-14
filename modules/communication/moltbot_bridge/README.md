# OpenClaw Bridge = 012's Digital Twin

> **OpenClaw** (formerly Moltbot/Clawdbot), trained on WSP framework, operating on Foundups-Agent codebase

## Version Note

| Date | Name | Package |
|------|------|---------|
| Jan 30, 2026 | **OpenClaw** (current) | `openclaw` |
| Jan 27, 2026 | Moltbot | `moltbot` |
| Pre-2026 | Clawdbot | `clawdbot` |

## Vision

OpenClaw becomes **0102** — the Digital Twin of 012:
- **Voice**: Multi-channel (WhatsApp, Telegram, Discord, Voice)
- **Brain**: WSP framework + HoloIndex semantic search
- **Body**: Foundups-Agent codebase

## Architecture

```
012 (Human) ──voice/chat──► OpenClaw Gateway ──WSP-trained──► Foundups Codebase
                                   │
                                   ├── AGENTS.md (WSP training)
                                   ├── SOUL.md (0102 identity)
                                   └── skills/ (foundups-wsp, holo-search)
```

## Setup

> ⚠️ **Important**: See [docs/INSTALL_OPENCLAW.md](docs/INSTALL_OPENCLAW.md) for full guide

1. **Install Node.js in WSL**: Required first! (not Windows Node)
2. **Install OpenClaw**: `npm i -g openclaw && openclaw onboard`
3. **Configure workspace**: Point to this module's `workspace/` directory
4. **Set env**: `DISCORD_BOT_TOKEN`, `FOUNDUPS_WEBHOOK_TOKEN`

## IronClaw Sidecar Mode (Optional)

OpenClaw DAE can route conversational responses through an IronClaw
OpenAI-compatible gateway while keeping existing WRE control-plane behavior.

- `OPENCLAW_CONVERSATION_BACKEND=ironclaw`
- `IRONCLAW_BASE_URL=http://127.0.0.1:3000`
- `IRONCLAW_MODEL=local/qwen-coder-7b`
- `IRONCLAW_AUTH_TOKEN=<token>` (optional, if gateway requires bearer auth)
- `IRONCLAW_NO_API_KEYS=1` (default): strips provider API keys from IronClaw launch env
- `OPENCLAW_NO_API_KEYS=1` (recommended): disables OpenClaw cloud LLM fallbacks
- `OPENCLAW_ALLOW_EXTERNAL_LLM=0` (recommended with key isolation)
- `IRONCLAW_START_CMD=<your start command>` (used by CLI submenu launcher)

CLI integration:
- Main menu -> `16. OpenClaw / IronClaw` -> options `5/6/7/8`
- Direct flags: `--ironclaw-chat`, `--ironclaw-voice`

## Standalone Action CLI (Agent API Surface)

For autonomous execution outside menu navigation, use:

```bash
python -m modules.communication.moltbot_bridge.src.action_cli \
  --command "youtube action comments channel=move2japan max_comments=2 dry_run=true"
```

Optional DAE-routed mode:

```bash
python -m modules.communication.moltbot_bridge.src.action_cli \
  --command "x action post content=smoke_test dry_run=true" \
  --via-dae --backend ironclaw --no-api-keys on
```

Repeat mode for 012 observation/testing:

```bash
python -m modules.communication.moltbot_bridge.src.action_cli \
  --command "linkedin action read_feed max_posts=2" \
  --repeat 5 --interval-sec 60
```

LinkedIn digital twin command example:

```bash
python -m modules.communication.moltbot_bridge.src.action_cli \
  --command "linkedin action digital_twin comment_text='...' repost_text='...' schedule_date='Mar 12, 2026' schedule_time='10:00 PM' mentions='@foundups,@Mo Gawdat' identity_cycle='FOUNDUPS,Move2Japan,UnDaoDu'" \
  --via-dae
```

Adapter note:
- `linkedin_social_adapter` now passes `mentions` and `identity_cycle` through to the LinkedIn layered digital twin flow.

Security:
- Standalone adapter mode runs the same Cisco skill-safety gate before execution.
- DAE mode (`--via-dae`) also enforces skill safety through OpenClawDAE.

### Memory Writeback (WSP 60 / WSP 48)

Standalone action runs are now persisted into WRE PatternMemory as `skill_outcomes`
records (`action_cli_<route>_<action>`), enabling recall of:
- what command ran,
- whether it succeeded,
- response summary,
- execution duration.

## Files

| Path | Purpose |
|------|---------|
| `workspace/AGENTS.md` | WSP framework training |
| `workspace/SOUL.md` | 0102 identity/voice |
| `workspace/TOOLS.md` | Foundups CLI commands |
| `workspace/skills/` | OpenClaw skills |
| `config/moltbot.json` | Legacy sample config (OpenClaw uses `~/.openclaw/openclaw.json`) |

## Skill Safety Gate (Cisco Skill Scanner)

OpenClaw DAE now runs a cached safety preflight on local skills before mutating routes
(`command`, `system`, `schedule`, `social`, `automation`, `foundup`).

- Scanner package: `cisco-ai-skill-scanner`
- CLI: `skill-scanner`
- Skills path scanned: `modules/communication/moltbot_bridge/workspace/skills`
- Report path: `modules/communication/moltbot_bridge/reports/openclaw_skill_scan_report.json`

Environment toggles:
- `OPENCLAW_SKILL_SCAN_REQUIRED=1` (default): fail closed if scanner missing
- `OPENCLAW_SKILL_SCAN_ENFORCED=1` (default): block risky scans above threshold
- `OPENCLAW_SKILL_SCAN_MAX_SEVERITY=medium` (default)
- `OPENCLAW_SKILL_SCAN_TTL_SEC=900` (default cache window)
- `OPENCLAW_SKILL_SCAN_ALWAYS=0` (default): set `1` to force scan on every mutating route
- `OPENCLAW_SKILL_MANIFEST_REQUIRED=1` (default): require `workspace/skills/SKILL_MANIFEST.json`
- `OPENCLAW_SKILL_MANIFEST_ENFORCED=1` (default): block on missing/mismatched manifest
- `OPENCLAW_SKILL_MANIFEST_VERIFY_SIGNATURE=0` (default): verify HMAC signature when enabled
- `OPENCLAW_SKILL_MANIFEST_ALLOW_EXTRA=0` (default): block unlisted `SKILL.md/SKILLz.md` files
- `OPENCLAW_SKILL_MANIFEST_FILE=` (optional): override manifest path
- `OPENCLAW_SKILL_MANIFEST_HMAC_KEY=` (optional): key for signature verification

## Skill Boundary Policy

OpenClaw workspace skills and internal `skillz` are intentionally separated.

- Policy: `docs/SKILL_BOUNDARY_POLICY.md`
- OpenClaw workspace skills: `workspace/skills/**/SKILL.md` (operator workflow layer)
- Internal execution skillz: `modules/**/skillz/**/SKILLz.md` (trusted module layer)

## Security Hardening

### SOURCE Tier Permission Check
SOURCE tier operations (code edits) require explicit permission via AgentPermissionManager.
Fail-closed: blocked if manager unavailable or check fails. Permission denied events emitted with 60s dedupe.

### Webhook Rate Limiting
Token bucket rate limiting per sender and channel (defense-in-depth):
- `OPENCLAW_RATE_LIMITING_ENABLED=1` (default)
- `OPENCLAW_RATE_SENDER_PER_SEC=2.0` / `OPENCLAW_RATE_SENDER_BURST=10.0`
- `OPENCLAW_RATE_CHANNEL_PER_SEC=5.0` / `OPENCLAW_RATE_CHANNEL_BURST=20.0`

Returns HTTP 429 with `X-Retry-After` when exceeded.

### COMMAND Graceful Degradation
When WRE is unavailable, COMMAND intents return deterministic advisory fallback with:
- Advisory Mode header
- Command recognition
- Three actionable options (CLI, retry, query mode)

## WSP 97 Control-Plane Module Map

OpenClaw now follows a facade + delegated-module design.
`OpenClawDAE` remains the public contract surface, while the runtime is split into focused control-plane modules.

| Module | Responsibility |
|------|------|
| `src/openclaw_dae.py` | Facade, public contract, dependency wiring |
| `src/openclaw_intent_planner.py` | Intent classification, WSP preflight, plan construction |
| `src/openclaw_permission_policy.py` | Autonomy tiers, SOURCE gating, containment, skill safety |
| `src/openclaw_execution_routes.py` | Post-plan route dispatch |
| `src/openclaw_conversation_engine.py` | Conversation execution and response shaping |
| `src/openclaw_model_policy.py` | Agentic model routing and live model switching |
| `src/openclaw_identity_context.py` | Identity card, platform context pack, WSP_00 prompt assembly |
| `src/openclaw_runtime_support.py` | Runtime probing, IronClaw autostart, model availability |
| `src/openclaw_status_surface.py` | `connect wre` readiness/status and outward status push |
| `src/openclaw_process_loop.py` | Full autonomy loop orchestration |
| `src/openclaw_result_memory.py` | Validate + remember (WRE pattern memory writeback) |
| `src/openclaw_turn_state.py` | Token telemetry and cooperative turn cancellation |
| `src/openclaw_action_ledger.py` | Structured DAEmon action emission |
| `src/openclaw_social_controller.py` | Social-routing bridge and LinkedIn mission control |
| `src/openclaw_provider_chain.py` | Preferred external / IronClaw provider call chain |
| `src/openclaw_bootstrap_config.py` | Constructor-time state/bootstrap wiring |

Current refactor result:
- `openclaw_dae.py` reduced from `2638` lines to `1342`
- remaining file content is predominantly facade wrappers, dataclasses, and the honeypot surface
