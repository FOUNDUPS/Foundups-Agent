# Memory Horizon

**FoundUp ID:** `memory_horizon` | **Owner:** 012 | **Intake:** 0102  
**Status:** Registration candidate; SPECIFIED_NOT_IMPLEMENTED; TOKEN_DEFERRED.

Memory Horizon is a browser-first research and measurement game for mapping formation and retention of new episodic memories over time. A player moves through a minimal branching adventure. The system records unique events and later probes what happened after controlled delays, producing a transparent retention timeline rather than a black-box "memory score."

## Read order

1. [Outcome](docs/intake/OUTCOME.md)
2. [Solution](docs/intake/SOLUTION.md)
3. [Pain](docs/intake/PAIN.md)
4. [POC scope](docs/intake/POC_SCOPE.md)
5. [Prototype gate](docs/intake/PROTOTYPE_GATE.md)
6. [Skills map](docs/intake/SKILLS_MAP.md)
7. [Manifest draft](docs/intake/FOUNDUP_MANIFEST_DRAFT.md)
8. [Intake source](docs/intake/INTAKE_SOURCE.md)

Supporting records: [research](docs/RESEARCH.md), [data/scoring contract](docs/DATA_AND_SCORING_CONTRACT.md), [validation](docs/VALIDATION.md), [roadmap](ROADMAP.md), [interface](INTERFACE.md), [change log](ModLog.md).

## Core loop

play -> unique event -> continue playing -> delayed probe -> score raw response -> retire probed event -> adapt next delay -> repeat -> export timeline

The POC measures free recall, cued recall and recognition separately. Once an event has been scored, it is retired from the retention estimator so the test itself does not repeatedly refresh that same memory.

## Medical boundary

Memory Horizon is not a concussion test, diagnosis, triage system, discharge tool or substitute for A-WPTAS, SCAT6 or clinical assessment. Acute head-injury decisions remain with clinicians. Any future medical-device claim requires prospective validation, ethics review and applicable regulatory work.

## Execution boundary

This intake authorizes documentation and a bounded POC proposal only. No public route, DNS, patient-data service, clinical workflow, token, or reward mechanism is activated.

Next bounded slice: [issue #1821](https://github.com/FOUNDUPS/Foundups-Agent/issues/1821), `MEMORY_HORIZON_POC_PHASE1`.

Proposed future host: `memory.foundups.com`. Not configured or reserved by this intake.

## WSP references

WSP 00, 15, 22, 49, 50, 95, 97, 109. Follow the existing FoundUp onboarding protocol before runtime/public promotion.
