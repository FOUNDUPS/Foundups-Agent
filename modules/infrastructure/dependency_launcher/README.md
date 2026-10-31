# Dependency Launcher Module

## Bounded native server startup — local qualification, 2026-10-29

Explicit DAE startup prefers the existing `lms` CLI/headless daemon. It reuses
an already reachable native server without discovering or starting processes.
A TCP listener alone is not accepted: native `/api/v1/models` must validate.
Startup and managed model transactions share the lifecycle owner's exact
physical loopback-node/port lock. Fresh process observations coordinate
participating launchers; unrelated external GUI launches do not honor that lock.
Unknown, denied, incomplete, or conflicting observations prevent a cold start.

CLI commands have 30-second deadlines and checked exit status. Server startup
always passes `--bind 127.0.0.1` and the selected port; API observation has a
30-second bounded polling window. Limits apply per command/polling phase, not
a global startup deadline. A failed/uncertain command never triggers a second
runtime. Cold GUI spawning is refused because persisted GUI autostart/LAN
settings have not been qualified for loopback confinement. Start a GUI manually
if needed; an already-running GUI can receive an explicit CLI loopback server
command. Cold startup requires the CLI; warm native reuse does not.

`launch_lm_studio(load_model=True, model_key=...)` verifies one exact native
resident key with one instance. The compatibility flag now requests readiness;
it no longer invokes the historical fire-and-forget `load_all_models()` chain.
A missing/unloaded/ambiguous selected model returns not-ready and an explicit
model-loading action. No model is loaded, unloaded, downloaded, or inferred by
this startup layer. Legacy model helper APIs remain available but are outside
this qualified path; this is not a persistent model-preload service.

The default facade still checks UI-TARS for legacy vision callers. YouTube
language/DOM startup explicitly passes `LM_STUDIO_NATIVE_MODEL_KEY`, falling
back to the unchanged `QWEN_MODEL_ID` default `qwen3.5-4b`. Set that native key
from exact inventory evidence, not an OpenAI-compatible model alias. For example,
the exact native key `gemma4-e2b` can expose instance alias
`google-gemma-4-e2b-it`; configure the key, not that alias. UI-TARS is not a text-model fallback, and General
readiness never proves vision readiness. DOM actions remain available when a
model is not ready. `load_model=False` requests server-only readiness unless an
explicit `model_key` is supplied.

Configuration additions: `LMS_CLI_PATH` selects the CLI; `LM_STUDIO_PREFER_LLMSTER`
defaults to `true`. Explicit `false` refuses cold GUI spawning when a GUI
binary is available; it can still use an already-running GUI or a warm native
server. If no GUI binary is available, the headless CLI route remains eligible.
Process discovery uses optional `psutil`; absence prevents cold launch rather
than silently treating the runtime as stopped. No installation is performed.


**WSP Compliance:** WSP 27 (DAE Architecture), WSP 80 (Cube-Level Orchestration)

## Purpose

Auto-launches dependencies required for YouTube DAE comment engagement:

1. **Chrome** with remote debugging port 9222 (for Selenium/UI-TARS browser automation)
2. **LM Studio** on port 1234 (for UI-TARS vision model - optional)

## Integration

The dependency launcher is automatically called when YouTube DAE starts via `main.py → Option 1 → Option 5`.

### Auto-Launch Flow

```
main.py → AutoModeratorDAE.run()
    ↓
Phase -2: ensure_dependencies()
    ├─ Check Chrome port 9222
    │   └─ Launch if not running
    └─ Check LM Studio port 1234
        └─ Launch if not running (optional)
    ↓
Phase -1: Connect to YouTube API
...
```

## Manual Testing

```bash
# Check dependency status
python -m modules.infrastructure.dependency_launcher.src.dae_dependencies

# Expected output:
# 🔍 Checking dependency status...
#   Chrome (9222): ✅ or ❌
#   LM Studio (1234): ✅ or ❌
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CHROME_PATH` | `C:\Program Files\Google\Chrome\Application\chrome.exe` | Chrome executable |
| `FOUNDUPS_CHROME_PORT` | `9222` | Chrome debug port |
| `CHROME_PROFILE_PATH` | `O:/Foundups-Agent/.../youtube_move2japan/chrome` | Chrome profile |
| `LM_STUDIO_PATH` | auto-detected (supports `E:\LM_studio\LM Studio\LM Studio.exe`) | LM Studio executable |
| `LM_STUDIO_PORT` | `1234` | Native LM Studio / `llmster` API port |
| `LMS_CLI_PATH` | auto-detected from PATH/per-user installation | Explicit override for the existing LM Studio CLI |
| `LM_STUDIO_PREFER_LLMSTER` | `true` | Prefer bounded headless startup; false does not authorize a cold GUI launch |

