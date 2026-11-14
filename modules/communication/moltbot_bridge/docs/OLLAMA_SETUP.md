# OpenClaw Local Models (Ollama) Configuration

> [!TIP]
> Use Ollama for zero-cost local inference without API keys.

## Foundups fallback configuration

OpenClaw defaults to `qwen-overseer:latest`, for which
`models/Modelfile.qwen-overseer` supplies a definition. Its GGUF source is an
absolute machine-specific path: verify or adapt that path before creating the
model with `ollama create qwen-overseer -f models/Modelfile.qwen-overseer`.
Alternatively set `OPENCLAW_OLLAMA_MODEL` to an already installed model;
an explicitly blank setting disables this fallback. No model creation is
performed by OpenClaw's configuration change.

The chat request uses `OPENCLAW_OLLAMA_TIMEOUT_SEC` (default 120 seconds,
finite range 15–300). Blank, invalid and non-finite values fall back to 120.
This is a Requests connect/read timeout, not a total-response deadline;
synchronous waiting may delay cancellation until the existing post-call check.
A larger timeout does not establish cold-start readiness.

For operator-managed Windows storage, set `OLLAMA_MODELS` to a suitable existing
data volume before starting Ollama, and restart Ollama after changing it. The
preserved PC proposal used `E:\0102_Digital_Twin\models`; this path is an example,
not a portable requirement or a verified relocation in this slice.

## Ollama Setup

### 1. Install Ollama

**Windows** (native, no WSL needed for Ollama itself):
```powershell
winget install Ollama.Ollama
```

Or download from [ollama.ai](https://ollama.ai)

### 2. Pull a Model

```bash
# Recommended for coding tasks
ollama pull qwen2.5-coder:32b

# Or for general use
ollama pull llama3.1:70b
```

### 3. Start Ollama Server

```bash
ollama serve
# Runs on http://localhost:11434
```

---

## OpenClaw Configuration for Ollama

Add to `~/.openclaw/openclaw.json`:

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "ollama/qwen2.5-coder:32b"
      },
      "models": {
        "ollama/qwen2.5-coder:32b": { "alias": "Qwen Coder" }
      }
    }
  },
  "models": {
    "mode": "merge",
    "providers": {
      "ollama": {
        "baseUrl": "http://localhost:11434/v1",
        "apiKey": "ollama",
        "api": "openai-completions",
        "models": [
          {
            "id": "qwen2.5-coder:32b",
            "name": "Qwen 2.5 Coder 32B",
            "reasoning": false,
            "input": ["text"],
            "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
            "contextWindow": 32768,
            "maxTokens": 8192
          }
        ]
      }
    }
  }
}
```

---

## Hybrid: Ollama + Cloud Fallback

Use Ollama locally, fall back to Claude for complex tasks:

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "ollama/qwen2.5-coder:32b",
        "fallback": "anthropic/claude-sonnet-4"
      },
      "models": {
        "ollama/qwen2.5-coder:32b": { "alias": "Local" },
        "anthropic/claude-sonnet-4": { "alias": "Cloud" }
      }
    }
  }
}
```

---

## WSL + Ollama (Windows)

If running OpenClaw in WSL2, Ollama on Windows is accessible via:
```
http://host.docker.internal:11434/v1
```

Or get Windows IP:
```powershell
(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Ethernet").IPAddress
```

Then use that IP in WSL config:
```json
{
  "models": {
    "providers": {
      "ollama": {
        "baseUrl": "http://192.168.x.x:11434/v1"
      }
    }
  }
}
```

---

## Recommended Models for 012 Digital Twin

| Model | Size | Use Case |
|-------|------|----------|
| `qwen2.5-coder:32b` | ~20GB | Code generation, WSP development |
| `llama3.1:70b` | ~40GB | General reasoning |
| `deepseek-coder:33b` | ~20GB | Alternative for coding |
| `gemma2:27b` | ~16GB | Lighter weight option |

Choose based on your VRAM. 32B models need ~24GB VRAM or CPU offloading.
