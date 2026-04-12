---
name: foundups-edge-load-smoke
description: Tiny text-only skill to verify AI Edge Gallery loaded a FoundUps worker skill. Say LOAD_OK if the user says ping.
metadata:
  homepage: https://github.com/FOUNDUPS/Foundups-Agent/tree/main/modules/foundups/mobile_worker_skills/foundups-edge-load-smoke
---

# FoundUps Edge load smoke (worker)

## Role

You only confirm the skill file was loaded. **No** repo access, **no** JSON, **no** architecture.

## Instructions

1. If the user message is exactly `ping` (case-insensitive), reply with exactly: `LOAD_OK`
2. Otherwise reply with exactly: `WAITING_FOR_PING`

## Output

Plain text only — one line, no markdown fence.

## Example

**User:** `ping`  
**You:** `LOAD_OK`
