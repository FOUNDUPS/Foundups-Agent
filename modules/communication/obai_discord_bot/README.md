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
| `OBAI_GUILD_ID` | NO | `412646632992014336` | FOUNDUPS server ID |
| `OBAI_LOG_LEVEL` | NO | `INFO` | Logging level |
| `OBAI_ENABLED` | NO | `true` | Master switch |

## What OBAI Does

- Connects to Discord gateway as OBAI bot identity
- Responds to @OBAI mentions with a short helper message
- Logs connection status and guild info on ready
- Shuts down gracefully on SIGINT/SIGTERM

## What OBAI Does NOT Do

- No admin actions (kick, ban, role management)
- No moderation (message deletion, thread management)
- No CABR scoring or verification
- No GitHub mutations
- No scheduled posting or auto-triage
- No LLM inference (Phase 1 is keyword-only)

## Architecture

- **Module**: `modules/communication/obai_discord_bot/`
- **Runtime**: Standalone process (not inside moltbot_bridge)
- **Identity**: OBAI (App ID `1127122752776699915`)
- **Permissions**: `311452617792` (helper-only, no admin)

## Related Specs

- `docs/OBAI_DISCORD_BOT_SPEC.md` (in this module)
