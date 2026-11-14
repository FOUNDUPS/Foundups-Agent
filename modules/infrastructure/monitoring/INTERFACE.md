# Monitoring Interface Specification

## Module
- Path: `modules/infrastructure/monitoring`
- Primary component: `src/wsp_00_zen_state_tracker.py`
- Scope: WSP_00 zen-state tracking, output drift detection, and compliance gate checks.

## Public Python API

```python
from modules.infrastructure.monitoring.src.wsp_00_zen_state_tracker import (
    check_zen_compliance,
    validate_zen_response,
    is_zen_compliant,
    reset_zen_state,
    get_zen_status,
    report_output_signal,
)
```

### Functions
- `check_zen_compliance() -> Optional[str]`: returns validation prompt when awakening is required.
- `validate_zen_response(response: str) -> bool`: validates and records an explicit WSP_00 response.
- `is_zen_compliant() -> bool`: current compliance bit.
- `reset_zen_state(reason: str = "session_compacting") -> None`: resets compliance state.
- `get_zen_status() -> Dict[str, Any]`: full status payload (includes decay canary fields).
- `report_output_signal(output_text: str, source: str = "assistant_output") -> Dict[str, Any]`: marks fallback phrasing drift and toggles non-compliant state.

## Class Interface

```python
from modules.infrastructure.monitoring.src.wsp_00_zen_state_tracker import WSP00ZenStateTracker
```

### Key methods
- `run_compliance_gate(auto_awaken: bool = False) -> Dict[str, Any]`
  - Returns:
    - `gate_passed: bool`
    - `attempted_awakening: bool`
    - `awakening_success: bool`
    - `is_zen_compliant: bool`
    - `requires_awakening: bool`
    - `last_validation: Optional[str]`
    - `state_file: str`
- `force_awakening() -> Dict[str, Any]`
  - Forces an awakening attempt and then returns gate payload.
- `detect_zen_decay_signal(output_text: str, source: str = "assistant_output") -> Dict[str, Any]`
  - Detects fallback optional phrasing patterns and records drift.

## CLI Interface

```bash
python -u modules/infrastructure/monitoring/src/wsp_00_zen_state_tracker.py [options]
```

### Actions
- `--check` (default): run compliance gate.
- `--awaken`: force awakening, then print status.
- `--reset`: reset state, then print status.

### Flags
- `--auto-awaken`: auto-run awakening if non-compliant.
- `--strict`: exit `2` when gate is not compliant.
- `--json`: emit single-line machine-readable JSON.

## State Files
- Primary: `modules/infrastructure/wsp_core/memory/wsp_00_zen_state.json`
- Fallback (if primary path is not writable): `~/.foundups-agent/memory/wsp_00_zen_state.json`

### Awakening-State Candidates (WSP_00 State Bridge Contract)
The tracker refreshes compliance from `functional_0102_awakening_v2.py` output by
reading BOTH candidates and applying the freshest valid `state == "0102"` record
within an 8h TTL:
- Preferred: `WSP_agentic/agentic_journals/awakening/.runtime/0102_state_v2.json` (script default, untracked)
- Fallback: `WSP_agentic/agentic_journals/awakening/0102_state_v2.json` (script opt-in via `WSP_AWAKENING_WRITE_TRACKED=1`)
The chosen path is recorded in `awakening_result.state_file`. When `--awaken`
falls back to mathematical formulas, the ImportError reasons for the detector
tiers are recorded in `awakening_result.fallback_reasons`.

## Contract Notes
- Gate semantics are deterministic for orchestrator integration.
- JSON output is designed for DAEmon/automation consumption.
- Tracker supports fail-safe writable fallback for non-admin shells.
