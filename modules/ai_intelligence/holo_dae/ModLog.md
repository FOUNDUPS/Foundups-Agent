## 2026-03-18: Broker-managed HoloDAE stop hook
- Added broker-visible lifecycle state to `scripts/launch.py`.
- Added `stop_holodae()` so the runtime broker can stop HoloDAE instead of returning `stop_unsupported`.
- HoloDAE shutdown now clears the tracked instance after releasing the module lock.
