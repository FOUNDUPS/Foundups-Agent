# OBAI Discord Bot

Standalone Discord gateway bot for FOUNDUPS community help.

OBAI is a **non-admin helper bot** — it explains, observes, routes, and responds.
It is NOT 0102. They are separate identities, separate tokens, separate runtimes.

## Quick Start

```bash
# Set required env vars
export OBAI_BOT=<your-obai-bot-token>
export OBAI_GUILD_ID=412646632992014336

# Install dependencies
pip install -r requirements.txt

# Run
python -m modules.communication.obai_discord_bot.src.obai_discord_bot
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OBAI_BOT` | YES | — | OBAI Discord bot token |
| `OBAI_GUILD_ID` | NO | `412646632992014336` | Guild ID for logging (not enforced at runtime) |
| `OBAI_LOG_LEVEL` | NO | `INFO` | Logging level |
| `OBAI_ENABLED` | NO | `true` | Master switch |

## What OBAI Does (Phase 1 Layer 1 — Current)

- Connects to Discord gateway as OBAI bot identity
- Logs connection status and guild info on `on_ready`
- Sets activity status: "Watching FOUNDUPS threads"
- Responds to @OBAI mentions with a short helper message
- Ignores: own messages, other bots, @everyone/@here, DMs
- Shuts down gracefully on SIGINT/SIGTERM

## What OBAI Does NOT Do (Yet)

- No guild filtering (responds in any guild it's invited to — see note below)
- No thread auto-join (designed in spec, not implemented)
- No keyword routing (generic help text only)
- No channel allow-list filtering
- No slash commands (Phase 2)
- No LLM inference (Phase 1 is keyword-only, but keywords aren't wired yet)

## What OBAI Will NEVER Do

- No admin actions (kick, ban, role management)
- No moderation (message deletion, thread management)
- No CABR scoring or verification
- No GitHub mutations
- No scheduled posting or auto-triage

---

## Operator Runbook

### 1. Guild Targeting (Important)

**Current behavior**: `OBAI_GUILD_ID` is used only for logging on startup — the bot logs info about that guild. However, the bot will respond to @OBAI mentions in **any guild it's invited to**, not just the configured guild. There is no runtime guild filter in Phase 1.

**Implication**: If OBAI is invited to multiple servers, it will respond in all of them. To restrict OBAI to FOUNDUPS only, do not invite it to other servers.

### 2. Required Discord Intents

Set in Discord Developer Portal under Bot > Privileged Gateway Intents:

| Intent | Required | Enabled |
|--------|----------|---------|
| `MESSAGE_CONTENT` | YES | Must be ON |
| `GUILDS` | YES | Default on |
| `GUILD_MESSAGES` | YES | Default on |
| `PRESENCE` | NO | Not needed |
| `MEMBERS` | NO | Not needed |

### 3. Bot Permissions

OBAI uses permission integer `311452617792` (set during invite):

| Permission | Status | Purpose |
|------------|--------|---------|
| View Channels | YES | See public channels |
| Send Messages | YES | Post in channels |
| Send Messages in Threads | YES | Post in threads |
| Create Public Threads | YES | Future thread creation |
| Embed Links | YES | Structured embeds |
| Attach Files | YES | Screenshots, diagrams |
| Read Message History | YES | Context for responses |
| Add Reactions | YES | Acknowledgment signals |
| Use External Emojis | YES | Visual indicators |
| Use Slash Commands | YES | Future slash support |
| Administrator | NO | Never |
| Manage Channels/Roles/Server | NO | Never |
| Kick/Ban | NO | Never |
| Manage Messages | NO | Never |

### 4. Startup Command

```bash
# From repo root
export OBAI_BOT="<token-from-env-or-1password>"
python -m modules.communication.obai_discord_bot.src.obai_discord_bot
```

### 5. Expected Startup Logs

```
2026-04-09 12:00:00 INFO     obai_discord_bot — [OBAI] Starting OBAI Discord bot...
2026-04-09 12:00:01 INFO     obai_discord_bot — [OBAI] Connected as OBAI#1234 (ID: 1127122752776699915)
2026-04-09 12:00:01 INFO     obai_discord_bot — [OBAI] Guild: FOUNDUPS (ID: 412646632992014336) — 42 channels
2026-04-09 12:00:01 INFO     obai_discord_bot — [OBAI] Activity set: Watching FOUNDUPS threads
```

### 6. Smoke-Check Procedure

1. **Verify online**: In Discord, check member list — OBAI should show online with "Watching FOUNDUPS threads" status
2. **Test mention**: In any public channel, type `@OBAI help me` — should get `[OBAI] I'm the FOUNDUPS community helper bot...` reply
3. **Test ignore**: Have another bot mention OBAI — should NOT reply
4. **Test DM**: DM the bot directly — should NOT reply (guild channels only)
5. **Test shutdown**: Ctrl+C the process — should log `[OBAI] Received shutdown signal.` and `[OBAI] Shutdown complete.`

### 7. Failure Checklist

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `Login failed` | Invalid token | Verify `OBAI_BOT` env var |
| `Target guild not found` | Bot not invited to configured guild | Re-invite with correct permissions |
| Bot online but no reply | MESSAGE_CONTENT intent disabled | Enable in Developer Portal |
| Bot replies in other guilds | No guild filter in Phase 1 | Expected — don't invite to other guilds |

---

## Architecture

- **Module**: `modules/communication/obai_discord_bot/`
- **Runtime**: Standalone process (not inside moltbot_bridge)
- **Identity**: OBAI (App ID `1127122752776699915`)
- **Permissions**: `311452617792` (helper-only, no admin)

## Related Specs

- `docs/OBAI_DISCORD_BOT_SPEC.md` (in this module) — full design including future phases
