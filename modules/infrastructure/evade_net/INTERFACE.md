# EvadeNet Liberty Alert launcher adapter interface

The callable owner is
[`scripts/launch.py::run_evade_net`](scripts/launch.py), also used by the guarded
script entrypoint. It takes no arguments and has no structured result contract.

The function is decorated with `preflight_guard("evade_net_dae")` when that WRE
import succeeds; ImportError installs an identity decorator. Inside the function,
it imports `LibertyAlertOrchestrator` and `LibertyAlertConfig` from the existing
communication module, sets `mesh_enabled=True`, `voice_enabled=True`,
`default_language="es"`, and `alert_radius_km=5.0`, then calls
`asyncio.run(orchestrator.run())`.

Exceptions within the function's launch block are printed with a traceback and
are not re-raised there. A normal return or process exit is therefore not a
verified healthy launch. Errors in decorator/import setup may occur earlier.
Calling inside an existing event loop is not handled by a separate async API.

The source contains a quoted historical UTF-8 wrapper example; it is not active
stream-wrapping code. This document describes source behavior only. Runtime,
network, voice, preflight and lifecycle acceptance must be verified through the
existing Liberty Alert owner before claiming an operational deployment.
