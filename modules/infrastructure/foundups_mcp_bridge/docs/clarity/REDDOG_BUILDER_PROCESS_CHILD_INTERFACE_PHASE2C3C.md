# RedDog Builder Process Child Interface - Phase 2C3c

## Decision

Phase 2C3c is one inert observation layer above the exact Phase 2C3a builder
runtime. It launches exactly one held interpreter, proves the live process, and
returns path-free evidence. It does not serialize or preserve
`BuilderProcessAuthority`; that capability remains private to the child.

## Public call

```python
run_builder_process_once(
    *,
    builder_runtime: BuilderRuntimeCompositionBinding,
    repo_root: Path | str,
    canonical_store: Path | str,
    temp_root: Path | str,
    timeout_seconds: float = 120.0,
) -> BuilderProcessChildEvidence
```

The canonical store and temporary directory must already exist on O: or E:.
They must be outside the repository; the temporary directory must also be
disjoint from the canonical store and every base, dependency, and composition
store/generation root.

## Parent sequence

1. Rebuild and exact-compare the typed builder/runtime binding.
2. Fully reprove the runtime composition.
3. Prove and hold the exact interpreter across the launch.
4. Start one child with `-I -S -B -E -s -c`, no shell, no stdin, discarded
   stderr, bounded stdout, a finite timeout, and only O:/E:-local `TEMP`/`TMP`.
5. Replace `sys.path` with exactly: base `python312.zip`, base `DLLs`, base
   `Lib`, base prefix, dependency `site-packages`, and the repository root.
6. Accept exactly one canonical ASCII JSON line with no duplicate keys.
7. Cross-bind process image, composition, dependency, and repository identity.
8. Fully reprove the same runtime composition and require exact equality.

The shared bounded child runner caps stdout at 16 KiB, drains it without an
unbounded `communicate()`, and terminates a live process tree on timeout or
output overflow. Windows launch is suspended until a private kill-on-close Job
Object contains the process; closing the guard also kills descendants after a
direct-parent exit. Cleanup explicitly terminates the Job before releasing its
handle and resolves no external executable. Direct parsing enforces the same
byte cap. The maintenance process keeps its
compatibility API over that shared mechanism.

## Qualified physical evidence

The real integration uses the reviewed `packaging==26.0` wheel and an inert
O:-materialized CPython 3.12.10 AMD64 runtime. The official archive is
32,399,361 bytes at
`sha256:8649692de846c56a7189d6dae5c322ab20deb1b5908b6f39426b62a36f39415d`.
Python.org identifies 3.12.10 as the final 3.12 release with Windows binaries;
3.12 is now security-fixes-only. Therefore this proves the bounded interface,
not current patch posture or production suitability.

Hostile validation proved why persistent write denial remains false: test hosts
that selected the materialized interpreter without `-B` created bytecode absent
from its inventory. Both invalid generations are preserved in O: quarantine.
The official source rematerialized to the identical generation, descriptor, and
inventory IDs. Test hosts now use the clean O: source interpreter, all Python
children use `-B`, and the Windows conversation override requires a regular
O:/E: executable. Final physical, adjacent, conversation, and release replays
left both the source and active materialized trees with zero pycache/pyc.

Primary references:

- https://www.python.org/downloads/release/python-31210/
- https://www.python.org/downloads/release/python-31214/
- https://www.python.org/ftp/python/3.12.10/windows-3.12.10.json

## Explicit false claims

The public evidence keeps all of these false: capability preservation,
authenticated producer, pre-import loader, loaded-module origins, ABI
compatibility, native-loader closure, subprocess closure, deterministic
effects, signature, persistent write denial, activation eligibility, A-grade,
and retrieval RSI. No route, owner, queue, Git, maintenance, or VSIX execution
authority is added.
