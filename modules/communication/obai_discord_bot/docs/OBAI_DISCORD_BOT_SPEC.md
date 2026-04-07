# OBAI Discord Bot Spec

**Status**: Canonical spec
**Owner**: 0102 (Worker R)
**Slice**: `OBAI_DISCORD_BOT_SPEC_PHASE1`
**Date**: 2026-04-07
**Parent**: obai_discord_bot module, Discord dual-bot architecture

---

## 1. Problem

OBAI exists as a Discord application with scoped permissions (no admin), but no code process is running behind it. The bot appears offline. Science Swarm has 5 seeded research threads in #swarm-work with zero participants because no agent can join or post in them.

The moltbot_bridge module is webhook-based — it receives messages FROM OpenClaw Gateway via HTTP POST, not directly from Discord. There is no discord.py Client, no gateway connection, no event handlers. The `DISCORD_0102_BOT_TOKEN` in `moltbot.json` is consumed by the OpenClaw Gateway (Node.js), not by the Python service.

OBAI needs a Discord gateway bot — a running Python process that connects to Discord directly, can join threads, post structured messages, and observe channel activity.

**Architect call**: OBAI first (not 0102). OBAI is the safer first live bot for Science Swarm threads. 0102 stays privileged/admin, not the first general thread participant.

---

## 2. What OBAI Is and Is Not

### OBAI IS

- A community-facing helper bot
- An explainer of contribution paths, CABR, participation, GitHub-first workflow
- A thread participant that can observe, structure inputs, and report
- A router that helps people find the right channel, repo, or workflow
- A relay for GitHub events and structured notifications

### OBAI IS NOT

- A live CABR scoring engine (scoring pipeline does not exist yet)
- A verification authority (3V pipeline is spec-only)
- An admin bot (no kick/ban/role management/server settings)
- A replacement for 0102 (0102 is the privileged operator surface)
- A general chatbot (scoped to FoundUps domain knowledge)

**Boundary rule**: OBAI must never claim authority it does not have. If a user asks "what's my CABR score?" — OBAI says "CABR scoring is not live yet. Here's how it will work: [link to spec]." It does not fabricate numbers.

---

## 3. Architecture Decision: Standalone Gateway Bot

### Why Not Adapt moltbot_bridge

| Factor | moltbot_bridge | Standalone OBAI bot |
|--------|---------------|-------------------|
| Discord connection | None — receives webhooks from Node.js OpenClaw Gateway | Direct discord.py gateway connection |
| Dependencies | fastapi, uvicorn (HTTP server) | discord.py (WebSocket client) |
| Runtime model | Passive — waits for POST | Active — listens to Discord events |
| Token used | FOUNDUPS_WEBHOOK_TOKEN (shared secret) | OBAI bot token (Discord auth) |
| Thread participation | Cannot — webhook receiver doesn't know about threads | Native — discord.py Thread API |

**Decision**: Standalone discord.py bot in its own module. Not an adaptation of moltbot_bridge's webhook receiver.

**Location**: `modules/communication/obai_discord_bot/src/obai_discord_bot.py`

**Why a new module, not moltbot_bridge**: moltbot_bridge is 0102's runtime — its config says "You are 0102", its INTERFACE.md describes OpenClawDAE, its token is 0102's token. Grafting OBAI into that runtime would violate the dual-bot identity boundary and create a permission confusion surface (0102 is ADMINISTRATOR; OBAI must never be). A separate module enforces identity and permission isolation at the process level.

### Future Bridge Points

The standalone bot can later be wired to:
- **OpenClaw DAE** (`openclaw_dae.py`) for intent classification and WRE-backed responses
- **Signal filter pipeline** (CABR engagement tracking) for reading Discord activity
- **GitHub event relay** for posting PR/issue notifications from webhook payloads
- **moltbot_bridge webhook receiver** for receiving structured commands via HTTP

These are NOT Phase 1. Phase 1 is: connect, join threads, post structured messages, respond to mentions.

---

## 4. Component Design

### 4.1 Core Class

```python
class OBAIDiscordBot:
    """
    OBAI Discord gateway bot — community helper for FOUNDUPS.

    Non-admin, non-scoring, non-verification.
    Observes, explains, routes, reports.
    """

    def __init__(
        self,
        token: str,              # OBAI_BOT env var
        guild_id: int,           # 412646632992014336
        allowed_channels: list,  # Channel IDs OBAI can post in
    ): ...

    async def start(self) -> None:
        """Connect to Discord gateway and begin listening."""

    async def stop(self) -> None:
        """Graceful disconnect."""

    # Event handlers
    async def on_ready(self) -> None:
        """Log connection, set status/activity."""

    async def on_message(self, message) -> None:
        """Handle mentions and commands in allowed channels."""

    async def on_thread_create(self, thread) -> None:
        """Auto-join new threads in watched channels."""
```

### 4.2 Intents

```python
intents = discord.Intents.default()
intents.message_content = True    # Read message content (privileged, enabled in portal)
intents.guilds = True             # Guild/channel info
intents.guild_messages = True     # Receive message events
```

