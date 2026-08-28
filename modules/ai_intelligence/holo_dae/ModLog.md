## 2026-08-28: Tier-0 contract restoration
- Added root README/INTERFACE contracts so strict Holo module retrieval can
  return the mandatory pair instead of failing `HOLOINDEX_TIER0_INCOMPLETE`.
- Documented the observed broker policy and the unresolved legacy boundary:
  explicit launch still constructs `AutonomousHoloDAE`, whose direct
  `HoloIndex` and auto-reindex path is not governed query/maintenance authority.
- No launcher, owner, index, maintenance, route, or RSI behavior changed.

## 2026-07-16: HOLOINDEX_RESIDENT_DAE_RUNTIME_CONSOLIDATION_PHASE1
- Marked HoloDAE's main.py broker registration as `resident_owner=dae_launch_broker`,
  `runtime_autostart=false`, `runtime_reindex_allowed=false`, and
  `query_runtime=true`.
- Added regression coverage that HoloDAE registers with a stop hook but does not
  autostart during normal runtime bootstrap.
- Boundary: no HoloIndex re-index, no automatic HoloDAE launch, no semantic-store
  mutation, and no RedDog/OpenClaw execution wiring.

## 2026-03-18: Broker-managed HoloDAE stop hook
- Added broker-visible lifecycle state to `scripts/launch.py`.
- Added `stop_holodae()` so the runtime broker can stop HoloDAE instead of returning `stop_unsupported`.
- HoloDAE shutdown now clears the tracked instance after releasing the module lock.
