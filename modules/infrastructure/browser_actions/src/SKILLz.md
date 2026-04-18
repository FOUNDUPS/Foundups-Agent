---
name: linkedin_actions
description: Vision-based LinkedIn engagement using UI-TARS for intelligent post reading and contextual replies
version: 1.0_prototype
author: 0102
created: 2026-04-18
category: workflow
agents: [qwen, gemma]
primary_agent: qwen
intent_type: engagement
promotion_state: prototype
pattern_fidelity_threshold: 0.85
evals: []
retirement_date: null
trigger:
  manual
---

# LinkedIn Actions

**Purpose**: Vision-based LinkedIn engagement for 0102 autonomy. Uses UI-TARS Vision for reading posts, intelligent reply decisions, and contextual engagement.

**Source**: `modules/infrastructure/browser_actions/src/linkedin_actions.py`
**Lines**: 2827
**Category**: infrastructure

---

## What This Skill Does

All engagement actions use UI-TARS Vision for:
- Reading and understanding posts
- Intelligent reply decisions
- Contextual engagement
- Dynamic UI handling

Selenium only for: navigation, login (known forms)

---

## Execution

```bash
python -c "from modules.infrastructure.browser_actions.src.linkedin_actions import LinkedInActions; print('Ready')"
```

---

## WRE Connection

- **Trigger**: `manual`
- **Agent**: qwen
- **Integration**: ActionRouter for Selenium/Vision routing

---

## Autonomy Test

Can N compute cycles complete without 012? **PARTIAL** - Requires browser session and login credentials, but engagement logic is autonomous.

---

*WSP Compliance*: WSP 3 (Infrastructure domain), WSP 77 (AI Overseer integration), WSP 80 (DAE coordination)
