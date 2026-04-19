# FCA1 — AG2 Assessment: main.py / DAE boot / AI Overseer hooks

**Date**: 2026-04-19
**Window**: AG2
**Slice**: FCA1-AG2
**Lane**: FCA (full codebase assessment, phase 1)
**Mode**: read-only audit
**Verdict**: ACCEPTED by 012
**WSP**: 97 (truthful state distinction), 77 (agent coordination), 22 (ModLog)

---

## Scope

One of nine FCA1 subsystem audits:

| Window | Lane | Subsystem |
|---|---|---|
| CW1 | WRE / HoloIndex / Rolodex / SKILLz | recursive control plane |
| CW2 | FoundUps Runtime Modules | AntifaFM, Kosei, GotJunk, Science Swarm, AutoPost |
| CW3 | Hermes / Externalization / Repo Boundary | DD/DE/DI chain, extraction gates |
| CW4 | YouTube Platform Stack | youtube_auth, stream_resolver, channel_pull, pfMALL |
| CW5 | Communication / Comment Automation | video_comments, livechat, reply agents |
| AG1 | Docs / ModLog / Session Briefing Hygiene | document-sprawl audit |
| **AG2** | **Main.py / DAE Boot / AI Overseer Hooks** | **this report** |
| AG3 | pfMALL / Browser Agent Control | PMCTRL, RedDog control surface |
| AG4 | Security Stack | SEC1–SEC10 end-to-end |
| AG5 | Test Quality / CI Truth | production-path vs copied-logic coverage |

**Mode**: read-only. No code edits. No `main.py` edits in this slice. Implementation slices (DJ2 lane) will act on findings here.

---

## Boot-time preflight surface

[main.py](../../main.py) (1,485 lines, 16 top-level fns). Nine preflights execute during boot plus one post-connect CLI hook:

| # | Preflight | Location | Exit states | Blocks startup? | AI-resolution dispatch? |
|---|---|---|---|---|---|
| 1 | OAuth token | inline in `monitor_youtube` | PASS/WARN | no | **no** |
| 2 | OpenClaw Security | `run_openclaw_security_preflight` | PASS/FAIL | only if enforced | **no** |
| 3 | IronClaw Runtime | `run_ironclaw_runtime_preflight` | PASS/FAIL/WARN/**SKIP** | only if enforced | **no** |
| 4 | DEP-SECURITY | `run_dependency_security_preflight` | PASS/FAIL | only if enforced | ✅ DJ #383 |
| 5 | ENV-HYGIENE | `run_env_hygiene_preflight` | PASS/**WARN** | only if enforced | **no** |
| 6 | BRAIN-MEMORY | `run_brain_artifact_preflight` | PASS/FAIL/WARN | only if enforced | **no** |
| 7 | WRE-DASHBOARD | `run_wre_dashboard_preflight` | **PASS(INSUFFICIENT_DATA)**/PASS/FAIL | only if enforced | **no** |
| 8 | WSP-FRAMEWORK | `run_wsp_framework_preflight` | PASS/FAIL | only if enforced | ✅ DJ #383 |
| 9 | GIT-MERGE-SENTINEL | `run_git_main_merge_sentinel_preflight` | PASS/FAIL/WARN | only if enforced | **no** |

Non-preflight CLI hook: `run_connect_wre` (WSP 97 §4.6).

---

## FCA1 nine-question matrix

### 1. What is operational?

