---
name: yumori-moshpit
description: Route and order YUMORI campaign activity versus 0102 agent-learning events. Use for Moshpit updates, campaign activity logging, and monk timeline maintenance.
---

# YUMORI Moshpit

Canonical instructions: `modules/foundups/esingularity/skills/yumori-moshpit/SKILL.md`.

Apply that file as the source of truth. Preserve the strict split:

- YUMORI Moshpit = campaign/monk history, reverse chronological within each JST day.
- 0102 Moshpit = agent mistakes, repairs, learning and RED DOG candidates.

For interval events, sort by completion/end time. Never let internal agent bookkeeping outrank the latest monk/campaign activity.


## PR lifecycle

0102 owns bounded skill PRs through exact-head checks and review, then squash-merges to main and verifies the merge. Routine GitHub mechanics are not handed to 012; escalate only genuine human decisions or permission blockers.
