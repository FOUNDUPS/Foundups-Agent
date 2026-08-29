# RedDog Base-Prefix Consumer Interface - Phase 2C3b

This focused interface records a correction to two existing consumers. It does
not add a new production entry point or widen the Phase 2C3a inert contract.

## Canonical topology

One materialized base runtime has two distinct roots:

- `generation_root`: descriptor, inventory, and immutable generation identity;
- `base_prefix_root = generation_root / "python-runtime"`: executable, DLLs,
  Lib, stdlib data, and CPython prefix authority.

`RuntimeCompositionBinding.interpreter_path` is therefore exactly
`base_prefix_root / "python.exe"`. Dependency site-packages remain rooted at
the dependency generation's `site-packages` payload.

## Corrected consumers

`prove_builder_process_authority(...)` uses the base prefix for all four
observed CPython prefixes and for its exact `sys.path` roles. It still binds the
OS-reported process image, strict isolation flags, image bytes, source root,
and dependency identity; native loaded-image closure remains false.

Candidate composition validation requires the canonical payload-directory
relationship and interpreter path. It continues to use the base generation
root for descriptor/inventory identity and volume classification.

The shared real-materialization test is regression evidence for this topology. The
older synthetic process and candidate fixtures also keep generation and prefix
roots distinct so they cannot recreate the false-green condition.

No child is launched. No producer authentication, pre-import proof, ABI/native
or subprocess closure, deterministic effects, signature, write denial,
activation, A-grade, or retrieval RSI authority is earned.
