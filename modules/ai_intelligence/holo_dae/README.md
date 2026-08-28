# HoloDAE

HoloDAE is the broker-visible observation and code-intelligence runtime for
HoloIndex. It owns lifecycle coordination and monitoring; it is not the
HoloIndex query owner, index-maintenance authority, retrieval ranker promotion
authority, or proof that recursive self-improvement (RSI) is operational.

## Current operational status

`main.py` registers `holodae` with the DAE launch broker and explicitly sets:

- `resident_owner=dae_launch_broker`
- `runtime_autostart=false`
- `runtime_reindex_allowed=false`
- `query_runtime=true`

The current `scripts/launch.py` remains a legacy compatibility surface. When
called explicitly it imports `AutonomousHoloDAE`, which directly constructs
`HoloIndex` and contains an automatic reindex loop. The broker metadata does
not enforce that boundary inside the legacy class. Consequently this launcher
is not an approved production maintenance or retrieval path and must not be
used to claim governed Holo operation.

Supported RedDog retrieval uses the authenticated, generation-bound owner
adapter (`scripts/reddog_holoindex_owner_query_once.py`). Index refresh and
replica activation use the separate governed OpenClaw/AgentDB post-merge
transaction. Query-time reindexing is forbidden.

## Public surfaces

- `scripts.launch.run_holodae()` — explicit legacy lifecycle entrypoint;
  broker-registered but not autostarted.
- `scripts.launch.stop_holodae()` — requests shutdown of the tracked runtime
  instance and returns `not_running` or `stopping`.
- `holo_index.qwen_advisor.holodae_coordinator.HoloDAECoordinator` — the
  modular observation coordinator that supersedes the monolithic design, but
  is not yet bound to this launch adapter.

See [INTERFACE.md](INTERFACE.md) for exact authority and side-effect boundaries.

## RSI truth

HoloDAE can observe activity, produce monitoring evidence, and route candidate
analysis. It does not currently provide a live retrieval proposer,
independently administered evaluator, authenticated admission, shadow canary,
signed ranker promotion, ranker rollback, or candidate-bound production
outcome learning. Retrieval RSI is therefore not operational.

## Structure debt

The runtime predates the current WSP module layout and still keeps executable
code in `scripts/`. Migrating the broker entrypoint from
`AutonomousHoloDAE` to a governed coordinator adapter is a separate P0 change;
this contract does not disguise that migration as complete.
