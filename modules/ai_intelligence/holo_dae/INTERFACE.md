# HoloDAE Interface

## Authority contract

This module owns broker-visible HoloDAE lifecycle state only. It does not own:

- persistent HoloIndex reads or writes;
- canonical index maintenance;
- query-replica selection or activation;
- retrieval candidate admission or promotion;
- production RSI decisions.

The governed query and maintenance authorities remain separate. A caller must
not infer permission to reindex from the existence of this launcher.

## `run_holodae()`

Location: `modules.ai_intelligence.holo_dae.scripts.launch`

Current behavior:

1. Acquires the `holodae_monitor` instance lock.
2. Imports and constructs the legacy `AutonomousHoloDAE`.
3. Starts its monitoring loop and optional WRE skill cadence.
4. Blocks until stopped, then releases the lock.

The function returns `None` and reports startup failures through status/log
output. It is registered with `runtime_autostart=false`. Because the legacy
class contains direct `HoloIndex` construction and automatic reindex logic,
this entrypoint is compatibility-only and is not approved for production
retrieval or maintenance.

## `stop_holodae()`

Location: `modules.ai_intelligence.holo_dae.scripts.launch`

Returns one of:

```json
{"status": "not_running"}
```

```json
{"status": "stopping"}
```

When an instance exists, shutdown is delegated to its
`stop_autonomous_monitoring()` method. The launcher clears the tracked instance
and releases its instance lock when the run loop exits.

## Broker registration

`main.bootstrap_runtime_dae_launches()` registers the module with:

```text
resident_owner=dae_launch_broker
runtime_autostart=false
runtime_reindex_allowed=false
query_runtime=true
```

These fields express broker policy; they do not retrofit an authority guard
inside the legacy `AutonomousHoloDAE` implementation.

## Supported Holo retrieval

Use the governed owner adapter:

```powershell
'{"query":"task","limit":5}' |
  python scripts/reddog_holoindex_owner_query_once.py
```

Accept evidence only when `ok=true`, `freshness=CURRENT`, and
`index_gap_detected=false`. The query path performs no reindex. On a freshness
failure, route the existing governed maintenance transaction; do not invoke
the legacy HoloDAE auto-reindex loop.

## Required migration

The next runtime change must replace the legacy class at this broker boundary
with a tested coordinator adapter that has no direct index mutation authority.
Until that change passes its own WSP_97 audit, HoloDAE remains observation and
compatibility infrastructure rather than operational RSI.
