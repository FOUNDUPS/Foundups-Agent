# Installing OpenClaw (Digital Twin Gateway)

> **OpenClaw** is the current name (formerly Moltbot/Clawdbot - rebranded Jan 2026)

## Prerequisites

### 1. WSL2 with Ubuntu

```powershell
# From PowerShell (Admin)
wsl --install -d Ubuntu-24.04
```

### 2. Supported Node.js INSIDE WSL

> [!CAUTION]
> **Critical**: Node.js must be installed **inside WSL**, not just on Windows.
> Using Windows npm causes `node: not found` errors when running OpenClaw.

```bash
# Current supported floors: Node 22.22.3+, 24.15+, or 25.9+.
# The official local-prefix installer provisions a compatible runtime.
curl -fsSL https://openclaw.ai/install-cli.sh | bash -s -- --no-onboard
```

---

## Installation

```bash
# Inside WSL; onboarding is a separate operator/configuration step.
~/.openclaw/bin/openclaw --version
~/.openclaw/bin/openclaw onboard

# Stable executable used by the Foundups-Agent advisory probe
sudo ln -sfn "$HOME/.openclaw/bin/openclaw" /usr/local/bin/openclaw
```

Install Hermes with its official installer, verify it, and expose the stable
probe path without granting it Foundups-Agent execution authority:

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
~/.hermes/hermes-agent/venv/bin/hermes --version
sudo ln -sfn "$HOME/.hermes/hermes-agent/venv/bin/hermes" /usr/local/bin/hermes
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
