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
    async def start(self) -> None
    async def stop(self) -> None
    def is_connected(self) -> bool
    def get_status(self) -> dict
```

## Events Handled

| Event | Behavior |
|-------|----------|
| `on_ready` | Log bot user, guild, channel count. Set activity status. |
| `on_message` | If bot is mentioned, reply with helper text. |

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
