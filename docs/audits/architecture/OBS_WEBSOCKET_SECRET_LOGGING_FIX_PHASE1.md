# OBS_WEBSOCKET_SECRET_LOGGING_FIX_PHASE1

## Status

Implemented for W10 review.

## Worker-Lane

0102 implementation lane after W1/W3 audit findings.

## Slice

OBS_WEBSOCKET_SECRET_LOGGING_FIX_PHASE1

## Problem

The AntifaFM OBS WebSocket dependency path could emit OBS connection
parameters through third-party `obsws_python` log records. The runtime audit
found plaintext password fields in local log files. This is a P0 secret
exposure boundary.

This slice prevents future emission of OBS WebSocket passwords,
authentication tokens, and stream keys through console or file logging. It
does not rotate secrets and does not purge historical logs; those are
operational actions outside the code slice.

## Root Cause

`OBS_WEBSOCKET_PASSWORD` is passed into `obsws_python.ReqClient(...)`. The
third-party package may log connection parameters or object representations
at INFO/WARNING levels. Repository root logging writes to stdout and
`logs/foundups_agent.log`, so unredacted third-party records can persist.

## Fix Shape

Added a narrow OBS logging guard:

- redaction filter for OBS password/authentication/key fields
- known `obsws_python` logger suppression above INFO
- guarded `create_obs_req_client()` helper
- root logger installation after `logging.basicConfig(...)`
- replacement of OBS client construction paths that read
  `OBS_WEBSOCKET_PASSWORD`

## Files Changed

| File | Change |
|------|--------|
| `main.py` | Install OBS logging guard after root logging setup |
| `modules/platform_integration/antifafm_broadcaster/src/obs_logging_guard.py` | New redaction and client-construction helper |
| `modules/platform_integration/antifafm_broadcaster/src/obs_controller.py` | Use guarded OBS client creation |
| `modules/platform_integration/antifafm_broadcaster/skillz/boot_layer_rotator/executor.py` | Use guarded OBS client creation |
| `modules/platform_integration/antifafm_broadcaster/skillz/news_maps/executor.py` | Use guarded OBS client creation |
| `modules/platform_integration/antifafm_broadcaster/skillz/gcc_shipping_tracker/executor.py` | Use guarded OBS client creation |
| `modules/platform_integration/antifafm_broadcaster/tests/test_obs_logging_guard.py` | New synthetic secret redaction tests |
| `modules/platform_integration/antifafm_broadcaster/ModLog.md` | WSP 22 change entry |
| `modules/platform_integration/antifafm_broadcaster/tests/TestModLog.md` | Test coverage entry |

## Validation Contract

All tests use synthetic secrets only.

No test reads `.env`, prints a real password, connects to OBS, starts OBS,
opens browser automation, or performs a network call.

## Operational Follow-Up

Because local logs already contained plaintext password fields before this
slice, the OBS WebSocket password should be treated as compromised unless it
has been rotated after the affected logs were produced.

Recommended operational actions:

1. Rotate the OBS WebSocket password.
2. Redact or purge local affected log files.
3. Keep the new guard in place to prevent recurrence.

## Truth Boundary Checklist Item

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | OBS_WEBSOCKET_SECRET_LOGGING_FIX_ONLY | YES | Scope is limited to OBS log redaction and affected client construction paths |
| 2 | DEFAULT_NO_SECRET_LOGGING | YES | Guard installs root/handler filters and suppresses known obsws loggers |
| 3 | SYNTHETIC_SECRET_TESTS_ONLY | YES | New tests use synthetic strings only |
| 4 | NO_ENV_SECRET_READ_IN_TESTS | YES | Tests do not read `.env` or `OBS_WEBSOCKET_PASSWORD` |
| 5 | NO_LIVE_OBS_CONNECTION_IN_TESTS | YES | Tests use a fake OBS module |
| 6 | NO_NETWORK_CALL_IN_TESTS | YES | Tests only exercise logging and fake client construction |
| 7 | NO_SECRET_VALUE_PRINTED | YES | Audit and tests contain no real password values |
| 8 | NO_STREAM_KEY_EXPOSURE | YES | Redaction covers stream key and key fields |
| 9 | HISTORICAL_LOG_ROTATION_NOT_PERFORMED | YES | Operational rotation/purge documented as follow-up |
| 10 | NO_ANTIFAFM_STARTUP_BOUNDARY_CHANGE | YES | Startup auto-launch behavior is deferred to a separate slice |
| 11 | NO_DEPENDENCY_CHANGE | YES | No new dependency added |
| 12 | NO_CI_CHANGE | YES | No workflow files changed |
| 13 | NO_REGISTRY_MUTATION | YES | No registry/catalog/manifest/projection files changed |
| 14 | NO_PUBLIC_ROUTE_ACTIVATION | YES | No public surface changed |
| 15 | NO_CABR_READY | YES | No readiness or governance promotion claimed |
| 16 | NO_PAYOUT_READY | YES | No payout readiness claimed |
| 17 | NO_DAO_ACTIVATION | YES | No DAO activation claimed |

## Next Slice

`MAIN_MENU_ANTIFAFM_STARTUP_BOUNDARY_FIX_PHASE1`

That slice should remove or strictly gate the legacy `ANTIFAFM_AUTO_START`
path that can launch OBS/metadata/rotator before the interactive menu.
