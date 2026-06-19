# YouTube Shorts Scheduler Skills

This directory contains AI skills for the youtube_shorts_scheduler module following WSP 95 (WRE Skills Wardrobe Protocol).

## Available Skills

| Skill | Intent Type | Agent | Status |
|-------|-------------|-------|--------|
| `ffcpln_title_enhance` | GENERATION | Qwen + Gemma | prototype |
| `gemma_content_type_classifier` | CLASSIFICATION | Gemma + Qwen | prototype |
| `what_should_i_schedule` | PRIORITIZATION | Gemma + Qwen | prototype |

### what_should_i_schedule

Read-only channel scheduling-priority ranking. Answers "which channel should I schedule
next?" by ranking the shorts-enabled channels by scheduling NEED (empty/under-target
upcoming days => HIGH priority). FOR THE AGENT (WRE/daemon triggers it; `--agent-command`
invokes it) -- 012 only observes the emitted breadcrumb + PatternMemory outcome. Reads the
persisted per-channel schedule tracker JSON; no browser, no live model, no mutation.

```bash
# agent / DAE invocation (structured JSON):
python main.py --agent-command "youtube action schedule_priority upcoming_days=7"
# spawns: python -m modules.platform_integration.youtube_shorts_scheduler.skillz.what_should_i_schedule.run_skill --upcoming-days 7 --json
```

## Architecture

```
skills/
├── ffcpln_title_enhance/     # FFCPLN clickbait title generation
│   ├── SKILL.md              # Instructions (WSP 95)
│   ├── executor.py           # Python implementation
│   └── tests/                # Unit tests
└── README.md                 # This file
```

## WSP 95 Compliance

Skills follow the micro chain-of-thought paradigm:
1. Qwen executes multi-step reasoning
2. Gemma validates each step
3. Pattern fidelity ≥ 90% required for production

## Usage

```python
from modules.platform_integration.youtube_shorts_scheduler.skills.ffcpln_title_enhance import FFCPLNTitleEnhanceSkill

skill = FFCPLNTitleEnhanceSkill()
result = skill.execute(context)
```
