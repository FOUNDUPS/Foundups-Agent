# External Capability Learning — proposed RSI Skillz

**Status:** PROPOSED / DOCUMENTATION ONLY — no runtime, account, credential, trial, or worker activation.
**Owner:** WRE Skillz / WSP_48 recursive self-improvement. **Principal:** 012. **Coordinator:** 0102.
**Date:** 2026-11-14. **Candidate pilot:** Enjoy.dev seven-day trial.

## Intent and boundary

FoundUps is designed as an agent-operated autonomous system: 0102 coordinates qualified Codex, Hermes, OpenClaw and other workers; Play FoundUps/RedDog interfaces are optional observation, approval and intervention surfaces, **not mandatory steps in the execution chain**. Do not build a second orchestrator or require 012 to manually shuttle tickets between agents.

Make external tool learning a reusable RSI workflow: discover useful products and open-source repositories; compare with actual WSP/WRE/AgentDB/Skillz/HoloIndex/PatternMemory code; obtain explicitly authorized access; run bounded experiments; extract **original transferable skills and mechanisms**, not proprietary source; implement through existing owners; independently verify; retain; and prove benefit on a later task. Rejecting an unsuitable tool is a valid result. This proposal is not an assertion that these integrations currently work.

## Governance and source of truth

- Bootstrap through **WSP_00** (0102 identity, role, origin, lifecycle), then **WSP_97 v1.10** (retrieve protocols and repository evidence; micro/macro analysis, dialectic, first principles; independent acceptance; exact-SHA and post-merge verification). **WSP_15** prioritizes bounded work; **WSP_48** qualifies *measured later-use improvement*; **WSP_95** governs Skillz admission/promotion; **WSP_110** governs reconciliation/closure. Respect WSP_50/77, existing WRE admission/security, and M2M WSP_99 contracts where applicable.
- Canonical anchors: `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md`; `WSP_framework/src/WSP_48_Recursive_Self_Improvement_Protocol.md`; `modules/infrastructure/wre_core/ROADMAP.md`; `docs/architecture/REDDOG_HYBRID_TICKET_SWARM_FEEDBACK_MODEL.md`; `docs/operations/RSI_SWARM_DISPATCH.md`; `docs/roadmaps/R24_AGENT_PRODUCTION_LINE_PACKET.md`; `modules/foundups/docs/BUILD_PLAN_SWARM_WRE_QUEUE_CONTRACT.md`; `modules/foundups/docs/BUILD_PLAN_SWARM_COORDINATION_CONTRACT.md`.
- Existing Skillz promotion policy explicitly describes unimplemented promotion/rollback; never treat documentation or a skill file as permission to promote itself. HoloIndex retrieves; AgentDB retains ticket state; PatternMemory admits evidence-backed reusable outcomes; none independently grants execution authority.
- Never let a worker be its own independent verifier. Preserve acceptance criteria, rollback, audit records, cost caps, expiry, cancellation, least privilege, and fail-closed handling.

## Proposed ticket lifecycle

`DISCOVERED -> INVENTORIED -> GAP_REVIEWED -> ACCESS_PENDING -> AUTHORIZED -> SANDBOX_RUNNING -> CANDIDATE_CAPTURED -> IMPLEMENTED -> INDEPENDENTLY_VERIFIED -> RETAINED -> LATER_USE_MEASURED -> CLOSED`

Other terminal states: `REJECTED`, `EXPIRED`, `BLOCKED`, `REVOKED`. An experiment can close without a promoted skill. Separate **tool behavior observed**, **candidate skill drafted**, **code executed**, **result independently verified**, **merged/main verified**, **deployed**, and **benefit demonstrated**.

Each durable experiment record should contain: ticket ID, tool/vendor/version, capability hypothesis, upstream sources and licenses/terms, existing owner and code paths, gap classification (IMPLEMENTED/TESTED_ONLY/SPECIFIED/BLOCKED/UNKNOWN), approval and account owner, scope/permissions, sandbox and allowed effects, access/trial start and expiry, cancellation/revocation plan, costs and renewal policy, agent/provider route, immutable artifacts and evidence refs, candidate skill version, acceptance tests, independent verifier, source/PR/main SHAs, measured later-use benefit and exclusions.

