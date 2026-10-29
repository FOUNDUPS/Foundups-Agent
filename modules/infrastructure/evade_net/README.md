# EvadeNet Liberty Alert launcher adapter

This owner contains the [launcher adapter](scripts/launch.py)
for the existing communication-domain Liberty Alert orchestrator. `main.py`
imports `run_evade_net`; the adapter does not implement a second mesh service.
Calling it constructs Liberty Alert configuration with mesh and voice enabled,
Spanish as the default language and a five-kilometre alert radius, then runs the
orchestrator through `asyncio.run`.

The optional WRE preflight decorator is imported when available. Its ImportError
fallback is an identity decorator, not proof that a permission or health check
ran. Launching can activate delegated communication/voice behavior, so reading
this module or its documentation is not a launch instruction.

[INTERFACE.md](INTERFACE.md) records the actual entrypoint and error behavior.
No module-local tests or independent runtime implementation are tracked. This
documentation-only review did not launch a mesh, voice service or daemon and
does not certify current Liberty Alert availability.
