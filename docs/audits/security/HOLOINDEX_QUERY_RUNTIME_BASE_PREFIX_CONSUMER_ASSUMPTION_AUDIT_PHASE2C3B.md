# HoloIndex Query Runtime Base-Prefix Consumer Assumption Audit - Phase 2C3b

**Status:** Implemented and falsified as a topology correction only
**Decision:** GO for Phase 2C3b; NO-GO for child or activation claims
**Base:** `2de765574f6d5fc1f5316034594187cdc3b11b84`
**WSP_15:** 20/P0, ULTRA

## Retrieval and false-green finding

The governed owner query was CURRENT at the exact base with no index gap or
reindex. It correctly ranked the process proof, candidate binding, Phase 2C3a
join, and their tests. The requested structured-memory bundle supplied all
required Tier-0/Tier-1 module documents; bounded direct reads were truncated,
so complete source and test files were read locally before changes.

Repository-wide exact-pattern search found only two incorrect production
consumers. Other generation-root uses open the base descriptor/inventory and
are correct. The ABI path already uses `base_prefix_root` for native payloads.

The existing process/candidate selection passed 28 tests with one expected
skip before repair. Those tests were not evidence of compatibility: both
synthetic base fixtures set `generation_root == base_prefix_root`. A new shared
materialized-runtime test produced three authentic RED failures:

1. candidate validation rejected the real payload prefix;
2. candidate validation accepted the obsolete root-level interpreter; and
3. process validation rejected the real payload prefix.

## Minimal correction

- Process prefix roles and exact `sys.path` now root at
  `composition.base_runtime.base_prefix_root`.
- Candidate validation requires
  `base_prefix_root == generation_root / PAYLOAD_DIRECTORY` and
  `interpreter_path == base_prefix_root / INTERPRETER_RELATIVE_PATH`.
- Both legacy fixtures now separate generation and payload roots.
- The shared materialized composition must pass both topology validators,
  while the old topology must fail.

No descriptor schema, identity digest, materializer, dependency, lock, process
launcher, or public API changes. The base generation root continues to own its
descriptor and inventory; only executable/prefix interpretation changes.

## Explicit nonclaims

This slice does not launch or authenticate a child, import packages, prove
pre-import safety, ABI/native loaded-image or subprocess closure, deterministic
effects, producer provenance, signature, persistent write denial, activation,
A-grade admission, or retrieval-quality RSI.