- All 9 boot preflights run and emit `[TAG] preflight=<STATE>` console lines.
- DJ dispatch contract (`modules/ai_intelligence/ai_overseer/src/preflight_resolution.py`, merged via PR #383) converts preflight failures into durable events under `alerts/preflight/*.json`.
- AI Overseer is initialized at boot and serves as sentinel for OpenClaw Security and WSP-Framework preflights. IronClaw uses its own gateway client.

### 2. What is only documented?

- `run_connect_wre` advertises `coded: YES` but its default return-shape is `connection: "DISCONNECTED" / readiness: "DISABLED"`. An unpopulated invocation ships a documented-success / runtime-degraded pair — WSP 97 risk.
- `FOUNDUPS_ENV_PREFLIGHT_ENFORCED` defaults to `0`. The preflight is advisory in all shipping envs.

### 3. What has WRE / 0102 hooks?

| Preflight | Hook |
|---|---|
| DEP-SECURITY | DJ dispatch → PatternMemory recall + AI proposal |
| WSP-FRAMEWORK | DJ dispatch → PatternMemory recall + AI proposal |
| OpenClaw Security | AI Overseer `monitor_openclaw_security` (sentinel, no downstream dispatch) |
| IronClaw | `IronClawGatewayClient().startup_probe()` (gateway only, no dispatch) |
| WRE-DASHBOARD | `DashboardAlertMonitor` (internal telemetry only) |

### 4. What lacks hooks?

Seven of nine preflights have **no** AI-resolution dispatch:
- OAuth token
- OpenClaw Security
- IronClaw Runtime
- ENV-HYGIENE
- BRAIN-MEMORY
- WRE-DASHBOARD
- GIT-MERGE-SENTINEL

### 5. What has tests proving production paths?

- DJ contract: 12 tests in `modules/ai_intelligence/ai_overseer/tests/test_preflight_resolution.py`. Two tests assert `main.py` emitters call the dispatcher (DEP-SECURITY, WSP-FRAMEWORK).
- Other 7 preflights: module-local tests exist for most underlying implementations; none assert the boot-fail → dispatch → artifact chain. Return-bool is checked; side-effect absence is not.

### 6. What has stale or duplicated docs?

- ENV-HYGIENE reimplements env parsing three times in a single function (`managed-env utility → legacy_scan fallback → emergency inline parser`). Defensive but duplicative — WSP 22 hygiene risk if the managed parser changes.
- Each preflight docstring lists its own env vars; no canonical table of `*_PREFLIGHT_*` variables. Discovery requires grepping 9 functions.

### 7. What has extraction risk?

- `main.py` is a 1,485-line monolith (boot orchestration + 9 preflights + DAE bootstrap + CLI). Any preflight extraction requires editing this file.
- `_create_ai_overseer_for_preflight` (used by OpenClaw Security and WSP-Framework) is a safe extraction candidate but touches the boot import graph.
- **Extraction risk is high**: any refactor collides with in-flight DJ / DJ-OBS / CW boot slices. Serialize implementation work on this file.

### 8. What has false claims / WSP 97 risk?

Five confirmed truth-distinction violations (each returns PASS/True while the underlying state is actually `skipped`, `insufficient_data`, or `missing`):

| Site | File / line-area | Claim | Actual state |
|---|---|---|---|
| WRE-DASHBOARD `INSUFFICIENT_DATA` | `run_wre_dashboard_preflight` (~line 790-796) | `preflight=PASS (INSUFFICIENT_DATA) samples=0/25` | insufficient_data — cannot assert health |
| IRONCLAW `SKIP` | `run_ironclaw_runtime_preflight` (~line 440) | `preflight=SKIP backend=<x>` → `return True` | skipped without asserting the skip is intentional |
| BRAIN-MEMORY `missing` | `run_brain_artifact_preflight` (~line 649) | `preflight=PASS (missing)` | directory absence treated as pass |
| OAuth | `monitor_youtube` (~line 299-301) | `[WARN] OAuth preflight...` | failure masked; downstream chat failure is the first signal |
| GIT-MERGE-SENTINEL ImportError | `run_git_main_merge_sentinel_preflight` (~line 927-930) | `preflight=WARN import_error` → `return True` | import failure non-observable |

### 9. Next smallest hardening slice

DJ2 lane, prioritized per 012:

```
DJ2-A  WRE_DASHBOARD_INSUFFICIENT_DATA_WARN_TIER
       Replace PASS(INSUFFICIENT_DATA) with WARN + dispatch.
       Severity: medium. Payload: samples, min_samples, insufficient_data=True,
       likely_cause="cold_start_or_telemetry_drop", automation_candidate=True.

DJ2-C  OAUTH_PREFLIGHT_DISPATCH
       Wire the two WARN sites in monitor_youtube's OAuth block.
       Severity: high. Payload: auto_reauth, error. Keep return behaviour.

DJ2-B  IRONCLAW_SKIP_INTENTIONALITY_ASSERTION
       Whitelist known-good backend strings. Unrecognised backend →
       dispatch severity="medium" with likely_cause=
       "unexpected_backend_string_skipped_runtime_probe".

DJ2-D  BRAIN_ARTIFACT_MISSING_DIR_EVENT
       Dispatch on "preflight=PASS (missing)" with severity="low",
       automation_candidate=False (may be intentional in minimal deployments).

DJ2-E  GIT_MERGE_SENTINEL_IMPORT_FAILURE_EVENT
       Dispatch on ImportError branch. Severity: low. Keep return behaviour.

DJ2-F  OPENCLAW_SECURITY_FAIL_DISPATCH
       Mirror DEP-SECURITY wiring at the passed=False branch.
       Severity: high by default.
```

**Serialisation requirement**: all six slices touch `main.py`. They must run one PR at a time unless a worker first extracts a shared helper (an `_emit_preflight_fail()` wrapper module that each preflight imports).

---

## Summary ratings

| Axis | Rating | Note |
|---|---|---|
| Operational completeness | PARTIAL | 9/9 preflights emit console lines; 2/9 dispatch structured events |
| Hook coverage | LOW (22%) | DJ #383 covers DEP-SECURITY + WSP-FRAMEWORK only |
| Test coverage of production failure paths | LOW | Module-local tests exist; boot-fail → dispatch → artifact chain tested only for the DJ pair |
| WSP 97 truth distinction | **VIOLATIONS** | 5 confirmed sites report PASS/True where state is `skipped`/`insufficient_data`/`missing` |
| Extraction readiness | HIGH RISK | `main.py` monolith; any lane refactor collides |
| Documentation hygiene | ADEQUATE | Per-fn docstrings present; no canonical env-var index |

---

## Out of scope for this slice

- DJ2-A through DJ2-F implementation (separate serialized slices).
- `main.py` monolith extraction (future lane).
- Canonical env-var index creation (documentation slice).
- Cross-subsystem impact of boot preflights (covered by CW1-CW5 / AG1-AG5).

## Coordination notes

- DJ PR #383 merged 2026-04-18. `preflight_resolution.py` is now available in `main`.
- DJ-OBS (AntifaFM OBS-start emitter) is independent of DJ2 but was implemented earlier; out of scope here.
- Per 012 directive, DJ2 slices must run serially, one PR each, because every slice edits `main.py`.

---

## Gates

```
G1 scope matches AG2 lane (main.py / DAE boot / AI Overseer hooks)   PASS
G2 read-only audit — no code edits                                    PASS
G3 9-question FCA1 matrix answered                                    PASS
G4 WSP 97 violations enumerated with file/line references             PASS
G5 DJ2 next-slice sequence defined and prioritised                    PASS
G6 no AntifaFM / non-AG2 paths touched                                PASS
```

**FCA1-AG2-DOCS Complete**
**Window: AG2**
**Verdict: READY_FOR_PR**
