"""
OBAI Discord Bot — standalone community helper for FOUNDUPS.

Phase 1 Layer 1: Gateway connect, ready event, basic mention reply.

OBAI is a non-admin helper bot. It explains, observes, routes, and responds.
It is NOT 0102. They are separate identities, separate tokens, separate runtimes.

Identity boundary:
    - No admin actions (kick, ban, role management)
    - No moderation (message deletion, thread management)
    - No CABR scoring or verification
    - No GitHub mutations
    - No scheduled posting or auto-triage

Usage:
    python -m modules.communication.obai_discord_bot.src.obai_discord_bot
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone

import discord

logger = logging.getLogger("obai_discord_bot")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FOUNDUPS_GUILD_ID = 412646632992014336


@dataclass
class OBAIConfig:
    """Configuration for OBAI Discord bot, loaded from environment."""

    token: str = ""
    guild_id: int = FOUNDUPS_GUILD_ID
    log_level: str = "INFO"
    enabled: bool = True


def load_config() -> OBAIConfig:
    """Load OBAI config from environment variables.

    Env vars:
        OBAI_BOT           — Bot token (required)
        OBAI_GUILD_ID      — Target guild ID (default: FOUNDUPS server)
        OBAI_LOG_LEVEL     — Logging level (default: INFO)
        OBAI_ENABLED       — Master switch (default: true)

    Returns:
        OBAIConfig with validated fields.

    Raises:
        SystemExit if token is missing and enabled is True.
    """
    token = os.environ.get("OBAI_BOT", "").strip()
    guild_id_str = os.environ.get("OBAI_GUILD_ID", str(FOUNDUPS_GUILD_ID)).strip()
    log_level = os.environ.get("OBAI_LOG_LEVEL", "INFO").strip().upper()
    enabled_str = os.environ.get("OBAI_ENABLED", "true").strip().lower()

    try:
        guild_id = int(guild_id_str)
    except ValueError:
        logger.error("[OBAI] Invalid OBAI_GUILD_ID: %r — must be an integer", guild_id_str)
        sys.exit(1)

    enabled = enabled_str in ("true", "1", "yes", "on")

    if enabled and not token:
        logger.error("[OBAI] OBAI_BOT env var is not set. Cannot start without a bot token.")
        sys.exit(1)

    return OBAIConfig(
        token=token,
        guild_id=guild_id,
        log_level=log_level,
        enabled=enabled,
    )


# ---------------------------------------------------------------------------
# Bot
# ---------------------------------------------------------------------------

HELP_TEXT = (
    "[OBAI] I'm the FOUNDUPS community helper bot.\n\n"
    "I can help with:\n"
    "- **Contribution paths** — how to get involved\n"
    "- **Science Swarm** — thread model, repos, workflows\n"
    "- **Navigation** — finding the right channel, repo, or doc\n\n"
    "Mention me with a question and I'll do my best.\n"
    "For operator actions, please contact a server operator."
)


class OBAIDiscordBot:
    """OBAI Discord gateway bot — community helper for FOUNDUPS.

    Non-admin, non-scoring, non-verification.
    Observes, explains, routes, responds.
    """

    def __init__(self, config: OBAIConfig) -> None:
        self.config = config
        self._started_at: datetime | None = None

        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True

        self._client = discord.Client(intents=intents)

        # Register event handlers
        self._client.event(self.on_ready)
        self._client.event(self.on_message)

    # -- Lifecycle -----------------------------------------------------------

    async def start(self) -> None:
        """Connect to Discord gateway and begin listening."""
        if not self.config.enabled:
            logger.info("[OBAI] Bot is disabled (OBAI_ENABLED=false). Not starting.")
            return

        logger.info("[OBAI] Starting OBAI Discord bot...")
        self._started_at = datetime.now(timezone.utc)
        await self._client.start(self.config.token)

    async def stop(self) -> None:
        """Graceful disconnect from Discord gateway."""
        logger.info("[OBAI] Shutting down OBAI Discord bot...")
        if not self._client.is_closed():
            await self._client.close()
        logger.info("[OBAI] Shutdown complete.")

    def is_connected(self) -> bool:
        """Check if the bot is connected and ready."""
        return self._client.is_ready() and not self._client.is_closed()

    def get_status(self) -> dict:
        """Return status dict for monitoring/health checks."""
        return {
            "connected": self.is_connected(),
            "enabled": self.config.enabled,
            "guild_id": self.config.guild_id,
            "bot_user": str(self._client.user) if self._client.user else None,
            "started_at": self._started_at.isoformat() if self._started_at else None,
        }

    # -- Events --------------------------------------------------------------

    async def on_ready(self) -> None:
        """Log connection details and set activity status."""
        bot_user = self._client.user
        logger.info("[OBAI] Connected as %s (ID: %s)", bot_user, bot_user.id if bot_user else "?")

        target_guild = self._client.get_guild(self.config.guild_id)
        if target_guild:
            logger.info(
                "[OBAI] Guild: %s (ID: %s) — %d channels",
                target_guild.name,
                target_guild.id,
                len(target_guild.channels),
            )
        else:
            logger.warning(
                "[OBAI] Target guild %d not found. Bot may not have been invited.",
                self.config.guild_id,
            )

        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="FOUNDUPS threads",
        )
        await self._client.change_presence(activity=activity)
        logger.info("[OBAI] Activity set: Watching FOUNDUPS threads")

    async def on_message(self, message: discord.Message) -> None:
        """Respond to @OBAI mentions with helper text."""
        # Never respond to own messages
        if message.author == self._client.user:
            return

        # Never respond to other bots
        if message.author.bot:
            return

        # Only respond when directly mentioned
        if not self._client.user or not self._client.user.mentioned_in(message):
            return

        # Ignore @everyone/@here mentions (not direct mentions)
        if message.mention_everyone:
            return

        logger.info(
            "[OBAI] Mentioned by %s in #%s: %s",
            message.author,
            getattr(message.channel, "name", "DM"),
            message.content[:100],
        )

        # Do not respond to DMs
        if isinstance(message.channel, discord.DMChannel):
            return

        await message.reply(HELP_TEXT)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def _setup_logging(level: str) -> None:
    """Configure logging for OBAI bot."""
    numeric_level = getattr(logging, level, logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def _run() -> None:
    """Main async entry: load config, create bot, run with signal handling."""
    config = load_config()
    _setup_logging(config.log_level)

    if not config.enabled:
        logger.info("[OBAI] Bot is disabled. Exiting.")
        return

    bot = OBAIDiscordBot(config)

    loop = asyncio.get_running_loop()

    def _signal_handler() -> None:
        logger.info("[OBAI] Received shutdown signal.")
        asyncio.ensure_future(bot.stop())

    # Register signal handlers (Unix-style; on Windows these may not fire
    # for all signals, but SIGINT from Ctrl+C works)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler for all signals
            signal.signal(sig, lambda s, f: _signal_handler())

    try:
        await bot.start()
    except discord.LoginFailure:
        logger.error("[OBAI] Login failed — check OBAI_BOT token.")
        sys.exit(1)
    except Exception:
        logger.exception("[OBAI] Unexpected error during bot lifecycle.")
        sys.exit(1)
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(_run())
