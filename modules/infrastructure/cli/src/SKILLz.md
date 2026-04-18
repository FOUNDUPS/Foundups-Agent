---
name: openclaw_voice
description: Voice REPL for 0102 - STT/TTS with Cohere, Whisper, edge-tts degradation chains
version: 1.0_prototype
author: 0102
created: 2026-04-18
category: workflow
agents: [qwen, gemma]
primary_agent: qwen
intent_type: interface
promotion_state: prototype
pattern_fidelity_threshold: 0.85
evals: []
retirement_date: null
trigger:
  manual
---

# OpenClaw Voice

**Purpose**: Talk to 0102 with your headset. Voice REPL with graceful degradation chains for STT and TTS.

**Source**: `modules/infrastructure/cli/src/openclaw_voice.py`
**Lines**: 1655
**Category**: infrastructure

---

## What This Skill Does

STT chain: Cohere Transcribe (local, lazy) → faster-whisper (local) → Google (cloud)
TTS chain: edge-tts (neural) → pyttsx3 (local SAPI5) → print-only fallback

Env vars:
- `OPENCLAW_VOICE_DISABLE_COHERE_STT=1` - Skip Cohere
- `OPENCLAW_VOICE_DISABLE_WASAPI=1` - Disable WASAPI shared mode

---

## Execution

```bash
python -m modules.infrastructure.cli.src.openclaw_voice
python main.py --voice
```

---

## WRE Connection

- **Trigger**: `manual`
- **Agent**: qwen
- **Integration**: Partner (012 voice) → Principal (OpenClawDAE) → Associates (domain DAEs)

---

## Autonomy Test

Can N compute cycles complete without 012? **NO** - Voice interface requires human interaction by design.

---

*WSP Compliance*: WSP 73 (Partner/Principal/Associate), WSP 84 (Code Reuse), WSP 91 (Lazy singleton loading)
