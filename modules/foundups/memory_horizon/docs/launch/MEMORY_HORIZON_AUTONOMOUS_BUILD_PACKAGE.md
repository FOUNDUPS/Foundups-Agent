# Memory Horizon Autonomous Build Package

Status: planning package; authored dispatch specification; not a signed WRE work-order receipt and not live execution authority.

## Restaurant model

012 provides the desired meal: outcome, corrections, boundaries, and observed product feedback.

0102 is the expeditor/architect. 0102 retrieves current repo truth, applies WSP 15/97, converts the FoundUp plan into bounded kitchen tickets, assigns dependency-safe lanes, integrates accepted work, owns the shell/public-surface decision, and returns the result through RedDog.

The machine flow is:

```text
012 intent
 -> 0102/RedDog intake
 -> WSP 109 FoundUp packet
 -> WSP 15 priority + WSP 97 evidence reconciliation
 -> WSP 99 machine tickets
 -> WRE/AgentDB admission + queue/lease
 -> OpenClaw supervision
 -> admitted Hermes/OpenClaw/equivalent leaf worker
 -> independent verifier
 -> 0102 integration
 -> WSP 102/104 public-surface gate
 -> RSI outcome capture
 -> re-observe
```

Creating this package dispatches nothing. Every execution cycle must re-bind current main, current authority, model/provider evidence and exact source scope.

## Product target

Phase 1 is Memory Horizon Sweep 0 + Sweep 1:
- intentionally low-fi survival/dungeon shell;
- deterministic event ledger;
- 12+ unique scorable events;
- delayed episodic probes at configurable 30 s / 1 / 2 / 4 / 8 min candidates;
- free recall -> cue -> recognition;
- explicit and natural in-world probe presentations;
- contamination/event-retirement rules;
- local JSON/CSV export and transparent retention curve;
- current mobile-browser acceptance;
- explicit non-diagnostic boundary.

Canonical design: `../GAME_DESIGN_SWEEPS.md`.

## Execution boundary

The module already exists as a WSP 109 candidate. Workers extend `modules/foundups/memory_horizon`; they do not create a second FoundUp or scaffold.

Public route architecture:
- landing: `/f/memory_horizon`
- app: `/f/memory_horizon/app`
- data namespace: `idb_memory_horizon`

0102 owns the public-surface integration decision. A frontend worker may build tenant-local product UI only inside admitted scope. It must not create an arbitrary root page or mutate shell ownership.

## Model/provider boundary

AI Gateway owns model eligibility and runtime binding. OpenRouter may be used only when the exact current provider/model binding is admitted by existing runtime policy. Ticket prose cannot grant provider authority or expose durable credentials.

## Experiment measurements

Track:
- tickets proposed/admitted/blocked/rejected;
- dependency wait time;
- model/runtime/provider where evidenced;
- calls/retries/time/cost where evidenced;
- merge conflicts and overlapping-scope prevention;
- verifier defects and narrow repair orders;
- 0102 interventions;
- first-pass acceptance rate;
- reusable skills/contracts discovered;
- whether a later cycle measurably improves using retained verified evidence.

Automation is not sufficient to claim RSI. Retained independently verified improvement is required.

## Machine source

- `MEMORY_HORIZON_AUTONOMOUS_BUILD_PACKAGE.json`
- `work_orders/CONTRACT.md`
- `work_orders/PROMETHEUS.md`
- numbered WSP 99 tickets in `work_orders/`
- `work_orders/RESULT_TEMPLATE.json`

Parent experiment: GitHub issue #1825.
