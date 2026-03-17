---
name: openclaw-automation
description: Query and control YouTube automation (scheduler, comments, streams)
user-invocable: true
command-dispatch: tool
command-tool: bash
command-arg-mode: raw
category: workflow
evals: []
---
# OpenClaw Automation Skill

Control and query the YouTube automation system (AutoModeratorDAE).

## Quick Status

Ask about automation status:
```
What's the scheduler status?
How many shorts are scheduled?
Any OOPS pages?
```

## Channel Control

Skip or resume channels:
```
Skip FoundUps for 2 hours
Resume Move2Japan
```

## Examples

| Question | Response |
|----------|----------|
| "scheduler status" | Shows cycle count, scheduled shorts, channel states |
| "skip foundups" | Pauses FoundUps channel for 1 hour |
| "oops pages" | Lists any channels with OOPS errors |
| "how many shorts" | Shows scheduled shorts per channel |

## Routes To

`auto_moderator_bridge.handle_automation_intent()` → AutoModeratorDAE
