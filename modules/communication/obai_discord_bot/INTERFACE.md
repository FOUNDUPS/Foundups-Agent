# OBAI Discord Bot — Interface

## Runtime Entry

```python
from modules.communication.obai_discord_bot.src.obai_discord_bot import (
    OBAIDiscordBot,
    OBAIConfig,
    load_config,
)

# Load config from environment
config = load_config()

# Create and run bot
bot = OBAIDiscordBot(config)
await bot.start()   # connects to Discord gateway
await bot.stop()    # graceful disconnect
```

## OBAIConfig

```python
@dataclass
class OBAIConfig:
    token: str               # OBAI bot token (from OBAI_BOT env var)
    guild_id: int            # Target guild (default: 412646632992014336)
    log_level: str           # Logging level (default: INFO)
    enabled: bool            # Master switch (default: True)
```

## OBAIDiscordBot

```python
class OBAIDiscordBot:
    async def start(self) -> None      # Connect and run (blocks until closed)
    async def stop(self) -> None       # Graceful disconnect
    def is_connected(self) -> bool     # True if gateway is ready
    def get_status(self) -> dict       # Status dict for monitoring
```

### get_status() Response

```python
{
    "connected": True,                          # Gateway ready
    "enabled": True,                            # Master switch
    "guild_id": 412646632992014336,            # Target guild
    "bot_user": "OBAI#1234",                   # Bot identity
    "started_at": "2026-04-09T12:00:00+00:00"  # ISO timestamp
}
```

## Events Handled

| Event | Current Behavior |
|-------|------------------|
| `on_ready` | Log bot user, guild, channel count. Set activity status "Watching FOUNDUPS threads". |
| `on_message` | If bot is mentioned (not @everyone, not bot, not DM), reply with generic HELP_TEXT. |

### Events NOT Handled (Spec-Only)

| Event | Spec Reference |
|-------|----------------|
| `on_thread_create` | Designed in spec (Layer 2), not implemented |
| Keyword routing | Designed in spec (Layer 3), not implemented |
| Slash commands | Phase 2 |

## Discord Intents Required

```python
intents = discord.Intents.default()
intents.message_content = True    # REQUIRED — privileged, must enable in portal
intents.guilds = True             # Default on
intents.guild_messages = True     # Default on
```

## Environment Variables

| Variable | Required | Default |
|----------|----------|---------|
| `OBAI_BOT` | YES | — |
| `OBAI_GUILD_ID` | NO | `412646632992014336` |
| `OBAI_LOG_LEVEL` | NO | `INFO` |
| `OBAI_ENABLED` | NO | `true` |

## WSP Compliance

- WSP 49: Standard module structure
- WSP 72: Module independence (no moltbot_bridge coupling)
- WSP 91: Observability (structured logging)
- WSP 97: Internal module boundaries respected
