# dae_daemon Tests

## Test Organization

Tests follow the 8-layer architecture — each layer tested independently before integration.

| Test | Layer | What it covers |
|------|-------|----------------|
| `test_schemas.py` | 0 | Enum values, dataclass serialization round-trips, deterministic IDs |
| Integration tests | 0-7 | Run via manual scripts (pytest has eth_typing conflict on Windows) |

## Focused event-store regressions — 2026-09-22

The nine `test_event_store_*` functions in `test_dae_observer.py` use disposable
SQLite/JSONL storage and a fail-fast wrapper around a real Lock. They cover collision
recovery, retry budgets0–4, unrelated SQLite/unique errors, duplicate no-op, lock
release and preserved write order. Partial-write/parity failure remains an expected
limitation, not a repaired contract. No daemon or live service is started by these cases.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -B -m pytest modules/infrastructure/dae_daemon/tests/test_dae_observer.py -k test_event_store_ -q -o addopts= -p no:cacheprovider
```

Result:9passed,3deselected, two plugin-configuration warnings. Existing observer
tests are deliberately outside this bounded run. Candidate production-lock process
replay is not claimed; broader witness review was blocked by automatic screening.
Full crash recovery, concurrent writers and registry acknowledgment need separate qualification.

## Persistence characterization — 2026-09-22

Seven additional cases in the same test file cover six boundaries: append failure, partial-write
reopen/retry, post-commit error, conflicting dedupe input, false-positive count
parity, and returned/raised storage failure with inert emergency spies. Run these
with the nine retry regressions using the exact selection recorded in TestModLog.
Result:16passed,3deselected locally and independently (overlapping cases).

These are current-behavior characterizations, not acceptance of the defects as a
future contract. Keep fault inputs fixed when proposing a repair, independently
review its stronger oracle, and retain the historical result. No daemon is started,
no real kill action occurs, and WRE/FAM comparisons are static only.

## Running Tests

```bash
# Formal pytest (if eth_typing issue is resolved)
python -m pytest modules/infrastructure/dae_daemon/tests/ -v

# Manual execution (Windows-safe)
cd O:/Foundups-Agent
python -c "
import sys; sys.path.insert(0, '.')
from modules.infrastructure.dae_daemon.tests.test_schemas import *
# Run test classes manually
"
```

## Coverage Target

- Layer 0 (schemas): 100% — all enums, all dataclass fields, round-trips
- Layer 1 (event_store): Write, query, dedupe, parity, persistence
- Layer 2 (registry): Register, heartbeat, toggle, stale detection
- Layer 3 (killswitch): Severity thresholds, PID mock, report generation, popup alert
- Layer 4 (daemon): Singleton, lifecycle, event forwarding
- Layer 5 (adapter): Registration, heartbeat, event reporting, graceful no-ops
- Layer 6 (FAM integration): FAM standalone + reports to central daemon
- Layer 7 (dashboard): Renders, enable/disable toggles

## Notes

- SQLite holds file locks on Windows — use `gc.collect()` before temp dir cleanup
- Tests mock `ctypes.windll.user32.MessageBoxW` to avoid actual popup dialogs
