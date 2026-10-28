# Prometheus M2M — WRE risk-based verification integration
Date: 2026-10-28. Status: **handoff only; implementation not authorized by this document alone**.
Repository: `FOUNDUPS/Foundups-Agent`. Execution mode: Codex / ChatGPT Work, with repository access.

## Mission
Integrate the existing risk-based test-impact planning and verifier evidence into the authorized WRE/RSI worker completion lifecycle without a new scheduler, memory store, or self-authorizing judge. Optimize verified improvement per unit of compute while preserving non-bypassable safety, security and release gates. Do not mistake CI queueing for a universal requirement to run all workflows on every agent change.

## Authoritative retrieval order
1. `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md` (active v1.10; completion rule), byte-compare `WSP_knowledge/src/WSP_97_System_Execution_Prompting_Protocol.md` (mirror, not separate authority).
2. `WSP_framework/src/WSP_48_Recursive_Self_Improvement_Protocol.md`, WSP 6, WSP 15, WSP 71, WSP 81, WSP 95; read the applicable WRE admission/authority contracts before runtime effects.
3. `docs/operations/RSI_SWARM_DISPATCH.md`, `docs/architecture/REDDOG_HYBRID_TICKET_SWARM_FEEDBACK_MODEL.md`, `docs/architecture/REDDOG_EPHEMERAL_AUTHORITY_WORKER_ROUTING.md`, `docs/roadmaps/R02_WSP_RSI_ENFORCEMENT_MAP.md`, `docs/roadmaps/R24_AGENT_PRODUCTION_LINE_PACKET.md`.
4. `modules/infrastructure/wre_core/src/wre_test_impact_differential_gate.py`, `wre_test_registry_impact_binding.py`, `wre_test_registry_scope_plan.py`, `wre_test_registry_differential_plan_runtime.py`, `wre_test_differential_runtime.py`, `wre_test_differential_verification.py`, `skill_execution_truth.py`; inspect corresponding tests and interfaces.
5. `modules/ai_intelligence/ai_gateway/README.md`, `INTERFACE.md`, `ROADMAP.md`; `modules/foundups/agent/src/swarm_dispatch_integration.py`; `modules/foundups/agent_market/src/task_pipeline.py`; HoloIndex retrieval and freshness contracts.
6. `modules/foundups/eduit/docs/TILE_PRODUCTION_RSI.md` and Storytime PRs #2244, #2245, #2246, #2247 as regression motivation, **not** global architecture owners.

## Verified architectural observations from source review
- WRE has deterministic impact classes `ISOLATED/MODULAR/SYSTEMIC` and test suite scopes `FOCUSED/MODULE_CLOSURE/DEPENDENCY_CLOSURE/FULL_REPOSITORY`. The registry projection produces an exact-SHA plan **without executing tests**.
- The differential runtime can execute verifier-owned parent/candidate pytest comparisons; planning, test execution, authenticated independent verification and promotion authority remain distinct.
- Stale dependency/HoloIndex evidence, protected authority changes, releases and periodic audits escalate scope to SYSTEMIC in the registry binding. Do not allow a model to downgrade those flags.
- WSP 97 owns task completion; WSP 48 owns demonstrated RSI transfer; WSP 71/admission owns authority; WRE Pattern Memory retains approved outcomes; HoloIndex/Brain/Memex provide retrieval/continuity, not authority.
- RedDog/WRE hybrid swarm and NVIDIA Nemotron candidate topology routing are described, but integrated native worker admission and autonomous transfer are not established. Do not claim that documentation activates either.
- GitHub Actions workflow success/failure and required branch protection must be discovered from current GitHub configuration. Empty statuses or missing workflow runs are UNKNOWN, not PASS.

## Execution tasks — smallest bounded slice
A. **Audit first:** produce a current-state table mapping each proposed edge (ticket -> impact plan -> test execution -> independent verification -> completion receipt -> memory -> future reuse) to exact source, tests, owner, live wiring evidence and gap. Classify IMPLEMENTED, TESTED_ONLY, SPECIFIED or BLOCKED. Inspect actual CI workflow triggers, required checks and change-path filters before proposing modifications.
B. **Design:** reuse existing impact-plan schemas and WRE admission/verification capability. Specify deterministic selection by changed paths, dependency closure, protected surfaces and risk; make policy versioned and auditable. Preserve fail-closed escalation on stale/missing evidence and no worker-controlled bypass. One economical worker is default; bounded teams are optional, not a second orchestration plane.
C. **Implement one narrow integration only if authorized by existing runtime authority:** bind exact-SHA impact plan to worker result and verifier-owned completion receipt. Separate local focused tests, pre-merge integration tests, post-merge exact-main checks, live-output verification and RSI promotion. Do not wire new autonomous dispatch, self-promotion or credential access merely to satisfy a planning task.
D. **Regression:** add deterministic tests for isolated/modular/systemic selection; protected/release/stale escalation; changed-path/dependency mismatch; omitted tests; missing/failed/pending CI; PR-head vs main-head mismatch; independent verifier spoofing; cancellation/retry/idempotency; and no downgrade on budget pressure. Include Storytime's `celebrating -> over` regression as an example, not a special-case global rule.
E. **Evidence and closure:** run scoped tests and required checks, inspect results, record compute/time where measurable, verify branch and final main SHA. Update the canonical WRE docs and module ModLog; WSP 97 Framework and Knowledge copies must remain byte-identical if changed. Create PR, inspect applicable checks, squash merge only under actual policy, and verify resulting main SHA. If blocked, leave explicit receipt and reason; never claim complete or silently bypass.

## Acceptance criteria
- No duplicate policy engine, queue, memory, model router or independent judge.
- Same changed paths + same verified policy inputs yield same test scope; mandatory gates cannot be weakened by a proposing model.
- The worker cannot certify its own acceptance or promote its own RSI result.
- Focused test selection saves work where safe; security/release/systemic closure remains mandatory.
- Evidence distinguishes PLAN, EXECUTED, INDEPENDENTLY_VERIFIED, MERGED, MAIN_CI_VERIFIED, DEPLOYED and TRANSFER_DEMONSTRATED.
- Independent reviewer validates actual outputs; benchmark efficiency only after equal safety/quality gates.
- No child gameplay telemetry, credentials or unrelated FoundUp data enter RSI memory.
- Deliver source-path diff, tests and logs, before/after compute measurements where available, blockers, PR URL, squash SHA and exact-main CI receipt.

## Operator instruction
Do not ask 012 to navigate PRs or run tests. Investigate and execute within authenticated authority. If authority or CI evidence is missing, document precise blocker and stop the affected operation. Keep the existing WSP 97 universal rule; optimize **selection and execution**, not the meaning of completion.
