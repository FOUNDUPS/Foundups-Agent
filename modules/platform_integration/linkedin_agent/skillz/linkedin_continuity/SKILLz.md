---
name: linkedin_continuity
description: Resume and close LinkedIn jobs with verified private receipts, evidence-backed skill improvement and clean PR closure
version: 1.0.0
author: 0102
agents: [qwen]
intent_type: AUDIT
promotion_state: prototype
category: workflow
evals: []
---
# LinkedIn continuity and improvement

Read the [master routing contract](../../docs/LINKEDIN_ACTIVITY_ROUTING.md) and
the private receipt contract in [review workflow](../../docs/LINKEDIN_REVIEW_WORKFLOW.md).

At entry retrieve account-scoped state, source/target IDs, timestamps/timezones,
approval scope, last verified action and pending owner. Revalidate live state;
historical receipts do not prove present state. Resume an interrupted submission
with read-back, not a repeated send. Mark unknown when evidence is insufficient.

At close record coverage, each action and verification, holds, failures, drafts,
all requested publication lanes, exact next action/owner and relevant triggers.
Use the existing authorized private journal/Moshpit; if unavailable provide a
private handoff and explicitly report that durable continuity was not written.
Never put private messages, contact dossiers, credentials or raw transcripts in
public Git, reusable skills or campaign logs. Only material project outcomes
belong in that project's journal; generic LinkedIn telemetry stays separate.

Every run checks for an improvement: observation -> cause -> smallest reusable
correction -> acceptance case -> verify. A no-change finding is valid; do not edit
for its own sake or silently expand authority. Reuse the existing skill owner,
apply WSP 97 before structural changes and preserve narrow-command behavior.
For authorized repo changes: inspect current main and in-flight ownership, use a
dedicated branch/PR, test exact changed paths without live side effects, review
diff and check results, squash only when authorized and relevant gates pass.
Do not bypass failed checks; keep blocked work committed and report the blocker.
Verify merge and clean local tree. Never enable unattended jobs merely by writing
instructions or claiming a prototype is operational.

Report concisely: CONNECTIONS; MESSAGES; NEWSLETTERS (FoundUps/JHR/ROC);
OPENCLAW GROUP; ENGAGEMENT; OUTREACH; PUBLISHING; SYSTEM HEALTH; 012 ACTION
REQUIRED. Use actual counts and stages, including not checked. Escalate only
genuine decisions/authority gaps; do not re-request an unchanged exact approval.
