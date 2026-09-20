# Memory Horizon

**FoundUp ID:** `memory_horizon` | **Owners:** 012 + 0102 | **Intake:** 0102  
**Status:** Registration candidate; SPECIFIED_NOT_IMPLEMENTED; TOKEN_DEFERRED.

Memory Horizon is our browser-first research and measurement FoundUp for mapping formation and retention of new episodic memories over time. A player moves through a minimal branching adventure. The system records unique events and later probes what happened after controlled delays, producing a transparent retention timeline rather than a black-box "memory score."

A later **Memory Horizon Companion** track extends the same event model into an assistive "memory seeing dog": a phone/headset/wearable captures compact private episodic breadcrumbs and, when the wearer asks something like "Where is my phone?", retrieves the most recent evidence and gives the smallest useful cue. See [Assistive Memory Companion](docs/ASSISTIVE_MEMORY_COMPANION.md).

## Read order

1. [Outcome](docs/intake/OUTCOME.md)
2. [Solution](docs/intake/SOLUTION.md)
3. [Pain](docs/intake/PAIN.md)
4. [POC scope](docs/intake/POC_SCOPE.md)
5. [Prototype gate](docs/intake/PROTOTYPE_GATE.md)
6. [Skills map](docs/intake/SKILLS_MAP.md)
7. [Manifest draft](docs/intake/FOUNDUP_MANIFEST_DRAFT.md)
8. [Intake source](docs/intake/INTAKE_SOURCE.md)

Supporting records: [research](docs/RESEARCH.md), [data/scoring contract](docs/DATA_AND_SCORING_CONTRACT.md), [assistive companion](docs/ASSISTIVE_MEMORY_COMPANION.md), [validation](docs/VALIDATION.md), [roadmap](ROADMAP.md), [interface](INTERFACE.md), [change log](ModLog.md).

## Core loop

play -> unique event -> continue playing -> delayed probe -> score raw response -> retire probed event -> adapt next delay -> repeat -> export timeline

The POC measures free recall, cued recall and recognition separately. Once an event has been scored, it is retired from the retention estimator so the test itself does not repeatedly refresh that same memory.

## Two product layers

**Measurement layer:** controlled game events estimate episodic retention over increasing delays.

**Assistive layer (deferred):** lived events become evidence-bearing breadcrumbs; explicit retrieval failures trigger graded cues. The same underlying event model can therefore support both controlled measurement and real-world recall assistance without pretending they are clinically interchangeable.

## Medical boundary

Memory Horizon is not a concussion test, diagnosis, triage system, discharge tool or substitute for A-WPTAS, SCAT6 or clinical assessment. The Companion is likewise not a treatment or medical decision system. Acute head-injury decisions remain with clinicians. Any future medical-device claim requires prospective validation, ethics review and applicable regulatory work.

## Execution boundary

This intake authorizes documentation and a bounded POC proposal only. No public route, DNS, patient-data service, clinical workflow, wearable runtime, token, or reward mechanism is activated.

Next bounded slice: [issue #1821](https://github.com/FOUNDUPS/Foundups-Agent/issues/1821), `MEMORY_HORIZON_POC_PHASE1`.

Deferred assistive track: [issue #1823](https://github.com/FOUNDUPS/Foundups-Agent/issues/1823), `MEMORY_HORIZON_COMPANION_PHASE1`.

Proposed future host: `memory.foundups.com`. Not configured or reserved by this intake.

## WSP references

WSP 00, 15, 22, 49, 50, 60, 95, 97, 109. Follow the existing FoundUp onboarding protocol before runtime/public promotion.
