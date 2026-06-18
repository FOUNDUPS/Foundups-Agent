# openrouter_client -- DORMANT (contract_pending)

**Status**: `contract_pending` / dormant. This module is NOT runtime-enabled and has NO live client.

## What this is

This directory is the reserved future home for a live OpenRouter client. Its earlier source was
reverted (added in `a0fad35b3`, reverted in `6f952f6b9`); only orphan `__pycache__/*.pyc` bytecode
artifacts linger on disk (untracked -- intentionally left alone, not committed). There is no `.py`
source here and no tracked implementation.

The OpenClaw integration manifest previously over-claimed this as `status: "landed"`. That was false and
has been corrected to `status: "parked"` in
`modules/communication/moltbot_bridge/config/openclaw_integration_manifest.json`. ("parked" is the
schema-valid honest value; the manifest status enum is landed/planned/parked/removed. The precise
`contract_pending` / `BLOCKED_PENDING_REDACTION_GATE` semantics are carried in that entry's `notes` field.)

## Where the contract actually lives

The advisory Fusion worker-panel CONTRACT (mock/dry-run only) lives under Hermes, not here:

- `modules/communication/moltbot_bridge/src/fusion_adapter.py`

## Hard boundaries (do not violate)

- Do NOT make this module executable or import it into a runtime path.
- Do NOT read any `OPENROUTER_*` env var / API key from here.
- Do NOT add runtime registration (Hermes / OpenClaw / HoloIndex).
- Live OpenRouter use is `BLOCKED_PENDING_REDACTION_GATE`.

## References

- Audit: `docs/audits/architecture/OPENROUTER_FUSION_FOUNDUPS_INTEGRATION_AUDIT_PHASE1.md`
- Slice: `HERMES_FUSION_ADAPTER_CONTRACT_PHASE1`