## Acquisition and security

0102 may discover and recommend accounts; account creation, OAuth consent, financial commitments and trial-to-paid renewal require the appropriate 012 approval and provider terms. Never silently sign up, impersonate the user, circumvent trial limits, scrape protected code, copy proprietary assets, expose production credentials, or use an unrelated user's data. Prefer publicly documented interfaces, permitted black-box experiments, and properly licensed open-source components. Use isolated test repos and synthetic fixtures. Record revocation/expiry and prevent surprise billing. Access automation must be separately authorized and actually connected; Codex web control is not assumed to exist from a ChatGPT chat.

## Enjoy.dev pilot — seven-day research, not seven-day guarantee of automation

1. Inventory Enjoy features and trial terms; compare against existing FoundUps rather than assume every feature is necessary.
2. Inspect observable agent creation, routing, delegation and permissions.
3. Test bounded concurrent sessions, file ownership and isolated worktrees.
4. Test session persistence, crash recovery, retry/cancellation and cross-agent handoffs.
5. Test scheduling, health/usage telemetry, remote observation and approval paths.
6. Reconcile with WRE, WSP, Codex, Hermes, OpenClaw, RedDog and Play FoundUps; document exact code paths, tests, missing edges, and licensing constraints.
7. Implement **one** smallest justified improvement in a sandbox, independently verify and prepare a later-use evaluation.

Open-source research candidates: Gas City/Gas Town (durable work/dependency ledger), Superset (parallel agent/worktree operator patterns; review license), Sandcastle (sandbox patterns; review license), OpenCode (replaceable coding worker), Vibe Kanban (task/worktree management). These are **candidates**, not approved dependencies or verified superior implementations.

## Known blockers — do not paper over them

- `modules/foundups/agent/src/build_plan_swarm_queue.py` explicitly labels its WRE queue simulated, without real worker dequeue.
- Swarm coordination contract labels real parallel execution not implemented.
- RedDog hybrid ticket/team integration is specified but not end-to-end proven.
- Current WRE roadmap (2026-11-01) identifies protected native requester/lease-consumption gap (Native19/P0); local differential testing does not prove authenticated native execution or WSP_48 transfer.
- Earlier OpenClaw/Hermes audit showed queue creation without worker execution; **recheck current source and runtime**, not historical claims.
- Live Codex/Hermes account bindings, permissions, provider routing, cancellation, receipts, exact-main CI and conversation persistence require independent qualification.

**First implementation prerequisite:** trace `012 intent -> 0102 -> governed ticket -> WRE admission -> qualified worker -> actual execution -> independent verifier -> receipt -> retained memory` and identify the first failing edge using current evidence. Prove one real authorized worker end-to-end before optional swarm expansion.

## Acceptance and learning proof

Baseline and candidate must use equivalent tasks, safety/quality gates, independent tests and recorded costs. A skill candidate is not a promoted skill. Prove later reuse on a distinct held-out task and compare accepted outcome quality, elapsed time, total compute/cost, retries and regressions. No result is accepted solely from an agent's self-report, successful tool call, PR creation, or documentation.

## Proposed bounded implementation packets

- **S0** audit code owners, tests, real wiring and current Native19/P0 blocker; no mutation.
- **S1** add durable external-capability experiment ticket/schema only by extending existing owner; approval/expiry/revocation modeled and tested.
- **S2** connect one authenticated worker to one isolated permitted experiment with cancellation and receipts.
- **S3** skill candidate extraction with provenance/license checks and independent evaluation.
- **S4** retention and held-out later-use measurement via existing Skillz/PatternMemory authority.
- **S5** optional Play FoundUps status/approval tile; never a required execution hop.

Each packet requires WSP_15 priority, frozen acceptance, exact source/tests, owner, evidence, rollback, and WSP_97/WSP_110 closure. Avoid wholesale rewrites and duplicate schedulers, stores, model routers or self-authorizing promoters.

## Handoff / next action

Read this proposal alongside canonical current WSP/WRE documentation. Perform a read-only, evidence-linked audit and choose the smallest integration gap. Do not activate an Enjoy trial or change runtime from this file. Preserve this proposal as a candidate until reviewed and admitted.
