# Token Efficiency ModLog

## 2026-09-15 — Reject unsafe legacy invariant emission

AmIBot G0 at main 582cbe82 exposed nested constraint loss in the existing compiler.
Added a bounded scalar serializer guard and preserved invalid falsey inputs until
validation. Existing parser/YAML and canonical envelope qualification are separate.
No new module, skill, dependency or test file. WSP00/15/22/50/62/84/97/99.

Initial matrix reproduced 30 failures. Independent review rejected overly strict
empty-value/internal-space-key handling despite 207 passing tests; corrected it
and added Unicode-line-boundary cases. Final 222 tests pass in both author and
independent runs:162 existing, 44 rejection and 16 scalar compatibility cases.
Eight manifest tests and 15 fast groups pass; one runtime hash changes among 1,400
members, with both existing pins updated. Registry unchanged 1,650/269 quarantined.
Shared handoff parent 18/P0 remains open for typed identity/consumer qualification.
Evidence: `amibot_g0_continuation_20260915` in canonical baseline observations.
Local review accepts this guard only; no signed WRE retention or worker activation.

## 2026-09-14 — Preserve explicit stop rules through decompilation

At main `3fc74285cb19b681de5219b8288e5307a0ea533a`, the compact compiler kept
stop conditions in its parsed object but omitted them from readable instructions.
The existing fidelity gate returned success. Extended the existing compiler
renderer and gate; no new runtime, schema, scheduler or model call.

Five regression cases failed before the repair; all 162 focused tests pass
afterward. Checks cover real rendering, dropped/weakened/substituted stop
instructions, legacy packets and unchanged stop-free output. The new
`tests/TestModLog.md` inventories the seven existing test files for future
reuse. Existing parser loss remains rejected; whole-prose fidelity and signed
runtime admission are separate requirements.

Packaging verification: all 15 RedDog fast groups and eight manifest tests
pass; runtime membership remains 1,400 files with only these two source hashes
changed. The existing external Python dependency-root configuration resolved
the first fast-tier setup failure in this worktree.

Retrieval found the existing source/test owners through the governed local
bundle, with UNKNOWN freshness and no semantic-owner query. Missing optional
artifacts were recorded; no alternate compiler was introduced. Local WSP 15
score: 2+4+4+4=14/P1. WSP 00/15/22/50/84/87/97/99.