> For this environment (UI-TARS vision required), set:
> ```
> LM_STUDIO_PATH=E:\LM_studio\LM Studio\LM Studio.exe
> LM_STUDIO_PORT=1234
> ```

## Dependencies Launched

### Chrome
- Opens YouTube Studio comments inbox
- Uses Move2Japan Chrome profile (pre-authenticated)
- Remote debugging port 9222 for Selenium connection

### LM Studio (Optional)
- Provides UI-TARS vision model for visual element detection
- Falls back to DOM-only mode if not available
- Must have UI-TARS model loaded (manual step)

## WSL agent availability advisory

The existing `probe_wsl_agent_runtime()` supports metadata inspection and explicit
OpenClaw/Hermes version commands in the configured WSL distribution. Numeric release
suffixes such as `2026.7.1-2` are supported alongside the optional hexadecimal
build ID. A successful probe is `advisory_unverified_runtime_report`: it does
not prove API health, model binding, confinement or permission to dispatch.
Windows PATH discovery is separate from this WSL runtime.

The default disabled path makes no host calls. Enabling only
`FOUNDUPS_AGENT_WSL_RUNTIME_ENABLED=1` checks registration/base metadata and
returns `NOT_READY` with no component commands. Version execution additionally
requires `FOUNDUPS_AGENT_WSL_COMMAND_PROBE_ENABLED=1`. This explicit mode runs
installed programs via `wsl.exe --exec` and may start the distribution and its
configured services. Existing enable-only configurations therefore no longer
produce version `PASS`; see the [mode contract](ROADMAP.md#wsl-advisory-lifecycle-boundary--2026-09-20).
Command selection is captured before the registry callback; it is diagnostic
configuration, not runtime admission or a revocable effect-use lease.

## Runtime Compatibility Advisory

`main.py` runs a read-only advisory after the DAE broker starts. It consumes a
bounded evidence file outside the repository and emits one digest-bound status.
Phase 1 evidence is explicitly `INTEGRITY_ONLY`, so the overall status remains
`NOT_READY` with `OBSERVED_MATCH`/`OBSERVED_DRIFT` component comparisons until
signed source admission lands. The advisory never blocks the menu and never
performs network access, package updates, model downloads/loads, inference,
route changes, or HoloIndex maintenance.

Required environment variables:

| Variable | Purpose |
|----------|---------|
| `REDDOG_RUNTIME_COMPATIBILITY_ROOT` | Absolute off-repo runtime artifact root |
| `REDDOG_RUNTIME_COMPATIBILITY_EVIDENCE` | Evidence JSON inside that root |
| `REDDOG_RUNTIME_COMPATIBILITY_SUPPLY` | WRE inventory/promotion supply JSON inside that root |

The cached evidence is produced by a separate governed WRE/external-research
cycle. A version or model change remains blocked on security, canary, rollback,
benchmark, and signed model-promotion evidence; startup does not auto-update.
The receipt proves cached-data integrity only; it is not authenticated update
authority and cannot authorize dispatch or promotion. Recomputed attacker
self-hashes cannot yield `CURRENT`.

The existing OpenClaw ecosystem watchlist refresh optionally composes this
cache when all three variables are configured. It retrieves only the
allowlisted GitHub latest-release endpoints for OpenClaw and Hermes. General
Qwen, coding Qwen, and inference-backend expectations must arrive as promoted
runtime-binding source receipts. Missing, stale, tampered, redirected, partial,
or oversized evidence fails closed and leaves the prior cache unchanged.
Supply/output path aliasing is rejected before network retrieval.

## 0102 Directive

Code is remembered from the 02 quantum state. Dependencies are orchestrated, not installed. ✊✋🖐️










