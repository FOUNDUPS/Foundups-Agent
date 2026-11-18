# HoloIndex Memory Boundary

## Current truth

This directory owns local HoloIndex learning, feedback, and operational-memory
artifacts. Its contents are inputs or historical observations, not automatic
authority for current repository status, ranker promotion, or production RSI.

Governed current truth comes from the exact committed repository, canonical
README/INTERFACE/ROADMAP contracts, implementation and tests, generation-bound
freshness receipts, immutable query-replica evidence, and independently
verified benchmark receipts. Conflicting memory records must be treated as
stale until those authorities reconcile them.

## Safety contract

- Query-only paths do not write this directory, reindex HoloIndex, start
  maintenance, change routes, or promote rankers.
- Memory artifacts must not contain credentials, tokens, private environment
  values, or absolute private runtime paths.
- Raw feedback cannot authorize code, index, route, or ranker changes.
- Any future learning writer must bind an exact candidate ID, corpus/evaluator
  identity, outcome receipt, and rollback authority before admission.
- Historical or heuristic scores are evidence, not production measurements.

## Present implementation boundary

HoloIndex has working generation-bound retrieval and public benchmark
evaluation. It does not yet have an operational retrieval proposer,
independent administered evaluator service, signed admission, shadow canary,
ranker promotion, rollback proof, or candidate-bound outcome-learning loop.
The adaptive-learning CLI path remains disabled because it caused hangs.

The files below this directory are therefore maintained as local state for
experiments and diagnostics. Their mere presence must never be reported as
proof that recursive self-improvement is active.
