# AmIBot Autonomous Build Package

Status: planning package in repository knowledge. It is not a runtime receipt and does not by itself authorize dispatch, merge, deployment, token activation, or external effects.

## Operator boundary

012 interacts with Red Dog. 012 supplies intent, corrections, strategic boundaries, and observations. 012 is not expected to research, author the package, edit JSON, prioritize tickets, select agents, or manage implementation details.

0102 owns the machine-side work: retrieve repository truth, research, apply WSP 15, construct and maintain the package, route admitted work through existing owners, synthesize verification, update repository knowledge, and prepare the FoundUps public surface.

This preserves the intended flow:

`012 -> Red Dog -> 0102/WRE -> admitted workers -> independent verifier -> evidence -> 0102 -> Red Dog -> 012`

A conversation is intent/context; an admitted work order and receipt chain are execution evidence.

AmIBot is registered as the existing `detect_ai` skeleton candidate, hidden and
SPECIFIED_NOT_IMPLEMENTED. Its declarative manifest and interface satisfy the
onboarding metadata layer. The package still has 13 planning orders and
`dispatchable=false`; registration does not complete G0 or admit a build worker.

## Restaurant/order model

The JSON package is the planning order rail. Each row records a role, candidate owner/retrieval roots, dependencies, WSP 15 score, phase, deliverables and acceptance criteria. Its `paths` are not executable allowlists. Before dispatch, compile a WSP 99 packet with exact allowed/denied files, invariants, outputs, tests and fail conditions, then obtain current WRE/AgentDB admission. The architect reconciles shared contracts; workers stay within admitted scope.

WSP 15 is used exactly as defined: Complexity + Importance + Deferability/urgency + Impact, with canonical P0-P4 ranges. It orders eligible work; it does not create execution authority.

## Parallel production plan

- G0: preflight and current-source authority.
- G1 after G0: conservatively serialize A04 -> A03 -> A02 -> A05 -> A06. All five share `modules/foundups/detect_ai`; G0 must first freeze shared session/safety/round contracts and resolve hard prerequisites. WSP 15 ordering is provisional, never an override of a functional dependency.
- G2: real human-human clean-chat integration, explicitly waiting for all five G1 orders.
- G3: randomized human-or-AI detection integration.
- G4: real iPhone/Android PWA acceptance.
- G5: independent security/privacy/benchmark verification.
- G6: authorized FoundUps.com POC publication, then final success report including publication disposition. Provisional telemetry is continuous; on any blocked/failed stage, the coordinator records controlled-failure evidence without waiting for downstream success-only jobs or falsely completing them.
- Deferred: mature/18+ research. It does not block the clean POC.

## Scope qualification — 2026-09-21

At main `e3753a65267e4223369c0eecd65dc32e3fa6b499`, static literal-root analysis found ten overlapping G1 pairs and twelve unordered active pairs across the full success DAG. Six dependency rows are corrected; the revised DAG is acyclic with zero unordered literal-root overlaps. All 13 IDs, WSP 15 scores, source roots and deliverables are preserved. Deferred mature research is excluded from active scheduling. This verifies planning consistency, not glob/OS isolation or actual worker execution.

Phase labels supply neither barriers nor concurrency permission. Parallelism can return after independently qualifying disjoint writes, including tests, documents and generated artifacts, and reconciling integration dependencies. The existing Hermes `WorkspaceBinding` checks one job; AgentDB claims bind tasks, and FoundUp `SwarmCoordinator` file claims are simulated exact-file claims. None establishes package-wide root exclusion. Reuse those owners when qualifying actual packets; this change adds no scheduler or validator module.

The onboarding Skillz and `create_foundup_dryrun.py` describe new identity scaffolding. An otherwise valid new-scaffold request for already registered `detect_ai` fails `FAIL_FOUNDUP_ID_EXISTS`. Preserve that identity and existing artifacts. `build_foundup` is the existing-module candidate action in `foundup_job_contract.py`, subject to its own readiness/admission gates; no `FoundUpJob` is constructed here. Controlled-failure reporting above is a coordinator contract, not an implemented failure-event consumer.

## Existing-module build route — 2026-09-21

Source base: main `1571ec5528bf2f1a8e34ebc6046fc78397ec4da7`. Qualification is
source/test-contract review, not a running-PC or end-to-end execution result.