Presence and Members intents are NOT needed for OBAI (those are for 0102).

### 4.3 Thread Participation Model

OBAI participates in threads in two ways:

**A. Auto-join on creation** — When a new thread is created in a watched channel (e.g., #swarm-work), OBAI automatically joins it. This ensures the bot is present when agents or humans start discussing.

```python
WATCHED_CHANNELS = [
    # #swarm-work — Science Swarm research threads
    int(os.getenv("OBAI_SWARM_WORK_CHANNEL_ID", "0")),
]

async def on_thread_create(self, thread):
    if thread.parent_id in self.watched_channels:
        await thread.join()
        logger.info(f"[OBAI] Joined thread: {thread.name}")
```

**B. Mention-triggered response** — When mentioned (`@OBAI`) in any allowed channel or thread, OBAI responds with contextual help.

```python
async def on_message(self, message):
    if self.user.mentioned_in(message):
        await self.handle_mention(message)
```

### 4.4 Structured Message Format

OBAI posts structured embeds, not raw text. This makes bot messages visually distinct from human messages.

```python
embed = discord.Embed(
    title="Thread: PQN Threshold Proof",
    description="This thread investigates convergence bounds...",
    color=0x7c5cfc,  # FoundUPS purple
)
embed.add_field(name="Repo", value="[science-swarm-hub](https://github.com/FOUNDUPS/science-swarm-hub)")
embed.add_field(name="Expected Output", value="Formal proof or counterexample → GitHub PR")
embed.set_footer(text="OBAI — FoundUPS Helper | Not a scoring authority")
```

**Footer rule**: Every OBAI embed includes the disclaimer footer. This prevents authority confusion.

### 4.5 Mention/Route Rules

When mentioned, OBAI classifies the request and responds:

| Intent | Response |
|--------|----------|
| "how do I contribute?" | Links to CONTRIBUTING.md, Discord thread model, GitHub-first workflow |
| "what is CABR?" | Explanation from WSP 29 spec + link + "not live yet" disclaimer |
| "where do I file a bug?" | Link to relevant repo's issues page |
| "what's happening in [FoundUp]?" | Summary of recent thread activity in that FoundUp's channels |
| Unrecognized | "I'm not sure how to help with that. Try asking in #swarm-general or check the wiki." |

**Phase 1 intent classification**: Simple keyword matching. No LLM inference. No OpenClaw routing. Keep it dumb and reliable.

```python
ROUTES = {
    "contribute": "Here's how to contribute: ...",
    "cabr": "CABR is the Consensus-Driven Autonomous Benefit Rate...",
    "bug": "File bugs at: https://github.com/FOUNDUPS/{repo}/issues",
    "help": "I can help with: contribute, cabr, bug, thread, repo",
}
```

### 4.6 Activity Status

OBAI displays a status message indicating it's a helper:

```python
await bot.change_presence(
    activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="FOUNDUPS threads"
    )
)
```

---

## 5. Environment Variables

```bash
# Required
OBAI_BOT=                          # OBAI bot token (in .env)

# Defaults (can override)
OBAI_GUILD_ID=412646632992014336   # FOUNDUPS server
OBAI_ENABLED=false                 # Master switch (default off until tested)

# Channel IDs (watched for auto-join)
OBAI_SWARM_WORK_CHANNEL_ID=       # #swarm-work — set after lookup
```

---

## 6. Permissions Model (Server-Side)

OBAI's Discord permissions (set during invite, integer `311452617792`):

| Permission | Granted | Purpose |
|------------|---------|---------|
| View Channels | YES | See public channels |
| Send Messages | YES | Post in channels |
| Send Messages in Threads | YES | Post in threads |
| Create Public Threads | YES | Create threads if needed |
| Embed Links | YES | Structured embeds |
| Attach Files | YES | Screenshots, diagrams |
| Read Message History | YES | Context for responses |
| Add Reactions | YES | Acknowledgment signals |
| Use External Emojis | YES | Visual indicators |
| Use Slash Commands | YES | Future slash command support |
| Change Nickname | YES | Self-rename per context |
| Administrator | NO | Never |
| Manage Channels/Roles/Server | NO | Never |
| Kick/Ban | NO | Never |
| Manage Messages | NO | Never — cannot delete others' messages |

### Channel Access

| Channel Category | OBAI Access | Rationale |
|-----------------|-------------|-----------|
| SCIENCE SWARM HUB | Read + Post | Primary workspace |
| FoundUp channels (#autopost-*, #swarm-*, etc.) | Read + Post | Help routing |
| Community (#general, #introductions, etc.) | Read + Post | Onboarding help |
| OPERATOR (#mod-room, #operator-log) | NO | Admin-only |
| ARCHIVE | NO | Dead channels |

---

## 7. What OBAI Does NOT Do in Phase 1

1. **No LLM inference** — keyword routing only. No OpenClaw, no Qwen, no Gemma.
2. **No CABR scoring** — explains the concept, does not compute scores.
3. **No verification authority** — cannot mark tasks as verified, cannot approve PRs.
4. **No role management** — cannot assign @swarm-contributor or any other role.
5. **No DM responses** — guild-only. Does not respond to DMs.
6. **No slash commands** — Phase 1 is mention-based only. Slash commands are Phase 2.
7. **No cross-server** — FOUNDUPS guild only.
8. **No message deletion** — cannot and should not delete others' messages.
9. **No admin escalation** — if an admin action is needed, OBAI says "ask an Operator."

---

## 8. Integration with Existing Systems

### 8.1 Where It Lives

```
modules/communication/obai_discord_bot/
  README.md
  INTERFACE.md
  ModLog.md
  requirements.txt
  src/
    __init__.py
    obai_discord_bot.py         ← Discord gateway bot
  tests/
    __init__.py
    test_obai_discord_bot.py
  docs/
    OBAI_DISCORD_BOT_SPEC.md   ← THIS FILE
```

### 8.2 Relationship to OpenClaw Gateway

The OpenClaw Gateway (Node.js) currently handles Discord → webhook routing for the OpenClaw chat interface. OBAI is a **separate bot with a separate token** — it does not go through the OpenClaw Gateway.

```
Current:
  Discord user → OpenClaw Gateway (Node.js) → webhook → openclaw_dae.py

OBAI (new):
  Discord user → @OBAI mention → obai_discord_bot.py → keyword response

Future:
  Discord user → @OBAI mention → obai_discord_bot.py → openclaw_dae.py → WRE response
```

Phase 1 is the middle path — direct keyword responses. Phase 2+ wires OBAI to OpenClaw for LLM-backed responses.

### 8.3 Relationship to Signal Filter Pipeline

The CABR signal filter spec (DISCORD_GITHUB_TO_CABR_SIGNAL_FILTER.md) defines Discord events as inputs to the participation scoring system. OBAI's `on_message` handler sees all messages in channels it has access to — it's a natural collection point for the signal filter.

**Phase 1**: OBAI does NOT collect signals. It's a helper, not a data pipeline.
**Future**: OBAI's event stream feeds `signal_filter.py` for Un participation scoring.

---

## 9. Current Repo State

| Component | Status | Evidence |
|-----------|--------|----------|
| OBAI Discord application | LIVE | App ID `1127122752776699915`, in FOUNDUPS server |
| OBAI bot token | SET | In `.env` (env var name TBD — verify) |
| OBAI server permissions | CORRECT | `311452617792` — no admin, helper-only |
| moltbot_bridge module | LIVE | webhook_receiver.py, openclaw_dae.py |
| obai_discord_bot.py | DOES NOT EXIST | This spec defines it |
| discord.py dependency | NOT INSTALLED | Need to add to requirements.txt |
| Thread auto-join | DOES NOT EXIST | This spec defines it |
| Keyword routing | DOES NOT EXIST | This spec defines it |

---

## 10. Dependencies

### New Python Dependencies

Add to `modules/communication/moltbot_bridge/requirements.txt`:

```
discord.py>=2.3.0    # Discord gateway bot
```

PyNaCl is NOT needed (OBAI does not use voice).

### System Dependencies

None beyond what's already installed.

---

## 11. Implementation Order

### Layer 1 — Bot Skeleton + Connect
- Create `obai_discord_bot.py`
- Connect to Discord gateway with OBAI token
- Set activity status ("Watching FOUNDUPS threads")
- Log `on_ready` with guild and channel info
- Test: OBAI appears online in member list

### Layer 2 — Thread Auto-Join
- Auto-join new threads in watched channels (#swarm-work)
- Join existing threads on startup
- Test: create thread in #swarm-work → OBAI joins automatically

### Layer 3 — Mention Response
- Respond to @OBAI mentions with keyword routing
- Structured embeds with footer disclaimer
- Fallback for unrecognized requests
- Test: mention OBAI with "how do I contribute?" → get structured response

### Layer 4 — Channel Routing
- Help users find the right channel/repo/workflow
- Link to relevant docs, issues pages, wiki
- Test: mention OBAI with "where do I file a bug?" → get repo link

### Layer 5 — CLI Integration
- Add start/stop/status commands to CLI menu
- Integrate with broadcaster-style health monitoring
- Test: start OBAI from CLI → bot goes online

Each layer is tested independently. Each layer is a single PR.

---

## 12. Non-Goals

- No LLM inference in Phase 1
- No CABR scoring
- No admin actions
- No OpenClaw routing (Phase 2)
- No signal filter collection (future)
- No slash commands (Phase 2)
- No DM handling
- No voice channel participation (that's antifaFM Radio's job)

---

*Inspected moltbot_bridge module (webhook_receiver.py, openclaw_dae.py, moltbot.json, requirements.txt). Confirmed no Discord gateway code exists. Confirmed OBAI application live in server with scoped permissions. Designed standalone gateway bot with keyword routing, thread auto-join, and structured embeds. Preserved boundary: OBAI explains but does not score, verify, or administer.*
