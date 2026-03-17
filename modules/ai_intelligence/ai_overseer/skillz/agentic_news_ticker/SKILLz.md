---
name: agentic_news_ticker
description: Autonomous news aggregation for antifaFM stream ticker
version: 1.0_prototype
author: 0102
created: 2026-03-18
agents: [qwen]
primary_agent: qwen
intent_type: GENERATION
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: workflow
evals: []
trigger:
  cadence: 30min
---
# Agentic News Ticker Skill

## Overview
Autonomous news aggregation for antifaFM stream ticker. Fetches real-time news every 30 minutes and updates the ticker headlines.

## Functionality

### News Sources
1. **Web Search** - DuckDuckGo/Serper for breaking news
2. **News Categories**:
   - Labor movements / unions
   - Anti-fascist actions
   - Community organizing
   - Progressive politics
   - Climate activism
   - Mutual aid networks

### Update Cycle
- **Frequency**: Every 30 minutes
- **Headlines per update**: 5-8
- **Format**: Short, punchy, ticker-friendly (< 80 chars)

### Pipeline
```
1. Web Search (MCP web_search_news)
   ↓
2. AI Filter (Qwen - relevance scoring)
   ↓
3. AI Format (Qwen - ticker formatting)
   ↓
4. Write to headlines.json
   ↓
5. OBS ticker auto-reloads
```

## Invocation

```python
from ai_overseer.skillz.agentic_news_ticker import AgenticNewsTicker

ticker = AgenticNewsTicker()
await ticker.update_headlines()  # One-time update
await ticker.run_daemon()        # Continuous 30-min updates
```

## CLI

```bash
# One-time update
python -m ai_overseer.skillz.agentic_news_ticker.executor --update

# Run daemon (every 30 min)
python -m ai_overseer.skillz.agentic_news_ticker.executor --daemon

# Add custom headline
python -m ai_overseer.skillz.agentic_news_ticker.executor --add "Breaking: Workers win!"
```

## Configuration

```yaml
# Environment variables
AGENTIC_TICKER_INTERVAL: 1800  # 30 minutes in seconds
AGENTIC_TICKER_HEADLINES: 6    # Number of headlines to keep
AGENTIC_TICKER_TOPICS: "labor,union,antifa,protest,mutual aid,climate"
```

## WSP Compliance
- WSP 27: DAE Architecture (Phase 1 - sensor/actuator)
- WSP 77: Agent Coordination (Qwen for filtering)
- WSP 91: Observability (update logging)
