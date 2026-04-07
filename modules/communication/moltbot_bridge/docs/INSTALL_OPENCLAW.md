# Installing OpenClaw (Digital Twin Gateway)

> **OpenClaw** is the current name (formerly Moltbot/Clawdbot - rebranded Jan 2026)

## Prerequisites

### 1. WSL2 with Ubuntu

```powershell
# From PowerShell (Admin)
wsl --install -d Ubuntu-24.04
```

### 2. Node.js 22+ INSIDE WSL

> [!CAUTION]
> **Critical**: Node.js must be installed **inside WSL**, not just on Windows.
> Using Windows npm causes `node: not found` errors when running OpenClaw.

```bash
# Inside WSL terminal
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify
node --version   # Should show v22.x.x
npm --version
```

---

## Installation

```bash
# Inside WSL
npm install -g openclaw
openclaw onboard
```

### Onboarding Wizard

The wizard will prompt for:
1. **LLM Provider**: Anthropic (Claude) or OpenAI
2. **API Key**: Your provider's API key
3. **Channels**: Discord, Telegram, WhatsApp, etc.
4. **Workspace**: Point to `O:/Foundups-Agent/modules/communication/moltbot_bridge/workspace`

---

## Configuration

### Config File Locations

| Version | Path |
|---------|------|
| OpenClaw (current) | `~/.openclaw/openclaw.json` |
| Moltbot (legacy) | `~/.clawdbot/moltbot.json` |

### Discord Setup

1. Create bot at [Discord Developer Portal](https://discord.com/developers/applications)
2. Enable **Message Content Intent**, **Server Members Intent**
3. Copy bot token
4. Add to config:

```json
{
  "channels": {
    "discord": {
      "enabled": true,
      "botToken": "${DISCORD_0102_BOT_TOKEN}"
    }
  }
}
```

Or set env:

```bash
export DISCORD_0102_BOT_TOKEN=your-token-here
export DISCORD_BOT_TOKEN="$DISCORD_0102_BOT_TOKEN"   # Legacy alias during transition
```

---

## Running OpenClaw

```bash
# Start gateway
openclaw start

# Interactive TUI
openclaw tui

# Channel login (WhatsApp QR, etc.)
openclaw channels login
```

---

## Linking Foundups Workspace

```bash
# Set workspace in config
openclaw config set agents.defaults.workspace /mnt/o/Foundups-Agent/modules/communication/moltbot_bridge/workspace

# Or symlink workspace files
mkdir -p ~/.openclaw/workspace
ln -sf /mnt/o/Foundups-Agent/modules/communication/moltbot_bridge/workspace/* ~/.openclaw/workspace/
```

---

## Troubleshooting

### `node: not found`
**Cause**: OpenClaw installed via Windows npm, but Node.js not in WSL PATH  
**Fix**: Install Node.js inside WSL (see Prerequisites)

### Bot shows offline in Discord
**Cause**: OpenClaw gateway not running  
**Fix**: Run `openclaw start` in WSL

### Config not loading
**Check paths**:
```bash
ls -la ~/.openclaw/
cat ~/.openclaw/openclaw.json
```

---

## Version History

| Date | Name | Package |
|------|------|---------|
| Jan 30, 2026 | OpenClaw | `openclaw` |
| Jan 27, 2026 | Moltbot | `moltbot` |
| Pre-2026 | Clawdbot | `clawdbot` |

Config migrates automatically between versions.
