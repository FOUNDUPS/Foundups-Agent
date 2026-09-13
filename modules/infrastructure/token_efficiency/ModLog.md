# Token Efficiency ModLog

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
