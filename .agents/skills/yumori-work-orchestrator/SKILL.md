---
name: yumori-work-orchestrator
description: Convert 012/Red Dog YUMORI planning conversations into a verified, deduplicated, WSP 15-ranked backlog and bounded Work handoff.
---

# YUMORI.me Work Orchestrator

Canonical Skillz: `modules/foundups/esingularity/skillz/yumori_work_orchestrator/SKILLz.md`.

Apply that file as the source of truth.

Key invariants:

- Retrieve live state before creating the backlog; chat memory is not project truth.
- De-duplicate DONE, WAIT, SUPERSEDED and already-sent work before WSP 15 scoring.
- Separate 012 physical/decision actions from machine-executable Work tasks.
- Use canonical WSP 15 scoring and dependency ordering.
- Handoff only verified WORK_READY items through the existing RedDog governed-work authorization chain.
- Do not create a second project ledger, executor, signer, queue, or email memory database.
- Work results require receipts and writeback to the owning YUMORI/Gmail/Drive/repo state.
