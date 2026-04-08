# OpenClaw Channel Setup Guide

> Formerly "Moltbot Channel Setup Guide" - updated Jan 2026 for OpenClaw rebrand

## Prerequisites

- OpenClaw installed: `npm i -g openclaw && openclaw onboard`
- Config file: `~/.openclaw/openclaw.json`

---

## 1. WhatsApp (via Baileys)

**Requirement**: Separate phone number recommended (or use personal with caution)

### Setup Steps
1. Add to `openclaw.json`:
```json
{
  "channels": {
    "whatsapp": {
      "dmPolicy": "allowlist",
      "allowFrom": ["+81XXXXXXXXXX"]
    }
  }
}
```

2. Login via QR code:
```bash
openclaw channels login
```
- Scan with WhatsApp → Linked Devices

3. Start gateway:
```bash
openclaw start
```

---

## 2. Telegram (Bot API)

### Setup Steps
1. Create bot with [@BotFather](https://t.me/BotFather):
   - Send `/newbot`
   - Name: `FoundupsDigitalTwin`
   - Username: `FoundupsTwinBot` (must end in `bot`)
   - Copy the token

2. Set privacy (optional):
   - `/setprivacy` → Disable (to see group messages)
   - `/setjoingroups` → Enable

3. Add to `openclaw.json`:
```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
      "dmPolicy": "pairing",
      "groups": { "*": { "requireMention": true } }
    }
  }
}
```

4. Or set env: `TELEGRAM_BOT_TOKEN=123456789:ABCdefGHI...`

---

## 3. Discord (Bot API)

> **Full runbook**: See [DISCORD_OPERATOR_SURFACE.md](DISCORD_OPERATOR_SURFACE.md) for verified install flow, permissions, and troubleshooting.

### Setup Steps
1. Create app at [Discord Developer Portal](https://discord.com/developers/applications):
   - New Application → Name: `FoundupsDigitalTwin`
   - Bot → Add Bot → Copy Token

2. Enable **ALL THREE** Gateway Intents (Bot → Privileged Gateway Intents):
   - ✅ Presence Intent
   - ✅ Server Members Intent
   - ✅ Message Content Intent

3. Generate Invite URL (OAuth2 → URL Generator):
   - Scopes: `bot`, `applications.commands`
   - Permissions: View Channels, Send Messages, Read History, Embed Links, Attach Files, Add Reactions

4. Invite bot to your server using generated URL

> **OAuth Fix**: If Developer Portal shows `Install Link = None` and you see `"Integration requires code grant"`, use a direct OAuth URL:
> ```
> https://discord.com/oauth2/authorize?client_id=YOUR_APP_ID&scope=bot+applications.commands&permissions=YOUR_PERMS
> ```

5. Get IDs (enable Developer Mode in Discord settings):
   - Right-click server → Copy Server ID
   - Right-click channel → Copy Channel ID

6. Add to `openclaw.json`:
```json
{
  "channels": {
    "discord": {
      "enabled": true,
      "botToken": "${DISCORD_0102_BOT_TOKEN}",
      "guilds": {
        "YOUR_GUILD_ID": {
          "channels": ["CHANNEL_ID"],
          "requireMention": true
        }
      }
    }
  }
}
```

---

## 4. Voice (ElevenLabs Talk Mode)

### Setup Steps
1. Get ElevenLabs API key from [elevenlabs.io](https://elevenlabs.io)

2. Get/create Voice ID:
   - Use existing voice or clone 012's voice
   - Copy Voice ID from ElevenLabs dashboard

3. Add to `openclaw.json`:
```json
{
  "talk": {
    "voiceId": "YOUR_ELEVENLABS_VOICE_ID",
    "modelId": "eleven_v3",
    "apiKey": "${ELEVENLABS_API_KEY}",
    "interruptOnSpeech": true
  }
}
```

4. Or set env: `ELEVENLABS_API_KEY=...` and `ELEVENLABS_VOICE_ID=...`

5. Enable in macOS app: Menu bar → Talk

---

## Complete openclaw.json Example

```json
{
  "agent": {
    "model": "anthropic/claude-opus-4-5"
  },
  "agents": {
    "defaults": {
      "workspace": "O:/Foundups-Agent/modules/communication/moltbot_bridge/workspace",
      "repoRoot": "O:/Foundups-Agent"
    }
  },
  "channels": {
    "whatsapp": {
      "dmPolicy": "allowlist",
      "allowFrom": ["+81XXXXXXXXXX"]
    },
    "telegram": {
      "enabled": true,
      "botToken": "${TELEGRAM_BOT_TOKEN}",
      "dmPolicy": "pairing"
    },
    "discord": {
      "enabled": true,
      "botToken": "${DISCORD_0102_BOT_TOKEN}"
    }
  },
  "talk": {
    "voiceId": "${ELEVENLABS_VOICE_ID}",
    "apiKey": "${ELEVENLABS_API_KEY}",
    "modelId": "eleven_v3"
  },
  "skills": {
    "managed": ["foundups-wsp", "holo-search"]
  }
}
```

---

## Environment Variables

Add to `.env` or shell profile:

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHI...
DISCORD_0102_BOT_TOKEN=MTIz...
DISCORD_BOT_TOKEN=${DISCORD_0102_BOT_TOKEN}
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_VOICE_ID=...
FOUNDUPS_WEBHOOK_TOKEN=your-secret
```
