# OpenClaw Windows (WSL2) Installation Guide

> [!IMPORTANT]
> OpenClaw runs on Windows via **WSL2** (Windows Subsystem for Linux).
> The Gateway runs inside WSL, accessible from Windows.

## Quick Install

### Step 1: Install WSL2 + Ubuntu

Open PowerShell as Administrator:
```powershell
wsl --install -d Ubuntu-24.04
```

Restart your computer if prompted.

For a dedicated agent disk, move the stopped distribution with WSL itself so
its registration and virtual disk remain consistent:

```powershell
wsl --shutdown
wsl --manage Ubuntu-24.04 --move E:\Agents\WSL\Ubuntu-24.04
wsl --set-default Ubuntu-24.04
```

Foundups-Agent can verify that host binding at startup with:

```powershell
setx FOUNDUPS_AGENT_WSL_DISTRO Ubuntu-24.04
setx FOUNDUPS_AGENT_WSL_EXPECTED_BASE E:\Agents\WSL\Ubuntu-24.04
```

The version probe executes installed programs and is therefore opt-in for an
explicit maintenance run, not a resident authority check:

```powershell
$env:FOUNDUPS_AGENT_WSL_RUNTIME_ENABLED = '1'
python main.py
Remove-Item Env:FOUNDUPS_AGENT_WSL_RUNTIME_ENABLED
```

### Step 2: Enable systemd (Required for Gateway)

Inside WSL (Ubuntu terminal):
```bash
sudo tee /etc/wsl.conf > /dev/null <<'EOF'
[boot]
systemd=true
EOF
```

Then in PowerShell:
```powershell
wsl --shutdown
```

Restart WSL to apply.

### Step 3: Install OpenClaw and Hermes in WSL

```bash
curl -fsSL https://openclaw.ai/install-cli.sh | bash -s -- --no-onboard
~/.openclaw/bin/openclaw onboard
sudo ln -sfn "$HOME/.openclaw/bin/openclaw" /usr/local/bin/openclaw

curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
sudo ln -sfn "$HOME/.hermes/hermes-agent/venv/bin/hermes" /usr/local/bin/hermes
```

### Step 4: Start the OpenClaw Gateway

```bash
~/.openclaw/bin/openclaw start
```

---

## Accessing OpenClaw from Windows

The Gateway runs on `ws://127.0.0.1:18789` inside WSL.
WSL2 shares `localhost` with Windows, so you can access it directly.

## Configuration Location

```bash
# Inside WSL
~/.openclaw/openclaw.json

# From Windows (if needed)
\\wsl$\Ubuntu-24.04\home\<username>\.openclaw\openclaw.json
```

## What is WHATSAPP_ALLOWED_NUMBER?

WhatsApp uses an **allowlist** for security. Only phone numbers in `allowFrom` can message 012.

```json
{
  "channels": {
    "whatsapp": {
      "dmPolicy": "allowlist",
      "allowFrom": ["+81XXXXXXXXXX", "+1234567890"]
    }
  }
}
```

- `+81XXXXXXXXXX` - 012's personal WhatsApp number
- Add multiple numbers to allow family, team, etc.
- Use international format with `+` prefix

---

## WSL Tips

```powershell
# Enter WSL
wsl

# Probe the exact distro-bound OpenClaw runtime
wsl -d Ubuntu-24.04 --exec /usr/local/bin/openclaw --version

# Probe the exact distro-bound Hermes runtime
wsl -d Ubuntu-24.04 --exec /usr/local/bin/hermes --version

# Shutdown WSL
wsl --shutdown
```
