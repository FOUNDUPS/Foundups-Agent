# OpenRouter Client

Unified LLM routing via [OpenRouter](https://openrouter.ai) with fallback support for the FoundUps Agent.

## Overview

OpenRouter provides a single API to access 200+ LLM models from multiple providers:
- **Anthropic**: Claude Sonnet 4, Claude Opus 4, Claude Haiku
- **OpenAI**: GPT-4o, GPT-4 Turbo
- **Meta**: Llama 3.1 (70B, 8B)
- **Mistral**: Mistral Large, Mixtral
- **Google**: Gemini Pro

## Quick Start

```python
from modules.infrastructure.openrouter_client import OpenRouterClient, openrouter_chat

# Using the class
client = OpenRouterClient()
response = client.chat_completion(
    user_message="Explain quantum computing in simple terms",
    system_prompt="You are a helpful teacher.",
    model="sonnet",  # Alias for anthropic/claude-sonnet-4
)

if response.ok:
    print(response.content)
    print(f"Cost: ${response.cost:.4f}")
    print(f"Tokens: {response.prompt_tokens} + {response.completion_tokens}")

# Quick function
response = openrouter_chat("Hello!", model="gpt4")
```

## Configuration

Set in `.env`:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_DEFAULT_MODEL=anthropic/claude-sonnet-4
OPENROUTER_PRESET=foundups-agent
OPENROUTER_FALLBACK_ENABLED=true
OPENROUTER_WEB_SEARCH=false
OPENROUTER_TIMEOUT_SEC=60
```

## Model Aliases

| Alias | Full Model ID |
|-------|---------------|
| `sonnet` | `anthropic/claude-sonnet-4` |
| `claude` | `anthropic/claude-sonnet-4` |
| `opus` | `anthropic/claude-opus-4` |
| `haiku` | `anthropic/claude-3.5-haiku` |
| `gpt4` | `openai/gpt-4o` |
| `llama` | `meta-llama/llama-3.1-70b-instruct` |
| `mistral` | `mistralai/mistral-large` |
| `gemini` | `google/gemini-pro-1.5` |

## Features

### Web Search Plugin

Enable web search for grounded responses:

```python
response = client.chat_completion(
    user_message="What happened in tech news today?",
    web_search=True,
)
```

### Preset Support

Uses the `@preset/foundups-agent` preset configured on OpenRouter dashboard:
- Temperature: 0.3
- Max tokens: 4096
- Models: Claude Sonnet 4, GPT-4o, Llama 3.1 70B

### Health Checks

```python
ok, detail = client.health()
print(f"OpenRouter: {'OK' if ok else 'DOWN'} - {detail}")

# Startup probe with remediation
probe = client.startup_probe()
if not probe["ok"]:
    print("Remediation:", probe["remediation"])
```

## Integration Points

- **OpenClaw fallback**: When local Qwen/Gemma models fail
- **IronClaw fallback**: When IronClaw gateway is unavailable
- **Direct usage**: Any module needing LLM capabilities

## WSP References

- WSP 3: Module Organization (infrastructure domain)
- WSP 49: Module Structure
- WSP 50: Pre-Action Verification
