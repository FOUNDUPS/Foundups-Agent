# AF1 — AntifaFM Internal Operational Readiness Audit (Phase 1)

**Date**: 2026-04-19
**Window**: CW2
**Slice**: AF1
**Lane**: AF
**Mode**: read-only audit
**Activity collision**: PASS (no tracked AntifaFM code files modified)
**Files edited**: none
**Live systems touched**: none

---

## Objective

Read-only operational audit of AntifaFM Broadcaster as an internal FoundUp.
Assess operational readiness, map control hooks, decide internal vs extraction,
identify OBS failure escalation point.

## Source Examined

| Path | Approx. Lines | Purpose |
|------|---------------|---------|
| `modules/platform_integration/antifafm_broadcaster/src/antifafm_broadcaster.py` | ~4,200 | Core broadcaster: FFmpeg pipeline, status FSM, heartbeat |
| `modules/platform_integration/antifafm_broadcaster/src/obs_controller.py` | ~600 | OBS WebSocket control: start/stop streaming, scene management |
| `modules/platform_integration/antifafm_broadcaster/src/visual_schema_rotator.py` | ~3,500 | Visual layer rotation, schema management |
| `modules/platform_integration/antifafm_broadcaster/src/youtube_broadcast_manager.py` | ~800 | YouTube Data API: broadcast + stream + binding |
| `modules/platform_integration/antifafm_broadcaster/src/discord_voice_adapter.py` | ~400 | Discord voice output via FFmpeg-to-Opus |
| `modules/platform_integration/antifafm_broadcaster/skillz/` | various | WRE skill triggers (news_maps, gcc_shipping_tracker, etc.) |
| Total source | ~19,000 | Full module surface |

## Operational Summary

| Dimension | Status | Evidence |
|-----------|--------|----------|
| Core broadcasting (FFmpeg→Icecast→YouTube) | Operational | Status FSM, heartbeat loop, error recovery |
| OBS WebSocket integration | Operational with gap | `start_streaming()` accepts command but `output_active` failure unescalated |
| Visual schema rotation | Operational | Rotator runs on schedule, multiple schema types |
| YouTube broadcast binding | Operational | `YouTubeBroadcastManager` solves stream-key orphan |
| Discord voice output | Operational (optional) | Adapter with fail-closed snowflake validation |
| WRE skill triggers | Partial | Skills exist but orphan rate high per scanner |
| AI Overseer integration | Gap | `_notify_ai_overseer()` only logs, no structured dispatch |
| Hermes extraction readiness | Not ready | Cross-module imports, monorepo coupling |

## Control Hook Map (15 surfaces identified)

| # | Hook | Location | Type | Escalation Path |
|---|------|----------|------|-----------------|
| 1 | FFmpeg process start/restart | `antifafm_broadcaster.py` | Process lifecycle | Logger + status FSM |
| 2 | FFmpeg health monitor | `antifafm_broadcaster.py` | Heartbeat | Restart callback |
| 3 | Icecast connection | `antifafm_broadcaster.py` | Network | Retry with backoff |
| 4 | YouTube RTMP output | `antifafm_broadcaster.py` | Network | Status FSM |
| 5 | OBS WebSocket connect | `obs_controller.py` | Network | Exception → caller |
| 6 | OBS start streaming | `obs_controller.py:325-395` | Command + verify | **GAP: logs only** |
| 7 | OBS stop streaming | `obs_controller.py` | Command | Return bool |
| 8 | OBS scene switching | `obs_controller.py` | Command | Return bool |
| 9 | OBS stream service config | `obs_controller.py:410-467` | Config mutation | `ensure_stream_service_custom()` |
| 10 | YouTube broadcast create | `youtube_broadcast_manager.py` | API call | Exception handling |
| 11 | YouTube stream bind | `youtube_broadcast_manager.py` | API call | Exception handling |
| 12 | Visual schema rotation | `visual_schema_rotator.py` | Scheduled | Logger |
| 13 | Discord voice connect | `discord_voice_adapter.py` | Network | Fail-closed |
| 14 | Discord voice health | `discord_voice_adapter.py` | Monitor | Restart callback |
| 15 | AI Overseer notify | `antifafm_broadcaster.py:546-560` | Hook | **Logger only — no dispatch** |

## OBS / DJ-OBS Decision

**Hook #6** (`obs_controller.py:start_streaming()` timeout branch, lines 376-390) is the
critical gap. OBS accepts the start command but `output_active` never becomes True.
The error code `stream_output_inactive_after_start` is logged but not dispatched to the
existing `on_preflight_fail()` contract in `preflight_resolution.py`.

**Decision**: DJ-OBS should wire a single `on_preflight_fail()` emitter at this branch.
This is an emitter addition, not infrastructure work — the dispatch contract already has
12 tests and 2 working emitters (dep_security, wsp_framework).

**Root causes for output_active failure**:
1. YouTube broadcast not bound to stream key (solvable: `YouTubeBroadcastManager`)
2. OBS modal blocking stream start (solvable: `ensure_stream_service_custom()`)
3. Misconfigured stream service type (solvable: config mutation)
4. YouTube modal requires manual click (hard floor: requires 012)

## Internal vs Extraction Verdict

**INTERNAL_NOT_READY**

Rationale:
- AntifaFM has cross-module imports (ai_overseer, wre_core, infrastructure)
- Monorepo coupling through shared config, env parsing, and import paths
- No standalone test suite — tests depend on monorepo fixtures
- Hermes extraction would require orphaned import scan, secrets audit, CI portability
- Current operational gaps (Hook #15, Hook #6) must be resolved before extraction is viable

AntifaFM remains an internal FoundUp. Extraction is a future gate after:
1. DJ-OBS emitter wired (structured escalation exists)
2. AF3 control hook map formalized
3. AF4 smoke harness proven
4. Orphaned import scan passing

## Next Slice

**AF2** — OBS failure escalation specification (read-only spec to define the DJ-OBS contract)

---

**WSP**: WSP 15 (pre-action verification), WSP 22 (ModLog), WSP 97 (no overclaiming)
**Generated**: 2026-04-19
**Agent**: 0102 (Claude Opus 4.6), CW2
