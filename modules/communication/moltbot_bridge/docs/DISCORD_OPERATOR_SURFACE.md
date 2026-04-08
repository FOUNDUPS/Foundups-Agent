# Discord Operator Surface — 0102/OpenClaw

> Verified: 2026-04-09 | Worker AW | WSP 15/97

## Summary

This document defines the verified operator surface for the **0102 bot** in the FOUNDUPS Discord server, used by OpenClaw as its Discord channel presence.

---

## Bot Identity

| Property | Value |
|----------|-------|
| **Bot Name** | 0102 |
| **App ID** | `839968873851387944` |
| **Token Env Var** | `DISCORD_0102_BOT_TOKEN` (preferred) or `DISCORD_BOT_TOKEN` (legacy) |
| **Server (Guild)** | FOUNDUPS (`412646632992014336`) |

> **Note**: The 0102 bot is distinct from the OBAI helper bot. Do not conflate them.

---

## OAuth Install Flow

### The Problem

Discord's **Install Link** setting in Developer Portal defaults to `None`. When `None`:
- The "Add to Server" button in the application page shows an error:
- `"Integration requires code grant"`
- This blocks OAuth authorization flow entirely

### The Fix

Use either:

1. **Discord Provided Link** (set in Developer Portal → Installation → Install Link)
2. **Direct OAuth URL** with explicit scopes:

```
https://discord.com/oauth2/authorize?client_id=839968873851387944&scope=bot+applications.commands&permissions=<PERMISSION_INT>
```

### Verified Working URL

```
https://discord.com/oauth2/authorize?client_id=839968873851387944&scope=bot+applications.commands&permissions=8
```

Where:
- `scope=bot+applications.commands` — Required for bot presence + slash commands
- `permissions=8` — Administrator (current 0102 config; see below for minimum)

---

## Required Scopes

| Scope | Required | Purpose |
|-------|----------|---------|
| `bot` | **Yes** | Bot user presence in guild |
| `applications.commands` | **Yes** | Slash command registration |

---

## Required Intents

All three Privileged Gateway Intents must be **enabled** in Developer Portal:

| Intent | Required | Purpose |
|--------|----------|---------|
| **Presence Intent** | Yes | See member online status |
| **Server Members Intent** | Yes | Access member list, join/leave events |
| **Message Content Intent** | Yes | Read message text (non-slash) |

> Without Message Content Intent, OpenClaw cannot process non-slash DMs or mentions.

---

## Minimum Permissions

For **production operator use** (not admin):

| Permission | Bit | Purpose |
|------------|-----|---------|
| View Channels | `1024` | See channels |
| Send Messages | `2048` | Respond |
| Send Messages in Threads | `274877906944` | Thread replies |
| Embed Links | `16384` | Rich embeds |
| Attach Files | `32768` | File uploads |
| Read Message History | `65536` | Context |
| Add Reactions | `64` | Reactions |
| Use Slash Commands | `2147483648` | Slash commands |

**Minimum permission integer**: `2147558464` (without file/embed) or `2147614784` (with)

Current 0102 config uses **Administrator** (`8`) for operational simplicity during development.

---

## Runtime Boundary

### What 0102/OpenClaw Does Now (Verified)

| Capability | Status | Notes |
|------------|--------|-------|
| Bot presence in FOUNDUPS server | ✅ Verified | Online when OpenClaw gateway running |
| Receive webhook payloads | ✅ Verified | Via OpenClaw gateway → webhook_receiver |
| Respond to mentions | ✅ Verified | Requires Message Content Intent |
| Process DMs | ✅ Verified | OpenClaw gateway handles DM routing |

### What Is NOT Yet Implemented

| Feature | Status | Notes |
|---------|--------|-------|
| Slash commands | ❌ Not registered | No `/` commands deployed |
| Thread auto-create | ❌ Not implemented | Future operator surface |
| Reaction-based triggers | ❌ Not implemented | Future |
| Voice channel presence | ❌ Separate bot | antifaFM Radio bot handles voice |
| Server moderation | ❌ Not scoped | 0102 has perms but no mod logic |

---

## Channel/Thread Surface (Intended)

| Surface | Purpose | Status |
|---------|---------|--------|
| DMs to 0102 | Operator queries, OpenClaw routing | Verified |
| `#0102-lab` or similar | Dev/test channel for OpenClaw | TBD |
| Threads | Per-task context (future) | Not implemented |

> No specific channel binding is currently enforced. OpenClaw receives any message routed by the gateway.

---

## Environment Checklist

```bash
# Required
DISCORD_0102_BOT_TOKEN=<your-token>

# Legacy alias (for older OpenClaw gateway versions)
DISCORD_BOT_TOKEN=${DISCORD_0102_BOT_TOKEN}

# Webhook auth (for Foundups-Agent webhook receiver)
FOUNDUPS_WEBHOOK_TOKEN=<your-webhook-secret>
```

---

## Operator Runbook

### 1. Invite/Install Bot

If 0102 is not in the server or needs re-invite:

```
https://discord.com/oauth2/authorize?client_id=839968873851387944&scope=bot+applications.commands&permissions=8
```

Select the target server and authorize.

### 2. Verify Bot in Server

1. Check Discord server member list for `0102` bot
2. Bot should show "Online" when OpenClaw gateway is running
3. If offline, check gateway: `openclaw status` or `openclaw start`

### 3. Verify Gateway → Webhook

```bash
# Start OpenClaw gateway (in WSL)
openclaw start

# Check webhook receiver is up
curl -X GET http://127.0.0.1:18800/health
# Should return {"status": "ok"}
```

### 4. Smoke Test: DM the Bot

1. DM 0102 in Discord: `ping`
2. OpenClaw should respond (if gateway + webhook running)
3. Check logs: `openclaw logs` or `tail -f ~/.openclaw/logs/gateway.log`

### 5. Troubleshoot

| Symptom | Check |
|---------|-------|
| Bot offline | `openclaw start` in WSL |
| "Integration requires code grant" | Use direct OAuth URL (not Install Link = None) |
| Bot online but no response | Check webhook receiver: `curl http://127.0.0.1:18800/health` |
| Response in wrong channel | Check `openclaw.json` guild/channel config |

---

## Related Docs

- [CHANNEL_SETUP.md](CHANNEL_SETUP.md) — Multi-channel configuration
- [INSTALL_OPENCLAW.md](INSTALL_OPENCLAW.md) — Gateway installation
- [README.md](../README.md) — Module overview
- [INTERFACE.md](../INTERFACE.md) — Public API

---

## Version History

| Date | Change |
|------|--------|
| 2026-04-09 | Initial operator surface verification (Worker AW) |
