# GotJunk test inventory

## 2026-10-19 — Multipart parser security upgrade

- `test_backend_security.py`: offline Firebase identity/configuration failures,
  issuer/signature checks, per-process rate admission, fixed/chunked body limits,
  and patched form-separator behavior plus FastAPI multipart upload compatibility.
- `test_migration_inventory.py`: metadata-only dry-run ordering/idempotency,
  conflicting owner/digest/state rejection, private-field and tenant rejection,
  redacted reports, and empty inventories without cloud access.
- `test_manifest.py`: FoundUp manifest schema, routing, capability and lifecycle
  contracts. This does not prove deployed service availability.
- `security_rules.mjs`: Firestore/Storage emulator authorization, concurrent
  message/vote synchronization, and reservations; requires the isolated tools
  installation described in `../SECURITY.md`.

The existing backend test file was extended; no duplicate suite was introduced.
Run Python tests with the backend requirements, pytest and httpx, using
`python -B -m pytest -q -c /dev/null --noconftest -p no:cacheprovider modules/foundups/gotjunk/tests`.
Results and deployment limits are recorded in the module ModLog.
