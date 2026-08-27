# WRE Core Roadmap

## WRE master orchestrator decomposition

Execution-truth hardening extracted registry-bound executor dispatch, local
proposal inference, production admission/scanner policy, and legacy support
plugins into focused modules. The inherited coordinator fell from 1,814 to
a substantially smaller compatibility host and remains below the canonical
Python hard limit without a candidate-authored exemption. Exact current size is
verified mechanically by WSP 62 rather than frozen into roadmap prose.

Continue parity-proven decomposition in later focused slices:

- extract outcome recording and continuity breadcrumbs from
  `_execute_skill_once` (250 lines; inherited debt reduced from 329);
- extract the ReAct retry controller (113 lines; inherited debt reduced from
  122);
- extract candidate proposal construction/storage from `evolve_skill` (108
  lines; inherited debt reduced from 123);
- extract constructor configuration blocks (`__init__`, 88 lines; inherited
  debt reduced from 93);
- separate selection, evolution proposals, and telemetry;
- keep every new module/function below WSP 62 thresholds.

## Execution-truth P0 follow-ons

- implement an authenticated independent outcome evaluator;
- implement durable proposer/verifier/promoter separation and signed receipts;
- bind a generation-current read-only Holo owner adapter before re-enabling
  any generic pre-execution retrieval;
- bring CodeAct under exact WSP 95 registry, scanner receipt, captured bytes,
  typed effect receipts, and independent verification before enabling it;
- bind A/B candidates to immutable runtime artifacts before re-enabling traffic;
- build governed artifact activation and rollback without query-time Holo writes;
- prove a production end-to-end RSI canary before describing WRE as production RSI;
- add typed admission-failure audit storage without conflating it with successful
  PatternMemory outcomes.
- replace process-global PatternMemory/cache mutation with per-work-item
  connections or serialized transaction ownership before concurrent multi-agent
  execution; `check_same_thread=False` is not a concurrency proof;
- bind shared in-process admission caches to an explicit synchronization and
  bounded-eviction contract before one RedDog process serves many FoundUps.

## Code-health composition

The deterministic WSP 62 admission layer is proposal-only and intentionally
has no runtime caller. Compose it without widening authority:

- persist one immutable, module-grouped health-review packet for bounded
  no-baseline debt samples;
- obtain RedDog architect `FIX`/`DEFER`/`REJECT` determinations with canonical
  numeric WSP 15 C/I/D/Impact scores and exact allowed paths;
- convert only authenticated `FIX` determinations to the existing signed work
  order, preserving producer-to-verifier lineage;
- route through exact typed AgentDB/OpenClaw/Hermes workers and require
  independent diff/test/effect evidence before a draft PR;
- keep Nemotron, Qwen, Gemma, AutoResearch, and PatternMemory advisory until
  deterministic admission and independent verification accept their outputs;
- add incremental exact-changed-file FMAS scanning and bounded caching. The
  tracked-only producer reduced the live scan to 471 findings / 16.3 seconds,
  but that is still too expensive per prompt or per worker;
- replace the qualitative `WSP15Priority` compatibility object with a real
  signed numeric WSP 15 allocation receipt at the architect boundary.

Dead/orphan/duplicate evidence is a separate lane. Current legacy detectors
are not deletion authorities; first build one receipt-bound import/entrypoint/
runtime/registry/Git evidence graph and held-out false-positive corpus, then
perform WSP 79 preservation before archive or consolidation.

## Autonomous slice verifier decomposition

Decompose `wre_autonomous_slice_verifier_runtime.py` without weakening its
independent authority, evidence, exact-SHA, or receipt-chain checks. The
temporary exact no-growth exemption remains a ceiling, not permission to add
logic to the inherited coordinator.

## FoundUp job router and consumer WSP62 decomposition

The create-route prerequisite now isolates its routing decision in
`src/foundup_job_route_decision.py`; every function in that module and the
public `route_foundup_job` entrypoint is at or below 75 lines.

Remaining inherited WSP 62 debt is recorded with exact, non-ratcheting
ceilings in `wsp_62_exemptions.yaml`:

- Split envelope, evidence-reference, live-mode, and compute-budget validation
  out of `src/foundup_job_router.py`.
- Split Hermes dispatch, dry-run context attachment, and queue-retention
  orchestration out of `src/foundup_job_consumer.py`.
- Remove each function exemption when its extracted replacement is at or below
  75 lines, then remove the file exemption when the host is at or below the
  canonical file threshold.

Target: complete the decomposition before the temporary exemptions expire on
2026-09-30, without widening any recorded ceiling.

## FoundUp model-capability projection follow-up

Phase 1 projects existing route and runtime-binding authority into
`validate_foundup` only. Build and extract profiles intentionally keep all
capability requirements unspecified, and no consumer selection or binding
path has been added.

Before expanding consumption beyond validation:

- designate a production authority for modality, tool, structured-output,
  reasoning, selection-mode, and panel-limit requirements;
- define the selection-receipt handoff without letting a projection select,
  bind, call a provider, or mutate catalog/runtime state;
- add action-specific admission tests and preserve exact receipt lineage;
- keep `model_preference` limited to cost-class intent.

The injected runtime-binding resolver remains a trust anchor. A production
adapter must read the persisted result of the existing outside-repository
confined artifact-supply workflow. Detecting a malicious resolver that returns
a different self-consistent receipt requires a separately authorized
provenance/signature contract and is outside Phase 1.

## WRE documentation archival

`README.md` and `INTERFACE.md` now describe current truth below the Markdown
threshold. `ModLog.md` and `tests/TestModLog.md` remain required append-only
audit histories under non-blocking archival advisories. Archive them through an
approved retention workflow without losing lineage.
