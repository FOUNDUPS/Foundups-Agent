# Social Twin FoundUp Roadmap

## Current Phase
PoC architecture lock and contract definition.

## Objective
Ship a FoundUp that turns digital-twin social engagement into a reusable,
compute-backed product:

1. discover relevant social posts
2. queue them by priority
3. let a human review while mobile
4. approve bounded actions
5. execute through existing platform automation
6. schedule amplification and follow-up

## First-Principles Constraints
1. Human approval stays in the loop for all first-order mutations.
2. Control plane and action plane stay separated.
3. Existing platform executors are reused; no duplicate DOM stacks.
4. Ranking must be evidence-based and retrieval-backed, not generic social spam.
5. Product claims stop at app-layer/social-layer automation, not universal growth guarantees.

## Architecture Decision
Run one FoundUp with two core agent roles:

- `orchestrator_0102`: queue, reasoning, approval, routing
- `engager_0102`: deterministic execution and outcome logging

Do not treat them as two unrelated twins. They are two roles inside one FoundUp.

Optional later:
- `amplifier_0102`: likes, scheduled reposts, delayed rechecks

## Layered Delivery

### Layer 0 - Queue and Contracts
- Add opportunity queue contract and state machine.
- Add role topology contract.
- Add approval actions and follow-up actions.
- Exit:
  - typed queue items exist
  - two-role topology is stable

### Layer 1 - LinkedIn Morning Queue
- Scan LinkedIn feed for candidate posts.
- Rank candidates by alignment, author, recency, and risk.
- Persist queue for morning review.
- Exit:
  - operator can fetch `next` ranked opportunity
  - queue is resumable across sessions

### Layer 2 - OpenClaw Review Surface
- Route queue review through Discord or Telegram.
- Support commands:
  - `next`
  - `skip`
  - `rewrite`
  - `approve`
  - `reply as <entity>`
  - `followup 5d`
  - `followup 7d`
- Exit:
  - reviewed item can move from `queued` to `approved`

### Layer 3 - Execution Bridge
- Bridge approved actions into existing LinkedIn execution flow.
- Use `engager_0102` for reply/like/repost scheduling.
- Record outcome and failure reasons.
- Exit:
  - approved queue item executes end-to-end

### Layer 4 - Amplification and Follow-Up
- Add optional like/repost/revisit associates.
- Add 5-7 day thread recheck jobs.
- Add escalate-to-article path.
- Exit:
  - post lifecycle remains observable after the first reply

### Layer 5 - Productization
- Multi-tenant policy profiles
- compute budgeting
- channel packs per platform
- hosted review/operator surface

## Model Policy

### Orchestrator lane
- preferred: Qwen/OpenClaw/local-first
- optional stronger external model for high-value drafting
- responsible for ranking, routing, and draft refinement

### Engager lane
- preferred: deterministic DOM/API actions first
- model usage only for bounded draft regeneration or safety checks
- should remain small, observable, and fail-closed

## WSP 15 Priority Queue

### P0
1. FoundUp module skeleton and role contracts
2. LinkedIn opportunity queue contract
3. Queue ranking policy
4. Discord review path through OpenClaw
5. Approve-to-execute bridge into LinkedIn digital twin flow

### P1
1. Telegram review path
2. Amplifier role contract
3. Follow-up scheduling and thread revisit
4. Escalate-to-article path using publishing router

### P2
1. Multi-platform support beyond LinkedIn
2. Hosted operator UI / extension sidecar
3. Multi-tenant compute and billing policy

## Risks
- too much autonomy too early becomes spam and platform risk
- coupling ranking with execution makes failure diagnosis opaque
- remote phone/voice expectations exceed current local browser reality

## Current Recommendation
Build Discord/OpenClaw review first, not the extension first.
