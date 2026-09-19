# Dependency Launcher Module - ROADMAP

**Module:** infrastructure/dependency_launcher
**WSP Reference:** WSP 22 (Module Roadmap Protocol)

---

## Vision Statement

Provide zero-friction startup for YouTube DAE by automatically launching all required dependencies (Chrome, LM Studio) when the DAE starts.

---

## LLME Progression

| Level | Status | Description |
|-------|--------|-------------|
| A1 | ✅ | Chrome auto-launch with debug port |
| A2 | ✅ | LM Studio auto-launch (optional) |
| A3 | ✅ | Integration with auto_moderator_dae.py |
| **A4** | 🚧 | Health monitoring and auto-restart |
| A5 | 🔮 | Multi-dependency orchestration |

---

## Phase 1: Core Dependency Launch ✅ COMPLETE

**Objective:** Auto-launch Chrome and LM Studio

- [x] `launch_chrome()` - Debug port 9222, YouTube profile
- [x] `launch_lm_studio()` - Port 1234 for UI-TARS
- [x] Port availability checks
- [x] Timeout handling (30s Chrome, 120s LM Studio)

---

## Phase 2: DAE Integration ✅ COMPLETE

**Objective:** Integrate into YouTube DAE startup

- [x] Phase -2 in `auto_moderator_dae.py`
- [x] Graceful degradation if Chrome unavailable
- [x] Optional LM Studio (falls back to DOM-only)
- [x] NAVIGATION.py entries for HoloIndex

---

## Phase 3: Health Monitoring 📋 PLANNED

**Objective:** Monitor and auto-restart crashed dependencies

### 3.1 Health Checks
- [ ] Periodic Chrome port check
- [ ] LM Studio API health endpoint
- [ ] Selenium connection validation

### 3.2 Auto-Recovery
- [ ] Detect Chrome crash → restart
- [ ] Detect LM Studio timeout → restart
- [ ] Notification to DAE on recovery

---

## Phase 4: Multi-Dependency Orchestration 🔮 FUTURE

**Objective:** Support additional DAE dependencies

- [ ] Database connections
- [ ] API service health
- [ ] External tool integration
- [ ] Dependency graph management

---

## Runtime Freshness and Compatibility

- [x] Phase 1: read-only, digest-bound startup advisory receipt.
- [x] Phase 2: WRE watchlist producer for official OpenClaw/Hermes release
  evidence plus promoted Qwen/backend expectation references.
- [ ] Authenticate source receipts and bind Qwen/backend compatibility to
  signed model benchmark and promotion evidence at use time.
- [ ] Canary and rollback receipts before any runtime or model update.

Automatic updates during `main.py` startup are explicitly rejected. The runtime
compatibility advisory observes cached evidence only; the separate opt-in WSL
version advisory executes installed programs. WRE owns research and any later
governed proposal.

## WSL advisory lifecycle boundary — 2026-09-20

- [x] Qualify current behavior and caller ownership: 25 existing tests pass;
  seven external injected witnesses show command reachability and the
  running-check/stop-before-exec race, with zero actual WSL calls. Independent
  source/caller reviews accept this bounded qualification (WSP15 13/P1).
- [ ] Implement the separately qualified existing-owner repair (C2/I4/D3/Impact3,
  12/P2) in `src/wsl_agent_runtime.py` and its existing test file.

Current behavior: the default is disabled; setting only
`FOUNDUPS_AGENT_WSL_RUNTIME_ENABLED=1` executes two fixed version commands.
Microsoft documents [distribution execution and running-state observation](https://learn.microsoft.com/en-us/windows/wsl/basic-commands)
as separate commands and [systemd startup after distribution restart](https://learn.microsoft.com/en-us/windows/wsl/systemd).
Together with the existing Gateway cold-start handling, this establishes a
possible lifecycle effect, not proof that this audit started any service.

The next source contract is **not implemented**:

| Advisory enabled | Proposed `FOUNDUPS_AGENT_WSL_COMMAND_PROBE_ENABLED` | Required result |
|---|---|---|
| false | any | Preserve existing `DISABLED` receipt bytes; no host access |
| true | absent/false | Validate registration/base; return `NOT_READY`, empty components, stable `command_probe_disabled` reason; no command runner |
| true | true | Preserve existing exact version vectors, parser, ten-second bounds and advisory receipt; possible distro/service startup |

Capture command-mode selection before invoking the registry resolver so a
callback cannot upgrade a metadata request by mutating its environment. This
snapshot selects diagnostic behavior; it is not an effect-use lease or runtime
admission. Invalid distro/base bindings still fail before execution. A separate
running-state precheck cannot remove the stop-before-exec race and is not the
chosen boundary.

Reuse the existing receipt, resolver, probe and injected fixtures. Preserve
`DEFAULT_DISTRO`, `resolve_trusted_wsl_executable()` and Gateway callers, the
fail-soft main menu, and the existing 240-line file/50-line function/200-line class
guards. No replacement launcher, supervisor, schema, skill or source owner is
needed. Metadata observation cannot yield version `PASS`. Explicit command mode
does not authorize workers, models, updates, deployment or provider effects.

The source slice must validate disabled-byte compatibility, zero calls in
metadata mode, callback mutation, rejected bindings, explicit-mode legacy results,
trusted executable resolution and connected main/Gateway fixtures. Correct the
existing source/test lifecycle overclaims without treating injected tests as a
live sandbox qualification. Exact evidence and the next packet are in the
[canonical backlog](../../../docs/roadmaps/rsi_swarm_backlog.json).

## 0102 Directive

Dependencies are orchestrated, not installed. The system self-heals. ✊✋🖐️