| Existing owner | What current source establishes | Remaining boundary |
|---|---|---|
| `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py` | `build_foundup` returns genesis/lifecycle readiness; separate commander-authorized intent handling queues a typed job | Neither result is worker execution or AmIBot package compilation |
| `modules/infrastructure/wre_core/run_wre.py::cmd_drain` and `modules/infrastructure/wre_core/src/foundup_job_consumer.py` | Existing CLI drain consumes the OpenClaw queue through the router | No CLI/queue was invoked here; source availability is not a running service |
| `modules/infrastructure/wre_core/src/foundup_job_router.py` | `build_foundup` selects `HERMES_BUILDER` after route checks | A backend label is not a functioning product builder |
| `modules/infrastructure/wre_core/src/foundup_job_consumer.py::_dispatch_to_hermes` | Imports WRE `execute_foundup_job`, not the older agent executor | Current model-capability consumer admission applies only to `validate_foundup`; build/extract requirements remain unspecified |
| `modules/infrastructure/wre_core/src/hermes_job_executor.py` | Fresh singleton defaults to dry-run; only guard-admitted dry/disabled paths simulate. Unqualified build/extract can block first; live delegation remains blocked. Controlled adapter mode records interface proof with no live call | A configured executable/model/runtime and independently verified confined writer are still required; flags or runtime upgrades alone cannot provide them |
| `modules/foundups/agent/src/hermes_foundup_job_executor.py` | Older `build_foundup` branch calls extraction; existing test mocks that extraction | Not the current WRE consumer target; do not delete, consolidate or route AmIBot into it based on the shared name |
| `modules/infrastructure/wre_core/src/foundup_job_consumer.py::_attach_context_bundle_dry_run` | Existing dry branch attaches read-only ContextBundle preview with readiness false | Component wiring is implemented; its positive seam test uses validation, not live AmIBot authoring |

The surrounding WRE executor writes evidence even for simulated/blocked results;
a future local test must bind disposable evidence/workspace roots before imports.
A dry-run label is not an OS sandbox or a no-write guarantee.

The existing consumer test named `test_wre_executor_uses_singleton_dry_run`
patches `execute_foundup_job`; it checks invocation, not the singleton's policy.
Consumer documentation promises forced dry-run, while the convenience function
reuses a previously configured singleton. Qualify fresh and warmed instances,
consumer/job flag combinations and blocked-effect evidence in the existing test
owner before a minimal policy repair. Do not weaken the promise or enable a live
path merely to make tests pass. No such behavioral test ran in this qualification.

G0 remains blocked for live authoring. Reuse the existing consumer/executor,
model-capability contracts, typed M2M packet owners and independent verifier;
resolve their action-specific requirements and admission before any worker.
Current source proofs do not grant any missing authority. Preserve the13-order
planning DAG and registered `detect_ai`; no new scaffold, builder or domain.

## RSI decision

AmIBot is a strong controlled RSI/autonomous-build test, not because the system should be given unconstrained authority, but because the FoundUp is early-stage, scoped, reversible, measurable and has explicit tests. The existing RSI production-line contract already calls for admitted tickets, bounded workers, evidence synthesis and independent verification. OpenClaw supervises admitted execution; Hermes handles bounded leaf work when its profile is accepted; WRE/AgentDB retain work and process authority.

The experiment should measure more than whether AmIBot launches. Record: planning-to-delivery latency, worker retries, merge conflicts, duplicated work avoided, validation failures caught before promotion, model/tool cost, amount of 0102 intervention, and reusable launch procedures discovered. The result should improve the FoundUp-launch machinery only when independently verified.

## Public surface

The package requests `https://foundups.com/f/amibot`. Canonical identity remains
`detect_ai`, so WSP 104 declares `/f/detect_ai` and `idb_detect_ai`. The current shell
uses exact ID lookup; the requested public name requires its owner's reconciliation
before publication. Neither address is activated by registration. No new domain
or second FoundUp is needed. A route declaration is not a deployed page.

## Machine source

Canonical machine-readable package: `AMIBOT_AUTONOMOUS_BUILD_PACKAGE.json` in this directory.

Related product evidence remains in the module: WSP 109 intake, ROADMAP, RESEARCH, CHAT_PWA_SAFETY_RESEARCH, BENCHMARK_CONTRACT and ModLog. This package points at them; it does not duplicate their detailed research.
